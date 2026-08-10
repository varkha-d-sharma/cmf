# cmf-server api's
import io
import time
import zipfile
from fastapi import FastAPI, Request, HTTPException, Query, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pandas as pd
from typing import List, Dict, Any, Optional
from cmflib.cmfquery import CmfQuery
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from server.app.utils import extract_hostname, get_fqdn
from server.app.get_data import (
    get_mlmd_from_server,
    get_artifact_types,
    get_all_artifact_ids,
    get_all_exe_ids,
    async_api,
    get_model_data,
    executions_list,
    server_mlmd_pull,
    log_sync_attempt,
    compute_next_run_from_recurrence,
    compute_initial_next_run_utc,
)
from server.app.query_execution_lineage_d3tree import query_execution_lineage_d3tree
from server.app.query_artifact_lineage_d3tree import query_artifact_lineage_d3tree
from server.app.query_visualization_artifact_execution import query_visualization_artifact_execution
from server.app.db.dbconfig import get_db, init_db, async_session
from server.app.db.dbqueries import (
    fetch_unique_execution_stages,
    fetch_executions_by_stage,
    fetch_artifacts_by_stage,
    fetch_artifact_types_by_stage,
    register_server_details,
    get_registered_server_details,
    get_sync_status,
    update_sync_status,
    create_schedule,
    list_schedules,
    due_schedules,
    update_next_run,
    log_sync_run,
    list_sync_logs,
    get_completed_logs_by_server,
    get_registered_server_by_id,
    update_schedule_fields,
    delete_schedule,
)
from pathlib import Path
import os
import json
import typing as t
from server.app.schemas.dataframe import (
    MLMDPushRequest,
    ServerRegistrationRequest, 
    AcknowledgeRequest,
    MLMDPullRequest,
    ScheduleCreateRequest,
    ArtifactByStageRequest,
    ExecutionByStageRequest,
)
from server.app.api.v1.metadata import router as metadata_router
from server.app.api.v1.pipelines import router as pipelines_router
from server.app.api.v1.servers import router as servers_router
import httpx
import socket
import dotenv
from jsonpath_ng.ext import parse
from cmflib.cmf_federation import update_mlmd
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from server.app.core.middleware import RequestIDMiddleware
from server.app.core.exceptions import APIException
from server.app.core.responses import error_response

dotenv.load_dotenv()

# Import globals from the dedicated globals module
from server.app.core.globals import (
    query,
    dict_of_art_ids,
    dict_of_exe_ids,
    pipeline_locks,
    lock_counts,
    LOCAL_ADDRESSES,
    REACT_APP_CMF_API_URL,
)
#lifespan used to prevent multiple loading and save time for visualization.
@asynccontextmanager
async def lifespan(app: FastAPI):
    global dict_of_art_ids
    global dict_of_exe_ids

    # Initialize the database schema
    await init_db()

    if query:
        # loaded execution ids with names into memory
        exe_ids = await async_api(get_all_exe_ids, query)
        dict_of_exe_ids.update(exe_ids)
        # loaded artifact ids into memory
        art_ids = await async_api(get_all_artifact_ids, query, dict_of_exe_ids)
        dict_of_art_ids.update(art_ids)
    # Start background scheduler task
    app.state.scheduler_task = asyncio.create_task(schedule_runner())
    yield
    # Cancel scheduler on shutdown
    # If FastAPI is down, no scheduled sync runs.
    # On restart, the scheduler resumes from DB state.
    # Missed schedules are not deleted or skipped automatically.
    # One-time schedules run once after restart if overdue.
    # Periodic schedules keep running and may attempt backlog catch-up.
    # There is no explicit restart cleanup/update pass for scheduled_syncs.
    task = getattr(app.state, "scheduler_task", None)
    if task:
        task.cancel()
    dict_of_art_ids.clear()
    dict_of_exe_ids.clear()

app = FastAPI(title="cmf-server", lifespan=lifespan, root_path="/api")


app.include_router(pipelines_router)
app.include_router(metadata_router)
app.include_router(servers_router)

