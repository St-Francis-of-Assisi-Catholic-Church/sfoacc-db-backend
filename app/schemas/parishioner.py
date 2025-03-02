from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Any, Optional, List
from enum import Enum
from app.models.parishioner import MembershipStatus, SacramentType, Gender, ParentalStatus, MaritalStatus, VerificationStatus 

# Base Schemas
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



class ChildUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
class ParentInfo(BaseModel):
    name: Optional[str] = None
    status: Optional[ParentalStatus] = None

class SpouseInfo(BaseModel):
    name: Optional[str] = None
    status: Optional[ParentalStatus] = None
    phone: Optional[str] = None

class ChildInfo(BaseModel):
    name: Optional[str] = None

class FamilyInfoBatch(BaseModel):
    spouse: Optional[SpouseInfo] = None
    children: Optional[List[ChildInfo]] = None
    father: Optional[ParentInfo] = None
    mother: Optional[ParentInfo] = None

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
# Parishioner Schemas
class ParishionerBase(BaseModel):
    old_church_id: Optional[str] = None
    new_church_id: Optional[str] = None
    first_name: str = Field(..., min_length=2, max_length=50)
    other_names: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=50)
    maiden_name: Optional[str] = Field(None, max_length=50)
    gender: Gender
    date_of_birth: date
    place_of_birth: Optional[str] = None
    hometown: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    marital_status: Optional[MaritalStatus] = MaritalStatus.SINGLE
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email_address: Optional[EmailStr] = None
    place_of_worship: Optional[str] = None
    current_residence: Optional[str] = None

    membership_status: Optional[MembershipStatus] = MembershipStatus.ACTIVE  # Default value
    verification_status: Optional[VerificationStatus] = VerificationStatus.UNVERIFIED 

class ParishionerCreate(ParishionerBase):
    pass

class ParishionerUpdate(ParishionerBase):
   pass

class ParishionerPartialUpdate(BaseModel):
    old_church_id: Optional[str] = None
    new_church_id: Optional[str] = None
    first_name: Optional[str] = None
    other_names: Optional[str] = None
    last_name: Optional[str] = None
    maiden_name: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    place_of_birth: Optional[str] = None
    hometown: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email_address: Optional[EmailStr] = None
    place_of_worship: Optional[str] = None
    current_residence: Optional[str] = None

    membership_status: Optional[MembershipStatus] = MembershipStatus.ACTIVE 
    verification_status: Optional[VerificationStatus] = VerificationStatus.UNVERIFIED 


class ParishionerRead(ParishionerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class ParishionerDetailedRead(ParishionerRead):
    family_info: Optional[FamilyInfoRead] = None
    occupation: Optional[OccupationRead] = None
    emergency_contacts: List[EmergencyContactRead] = []
    medical_conditions: List[MedicalConditionRead] = []
    sacraments: List[SacramentRead] = []
    skills: List[SkillRead] = []
    # languages: List[]

    class Config:
        from_attributes = True

# Response Models
class APIResponse(BaseModel):
    message: str
    data: Any | None