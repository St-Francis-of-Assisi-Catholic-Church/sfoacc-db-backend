from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Enum, ForeignKey, Table, Text, func
from sqlalchemy.orm import relationship as db_relationship
import enum
from app.core.database import Base

# Enums
class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    DECEASED = "deceased"
    DISABLED = "disabled"

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    PENDING = "pending"


class MaritalStatus(str, enum.Enum):
    SINGLE = "single"
    MARRIED = "married"
    WIDOWED = "widowed"
    DIVORCED = "divorced"

class ParentalStatus(str, enum.Enum):
    ALIVE = "alive"
    DECEASED = "deceased"
    UNKNOWN = "unknown"

class ParSacramentType(str, enum.Enum):
    BAPTISM = "Baptism"
    FIRST_COMMUNION = "First Holy Communion"
    CONFIRMATION = "Confirmation"
    PENANCE = "Penance"
    ANOINTING = "Anointing of the Sick"
    HOLY_ORDERS = "Holy Orders"
    MATRIMONY = "Holy Matrimony"

# Association table for skills
parishioner_skills = Table(
    'par_parishioner_skills',
    Base.metadata,
    Column('parishioner_id', Integer, ForeignKey('parishioners.id')),
    Column('skill_id', Integer, ForeignKey('par_skills.id'))
)

# Association table for languages
parishioner_languages = Table(
    'par_parishioner_languages',
    Base.metadata,
    Column('parishioner_id', Integer, ForeignKey('parishioners.id')),
    Column('language_id', Integer, ForeignKey('par_languages.id'))
)

class Parishioner(Base):
    __tablename__ = "parishioners"

    id = Column(Integer, primary_key=True, index=True)
    old_church_id = Column(String, nullable=True)
    new_church_id = Column(String,nullable=True)

    # Status fields with defaults
    membership_status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.ACTIVE, server_default=MembershipStatus.ACTIVE.name)
    verification_status = Column(Enum(VerificationStatus), nullable=False, default=VerificationStatus.UNVERIFIED, server_default=VerificationStatus.UNVERIFIED.name)

    # Personal Info
    first_name = Column(String, nullable=False)
    other_names = Column(String, nullable=True)
    last_name = Column(String, nullable=False)
    maiden_name = Column(String, nullable=True)
    gender = Column(Enum(Gender), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    place_of_birth = Column(String, nullable=True)
    hometown = Column(String, nullable=True)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    marital_status = Column(Enum(MaritalStatus), nullable=False, default=MaritalStatus.SINGLE, server_default=MaritalStatus.SINGLE.name)
    mobile_number = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    email_address = Column(String, nullable=True)
    # new additions
    place_of_worship = Column(String, nullable=True)
    current_residence = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

    # Relationships
    occupation_rel = db_relationship("Occupation", back_populates="parishioner_ref", uselist=False)
    family_info_rel = db_relationship("FamilyInfo", back_populates="parishioner_ref", uselist=False)
    emergency_contacts_rel = db_relationship("EmergencyContact", back_populates="parishioner_ref")
    medical_conditions_rel = db_relationship("MedicalCondition", back_populates="parishioner_ref")
    par_sacraments_rel = db_relationship("ParSacrament", back_populates="parishioner_ref")
    skills_rel = db_relationship("Skill", secondary=parishioner_skills, back_populates="parishioners_ref")
    languages_rel = db_relationship("Language", secondary=parishioner_languages, back_populates="parishioners_ref")
    # societies
    societies = db_relationship("Society", secondary="par_society_members", back_populates="members")

class Occupation(Base):
    __tablename__ = "par_occupations"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"), unique=True)
    role = Column(String, nullable=False)
    employer = Column(String, nullable=False)

    parishioner_ref = db_relationship("Parishioner", back_populates="occupation_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class FamilyInfo(Base):
    __tablename__ = "par_family"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"), unique=True)
    
    # Spouse Information
    spouse_name = Column(String, nullable=True)
    spouse_status = Column(String, nullable=True)
    spouse_phone = Column(String, nullable=True)
    
    # Parent Information
    father_name = Column(String, nullable=True)
    father_status = Column(Enum(ParentalStatus), nullable=True)
    mother_name = Column(String, nullable=True)
    mother_status = Column(Enum(ParentalStatus), nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="family_info_rel")
    children_rel = db_relationship("Child", back_populates="family_ref")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Child(Base):
    __tablename__ = "par_children"

    id = Column(Integer, primary_key=True, index=True)
    family_info_id = Column(Integer, ForeignKey("par_family.id"))
    name = Column(String, nullable=False)

    family_ref = db_relationship("FamilyInfo", back_populates="children_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class EmergencyContact(Base):
    __tablename__ = "par_emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"))
    name = Column(String, nullable=False)
    relationship = Column(String, nullable=False)
    primary_phone = Column(String, nullable=False)
    alternative_phone = Column(String, nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="emergency_contacts_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class MedicalCondition(Base):
    __tablename__ = "par_medical_conditions"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"))
    condition = Column(String, nullable=False)
    notes = Column(Text, nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="medical_conditions_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class ParSacrament(Base):
    __tablename__ = "par_sacraments"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"))
    type = Column(Enum(ParSacramentType), nullable=False)
    date = Column(Date, nullable=False)
    place = Column(String, nullable=False)
    minister = Column(String, nullable=False)

    parishioner_ref = db_relationship("Parishioner", back_populates="par_sacraments_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Skill(Base):
    __tablename__ = "par_skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    parishioners_ref = db_relationship("Parishioner", secondary=parishioner_skills, back_populates="skills_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Language(Base):
    __tablename__ = "par_languages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    parishioners_ref = db_relationship("Parishioner", secondary=parishioner_languages, back_populates="languages_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)