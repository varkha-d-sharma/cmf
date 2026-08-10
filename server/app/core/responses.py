"""Unified API response wrapper for all endpoints"""

from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel
import json


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = 1
    per_page: int = 10
    total: int = 0
    has_next: bool = False
    has_prev: bool = False


class ResponseMeta(BaseModel):
    """Response metadata"""
    request_id: str = ""
    timestamp: str = ""
    pagination: Optional[PaginationMeta] = None


class APIResponse(BaseModel):
    """Standard response wrapper for all API endpoints"""
    status: str  # "success", "error", "partial"
    code: int
    data: Any = None
    message: str = ""
    errors: List[Dict[str, Any]] = []
    meta: ResponseMeta = ResponseMeta()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v else None,
        }


def success_response(
    data: Any = None,
    message: str = "Success",
    code: int = 200,
    pagination: Optional[PaginationMeta] = None,
    request_id: str = "",
) -> APIResponse:
    """Create a success response"""
    return APIResponse(
        status="success",
        code=code,
        data=data,
        message=message,
        errors=[],
        meta=ResponseMeta(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            pagination=pagination,
        ),
    )


def error_response(
    message: str = "Error",
    code: int = 400,
    errors: Optional[List[Dict[str, Any]]] = None,
    data: Any = None,
    request_id: str = "",
) -> APIResponse:
    """Create an error response"""
    return APIResponse(
        status="error",
        code=code,
        data=data,
        message=message,
        errors=errors or [],
        meta=ResponseMeta(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        ),
    )


def partial_response(
    data: Any = None,
    message: str = "Partial success",
    code: int = 206,
    errors: Optional[List[Dict[str, Any]]] = None,
    pagination: Optional[PaginationMeta] = None,
    request_id: str = "",
) -> APIResponse:
    """Create a partial success response"""
    return APIResponse(
        status="partial",
        code=code,
        data=data,
        message=message,
        errors=errors or [],
        meta=ResponseMeta(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            pagination=pagination,
        ),
    )
