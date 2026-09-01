"""Version 1 API routers for the CMF server."""
from fastapi import APIRouter
from server.app.api.v1.artifacts import router as artifacts_router
from server.app.api.v1.executions import router as executions_router
from server.app.api.v1.pipelines import router as pipelines_router

api_router = APIRouter(prefix="/v1")

api_router.include_router(pipelines_router)
api_router.include_router(executions_router)
api_router.include_router(artifacts_router)
