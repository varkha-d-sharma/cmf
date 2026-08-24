"""
Execution API endpoints and business logic.

This module contains execution-related API endpoints and their business logic,
including execution listing and Python environment management.
"""

import os

from fastapi import APIRouter, Request, HTTPException, UploadFile, File

from server.app.schemas.responses import success_response
from server.app.main import (
    query,
    dict_of_exe_ids,
)

from server.app.get_data import (
    async_api,
    executions_list,
)

from server.app.api.v1.metadata import (
    check_mlmd_file_exists,
    check_pipeline_exists,
)

router = APIRouter(prefix="/v1", tags=["executions"])


# ==================== Business Logic Functions ====================

async def list_of_executions(request: Request, pipeline_name: str):
    """Get list of executions for a pipeline."""
    await check_mlmd_file_exists()
    await check_pipeline_exists(pipeline_name)

    response = await async_api(
        executions_list,
        query,
        pipeline_name,
        dict_of_exe_ids,
    )

    return response


async def upload_python_env(request: Request, file: UploadFile):
    """Upload Python environment file."""
    try:
        if file.filename is None:
            raise HTTPException(status_code=400,detail="No file uploaded",)

        file_path = os.path.join("/cmf-server/data/env/",os.path.basename(file.filename),)

        os.makedirs(os.path.dirname(file_path),exist_ok=True,)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        return {
            "message": f"File '{file.filename}' uploaded successfully"
        }

    except HTTPException:
        raise

    except OSError as e:
        raise HTTPException(
            status_code=500,detail=f"Failed to upload file: {str(e)}",) from e

    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Failed to upload file: {str(e)}",) from e


async def get_python_env(file_name: str) -> str:
    """Retrieve Python environment file content."""
    if not (
        file_name.endswith(".txt")
        or file_name.endswith(".yaml")
    ):
        raise HTTPException(status_code=400,detail="Unsupported file extension. Use .txt or .yaml",)

    file_path = os.path.join( "/cmf-server/data/env/", os.path.basename(file_name),)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404,detail="File not found")

    try:
        with open(file_path, "r") as file:
            content = file.read()
        return content

    except OSError as e:
        raise HTTPException(status_code=500,detail=f"Error reading file: {str(e)}",) from e


# ==================== API Endpoints ====================

@router.post("/executions/python-env")
async def upload_python_environment(request: Request,file: UploadFile = File(...),):
    result = await upload_python_env(request, file)

    return success_response(
        data=result,
        message="Python environment uploaded successfully",
        code=201,
    )


@router.get("/executions/python-env")
async def get_python_environment(request: Request,file_name: str,):
    result = await get_python_env(file_name)

    return success_response(
        data=result,
        message="Python environment retrieved successfully",
        code=200,
    )


@router.get("/executions/{pipeline_name}")
async def get_executions_endpoint(request: Request,pipeline_name: str,):
    result = await list_of_executions(
        request,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Executions retrieved successfully",
        code=200,
    )


@router.get("/metadata/list-of-executions/{pipeline_name}")
async def get_metadata_list_of_executions(request: Request,pipeline_name: str,):
    result = await list_of_executions(
        request,
        pipeline_name,
    )

    return success_response(
        data=result,
        message="Executions retrieved successfully",
        code=200,
    )