###
# Copyright (2023) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

"""
CMF API Client module.

High-level client wrapper for communicating with CMF Server REST API.
Provides domain-specific methods for pipelines, executions, artifacts, metadata,
servers, schedules, and Python environment management.

Originally from the cmfAPI package (https://github.com/atripathy86/cmfapi).
Inlined here to remove the external dependency.
"""

from .conn import cmfConnection


class cmfClient:
    def __init__(self, base_url, tls_verify=None):
        """
        Initialize the CMF API client wrapper.

        :param base_url: CMF Server base URL
        :param tls_verify: TLS certificate verification (True/False/path to CA bundle, default from env)
        """
        self.connection = cmfConnection(base_url, tls_verify=tls_verify)

    # Pipelines
    def get_pipelines(self):
        """Retrieve all registered pipelines."""
        return self.connection.get("/v1/pipelines")

    def get_pipeline_stages(self, pipeline_name):
        """Retrieve unique execution stages for a pipeline."""
        return self.connection.get(f"/v1/pipelines/{pipeline_name}/stages")

    # Executions
    def get_executions(self, pipeline_name):
        """Retrieve execution list for a pipeline."""
        return self.connection.get(f"/v1/pipelines/{pipeline_name}/executions")

    def get_executions_by_stage(
        self,
        pipeline_name,
        stage_name,
        active_page=1,
        record_per_page=5,
        sort_order="DESC",
        filter_value="",
    ):
        """Retrieve executions filtered by pipeline and stage."""
        payload = {
            "pipeline_name": pipeline_name,
            "stage_name": stage_name,
            "active_page": active_page,
            "record_per_page": record_per_page,
            "sort_order": sort_order,
            "filter_value": filter_value,
        }
        return self.connection.post(f"/v1/pipelines/{pipeline_name}/executions", data=payload)

    def get_execution_lineage(self, pipeline_name, uuid):
        """Retrieve execution lineage for a given execution UUID."""
        return self.connection.get(f"/v1/pipelines/{pipeline_name}/executions/{uuid}/lineage")

    # Artifacts
    def get_artifact_types(self):
        """Retrieve all available artifact types."""
        return self.connection.get("/v1/metadata/artifact-types")

    def get_artifact_types_by_stage(self, pipeline_name, stage_name):
        """Retrieve artifact types for a given pipeline and stage."""
        payload = {"pipeline_name": pipeline_name, "stage_name": stage_name}
        return self.connection.post(f"/v1/pipelines/{pipeline_name}/artifacts/types", data=payload)

    def get_artifacts_by_stage(
        self,
        pipeline_name,
        stage_name,
        artifact_type,
        active_page=1,
        record_per_page=5,
        sort_field="name",
        sort_order="asc",
        filter_value="",
    ):
        """Retrieve artifacts filtered by pipeline, stage, and artifact type."""
        payload = {
            "pipeline_name": pipeline_name,
            "stage_name": stage_name,
            "artifact_type": artifact_type,
            "active_page": active_page,
            "record_per_page": record_per_page,
            "sort_field": sort_field,
            "sort_order": sort_order,
            "filter_value": filter_value,
        }
        return self.connection.post(f"/v1/pipelines/{pipeline_name}/artifacts", data=payload)

    def get_artifacts(self, pipeline_name, artifact_type):
        """Backward-compatible alias for artifact fetch by type."""
        return self.get_artifacts_by_stage(
            pipeline_name=pipeline_name,
            stage_name="",
            artifact_type=artifact_type,
        )

    def get_artifact_lineage(self, pipeline_name):
        """Retrieve artifact lineage for a pipeline."""
        return self.connection.get(f"/v1/pipelines/{pipeline_name}/artifacts/lineage")

    def get_artifact_execution_lineage(self, pipeline_name):
        """Retrieve artifact-to-execution lineage for a pipeline."""
        return self.connection.get(f"/v1/pipelines/{pipeline_name}/artifact-executions/lineage")

    def get_model_card(self, model_id):
        """Retrieve model card information for a given model id."""
        model_id_int = int(model_id)
        return self.connection.get("/v1/artifacts/model-card", params={"modelId": model_id_int})

    # Python environment
    def upload_python_env(self, file_path, filename=None):
        """Upload a Python environment file to the server."""
        import os

        file_name = filename or os.path.basename(file_path)
        with open(file_path, "rb") as file_handle:
            files = {"file": (file_name, file_handle, "application/octet-stream")}
            return self.connection.post("/v1/executions/python-env", files=files)

    def get_python_env(self, file_name):
        """Retrieve the content of a stored Python environment file."""
        return self.connection.get("/v1/executions/python-env", params={"file_name": file_name})

    def download_python_env(self, list_of_files=None):
        """Download a zip of Python environment files or the entire environment folder."""
        params = None if list_of_files is None else {"list_of_files": list_of_files}
        return self.connection.get("/v1/python-envs/download", params=params, is_binary=True)

    # MLMD metadata sync
    def mlmd_push(self, pipeline_name, json_payload, exec_uuid=None):
        """Push MLMD payload to the server for a pipeline."""
        payload = {
            "pipeline_name": pipeline_name,
            "json_payload": json_payload,
            "exec_uuid": exec_uuid,
        }
        return self.connection.post("/v1/mlmd/push", data=payload)

    def mlmd_pull(self, pipeline_name=None, exec_uuid=None, last_sync_time=None):
        """Pull MLMD data from the server, optionally filtered by pipeline and UUID."""
        payload = {
            "pipeline_name": pipeline_name,
            "exec_uuid": exec_uuid,
            "last_sync_time": last_sync_time,
        }
        return self.connection.post("/v1/mlmd/pull", data=payload)


    # Server registration and sync
    def register_server(self, server_name, server_url, last_sync_time=None):
        """Register a remote server."""
        payload = {
            "server_name": server_name,
            "server_url": server_url,
            "last_sync_time": last_sync_time,
        }
        return self.connection.post("/v1/servers/register", data=payload)

    def sync_server(self, server_name, server_url, last_sync_time=None):
        """Trigger metadata sync with a registered server."""
        payload = {
            "server_name": server_name,
            "server_url": server_url,
            "last_sync_time": last_sync_time,
        }
        return self.connection.post("/v1/servers/sync", data=payload)

    def list_servers(self):
        """List registered servers."""
        return self.connection.get("/v1/servers")

    # Schedule management
    def create_schedule(
        self,
        server_id,
        timezone="UTC",
        start_time_local_iso=None,
        one_time=False,
        recurrence_mode=None,
        interval_unit=None,
        interval_value=None,
        daily_time=None,
        weekly_day=None,
        weekly_time=None,
    ):
        """Create a sync schedule."""
        payload = {
            "server_id": server_id,
            "timezone": timezone,
            "start_time_local_iso": start_time_local_iso,
            "one_time": one_time,
            "recurrence_mode": recurrence_mode,
            "interval_unit": interval_unit,
            "interval_value": interval_value,
            "daily_time": daily_time,
            "weekly_day": weekly_day,
            "weekly_time": weekly_time,
        }
        return self.connection.post("/v1/schedules", data=payload)

    def list_schedules(self, server_id=None):
        """List schedules, optionally filtered by server_id."""
        params = None if server_id is None else {"server_id": server_id}
        return self.connection.get("/v1/schedules", params=params)

    def get_schedule_logs(self, schedule_id):
        """Get run logs for a schedule."""
        return self.connection.get(f"/v1/schedules/{schedule_id}/logs")

    def get_server_completed_logs(self, server_id):
        """Get completed logs for a server."""
        return self.connection.get(f"/v1/servers/{server_id}/completed-logs")

    def delete_schedule(self, schedule_id):
        """Delete or deactivate a schedule."""
        return self.connection.delete(f"/v1/schedules/{schedule_id}")

    def close_session(self):
        """Close the session with the CMF server."""
        self.connection.exit()
