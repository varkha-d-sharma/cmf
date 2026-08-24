"""
Artifact API endpoints and business logic.

This module contains artifact-related API endpoints and their business logic,
including artifact types.
"""
import os
import json
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, UploadFile,File

from server.app.schemas.responses import success_response
from server.app.main import (
    query,
    dict_of_art_ids,
    dict_of_exe_ids,
)

from server.app.get_data import (
    get_artifact_types,
    async_api,
    get_model_data,
)

from server.app.query_artifact_lineage_d3tree import query_artifact_lineage_d3tree
from server.app.query_visualization_artifact_execution import (
    query_visualization_artifact_execution,
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
        return {"error": f"Failed to up load file: {e}"}

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


# ==================== API Endpoints ====================

@router.get("/metadata/artifact-types")
async def get_artifact_types(
    request: Request,
):
    result = await artifact_types()

    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200,
    )


@router.get("/artifacts/model-card")
async def get_model_card_endpoint( request: Request, modelId: int,):
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
async def get_label_data_endpoint(request: Request,file_name: str,):
    result = await get_label_data(file_name)

    return success_response(
        data=result,
        message="Label data retrieved successfully",
        code=200,
    )
