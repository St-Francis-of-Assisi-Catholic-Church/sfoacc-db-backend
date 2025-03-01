import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func


from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    Occupation, FamilyInfo,
    EmergencyContact, MedicalCondition, Sacrament,
    Skill, Child
)
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
        total_parishioners = session.query(ParishionerModel).count()
        
        # Gender distribution
        gender_stats = (
            session.query(
                ParishionerModel.gender,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.gender)
            .all()
        )
        
        # Marital status distribution
        marital_stats = (
            session.query(
                ParishionerModel.marital_status,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.marital_status)
            .all()
        )
        
        # Sacraments statistics
        sacrament_stats = (
            session.query(
                Sacrament.type,
                func.count(Sacrament.id)
            )
            .group_by(Sacrament.type)
            .all()
        )
        
        # Region distribution
        region_stats = (
            session.query(
                ParishionerModel.region,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.region)
            .all()
        )

        stats = {
            "total_parishioners": total_parishioners,
            "gender_distribution": {g[0]: g[1] for g in gender_stats},
            "marital_status_distribution": {m[0]: m[1] for m in marital_stats},
            "sacraments_distribution": {s[0]: s[1] for s in sacrament_stats},
            "region_distribution": {r[0]: r[1] for r in region_stats}
        }

        return APIResponse(
            message="Statistics retrieved successfully",
            data=stats
        )
    
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        )
