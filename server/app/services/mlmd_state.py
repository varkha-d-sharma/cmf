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
from build.lib.cmflib.cmfquery import CmfQuery
from server.app.get_data import (async_api, get_all_artifact_ids, get_all_exe_ids)
from server.app.utils import extract_hostname, get_fqdn

# API Configuration
REACT_APP_CMF_API_URL = os.getenv("REACT_APP_CMF_API_URL", "http://localhost:8080")

class MlmdState:
    """Container for server-level MLMD state stored on the FastAPI app."""

    def __init__(self):
        self.query = CmfQuery(is_server=True)
        self.dict_of_art_ids = {}
        self.dict_of_exe_ids = {}
        self.pipeline_locks = {}
        self.lock_counts: defaultdict[str, int] = defaultdict(int)

        self.LOCAL_ADDRESSES = {"127.0.0.1", "localhost"}
        hostname = extract_hostname(REACT_APP_CMF_API_URL)
        self.LOCAL_ADDRESSES.add(hostname)
        self.LOCAL_ADDRESSES.add(get_fqdn(hostname))

    async def update_global_art_dict(self, pipeline_name):
        """Update artifact IDs dictionary for a pipeline."""
        output_dict = await async_api(get_all_artifact_ids, self.query, self.dict_of_art_ids, pipeline_name)
        self.dict_of_art_ids[pipeline_name] = output_dict[pipeline_name]
        return

    async def update_global_exe_dict(self, pipeline_name):
        """Update execution IDs dictionary for a pipeline."""
        output_dict = await async_api(get_all_exe_ids, self.query, pipeline_name)
        self.dict_of_exe_ids[pipeline_name] = output_dict[pipeline_name]
        return


mlmd_state = MlmdState()

# Backward-compatible module-level aliases for legacy imports.
query = mlmd_state.query
dict_of_art_ids = mlmd_state.dict_of_art_ids
dict_of_exe_ids = mlmd_state.dict_of_exe_ids
pipeline_locks = mlmd_state.pipeline_locks
lock_counts = mlmd_state.lock_counts
LOCAL_ADDRESSES = mlmd_state.LOCAL_ADDRESSES


async def update_global_art_dict(pipeline_name):
    """Update global artifact IDs dictionary for a pipeline."""
    return await mlmd_state.update_global_art_dict(pipeline_name)


async def update_global_exe_dict(pipeline_name):
    """Update global execution IDs dictionary for a pipeline."""
    return await mlmd_state.update_global_exe_dict(pipeline_name)
