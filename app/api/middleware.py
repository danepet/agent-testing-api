import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

from app.core.metrics import record_api_latency
from app.core.rate_limit import rate_limiter

# Configure logging
logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging request details and adding request ID.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Calculate request processing time
            process_time = time.time() - start_time
            
            # Log request details
            logger.info(
                f"Request processed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "client_host": request.client.host if request.client else None,
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate request processing time
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Error processing request: {request.method} {request.url.path} - {str(e)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "client_host": request.client.host if request.client else None,
                }
            )
            
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for recording API metrics.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip metrics endpoint to avoid circular dependencies
        if path.endswith("/metrics") or path.endswith("/health"):
            return await call_next(request)
        
        # Record API latency
        with record_api_latency(f"{request.method}:{path}"):
            response = await call_next(request)
            
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check rate limit
        await rate_limiter.check_rate_limit(request)
        
        # Process request
        response = await call_next(request)
        
        return response


def add_middleware(app: FastAPI):
    """
    Add all middleware to the FastAPI application.
    """
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)