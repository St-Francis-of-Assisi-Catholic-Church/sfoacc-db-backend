import logging
from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.society import Society, SocietyLeadership, LeadershipRole, MeetingFrequency
from app.models.parishioner import Parishioner
from app.schemas.parishioner import APIResponse
from app.schemas.society import (
    SocietyCreate, 
    SocietyUpdate, 
    SocietyResponse, 
    SocietyDetailResponse,
    SocietyLeadershipCreate,
    SocietyLeadershipUpdate,
    SocietyLeadershipResponse,
    AddMembersRequest,
    RemoveMembersRequest,

)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Helper functions for reused logic
def get_all_society_leadership(
    session: Session, 
    society_id: int
) -> List[Dict[str, Any]]:
    # Query leadership with parishioner info
    leadership = session.query(
        SocietyLeadership,
        Parishioner.first_name,
        Parishioner.last_name,
        Parishioner.new_church_id,
        Parishioner.mobile_number
    ).join(
        Parishioner, SocietyLeadership.parishioner_id == Parishioner.id
    ).filter(
        SocietyLeadership.society_id == society_id
    ).all()
    
    result = []
    for l, first_name, last_name, church_id, contact in leadership:
        result.append({
            "id": l.id,
            "role": l.role,
            "custom_role": l.custom_role,
            "elected_date": l.elected_date,
            "end_date": l.end_date,
            "parishioner_id": l.parishioner_id,
            "parishioner_name": f"{first_name} {last_name}",
            "parishioner_church_id": church_id,
            "parishioner_contact": contact
        })
    
    return result

