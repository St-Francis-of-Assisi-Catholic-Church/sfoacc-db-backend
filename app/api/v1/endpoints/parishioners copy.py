import logging
from typing import Any, List
from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import (
    Parishioner as ParishionerModel,
    ContactInfo, Occupation, FamilyInfo,
    EmergencyContact, MedicalCondition, Sacrament,
    Skill, Child
)
from app.schemas.parishioner import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# create single parishioner
@router.post("/", response_model=APIResponse)
async def create_parishioner(
    *,
    session: SessionDep,
    parishioner_in: ParishionerCreate,
    current_user: CurrentUser,
) -> Any:
    """Create new parishioner with all related information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        # Create main parishioner record
        parishioner = ParishionerModel(**parishioner_in.model_dump(
            exclude={'contact_info', 'occupation', 'emergency_contacts', 
                    'medical_conditions', 'sacraments', 'skills'}
        ))
        session.add(parishioner)
        session.flush()  # Get ID before creating related records

        # Create contact info if provided
        if parishioner_in.contact_info:
            contact_info = ContactInfo(
                parishioner_id=parishioner.id,
                **parishioner_in.contact_info.model_dump()
            )
            session.add(contact_info)

        # Create occupation if provided
        if parishioner_in.occupation:
            occupation = Occupation(
                parishioner_id=parishioner.id,
                **parishioner_in.occupation.model_dump()
            )
            session.add(occupation)

        # Create emergency contacts
        for contact in parishioner_in.emergency_contacts:
            emergency_contact = EmergencyContact(
                parishioner_id=parishioner.id,
                **contact.model_dump()
            )
            session.add(emergency_contact)

        # Create medical conditions
        for condition in parishioner_in.medical_conditions:
            medical_condition = MedicalCondition(
                parishioner_id=parishioner.id,
                **condition.model_dump()
            )
            session.add(medical_condition)

        # Create sacraments
        for sacrament in parishioner_in.sacraments:
            sacrament_record = Sacrament(
                parishioner_id=parishioner.id,
                **sacrament.model_dump()
            )
            session.add(sacrament_record)

        # Handle skills
        for skill_name in parishioner_in.skills:
            skill = session.query(Skill).filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                session.add(skill)
            parishioner.skills_rel.append(skill)

        session.commit()
        session.refresh(parishioner)

        return APIResponse(
            message="Parishioner created successfully",
            data=ParishionerRead.model_validate(parishioner)
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

@router.get("/parishioners/{parishioner_id}", response_model=APIResponse)
async def get_parishioner(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get detailed parishioner information by ID."""
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()

    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )

    # Add relationships to response
    response_data = {
        "id": parishioner.id,
        "first_name": parishioner.first_name,
        "last_name": parishioner.last_name,
        "other_names": parishioner.other_names,
        "maiden_name": parishioner.maiden_name,
        "gender": parishioner.gender,
        "date_of_birth": parishioner.date_of_birth,
        "place_of_birth": parishioner.place_of_birth,
        "hometown": parishioner.hometown,
        "region": parishioner.region,
        "country": parishioner.country,
        "marital_status": parishioner.marital_status,
        "created_at": parishioner.created_at,
        "updated_at": parishioner.updated_at,
        "contact_info": parishioner.contact_info_rel,
        "occupation": parishioner.occupation_rel,
        "family_info": parishioner.family_info_rel,
        "emergency_contacts": parishioner.emergency_contacts_rel,
        "medical_conditions": parishioner.medical_conditions_rel,
        "sacraments": parishioner.sacraments_rel,
        "skills": parishioner.skills_rel
    }

    return APIResponse(
        message="Parishioner retrieved successfully",
        data=response_data
    )

