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
Metadata API endpoints and business logic.

This module contains all metadata-related API endpoints and their business logic,
including MLMD push/pull, 
"""


import asyncio
import os
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from server.app.db.dbconfig import get_db
from server.app.schemas.requests import MLMDPullRequest, MLMDPushRequest
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import mlmd_state
from server.app.get_data import (
    get_mlmd_from_server,
    async_api, 
)
from cmflib.cmf_federation import update_mlmd

router = APIRouter(prefix="/v1", tags=["metadata"])

# ==================== Business Logic Functions ====================

# API to post MLMD file to cmf-server.
async def mlmd_push(info: MLMDPushRequest, request: Request | None = None):
    """Push MLMD metadata to the server."""
    state = (request.app.state.mlmd if request is not None else mlmd_state)
    print("mlmd push started")
    print("......................")
    status = "unknown_error"
    req_info = info.model_dump() # Serializing the input data into a dictionary using model_dump()
    pipeline_name = req_info.get("pipeline_name", "")
    if pipeline_name not in state.pipeline_locks: # create lock object for pipeline if it doesn't exists in lock
        state.pipeline_locks[pipeline_name] = asyncio.Lock()
    pipeline_lock = state.pipeline_locks[pipeline_name]
    state.lock_counts[pipeline_name] += 1  # increment lock count by 1 if pipeline going to enter inside lock section
    async with pipeline_lock:
        try:
            status = await async_api(
                update_mlmd,
                state.query,
                req_info["json_payload"],
                pipeline_name,
                "push",
                req_info["exec_uuid"],
            )
            # Invalid JSON payload, return 400 Bad Request
            if status == "invalid_json_payload":
                raise HTTPException(status_code=400, detail="Invalid JSON payload. The pipeline name is missing.")
            if status == "version_update":
                # Raise an HTTPException with status code 422
                raise HTTPException(status_code=422, detail="version_update")
            if status != "exists":
                 # async function
                await state.update_global_exe_dict(pipeline_name)
                await state.update_global_art_dict(pipeline_name)
        finally:
            state.lock_counts[pipeline_name] -= 1 # Decrement the reference count after lock released
            if state.lock_counts[pipeline_name] == 0:  #if lock_counts of pipeline is zero means lock is release from it
                del state.pipeline_locks[pipeline_name] # Remove the lock if it's no longer needed
                del state.lock_counts[pipeline_name]
    return {"status": status}


# API to get MLMD file from cmf-server.
async def mlmd_pull(info: MLMDPullRequest, request: Request | None = None):
    """Pull MLMD metadata from the server."""
    state = (request.app.state.mlmd if request is not None else mlmd_state)
    pipeline_name = info.pipeline_name
    exec_uuid = info.exec_uuid
    last_sync_time = info.last_sync_time
    print("mlmd pull started")
    print("......................")
    # checks if mlmd file exists on server
    await state.check_mlmd_file_exists()
    if pipeline_name:
        # checks if pipeline exists
        await state.check_pipeline_exists(pipeline_name)
        #json_payload values can be json data, none or no_exec_id.
        json_payload = await async_api(
            get_mlmd_from_server,
            state.query,
            pipeline_name,
            exec_uuid,
            last_sync_time,
            state.dict_of_exe_ids,
        )
    else:
        json_payload = await async_api(get_mlmd_from_server, state.query, None, None, last_sync_time)

    if json_payload is None:
        raise HTTPException(status_code=406, detail=f"Pipeline {pipeline_name} not found.")
    return json_payload


# Upload TensorBoard logs for a pipeline.
async def upload_tensorboard_logs(
    request: Request,
    pipeline_name: str = Query(..., description="Pipeline name"),
    file: UploadFile = File(..., description="The file to upload"),
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
    except Exception as e:
        return {"error": f"Failed to up load file: {e}"}


@router.post("/mlmd/push")
async def metadata_push(request: Request, info: MLMDPushRequest):
    result = await mlmd_push(info, request)
    return success_response(
        data=result,
        message="MLMD pushed successfully",
        code=200,
    )


@router.post("/mlmd/pull", response_class=HTMLResponse)
async def metadata_pull(request: Request, info: MLMDPullRequest):
    return await mlmd_pull(info, request)


@router.post("/tensorboard")
async def tensorboard_upload(
    request: Request,
    pipeline_name: str = Query(..., description="Pipeline name"),
    file: UploadFile = File(..., description="The file to upload"),
):
    result = await upload_tensorboard_logs(request, pipeline_name, file)
    return success_response(
        data=result,
        message="TensorBoard file uploaded successfully",
        code=200,
    )

