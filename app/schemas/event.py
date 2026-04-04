from datetime import date, datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.church_unit_admin import EventMessageType, RecurrenceFrequency


# ── Event Messages ────────────────────────────────────────────────────────────

class EventMessageCreate(BaseModel):
    message_type: EventMessageType = EventMessageType.NOTE
    title: Optional[str] = None
    content: str
    scheduled_at: Optional[datetime] = None


class EventMessageUpdate(BaseModel):
    message_type: Optional[EventMessageType] = None
    title: Optional[str] = None
    content: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    is_sent: Optional[bool] = None


class EventMessageRead(BaseModel):
    id: int
    event_id: int
    message_type: EventMessageType
    title: Optional[str] = None
    content: str
    scheduled_at: Optional[datetime] = None
    is_sent: bool
    created_by_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Events ────────────────────────────────────────────────────────────────────

class RecurrenceConfig(BaseModel):
    """
    Recurrence settings for a recurring event.

    frequency:            daily | weekly | monthly | yearly
    day_of_week:          0–6 (Sun=0 … Sat=6). Required when frequency=weekly.
    recurrence_end_date:  date the series stops naturally (leave null for open-ended).

    Example — every Thursday:
        {"frequency": "weekly", "day_of_week": 4}
    """
    frequency: RecurrenceFrequency
    day_of_week: Optional[int] = None          # 0-6; required for weekly
    recurrence_end_date: Optional[date] = None

    @field_validator("day_of_week")
    @classmethod
    def validate_day(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0 <= v <= 6):
            raise ValueError("day_of_week must be 0 (Sunday) through 6 (Saturday)")
        return v


class ChurchEventCreate(BaseModel):
    church_unit_id: int
    name: str
    description: Optional[str] = None
    event_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    is_public: bool = True
    recurrence: Optional[RecurrenceConfig] = None   # omit for one-time events


class ChurchEventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    is_public: Optional[bool] = None
    recurrence: Optional[RecurrenceConfig] = None   # set to null to remove recurrence


class ChurchEventRead(BaseModel):
    id: int
    church_unit_id: int
    church_unit_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    event_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    is_public: bool
    is_recurring: bool
    recurrence_frequency: Optional[RecurrenceFrequency] = None
    recurrence_day_of_week: Optional[int] = None
    recurrence_end_date: Optional[date] = None
    terminated_at: Optional[datetime] = None
    is_active: bool  # computed: not terminated and not past end date
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChurchEventDetailRead(ChurchEventRead):
    messages: List[EventMessageRead] = []
