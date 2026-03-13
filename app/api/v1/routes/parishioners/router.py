import logging
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.church_community import ChurchCommunity
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    FamilyInfo,
)
from app.models.place_of_worship import PlaceOfWorship
from app.models.society import society_members
from app.schemas.common import APIResponse
from app.schemas.parishioner import (
    ParishionerCreate,
    ParishionerRead,
    ParishionerPartialUpdate,
    ParishionerDetailedRead,
)

from app.api.v1.routes.parishioners.occupation import occupation_router
from app.api.v1.routes.parishioners.emergency_contacts import emergency_contacts_router
from app.api.v1.routes.parishioners.medical import medical_conditions_router
from app.api.v1.routes.parishioners.family import family_info_router
from app.api.v1.routes.parishioners.sacraments import sacraments_router
from app.api.v1.routes.parishioners.skills import skills_router
from app.api.v1.routes.parishioners.verification import verify_router
from app.api.v1.routes.parishioners.languages import languages_router
from app.api.v1.routes.parishioners.import_ import file_upload_router

from app.services.sms.service import sms_service
from app.services.email.service import email_service

logger = logging.getLogger(__name__)

router = APIRouter()

_ADMIN_ROLES = ["super_admin", "admin"]


def _require_admin(current_user):
    if current_user.role not in _ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


