from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import date, datetime
from typing import Any, Optional, List, Union
from enum import Enum


from app.models.parishioner import MembershipStatus, Gender, LifeStatus, MaritalStatus, VerificationStatus
from app.models.sacrament import SacramentType
from app.schemas.sacrament import SacramentRead
from app.schemas.parish import ChurchUnitRead


class ChurchCommunityBase(BaseModel):
    name: str
    description: Optional[str] = None

class ChurchCommunityRead(ChurchCommunityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PlaceOfWorshipBase(BaseModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None

class PlaceOfWorshipRead(PlaceOfWorshipBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

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


# ------- Parishioner Sacrements -------------
# class ParSacramentBase(BaseModel):
#     type: SacramentType
#     date: datetime
#     place: str
#     minister: str
class ParSacramentBase(BaseModel):
    date_received: Optional[date] = None
    place: Optional[str] = None
    minister: Optional[str] = None
    notes: Optional[str] = None

class ParSacramentCreate(ParSacramentBase):
    sacrament_id: Union[int, SacramentType]
    
    # Add validators if needed
    # @validator('place', 'minister')
    # def not_empty(cls, v):
    #     if not v or not v.strip():
    #         raise ValueError('Cannot be empty')
    #     return v
    
class ParSacramentUpdate(BaseModel):
    sacrament_id: Optional[int] = None
    date_received: Optional[date] = None
    place: Optional[str] = None
    minister: Optional[str] = None
    notes: Optional[str] = None
    
    # @validator('place', 'minister')
    # def not_empty(cls, v):
    #     if v is not None and not v.strip():
    #         raise ValueError('Cannot be empty string')
    #     return v
    
    class Config:
        from_attributes = True
    
class ParSacramentRead(ParSacramentBase):
    id: int
    parishioner_id: UUID
    # sacrament_id: int
    sacrament: SacramentRead
    
    class Config:
        from_attributes = True



# -------- Societies --------
class ParSocietyBase (BaseModel):
    name: str
    description: Optional[str] = None
class ParSocietyRead(ParSocietyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    name: str
    description: Optional[str] = None

    date_joined: Optional[datetime] = None
    membership_status: Optional[str] = None

    class Config:
        from_attributes = True


# ------- Par Sklls ---
class SkillBase(BaseModel):
    name: str


# --------- Par Languages --------
class ParLanguageRead(BaseModel):
    assignment_date: datetime
    last_updated: datetime
    
    class Config:
        from_attributes = True


class LanguagesAssignRequest(BaseModel):
    language_ids: List[int]




# Create Schemas
class OccupationCreate(OccupationBase):
    pass

class ChildCreate(ChildBase):
    pass

class EmergencyContactCreate(EmergencyContactBase):
    pass

class MedicalConditionCreate(MedicalConditionBase):
    pass



class SkillCreate(SkillBase):
    pass

# Read Schemas
class OccupationRead(OccupationBase):
    id: int
    parishioner_id: UUID
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
    parishioner_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MedicalConditionRead(MedicalConditionBase):
    id: int
    parishioner_id: UUID
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
    status: Optional[LifeStatus] = None

class SpouseInfo(BaseModel):
    name: Optional[str] = None
    status: Optional[LifeStatus] = None
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
    father_status: Optional[LifeStatus] = None
    mother_name: Optional[str] = None
    mother_status: Optional[LifeStatus] = None
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
    father_status: Optional[LifeStatus] = None
    mother_name: Optional[str] = Field(None, min_length=2, max_length=100)
    mother_status: Optional[LifeStatus] = None
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
class SocietyMembershipCreate(BaseModel):
    society_id: int
    date_joined: Optional[date] = None


# Parishioner Schemas
class ParishionerBase(BaseModel):
    # Identity
    title: Optional[str] = Field(None, max_length=20)
    old_church_id: Optional[str] = None
    new_church_id: Optional[str] = None
    first_name: str = Field(..., min_length=2, max_length=50)
    other_names: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=50)
    maiden_name: Optional[str] = Field(None, max_length=50)
    baptismal_name: Optional[str] = Field(None, max_length=100)
    gender: Gender
    date_of_birth: Optional[date] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = Field(None, max_length=100)
    hometown: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    marital_status: Optional[MaritalStatus] = MaritalStatus.SINGLE

    # Contact
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email_address: Optional[EmailStr] = None
    current_residence: Optional[str] = None

    # Vital status
    is_deceased: Optional[bool] = False
    date_of_death: Optional[date] = None

    # Profile
    photo_url: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None

    membership_status: Optional[MembershipStatus] = MembershipStatus.ACTIVE
    verification_status: Optional[VerificationStatus] = VerificationStatus.UNVERIFIED


class ParishionerCreate(ParishionerBase):
    pass


class ParishionerFullCreate(ParishionerBase):
    """Full registration payload — core fields + all optional sub-resources."""
    church_unit_id: Optional[int] = None
    church_community_id: Optional[int] = None

    occupation: Optional[OccupationCreate] = None
    family_info: Optional[FamilyInfoBatch] = None
    emergency_contacts: Optional[List[EmergencyContactCreate]] = Field(None, max_length=3)
    medical_conditions: Optional[List[MedicalConditionCreate]] = Field(None, max_length=5)
    sacraments: Optional[List[ParSacramentCreate]] = None
    # Skills: provide name only; backend will find-or-create
    skills: Optional[List[str]] = None
    language_ids: Optional[List[int]] = None
    societies: Optional[List[SocietyMembershipCreate]] = None


class ParishionerUpdate(ParishionerBase):
    pass


class ParishionerPartialUpdate(BaseModel):
    title: Optional[str] = None
    old_church_id: Optional[str] = None
    new_church_id: Optional[str] = None
    first_name: Optional[str] = None
    other_names: Optional[str] = None
    last_name: Optional[str] = None
    maiden_name: Optional[str] = None
    baptismal_name: Optional[str] = None
    gender: Optional[Gender] = None
    date_of_birth: Optional[date] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    hometown: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None
    mobile_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email_address: Optional[EmailStr] = None
    church_unit_id: Optional[int] = None
    church_community_id: Optional[str] = None
    current_residence: Optional[str] = None
    is_deceased: Optional[bool] = None
    date_of_death: Optional[date] = None
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    membership_status: Optional[MembershipStatus] = None
    verification_status: Optional[VerificationStatus] = None


class ParishionerRead(ParishionerBase):
    id: UUID
    church_unit_name: Optional[str] = None
    church_community_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        instance = super().model_validate(obj, *args, **kwargs)
        if hasattr(obj, "church_unit") and obj.church_unit:
            instance.church_unit_name = obj.church_unit.name
        if hasattr(obj, "church_community") and obj.church_community:
            instance.church_community_name = obj.church_community.name
        return instance

    class Config:
        from_attributes = True

class ParishionerDetailedRead(ParishionerRead):
    family_info: Optional[FamilyInfoRead] = None
    occupation: Optional[OccupationRead] = None
    emergency_contacts: List[EmergencyContactRead] = []
    medical_conditions: List[MedicalConditionRead] = []
    sacraments: List[ParSacramentRead] = []
    skills: List[SkillRead] = []
    church_unit: Optional[ChurchUnitRead] = None
    church_community: Optional[ChurchCommunityRead] = None
    societies: List[ParSocietyRead] = []
    languages_spoken: List[Any] = []

    class Config:
        from_attributes = True

