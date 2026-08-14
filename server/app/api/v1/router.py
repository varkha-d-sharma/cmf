from fastapi import APIRouter
from server.app.api.v1 import artifacts, executions, pipelines

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(pipelines.router, prefix="/pipelines", tags=["CmfQuery - Pipelines"])
api_v1_router.include_router(artifacts.router, prefix="/artifacts", tags=["CmfQuery - Artifacts"])
api_v1_router.include_router(executions.router, prefix="/executions", tags=["CmfQuery - Executions"])