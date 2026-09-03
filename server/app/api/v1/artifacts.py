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
Artifact API endpoints and business logic.

This module contains artifact-related API endpoints and their business logic,
including artifact types.
"""
from fastapi import APIRouter, Depends, Request
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import MlmdState
from server.app.get_data import (
    get_artifact_types,
    async_api,
)

router = APIRouter(prefix="/v1", tags=["artifacts"])

# ==================== API Endpoints ====================

# only This API is used by the MCP server.
@router.get("/artifacts/types")
async def get_artifacts_by_types(
    request: Request,
):
    """
    Retrieve available artifact types.
    """
    state = request.app.state.mlmd
    result = await get_artifacts_types(state)

    return success_response(
        data=result,
        message="Artifact types retrieved successfully",
        code=200
    )


# ==================== Business Logic Functions ====================

# This API returns a list of artifact types in the current MLMD store.
async def get_artifacts_types(state: MlmdState):
    """Get list of artifact types."""
    await state.check_mlmd_file_exists()

    artifact_types_list = await async_api(
        get_artifact_types,
        state.query
    )

    if "Environment" in artifact_types_list:
        artifact_types_list.remove("Environment")

    return artifact_types_list