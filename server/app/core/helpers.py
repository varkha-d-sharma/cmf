"""Helper utilities for endpoint wrapping and response standardization"""

from typing import Any, Callable, Optional, Coroutine
from functools import wraps
from fastapi import Request
from server.app.core.responses import success_response, PaginationMeta, APIResponse
from server.app.core.exceptions import InternalServerError
import logging

logger = logging.getLogger(__name__)


def wrap_endpoint_response(
    func: Callable,
    message: str = "Success",
    code: int = 200,
    pagination: Optional[PaginationMeta] = None,
) -> Callable:
    """
    Decorator to wrap endpoint responses in standard format.
    
    Usage:
        @wrap_endpoint_response("Data retrieved successfully")
        async def my_endpoint(request: Request):
            return {"data": "value"}  # Will be wrapped in standard format
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> APIResponse:
        try:
            request: Optional[Request] = None
            # Try to find Request object in args/kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]
            
            request_id = getattr(request.state, "request_id", "") if request else ""
            
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Wrap in standard format
            return success_response(
                data=result,
                message=message,
                code=code,
                pagination=pagination,
                request_id=request_id,
            )
        except Exception as e:
            request_id = getattr(request.state, "request_id", "") if request else ""
            logger.error(
                f"[{request_id}] Error in {func.__name__}: {str(e)}",
                exc_info=True,
                extra={"request_id": request_id},
            )
            raise InternalServerError(f"Error in {func.__name__}: {str(e)}")
    
    return wrapper


def handle_endpoint_error(func: Callable) -> Callable:
    """
    Decorator to add error handling to endpoints.
    Automatically catches exceptions and converts them to proper error responses.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]
            
            request_id = getattr(request.state, "request_id", "") if request else ""
            
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            request_id = getattr(request.state, "request_id", "") if request else ""
            logger.error(
                f"[{request_id}] Unhandled error in {func.__name__}: {str(e)}",
                exc_info=True,
                extra={"request_id": request_id},
            )
            # Re-raise to let global exception handlers deal with it
            raise
    
    return wrapper
