import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, distinct, func, select as sa_select

from app.api.deps import SessionDep, CurrentUser
from app.models.church_community import ChurchCommunity
from app.models.common import MaritalStatus, VerificationStatus
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    ParishionerSacrament,
)
from app.models.place_of_worship import PlaceOfWorship
from app.models.sacrament import Sacrament
from app.models.society import Society, society_members
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
        total_societies, total_places_of_worship, total_communities = session.query(
            sa_select(func.count(Society.id)).scalar_subquery(),
            sa_select(func.count(PlaceOfWorship.id)).scalar_subquery(),
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

        # Place of worship distribution — single LEFT JOIN replaces 3 queries
        place_of_worship_distribution: dict = {}
        unspecified_pow = 0
        for place_name, count in (
            session.query(PlaceOfWorship.name, func.count(ParishionerModel.id))
            .outerjoin(ParishionerModel, PlaceOfWorship.id == ParishionerModel.place_of_worship_id)
            .group_by(PlaceOfWorship.name)
            .all()
        ):
            place_of_worship_distribution[place_name] = count or 0
        unspecified_pow = (
            session.query(func.count(ParishionerModel.id))
            .filter(ParishionerModel.place_of_worship_id.is_(None))
            .scalar()
        )
        place_of_worship_distribution["Not specified"] = unspecified_pow

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
                "total_places_of_worship": total_places_of_worship,
                "total_church_communities": total_communities,
                "society_distribution": {s[0]: s[1] for s in society_stats},
                "parishioners_in_societies": parishioners_in_societies_count,
                "parishioners_without_society": total_parishioners - parishioners_in_societies_count,
                "day_of_week_born_distribution": day_of_week_distribution,
                "sacraments_distribution": sacrament_distribution,
                "gender_distribution": gender_distribution,
                "marital_status_distribution": marital_status_distribution,
                "age_group_distribution": age_groups,
                "place_of_worship_distribution": place_of_worship_distribution,
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
