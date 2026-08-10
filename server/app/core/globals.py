"""
Global variables and initialization for CMF server.

This module contains all shared global state that is used across
multiple API routers and business logic modules.
"""

import os
from collections import defaultdict
from cmflib.cmfquery import CmfQuery
from server.app.utils import extract_hostname, get_fqdn


# Initialize CMF Query instance for server
query = CmfQuery(is_server=True)

# Cache for artifact and execution IDs
dict_of_art_ids = {}
dict_of_exe_ids = {}

# Lock management for concurrent pipeline operations
pipeline_locks = {}
lock_counts: defaultdict[str, int] = defaultdict(int)

# Local address detection for server registration validation
REACT_APP_CMF_API_URL = os.getenv("REACT_APP_CMF_API_URL", "http://localhost:8080")

LOCAL_ADDRESSES = set()
LOCAL_ADDRESSES.update(["127.0.0.1", "localhost"])
hostname = extract_hostname(REACT_APP_CMF_API_URL)
LOCAL_ADDRESSES.add(hostname)
# Adding hostname if IP is given
LOCAL_ADDRESSES.add(get_fqdn(hostname))
print("Local addresses= ", LOCAL_ADDRESSES)
