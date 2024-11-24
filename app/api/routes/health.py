from fastapi import APIRouter, status
from datetime import datetime
from typing import Dict
from app.core.config import settings

router = APIRouter()

@router.get("/", response_model=Dict, status_code=status.HTTP_200_OK, summary="Health Check Endpoint",
    description="Returns the current status of the API including uptime and version",)
async def health_check() -> Dict:
    """
    Endpoint to check the health status of the API.
    
    Returns:
        Dict: Contains status, timestamp, and version information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }