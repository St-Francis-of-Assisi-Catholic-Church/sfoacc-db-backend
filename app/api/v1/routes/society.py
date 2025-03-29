import logging
from typing import Any, List, Optional, Dict, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks
from sqlalchemy import func, Column, ForeignKey, String, Boolean, Table, DateTime, text
from sqlalchemy.orm import Session, joinedload, relationship
from sqlalchemy.exc import IntegrityError
from datetime import datetime

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
    UpdateMemberStatusRequest,
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
    
    # Find the association table name from the relationship metadata
    # This approach is more robust than directly accessing property.secondary
    association_table = Society.members.prop.secondary
    
    query = session.query(
        Parishioner.id,
        Parishioner.first_name,
        Parishioner.last_name,
        Parishioner.new_church_id,
        Parishioner.mobile_number,
        Parishioner.email_address,
        Parishioner.gender,
        association_table.c.status.label('membership_status'),
        association_table.c.join_date.label('join_date')
    ).join(
        association_table,
        Parishioner.id == association_table.c.parishioner_id
    ).filter(
        association_table.c.society_id == society_id
    )
    
    if search:
        query = query.filter(
            (Parishioner.first_name.ilike(f"%{search}%")) | 
            (Parishioner.last_name.ilike(f"%{search}%")) |
            (Parishioner.new_church_id.ilike(f"%{search}%"))
        )
    
    members = query.offset(skip).limit(limit).all()
    
    result = []
    for row in members:
        # Extract all fields from the query result
        id, first_name, last_name, church_id, mobile, email, gender, membership_status, join_date = row
        
        result.append({
            "id": id,
            "name": f"{first_name} {last_name}",
            "church_id": church_id,
            "mobile": mobile,
            "email": email, 
            "gender": gender,
            "membership_status": membership_status or "active",  # Default to active if null
            "join_date": join_date
        })
    
    return result

# Convert Society model to dict for Pydantic schemas
def society_to_dict(society, session=None, include_leadership=True, include_members=False, member_limit=10):
    # Get members count using a query instead of len()
    association_table = Society.members.prop.secondary
    members_count = 0
    
    if session:
        members_count = session.query(func.count(association_table.c.parishioner_id))\
            .filter(association_table.c.society_id == society.id)\
            .scalar() or 0
            
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
        "members_count": members_count
    }
    
    if include_leadership and session:
        result["leadership"] = get_all_society_leadership(session, society.id)
    else:
        result["leadership"] = []
    
    if include_members and session:
        result["members"] = get_society_members(session, society.id, limit=member_limit)
    
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
        # Check if society with this name already exists
        existing_society = session.query(Society).filter(
            Society.name == society.name
        ).first()
        
        if existing_society:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A society with this name already exists"
            )
        
        # Convert to dict first to prevent field issues
        society_data = society.model_dump(exclude_unset=True)
        
        # Create society from input data 
        db_society = Society(**society_data)
        
        session.add(db_society)
        session.commit()
        session.refresh(db_society)
        
        # Convert to dict for Pydantic model
        society_dict = society_to_dict(db_society, session)
        
        return APIResponse(
            message="Society created successfully",
            data=society_dict  # Use dict instead of directly passing the ORM model
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
        
        # Convert each society to dict
        result = [society_to_dict(society, session) for society in societies]
        
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
        
        # Convert to dict with members included
        society_dict = society_to_dict(society, session, include_members=True)
        
        return APIResponse(
            message="Society retrieved successfully",
            data=society_dict
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
            society_dict = society_to_dict(db_society, session)
            return APIResponse(
                message="No fields to update",
                data=society_dict
            )
        
        for field, value in update_data.items():
            setattr(db_society, field, value)
        
        session.commit()
        session.refresh(db_society)
        
        # Convert to dict for response
        society_dict = society_to_dict(db_society, session)
        
        return APIResponse(
            message="Society updated successfully",
            data=society_dict
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
        
        # Check if the parishioner is already a leader in this society
        existing_leadership = session.query(SocietyLeadership).filter(
            SocietyLeadership.society_id == society_id,
            SocietyLeadership.parishioner_id == leadership.parishioner_id,
            SocietyLeadership.role == leadership.role
        ).first()
        
        if existing_leadership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This parishioner already has this leadership role in the society"
            )
        
        # Automatically add the parishioner as a member if they're not already
        # Check if already a member
        association_table = Society.members.prop.secondary
        is_member = session.query(association_table).filter(
            association_table.c.society_id == society_id,
            association_table.c.parishioner_id == leadership.parishioner_id
        ).first()
        
        if not is_member:
            # Add to society with status and join_date
            now = datetime.now()
            
            # Use direct SQL insert for the association table to include status and join_date
            stmt = association_table.insert().values(
                society_id=society_id,
                parishioner_id=leadership.parishioner_id,
                status="active",
                join_date=now
            )
            session.execute(stmt)
            logger.info(f"Added parishioner {leadership.parishioner_id} as a member when adding as a leader")
        
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
                    data=item  # Use dict directly
                )
        
        # Fallback in case the data isn't found in the query result
        return APIResponse(
            message="Leadership position added successfully",
            data={
                "id": db_leadership.id,
                "role": db_leadership.role,
                "custom_role": db_leadership.custom_role,
                "elected_date": db_leadership.elected_date,
                "end_date": db_leadership.end_date,
                "parishioner_id": db_leadership.parishioner_id,
                "parishioner_name": f"{parishioner.first_name} {parishioner.last_name}",
                "parishioner_church_id": parishioner.new_church_id,
                "parishioner_contact": parishioner.mobile_number
            }
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
                
            # Get society
            society = session.query(Society).filter(Society.id == society_id).first()
            
            # Ensure the new leader is also a member of the society
            association_table = Society.members.prop.secondary
            is_member = session.query(association_table).filter(
                association_table.c.society_id == society_id,
                association_table.c.parishioner_id == update_data["parishioner_id"]
            ).first()
            
            if not is_member:
                # Add to society with status and join_date
                now = datetime.now()
                
                # Use direct SQL insert for the association table to include status and join_date
                stmt = association_table.insert().values(
                    society_id=society_id,
                    parishioner_id=update_data["parishioner_id"],
                    status="active",
                    join_date=now
                )
                session.execute(stmt)
                logger.info(f"Added parishioner {update_data['parishioner_id']} as a member when updating leadership")
        
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
                    data=item  # Use dict directly
                )
        
        # Fallback - get parishioner info for response
        parishioner = session.query(Parishioner).filter(Parishioner.id == db_leadership.parishioner_id).first()
        
        return APIResponse(
            message="Leadership position updated successfully",
            data={
                "id": db_leadership.id,
                "role": db_leadership.role,
                "custom_role": db_leadership.custom_role,
                "elected_date": db_leadership.elected_date,
                "end_date": db_leadership.end_date,
                "parishioner_id": db_leadership.parishioner_id,
                "parishioner_name": f"{parishioner.first_name} {parishioner.last_name}",
                "parishioner_church_id": parishioner.new_church_id,
                "parishioner_contact": parishioner.mobile_number
            }
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
    
    Members are added with 'active' status by default and the current date as join date.
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
        
        # Get the association table
        association_table = Society.members.prop.secondary
        
        added = 0
        existing = 0
        not_found = 0
        
        for p_id in members.parishioner_ids:
            parishioner = session.query(Parishioner).filter(Parishioner.id == p_id).first()
            if not parishioner:
                not_found += 1
                continue
            
            # Check if already a member
            is_member = session.query(association_table).filter(
                association_table.c.society_id == society_id,
                association_table.c.parishioner_id == p_id
            ).first()
            
            if is_member:
                existing += 1
                continue
            
            # Add to society with status and join_date
            now = datetime.now()
            
            # Use direct SQL insert for the association table to include status and join_date
            stmt = association_table.insert().values(
                society_id=society_id,
                parishioner_id=p_id,
                status="active",
                join_date=now
            )
            session.execute(stmt)
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
        
        association_table = Society.members.prop.secondary
        removed = 0
        not_member = 0
        
        for p_id in members.parishioner_ids:
            parishioner = session.query(Parishioner).filter(Parishioner.id == p_id).first()
            if not parishioner:
                not_member += 1
                continue
            
            # Check if a member using the association table
            is_member = session.query(association_table).filter(
                association_table.c.society_id == society_id,
                association_table.c.parishioner_id == p_id
            ).first()
            
            if not is_member:
                not_member += 1
                continue
            
            # Delete the membership row
            stmt = association_table.delete().where(
                association_table.c.society_id == society_id,
                association_table.c.parishioner_id == p_id
            )
            session.execute(stmt)
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
    search: Optional[str] = None,
    status: Optional[str] = Query(None, description="Filter by membership status (active, inactive, suspended, pending)")
) -> Any:
    """
    Get members of a society with pagination and optional search and status filtering.
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
        
        # Get the association table for counting
        association_table = Society.members.prop.secondary
        
        # Build the count query with filters
        count_query = session.query(func.count(association_table.c.parishioner_id))\
            .filter(association_table.c.society_id == society_id)
            
        # Apply status filter to count if provided
        if status:
            count_query = count_query.filter(association_table.c.status == status)
            
        total_count = count_query.scalar() or 0
        
        # Get members with optional filters
        members = get_society_members(session, society_id, skip, limit, search)
        
        # Filter by status if provided
        if status:
            members = [m for m in members if m["membership_status"] == status]
        
        return APIResponse(
            message=f"Retrieved {len(members)} society members",
            data={
                "total": total_count,
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

@router.put("/{society_id}/members/{parishioner_id}/status", response_model=APIResponse)
async def update_member_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    parishioner_id: int,
    status_update: UpdateMemberStatusRequest
) -> Any:
    """
    Update a member's status in the society.
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
        parishioner = session.query(Parishioner).filter(Parishioner.id == parishioner_id).first()
        if not parishioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parishioner not found"
            )
        
        # Get the association table
        association_table = Society.members.prop.secondary
        
        # Check if parishioner is a member of the society
        membership = session.query(association_table).filter(
            association_table.c.society_id == society_id,
            association_table.c.parishioner_id == parishioner_id
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parishioner is not a member of this society"
            )
        
        # Update the status
        stmt = association_table.update().where(
            association_table.c.society_id == society_id,
            association_table.c.parishioner_id == parishioner_id
        ).values(
            status=status_update.status
        )
        
        session.execute(stmt)
        session.commit()
        
        return APIResponse(
            message=f"Member status updated to {status_update.status}",
            data={
                "society_id": society_id,
                "parishioner_id": parishioner_id,
                "parishioner_name": f"{parishioner.first_name} {parishioner.last_name}",
                "status": status_update.status
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating member status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{society_id}/members/status/{status}", response_model=APIResponse)
async def get_members_by_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    society_id: int,
    status: Literal["active", "inactive", "suspended", "pending"],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """
    Get society members filtered by status.
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
        
        # Get the association table
        association_table = Society.members.prop.secondary
        
        # Query members with the specified status
        query = session.query(
            Parishioner.id,
            Parishioner.first_name,
            Parishioner.last_name,
            Parishioner.new_church_id,
            Parishioner.mobile_number,
            Parishioner.email_address,
            Parishioner.gender,
            association_table.c.status.label('membership_status'),
            association_table.c.join_date.label('join_date')
        ).join(
            association_table,
            Parishioner.id == association_table.c.parishioner_id
        ).filter(
            association_table.c.society_id == society_id,
            association_table.c.status == status
        )
        
        # Count total matching records
        total_count = query.count()
        
        # Apply pagination
        members = query.offset(skip).limit(limit).all()
        
        result = []
        for row in members:
            # Extract all fields from the query result
            id, first_name, last_name, church_id, mobile, email, gender, membership_status, join_date = row
            
            result.append({
                "id": id,
                "name": f"{first_name} {last_name}",
                "church_id": church_id,
                "mobile": mobile,
                "email": email, 
                "gender": gender,
                "membership_status": membership_status,
                "join_date": join_date
            })
        
        return APIResponse(
            message=f"Retrieved {len(result)} society members with status '{status}'",
            data={
                "total": total_count,
                "items": result,
                "skip": skip,
                "limit": limit,
                "status": status
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching society members by status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )