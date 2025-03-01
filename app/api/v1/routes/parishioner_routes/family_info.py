import logging
from typing import Any, List
from fastapi import APIRouter, HTTPException, status, Path as FastAPIPath
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import Parishioner, FamilyInfo, Child, ParentalStatus
from app.schemas.parishioner import (
    FamilyInfoRead, FamilyInfoUpdate, ChildCreate,
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

# Delete family info for a parishioner
@family_info_router.delete("/", response_model=APIResponse)
async def delete_family_info(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Delete family information for a parishioner, including all children."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get existing family info
    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family information not found for this parishioner"
        )
    
    try:
        # Clear the relationship first
        parishioner.family_info_rel = None
        
        # Children will be deleted automatically due to CASCADE delete in database
        # Delete the family info
        session.delete(family_info)
        session.commit()
        
        return APIResponse(
            message="Family information deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting family information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Add a child to family info
@family_info_router.post("/children", response_model=APIResponse)
async def add_child(
    *,
    parishioner_id: int,
    child_in: ChildCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Add a child to a parishioner's family information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get family info
    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        # Create family info if it doesn't exist
        family_info = FamilyInfo(parishioner_id=parishioner_id)
        session.add(family_info)
        session.commit()
        session.refresh(family_info)
    
    try:
        # Create new child
        new_child = Child(
            family_info_id=family_info.id,
            name=child_in.name
        )
        
        session.add(new_child)
        session.commit()
        session.refresh(new_child)
        
        return APIResponse(
            message="Child added successfully",
            data=ChildRead.model_validate(new_child)
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding child: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Update a child's information
@family_info_router.put("/children/{child_id}", response_model=APIResponse)
async def update_child(
    *,
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    child_id: int = FastAPIPath(..., title="The ID of the child to update"),
    child_in: ChildUpdate,
) -> Any:
    """Update a child's information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get family info
    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family information not found for this parishioner"
        )
    
    # Get the child
    child = session.query(Child).filter(
        Child.id == child_id,
        Child.family_info_id == family_info.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found"
        )
    
    try:
        # Update child
        child.name = child_in.name
        
        session.commit()
        session.refresh(child)
        
        return APIResponse(
            message="Child updated successfully",
            data=ChildRead.model_validate(child)
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating child: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Delete a child
@family_info_router.delete("/children/{child_id}", response_model=APIResponse)
async def delete_child(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    child_id: int = FastAPIPath(..., title="The ID of the child to delete"),
) -> Any:
    """Delete a child from a parishioner's family information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get family info
    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family information not found for this parishioner"
        )
    
    # Get the child
    child = session.query(Child).filter(
        Child.id == child_id,
        Child.family_info_id == family_info.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found"
        )
    
    try:
        # Delete child
        session.delete(child)
        session.commit()
        
        return APIResponse(
            message="Child deleted successfully",
            data=None
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting child: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get all children for a parishioner
@family_info_router.get("/children", response_model=APIResponse)
async def get_children(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all children for a parishioner."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get family info
    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        return APIResponse(
            message="No family information found for this parishioner",
            data=[]
        )
    
    # Get children
    children = session.query(Child).filter(
        Child.family_info_id == family_info.id
    ).all()
    
    return APIResponse(
        message=f"Retrieved {len(children)} children",
        data=[ChildRead.model_validate(child) for child in children]
    )

# Get a specific child
@family_info_router.get("/children/{child_id}", response_model=APIResponse)
async def get_child(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    child_id: int = FastAPIPath(..., title="The ID of the child to get"),
) -> Any:
    """Get a specific child by ID."""
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get family info
    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family information not found for this parishioner"
        )
    
    # Get the child
    child = session.query(Child).filter(
        Child.id == child_id,
        Child.family_info_id == family_info.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found"
        )
    
    return APIResponse(
        message="Child retrieved successfully",
        data=ChildRead.model_validate(child)
    )