@router.get("/parishioners/{parishioner_id}/family", response_model=APIResponse)
async def get_family_info(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get family information."""
    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family information not found"
        )
    
    # Include children in response
    response_data = {
        "id": family_info.id,
        "spouse_name": family_info.spouse_name,
        "spouse_status": family_info.spouse_status,
        "spouse_phone": family_info.spouse_phone,
        "father_name": family_info.father_name,
        "father_status": family_info.father_status,
        "mother_name": family_info.mother_name,
        "mother_status": family_info.mother_status,
        "children": family_info.children_rel,
        "created_at": family_info.created_at,
        "updated_at": family_info.updated_at
    }
    
    return APIResponse(
        message="Family information retrieved successfully",
        data=response_data
    )

@router.get("/parishioners/{parishioner_id}/emergency-contacts", response_model=APIResponse)
async def get_emergency_contacts(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all emergency contacts for a parishioner."""
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    return APIResponse(
        message="Emergency contacts retrieved successfully",
        data=[EmergencyContactRead.model_validate(contact) for contact in parishioner.emergency_contacts_rel]
    )

@router.get("/parishioners/{parishioner_id}/sacraments", response_model=APIResponse)
async def get_sacraments(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all sacrament records for a parishioner."""
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    return APIResponse(
        message="Sacraments retrieved successfully",
        data=[SacramentRead.model_validate(sacrament) for sacrament in parishioner.sacraments_rel]
    )

@router.get("/parishioners/{parishioner_id}/skills", response_model=APIResponse)
async def get_skills(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all skills for a parishioner."""
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    return APIResponse(
        message="Skills retrieved successfully",
        data=[SkillRead.model_validate(skill) for skill in parishioner.skills_rel]
    )

@router.put("/parishioners/{parishioner_id}/family", response_model=APIResponse)
async def update_family_info(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
    family_in: FamilyInfoUpdate,
) -> Any:
    """Update family information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    family_info = session.query(FamilyInfo).filter(
        FamilyInfo.parishioner_id == parishioner_id
    ).first()
    
    if not family_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family information not found"
        )

    try:
        # Update family info
        update_data = family_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(family_info, field, value)

        session.add(family_info)
        session.commit()
        session.refresh(family_info)

        # Include children in response
        response_data = {
            "id": family_info.id,
            "spouse_name": family_info.spouse_name,
            "spouse_status": family_info.spouse_status,
            "spouse_phone": family_info.spouse_phone,
            "father_name": family_info.father_name,
            "father_status": family_info.father_status,
            "mother_name": family_info.mother_name,
            "mother_status": family_info.mother_status,
            "children": family_info.children_rel,
            "created_at": family_info.created_at,
            "updated_at": family_info.updated_at
        }

        return APIResponse(
            message="Family information updated successfully",
            data=response_data
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/parishioners/{parishioner_id}/skills", response_model=APIResponse)
async def add_skill(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
    skill_in: SkillCreate,
) -> Any:
    """Add a skill to a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )

    try:
        # Get or create skill
        skill = session.query(Skill).filter(Skill.name == skill_in.name).first()
        if not skill:
            skill = Skill(**skill_in.model_dump())
            session.add(skill)
            session.flush()

        # Add skill to parishioner if not already added
        if skill not in parishioner.skills_rel:
            parishioner.skills_rel.append(skill)
            session.commit()
            return APIResponse(
                message="Skill added successfully",
                data=SkillRead.model_validate(skill)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skill already added to parishioner"
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/parishioners/search", response_model=APIResponse)
async def search_parishioners(
    session: SessionDep,
    current_user: CurrentUser,
    query: str = Query(None, min_length=2),
    skill: str = Query(None),
    sacrament_type: SacramentType = Query(None),
    region: str = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Search parishioners with various filters.
    """
    base_query = session.query(ParishionerModel)
    # Continuing the search function...
    # Apply filters
    if query:
        base_query = base_query.filter(
            (ParishionerModel.first_name.ilike(f"%{query}%")) |
            (ParishionerModel.last_name.ilike(f"%{query}%")) |
            (ParishionerModel.other_names.ilike(f"%{query}%"))
        )

    if skill:
        base_query = base_query.join(ParishionerModel.skills_rel).filter(
            Skill.name.ilike(f"%{skill}%")
        )

    if sacrament_type:
        base_query = base_query.join(ParishionerModel.sacraments_rel).filter(
            Sacrament.type == sacrament_type
        )

    if region:
        base_query = base_query.filter(ParishionerModel.region.ilike(f"%{region}%"))

    # Apply pagination
    total = base_query.count()
    parishioners = base_query.offset(skip).limit(limit).all()

    return APIResponse(
        message="Search results retrieved successfully",
        data={
            "total": total,
            "parishioners": [ParishionerRead.model_validate(p) for p in parishioners],
            "page": skip // limit + 1,
            "page_size": limit
        }
    )

@router.post("/parishioners/{parishioner_id}/medical", response_model=APIResponse)
async def create_medical_condition(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
    condition_in: MedicalConditionCreate,
) -> Any:
    """Add a medical condition."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )

    try:
        condition = MedicalCondition(
            parishioner_id=parishioner_id,
            **condition_in.model_dump()
        )
        session.add(condition)
        session.commit()
        session.refresh(condition)
        return APIResponse(
            message="Medical condition added successfully",
            data=MedicalConditionRead.model_validate(condition)
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/parishioners/{parishioner_id}/medical", response_model=APIResponse)
async def get_medical_conditions(
    parishioner_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get all medical conditions for a parishioner."""
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    return APIResponse(
        message="Medical conditions retrieved successfully",
        data=[MedicalConditionRead.model_validate(condition) 
              for condition in parishioner.medical_conditions_rel]
    )

@router.post("/parishioners/{parishioner_id}/contact", response_model=APIResponse)
async def create_contact_info(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
    contact_in: ContactInfoCreate,
) -> Any:
    """Create contact information for a parishioner."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Check if parishioner exists
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )

    # Check if contact info already exists
    if parishioner.contact_info_rel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact information already exists for this parishioner"
        )

    try:
        contact_info = ContactInfo(
            parishioner_id=parishioner_id,
            **contact_in.model_dump()
        )
        session.add(contact_info)
        session.commit()
        session.refresh(contact_info)

        return APIResponse(
            message="Contact information created successfully",
            data=ContactInfoRead.model_validate(contact_info)
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/parishioners/{parishioner_id}/contact", response_model=APIResponse)
async def update_contact_info(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
    contact_in: ContactInfoUpdate,
) -> Any:
    """Update contact information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner or not parishioner.contact_info_rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact information not found"
        )

    try:
        update_data = contact_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(parishioner.contact_info_rel, field, value)

        session.add(parishioner.contact_info_rel)
        session.commit()
        session.refresh(parishioner.contact_info_rel)

        return APIResponse(
            message="Contact information updated successfully",
            data=ContactInfoRead.model_validate(parishioner.contact_info_rel)
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/parishioners/{parishioner_id}/contact", response_model=APIResponse)
async def delete_contact_info(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
) -> Any:
    """Delete contact information."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner or not parishioner.contact_info_rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact information not found"
        )

    try:
        session.delete(parishioner.contact_info_rel)
        session.commit()
        return APIResponse(
            message="Contact information deleted successfully",
            data=None
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    

@router.post("/parishioners/{parishioner_id}/sacraments", response_model=APIResponse)
async def create_sacrament(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
    sacrament_in: SacramentCreate,
) -> Any:
    """Add a sacrament record."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )

    # Check if this type of sacrament already exists
    existing_sacrament = any(
        s.type == sacrament_in.type for s in parishioner.sacraments_rel
    )
    if existing_sacrament:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sacrament of type {sacrament_in.type} already exists"
        )

    try:
        sacrament = Sacrament(
            parishioner_id=parishioner_id,
            **sacrament_in.model_dump()
        )
        session.add(sacrament)
        session.commit()
        session.refresh(sacrament)
        return APIResponse(
            message="Sacrament record added successfully",
            data=SacramentRead.model_validate(sacrament)
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/parishioners/{parishioner_id}/sacraments/{sacrament_id}", response_model=APIResponse)
async def delete_sacrament(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: int,
    sacrament_id: int,
) -> Any:
    """Delete a sacrament record."""
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    sacrament = session.query(Sacrament).filter(
        Sacrament.id == sacrament_id,
        Sacrament.parishioner_id == parishioner_id
    ).first()
    
    if not sacrament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sacrament record not found"
        )

    try:
        session.delete(sacrament)
        session.commit()
        return APIResponse(
            message="Sacrament record deleted successfully",
            data=None
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/parishioners/stats", response_model=APIResponse)
async def get_parishioner_stats(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get general statistics about parishioners."""
    try:
        total_parishioners = session.query(ParishionerModel).count()
        
        # Gender distribution
        gender_stats = (
            session.query(
                ParishionerModel.gender,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.gender)
            .all()
        )
        
        # Marital status distribution
        marital_stats = (
            session.query(
                ParishionerModel.marital_status,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.marital_status)
            .all()
        )
        
        # Sacraments statistics
        sacrament_stats = (
            session.query(
                Sacrament.type,
                func.count(Sacrament.id)
            )
            .group_by(Sacrament.type)
            .all()
        )
        
        # Region distribution
        region_stats = (
            session.query(
                ParishionerModel.region,
                func.count(ParishionerModel.id)
            )
            .group_by(ParishionerModel.region)
            .all()
        )

        stats = {
            "total_parishioners": total_parishioners,
            "gender_distribution": {g[0]: g[1] for g in gender_stats},
            "marital_status_distribution": {m[0]: m[1] for m in marital_stats},
            "sacraments_distribution": {s[0]: s[1] for s in sacrament_stats},
            "region_distribution": {r[0]: r[1] for r in region_stats}
        }

        return APIResponse(
            message="Statistics retrieved successfully",
            data=stats
        )
    
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        )

# Add route to get all unique skills
@router.get("/skills", response_model=APIResponse)
async def get_all_skills(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get list of all unique skills in the system."""
    try:
        skills = session.query(Skill).order_by(Skill.name).all()
        return APIResponse(
            message="Skills retrieved successfully",
            data=[SkillRead.model_validate(skill) for skill in skills]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )