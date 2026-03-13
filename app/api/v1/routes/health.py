from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import db

router = APIRouter()


@router.get(
    "/",
    response_model=Dict,
    status_code=status.HTTP_200_OK,
    summary="Health Check Endpoint",
    description="Returns the current status of the API and database connectivity",
)
async def health_check() -> Dict:
    db_ok = await db.check_connection()
    payload = {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }
    http_status = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=http_status)