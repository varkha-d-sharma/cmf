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
Execution API endpoints and business logic.

This module contains execution-related API endpoints and their business logic,
including execution listing and Python environment management.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from cmflib.cmfquery import CmfQuery
from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    fetch_executions_by_stage,
    fetch_unique_execution_stages
)
from server.app.schemas.requests import (
    ExecutionByStageRequest
)
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import MlmdState
from server.app.get_data import (
    async_api,
    executions_list,
)

router = APIRouter(prefix="/v1", tags=["executions"])


# ==================== Business Logic Functions ====================

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


# ==================== API Endpoints ====================

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