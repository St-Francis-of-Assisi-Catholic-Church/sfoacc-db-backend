from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class ChurchCommunityBase(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None  # GPS coordinates

class ChurchCommunityCreate(ChurchCommunityBase):
    pass

class ChurchCommunityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

class ChurchCommunityRead(ChurchCommunityBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True