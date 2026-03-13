import logging
from typing import Any, Optional
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import func

from app.api.deps import CurrentUser, SessionDep
from app.models.language import Language
from app.schemas.common import APIResponse
from app.schemas.language import LanguageCreate, LanguageRead, LanguageUpdate


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/available", response_model=APIResponse)
async def get_all_languages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None
) -> Any:
    """
    Get all available languages with optional search and pagination.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Build query
        query = session.query(Language)
        
        # Apply search filter if provided
        if search:
            query = query.filter(Language.name.ilike(f"%{search}%"))
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        languages = query.offset(skip).limit(limit).all()
        
        # Convert to response model
        languages_data = [LanguageRead.model_validate(lang) for lang in languages]
        
        return APIResponse(
            message=f"Retrieved {len(languages_data)} languages",
            data={
                "total": total_count,
                "languages": languages_data,
                "skip": skip,
                "limit": limit
            }
        )
    except Exception as e:
        logger.error(f"Error fetching languages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/available", response_model=APIResponse, status_code=201)
async def create_language(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    language_in: LanguageCreate
) -> Any:
    """
    Create a new language.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if language with this name already exists
        existing_language = session.query(Language).filter(
            func.lower(Language.name) == func.lower(language_in.name)
        ).first()
        
        if existing_language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A language with this name already exists"
            )
        
        # Create language
        db_language = Language(
            name=language_in.name,
            description=language_in.description
        )
        
        session.add(db_language)
        session.commit()
        session.refresh(db_language)
        
        return APIResponse(
            message="Language created successfully",
            data=LanguageRead.model_validate(db_language)
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Language with this name already exists"
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating language: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/available/{language_id}", response_model=APIResponse)
async def get_language(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    language_id: int = Path(..., ge=1)
) -> Any:
    """
    Get a specific language by ID.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Get language
        language = session.query(Language).filter(Language.id == language_id).first()
        
        if not language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language not found"
            )
        
        return APIResponse(
            message="Language retrieved successfully",
            data=LanguageRead.model_validate(language)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching language: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/available/{language_id}", response_model=APIResponse)
async def update_language(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    language_id: int = Path(..., ge=1),
    language_in: LanguageUpdate
) -> Any:
    """
    Update a language.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Get language
        language = session.query(Language).filter(Language.id == language_id).first()
        
        if not language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language not found"
            )
        
        # Check for name conflicts if name is being updated
        if language_in.name and language_in.name.lower() != language.name.lower():
            existing_language = session.query(Language).filter(
                func.lower(Language.name) == func.lower(language_in.name)
            ).first()
            
            if existing_language:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A language with this name already exists"
                )
        
        # Update language
        update_data = language_in.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(language, field, update_data[field])
        
        session.commit()
        session.refresh(language)
        
        return APIResponse(
            message="Language updated successfully",
            data=LanguageRead.model_validate(language)
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Language with this name already exists"
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating language: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/available/{language_id}", response_model=APIResponse)
async def delete_language(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    language_id: int = Path(..., ge=1),
) -> None:
    """
    Delete a language.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Get language
        language = session.query(Language).filter(Language.id == language_id).first()
        
        if not language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language not found"
            )
        
        # Delete language
        session.delete(language)
        session.commit()
        
        return APIResponse(
            message="Language deleted successfully",
            data=None
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting language: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
