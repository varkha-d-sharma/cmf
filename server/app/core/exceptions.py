"""Standardized exception classes for API error handling"""

from typing import List, Dict, Any, Optional


class APIException(Exception):
    """Base exception for API errors"""

    def __init__(
        self,
        message: str,
        code: int = 400,
        errors: Optional[List[Dict[str, Any]]] = None,
        data: Any = None,
    ):
        self.message = message
        self.code = code
        self.errors = errors or []
        self.data = data
        super().__init__(self.message)


class ValidationError(APIException):
    """Validation error - 422 Unprocessable Entity"""

    def __init__(
        self, message: str = "Validation error", errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            message=message,
            code=422,
            errors=errors or [],
        )


class NotFoundError(APIException):
    """Resource not found - 404"""

    def __init__(self, resource: str, identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        super().__init__(message=message, code=404)


class UnauthorizedError(APIException):
    """Authentication error - 401"""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message, code=401)


class ForbiddenError(APIException):
    """Permission denied - 403"""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message=message, code=403)


class ConflictError(APIException):
    """Conflict - 409"""

    def __init__(self, message: str = "Conflict"):
        super().__init__(message=message, code=409)


class InternalServerError(APIException):
    """Internal server error - 500"""

    def __init__(self, message: str = "Internal server error", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code=500,
            errors=errors or [],
        )


def create_field_error(field: str, message: str, code: str = "VALIDATION_ERROR") -> Dict[str, Any]:
    """Create a field-level error"""
    return {
        "field": field,
        "message": message,
        "code": code,
    }
