import enum

# enums
class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    DECEASED = "deceased"
    DISABLED = "disabled"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    PENDING = "pending"

class MaritalStatus(str, enum.Enum):
    SINGLE = "single"
    MARRIED = "married"
    WIDOWED = "widowed"
    DIVORCED = "divorced"

class LifeStatus(str, enum.Enum):
    ALIVE = "alive"
    DECEASED = "deceased"
    UNKNOWN = "unknown"