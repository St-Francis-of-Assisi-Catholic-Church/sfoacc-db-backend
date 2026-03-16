from datetime import date, datetime, time
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.models.church_unit_admin import LeadershipRole


# ── Leadership ────────────────────────────────────────────────────────────────

class LeadershipCreate(BaseModel):
    role: LeadershipRole
    custom_role: Optional[str] = None
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_current: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class LeadershipUpdate(BaseModel):
    role: Optional[LeadershipRole] = None
    custom_role: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_current: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class LeadershipRead(BaseModel):
    id: int
    church_unit_id: int
    role: LeadershipRole
    custom_role: Optional[str] = None
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_current: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Events ────────────────────────────────────────────────────────────────────

class ChurchEventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    is_public: bool = True


class ChurchEventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    is_public: Optional[bool] = None


class ChurchEventRead(BaseModel):
    id: int
    church_unit_id: int
    name: str
    description: Optional[str] = None
    event_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
