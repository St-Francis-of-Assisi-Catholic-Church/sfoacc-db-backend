from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import time
from typing import Callable

from fastapi.routing import APIRoute

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def custom_generate_unique_id(route: APIRoute) -> str:
    """Generate unique ID for API routes"""
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    generate_unique_id_function=custom_generate_unique_id,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)


# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    """Add processing time to response header"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation Error",
            "errors": exc.errors()
        }
    )

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# api router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint providing API information and documentation links.
    """
    return {
        "message": "Welcome to St Francis Church Management System API",
        "docs": f"{settings.API_V1_STR}/docs",
        "redoc": f"{settings.API_V1_STR}/redoc"
    }

@app.on_event("startup")
async def startup_event():
    """
    Actions to run on application startup
    """
    logger.info("Starting up application...")
    try:
        # Initialize database
        db.init_db()
        
        # Check database connection
        if await db.check_connection():
            logger.info("Successfully connected to database")
        else:
            logger.error("Failed to connect to database")
            raise Exception("Database connection failed")
        
        # Additional startup tasks
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"API Version 1 path: {settings.API_V1_STR}")
        logger.info(f"Backend CORS origins: {settings.BACKEND_CORS_ORIGINS}")
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Actions to run on application shutdown
    """
    logger.info("Shutting down application...")
    try:
        # Add cleanup tasks here
        # For example: close connections, cleanup resources
        logger.info("Cleaning up resources...")
        
        # Log successful shutdown
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

