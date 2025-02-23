from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Enum, ForeignKey, Table, Text, func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

# Enums
class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class MaritalStatus(str, enum.Enum):
    SINGLE = "single"
    MARRIED = "married"
    WIDOWED = "widowed"
    DIVORCED = "divorced"

class ParentalStatus(str, enum.Enum):
    ALIVE = "alive"
    DECEASED = "deceased"
    UNKNOWN = "unknown"

class SacramentType(str, enum.Enum):
    BAPTISM = "Baptism"
    FIRST_COMMUNION = "First Holy Communion"
    CONFIRMATION = "Confirmation"
    PENANCE = "Penance"
    ANOINTING = "Anointing of the Sick"
    HOLY_ORDERS = "Holy Orders"
    MATRIMONY = "Holy Matrimony"

# Association table for skills
parishioner_skills = Table(
    'parishioner_skills',
    Base.metadata,
    Column('parishioner_id', Integer, ForeignKey('parishioners.id')),
    Column('skill_id', Integer, ForeignKey('skills.id'))
)

class Parishioner(Base):
    __tablename__ = "parishioners"

    id = Column(Integer, primary_key=True, index=True)
    old_church_id = Column(String, nullable=True)
    new_church_id = Column(String,nullable=True)
    # Personal Info
    first_name = Column(String, nullable=False)
    other_names = Column(String, nullable=True)
    last_name = Column(String, nullable=False)
    maiden_name = Column(String, nullable=True)
    gender = Column(Enum(Gender), nullable=False)
    date_of_birth = Column(DateTime(timezone=True), nullable=False)
    place_of_birth = Column(String, nullable=False)
    hometown = Column(String, nullable=False)
    region = Column(String, nullable=False)
    country = Column(String, nullable=False)
    marital_status = Column(Enum(MaritalStatus), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

    # Relationships
    contact_info_rel = relationship("ContactInfo", back_populates="parishioner_ref", uselist=False)
    occupation_rel = relationship("Occupation", back_populates="parishioner_ref", uselist=False)
    family_info_rel = relationship("FamilyInfo", back_populates="parishioner_ref", uselist=False)
    emergency_contacts_rel = relationship("EmergencyContact", back_populates="parishioner_ref")
    medical_conditions_rel = relationship("MedicalCondition", back_populates="parishioner_ref")
    sacraments_rel = relationship("Sacrament", back_populates="parishioner_ref")
    skills_rel = relationship("Skill", secondary=parishioner_skills, back_populates="parishioners_ref")

class ContactInfo(Base):
    __tablename__ = "contact_info"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"), unique=True)
    mobile_number = Column(String, nullable=False)
    whatsapp_number = Column(String, nullable=True)
    email_address = Column(String, nullable=True)
    
    parishioner_ref = relationship("Parishioner", back_populates="contact_info_rel")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Occupation(Base):
    __tablename__ = "occupations"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"), unique=True)
    role = Column(String, nullable=False)
    employer = Column(String, nullable=False)

    parishioner_ref = relationship("Parishioner", back_populates="occupation_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class FamilyInfo(Base):
    __tablename__ = "family_info"

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

    parishioner_ref = relationship("Parishioner", back_populates="family_info_rel")
    children_rel = relationship("Child", back_populates="family_ref")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    family_info_id = Column(Integer, ForeignKey("family_info.id"))
    name = Column(String, nullable=False)

    family_ref = relationship("FamilyInfo", back_populates="children_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"))
    name = Column(String, nullable=False)
    relationshipp = Column(String, nullable=False)
    primary_phone = Column(String, nullable=False)
    alternative_phone = Column(String, nullable=True)

    parishioner_ref = relationship("Parishioner", back_populates="emergency_contacts_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class MedicalCondition(Base):
    __tablename__ = "medical_conditions"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"))
    condition = Column(String, nullable=False)
    notes = Column(Text, nullable=True)

    parishioner_ref = relationship("Parishioner", back_populates="medical_conditions_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Sacrament(Base):
    __tablename__ = "sacraments"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(Integer, ForeignKey("parishioners.id"))
    type = Column(Enum(SacramentType), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    place = Column(String, nullable=False)
    minister = Column(String, nullable=False)

    parishioner_ref = relationship("Parishioner", back_populates="sacraments_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    parishioners_ref = relationship("Parishioner", secondary=parishioner_skills, back_populates="skills_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)