# Add Request ID Middleware (must be added first, before other middleware)
app.add_middleware(RequestIDMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions"""
    request_id = getattr(request.state, "request_id", "")
    response = error_response(
        message=exc.message,
        code=exc.code,
        errors=exc.errors,
        data=exc.data,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.code, content=response.dict())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    request_id = getattr(request.state, "request_id", "")
    # Parse validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0])
        errors.append({
            "field": field,
            "message": error["msg"],
            "code": error["type"],
        })
    
    response = error_response(
        message="Request validation failed",
        code=422,
        errors=errors,
        request_id=request_id,
    )
    return JSONResponse(status_code=422, content=response.dict())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException"""
    request_id = getattr(request.state, "request_id", "")
    response = error_response(
        message=str(exc.detail),
        code=exc.status_code,
        errors=[],
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=response.dict())

BASE_PATH = Path(__file__).resolve().parent
app.mount("/cmf-server/data/static", StaticFiles(directory="/cmf-server/data/static"), name="static")


async def schedule_runner():
    """Input: none
    Output: none (runs continuously)
    Description: Background loop that executes due schedules using 3-stage server validation.
    Step 1: Query all due schedules using current UTC epoch milliseconds.
    Step 2: Check if server record exists in DB (registration check).
            - If NOT registered: permanent config issue -> deactivate ALL schedule types.
    Step 3: Check if the registered server is currently reachable (liveness check).
            - If NOT alive: transient outage:
                one-time  -> deactivate (missed its window, cannot retry)
                periodic  -> log failure, compute next run, keep active for retry
    Step 4: Server is registered AND alive -> perform sync, log result, advance schedule.
    Step 5: Sleep 30 seconds and repeat.
    Example: periodic schedule with unreachable server logs failure and reschedules."""
    while True:
        try:
            async with async_session() as db:
                now_ms = int(time.time() * 1000)
                schedules = await due_schedules(db, now_ms)
                for sch in schedules:
                    sync_type = "schedule_once" if sch.get("one_time") else "periodic"

                    # Stage 1: Registration check
                    # Checks whether the server record still exists in the registered_servers
                    # table. A missing record is a permanent configuration issue (server was
                    # deleted/deregistered), not a temporary outage. Deactivate all schedule
                    # types so we do not keep polling a server that no longer exists.
                    server = await get_registered_server_by_id(db, sch["server_id"])
                    if not server:
                        await log_sync_run(
                            db, sch["id"], now_ms, "failed",
                            "Server record not found in registered servers. Schedule deactivated.",
                            sync_type,
                        )
                        await update_schedule_fields(db, schedule_id=sch["id"], active=False, status="failed")
                        continue

                    # Stage 2: Liveness check
                    # Server is registered. Now check if it is currently reachable by sending
                    # a lightweight ping to /api/acknowledge (5-second timeout).
                    # This distinguishes transient network/outage failures from config errors.
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            response = await client.post(
                                f"{server['host_info']}/api/acknowledge",
                                json={"server_name": server["server_name"], "server_url": server["host_info"]}
                            )
                        server_alive = response.status_code == 200
                    except Exception:
                        server_alive = False
                    if not server_alive:
                        if sch.get("one_time"):
                            # One-time sync missed its scheduled window during outage.
                            # It will not retry automatically -> deactivate.
                            await log_sync_run(
                                db, sch["id"], now_ms, "failed",
                                "Server is not reachable. One-time sync deactivated.",
                                sync_type,
                            )
                            await update_schedule_fields(db, schedule_id=sch["id"], active=False, status="failed")
                        else:
                            # Periodic sync: transient outage, keep schedule alive and
                            # advance next_run_time_utc so it retries at the next interval.
                            await log_sync_run(
                                db, sch["id"], now_ms, "failed",
                                "Server is not reachable. Will retry at next scheduled run.",
                                sync_type,
                            )
                            next_ms = await compute_next_run_from_recurrence(
                                sch["next_run_time_utc"],
                                sch["timezone"],
                                sch["recurrence_mode"],
                                interval_unit=sch.get("interval_unit"),
                                interval_value=sch.get("interval_value"),
                                daily_time=sch.get("daily_time"),
                                weekly_day=sch.get("weekly_day"),
                                weekly_time=sch.get("weekly_time"),
                            )
                            await update_next_run(db, sch["id"], next_ms)
                            await update_schedule_fields(db, schedule_id=sch["id"], status="active")
                        continue

                    # Stage 3: Server is registered and alive -> perform sync
                    req = ServerRegistrationRequest(server_name=server["server_name"], server_url=server["host_info"])
                    status_msg = ""
                    status = "failed"
                    await update_schedule_fields(db, schedule_id=sch["id"], status="running")
                    try:
                        result = await sync_metadata(request=req, db=db, skip_logging=True)
                        status = result.get("status", "unknown")
                        status_msg = result.get("message", "")
                    except HTTPException as he:
                        status = "failed"
                        status_msg = he.detail if isinstance(he.detail, str) else str(he.detail)
                    except Exception as e:
                        status = "failed"
                        status_msg = f"Unexpected error: {e}"

                    await log_sync_run(db, sch["id"], now_ms, status, status_msg, sync_type)
                    if sch.get("one_time"):
                        # One-time schedules always deactivate after their single attempt.
                        await update_schedule_fields(db, schedule_id=sch["id"], active=False, status="completed")
                    else:
                        # Periodic: advance to next run time and keep active.
                        next_ms = await compute_next_run_from_recurrence(
                            sch["next_run_time_utc"],
                            sch["timezone"],
                            sch["recurrence_mode"],
                            interval_unit=sch.get("interval_unit"),
                            interval_value=sch.get("interval_value"),
                            daily_time=sch.get("daily_time"),
                            weekly_day=sch.get("weekly_day"),
                            weekly_time=sch.get("weekly_time"),
                        )
                        await update_next_run(db, sch["id"], next_ms)
                        await update_schedule_fields(db, schedule_id=sch["id"], status="active")
        except Exception as e:
            # Prevent scheduler from crashing; log to stdout
            print(f"Scheduler error: {e}")

        await asyncio.sleep(30)


@app.get("/")
async def read_root(request: Request):
    return {"cmf-server"}


# Business logic functions have been moved to their respective router modules:
# - Metadata functions: server/app/api/v1/metadata.py
# - Pipeline functions: server/app/api/v1/pipelines.py  
# - Server functions: server/app/api/v1/servers.py


"""
following APIs are no longer in use within the project but is retained for reference or potential future use.

@app.get("/execution-lineage/force-directed-graph/{pipeline_name}/{uuid}")
async def execution_lineage(request: Request, pipeline_name: str, uuid: str):
    '''
      returns dictionary of nodes and links for given execution_type.
      response = {
                   nodes: [{id:"",name:"",execution_uuid:""}],
                   links: [{source:1,target:4},{}],
                 } 
    '''
    # checks if mlmd file exists on server
    if os.path.exists(server_store_path):
        query = cmfquery.CmfQuery(server_store_path)
        if (pipeline_name in query.get_pipeline_names()):
            response = await async_api(query_execution_lineage_d3force, server_store_path, pipeline_name, dict_of_exe_ids, uuid)
    else:
        response = None
    return response


@app.get("/artifact-lineage/force-directed-graph/{pipeline_name}")
async def artifact_lineage(request: Request, pipeline_name: str):
    '''
      This api returns dictionary of nodes and links for given pipeline.
      response = {
                   nodes: [{id:"",name:""}],
                   links: [{source:1,target:4},{}],
                 }

    '''
    # checks if mlmd file exists on server
    if os.path.exists(server_store_path):
        query = cmfquery.CmfQuery(server_store_path)
        if (pipeline_name in query.get_pipeline_names()):
            response=await async_api(get_lineage_data, server_store_path, pipeline_name, "Artifacts", dict_of_art_ids, dict_of_exe_ids)
            return response
        else:
            return f"Pipeline name {pipeline_name} doesn't exist."

    else:
        return None

"""
