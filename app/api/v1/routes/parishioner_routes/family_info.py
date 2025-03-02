import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status, Path as FastAPIPath
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import Parishioner, FamilyInfo, Child, ParentalStatus
from app.schemas.parishioner import (
    FamilyInfoBatch, FamilyInfoRead, FamilyInfoUpdate, ChildCreate,
    ChildRead, ChildUpdate, APIResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

family_info_router = APIRouter()

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


# Create or update family info for a parishioner
@family_info_router.post("/", response_model=APIResponse)
async def create_or_update_family_info(
    *,
    parishioner_id: int,
    family_info_in: FamilyInfoUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Create or update family information for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    try:
        # Check if family info already exists for this parishioner
        existing_family_info = session.query(FamilyInfo).filter(
            FamilyInfo.parishioner_id == parishioner_id
        ).first()
        
        # Process data from input
        family_info_data = family_info_in.model_dump(exclude_unset=True, exclude_none=True)
        children_data = family_info_data.pop('children', None)
        
        message = ""
        
        if existing_family_info:
            # Update existing family info
            for field, value in family_info_data.items():
                setattr(existing_family_info, field, value)
            
            # Ensure relationship is maintained
            existing_family_info.parishioner_ref = parishioner
            
            session.commit()
            session.refresh(existing_family_info)
            
            family_info = existing_family_info
            message = "Family information updated successfully"
        else:
            # Create new family info
            new_family_info = FamilyInfo(
                parishioner_id=parishioner_id,
                **family_info_data
            )
            
            # Add to session and set relationship
            session.add(new_family_info)
            parishioner.family_info_rel = new_family_info
            
            session.commit()
            session.refresh(new_family_info)
            
            family_info = new_family_info
            message = "Family information created successfully"
        
        # Handle children if provided
        if children_data:
            # Remove existing children and add new ones
            if existing_family_info:
                # Delete existing children
                session.query(Child).filter(
                    Child.family_info_id == family_info.id
                ).delete()
                session.commit()
            
            # Add new children
            for child_data in children_data:
                child = Child(
                    family_info_id=family_info.id,
                    name=child_data['name']
                )
                session.add(child)
            
            session.commit()
            
            # Refresh to get updated children
            session.refresh(family_info)
        
        # Also refresh the parishioner to ensure the relationship is loaded
        session.refresh(parishioner)
        
        # Need to explicitly load children for response
        family_info_with_children = session.query(FamilyInfo).options(
            joinedload(FamilyInfo.children_rel)
        ).filter(
            FamilyInfo.id == family_info.id
        ).first()
        
        return APIResponse(
            message=message,
            data=FamilyInfoRead.model_validate(family_info_with_children)
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
        logger.error(f"Error creating/updating family information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get family info for a parishioner
@family_info_router.get("/", response_model=APIResponse)
async def get_family_info(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get family information for a parishioner including children."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get family info with children loaded
    family_info = session.query(FamilyInfo).options(
        joinedload(FamilyInfo.children_rel)
    ).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        return APIResponse(
            message="No family information found for this parishioner",
            data=None
        )
    
    return APIResponse(
        message="Family information retrieved successfully",
        data=FamilyInfoRead.model_validate(family_info)
    )


# batch adding of pa
@family_info_router.post("/batch", response_model=APIResponse)
async def batch_update_family_info(
    parishioner_id: int,
    family_batch: Dict[str, Any],  # Use Dict instead of Pydantic model
    session: SessionDep,
    current_user: CurrentUser,
) -> APIResponse:
    """
    Replace all existing family information of a parishioner with the new data.
    Accepts a structured object with spouse, children, father, and mother information.
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
        # First, check if family info exists for this parishioner
        existing_family_info = session.query(FamilyInfo).filter(
            FamilyInfo.parishioner_id == parishioner_id
        ).first()
        
        # Delete existing family info (children will be deleted via CASCADE)
        if existing_family_info:
            session.delete(existing_family_info)
            session.commit()
        
        # Create new family info object
        new_family_info = FamilyInfo(parishioner_id=parishioner_id)
        
        # Handle spouse information
        if 'spouse' in family_batch:
            if family_batch['spouse']:
                spouse_data = family_batch['spouse']
                new_family_info.spouse_name = spouse_data.get('name')
                
                # Safely handle status value
                spouse_status = spouse_data.get('status')
                if spouse_status:
                    try:
                        new_family_info.spouse_status = ParentalStatus(spouse_status.lower())
                    except (ValueError, AttributeError):
                        new_family_info.spouse_status = ParentalStatus.UNKNOWN
                
                new_family_info.spouse_phone = spouse_data.get('phone')
            else:
                # If spouse is null/None, explicitly set spouse fields to None
                new_family_info.spouse_name = None
                new_family_info.spouse_status = None
                new_family_info.spouse_phone = None
        
        # Handle father information
        if 'father' in family_batch:
            if family_batch['father']:
                father_data = family_batch['father']
                new_family_info.father_name = father_data.get('name')
                
                # Safely handle status value
                father_status = father_data.get('status')
                if father_status:
                    try:
                        new_family_info.father_status = ParentalStatus(father_status.lower())
                    except (ValueError, AttributeError):
                        new_family_info.father_status = ParentalStatus.UNKNOWN
            else:
                # If father is null/None, explicitly set father fields to None
                new_family_info.father_name = None
                new_family_info.father_status = None
        
        # Handle mother information
        if 'mother' in family_batch:
            if family_batch['mother']:
                mother_data = family_batch['mother']
                new_family_info.mother_name = mother_data.get('name')
                
                # Safely handle status value
                mother_status = mother_data.get('status')
                if mother_status:
                    try:
                        new_family_info.mother_status = ParentalStatus(mother_status.lower())
                    except (ValueError, AttributeError):
                        new_family_info.mother_status = ParentalStatus.UNKNOWN
            else:
                # If mother is null/None, explicitly set mother fields to None
                new_family_info.mother_name = None
                new_family_info.mother_status = None
        
        # Add family info to session
        session.add(new_family_info)
        session.flush()  # Flush to get ID for children
        
        # Handle children information
        if 'children' in family_batch and family_batch['children']:
            for child_data in family_batch['children']:
                child = Child(
                    family_info_id=new_family_info.id,
                    name=child_data.get('name', '')
                )
                session.add(child)
        
        # Commit changes
        session.commit()
        
        # Refresh to get updated data
        session.refresh(new_family_info)
        
        # Build response in the same format as the request
        response_data = {
            "spouse": None,
            "children": [],
            "father": None,
            "mother": None
        }
        
        # Add spouse info to response
        if new_family_info.spouse_name:
            status_value = None
            if new_family_info.spouse_status:
                if hasattr(new_family_info.spouse_status, 'value'):
                    status_value = new_family_info.spouse_status.value
                else:
                    status_value = str(new_family_info.spouse_status)
                    
            response_data["spouse"] = {
                "name": new_family_info.spouse_name,
                "status": status_value,
                "phone": new_family_info.spouse_phone
            }
        
        # Add father info to response
        if new_family_info.father_name:
            status_value = None
            if new_family_info.father_status:
                if hasattr(new_family_info.father_status, 'value'):
                    status_value = new_family_info.father_status.value
                else:
                    status_value = str(new_family_info.father_status)
                    
            response_data["father"] = {
                "name": new_family_info.father_name,
                "status": status_value
            }
        
        # Add mother info to response
        if new_family_info.mother_name:
            status_value = None
            if new_family_info.mother_status:
                if hasattr(new_family_info.mother_status, 'value'):
                    status_value = new_family_info.mother_status.value
                else:
                    status_value = str(new_family_info.mother_status)
                    
            response_data["mother"] = {
                "name": new_family_info.mother_name,
                "status": status_value
            }
        
        # Add children to response
        children = session.query(Child).filter(
            Child.family_info_id == new_family_info.id
        ).all()
        
        response_data["children"] = [{"name": child.name} for child in children]
        
        return APIResponse(
            message="Family information updated successfully",
            data=response_data
        )
        
    except ValueError as e:
        session.rollback()
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating family information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    







