import uuid
from uuid import UUID
from typing import Any, List, Literal, Optional
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta, timezone
from app.api.deps import SessionDep, CurrentUser, require_permission
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

@verify_router.post("", response_model=APIResponse, dependencies=[require_permission("parishioner:verify")])
async def send_verification_message(
    *,
    session: SessionDep,
    parishioner_id: UUID,
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
        joinedload(ParishionerModel.church_unit),
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
    if channel == "email" and not parishioner.email_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parishioner does not have an email address"
        )

    if channel == "sms" and not parishioner.mobile_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parishioner does not have a phone number"
        )

    if channel == "both":
        if not parishioner.email_address and not parishioner.mobile_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parishioner has neither an email address nor a phone number"
            )
        # Gracefully fall back to whichever channel is available
        if not parishioner.email_address:
            channel = "sms"
        elif not parishioner.mobile_number:
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
    
    # Full link for email; short redirect link for SMS (saves ~36 chars → lower cost)
    verification_link = f"{settings.BACKEND_HOST}{settings.API_V1_STR}/parishioners/verify/view/{verification_id}"
    sms_link = f"{settings.BACKEND_HOST}/v/{verification_id}"

    # Get parishioner name
    parishioner_name = f"{parishioner.first_name} {parishioner.last_name}"

    # Response data
    response_data = {
        "parishioner_id": parishioner.id,
        "verification_link": verification_link,
        "channel_requested": channel,
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
            verification_link=sms_link,
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
            sms_service.send_record_verification_confirmation_message,
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

class BatchVerifyRequest(BaseModel):
    """
    parishioner_ids: list of UUIDs to send to. Required unless send_to_all_unverified=true.
    send_to_all_unverified: if true, targets every parishioner with status
                            'unverified' or 'pending' (ignores parishioner_ids).
    channel: email | sms | both  (default: both)
    church_unit_id: optional — limit send_to_all_unverified to a specific unit.
    """
    parishioner_ids: Optional[List[UUID]] = None
    send_to_all_unverified: bool = False
    channel: Literal["email", "sms", "both"] = "both"
    church_unit_id: Optional[int] = None


def _process_batch(
    parishioners: list,
    channel: str,
    session,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Core batch logic: generate/refresh verification pages and enqueue sends.
    Returns a results dict.
    """
    par_ids = [p.id for p in parishioners]
    existing_verifications = {
        v.parishioner_id: v
        for v in session.query(VerificationRecord).filter(
            VerificationRecord.parishioner_id.in_(par_ids)
        ).all()
    }

    results: dict = {"total": len(par_ids), "processed": 0, "skipped": 0, "details": []}

    for parishioner in parishioners:
        has_email = bool(parishioner.email_address)
        has_mobile = bool(parishioner.mobile_number)
        send_email = channel in ["email", "both"] and has_email
        send_sms   = channel in ["sms",   "both"] and has_mobile

        if not send_email and not send_sms:
            results["skipped"] += 1
            results["details"].append({
                "parishioner_id": parishioner.id,
                "name": f"{parishioner.first_name} {parishioner.last_name}",
                "status": "skipped",
                "reason": "No contact info available for the requested channel",
            })
            continue

        parishioner.verification_status = VerificationStatus.PENDING

        existing = existing_verifications.get(parishioner.id)
        if existing:
            verification_id = existing.id
            verification_data = VerificationPageGenerator.generate_page(
                parishioner, db_session=session, verification_id=verification_id
            )
            existing.html_content = verification_data["html"]
            existing.access_code  = verification_data["access_code"]
            existing.expires_at   = datetime.now(timezone.utc) + timedelta(hours=48)
        else:
            verification_id = str(uuid.uuid4())
            verification_data = VerificationPageGenerator.generate_page(
                parishioner, db_session=session, verification_id=verification_id
            )
            session.add(VerificationRecord.create_with_expiration(
                id=verification_id,
                parishioner_id=parishioner.id,
                html_content=verification_data["html"],
                access_code=verification_data["access_code"],
            ))

        verification_link = (
            f"{settings.BACKEND_HOST}{settings.API_V1_STR}"
            f"/parishioners/verify/view/{verification_id}"
        )
        sms_link = f"{settings.BACKEND_HOST}/v/{verification_id}"
        parishioner_name = f"{parishioner.first_name} {parishioner.last_name}"

        if send_email:
            background_tasks.add_task(
                email_service.send_verification_message,
                email=parishioner.email_address,
                parishioner_name=parishioner_name,
                verification_link=verification_link,
                access_code=verification_data["access_code"],
            )

        if send_sms:
            background_tasks.add_task(
                sms_service.send_verification_message,
                phone=parishioner.mobile_number,
                parishioner_name=parishioner_name,
                verification_link=sms_link,
                access_code=verification_data["access_code"],
            )

        results["processed"] += 1
        results["details"].append({
            "parishioner_id": parishioner.id,
            "name": parishioner_name,
            "status": "sent",
            "email": parishioner.email_address if send_email else None,
            "mobile": parishioner.mobile_number if send_sms else None,
            "verification_link": verification_link,
            "channels_sent": [m for m, s in [("email", send_email), ("sms", send_sms)] if s],
        })

    session.commit()
    return results


@verify_router.post("/batch", response_model=APIResponse, dependencies=[require_permission("parishioner:verify")])
async def send_batch_verification_messages(
    *,
    session: SessionDep,
    body: BatchVerifyRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
) -> Any:
    """
    Send verification messages to a selected list of parishioners, or to all
    unverified/pending parishioners in one shot.

    Modes:
    - Explicit list: set `parishioner_ids` to an array of UUIDs.
    - All unverified: set `send_to_all_unverified: true`. Optionally scope to a
      unit with `church_unit_id`.

    For each parishioner this endpoint will:
      1. Generate (or refresh) a verification page with their full details.
      2. Set their status to `pending`.
      3. Dispatch email/SMS in the background.

    Parishioners with no contact info for the requested channel are skipped and
    reported in `data.details`.
    """
    if not body.send_to_all_unverified and not body.parishioner_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide parishioner_ids or set send_to_all_unverified=true",
        )

    _opts = [
        joinedload(ParishionerModel.occupation_rel),
        joinedload(ParishionerModel.family_info_rel).joinedload(FamilyInfo.children_rel),
        joinedload(ParishionerModel.emergency_contacts_rel),
        joinedload(ParishionerModel.medical_conditions_rel),
        joinedload(ParishionerModel.sacrament_records),
        joinedload(ParishionerModel.skills_rel),
        joinedload(ParishionerModel.languages_rel),
        joinedload(ParishionerModel.societies),
        joinedload(ParishionerModel.church_unit),
        joinedload(ParishionerModel.church_community),
    ]

    if body.send_to_all_unverified:
        q = session.query(ParishionerModel).options(*_opts).filter(
            ParishionerModel.verification_status.in_([
                VerificationStatus.UNVERIFIED,
                VerificationStatus.PENDING,
            ])
        )
        if body.church_unit_id is not None:
            q = q.filter(ParishionerModel.church_unit_id == body.church_unit_id)
        parishioners = q.all()
    else:
        parishioners = (
            session.query(ParishionerModel).options(*_opts)
            .filter(ParishionerModel.id.in_(body.parishioner_ids))
            .all()
        )

    if not parishioners:
        return APIResponse(
            message="No matching parishioners found",
            data={"total": 0, "processed": 0, "skipped": 0, "details": []},
        )

    results = _process_batch(parishioners, body.channel, session, background_tasks)

    return APIResponse(
        message=f"Processed {results['processed']} verifications, skipped {results['skipped']}",
        data=results,
    )

@verify_router.get("/check/{verification_id}", response_model=APIResponse,
                   dependencies=[require_permission("parishioner:verify")])
async def check_verification_status(
    verification_id: str,
    current_user: CurrentUser,
    session: SessionDep,
) -> Any:
    """
    Check if a verification page exists and is accessible.
    """
    
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