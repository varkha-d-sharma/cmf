from typing import Optional

from cmflib.cmfquery import CmfQuery
from fastapi import APIRouter
from server.app.get_data import async_api
from server.app.services.mlmd_state import mlmd_state
from server.app.schemas.responses import (
    ArtifactIdsRequest,
    ErrorDetail,
    APIResponse,
    error_response,
    success_response,
)

router = APIRouter(prefix="/v1", tags=["artifacts"])
query = mlmd_state.query


# ==================== API Endpoints For CMFQuery ====================

@router.get("/artifacts", response_model=APIResponse)
async def cmfquery_list_artifacts():
    artifact_names = await async_api(list_all_artifacts, query)
    if artifact_names == []:
        return error_response(
            message="No artifacts found",
            code=404,
            errors=[
                ErrorDetail(
                    field="artifacts",
                    message="No artifacts found in the system",
                )
            ],
        )

    return success_response(
        data={
            "artifacts": artifact_names,
            "total_artifacts": len(artifact_names),
        },
        message="Artifacts retrieved successfully",
        code=200,
    )


@router.get("/artifacts/types", response_model=APIResponse)
async def cmfquery_list_artifact_types():
    artifact_types = await async_api(list_all_artifact_types, query)
    if artifact_types == []:
        return error_response(
            message="No artifact types found",
            code=404,
            errors=[
                ErrorDetail(
                    field="artifact_types",
                    message="No artifact types found in the system",
                )
            ],
        )

    return success_response(
        data={
            "artifact_types": artifact_types,
            "total_artifact_types": len(artifact_types),
        },
        message="Artifacts retrieved successfully",
        code=200,
    )


@router.get("/artifacts/{pipeline_name}", response_model=APIResponse)
async def cmfquery_get_all_artifacts_by_context(pipeline_name: str):
    artifacts = await async_api(get_all_artifacts_by_context, query, pipeline_name)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts associated with pipeline not found",
            code=404,
            errors=[
                ErrorDetail(
                    field="pipeline_name",
                    message=f"Pipeline '{pipeline_name}' not found or has no artifacts",
                )
            ],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "pipeline_name": pipeline_name,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="Artifacts associated with pipeline retrieved successfully",
        code=200,
    )


@router.post("/artifacts/by-ids", response_model=APIResponse)
async def cmfquery_get_all_artifacts_by_ids_list(
    request: ArtifactIdsRequest,
):
    artifacts = await async_api(get_all_artifacts_by_ids_list, query, request.artifact_ids)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[
                ErrorDetail(
                    field="artifact_ids",
                    message=f"Artifacts not found for ids {request.artifact_ids}",
                )
            ],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "artifact_ids": request.artifact_ids,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="Artifacts retrieved successfully",
        code=200,
    )


@router.get("/artifacts/name/{artifact_name:path}", response_model=APIResponse)
async def cmfquery_get_artifact(artifact_name: str):
    artifact = await async_api(get_artifact, query, artifact_name)
    if artifact is None or artifact.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[ErrorDetail(field="artifact_name", message=f"Artifact '{artifact_name}' not found")],
        )

    artifact_records = _dataframe_records(artifact)
    return success_response(
        data={
            "artifact_name": artifact_name,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="Artifact retrieved successfully",
        code=200,
    )


@router.get("/executions/{execution_id}/artifacts", response_model=APIResponse)
async def cmfquery_get_all_artifacts_for_execution(execution_id: int):
    artifacts = await async_api(get_all_artifacts_for_execution, query, execution_id)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[ErrorDetail(field="execution_id", message=f"Artifacts not found for execution id {execution_id}")],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "execution_id": execution_id,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="Artifacts for execution retrieved successfully",
        code=200,
    )


@router.get("/artifacts/children/{artifact_name:path}", response_model=APIResponse)
async def cmfquery_get_one_hop_child_artifacts(
    artifact_name: str,
    pipeline_id: Optional[int] = None,
):
    artifacts = await async_api(get_one_hop_child_artifacts, query, artifact_name, pipeline_id)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[ErrorDetail(field="artifact_name", message=f"Child artifacts not found for artifact '{artifact_name}'")],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "artifact_name": artifact_name,
            "pipeline_id": pipeline_id,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="One-hop child artifacts retrieved successfully",
        code=200,
    )


@router.get("/artifacts/children/all/{artifact_name:path}", response_model=APIResponse)
async def cmfquery_get_all_child_artifacts(artifact_name: str):
    artifacts = await async_api(get_all_child_artifacts, query, artifact_name)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[ErrorDetail(field="artifact_name", message=f"Child artifacts not found for artifact '{artifact_name}'")],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "artifact_name": artifact_name,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="All child artifacts retrieved successfully",
        code=200,
    )


@router.get("/artifacts/parents/{artifact_name:path}", response_model=APIResponse)
async def cmfquery_get_one_hop_parent_artifacts(artifact_name: str):
    artifacts = await async_api(get_one_hop_parent_artifacts, query, artifact_name)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[ErrorDetail(field="artifact_name", message=f"Parent artifacts not found for artifact '{artifact_name}'")],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "artifact_name": artifact_name,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="One-hop parent artifacts retrieved successfully",
        code=200,
    )


@router.get("/artifacts/{artifact_id}/parents", response_model=APIResponse)
async def cmfquery_get_one_hop_parent_artifacts_with_id(artifact_id: int):
    artifacts = await async_api(get_one_hop_parent_artifacts_with_id, query, artifact_id)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[ErrorDetail(field="artifact_id", message=f"Parent artifacts not found for artifact id {artifact_id}")],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "artifact_id": artifact_id,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="One-hop parent artifacts retrieved successfully",
        code=200,
    )


@router.get("/artifacts/parents/all/{artifact_name:path}", response_model=APIResponse)
async def cmfquery_get_all_parent_artifacts(artifact_name: str):
    artifacts = await async_api(get_all_parent_artifacts, query, artifact_name)
    if artifacts is None or artifacts.empty:
        return error_response(
            message="Artifacts not found",
            code=404,
            errors=[ErrorDetail(field="artifact_name", message=f"Parent artifacts not found for artifact '{artifact_name}'")],
        )

    artifact_records = _dataframe_records(artifacts)
    return success_response(
        data={
            "artifact_name": artifact_name,
            "artifacts": artifact_records,
            "total_artifacts": len(artifact_records),
        },
        message="All parent artifacts retrieved successfully",
        code=200,
    )


@router.get("/metrics/{metrics_name:path}", response_model=APIResponse)
async def cmfquery_get_metrics(metrics_name: str):
    metrics = await async_api(get_metrics, query, metrics_name)
    if metrics is None or metrics.empty:
        return error_response(
            message="Metrics not found",
            code=404,
            errors=[ErrorDetail(field="metrics_name", message=f"Metrics '{metrics_name}' not found")],
        )

    metric_records = _dataframe_records(metrics)
    return success_response(
        data={
            "metrics_name": metrics_name,
            "metrics": metric_records,
            "total_metrics": len(metric_records),
        },
        message="Metrics retrieved successfully",
        code=200,
    )


# ==================== Business Logic Functions For CMFQuery ====================

def _dataframe_records(dataframe) -> list[dict]:
    return dataframe.where(dataframe.notna(), None).to_dict(orient="records")


def list_all_artifacts(query: CmfQuery):
    return query.get_all_artifacts()


def get_all_artifacts_by_context(query: CmfQuery, pipeline_name: str):
    return query.get_all_artifacts_by_context(pipeline_name)


def get_all_artifacts_by_ids_list(query: CmfQuery, artifact_ids: list[int]):
    return query.get_all_artifacts_by_ids_list(artifact_ids)


def get_artifact(query: CmfQuery, artifact_name: str):
    return query.get_artifact(artifact_name)


def get_all_artifacts_for_execution(query: CmfQuery, execution_id: int):
    return query.get_all_artifacts_for_execution(execution_id)


def get_one_hop_child_artifacts(query: CmfQuery, artifact_name: str, pipeline_id: Optional[int]):
    return query.get_one_hop_child_artifacts(artifact_name, pipeline_id)


def get_all_child_artifacts(query: CmfQuery, artifact_name: str):
    return query.get_all_child_artifacts(artifact_name)


def get_one_hop_parent_artifacts(query: CmfQuery, artifact_name: str):
    return query.get_one_hop_parent_artifacts(artifact_name)


def get_one_hop_parent_artifacts_with_id(query: CmfQuery, artifact_id: int):
    return query.get_one_hop_parent_artifacts_with_id(artifact_id)


def get_all_parent_artifacts(query: CmfQuery, artifact_name: str):
    return query.get_all_parent_artifacts(artifact_name)


def get_metrics(query: CmfQuery, metrics_name: str):
    return query.get_metrics(metrics_name)


def list_all_artifact_types(query: CmfQuery):
    return query.get_all_artifact_types()
