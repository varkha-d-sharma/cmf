from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ResponseMeta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


class StandardResponse(BaseModel):
    status: str
    code: int
    data: Optional[dict[str, Any]] = None
    message: str
    errors: list[ErrorDetail] = Field(default_factory=list)
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class PipelineNameRequest(BaseModel):
    pipeline_name: str = Field(..., min_length=1, description="Name of the pipeline")


class StageNameRequest(BaseModel):
    stage_name: str = Field(..., min_length=1, description="Name of the stage")
