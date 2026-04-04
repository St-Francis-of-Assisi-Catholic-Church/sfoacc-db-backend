import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import joinedload

from app.api.deps import ChurchUnitScope, CurrentUser, SessionDep, require_permission
from app.models.church_community import ChurchCommunity
from app.models.common import VerificationStatus
from app.models.parishioner.core import Parishioner as ParishionerModel
from app.models.parish import ChurchUnit
from app.models.society import society_members
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)

data_quality_router = APIRouter()

_REQUIRE = require_permission("parishioner:write")

# ── Issue catalogue ───────────────────────────────────────────────────────────

ISSUE_LABELS: dict[str, str] = {
    "missing_dob":            "Missing date of birth",
    "missing_phone":          "No phone number (mobile or WhatsApp)",
    "missing_baptismal_name": "Missing baptismal name",
    "missing_community":      "Not assigned to a church community",
    "missing_church_unit":    "Not assigned to a church unit / outstation",
    "no_church_id":           "No church ID assigned",
    "unverified":             "Verification status: unverified",
    "no_nationality":         "Nationality not recorded",
    "no_hometown":            "Hometown not recorded",
    "no_society":             "Not a member of any society",
}


def _sql_condition(issue: str):
    """Return the SQLAlchemy WHERE clause for an issue key."""
    if issue == "missing_dob":
        return ParishionerModel.date_of_birth.is_(None)
    if issue == "missing_phone":
        return and_(
            ParishionerModel.mobile_number.is_(None),
            ParishionerModel.whatsapp_number.is_(None),
        )
    if issue == "missing_baptismal_name":
        return ParishionerModel.baptismal_name.is_(None)
    if issue == "missing_community":
        return ParishionerModel.church_community_id.is_(None)
    if issue == "missing_church_unit":
        return ParishionerModel.church_unit_id.is_(None)
    if issue == "no_church_id":
        return ParishionerModel.new_church_id.is_(None)
    if issue == "unverified":
        return ParishionerModel.verification_status == VerificationStatus.UNVERIFIED
    if issue == "no_nationality":
        return ParishionerModel.nationality.is_(None)
    if issue == "no_hometown":
        return ParishionerModel.hometown.is_(None)
    if issue == "no_society":
        return ~exists().where(
            society_members.c.parishioner_id == ParishionerModel.id
        )
    return None


def _compute_issues(p: ParishionerModel, society_member_ids: set) -> list[str]:
    """Evaluate data issues for a single loaded parishioner (Python-side)."""
    issues = []
    if p.date_of_birth is None:
        issues.append("missing_dob")
    if p.mobile_number is None and p.whatsapp_number is None:
        issues.append("missing_phone")
    if p.baptismal_name is None:
        issues.append("missing_baptismal_name")
    if p.church_community_id is None:
        issues.append("missing_community")
    if p.church_unit_id is None:
        issues.append("missing_church_unit")
    if p.new_church_id is None:
        issues.append("no_church_id")
    if p.verification_status == VerificationStatus.UNVERIFIED:
        issues.append("unverified")
    if p.nationality is None:
        issues.append("no_nationality")
    if p.hometown is None:
        issues.append("no_hometown")
    if p.id not in society_member_ids:
        issues.append("no_society")
    return issues


_SORT_FIELDS = {
    "last_name":  ParishionerModel.last_name,
    "first_name": ParishionerModel.first_name,
    "created_at": ParishionerModel.created_at,
    "updated_at": ParishionerModel.updated_at,
}


# ── Endpoint ──────────────────────────────────────────────────────────────────

