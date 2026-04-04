"""OTP generation, storage, verification, and delivery."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.otp import OTPCode
from app.models.settings import ParishSettings
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Settings helpers ──────────────────────────────────────────────────────────

_AUTH_DEFAULTS = {
    "auth.password_enabled": "true",
    "auth.otp_sms_enabled": "false",
    "auth.otp_email_enabled": "false",
    "auth.otp_expiry_minutes": "10",
    "auth.otp_code_length": "6",
}


def get_auth_setting(session: Session, key: str) -> str:
    row = session.query(ParishSettings).filter(ParishSettings.key == key).first()
    if row and row.value is not None:
        return row.value
    return _AUTH_DEFAULTS.get(key, "false")


def is_method_enabled(session: Session, method: str) -> bool:
    """method: 'password' | 'otp_sms' | 'otp_email'"""
    return get_auth_setting(session, f"auth.{method}_enabled").lower() == "true"


# ── OTP lifecycle ─────────────────────────────────────────────────────────────

def _hash_code(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_otp(session: Session, user: User) -> str:
    """
    Generate one OTP code for the user, invalidate all previous unused codes,
    and return the raw code. The same code is sent to all available channels.
    """
    length = int(get_auth_setting(session, "auth.otp_code_length"))
    expiry_minutes = int(get_auth_setting(session, "auth.otp_expiry_minutes"))

    # Invalidate all existing unused OTPs for this user
    session.query(OTPCode).filter(
        OTPCode.user_id == user.id,
        OTPCode.used == False,  # noqa: E712
    ).update({"used": True})

    raw_code = "".join(str(secrets.randbelow(10)) for _ in range(length))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

    otp = OTPCode(
        user_id=user.id,
        code_hash=_hash_code(raw_code),
        delivery="otp",
        expires_at=expires_at,
    )
    session.add(otp)
    session.flush()
    return raw_code


def verify_otp(session: Session, user: User, raw_code: str) -> bool:
    """
    Verify the raw OTP code regardless of which channel delivered it.
    Marks it as used on success. Returns True on match, False otherwise.
    """
    now = datetime.now(timezone.utc)
    code_hash = _hash_code(raw_code)

    otp = (
        session.query(OTPCode)
        .filter(
            OTPCode.user_id == user.id,
            OTPCode.code_hash == code_hash,
            OTPCode.used == False,  # noqa: E712
            OTPCode.expires_at > now,
        )
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if not otp:
        return False

    otp.used = True
    return True


# ── Delivery helpers ──────────────────────────────────────────────────────────

def send_otp_sms(user: User, code: str) -> bool:
    """Send OTP via SMS. Returns True if dispatched."""
    if not user.phone:
        return False
    try:
        from app.services.sms.service import sms_service
        sms_service.send_sms(
            phone_numbers=[user.phone],
            message=f"Your SFOACC login code is: {code}\nExpires in 10 minutes. Do not share.",
        )
        return True
    except Exception:
        logger.exception("Failed to send OTP SMS to user %s", user.id)
        return False


async def send_otp_email(user: User, code: str) -> bool:
    """Send OTP via email. Returns True if dispatched."""
    try:
        from app.services.email.service import email_service
        await email_service.send_otp_code(
            email=user.email,
            full_name=user.full_name,
            code=code,
        )
        return True
    except Exception:
        logger.exception("Failed to send OTP email to user %s", user.id)
        return False
