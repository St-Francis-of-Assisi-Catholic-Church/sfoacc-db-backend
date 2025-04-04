import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import distinct, func


from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    Occupation, FamilyInfo,
    EmergencyContact, MedicalCondition, ParSacrament,
    Skill, Child
)
from app.models.society import Society, society_members
from app.schemas.common import APIResponse
from app.schemas.parishioner import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/parishioners", response_model=APIResponse)
async def get_parishioner_stats(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get general statistics about parishioners."""
    try:
        # 1. Total parishioners
        total_parishioners = session.query(func.count(ParishionerModel.id)).scalar()
        
        # 2. Total societies
        total_societies = session.query(func.count(Society.id)).scalar()
        
        # 3. Count parishioners by societies
        society_stats = (
            session.query(
                Society.name,
                func.count(society_members.c.parishioner_id)
            )
            .join(society_members, Society.id == society_members.c.society_id)
            .group_by(Society.id, Society.name)
            .all()
        )
        
        # Count parishioners without any society
        # First, get IDs of parishioners who belong to at least one society
        parishioners_in_societies = (
            session.query(society_members.c.parishioner_id)
            .distinct()
            .subquery()
        )
        
        # Then count parishioners not in that subquery
        parishioners_without_society = (
            session.query(func.count(ParishionerModel.id))
            .filter(~ParishionerModel.id.in_(
                session.query(parishioners_in_societies.c.parishioner_id)
            ))
            .scalar()
        )
        
        # 4. Count of parishioners by day of week born
        day_of_week_stats = (
            session.query(
                func.extract('dow', ParishionerModel.date_of_birth),
                func.count(ParishionerModel.id)
            )
            .group_by(func.extract('dow', ParishionerModel.date_of_birth))
            .all()
        )
        
        # Convert day of week numbers to names
        days_of_week = {
            0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
            4: "Thursday", 5: "Friday", 6: "Saturday"
        }
        day_of_week_distribution = {days_of_week[int(day)]: count for day, count in day_of_week_stats}
        
        # 5. Count of parishioners by gender
        gender_stats = (
            session.query(
                ParishionerModel.gender,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.gender)
            .all()
        )
        
        # 6. Count of parishioners by place of worship
        worship_place_stats = (
            session.query(
                ParishionerModel.place_of_worship,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.place_of_worship)
            .all()
        )
        
        # 7. Count of parishioners by sacraments
        sacrament_stats = (
            session.query(
                ParSacrament.type,
                func.count(distinct(ParSacrament.parishioner_id))
            )
            .group_by(ParSacrament.type)
            .all()
        )

        stats = {
            "total_parishioners": total_parishioners,
            "total_societies": total_societies,
            "society_distribution": {s[0]: s[1] for s in society_stats},
            "parishioners_without_society": parishioners_without_society,
            "day_of_week_born_distribution": day_of_week_distribution,
            "gender_distribution": {g[0].value: g[1] for g in gender_stats},
            "place_of_worship_distribution": {w[0] or "Not specified": w[1] for w in worship_place_stats},
            "sacraments_distribution": {s[0].value: s[1] for s in sacrament_stats}
        }

        return APIResponse(
            message="Parishioner statistics retrieved successfully",
            data=stats
        )
    
    except Exception as e:
        logger.error(f"Error retrieving parishioner statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving parishioner statistics: {str(e)}"
        )
    




@router.get("/registration", response_model=APIResponse)
async def get_registration_stats(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get statistics about parishioner registration and verification status."""
    try:
        # 1. Total parishioners
        total_parishioners = session.query(func.count(ParishionerModel.id)).scalar()
        
        # 2. Total verified
        total_verified = (
            session.query(func.count(ParishionerModel.id))
            .filter(ParishionerModel.verification_status == VerificationStatus.VERIFIED)
            .scalar()
        )
        
        # 3. Total pending verification
        total_pending = (
            session.query(func.count(ParishionerModel.id))
            .filter(ParishionerModel.verification_status == VerificationStatus.PENDING)
            .scalar()
        )
        
        # 4. Total with new church ID
        total_with_new_church_id = (
            session.query(func.count(ParishionerModel.id))
            .filter(ParishionerModel.new_church_id.isnot(None))
            .scalar()
        )
        
        # 5. Total with no new church ID
        total_without_new_church_id = (
            session.query(func.count(ParishionerModel.id))
            .filter(ParishionerModel.new_church_id.is_(None))
            .scalar()
        )

        stats = {
            "total_parishioners": total_parishioners,
            "total_verified": total_verified,
            "total_pending_verification": total_pending,
            "total_unverified": total_parishioners - total_verified - total_pending,
            "total_with_new_church_id": total_with_new_church_id,
            "total_without_new_church_id": total_without_new_church_id
        }

        return APIResponse(
            message="Registration statistics retrieved successfully",
            data=stats
        )
    
    except Exception as e:
        logger.error(f"Error retrieving registration statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving registration statistics: {str(e)}"
        )