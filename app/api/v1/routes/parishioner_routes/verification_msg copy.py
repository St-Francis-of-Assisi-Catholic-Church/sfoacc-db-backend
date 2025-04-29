import uuid
from uuid import UUID
from typing import Any, List
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import (Parishioner as ParishionerModel, FamilyInfo)
from app.models.verification import VerificationRecord

from app.schemas.common import APIResponse
from app.services.email.service import email_service
from app.services.verification.page_generator import VerificationPageGenerator
from app.core.config import settings

# Create a router for this endpoint
verify_router = APIRouter()

@verify_router.post("", response_model=APIResponse)
async def send_verification_message(
    *,
    session: SessionDep,
    parishioner_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
) -> Any:
    """
    Send a verification message to a parishioner with their complete details.
    """
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
        joinedload(ParishionerModel.sacraments_rel),
        joinedload(ParishionerModel.skills_rel)
    ).filter(
        ParishionerModel.id == parishioner_id
    ).first()

    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
        
    if not parishioner.email_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parishioner does not have an email address"
        )
    
    # Generate verification page HTML
    verification_data = VerificationPageGenerator.generate_page(parishioner)
    
    # Generate a unique identifier for this verification
    verification_id = str(uuid.uuid4())
    
    # Create verification record in database
    verification_record = VerificationRecord.create_with_expiration(
        id=verification_id,
        parishioner_id=parishioner.id,
        html_content=verification_data["html"],
        access_code=verification_data["access_code"]
    )
    
    session.add(verification_record)
    session.commit()
    
    # Create verification link (points to our backend endpoint)
    verification_link = f"{settings.DOMAIN}{settings.API_V1_STR}/parishioners/verify/view/{verification_id}"
    # verification_link = f"http://localhost:8000{settings.API_V1_STR}/parishioners/verification/view/{verification_id}"
    
    # Get parishioner name
    parishioner_name = f"{parishioner.first_name} {parishioner.last_name}"
    
    # Send verification email in the background
    background_tasks.add_task(
        email_service.send_verification_message,
        email=parishioner.email_address,
        parishioner_name=parishioner_name,
        verification_link=verification_link,
        access_code=""  # We don't need to send the access code in the email anymore
    )
    
    return APIResponse(
        message="Verification message sent successfully",
        data={
            "parishioner_id": parishioner.id,
            "email": parishioner.email_address,
            "verification_link": verification_link
        }
    )

@verify_router.get("/view/{verification_id}", response_class=HTMLResponse)
async def view_verification_page(
    verification_id: str,
    session: SessionDep
) -> Any:
    """
    View the verification page for a parishioner.
    This endpoint serves the HTML directly from the backend.
    """
    verification = session.query(VerificationRecord).filter(
        VerificationRecord.id == verification_id
    ).first()
    
    if not verification:
        return HTMLResponse(content="<html><body><h1>Verification page not found</h1><p>This verification link is invalid or has been removed.</p></body></html>")
    
    now = datetime.now(timezone.utc)
    
    # Check if verification has expired
    if verification.expires_at < now:
        return HTMLResponse(content="<html><body><h1>Verification expired</h1><p>This verification link has expired. Please contact the church administration for a new link.</p></body></html>")
    
    # Return the stored HTML content
    return HTMLResponse(content=verification.html_content)

@verify_router.post("/batch", response_model=APIResponse)
async def send_batch_verification_messages(
    *,
    session: SessionDep,
    parishioner_ids: List[UUID],
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
) -> Any:
    """
    Send verification messages to multiple parishioners at once.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    if not parishioner_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parishioner IDs provided"
        )
    
    # Query all parishioners with all relationships eagerly loaded
    parishioners = session.query(ParishionerModel).options(
        joinedload(ParishionerModel.occupation_rel),
        joinedload(ParishionerModel.family_info_rel).joinedload(FamilyInfo.children_rel),
        joinedload(ParishionerModel.emergency_contacts_rel),
        joinedload(ParishionerModel.medical_conditions_rel),
        joinedload(ParishionerModel.sacraments_rel),
        joinedload(ParishionerModel.skills_rel)
    ).filter(
        ParishionerModel.id.in_(parishioner_ids)
    ).all()
    
    # Track results
    results = {
        "total": len(parishioner_ids),
        "processed": 0,
        "skipped": 0,
        "details": []
    }
    
    # Process each parishioner
    for parishioner in parishioners:
        # Skip if no email
        if not parishioner.email_address:
            results["skipped"] += 1
            results["details"].append({
                "parishioner_id": parishioner.id,
                "status": "skipped",
                "reason": "No email address"
            })
            continue
        
        # Generate verification page HTML
        verification_data = VerificationPageGenerator.generate_page(parishioner)
        
        # Generate a unique identifier for this verification
        verification_id = str(uuid.uuid4())
        
        # Create verification record in database
        verification_record = VerificationRecord.create_with_expiration(
            id=verification_id,
            parishioner_id=parishioner.id,
            html_content=verification_data["html"],
            access_code=verification_data["access_code"]
        )
        
        session.add(verification_record)
        
        # Create verification link
        verification_link = f"{settings.DOMAIN}{settings.API_V1_STR}/parishioners/verify/view/{verification_id}"
        
        # Get parishioner name
        parishioner_name = f"{parishioner.first_name} {parishioner.last_name}"
        
        # Send verification email in the background
        background_tasks.add_task(
            email_service.send_verification_message,
            email=parishioner.email_address,
            parishioner_name=parishioner_name,
            verification_link=verification_link,
            access_code=""
        )
        
        results["processed"] += 1
        results["details"].append({
            "parishioner_id": parishioner.id,
            "status": "sent",
            "email": parishioner.email_address,
            "verification_link": verification_link
        })
    
    # Commit all the verification records at once
    session.commit()
    
    return APIResponse(
        message=f"Processed {results['processed']} verification messages, skipped {results['skipped']}",
        data=results
    )

@verify_router.get("/check/{verification_id}", response_model=APIResponse)
async def check_verification_status(
    verification_id: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> Any:
    """
    Check if a verification page exists and is accessible.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    verification = session.query(VerificationRecord).filter(
        VerificationRecord.id == verification_id
    ).first()
    
    if not verification:
        return APIResponse(
            message="Verification not found",
            data={
                "exists": False,
                "verification_id": verification_id
            }
        )
    
    now = datetime.utcnow()
    is_expired = verification.expires_at < now
    
    return APIResponse(
        message="Verification found",
        data={
            "exists": True,
            "is_expired": is_expired,
            "verification_id": verification_id,
            "parishioner_id": verification.parishioner_id,
            "created_at": verification.created_at,
            "expires_at": verification.expires_at
        })