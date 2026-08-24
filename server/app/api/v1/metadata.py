"""
Metadata API endpoints and business logic.

This module contains all metadata-related API endpoints and their business logic,
including MLMD push/pull, 
"""


import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request,HTTPException
from fastapi.responses import HTMLResponse

from server.app.db.dbconfig import get_db
from server.app.schemas.requests import MLMDPullRequest, MLMDPushRequest
from server.app.schemas.responses import success_response
from server.app.main import (
    query,
    dict_of_art_ids,
    dict_of_exe_ids,
    pipeline_locks,
    lock_counts,
    update_global_art_dict,
    update_global_exe_dict,
)
from server.app.get_data import (
    get_mlmd_from_server,
    get_all_artifact_ids,
    get_all_exe_ids,
    async_api, 
)
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

@router.post("/mlmd/push")
async def metadata_push(request: Request, info: MLMDPushRequest):
    result = await mlmd_push(info)
    return success_response(
        data=result,
        message="MLMD pushed successfully",
        code=200,
    )


@router.post("/mlmd/pull", response_class=HTMLResponse)
async def metadata_pull(request: Request, info: MLMDPullRequest):
    return await mlmd_pull(info)

