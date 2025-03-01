import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import Parishioner, Occupation
from app.schemas.parishioner import OccupationCreate, OccupationRead, OccupationUpdate, APIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

occupation_router = APIRouter()

# Helper function to get parishioner or raise 404
def get_parishioner_or_404(session: Session, parishioner_id: int):
    parishioner = session.query(Parishioner).filter(
        Parishioner.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    return parishioner

# Create occupation for a parishioner
@occupation_router.post("/", response_model=APIResponse)
async def create_occupation(
    *,
    parishioner_id: int,
    occupation_in: OccupationCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Create or replace occupation for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    try:
        # Check if occupation already exists for this parishioner
        existing_occupation = session.query(Occupation).filter(
            Occupation.parishioner_id == parishioner_id
        ).first()
        
        if existing_occupation:
            # Update existing occupation
            for field, value in occupation_in.model_dump().items():
                setattr(existing_occupation, field, value)
            
            session.commit()
            session.refresh(existing_occupation)
            return APIResponse(
                message="Occupation updated successfully",
                data=OccupationRead.model_validate(existing_occupation)
            )
        else:
            # Create new occupation
            new_occupation = Occupation(
                parishioner_id=parishioner_id,
                **occupation_in.model_dump()
            )
            
            session.add(new_occupation)
            session.commit()
            session.refresh(new_occupation)
            
            return APIResponse(
                message="Occupation created successfully",
                data=OccupationRead.model_validate(new_occupation)
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
        logger.error(f"Error creating occupation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get occupation for a parishioner
@occupation_router.get("/", response_model=APIResponse)
async def get_occupation(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get occupation information for a parishioner."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get occupation
    occupation = session.query(Occupation).filter(
        Occupation.parishioner_id == parishioner_id
    ).first()
    
    if not occupation:
        return APIResponse(
            message="No occupation found for this parishioner",
            data=None
        )
    
    return APIResponse(
        message="Occupation retrieved successfully",
        data=OccupationRead.model_validate(occupation)
    )

# Update occupation for a parishioner
@occupation_router.put("/", response_model=APIResponse)
async def update_occupation(
    *,
    parishioner_id: int,
    occupation_in: OccupationUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Update occupation for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing occupation
    occupation = session.query(Occupation).filter(
        Occupation.parishioner_id == parishioner_id
    ).first()
    
    if not occupation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Occupation not found for this parishioner"
        )
    
    try:
        # Update only fields that were provided
        update_data = occupation_in.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=OccupationRead.model_validate(occupation)
            )
            
        for field, value in update_data.items():
            setattr(occupation, field, value)
            
        session.commit()
        session.refresh(occupation)
        
        return APIResponse(
            message="Occupation updated successfully",
            data=OccupationRead.model_validate(occupation)
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating occupation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete occupation for a parishioner
@occupation_router.delete("/", response_model=APIResponse)
async def delete_occupation(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Delete occupation for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing occupation
    occupation = session.query(Occupation).filter(
        Occupation.parishioner_id == parishioner_id
    ).first()
    
    if not occupation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Occupation not found for this parishioner"
        )
    
    try:
        session.delete(occupation)
        session.commit()
        
        return APIResponse(
            message="Occupation deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting occupation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )