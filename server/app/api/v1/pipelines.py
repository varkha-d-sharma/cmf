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

Pipeline API endpoints and business logic.

This module contains API endpoints for pipeline discovery, stage queries,
executions, artifacts, and execution/artifact lineage.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    fetch_unique_execution_stages,
    fetch_artifact_types_by_stage,
    fetch_artifacts_by_stage,
    fetch_executions_by_stage,
    fetch_unique_execution_stages
)
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import MlmdState
from typing import List, Dict, Any, Optional
from server.app.get_data import async_api
from server.app.query_execution_lineage_d3tree import (query_execution_lineage_d3tree)
from server.app.query_artifact_lineage_d3tree import (query_artifact_lineage_d3tree)
from server.app.query_visualization_artifact_execution import (query_visualization_artifact_execution)
from server.app.schemas.requests import (
    ArtifactByStageRequest,
    ExecutionByStageRequest
)
from cmflib.cmfquery import CmfQuery
from server.app.get_data import (
    async_api,
    executions_list,
)

router = APIRouter(prefix="/v1", tags=["pipelines"])

# ==================== API Endpoints ====================

@router.get("/pipelines")
async def list_pipelines(request: Request):
    state = request.app.state.mlmd
    result = await pipelines(state)
    return success_response(
        data=result,
        message="Pipelines retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/stages")
async def pipeline_stages(pipeline_name: str, db: AsyncSession = Depends(get_db)):
    result = await get_pipeline_stages(pipeline_name, db)
    return success_response(
        data=result,
        message="Pipeline stages retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/executions/{uuid}/lineage")
async def get_execution_lineage(
    request: Request,
    uuid: str,
    pipeline_name: str
):
    state = request.app.state.mlmd
    result = await execution_lineage_tangled(
        state=state,
        uuid=uuid,
        pipeline_name=pipeline_name
    )

    return success_response(
        data=result,
        message="Execution lineage retrieved successfully",
        code=200
    )


@router.get("/pipelines/{pipeline_name}/artifacts/lineage")
async def get_artifact_lineage(
    request: Request,
    pipeline_name: str
):
    state = request.app.state.mlmd
    result = await artifact_lineage_tangled(
        state=state,
        pipeline_name=pipeline_name
    )

    return success_response(
        data=result,
        message="Artifact lineage retrieved successfully",
        code=200
    )


@router.get("/pipelines/{pipeline_name}/artifact-executions/lineage")
async def get_artifact_execution_lineage(
    request: Request,
    pipeline_name: str
):
    state = request.app.state.mlmd
    result = await artifact_execution_lineage(
        state=state,
        pipeline_name=pipeline_name
    )

    return success_response(
        data=result,
        message="Artifact-execution lineage retrieved successfully",
        code=200
    )


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


@router.get("/pipelines/{pipeline_name}/executions")
async def get_all_pipeline_executions(request: Request, pipeline_name: str):
    """Retrieve all executions for a pipeline without pagination or filtering."""
    state = request.app.state.mlmd
    result = await get_all_executions(state, pipeline_name)
    return success_response(
        data=result,
        message="Pipeline executions retrieved successfully",
        code=200
    )


@router.get("/pipelines/{pipeline_name}/executions/list")
async def get_executions(request: Request, pipeline_name: str):
    """Retrieve the execution list for a pipeline."""
    state = request.app.state.mlmd
    result = await list_of_executions(
        state=state,
        pipeline_name=pipeline_name
    )
    return success_response(
        data=result,
        message="Executions retrieved successfully",
        code=200
    )


