import logging
from typing import Any, List
from fastapi import APIRouter, HTTPException, status, Path as FastAPIPath
from pydantic import validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import Parishioner, Sacrament, SacramentType
from app.schemas.parishioner import SacramentCreate, SacramentRead, SacramentUpdate, APIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sacraments_router = APIRouter()


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



# Helper endpoint to check which sacraments a parishioner has received
@sacraments_router.get("/summary", response_model=APIResponse)
async def get_sacrament_summary(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get a summary of which sacraments a parishioner has received."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get all sacraments for this parishioner
    sacraments = session.query(Sacrament.type).filter(
        Sacrament.parishioner_id == parishioner_id
    ).all()
    
    # Extract sacrament types
    received_sacrament_types = [s.type for s in sacraments]
    
    # Create a summary dictionary with all possible sacrament types
    summary = {
        sacrament_type.value: sacrament_type in received_sacrament_types
        for sacrament_type in SacramentType
    }
    
    return APIResponse(
        message="Sacrament summary retrieved successfully",
        data=summary
    )

# Add or update a sacrament for a parishioner
@sacraments_router.post("/", response_model=APIResponse)
async def add_or_update_sacrament(
    *,
    parishioner_id: int,
    sacrament_in: SacramentCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Add or update a sacrament for a parishioner. Only one record per sacrament type is allowed."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    try:
        # Check if this sacrament type already exists for this parishioner
        existing_sacrament = session.query(Sacrament).filter(
            and_(
                Sacrament.parishioner_id == parishioner_id,
                Sacrament.type == sacrament_in.type
            )
        ).first()
        
        if existing_sacrament:
            # Update existing sacrament
            existing_sacrament.date = sacrament_in.date
            existing_sacrament.place = sacrament_in.place
            existing_sacrament.minister = sacrament_in.minister
            
            session.commit()
            session.refresh(existing_sacrament)
            
            return APIResponse(
                message=f"{sacrament_in.type.value} sacrament updated successfully",
                data=SacramentRead.model_validate(existing_sacrament)
            )
        else:
            # Create new sacrament
            new_sacrament = Sacrament(
                parishioner_id=parishioner_id,
                type=sacrament_in.type,
                date=sacrament_in.date,
                place=sacrament_in.place,
                minister=sacrament_in.minister
            )
            
            session.add(new_sacrament)
            session.commit()
            session.refresh(new_sacrament)
            
            # Also refresh the parishioner to make sure the relationship is loaded
            session.refresh(parishioner)
            
            return APIResponse(
                message=f"{sacrament_in.type.value} sacrament added successfully",
                data=SacramentRead.model_validate(new_sacrament)
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
        logger.error(f"Error adding/updating sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get all sacraments for a parishioner
@sacraments_router.get("/", response_model=APIResponse)
async def get_sacraments(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all sacraments for a parishioner."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get sacraments
    sacraments = session.query(Sacrament).filter(
        Sacrament.parishioner_id == parishioner_id
    ).all()
    
    return APIResponse(
        message=f"Retrieved {len(sacraments)} sacraments",
        data=[SacramentRead.model_validate(sacrament) for sacrament in sacraments]
    )

# Get a specific sacrament by type
@sacraments_router.get("/type/{sacrament_type}", response_model=APIResponse)
async def get_sacrament_by_type(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_type: SacramentType,
) -> Any:
    """Get a specific sacrament by type."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get the specific sacrament
    sacrament = session.query(Sacrament).filter(
        and_(
            Sacrament.parishioner_id == parishioner_id,
            Sacrament.type == sacrament_type
        )
    ).first()
    
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{sacrament_type.value} sacrament not found"
        )
    
    return APIResponse(
        message=f"{sacrament_type.value} sacrament retrieved successfully",
        data=SacramentRead.model_validate(sacrament)
    )

# Get a specific sacrament by ID
@sacraments_router.get("/{sacrament_id}", response_model=APIResponse)
async def get_sacrament(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_id: int = FastAPIPath(..., title="The ID of the sacrament to get"),
) -> Any:
    """Get a specific sacrament by ID."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get the specific sacrament
    sacrament = session.query(Sacrament).filter(
        and_(
            Sacrament.id == sacrament_id,
            Sacrament.parishioner_id == parishioner_id
        )
    ).first()
    
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sacrament not found"
        )
    
    return APIResponse(
        message="Sacrament retrieved successfully",
        data=SacramentRead.model_validate(sacrament)
    )

# Update a sacrament
@sacraments_router.put("/{sacrament_id}", response_model=APIResponse)
async def update_sacrament(
    *,
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_id: int = FastAPIPath(..., title="The ID of the sacrament to update"),
    sacrament_in: SacramentUpdate,
) -> Any:
    """Update a sacrament for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing sacrament
    sacrament = session.query(Sacrament).filter(
        and_(
            Sacrament.id == sacrament_id,
            Sacrament.parishioner_id == parishioner_id
        )
    ).first()
    
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sacrament not found"
        )
    
    try:
        # Update only fields that were provided
        update_data = sacrament_in.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=SacramentRead.model_validate(sacrament)
            )
        
        # If type is being updated, check for duplicates
        if 'type' in update_data and update_data['type'] != sacrament.type:
            # Check if this new sacrament type already exists for this parishioner
            existing_sacrament = session.query(Sacrament).filter(
                and_(
                    Sacrament.parishioner_id == parishioner_id,
                    Sacrament.type == update_data['type']
                )
            ).first()
            
            if existing_sacrament:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{update_data['type'].value} sacrament already exists for this parishioner"
                )
        
        # Apply updates
        for field, value in update_data.items():
            setattr(sacrament, field, value)
            
        session.commit()
        session.refresh(sacrament)
        
        return APIResponse(
            message="Sacrament updated successfully",
            data=SacramentRead.model_validate(sacrament)
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete a sacrament
@sacraments_router.delete("/{sacrament_id}", response_model=APIResponse)
async def delete_sacrament(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_id: int = FastAPIPath(..., title="The ID of the sacrament to delete"),
) -> Any:
    """Delete a sacrament for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing sacrament
    sacrament = session.query(Sacrament).filter(
        and_(
            Sacrament.id == sacrament_id,
            Sacrament.parishioner_id == parishioner_id
        )
    ).first()
    
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sacrament not found"
        )
    
    try:
        # Get sacrament type for message before deletion
        sacrament_type = sacrament.type.value
        
        # Delete the sacrament
        session.delete(sacrament)
        session.commit()
        
        # Refresh the parishioner to update relationship
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"{sacrament_type} sacrament deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete a sacrament by type
@sacraments_router.delete("/type/{sacrament_type}", response_model=APIResponse)
async def delete_sacrament_by_type(
    parishioner_id: int,
    sacrament_type: SacramentType,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Delete a sacrament by type for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing sacrament
    sacrament = session.query(Sacrament).filter(
        and_(
            Sacrament.parishioner_id == parishioner_id,
            Sacrament.type == sacrament_type
        )
    ).first()
    
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{sacrament_type.value} sacrament not found"
        )
    
    try:
        # Delete the sacrament
        session.delete(sacrament)
        session.commit()
        
        # Refresh the parishioner to update relationship
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"{sacrament_type.value} sacrament deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )





# Now add the batch endpoint to the sacraments_router
@sacraments_router.post("/batch", response_model=APIResponse)
async def batch_update_sacraments(
    parishioner_id: int,
    batch_data: List[SacramentCreate],
    session: SessionDep,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Replace all existing sacraments of a parishioner with the new batch.
    Each parishioner can have at most one of each sacrament type.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    try:
        # Delete all existing sacraments for this parishioner
        session.query(Sacrament).filter(
            Sacrament.parishioner_id == parishioner_id
        ).delete()
        
        # Validate no duplicate sacrament types in the request
        sacrament_types = [sacrament.type for sacrament in batch_data]
        if len(sacrament_types) != len(set(sacrament_types)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each parishioner can have at most one of each sacrament type"
            )
        
        # Create new sacraments
        new_sacraments = []
        for sacrament_data in batch_data:
            new_sacrament = Sacrament(
                parishioner_id=parishioner_id,
                type=sacrament_data.type,
                date=sacrament_data.date,
                place=sacrament_data.place,
                minister=sacrament_data.minister
            )
            session.add(new_sacrament)
            new_sacraments.append(new_sacrament)
        
        session.commit()
        
        # Refresh all new sacraments to get their IDs and any other database-generated values
        for sacrament in new_sacraments:
            session.refresh(sacrament)
        
        # Refresh the parishioner to update relationships
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"Successfully replaced sacraments for parishioner. Now has {len(new_sacraments)} sacraments.",
            data=[SacramentRead.model_validate(sacrament) for sacrament in new_sacraments]
        )
        
    except ValueError as e:
        # Handle validation errors from the Pydantic model
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating sacraments for parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )