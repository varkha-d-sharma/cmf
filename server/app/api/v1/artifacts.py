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
from fastapi import APIRouter, HTTPException, Request
from server.app.schemas.responses import success_response
from server.app.services.mlmd_state import MlmdState
from server.app.get_data import (
    get_artifact_types,
    async_api,
    get_model_data
)
import json
from cmflib.cmfquery import CmfQuery

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


@router.get("/artifacts/models/{model_id}/card")
async def get_model_artifact_card(request: Request, model_id: int):
    """Retrieve model card data for a model artifact."""
    state = request.app.state.mlmd
    result = await get_model_card_by_artifact_id(state, model_id)
    return success_response(
        data=result,
        message="Model card retrieved successfully",
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


async def get_model_card_by_artifact_id(state: MlmdState, model_id: int):
    """Get model card details for a model artifact id."""
    await state.check_mlmd_file_exists()

    model_artifact = await async_api(
        CmfQuery.get_all_artifacts_by_ids_list,
        state.query,
        [model_id]
    )
    if model_artifact.empty:
        raise HTTPException(status_code=404, detail=f"Model artifact with id {model_id} not found")

    artifact_type = model_artifact["type"].tolist()[0]
    if artifact_type != "Model":
        raise HTTPException(status_code=400, detail=f"Artifact id {model_id} is not a Model artifact")

    model_data_df, model_exe_df, model_input_art_df, model_output_art_df = await async_api(
        get_model_data,
        state.query,
        model_id
    )
    return [
        json.loads(model_data_df.to_json(orient="records")) if not model_data_df.empty else "",
        json.loads(model_exe_df.to_json(orient="records")) if not model_exe_df.empty else "",
        json.loads(model_input_art_df.to_json(orient="records")) if not model_input_art_df.empty else "",
        json.loads(model_output_art_df.to_json(orient="records")) if not model_output_art_df.empty else "",
    ]