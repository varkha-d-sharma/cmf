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

# ==================== Global Variables ====================
# Initialize CMF Query instance for server
query = CmfQuery(is_server=True)

# Cache for artifact and execution IDs
dict_of_art_ids = {}
dict_of_exe_ids = {}

# Lock management for concurrent pipeline operations
pipeline_locks = {}
lock_counts: defaultdict[str, int] = defaultdict(int)

# API Configuration
REACT_APP_CMF_API_URL = os.getenv("REACT_APP_CMF_API_URL", "http://localhost:8080")

# Local address detection for server registration validation
LOCAL_ADDRESSES = set()
LOCAL_ADDRESSES.update(["127.0.0.1", "localhost"])
hostname = extract_hostname(REACT_APP_CMF_API_URL)
LOCAL_ADDRESSES.add(hostname)
# Adding hostname if IP is given
LOCAL_ADDRESSES.add(get_fqdn(hostname))
print("Local addresses= ", LOCAL_ADDRESSES)

# ==================== Global Helper Functions ====================

async def update_global_art_dict(pipeline_name):
    """Update global artifact IDs dictionary for a pipeline."""
    output_dict = await async_api(get_all_artifact_ids, query, dict_of_art_ids, pipeline_name)
    dict_of_art_ids[pipeline_name] = output_dict[pipeline_name]
    return


async def update_global_exe_dict(pipeline_name):
    """Update global execution IDs dictionary for a pipeline."""
    output_dict = await async_api(get_all_exe_ids, query, pipeline_name)
    dict_of_exe_ids[pipeline_name] = output_dict[pipeline_name]
    return
