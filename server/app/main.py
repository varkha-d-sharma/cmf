# cmf-server api's
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import pandas as pd
import asyncio
from server.app.get_data import (
    get_all_artifact_ids,
    get_all_exe_ids,
    async_api,
)
from server.app.services.mlmd_state import (
    query,
    dict_of_art_ids,
    dict_of_exe_ids,
)

from server.app.services.scheduler import schedule_runner
from server.app.db.dbconfig import init_db
from pathlib import Path
import typing as t
import dotenv
from jsonpath_ng.ext import parse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from server.app.schemas.responses import error_response
dotenv.load_dotenv()


# ==================== Router Imports ====================
from server.app.api.v1.metadata import router as metadata_router
from server.app.api.v1.pipelines import router as pipelines_router
from server.app.api.v1.servers import router as servers_router, sync_metadata
from server.app.api.v1.executions import router as executions_router
from server.app.api.v1.artifacts import router as artifacts_router
from server.app.api.v1.lineage import router as lineage_router

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
app.include_router(executions_router)
app.include_router(artifacts_router)
app.include_router(lineage_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
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
    )
    return JSONResponse(status_code=422, content=response.dict())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException"""
    response = error_response(
        message=str(exc.detail),
        code=exc.status_code,
        errors=[],
    )
    return JSONResponse(status_code=exc.status_code, content=response.dict())

BASE_PATH = Path(__file__).resolve().parent
app.mount("/cmf-server/data/static", StaticFiles(directory="/cmf-server/data/static"), name="static")

@app.get("/")
async def read_root(request: Request):
    return {"cmf-server"}


# Business logic functions have been moved to their respective router modules:
# - Metadata functions: server/app/api/v1/metadata.py
# - Pipeline functions: server/app/api/v1/pipelines.py  
# - Server functions: server/app/api/v1/servers.py
# - Execution functions: server/app/api/v1/executions.py
# - Artifact functions: server/app/api/v1/artifacts.py
# - Lineage functions: server/app/api/v1/lineage.py
