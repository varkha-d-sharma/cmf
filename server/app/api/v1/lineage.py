"""
Copyright (2023) Hewlett Packard Enterprise Development LP

Licensed under the Apache License, Version 2.0 (the "License");
You may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Lineage API endpoints and business logic.

This module contains lineage-related API endpoints and their business logic,
including execution lineage, artifact lineage, and artifact-execution lineage.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import mlmd_state
from server.app.get_data import async_api
from server.app.query_execution_lineage_d3tree import (query_execution_lineage_d3tree,)
from server.app.query_artifact_lineage_d3tree import (query_artifact_lineage_d3tree,)
from server.app.query_visualization_artifact_execution import (query_visualization_artifact_execution,)
from server.app.services.mlmd_state import mlmd_state

router = APIRouter(prefix="/v1", tags=["lineage"])


# ==================== Business Logic Functions ====================

async def execution_lineage(
    request: Request,
    uuid: str,
    pipeline_name: str,
):
    """Get execution lineage for D3 tree visualization."""
    state = request.app.state.mlmd
    await state.check_mlmd_file_exists()
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_execution_lineage_d3tree,
        state.query,
        pipeline_name,
        state.dict_of_exe_ids,
        uuid,
    )

    return response


async def artifact_lineage_tangled(
    request: Request,
    pipeline_name: str,
) -> Optional[List[List[Dict[str, Any]]]]:
    """Get artifact lineage for tangled tree visualization."""
    state = request.app.state.mlmd
    await state.check_mlmd_file_exists()
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_artifact_lineage_d3tree,
        state.query,
        pipeline_name,
        state.dict_of_art_ids,
    )

    return response


async def artifact_execution_lineage(
    request: Request,
    pipeline_name: str,
):
    """Get artifact-execution lineage visualization."""
    state = request.app.state.mlmd
    await state.check_mlmd_file_exists()
    await state.check_pipeline_exists(pipeline_name)

    response = await async_api(
        query_visualization_artifact_execution,
        state.query,
        pipeline_name,
        state.dict_of_art_ids,
        state.dict_of_exe_ids,
    )

    return response


# ==================== API Endpoints ====================

@router.get("/pipelines/{pipeline_name}/executions/{uuid}/lineage")
async def get_execution_lineage(
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


@router.get("/pipelines/{pipeline_name}/artifacts/lineage")
async def get_artifact_lineage(
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


@router.get("/pipelines/{pipeline_name}/artifact-executions/lineage")
async def get_artifact_execution_lineage(
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