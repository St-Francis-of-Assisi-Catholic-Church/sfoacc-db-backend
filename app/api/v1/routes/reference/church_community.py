import logging
from typing import Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser, ChurchUnitScope, require_permission, has_permission
from app.models.church_community import ChurchCommunity
from app.models.parishioner.core import Parishioner
from app.models.parish import ChurchUnit, ChurchUnitType
from app.schemas.church_community import ChurchCommunityRead, ChurchCommunityCreate, ChurchCommunityUpdate
from app.schemas.parishioner import ParishionerRead
from app.schemas.common import APIResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
_REQUIRE_ADMIN = require_permission("admin:all")

@router.get("/all", response_model=APIResponse)
async def get_church_communities(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    search: Optional[str] = None,
    church_unit_id: Optional[int] = Query(None, description="Filter by church unit"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    """
    Get all church communities with optional search by name or description.
    """
    try:
        # Build query
        query = session.query(ChurchCommunity)

        # Unit-scoped users always see only their unit; global admins can optionally filter
        if unit_scope is not None:
            query = query.filter(ChurchCommunity.church_unit_id == unit_scope)
        elif church_unit_id is not None:
            query = query.filter(ChurchCommunity.church_unit_id == church_unit_id)

        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ChurchCommunity.name.ilike(search_term),
                    ChurchCommunity.description.ilike(search_term)
                )
            )

        total = query.count()
        communities = query.offset(skip).limit(limit).all()

        # Convert to Pydantic models
        communities_data = [
            ChurchCommunityRead.model_validate(community)
            for community in communities
        ]

        return APIResponse(
            message=f"Retrieved {len(communities_data)} church communities",
            data={"total": total, "items": communities_data, "skip": skip, "limit": limit},
        )
        
    except Exception as e:
        logger.error(f"Error retrieving church communities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving church communities: {str(e)}"
        )

@router.post("", response_model=APIResponse, dependencies=[_REQUIRE_ADMIN])
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
    
    try:
        data = community_in.model_dump()
        # Default to main parish if no church_unit_id provided
        if not data.get("church_unit_id"):
            main_parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
            if main_parish:
                data["church_unit_id"] = main_parish.id

        community = ChurchCommunity(**data)
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

@router.get("/{community_id}/members", response_model=APIResponse)
async def get_community_members(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    community_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
) -> Any:
    """Get all parishioners belonging to a church community."""
    if not has_permission(current_user, "community:read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    community = session.query(ChurchCommunity).filter(ChurchCommunity.id == community_id).first()
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Church community with ID {community_id} not found"
        )

    try:
        query = session.query(Parishioner).filter(Parishioner.church_community_id == community_id)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Parishioner.first_name.ilike(term),
                    Parishioner.last_name.ilike(term),
                    Parishioner.other_names.ilike(term),
                    Parishioner.new_church_id.ilike(term),
                )
            )

        total = query.count()
        parishioners = query.offset(skip).limit(limit).all()

        return APIResponse(
            message=f"Retrieved {len(parishioners)} members of '{community.name}'",
            data={
                "total": total,
                "items": [ParishionerRead.model_validate(p) for p in parishioners],
                "skip": skip,
                "limit": limit,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving community members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving community members: {str(e)}"
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

@router.put("/{community_id}", response_model=APIResponse, dependencies=[_REQUIRE_ADMIN])
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

@router.delete("/{community_id}", response_model=APIResponse, dependencies=[_REQUIRE_ADMIN])
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