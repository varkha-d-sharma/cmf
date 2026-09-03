
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
UI Actions API endpoints and business logic.
 
"""

import os
import json
from fastapi import  APIRouter, Request, HTTPException, UploadFile, File, Query
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import MlmdState
from server.app.get_data import (
    async_api,
    get_model_data
)
import pandas as pd
router = APIRouter(prefix="/v1", tags=["ui-actions"])

# ==================== API Endpoints ====================

@router.get("/model-card")
async def get_model_card( request: Request, modelId: int):
    """Return model, execution, input-artifact, and output-artifact card data."""
    state = request.app.state.mlmd
    result = await model_card(state, modelId)
    return success_response(
        data=result,
        message="Model card retrieved successfully",
        code=200
    )


@router.post("/label")
async def upload_label_file(file: UploadFile = File(..., description="The file to upload")):
    """Upload a label file to the server label directory."""
    result = await upload_label(file)

    return success_response(
        data=result,
        message="Label uploaded successfully",
        code=201
    )


@router.get("/label-data")
async def get_label_data_route(file_name: str):
    """Return the contents of a stored label data file."""
    result = await get_label_data(file_name)

    return success_response(
        data=result,
        message="Label data retrieved successfully",
        code=200
    )

@router.post("/tensorboard")
async def tensorboard_upload(
    pipeline_name: str = Query(..., description="Pipeline name"),
    file: UploadFile = File(..., description="The file to upload")
):
    """Upload a TensorBoard log file to a pipeline-specific directory."""
    result = await upload_tensorboard_logs(pipeline_name, file)
    return success_response(
        data=result,
        message="TensorBoard file uploaded successfully",
        code=200,
    )


# ==================== Business Logic Functions ====================
# This API returns the model card payload including model, execution, and artifact data.
async def model_card(state: MlmdState, modelId: int):
    """Get model card information."""
    json_payload_1 = ""
    json_payload_2 = ""
    json_payload_3 = ""
    json_payload_4 = ""
    model_data_df = pd.DataFrame()
    model_exe_df = pd.DataFrame()
    model_input_art_df = pd.DataFrame()
    model_output_art_df = pd.DataFrame()
    # checks if mlmd file exists on server
    await state.check_mlmd_file_exists()
    model_data_df, model_exe_df, model_input_art_df, model_output_art_df = await async_api(
        get_model_data, state.query, modelId
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


async def upload_label(file: UploadFile):
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}") from e


"""Retrieve label data from from the /cmf-server/data/labels folder."""
async def get_label_data(file_name: str) -> str:
   
    """
    API endpoint to fetch the content of a requirements file.

    Args:
        file_name (str): The name of the file to be fetched. Must end with .csv.

    Returns:
        str: The content of the file as plain text.

    Raises:
        HTTPException: If the file does not exist or the extension is unsupported.
    """
    # Check if the file exists
    file_path = os.path.join("/cmf-server/data/labels/", os.path.basename(file_name))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    # Read and return the file content as plain text
    try:
        with open(file_path, "r") as file:
            content = file.read()
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


    # Upload TensorBoard logs for a pipeline.
async def upload_tensorboard_logs(
    pipeline_name: str,
    file: UploadFile
):
    """Upload a TensorBoard log file under the pipeline-specific logs directory."""
    try:
        if file.filename is None:
            raise HTTPException(status_code=400, detail="No file uploaded")
        file_path = os.path.join("/cmf-server/data/tensorboard-logs", pipeline_name, file.filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        return {"message": f"File '{file.filename}' uploaded successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}") from e
