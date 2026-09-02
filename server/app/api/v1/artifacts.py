"""
Copyright (2023) Hewlett Packard Enterprise Development LP

Licensed under the Apache License, Version 2.0 (the "License");
You may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Artifact API endpoints and business logic.

This module contains artifact-related API endpoints and their business logic,
including artifact types.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    fetch_artifact_types_by_stage,
    fetch_artifacts_by_stage,
)
from server.app.schemas.requests import (
    ArtifactByStageRequest,
)
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import MlmdState
from server.app.get_data import (
    get_artifact_types,
    async_api,
)
import pandas as pd
from cmflib.cmfquery import CmfQuery
router = APIRouter(prefix="/v1", tags=["artifacts"])

# ==================== Business Logic Functions ====================

# Used by the MCP client to retrieve all pipeline artifacts
async def get_all_artifacts(state: MlmdState, pipeline_name: str):
    """Retrieve all artifacts for a pipeline without pagination or filtering."""
    await state.check_mlmd_file_exists()
    await state.check_pipeline_exists(pipeline_name)

    artifacts = await async_api(
        CmfQuery.get_all_artifacts_by_context,
        state.query,
        pipeline_name
    )
    if artifacts.empty:
        return []
    return artifacts.to_dict(orient="records")

# This API returns a list of artifact types in the current MLMD store.
async def get_artifacts_types(state: MlmdState):
    """Get list of artifact types."""
    await state.check_mlmd_file_exists()

    artifact_types_list = await async_api(
        get_artifact_types,
        state.query
    )

    if "Environment" in artifact_types_list:
        artifact_types_list.remove("Environment")

    return artifact_types_list


async def get_artifact_types_by_stage(
    pipeline_name: str,
    stage_name: str,
    db: AsyncSession
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
    stage_name: str,
    artifact_type: str,
    filter_value: str,
    active_page: int,
    record_per_page: int,
    sort_field: str,
    sort_order: str,
    db: AsyncSession
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


# ==================== API Endpoints ====================

@router.get("/pipelines/{pipeline_name}/artifacts")
async def get_artifacts(request: Request, pipeline_name: str):
    """Retrieve all artifacts for a pipeline without pagination or filtering."""
    state = request.app.state.mlmd
    result = await get_all_artifacts(state, pipeline_name)
    return success_response(
        data=result,
        message="Pipeline artifacts retrieved successfully",
        code=200
    )


# only This API is used by the MCP server.
@router.get("/artifacts/artifact/types")
async def get_artifacts_by_types(
    request: Request,
):
    """
    Retrieve available artifact types.
    """
    state = request.app.state.mlmd
    result = await get_artifacts_types(state)

    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200
    )


@router.post("/pipelines/{pipeline_name}/artifacts/stages/{stage:path}/types")
async def get_artifact_types_by_stage_route(
    pipeline_name: str,
    stage: str,
    db: AsyncSession = Depends(get_db)
):
    result = await get_artifact_types_by_stage(
        pipeline_name,
        stage,
        db
    )
    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200
    )


@router.post("/pipelines/{pipeline_name}/artifacts/stages/{stage:path}")
async def get_artifacts_by_stage_route(
    query_params: ArtifactByStageRequest,
    pipeline_name: str,
    stage: str,
    db: AsyncSession = Depends(get_db)
):
    result = await get_artifacts_by_stage(
        pipeline_name,
        stage,
        query_params.artifact_type,
        query_params.filter_value,
        query_params.active_page,
        query_params.record_per_page,
        query_params.sort_field,
        query_params.sort_order,
        db
    )
    return success_response(
        data=result,
        message="Artifacts retrieved successfully",
        code=200
    )