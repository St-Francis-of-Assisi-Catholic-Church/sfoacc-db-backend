from datetime import datetime
import enum
from sqlalchemy import UUID, Column, ForeignKey, Integer, Date, DateTime, String, Table, Text, Time, func, Enum
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base
from app.models.common import MembershipStatus


# Association table for society members
society_members = Table(
    'par_society_members',
    Base.metadata,
    Column('society_id', Integer, ForeignKey('societies.id', ondelete="CASCADE")),
    Column('parishioner_id', UUID(as_uuid=True), ForeignKey('parishioners.id', ondelete="CASCADE")),
    Column('join_date', DateTime, nullable=True),
    Column('membership_status', 
           Enum(MembershipStatus), 
           nullable=False, 
           default=MembershipStatus.ACTIVE, server_default=MembershipStatus.ACTIVE.name),
    Column('created_at', DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column('updated_at', DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
)


class MeetingFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"



class LeadershipRole(str, enum.Enum):
    PRESIDENT = "President"
    VICE_PRESIDENT = "Vice President"
    SECRETARY = "Secretary"
    TREASURER = "Treasurer"
    CHAPLAIN = "Chaplain"
    COORDINATOR = "Coordinator"
    PATRON = "Patron"
    OTHER = "Other"


class Society(Base):
    __tablename__="societies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    date_inaugurated = Column(Date, nullable=True)

    # Meeting schedule
    meeting_frequency = Column(Enum(MeetingFrequency), nullable=False, default=MeetingFrequency.MONTHLY)
    meeting_day = Column(String, nullable=True)
    meeting_time = Column(Time, nullable=True)
    meeting_venue = Column(String, nullable=True)

    # Relationships
    members = db_relationship("Parishioner", secondary=society_members, back_populates="societies", lazy="dynamic")
    leadership_positions = db_relationship("SocietyLeadership", back_populates="society")



    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)



class SocietyLeadership(Base):
    __tablename__ = "society_leadership"

    id = Column(Integer, primary_key=True, index=True)
    society_id = Column(Integer, ForeignKey("societies.id", ondelete="CASCADE"))
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"))
    role = Column(Enum(LeadershipRole), nullable=False)
    custom_role = Column(String, nullable=True)  
    elected_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

    # Relationships
    society = db_relationship("Society", back_populates="leadership_positions")
    parishioner = db_relationship("Parishioner")