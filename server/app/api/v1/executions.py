from cmflib.cmfquery import CmfQuery
from fastapi import APIRouter, Depends
from server.app.api.dependencies import get_cmf_query
from server.app.schemas.cmf_query_schema import (
    ArtifactIdRequest,
    ArtifactNameRequest,
    ErrorDetail,
    ExecutionIdsRequest,
    ExecutionIdsWithPipelineRequest,
    ParentExecutionIdRequest,
    ParentExecutionIdsRequest,
    StageIdRequest,
    StageNameRequest,
    StandardResponse,
)

router = APIRouter()

def _mlmd_properties_to_dict(properties) -> dict:
    output = {}
    for key, value in properties.items():
        if value.HasField("string_value"):
            output[key] = value.string_value
        elif value.HasField("int_value"):
            output[key] = value.int_value
        elif value.HasField("double_value"):
            output[key] = value.double_value
        elif value.HasField("bool_value"):
            output[key] = value.bool_value
        else:
            output[key] = None
    return output


def _execution_to_dict(execution) -> dict:
    return {
        "id": execution.id,
        "type_id": execution.type_id,
        "name": execution.name,
        "external_id": execution.external_id,
        "create_time_since_epoch": execution.create_time_since_epoch,
        "last_update_time_since_epoch": execution.last_update_time_since_epoch,
        "properties": _mlmd_properties_to_dict(execution.properties),
        "custom_properties": _mlmd_properties_to_dict(execution.custom_properties),
    }


def _dataframe_records(dataframe) -> list[dict]:
    return dataframe.where(dataframe.notna(), None).to_dict(orient="records")


def _dataframe_response(dataframe, data: dict, not_found_field: str, not_found_message: str, success_message: str) -> StandardResponse:
    if dataframe is None or dataframe.empty:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Executions not found",
            errors=[ErrorDetail(field=not_found_field, message=not_found_message)],
        )

    execution_records = _dataframe_records(dataframe)
    data.update(
        {
            "executions": execution_records,
            "total_executions": len(execution_records),
        }
    )
    return StandardResponse(
        status="success",
        code=200,
        data=data,
        message=success_message,
    )


def _execution_list_response(executions, data: dict, not_found_field: str, not_found_message: str, success_message: str) -> StandardResponse:
    if not executions:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Executions not found",
            errors=[ErrorDetail(field=not_found_field, message=not_found_message)],
        )

    execution_records = [
        _execution_to_dict(execution) if hasattr(execution, "id") else execution
        for execution in executions
    ]
    data.update(
        {
            "executions": execution_records,
            "total_executions": len(execution_records),
        }
    )
    return StandardResponse(
        status="success",
        code=200,
        data=data,
        message=success_message,
    )


def list_executions_in_pipeline_stages(request: StageNameRequest, query: CmfQuery) -> StandardResponse:
    # this function will return all executions associated with a given stage name[mlpb.Execution]
    executions = query.get_all_exe_in_stage(request.stage_name)
    if executions == []:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Executions associated with stage not found",
            errors=[
                ErrorDetail(
                    field="stage_name",
                    message=f"Stage '{request.stage_name}' not found",
                )
            ],
        )

    return StandardResponse(
        status="success",
        code=200,
        data={
            "stage_name": request.stage_name,
            "executions": [_execution_to_dict(execution) for execution in executions],
            "total_executions": len(executions),
        },
        message="Executions associated with pipeline stage retrieved successfully",
    )


def get_executions_in_pipeline_stages(request: StageNameRequest, query: CmfQuery) -> StandardResponse:
    # this function will return all executions associated with a given stage name[dataframe]
    executions = query.get_all_executions_in_stage(request.stage_name)
    if executions.empty:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Executions associated with stage not found",
            errors=[
                ErrorDetail(
                    field="stage_name",
                    message=f"Stage '{request.stage_name}' not found",
                )
            ],
        )

    return StandardResponse(
        status="success",
        code=200,
        data={
            "stage_name": request.stage_name,
            "executions": _dataframe_records(executions),
            "total_executions": len(executions),
        },
        message="Executions associated with pipeline stage retrieved successfully",
    )


