"""
Server API endpoints and business logic.

This module contains all server-related API endpoints and their business logic,
including server registration, sync, scheduling, and logging.
"""

import io
import json
import os
import time
import zipfile
import asyncio
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    register_server_details,
    get_sync_status,
    get_registered_server_details,
    update_sync_status,
    create_schedule,
    list_schedules,
    get_registered_server_by_id,
    list_sync_logs,
    get_completed_logs_by_server,
    delete_schedule,
)
from server.app.schemas.dataframe import ScheduleCreateRequest, ServerRegistrationRequest
from server.app.core.responses import success_response
from server.app.core.globals import (
    query,
    LOCAL_ADDRESSES,
    dict_of_art_ids,
    dict_of_exe_ids,
)
from server.app.utils import extract_hostname
from server.app.get_data import (
    server_mlmd_pull,
    log_sync_attempt,
    async_api,
    compute_next_run_from_recurrence,
    compute_initial_next_run_utc,
)
from cmflib.cmf_federation import update_mlmd

router = APIRouter(prefix="/v1", tags=["servers"])


# ==================== Helper Functions ====================

async def update_global_art_dict(pipeline_name):
    """Update global artifact IDs dictionary for a pipeline."""
    from server.app.get_data import get_all_artifact_ids
    output_dict = await async_api(get_all_artifact_ids, query, dict_of_exe_ids, pipeline_name)
    dict_of_art_ids[pipeline_name] = output_dict[pipeline_name]
    return


async def update_global_exe_dict(pipeline_name):
    """Update global execution IDs dictionary for a pipeline."""
    from server.app.get_data import get_all_exe_ids
    output_dict = await async_api(get_all_exe_ids, query, pipeline_name)
    dict_of_exe_ids[pipeline_name] = output_dict[pipeline_name]
    return


# ==================== Business Logic Functions ====================

async def register_server(request: ServerRegistrationRequest, db: AsyncSession = Depends(get_db)):
    """Register a new server."""
    try:
        server_name = request.server_name
        server_url = request.server_url
        server = extract_hostname(server_url)

        # Check user is registering with own details
        if server in LOCAL_ADDRESSES:
            return {"message": "Registration failed: Cannot register the server with its own details."}

        # Step 1: Send a request to the target server for acknowledgement
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{server_url}/api/acknowledge",
                    json={"server_name": server_name, "server_url": server_url}
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Target server did not respond successfully")
                target_server_data = response.json()
            except httpx.RequestError:
                raise HTTPException(status_code=500, detail="Target server is not reachable")

        # Save server details in the database
        return await register_server_details(db, server_name, server_url)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register server: {e}")


async def sync_metadata(request: ServerRegistrationRequest, db: AsyncSession = Depends(get_db), skip_logging: bool = False):
    """
    Synchronize metadata for a registered server.

    Args:
        request (ServerRegistrationRequest): The request containing server details.
        skip_logging (bool): If True, prevents duplicate log entries in the database.
            When the background scheduler calls this function, it creates its own 
            schedule and log entries, so we skip the immediate sync logging to avoid 
            duplicate records. Set to False for manual/API-triggered syncs.

    Returns:
        dict: A response containing the sync status and last sync time.

    Raises:
        HTTPException: If the server is not found or an error occurs during synchronization.
    """
    server_name = request.server_name
    server_url = request.server_url
    current_utc_epoch_time = int(time.time() * 1000)
    
    try:
        # Verify the server exists in the registered servers list and get last sync time
        row = await get_sync_status(db, server_name, server_url)

        if not row:
            # Log the failed sync attempt before raising the exception
            await log_sync_attempt("failed", "Server not found in the registered servers list", db, server_name, server_url, current_utc_epoch_time, skip_logging)
            raise HTTPException(status_code=404, detail="Server not found in the registered servers list")

        last_sync_time = row[0]['last_sync_time']

        # Pull MLMD data from the target server using the /mlmd_pull endpoint
        json_payload = await server_mlmd_pull(server_url, last_sync_time)

        json_data = {
            "exec_uuid": None,
            "json_payload": json.dumps(json_payload),
            "pipeline_name": None
        }

        # Ensure the pipeline name in req_info matches the one in the JSON payload
        # to maintain data integrity
        pipelines = json_payload.get("Pipeline", [])
        len_pipelines = len(pipelines)
        pipeline_names = []

        if not pipelines:
            await log_sync_attempt("success", "Nothing to sync", db, server_name, server_url, current_utc_epoch_time, skip_logging)
            return {
                "message": "Nothing to sync",
                "status": "success",
                "last_sync_time": current_utc_epoch_time
            }

        # in case of push check pipeline name exists inside mlmd_data
        pipeline_names = [pipeline.get("name") for pipeline in pipelines]

        # Push the JSON payload to the host server
        status = await async_api(update_mlmd, query, json_data["json_payload"], None, "push", None)
        if status == "invalid_json_payload":
            # Invalid JSON payload, return 400 Bad Request
            await log_sync_attempt("failed", "Invalid JSON payload. The pipeline name is missing.", db, server_name, server_url, current_utc_epoch_time, skip_logging)
            raise HTTPException(status_code=400, detail="Invalid JSON payload. The pipeline name is missing.")           
        if status == "version_update":
            # Raise an HTTPException with status code 422
            await log_sync_attempt("failed", "Version update required", db, server_name, server_url, current_utc_epoch_time, skip_logging)
            raise HTTPException(status_code=422, detail="version_update")
        message = "Nothing to sync."
        if status != "exists":
            if not last_sync_time:
                message = f"Host server is syncing with the selected server '{server_name}' at address '{server_url}' for the first time."
            else:
                message = f"Host server is being synced with the selected server '{server_name}' at address '{server_url}'."
            for pipeline_name in pipeline_names:
                await update_global_exe_dict(pipeline_name)
                await update_global_art_dict(pipeline_name)

        # Update the last_sync_time in the database only if sync status is successful
        if status == "success":
            await update_sync_status(db, current_utc_epoch_time, server_name, server_url)

        # Log this immediate sync
        await log_sync_attempt(status, message, db, server_name, server_url, current_utc_epoch_time, skip_logging)

        return {
            "message": message,
            "status": status,
            "last_sync_time": current_utc_epoch_time
        }

    except HTTPException:
        # Re-raise HTTPExceptions (already logged above)
        raise
    except Exception as e:
        print(e)
        # Log unexpected errors
        await log_sync_attempt("failed", f"Failed to sync metadata: {str(e)}", db, server_name, server_url, current_utc_epoch_time, skip_logging)
        raise HTTPException(status_code=500, detail=f"Failed to sync metadata: {e}")


