import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import SessionDep, CurrentUser

from app.models.sacrament import Sacrament
from app.schemas.common import APIResponse
from app.schemas.sacrament import SacramentRead



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Function to initialize the sacraments data
def initialize_sacraments(db: Session):
    # Check if sacraments already exist
    existing_count = db.query(Sacrament).count()
    if existing_count > 0:
        logger.info(f"Sacraments already initialized ({existing_count} found)")
        return
    
    # Initial sacrament data
    sacraments_data = [
        {
            "name": "Baptism",
            "description": "The first sacrament of initiation, which cleanses a person of original sin and welcomes them into the Church as a child of God.",
            "once_only": True
        },
        {
            "name": "Holy Communion",
            "description": "Also known as First Holy Communion or Eucharist, this sacrament commemorates the Last Supper, where Catholics receive the Body and Blood of Christ in the form of bread and wine.",
            "once_only": False
        },
        {
            "name": "Confirmation",
            "description": "A sacrament of initiation where a baptized person receives the gifts of the Holy Spirit, strengthening their faith and commitment to the Church.",
            "once_only": True
        },
        {
            "name": "Reconciliation",
            "description": "Also called Confession or Penance, this sacrament allows Catholics to confess their sins, receive absolution from a priest, and be reconciled with God.",
            "once_only": False
        },
        {
            "name": "Anointing of the Sick",
            "description": "A sacrament of healing given to those who are seriously ill or near death, providing spiritual strength, comfort, and sometimes physical healing.",
            "once_only": False
        },
        {
            "name": "Holy Orders",
            "description": "The sacrament through which men are ordained as deacons, priests, or bishops to serve the Church in a special way.",
            "once_only": True
        },
        {
            "name": "Holy Matrimony",
            "description": "The sacrament of marriage, where a man and woman enter into a sacred covenant with God and each other, forming a lifelong union.",
            "once_only": False
        }
    ]
    
    # Create and add sacrament instances
    for sacrament_data in sacraments_data:
        sacrament = Sacrament(**sacrament_data)
        db.add(sacrament)
    
    try:
        db.commit()
        logger.info(f"Successfully initialized {len(sacraments_data)} sacraments")
    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing sacraments: {str(e)}")

@router.get("/all", response_model=APIResponse)
async def get_sacraments(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    search: Optional[str] = None
) -> Any:
    """
    Get all sacraments with optional search by name or description.
    """
    try:
        # Ensure sacraments are initialized
        initialize_sacraments(session)
        
        # Build query
        query = session.query(Sacrament)
        
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Sacrament.name.ilike(search_term),
                    Sacrament.description.ilike(search_term)
                )
            )
            
        # Execute query
        sacraments = query.all()
        
        # Convert to Pydantic models
        sacraments_data = [
            SacramentRead.model_validate(sacrament) 
            for sacrament in sacraments
        ]
        
        return APIResponse(
            message=f"Retrieved {len(sacraments_data)} sacraments",
            data=sacraments_data
        )
        
    except Exception as e:
        logger.error(f"Error retrieving sacraments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sacraments: {str(e)}"
        )

@router.get("/{sacrament_id}", response_model=APIResponse)
async def get_sacrament_by_id(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    sacrament_id: int
) -> Any:
    """
    Get a specific sacrament by ID.
    """
    try:
        # Ensure sacraments are initialized
        initialize_sacraments(session)
        
        # Query for specific sacrament
        sacrament = session.query(Sacrament).filter(Sacrament.id == sacrament_id).first()
        
        if not sacrament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sacrament with ID {sacrament_id} not found"
            )
            
        # Convert to Pydantic model
        sacrament_data = SacramentRead.model_validate(sacrament)
        
        return APIResponse(
            message=f"Retrieved sacrament: {sacrament.name}",
            data=sacrament_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving sacrament: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sacrament: {str(e)}"
        )