def get_all_executions_by_ids_list(request: ExecutionIdsRequest, query: CmfQuery) -> StandardResponse:
    executions = query.get_all_executions_by_ids_list(request.exe_ids)
    if executions.empty:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Executions not found",
            errors=[
                ErrorDetail(
                    field="exe_ids",
                    message=f"Executions not found for ids {request.exe_ids}",
                )
            ],
        )

    execution_records = _dataframe_records(executions)
    return StandardResponse(
        status="success",
        code=200,
        data={
            "exe_ids": request.exe_ids,
            "executions": execution_records,
            "total_executions": len(execution_records),
        },
        message="Executions retrieved successfully",
    )


def get_all_executions_for_artifact(request: ArtifactNameRequest, query: CmfQuery) -> StandardResponse:
    executions = query.get_all_executions_for_artifact(request.artifact_name)
    return _dataframe_response(
        executions,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Executions not found for artifact '{request.artifact_name}'",
        "Executions for artifact retrieved successfully",
    )


def get_all_executions_for_artifact_id(request: ArtifactIdRequest, query: CmfQuery) -> StandardResponse:
    executions = query.get_all_executions_for_artifact_id(request.artifact_id)
    return _dataframe_response(
        executions,
        {"artifact_id": request.artifact_id},
        "artifact_id",
        f"Executions not found for artifact id {request.artifact_id}",
        "Executions for artifact retrieved successfully",
    )


def get_one_hop_parent_executions(request: ExecutionIdsWithPipelineRequest, query: CmfQuery) -> StandardResponse:
    executions = query.get_one_hop_parent_executions(request.execution_id, request.pipeline_id)
    return _execution_list_response(
        executions,
        {"execution_id": request.execution_id, "pipeline_id": request.pipeline_id},
        "execution_id",
        f"Parent executions not found for execution ids {request.execution_id}",
        "One-hop parent executions retrieved successfully",
    )


def get_one_hop_parent_execution_ids(request: ParentExecutionIdRequest, query: CmfQuery) -> StandardResponse:
    execution_ids = query.get_one_hop_parent_execution_ids(request.execution_id, request.pipeline_id)
    if not execution_ids:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Parent execution ids not found",
            errors=[
                ErrorDetail(
                    field="execution_id",
                    message=f"Parent execution ids not found for execution id {request.execution_id}",
                )
            ],
        )

    return StandardResponse(
        status="success",
        code=200,
        data={
            "execution_id": request.execution_id,
            "pipeline_id": request.pipeline_id,
            "parent_execution_ids": execution_ids,
            "total_parent_execution_ids": len(execution_ids),
        },
        message="One-hop parent execution ids retrieved successfully",
    )


def get_all_parent_executions_by_id(request: ParentExecutionIdsRequest, query: CmfQuery) -> StandardResponse:
    parent_executions = query.get_all_parent_executions_by_id(request.execution_id, request.pipeline_id)
    parent_details = parent_executions[0] if parent_executions else []
    parent_links = parent_executions[1] if len(parent_executions) > 1 else []
    if not parent_details and not parent_links:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Parent executions not found",
            errors=[
                ErrorDetail(
                    field="execution_id",
                    message=f"Parent executions not found for execution ids {request.execution_id}",
                )
            ],
        )

    return StandardResponse(
        status="success",
        code=200,
        data={
            "execution_id": request.execution_id,
            "pipeline_id": request.pipeline_id,
            "parent_executions": parent_details,
            "links": parent_links,
            "total_parent_executions": len(parent_details),
        },
        message="All parent executions retrieved successfully",
    )


def get_all_parent_executions(request: ArtifactNameRequest, query: CmfQuery) -> StandardResponse:
    executions = query.get_all_parent_executions(request.artifact_name)
    return _dataframe_response(
        executions,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Parent executions not found for artifact '{request.artifact_name}'",
        "All parent executions retrieved successfully",
    )


