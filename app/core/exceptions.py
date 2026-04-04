from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def make_json_safe(obj):
    """Recursively convert objects to JSON-safe format"""
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(item) for item in obj]
    elif isinstance(obj, Exception):
        return str(obj)
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors and return properly formatted JSON responses
    """
    logger.error(f"Validation error: {exc.errors()}")

    # Extract error details and make them JSON serializable
    safe_errors = make_json_safe(exc.errors())

    response_content = {
        "detail": "Validation error",
        "errors": safe_errors,
        # "timestamp": datetime.utcnow().isoformat()
    }

    logger.error(f"Request failed: {response_content}")

    return JSONResponse(
        status_code=422,
        content=response_content
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions
    """
    logger.error(f"HTTP error: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            # "status_code": exc.status_code,
            # "timestamp": datetime.utcnow().isoformat()
        },
        headers=exc.headers
    )

async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle general exceptions
    """
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            # "timestamp": datetime.utcnow().isoformat()
        }
    )
