"""
Lineage API endpoints and business logic.

This module contains lineage-related API endpoints and their business logic,
including execution lineage, artifact lineage, and artifact-execution lineage.
"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Request

from server.app.schemas.responses import success_response
from server.app.main import (
    query,
    dict_of_art_ids,
    dict_of_exe_ids,
)

from server.app.get_data import async_api

from server.app.query_execution_lineage_d3tree import (
    query_execution_lineage_d3tree,
)

from server.app.query_artifact_lineage_d3tree import (
    query_artifact_lineage_d3tree,
)

from server.app.query_visualization_artifact_execution import (
    query_visualization_artifact_execution,
)

from server.app.api.v1.metadata import (
    check_mlmd_file_exists,
    check_pipeline_exists,
)

router = APIRouter(prefix="/v1", tags=["lineage"])


# ==================== Business Logic Functions ====================

async def execution_lineage(
    request: Request,
    uuid: str,
    pipeline_name: str,
):
    """Get execution lineage for D3 tree visualization."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_execution_lineage_d3tree,
        query,
        pipeline_name,
        dict_of_exe_ids,
        uuid,
    )

    return response


async def artifact_lineage_tangled(
    request: Request,
    pipeline_name: str,
) -> Optional[List[List[Dict[str, Any]]]]:
    """Get artifact lineage for tangled tree visualization."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_artifact_lineage_d3tree,
        query,
        pipeline_name,
        dict_of_art_ids,
    )

    return response


async def artifact_execution_lineage(
    request: Request,
    pipeline_name: str,
):
    """Get artifact-execution lineage visualization."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_visualization_artifact_execution,
        query,
        pipeline_name,
        dict_of_art_ids,
        dict_of_exe_ids,
    )

    return response


# ==================== API Endpoints ====================

@router.get("/lineage/execution/{uuid}/{pipeline_name}")
async def normalized_execution_lineage(
    request: Request,
    uuid: str,
    pipeline_name: str,
):
    result = await execution_lineage(
        request,
        uuid,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Execution lineage retrieved successfully",
        code=200,
    )


@router.get("/metadata/execution-lineage/{uuid}/{pipeline_name}")
async def metadata_execution_lineage(
    request: Request,
    uuid: str,
    pipeline_name: str,
):
    result = await execution_lineage(
        request,
        uuid,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Execution lineage retrieved successfully",
        code=200,
    )


@router.get("/lineage/artifact/{pipeline_name}")
async def normalized_artifact_lineage(
    request: Request,
    pipeline_name: str,
):
    result = await artifact_lineage_tangled(
        request,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Artifact lineage retrieved successfully",
        code=200,
    )


@router.get("/metadata/artifact-lineage/{pipeline_name}")
async def metadata_artifact_lineage(
    request: Request,
    pipeline_name: str,
):
    result = await artifact_lineage_tangled(
        request,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Artifact lineage retrieved successfully",
        code=200,
    )


@router.get("/lineage/artifact-execution/{pipeline_name}")
async def normalized_artifact_execution_lineage(
    request: Request,
    pipeline_name: str,
):
    result = await artifact_execution_lineage(
        request,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Artifact-execution lineage retrieved successfully",
        code=200,
    )


@router.get("/metadata/artifact-execution-lineage/{pipeline_name}")
async def metadata_artifact_execution_lineage(
    request: Request,
    pipeline_name: str,
):
    result = await artifact_execution_lineage(
        request,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Artifact-execution lineage retrieved successfully",
        code=200,
    )