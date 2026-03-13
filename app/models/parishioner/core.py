from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, Date, DateTime, Integer, String, Enum, ForeignKey, Table, Text, func, Index
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

from app.models.common import Gender, MaritalStatus, MembershipStatus, VerificationStatus
from app.models.society import society_members

_now = lambda: datetime.now(timezone.utc)

# Association table for skills
parishioner_skills = Table(
    'par_parishioner_skills',
    Base.metadata,
    Column('parishioner_id', UUID(as_uuid=True), ForeignKey('parishioners.id', ondelete="CASCADE")),
    Column('skill_id', Integer, ForeignKey('par_skills.id')),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()),
    Column('updated_at', DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now()),
)

# Association table for languages
parishioner_languages = Table(
    'par_languages',
    Base.metadata,
    Column('parishioner_id', UUID(as_uuid=True), ForeignKey('parishioners.id', ondelete="CASCADE")),
    Column('language_id', Integer, ForeignKey('languages.id', ondelete="CASCADE")),
    Column('created_at', DateTime(timezone=True), nullable=False, default=_now, server_default=func.now()),
    Column('updated_at', DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now()),
)


class ParishionerSacrament(Base):
    __tablename__ = "par_sacraments"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey('parishioners.id', ondelete="CASCADE"), nullable=False)
    sacrament_id = Column(Integer, ForeignKey('sacrament.id', ondelete="CASCADE"), nullable=False)
    date_received = Column(Date, nullable=True)
    place = Column(String, nullable=True)
    minister = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    parishioner = db_relationship("Parishioner", back_populates="sacrament_records")
    sacrament = db_relationship("Sacrament")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())


class Parishioner(Base):
    __tablename__ = "parishioners"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    old_church_id = Column(String, nullable=True, index=True)
    new_church_id = Column(String, nullable=True, index=True)

    membership_status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.ACTIVE, server_default=MembershipStatus.ACTIVE.name, index=True)
    verification_status = Column(Enum(VerificationStatus), nullable=False, default=VerificationStatus.UNVERIFIED, server_default=VerificationStatus.UNVERIFIED.name, index=True)

    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    other_names = Column(String(200), nullable=True)
    maiden_name = Column(String(100), nullable=True)
    gender = Column(Enum(Gender), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    place_of_birth = Column(String, nullable=True)
    hometown = Column(String, nullable=True)
    region = Column(String, nullable=True)
    country = Column(String, nullable=True)
    marital_status = Column(Enum(MaritalStatus), nullable=False, default=MaritalStatus.SINGLE, server_default=MaritalStatus.SINGLE.name)
    mobile_number = Column(String, nullable=True, index=True)
    whatsapp_number = Column(String, nullable=True)
    email_address = Column(String, nullable=True, index=True)
    current_residence = Column(String, nullable=True)

    church_community_id = Column(Integer, ForeignKey("church_communities.id", ondelete="CASCADE"), nullable=True, index=True)
    place_of_worship_id = Column(Integer, ForeignKey("places_of_worship.id", ondelete="CASCADE"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            'unique_parishioner_composite_idx',
            'first_name', 'last_name', 'other_names',
            'date_of_birth', 'gender', 'place_of_birth',
            unique=True,
            postgresql_where=(
                (first_name.isnot(None)) & (last_name.isnot(None))
            ),
        ),
    )

    def __repr__(self):
        return f"<Parishioner(id={self.id}, name='{self.first_name} {self.last_name}', old_id='{self.old_church_id}')>"

    occupation_rel = db_relationship("Occupation", back_populates="parishioner_ref", uselist=False, cascade="all, delete-orphan")
    family_info_rel = db_relationship("FamilyInfo", back_populates="parishioner_ref", uselist=False, cascade="all, delete-orphan")
    emergency_contacts_rel = db_relationship("EmergencyContact", back_populates="parishioner_ref", cascade="all, delete-orphan")
    medical_conditions_rel = db_relationship("MedicalCondition", back_populates="parishioner_ref", cascade="all, delete-orphan")

    skills_rel = db_relationship("Skill", secondary=parishioner_skills, back_populates="parishioners_ref")
    languages_rel = db_relationship("Language", secondary=parishioner_languages, back_populates="parishioners_ref")

    societies = db_relationship("Society", secondary=society_members, back_populates="members")

    church_community = db_relationship("ChurchCommunity", backref="parishioners")
    place_of_worship = db_relationship("PlaceOfWorship", backref="parishioners")
    sacrament_records = db_relationship("ParishionerSacrament", back_populates="parishioner", cascade="all, delete-orphan")
