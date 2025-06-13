import logging
from typing import Any, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Query
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.church_community import ChurchCommunity
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    FamilyInfo
)
from app.models.place_of_worship import PlaceOfWorship
from app.schemas.common import APIResponse
from app.schemas.parishioner import *

from app.api.v1.routes.parishioner_routes.occupation import occupation_router
from app.api.v1.routes.parishioner_routes.emergency_contacts import emergency_contacts_router
from app.api.v1.routes.parishioner_routes.medical_conditions import medical_conditions_router
from app.api.v1.routes.parishioner_routes.family_info import family_info_router
from app.api.v1.routes.parishioner_routes.sacraments import sacraments_router
from app.api.v1.routes.parishioner_routes.skills import skills_router
from app.api.v1.routes.parishioner_routes.verification_msg import verify_router
from app.api.v1.routes.parishioner_routes.languages import languages_router

from app.services.sms.service import sms_service
from app.services.email.service import email_service


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# create single parishioner
@router.post("", response_model=APIResponse)
async def create_parishioner(
    *,
    session: SessionDep,
    parishioner_in: ParishionerCreate,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Create new parishioner with all related information.
 
    and returns created parishioner instance
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
       # Create new parishioner from input data
        db_parishioner = ParishionerModel(**parishioner_in.model_dump())
        

        session.add(db_parishioner)
        session.flush()  # Get ID before creating related records
        session.commit()
        session.refresh(db_parishioner)

        # send welcome sms
        background_tasks.add_task(
            sms_service.send_parishioner_onboarding_welcome_message,
            phone=parishioner_in.mobile_number,
            parishioner_name=parishioner_in.first_name + " " + parishioner_in.last_name
        )

        return APIResponse(
            message="Parishioner created successfully",
            data=ParishionerRead.model_validate(db_parishioner)
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
        logger.error(f"Error creating parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Get all parishioners with filters
@router.get("/all", response_model=APIResponse)
async def get_all_parishioners(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    search: Optional[str] = None,
    # Filter parameters
    society_id: Optional[int] = Query(None, description="Filter by society ID"),
    church_community_id: Optional[int] = Query(None, description="Filter by church community ID"),
    place_of_worship_id: Optional[int] = Query(None, description="Filter by place of worship ID"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    marital_status: Optional[str] = Query(None, description="Filter by marital status"),
    birth_day_name: Optional[str] = Query(None, description="Filter by day of the week of birth (Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday)"),
    birth_month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month of birth (1-12)"),
    membership_status: Optional[str] = Query(None, description="Filter by membership status"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    has_old_church_id: Optional[bool] = Query(None, description="Filter by presence of old church ID (true=has ID, false=no ID)"),
    has_new_church_id: Optional[bool] = Query(None, description="Filter by presence of new church ID (true=has ID, false=no ID)")
) -> Any:
    """
    Get list of all parishioners with pagination and filtering options.
    
    Available filters:
    - search: Search by parishioner ID, church IDs, or any name
    - society_id: Filter by society membership
    - church_community_id: Filter by church community
    - place_of_worship_id: Filter by place of worship
    - gender: Filter by gender
    - marital_status: Filter by marital status
    - birth_day_name: Filter by day of the week of birth (Sunday, Monday, etc.)
    - birth_month: Filter by month of birth (1-12)
    - membership_status: Filter by membership status
    - verification_status: Filter by verification status
    - has_old_church_id: Filter by presence of old church ID (true=has ID, false=no ID)
    - has_new_church_id: Filter by presence of new church ID (true=has ID, false=no ID)
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Initialize query
    query = session.query(ParishionerModel)
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                # System ID
                cast(ParishionerModel.id, String).ilike(search_term),
                # Church IDs
                ParishionerModel.old_church_id.ilike(search_term),
                ParishionerModel.new_church_id.ilike(search_term),
                # Name fields
                ParishionerModel.first_name.ilike(search_term),
                ParishionerModel.last_name.ilike(search_term),
                ParishionerModel.other_names.ilike(search_term),
                ParishionerModel.maiden_name.ilike(search_term)
            )
        )
    
    # Apply society filter
    if society_id is not None:
        # Join with society_members table to filter by society
        from app.models.society import society_members
        query = query.join(
            society_members,
            ParishionerModel.id == society_members.c.parishioner_id
        ).filter(
            society_members.c.society_id == society_id
        )
    
    # Apply church community filter
    if church_community_id is not None:
        query = query.filter(ParishionerModel.church_community_id == church_community_id)
    
    # Apply place of worship filter
    if place_of_worship_id is not None:
        query = query.filter(ParishionerModel.place_of_worship_id == place_of_worship_id)
    
    # Apply gender filter
    if gender is not None:
        # Normalize input and match against enum values
        gender_lower = gender.strip().lower()
        gender_mapping = {
            'male': 'male',
            'female': 'female', 
            'other': 'other',
            # Handle common variations
            'man': 'male',
            'woman': 'female',
            'boy': 'male',
            'girl': 'female',
            'm': 'male',
            'f': 'female'
        }
        
        if gender_lower in gender_mapping:
            query = query.filter(ParishionerModel.gender == gender_mapping[gender_lower])
        else:
            # If no exact match, return no results rather than partial matches
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid gender value. Use: male, female, other (or common variations like man, woman, m, f)"
            )
    
    # Apply marital status filter
    if marital_status is not None:
        # Normalize input and match against enum values
        marital_lower = marital_status.strip().lower()
        marital_mapping = {
            'single': 'single',
            'married': 'married',
            'widowed': 'widowed',
            'divorced': 'divorced',
            'separated': 'separated',
            # Handle common variations
            'unmarried': 'single',
            'wed': 'married',
            'widow': 'widowed',
            'widower': 'widowed'
        }
        
        if marital_lower in marital_mapping:
            query = query.filter(ParishionerModel.marital_status == marital_mapping[marital_lower])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid marital status. Use: single, married, widowed, divorced, separated (or common variations)"
            )
    
    # Apply birth day name filter (day of the week)
    if birth_day_name is not None:
        # Normalize the day name input
        day_name = birth_day_name.strip().lower()
        
        # Map day names to numbers (Sunday = 0, Monday = 1, ..., Saturday = 6)
        day_mapping = {
            'sunday': 0, 'sun': 0,
            'monday': 1, 'mon': 1,
            'tuesday': 2, 'tue': 2, 'tues': 2,
            'wednesday': 3, 'wed': 3,
            'thursday': 4, 'thu': 4, 'thur': 4, 'thurs': 4,
            'friday': 5, 'fri': 5,
            'saturday': 6, 'sat': 6
        }
        
        if day_name in day_mapping:
            day_number = day_mapping[day_name]
            # Use database-specific day of week extraction
            # PostgreSQL: extract('dow') returns 0=Sunday, 1=Monday, ..., 6=Saturday
            # MySQL: dayofweek() returns 1=Sunday, 2=Monday, ..., 7=Saturday
            # SQLite: strftime('%w') returns 0=Sunday, 1=Monday, ..., 6=Saturday
            
            # For PostgreSQL and SQLite (most common with FastAPI)
            query = query.filter(func.extract('dow', ParishionerModel.date_of_birth) == day_number)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid day name. Use: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday (or abbreviated forms)"
            )
    
    # Apply birth month filter
    if birth_month is not None:
        query = query.filter(func.extract('month', ParishionerModel.date_of_birth) == birth_month)
    
    # Apply membership status filter
    if membership_status is not None:
        # Normalize input and match against enum values
        membership_lower = membership_status.strip().lower()
        membership_mapping = {
            'active': 'active',
            'deceased': 'deceased',
            'disabled': 'disabled',
            # Handle common variations
            'alive': 'active',
            'dead': 'deceased',
            'inactive': 'disabled'
        }
        
        if membership_lower in membership_mapping:
            query = query.filter(ParishionerModel.membership_status == membership_mapping[membership_lower])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid membership status. Use: active, deceased, disabled (or variations like alive, dead, inactive)"
            )
    
    # Apply verification status filter
    if verification_status is not None:
        # Normalize input and match against enum values
        verification_lower = verification_status.strip().lower()
        verification_mapping = {
            'unverified': 'unverified',
            'verified': 'verified',
            'pending': 'pending',
            # Handle common variations
            'not verified': 'unverified',
            'not_verified': 'unverified',
            'confirm': 'verified',
            'confirmed': 'verified',
            'waiting': 'pending'
        }
        
        if verification_lower in verification_mapping:
            query = query.filter(ParishionerModel.verification_status == verification_mapping[verification_lower])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification status. Use: unverified, verified, pending (or variations)"
            )
        

    # Apply old church ID presence filter
    if has_old_church_id is not None:
        if has_old_church_id:
            # Filter for parishioners who have an old church ID (not null and not empty)
            query = query.filter(
                ParishionerModel.old_church_id.isnot(None),
                ParishionerModel.old_church_id != ''
            )
        else:
            # Filter for parishioners who don't have an old church ID (null or empty)
            query = query.filter(
                or_(
                    ParishionerModel.old_church_id.is_(None),
                    ParishionerModel.old_church_id == ''
                )
            )

    # Apply new church ID presence filter
    if has_new_church_id is not None:
        if has_new_church_id:
            # Filter for parishioners who have a new church ID (not null and not empty)
            query = query.filter(
                ParishionerModel.new_church_id.isnot(None),
                ParishionerModel.new_church_id != ''
            )
        else:
            # Filter for parishioners who don't have a new church ID (null or empty)
            query = query.filter(
                or_(
                    ParishionerModel.new_church_id.is_(None),
                    ParishionerModel.new_church_id == ''
                )
            )
    
    # Get total count with all filters applied
    total_count = query.count()
    
    # Apply pagination
    parishioners = query.offset(skip).limit(limit).all()
    
    # Convert to response model
    parishioners_data = [
        ParishionerRead.model_validate(parishioner) 
        for parishioner in parishioners
    ]
    
    # Build filter summary for response
    applied_filters = {}
    if search:
        applied_filters["search"] = search
    if society_id is not None:
        applied_filters["society_id"] = society_id
    if church_community_id is not None:
        applied_filters["church_community_id"] = church_community_id
    if place_of_worship_id is not None:
        applied_filters["place_of_worship_id"] = place_of_worship_id
    if gender is not None:
        applied_filters["gender"] = gender
    if marital_status is not None:
        applied_filters["marital_status"] = marital_status
    if birth_day_name is not None:
        applied_filters["birth_day_name"] = birth_day_name
    if birth_month is not None:
        applied_filters["birth_month"] = birth_month
    if membership_status is not None:
        applied_filters["membership_status"] = membership_status
    if verification_status is not None:
        applied_filters["verification_status"] = verification_status
    if has_old_church_id is not None:
        applied_filters["has_old_church_id"] = has_old_church_id
    if has_new_church_id is not None:
        applied_filters["has_new_church_id"] = has_new_church_id
    
    return APIResponse(
        message=f"Retrieved {len(parishioners_data)} parishioners",
        data={
            "total": total_count,
            "parishioners": parishioners_data,
            "skip": skip,
            "limit": limit,
            "filters_applied": applied_filters
        }
    )


# get detailed parishioner
@router.get("/{parishioner_id}", response_model=APIResponse)
async def get_detailed_parishioner(
    parishioner_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get detailed parishioner information by ID including all related entities."""

    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
    )
    
    # Query parishioner with all relationships eagerly loaded
    parishioner = session.query(ParishionerModel).options(
        joinedload(ParishionerModel.occupation_rel),
        joinedload(ParishionerModel.family_info_rel).joinedload(FamilyInfo.children_rel),
        joinedload(ParishionerModel.emergency_contacts_rel),
        joinedload(ParishionerModel.medical_conditions_rel),
        joinedload(ParishionerModel.sacrament_records),
        joinedload(ParishionerModel.skills_rel),
        joinedload(ParishionerModel.societies)  
    ).filter(
        ParishionerModel.id == parishioner_id
    ).first()

    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
     # Get children properly
    children = []
    if parishioner.family_info_rel and parishioner.family_info_rel.children_rel:
        for child in parishioner.family_info_rel.children_rel:
            children.append({
                "id": child.id,
                "name": child.name,
                "created_at": child.created_at,
                "updated_at": child.updated_at
            })
    
    family_info = None
    if parishioner.family_info_rel:
        family_info = {
            "id": parishioner.family_info_rel.id,
            "spouse_name": parishioner.family_info_rel.spouse_name,
            "spouse_status": parishioner.family_info_rel.spouse_status,
            "spouse_phone": parishioner.family_info_rel.spouse_phone,
            "father_name": parishioner.family_info_rel.father_name,
            "father_status": parishioner.family_info_rel.father_status,
            "mother_name": parishioner.family_info_rel.mother_name,
            "mother_status": parishioner.family_info_rel.mother_status,
            "children": children,  # Add children explicitly
            "created_at": parishioner.family_info_rel.created_at,
            "updated_at": parishioner.family_info_rel.updated_at
        }

    # Format societies data to include relevant fields
    # Format societies data to include relevant fields
    societies_data = []
    if parishioner.societies:
        # Import the association table to query membership details
        from app.models.society import society_members
        
        for society in parishioner.societies:
            # Query the association table for membership details directly
            membership_details = session.query(society_members).filter(
                society_members.c.parishioner_id == parishioner_id,
                society_members.c.society_id == society.id
            ).first()
            
            # Log the details properly to see what's available
            logger.info(f"Society: {society.name}, Membership details: {membership_details}")
            
            # Get date_joined and membership_status from the association table
            date_joined = None
            membership_status = None
            if membership_details:
                # Access the columns by their names as dictionary keys
                date_joined = membership_details._mapping.get('join_date')
                membership_status = membership_details._mapping.get('membership_status')
            
            societies_data.append({
                "id": society.id,
                "name": society.name,
                "description": society.description,
                "date_joined": date_joined,
                "membership_status": membership_status, 
                "created_at": society.created_at,
                "updated_at": society.updated_at,
            })
 
    languages_data = []
    if parishioner.languages_rel:
        for language in parishioner.languages_rel:
            languages_data.append({
                "id": language.id,
                "name": language.name,
                "description": language.description
            })
    
    parishioner_dict = {
        # Basic fields from ParishionerRead
        "id": parishioner.id,
        "old_church_id": parishioner.old_church_id,
        "new_church_id": parishioner.new_church_id,
        "first_name": parishioner.first_name,
        "other_names": parishioner.other_names,
        "last_name": parishioner.last_name,
        "maiden_name": parishioner.maiden_name,
        "gender": parishioner.gender,
        "date_of_birth": parishioner.date_of_birth,
        "place_of_birth": parishioner.place_of_birth,
        "hometown": parishioner.hometown,
        "region": parishioner.region,
        "country": parishioner.country,
        "marital_status": parishioner.marital_status,
        "mobile_number": parishioner.mobile_number,
        "whatsapp_number": parishioner.whatsapp_number,
        "email_address": parishioner.email_address,
        "current_residence": parishioner.current_residence,
        "membership_status": parishioner.membership_status,
        "verification_status": parishioner.verification_status,
        "created_at": parishioner.created_at,
        "updated_at": parishioner.updated_at,
        
        # Map relationship fields with correct names
        "occupation": parishioner.occupation_rel,
        "family_info": family_info,
        "emergency_contacts": parishioner.emergency_contacts_rel,
        "medical_conditions": parishioner.medical_conditions_rel,
        "sacraments": parishioner.sacrament_records,
        "skills": parishioner.skills_rel,
        "place_of_worship": parishioner.place_of_worship,
        "church_community": parishioner.church_community,
        "societies": societies_data,
        "languages_spoken": languages_data

    }

    return APIResponse(
        message="Parishioner retrieved successfully",
        data=ParishionerDetailedRead.model_validate(parishioner_dict)  # Pydantic will automatically handle the conversion
    )


@router.put("/{parishioner_id}", response_model=APIResponse)
async def update_parishioner(
    *,
    session: SessionDep,
    parishioner_id: UUID,
    parishioner_in: ParishionerPartialUpdate,
    current_user: CurrentUser,
) -> Any:
    """Update a parishioner's information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Get existing parishioner
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    try:
        # Only update fields that were actually provided
        update_data = parishioner_in.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            return APIResponse(
                message="No fields to update",
                data=ParishionerRead.model_validate(parishioner)
            )
        
        # Handle place_of_worship_id validation
        if 'place_of_worship_id' in update_data:
            try:
                # Convert to integer if it's a string
                if isinstance(update_data['place_of_worship_id'], str):
                    update_data['place_of_worship_id'] = int(update_data['place_of_worship_id'])
                
                # Validate the ID exists
                place_of_worship = session.query(PlaceOfWorship).filter(
                    PlaceOfWorship.id == update_data['place_of_worship_id']
                ).first()
                
                if not place_of_worship:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Place of worship with ID {update_data['place_of_worship_id']} not found"
                    )
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid place_of_worship_id format. Must be a valid integer."
                )
                
        # Handle church_community_id validation
        if 'church_community_id' in update_data:
            try:
                # Convert to integer if it's a string
                if isinstance(update_data['church_community_id'], str):
                    update_data['church_community_id'] = int(update_data['church_community_id'])
                
                # Validate the ID exists
                church_community = session.query(ChurchCommunity).filter(
                    ChurchCommunity.id == update_data['church_community_id']
                ).first()
                
                if not church_community:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Church community with ID {update_data['church_community_id']} not found"
                    )
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid church_community_id format. Must be a valid integer."
                )
        
        # Update all fields
        for field, value in update_data.items():
            setattr(parishioner, field, value)

        session.commit()
        session.refresh(parishioner)
        
        return APIResponse(
            message="Parishioner updated successfully",
            data=ParishionerRead.model_validate(parishioner)
        )
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry."
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    

    
# generate churchID
@router.post("/{parishioner_id}/generate-church-id", response_model=APIResponse)
async def generate_church_id(
    *,
    session: SessionDep,
    parishioner_id: UUID,
    old_church_id: str = Query(..., description="Old church ID to be incorporated into the new ID"),
    current_user: CurrentUser,
    send_email: bool = Query(False, description="Whether to send confirmation email to the parishioner"),
    send_sms: bool = Query(False, description="Whether to send confirmation SMS to the parishioner"),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Generate a new church ID for a parishioner.
    
    Format: first_name_initial + last_name_initial + day_of_birth(2 digits) + 
    month_of_birth(2 digits) + "-" + old_church_id
    
    Example: Kofi Maxwell Nkrumah, DOB: 30/01/2005, Old ID: 045
    New church ID: KN3001-045
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get existing parishioner
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    # Check required fields are present
    if not parishioner.first_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name is required to generate church ID"
        )
    
    if not parishioner.last_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last name is required to generate church ID"
        )
    
    if not parishioner.date_of_birth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date of birth is required to generate church ID"
        )
    
    if not old_church_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old church ID is required to generate new church ID"
        )
    
    try:
        # Generate new church ID
        first_name_initial = parishioner.first_name[0].upper()
        last_name_initial = parishioner.last_name[0].upper()
        
        # Format day and month with leading zeros if needed
        day_of_birth = f"{parishioner.date_of_birth.day:02d}"
        month_of_birth = f"{parishioner.date_of_birth.month:02d}"
        
        new_church_id = f"{first_name_initial}{last_name_initial}{day_of_birth}{month_of_birth}-{old_church_id}"
        
        # Update parishioner with new and old church IDs
        parishioner.new_church_id = new_church_id
        parishioner.old_church_id = old_church_id
        
        session.commit()
        session.refresh(parishioner)

        email_sent = False
        if send_email:
            if not parishioner.email_address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parishioner does not have email address"
                )
            
            
            parishioner_full_name = f"{parishioner.first_name} {parishioner.last_name}"
            email_sent = await email_service.send_church_id_confirmation(
                email=parishioner.email_address,
                parishioner_name=parishioner_full_name,
                system_id=str(parishioner_id),
                old_church_id=parishioner.old_church_id,
                new_church_id=parishioner.new_church_id
            )

        sms_sent = False
        if send_sms:
            if not parishioner.mobile_number:
                 raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parishioner does not have mobile number"
                )
        
            parishioner_full_name = f"{parishioner.first_name} {parishioner.last_name}"
            background_tasks.add_task(
                sms_service.send_church_id_generation_message,  
                parishioner_name=parishioner_full_name,
                phone=parishioner.mobile_number,
                new_church_id=parishioner.new_church_id
            )




        
        return APIResponse(
            message="Church ID generated successfully",
            data={
                "parishioner_id": parishioner.id,
                "old_church_id": parishioner.old_church_id,
                "new_church_id": parishioner.new_church_id,
                "email_sent": email_sent,
                "sms_sent":  send_sms and bool(parishioner.mobile_number)
            }
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error generating church ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# parishioner occupation
router.include_router(
    occupation_router,
    prefix="/{parishioner_id}/occupation",
)

# 
router.include_router(
    emergency_contacts_router,
    prefix="/{parishioner_id}/emergency-contacts",
)

# 
router.include_router(
    medical_conditions_router,
    prefix="/{parishioner_id}/medical-conditions",
)

# family info
router.include_router(
    family_info_router,
     prefix="/{parishioner_id}/family-info",
)

# sacraments
router.include_router(
    sacraments_router,
    prefix="/{parishioner_id}/sacraments",
)

# skills
router.include_router(
    skills_router,
    prefix="/{parishioner_id}/skills",
)

# languages
router.include_router(
languages_router,
prefix="/{parishioner_id}/languages",
)



# verification msg
router.include_router(
verify_router,
prefix="/verify"
)