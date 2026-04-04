import logging
from datetime import date
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep, CurrentUser, require_permission, is_super_admin
from app.models.parish import ChurchUnit, ChurchUnitType, MassSchedule
from app.models.church_unit_admin import ChurchUnitLeadership, ChurchEvent
from app.models.society import Society
from app.models.church_community import ChurchCommunity
from app.schemas.parish import (
    ChurchUnitCreate, ChurchUnitUpdate, ChurchUnitRead, ChurchUnitWithSchedules,
    OutstationCreate, OutstationUpdate, OutstationRead, OutstationDetail,
    ParishDetail,
    MassScheduleCreate, MassScheduleUpdate, MassScheduleRead,
)
from app.schemas.church_unit_admin import (
    LeadershipCreate, LeadershipUpdate, LeadershipRead,
    ChurchEventCreate, ChurchEventUpdate, ChurchEventRead,
)
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────

def _get_unit_or_404(session, unit_id: int) -> ChurchUnit:
    unit = session.query(ChurchUnit).filter(ChurchUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Church unit not found")
    return unit


def _can_manage_schedules(current_user, unit_id=None) -> bool:
    perms = {p.code for p in current_user.role_ref.permissions} if current_user.role_ref else set()
    if "admin:all" in perms or "admin:outstations" in perms or "admin:parish" in perms:
        return True
    if unit_id and "admin:outstation" in perms:
        member_unit_ids = {m.church_unit_id for m in current_user.unit_memberships}
        if unit_id in member_unit_ids:
            return True
    return False


def _can_manage_unit(current_user, unit_id: int) -> bool:
    perms = {p.code for p in current_user.role_ref.permissions} if current_user.role_ref else set()
    can_manage_all = (
        "admin:all" in perms
        or "admin:parish" in perms
        or "admin:outstations" in perms
    )
    if can_manage_all:
        return True
    if "admin:outstation" in perms:
        member_unit_ids = {m.church_unit_id for m in current_user.unit_memberships}
        return unit_id in member_unit_ids
    return False


# ── Parish (primary unit) ───────────────────────────────────────

def _build_outstation_detail(session, unit: ChurchUnit) -> dict:
    """Build the full detail dict for an outstation."""
    schedules = session.query(MassSchedule).filter(MassSchedule.church_unit_id == unit.id).all()
    societies = session.query(Society).filter(Society.church_unit_id == unit.id).all()
    communities = session.query(ChurchCommunity).filter(ChurchCommunity.church_unit_id == unit.id).all()
    return {
        **OutstationDetail.model_validate(unit).model_dump(),
        "mass_schedules": [MassScheduleRead.model_validate(s) for s in schedules],
        "societies": societies,
        "communities": communities,
    }


@router.get("", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def get_parish(session: SessionDep, current_user: CurrentUser) -> Any:
    """Return the primary parish with outstations (each with schedules, societies, communities)."""
    parish = (
        session.query(ChurchUnit)
        .filter(ChurchUnit.type == ChurchUnitType.PARISH)
        .first()
    )
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")

    outstations = (
        session.query(ChurchUnit)
        .filter(ChurchUnit.type == ChurchUnitType.OUTSTATION, ChurchUnit.parent_id == parish.id)
        .all()
    )
    parish_schedules = session.query(MassSchedule).filter(MassSchedule.church_unit_id == parish.id).all()
    parish_societies = session.query(Society).filter(Society.church_unit_id == parish.id).all()
    parish_communities = session.query(ChurchCommunity).filter(ChurchCommunity.church_unit_id == parish.id).all()

    data = {
        **ParishDetail.model_validate(parish).model_dump(),
        "mass_schedules": [MassScheduleRead.model_validate(s) for s in parish_schedules],
        "societies": parish_societies,
        "communities": parish_communities,
        "outstations": [_build_outstation_detail(session, o) for o in outstations],
    }

    return APIResponse(message="Parish retrieved", data=ParishDetail.model_validate(data))


@router.put("", response_model=APIResponse, dependencies=[require_permission("admin:parish")])
async def update_parish(*, session: SessionDep, current_user: CurrentUser, data: ChurchUnitUpdate) -> Any:
    """Update the primary parish."""
    parish = (
        session.query(ChurchUnit)
        .filter(ChurchUnit.type == ChurchUnitType.PARISH)
        .first()
    )
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(parish, field, value)
    session.commit()
    session.refresh(parish)
    return APIResponse(message="Parish updated", data=ChurchUnitRead.model_validate(parish))


# ── Parish mass schedules ───────────────────────────────────────

@router.get("/mass-schedules", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_parish_mass_schedules(session: SessionDep, current_user: CurrentUser) -> Any:
    """List mass schedules for the primary parish."""
    parish = (
        session.query(ChurchUnit)
        .filter(ChurchUnit.type == ChurchUnitType.PARISH)
        .first()
    )
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    schedules = (
        session.query(MassSchedule)
        .filter(MassSchedule.church_unit_id == parish.id)
        .all()
    )
    return APIResponse(
        message="Mass schedules retrieved",
        data=[MassScheduleRead.model_validate(s) for s in schedules],
    )


@router.post("/mass-schedules", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_parish_mass_schedule(
    *, session: SessionDep, current_user: CurrentUser, data: MassScheduleCreate
) -> Any:
    parish = (
        session.query(ChurchUnit)
        .filter(ChurchUnit.type == ChurchUnitType.PARISH)
        .first()
    )
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    if not _can_manage_schedules(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    schedule = MassSchedule(**data.model_dump(), church_unit_id=parish.id)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return APIResponse(message="Mass schedule created", data=MassScheduleRead.model_validate(schedule))


@router.put("/mass-schedules/{schedule_id}", response_model=APIResponse)
async def update_parish_mass_schedule(
    schedule_id: int, *, session: SessionDep, current_user: CurrentUser, data: MassScheduleUpdate
) -> Any:
    parish = (
        session.query(ChurchUnit)
        .filter(ChurchUnit.type == ChurchUnitType.PARISH)
        .first()
    )
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    schedule = session.query(MassSchedule).filter(
        MassSchedule.id == schedule_id,
        MassSchedule.church_unit_id == parish.id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not _can_manage_schedules(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    session.commit()
    session.refresh(schedule)
    return APIResponse(message="Schedule updated", data=MassScheduleRead.model_validate(schedule))


@router.delete("/mass-schedules/{schedule_id}", response_model=APIResponse)
async def delete_parish_mass_schedule(
    schedule_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    parish = (
        session.query(ChurchUnit)
        .filter(ChurchUnit.type == ChurchUnitType.PARISH)
        .first()
    )
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    schedule = session.query(MassSchedule).filter(
        MassSchedule.id == schedule_id,
        MassSchedule.church_unit_id == parish.id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not _can_manage_schedules(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(schedule)
    session.commit()
    return APIResponse(message="Schedule deleted")


# ── Outstations (backward-compat) ──────────────────────────────

@router.get("/outstations", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_outstations(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List all OUTSTATION-type church units."""
    query = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.OUTSTATION)
    total = query.count()
    outstations = query.offset(skip).limit(limit).all()
    return APIResponse(
        message="Outstations retrieved",
        data={
            "total": total,
            "items": [OutstationRead.model_validate(o) for o in outstations],
            "skip": skip,
            "limit": limit,
        },
    )


@router.post(
    "/outstations",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("admin:outstations")],
)
async def create_outstation(
    *, session: SessionDep, current_user: CurrentUser, data: OutstationCreate
) -> Any:
    """Create a new outstation. Type is forced to OUTSTATION."""
    if data.parent_id is not None:
        parent = session.query(ChurchUnit).filter(ChurchUnit.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent church unit not found")
    # Ensure type is OUTSTATION regardless of what was submitted
    payload = data.model_dump()
    payload["type"] = ChurchUnitType.OUTSTATION
    unit = ChurchUnit(**payload)
    session.add(unit)
    try:
        session.commit()
        session.refresh(unit)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Outstation already exists")
    return APIResponse(message="Outstation created", data=OutstationRead.model_validate(unit))


@router.get("/outstations/{outstation_id}", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def get_outstation(outstation_id: int, session: SessionDep, current_user: CurrentUser) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id,
        ChurchUnit.type == ChurchUnitType.OUTSTATION,
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    return APIResponse(
        message="Outstation retrieved",
        data=OutstationDetail.model_validate(_build_outstation_detail(session, unit)),
    )


@router.put("/outstations/{outstation_id}", response_model=APIResponse)
async def update_outstation(
    outstation_id: int,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    data: OutstationUpdate,
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id,
        ChurchUnit.type == ChurchUnitType.OUTSTATION,
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    if not _can_manage_unit(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)
    session.commit()
    session.refresh(unit)
    return APIResponse(message="Outstation updated", data=OutstationRead.model_validate(unit))


@router.delete(
    "/outstations/{outstation_id}",
    response_model=APIResponse,
    dependencies=[require_permission("admin:outstations")],
)
async def delete_outstation(
    outstation_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id,
        ChurchUnit.type == ChurchUnitType.OUTSTATION,
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    session.delete(unit)
    session.commit()
    return APIResponse(message="Outstation deleted")


# ── Outstation mass schedules ───────────────────────────────────

@router.get("/outstations/{outstation_id}/mass-schedules", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_outstation_mass_schedules(
    outstation_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id,
        ChurchUnit.type == ChurchUnitType.OUTSTATION,
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    schedules = (
        session.query(MassSchedule)
        .filter(MassSchedule.church_unit_id == outstation_id)
        .all()
    )
    return APIResponse(
        message="Mass schedules retrieved",
        data=[MassScheduleRead.model_validate(s) for s in schedules],
    )


@router.post(
    "/outstations/{outstation_id}/mass-schedules",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_outstation_mass_schedule(
    outstation_id: int,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    data: MassScheduleCreate,
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id,
        ChurchUnit.type == ChurchUnitType.OUTSTATION,
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    if not _can_manage_schedules(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    schedule = MassSchedule(**data.model_dump(), church_unit_id=outstation_id)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return APIResponse(message="Mass schedule created", data=MassScheduleRead.model_validate(schedule))


@router.put("/outstations/{outstation_id}/mass-schedules/{schedule_id}", response_model=APIResponse)
async def update_outstation_mass_schedule(
    outstation_id: int,
    schedule_id: int,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    data: MassScheduleUpdate,
) -> Any:
    schedule = session.query(MassSchedule).filter(
        MassSchedule.id == schedule_id,
        MassSchedule.church_unit_id == outstation_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not _can_manage_schedules(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    session.commit()
    session.refresh(schedule)
    return APIResponse(message="Schedule updated", data=MassScheduleRead.model_validate(schedule))


@router.delete("/outstations/{outstation_id}/mass-schedules/{schedule_id}", response_model=APIResponse)
async def delete_outstation_mass_schedule(
    outstation_id: int,
    schedule_id: int,
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    schedule = session.query(MassSchedule).filter(
        MassSchedule.id == schedule_id,
        MassSchedule.church_unit_id == outstation_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not _can_manage_schedules(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(schedule)
    session.commit()
    return APIResponse(message="Schedule deleted")


# ── General Church Units CRUD (all types) ──────────────────────
# Available at /parish/units — full CRUD for all church unit types.

@router.get("/units", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_church_units(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """List all church units (parishes and outstations)."""
    query = session.query(ChurchUnit)
    total = query.count()
    units = query.offset(skip).limit(limit).all()
    return APIResponse(
        message="Church units retrieved",
        data={
            "total": total,
            "items": [ChurchUnitRead.model_validate(u) for u in units],
            "skip": skip,
            "limit": limit,
        },
    )


@router.post(
    "/units",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("admin:parish")],
)
async def create_church_unit(
    *, session: SessionDep, current_user: CurrentUser, data: ChurchUnitCreate
) -> Any:
    if data.parent_id is not None:
        if not session.query(ChurchUnit).filter(ChurchUnit.id == data.parent_id).first():
            raise HTTPException(status_code=404, detail="Parent church unit not found")
    unit = ChurchUnit(**data.model_dump())
    session.add(unit)
    try:
        session.commit()
        session.refresh(unit)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Church unit already exists")
    return APIResponse(message="Church unit created", data=ChurchUnitRead.model_validate(unit))


@router.get("/units/{unit_id}", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def get_church_unit(unit_id: int, session: SessionDep, current_user: CurrentUser) -> Any:
    unit = _get_unit_or_404(session, unit_id)
    if unit.type == ChurchUnitType.PARISH:
        return await get_parish(session, current_user)
    return APIResponse(
        message="Church unit retrieved",
        data=OutstationDetail.model_validate(_build_outstation_detail(session, unit)),
    )


@router.put("/units/{unit_id}", response_model=APIResponse)
async def update_church_unit(
    unit_id: int,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    data: ChurchUnitUpdate,
) -> Any:
    unit = _get_unit_or_404(session, unit_id)
    if not _can_manage_unit(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)
    session.commit()
    session.refresh(unit)
    return APIResponse(message="Church unit updated", data=ChurchUnitRead.model_validate(unit))


@router.delete(
    "/units/{unit_id}",
    response_model=APIResponse,
    dependencies=[require_permission("admin:parish")],
)
async def delete_church_unit(unit_id: int, *, session: SessionDep, current_user: CurrentUser) -> Any:
    unit = _get_unit_or_404(session, unit_id)
    session.delete(unit)
    session.commit()
    return APIResponse(message="Church unit deleted")


# ── General mass schedules by unit ID ──────────────────────────

@router.get("/units/{unit_id}/mass-schedules", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_unit_mass_schedules(
    unit_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    _get_unit_or_404(session, unit_id)
    schedules = (
        session.query(MassSchedule)
        .filter(MassSchedule.church_unit_id == unit_id)
        .all()
    )
    return APIResponse(
        message="Mass schedules retrieved",
        data=[MassScheduleRead.model_validate(s) for s in schedules],
    )


@router.post(
    "/units/{unit_id}/mass-schedules",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit_mass_schedule(
    unit_id: int, *, session: SessionDep, current_user: CurrentUser, data: MassScheduleCreate
) -> Any:
    _get_unit_or_404(session, unit_id)
    if not _can_manage_schedules(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    schedule = MassSchedule(**data.model_dump(), church_unit_id=unit_id)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return APIResponse(message="Mass schedule created", data=MassScheduleRead.model_validate(schedule))


@router.put("/units/{unit_id}/mass-schedules/{schedule_id}", response_model=APIResponse)
async def update_unit_mass_schedule(
    unit_id: int,
    schedule_id: int,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    data: MassScheduleUpdate,
) -> Any:
    schedule = session.query(MassSchedule).filter(
        MassSchedule.id == schedule_id,
        MassSchedule.church_unit_id == unit_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not _can_manage_schedules(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    session.commit()
    session.refresh(schedule)
    return APIResponse(message="Schedule updated", data=MassScheduleRead.model_validate(schedule))


@router.delete("/units/{unit_id}/mass-schedules/{schedule_id}", response_model=APIResponse)
async def delete_unit_mass_schedule(
    unit_id: int,
    schedule_id: int,
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    schedule = session.query(MassSchedule).filter(
        MassSchedule.id == schedule_id,
        MassSchedule.church_unit_id == unit_id,
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not _can_manage_schedules(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(schedule)
    session.commit()
    return APIResponse(message="Schedule deleted")


# ── Leadership (per church unit) ────────────────────────────────

def _list_leadership(session, unit_id: int, current_only: bool) -> list:
    q = session.query(ChurchUnitLeadership).filter(ChurchUnitLeadership.church_unit_id == unit_id)
    if current_only:
        q = q.filter(ChurchUnitLeadership.is_current == True)
    return q.order_by(ChurchUnitLeadership.role).all()


@router.get("/units/{unit_id}/leadership", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_unit_leadership(
    unit_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    current_only: bool = Query(True, description="Return only current leaders"),
) -> Any:
    """List leadership/executives for a church unit."""
    _get_unit_or_404(session, unit_id)
    records = _list_leadership(session, unit_id, current_only)
    return APIResponse(
        message="Leadership retrieved",
        data=[LeadershipRead.model_validate(r) for r in records],
    )


@router.post("/units/{unit_id}/leadership", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_unit_leadership(
    unit_id: int, *, session: SessionDep, current_user: CurrentUser, data: LeadershipCreate,
) -> Any:
    """Add a leadership/executive record to a church unit."""
    _get_unit_or_404(session, unit_id)
    if not _can_manage_unit(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    record = ChurchUnitLeadership(**data.model_dump(), church_unit_id=unit_id)
    session.add(record)
    session.commit()
    session.refresh(record)
    return APIResponse(message="Leadership record created", data=LeadershipRead.model_validate(record))


@router.get("/units/{unit_id}/leadership/{leadership_id}", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def get_unit_leadership(
    unit_id: int, leadership_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    record = session.query(ChurchUnitLeadership).filter(
        ChurchUnitLeadership.id == leadership_id,
        ChurchUnitLeadership.church_unit_id == unit_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    return APIResponse(message="Leadership record retrieved", data=LeadershipRead.model_validate(record))


@router.put("/units/{unit_id}/leadership/{leadership_id}", response_model=APIResponse)
async def update_unit_leadership(
    unit_id: int, leadership_id: int,
    *, session: SessionDep, current_user: CurrentUser, data: LeadershipUpdate,
) -> Any:
    record = session.query(ChurchUnitLeadership).filter(
        ChurchUnitLeadership.id == leadership_id,
        ChurchUnitLeadership.church_unit_id == unit_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    if not _can_manage_unit(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    session.commit()
    session.refresh(record)
    return APIResponse(message="Leadership record updated", data=LeadershipRead.model_validate(record))


@router.delete("/units/{unit_id}/leadership/{leadership_id}", response_model=APIResponse)
async def delete_unit_leadership(
    unit_id: int, leadership_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    record = session.query(ChurchUnitLeadership).filter(
        ChurchUnitLeadership.id == leadership_id,
        ChurchUnitLeadership.church_unit_id == unit_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    if not _can_manage_unit(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(record)
    session.commit()
    return APIResponse(message="Leadership record deleted")


# ── Leadership convenience routes (primary parish & outstations) ─

@router.get("/leadership", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_parish_leadership(
    session: SessionDep,
    current_user: CurrentUser,
    current_only: bool = Query(True),
) -> Any:
    """List leadership for the primary parish."""
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    records = _list_leadership(session, parish.id, current_only)
    return APIResponse(
        message="Leadership retrieved",
        data=[LeadershipRead.model_validate(r) for r in records],
    )


@router.post("/leadership", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_parish_leadership(
    *, session: SessionDep, current_user: CurrentUser, data: LeadershipCreate
) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    if not _can_manage_unit(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    record = ChurchUnitLeadership(**data.model_dump(), church_unit_id=parish.id)
    session.add(record)
    session.commit()
    session.refresh(record)
    return APIResponse(message="Leadership record created", data=LeadershipRead.model_validate(record))


@router.put("/leadership/{leadership_id}", response_model=APIResponse)
async def update_parish_leadership(
    leadership_id: int, *, session: SessionDep, current_user: CurrentUser, data: LeadershipUpdate
) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    record = session.query(ChurchUnitLeadership).filter(
        ChurchUnitLeadership.id == leadership_id,
        ChurchUnitLeadership.church_unit_id == parish.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    if not _can_manage_unit(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    session.commit()
    session.refresh(record)
    return APIResponse(message="Leadership record updated", data=LeadershipRead.model_validate(record))


@router.delete("/leadership/{leadership_id}", response_model=APIResponse)
async def delete_parish_leadership(
    leadership_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    record = session.query(ChurchUnitLeadership).filter(
        ChurchUnitLeadership.id == leadership_id,
        ChurchUnitLeadership.church_unit_id == parish.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    if not _can_manage_unit(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(record)
    session.commit()
    return APIResponse(message="Leadership record deleted")


@router.get("/outstations/{outstation_id}/leadership", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_outstation_leadership(
    outstation_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    current_only: bool = Query(True),
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id, ChurchUnit.type == ChurchUnitType.OUTSTATION
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    records = _list_leadership(session, outstation_id, current_only)
    return APIResponse(
        message="Leadership retrieved",
        data=[LeadershipRead.model_validate(r) for r in records],
    )


@router.post(
    "/outstations/{outstation_id}/leadership",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_outstation_leadership(
    outstation_id: int, *, session: SessionDep, current_user: CurrentUser, data: LeadershipCreate
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id, ChurchUnit.type == ChurchUnitType.OUTSTATION
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    if not _can_manage_unit(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    record = ChurchUnitLeadership(**data.model_dump(), church_unit_id=outstation_id)
    session.add(record)
    session.commit()
    session.refresh(record)
    return APIResponse(message="Leadership record created", data=LeadershipRead.model_validate(record))


@router.put("/outstations/{outstation_id}/leadership/{leadership_id}", response_model=APIResponse)
async def update_outstation_leadership(
    outstation_id: int, leadership_id: int,
    *, session: SessionDep, current_user: CurrentUser, data: LeadershipUpdate,
) -> Any:
    record = session.query(ChurchUnitLeadership).filter(
        ChurchUnitLeadership.id == leadership_id,
        ChurchUnitLeadership.church_unit_id == outstation_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    if not _can_manage_unit(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    session.commit()
    session.refresh(record)
    return APIResponse(message="Leadership record updated", data=LeadershipRead.model_validate(record))


@router.delete("/outstations/{outstation_id}/leadership/{leadership_id}", response_model=APIResponse)
async def delete_outstation_leadership(
    outstation_id: int, leadership_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    record = session.query(ChurchUnitLeadership).filter(
        ChurchUnitLeadership.id == leadership_id,
        ChurchUnitLeadership.church_unit_id == outstation_id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    if not _can_manage_unit(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(record)
    session.commit()
    return APIResponse(message="Leadership record deleted")


# ── Church Events (per church unit) ────────────────────────────

def _list_events(
    session, unit_id: int, upcoming_only: bool, from_date: Optional[date], to_date: Optional[date]
) -> list:
    q = session.query(ChurchEvent).filter(ChurchEvent.church_unit_id == unit_id)
    if upcoming_only:
        q = q.filter(ChurchEvent.event_date >= date.today())
    if from_date:
        q = q.filter(ChurchEvent.event_date >= from_date)
    if to_date:
        q = q.filter(ChurchEvent.event_date <= to_date)
    return q.order_by(ChurchEvent.event_date).all()


@router.get("/units/{unit_id}/events", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_unit_events(
    unit_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    upcoming_only: bool = Query(False),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> Any:
    """List events for a church unit."""
    _get_unit_or_404(session, unit_id)
    events = _list_events(session, unit_id, upcoming_only, from_date, to_date)
    return APIResponse(
        message="Events retrieved",
        data=[ChurchEventRead.model_validate(e) for e in events],
    )


@router.post("/units/{unit_id}/events", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_unit_event(
    unit_id: int, *, session: SessionDep, current_user: CurrentUser, data: ChurchEventCreate
) -> Any:
    _get_unit_or_404(session, unit_id)
    if not _can_manage_unit(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    event = ChurchEvent(**data.model_dump(), church_unit_id=unit_id)
    session.add(event)
    session.commit()
    session.refresh(event)
    return APIResponse(message="Event created", data=ChurchEventRead.model_validate(event))


@router.get("/units/{unit_id}/events/{event_id}", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def get_unit_event(
    unit_id: int, event_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    event = session.query(ChurchEvent).filter(
        ChurchEvent.id == event_id, ChurchEvent.church_unit_id == unit_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return APIResponse(message="Event retrieved", data=ChurchEventRead.model_validate(event))


@router.put("/units/{unit_id}/events/{event_id}", response_model=APIResponse)
async def update_unit_event(
    unit_id: int, event_id: int,
    *, session: SessionDep, current_user: CurrentUser, data: ChurchEventUpdate,
) -> Any:
    event = session.query(ChurchEvent).filter(
        ChurchEvent.id == event_id, ChurchEvent.church_unit_id == unit_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_unit(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    session.commit()
    session.refresh(event)
    return APIResponse(message="Event updated", data=ChurchEventRead.model_validate(event))


@router.delete("/units/{unit_id}/events/{event_id}", response_model=APIResponse)
async def delete_unit_event(
    unit_id: int, event_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    event = session.query(ChurchEvent).filter(
        ChurchEvent.id == event_id, ChurchEvent.church_unit_id == unit_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_unit(current_user, unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(event)
    session.commit()
    return APIResponse(message="Event deleted")


# ── Events convenience routes (primary parish & outstations) ────

@router.get("/events", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_parish_events(
    session: SessionDep,
    current_user: CurrentUser,
    upcoming_only: bool = Query(False),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> Any:
    """List events for the primary parish."""
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    events = _list_events(session, parish.id, upcoming_only, from_date, to_date)
    return APIResponse(
        message="Events retrieved",
        data=[ChurchEventRead.model_validate(e) for e in events],
    )


@router.post("/events", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_parish_event(
    *, session: SessionDep, current_user: CurrentUser, data: ChurchEventCreate
) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    if not _can_manage_unit(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    event = ChurchEvent(**data.model_dump(), church_unit_id=parish.id)
    session.add(event)
    session.commit()
    session.refresh(event)
    return APIResponse(message="Event created", data=ChurchEventRead.model_validate(event))


@router.put("/events/{event_id}", response_model=APIResponse)
async def update_parish_event(
    event_id: int, *, session: SessionDep, current_user: CurrentUser, data: ChurchEventUpdate
) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    event = session.query(ChurchEvent).filter(
        ChurchEvent.id == event_id, ChurchEvent.church_unit_id == parish.id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_unit(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    session.commit()
    session.refresh(event)
    return APIResponse(message="Event updated", data=ChurchEventRead.model_validate(event))


@router.delete("/events/{event_id}", response_model=APIResponse)
async def delete_parish_event(
    event_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    event = session.query(ChurchEvent).filter(
        ChurchEvent.id == event_id, ChurchEvent.church_unit_id == parish.id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_unit(current_user, parish.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(event)
    session.commit()
    return APIResponse(message="Event deleted")


@router.get("/outstations/{outstation_id}/events", response_model=APIResponse, dependencies=[require_permission("church_unit:read")])
async def list_outstation_events(
    outstation_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    upcoming_only: bool = Query(False),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id, ChurchUnit.type == ChurchUnitType.OUTSTATION
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    events = _list_events(session, outstation_id, upcoming_only, from_date, to_date)
    return APIResponse(
        message="Events retrieved",
        data=[ChurchEventRead.model_validate(e) for e in events],
    )


@router.post(
    "/outstations/{outstation_id}/events",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_outstation_event(
    outstation_id: int, *, session: SessionDep, current_user: CurrentUser, data: ChurchEventCreate
) -> Any:
    unit = session.query(ChurchUnit).filter(
        ChurchUnit.id == outstation_id, ChurchUnit.type == ChurchUnitType.OUTSTATION
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Outstation not found")
    if not _can_manage_unit(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    event = ChurchEvent(**data.model_dump(), church_unit_id=outstation_id)
    session.add(event)
    session.commit()
    session.refresh(event)
    return APIResponse(message="Event created", data=ChurchEventRead.model_validate(event))


@router.put("/outstations/{outstation_id}/events/{event_id}", response_model=APIResponse)
async def update_outstation_event(
    outstation_id: int, event_id: int,
    *, session: SessionDep, current_user: CurrentUser, data: ChurchEventUpdate,
) -> Any:
    event = session.query(ChurchEvent).filter(
        ChurchEvent.id == event_id, ChurchEvent.church_unit_id == outstation_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_unit(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    session.commit()
    session.refresh(event)
    return APIResponse(message="Event updated", data=ChurchEventRead.model_validate(event))


@router.delete("/outstations/{outstation_id}/events/{event_id}", response_model=APIResponse)
async def delete_outstation_event(
    outstation_id: int, event_id: int, *, session: SessionDep, current_user: CurrentUser
) -> Any:
    event = session.query(ChurchEvent).filter(
        ChurchEvent.id == event_id, ChurchEvent.church_unit_id == outstation_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not _can_manage_unit(current_user, outstation_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    session.delete(event)
    session.commit()
    return APIResponse(message="Event deleted")