async def server_list(db: AsyncSession = Depends(get_db)):
    """Get list of all registered servers."""
    rows = await get_registered_server_details(db)
    return rows


def download_python_env(request: Request, list_of_files: Optional[list[str]] = Query(None)):
    """Download Python environment files as ZIP."""
    try:
        DIRECTORY = "/cmf-server/data/env/"  # Directory to be compressed
        # Check if the directory exists
        if not os.path.exists(DIRECTORY):
            return {"error": "Directory does not exist"}

        # Determine files to include in the ZIP
        files_to_zip = []
        # if list_of_files is provided, include only those files
        # else include all files in the directory
        if list_of_files:
            for file_name in list_of_files:
                file_path = os.path.join(DIRECTORY, file_name)
                if os.path.exists(file_path):
                    files_to_zip.append((file_path, file_name))
                else:
                    return {"error": f"File {file_name} does not exist"}
        else:
            if not os.listdir(DIRECTORY):
                return {"error": "Directory is empty"}
            for root, _, files in os.walk(DIRECTORY):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, DIRECTORY)
                    files_to_zip.append((file_path, arcname))

        # Create and send the ZIP file 
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path, arcname in files_to_zip:
                zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={'python_env_files.zip' if list_of_files else 'python_env_folder.zip'}"
            }
        )
    except Exception as e:
        return {"error": f"Failed to download files: {e}"}


