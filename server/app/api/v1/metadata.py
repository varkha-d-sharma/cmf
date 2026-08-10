"""
Metadata API endpoints and business logic.

This module contains all metadata-related API endpoints and their business logic,
including MLMD push/pull, lineage queries, and file management for Python environments
and labels.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, File, Request, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
import pandas as pd

from server.app.db.dbconfig import get_db
from server.app.schemas.dataframe import MLMDPullRequest, MLMDPushRequest
from server.app.core.responses import success_response
from server.app.core.globals import (
    query,
    dict_of_art_ids,
    dict_of_exe_ids,
    pipeline_locks,
    lock_counts,
)
from server.app.get_data import (
    get_mlmd_from_server,
    get_artifact_types,
    get_all_artifact_ids,
    get_all_exe_ids,
    async_api,
    get_model_data,
    executions_list,
)
from server.app.query_execution_lineage_d3tree import query_execution_lineage_d3tree
from server.app.query_artifact_lineage_d3tree import query_artifact_lineage_d3tree
from server.app.query_visualization_artifact_execution import query_visualization_artifact_execution
from cmflib.cmf_federation import update_mlmd

router = APIRouter(prefix="/v1", tags=["metadata"])


# ==================== Helper Functions ====================

async def check_mlmd_file_exists():
    """Check if MLMD file exists on server."""
    if not query:
        print(f"DB doesn't exist.")
        raise HTTPException(status_code=404, detail="Database doesn't exist.")


async def check_pipeline_exists(pipeline_name):
    """Check if the pipeline exists."""
    if pipeline_name not in query.get_pipeline_names():
        print(f"Pipeline {pipeline_name} not found.")
        raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_name} not found.")


async def update_global_art_dict(pipeline_name):
    """Update global artifact IDs dictionary for a pipeline."""
    output_dict = await async_api(get_all_artifact_ids, query, dict_of_exe_ids, pipeline_name)
    dict_of_art_ids[pipeline_name] = output_dict[pipeline_name]
    return


async def update_global_exe_dict(pipeline_name):
    """Update global execution IDs dictionary for a pipeline."""
    output_dict = await async_api(get_all_exe_ids, query, pipeline_name)
    dict_of_exe_ids[pipeline_name] = output_dict[pipeline_name]
    return


# ==================== Business Logic Functions ====================

async def mlmd_push(info: MLMDPushRequest):
    """Push MLMD metadata to the server."""
    print("mlmd push started")
    print("......................")
    status = "unknown_error"
    req_info = info.model_dump()
    pipeline_name = req_info.get("pipeline_name", "")
    if pipeline_name not in pipeline_locks:
        pipeline_locks[pipeline_name] = asyncio.Lock()
    pipeline_lock = pipeline_locks[pipeline_name]
    lock_counts[pipeline_name] += 1
    async with pipeline_lock:
        try:
            status = await async_api(
                update_mlmd,
                query,
                req_info["json_payload"],
                pipeline_name,
                "push",
                req_info["exec_uuid"],
            )
            if status == "invalid_json_payload":
                raise HTTPException(status_code=400, detail="Invalid JSON payload. The pipeline name is missing.")
            if status == "version_update":
                raise HTTPException(status_code=422, detail="version_update")
            if status != "exists":
                await update_global_exe_dict(pipeline_name)
                await update_global_art_dict(pipeline_name)
        finally:
            lock_counts[pipeline_name] -= 1
            if lock_counts[pipeline_name] == 0:
                del pipeline_locks[pipeline_name]
                del lock_counts[pipeline_name]
    return {"status": status}


async def mlmd_pull(info: MLMDPullRequest):
    """Pull MLMD metadata from the server."""
    pipeline_name = info.pipeline_name
    exec_uuid = info.exec_uuid
    last_sync_time = info.last_sync_time
    print("mlmd pull started")
    print("......................")
    await check_mlmd_file_exists()
    if pipeline_name:
        await check_pipeline_exists(pipeline_name)
        json_payload = await async_api(
            get_mlmd_from_server,
            query,
            pipeline_name,
            exec_uuid,
            last_sync_time,
            dict_of_exe_ids,
        )
    else:
        json_payload = await async_api(get_mlmd_from_server, query, None, None, last_sync_time)

    if json_payload is None:
        raise HTTPException(status_code=406, detail=f"Pipeline {pipeline_name} not found.")
    return json_payload


async def execution_lineage(request: Request, uuid: str, pipeline_name: str):
    """Get execution lineage for D3 tree visualization."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)
    response = await async_api(
        query_execution_lineage_d3tree,
        query,
        pipeline_name,
        dict_of_exe_ids,
        uuid,
    )
    return response


