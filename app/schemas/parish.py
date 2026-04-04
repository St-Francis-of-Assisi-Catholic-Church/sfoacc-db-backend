from datetime import date, datetime, time
from typing import List, Optional
from pydantic import BaseModel
from app.models.parish import ChurchUnitType, DayOfWeek, MassType


# ── Mass Schedules ─────────────────────────────────────────────

class MassScheduleCreate(BaseModel):
    day_of_week: DayOfWeek
    time: time
    mass_type: MassType = MassType.SUNDAY
    language: str = "English"
    description: Optional[str] = None


class MassScheduleUpdate(MassScheduleCreate):
    day_of_week: Optional[DayOfWeek] = None
    time: Optional[time] = None
    is_active: Optional[bool] = None


class MassScheduleRead(MassScheduleCreate):
    id: int
    church_unit_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Church Unit base ───────────────────────────────────────────

class ChurchUnitCreate(BaseModel):
    type: ChurchUnitType
    parent_id: Optional[int] = None
    name: str
    diocese: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    established_date: Optional[date] = None
    location_description: Optional[str] = None
    google_maps_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    priest_in_charge: Optional[str] = None
    priest_phone: Optional[str] = None


class ChurchUnitUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    diocese: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    established_date: Optional[date] = None
    location_description: Optional[str] = None
    google_maps_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    priest_in_charge: Optional[str] = None
    priest_phone: Optional[str] = None
    is_active: Optional[bool] = None


class ChurchUnitRead(ChurchUnitCreate):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Embedded summary types (used inside detailed responses) ────

class _SocietySummary(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    meeting_day: Optional[str] = None
    meeting_time: Optional[time] = None
    meeting_venue: Optional[str] = None
    model_config = {"from_attributes": True}


class _CommunitySummary(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Outstation detail (with schedules, societies, communities) ─

class OutstationDetail(ChurchUnitRead):
    """Full detail for a single outstation."""
    mass_schedules: List[MassScheduleRead] = []
    societies: List[_SocietySummary] = []
    communities: List[_CommunitySummary] = []


# ── Parish detail ──────────────────────────────────────────────

class ParishDetail(ChurchUnitRead):
    """Full detail for the parish, including all outstations."""
    mass_schedules: List[MassScheduleRead] = []
    societies: List[_SocietySummary] = []
    communities: List[_CommunitySummary] = []
    outstations: List[OutstationDetail] = []


# ── Simple with-schedules read (used by outstation list) ──────

class ChurchUnitWithSchedules(ChurchUnitRead):
    mass_schedules: List[MassScheduleRead] = []


# ── Type-specific create schemas ───────────────────────────────

class ParishCreate(ChurchUnitCreate):
    """Create schema for a parish unit. Type defaults to PARISH."""
    type: ChurchUnitType = ChurchUnitType.PARISH


class OutstationCreate(ChurchUnitCreate):
    """Create schema for an outstation. Type defaults to OUTSTATION."""
    type: ChurchUnitType = ChurchUnitType.OUTSTATION
    parent_id: Optional[int] = None


class StationCreate(ChurchUnitCreate):
    """Alias for OutstationCreate — type defaults to OUTSTATION."""
    type: ChurchUnitType = ChurchUnitType.OUTSTATION


# ── Backward-compat aliases ────────────────────────────────────
ParishUpdate = ChurchUnitUpdate
ParishRead = ChurchUnitRead
OutstationUpdate = ChurchUnitUpdate
OutstationRead = ChurchUnitRead
OutstationWithSchedules = ChurchUnitWithSchedules
StationUpdate = ChurchUnitUpdate
StationRead = ChurchUnitRead
StationWithSchedules = ChurchUnitWithSchedules

# Rebuild forward refs
OutstationDetail.model_rebuild()
ParishDetail.model_rebuild()
