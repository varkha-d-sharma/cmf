import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from server.app.schemas.responses import success_response
from fastapi.responses import StreamingResponse
import zipfile
import io
import os
from typing import Optional

router = APIRouter(prefix="/v1", tags=["environment"])

# ==================== API Endpoints ====================

@router.post("/python-env")
async def upload_python_environment(file: UploadFile = File(..., description="The Python environment file to upload")):
    result = await upload_python_env(file)

    return success_response(
        data=result,
        message="Python environment uploaded successfully",
        code=201
    )


@router.get("/python-env")
async def get_python_environment(file_name: str):
    result = await get_python_env(file_name)

    return success_response(
        data=result,
        message="Python environment retrieved successfully",
        code=200
    )


@router.get("/python-env/download")
async def download_python_env_route(list_of_files: Optional[list[str]] = Query(None)):
    """Download Python environment files as ZIP."""
    return download_python_env(list_of_files)


# ==================== Business Logic Functions ====================

# API endpoint for uploading Python environment files.
async def upload_python_env(file: UploadFile):
    """Upload Python environment file."""
    try:
        if file.filename is None:
            raise HTTPException(status_code=400, detail="No file uploaded")

        file_path = os.path.join("/cmf-server/data/env/", os.path.basename(file.filename))

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        return {
            "message": f"File '{file.filename}' uploaded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}") from e


# Rest api to fetch the env data from the /cmf-server/data/env folder
async def get_python_env(file_name: str) -> str:
    """
    API endpoint to fetch the content of a requirements file.

    Args:
        file_name (str): The name of the file to be fetched. Must end with .txt or .yaml.

    Returns:
        str: The content of the file as plain text.

    Raises:
        HTTPException: If the file does not exist or the extension is unsupported.
    """
    # Validate file extension
    if not (file_name.endswith(".txt") or file_name.endswith(".yaml")):
        raise HTTPException(status_code=400, detail="Unsupported file extension. Use .txt or .yaml")
    # Check if the file exists
    file_path = os.path.join("/cmf-server/data/env/", os.path.basename(file_name))

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
     # Read and return the file content as plain text
    try:
        with open(file_path, "r") as file:
            content = file.read()
        return content

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


def download_python_env(list_of_files: Optional[list[str]] = None):
    """
    API endpoint to compress and download the entire folder as a ZIP file.
    """
    try:
        DIRECTORY = "/cmf-server/data/env/" # Directory to be compressed
        #  Check if the directory exists
        if not os.path.exists(DIRECTORY):
            return {"error": "Directory does not exist"}
        # Determine files to include in the ZIP
        files_to_zip = []
        # if list_of_files is provided, include only those files
        # else include all files in the directory
        if list_of_files:
            for file_name in list_of_files:
                file_path = os.path.join(DIRECTORY, file_name)
                if os.path.exists(file_path):
                    files_to_zip.append((file_path, file_name))
                else:
                    return {"error": f"File {file_name} does not exist"}
        else:
            if not os.listdir(DIRECTORY):
                return {"error": "Directory is empty"}
            for root, _, files in os.walk(DIRECTORY):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, DIRECTORY)
                    files_to_zip.append((file_path, arcname))

        # Create and send the ZIP file 
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer,"w",zipfile.ZIP_DEFLATED,) as zip_file:
            for file_path, arcname in files_to_zip:
                zip_file.write(file_path, arcname)

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={'python_env_files.zip' if list_of_files else 'python_env_folder.zip'}"
            }
        )
    except Exception as e:
        return {"error": str(e)}