async def artifact_lineage_tangled(request: Request, pipeline_name: str) -> Optional[List[List[Dict[str, Any]]]]:
    """Get artifact lineage for tangled tree visualization."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)
    response = await async_api(
        query_artifact_lineage_d3tree,
        query,
        pipeline_name,
        dict_of_art_ids,
    )
    return response


async def artifact_execution_lineage(request: Request, pipeline_name: str):
    """Get artifact-execution lineage visualization."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)
    response = await async_api(
        query_visualization_artifact_execution,
        query,
        pipeline_name,
        dict_of_art_ids,
        dict_of_exe_ids,
    )
    return response


async def list_of_executions(request: Request, pipeline_name: str):
    """Get list of executions for a pipeline."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)
    response = await async_api(executions_list, query, pipeline_name, dict_of_exe_ids)
    return response


async def artifact_types():
    """Get list of artifact types."""
    await check_mlmd_file_exists()
    artifact_types_list = await async_api(get_artifact_types, query)
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


async def upload_python_env(request: Request, file: UploadFile):
    """Upload Python environment file."""
    try:
        if file.filename is None:
            raise HTTPException(status_code=400, detail="No file uploaded")
        file_path = os.path.join("/cmf-server/data/env/", os.path.basename(file.filename))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        return {"message": f"File '{file.filename}' uploaded successfully"}
    except Exception as e:
        return {"error": f"Failed to up load file: {e}"}


async def get_python_env(file_name: str) -> str:
    """Retrieve Python environment file content."""
    if not (file_name.endswith(".txt") or file_name.endswith(".yaml")):
        raise HTTPException(
            status_code=400, detail="Unsupported file extension. Use .txt or .yaml"
        )

    file_path = os.path.join("/cmf-server/data/env/", os.path.basename(file_name))
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path, "r") as file:
            content = file.read()
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


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


@router.post("/mlmd/push")
async def normalized_mlmd_push(request: Request, info: MLMDPushRequest):
    request_id = getattr(request.state, "request_id", "")
    result = await mlmd_push(info)
    return success_response(
        data=result,
        message="MLMD pushed successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/mlmd/pull", response_class=HTMLResponse)
async def normalized_mlmd_pull(request: Request, info: MLMDPullRequest):
    return await mlmd_pull(info)


@router.get("/lineage/execution/{uuid}/{pipeline_name}")
async def normalized_execution_lineage(request: Request, uuid: str, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await execution_lineage(request, uuid, pipeline_name)
    return success_response(
        data=result,
        message="Execution lineage retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/lineage/artifact/{pipeline_name}")
async def normalized_artifact_lineage(request: Request, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await artifact_lineage_tangled(request, pipeline_name)
    return success_response(
        data=result,
        message="Artifact lineage retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/lineage/artifact-execution/{pipeline_name}")
async def normalized_artifact_execution_lineage(request: Request, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await artifact_execution_lineage(request, pipeline_name)
    return success_response(
        data=result,
        message="Artifact-execution lineage retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/executions/{pipeline_name}")
async def normalized_list_of_executions(request: Request, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await list_of_executions(request, pipeline_name)
    return success_response(
        data=result,
        message="Executions retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/model-card")
async def normalized_model_card(request: Request, modelId: int):
    request_id = getattr(request.state, "request_id", "")
    result = await model_card(request, modelId)
    return success_response(
        data=result,
        message="Model card retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/python-env")
async def normalized_upload_python_env(request: Request, file: UploadFile = File(...)):
    request_id = getattr(request.state, "request_id", "")
    result = await upload_python_env(request, file)
    return success_response(
        data=result,
        message="Python environment uploaded successfully",
        code=201,
        request_id=request_id,
    )


@router.get("/python-env")
async def normalized_get_python_env(request: Request, file_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await get_python_env(file_name)
    return success_response(
        data=result,
        message="Python environment retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/label")
async def normalized_upload_label(request: Request, file: UploadFile = File(...)):
    request_id = getattr(request.state, "request_id", "")
    result = await upload_label(request, file)
    return success_response(
        data=result,
        message="Label uploaded successfully",
        code=201,
        request_id=request_id,
    )


@router.get("/label-data")
async def normalized_get_label_data(request: Request, file_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await get_label_data(file_name)
    return success_response(
        data=result,
        message="Label data retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/metadata/push")
async def metadata_push(request: Request, info: MLMDPushRequest):
    request_id = getattr(request.state, "request_id", "")
    result = await mlmd_push(info)
    return success_response(
        data=result,
        message="MLMD pushed successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/metadata/pull", response_class=HTMLResponse)
async def metadata_pull(request: Request, info: MLMDPullRequest):
    return await mlmd_pull(info)


@router.get("/metadata/artifact-types")
async def metadata_artifact_types(request: Request):
    request_id = getattr(request.state, "request_id", "")
    result = await artifact_types()
    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/metadata/model-card")
async def metadata_model_card(request: Request, modelId: int):
    request_id = getattr(request.state, "request_id", "")
    result = await model_card(request, modelId)
    return success_response(
        data=result,
        message="Model card retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/metadata/execution-lineage/{uuid}/{pipeline_name}")
async def metadata_execution_lineage(request: Request, uuid: str, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await execution_lineage(request, uuid, pipeline_name)
    return success_response(
        data=result,
        message="Execution lineage retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/metadata/artifact-lineage/{pipeline_name}")
async def metadata_artifact_lineage(request: Request, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await artifact_lineage_tangled(request, pipeline_name)
    return success_response(
        data=result,
        message="Artifact lineage retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/metadata/artifact-execution-lineage/{pipeline_name}")
async def metadata_artifact_execution_lineage(request: Request, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await artifact_execution_lineage(request, pipeline_name)
    return success_response(
        data=result,
        message="Artifact-execution lineage retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/metadata/list-of-executions/{pipeline_name}")
async def metadata_list_of_executions(request: Request, pipeline_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await list_of_executions(request, pipeline_name)
    return success_response(
        data=result,
        message="Executions retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/metadata/python-env")
async def metadata_upload_python_env(request: Request, file: UploadFile = File(...)):
    request_id = getattr(request.state, "request_id", "")
    result = await upload_python_env(request, file)
    return success_response(
        data=result,
        message="Python environment uploaded successfully",
        code=201,
        request_id=request_id,
    )


@router.get("/metadata/python-env")
async def metadata_get_python_env(request: Request, file_name: str):
    request_id = getattr(request.state, "request_id", "")
    result = await get_python_env(file_name)
    return success_response(
        data=result,
        message="Python environment retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/metadata/label")
async def metadata_upload_label(request: Request, file: UploadFile = File(...)):
    request_id = getattr(request.state, "request_id", "")
    result = await upload_label(request, file)
    return success_response(
        data=result,
        message="Label uploaded successfully",
        code=201,
        request_id=request_id,
    )


@router.get("/metadata/label-data")
async def metadata_get_label_data(request: Request, file_name: str):

    request_id = getattr(request.state, "request_id", "")
    result = await get_label_data(file_name)
    return success_response(
        data=result,
        message="Label data retrieved successfully",
        code=200,
        request_id=request_id,
    )
