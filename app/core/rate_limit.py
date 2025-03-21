import time
from typing import Dict, Tuple, Optional
import logging
from fastapi import Request, HTTPException, status

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter implementation with a sliding window algorithm.
    """
    
    def __init__(self):
        self.requests: Dict[str, Tuple[int, float]] = {}  # client_id -> (count, first_request_time)
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get a unique identifier for the client.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Client identifier
        """
        # Use the client's IP address as the identifier
        client_ip = request.client.host if request.client else "unknown"
        
        # Don't try to access request.user as it requires AuthenticationMiddleware
        # Instead, just use the client IP
        return client_ip
    
    async def check_rate_limit(self, request: Request) -> None:
        """
        Check if the request exceeds the rate limit.
        
        Args:
            request: FastAPI request object
            
        Raises:
            HTTPException: If the rate limit is exceeded
        """
        # Skip rate limiting for metrics and health endpoints
        path = request.url.path
        if path.endswith("/metrics") or path.endswith("/health"):
            return
        
        # Get rate limit from settings
        rate_limit = settings.RATE_LIMIT_PER_MINUTE
        
        # Get client ID
        client_id = self._get_client_id(request)
        
        # Get current time
        current_time = time.time()
        
        # Get the client's request history, or create a new one
        count, first_request_time = self.requests.get(client_id, (0, current_time))
        
        # Remove requests older than 1 minute
        if current_time - first_request_time > 60:
            # Reset the counter if the window has passed
            count = 0
            first_request_time = current_time
        
        # Check if the rate limit is exceeded
        if count >= rate_limit:
            # Calculate the time until the rate limit resets
            reset_time = int(first_request_time + 60 - current_time)
            
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={
                    "client_id": client_id,
                    "request_count": count,
                    "rate_limit": rate_limit,
                    "reset_time": reset_time
                }
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"X-Rate-Limit-Reset": str(reset_time)}
            )
        
        # Increment the request count
        self.requests[client_id] = (count + 1, first_request_time)


# Create a global rate limiter instance
rate_limiter = RateLimiter()