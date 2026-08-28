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
import os
import json
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, Query, Request, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    fetch_artifact_types_by_stage,
    fetch_artifacts_by_stage,
)
from server.app.schemas.requests import (
    ArtifactByStageRequest,
    ArtifactTypesByStageRequest,
)
from server.app.schemas.responses import success_response
from server.app.main import (
    query,
)

from server.app.get_data import (
    get_artifact_types,
    async_api,
    get_model_data,
)

from server.app.api.v1.metadata import (
    check_mlmd_file_exists,
)

router = APIRouter(prefix="/v1", tags=["artifacts"])
import pandas as pd

# ==================== Business Logic Functions ====================

async def artifact_types():
    """Get list of artifact types."""
    await check_mlmd_file_exists()

    artifact_types_list = await async_api(
        get_artifact_types,
        query,
    )

    if "Environment" in artifact_types_list:
        artifact_types_list.remove("Environment")

    return artifact_types_list

async def model_card(request: Request, modelId: int, response_model=List[Dict[str, Any]]):
    """Get model card information."""
    json_payload_1 = ""
    json_payload_2 = ""
    json_payload_3 = ""
    json_payload_4 = ""
    model_data_df = pd.DataFrame()
    model_exe_df = pd.DataFrame()
    model_input_art_df = pd.DataFrame()
    model_output_art_df = pd.DataFrame()
    await check_mlmd_file_exists()
    model_data_df, model_exe_df, model_input_art_df, model_output_art_df = await async_api(
        get_model_data, query, modelId
    )
    if not model_data_df.empty:
        result_1 = model_data_df.to_json(orient="records")
        json_payload_1 = json.loads(result_1)
    if not model_exe_df.empty:
        result_2 = model_exe_df.to_json(orient="records")
        json_payload_2 = json.loads(result_2)
    if not model_input_art_df.empty:
        result_3 = model_input_art_df.to_json(orient="records")
        json_payload_3 = json.loads(result_3)
    if not model_output_art_df.empty:
        result_4 = model_output_art_df.to_json(orient="records")
        json_payload_4 = json.loads(result_4)
    return [json_payload_1, json_payload_2, json_payload_3, json_payload_4]


async def upload_label(request: Request, file: UploadFile):
    """Upload label file."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided.")

        labels_dir = "/cmf-server/data/labels"
        file_path = os.path.join(labels_dir, os.path.basename(file.filename))

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if os.path.exists(file_path):
            return {
                "message": f"File '{file.filename}' already exists at {labels_dir}. Skipping upload."
            }

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        return {"message": f"File '{file.filename}' uploaded successfully to {labels_dir}."}

    except Exception as e:
        return {"error": f"Failed to upload file: {e}"}


async def get_label_data(file_name: str) -> str:
    """Retrieve label data file content."""
    file_path = os.path.join("/cmf-server/data/labels/", os.path.basename(file_name))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path, "r") as file:
            content = file.read()
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


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


# ==================== API Endpoints ====================

@router.get("/metadata/artifact-types")
async def get_artifacts(
    request: Request,
):
    """
    Retrieve available artifact types.

    This API is used by the MCP server.
    """
    result = await artifact_types()

    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200,
    )


@router.get("/artifacts/model-card")
async def get_model_card( request: Request, modelId: int,):
    result = await model_card(request, modelId)
    return success_response(
        data=result,
        message="Model card retrieved successfully",
        code=200,
    )

@router.post("/artifacts/label")
async def upload_label_file(request: Request,file: UploadFile = File(...),):
    result = await upload_label(request, file)

    return success_response(
        data=result,
        message="Label uploaded successfully",
        code=201,
    )


@router.get("/artifacts/label-data")
async def get_label_data_route(request: Request, file_name: str):
    result = await get_label_data(file_name)

    return success_response(
        data=result,
        message="Label data retrieved successfully",
        code=200,
    )


@router.post("/pipelines/{pipeline_name}/artifacts/types")
async def get_artifact_types_by_stage_route(
    request: Request,
    query_params: ArtifactTypesByStageRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await get_artifact_types_by_stage(
        query_params.pipeline_name,
        query_params.stage_name,
        db,
    )
    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200,
    )


@router.post("/pipelines/{pipeline_name}/artifacts")
async def get_artifacts_types(
    request: Request,
    query_params: ArtifactByStageRequest,
    db: AsyncSession = Depends(get_db),
):
    pipeline_name = query_params.pipeline_name
    result = await get_artifacts_by_stage(pipeline_name, query_params, db)
    return success_response(
        data=result,
        message="Artifacts retrieved successfully",
        code=200,
    )