def get_executions_with_execution_ids(request: ExecutionIdsRequest, query: CmfQuery) -> StandardResponse:
    executions = query.get_executions_with_execution_ids(request.exe_ids)
    return _dataframe_response(
        executions,
        {"exe_ids": request.exe_ids},
        "exe_ids",
        f"Executions not found for ids {request.exe_ids}",
        "Execution summary retrieved successfully",
    )


def get_all_executions_by_stage(request: StageIdRequest, query: CmfQuery) -> StandardResponse:
    executions = query.get_all_executions_by_stage(request.stage_id, request.execution_uuid)
    return _execution_list_response(
        executions,
        {"stage_id": request.stage_id, "execution_uuid": request.execution_uuid},
        "stage_id",
        f"Executions not found for stage id {request.stage_id}",
        "Executions for stage retrieved successfully",
    )


def find_producer_execution(request: ArtifactNameRequest, query: CmfQuery) -> StandardResponse:
    execution = query.find_producer_execution(request.artifact_name)
    if execution is None:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="Producer execution not found",
            errors=[
                ErrorDetail(
                    field="artifact_name",
                    message=f"Producer execution not found for artifact '{request.artifact_name}'",
                )
            ],
        )

    return StandardResponse(
        status="success",
        code=200,
        data={
            "artifact_name": request.artifact_name,
            "execution": _execution_to_dict(execution),
        },
        message="Producer execution retrieved successfully",
    )


@router.get("/get_executions_in_pipeline_stages", response_model=StandardResponse)
def cmfquery_get_executions_in_pipeline_stages(
    request: StageNameRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_executions_in_pipeline_stages(request, query)


@router.get("/list_executions_in_pipeline_stages", response_model=StandardResponse)
def cmfquery_list_executions_in_pipeline_stages(
    request: StageNameRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return list_executions_in_pipeline_stages(request, query)


@router.post("/get_all_executions_by_ids_list", response_model=StandardResponse)
def cmfquery_get_all_executions_by_ids_list(
    request: ExecutionIdsRequest,
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_all_executions_by_ids_list(request, query)


@router.get("/get_all_executions_for_artifact", response_model=StandardResponse)
def cmfquery_get_all_executions_for_artifact(
    request: ArtifactNameRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_all_executions_for_artifact(request, query)


@router.get("/get_all_executions_for_artifact_id", response_model=StandardResponse)
def cmfquery_get_all_executions_for_artifact_id(
    request: ArtifactIdRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_all_executions_for_artifact_id(request, query)


@router.post("/get_one_hop_parent_executions", response_model=StandardResponse)
def cmfquery_get_one_hop_parent_executions(
    request: ExecutionIdsWithPipelineRequest,
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_one_hop_parent_executions(request, query)


@router.get("/get_one_hop_parent_execution_ids", response_model=StandardResponse)
def cmfquery_get_one_hop_parent_execution_ids(
    request: ParentExecutionIdRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_one_hop_parent_execution_ids(request, query)


@router.post("/get_all_parent_executions_by_id", response_model=StandardResponse)
def cmfquery_get_all_parent_executions_by_id(
    request: ParentExecutionIdsRequest,
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_all_parent_executions_by_id(request, query)


@router.get("/get_all_parent_executions", response_model=StandardResponse)
def cmfquery_get_all_parent_executions(
    request: ArtifactNameRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_all_parent_executions(request, query)


@router.post("/get_executions_with_execution_ids", response_model=StandardResponse)
def cmfquery_get_executions_with_execution_ids(
    request: ExecutionIdsRequest,
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_executions_with_execution_ids(request, query)


@router.get("/get_all_executions_by_stage", response_model=StandardResponse)
def cmfquery_get_all_executions_by_stage(
    request: StageIdRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return get_all_executions_by_stage(request, query)


@router.get("/find_producer_execution", response_model=StandardResponse)
def cmfquery_find_producer_execution(
    request: ArtifactNameRequest = Depends(),
    query: CmfQuery = Depends(get_cmf_query),
):
    return find_producer_execution(request, query)
