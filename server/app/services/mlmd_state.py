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

MLMD state management for pipelines.

This module contains functions to manage and cache MLMD state for pipelines,
including artifact and execution IDs.
"""

from collections import defaultdict
import os
from cmflib.cmfquery import CmfQuery
from fastapi import HTTPException
from server.app.get_data import (async_api, get_all_artifact_ids, get_all_exe_ids)
from server.app.utils import extract_hostname, get_fqdn

class MlmdState:
    """Container for server-level MLMD state stored on the FastAPI app."""

    def __init__(self):
        self.query = CmfQuery(is_server=True)
        self.dict_of_art_ids = {}
        self.dict_of_exe_ids = {}
        self.pipeline_locks = {}
        self.lock_counts: defaultdict[str, int] = defaultdict(int)

        self.LOCAL_ADDRESSES = {"127.0.0.1", "localhost"}
        react_app_cmf_api_url = os.getenv("REACT_APP_CMF_API_URL", "http://localhost:8080")
        hostname = extract_hostname(react_app_cmf_api_url)
        self.LOCAL_ADDRESSES.add(hostname)
        self.LOCAL_ADDRESSES.add(get_fqdn(hostname))

    async def update_global_art_dict(self, pipeline_name):
        """Update artifact IDs dictionary for a pipeline."""
        output_dict = await async_api(get_all_artifact_ids, self.query, self.dict_of_exe_ids, pipeline_name)
        if pipeline_name is None:
            self.dict_of_art_ids = output_dict
        else:
            self.dict_of_art_ids[pipeline_name] = output_dict[pipeline_name]
        return

    async def update_global_exe_dict(self, pipeline_name):
        """Update execution IDs dictionary for a pipeline."""
        output_dict = await async_api(get_all_exe_ids, self.query, pipeline_name)
        if pipeline_name is None:
            self.dict_of_exe_ids = output_dict
        else:
            self.dict_of_exe_ids[pipeline_name] = output_dict[pipeline_name]
        return

    async def check_mlmd_file_exists(self):
        """Raise 404 when the server MLMD database is unavailable."""
        if not self.query:
            print("DB doesn't exist.")
            raise HTTPException(status_code=404, detail="Database doesn't exist.")

    async def check_pipeline_exists(self, pipeline_name):
        """Raise 404 when the requested pipeline is unavailable."""
        if pipeline_name not in self.query.get_pipeline_names():
            print(f"Pipeline {pipeline_name} not found.")
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_name} not found.")

    def _mlmd_properties_to_dict(self, properties) -> dict:
        output = {}
        for key, value in properties.items():
            output[key] = self._mlmd_value_to_python(value)
        return output

    def _mlmd_value_to_python(self, value):
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

    def _execution_to_dict(self, execution) -> dict:
        return {
            "id": execution.id,
            "type_id": execution.type_id,
            "name": execution.name,
            "external_id": execution.external_id,
            "create_time_since_epoch": execution.create_time_since_epoch,
            "last_update_time_since_epoch": execution.last_update_time_since_epoch,
            "properties": self._mlmd_properties_to_dict(execution.properties),
            "custom_properties": self._mlmd_properties_to_dict(execution.custom_properties),
        }

    def _dataframe_records(self, dataframe) -> list[dict]:
        records = dataframe.where(dataframe.notna(), None).to_dict(orient="records")
        return [
            {
                key: self._mlmd_value_to_python(value) if hasattr(value, "HasField") else value
                for key, value in record.items()
            }
            for record in records
        ]


mlmd_state = MlmdState()