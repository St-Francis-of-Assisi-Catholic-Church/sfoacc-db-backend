"""
Audit log middleware.
Logs every state-changing request (POST, PUT, PATCH, DELETE) to the audit_logs table.
Runs after the response so it never blocks the request.
"""
import re
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from jwt import DecodeError, ExpiredSignatureError, api_jwt

from app.core.config import settings
from app.core.security import ALGORITHM

logger = logging.getLogger(__name__)

# Paths to skip entirely (read-only or system routes)
_SKIP_PREFIXES = (
    "/api/v1/health",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
    "/api/v1/guide",
    "/",
)

_LOG_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Maps (METHOD, path-pattern) → human label
_SUMMARIES: list[tuple[str, re.Pattern, str]] = [
    # Auth
    ("POST", re.compile(r"^/api/v1/auth/login"), "Logged in"),
    ("POST", re.compile(r"^/api/v1/auth/otp/request"), "Requested OTP"),
    ("POST", re.compile(r"^/api/v1/auth/otp/verify"), "Verified OTP"),
    ("POST", re.compile(r"^/api/v1/auth/reset-password"), "Reset password"),
    # Users
    ("POST",   re.compile(r"^/api/v1/user-management$"), "Created user"),
    ("PUT",    re.compile(r"^/api/v1/user-management/(?P<id>[^/]+)$"), "Updated user {id}"),
    ("DELETE", re.compile(r"^/api/v1/user-management/(?P<id>[^/]+)$"), "Deleted user {id}"),
    # Parishioners
    ("POST",   re.compile(r"^/api/v1/parishioners$"), "Created parishioner"),
    ("PUT",    re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)$"), "Updated parishioner {id}"),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)$"), "Deleted parishioner {id}"),
    ("POST",   re.compile(r"^/api/v1/parishioners/upload"), "Imported parishioners (CSV)"),
    ("GET",    re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/generate-church-id"), "Generated church ID for {id}"),
    # Societies
    ("POST",   re.compile(r"^/api/v1/societies$"), "Created society"),
    ("PUT",    re.compile(r"^/api/v1/societies/(?P<id>[^/]+)$"), "Updated society {id}"),
    ("DELETE", re.compile(r"^/api/v1/societies/(?P<id>[^/]+)$"), "Deleted society {id}"),
    ("POST",   re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/members$"), "Added members to society {id}"),
    ("DELETE", re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/members$"), "Removed members from society {id}"),
    # Communities
    ("POST",   re.compile(r"^/api/v1/church-community$"), "Created community"),
    ("PUT",    re.compile(r"^/api/v1/church-community/(?P<id>[^/]+)$"), "Updated community {id}"),
    ("DELETE", re.compile(r"^/api/v1/church-community/(?P<id>[^/]+)$"), "Deleted community {id}"),
    # Parish / outstations
    ("PUT",    re.compile(r"^/api/v1/parish$"), "Updated parish"),
    ("POST",   re.compile(r"^/api/v1/parish/outstations$"), "Created outstation"),
    ("PUT",    re.compile(r"^/api/v1/parish/outstations/(?P<id>[^/]+)$"), "Updated outstation {id}"),
    ("DELETE", re.compile(r"^/api/v1/parish/outstations/(?P<id>[^/]+)$"), "Deleted outstation {id}"),
    # Mass schedules
    ("POST",   re.compile(r"^/api/v1/parish/mass-schedules$"), "Created parish mass schedule"),
    ("PUT",    re.compile(r"^/api/v1/parish/mass-schedules/(?P<id>[^/]+)$"), "Updated parish mass schedule {id}"),
    ("DELETE", re.compile(r"^/api/v1/parish/mass-schedules/(?P<id>[^/]+)$"), "Deleted parish mass schedule {id}"),
    # Admin — settings & RBAC
    ("PUT",    re.compile(r"^/api/v1/admin/settings/auth"), "Updated auth settings"),
    ("PUT",    re.compile(r"^/api/v1/admin/settings/app"), "Updated app settings"),
    ("PUT",    re.compile(r"^/api/v1/admin/settings"), "Updated settings"),
    ("POST",   re.compile(r"^/api/v1/admin/roles$"), "Created role"),
    ("PUT",    re.compile(r"^/api/v1/admin/roles/(?P<id>[^/]+)/permissions"), "Updated role {id} permissions"),
    ("PUT",    re.compile(r"^/api/v1/admin/roles/(?P<id>[^/]+)$"), "Updated role {id}"),
    ("DELETE", re.compile(r"^/api/v1/admin/roles/(?P<id>[^/]+)$"), "Deleted role {id}"),
    # Bulk messaging
    ("POST",   re.compile(r"^/api/v1/bulk-message"), "Sent bulk message"),
]


def _build_summary(method: str, path: str) -> str:
    for m, pattern, template in _SUMMARIES:
        if m != method:
            continue
        match = pattern.match(path)
        if match:
            try:
                return template.format(**match.groupdict())
            except KeyError:
                return template
    # Fallback
    parts = [p for p in path.split("/") if p and p not in ("api", "v1")]
    return f"{method} /{'/'.join(parts)}"


def _extract_user_id(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        payload = api_jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except (DecodeError, ExpiredSignatureError, Exception):
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        method = request.method
        path = request.url.path

        # Only log state-changing methods (plus GET generate-church-id which is actually an action)
        should_log = (
            method in _LOG_METHODS
            or "generate-church-id" in path
        ) and not any(path.startswith(p) for p in _SKIP_PREFIXES)

        if not should_log:
            return response

        logger.info("AUDIT: %s %s → %s", method, path, response.status_code)

        user_id = _extract_user_id(request)
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent", "")[:500]
        summary = _build_summary(method, path)

        # Write to DB — use raw session factory to avoid context manager conflicts
        try:
            from app.core.database import db
            from app.models.audit import AuditLog
            session = db.session_factory()
            try:
                session.add(AuditLog(
                    user_id=user_id,
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    ip_address=ip,
                    user_agent=user_agent,
                    summary=summary,
                ))
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        except Exception:
            logger.exception("Failed to write audit log for %s %s", method, path)

        return response
