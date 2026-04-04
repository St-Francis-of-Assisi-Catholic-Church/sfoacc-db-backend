import time
import json
import logging
from typing import Callable
from datetime import datetime
from uuid import uuid4

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Configure logger
logger = logging.getLogger(__name__)


class LoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    Logs request details, response status, and processing time.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID for tracking
        request_id = str(uuid4())
        
        # Start time for calculating request duration
        start_time = time.time()
        
        # Log request details
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                request_body = body.decode("utf-8") if body else None
                # Create a new request with the same body for downstream processing
                from starlette.datastructures import Headers
                from starlette.requests import Request as StarletteRequest
                
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request = StarletteRequest(
                    scope=request.scope,
                    receive=receive,
                    send=request._send
                )
            except Exception as e:
                logger.error(f"Error reading request body: {e}")
        
        # Log incoming request
        logger.info(
            f"REQUEST [{request_id}] - {request.method} {request.url.path} "
            f"- Client: {request.client.host if request.client else 'Unknown'}"
        )
        
        if request_body:
            _SENSITIVE_FIELDS = {"password", "new_password", "temp_password", "old_password", "secret", "token"}
            try:
                body_dict = json.loads(request_body)
                for field in _SENSITIVE_FIELDS:
                    if field in body_dict:
                        body_dict[field] = "***REDACTED***"
                logger.debug(f"Request Body [{request_id}]: {json.dumps(body_dict)}")
            except json.JSONDecodeError:
                logger.debug(f"Request Body [{request_id}]: {request_body[:200]}...")
        
        # Process request
        response = await call_next(request)
        
        # Calculate request duration
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"RESPONSE [{request_id}] - Status: {response.status_code} "
            f"- Duration: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class EndpointLoggerRoute(APIRoute):
    """
    Custom APIRoute class that logs endpoint-specific information.
    Can be used for more granular logging per endpoint.
    """
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            # Log endpoint access
            logger.debug(
                f"Endpoint accessed: {request.method} {request.url.path} "
                f"- Function: {self.endpoint.__name__}"
            )
            
            response = await original_route_handler(request)
            return response
        
        return custom_route_handler


def setup_logging(
    level: str = "INFO",
    format_string: str = None,
    log_file: str = None
) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        log_file: Optional file path to write logs to
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(console_handler)
    
    # Setup file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific loggers to appropriate levels
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class RequestContextLoggerMiddleware(BaseHTTPMiddleware):
    """
    Advanced middleware that adds request context to all log messages
    during request processing.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid4())
        
        # Store request context in request state
        request.state.request_id = request_id
        request.state.start_time = time.time()
        
        # Create a context filter for this request
        class RequestContextFilter(logging.Filter):
            def filter(self, record):
                record.request_id = request_id
                record.method = request.method
                record.path = request.url.path
                return True
        
        # Add filter to logger
        context_filter = RequestContextFilter()
        logger.addFilter(context_filter)
        
        try:
            response = await call_next(request)
            
            # Log successful request completion
            duration = time.time() - request.state.start_time
            logger.info(
                f"Request completed successfully",
                extra={
                    "status_code": response.status_code,
                    "duration": f"{duration:.3f}s"
                }
            )
            
        except Exception as e:
            # Log exception
            duration = time.time() - request.state.start_time
            logger.error(
                f"Request failed with exception: {str(e)}",
                extra={
                    "duration": f"{duration:.3f}s",
                    "exception": str(e)
                }
            )
            raise
        
        finally:
            # Remove filter after request is processed
            logger.removeFilter(context_filter)
        
        return response


# Utility function for structured logging
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)