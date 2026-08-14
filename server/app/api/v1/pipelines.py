from cmflib.cmfquery import CmfQuery
from fastapi import APIRouter, Depends
from server.app.api.dependencies import get_cmf_query
from server.app.schemas.cmf_query_schema import ErrorDetail, PipelineNameRequest, StandardResponse

router = APIRouter()

def _dataframe_records(dataframe):
    return dataframe.where(dataframe.notna(), None).to_dict(orient="records")

def list_pipeline_names(query: CmfQuery) -> StandardResponse:
    pipeline_names = query.get_pipeline_names()
    return StandardResponse(
        status="success",
        code=200,
        data={
            "pipelines": pipeline_names,
            "total_pipelines": len(pipeline_names),
        },
        message="Pipeline names retrieved successfully",
    )

def return_pipeline_id(request: PipelineNameRequest, query: CmfQuery) -> StandardResponse:
    pipeline_id = query.get_pipeline_id(request.pipeline_name)
    if pipeline_id == -1:
        return StandardResponse(
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

    return StandardResponse(
        status="success",
        code=200,
        data={
            "pipeline_name": request.pipeline_name,
            "pipeline_id": pipeline_id,
        },
        message="Pipeline ID retrieved successfully",
    )

def list_pipeline_stages(request: PipelineNameRequest, query: CmfQuery) -> StandardResponse:
    stages = query.get_pipeline_stages(request.pipeline_name)
    if stages == []:
        return StandardResponse(
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

    return StandardResponse(
        status="success",
        code=200,
        data={
            "pipeline_name": request.pipeline_name,
            "stages": stages,
            "total_stages": len(stages),
        },
        message="Pipeline stages retrieved successfully",
    )


@router.get("/stages/", response_model=StandardResponse)
async def cmfquery_get_pipeline_stages(
    request: PipelineNameRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return list_pipeline_stages(request, query)


@router.get("", response_model=StandardResponse)
async def cmfquery_list_pipelines(query: CmfQuery = Depends(get_cmf_query)):
    return list_pipeline_names(query)

@router.get("/id/", response_model=StandardResponse)
async def cmfquery_get_pipeline_id(
    request: PipelineNameRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return return_pipeline_id(request, query)



# def get_pipeline_executions(request: PipelineNameRequest, query: CmfQuery) -> StandardResponse:
#     if query.get_pipeline_id(request.pipeline_name) == -1:
#         return StandardResponse(
#             status="error",
#             code=404,
#             data=None,
#             message="Pipeline not found",
#             errors=[
#                 ErrorDetail(
#                     field="pipeline_name",
#                     message=f"Pipeline '{request.pipeline_name}' not found",
#                 )
#             ],
#         )

#     executions = query.get_all_executions_in_pipeline(request.pipeline_name)
#     if executions.empty:
#         execution_records = []
#     else:
#         execution_records = _dataframe_records(executions)

#     return StandardResponse(
#         status="success",
#         code=200,
#         data={
#             "pipeline_name": request.pipeline_name,
#             "executions": execution_records,
#             "total_executions": len(execution_records),
#         },
#         message="Pipeline executions retrieved successfully",
#     )

