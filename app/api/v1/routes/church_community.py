import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.church_community import ChurchCommunity
from app.schemas.church_community import ChurchCommunityRead, ChurchCommunityCreate, ChurchCommunityUpdate
from app.schemas.common import APIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=APIResponse)
async def get_church_communities(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    search: Optional[str] = None
) -> Any:
    """
    Get all church communities with optional search by name or description.
    """
    try:
        # Build query
        query = session.query(ChurchCommunity)
        
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ChurchCommunity.name.ilike(search_term),
                    ChurchCommunity.description.ilike(search_term)
                )
            )
            
        # Execute query
        communities = query.all()
        
        # Convert to Pydantic models
        communities_data = [
            ChurchCommunityRead.model_validate(community) 
            for community in communities
        ]
        
        return APIResponse(
            message=f"Retrieved {len(communities_data)} church communities",
            data=communities_data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving church communities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving church communities: {str(e)}"
        )

@router.post("/", response_model=APIResponse)
async def create_church_community(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    community_in: ChurchCommunityCreate
) -> Any:
    """
    Create a new church community.
    Only admins can create church communities.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Create new church community
        community = ChurchCommunity(**community_in.model_dump())
        session.add(community)
        session.commit()
        session.refresh(community)
        
        return APIResponse(
            message=f"Church community '{community.name}' created successfully",
            data=ChurchCommunityRead.model_validate(community)
        )
        
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A church community with this name already exists"
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating church community: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating church community: {str(e)}"
        )

@router.get("/{community_id}", response_model=APIResponse)
async def get_church_community_by_id(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    community_id: int
) -> Any:
    """
    Get a specific church community by ID.
    """
    try:
        # Query for specific church community
        community = session.query(ChurchCommunity).filter(ChurchCommunity.id == community_id).first()
        
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Church community with ID {community_id} not found"
            )
            
        # Convert to Pydantic model
        community_data = ChurchCommunityRead.model_validate(community)
        
        return APIResponse(
            message=f"Retrieved church community: {community.name}",
            data=community_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving church community: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving church community: {str(e)}"
        )

@router.put("/{community_id}", response_model=APIResponse)
async def update_church_community(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    community_id: int,
    community_update: ChurchCommunityUpdate
) -> Any:
    """
    Update a church community by ID.
    Only admins can update church communities.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Query for specific church community
        community = session.query(ChurchCommunity).filter(ChurchCommunity.id == community_id).first()
        
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Church community with ID {community_id} not found"
            )
        
        # Update only fields that were provided
        update_data = community_update.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=ChurchCommunityRead.model_validate(community)
            )
        
        # Apply updates
        for field, value in update_data.items():
            setattr(community, field, value)
        
        session.commit()
        session.refresh(community)
        
        return APIResponse(
            message=f"Church community '{community.name}' updated successfully",
            data=ChurchCommunityRead.model_validate(community)
        )
        
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A church community with this name already exists"
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating church community: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating church community: {str(e)}"
        )

@router.delete("/{community_id}", response_model=APIResponse)
async def delete_church_community(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    community_id: int
) -> Any:
    """
    Delete a church community by ID.
    Only admins can delete church communities.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Query for specific church community
        community = session.query(ChurchCommunity).filter(ChurchCommunity.id == community_id).first()
        
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Church community with ID {community_id} not found"
            )
        
        # Save the name for the response message
        community_name = community.name
        
        # Delete the church community
        session.delete(community)
        session.commit()
        
        return APIResponse(
            message=f"Church community '{community_name}' deleted successfully",
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting church community: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting church community: {str(e)}"
        )