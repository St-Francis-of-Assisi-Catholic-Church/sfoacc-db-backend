import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field

from app.schemas.bulk_message import BulkMessageIn
from app.schemas.common import APIResponse
from app.services.sms.service import sms_service
from app.services.email.service import email_service
from app.models.parishioner import Parishioner
from app.api.deps import SessionDep, CurrentUser
from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_message_templates():
    templates = [
        {"id": tid, "name": t.name, "content": t.content}
        for tid, t in sms_service.templates.items()
    ]
    templates.append({"id": "custom_message", "name": "Custom Message", "content": None})
    return templates


async def _dispatch_sms(phone: str, template: str, message_content: str, context: dict):
    """Fire-and-forget SMS dispatch (called via BackgroundTasks)."""
    if template == "custom_message":
        try:
            formatted = message_content.format(**context)
        except KeyError as e:
            logger.error(f"Missing SMS template variable: {e}")
            return
        sms_service.send_sms(phone_numbers=[phone], message=formatted)
    else:
        sms_service.send_from_template(
            template_name=template,
            phone_numbers=[phone],
            context=context,
        )


async def _dispatch_email(email: str, template: str, message_content: str, subject: str, context: dict):
    """Fire-and-forget email dispatch (called via BackgroundTasks)."""
    if template == "custom_message":
        await email_service.send_custom_message(
            to_email=email,
            parishioner_name=context.get("parishioner_name", ""),
            custom_message=message_content,
            subject=subject,
            **context,
        )
    else:
        await email_service.send_from_template(
            template_name=template,
            to_emails=[email],
            context=context,
        )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/send", response_model=APIResponse)
async def send_bulk_message(
    *,
    session: SessionDep,
    bulk_message_in: BulkMessageIn = Body(...),
    background_tasks: BackgroundTasks,
) -> Any:
    try:
        template_ids = [t["id"] for t in get_message_templates()]

        if bulk_message_in.template not in template_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template: {bulk_message_in.template}. Must be one of: {', '.join(template_ids)}",
            )

        if bulk_message_in.template == "custom_message" and not bulk_message_in.custom_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom_message body is required when using the custom_message template",
            )

        parishioners = (
            session.query(Parishioner)
            .filter(Parishioner.id.in_(bulk_message_in.parishioner_ids))
            .all()
        )
        if not parishioners:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No parishioners found with the provided IDs",
            )

        logger.info(
            f"Queuing {bulk_message_in.channel} message to {len(parishioners)} parishioners "
            f"(template={bulk_message_in.template})"
        )

        queued = 0
        for parishioner in parishioners:
            full_name = f"{parishioner.first_name} {parishioner.last_name}"
            context = {
                "parishioner_name": full_name,
                "church_name": settings.CHURCH_NAME,
                "church_contact": settings.CHURCH_CONTACT,
                "new_church_id": parishioner.new_church_id or "N/A",
                "event_name": bulk_message_in.event_name or "Parish Event",
                "event_date": bulk_message_in.event_date or "Sunday",
                "event_time": bulk_message_in.event_time or "10:00 AM",
            }

            sent_this = False

            if bulk_message_in.channel in ("sms", "both") and parishioner.mobile_number:
                background_tasks.add_task(
                    _dispatch_sms,
                    parishioner.mobile_number,
                    bulk_message_in.template,
                    bulk_message_in.custom_message or "",
                    context,
                )
                sent_this = True

            if (
                bulk_message_in.channel in ("email", "both")
                and getattr(parishioner, "email_address", None)
            ):
                background_tasks.add_task(
                    _dispatch_email,
                    parishioner.email_address,
                    bulk_message_in.template,
                    bulk_message_in.custom_message or "",
                    bulk_message_in.subject or "Message from Your Parish",
                    context,
                )
                sent_this = True

            if sent_this:
                queued += 1

        return APIResponse(
            message=f"Successfully queued messages to {queued} parishioners",
            data={"queued_count": queued},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending bulk message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}",
        )


# ── Scheduled messaging ───────────────────────────────────────────────────────

