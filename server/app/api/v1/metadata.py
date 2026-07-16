from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse

from server.app.db.dbconfig import get_db
from server.app.schemas.dataframe import MLMDPullRequest, MLMDPushRequest

router = APIRouter(prefix="/v1", tags=["metadata"])


@router.post("/mlmd/push")
async def normalized_mlmd_push(info: MLMDPushRequest):
    from server.app.main import mlmd_push

    return await mlmd_push(info)


@router.post("/mlmd/pull", response_class=HTMLResponse)
async def normalized_mlmd_pull(info: MLMDPullRequest):
    from server.app.main import mlmd_pull

    return await mlmd_pull(info)


@router.get("/lineage/execution/{uuid}/{pipeline_name}")
async def normalized_execution_lineage(request: Request, uuid: str, pipeline_name: str):
    from server.app.main import execution_lineage

    return await execution_lineage(request, uuid, pipeline_name)


@router.get("/lineage/artifact/{pipeline_name}")
async def normalized_artifact_lineage(request: Request, pipeline_name: str):
    from server.app.main import artifact_lineage_tangled

    return await artifact_lineage_tangled(request, pipeline_name)


@router.get("/lineage/artifact-execution/{pipeline_name}")
async def normalized_artifact_execution_lineage(request: Request, pipeline_name: str):
    from server.app.main import artifact_execution_lineage

    return await artifact_execution_lineage(request, pipeline_name)


@router.get("/executions/{pipeline_name}")
async def normalized_list_of_executions(request: Request, pipeline_name: str):
    from server.app.main import list_of_executions

    return await list_of_executions(request, pipeline_name)


@router.post("/metadata/push")
async def metadata_push(info: MLMDPushRequest):
    from server.app.main import mlmd_push

    return await mlmd_push(info)


@router.post("/metadata/pull", response_class=HTMLResponse)
async def metadata_pull(info: MLMDPullRequest):
    from server.app.main import mlmd_pull

    return await mlmd_pull(info)


@router.get("/metadata/artifact-types")
async def metadata_artifact_types():
    from server.app.main import artifact_types

    return await artifact_types()


@router.get("/metadata/model-card")
async def metadata_model_card(request: Request, modelId: int):
    from server.app.main import model_card

    return await model_card(request, modelId)


@router.get("/metadata/execution-lineage/{uuid}/{pipeline_name}")
async def metadata_execution_lineage(request: Request, uuid: str, pipeline_name: str):
    from server.app.main import execution_lineage

    return await execution_lineage(request, uuid, pipeline_name)


@router.get("/metadata/artifact-lineage/{pipeline_name}")
async def metadata_artifact_lineage(request: Request, pipeline_name: str):
    from server.app.main import artifact_lineage_tangled

    return await artifact_lineage_tangled(request, pipeline_name)


@router.get("/metadata/artifact-execution-lineage/{pipeline_name}")
async def metadata_artifact_execution_lineage(request: Request, pipeline_name: str):
    from server.app.main import artifact_execution_lineage

    return await artifact_execution_lineage(request, pipeline_name)


@router.get("/metadata/list-of-executions/{pipeline_name}")
async def metadata_list_of_executions(request: Request, pipeline_name: str):
    from server.app.main import list_of_executions

    return await list_of_executions(request, pipeline_name)


@router.post("/metadata/python-env")
async def metadata_upload_python_env(request: Request, file: UploadFile = File(...)):
    from server.app.main import upload_python_env

    return await upload_python_env(request, file)


@router.get("/metadata/python-env")
async def metadata_get_python_env(file_name: str):
    from server.app.main import get_python_env

    return await get_python_env(file_name)


@router.post("/metadata/label")
async def metadata_upload_label(request: Request, file: UploadFile = File(...)):
    from server.app.main import upload_label

    return await upload_label(request, file)


@router.get("/metadata/label-data")
async def metadata_get_label_data(file_name: str):
    from server.app.main import get_label_data

    return await get_label_data(file_name)
