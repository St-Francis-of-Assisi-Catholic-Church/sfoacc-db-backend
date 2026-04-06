import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import String, cast, func, insert, or_, select
from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser, ChurchUnitScope, require_permission
from app.models.church_community import ChurchCommunity
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    FamilyInfo,
    Child,
    Occupation,
    EmergencyContact,
    MedicalCondition,
    ParishionerSacrament,
    Skill,
)
from app.models.language import Language
from app.models.sacrament import Sacrament
from app.models.parish import ChurchUnit
from app.models.society import Society, society_members
from app.schemas.common import APIResponse
from app.schemas.parishioner import (
    ParishionerCreate,
    ParishionerFullCreate,
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
from app.api.v1.routes.parishioners.report import report_router
from app.api.v1.routes.parishioners.registration_schema import registration_schema_router
from app.api.v1.routes.parishioners.data_quality import data_quality_router

from app.services.sms.service import sms_service
from app.services.email.service import email_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Static-path sub-routers must be registered BEFORE /{parishioner_id} routes
# to prevent FastAPI matching "report", "verify", "import" as a UUID.
router.include_router(verify_router, prefix="/verify")
router.include_router(file_upload_router, prefix="/import")
router.include_router(report_router, prefix="/report")
router.include_router(registration_schema_router, prefix="/registration-schema")
router.include_router(data_quality_router, prefix="/data-quality")


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[require_permission("parishioner:write")])
async def register_parishioner(
    *,
    session: SessionDep,
    payload: ParishionerFullCreate,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Full parishioner registration in one request.
    Creates the core record plus occupation, family info, emergency contacts,
    medical conditions, sacraments, skills, languages, and society memberships
    atomically. Rolls back everything if any step fails.
    """
    try:
        # ── 1. Core parishioner ────────────────────────────────────────────
        core_fields = payload.model_dump(exclude={
            "occupation", "family_info", "emergency_contacts",
            "medical_conditions", "sacraments", "skills",
            "language_ids", "societies",
        })
        parishioner = ParishionerModel(**core_fields)
        session.add(parishioner)
        session.flush()  # get the UUID without committing

        pid = parishioner.id

        # ── 2. Occupation ──────────────────────────────────────────────────
        if payload.occupation:
            session.add(Occupation(parishioner_id=pid, **payload.occupation.model_dump()))

        # ── 3. Family info ─────────────────────────────────────────────────
        if payload.family_info:
            fi_data = payload.family_info
            family = FamilyInfo(
                parishioner_id=pid,
                spouse_name=fi_data.spouse.name if fi_data.spouse else None,
                spouse_status=fi_data.spouse.status if fi_data.spouse else None,
                spouse_phone=fi_data.spouse.phone if fi_data.spouse else None,
                father_name=fi_data.father.name if fi_data.father else None,
                father_status=fi_data.father.status if fi_data.father else None,
                mother_name=fi_data.mother.name if fi_data.mother else None,
                mother_status=fi_data.mother.status if fi_data.mother else None,
            )
            session.add(family)
            session.flush()
            for child in (fi_data.children or []):
                if child.name:
                    session.add(Child(family_info_id=family.id, name=child.name))

        # ── 4. Emergency contacts ──────────────────────────────────────────
        for ec in (payload.emergency_contacts or []):
            session.add(EmergencyContact(parishioner_id=pid, **ec.model_dump()))

        # ── 5. Medical conditions ──────────────────────────────────────────
        for mc in (payload.medical_conditions or []):
            session.add(MedicalCondition(parishioner_id=pid, **mc.model_dump()))

        # ── 6. Sacraments ──────────────────────────────────────────────────
        for sac in (payload.sacraments or []):
            sacrament = session.query(Sacrament).filter(Sacrament.id == sac.sacrament_id).first()
            if not sacrament:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sacrament with id {sac.sacrament_id} not found",
                )
            session.add(ParishionerSacrament(
                parishioner_id=pid,
                sacrament_id=sacrament.id,
                date_received=sac.date_received,
                place=sac.place,
                minister=sac.minister,
                notes=sac.notes,
            ))

        # ── 7. Skills (find-or-create by name) ────────────────────────────
        for skill_name in (payload.skills or []):
            skill_name = skill_name.strip()
            if not skill_name:
                continue
            skill = session.query(Skill).filter(
                func.lower(Skill.name) == skill_name.lower()
            ).first()
            if not skill:
                skill = Skill(name=skill_name)
                session.add(skill)
                session.flush()
            parishioner.skills_rel.append(skill)

        # ── 8. Languages ───────────────────────────────────────────────────
        for lang_id in (payload.language_ids or []):
            lang = session.query(Language).filter(Language.id == lang_id).first()
            if not lang:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Language with id {lang_id} not found",
                )
            parishioner.languages_rel.append(lang)

        # ── 9. Societies ───────────────────────────────────────────────────
        for sm in (payload.societies or []):
            society = session.query(Society).filter(Society.id == sm.society_id).first()
            if not society:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Society with id {sm.society_id} not found",
                )
            session.execute(
                insert(society_members).values(
                    society_id=sm.society_id,
                    parishioner_id=pid,
                    join_date=sm.date_joined,
                )
            )

        session.commit()
        session.refresh(parishioner)

        background_tasks.add_task(
            sms_service.send_parishioner_onboarding_welcome_message,
            phone=payload.mobile_number,
            parishioner_name=f"{payload.first_name} {payload.last_name}",
        )

        return APIResponse(
            message="Parishioner registered successfully",
            data=ParishionerRead.model_validate(parishioner),
        )

    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate entry — a parishioner with these details may already exist.",
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Error during full registration: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("", response_model=APIResponse, dependencies=[require_permission("parishioner:write")])
async def create_parishioner(
    *,
    session: SessionDep,
    parishioner_in: ParishionerCreate,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Any:
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


def _apply_parishioner_filters(
    query,
    session,
    unit_scope,
    search=None,
    society_id=None,
    church_community_id=None,
    church_unit_id=None,
    gender=None,
    marital_status=None,
    birth_day_name=None,
    birth_month=None,
    membership_status=None,
    verification_status=None,
    has_old_church_id=None,
    has_new_church_id=None,
):
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

    if unit_scope is not None:
        query = query.filter(ParishionerModel.church_unit_id == unit_scope)
    elif church_unit_id is not None:
        query = query.filter(ParishionerModel.church_unit_id == church_unit_id)

    if gender is not None:
        gender_mapping = {
            'male': 'male', 'man': 'male', 'boy': 'male', 'm': 'male',
            'female': 'female', 'woman': 'female', 'girl': 'female', 'f': 'female',
            'other': 'other',
        }
        mapped = gender_mapping.get(gender.strip().lower())
        if not mapped:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid gender value. Use: male, female, other")
        query = query.filter(ParishionerModel.gender == mapped)

    if marital_status is not None:
        marital_mapping = {
            'single': 'single', 'unmarried': 'single',
            'married': 'married', 'wed': 'married',
            'widowed': 'widowed', 'widow': 'widowed', 'widower': 'widowed',
            'divorced': 'divorced', 'separated': 'separated',
        }
        mapped = marital_mapping.get(marital_status.strip().lower())
        if not mapped:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid marital status. Use: single, married, widowed, divorced, separated")
        query = query.filter(ParishionerModel.marital_status == mapped)

    if birth_day_name is not None:
        day_mapping = {
            'sunday': 0, 'sun': 0, 'monday': 1, 'mon': 1,
            'tuesday': 2, 'tue': 2, 'tues': 2, 'wednesday': 3, 'wed': 3,
            'thursday': 4, 'thu': 4, 'thur': 4, 'thurs': 4,
            'friday': 5, 'fri': 5, 'saturday': 6, 'sat': 6,
        }
        day_number = day_mapping.get(birth_day_name.strip().lower())
        if day_number is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid day name. Use: Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday")
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid membership status. Use: active, deceased, disabled")
        query = query.filter(ParishionerModel.membership_status == mapped)

    if verification_status is not None:
        verification_mapping = {
            'unverified': 'unverified', 'not verified': 'unverified', 'not_verified': 'unverified',
            'verified': 'verified', 'confirm': 'verified', 'confirmed': 'verified',
            'pending': 'pending', 'waiting': 'pending',
        }
        mapped = verification_mapping.get(verification_status.strip().lower())
        if not mapped:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid verification status. Use: unverified, verified, pending")
        query = query.filter(ParishionerModel.verification_status == mapped)

    if has_old_church_id is not None:
        if has_old_church_id:
            query = query.filter(ParishionerModel.old_church_id.isnot(None), ParishionerModel.old_church_id != '')
        else:
            query = query.filter(or_(ParishionerModel.old_church_id.is_(None), ParishionerModel.old_church_id == ''))

    if has_new_church_id is not None:
        if has_new_church_id:
            query = query.filter(ParishionerModel.new_church_id.isnot(None), ParishionerModel.new_church_id != '')
        else:
            query = query.filter(or_(ParishionerModel.new_church_id.is_(None), ParishionerModel.new_church_id == ''))

    return query


_FILTER_PARAMS = dict(
    search=(Optional[str], None),
    society_id=(Optional[int], Query(None, description="Filter by society ID")),
    church_community_id=(Optional[int], Query(None, description="Filter by church community ID")),
    church_unit_id=(Optional[int], Query(None, description="Filter by church unit ID")),
    gender=(Optional[str], Query(None, description="Filter by gender")),
    marital_status=(Optional[str], Query(None, description="Filter by marital status")),
    birth_day_name=(Optional[str], Query(None, description="Filter by day of the week of birth")),
    birth_month=(Optional[int], Query(None, ge=1, le=12, description="Filter by month of birth (1-12)")),
    membership_status=(Optional[str], Query(None, description="Filter by membership status")),
    verification_status=(Optional[str], Query(None, description="Filter by verification status")),
    has_old_church_id=(Optional[bool], Query(None, description="Filter by presence of old church ID")),
    has_new_church_id=(Optional[bool], Query(None, description="Filter by presence of new church ID")),
)


@router.get("/all", response_model=APIResponse, dependencies=[require_permission("parishioner:read")])
async def get_all_parishioners(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    search: Optional[str] = None,
    society_id: Optional[int] = Query(None, description="Filter by society ID"),
    church_community_id: Optional[int] = Query(None, description="Filter by church community ID"),
    church_unit_id: Optional[int] = Query(None, description="Filter by church unit ID"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    marital_status: Optional[str] = Query(None, description="Filter by marital status"),
    birth_day_name: Optional[str] = Query(None, description="Filter by day of the week of birth"),
    birth_month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month of birth (1-12)"),
    membership_status: Optional[str] = Query(None, description="Filter by membership status"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    has_old_church_id: Optional[bool] = Query(None, description="Filter by presence of old church ID"),
    has_new_church_id: Optional[bool] = Query(None, description="Filter by presence of new church ID"),
) -> Any:

    query = _apply_parishioner_filters(
        session.query(ParishionerModel), session, unit_scope,
        search, society_id, church_community_id, church_unit_id,
        gender, marital_status, birth_day_name, birth_month,
        membership_status, verification_status, has_old_church_id, has_new_church_id,
    )

    total_count = query.count()
    parishioners = query.offset(skip).limit(limit).all()
    parishioners_data = [ParishionerRead.model_validate(p) for p in parishioners]

    applied_filters = {k: v for k, v in {
        "search": search, "society_id": society_id, "church_community_id": church_community_id,
        "church_unit_id": church_unit_id, "gender": gender, "marital_status": marital_status,
        "birth_day_name": birth_day_name, "birth_month": birth_month,
        "membership_status": membership_status, "verification_status": verification_status,
        "has_old_church_id": has_old_church_id, "has_new_church_id": has_new_church_id,
    }.items() if v is not None}

    return APIResponse(
        message=f"Retrieved {len(parishioners_data)} parishioners",
        data={
            "total": total_count,
            "items": parishioners_data,
            "skip": skip,
            "limit": limit,
            "filters_applied": applied_filters,
        },
    )


@router.get("/export-csv", dependencies=[require_permission("parishioner:read")])
async def export_parishioners_csv(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    search: Optional[str] = None,
    society_id: Optional[int] = Query(None),
    church_community_id: Optional[int] = Query(None),
    church_unit_id: Optional[int] = Query(None),
    gender: Optional[str] = Query(None),
    marital_status: Optional[str] = Query(None),
    birth_day_name: Optional[str] = Query(None),
    birth_month: Optional[int] = Query(None, ge=1, le=12),
    membership_status: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    has_old_church_id: Optional[bool] = Query(None),
    has_new_church_id: Optional[bool] = Query(None),
) -> StreamingResponse:
    """Export filtered parishioners with full detail as CSV."""

    query = _apply_parishioner_filters(
        session.query(ParishionerModel), session, unit_scope,
        search, society_id, church_community_id, church_unit_id,
        gender, marital_status, birth_day_name, birth_month,
        membership_status, verification_status, has_old_church_id, has_new_church_id,
    ).options(
        subqueryload(ParishionerModel.church_unit),
        subqueryload(ParishionerModel.church_community),
        subqueryload(ParishionerModel.occupation_rel),
        subqueryload(ParishionerModel.family_info_rel).subqueryload(FamilyInfo.children_rel),
        subqueryload(ParishionerModel.emergency_contacts_rel),
        subqueryload(ParishionerModel.medical_conditions_rel),
        subqueryload(ParishionerModel.sacrament_records).subqueryload(ParishionerSacrament.sacrament),
        subqueryload(ParishionerModel.societies),
        subqueryload(ParishionerModel.skills_rel),
        subqueryload(ParishionerModel.languages_rel),
    ).order_by(ParishionerModel.last_name, ParishionerModel.first_name)

    parishioners = query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "old_church_id", "new_church_id",
        "title", "first_name", "last_name", "other_names",
        "maiden_name", "baptismal_name", "gender",
        "date_of_birth", "place_of_birth",
        "nationality", "hometown", "region", "country",
        "marital_status",
        "mobile_number", "whatsapp_number", "email_address", "current_residence",
        "is_deceased", "date_of_death",
        "membership_status", "verification_status",
        "church_unit", "church_community",
        "occupation_role", "occupation_employer",
        "spouse_name", "spouse_status", "spouse_phone",
        "father_name", "father_status",
        "mother_name", "mother_status",
        "children",
        "emergency_contacts",
        "medical_conditions",
        "sacraments",
        "societies",
        "skills", "languages",
        "created_at", "updated_at",
    ])

    def _sep(items):
        return " | ".join(i for i in items if i)

    for p in parishioners:
        fam = p.family_info_rel
        occ = p.occupation_rel

        children = _sep([c.name for c in fam.children_rel]) if fam else ""
        emergency = _sep([
            f"{ec.name} ({ec.relationship}) {ec.primary_phone}"
            + (f"/{ec.alternative_phone}" if ec.alternative_phone else "")
            for ec in p.emergency_contacts_rel
        ])
        medical = _sep([mc.condition for mc in p.medical_conditions_rel])
        sacraments = _sep([
            f"{sr.sacrament.name}"
            + (f" on {sr.date_received.isoformat()}" if sr.date_received else "")
            + (f" at {sr.place}" if sr.place else "")
            + (f" by {sr.minister}" if sr.minister else "")
            for sr in p.sacrament_records
        ])
        societies = _sep([s.name for s in p.societies])
        skills = _sep([sk.name for sk in p.skills_rel])
        languages = _sep([lang.name for lang in p.languages_rel])

        writer.writerow([
            str(p.id), p.old_church_id or "", p.new_church_id or "",
            p.title or "", p.first_name, p.last_name, p.other_names or "",
            p.maiden_name or "", p.baptismal_name or "",
            p.gender.value if p.gender else "",
            p.date_of_birth.isoformat() if p.date_of_birth else "",
            p.place_of_birth or "", p.nationality or "", p.hometown or "",
            p.region or "", p.country or "",
            p.marital_status.value if p.marital_status else "",
            p.mobile_number or "", p.whatsapp_number or "",
            p.email_address or "", p.current_residence or "",
            "yes" if p.is_deceased else "no",
            p.date_of_death.isoformat() if p.date_of_death else "",
            p.membership_status.value if p.membership_status else "",
            p.verification_status.value if p.verification_status else "",
            p.church_unit.name if p.church_unit else "",
            p.church_community.name if p.church_community else "",
            occ.role if occ else "", occ.employer if occ else "",
            fam.spouse_name if fam else "",
            fam.spouse_status.value if fam and fam.spouse_status else "",
            fam.spouse_phone if fam else "",
            fam.father_name if fam else "",
            fam.father_status.value if fam and fam.father_status else "",
            fam.mother_name if fam else "",
            fam.mother_status.value if fam and fam.mother_status else "",
            children, emergency, medical, sacraments, societies, skills, languages,
            p.created_at.isoformat() if p.created_at else "",
            p.updated_at.isoformat() if p.updated_at else "",
        ])

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"parishioners_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{parishioner_id}", response_model=APIResponse, dependencies=[require_permission("parishioner:read")])
async def get_detailed_parishioner(
    parishioner_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:

    parishioner = session.query(ParishionerModel).options(
        joinedload(ParishionerModel.occupation_rel),
        joinedload(ParishionerModel.family_info_rel).joinedload(FamilyInfo.children_rel),
        joinedload(ParishionerModel.emergency_contacts_rel),
        joinedload(ParishionerModel.medical_conditions_rel),
        joinedload(ParishionerModel.sacrament_records).joinedload(ParishionerSacrament.sacrament),
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
        "church_unit": parishioner.church_unit,
        "church_community": parishioner.church_community,
        "societies": societies_data,
        "languages_spoken": languages_data,
    }

    return APIResponse(
        message="Parishioner retrieved successfully",
        data=ParishionerDetailedRead.model_validate(parishioner_dict),
    )


@router.put("/{parishioner_id}", response_model=APIResponse, dependencies=[require_permission("parishioner:write")])
async def update_parishioner(
    *,
    session: SessionDep,
    parishioner_id: UUID,
    parishioner_in: ParishionerPartialUpdate,
    current_user: CurrentUser,
) -> Any:

    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()

    if not parishioner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parishioner not found")

    try:
        update_data = parishioner_in.model_dump(exclude_unset=True, exclude_none=True)

        if not update_data:
            return APIResponse(message="No fields to update", data=ParishionerRead.model_validate(parishioner))

        if 'church_unit_id' in update_data:
            try:
                update_data["church_unit_id"] = int(update_data["church_unit_id"])
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid church_unit_id format. Must be a valid integer.",
                )
            church_unit = session.query(ChurchUnit).filter(ChurchUnit.id == update_data["church_unit_id"]).first()
            if not church_unit:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Church unit with ID {update_data['church_unit_id']} not found",
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


@router.post("/{parishioner_id}/generate-church-id", response_model=APIResponse,
             dependencies=[require_permission("parishioner:generate_id")])
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