@data_quality_router.get("", dependencies=[_REQUIRE], response_model=APIResponse)
async def get_data_quality(
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    issues: Optional[List[str]] = Query(
        default=None,
        description=(
            "Show only parishioners with these issues (OR logic). "
            f"Valid keys: {', '.join(ISSUE_LABELS)}"
        ),
    ),
    sort_by: str = Query(
        default="last_name",
        description="Sort field: last_name | first_name | created_at | updated_at",
    ),
    sort_dir: str = Query(default="asc", description="asc | desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Any:
    """
    Data quality audit — parishioners with missing or incomplete fields.

    Returns per-issue summary counts and a paginated list of flagged records.
    Each record includes a `data_issues` array listing every issue found on it.

    Filter with ?issues=missing_dob&issues=missing_phone to focus on specific
    problems. Omit the filter to return all parishioners that have at least one
    issue.

    Scoped via X-Church-Unit-Id header (non-super-admins are auto-scoped to
    their assigned unit).

    Accessible to: super_admin, church_administrator, database_management_team,
    church_secretary.
    """
    # Validate requested issue keys
    if issues:
        invalid = [k for k in issues if k not in ISSUE_LABELS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unknown issue key(s): {invalid}. "
                    f"Valid keys: {list(ISSUE_LABELS.keys())}"
                ),
            )

    # ── Scoped base query ─────────────────────────────────────────────────────
    base_q = session.query(ParishionerModel).options(
        joinedload(ParishionerModel.church_unit),
        joinedload(ParishionerModel.church_community),
    )
    if unit_scope is not None:
        base_q = base_q.filter(ParishionerModel.church_unit_id == unit_scope)

    # ── Summary: count per issue type (ignores the issues filter) ─────────────
    summary: dict = {}
    for key, label in ISSUE_LABELS.items():
        cond = _sql_condition(key)
        if cond is not None:
            summary[key] = {
                "label": label,
                "count": base_q.filter(cond).count(),
            }

    # Total parishioners with at least one issue
    all_conds = [c for c in (_sql_condition(k) for k in ISSUE_LABELS) if c is not None]
    total_with_any_issue = base_q.filter(or_(*all_conds)).count() if all_conds else 0

    # ── Apply issues filter ───────────────────────────────────────────────────
    filter_keys = issues if issues else list(ISSUE_LABELS.keys())
    filter_conds = [c for c in (_sql_condition(k) for k in filter_keys) if c is not None]
    filter_q = base_q.filter(or_(*filter_conds)) if filter_conds else base_q

    # ── Sort ──────────────────────────────────────────────────────────────────
    sort_col = _SORT_FIELDS.get(sort_by, ParishionerModel.last_name)
    filter_q = filter_q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # ── Paginate ──────────────────────────────────────────────────────────────
    total_filtered = filter_q.count()
    parishioners = filter_q.offset((page - 1) * page_size).limit(page_size).all()

    # ── Society membership for this page (single batch query) ─────────────────
    par_ids = {p.id for p in parishioners}
    society_member_ids: set = set()
    if par_ids:
        rows = session.execute(
            society_members.select().where(
                society_members.c.parishioner_id.in_(par_ids)
            )
        ).fetchall()
        society_member_ids = {r.parishioner_id for r in rows}

    # ── Serialise ─────────────────────────────────────────────────────────────
    items = []
    for p in parishioners:
        items.append({
            "id": str(p.id),
            "old_church_id": p.old_church_id,
            "new_church_id": p.new_church_id,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "other_names": p.other_names,
            "gender": p.gender.value if p.gender else None,
            "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            "mobile_number": p.mobile_number,
            "whatsapp_number": p.whatsapp_number,
            "nationality": p.nationality,
            "hometown": p.hometown,
            "baptismal_name": p.baptismal_name,
            "verification_status": p.verification_status.value if p.verification_status else None,
            "membership_status": p.membership_status.value if p.membership_status else None,
            "church_unit_name": p.church_unit.name if p.church_unit else None,
            "church_community_name": p.church_community.name if p.church_community else None,
            "data_issues": _compute_issues(p, society_member_ids),
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })

    return APIResponse(
        message="Data quality report retrieved",
        data={
            "summary": summary,
            "total_with_any_issue": total_with_any_issue,
            "total_filtered": total_filtered,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_filtered + page_size - 1) // page_size if total_filtered else 0,
            "parishioners": items,
        },
    )
