"""
Bulk messaging router.

Design:
- Templates are stored in the DB (message_templates table) and editable by admins.
- Dispatch is fire-and-forget via BackgroundTasks.
- Template content is resolved once per request; background tasks receive plain text.
- `custom_message` is a virtual template — its content comes from the request body.
"""
import logging
from datetime import datetime, timezone
from typing import Any, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, SessionDep, require_permission
from app.core.config import settings
from app.models.messaging import MessageTemplate, ScheduledMessage, ScheduledMessageStatus
from app.models.parishioner import Parishioner
from app.schemas.bulk_message import (
    BulkMessageIn,
    MessageTemplateCreate,
    MessageTemplateRead,
    MessageTemplateUpdate,
    ScheduleMessageIn,
    ScheduleSingleMessageIn,
    SingleMessageIn,
)
from app.schemas.common import APIResponse
from app.services.email.service import email_service
from app.services.sms.service import sms_service

logger = logging.getLogger(__name__)

router = APIRouter()

_SEND_PERMISSION = require_permission("parishioner:write")
_ADMIN_PERMISSION = require_permission("admin:all")

# Available context variables exposed in the API docs
_AVAILABLE_VARIABLES = [
    {"name": "parishioner_name", "description": "Full name of the parishioner"},
    {"name": "church_name",      "description": "Name of the church"},
    {"name": "church_contact",   "description": "Church contact information"},
    {"name": "new_church_id",    "description": "Parishioner's new church ID"},
    {"name": "event_name",       "description": "Event name (supplied in request)"},
    {"name": "event_date",       "description": "Event date (supplied in request)"},
    {"name": "event_time",       "description": "Event time (supplied in request)"},
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_template(session, template_id: str, custom_message: str | None) -> str:
    """
    Return the raw template content string for the given template_id.
    Raises HTTP 400 if the template doesn't exist.
    The caller is responsible for formatting with context before sending.
    """
    if template_id == "custom_message":
        if not custom_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom_message body is required when template is 'custom_message'",
            )
        return custom_message

    tmpl = session.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template '{template_id}' not found. Use GET /templates to see available templates.",
        )
    return tmpl.content


def _build_context(parishioner: Parishioner, event_name=None, event_date=None, event_time=None) -> dict:
    return {
        "parishioner_name": f"{parishioner.first_name} {parishioner.last_name}",
        "church_name":      settings.CHURCH_NAME,
        "church_contact":   settings.CHURCH_CONTACT,
        "new_church_id":    parishioner.new_church_id or "N/A",
        "event_name":       event_name or "Parish Event",
        "event_date":       event_date or "Sunday",
        "event_time":       event_time or "10:00 AM",
    }


def _format_content(content: str, context: dict) -> str:
    try:
        return content.format(**context)
    except KeyError as e:
        logger.warning("Missing template variable %s — using content as-is", e)
        return content


def _queue_for_parishioner(
    background_tasks: BackgroundTasks,
    parishioner: Parishioner,
    channel: str,
    content: str,
    subject: str,
    event_name=None,
    event_date=None,
    event_time=None,
) -> bool:
    """Queue SMS and/or email tasks. Returns True if at least one task was queued."""
    ctx = _build_context(parishioner, event_name, event_date, event_time)
    formatted = _format_content(content, ctx)
    queued = False

    if channel in ("sms", "both") and parishioner.mobile_number:
        background_tasks.add_task(
            _send_sms_task,
            parishioner.mobile_number,
            formatted,
        )
        queued = True

    if channel in ("email", "both") and parishioner.email_address:
        background_tasks.add_task(
            _send_email_task,
            parishioner.email_address,
            ctx["parishioner_name"],
            formatted,
            subject,
        )
        queued = True

    return queued


# ── Background tasks (plain functions — no DB access needed) ──────────────────

def _send_sms_task(phone: str, message: str) -> None:
    sms_service.send_sms(phone_numbers=[phone], message=message)


