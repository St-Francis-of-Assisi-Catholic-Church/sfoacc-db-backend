
import logging
from sqlite3 import IntegrityError
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import SessionDep, CurrentUser
from app.models.place_of_worship import PlaceOfWorship
from app.schemas.place_of_worship import PlaceOfWorshipRead, PlaceOfWorshipUpdate
from app.schemas.common import APIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/all", response_model=APIResponse)
async def get_places_of_worship(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    search: Optional[str] = None
) -> Any:
    """
    Get all places of worship with optional search by name, description, or location.
    """
    try:
        # Build query
        query = session.query(PlaceOfWorship)
        
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    PlaceOfWorship.name.ilike(search_term),
                    PlaceOfWorship.description.ilike(search_term),
                    PlaceOfWorship.location.ilike(search_term)
                )
            )
            
        # Execute query
        places = query.all()
        
        # Convert to Pydantic models
        places_data = [
            PlaceOfWorshipRead.model_validate(place) 
            for place in places
        ]
        
        return APIResponse(
            message=f"Retrieved {len(places_data)} places of worship",
            data=places_data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving places of worship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving places of worship: {str(e)}"
        )

@router.get("/{place_id}", response_model=APIResponse)
async def get_place_of_worship_by_id(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    place_id: int
) -> Any:
    """
    Get a specific place of worship by ID.
    """
    try:
        # Query for specific place of worship
        place = session.query(PlaceOfWorship).filter(PlaceOfWorship.id == place_id).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Place of worship with ID {place_id} not found"
            )
            
        # Convert to Pydantic model
        place_data = PlaceOfWorshipRead.model_validate(place)
        
        return APIResponse(
            message=f"Retrieved place of worship: {place.name}",
            data=place_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving place of worship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving place of worship: {str(e)}"
        )

# Additional endpoints for app/api/routers/places_of_worship.py

@router.put("/{place_id}", response_model=APIResponse)
async def update_place_of_worship(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    place_id: int,
    place_update: PlaceOfWorshipUpdate
) -> Any:
    """
    Update a place of worship by ID.
    Only admins can update places of worship.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Query for specific place of worship
        place = session.query(PlaceOfWorship).filter(PlaceOfWorship.id == place_id).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Place of worship with ID {place_id} not found"
            )
        
        # Update only fields that were provided
        update_data = place_update.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=PlaceOfWorshipRead.model_validate(place)
            )
        
        # Apply updates
        for field, value in update_data.items():
            setattr(place, field, value)
        
        session.commit()
        session.refresh(place)
        
        return APIResponse(
            message=f"Place of worship '{place.name}' updated successfully",
            data=PlaceOfWorshipRead.model_validate(place)
        )
        
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A place of worship with this name already exists"
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating place of worship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating place of worship: {str(e)}"
        )

@router.delete("/{place_id}", response_model=APIResponse)
async def delete_place_of_worship(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    place_id: int
) -> Any:
    """
    Delete a place of worship by ID.
    Only admins can delete places of worship.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Query for specific place of worship
        place = session.query(PlaceOfWorship).filter(PlaceOfWorship.id == place_id).first()
        
        if not place:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Place of worship with ID {place_id} not found"
            )
        
        # Save the name for the response message
        place_name = place.name
        
        # Delete the place of worship
        session.delete(place)
        session.commit()
        
        return APIResponse(
            message=f"Place of worship '{place_name}' deleted successfully",
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting place of worship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting place of worship: {str(e)}"
        )