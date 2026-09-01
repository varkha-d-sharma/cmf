import json
from cmflib.cmfquery import CmfQuery
from fastapi import APIRouter, Depends
from server.app.services.mlmd_state import mlmd_state
from server.app.schemas.responses import ErrorDetail, LastSyncTimeRequest, PipelineJsonRequest, PipelineNameRequest, APIResponse

router = APIRouter(prefix="/v1", tags=["pipelines"])
query = mlmd_state.query

# ==================== Business Logic Functions For CMFQuery ====================

def _dataframe_records(dataframe):
    # Replace NaN values with None and convert the DataFrame to a list of dictionaries
    return dataframe.where(dataframe.notna(), None).to_dict(orient="records")


def list_pipeline_names(query: CmfQuery) -> APIResponse:
    pipeline_names = query.get_pipeline_names()
    return APIResponse(
        status="success",
        code=200,
        data={
            "pipelines": pipeline_names,
            "total_pipelines": len(pipeline_names),
        },
        message="Pipeline names retrieved successfully",
    )


def return_pipeline_id(request: PipelineNameRequest, query: CmfQuery) -> APIResponse:
    pipeline_id = query.get_pipeline_id(request.pipeline_name)
    if pipeline_id == -1:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="Pipeline not found",
            errors=[
                ErrorDetail(
                    field="pipeline_name",
                    message=f"Pipeline '{request.pipeline_name}' not found",
                )
            ],
        )

    return APIResponse(
        status="success",
        code=200,
        data={
            "pipeline_name": request.pipeline_name,
            "pipeline_id": pipeline_id,
        },
        message="Pipeline ID retrieved successfully",
    )


def list_pipeline_stages(request: PipelineNameRequest, query: CmfQuery) -> APIResponse:
    stages = query.get_pipeline_stages(request.pipeline_name)
    if stages == []:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="Pipeline not found",
            errors=[
                ErrorDetail(
                    field="pipeline_name",
                    message=f"Pipeline '{request.pipeline_name}' not found",
                )
            ],
        )

    return APIResponse(
        status="success",
        code=200,
        data={
            "pipeline_name": request.pipeline_name,
            "stages": stages,
            "total_stages": len(stages),
        },
        message="Pipeline stages retrieved successfully",
    )


def get_pipeline_executions(request: PipelineNameRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_all_executions_in_pipeline(request.pipeline_name)
    execution_records = [] if executions.empty else _dataframe_records(executions)
    return APIResponse(
        status="success",
        code=200,
        data={
            "pipeline_name": request.pipeline_name,
            "executions": execution_records,
            "total_executions": len(execution_records),
        },
        message="Pipeline executions retrieved successfully",
    )


def get_pipeline_json(request: PipelineJsonRequest, query: CmfQuery) -> APIResponse:
    if query.get_pipeline_id(request.pipeline_name) == -1:
        return APIResponse(
            status="error",
            code=404,
            data=None,
            message="Pipeline not found",
            errors=[
                ErrorDetail(
                    field="pipeline_name",
                    message=f"Pipeline '{request.pipeline_name}' not found",
                )
            ],
        )

    pipeline_json = query.dumptojson(request.pipeline_name, request.exec_uuid)
    return APIResponse(
        status="success",
        code=200,
        data=json.loads(pipeline_json) if pipeline_json else {"Pipeline": []},
        message="Pipeline JSON retrieved successfully",
    )


def extract_pipelines_to_json(request: LastSyncTimeRequest, query: CmfQuery) -> APIResponse:
    pipeline_json = query.extract_to_json(request.last_sync_time)
    return APIResponse(
        status="success",
        code=200,
        data=json.loads(pipeline_json),
        message="Pipelines JSON extracted successfully",
    )

# ==================== API Endpoints For CMfQuery ====================
 
@router.get("/stages/", response_model=APIResponse)
async def cmfquery_get_pipeline_stages(
    request: PipelineNameRequest = Depends(),
):
    return list_pipeline_stages(request, query)


@router.get("", response_model=APIResponse)
async def cmfquery_list_pipelines():
    return list_pipeline_names(query)


@router.get("/id/", response_model=APIResponse)
async def cmfquery_get_pipeline_id(
    request: PipelineNameRequest = Depends(),
):
    return return_pipeline_id(request, query)


@router.get("/executions/", response_model=APIResponse)
async def cmfquery_get_pipeline_executions(
    request: PipelineNameRequest = Depends(),
):
    return get_pipeline_executions(request, query)


@router.get("/dumptojson", response_model=APIResponse)
async def cmfquery_dump_pipeline_to_json(
    request: PipelineJsonRequest = Depends(),
):
    return get_pipeline_json(request, query)


@router.get("/extract_to_json", response_model=APIResponse)
async def cmfquery_extract_pipelines_to_json(
    request: LastSyncTimeRequest = Depends(),
):
    return extract_pipelines_to_json(request, query)
