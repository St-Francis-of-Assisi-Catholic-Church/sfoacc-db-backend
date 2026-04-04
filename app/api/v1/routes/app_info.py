"""
Public app info endpoints — no authentication required.
All responses are safe to cache indefinitely on the client.

  GET /api/v1/app/config         — branding, contact info, version, currency
  GET /api/v1/app/login-config   — login methods + groups + church units (login page bootstrap)
  GET /api/v1/app/groups         — available groups (name, label, description)
  GET /api/v1/app/church-units   — active church units (id, name, type)
"""
from typing import Any
from fastapi import APIRouter

from app.api.deps import SessionDep
from app.services.otp_service import is_method_enabled

router = APIRouter()

# ── App config ────────────────────────────────────────────────────────────────

_APP_CONFIG_KEYS = [
    "app.name",
    "app.description",
    "app.version",
    "app.church_code",
    "app.currency_symbol",
    "app.currency_code",
    "app.contact_email",
    "app.contact_phone",
    "app.website",
    "app.address",
    "app.logo_url",
    "app.support_email",
]

_APP_CONFIG_DEFAULTS = {
    "app.name": "Parish Database Management System",
    "app.description": "Church records and community management platform.",
    "app.version": "1.0.0",
    "app.church_code": "SFOACC",
    "app.currency_symbol": "¢",
    "app.currency_code": "GHS",
    "app.contact_email": "",
    "app.contact_phone": "",
    "app.website": "",
    "app.address": "",
    "app.logo_url": "",
    "app.support_email": "",
}


@router.get("/config")
async def get_app_config(session: SessionDep) -> Any:
    """
    App branding and contact config.
    Single source of truth for app name, version, church code, currency, contact info, etc.
    Updated by admins via PUT /api/v1/admin/settings/app.
    """
    from app.models.settings import ParishSettings
    rows = session.query(ParishSettings).filter(
        ParishSettings.key.in_(_APP_CONFIG_KEYS)
    ).all()
    config = {**_APP_CONFIG_DEFAULTS}
    for row in rows:
        config[row.key] = row.value or ""
    return {"data": {k.replace("app.", ""): v for k, v in config.items()}}


# ── Login config (bootstrap) ─────────────────────────────────────────────────

@router.get("/login-config")
async def get_login_config(session: SessionDep) -> Any:
    """
    Everything the login page needs in one call:
      - login_methods: which methods are currently enabled

    Frontend logic:
      - Show password field only when login_methods.password == true
      - Show OTP option only when otp_email or otp_sms == true
    """
    return {
        "data": {
            "login_methods": {
                "password": is_method_enabled(session, "password"),
                "otp_email": is_method_enabled(session, "otp_email"),
                "otp_sms": is_method_enabled(session, "otp_sms"),
            },
        }
    }


# ── Groups ────────────────────────────────────────────────────────────────────

@router.get("/groups")
async def list_groups(session: SessionDep) -> Any:
    """
    All available groups (name, label, description).
    Used to populate group selector dropdowns.
    """
    from app.models.rbac import Role
    roles = session.query(Role.name, Role.label, Role.description).order_by(Role.label).all()
    return {"data": [{"name": r.name, "label": r.label, "description": r.description} for r in roles]}


# ── Church units ──────────────────────────────────────────────────────────────

@router.get("/church-units")
async def list_church_units(session: SessionDep) -> Any:
    """
    All active church units (id, name, type).
    Used to populate church unit selector dropdowns.
    """
    from app.models.parish import ChurchUnit
    units = (
        session.query(ChurchUnit.id, ChurchUnit.name, ChurchUnit.type)
        .filter(ChurchUnit.is_active == True)  # noqa: E712
        .order_by(ChurchUnit.type, ChurchUnit.name)
        .all()
    )
    return {"data": [{"id": u.id, "name": u.name, "type": u.type.value} for u in units]}
