import logging
from typing import Any, List
from fastapi import APIRouter, HTTPException, status, Path as FastAPIPath
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import Parishioner, ParishionerSacrament
from app.models.sacrament import Sacrament, SacramentType
from app.schemas.common import APIResponse
from app.schemas.parishioner import ParSacramentCreate, ParSacramentRead, SacramentUpdate

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


# Helper function to get sacrament by type or id
def get_sacrament_by_type_or_id(session: Session, sacrament_identifier):
    # Try to get by ID if it's an integer
    if isinstance(sacrament_identifier, int):
        sacrament = session.query(Sacrament).filter(Sacrament.id == sacrament_identifier).first()
    elif isinstance(sacrament_identifier, SacramentType):
        # It's a SacramentType enum
        sacrament = session.query(Sacrament).filter(Sacrament.name == sacrament_identifier.value).first()
    else:
        # Try to get by name string
        try:
            # Try to convert to SacramentType enum if it's a string
            sacrament_type = SacramentType(sacrament_identifier)
            sacrament = session.query(Sacrament).filter(Sacrament.name == sacrament_type.value).first()
        except (ValueError, TypeError):
            # If not a valid enum value, try direct name lookup
            sacrament = session.query(Sacrament).filter(Sacrament.name == sacrament_identifier).first()
    
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sacrament not found: {sacrament_identifier}"
        )
    return sacrament


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
    
    # Get all sacrament records for this parishioner
    parishioner_sacraments = session.query(ParishionerSacrament).filter(
        ParishionerSacrament.parishioner_id == parishioner_id
    ).all()
    
    # Create a set of sacrament IDs the parishioner has received
    received_sacrament_ids = {record.sacrament_id for record in parishioner_sacraments}
    
    # Create a summary dictionary with all possible sacrament types
    summary = {}
    for sacrament_type in SacramentType:
        # Get the sacrament record for this type
        sacrament = session.query(Sacrament).filter(
            Sacrament.name == sacrament_type.value
        ).first()
        
        if sacrament:
            summary[sacrament_type.value] = sacrament.id in received_sacrament_ids
        else:
            # If sacrament record doesn't exist yet, mark as not received
            summary[sacrament_type.value] = False
    
    return APIResponse(
        message="Sacrament summary retrieved successfully",
        data=summary
    )

# Add a sacrament for a parishioner
@sacraments_router.post("/", response_model=APIResponse)
async def add_sacrament(
    *,
    parishioner_id: int,
    sacrament_in: ParSacramentCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Add a sacrament for a parishioner.
    For once-only sacraments (like Baptism), each parishioner can receive it only once.
    For repeatable sacraments (like Confession), multiple entries are allowed.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get sacrament
    sacrament = get_sacrament_by_type_or_id(session, sacrament_in.sacrament_id)
    
    try:
        # For once-only sacraments, check if the parishioner already has it
        if sacrament.once_only:
            existing_sacrament = session.query(ParishionerSacrament).filter(
                and_(
                    ParishionerSacrament.parishioner_id == parishioner_id,
                    ParishionerSacrament.sacrament_id == sacrament.id
                )
            ).first()
            
            if existing_sacrament:
                # Update the existing record for once-only sacraments
                existing_sacrament.date_received = sacrament_in.date_received
                existing_sacrament.place = sacrament_in.place
                existing_sacrament.minister = sacrament_in.minister
                existing_sacrament.notes = sacrament_in.notes
                
                session.commit()
                session.refresh(existing_sacrament)
                
                return APIResponse(
                    message=f"{sacrament.name} sacrament updated successfully",
                    data=ParSacramentRead.model_validate(existing_sacrament)
                )
        
        # Create a new sacrament record
        # This will be for repeatable sacraments or once-only sacraments that don't exist yet
        new_sacrament_record = ParishionerSacrament(
            parishioner_id=parishioner_id,
            sacrament_id=sacrament.id,
            date_received=sacrament_in.date_received,
            place=sacrament_in.place,
            minister=sacrament_in.minister,
            notes=sacrament_in.notes
        )
        
        session.add(new_sacrament_record)
        session.commit()
        session.refresh(new_sacrament_record)
        
        # Also refresh the parishioner to make sure the relationship is loaded
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"{sacrament.name} sacrament added successfully",
            data=ParSacramentRead.model_validate(new_sacrament_record)
        )
            
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        
        # Check if this is a once-only sacrament violation
        if "once-only sacraments once" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This parishioner has already received the {sacrament.name} sacrament, which can only be received once."
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding/updating sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get all sacrament records for a parishioner
@sacraments_router.get("/", response_model=APIResponse)
async def get_sacraments(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all sacrament records for a parishioner."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get sacraments
    sacrament_records = session.query(ParishionerSacrament).filter(
        ParishionerSacrament.parishioner_id == parishioner_id
    ).all()
    
    return APIResponse(
        message=f"Retrieved {len(sacrament_records)} sacrament records",
        data=[ParSacramentRead.model_validate(record) for record in sacrament_records]
    )

# Get all records for a specific sacrament type
@sacraments_router.get("/type/{sacrament_type}", response_model=APIResponse)
async def get_sacrament_records_by_type(
    parishioner_id: int,
    sacrament_type: SacramentType,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all records for a specific sacrament type."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get the sacrament by type
    sacrament = session.query(Sacrament).filter(Sacrament.name == sacrament_type.value).first()
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sacrament not found for type: {sacrament_type.value}"
        )
    
    # Get all the sacrament records for this type
    sacrament_records = session.query(ParishionerSacrament).filter(
        and_(
            ParishionerSacrament.parishioner_id == parishioner_id,
            ParishionerSacrament.sacrament_id == sacrament.id
        )
    ).all()
    
    if not sacrament_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{sacrament_type.value} sacrament not found for this parishioner"
        )
    
    return APIResponse(
        message=f"Retrieved {len(sacrament_records)} {sacrament_type.value} sacrament records",
        data=[ParSacramentRead.model_validate(record) for record in sacrament_records]
    )

