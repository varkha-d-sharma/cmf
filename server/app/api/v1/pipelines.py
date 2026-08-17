"""
Pipeline API endpoints and business logic.

This module contains all pipeline-related API endpoints and their business logic,
including pipeline listing, stage queries, execution and artifact retrieval.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    fetch_executions_by_stage,
    fetch_unique_execution_stages,
    fetch_artifact_types_by_stage,
    fetch_artifacts_by_stage,
)
from server.app.schemas.requests import ArtifactByStageRequest, ExecutionByStageRequest
from server.app.schemas.responses import success_response
from server.app.main import query

router = APIRouter(prefix="/v1", tags=["pipelines"])


# ==================== Business Logic Functions ====================

async def pipelines(request: Request):
    """Get list of all pipelines."""
    if query:
        pipeline_names = query.get_pipeline_names()
        return pipeline_names
    else:
        print("No mlmd file submitted.")
        pipeline_names = []
        return pipeline_names


async def get_executions_by_stage(
    pipeline_name: str,
    query_params: ExecutionByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve executions filtered by pipeline and stage name (Context_Type).
    
    Args:
        pipeline_name: Name of the pipeline
        stage_name: Stage name (Context_Type value) to filter executions
        active_page: Page number for pagination
        record_per_page: Number of records per page
        
    Returns:
        Dictionary with total_items and list of executions with their properties
        
    Example response:
    {
        "total_items": 10,
        "items": [
            {
                "execution_id": 2,
                "execution_properties": [...]
            }
        ]
    }
    """
    stage_name = query_params.stage_name
    active_page = query_params.active_page
    record_per_page = query_params.record_per_page
    sort_order = query_params.sort_order
    filter_value = query_params.filter_value

    return await fetch_executions_by_stage(db, pipeline_name, stage_name, active_page, record_per_page, sort_order, filter_value)


async def get_pipeline_stages(
    pipeline_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve unique artifact stages (Context_Type values) for a given pipeline.
    Since artifacts inherit stages from executions, this uses the same query as execution stages.
    
    Args:
        pipeline_name: Name of the pipeline to get stages from
        
    Returns:
        Dictionary with pipeline_name, list of unique stages, and total count
        
    Example response:
    {
        "stages": ["Test-env/Prepare", "Test-env/Train", "Test-env/Evaluate"],
        "total_stages": 3
    }
    """
    print("DEBUG: get_pipeline_stages called with:", pipeline_name)
    result = await fetch_unique_execution_stages(db, pipeline_name)

    print("DEBUG: result =", result)

    return result


async def get_artifact_types_by_stage(
    pipeline_name: str,
    stage_name: str = Query(..., description="Stage name (Context_Type value)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve unique artifact types available in a specific stage of a pipeline.
    
    Args:
        pipeline_name: Name of the pipeline
        stage_name: Stage name (Context_Type value) to filter by
        
    Returns:
        List of unique artifact type names
        
    Example response:
    ["Dataset", "Metrics", "Model"]
    """
    return await fetch_artifact_types_by_stage(db, pipeline_name, stage_name)


async def get_artifacts_by_stage(
    pipeline_name: str,
    query_params: ArtifactByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve artifacts filtered by pipeline, stage, and artifact type.
    
    Args:
        pipeline_name: Name of the pipeline
        stage_name: Stage name (Context_Type value) to filter artifacts
        artifact_type: Type of artifacts to retrieve
        sort_order: Sort order (asc or desc)
        active_page: Page number for pagination
        record_per_page: Number of records per page
        filter_value: Search filter value
        sort_field: Field to sort by
        
    Returns:
        Dictionary with total_items and list of artifacts with their properties
        
    Example response:
    {
        "total_items": 10,
        "items": [
            {
                "artifact_id": 5,
                "name": "dataset.csv",
                "create_time_since_epoch": 1234567890,
                "artifact_properties": [...]
            }
        ]
    }
    """
    stage_name = query_params.stage_name
    artifact_type = query_params.artifact_type
    filter_value = query_params.filter_value
    active_page = query_params.active_page
    record_per_page = query_params.record_per_page
    sort_field = query_params.sort_field
    sort_order = query_params.sort_order

    return await fetch_artifacts_by_stage(
        db=db,
        pipeline_name=pipeline_name,
        stage_name=stage_name,
        artifact_type=artifact_type,
        filter_value=filter_value,
        active_page=active_page,
        record_per_page=record_per_page,
        sort_column=sort_field,
        sort_order=sort_order
    )


@router.get("/pipelines")
async def list_pipelines(request: Request):
    result = await pipelines(request)
    return success_response(
        data=result,
        message="Pipelines retrieved successfully",
        code=200,
    )


@router.get("/executions")
async def standardized_executions(
    request: Request,
    pipeline_name: str = Query(..., description="Pipeline name"),
    query_params: ExecutionByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await get_executions_by_stage(pipeline_name, query_params, db)
    return success_response(
        data=result,
        message="Executions retrieved successfully",
        code=200,
    )


@router.get("/executions/stages")
async def standardized_execution_stages(
    request: Request,
    pipeline_name: str = Query(..., description="Pipeline name"),
    db: AsyncSession = Depends(get_db),
):
    result = await get_pipeline_stages(pipeline_name, db)
    return success_response(
        data=result,
        message="Pipeline stages retrieved successfully",
        code=200,
    )


@router.get("/artifacts/types")
async def standardized_artifact_types(
    request: Request,
    pipeline_name: str = Query(..., description="Pipeline name"),
    stage_name: str = Query(..., description="Stage name (Context_Type value)"),
    db: AsyncSession = Depends(get_db),
):
    result = await get_artifact_types_by_stage(pipeline_name, stage_name, db)
    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200,
    )


@router.get("/artifacts")
async def standardized_artifacts(
    request: Request,
    pipeline_name: str = Query(..., description="Pipeline name"),
    query_params: ArtifactByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await get_artifacts_by_stage(pipeline_name, query_params, db)
    return success_response(
        data=result,
        message="Artifacts retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/executions")
async def pipeline_executions(
    request: Request,
    pipeline_name: str,
    query_params: ExecutionByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await get_executions_by_stage(pipeline_name, query_params, db)
    return success_response(
        data=result,
        message="Pipeline executions retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/stages")
async def pipeline_stages(request: Request, pipeline_name: str, db: AsyncSession = Depends(get_db)):
    result = await get_pipeline_stages(pipeline_name, db)
    return success_response(
        data=result,
        message="Pipeline stages retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/artifact-types-by-stage")
async def pipeline_artifact_types_by_stage(
    request: Request,
    pipeline_name: str,
    stage_name: str = Query(..., description="Stage name (Context_Type value)"),
    db: AsyncSession = Depends(get_db),
):
    result = await get_artifact_types_by_stage(pipeline_name, stage_name, db)
    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/artifacts-by-stage")
async def pipeline_artifacts_by_stage(
    request: Request,
    pipeline_name: str,
    query_params: ArtifactByStageRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await get_artifacts_by_stage(pipeline_name, query_params, db)
    return success_response(
        data=result,
        message="Artifacts retrieved successfully",
        code=200,
    )
