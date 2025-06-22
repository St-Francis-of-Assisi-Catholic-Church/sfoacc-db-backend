from datetime import datetime
import uuid
from sqlalchemy import UUID, Boolean, Column, Date, DateTime, Index, Integer, String, Enum, ForeignKey, Table, Text, func, UniqueConstraint
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

from app.models.common import Gender, LifeStatus, MaritalStatus, MembershipStatus, VerificationStatus
from app.models.society import society_members


# Association table for skills
parishioner_skills = Table(
    'par_parishioner_skills',
    Base.metadata,
    Column('parishioner_id', UUID(as_uuid=True), ForeignKey('parishioners.id', ondelete="CASCADE")),
    Column('skill_id', Integer, ForeignKey('par_skills.id')),
    Column('created_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now()),
    Column('updated_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=func.now())
)

# Association table for languages
parishioner_languages = Table(
    'par_languages', 
    Base.metadata,
    Column('parishioner_id', UUID(as_uuid=True), ForeignKey('parishioners.id', ondelete="CASCADE")),
    Column('language_id', Integer, ForeignKey('languages.id', ondelete="CASCADE")) ,
    Column('created_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now()),
    Column('updated_at', DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=func.now())
)





# Parishioner sacrament records
class ParishionerSacrament(Base):
    __tablename__ = "par_sacraments"
    
    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey('parishioners.id', ondelete="CASCADE"), nullable=False)
    sacrament_id = Column(Integer, ForeignKey('sacrament.id', ondelete="CASCADE"), nullable=False)
    date_received = Column(Date, nullable=True)
    place = Column(String, nullable=True)
    minister = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    parishioner = db_relationship("Parishioner", back_populates="sacrament_records")
    sacrament = db_relationship("Sacrament")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)
    
    # Ensure once_only sacraments can only occur once per parishioner
    # __table_args__ = (
    #     UniqueConstraint('parishioner_id', 'sacrament_id', name='uq_parishioner_once_only_sacrament'),
    # )

class Parishioner(Base):
    __tablename__ = "parishioners"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    old_church_id = Column(String, nullable=True)
    new_church_id = Column(String, nullable=True)

    # Status fields with defaults
    membership_status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.ACTIVE, server_default=MembershipStatus.ACTIVE.name)
    verification_status = Column(Enum(VerificationStatus), nullable=False, default=VerificationStatus.UNVERIFIED, server_default=VerificationStatus.UNVERIFIED.name)

     # Core identity fields
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    other_names = Column(String(200), nullable=True)
    maiden_name = Column(String(100), nullable=True)

    # Personal Info
    # first_name = Column(String, nullable=False)
    # other_names = Column(String, nullable=True)
    # last_name = Column(String, nullable=False)
    # maiden_name = Column(String, nullable=True)
    gender = Column(Enum(Gender), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    place_of_birth = Column(String, nullable=True)
    hometown = Column(String, nullable=True)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    marital_status = Column(Enum(MaritalStatus), nullable=False, default=MaritalStatus.SINGLE, server_default=MaritalStatus.SINGLE.name)
    mobile_number = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    email_address = Column(String, nullable=True)
    current_residence = Column(String, nullable=True)
    
    # Foreign keys for related models
    church_community_id = Column(Integer, ForeignKey("church_communities.id", ondelete="CASCADE"), nullable=True)
    place_of_worship_id = Column(Integer, ForeignKey("places_of_worship.id", ondelete="CASCADE"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

     # Add the functional unique index at the table level
    __table_args__ = (
        # This creates the unique constraint in SQLAlchemy
        Index(
            'unique_parishioner_composite_idx',
            'first_name', 'last_name', 'other_names', 
            'date_of_birth', 'gender', 'place_of_birth',
            unique=True,
            postgresql_where=(
                (first_name.isnot(None)) & (last_name.isnot(None))
            )
        ),
    )
    def __repr__(self):
        return f"<Parishioner(id={self.id}, name='{self.first_name} {self.last_name}', old_id='{self.old_church_id}')>"

    # Relationships
    occupation_rel = db_relationship("Occupation", back_populates="parishioner_ref", uselist=False, cascade="all, delete-orphan")
    family_info_rel = db_relationship("FamilyInfo", back_populates="parishioner_ref", uselist=False, cascade="all, delete-orphan")
    emergency_contacts_rel = db_relationship("EmergencyContact", back_populates="parishioner_ref", cascade="all, delete-orphan")
    medical_conditions_rel = db_relationship("MedicalCondition", back_populates="parishioner_ref", cascade="all, delete-orphan")

    # no need for cascade for many-to-many
    skills_rel = db_relationship("Skill", secondary=parishioner_skills, back_populates="parishioners_ref")
    languages_rel = db_relationship("Language", secondary=parishioner_languages, back_populates="parishioners_ref")
    
    # Societies relationship
    societies = db_relationship("Society", secondary=society_members, back_populates="members")
    
    # New relationships for the added models
    church_community = db_relationship("ChurchCommunity", backref="parishioners")
    place_of_worship = db_relationship("PlaceOfWorship", backref="parishioners")
    sacrament_records = db_relationship("ParishionerSacrament", back_populates="parishioner", cascade="all, delete-orphan")

class Occupation(Base):
    __tablename__ = "par_occupations"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"), unique=True)
    role = Column(String, nullable=False)
    employer = Column(String, nullable=False)

    parishioner_ref = db_relationship("Parishioner", back_populates="occupation_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class FamilyInfo(Base):
    __tablename__ = "par_family"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"), unique=True)
    
    # Spouse Information
    spouse_name = Column(String, nullable=True)
    spouse_status = Column(String, nullable=True)
    spouse_phone = Column(String, nullable=True)
    
    # Parent Information
    father_name = Column(String, nullable=True)
    father_status = Column(Enum(LifeStatus), nullable=True)
    mother_name = Column(String, nullable=True)
    mother_status = Column(Enum(LifeStatus), nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="family_info_rel")
    children_rel = db_relationship("Child", back_populates="family_ref", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class Child(Base):
    __tablename__ = "par_children"

    id = Column(Integer, primary_key=True, index=True)
    family_info_id = Column(Integer, ForeignKey("par_family.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)

    family_ref = db_relationship("FamilyInfo", back_populates="children_rel")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

class EmergencyContact(Base):
    __tablename__ = "par_emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"))
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
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"))
    condition = Column(String, nullable=False)
    notes = Column(Text, nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="medical_conditions_rel")

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