class ScheduleMessageIn(BaseModel):
    parishioner_ids: List[UUID]
    channel: str = "both"
    template: str = "main_welcome_message"
    custom_message: Optional[str] = None
    subject: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    send_at: datetime = Field(..., description="UTC datetime when the message should be sent")


@router.post("/schedule", response_model=APIResponse)
async def schedule_message(
    *,
    session: SessionDep,
    payload: ScheduleMessageIn = Body(...),
) -> Any:
    """Schedule a bulk message to be sent at a future UTC datetime."""
    try:
        from app.models.messaging import ScheduledMessage, ScheduledMessageStatus

        template_ids = [t["id"] for t in get_message_templates()]
        if payload.template not in template_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template: {payload.template}",
            )
        if payload.template == "custom_message" and not payload.custom_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom_message body is required when using the custom_message template",
            )

        send_at = payload.send_at
        if send_at.tzinfo is None:
            send_at = send_at.replace(tzinfo=timezone.utc)
        if send_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="send_at must be a future datetime",
            )

        job = ScheduledMessage(
            parishioner_ids=[str(pid) for pid in payload.parishioner_ids],
            channel=payload.channel,
            template=payload.template,
            custom_message=payload.custom_message,
            subject=payload.subject,
            event_name=payload.event_name,
            event_date=payload.event_date,
            event_time=payload.event_time,
            send_at=send_at,
            status=ScheduledMessageStatus.PENDING,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        return APIResponse(
            message="Message scheduled successfully",
            data={
                "id": job.id,
                "send_at": job.send_at.isoformat(),
                "recipient_count": len(payload.parishioner_ids),
                "channel": job.channel,
                "template": job.template,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error scheduling message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling message: {str(e)}",
        )


@router.get("/scheduled", response_model=APIResponse)
async def list_scheduled_messages(
    session: SessionDep,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """List scheduled messages, optionally filtered by status."""
    try:
        from app.models.messaging import ScheduledMessage, ScheduledMessageStatus

        q = session.query(ScheduledMessage)
        if status_filter:
            try:
                q = q.filter(ScheduledMessage.status == ScheduledMessageStatus(status_filter))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

        total = q.count()
        jobs = q.order_by(ScheduledMessage.send_at).offset(skip).limit(limit).all()

        return APIResponse(
            message="Scheduled messages retrieved",
            data={
                "items": [
                    {
                        "id": j.id,
                        "channel": j.channel,
                        "template": j.template,
                        "send_at": j.send_at.isoformat(),
                        "status": j.status.value,
                        "sent_count": j.sent_count,
                        "error_message": j.error_message,
                        "recipient_count": len(j.parishioner_ids),
                        "created_at": j.created_at.isoformat(),
                    }
                    for j in jobs
                ],
                "total": total,
                "skip": skip,
                "limit": limit,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled/{job_id}", response_model=APIResponse)
async def cancel_scheduled_message(job_id: int, session: SessionDep) -> Any:
    """Cancel a pending scheduled message."""
    from app.models.messaging import ScheduledMessage, ScheduledMessageStatus

    job = session.query(ScheduledMessage).filter(ScheduledMessage.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled message not found")
    if job.status != ScheduledMessageStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a message with status '{job.status.value}'",
        )
    job.status = ScheduledMessageStatus.CANCELLED
    session.commit()
    return APIResponse(message="Scheduled message cancelled", data={"id": job_id})


@router.get("/templates", response_model=APIResponse)
async def get_all_bulk_message_templates() -> Any:
    try:
        return APIResponse(
            message="Templates retrieved successfully",
            data={
                "message_templates": get_message_templates(),
                "available_variables": [
                    {"name": "parishioner_name", "description": "Full name of the parishioner"},
                    {"name": "church_name", "description": "Name of the church"},
                    {"name": "church_contact", "description": "Church contact info"},
                    {"name": "new_church_id", "description": "Parishioner's church ID"},
                    {"name": "event_name", "description": "Event name (from request)"},
                    {"name": "event_date", "description": "Event date (from request)"},
                    {"name": "event_time", "description": "Event time (from request)"},
                ],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
