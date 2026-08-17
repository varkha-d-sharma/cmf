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


class ExecutionIdsRequest(BaseModel):
    exe_ids: list[int] = Field(..., min_items=1, description="List of execution identifiers")


class ArtifactIdsRequest(BaseModel):
    artifact_ids: list[int] = Field(..., min_items=1, description="List of artifact identifiers")


class ArtifactNameRequest(BaseModel):
    artifact_name: str = Field(..., min_length=1, description="Name of the artifact")


class ArtifactNameWithPipelineRequest(BaseModel):
    artifact_name: str = Field(..., min_length=1, description="Name of the artifact")
    pipeline_id: Optional[int] = Field(None, description="Optional pipeline identifier")


class ArtifactIdRequest(BaseModel):
    artifact_id: int = Field(..., description="Artifact identifier")


class ExecutionIdRequest(BaseModel):
    execution_id: int = Field(..., description="Execution identifier")


class ExecutionIdsWithPipelineRequest(BaseModel):
    execution_id: list[int] = Field(..., min_items=1, description="List of execution identifiers")
    pipeline_id: Optional[int] = Field(None, description="Optional pipeline identifier")


class ParentExecutionIdsRequest(BaseModel):
    execution_id: list[int] = Field(..., min_items=1, description="List of execution identifiers")
    pipeline_id: Optional[int] = Field(None, description="Optional pipeline identifier")


class ParentExecutionIdRequest(BaseModel):
    execution_id: int = Field(..., description="Execution identifier")
    pipeline_id: Optional[int] = Field(None, description="Optional pipeline identifier")


class StageIdRequest(BaseModel):
    stage_id: int = Field(..., description="Stage identifier")
    execution_uuid: Optional[str] = Field(None, description="Optional execution UUID")


class MetricsNameRequest(BaseModel):
    metrics_name: str = Field(..., min_length=1, description="Name of the metrics artifact")


class PipelineJsonRequest(BaseModel):
    pipeline_name: str = Field(..., min_length=1, description="Name of the pipeline")
    exec_uuid: Optional[str] = Field(None, description="Optional execution UUID")


class LastSyncTimeRequest(BaseModel):
    last_sync_time: int = Field(..., description="Last sync time in epoch milliseconds")