@router.post("", response_model=APIResponse)
async def create_parishioner(
    *,
    session: SessionDep,
    parishioner_in: ParishionerCreate,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Any:
    _require_admin(current_user)
    try:
        db_parishioner = ParishionerModel(**parishioner_in.model_dump())
        session.add(db_parishioner)
        session.flush()
        session.commit()
        session.refresh(db_parishioner)

        background_tasks.add_task(
            sms_service.send_parishioner_onboarding_welcome_message,
            phone=parishioner_in.mobile_number,
            parishioner_name=f"{parishioner_in.first_name} {parishioner_in.last_name}",
        )

        return APIResponse(
            message="Parishioner created successfully",
            data=ParishionerRead.model_validate(db_parishioner),
        )
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry.",
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating parishioner: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/all", response_model=APIResponse)
async def get_all_parishioners(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    search: Optional[str] = None,
    society_id: Optional[int] = Query(None, description="Filter by society ID"),
    church_community_id: Optional[int] = Query(None, description="Filter by church community ID"),
    place_of_worship_id: Optional[int] = Query(None, description="Filter by place of worship ID"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    marital_status: Optional[str] = Query(None, description="Filter by marital status"),
    birth_day_name: Optional[str] = Query(None, description="Filter by day of the week of birth"),
    birth_month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month of birth (1-12)"),
    membership_status: Optional[str] = Query(None, description="Filter by membership status"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    has_old_church_id: Optional[bool] = Query(None, description="Filter by presence of old church ID"),
    has_new_church_id: Optional[bool] = Query(None, description="Filter by presence of new church ID"),
) -> Any:
    _require_admin(current_user)

    query = session.query(ParishionerModel)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                cast(ParishionerModel.id, String).ilike(search_term),
                ParishionerModel.old_church_id.ilike(search_term),
                ParishionerModel.new_church_id.ilike(search_term),
                ParishionerModel.first_name.ilike(search_term),
                ParishionerModel.last_name.ilike(search_term),
                ParishionerModel.other_names.ilike(search_term),
                ParishionerModel.maiden_name.ilike(search_term),
            )
        )

    if society_id is not None:
        query = query.join(
            society_members,
            ParishionerModel.id == society_members.c.parishioner_id,
        ).filter(society_members.c.society_id == society_id)

    if church_community_id is not None:
        query = query.filter(ParishionerModel.church_community_id == church_community_id)

    if place_of_worship_id is not None:
        query = query.filter(ParishionerModel.place_of_worship_id == place_of_worship_id)

    if gender is not None:
        gender_mapping = {
            'male': 'male', 'man': 'male', 'boy': 'male', 'm': 'male',
            'female': 'female', 'woman': 'female', 'girl': 'female', 'f': 'female',
            'other': 'other',
        }
        mapped = gender_mapping.get(gender.strip().lower())
        if not mapped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid gender value. Use: male, female, other",
            )
        query = query.filter(ParishionerModel.gender == mapped)

    if marital_status is not None:
        marital_mapping = {
            'single': 'single', 'unmarried': 'single',
            'married': 'married', 'wed': 'married',
            'widowed': 'widowed', 'widow': 'widowed', 'widower': 'widowed',
            'divorced': 'divorced',
            'separated': 'separated',
        }
        mapped = marital_mapping.get(marital_status.strip().lower())
        if not mapped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid marital status. Use: single, married, widowed, divorced, separated",
            )
        query = query.filter(ParishionerModel.marital_status == mapped)

    if birth_day_name is not None:
        day_mapping = {
            'sunday': 0, 'sun': 0,
            'monday': 1, 'mon': 1,
            'tuesday': 2, 'tue': 2, 'tues': 2,
            'wednesday': 3, 'wed': 3,
            'thursday': 4, 'thu': 4, 'thur': 4, 'thurs': 4,
            'friday': 5, 'fri': 5,
            'saturday': 6, 'sat': 6,
        }
        day_number = day_mapping.get(birth_day_name.strip().lower())
        if day_number is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid day name. Use: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday",
            )
        query = query.filter(func.extract('dow', ParishionerModel.date_of_birth) == day_number)

    if birth_month is not None:
        query = query.filter(func.extract('month', ParishionerModel.date_of_birth) == birth_month)

    if membership_status is not None:
        membership_mapping = {
            'active': 'active', 'alive': 'active',
            'deceased': 'deceased', 'dead': 'deceased',
            'disabled': 'disabled', 'inactive': 'disabled',
        }
        mapped = membership_mapping.get(membership_status.strip().lower())
        if not mapped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid membership status. Use: active, deceased, disabled",
            )
        query = query.filter(ParishionerModel.membership_status == mapped)

    if verification_status is not None:
        verification_mapping = {
            'unverified': 'unverified', 'not verified': 'unverified', 'not_verified': 'unverified',
            'verified': 'verified', 'confirm': 'verified', 'confirmed': 'verified',
            'pending': 'pending', 'waiting': 'pending',
        }
        mapped = verification_mapping.get(verification_status.strip().lower())
        if not mapped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification status. Use: unverified, verified, pending",
            )
        query = query.filter(ParishionerModel.verification_status == mapped)

    if has_old_church_id is not None:
        if has_old_church_id:
            query = query.filter(
                ParishionerModel.old_church_id.isnot(None),
                ParishionerModel.old_church_id != '',
            )
        else:
            query = query.filter(
                or_(ParishionerModel.old_church_id.is_(None), ParishionerModel.old_church_id == '')
            )

    if has_new_church_id is not None:
        if has_new_church_id:
            query = query.filter(
                ParishionerModel.new_church_id.isnot(None),
                ParishionerModel.new_church_id != '',
            )
        else:
            query = query.filter(
                or_(ParishionerModel.new_church_id.is_(None), ParishionerModel.new_church_id == '')
            )

    total_count = query.count()
    parishioners = query.offset(skip).limit(limit).all()
    parishioners_data = [ParishionerRead.model_validate(p) for p in parishioners]

    applied_filters = {k: v for k, v in {
        "search": search,
        "society_id": society_id,
        "church_community_id": church_community_id,
        "place_of_worship_id": place_of_worship_id,
        "gender": gender,
        "marital_status": marital_status,
        "birth_day_name": birth_day_name,
        "birth_month": birth_month,
        "membership_status": membership_status,
        "verification_status": verification_status,
        "has_old_church_id": has_old_church_id,
        "has_new_church_id": has_new_church_id,
    }.items() if v is not None}

    return APIResponse(
        message=f"Retrieved {len(parishioners_data)} parishioners",
        data={
            "total": total_count,
            "parishioners": parishioners_data,
            "skip": skip,
            "limit": limit,
            "filters_applied": applied_filters,
        },
    )


