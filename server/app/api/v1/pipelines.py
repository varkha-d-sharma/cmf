from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.dbconfig import get_db
from server.app.schemas.dataframe import ArtifactByStageRequest, ExecutionByStageRequest

router = APIRouter(prefix="/v1", tags=["pipelines"])


@router.get("/pipelines")
async def list_pipelines(request: Request):
    from server.app.main import pipelines

    return await pipelines(request)


@router.get("/executions")
async def standardized_executions(
    pipeline_name: str = Query(..., description="Pipeline name"),
    query_params: ExecutionByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    from server.app.main import get_executions_by_stage

    return await get_executions_by_stage(pipeline_name, query_params, db)


@router.get("/executions/stages")
async def standardized_execution_stages(
    pipeline_name: str = Query(..., description="Pipeline name"),
    db: AsyncSession = Depends(get_db),
):
    from server.app.main import get_pipeline_stages

    return await get_pipeline_stages(pipeline_name, db)


@router.get("/artifacts/types")
async def standardized_artifact_types(
    pipeline_name: str = Query(..., description="Pipeline name"),
    stage_name: str = Query(..., description="Stage name (Context_Type value)"),
    db: AsyncSession = Depends(get_db),
):
    from server.app.main import get_artifact_types_by_stage

    return await get_artifact_types_by_stage(pipeline_name, stage_name, db)


@router.get("/artifacts")
async def standardized_artifacts(
    pipeline_name: str = Query(..., description="Pipeline name"),
    query_params: ArtifactByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    from server.app.main import get_artifacts_by_stage

    return await get_artifacts_by_stage(pipeline_name, query_params, db)


@router.get("/pipelines/{pipeline_name}/executions")
async def pipeline_executions(
    pipeline_name: str,
    query_params: ExecutionByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    from server.app.main import get_executions_by_stage

    return await get_executions_by_stage(pipeline_name, query_params, db)


@router.get("/pipelines/{pipeline_name}/stages")
async def pipeline_stages(pipeline_name: str, db: AsyncSession = Depends(get_db)):
    from server.app.main import get_pipeline_stages

    return await get_pipeline_stages(pipeline_name, db)


@router.get("/pipelines/{pipeline_name}/artifact-types-by-stage")
async def pipeline_artifact_types_by_stage(
    pipeline_name: str,
    stage_name: str = Query(..., description="Stage name (Context_Type value)"),
    db: AsyncSession = Depends(get_db),
):
    from server.app.main import get_artifact_types_by_stage

    return await get_artifact_types_by_stage(pipeline_name, stage_name, db)


@router.get("/pipelines/{pipeline_name}/artifacts-by-stage")
async def pipeline_artifacts_by_stage(
    pipeline_name: str,
    query_params: ArtifactByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    from server.app.main import get_artifacts_by_stage

    return await get_artifacts_by_stage(pipeline_name, query_params, db)
