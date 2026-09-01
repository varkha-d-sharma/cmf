from cmflib.cmfquery import CmfQuery
from fastapi import APIRouter, Depends
from server.app.services.mlmd_state import mlmd_state
from server.app.schemas.responses import (
    ArtifactIdRequest,
    ArtifactNameRequest,
    ErrorDetail,
    ExecutionIdsRequest,
    ExecutionIdsWithPipelineRequest,
    ParentExecutionIdRequest,
    ParentExecutionIdsRequest,
    StageIdRequest,
    StageNameRequest,
    APIResponse,
)

router = APIRouter(prefix="/v1", tags=["executions"])
query = mlmd_state.query

# ==================== Business Logic Functions For CMFQuery ====================

def _mlmd_properties_to_dict(properties) -> dict:
    output = {}
    for key, value in properties.items():
        output[key] = _mlmd_value_to_python(value)
    return output


def _mlmd_value_to_python(value):
    if hasattr(value, "HasField"):
        if value.HasField("string_value"):
            return value.string_value
        if value.HasField("int_value"):
            return value.int_value
        if value.HasField("double_value"):
            return value.double_value
        if value.HasField("bool_value"):
            return value.bool_value
    return None


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
    records = dataframe.where(dataframe.notna(), None).to_dict(orient="records")
    return [
        {
            key: _mlmd_value_to_python(value) if hasattr(value, "HasField") else value
            for key, value in record.items()
        }
        for record in records
    ]