async def _send_email_task(email: str, name: str, message: str, subject: str) -> None:
    await email_service.send_custom_message(
        to_email=email,
        parishioner_name=name,
        custom_message=message,
        subject=subject,
    )


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=APIResponse)
async def list_templates(session: SessionDep) -> Any:
    """List all message templates including admin-created ones."""
    templates = session.query(MessageTemplate).order_by(MessageTemplate.name).all()
    data = [MessageTemplateRead.model_validate(t) for t in templates]
    data_list = [t.model_dump() for t in data]
    # append the virtual custom_message entry
    data_list.append({
        "id": "custom_message",
        "name": "Custom Message",
        "content": None,
        "description": "Write your own message body. Supports {parishioner_name}, {church_name}, {event_name}, {event_date}, {event_time}.",
        "is_system": False,
        "created_at": None,
        "updated_at": None,
    })
    return APIResponse(
        message="Templates retrieved successfully",
        data={"templates": data_list, "available_variables": _AVAILABLE_VARIABLES},
    )


@router.post("/templates", response_model=APIResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[_ADMIN_PERMISSION])
async def create_template(session: SessionDep, payload: MessageTemplateCreate, current_user: CurrentUser) -> Any:
    """Create a new message template. Admin only."""
    if payload.id == "custom_message":
        raise HTTPException(status_code=400, detail="'custom_message' is a reserved template ID")

    existing = session.query(MessageTemplate).filter(MessageTemplate.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Template '{payload.id}' already exists")

    tmpl = MessageTemplate(
        id=payload.id,
        name=payload.name,
        content=payload.content,
        description=payload.description,
        is_system=False,
    )
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return APIResponse(
        message="Template created successfully",
        data=MessageTemplateRead.model_validate(tmpl),
    )


@router.put("/templates/{template_id}", response_model=APIResponse, dependencies=[_ADMIN_PERMISSION])
async def update_template(
    template_id: str, session: SessionDep, payload: MessageTemplateUpdate, current_user: CurrentUser
) -> Any:
    """Update an existing template's name, content, or description. Admin only."""
    tmpl = session.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    if payload.name is not None:
        tmpl.name = payload.name
    if payload.content is not None:
        tmpl.content = payload.content
    if payload.description is not None:
        tmpl.description = payload.description

    session.commit()
    session.refresh(tmpl)
    return APIResponse(
        message="Template updated successfully",
        data=MessageTemplateRead.model_validate(tmpl),
    )


@router.delete("/templates/{template_id}", response_model=APIResponse, dependencies=[_ADMIN_PERMISSION])
async def delete_template(template_id: str, session: SessionDep, current_user: CurrentUser) -> Any:
    """Delete a non-system template. Admin only."""
    tmpl = session.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    if tmpl.is_system:
        raise HTTPException(status_code=400, detail="System templates cannot be deleted. You can edit their content.")

    session.delete(tmpl)
    session.commit()
    return APIResponse(message="Template deleted successfully", data={"id": template_id})


# ── Send ──────────────────────────────────────────────────────────────────────

@router.post("/send/{parishioner_id}", response_model=APIResponse, dependencies=[_SEND_PERMISSION])
async def send_to_parishioner(
    parishioner_id: UUID,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: SingleMessageIn = Body(...),
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Quick send to a single parishioner by ID.
    Resolves template, formats message, and dispatches in the background.
    """
    parishioner = session.query(Parishioner).filter(Parishioner.id == parishioner_id).first()
    if not parishioner:
        raise HTTPException(status_code=404, detail="Parishioner not found")

    content = _resolve_template(session, payload.template, payload.custom_message)
    subject = payload.subject or "Message from Your Parish"

    if payload.channel in ("sms", "both") and not parishioner.mobile_number:
        if payload.channel == "sms":
            raise HTTPException(status_code=400, detail="Parishioner has no mobile number on record")
    if payload.channel in ("email", "both") and not parishioner.email_address:
        if payload.channel == "email":
            raise HTTPException(status_code=400, detail="Parishioner has no email address on record")

    queued = _queue_for_parishioner(
        background_tasks, parishioner, payload.channel, content, subject,
        payload.event_name, payload.event_date, payload.event_time,
    )

    channels = []
    if payload.channel in ("sms", "both") and parishioner.mobile_number:
        channels.append("sms")
    if payload.channel in ("email", "both") and parishioner.email_address:
        channels.append("email")

    return APIResponse(
        message=f"Message queued via {', '.join(channels) if channels else 'no available channel'}",
        data={
            "parishioner_id": str(parishioner_id),
            "parishioner_name": f"{parishioner.first_name} {parishioner.last_name}",
            "channels": channels,
            "template": payload.template,
        },
    )


@router.post("/schedule/{parishioner_id}", response_model=APIResponse, dependencies=[_SEND_PERMISSION])
async def schedule_message_for_parishioner(
    parishioner_id: UUID,
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: ScheduleSingleMessageIn = Body(...),
) -> Any:
    """Schedule a message to a single parishioner at a future UTC datetime."""
    parishioner = session.query(Parishioner).filter(Parishioner.id == parishioner_id).first()
    if not parishioner:
        raise HTTPException(status_code=404, detail="Parishioner not found")

    # Validate template exists before saving
    _resolve_template(session, payload.template, payload.custom_message)

    send_at = payload.send_at
    if send_at.tzinfo is None:
        send_at = send_at.replace(tzinfo=timezone.utc)
    if send_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="send_at must be a future datetime")

    job = ScheduledMessage(
        parishioner_ids=[str(parishioner_id)],
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
            "parishioner_id": str(parishioner_id),
            "parishioner_name": f"{parishioner.first_name} {parishioner.last_name}",
            "channel": job.channel,
            "template": job.template,
            "send_at": job.send_at.isoformat(),
        },
    )


@router.post("/send", response_model=APIResponse, dependencies=[_SEND_PERMISSION])
async def send_bulk_message(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: BulkMessageIn = Body(...),
    background_tasks: BackgroundTasks,
) -> Any:
    """Send a message to one or more parishioners immediately."""
    content = _resolve_template(session, payload.template, payload.custom_message)
    subject = payload.subject or "Message from Your Parish"

    parishioners = (
        session.query(Parishioner).filter(Parishioner.id.in_(payload.parishioner_ids)).all()
    )
    if not parishioners:
        raise HTTPException(status_code=404, detail="No parishioners found with the provided IDs")

    queued = 0
    skipped = 0
    for p in parishioners:
        sent = _queue_for_parishioner(
            background_tasks, p, payload.channel, content, subject,
            payload.event_name, payload.event_date, payload.event_time,
        )
        if sent:
            queued += 1
        else:
            skipped += 1

    logger.info(
        "Queued %s message (%s) to %d parishioners, skipped %d (no contact info)",
        payload.channel, payload.template, queued, skipped,
    )

    return APIResponse(
        message=f"Queued messages to {queued} parishioner(s)",
        data={"queued": queued, "skipped": skipped, "total": len(parishioners)},
    )


# ── Scheduled messaging ───────────────────────────────────────────────────────

@router.post("/schedule", response_model=APIResponse, dependencies=[_SEND_PERMISSION])
async def schedule_message(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    payload: ScheduleMessageIn = Body(...),
) -> Any:
    """Schedule a bulk message to be sent at a future UTC datetime."""
    # Validate template exists before saving
    _resolve_template(session, payload.template, payload.custom_message)

    send_at = payload.send_at
    if send_at.tzinfo is None:
        send_at = send_at.replace(tzinfo=timezone.utc)
    if send_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="send_at must be a future datetime")

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


@router.get("/scheduled", response_model=APIResponse, dependencies=[_SEND_PERMISSION])
async def list_scheduled_messages(
    session: SessionDep,
    current_user: CurrentUser,
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, sent, failed, cancelled"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Any:
    """List scheduled messages, optionally filtered by status."""
    q = session.query(ScheduledMessage)
    if status_filter:
        try:
            q = q.filter(ScheduledMessage.status == ScheduledMessageStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status_filter}'. Use: pending, processing, sent, failed, cancelled")

    total = q.count()
    jobs = q.order_by(ScheduledMessage.send_at).offset(skip).limit(limit).all()

    return APIResponse(
        message=f"{total} scheduled message(s)",
        data={
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [
                {
                    "id": j.id,
                    "channel": j.channel,
                    "template": j.template,
                    "send_at": j.send_at.isoformat(),
                    "status": j.status.value,
                    "recipient_count": len(j.parishioner_ids),
                    "sent_count": j.sent_count,
                    "error_message": j.error_message,
                    "created_at": j.created_at.isoformat(),
                }
                for j in jobs
            ],
        },
    )


@router.delete("/scheduled/{job_id}", response_model=APIResponse, dependencies=[_SEND_PERMISSION])
async def cancel_scheduled_message(
    job_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    """Cancel a pending scheduled message."""
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
