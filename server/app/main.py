# cmf-server api's
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from server.app.get_data import (
    get_all_artifact_ids,
    get_all_exe_ids,
    async_api,
)
from server.app.services.mlmd_state import (
    mlmd_state,
)
from server.app.services.scheduler import schedule_runner
from server.app.db.dbconfig import init_db
from pathlib import Path
import dotenv
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from server.app.schemas.responses import error_response
from server.app.api.v1 import api_router
dotenv.load_dotenv()

#lifespan used to prevent multiple loading and save time for visualization.
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mlmd = mlmd_state

    # Initialize the database schema
    await init_db()

    if app.state.mlmd.query:
        # loaded execution ids with names into memory
        exe_ids = await async_api(get_all_exe_ids, app.state.mlmd.query)
        app.state.mlmd.dict_of_exe_ids.update(exe_ids)
        # loaded artifact ids into memory
        art_ids = await async_api(get_all_artifact_ids, app.state.mlmd.query, app.state.mlmd.dict_of_exe_ids)
        app.state.mlmd.dict_of_art_ids.update(art_ids)
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
    app.state.mlmd.dict_of_art_ids.clear()
    app.state.mlmd.dict_of_exe_ids.clear()

app = FastAPI(title="cmf-server", lifespan=lifespan, root_path="/api")
app.state.mlmd = mlmd_state

app.include_router(api_router)

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
