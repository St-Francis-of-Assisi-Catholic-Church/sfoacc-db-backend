# Re-export everything so existing imports continue to work
from app.models.parishioner.core import (
    _now,
    parishioner_skills,
    parishioner_languages,
    ParishionerSacrament,
    Parishioner,
)
from app.models.parishioner.related import (
    Occupation,
    FamilyInfo,
    Child,
    EmergencyContact,
)
from app.models.parishioner.medical import (
    MedicalCondition,
    Skill,
)

# Re-export enums that callers import from this module
from app.models.common import (
    Gender,
    MaritalStatus,
    MembershipStatus,
    VerificationStatus,
    LifeStatus,
)

__all__ = [
    "_now",
    "parishioner_skills",
    "parishioner_languages",
    "ParishionerSacrament",
    "Parishioner",
    "Occupation",
    "FamilyInfo",
    "Child",
    "EmergencyContact",
    "MedicalCondition",
    "Skill",
    "Gender",
    "MaritalStatus",
    "MembershipStatus",
    "VerificationStatus",
    "LifeStatus",
]
