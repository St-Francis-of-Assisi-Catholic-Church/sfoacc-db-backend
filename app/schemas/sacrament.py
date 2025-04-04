from pydantic import BaseModel
from typing import Optional

class SacramentBase(BaseModel):
    name: str
    description: str
    once_only: bool

class SacramentCreate(SacramentBase):
    pass

class SacramentRead(SacramentBase):
    id: int
    
    class Config:
        from_attributes = True