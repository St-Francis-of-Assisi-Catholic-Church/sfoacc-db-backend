from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class PlaceOfWorshipBase(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    mass_schedule: Optional[str] = None

class PlaceOfWorshipCreate(PlaceOfWorshipBase):
    pass

class PlaceOfWorshipUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    mass_schedule: Optional[str] = None

class PlaceOfWorshipRead(PlaceOfWorshipBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True