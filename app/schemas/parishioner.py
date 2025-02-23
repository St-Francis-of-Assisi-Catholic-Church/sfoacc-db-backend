from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Any, Optional, List
from enum import Enum
from app.models.parishioner import SacramentType, Gender, ParentalStatus, MaritalStatus 

# Base Schemas
class ContactInfoBase(BaseModel):
    mobile_number: str
    whatsapp_number: Optional[str] = None
    email_address: Optional[EmailStr] = None

class OccupationBase(BaseModel):
    role: str
    employer: str

class ChildBase(BaseModel):
    name: str

class EmergencyContactBase(BaseModel):
    name: str
    relationship: str
    primary_phone: str
    alternative_phone: Optional[str] = None

class MedicalConditionBase(BaseModel):
    condition: str
    notes: Optional[str] = None

class SacramentBase(BaseModel):
    type: SacramentType
    date: datetime
    place: str
    minister: str

class SkillBase(BaseModel):
    name: str

# Create Schemas
class ContactInfoCreate(ContactInfoBase):
    pass

class OccupationCreate(OccupationBase):
    pass

class ChildCreate(ChildBase):
    pass

class EmergencyContactCreate(EmergencyContactBase):
    pass

class MedicalConditionCreate(MedicalConditionBase):
    pass

class SacramentCreate(SacramentBase):
    pass

class SkillCreate(SkillBase):
    pass

# Read Schemas
class ContactInfoRead(ContactInfoBase):
    id: int
    parishioner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OccupationRead(OccupationBase):
    id: int
    parishioner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChildRead(ChildBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EmergencyContactRead(EmergencyContactBase):
    id: int
    parishioner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MedicalConditionRead(MedicalConditionBase):
    id: int
    parishioner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SacramentRead(SacramentBase):
    id: int
    parishioner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SkillRead(SkillBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Update Schemas
class ContactInfoUpdate(BaseModel):
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email_address: Optional[EmailStr] = None

class OccupationUpdate(BaseModel):
    role: Optional[str] = None
    employer: Optional[str] = None

class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    primary_phone: Optional[str] = None
    alternative_phone: Optional[str] = None

class MedicalConditionUpdate(BaseModel):
    condition: Optional[str] = None
    notes: Optional[str] = None

class SacramentUpdate(BaseModel):
    type: Optional[SacramentType] = None
    date: Optional[datetime] = None
    place: Optional[str] = None
    minister: Optional[str] = None

# Parishioner Schemas
class ParishionerBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    other_names: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=50)
    maiden_name: Optional[str] = Field(None, max_length=50)
    gender: Gender
    date_of_birth: datetime
    place_of_birth: str
    hometown: str
    region: str
    country: str
    marital_status: MaritalStatus

class ParishionerCreate(ParishionerBase):
    contact_info: Optional[ContactInfoCreate] = None
    occupation: Optional[OccupationCreate] = None
    emergency_contacts: List[EmergencyContactCreate] = []
    medical_conditions: List[MedicalConditionCreate] = []
    sacraments: List[SacramentCreate] = []
    skills: List[str] = []  # List of skill names

class ParishionerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    other_names: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    maiden_name: Optional[str] = Field(None, max_length=50)
    gender: Optional[Gender] = None
    date_of_birth: Optional[datetime] = None
    place_of_birth: Optional[str] = None
    hometown: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None

class ParishionerRead(ParishionerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    contact_info: Optional[ContactInfoRead] = None
    occupation: Optional[OccupationRead] = None
    emergency_contacts: List[EmergencyContactRead] = []
    medical_conditions: List[MedicalConditionRead] = []
    sacraments: List[SacramentRead] = []
    skills: List[SkillRead] = []

    class Config:
        from_attributes = True

class ChildUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

# Detailed Parishioner Response Schema
class FamilyInfoRead(BaseModel):
    id: int
    spouse_name: Optional[str] = None
    spouse_status: Optional[str] = None
    spouse_phone: Optional[str] = None
    father_name: Optional[str] = None
    father_status: Optional[ParentalStatus] = None
    mother_name: Optional[str] = None
    mother_status: Optional[ParentalStatus] = None
    children: List[ChildRead] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FamilyInfoUpdate(BaseModel):
    spouse_name: Optional[str] = Field(None, min_length=2, max_length=100)
    spouse_status: Optional[str] = Field(None, min_length=2, max_length=50)
    spouse_phone: Optional[str] = Field(None, min_length=2, max_length=20)
    father_name: Optional[str] = Field(None, min_length=2, max_length=100)
    father_status: Optional[ParentalStatus] = None
    mother_name: Optional[str] = Field(None, min_length=2, max_length=100)
    mother_status: Optional[ParentalStatus] = None
    children: Optional[List[ChildUpdate]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "spouse_name": "Jane Doe",
                "spouse_status": "alive",
                "spouse_phone": "+1234567890",
                "father_name": "John Smith",
                "father_status": "deceased",
                "mother_name": "Mary Smith",
                "mother_status": "alive",
                "children": [
                    {"name": "John Doe Jr."},
                    {"name": "Jane Doe Jr."}
                ]
            }
        }

class ParishionerDetailedRead(ParishionerRead):
    family_info: Optional[FamilyInfoRead] = None

    class Config:
        from_attributes = True

# Response Models
class APIResponse(BaseModel):
    message: str
    data: Any | None