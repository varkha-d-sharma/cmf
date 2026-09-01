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

import os
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    fetch_executions_by_stage,
    fetch_unique_execution_stages,
)
from server.app.schemas.requests import (
    ExecutionByStageRequest,
)
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import MlmdState
from server.app.get_data import (
    async_api,
    executions_list,
)

router = APIRouter(prefix="/v1", tags=["executions"])


# ==================== Business Logic Functions ====================

# This API returns the list of execution types for a given pipeline.
async def list_of_executions(state: MlmdState, pipeline_name: str):
    # checks if mlmd file exists on server
    await state.check_mlmd_file_exists()
    # checks if pipeline exists
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        executions_list,
        state.query,
        pipeline_name,
        state.dict_of_exe_ids,
    )

    return response


# API endpoint for uploading Python environment files.
async def upload_python_env(file: UploadFile):
    """Upload Python environment file."""
    try:
        if file.filename is None:
            raise HTTPException(status_code=400, detail="No file uploaded")

        file_path = os.path.join("/cmf-server/data/env/", os.path.basename(file.filename))

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        return {
            "message": f"File '{file.filename}' uploaded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}") from e


# Rest api to fetch the env data from the /cmf-server/data/env folder
async def get_python_env(file_name: str) -> str:
    """
    API endpoint to fetch the content of a requirements file.

    Args:
        file_name (str): The name of the file to be fetched. Must end with .txt or .yaml.

    Returns:
        str: The content of the file as plain text.

    Raises:
        HTTPException: If the file does not exist or the extension is unsupported.
    """
    # Validate file extension
    if not (file_name.endswith(".txt") or file_name.endswith(".yaml")):
        raise HTTPException(status_code=400, detail="Unsupported file extension. Use .txt or .yaml")
    # Check if the file exists
    file_path = os.path.join("/cmf-server/data/env/", os.path.basename(file_name))

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
     # Read and return the file content as plain text
    try:
        with open(file_path, "r") as file:
            content = file.read()
        return content

    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}") from e


async def get_executions_by_stage(
    pipeline_name: str,
    stage_name: str,
    active_page: int,
    record_per_page: int,
    sort_order: str,
    filter_value: str,
    db: AsyncSession,
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
    db: AsyncSession,
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

@router.post("/executions/python-env")
async def upload_python_environment(file: UploadFile = File(...)):
    result = await upload_python_env(file)

    return success_response(
        data=result,
        message="Python environment uploaded successfully",
        code=201,
    )


@router.get("/executions/python-env")
async def get_python_environment(file_name: str):
    result = await get_python_env(file_name)

    return success_response(
        data=result,
        message="Python environment retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/stages")
async def pipeline_stages(
    pipeline_name: str,
    db: AsyncSession = Depends(get_db),
):
    result = await get_pipeline_stages(pipeline_name, db)
    return success_response(
        data=result,
        message="Pipeline stages retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/executions")
async def get_executions(request: Request, pipeline_name: str):
    """Retrieve the execution list for a pipeline."""
    state = request.app.state.mlmd
    result = await list_of_executions(
        state=state,
        pipeline_name=pipeline_name,
    )
    return success_response(
        data=result,
        message="Executions retrieved successfully",
        code=200,
    )


@router.post("/pipelines/{pipeline_name}/executions")
async def pipeline_executions(
    query_params: ExecutionByStageRequest,
    pipeline_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve executions filtered/stage-based search by pipeline and stage name."""
    result = await get_executions_by_stage(
        pipeline_name=pipeline_name,
        stage_name=query_params.stage_name,
        active_page=query_params.active_page,
        record_per_page=query_params.record_per_page,
        sort_order=query_params.sort_order,
        filter_value=query_params.filter_value,
        db=db,
    )
    return success_response(
        data=result,
        message="Pipeline executions retrieved successfully",
        code=200,
    )