def get_society_members(
    session: Session, 
    society_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    society = session.query(Society).filter(Society.id == society_id).first()
    if not society:
        return []
    
    query = session.query(
        Parishioner.id,
        Parishioner.first_name,
        Parishioner.last_name,
        Parishioner.new_church_id,
        Parishioner.mobile_number,
        Parishioner.email_address,
        Parishioner.gender
    ).join(
        society.members.property.secondary,
        Parishioner.id == society.members.property.secondary.c.parishioner_id
    ).filter(
        society.members.property.secondary.c.society_id == society_id
    )
    
    if search:
        query = query.filter(
            (Parishioner.first_name.ilike(f"%{search}%")) | 
            (Parishioner.last_name.ilike(f"%{search}%")) |
            (Parishioner.new_church_id.ilike(f"%{search}%"))
        )
    
    members = query.offset(skip).limit(limit).all()
    
    result = []
    for id, first_name, last_name, church_id, mobile, email, gender in members:
        result.append({
            "id": id,
            "name": f"{first_name} {last_name}",
            "church_id": church_id,
            "mobile": mobile,
            "email": email,
            "gender": gender
        })
    
    return result

# Society endpoints
@router.post("", response_model=APIResponse, status_code=201)
async def create_new_society(
    *,
    session: SessionDep,
    society: SocietyCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Create a new society with all necessary details.
    
    Returns the created society instance.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Create society from input data
        db_society = Society(
            name=society.name,
            description=society.description,
            date_inaugurated=society.date_inaugurated,
            meeting_frequency=society.meeting_frequency,
            meeting_day=society.meeting_day,
            meeting_time=society.meeting_time,
            meeting_venue=society.meeting_venue
        )
        
        session.add(db_society)
        session.commit()
        session.refresh(db_society)
        
        return APIResponse(
            message="Society created successfully",
            data=SocietyResponse.model_validate(db_society)
        )
    
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate society name."
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating society: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("", response_model=APIResponse)
async def read_societies(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None
) -> Any:
    """
    Get list of all societies with pagination and optional search.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Build the query
        query = session.query(Society)
        
        if search:
            query = query.filter(Society.name.ilike(f"%{search}%"))
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        societies = query.offset(skip).limit(limit).all()
        
        # Enhance with member counts and leadership info
        result = []
        for society in societies:
            society_dict = {
                "id": society.id,
                "name": society.name,
                "description": society.description,
                "date_inaugurated": society.date_inaugurated,
                "meeting_frequency": society.meeting_frequency,
                "meeting_day": society.meeting_day,
                "meeting_time": society.meeting_time,
                "meeting_venue": society.meeting_venue,
                "created_at": society.created_at,
                "updated_at": society.updated_at,
                "members_count": len(society.members),
                "leadership": get_all_society_leadership(session, society.id)
            }
            result.append(society_dict)
        
        return APIResponse(
            message=f"Retrieved {len(result)} societies",
            data={
                "total": total_count,
                "societies": result,
                "skip": skip,
                "limit": limit
            }
        )
    
    except Exception as e:
        logger.error(f"Error fetching societies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{society_id}", response_model=APIResponse)
async def read_society(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int = Path(..., title="The ID of the society to get")
) -> Any:
    """
    Get detailed information about a specific society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        society = session.query(Society).filter(Society.id == society_id).first()
        
        if society is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        # Get leadership
        leadership = get_all_society_leadership(session, society_id)
        
        # Get members count
        members_count = session.query(func.count(society.members.property.secondary.c.parishioner_id)).filter(
            society.members.property.secondary.c.society_id == society_id
        ).scalar()
        
        # Get basic member info (limited to 10 for overview)
        members = get_society_members(session, society_id, limit=10)
        
        result = {
            "id": society.id,
            "name": society.name,
            "description": society.description,
            "date_inaugurated": society.date_inaugurated,
            "meeting_frequency": society.meeting_frequency,
            "meeting_day": society.meeting_day,
            "meeting_time": society.meeting_time,
            "meeting_venue": society.meeting_venue,
            "created_at": society.created_at,
            "updated_at": society.updated_at,
            "members_count": members_count,
            "leadership": leadership,
            "members": members
        }
        
        return APIResponse(
            message="Society retrieved successfully",
            data=SocietyDetailResponse.model_validate(result)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching society: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{society_id}", response_model=APIResponse)
async def update_existing_society(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    society_update: SocietyUpdate
) -> Any:
    """
    Update an existing society's information.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        db_society = session.query(Society).filter(Society.id == society_id).first()
        
        if not db_society:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        # Only update fields that were provided
        update_data = society_update.model_dump(exclude_unset=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=SocietyResponse.model_validate(db_society)
            )
        
        for field, value in update_data.items():
            setattr(db_society, field, value)
        
        session.commit()
        session.refresh(db_society)
        
        # Prepare response with additional info
        result = {
            "id": db_society.id,
            "name": db_society.name,
            "description": db_society.description,
            "date_inaugurated": db_society.date_inaugurated,
            "meeting_frequency": db_society.meeting_frequency,
            "meeting_day": db_society.meeting_day,
            "meeting_time": db_society.meeting_time,
            "meeting_venue": db_society.meeting_venue,
            "created_at": db_society.created_at,
            "updated_at": db_society.updated_at,
            "members_count": len(db_society.members),
            "leadership": get_all_society_leadership(session, society_id)
        }
        
        return APIResponse(
            message="Society updated successfully",
            data=SocietyResponse.model_validate(result)
        )
    
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry."
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating society: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{society_id}", status_code=204)
async def delete_existing_society(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int
) -> None:
    """
    Delete an existing society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        db_society = session.query(Society).filter(Society.id == society_id).first()
        
        if not db_society:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        session.delete(db_society)
        session.commit()
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting society: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Society Leadership endpoints
@router.post("/{society_id}/leadership", response_model=APIResponse)
async def add_leadership_position(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    leadership: SocietyLeadershipCreate
) -> Any:
    """
    Add a leadership position to a society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if society exists
        society = session.query(Society).filter(Society.id == society_id).first()
        if not society:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        # Check if parishioner exists
        parishioner = session.query(Parishioner).filter(Parishioner.id == leadership.parishioner_id).first()
        if not parishioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parishioner not found"
            )
        
        # Create leadership position
        db_leadership = SocietyLeadership(
            society_id=society_id,
            parishioner_id=leadership.parishioner_id,
            role=leadership.role,
            custom_role=leadership.custom_role if leadership.role == LeadershipRole.OTHER else None,
            elected_date=leadership.elected_date,
            end_date=leadership.end_date
        )
        
        session.add(db_leadership)
        session.commit()
        session.refresh(db_leadership)
        
        # Fetch additional data for response
        leadership_data = get_all_society_leadership(session, society_id)
        for item in leadership_data:
            if item["id"] == db_leadership.id:
                return APIResponse(
                    message="Leadership position added successfully",
                    data=SocietyLeadershipResponse.model_validate(item)
                )
        
        # Fallback in case the data isn't found in the query result
        return APIResponse(
            message="Leadership position added successfully",
            data=SocietyLeadershipResponse.model_validate(db_leadership)
        )
    
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry."
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding leadership position: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{society_id}/leadership", response_model=APIResponse)
async def get_leadership(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int
) -> Any:
    """
    Get all leadership positions for a society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        society = session.query(Society).filter(Society.id == society_id).first()
        if society is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        leadership_data = get_all_society_leadership(session, society_id)
        
        return APIResponse(
            message=f"Retrieved {len(leadership_data)} leadership positions",
            data=leadership_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching leadership positions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{society_id}/leadership/{leadership_id}", response_model=APIResponse)
async def update_leadership_position(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    leadership_id: int,
    leadership_update: SocietyLeadershipUpdate
) -> Any:
    """
    Update a leadership position for a society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        db_leadership = session.query(SocietyLeadership).filter(
            SocietyLeadership.society_id == society_id,
            SocietyLeadership.id == leadership_id
        ).first()
        
        if not db_leadership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leadership position not found"
            )
        
        update_data = leadership_update.model_dump(exclude_unset=True)
        
        # If parishioner_id is updated, check if the parishioner exists
        if "parishioner_id" in update_data:
            parishioner = session.query(Parishioner).filter(Parishioner.id == update_data["parishioner_id"]).first()
            if not parishioner:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parishioner not found"
                )
        
        # If role is updated to OTHER, ensure custom_role is set
        if "role" in update_data and update_data["role"] == LeadershipRole.OTHER:
            if "custom_role" not in update_data or not update_data["custom_role"]:
                update_data["custom_role"] = "Other Role"
        
        # Apply updates
        for key, value in update_data.items():
            setattr(db_leadership, key, value)
        
        session.commit()
        session.refresh(db_leadership)
        
        # Fetch additional data for response
        leadership_data = get_all_society_leadership(session, society_id)
        for item in leadership_data:
            if item["id"] == leadership_id:
                return APIResponse(
                    message="Leadership position updated successfully",
                    data=SocietyLeadershipResponse.model_validate(item)
                )
        
        # Fallback
        return APIResponse(
            message="Leadership position updated successfully",
            data=SocietyLeadershipResponse.model_validate(db_leadership)
        )
    
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry."
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating leadership position: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{society_id}/leadership/{leadership_id}", status_code=204)
async def delete_leadership_position(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    leadership_id: int
) -> None:
    """
    Delete a leadership position from a society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        db_leadership = session.query(SocietyLeadership).filter(
            SocietyLeadership.society_id == society_id,
            SocietyLeadership.id == leadership_id
        ).first()
        
        if not db_leadership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leadership position not found"
            )
        
        session.delete(db_leadership)
        session.commit()
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting leadership position: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Society Membership endpoints
@router.post("/{society_id}/members", response_model=APIResponse)
async def add_members_to_society(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    members: AddMembersRequest
) -> Any:
    """
    Add members to a society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        society = session.query(Society).filter(Society.id == society_id).first()
        if not society:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        added = 0
        existing = 0
        not_found = 0
        
        for p_id in members.parishioner_ids:
            parishioner = session.query(Parishioner).filter(Parishioner.id == p_id).first()
            if not parishioner:
                not_found += 1
                continue
            
            # Check if already a member
            is_member = session.query(society.members).filter(Parishioner.id == p_id).first()
            if is_member:
                existing += 1
                continue
            
            # Add to society
            society.members.append(parishioner)
            added += 1
        
        session.commit()
        
        return APIResponse(
            message="Members added to society",
            data={
                "success": True,
                "added": added,
                "existing": existing,
                "not_found": not_found
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding members to society: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{society_id}/members", response_model=APIResponse)
async def remove_members_from_society(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    members: RemoveMembersRequest
) -> Any:
    """
    Remove members from a society.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        society = session.query(Society).filter(Society.id == society_id).first()
        if not society:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        removed = 0
        not_member = 0
        
        for p_id in members.parishioner_ids:
            parishioner = session.query(Parishioner).filter(Parishioner.id == p_id).first()
            if not parishioner:
                not_member += 1
                continue
            
            # Check if a member
            is_member = parishioner in society.members
            if not is_member:
                not_member += 1
                continue
            
            # Remove from society
            society.members.remove(parishioner)
            removed += 1
        
        session.commit()
        
        return APIResponse(
            message="Members removed from society",
            data={
                "success": True,
                "removed": removed,
                "not_member": not_member
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error removing members from society: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{society_id}/members", response_model=APIResponse)
async def get_members_of_society(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None
) -> Any:
    """
    Get members of a society with pagination and optional search.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        society = session.query(Society).filter(Society.id == society_id).first()
        if society is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Society not found"
            )
        
        members = get_society_members(session, society_id, skip, limit, search)
        
        return APIResponse(
            message=f"Retrieved {len(members)} society members",
            data={
                "total": len(society.members),
                "items": members,
                "skip": skip,
                "limit": limit
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching society members: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )