import logging
from typing import Any, List
from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import (
    Parishioner as ParishionerModel,
     Occupation, FamilyInfo,
    EmergencyContact, MedicalCondition, Sacrament,
    Skill, Child
)
from app.schemas.parishioner import *

from app.api.v1.routes.parishioner_routes.occupation import occupation_router
from app.api.v1.routes.parishioner_routes.emergency_contacts import emergency_contacts_router
from app.api.v1.routes.parishioner_routes.medical_conditions import medical_conditions_router
from app.api.v1.routes.parishioner_routes.family_info import family_info_router
from app.api.v1.routes.parishioner_routes.sacrements import sacraments_router
from app.api.v1.routes.parishioner_routes.skills import skills_router
from app.api.v1.routes.parishioner_routes.file_upload import file_upload_router
from app.api.v1.routes.parishioner_routes.verification_msg import verify_router


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# create single parishioner
@router.post("", response_model=APIResponse)
async def create_parishioner(
    *,
    session: SessionDep,
    parishioner_in: ParishionerCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Create new parishioner with all related information.
 
    and returns created parishioner instance
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
       # Create new parishioner from input data
        db_parishioner = ParishionerModel(**parishioner_in.model_dump())
        

        session.add(db_parishioner)
        session.flush()  # Get ID before creating related records
        session.commit()
        session.refresh(db_parishioner)

        return APIResponse(
            message="Parishioner created successfully",
            data=ParishionerRead.model_validate(db_parishioner)
        )

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get all parishioners
@router.get("/all", response_model=APIResponse)
async def get_all_parishioners(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get list of all parishioners with pagination."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Query parishioners with pagination
    parishioners = session.query(ParishionerModel)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    # Get total count
    total_count = session.query(func.count(ParishionerModel.id)).scalar()
    
    # Convert to response model
    parishioners_data = [
        ParishionerRead.model_validate(parishioner) 
        for parishioner in parishioners
    ]
    
    return APIResponse(
        message=f"Retrieved {len(parishioners_data)} parishioners",
        data={
            "total": total_count,
            "parishioners": parishioners_data,
            "skip": skip,
            "limit": limit
        }
    )

# get detailed parishioner
@router.get("/{parishioner_id}", response_model=APIResponse)
async def get_detailed_parishioner(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get detailed parishioner information by ID including all related entities."""

    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
    )
    
    # Query parishioner with all relationships eagerly loaded
    parishioner = session.query(ParishionerModel).options(
        joinedload(ParishionerModel.occupation_rel),
        joinedload(ParishionerModel.family_info_rel).joinedload(FamilyInfo.children_rel),
        joinedload(ParishionerModel.emergency_contacts_rel),
        joinedload(ParishionerModel.medical_conditions_rel),
        joinedload(ParishionerModel.sacraments_rel),
        joinedload(ParishionerModel.skills_rel)
    ).filter(
        ParishionerModel.id == parishioner_id
    ).first()

    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
     # Get children properly
    children = []
    if parishioner.family_info_rel and parishioner.family_info_rel.children_rel:
        for child in parishioner.family_info_rel.children_rel:
            children.append({
                "id": child.id,
                "name": child.name,
                "created_at": child.created_at,
                "updated_at": child.updated_at
            })
    
    family_info = None
    if parishioner.family_info_rel:
        family_info = {
            "id": parishioner.family_info_rel.id,
            "spouse_name": parishioner.family_info_rel.spouse_name,
            "spouse_status": parishioner.family_info_rel.spouse_status,
            "spouse_phone": parishioner.family_info_rel.spouse_phone,
            "father_name": parishioner.family_info_rel.father_name,
            "father_status": parishioner.family_info_rel.father_status,
            "mother_name": parishioner.family_info_rel.mother_name,
            "mother_status": parishioner.family_info_rel.mother_status,
            "children": children,  # Add children explicitly
            "created_at": parishioner.family_info_rel.created_at,
            "updated_at": parishioner.family_info_rel.updated_at
        }
    
    parishioner_dict = {
        # Basic fields from ParishionerRead
        "id": parishioner.id,
        "old_church_id": parishioner.old_church_id,
        "new_church_id": parishioner.new_church_id,
        "first_name": parishioner.first_name,
        "other_names": parishioner.other_names,
        "last_name": parishioner.last_name,
        "maiden_name": parishioner.maiden_name,
        "gender": parishioner.gender,
        "date_of_birth": parishioner.date_of_birth,
        "place_of_birth": parishioner.place_of_birth,
        "hometown": parishioner.hometown,
        "region": parishioner.region,
        "country": parishioner.country,
        "marital_status": parishioner.marital_status,
        "mobile_number": parishioner.mobile_number,
        "whatsapp_number": parishioner.whatsapp_number,
        "email_address": parishioner.email_address,
        "membership_status": parishioner.membership_status,
        "verification_status": parishioner.verification_status,
        "created_at": parishioner.created_at,
        "updated_at": parishioner.updated_at,
        
        # Map relationship fields with correct names
        "occupation": parishioner.occupation_rel,
        "family_info": family_info,
        "emergency_contacts": parishioner.emergency_contacts_rel,
        "medical_conditions": parishioner.medical_conditions_rel,
        "sacraments": parishioner.sacraments_rel,
        "skills": parishioner.skills_rel
    }

    return APIResponse(
        message="Parishioner retrieved successfully",
        data=ParishionerDetailedRead.model_validate(parishioner_dict)  # Pydantic will automatically handle the conversion
    )

# Update parishioner
@router.put("/{parishioner_id}", response_model=APIResponse)
async def update_parishioner(
    *,
    session: SessionDep,
    parishioner_id: int,
    parishioner_in: ParishionerPartialUpdate,
    current_user: CurrentUser,
) -> Any:
    """Update a parishioner's information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Get existing parishioner
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    try:
       # Only update fields that were actually provided
        update_data = parishioner_in.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=ParishionerRead.model_validate(parishioner)
            )
            
        for field, value in update_data.items():
            setattr(parishioner, field, value)

        session.commit()
        session.refresh(parishioner)
        
        return APIResponse(
            message="Parishioner updated successfully",
            data=ParishionerRead.model_validate(parishioner)
        )
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# generate churchID
@router.post("/{parishioner_id}/generate-church-id", response_model=APIResponse)
async def generate_church_id(
    *,
    session: SessionDep,
    parishioner_id: int,
    old_church_id: str = Query(..., description="Old church ID to be incorporated into the new ID"),
    current_user: CurrentUser,
    send_email: bool = Query(False, description="Whether to send confirmation email to the parishioner"),
) -> Any:
    """
    Generate a new church ID for a parishioner.
    
    Format: first_name_initial + last_name_initial + day_of_birth(2 digits) + 
    month_of_birth(2 digits) + "-" + old_church_id
    
    Example: Kofi Maxwell Nkrumah, DOB: 30/01/2005, Old ID: 045
    New church ID: KN3001-045
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get existing parishioner
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    # Check required fields are present
    if not parishioner.first_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name is required to generate church ID"
        )
    
    if not parishioner.last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last name is required to generate church ID"
        )
    
    if not parishioner.date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth is required to generate church ID"
        )
    
    if not old_church_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old church ID is required to generate new church ID"
        )
    
    try:
        # Generate new church ID
        first_name_initial = parishioner.first_name[0].upper()
        last_name_initial = parishioner.last_name[0].upper()
        
        # Format day and month with leading zeros if needed
        day_of_birth = f"{parishioner.date_of_birth.day:02d}"
        month_of_birth = f"{parishioner.date_of_birth.month:02d}"
        
        new_church_id = f"{first_name_initial}{last_name_initial}{day_of_birth}{month_of_birth}-{old_church_id}"
        
        # Update parishioner with new and old church IDs
        parishioner.new_church_id = new_church_id
        parishioner.old_church_id = old_church_id
        
        session.commit()
        session.refresh(parishioner)

        email_sent = False
        if send_email:
            if not parishioner.email_address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parishioner does not have email address"
                )
            
            from app.services.email.service import email_service
            parishioner_full_name = f"{parishioner.first_name} {parishioner.last_name}"
            email_sent = await email_service.send_church_id_confirmation(
                email=parishioner.email_address,
                parishioner_name=parishioner_full_name,
                system_id=str(parishioner_id),
                old_church_id=parishioner.old_church_id,
                new_church_id=parishioner.new_church_id
            )



        
        return APIResponse(
            message="Church ID generated successfully",
            data={
                "parishioner_id": parishioner.id,
                "old_church_id": parishioner.old_church_id,
                "new_church_id": parishioner.new_church_id,
                "email_sent": email_sent
            }
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error generating church ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# parishioner occupation
router.include_router(
    occupation_router,
    prefix="/{parishioner_id}/occupation",
)

# 
router.include_router(
    emergency_contacts_router,
    prefix="/{parishioner_id}/emergency-contacts",
)

# 
router.include_router(
    medical_conditions_router,
    prefix="/{parishioner_id}/medical-conditions",
)

# family info
router.include_router(
    family_info_router,
     prefix="/{parishioner_id}/family-info",
)

# sacrements
router.include_router(
    sacraments_router,
    prefix="/{parishioner_id}/sacraments",
)

# skills
router.include_router(
    skills_router,
    prefix="/{parishioner_id}/skills",
)

# file upload
router.include_router(
file_upload_router,
prefix="/import"
)


# verification msg
router.include_router(
verify_router,
prefix="/verify"
)