async def schedule_sync(request: ScheduleCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a one-time or periodic sync schedule for a registered server.

    Args:
        request (ScheduleCreateRequest): Schedule configuration payload.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Created schedule id and computed next run time.
    """
    try:
        # Validate that target server exists before creating a schedule.
        server = await get_registered_server_by_id(db, request.server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Registered server not found")

        # Parse local ISO datetime and convert to UTC epoch ms
        try:
            tz = ZoneInfo(request.timezone)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid timezone")

        try:
            # Accepts e.g. 2026-01-04T15:00
            local_dt = datetime.strptime(request.start_time_local_iso, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format. Use YYYY-MM-DDTHH:MM")

        # Convert local datetime with timezone info to UTC epoch milliseconds
        local_dt = local_dt.replace(tzinfo=tz)
        start_utc_ms = int(local_dt.astimezone(ZoneInfo("UTC")).timestamp() * 1000)

        # Derive recurrence fields from the selected start datetime.
        derived_time = local_dt.strftime("%H:%M")
        recurrence_mode = None if request.one_time else request.recurrence_mode
        daily_time = derived_time if recurrence_mode == "daily" else None
        weekly_day = request.weekly_day if recurrence_mode == "weekly" else None
        weekly_time = derived_time if recurrence_mode == "weekly" else None

        now_ms = int(time.time() * 1000)
        if request.one_time:
            # One-time schedules must be strictly in the future.
            if start_utc_ms <= now_ms:
                raise HTTPException(status_code=400, detail="Start time must be in the future for one-time schedules")
            next_ms = start_utc_ms
        else:
            # Compute first due run for periodic schedules based on recurrence settings.
            next_ms = await compute_initial_next_run_utc(
                start_utc_ms,
                now_ms,
                request.timezone,
                recurrence_mode,
                interval_unit=request.interval_unit,
                interval_value=request.interval_value,
                daily_time=daily_time,
                weekly_day=weekly_day,
                weekly_time=weekly_time,
            )

        # Persist schedule details and return created id plus first next-run timestamp.
        created = await create_schedule(
            db,
            server_id=request.server_id,
            timezone=request.timezone,
            start_time_utc=start_utc_ms,
            next_run_time_utc=next_ms,
            created_at=now_ms,
            one_time=request.one_time,
            recurrence_mode=recurrence_mode,
            interval_unit=request.interval_unit,
            interval_value=request.interval_value,
            daily_time=daily_time,
            weekly_day=weekly_day,
            weekly_time=weekly_time,
        )
        return {"message": "Schedule created", "schedule_id": created["id"], "next_run_time_utc": next_ms}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {e}")


async def get_schedules(server_id: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    """
    Retrieve active schedules, optionally filtered by server id.

    Args:
        server_id (Optional[int]): Optional server id filter.
        db (AsyncSession): Database session dependency.

    Returns:
        list: Active schedule rows.
    """
    rows = await list_schedules(db, server_id)
    return rows


async def get_schedule_logs(schedule_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve run history logs for a schedule id.

    Args:
        schedule_id (int): Schedule id.
        db (AsyncSession): Database session dependency.

    Returns:
        list: Sync log rows ordered by latest first.
    """
    rows = await list_sync_logs(db, schedule_id)
    return rows


async def get_server_completed_logs(server_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all completed sync logs for a specific server.
    
    Args:
        server_id (int): The ID of the server to get logs for.
    
    Returns:
        list: A list of completed sync logs with sync_type, status, message, and timestamp.
    """
    try:
        logs = await get_completed_logs_by_server(db, server_id)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch completed logs: {e}")


async def delete_schedule_route(schedule_id: int, db: AsyncSession = Depends(get_db)):
    """
    Deactivate a schedule so future runs stop.

    Args:
        schedule_id (int): Schedule id to deactivate.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Deactivation status message.
    """
    return await delete_schedule(db, schedule_id)


@router.post("/servers/register")
async def register_server_route(request: Request, info: ServerRegistrationRequest, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await register_server(info, db)
    return success_response(
        data=result,
        message="Server registered successfully",
        code=201,
        request_id=request_id,
    )


@router.post("/servers/sync")
async def sync_server(request: Request, info: ServerRegistrationRequest, db: AsyncSession = Depends(get_db), skip_logging: bool = False):
    request_id = getattr(request.state, "request_id", "")
    result = await sync_metadata(info, db, skip_logging)
    return success_response(
        data=result,
        message="Server synced successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/servers")
async def list_servers(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await server_list(db)
    return success_response(
        data=result,
        message="Servers retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.post("/schedules")
async def create_schedule(request: Request, schedule_info: ScheduleCreateRequest, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await schedule_sync(schedule_info, db)
    return success_response(
        data=result,
        message="Schedule created successfully",
        code=201,
        request_id=request_id,
    )


@router.post("/servers/schedules")
async def create_schedule_legacy(request: Request, schedule_info: ScheduleCreateRequest, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await schedule_sync(schedule_info, db)
    return success_response(
        data=result,
        message="Schedule created successfully",
        code=201,
        request_id=request_id,
    )


@router.get("/schedules")
async def list_schedules_standard(request: Request, server_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await get_schedules(server_id, db)
    return success_response(
        data=result,
        message="Schedules retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/servers/schedules")
async def list_schedules(request: Request, server_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await get_schedules(server_id, db)
    return success_response(
        data=result,
        message="Schedules retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/schedules/{schedule_id}/logs")
async def schedule_logs_standard(request: Request, schedule_id: int, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await get_schedule_logs(schedule_id, db)
    return success_response(
        data=result,
        message="Schedule logs retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/servers/schedules/{schedule_id}/logs")
async def schedule_logs(request: Request, schedule_id: int, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await get_schedule_logs(schedule_id, db)
    return success_response(
        data=result,
        message="Schedule logs retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.get("/servers/{server_id}/completed-logs")
async def server_completed_logs(request: Request, server_id: int, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await get_server_completed_logs(server_id, db)
    return success_response(
        data=result,
        message="Server completed logs retrieved successfully",
        code=200,
        request_id=request_id,
    )


@router.delete("/schedules/{schedule_id}")
async def delete_schedule_standard(request: Request, schedule_id: int, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await delete_schedule_route(schedule_id, db)
    return success_response(
        data=result,
        message="Schedule deleted successfully",
        code=200,
        request_id=request_id,
    )


@router.delete("/servers/schedules/{schedule_id}")
async def delete_server_schedule(request: Request, schedule_id: int, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    result = await delete_schedule_route(schedule_id, db)
    return success_response(
        data=result,
        message="Schedule deleted successfully",
        code=200,
        request_id=request_id,
    )
