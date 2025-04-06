import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import distinct, func


from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    Occupation, FamilyInfo,
    EmergencyContact, MedicalCondition,
    ParishionerSacrament,
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
        
        # 3. Total places of worship
        from app.models.place_of_worship import PlaceOfWorship
        total_places_of_worship = session.query(func.count(PlaceOfWorship.id)).scalar()
        
        # 4. Society distribution (count of members in each society)
        society_stats = (
            session.query(
                Society.name,
                func.count(society_members.c.parishioner_id)
            )
            .join(society_members, Society.id == society_members.c.society_id)
            .group_by(Society.id, Society.name)
            .all()
        )
        
        # 5. Parishioners in societies
        parishioners_in_societies_count = (
            session.query(func.count(distinct(society_members.c.parishioner_id)))
            .scalar()
        )
        
        # 6. Parishioners without any society
        parishioners_without_society = total_parishioners - parishioners_in_societies_count
        
        # 7. Day of week born distribution (all days with counts, 0 if none)
        day_of_week_stats = (
            session.query(
                func.extract('dow', ParishionerModel.date_of_birth),
                func.count(ParishionerModel.id)
            )
            .group_by(func.extract('dow', ParishionerModel.date_of_birth))
            .all()
        )
        
        # Convert day of week numbers to names and ensure all days are included
        days_of_week = {
            0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
            4: "Thursday", 5: "Friday", 6: "Saturday"
        }
        
        # Initialize with 0 counts for all days
        day_of_week_distribution = {day_name: 0 for day_name in days_of_week.values()}
        
        # Update with actual counts
        for day, count in day_of_week_stats:
            if day is not None:
                day_of_week_distribution[days_of_week[int(day)]] = count
        
        # 8. Sacraments distribution per parishioner
        from app.models.sacrament import Sacrament
        
        # Get all sacraments first to ensure we include those with zero counts
        all_sacraments = session.query(Sacrament.name).all()
        sacrament_names = [sacrament[0] for sacrament in all_sacraments]
        
        # Initialize counts with zeros
        sacrament_distribution = {name: 0 for name in sacrament_names}
        
        # Update with actual counts from ParishionerSacrament
        sacrament_stats = (
            session.query(
                Sacrament.name,
                func.count(distinct(ParishionerSacrament.parishioner_id))
            )
            .join(ParishionerSacrament, Sacrament.id == ParishionerSacrament.sacrament_id)
            .group_by(Sacrament.name)
            .all()
        )
        
        for sacrament_name, count in sacrament_stats:
            if sacrament_name is not None:
                sacrament_distribution[sacrament_name] = count
        
        # 9. Additional useful statistics
        
        # Gender distribution
        gender_stats = (
            session.query(
                ParishionerModel.gender,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.gender)
            .all()
        )
        
        gender_distribution = {g[0].value if g[0] else "Not specified": g[1] for g in gender_stats}
        
        # Age group distribution
        current_year = datetime.utcnow().year
        age_groups = {
            "0-17": 0,
            "18-25": 0,
            "26-40": 0,
            "41-60": 0,
            "61+": 0,
            "Unknown": 0
        }
        
        for year_born, count in session.query(
            func.extract('year', ParishionerModel.date_of_birth),
            func.count(ParishionerModel.id)
        ).group_by(func.extract('year', ParishionerModel.date_of_birth)).all():
            if year_born is None:
                age_groups["Unknown"] += count
            else:
                age = current_year - int(year_born)
                if age <= 17:
                    age_groups["0-17"] += count
                elif age <= 25:
                    age_groups["18-25"] += count
                elif age <= 40:
                    age_groups["26-40"] += count
                elif age <= 60:
                    age_groups["41-60"] += count
                else:
                    age_groups["61+"] += count
        
        # Total church communities
        from app.models.church_community import ChurchCommunity
        total_communities = session.query(func.count(ChurchCommunity.id)).scalar()

        stats = {
            "total_parishioners": total_parishioners,
            "total_societies": total_societies,
            "total_places_of_worship": total_places_of_worship,
            "total_church_communities": total_communities,
            "society_distribution": {s[0]: s[1] for s in society_stats},
            "parishioners_in_societies": parishioners_in_societies_count,
            "parishioners_without_society": parishioners_without_society,
            "day_of_week_born_distribution": day_of_week_distribution,
            "sacraments_distribution": sacrament_distribution,
            "gender_distribution": gender_distribution,
            "age_group_distribution": age_groups
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