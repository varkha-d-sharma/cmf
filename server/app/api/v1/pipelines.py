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

Pipeline API endpoints and business logic.

This module contains all pipeline-related API endpoints and their business logic,
including pipeline listing and stage queries.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.dbconfig import get_db
from server.app.db.dbqueries import (
    fetch_unique_execution_stages,
)
from server.app.schemas.responses import success_response
from server.app.main import query

router = APIRouter(prefix="/v1", tags=["pipelines"])


# ==================== Business Logic Functions ====================

async def pipelines(request: Request):
    """Get list of all pipelines."""
    if query:
        pipeline_names = query.get_pipeline_names()
        return pipeline_names
    else:
        print("No mlmd file submitted.")
        pipeline_names = []
        return pipeline_names


async def get_pipeline_stages(
    pipeline_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve unique pipeline stages (Context_Type values) for a given pipeline.
    
    Args:
        pipeline_name: Name of the pipeline to get stages from
        
    Returns:
        Dictionary with pipeline_name, list of unique stages, and total count
        
    Example response:
    {
        "stages": ["Test-env/Prepare", "Test-env/Train", "Test-env/Evaluate"],
        "total_stages": 3
    }
    """
    result = await fetch_unique_execution_stages(db, pipeline_name)
    return result


@router.get("/pipelines")
async def list_pipelines(request: Request):
    result = await pipelines(request)
    return success_response(
        data=result,
        message="Pipelines retrieved successfully",
        code=200,
    )


@router.get("/pipelines/{pipeline_name}/stages")
async def pipeline_stages(request: Request, pipeline_name: str, db: AsyncSession = Depends(get_db)):
    result = await get_pipeline_stages(pipeline_name, db)
    return success_response(
        data=result,
        message="Pipeline stages retrieved successfully",
        code=200,
    )