@router.post("/pipelines/{pipeline_name}/executions/stages/{stage:path}")
async def pipeline_executions(
    query_params: ExecutionByStageRequest,
    pipeline_name: str,
    stage: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve executions filtered/stage-based search by pipeline and stage name."""
    result = await get_executions_by_stage(
        pipeline_name=pipeline_name,
        stage_name= stage,
        active_page=query_params.active_page,
        record_per_page=query_params.record_per_page,
        sort_order=query_params.sort_order,
        filter_value=query_params.filter_value,
        db=db
    )
    return success_response(
        data=result,
        message="Pipeline executions retrieved successfully",
        code=200
    )


# ==================== Business Logic Functions ====================

# This API returns the list of pipeline names present in the current MLMD store.
async def pipelines(state: MlmdState):
    """Get list of all pipelines."""
    if state.query:
        pipeline_names = state.query.get_pipeline_names()
        return pipeline_names
    else:
        print("No mlmd file submitted.")
        pipeline_names = []
        return pipeline_names


async def get_pipeline_stages(
    pipeline_name: str,
    db: AsyncSession,
):
    """
    Retrieve unique pipeline stages (Context_Type values) for a given pipeline.
    
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
    result = await fetch_unique_execution_stages(db, pipeline_name)
    return result


    # This API returns the execution lineage graph for a selected execution UUID.
async def execution_lineage_tangled(
    state: MlmdState,
    uuid: str,
    pipeline_name: str
):
    """returns dictionary of nodes and links for given execution_type.
      response = {
                   nodes: [{id:"",name:"",execution_uuid:""}],
                   links: [{source:1,target:4},{}],
                 } """
    # checks if mlmd file exists on server
    await state.check_mlmd_file_exists()
    # checks if pipeline exists
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_execution_lineage_d3tree,
        state.query,
        pipeline_name,
        state.dict_of_exe_ids,
        uuid
    )

    return response


# This API returns artifact lineage in a nested structure used by the tangled-tree visualization.
async def artifact_lineage_tangled(
    state: MlmdState,
    pipeline_name: str
) -> Optional[List[List[Dict[str, Any]]]]:
    """ Returns:
      A nested list of dictionaries with 'id' and 'parents' keys.
      response = [
        [{'id': 'data.xml.gz:236d', 'parents': []}],
        [{'id': 'parsed/train.tsv:32b7', 'parents': ['data.xml.gz:236d']}, 
        ]"""
    # checks if mlmd file exists on server
    await state.check_mlmd_file_exists()
    # checks if pipeline exists
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_artifact_lineage_d3tree,
        state.query,
        pipeline_name,
        state.dict_of_art_ids
    )

    return response


# This API returns the artifact-execution lineage graph for visualizing how artifacts and
async def artifact_execution_lineage(
    state: MlmdState,
    pipeline_name: str
):
    """Get artifact-execution lineage visualization."""
    # checks if mlmd file exists on server
    await state.check_mlmd_file_exists()
    # checks if pipeline exists
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_visualization_artifact_execution,
        state.query,
        pipeline_name,
        state.dict_of_art_ids,
        state.dict_of_exe_ids
    )

    return response


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


# Used by the MCP client to retrieve all pipeline executions
async def get_all_executions(state: MlmdState, pipeline_name: str):
    """Retrieve all executions for a pipeline without pagination or filtering."""
    await state.check_mlmd_file_exists()
    await state.check_pipeline_exists(pipeline_name)

    executions = await async_api(
        CmfQuery.get_all_executions_in_pipeline,
        state.query,
        pipeline_name
    )
    if executions.empty:
        return []
    return executions.to_dict(orient="records")


async def list_of_executions(state: MlmdState, pipeline_name: str):
    '''
      This api's returns list of execution types.

    '''
    # checks if mlmd file exists on server
    await state.check_mlmd_file_exists()
    # checks if pipeline exists
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        executions_list,
        state.query,
        pipeline_name,
        state.dict_of_exe_ids
    )

    return response


async def get_executions_by_stage(
    pipeline_name: str,
    stage_name: str,
    active_page: int,
    record_per_page: int,
    sort_order: str,
    filter_value: str,
    db: AsyncSession
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
    return await fetch_executions_by_stage(db, pipeline_name, stage_name, active_page, record_per_page, sort_order, filter_value)


async def get_pipeline_stages(
    pipeline_name: str,
    db: AsyncSession
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
