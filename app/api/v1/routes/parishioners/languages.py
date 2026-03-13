import logging
from typing import Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Path, Query, BackgroundTasks


from app.api.deps import CurrentUser, SessionDep
from app.models.language import Language
from app.models.parishioner import Parishioner
from app.schemas.common import APIResponse
from app.schemas.language import LanguageRead
from app.schemas.parishioner import LanguagesAssignRequest



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

languages_router = APIRouter()


# === Parishioner Language Assignment Endpoints ===
@languages_router.get("", response_model=APIResponse)
async def get_parishioner_languages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: UUID
) -> Any:
    """
    Get all languages spoken by a parishioner.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if parishioner exists
        parishioner = session.query(Parishioner).filter(Parishioner.id == parishioner_id).first()
        
        if not parishioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parishioner not found"
            )
        
        # Get languages
        languages = parishioner.languages_rel
        
        return APIResponse(
            message=f"Retrieved {len(languages)} languages for parishioner",
            data=[LanguageRead.model_validate(lang) for lang in languages]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching parishioner languages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@languages_router.post("/assign", response_model=APIResponse)
async def assign_languages_to_parishioner(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: UUID,
    language_ids: LanguagesAssignRequest
) -> Any:
    """
    Assign languages to a parishioner.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if parishioner exists
        parishioner = session.query(Parishioner).filter(Parishioner.id == parishioner_id).first()
        
        if not parishioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parishioner not found"
            )
        
        # Track stats
        added = 0
        already_assigned = 0
        not_found = 0
        
        for language_id in language_ids.language_ids:
            # Check if language exists
            language = session.query(Language).filter(Language.id == language_id).first()
            
            if not language:
                not_found += 1
                continue
            
            # Check if already assigned
            if language in parishioner.languages_rel:
                already_assigned += 1
                continue
            
            # Assign language
            parishioner.languages_rel.append(language)
            added += 1
        
        session.commit()
        
        # Get updated languages list
        session.refresh(parishioner)
        
        return APIResponse(
            message="Languages assigned to parishioner",
            data={
                "added": added,
                "already_assigned": already_assigned,
                "not_found": not_found,
                "languages": [LanguageRead.model_validate(lang) for lang in parishioner.languages_rel]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error assigning languages to parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@languages_router.post("/remove", response_model=APIResponse)
async def remove_languages_from_parishioner(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: UUID,
    language_ids: LanguagesAssignRequest
) -> Any:
    """
    Remove languages from a parishioner.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if parishioner exists
        parishioner = session.query(Parishioner).filter(Parishioner.id == parishioner_id).first()
        
        if not parishioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parishioner not found"
            )
        
        # Track stats
        removed = 0
        not_assigned = 0
        not_found = 0
        
        for language_id in language_ids.language_ids:
            # Check if language exists
            language = session.query(Language).filter(Language.id == language_id).first()
            
            if not language:
                not_found += 1
                continue
            
            # Check if assigned
            if language not in parishioner.languages_rel:
                not_assigned += 1
                continue
            
            # Remove language
            parishioner.languages_rel.remove(language)
            removed += 1
        
        session.commit()
        
        # Get updated languages list
        session.refresh(parishioner)
        
        return APIResponse(
            message="Languages removed from parishioner",
            data={
                "removed": removed,
                "not_assigned": not_assigned,
                "not_found": not_found,
                "languages": [LanguageRead.model_validate(lang) for lang in parishioner.languages_rel]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error removing languages from parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@languages_router.delete("/{language_id}", response_model=APIResponse)
async def remove_language_from_parishioner(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    parishioner_id: UUID,
    language_id: int = Path(..., ge=1)
) -> Any:
    """
    Remove a specific language from a parishioner.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if parishioner exists
        parishioner = session.query(Parishioner).filter(Parishioner.id == parishioner_id).first()
        
        if not parishioner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parishioner not found"
            )
        
        # Check if language exists
        language = session.query(Language).filter(Language.id == language_id).first()
        
        if not language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language not found"
            )
        
        # Check if language is assigned to parishioner
        if language not in parishioner.languages_rel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language is not assigned to this parishioner"
            )
        
        # Remove language
        parishioner.languages_rel.remove(language)
        session.commit()
        
        return APIResponse(
            message=f"Language '{language.name}' removed from parishioner",
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error removing language from parishioner: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )