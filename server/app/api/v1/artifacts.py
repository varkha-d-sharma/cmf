from cmflib.cmfquery import CmfQuery
from fastapi import APIRouter, Depends
from server.app.services.mlmd_state import mlmd_state
from server.app.schemas.responses import (
    ArtifactIdRequest,
    ArtifactIdsRequest,
    ArtifactNameRequest,
    ArtifactNameWithPipelineRequest,
    ErrorDetail,
    ExecutionIdRequest,
    MetricsNameRequest,
    PipelineNameRequest,
    APIResponse,
)

router = APIRouter(prefix="/v1", tags=["artifacts"])
query = mlmd_state.query

# ==================== Business Logic Functions For CMFQuery ====================

def _dataframe_records(dataframe) -> list[dict]:
    return dataframe.where(dataframe.notna(), None).to_dict(orient="records")


def _dataframe_response(dataframe, data: dict, not_found_field: str, not_found_message: str, success_message: str) -> APIResponse:
    if dataframe is None or dataframe.empty:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="Artifacts not found",
            errors=[ErrorDetail(field=not_found_field, message=not_found_message)],
        )

    artifact_records = _dataframe_records(dataframe)
    data.update(
        {
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        }
    )
    return APIResponse(
        status="success",
        code=200,
        data=data,
        message=success_message,
    )


def _metrics_response(dataframe, metrics_name: str) -> APIResponse:
    if dataframe is None or dataframe.empty:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="Metrics not found",
            errors=[ErrorDetail(field="metrics_name", message=f"Metrics '{metrics_name}' not found")],
        )

    metric_records = _dataframe_records(dataframe)
    return APIResponse(
        status="success",
        code=200,
        data={
            "metrics_name": metrics_name,
            "metrics": metric_records,
            "total_metrics": len(metric_records),
        },
        message="Metrics retrieved successfully",
    )

def list_all_artifacts(query: CmfQuery) -> APIResponse:
    artifact_names = query.get_all_artifacts()
    if artifact_names == []:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="No artifacts found",
            errors=[
                ErrorDetail(
                    field="artifacts",
                    message="No artifacts found in the system",
                )
            ],
        )

    return APIResponse(
        status="success",
        code=200,
        data={
            "artifacts": artifact_names,
            "total_artifacts": len(artifact_names),
        },
        message="Artifacts retrieved successfully",
    )


def get_all_artifacts_by_context(request: PipelineNameRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_all_artifacts_by_context(request.pipeline_name)
    if artifacts.empty:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="Artifacts associated with pipeline not found",
            errors=[
                ErrorDetail(
                    field="pipeline_name",
                    message=f"Pipeline '{request.pipeline_name}' not found or has no artifacts",
                )
            ],
        )

    artifact_records = _dataframe_records(artifacts)
    return APIResponse(
        status="success",
        code=200,
        data={
            "pipeline_name": request.pipeline_name,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="Artifacts associated with pipeline retrieved successfully",
    )


def get_all_artifacts_by_ids_list(request: ArtifactIdsRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_all_artifacts_by_ids_list(request.artifact_ids)
    if artifacts.empty:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="Artifacts not found",
            errors=[
                ErrorDetail(
                    field="artifact_ids",
                    message=f"Artifacts not found for ids {request.artifact_ids}",
                )
            ],
        )

    artifact_records = _dataframe_records(artifacts)
    return APIResponse(
        status="success",
        code=200,
        data={
            "artifact_ids": request.artifact_ids,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="Artifacts retrieved successfully",
    )


def get_artifact(request: ArtifactNameRequest, query: CmfQuery) -> APIResponse:
    artifact = query.get_artifact(request.artifact_name)
    return _dataframe_response(
        artifact,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Artifact '{request.artifact_name}' not found",
        "Artifact retrieved successfully",
    )


def get_all_artifacts_for_execution(request: ExecutionIdRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_all_artifacts_for_execution(request.execution_id)
    return _dataframe_response(
        artifacts,
        {"execution_id": request.execution_id},
        "execution_id",
        f"Artifacts not found for execution id {request.execution_id}",
        "Artifacts for execution retrieved successfully",
    )


def get_one_hop_child_artifacts(request: ArtifactNameWithPipelineRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_one_hop_child_artifacts(request.artifact_name, request.pipeline_id)
    return _dataframe_response(
        artifacts,
        {"artifact_name": request.artifact_name, "pipeline_id": request.pipeline_id},
        "artifact_name",
        f"Child artifacts not found for artifact '{request.artifact_name}'",
        "One-hop child artifacts retrieved successfully",
    )


def get_all_child_artifacts(request: ArtifactNameRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_all_child_artifacts(request.artifact_name)
    return _dataframe_response(
        artifacts,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Child artifacts not found for artifact '{request.artifact_name}'",
        "All child artifacts retrieved successfully",
    )


def get_one_hop_parent_artifacts(request: ArtifactNameRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_one_hop_parent_artifacts(request.artifact_name)
    return _dataframe_response(
        artifacts,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Parent artifacts not found for artifact '{request.artifact_name}'",
        "One-hop parent artifacts retrieved successfully",
    )


def get_one_hop_parent_artifacts_with_id(request: ArtifactIdRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_one_hop_parent_artifacts_with_id(request.artifact_id)
    return _dataframe_response(
        artifacts,
        {"artifact_id": request.artifact_id},
        "artifact_id",
        f"Parent artifacts not found for artifact id {request.artifact_id}",
        "One-hop parent artifacts retrieved successfully",
    )


def get_all_parent_artifacts(request: ArtifactNameRequest, query: CmfQuery) -> APIResponse:
    artifacts = query.get_all_parent_artifacts(request.artifact_name)
    return _dataframe_response(
        artifacts,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Parent artifacts not found for artifact '{request.artifact_name}'",
        "All parent artifacts retrieved successfully",
    )


def get_metrics(request: MetricsNameRequest, query: CmfQuery) -> APIResponse:
    metrics = query.get_metrics(request.metrics_name)
    return _metrics_response(metrics, request.metrics_name)


def list_all_artifact_types(query: CmfQuery) -> APIResponse:
    artifact_types = query.get_all_artifact_types()
    if artifact_types == []:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="No artifact types found",
            errors=[
                ErrorDetail(
                    field="artifact_types",
                    message="No artifact types found in the system",
                )
            ],
        )
        
    return APIResponse(
        status="success",
        code=200,
        data={
            "artifact_types": artifact_types,
            "total_artifact_types": len(artifact_types),
        },
        message="Artifacts retrieved successfully",
    )


# ==================== API Endpoints For CMfQuery ====================
 
@router.get("", response_model=APIResponse)
def cmfquery_list_artifacts():
    return list_all_artifacts(query)


@router.get("/types", response_model=APIResponse)
def cmfquery_list_artifact_types():
    return list_all_artifact_types(query)


@router.get("/get_all_artifacts_by_context", response_model=APIResponse)
def cmfquery_get_all_artifacts_by_context(
    request: PipelineNameRequest = Depends(),
):
    return get_all_artifacts_by_context(request, query)


@router.post("/get_all_artifacts_by_ids_list", response_model=APIResponse)
def cmfquery_get_all_artifacts_by_ids_list(
    request: ArtifactIdsRequest,
):
    return get_all_artifacts_by_ids_list(request, query)


@router.get("/get_artifact", response_model=APIResponse)
def cmfquery_get_artifact(
    request: ArtifactNameRequest = Depends(),
):
    return get_artifact(request, query)


@router.get("/get_all_artifacts_for_execution", response_model=APIResponse)
def cmfquery_get_all_artifacts_for_execution(
    request: ExecutionIdRequest = Depends(),
):
    return get_all_artifacts_for_execution(request, query)


@router.get("/get_one_hop_child_artifacts", response_model=APIResponse)
def cmfquery_get_one_hop_child_artifacts(
    request: ArtifactNameWithPipelineRequest = Depends(),
):
    return get_one_hop_child_artifacts(request, query)


@router.get("/get_all_child_artifacts", response_model=APIResponse)
def cmfquery_get_all_child_artifacts(
    request: ArtifactNameRequest = Depends(),
):
    return get_all_child_artifacts(request, query)


@router.get("/get_one_hop_parent_artifacts", response_model=APIResponse)
def cmfquery_get_one_hop_parent_artifacts(
    request: ArtifactNameRequest = Depends(),
):
    return get_one_hop_parent_artifacts(request, query)


@router.get("/get_one_hop_parent_artifacts_with_id", response_model=APIResponse)
def cmfquery_get_one_hop_parent_artifacts_with_id(
    request: ArtifactIdRequest = Depends(),
):
    return get_one_hop_parent_artifacts_with_id(request, query)


@router.get("/get_all_parent_artifacts", response_model=APIResponse)
def cmfquery_get_all_parent_artifacts(
    request: ArtifactNameRequest = Depends(),
):
    return get_all_parent_artifacts(request, query)


@router.get("/get_metrics", response_model=APIResponse)
def cmfquery_get_metrics(
    request: MetricsNameRequest = Depends(),
):
    return get_metrics(request, query)


