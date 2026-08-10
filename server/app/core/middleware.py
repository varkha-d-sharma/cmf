"""Middleware for request processing and tracing"""

from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and track request IDs"""

    async def dispatch(self, request: Request, call_next):
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        
        # Store in request state for access in handlers
        request.state.request_id = request_id
        
        # Log incoming request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path}",
            extra={"request_id": request_id},
        )
        
        # Call the endpoint
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Request-Timestamp"] = (
            request.state.request_id if hasattr(request.state, "timestamp") else ""
        )
        
        return response
