"""Helper utilities for endpoint wrapping and response standardization"""

from typing import Any, Callable, Optional, Coroutine
from functools import wraps
from fastapi import Request
from server.app.schemas.responses import success_response, PaginationMeta, APIResponse
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
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Wrap in standard format
            return success_response(
                data=result,
                message=message,
                code=code,
                pagination=pagination,
            )
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {str(e)}",
                exc_info=True,
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
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(
                f"Unhandled error in {func.__name__}: {str(e)}",
                exc_info=True,
            )
            # Re-raise to let global exception handlers deal with it
            raise
    
    return wrapper
