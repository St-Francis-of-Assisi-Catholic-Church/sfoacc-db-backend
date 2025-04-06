import uuid
from typing import Any, List, Literal
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta, timezone
from app.api.deps import SessionDep, CurrentUser
from app.models.parishioner import (Parishioner as ParishionerModel, FamilyInfo)
from app.models.verification import VerificationRecord
from app.models.common import VerificationStatus
from app.schemas.common import APIResponse
from app.services.email.service import email_service
from app.services.sms.service import sms_service
from app.services.verification.page_generator import VerificationPageGenerator
from app.core.config import settings

# Create a router for this endpoint
verify_router = APIRouter()

@verify_router.post("", response_model=APIResponse)
async def send_verification_message(
    *,
    session: SessionDep,
    parishioner_id: int,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    channel: Literal["email", "sms", "both"] = "both",
) -> Any:
    """
     Send a verification message to a parishioner with their complete details.
    
    Parameters:
    - parishioner_id: ID of the parishioner to send verification to
    - channel: Communication channel to use (email, sms, or both)
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
        joinedload(ParishionerModel.sacrament_records),
        joinedload(ParishionerModel.skills_rel),
        joinedload(ParishionerModel.languages_rel),
        joinedload(ParishionerModel.societies),
        joinedload(ParishionerModel.place_of_worship),
        joinedload(ParishionerModel.church_community)
    ).filter(
        ParishionerModel.id == parishioner_id
    ).first()

    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    # Validate contact information based on selected channel
    if channel in ["email", "both"] and not parishioner.email_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parishioner does not have an email address"
        )
    
    if channel in ["sms", "both"] and not parishioner.mobile_number:
        if channel == "sms":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parishioner does not have a phone number"
            )
        else:
            # For "both" channel, just note that SMS won't be sent
            channel = "email"
    
    # Generate verification page HTML - pass the session to retrieve association data
    verification_id = None
    # Check if a verification record already exists for this parishioner
    existing_verification = session.query(VerificationRecord).filter(
        VerificationRecord.parishioner_id == parishioner.id
    ).first()
    
    if existing_verification:
        # Update existing record
        verification_id = existing_verification.id
        verification_data = VerificationPageGenerator.generate_page(
            parishioner, 
            db_session=session, 
            verification_id=verification_id
        )
        existing_verification.html_content = verification_data["html"]
        existing_verification.access_code = verification_data["access_code"]
        existing_verification.expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    else:
        # Create new verification record
        verification_id = str(uuid.uuid4())
        # Generate HTML with confirmation button
        verification_data = VerificationPageGenerator.generate_page(
            parishioner, 
            db_session=session,
            verification_id=verification_id
        )
        verification_record = VerificationRecord.create_with_expiration(
            id=verification_id,
            parishioner_id=parishioner.id,
            html_content=verification_data["html"],
            access_code=verification_data["access_code"]
        )
        session.add(verification_record)
    
    # Update parishioner verification status
    if parishioner.verification_status != VerificationStatus.PENDING:
        parishioner.verification_status = VerificationStatus.PENDING
    
    session.commit()
    
    # Create verification link (points to our backend endpoint with correct format)
    verification_link = f"{settings.BACKEND_HOST}{settings.API_V1_STR}/parishioners/verify/view/{verification_id}"

    # Get parishioner name
    parishioner_name = f"{parishioner.first_name} {parishioner.last_name}"
    
    # Response data
    response_data = {
        "parishioner_id": parishioner.id,
        "verification_link": verification_link,
        "channels_sent": [],
        "verification_status": parishioner.verification_status.value if hasattr(parishioner.verification_status, 'value') else str(parishioner.verification_status)
    }

    # Send via appropriate channels
    if channel in ["email", "both"] and parishioner.email_address:
        background_tasks.add_task(
            email_service.send_verification_message,
            email=parishioner.email_address,
            parishioner_name=parishioner_name,
            verification_link=verification_link,
            access_code=verification_data["access_code"]
        )
        response_data["email"] = parishioner.email_address
        response_data["channels_sent"].append("email")

    if channel in ["sms", "both"] and parishioner.mobile_number:
        background_tasks.add_task(
            sms_service.send_verification_message,
            phone=parishioner.mobile_number,
            parishioner_name=parishioner_name,
            verification_link=verification_link,
            access_code=verification_data["access_code"]
        )
        response_data["phone"] = parishioner.mobile_number
        response_data["channels_sent"].append("sms")
        
    return APIResponse(
        message=f"Verification message sent via {', '.join(response_data['channels_sent'])}",
        data=response_data
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

@verify_router.post("/confirm/{verification_id}", response_model=APIResponse)
async def confirm_verification(
    verification_id: str,
    session: SessionDep,
    background_tasks: BackgroundTasks
) -> Any:
    """
    Endpoint to confirm verification and update parishioner status.
    This is called from the confirm button on the verification page.
    """
    # Find the verification record
    verification = session.query(VerificationRecord).filter(
        VerificationRecord.id == verification_id
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification record not found"
        )
    
    # Check if verification has expired
    now = datetime.now(timezone.utc)
    if verification.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification has expired"
        )
    
    # Get the parishioner
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == verification.parishioner_id
    ).first()
    
    if not parishioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parishioner not found"
        )
    
    # Update parishioner status to VERIFIED
    parishioner.verification_status = VerificationStatus.VERIFIED
    
    # Delete the verification record (no longer needed)
    session.delete(verification)
    
    # Commit changes
    session.commit()

     # Prepare confirmation message
    parishioner_name = f"{parishioner.first_name} {parishioner.last_name}"

    # Send confirmation email if the parishioner has an email address
    if parishioner.email_address:
        background_tasks.add_task(
            email_service.send_verification_confirmation,
            email=parishioner.email_address,
            parishioner_name=parishioner_name,
           
        )

    # Send confirmation SMS if the parishioner has a phone number
    if parishioner.mobile_number:
        background_tasks.add_task(
            sms_service.send_record_verification_confirmation_sms,
            phone=parishioner.mobile_number,
            parishioner_name=parishioner_name
        )
    
    # Return success response
    return APIResponse(
        message="Verification confirmed successfully",
        data={
            "parishioner_id": parishioner.id,
            "verification_status": parishioner.verification_status.value if hasattr(parishioner.verification_status, 'value') else str(parishioner.verification_status),
            "confirmation_sent_to": {
                "email": parishioner.email_address if parishioner.email_address else None,
                "sms": parishioner.mobile_number if parishioner.mobile_number else None
            }
        }
    )

@verify_router.post("/batch", response_model=APIResponse)
async def send_batch_verification_messages(
    *,
    session: SessionDep,
    parishioner_ids: List[int],
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
        joinedload(ParishionerModel.sacrament_records),
        joinedload(ParishionerModel.skills_rel),
        joinedload(ParishionerModel.languages_rel),
        joinedload(ParishionerModel.societies),
        joinedload(ParishionerModel.place_of_worship),
        joinedload(ParishionerModel.church_community)
    ).filter(
        ParishionerModel.id.in_(parishioner_ids)
    ).all()
    
    # Get existing verification records for these parishioners
    existing_verifications = session.query(VerificationRecord).filter(
        VerificationRecord.parishioner_id.in_(parishioner_ids)
    ).all()
    
    # Create a lookup dictionary for fast access to existing verifications
    verification_by_parishioner_id = {v.parishioner_id: v for v in existing_verifications}
    
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
        
        # Update verification status
        parishioner.verification_status = VerificationStatus.PENDING
        
        if parishioner.id in verification_by_parishioner_id:
            # Update existing record
            existing_verification = verification_by_parishioner_id[parishioner.id]
            verification_id = existing_verification.id
            
            # Generate HTML with verification ID for confirmation button
            verification_data = VerificationPageGenerator.generate_page(
                parishioner, 
                db_session=session,
                verification_id=verification_id
            )
            
            existing_verification.html_content = verification_data["html"]
            existing_verification.access_code = verification_data["access_code"]
            existing_verification.expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
        else:
            # Create new verification record
            verification_id = str(uuid.uuid4())
            
            # Generate HTML with verification ID for confirmation button
            verification_data = VerificationPageGenerator.generate_page(
                parishioner, 
                db_session=session,
                verification_id=verification_id
            )
            
            verification_record = VerificationRecord.create_with_expiration(
                id=verification_id,
                parishioner_id=parishioner.id,
                html_content=verification_data["html"],
                access_code=verification_data["access_code"]
            )
            session.add(verification_record)
        
        # Create verification link
        verification_link = f"{settings.BACKEND_HOST}{settings.API_V1_STR}/parishioners/verify/view/{verification_id}"
        
        # Get parishioner name
        parishioner_name = f"{parishioner.first_name} {parishioner.last_name}"
        
        # Send verification email in the background
        background_tasks.add_task(
            email_service.send_verification_message,
            email=parishioner.email_address,
            parishioner_name=parishioner_name,
            verification_link=verification_link,
            access_code=verification_data["access_code"]
        )
        
        results["processed"] += 1
        results["details"].append({
            "parishioner_id": parishioner.id,
            "status": "sent",
            "email": parishioner.email_address,
            "verification_link": verification_link,
            "verification_status": parishioner.verification_status.value if hasattr(parishioner.verification_status, 'value') else str(parishioner.verification_status)
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
    
    now = datetime.now(timezone.utc)
    is_expired = verification.expires_at < now
    
    # Get the parishioner for their current verification status
    parishioner = session.query(ParishionerModel).filter(
        ParishionerModel.id == verification.parishioner_id
    ).first()
    
    verification_status = None
    if parishioner:
        verification_status = parishioner.verification_status.value if hasattr(parishioner.verification_status, 'value') else str(parishioner.verification_status)
    
    return APIResponse(
        message="Verification found",
        data={
            "exists": True,
            "is_expired": is_expired,
            "verification_id": verification_id,
            "parishioner_id": verification.parishioner_id,
            "created_at": verification.created_at,
            "expires_at": verification.expires_at,
            "verification_status": verification_status
        }
    )