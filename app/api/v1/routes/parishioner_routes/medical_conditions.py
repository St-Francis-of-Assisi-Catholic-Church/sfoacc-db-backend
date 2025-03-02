import logging
from typing import Any, List
from fastapi import APIRouter, HTTPException, status, Path as FastAPIPath
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import Parishioner, MedicalCondition
from app.schemas.parishioner import MedicalConditionCreate, MedicalConditionRead, MedicalConditionUpdate, APIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

medical_conditions_router = APIRouter()

# Maximum number of medical conditions allowed per parishioner
MAX_MEDICAL_CONDITIONS = 5

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

# Create medical condition for a parishioner
@medical_conditions_router.post("/", response_model=APIResponse)
async def create_medical_condition(
    *,
    parishioner_id: int,
    condition_in: MedicalConditionCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Create a new medical condition for a parishioner (limit 5 per parishioner)."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Check if parishioner already has 5 medical conditions
    existing_conditions_count = session.query(MedicalCondition).filter(
        MedicalCondition.parishioner_id == parishioner_id
    ).count()
    
    if existing_conditions_count >= MAX_MEDICAL_CONDITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parishioner already has the maximum of {MAX_MEDICAL_CONDITIONS} medical conditions"
        )
    
    try:
        # Create new medical condition
        new_condition = MedicalCondition(
            parishioner_id=parishioner_id,
            condition=condition_in.condition,
            notes=condition_in.notes
        )
        
        session.add(new_condition)
        session.commit()
        session.refresh(new_condition)
        
        # Also refresh the parishioner to make sure the relationship is loaded
        session.refresh(parishioner)
        
        return APIResponse(
            message="Medical condition created successfully",
            data=MedicalConditionRead.model_validate(new_condition)
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
        logger.error(f"Error creating medical condition: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get all medical conditions for a parishioner
@medical_conditions_router.get("/", response_model=APIResponse)
async def get_medical_conditions(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all medical conditions for a parishioner."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get medical conditions
    conditions = session.query(MedicalCondition).filter(
        MedicalCondition.parishioner_id == parishioner_id
    ).all()
    
    return APIResponse(
        message=f"Retrieved {len(conditions)} medical conditions",
        data=[MedicalConditionRead.model_validate(condition) for condition in conditions]
    )

# Get a specific medical condition by ID
@medical_conditions_router.get("/{condition_id}", response_model=APIResponse)
async def get_medical_condition(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    condition_id: int = FastAPIPath(..., title="The ID of the medical condition to get"),
) -> Any:
    """Get a specific medical condition by ID."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get the specific medical condition
    condition = session.query(MedicalCondition).filter(
        MedicalCondition.id == condition_id,
        MedicalCondition.parishioner_id == parishioner_id
    ).first()
    
    if not condition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical condition not found"
        )
    
    return APIResponse(
        message="Medical condition retrieved successfully",
        data=MedicalConditionRead.model_validate(condition)
    )

# Update a medical condition
@medical_conditions_router.put("/{condition_id}", response_model=APIResponse)
async def update_medical_condition(
    *,
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    condition_id: int = FastAPIPath(..., title="The ID of the medical condition to update"),
    condition_in: MedicalConditionUpdate,
) -> Any:
    """Update a medical condition for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing medical condition
    condition = session.query(MedicalCondition).filter(
        MedicalCondition.id == condition_id,
        MedicalCondition.parishioner_id == parishioner_id
    ).first()
    
    if not condition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical condition not found"
        )
    
    try:
        # Update only fields that were provided
        update_data = condition_in.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=MedicalConditionRead.model_validate(condition)
            )
            
        for field, value in update_data.items():
            setattr(condition, field, value)
            
        session.commit()
        session.refresh(condition)
        
        return APIResponse(
            message="Medical condition updated successfully",
            data=MedicalConditionRead.model_validate(condition)
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating medical condition: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete a medical condition
@medical_conditions_router.delete("/{condition_id}", response_model=APIResponse)
async def delete_medical_condition(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    condition_id: int = FastAPIPath(..., title="The ID of the medical condition to delete"),
) -> Any:
    """Delete a medical condition for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing medical condition
    condition = session.query(MedicalCondition).filter(
        MedicalCondition.id == condition_id,
        MedicalCondition.parishioner_id == parishioner_id
    ).first()
    
    if not condition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical condition not found"
        )
    
    try:
        session.delete(condition)
        session.commit()
        
        # Refresh the parishioner to update relationship
        session.refresh(parishioner)
        
        return APIResponse(
            message="Medical condition deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting medical condition: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Add the following endpoint to the medical_conditions_router

@medical_conditions_router.post("/batch", response_model=APIResponse)
async def batch_update_medical_conditions(
    parishioner_id: int,
    batch_data: List[MedicalConditionCreate],
    session: SessionDep,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Replace all existing medical conditions of a parishioner with the new batch.
    Maximum of 5 medical conditions allowed per parishioner.
    Each condition must be unique for the parishioner.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Validate batch size doesn't exceed maximum allowed
    if len(batch_data) > MAX_MEDICAL_CONDITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {MAX_MEDICAL_CONDITIONS} medical conditions allowed per parishioner"
        )
    
    # Check for duplicate conditions in the request
    condition_names = [condition.condition.lower().strip() for condition in batch_data]
    if len(condition_names) != len(set(condition_names)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate medical conditions detected in the request"
        )
    
    # Get existing conditions to check for duplicates
    existing_conditions = session.query(MedicalCondition).filter(
        MedicalCondition.parishioner_id == parishioner_id
    ).all()
    
    existing_condition_names = [condition.condition.lower().strip() for condition in existing_conditions]
    
    # Check if any requested conditions already exist
    duplicate_conditions = []
    for condition in batch_data:
        if condition.condition.lower().strip() in existing_condition_names:
            duplicate_conditions.append(condition.condition)
    
    if duplicate_conditions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following medical conditions already exist for this parishioner: {', '.join(duplicate_conditions)}"
        )
    
    try:
        
        # Create new medical conditions
        new_conditions = []
        for condition_data in batch_data:
            new_condition = MedicalCondition(
                parishioner_id=parishioner_id,
                condition=condition_data.condition,
                notes=condition_data.notes
            )
            session.add(new_condition)
            new_conditions.append(new_condition)
        
        session.commit()
        
        # Refresh all new conditions to get their IDs and any other database-generated values
        for condition in new_conditions:
            session.refresh(condition)
        
        # Refresh the parishioner to update relationships
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"Successfully replaced medical conditions for parishioner. Now has {len(new_conditions)} medical conditions.",
            data=[MedicalConditionRead.model_validate(condition) for condition in new_conditions]
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
        logger.error(f"Error updating medical conditions for parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )