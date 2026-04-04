import asyncio
import time
from datetime import datetime, timezone
from typing import Dict

import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db

router = APIRouter()


async def _check_database() -> dict:
    start = time.monotonic()
    try:
        ok = await db.check_connection()
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "status": "healthy" if ok else "unhealthy",
            "latency_ms": latency_ms,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_email() -> dict:
    import aiosmtplib
    missing = [
        k for k, v in {
            "SMTP_USER": settings.SMTP_USER,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
            "EMAILS_FROM_EMAIL": settings.EMAILS_FROM_EMAIL,
        }.items() if not v
    ]
    if missing:
        return {"status": "misconfigured", "missing": missing}

    start = time.monotonic()
    try:
        smtp = aiosmtplib.SMTP(
            hostname="smtp.gmail.com",
            port=465,
            use_tls=True,
            timeout=5,
        )
        await smtp.connect()
        await smtp.quit()
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def _check_sms() -> dict:
    if not settings.ARKESEL_API_KEY:
        return {"status": "misconfigured", "missing": ["ARKESEL_API_KEY"]}

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://sms.arkesel.com/api/v2/sms/send",
                headers={"api-key": settings.ARKESEL_API_KEY, "Content-Type": "application/json"},
                json={"sender": "", "message": "", "recipients": []},
            )
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        # Any HTTP response means the gateway is reachable — that's all we need to confirm.
        # Connection errors / timeouts are the real "unhealthy" signal.
        if resp.status_code in (401, 403):
            return {"status": "misconfigured", "error": "Invalid API key", "http_status": resp.status_code, "latency_ms": latency_ms}
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def _check_scheduler() -> dict:
    from app.services.messaging import scheduler as msg_scheduler
    running = msg_scheduler._scheduler.running
    jobs = (
        [
            {
                "id": j.id,
                "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
            }
            for j in msg_scheduler._scheduler.get_jobs()
        ]
        if running
        else []
    )
    return {"status": "running" if running else "stopped", "jobs": jobs}


_HEALTH_RESPONSE_SCHEMA = {
    "description": "Health status of all services",
    "content": {"application/json": {"schema": {"type": "object"}}},
}


@router.get(
    "",
    response_model=Dict,
    summary="Health Check",
    description="Returns the status of all services: API, database, email, SMS, and message scheduler. Returns 200 when all critical services are healthy, 503 when degraded.",
    responses={
        200: _HEALTH_RESPONSE_SCHEMA,
        503: {**_HEALTH_RESPONSE_SCHEMA, "description": "One or more critical services are degraded"},
    },
)
async def health_check() -> Dict:
    db_result, email_result, sms_result = await asyncio.gather(
        _check_database(),
        _check_email(),
        _check_sms(),
    )
    scheduler_result = _check_scheduler()

    services = {
        "database": db_result,
        "email": email_result,
        "sms": sms_result,
        "scheduler": scheduler_result,
    }

    # Overall status: healthy only if all critical services are healthy
    critical = [db_result, email_result, sms_result]
    all_healthy = all(s["status"] == "healthy" for s in critical)
    any_unhealthy = any(s["status"] == "unhealthy" for s in critical)

    if all_healthy:
        overall = "healthy"
    elif any_unhealthy:
        overall = "degraded"
    else:
        overall = "degraded"

    payload = {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "services": services,
    }

    http_status = (
        status.HTTP_200_OK if overall == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(content=payload, status_code=http_status)
