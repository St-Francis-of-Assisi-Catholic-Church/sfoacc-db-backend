import logging
from typing import List, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Path, Query
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import Parishioner, Skill
from app.schemas.common import APIResponse
from app.schemas.parishioner import  SkillCreate, SkillRead, SkillBase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

skills_router = APIRouter()

# Helper function to get parishioner or raise 404
def get_parishioner_or_404(session: SessionDep, parishioner_id: UUID):
    parishioner = session.query(Parishioner).filter(
        Parishioner.id == parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    return parishioner

# Get all skills for a parishioner
@skills_router.get("/", response_model=APIResponse)
async def get_parishioner_skills(
    parishioner_id: UUID = Path(..., description="The ID of the parishioner"),
    session: SessionDep = None,
    current_user: CurrentUser = None,
) -> APIResponse:
    """
    Get all skills associated with a parishioner.
    """
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Get all skills for this parishioner
    skills = parishioner.skills_rel
    
    return APIResponse(
        message=f"Retrieved {len(skills)} skills for parishioner",
        data=[SkillRead.model_validate(skill) for skill in skills]
    )

# Add a new skill to a parishioner
@skills_router.post("/", response_model=APIResponse)
async def add_parishioner_skill(
    parishioner_id: UUID = Path(..., description="The ID of the parishioner"),
    skill: SkillCreate = None,
    session: SessionDep = None,
    current_user: CurrentUser = None,
) -> APIResponse:
    """
    Add a new skill to a parishioner. If the skill already exists, it will be linked to the parishioner.
    If it doesn't exist, it will be created and then linked.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    try:
        # Check if skill already exists
        db_skill = session.query(Skill).filter(
            Skill.name == skill.name
        ).first()
        
        # If skill doesn't exist, create it
        if not db_skill:
            db_skill = Skill(name=skill.name)
            session.add(db_skill)
            session.flush()
        
        # Check if parishioner already has this skill
        if db_skill in parishioner.skills_rel:
            return APIResponse(
                message="Parishioner already has this skill",
                data=SkillRead.model_validate(db_skill)
            )
        
        # Add skill to parishioner
        parishioner.skills_rel.append(db_skill)
        session.commit()
        session.refresh(db_skill)
        
        return APIResponse(
            message="Skill added to parishioner successfully",
            data=SkillRead.model_validate(db_skill)
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding skill to parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Add multiple skills to a parishioner at once
@skills_router.post("/batch", response_model=APIResponse)
async def add_multiple_skills(
    parishioner_id: UUID = Path(..., description="The ID of the parishioner"),
    skills: List[SkillBase] = None,
    session: SessionDep = None,
    current_user: CurrentUser = None,
) -> APIResponse:
    """
    Replace all existing skills of a parishioner with the new batch of skills.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    try:
        # First, remove all existing skills association
        parishioner.skills_rel.clear()
        
        # If no new skills provided, just return empty list after clearing existing skills
        if not skills:
            session.commit()
            return APIResponse(
                message="All skills removed from parishioner, no new skills provided",
                data=[]
            )
        
        new_skills = []
        
        for skill_data in skills:
            # Check if skill already exists in the database
            db_skill = session.query(Skill).filter(
                Skill.name == skill_data.name
            ).first()
            
            # If skill doesn't exist in the database, create it
            if not db_skill:
                db_skill = Skill(name=skill_data.name)
                session.add(db_skill)
                session.flush()
            
            # Add skill to parishioner
            parishioner.skills_rel.append(db_skill)
            new_skills.append(db_skill)
        
        session.commit()
        
        # Return all skills now assigned to the parishioner
        return APIResponse(
            message=f"Successfully replaced skills for parishioner. Now has {len(new_skills)} skills.",
            data=[SkillRead.model_validate(skill) for skill in new_skills]
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating skills for parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
# Remove a skill from a parishioner
@skills_router.delete("/{skill_id}", response_model=APIResponse)
async def remove_parishioner_skill(
    parishioner_id: UUID = Path(..., description="The ID of the parishioner"),
    skill_id: int = Path(..., description="The ID of the skill to remove"),
    session: SessionDep = None,
    current_user: CurrentUser = None,
) -> APIResponse:
    """
    Remove a skill from a parishioner. This does not delete the skill from the database,
    it only removes the association between the parishioner and the skill.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if parishioner exists
    parishioner = get_parishioner_or_404(session, parishioner_id)
    
    # Check if skill exists
    skill = session.query(Skill).filter(
        Skill.id == skill_id
    ).first()
    
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    
    # Check if parishioner has this skill
    if skill not in parishioner.skills_rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner does not have this skill"
        )
    
    try:
        # Remove skill from parishioner
        parishioner.skills_rel.remove(skill)
        session.commit()
        
        return APIResponse(
            message="Skill removed from parishioner successfully",
            data=None
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error removing skill from parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Get all available skills (global endpoint)
@skills_router.get("/all-available", response_model=APIResponse)
async def get_all_available_skills(
    parishioner_id: UUID = Path(..., description="The ID of the parishioner"),
    session: SessionDep = None,
    current_user: CurrentUser = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> APIResponse:
    """
    Get a list of all available skills in the system.
    Useful for populating dropdown menus.
    """
    # Check permissions
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Query all skills with pagination
    skills = session.query(Skill).offset(skip).limit(limit).all()
    
    return APIResponse(
        message=f"Retrieved {len(skills)} available skills",
        data=[SkillRead.model_validate(skill) for skill in skills]
    )