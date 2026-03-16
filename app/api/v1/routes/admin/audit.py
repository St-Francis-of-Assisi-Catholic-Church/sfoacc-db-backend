import logging
from typing import Any, Optional
from fastapi import APIRouter, Query
from sqlalchemy import desc

from app.api.deps import SessionDep, CurrentUser, require_permission
from app.models.audit import AuditLog
from app.models.user import User as UserModel
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_REQUIRE = require_permission("admin:all")


@router.get("", response_model=APIResponse, dependencies=[_REQUIRE])
async def list_audit_logs(
    session: SessionDep,
    current_user: CurrentUser,
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    search: Optional[str] = Query(None, description="Search in path or summary"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> Any:
    """
    Audit log — all state-changing actions across the system.
    Super admin only.
    """
    q = session.query(AuditLog).order_by(desc(AuditLog.created_at))

    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if method:
        q = q.filter(AuditLog.method == method.upper())
    if search:
        term = f"%{search}%"
        q = q.filter(
            AuditLog.summary.ilike(term) | AuditLog.path.ilike(term)
        )

    total = q.count()
    logs = q.offset(skip).limit(limit).all()

    # Enrich with user name
    user_ids = {log.user_id for log in logs if log.user_id}
    users = {
        str(u.id): u.full_name
        for u in session.query(UserModel.id, UserModel.full_name)
        .filter(UserModel.id.in_(user_ids))
        .all()
    } if user_ids else {}

    return APIResponse(
        message=f"{total} audit log entries",
        data={
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "user_name": users.get(log.user_id or "", "Unknown") if log.user_id else "Unauthenticated",
                    "method": log.method,
                    "path": log.path,
                    "status_code": log.status_code,
                    "ip_address": log.ip_address,
                    "summary": log.summary,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        },
    )
