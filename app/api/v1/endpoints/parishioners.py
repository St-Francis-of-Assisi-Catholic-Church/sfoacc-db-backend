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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# create single parishioner
@router.post("/", response_model=APIResponse)
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
@router.get("/", response_model=APIResponse)
async def get_all_parishioners(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get list of all parishioners with pagination."""
    
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

    return APIResponse(
        message="Parishioner retrieved successfully",
        data=ParishionerDetailedRead.model_validate(parishioner)  # Pydantic will automatically handle the conversion
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
    
