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
)

_LOG_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Each entry: (METHOD, compiled-pattern, success_label, fail_label_or_None)
# fail_label is used when HTTP status >= 400; leave None to use success_label for all codes.
# ORDER MATTERS: more-specific patterns must appear before broader ones.
_SUMMARIES: list[tuple[str, re.Pattern, str, str | None]] = [
    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    ("POST", re.compile(r"^/api/v1/auth/login"),         "Logged in",             "Login failed"),
    ("POST", re.compile(r"^/api/v1/auth/logout"),         "Logged out",            None),
    ("POST", re.compile(r"^/api/v1/auth/otp/request"),    "Requested OTP",         None),
    ("POST", re.compile(r"^/api/v1/auth/otp/verify"),     "Logged in via OTP",     "OTP verification failed"),
    ("POST", re.compile(r"^/api/v1/auth/reset-password"), "Reset password",        "Password reset failed"),

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    ("POST",   re.compile(r"^/api/v1/user-management$"), "Created user", None),
    ("PUT",    re.compile(r"^/api/v1/user-management/(?P<id>[^/]+)$"), "Updated user {id}", None),
    ("DELETE", re.compile(r"^/api/v1/user-management/(?P<id>[^/]+)$"), "Deleted user {id}", None),

    # ------------------------------------------------------------------
    # Parishioners — static sub-routes first (before /{id} catch-alls)
    # ------------------------------------------------------------------
    # Import
    ("POST", re.compile(r"^/api/v1/parishioners/import/batch"), "Imported parishioners (CSV)", None),

    # Verification
    ("POST", re.compile(r"^/api/v1/parishioners/verify/batch"), "Sent batch verification messages", None),
    ("POST", re.compile(r"^/api/v1/parishioners/verify/confirm/(?P<vid>[^/]+)"), "Confirmed verification {vid}", None),
    ("POST", re.compile(r"^/api/v1/parishioners/verify"), "Sent verification message", None),

    # Church-ID generation (GET treated as action)
    ("GET",  re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/generate-church-id"), "Generated church ID for parishioner {id}", None),

    # Occupation
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/occupation$"), "Added occupation for parishioner {id}", None),
    ("PUT",    re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/occupation$"), "Updated occupation for parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/occupation$"), "Deleted occupation for parishioner {id}", None),

    # Emergency contacts — batch before individual
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/emergency-contacts/batch"), "Batch updated emergency contacts for parishioner {id}", None),
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/emergency-contacts"), "Added emergency contact for parishioner {id}", None),
    ("PUT",    re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/emergency-contacts/(?P<cid>[^/]+)"), "Updated emergency contact for parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/emergency-contacts/(?P<cid>[^/]+)"), "Deleted emergency contact for parishioner {id}", None),

    # Medical conditions — batch before individual
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/medical-conditions/batch"), "Batch updated medical conditions for parishioner {id}", None),
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/medical-conditions"), "Added medical condition for parishioner {id}", None),
    ("PUT",    re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/medical-conditions/(?P<cid>[^/]+)"), "Updated medical condition for parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/medical-conditions/(?P<cid>[^/]+)"), "Deleted medical condition for parishioner {id}", None),

    # Family info — batch before single
    ("POST", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/family-info/batch"), "Batch updated family info for parishioner {id}", None),
    ("POST", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/family-info"), "Updated family info for parishioner {id}", None),

    # Sacraments — batch/type before individual
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/sacraments/batch"), "Batch updated sacraments for parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/sacraments/type/(?P<type>[^/]+)"), "Deleted all {type} sacraments for parishioner {id}", None),
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/sacraments"), "Added sacrament record for parishioner {id}", None),
    ("PUT",    re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/sacraments/(?P<sid>[^/]+)"), "Updated sacrament record for parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/sacraments/(?P<sid>[^/]+)"), "Deleted sacrament record for parishioner {id}", None),

    # Skills — batch before individual
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/skills/batch"), "Batch updated skills for parishioner {id}", None),
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/skills"), "Added skill to parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/skills/(?P<sid>[^/]+)"), "Removed skill from parishioner {id}", None),

    # Languages — named actions before generic delete
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/languages/assign"), "Assigned languages to parishioner {id}", None),
    ("POST",   re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/languages/remove"), "Removed languages from parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)/languages/(?P<lid>[^/]+)"), "Removed language from parishioner {id}", None),

    # Core parishioner CRUD (must come after all sub-resource patterns)
    ("POST",   re.compile(r"^/api/v1/parishioners$"), "Created parishioner", None),
    ("PUT",    re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)$"), "Updated parishioner {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parishioners/(?P<id>[^/]+)$"), "Deleted parishioner {id}", None),

    # ------------------------------------------------------------------
    # Societies
    # ------------------------------------------------------------------
    # Leadership — before member/general routes
    ("POST",   re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/leadership$"), "Added leadership position to society {id}", None),
    ("PUT",    re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/leadership/(?P<lid>[^/]+)$"), "Updated leadership position in society {id}", None),
    ("DELETE", re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/leadership/(?P<lid>[^/]+)$"), "Deleted leadership position from society {id}", None),
    # Members
    ("POST",   re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/members$"), "Added members to society {id}", None),
    ("DELETE", re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/members$"), "Removed members from society {id}", None),
    ("PUT",    re.compile(r"^/api/v1/societies/(?P<id>[^/]+)/members/(?P<pid>[^/]+)/status"), "Updated member status in society {id}", None),
    # Core society CRUD
    ("POST",   re.compile(r"^/api/v1/societies$"), "Created society", None),
    ("PUT",    re.compile(r"^/api/v1/societies/(?P<id>[^/]+)$"), "Updated society {id}", None),
    ("DELETE", re.compile(r"^/api/v1/societies/(?P<id>[^/]+)$"), "Deleted society {id}", None),

    # ------------------------------------------------------------------
    # Church communities
    # ------------------------------------------------------------------
    ("POST",   re.compile(r"^/api/v1/church-community$"), "Created community", None),
    ("PUT",    re.compile(r"^/api/v1/church-community/(?P<id>[^/]+)$"), "Updated community {id}", None),
    ("DELETE", re.compile(r"^/api/v1/church-community/(?P<id>[^/]+)$"), "Deleted community {id}", None),

    # ------------------------------------------------------------------
    # Languages (reference data)
    # ------------------------------------------------------------------
    ("POST",   re.compile(r"^/api/v1/languages/available$"), "Created language", None),
    ("PUT",    re.compile(r"^/api/v1/languages/available/(?P<id>[^/]+)$"), "Updated language {id}", None),
    ("DELETE", re.compile(r"^/api/v1/languages/available/(?P<id>[^/]+)$"), "Deleted language {id}", None),

    # ------------------------------------------------------------------
    # Parish — outstations (specific first, then general /parish routes)
    # ------------------------------------------------------------------
    # Outstation mass schedules
    ("POST",   re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/mass-schedules$"), "Added mass schedule to outstation {oid}", None),
    ("PUT",    re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/mass-schedules/(?P<sid>[^/]+)$"), "Updated mass schedule in outstation {oid}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/mass-schedules/(?P<sid>[^/]+)$"), "Deleted mass schedule from outstation {oid}", None),
    # Outstation leadership
    ("POST",   re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/leadership$"), "Added leadership to outstation {oid}", None),
    ("PUT",    re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/leadership/(?P<lid>[^/]+)$"), "Updated leadership in outstation {oid}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/leadership/(?P<lid>[^/]+)$"), "Deleted leadership from outstation {oid}", None),
    # Outstation events
    ("POST",   re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/events$"), "Created event for outstation {oid}", None),
    ("PUT",    re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/events/(?P<eid>[^/]+)$"), "Updated event in outstation {oid}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/outstations/(?P<oid>[^/]+)/events/(?P<eid>[^/]+)$"), "Deleted event from outstation {oid}", None),
    # Outstation CRUD
    ("POST",   re.compile(r"^/api/v1/parish/outstations$"), "Created outstation", None),
    ("PUT",    re.compile(r"^/api/v1/parish/outstations/(?P<id>[^/]+)$"), "Updated outstation {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/outstations/(?P<id>[^/]+)$"), "Deleted outstation {id}", None),

    # Parish units
    ("POST",   re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/mass-schedules$"), "Added mass schedule to unit {id}", None),
    ("PUT",    re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/mass-schedules/(?P<sid>[^/]+)$"), "Updated mass schedule in unit {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/mass-schedules/(?P<sid>[^/]+)$"), "Deleted mass schedule from unit {id}", None),
    ("POST",   re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/leadership$"), "Added leadership to unit {id}", None),
    ("PUT",    re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/leadership/(?P<lid>[^/]+)$"), "Updated leadership in unit {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/leadership/(?P<lid>[^/]+)$"), "Deleted leadership from unit {id}", None),
    ("POST",   re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/events$"), "Created event for unit {id}", None),
    ("PUT",    re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/events/(?P<eid>[^/]+)$"), "Updated event in unit {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)/events/(?P<eid>[^/]+)$"), "Deleted event from unit {id}", None),
    ("POST",   re.compile(r"^/api/v1/parish/units$"), "Created church unit", None),
    ("PUT",    re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)$"), "Updated church unit {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/units/(?P<id>[^/]+)$"), "Deleted church unit {id}", None),

    # Parish mass schedules
    ("POST",   re.compile(r"^/api/v1/parish/mass-schedules$"), "Created parish mass schedule", None),
    ("PUT",    re.compile(r"^/api/v1/parish/mass-schedules/(?P<id>[^/]+)$"), "Updated parish mass schedule {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/mass-schedules/(?P<id>[^/]+)$"), "Deleted parish mass schedule {id}", None),

    # Parish leadership
    ("POST",   re.compile(r"^/api/v1/parish/leadership$"), "Added parish leadership", None),
    ("PUT",    re.compile(r"^/api/v1/parish/leadership/(?P<id>[^/]+)$"), "Updated parish leadership {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/leadership/(?P<id>[^/]+)$"), "Deleted parish leadership {id}", None),

    # Parish events
    ("POST",   re.compile(r"^/api/v1/parish/events$"), "Created parish event", None),
    ("PUT",    re.compile(r"^/api/v1/parish/events/(?P<id>[^/]+)$"), "Updated parish event {id}", None),
    ("DELETE", re.compile(r"^/api/v1/parish/events/(?P<id>[^/]+)$"), "Deleted parish event {id}", None),

    # Parish (top-level)
    ("PUT",    re.compile(r"^/api/v1/parish$"), "Updated parish", None),

    # ------------------------------------------------------------------
    # Admin — settings & RBAC
    # ------------------------------------------------------------------
    ("PUT",    re.compile(r"^/api/v1/admin/settings/auth"), "Updated auth settings", None),
    ("PUT",    re.compile(r"^/api/v1/admin/settings/app"), "Updated app settings", None),
    ("PUT",    re.compile(r"^/api/v1/admin/settings"), "Updated settings", None),
    ("POST",   re.compile(r"^/api/v1/admin/roles$"), "Created role", None),
    ("PUT",    re.compile(r"^/api/v1/admin/roles/(?P<id>[^/]+)/permissions"), "Updated role {id} permissions", None),
    ("PUT",    re.compile(r"^/api/v1/admin/roles/(?P<id>[^/]+)$"), "Updated role {id}", None),
    ("DELETE", re.compile(r"^/api/v1/admin/roles/(?P<id>[^/]+)$"), "Deleted role {id}", None),

    # ------------------------------------------------------------------
    # Bulk messaging
    # ------------------------------------------------------------------
    ("POST",   re.compile(r"^/api/v1/bulk-message/schedule"), "Scheduled bulk message", None),
    ("DELETE", re.compile(r"^/api/v1/bulk-message/scheduled/(?P<id>[^/]+)"), "Cancelled scheduled message {id}", None),
    ("POST",   re.compile(r"^/api/v1/bulk-message"), "Sent bulk message", None),
]


def _build_summary(method: str, path: str, status_code: int) -> str:
    is_failure = status_code >= 400
    for entry in _SUMMARIES:
        m, pattern, success_label = entry[0], entry[1], entry[2]
        fail_label = entry[3] if len(entry) > 3 else None
        if m != method:
            continue
        match = pattern.match(path)
        if match:
            label = (fail_label if is_failure and fail_label else success_label)
            try:
                return label.format(**match.groupdict())
            except KeyError:
                return label
    # Fallback
    parts = [p for p in path.split("/") if p and p not in ("api", "v1")]
    return f"{method} /{'/'.join(parts)}"


def _extract_user_id(request: Request) -> str | None:
    # Endpoints that authenticate the user (login, OTP verify) set this on
    # request.state so the audit log captures who just logged in.
    state_uid = getattr(request.state, "audit_user_id", None)
    if state_uid:
        return state_uid

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
        summary = _build_summary(method, path, response.status_code)

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
