from cmflib.cmfquery import CmfQuery
from server.app.schemas.cmf_query_schema import ErrorDetail, StageNameRequest, StandardResponse


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
            "executions": [ _execution_to_dict(row) for _, row in executions.iterrows()],
            "total_executions": len(executions),
        },
        message="Executions associated with pipeline stage retrieved successfully",
    )