def _dataframe_response(dataframe, data: dict, not_found_field: str, not_found_message: str, success_message: str) -> APIResponse:
    if dataframe is None or dataframe.empty:
        return APIResponse(
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
    return APIResponse(
        status="success",
        code=200,
        data=data,
        message=success_message,
    )


def _execution_list_response(executions, data: dict, not_found_field: str, not_found_message: str, success_message: str) -> APIResponse:
    if not executions:
        return APIResponse(
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
    return APIResponse(
        status="success",
        code=200,
        data=data,
        message=success_message,
    )


def list_executions_in_pipeline_stages(request: StageNameRequest, query: CmfQuery) -> APIResponse:
    # this function will return all executions associated with a given stage name[mlpb.Execution]
    executions = query.get_all_exe_in_stage(request.stage_name)
    if executions == []:
        return APIResponse(
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

    return APIResponse(
        status="success",
        code=200,
        data={
            "stage_name": request.stage_name,
            "executions": [_execution_to_dict(execution) for execution in executions],
            "total_executions": len(executions),
        },
        message="Executions associated with pipeline stage retrieved successfully",
    )


def get_executions_in_pipeline_stages(request: StageNameRequest, query: CmfQuery) -> APIResponse:
    # this function will return all executions associated with a given stage name[dataframe]
    executions = query.get_all_executions_in_stage(request.stage_name)
    if executions.empty:
        return APIResponse(
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

    return APIResponse(
        status="success",
        code=200,
        data={
            "stage_name": request.stage_name,
            "executions": _dataframe_records(executions),
            "total_executions": len(executions),
        },
        message="Executions associated with pipeline stage retrieved successfully",
    )


def get_all_executions_by_ids_list(request: ExecutionIdsRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_all_executions_by_ids_list(request.exe_ids)
    if executions.empty:
        return APIResponse(
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
    return APIResponse(
        status="success",
        code=200,
        data={
            "exe_ids": request.exe_ids,
            "executions": execution_records,
            "total_executions": len(execution_records),
        },
        message="Executions retrieved successfully",
    )


def get_all_executions_for_artifact(request: ArtifactNameRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_all_executions_for_artifact(request.artifact_name)
    return _dataframe_response(
        executions,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Executions not found for artifact '{request.artifact_name}'",
        "Executions for artifact retrieved successfully",
    )


def get_all_executions_for_artifact_id(request: ArtifactIdRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_all_executions_for_artifact_id(request.artifact_id)
    return _dataframe_response(
        executions,
        {"artifact_id": request.artifact_id},
        "artifact_id",
        f"Executions not found for artifact id {request.artifact_id}",
        "Executions for artifact retrieved successfully",
    )


def get_one_hop_parent_executions(request: ExecutionIdsWithPipelineRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_one_hop_parent_executions(request.execution_id, request.pipeline_id)
    return _execution_list_response(
        executions,
        {"execution_id": request.execution_id, "pipeline_id": request.pipeline_id},
        "execution_id",
        f"Parent executions not found for execution ids {request.execution_id}",
        "One-hop parent executions retrieved successfully",
    )


def get_one_hop_parent_execution_ids(request: ParentExecutionIdRequest, query: CmfQuery) -> APIResponse:
    execution_ids = query.get_one_hop_parent_execution_ids(request.execution_id, request.pipeline_id)
    if not execution_ids:
        return APIResponse(
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

    return APIResponse(
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


def get_all_parent_executions_by_id(request: ParentExecutionIdsRequest, query: CmfQuery) -> APIResponse:
    parent_executions = query.get_all_parent_executions_by_id(request.execution_id, request.pipeline_id)
    parent_details = parent_executions[0] if parent_executions else []
    parent_links = parent_executions[1] if len(parent_executions) > 1 else []
    if not parent_details and not parent_links:
        return APIResponse(
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

    return APIResponse(
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


def get_all_parent_executions(request: ArtifactNameRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_all_parent_executions(request.artifact_name)
    return _dataframe_response(
        executions,
        {"artifact_name": request.artifact_name},
        "artifact_name",
        f"Parent executions not found for artifact '{request.artifact_name}'",
        "All parent executions retrieved successfully",
    )


def get_executions_with_execution_ids(request: ExecutionIdsRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_executions_with_execution_ids(request.exe_ids)
    return _dataframe_response(
        executions,
        {"exe_ids": request.exe_ids},
        "exe_ids",
        f"Executions not found for ids {request.exe_ids}",
        "Execution summary retrieved successfully",
    )


def get_all_executions_by_stage(request: StageIdRequest, query: CmfQuery) -> APIResponse:
    executions = query.get_all_executions_by_stage(request.stage_id, request.execution_uuid)
    return _execution_list_response(
        executions,
        {"stage_id": request.stage_id, "execution_uuid": request.execution_uuid},
        "stage_id",
        f"Executions not found for stage id {request.stage_id}",
        "Executions for stage retrieved successfully",
    )


def find_producer_execution(request: ArtifactNameRequest, query: CmfQuery) -> APIResponse:
    execution = query.find_producer_execution(request.artifact_name)
    if execution is None:
        return APIResponse(
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

    return APIResponse(
        status="success",
        code=200,
        data={
            "artifact_name": request.artifact_name,
            "execution": _execution_to_dict(execution),
        },
        message="Producer execution retrieved successfully",
    )

# ==================== API Endpoints For CMfQuery ====================
 
@router.get("/get_executions_in_pipeline_stages", response_model=APIResponse)
def cmfquery_get_executions_in_pipeline_stages(
    request: StageNameRequest = Depends(),
):
    return get_executions_in_pipeline_stages(request, query)


@router.get("/list_executions_in_pipeline_stages", response_model=APIResponse)
def cmfquery_list_executions_in_pipeline_stages(
    request: StageNameRequest = Depends(),
):
    return list_executions_in_pipeline_stages(request, query)


@router.post("/get_all_executions_by_ids_list", response_model=APIResponse)
def cmfquery_get_all_executions_by_ids_list(
    request: ExecutionIdsRequest,
):
    return get_all_executions_by_ids_list(request, query)


@router.get("/get_all_executions_for_artifact", response_model=APIResponse)
def cmfquery_get_all_executions_for_artifact(
    request: ArtifactNameRequest = Depends(),
):
    return get_all_executions_for_artifact(request, query)


@router.get("/get_all_executions_for_artifact_id", response_model=APIResponse)
def cmfquery_get_all_executions_for_artifact_id(
    request: ArtifactIdRequest = Depends(),
):
    return get_all_executions_for_artifact_id(request, query)


@router.post("/get_one_hop_parent_executions", response_model=APIResponse)
def cmfquery_get_one_hop_parent_executions(
    request: ExecutionIdsWithPipelineRequest,
):
    return get_one_hop_parent_executions(request, query)


@router.get("/get_one_hop_parent_execution_ids", response_model=APIResponse)
def cmfquery_get_one_hop_parent_execution_ids(
    request: ParentExecutionIdRequest = Depends(),
):
    return get_one_hop_parent_execution_ids(request, query)


@router.post("/get_all_parent_executions_by_id", response_model=APIResponse)
def cmfquery_get_all_parent_executions_by_id(
    request: ParentExecutionIdsRequest,
):
    return get_all_parent_executions_by_id(request, query)


@router.get("/get_all_parent_executions", response_model=APIResponse)
def cmfquery_get_all_parent_executions(
    request: ArtifactNameRequest = Depends(),
):
    return get_all_parent_executions(request, query)


@router.post("/get_executions_with_execution_ids", response_model=APIResponse)
def cmfquery_get_executions_with_execution_ids(
    request: ExecutionIdsRequest,
):
    return get_executions_with_execution_ids(request, query)


@router.get("/get_all_executions_by_stage", response_model=APIResponse)
def cmfquery_get_all_executions_by_stage(
    request: StageIdRequest = Depends(),
):
    return get_all_executions_by_stage(request, query)


@router.get("/find_producer_execution", response_model=APIResponse)
def cmfquery_find_producer_execution(
    request: ArtifactNameRequest = Depends(),
):
    return find_producer_execution(request, query)
