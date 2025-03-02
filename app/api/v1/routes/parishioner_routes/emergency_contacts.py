import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status, Depends, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import EmergencyContact, Parishioner, Occupation
from app.schemas.parishioner import EmergencyContactCreate, EmergencyContactRead, EmergencyContactUpdate, OccupationCreate, OccupationRead, OccupationUpdate, APIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

emergency_contacts_router = APIRouter()

# Maximum number of emergency contacts allowed per parishioner
MAX_EMERGENCY_CONTACTS = 3

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

# Create emergency contact for a parishioner
@emergency_contacts_router.post("/", response_model=APIResponse)
async def create_emergency_contact(
    *,
    parishioner_id: int,
    contact_in: EmergencyContactCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Create a new emergency contact for a parishioner (limit 3 per parishioner)."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Check if parishioner already has 3 emergency contacts
    existing_contacts_count = session.query(EmergencyContact).filter(
        EmergencyContact.parishioner_id == parishioner_id
    ).count()
    
    if existing_contacts_count >= MAX_EMERGENCY_CONTACTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parishioner already has the maximum of {MAX_EMERGENCY_CONTACTS} emergency contacts"
        )
    
    try:
        # Create new emergency contact
        new_contact = EmergencyContact(
            parishioner_id=parishioner_id,
            name=contact_in.name,
            relationship=contact_in.relationship,
            primary_phone=contact_in.primary_phone,
            alternative_phone=contact_in.alternative_phone
        )
        
        session.add(new_contact)
        session.commit()
        session.refresh(new_contact)
        
        # Also refresh the parishioner to make sure the relationship is loaded
        session.refresh(parishioner)
        
        return APIResponse(
            message="Emergency contact created successfully",
            data=EmergencyContactRead.model_validate(new_contact)
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
        logger.error(f"Error creating emergency contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get all emergency contacts for a parishioner
@emergency_contacts_router.get("/", response_model=APIResponse)
async def get_emergency_contacts(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all emergency contacts for a parishioner."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get emergency contacts
    contacts = session.query(EmergencyContact).filter(
        EmergencyContact.parishioner_id == parishioner_id
    ).all()
    
    return APIResponse(
        message=f"Retrieved {len(contacts)} emergency contacts",
        data=[EmergencyContactRead.model_validate(contact) for contact in contacts]
    )

# Get a specific emergency contact by ID
@emergency_contacts_router.get("/{contact_id}", response_model=APIResponse)
async def get_emergency_contact(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    contact_id: int = Path(..., title="The ID of the emergency contact to get"),
) -> Any:
    """Get a specific emergency contact by ID."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get the specific emergency contact
    contact = session.query(EmergencyContact).filter(
        EmergencyContact.id == contact_id,
        EmergencyContact.parishioner_id == parishioner_id
    ).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )
    
    return APIResponse(
        message="Emergency contact retrieved successfully",
        data=EmergencyContactRead.model_validate(contact)
    )

# Update an emergency contact
@emergency_contacts_router.put("/{contact_id}", response_model=APIResponse)
async def update_emergency_contact(
    *,
    parishioner_id: int,
    contact_id: int = Path(..., title="The ID of the emergency contact to update"),
    contact_in: EmergencyContactUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Update an emergency contact for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing emergency contact
    contact = session.query(EmergencyContact).filter(
        EmergencyContact.id == contact_id,
        EmergencyContact.parishioner_id == parishioner_id
    ).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )
    
    try:
        # Update only fields that were provided
        update_data = contact_in.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=EmergencyContactRead.model_validate(contact)
            )
            
        for field, value in update_data.items():
            setattr(contact, field, value)
            
        session.commit()
        session.refresh(contact)
        
        return APIResponse(
            message="Emergency contact updated successfully",
            data=EmergencyContactRead.model_validate(contact)
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating emergency contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete an emergency contact
@emergency_contacts_router.delete("/{contact_id}", response_model=APIResponse)
async def delete_emergency_contact(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    contact_id: int = Path(..., title="The ID of the emergency contact to delete"),
) -> Any:
    """Delete an emergency contact for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing emergency contact
    contact = session.query(EmergencyContact).filter(
        EmergencyContact.id == contact_id,
        EmergencyContact.parishioner_id == parishioner_id
    ).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found"
        )
    
    try:
        session.delete(contact)
        session.commit()
        
        # Refresh the parishioner to update relationship
        session.refresh(parishioner)
        
        return APIResponse(
            message="Emergency contact deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting emergency contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    

# Batch addd
@emergency_contacts_router.post("/batch", response_model=APIResponse)
async def batch_update_emergency_contacts(
    parishioner_id: int,
    contacts: list[EmergencyContactCreate],
    session: SessionDep,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Replace all existing emergency contacts of a parishioner with the new batch.
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
        # Delete all existing emergency contacts for this parishioner
        session.query(EmergencyContact).filter(
            EmergencyContact.parishioner_id == parishioner_id
        ).delete()
        
        # If no new contacts provided, just return empty list after clearing existing contacts
        if not contacts:
            session.commit()
            return APIResponse(
                message="All emergency contacts removed from parishioner, no new contacts provided",
                data=[]
            )
        
        # Check if the number of new contacts exceeds the maximum allowed
        if len(contacts) > MAX_EMERGENCY_CONTACTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum of {MAX_EMERGENCY_CONTACTS} emergency contacts allowed per parishioner"
            )
        
        # Create new emergency contacts
        new_contacts = []
        for contact_data in contacts:
            new_contact = EmergencyContact(
                parishioner_id=parishioner_id,
                name=contact_data.name,
                relationship=contact_data.relationship,
                primary_phone=contact_data.primary_phone,
                alternative_phone=contact_data.alternative_phone
            )
            session.add(new_contact)
            new_contacts.append(new_contact)
        
        session.commit()
        
        # Refresh all new contacts to get their IDs and any other database-generated values
        for contact in new_contacts:
            session.refresh(contact)
        
        # Refresh the parishioner to update relationships
        session.refresh(parishioner)
        
        return APIResponse(
            message=f"Successfully replaced emergency contacts for parishioner. Now has {len(new_contacts)} contacts.",
            data=[EmergencyContactRead.model_validate(contact) for contact in new_contacts]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating emergency contacts for parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
