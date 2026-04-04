import logging
import time
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import case, distinct, func, select as sa_select

from app.api.deps import SessionDep, CurrentUser, ChurchUnitScope
from app.models.audit import AuditLog
from app.models.church_community import ChurchCommunity
from app.models.common import MaritalStatus, MembershipStatus, VerificationStatus
from app.models.messaging import ScheduledMessage, ScheduledMessageStatus
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    ParishionerSacrament,
)
from app.models.parish import ChurchUnit, ChurchUnitType, MassSchedule, MassType
from app.models.rbac import Role
from app.models.sacrament import Sacrament
from app.models.society import Society, society_members
from app.models.user import User as UserModel, UserStatus
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache: {cache_key: (timestamp, data)}
_stats_cache: dict = {}
_STATS_TTL = 300  # 5 minutes


@router.get("/parishioners", response_model=APIResponse)
async def get_parishioner_stats(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get general statistics about parishioners."""
    cache_key = "parishioner_stats"
    now = time.time()
    if cache_key in _stats_cache:
        ts, cached = _stats_cache[cache_key]
        if now - ts < _STATS_TTL:
            return cached

    try:
        total_parishioners = session.query(func.count(ParishionerModel.id)).scalar()

        # Use scalar subqueries to avoid cross-join bug
        total_outstations_sq = sa_select(func.count(ChurchUnit.id)).where(
            ChurchUnit.type == ChurchUnitType.OUTSTATION
        ).scalar_subquery()
        total_societies, total_stations, total_communities = session.query(
            sa_select(func.count(Society.id)).scalar_subquery(),
            total_outstations_sq,
            sa_select(func.count(ChurchCommunity.id)).scalar_subquery(),
        ).one()

        society_stats = (
            session.query(Society.name, func.count(society_members.c.parishioner_id))
            .join(society_members, Society.id == society_members.c.society_id)
            .group_by(Society.id, Society.name)
            .all()
        )

        parishioners_in_societies_count = (
            session.query(func.count(distinct(society_members.c.parishioner_id))).scalar()
        )

        day_of_week_stats = (
            session.query(
                func.extract('dow', ParishionerModel.date_of_birth),
                func.count(ParishionerModel.id),
            )
            .group_by(func.extract('dow', ParishionerModel.date_of_birth))
            .all()
        )

        days_of_week = {
            0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
            4: "Thursday", 5: "Friday", 6: "Saturday",
        }
        day_of_week_distribution = {day_name: 0 for day_name in days_of_week.values()}
        for day, count in day_of_week_stats:
            if day is not None:
                day_of_week_distribution[days_of_week[int(day)]] = count

        # Single LEFT JOIN covers both "all sacraments" and counts
        sacrament_distribution = {}
        for sacrament_name, count in (
            session.query(Sacrament.name, func.count(distinct(ParishionerSacrament.parishioner_id)))
            .outerjoin(ParishionerSacrament, Sacrament.id == ParishionerSacrament.sacrament_id)
            .group_by(Sacrament.name)
            .all()
        ):
            sacrament_distribution[sacrament_name] = count or 0

        gender_stats = (
            session.query(ParishionerModel.gender, func.count(ParishionerModel.id))
            .group_by(ParishionerModel.gender)
            .all()
        )
        gender_distribution = {g[0].value if g[0] else "Not specified": g[1] for g in gender_stats}

        marital_status_distribution = {s.value: 0 for s in MaritalStatus}
        marital_status_stats = (
            session.query(ParishionerModel.marital_status, func.count(ParishionerModel.id))
            .group_by(ParishionerModel.marital_status)
            .all()
        )
        for ms, count in marital_status_stats:
            if ms is not None:
                marital_status_distribution[ms.value] = count

        current_year = datetime.now(timezone.utc).year
        age_groups = {"0-17": 0, "18-25": 0, "26-40": 0, "41-60": 0, "61+": 0, "Unknown": 0}
        for year_born, count in session.query(
            func.extract('year', ParishionerModel.date_of_birth),
            func.count(ParishionerModel.id),
        ).group_by(func.extract('year', ParishionerModel.date_of_birth)).all():
            if year_born is None:
                age_groups["Unknown"] += count
            else:
                age = current_year - int(year_born)
                if age <= 17:
                    age_groups["0-17"] += count
                elif age <= 25:
                    age_groups["18-25"] += count
                elif age <= 40:
                    age_groups["26-40"] += count
                elif age <= 60:
                    age_groups["41-60"] += count
                else:
                    age_groups["61+"] += count

        # Church unit distribution — single LEFT JOIN
        outstation_distribution: dict = {}
        for unit_name, count in (
            session.query(ChurchUnit.name, func.count(ParishionerModel.id))
            .outerjoin(ParishionerModel, ChurchUnit.id == ParishionerModel.church_unit_id)
            .filter(ChurchUnit.type == ChurchUnitType.OUTSTATION)
            .group_by(ChurchUnit.name)
            .all()
        ):
            outstation_distribution[unit_name] = count or 0
        outstation_distribution["Not specified"] = (
            session.query(func.count(ParishionerModel.id))
            .filter(ParishionerModel.church_unit_id.is_(None))
            .scalar()
        )

        # Church community distribution — single LEFT JOIN replaces 3 queries
        church_community_distribution: dict = {}
        for community_name, count in (
            session.query(ChurchCommunity.name, func.count(ParishionerModel.id))
            .outerjoin(ParishionerModel, ChurchCommunity.id == ParishionerModel.church_community_id)
            .group_by(ChurchCommunity.name)
            .all()
        ):
            church_community_distribution[community_name] = count or 0
        church_community_distribution["Not specified"] = (
            session.query(func.count(ParishionerModel.id))
            .filter(ParishionerModel.church_community_id.is_(None))
            .scalar()
        )

        result = APIResponse(
            message="Parishioner statistics retrieved successfully",
            data={
                "total_parishioners": total_parishioners,
                "total_societies": total_societies,
                "total_outstations": total_stations,
                "total_church_communities": total_communities,
                "society_distribution": {s[0]: s[1] for s in society_stats},
                "parishioners_in_societies": parishioners_in_societies_count,
                "parishioners_without_society": total_parishioners - parishioners_in_societies_count,
                "day_of_week_born_distribution": day_of_week_distribution,
                "sacraments_distribution": sacrament_distribution,
                "gender_distribution": gender_distribution,
                "marital_status_distribution": marital_status_distribution,
                "age_group_distribution": age_groups,
                "outstation_distribution": outstation_distribution,
                "church_community_distribution": church_community_distribution,
            },
        )
        _stats_cache[cache_key] = (now, result)
        return result

    except Exception as e:
        logger.error(f"Error retrieving parishioner statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving parishioner statistics",
        )


@router.get("/registration", response_model=APIResponse)
async def get_registration_stats(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get statistics about parishioner registration and verification status."""
    try:
        # Single query replaces five separate scalar queries
        total, verified, pending, with_id = session.query(
            func.count(ParishionerModel.id),
            func.count(case((ParishionerModel.verification_status == VerificationStatus.VERIFIED, 1))),
            func.count(case((ParishionerModel.verification_status == VerificationStatus.PENDING, 1))),
            func.count(case((ParishionerModel.new_church_id.isnot(None), 1))),
        ).one()

        return APIResponse(
            message="Registration statistics retrieved successfully",
            data={
                "total_parishioners": total,
                "total_verified": verified,
                "total_pending_verification": pending,
                "total_unverified": total - verified - pending,
                "total_with_new_church_id": with_id,
                "total_without_new_church_id": total - with_id,
            },
        )

    except Exception as e:
        logger.error(f"Error retrieving registration statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving registration statistics",
        )


# ── Dashboard: System Tab ─────────────────────────────────────────────────────

@router.get("/dashboard/system", response_model=APIResponse)
async def get_system_dashboard(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    System-level dashboard stats (Tab 1).
    Covers church hierarchy, mass services, users & access, and communications.
    No unit scoping — this is a parish-wide view for admins.
    """
    cache_key = "dashboard_system"
    now = time.time()
    if cache_key in _stats_cache:
        ts, cached = _stats_cache[cache_key]
        if now - ts < _STATS_TTL:
            return cached

    try:
        # ── Church Hierarchy ──────────────────────────────────────────────────
        parish_count, outstation_count = session.query(
            func.count(case((ChurchUnit.type == ChurchUnitType.PARISH, 1))),
            func.count(case((ChurchUnit.type == ChurchUnitType.OUTSTATION, 1))),
        ).one()

        active_units = session.query(func.count(ChurchUnit.id)).filter(ChurchUnit.is_active == True).scalar()

        outstations = (
            session.query(ChurchUnit.id, ChurchUnit.name, ChurchUnit.is_active, ChurchUnit.parent_id)
            .filter(ChurchUnit.type == ChurchUnitType.OUTSTATION)
            .all()
        )
        parent_ids = {o.parent_id for o in outstations if o.parent_id}
        parent_names = {}
        if parent_ids:
            for row in session.query(ChurchUnit.id, ChurchUnit.name).filter(ChurchUnit.id.in_(parent_ids)).all():
                parent_names[row.id] = row.name

        hierarchy = [
            {
                "id": o.id,
                "name": o.name,
                "is_active": o.is_active,
                "parent": parent_names.get(o.parent_id),
            }
            for o in outstations
        ]

        # ── Mass Services ─────────────────────────────────────────────────────
        total_schedules = session.query(func.count(MassSchedule.id)).scalar()

        by_mass_type = {
            row[0].value: row[1]
            for row in session.query(MassSchedule.mass_type, func.count(MassSchedule.id))
            .group_by(MassSchedule.mass_type).all()
        }
        by_day = {
            row[0].value: row[1]
            for row in session.query(MassSchedule.day_of_week, func.count(MassSchedule.id))
            .group_by(MassSchedule.day_of_week).all()
        }
        active_schedules = session.query(func.count(MassSchedule.id)).filter(MassSchedule.is_active == True).scalar()

        # ── Users & Access ────────────────────────────────────────────────────
        total_users = session.query(func.count(UserModel.id)).scalar()

        by_status = {
            row[0].value: row[1]
            for row in session.query(UserModel.status, func.count(UserModel.id))
            .group_by(UserModel.status).all()
        }

        by_role = {}
        for role_name, role_label, count in (
            session.query(Role.name, Role.label, func.count(UserModel.id))
            .join(UserModel, UserModel.role_id == Role.id)
            .group_by(Role.id, Role.name, Role.label)
            .all()
        ):
            by_role[role_label] = count

        users_with_no_role = session.query(func.count(UserModel.id)).filter(UserModel.role_id.is_(None)).scalar()

        # ── Communications ────────────────────────────────────────────────────
        msg_stats = {}
        total_sent_recipients = 0
        for msg_status, count, recipients in (
            session.query(
                ScheduledMessage.status,
                func.count(ScheduledMessage.id),
                func.coalesce(func.sum(ScheduledMessage.sent_count), 0),
            )
            .group_by(ScheduledMessage.status)
            .all()
        ):
            msg_stats[msg_status.value] = {"messages": count, "recipients": recipients}
            if msg_status == ScheduledMessageStatus.SENT:
                total_sent_recipients = recipients

        result = APIResponse(
            message="System dashboard statistics retrieved",
            data={
                "church_hierarchy": {
                    "total_parishes": parish_count,
                    "total_outstations": outstation_count,
                    "total_units": parish_count + outstation_count,
                    "active_units": active_units,
                    "outstations": hierarchy,
                },
                "mass_services": {
                    "total_schedules": total_schedules,
                    "active_schedules": active_schedules,
                    "by_mass_type": by_mass_type,
                    "by_day_of_week": by_day,
                },
                "users_and_access": {
                    "total_users": total_users,
                    "by_status": by_status,
                    "by_role": by_role,
                    "no_role_assigned": users_with_no_role,
                },
                "communications": {
                    "by_status": msg_stats,
                    "total_recipients_reached": total_sent_recipients,
                },
            },
        )
        _stats_cache[cache_key] = (now, result)
        return result

    except Exception as e:
        logger.error(f"Error retrieving system dashboard: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving system dashboard")


# ── Dashboard: Station Tab ────────────────────────────────────────────────────

@router.get("/dashboard/station", response_model=APIResponse)
async def get_station_dashboard(
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
) -> Any:
    """
    Station/unit-level dashboard stats (Tab 2).
    Scoped to the unit selected via X-Church-Unit-Id header.
    Super admins with no header get parish-wide aggregates.
    Covers: overview, demographics, societies, communities, sacraments, financials.
    """
    cache_key = f"dashboard_station_{unit_scope}"
    now = time.time()
    if cache_key in _stats_cache:
        ts, cached = _stats_cache[cache_key]
        if now - ts < _STATS_TTL:
            return cached

    try:
        base_q = session.query(ParishionerModel)
        if unit_scope is not None:
            base_q = base_q.filter(ParishionerModel.church_unit_id == unit_scope)

        # ── Overview ──────────────────────────────────────────────────────────
        total, verified, pending, with_id, deceased = base_q.with_entities(
            func.count(ParishionerModel.id),
            func.count(case((ParishionerModel.verification_status == VerificationStatus.VERIFIED, 1))),
            func.count(case((ParishionerModel.verification_status == VerificationStatus.PENDING, 1))),
            func.count(case((ParishionerModel.new_church_id.isnot(None), 1))),
            func.count(case((ParishionerModel.membership_status == MembershipStatus.DECEASED, 1))),
        ).one()

        unverified = total - verified - pending
        active = total - deceased

        # ── Demographics ──────────────────────────────────────────────────────
        gender_dist = {
            (g.value if g else "not_specified"): cnt
            for g, cnt in base_q.with_entities(ParishionerModel.gender, func.count(ParishionerModel.id))
            .group_by(ParishionerModel.gender).all()
        }

        marital_dist = {s.value: 0 for s in MaritalStatus}
        for ms, cnt in (
            base_q.with_entities(ParishionerModel.marital_status, func.count(ParishionerModel.id))
            .group_by(ParishionerModel.marital_status).all()
        ):
            if ms:
                marital_dist[ms.value] = cnt

        current_year = datetime.now(timezone.utc).year
        age_groups = {"0-17": 0, "18-25": 0, "26-40": 0, "41-60": 0, "61+": 0, "unknown": 0}
        for year_born, cnt in (
            base_q.with_entities(
                func.extract("year", ParishionerModel.date_of_birth),
                func.count(ParishionerModel.id),
            ).group_by(func.extract("year", ParishionerModel.date_of_birth)).all()
        ):
            if year_born is None:
                age_groups["unknown"] += cnt
            else:
                age = current_year - int(year_born)
                if age <= 17:       age_groups["0-17"] += cnt
                elif age <= 25:     age_groups["18-25"] += cnt
                elif age <= 40:     age_groups["26-40"] += cnt
                elif age <= 60:     age_groups["41-60"] += cnt
                else:               age_groups["61+"] += cnt

        days_map = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday"}
        birth_day_dist = {d: 0 for d in days_map.values()}
        for dow, cnt in (
            base_q.with_entities(
                func.extract("dow", ParishionerModel.date_of_birth),
                func.count(ParishionerModel.id),
            ).group_by(func.extract("dow", ParishionerModel.date_of_birth)).all()
        ):
            if dow is not None:
                birth_day_dist[days_map[int(dow)]] = cnt

        # Per-gender: age groups
        age_groups_by_gender: dict = {}
        for gender, year_born, cnt in (
            base_q.with_entities(
                ParishionerModel.gender,
                func.extract("year", ParishionerModel.date_of_birth),
                func.count(ParishionerModel.id),
            ).group_by(ParishionerModel.gender, func.extract("year", ParishionerModel.date_of_birth)).all()
        ):
            g_key = gender.value if gender else "not_specified"
            bucket = age_groups_by_gender.setdefault(g_key, {"0-17": 0, "18-25": 0, "26-40": 0, "41-60": 0, "61+": 0, "unknown": 0})
            if year_born is None:
                bucket["unknown"] += cnt
            else:
                age = current_year - int(year_born)
                if age <= 17:       bucket["0-17"] += cnt
                elif age <= 25:     bucket["18-25"] += cnt
                elif age <= 40:     bucket["26-40"] += cnt
                elif age <= 60:     bucket["41-60"] += cnt
                else:               bucket["61+"] += cnt

        # Per-gender: marital status
        marital_by_gender: dict = {}
        for gender, ms, cnt in (
            base_q.with_entities(
                ParishionerModel.gender,
                ParishionerModel.marital_status,
                func.count(ParishionerModel.id),
            ).group_by(ParishionerModel.gender, ParishionerModel.marital_status).all()
        ):
            g_key = gender.value if gender else "not_specified"
            m_key = ms.value if ms else "not_specified"
            marital_by_gender.setdefault(g_key, {})[m_key] = cnt

        # Per-gender: birth day of week
        birth_day_by_gender: dict = {}
        for gender, dow, cnt in (
            base_q.with_entities(
                ParishionerModel.gender,
                func.extract("dow", ParishionerModel.date_of_birth),
                func.count(ParishionerModel.id),
            ).group_by(ParishionerModel.gender, func.extract("dow", ParishionerModel.date_of_birth)).all()
        ):
            if dow is None:
                continue
            g_key = gender.value if gender else "not_specified"
            birth_day_by_gender.setdefault(g_key, {d: 0 for d in days_map.values()})[days_map[int(dow)]] = cnt

        # ── Societies ─────────────────────────────────────────────────────────
        soc_q = session.query(Society)
        if unit_scope is not None:
            soc_q = soc_q.filter(Society.church_unit_id == unit_scope)

        total_societies = soc_q.count()

        _soc_unit_filter = (Society.church_unit_id == unit_scope) if unit_scope is not None else True

        society_member_counts = (
            session.query(Society.name, func.count(society_members.c.parishioner_id))
            .join(society_members, Society.id == society_members.c.society_id)
            .filter(_soc_unit_filter)
            .group_by(Society.id, Society.name)
            .all()
        )

        parishioners_in_any_society = (
            session.query(func.count(distinct(society_members.c.parishioner_id)))
            .join(Society, Society.id == society_members.c.society_id)
            .filter(_soc_unit_filter)
            .scalar()
        )

        # Per-society: by gender
        soc_gender_rows = (
            session.query(Society.name, ParishionerModel.gender, func.count(distinct(ParishionerModel.id)))
            .join(society_members, Society.id == society_members.c.society_id)
            .join(ParishionerModel, ParishionerModel.id == society_members.c.parishioner_id)
            .filter(_soc_unit_filter)
            .group_by(Society.id, Society.name, ParishionerModel.gender)
            .all()
        )
        soc_by_gender: dict = {}
        for soc_name, gender, cnt in soc_gender_rows:
            soc_by_gender.setdefault(soc_name, {})[gender.value if gender else "not_specified"] = cnt

        # Per-society: by membership status
        soc_membership_rows = (
            session.query(Society.name, society_members.c.membership_status, func.count(society_members.c.parishioner_id))
            .join(society_members, Society.id == society_members.c.society_id)
            .filter(_soc_unit_filter)
            .group_by(Society.id, Society.name, society_members.c.membership_status)
            .all()
        )
        soc_by_membership: dict = {}
        for soc_name, mem_status, cnt in soc_membership_rows:
            soc_by_membership.setdefault(soc_name, {})[mem_status.value if mem_status else "not_specified"] = cnt

        society_detail = {
            soc_name: {
                "total_members": cnt,
                "by_gender": soc_by_gender.get(soc_name, {}),
                "by_membership_status": soc_by_membership.get(soc_name, {}),
            }
            for soc_name, cnt in society_member_counts
        }

        # ── Church Communities ────────────────────────────────────────────────
        comm_q = session.query(ChurchCommunity)
        if unit_scope is not None:
            comm_q = comm_q.filter(ChurchCommunity.church_unit_id == unit_scope)

        total_communities = comm_q.count()

        _comm_unit_filter = (ChurchCommunity.church_unit_id == unit_scope) if unit_scope is not None else True

        community_member_counts = (
            session.query(ChurchCommunity.name, func.count(ParishionerModel.id))
            .outerjoin(ParishionerModel, ChurchCommunity.id == ParishionerModel.church_community_id)
            .filter(_comm_unit_filter)
            .group_by(ChurchCommunity.id, ChurchCommunity.name)
            .all()
        )
        no_community = base_q.filter(ParishionerModel.church_community_id.is_(None)).count()

        # Per-community: by gender
        comm_gender_rows = (
            session.query(ChurchCommunity.name, ParishionerModel.gender, func.count(ParishionerModel.id))
            .outerjoin(ParishionerModel, ChurchCommunity.id == ParishionerModel.church_community_id)
            .filter(_comm_unit_filter)
            .group_by(ChurchCommunity.id, ChurchCommunity.name, ParishionerModel.gender)
            .all()
        )
        comm_by_gender: dict = {}
        for comm_name, gender, cnt in comm_gender_rows:
            comm_by_gender.setdefault(comm_name, {})[gender.value if gender else "not_specified"] = cnt

        # Per-community: by marital status
        comm_marital_rows = (
            session.query(ChurchCommunity.name, ParishionerModel.marital_status, func.count(ParishionerModel.id))
            .outerjoin(ParishionerModel, ChurchCommunity.id == ParishionerModel.church_community_id)
            .filter(_comm_unit_filter)
            .group_by(ChurchCommunity.id, ChurchCommunity.name, ParishionerModel.marital_status)
            .all()
        )
        comm_by_marital: dict = {}
        for comm_name, ms, cnt in comm_marital_rows:
            comm_by_marital.setdefault(comm_name, {})[ms.value if ms else "not_specified"] = cnt

        community_detail = {
            comm_name: {
                "total_members": cnt,
                "by_gender": comm_by_gender.get(comm_name, {}),
                "by_marital_status": comm_by_marital.get(comm_name, {}),
            }
            for comm_name, cnt in community_member_counts
        }

        # ── Sacraments ────────────────────────────────────────────────────────
        _sac_unit_filter = (ParishionerModel.church_unit_id == unit_scope) if unit_scope is not None else True

        # Summary: count of parishioners (scoped) per sacrament
        sac_summary_rows = (
            session.query(Sacrament.name, func.count(distinct(ParishionerModel.id)))
            .outerjoin(ParishionerSacrament, Sacrament.id == ParishionerSacrament.sacrament_id)
            .outerjoin(ParishionerModel, ParishionerModel.id == ParishionerSacrament.parishioner_id)
            .filter(_sac_unit_filter)
            .group_by(Sacrament.name)
            .all()
        )

        # Per-sacrament: by gender
        sac_gender_rows = (
            session.query(Sacrament.name, ParishionerModel.gender, func.count(distinct(ParishionerModel.id)))
            .join(ParishionerSacrament, Sacrament.id == ParishionerSacrament.sacrament_id)
            .join(ParishionerModel, ParishionerModel.id == ParishionerSacrament.parishioner_id)
            .filter(_sac_unit_filter)
            .group_by(Sacrament.name, ParishionerModel.gender)
            .all()
        )
        sac_by_gender: dict = {}
        for sac_name, gender, cnt in sac_gender_rows:
            sac_by_gender.setdefault(sac_name, {})[gender.value if gender else "not_specified"] = cnt

        # Per-sacrament: by community
        sac_community_rows = (
            session.query(Sacrament.name, ChurchCommunity.name, func.count(distinct(ParishionerModel.id)))
            .join(ParishionerSacrament, Sacrament.id == ParishionerSacrament.sacrament_id)
            .join(ParishionerModel, ParishionerModel.id == ParishionerSacrament.parishioner_id)
            .outerjoin(ChurchCommunity, ChurchCommunity.id == ParishionerModel.church_community_id)
            .filter(_sac_unit_filter)
            .group_by(Sacrament.name, ChurchCommunity.id, ChurchCommunity.name)
            .all()
        )
        sac_by_community: dict = {}
        for sac_name, comm_name, cnt in sac_community_rows:
            sac_by_community.setdefault(sac_name, {})[comm_name or "not_specified"] = cnt

        # Per-sacrament: by age group (aggregated from year_born)
        sac_age_rows = (
            session.query(
                Sacrament.name,
                func.extract("year", ParishionerModel.date_of_birth),
                func.count(distinct(ParishionerModel.id)),
            )
            .join(ParishionerSacrament, Sacrament.id == ParishionerSacrament.sacrament_id)
            .join(ParishionerModel, ParishionerModel.id == ParishionerSacrament.parishioner_id)
            .filter(_sac_unit_filter)
            .group_by(Sacrament.name, func.extract("year", ParishionerModel.date_of_birth))
            .all()
        )
        sac_by_age: dict = {}
        _default_age_buckets = {"0-17": 0, "18-25": 0, "26-40": 0, "41-60": 0, "61+": 0, "unknown": 0}
        for sac_name, year_born, cnt in sac_age_rows:
            ag = "unknown"
            if year_born is not None:
                age = current_year - int(year_born)
                if age <= 17:       ag = "0-17"
                elif age <= 25:     ag = "18-25"
                elif age <= 40:     ag = "26-40"
                elif age <= 60:     ag = "41-60"
                else:               ag = "61+"
            bucket = sac_by_age.setdefault(sac_name, {**_default_age_buckets})
            bucket[ag] = bucket.get(ag, 0) + cnt

        sacrament_dist = {
            sac_name: {
                "count": cnt or 0,
                "percentage": round((cnt / total * 100), 1) if total else 0,
                "by_gender": sac_by_gender.get(sac_name, {}),
                "by_community": sac_by_community.get(sac_name, {}),
                "by_age_group": sac_by_age.get(sac_name, {**_default_age_buckets}),
            }
            for sac_name, cnt in sac_summary_rows
        }

        result = APIResponse(
            message="Station dashboard statistics retrieved",
            data={
                "scoped_to_unit_id": unit_scope,
                "overview": {
                    "total_parishioners": total,
                    "active": active,
                    "deceased": deceased,
                    "verified": verified,
                    "pending_verification": pending,
                    "unverified": unverified,
                    "with_church_id": with_id,
                    "without_church_id": total - with_id,
                    "verification_rate_pct": round(verified / total * 100, 1) if total else 0,
                    "church_id_coverage_pct": round(with_id / total * 100, 1) if total else 0,
                },
                "demographics": {
                    "gender": gender_dist,
                    "age_groups": {
                        "total": age_groups,
                        "by_gender": age_groups_by_gender,
                    },
                    "marital_status": {
                        "total": marital_dist,
                        "by_gender": marital_by_gender,
                    },
                    "birth_day_of_week": {
                        "total": birth_day_dist,
                        "by_gender": birth_day_by_gender,
                    },
                },
                "societies": {
                    "total_societies": total_societies,
                    "parishioners_in_at_least_one_society": parishioners_in_any_society,
                    "parishioners_not_in_any_society": total - parishioners_in_any_society,
                    "society_coverage_pct": round(parishioners_in_any_society / total * 100, 1) if total else 0,
                    "by_society": society_detail,
                },
                "church_communities": {
                    "total_communities": total_communities,
                    "parishioners_without_community": no_community,
                    "community_coverage_pct": round((total - no_community) / total * 100, 1) if total else 0,
                    "by_community": community_detail,
                },
                "sacraments": sacrament_dist,
                "financials": {
                    "_note": "Financial tracking not yet implemented.",
                },
            },
        )
        _stats_cache[cache_key] = (now, result)
        return result

    except Exception as e:
        logger.error(f"Error retrieving station dashboard: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving station dashboard")
