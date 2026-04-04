import logging
from typing import Any, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep, CurrentUser, require_permission
from app.models.parish import ChurchUnit, ChurchUnitType
from app.models.settings import ParishSettings
from app.schemas.settings import SettingRead, SettingsBulkUpdate
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_REQUIRE_SETTINGS = require_permission("admin:settings")
_REQUIRE_AUTH_CONFIG = require_permission("admin:auth_config")

_AUTH_SETTING_KEYS = {
    "auth.password_enabled",
    "auth.otp_sms_enabled",
    "auth.otp_email_enabled",
    "auth.otp_expiry_minutes",
    "auth.otp_code_length",
}

_APP_SETTING_KEYS = {
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
}


@router.get("", response_model=APIResponse, dependencies=[_REQUIRE_SETTINGS])
async def get_settings(session: SessionDep, current_user: CurrentUser) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    settings = session.query(ParishSettings).filter(ParishSettings.church_unit_id == parish.id).all()
    return APIResponse(message="Settings retrieved", data=[SettingRead.model_validate(s) for s in settings])


@router.put("", response_model=APIResponse, dependencies=[_REQUIRE_SETTINGS])
async def update_settings(*, session: SessionDep, current_user: CurrentUser, data: SettingsBulkUpdate) -> Any:
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")
    updated = []
    for key, value in data.settings.items():
        setting = session.query(ParishSettings).filter(
            ParishSettings.church_unit_id == parish.id,
            ParishSettings.key == key,
        ).first()
        if setting:
            setting.value = str(value) if value is not None else None
        else:
            setting = ParishSettings(church_unit_id=parish.id, key=key, value=str(value) if value is not None else None)
            session.add(setting)
        updated.append(setting)
    session.commit()
    return APIResponse(message=f"Updated {len(updated)} settings", data=[SettingRead.model_validate(s) for s in updated])


# ── Auth method configuration ─────────────────────────────────────────────────

class AppConfigUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: str | None = None
    church_code: str | None = None
    currency_symbol: str | None = None
    currency_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None
    address: str | None = None
    logo_url: str | None = None
    support_email: str | None = None


@router.get("/app", response_model=APIResponse, dependencies=[_REQUIRE_SETTINGS])
async def get_app_config(session: SessionDep, current_user: CurrentUser) -> Any:
    """Get current app branding and contact configuration."""
    rows = session.query(ParishSettings).filter(
        ParishSettings.key.in_(_APP_SETTING_KEYS)
    ).all()
    return APIResponse(
        message="App configuration retrieved",
        data={r.key.replace("app.", ""): r.value for r in rows},
    )


@router.put("/app", response_model=APIResponse, dependencies=[_REQUIRE_SETTINGS])
async def update_app_config(
    *, session: SessionDep, current_user: CurrentUser, data: AppConfigUpdate
) -> Any:
    """Update app branding and contact info. Reflected immediately on the public /auth/app-config endpoint."""
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")

    updates = {
        f"app.{k}": v
        for k, v in data.model_dump(exclude_unset=True).items()
        if v is not None
    }

    if not updates:
        return APIResponse(message="Nothing to update", data={})

    for key, value in updates.items():
        row = session.query(ParishSettings).filter(ParishSettings.key == key).first()
        if row:
            row.value = value
        else:
            row = ParishSettings(church_unit_id=parish.id, key=key, value=value)
            session.add(row)

    session.commit()
    return APIResponse(
        message=f"Updated {len(updates)} app settings",
        data={k.replace("app.", ""): v for k, v in updates.items()},
    )


class AuthConfigUpdate(BaseModel):
    password_enabled: bool | None = None
    otp_sms_enabled: bool | None = None
    otp_email_enabled: bool | None = None
    otp_expiry_minutes: int | None = None
    otp_code_length: int | None = None


@router.get("/auth", response_model=APIResponse, dependencies=[_REQUIRE_AUTH_CONFIG])
async def get_auth_config(session: SessionDep, current_user: CurrentUser) -> Any:
    """Get current authentication method configuration."""
    rows = session.query(ParishSettings).filter(
        ParishSettings.key.in_(_AUTH_SETTING_KEYS)
    ).all()
    return APIResponse(
        message="Auth configuration retrieved",
        data={r.key.replace("auth.", ""): r.value for r in rows},
    )


@router.put("/auth", response_model=APIResponse, dependencies=[_REQUIRE_AUTH_CONFIG])
async def update_auth_config(
    *, session: SessionDep, current_user: CurrentUser, data: AuthConfigUpdate
) -> Any:
    """
    Configure which login methods are enabled.
    Requires admin:auth_config permission (super admin only by default).
    """
    parish = session.query(ChurchUnit).filter(ChurchUnit.type == ChurchUnitType.PARISH).first()
    if not parish:
        raise HTTPException(status_code=404, detail="Parish not configured")

    updates = {
        k: v for k, v in {
            "auth.password_enabled":   str(data.password_enabled).lower() if data.password_enabled is not None else None,
            "auth.otp_sms_enabled":    str(data.otp_sms_enabled).lower() if data.otp_sms_enabled is not None else None,
            "auth.otp_email_enabled":  str(data.otp_email_enabled).lower() if data.otp_email_enabled is not None else None,
            "auth.otp_expiry_minutes": str(data.otp_expiry_minutes) if data.otp_expiry_minutes is not None else None,
            "auth.otp_code_length":    str(data.otp_code_length) if data.otp_code_length is not None else None,
        }.items()
        if v is not None
    }

    if not updates:
        return APIResponse(message="Nothing to update", data={})

    for key, value in updates.items():
        row = session.query(ParishSettings).filter(ParishSettings.key == key).first()
        if row:
            row.value = value
        else:
            row = ParishSettings(church_unit_id=parish.id, key=key, value=value)
            session.add(row)

    session.commit()
    return APIResponse(
        message=f"Updated {len(updates)} auth settings",
        data={k.replace("auth.", ""): v for k, v in updates.items()},
    )