@router.get("/{parishioner_id}", response_model=APIResponse)
async def get_detailed_parishioner(
    parishioner_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    _require_admin(current_user)

    parishioner = session.query(ParishionerModel).options(
        joinedload(ParishionerModel.occupation_rel),
        joinedload(ParishionerModel.family_info_rel).joinedload(FamilyInfo.children_rel),
        joinedload(ParishionerModel.emergency_contacts_rel),
        joinedload(ParishionerModel.medical_conditions_rel),
        joinedload(ParishionerModel.sacrament_records),
        joinedload(ParishionerModel.skills_rel),
        joinedload(ParishionerModel.societies),
    ).filter(ParishionerModel.id == parishioner_id).first()

    if not parishioner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parishioner not found")

    # Build children list
    children = []
    if parishioner.family_info_rel and parishioner.family_info_rel.children_rel:
        for child in parishioner.family_info_rel.children_rel:
            children.append({
                "id": child.id,
                "name": child.name,
                "created_at": child.created_at,
                "updated_at": child.updated_at,
            })

    family_info = None
    if parishioner.family_info_rel:
        fi = parishioner.family_info_rel
        family_info = {
            "id": fi.id,
            "spouse_name": fi.spouse_name,
            "spouse_status": fi.spouse_status,
            "spouse_phone": fi.spouse_phone,
            "father_name": fi.father_name,
            "father_status": fi.father_status,
            "mother_name": fi.mother_name,
            "mother_status": fi.mother_status,
            "children": children,
            "created_at": fi.created_at,
            "updated_at": fi.updated_at,
        }

    # Fetch all society memberships in a single query (fixes N+1)
    membership_rows = session.execute(
        select(society_members).where(society_members.c.parishioner_id == parishioner_id)
    ).mappings().all()
    membership_map = {row["society_id"]: row for row in membership_rows}

    societies_data = []
    for society in parishioner.societies:
        membership = membership_map.get(society.id, {})
        societies_data.append({
            "id": society.id,
            "name": society.name,
            "description": society.description,
            "date_joined": membership.get("join_date"),
            "membership_status": membership.get("membership_status"),
            "created_at": society.created_at,
            "updated_at": society.updated_at,
        })

    languages_data = [
        {"id": lang.id, "name": lang.name, "description": lang.description}
        for lang in (parishioner.languages_rel or [])
    ]

    parishioner_dict = {
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
        "occupation": parishioner.occupation_rel,
        "family_info": family_info,
        "emergency_contacts": parishioner.emergency_contacts_rel,
        "medical_conditions": parishioner.medical_conditions_rel,
        "sacraments": parishioner.sacrament_records,
        "skills": parishioner.skills_rel,
        "place_of_worship": parishioner.place_of_worship,
        "church_community": parishioner.church_community,
        "societies": societies_data,
        "languages_spoken": languages_data,
    }

    return APIResponse(
        message="Parishioner retrieved successfully",
        data=ParishionerDetailedRead.model_validate(parishioner_dict),
    )


@router.put("/{parishioner_id}", response_model=APIResponse)
async def update_parishioner(
    *,
    session: SessionDep,
    parishioner_id: UUID,
    parishioner_in: ParishionerPartialUpdate,
    current_user: CurrentUser,
) -> Any:
    _require_admin(current_user)

    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()

    if not parishioner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parishioner not found")

    try:
        update_data = parishioner_in.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            return APIResponse(message="No fields to update", data=ParishionerRead.model_validate(parishioner))

        if 'place_of_worship_id' in update_data:
            try:
                update_data['place_of_worship_id'] = int(update_data['place_of_worship_id'])
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid place_of_worship_id format. Must be a valid integer.",
                )
            place = session.query(PlaceOfWorship).filter(PlaceOfWorship.id == update_data['place_of_worship_id']).first()
            if not place:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Place of worship with ID {update_data['place_of_worship_id']} not found",
                )

        if 'church_community_id' in update_data:
            try:
                update_data['church_community_id'] = int(update_data['church_community_id'])
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid church_community_id format. Must be a valid integer.",
                )
            community = session.query(ChurchCommunity).filter(ChurchCommunity.id == update_data['church_community_id']).first()
            if not community:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Church community with ID {update_data['church_community_id']} not found",
                )

        for field, value in update_data.items():
            setattr(parishioner, field, value)

        session.commit()
        session.refresh(parishioner)

        return APIResponse(
            message="Parishioner updated successfully",
            data=ParishionerRead.model_validate(parishioner),
        )

    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error. Possible duplicate entry.",
        )
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating parishioner: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/{parishioner_id}/generate-church-id", response_model=APIResponse)
async def generate_church_id(
    *,
    session: SessionDep,
    parishioner_id: UUID,
    old_church_id: str = Query(..., description="Old church ID to be incorporated into the new ID"),
    current_user: CurrentUser,
    send_email: bool = Query(False, description="Whether to send confirmation email to the parishioner"),
    send_sms: bool = Query(False, description="Whether to send confirmation SMS to the parishioner"),
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Generate a new church ID for a parishioner.
    Format: first_initial + last_initial + day(2) + month(2) + "-" + old_id(5 digits)
    Example: KN3001-00045
    """
    _require_admin(current_user)

    parishioner = session.query(ParishionerModel).filter(ParishionerModel.id == parishioner_id).first()
    if not parishioner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parishioner not found")

    if not parishioner.first_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="First name is required to generate church ID")
    if not parishioner.last_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Last name is required to generate church ID")
    if not parishioner.date_of_birth:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date of birth is required to generate church ID")

    try:
        try:
            old_church_id_num = int(old_church_id)
            if old_church_id_num < 0:
                raise ValueError("Church ID cannot be negative")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Old church ID must be a valid positive number",
            )

        padded_old_church_id = str(old_church_id_num).zfill(5)

        # Single DB query to check for duplicate (replaces O(n) Python loop)
        existing = session.query(ParishionerModel).filter(
            ParishionerModel.old_church_id.in_([str(old_church_id_num), padded_old_church_id]),
            ParishionerModel.id != parishioner_id,
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Old church ID '{old_church_id}' already exists for parishioner: {existing.first_name} {existing.last_name}",
            )

        new_church_id = (
            f"{parishioner.first_name[0].upper()}"
            f"{parishioner.last_name[0].upper()}"
            f"{parishioner.date_of_birth.day:02d}"
            f"{parishioner.date_of_birth.month:02d}"
            f"-{padded_old_church_id}"
        )

        parishioner.new_church_id = new_church_id
        parishioner.old_church_id = padded_old_church_id

        session.commit()
        session.refresh(parishioner)

        email_sent = False
        if send_email:
            if not parishioner.email_address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parishioner does not have an email address",
                )
            parishioner_full_name = f"{parishioner.first_name} {parishioner.last_name}"
            email_sent = await email_service.send_church_id_confirmation(
                email=parishioner.email_address,
                parishioner_name=parishioner_full_name,
                system_id=str(parishioner_id),
                old_church_id=parishioner.old_church_id,
                new_church_id=parishioner.new_church_id,
            )

        if send_sms:
            if not parishioner.mobile_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parishioner does not have a mobile number",
                )
            parishioner_full_name = f"{parishioner.first_name} {parishioner.last_name}"
            background_tasks.add_task(
                sms_service.send_church_id_generation_message,
                parishioner_name=parishioner_full_name,
                phone=parishioner.mobile_number,
                new_church_id=parishioner.new_church_id,
            )

        return APIResponse(
            message="Church ID generated successfully",
            data={
                "parishioner_id": parishioner.id,
                "old_church_id": parishioner.old_church_id,
                "new_church_id": parishioner.new_church_id,
                "email_sent": email_sent,
                "sms_sent": send_sms and bool(parishioner.mobile_number),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error generating church ID: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


router.include_router(occupation_router, prefix="/{parishioner_id}/occupation")
router.include_router(emergency_contacts_router, prefix="/{parishioner_id}/emergency-contacts")
router.include_router(medical_conditions_router, prefix="/{parishioner_id}/medical-conditions")
router.include_router(family_info_router, prefix="/{parishioner_id}/family-info")
router.include_router(sacraments_router, prefix="/{parishioner_id}/sacraments")
router.include_router(skills_router, prefix="/{parishioner_id}/skills")
router.include_router(languages_router, prefix="/{parishioner_id}/languages")
router.include_router(verify_router, prefix="/verify")
router.include_router(file_upload_router, prefix="/import")