# Get a specific sacrament record by ID
@sacraments_router.get("/{sacrament_record_id}", response_model=APIResponse)
async def get_sacrament_record(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_record_id: int = FastAPIPath(..., title="The ID of the sacrament record to get"),
) -> Any:
    """Get a specific sacrament record by ID."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get the specific sacrament record
    sacrament_record = session.query(ParishionerSacrament).filter(
        and_(
            ParishionerSacrament.id == sacrament_record_id,
            ParishionerSacrament.parishioner_id == parishioner_id
        )
    ).first()
    
    if not sacrament_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sacrament record not found"
        )
    
    return APIResponse(
        message="Sacrament record retrieved successfully",
        data=ParSacramentRead.model_validate(sacrament_record)
    )

# Update a sacrament record
@sacraments_router.put("/{sacrament_record_id}", response_model=APIResponse)
async def update_sacrament_record(
    *,
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_record_id: int = FastAPIPath(..., title="The ID of the sacrament record to update"),
    sacrament_in: SacramentUpdate,
) -> Any:
    """Update a sacrament record for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing sacrament record
    sacrament_record = session.query(ParishionerSacrament).filter(
        and_(
            ParishionerSacrament.id == sacrament_record_id,
            ParishionerSacrament.parishioner_id == parishioner_id
        )
    ).first()
    
    if not sacrament_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sacrament record not found"
        )
    
    try:
        # Update only fields that were provided
        update_data = sacrament_in.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=ParSacramentRead.model_validate(sacrament_record)
            )
        
        # If sacrament_id is being updated
        if 'sacrament_id' in update_data:
            # Get the new sacrament
            new_sacrament = get_sacrament_by_type_or_id(session, update_data['sacrament_id'])
            update_data['sacrament_id'] = new_sacrament.id
            
            # If it's a once-only sacrament, check if the parishioner already has it
            if new_sacrament.once_only:
                existing_record = session.query(ParishionerSacrament).filter(
                    and_(
                        ParishionerSacrament.parishioner_id == parishioner_id,
                        ParishionerSacrament.sacrament_id == new_sacrament.id,
                        ParishionerSacrament.id != sacrament_record_id  # Exclude the current record
                    )
                ).first()
                
                if existing_record:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"This parishioner has already received the {new_sacrament.name} sacrament, which can only be received once."
                    )
        
        # Apply updates
        for field, value in update_data.items():
            setattr(sacrament_record, field, value)
            
        session.commit()
        session.refresh(sacrament_record)
        
        # Get sacrament name for message
        sacrament = session.query(Sacrament).filter(Sacrament.id == sacrament_record.sacrament_id).first()
        
        return APIResponse(
            message=f"{sacrament.name} sacrament record updated successfully",
            data=ParSacramentRead.model_validate(sacrament_record)
        )
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        
        # Check if this is a once-only sacrament violation
        if "once-only sacraments once" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This parishioner has already received this sacrament, which can only be received once."
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete a sacrament record
@sacraments_router.delete("/{sacrament_record_id}", response_model=APIResponse)
async def delete_sacrament_record(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_record_id: int = FastAPIPath(..., title="The ID of the sacrament record to delete"),
) -> Any:
    """Delete a sacrament record for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing sacrament record
    sacrament_record = session.query(ParishionerSacrament).filter(
        and_(
            ParishionerSacrament.id == sacrament_record_id,
            ParishionerSacrament.parishioner_id == parishioner_id
        )
    ).first()
    
    if not sacrament_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sacrament record not found"
        )
    
    try:
        # Get sacrament name for message before deletion
        sacrament = session.query(Sacrament).filter(Sacrament.id == sacrament_record.sacrament_id).first()
        sacrament_name = sacrament.name if sacrament else "Unknown"
        
        # Delete the sacrament record
        session.delete(sacrament_record)
        session.commit()
        
        # Refresh the parishioner to update relationship
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"{sacrament_name} sacrament record deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete all records for a specific sacrament type
@sacraments_router.delete("/type/{sacrament_type}", response_model=APIResponse)
async def delete_sacrament_records_by_type(
    parishioner_id: int,
    sacrament_type: SacramentType,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Delete all records for a specific sacrament type for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get the sacrament by type
    sacrament = session.query(Sacrament).filter(Sacrament.name == sacrament_type.value).first()
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sacrament not found: {sacrament_type.value}"
        )
    
    # Get existing sacrament records
    sacrament_records = session.query(ParishionerSacrament).filter(
        and_(
            ParishionerSacrament.parishioner_id == parishioner_id,
            ParishionerSacrament.sacrament_id == sacrament.id
        )
    ).all()
    
    if not sacrament_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{sacrament_type.value} sacrament records not found for this parishioner"
        )
    
    try:
        # Delete all sacrament records of this type
        count = len(sacrament_records)
        for record in sacrament_records:
            session.delete(record)
        
        session.commit()
        
        # Refresh the parishioner to update relationship
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"Deleted {count} {sacrament_type.value} sacrament records successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting sacraments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Batch update sacraments
@sacraments_router.post("/batch", response_model=APIResponse)
async def batch_update_sacraments(
    parishioner_id: int,
    batch_data: List[ParSacramentCreate],
    session: SessionDep,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Replace all existing sacraments of a parishioner with the new batch.
    For once-only sacraments, each parishioner can have at most one record per sacrament.
    For repeatable sacraments, multiple records are allowed.
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
        session.query(ParishionerSacrament).filter(
            ParishionerSacrament.parishioner_id == parishioner_id
        ).delete()
        
        # Process each sacrament in the batch
        once_only_sacrament_ids = set()
        new_sacrament_records = []
        
        for sacrament_data in batch_data:
            # Get the sacrament
            sacrament = get_sacrament_by_type_or_id(session, sacrament_data.sacrament_id)
            
            # Check for duplicates of once-only sacraments
            if sacrament.once_only and sacrament.id in once_only_sacrament_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate entry for once-only sacrament: {sacrament.name}"
                )
            
            # Only add to the set if it's a once-only sacrament
            if sacrament.once_only:
                once_only_sacrament_ids.add(sacrament.id)
            
            # Create new sacrament record
            new_record = ParishionerSacrament(
                parishioner_id=parishioner_id,
                sacrament_id=sacrament.id,
                date_received=sacrament_data.date_received,
                place=sacrament_data.place,
                minister=sacrament_data.minister,
                notes=sacrament_data.notes
            )
            
            session.add(new_record)
            new_sacrament_records.append(new_record)
        
        session.commit()
        
        # Refresh all new records to get their IDs
        for record in new_sacrament_records:
            session.refresh(record)
        
        # Refresh the parishioner to update relationships
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"Successfully replaced sacrament records for parishioner. Now has {len(new_sacrament_records)} sacrament records.",
            data=[ParSacramentRead.model_validate(record) for record in new_sacrament_records]
        )
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        
        # Check if this is a once-only sacrament violation
        if "once-only sacraments once" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch contains multiple entries for a once-only sacrament"
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error during batch update"
        )
    except ValueError as e:
        # Handle validation errors from the Pydantic model
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating sacraments for parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )