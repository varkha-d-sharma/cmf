from cmflib.cmfquery import CmfQuery
from fastapi import APIRouter, Depends
from server.app.api.dependencies import get_cmf_query
from server.app.schemas.cmf_query_schema import ErrorDetail, StandardResponse

router = APIRouter()

def list_all_artifacts(query: CmfQuery) -> StandardResponse:
    artifact_names = query.get_all_artifacts()
    if artifact_names == []:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="No artifacts found",
            errors=[
                ErrorDetail(
                    field="artifacts",
                    message="No artifacts found in the system",
                )
            ],
        )

    return StandardResponse(
        status="success",
        code=200,
        data={
            "artifacts": artifact_names,
            "total_artifacts": len(artifact_names),
        },
        message="Artifacts retrieved successfully",
    )


def list_all_artifact_types(query: CmfQuery) -> StandardResponse:
    artifact_types = query.get_all_artifact_types()
    if artifact_types == []:
        return StandardResponse(
            status="error",
            code=404,
            data=None,
            message="No artifact types found",
            errors=[
                ErrorDetail(
                    field="artifact_types",
                    message="No artifact types found in the system",
                )
            ],
        )
        
    return StandardResponse(
        status="success",
        code=200,
        data={
            "artifact_types": artifact_types,
            "total_artifact_types": len(artifact_types),
        },
        message="Artifacts retrieved successfully",
    )


@router.get("", response_model=StandardResponse)
def cmfquery_list_artifacts(query: CmfQuery = Depends(get_cmf_query)):
    return list_all_artifacts(query)


@router.get("/types", response_model=StandardResponse)
def cmfquery_list_artifact_types(query: CmfQuery = Depends(get_cmf_query)):
    return list_all_artifact_types(query)


