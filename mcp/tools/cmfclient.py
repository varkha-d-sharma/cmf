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
         """
        Retrieve currently registered pipelines.

        :return: API response containing registered pipelines."""
         return self.connection.get("/v1/pipelines")

    # Executions
    def get_executions_list(self, pipeline_name):
        """
        Retrieve a brief list of execution names for a pipeline.

        :param pipeline_name: Name of the pipeline.
        :return: API response containing execution names.
        """
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

    def get_execution_lineage_tangled_tree(self, pipeline_name, uuid):
        """
        Retrieve the execution lineage tangled tree for a given UUID and pipeline.

        :param uuid: Unique identifier for the execution.
        :param pipeline_name: Name of the pipeline.
        :return: API response containing the execution lineage tangled tree.
        """
        return self.connection.get(f"/v1/pipelines/{pipeline_name}/executions/{uuid}/lineage")

    # Artifacts
    def get_artifact_types(self):
        """
        Retrieve a list of artifact types.

        :return: API response containing artifact types.
        """
        return self.connection.get("/v1/artifacts/artifact-types")

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
        """
        Retrieve artifacts of a specific type for a given pipeline.

        :param pipeline_name: Name of the pipeline.
        :param artifact_type: Type of the artifact.
        :return: API response containing artifacts of the specified type.
        """
        return self.get_artifacts_by_stage(
            pipeline_name=pipeline_name,
            stage_name="",
            artifact_type=artifact_type,
        )

    def get_artifact_lineage_tangled_tree(self, pipeline_name):
        """
        Retrieve the artifact lineage for a given pipeline.

        :param pipeline_name: Name of the pipeline.
        :return: API response containing the artifact lineage tangled tree.
        """
        return self.connection.get(f"/v1/pipelines/{pipeline_name}/artifacts/lineage")

    def get_model_card(self, model_id):
        """
        Retrieve the model card information.

        :param model_id: Unique identifier for the model (as int).
        :return: API response containing the model card details.
        """
        model_id_int = int(model_id)
        return self.connection.get("/v1/artifacts/model-card", params={"modelId": model_id_int})

    def get_python_env(self, file_name):
        """
        Retrieve the Python environment details.

        :return: API response containing the Python environment details.
        """
        return self.connection.get("/v1/executions/python-env", params={"file_name": file_name})


    # MLMD metadata sync
    def mlmd_push(self, pipeline_name, json_payload, exec_uuid=None):
        """
        Push metadata to the MLMD server.

        :param payload: The data to be pushed (as a dictionary).
        :return: API response after pushing the metadata.
        """
        payload = {
            "pipeline_name": pipeline_name,
            "json_payload": json_payload,
            "exec_uuid": exec_uuid,
        }
        return self.connection.post("/v1/mlmd/push", data=payload)

    def mlmd_pull(self, pipeline_name=None, exec_uuid=None, last_sync_time=None):
        """
        Retrieve metadata for a specific pipeline.

        :param pipeline_name: Name of the pipeline.
        :return: API response containing the metadata.
        """
        payload = {
            "pipeline_name": pipeline_name,
            "exec_uuid": exec_uuid,
            "last_sync_time": last_sync_time,
        }
        return self.connection.post("/v1/mlmd/pull", data=payload)

    def close_session(self):
        """Close the session with the CMF server."""
        self.connection.exit()
