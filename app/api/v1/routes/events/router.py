import logging
from datetime import date, datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.api.deps import ChurchUnitScope, CurrentUser, SessionDep, require_permission
from app.models.church_unit_admin import ChurchEvent, EventMessage, RecurrenceFrequency
from app.models.parish import ChurchUnit
from app.schemas.common import APIResponse
from app.schemas.event import (
    ChurchEventCreate,
    ChurchEventDetailRead,
    ChurchEventRead,
    ChurchEventUpdate,
    EventMessageCreate,
    EventMessageUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_REQUIRE_READ  = require_permission("parishioner:read")   # broad read access
_REQUIRE_WRITE = require_permission("admin:outstation")   # admin-level for create/edit


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_active(event: ChurchEvent) -> bool:
    if event.terminated_at:
        return False
    if event.is_recurring and event.recurrence_end_date:
        return event.recurrence_end_date >= date.today()
    return True


def _serialize(event: ChurchEvent, include_messages: bool = False) -> dict:
    unit_name = event.church_unit.name if event.church_unit else None
    base = {
        "id": event.id,
        "church_unit_id": event.church_unit_id,
        "church_unit_name": unit_name,
        "name": event.name,
        "description": event.description,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "start_time": event.start_time.strftime("%H:%M") if event.start_time else None,
        "end_time": event.end_time.strftime("%H:%M") if event.end_time else None,
        "location": event.location,
        "is_public": event.is_public,
        "is_recurring": event.is_recurring,
        "recurrence_frequency": event.recurrence_frequency.value if event.recurrence_frequency else None,
        "recurrence_day_of_week": event.recurrence_day_of_week,
        "recurrence_end_date": event.recurrence_end_date.isoformat() if event.recurrence_end_date else None,
        "terminated_at": event.terminated_at.isoformat() if event.terminated_at else None,
        "is_active": _is_active(event),
        "message_count": len(event.messages) if event.messages is not None else 0,
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
    }
    if include_messages:
        base["messages"] = [
            {
                "id": m.id,
                "event_id": m.event_id,
                "message_type": m.message_type.value,
                "title": m.title,
                "content": m.content,
                "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
                "is_sent": m.is_sent,
                "created_by_id": str(m.created_by_id) if m.created_by_id else None,
                "created_at": m.created_at.isoformat(),
                "updated_at": m.updated_at.isoformat(),
            }
            for m in (event.messages or [])
        ]
    return base


def _load_one(session, event_id: int) -> ChurchEvent:
    event = (
        session.query(ChurchEvent)
        .options(
            joinedload(ChurchEvent.church_unit),
            joinedload(ChurchEvent.messages),
        )
        .filter(ChurchEvent.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _apply_recurrence(event: ChurchEvent, recurrence) -> None:
    """Set or clear recurrence fields from a RecurrenceConfig (or None)."""
    if recurrence is None:
        event.is_recurring           = False
        event.recurrence_frequency   = None
        event.recurrence_day_of_week = None
        event.recurrence_end_date    = None
    else:
        if recurrence.frequency == RecurrenceFrequency.WEEKLY and recurrence.day_of_week is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="day_of_week is required for weekly recurrence",
            )
        event.is_recurring           = True
        event.recurrence_frequency   = recurrence.frequency
        event.recurrence_day_of_week = recurrence.day_of_week
        event.recurrence_end_date    = recurrence.recurrence_end_date


# ── Events CRUD ───────────────────────────────────────────────────────────────

@router.get("", response_model=APIResponse, dependencies=[_REQUIRE_READ])
async def list_events(
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    church_unit_id: Optional[int] = Query(None, description="Filter by specific unit"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    is_recurring: Optional[bool] = Query(None, description="Filter recurring-only or one-time-only"),
    active_only: bool = Query(True, description="Exclude terminated / expired events"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Any:
    """List church events with optional filters."""
    q = session.query(ChurchEvent).options(
        joinedload(ChurchEvent.church_unit),
        joinedload(ChurchEvent.messages),
    )

    # Unit scoping
    scope = church_unit_id or unit_scope
    if scope is not None:
        q = q.filter(ChurchEvent.church_unit_id == scope)

    if date_from:
        q = q.filter(ChurchEvent.event_date >= date_from)
    if date_to:
        q = q.filter(ChurchEvent.event_date <= date_to)
    if is_recurring is not None:
        q = q.filter(ChurchEvent.is_recurring == is_recurring)

    events = q.order_by(ChurchEvent.event_date.asc()).all()

    if active_only:
        events = [e for e in events if _is_active(e)]

    total = len(events)
    start = (page - 1) * page_size
    page_events = events[start: start + page_size]

    return APIResponse(
        message="Events retrieved",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
            "events": [_serialize(e) for e in page_events],
        },
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[_REQUIRE_WRITE])
async def create_event(
    session: SessionDep,
    current_user: CurrentUser,
    payload: ChurchEventCreate,
) -> Any:
    """Create a church event (one-time or recurring)."""
    unit = session.query(ChurchUnit).filter(ChurchUnit.id == payload.church_unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Church unit not found")

    event = ChurchEvent(
        church_unit_id=payload.church_unit_id,
        name=payload.name,
        description=payload.description,
        event_date=payload.event_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        location=payload.location,
        is_public=payload.is_public,
    )
    _apply_recurrence(event, payload.recurrence)

    session.add(event)
    session.commit()
    session.refresh(event)

    event = _load_one(session, event.id)
    return APIResponse(message="Event created", data=_serialize(event, include_messages=True))


@router.get("/{event_id}", response_model=APIResponse, dependencies=[_REQUIRE_READ])
async def get_event(session: SessionDep, current_user: CurrentUser, event_id: int) -> Any:
    """Get a single event with all its messages."""
    event = _load_one(session, event_id)
    return APIResponse(message="Event retrieved", data=_serialize(event, include_messages=True))


@router.patch("/{event_id}", response_model=APIResponse, dependencies=[_REQUIRE_WRITE])
async def update_event(
    session: SessionDep,
    current_user: CurrentUser,
    event_id: int,
    payload: ChurchEventUpdate,
) -> Any:
    """Update event fields. Send `recurrence: null` to convert to a one-time event."""
    event = _load_one(session, event_id)

    if payload.name is not None:
        event.name = payload.name
    if payload.description is not None:
        event.description = payload.description
    if payload.event_date is not None:
        event.event_date = payload.event_date
    if payload.start_time is not None:
        event.start_time = payload.start_time
    if payload.end_time is not None:
        event.end_time = payload.end_time
    if payload.location is not None:
        event.location = payload.location
    if payload.is_public is not None:
        event.is_public = payload.is_public
    # `recurrence` key presence in the body means the caller intends to set/clear it
    if "recurrence" in payload.model_fields_set:
        _apply_recurrence(event, payload.recurrence)

    session.commit()
    event = _load_one(session, event_id)
    return APIResponse(message="Event updated", data=_serialize(event, include_messages=True))


@router.delete("/{event_id}", response_model=APIResponse, dependencies=[_REQUIRE_WRITE])
async def delete_event(session: SessionDep, current_user: CurrentUser, event_id: int) -> Any:
    """Permanently delete an event and all its messages."""
    event = session.query(ChurchEvent).filter(ChurchEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    session.delete(event)
    session.commit()
    return APIResponse(message="Event deleted", data={"id": event_id})


@router.post("/{event_id}/terminate", response_model=APIResponse, dependencies=[_REQUIRE_WRITE])
async def terminate_event(
    session: SessionDep,
    current_user: CurrentUser,
    event_id: int,
) -> Any:
    """
    Terminate a recurring event series immediately.
    Sets `terminated_at` to now — the event will no longer appear as active.
    Use DELETE if you want to remove it entirely.
    """
    event = _load_one(session, event_id)
    if not event.is_recurring:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only recurring events can be terminated. Use DELETE to remove a one-time event.",
        )
    if event.terminated_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event series is already terminated.",
        )
    event.terminated_at = datetime.now(timezone.utc)
    session.commit()
    event = _load_one(session, event_id)
    return APIResponse(message="Recurring event series terminated", data=_serialize(event, include_messages=True))


# ── Event Messages ────────────────────────────────────────────────────────────

@router.get("/{event_id}/messages", response_model=APIResponse, dependencies=[_REQUIRE_READ])
async def list_messages(session: SessionDep, current_user: CurrentUser, event_id: int) -> Any:
    """List all messages/reminders for an event."""
    event = _load_one(session, event_id)
    return APIResponse(
        message="Messages retrieved",
        data={
            "event_id": event_id,
            "event_name": event.name,
            "messages": [
                {
                    "id": m.id,
                    "message_type": m.message_type.value,
                    "title": m.title,
                    "content": m.content,
                    "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
                    "is_sent": m.is_sent,
                    "created_by_id": str(m.created_by_id) if m.created_by_id else None,
                    "created_at": m.created_at.isoformat(),
                    "updated_at": m.updated_at.isoformat(),
                }
                for m in (event.messages or [])
            ],
        },
    )


@router.post("/{event_id}/messages", response_model=APIResponse,
             status_code=status.HTTP_201_CREATED, dependencies=[_REQUIRE_WRITE])
async def add_message(
    session: SessionDep,
    current_user: CurrentUser,
    event_id: int,
    payload: EventMessageCreate,
) -> Any:
    """Add a note, announcement, or reminder to an event."""
    event = session.query(ChurchEvent).filter(ChurchEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    msg = EventMessage(
        event_id=event_id,
        message_type=payload.message_type,
        title=payload.title,
        content=payload.content,
        scheduled_at=payload.scheduled_at,
        created_by_id=current_user.id,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)

    return APIResponse(
        message="Message added",
        data={
            "id": msg.id,
            "event_id": msg.event_id,
            "message_type": msg.message_type.value,
            "title": msg.title,
            "content": msg.content,
            "scheduled_at": msg.scheduled_at.isoformat() if msg.scheduled_at else None,
            "is_sent": msg.is_sent,
            "created_by_id": str(msg.created_by_id) if msg.created_by_id else None,
            "created_at": msg.created_at.isoformat(),
            "updated_at": msg.updated_at.isoformat(),
        },
    )


@router.patch("/{event_id}/messages/{message_id}", response_model=APIResponse,
              dependencies=[_REQUIRE_WRITE])
async def update_message(
    session: SessionDep,
    current_user: CurrentUser,
    event_id: int,
    message_id: int,
    payload: EventMessageUpdate,
) -> Any:
    """Update a message attached to an event."""
    msg = session.query(EventMessage).filter(
        EventMessage.id == message_id,
        EventMessage.event_id == event_id,
    ).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if payload.message_type is not None:
        msg.message_type = payload.message_type
    if payload.title is not None:
        msg.title = payload.title
    if payload.content is not None:
        msg.content = payload.content
    if payload.scheduled_at is not None:
        msg.scheduled_at = payload.scheduled_at
    if payload.is_sent is not None:
        msg.is_sent = payload.is_sent

    session.commit()
    session.refresh(msg)

    return APIResponse(
        message="Message updated",
        data={
            "id": msg.id,
            "event_id": msg.event_id,
            "message_type": msg.message_type.value,
            "title": msg.title,
            "content": msg.content,
            "scheduled_at": msg.scheduled_at.isoformat() if msg.scheduled_at else None,
            "is_sent": msg.is_sent,
            "created_by_id": str(msg.created_by_id) if msg.created_by_id else None,
            "created_at": msg.created_at.isoformat(),
            "updated_at": msg.updated_at.isoformat(),
        },
    )


@router.delete("/{event_id}/messages/{message_id}", response_model=APIResponse,
               dependencies=[_REQUIRE_WRITE])
async def delete_message(
    session: SessionDep,
    current_user: CurrentUser,
    event_id: int,
    message_id: int,
) -> Any:
    """Delete a message from an event."""
    msg = session.query(EventMessage).filter(
        EventMessage.id == message_id,
        EventMessage.event_id == event_id,
    ).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    session.delete(msg)
    session.commit()
    return APIResponse(message="Message deleted", data={"id": message_id})
