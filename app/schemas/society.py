from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from datetime import date, time, datetime
from enum import Enum

from app.models.common import MembershipStatus
from app.models.society import MeetingFrequency, LeadershipRole

# Society Leadership Schemas
class SocietyLeadershipBase(BaseModel):
    role: LeadershipRole
    custom_role: Optional[str] = None
    elected_date: Optional[date] = None
    end_date: Optional[date] = None

class SocietyLeadershipCreate(SocietyLeadershipBase):
    parishioner_id: int

class SocietyLeadershipUpdate(BaseModel):
    role: Optional[LeadershipRole] = None
    custom_role: Optional[str] = None
    elected_date: Optional[date] = None
    end_date: Optional[date] = None
    parishioner_id: Optional[int] = None

class SocietyLeadershipInDB(SocietyLeadershipBase):
    id: int
    society_id: int
    parishioner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class SocietyLeadershipResponse(SocietyLeadershipBase):
    id: int
    parishioner_id: int
    parishioner_name: str = Field(..., description="First and last name of the parishioner")
    parishioner_church_id: Optional[str] = Field(None, description="Church ID of the parishioner")
    parishioner_contact: Optional[str] = Field(None, description="Mobile number of the parishioner")

    class Config:
        orm_mode = True

# Society Schemas
class SocietyBase(BaseModel):
    name: str
    description: Optional[str] = None
    date_inaugurated: Optional[date] = None
    meeting_frequency: MeetingFrequency
    meeting_day: Optional[str] = None
    meeting_time: Optional[time] = None
    meeting_venue: Optional[str] = None

class SocietyCreate(SocietyBase):
    pass

class SocietyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    date_inaugurated: Optional[date] = None
    meeting_frequency: Optional[MeetingFrequency] = None
    meeting_day: Optional[str] = None
    meeting_time: Optional[time] = None
    meeting_venue: Optional[str] = None

class SocietyInDB(SocietyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class SocietyResponse(SocietyBase):
    id: int
    members_count: int = Field(0, description="Number of members in the society")
    leadership: List[SocietyLeadershipResponse] = []

    class Config:
        orm_mode = True

class SocietyDetailResponse(SocietyResponse):
    members: List[dict] = Field([], description="List of members with basic info")

    class Config:
        orm_mode = True

# Member Management Schemas
class AddMembersRequest(BaseModel):
    parishioner_ids: List[int]

class RemoveMembersRequest(BaseModel):
    parishioner_ids: List[int]

class UpdateMemberStatusRequest(BaseModel):
    status: MembershipStatus  
