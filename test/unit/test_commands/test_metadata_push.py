###
# Copyright (2025) Hewlett Packard Enterprise Development LP
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
Layer 1: Core Command Unit Tests for Metadata Push

These tests focus on the CmdMetadataPush command class logic in isolation.
All external dependencies (file system, network, database) are mocked.

Test Coverage:
- Success path with valid pipeline and metadata file
- Error handling for missing files
- Error handling for missing/invalid execution UUID
- Error handling for missing pipeline
- Server response codes (200, 400, 422, 500)
- Optional parameter handling (execution_uuid, tensorboard_path)
- Python environment file upload logic
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

from cmflib.commands.metadata.push import CmdMetadataPush
from cmflib.cmf_exception_handling import (
    FileNotFound,
    PipelineNotFound,
    ExecutionUUIDNotFound,
    MissingArgument,
    DuplicateArgumentNotAllowed,
    UpdateCmfVersion,
    CmfServerNotAvailable,
    InternalServerError
)


class TestCmdMetadataPush:
    """Test suite for CmdMetadataPush command"""

    # ============================================================================
    # SUCCESS PATH TESTS
    # ============================================================================

    @patch('cmflib.commands.metadata.push.server_interface.call_mlmd_push')
    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_success_without_execution_uuid(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_server_call,
        mock_args_metadata_push,
        mock_live_spinner,
        mock_server_response_success
    ):
        """
        Test successful metadata push without execution UUID.
        
        Expected behavior:
        - File existence is checked
        - Pipeline name is validated
        - Metadata is converted to JSON
        - Server API is called with correct parameters
        - Success response is returned
        """
        # Arrange
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        # Mock CmfQuery instance
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{"name": "test-pipeline", "stages": []}]
        })
        mock_query_instance.get_all_executions_in_pipeline.return_value = Mock(empty=True)
        mock_cmfquery.return_value = mock_query_instance
        
        mock_server_call.return_value = mock_server_response_success
        
        # Create command instance
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert
        mock_exists.assert_called_once()
        mock_query_instance.get_pipeline_names.assert_called_once()
        mock_query_instance.dumptojson.assert_called_once_with("test-pipeline", None)
        mock_server_call.assert_called_once_with(
            mock_query_instance.dumptojson.return_value,
            "http://test-server:80",
            None,
            "test-pipeline"
        )
        assert result is not None


    @patch('cmflib.commands.metadata.push.server_interface.call_mlmd_push')
    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_success_with_execution_uuid(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_server_call,
        mock_args_metadata_push,
        mock_live_spinner,
        mock_server_response_success,
        sample_execution_uuid
    ):
        """
        Test successful metadata push with specific execution UUID.
        
        Expected behavior:
        - Execution UUID is validated against MLMD data
        - Only matching execution is pushed
        - Server receives execution-specific payload
        """
        # Arrange
        mock_args_metadata_push.execution_uuid = [sample_execution_uuid]
        
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        # Mock CmfQuery with execution data
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{
                "name": "test-pipeline",
                "stages": [{
                    "executions": [{
                        "properties": {
                            "Execution_uuid": sample_execution_uuid
                        }
                    }]
                }]
            }]
        })
        mock_cmfquery.return_value = mock_query_instance
        
        mock_server_call.return_value = mock_server_response_success
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert
        mock_server_call.assert_called_once()
        call_args = mock_server_call.call_args
        assert call_args[0][2] == sample_execution_uuid  # exec_uuid parameter


    @patch('cmflib.commands.metadata.push.server_interface.call_mlmd_push')
    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_with_multiple_execution_uuids_in_mlmd(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_server_call,
        mock_args_metadata_push,
        mock_live_spinner,
        mock_server_response_success
    ):
        """
        Test metadata push when MLMD contains comma-separated execution UUIDs.
        
        This tests the scenario where a single execution has multiple UUIDs.
        """
        # Arrange
        target_uuid = "uuid-2"
        mock_args_metadata_push.execution_uuid = [target_uuid]
        
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{
                "name": "test-pipeline",
                "stages": [{
                    "executions": [{
                        "properties": {
                            # Multiple UUIDs comma-separated
                            "Execution_uuid": "uuid-1,uuid-2,uuid-3"
                        }
                    }]
                }]
            }]
        })
        mock_cmfquery.return_value = mock_query_instance
        
        mock_server_call.return_value = mock_server_response_success
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert - should successfully find uuid-2 in the comma-separated list
        mock_server_call.assert_called_once()


    # ============================================================================
    # ERROR PATH TESTS - FILE OPERATIONS
    # ============================================================================

    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_file_not_found(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test error handling when MLMD file doesn't exist.
        
        Expected behavior:
        - FileNotFound exception is raised
        - No server calls are made
        """
        # Arrange
        mock_exists.return_value = False
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(FileNotFound) as exc_info:
            cmd.run(mock_live_spinner)
        
        assert "mlmd" in str(exc_info.value).lower()


    @patch('os.path.exists')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    def test_metadata_push_custom_file_path_not_found(
        self,
        mock_fetch_config,
        mock_exists,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test error handling when custom MLMD file path doesn't exist.
        """
        # Arrange
        mock_args_metadata_push.file_name = ["/custom/path/to/mlmd"]
        mock_exists.return_value = False
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(FileNotFound):
            cmd.run(mock_live_spinner)


    # ============================================================================
    # ERROR PATH TESTS - VALIDATION
    # ============================================================================

    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_pipeline_not_found(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test error when pipeline name doesn't exist in MLMD.
        
        Expected behavior:
        - No server call is made
        - Error is handled gracefully
        """
        # Arrange
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["different-pipeline"]
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert - when pipeline not found, nothing is pushed
        assert mock_query_instance.dumptojson.call_count == 0


    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_execution_uuid_not_found(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test error when specified execution UUID doesn't exist in MLMD.
        """
        # Arrange
        mock_args_metadata_push.execution_uuid = ["non-existent-uuid"]
        
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{
                "name": "test-pipeline",
                "stages": [{
                    "executions": [{
                        "properties": {
                            "Execution_uuid": "different-uuid"
                        }
                    }]
                }]
            }]
        })
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(ExecutionUUIDNotFound):
            cmd.run(mock_live_spinner)


    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    def test_metadata_push_missing_argument_empty_string(
        self,
        mock_fetch_config,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test error when required argument is empty string.
        """
        # Arrange
        mock_args_metadata_push.pipeline_name = [""]  # Empty string
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(MissingArgument):
            cmd.run(mock_live_spinner)


    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    def test_metadata_push_duplicate_argument_not_allowed(
        self,
        mock_fetch_config,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test error when duplicate arguments are provided.
        """
        # Arrange
        mock_args_metadata_push.pipeline_name = ["pipeline1", "pipeline2"]  # Duplicate
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(DuplicateArgumentNotAllowed):
            cmd.run(mock_live_spinner)


    # ============================================================================
    # ERROR PATH TESTS - SERVER RESPONSES
    # ============================================================================

    @patch('cmflib.commands.metadata.push.server_interface.call_mlmd_push')
    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_server_version_update_required(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_server_call,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test handling of 422 response (version update required).
        """
        # Arrange
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{"name": "test-pipeline", "stages": []}]
        })
        mock_cmfquery.return_value = mock_query_instance
        
        # Mock 422 response
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"status": "version_update"}
        mock_server_call.return_value = mock_response
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(UpdateCmfVersion):
            cmd.run(mock_live_spinner)


    @patch('cmflib.commands.metadata.push.server_interface.call_mlmd_push')
    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_server_unavailable(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_server_call,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test handling of 400 response (server unavailable).
        """
        # Arrange
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{"name": "test-pipeline", "stages": []}]
        })
        mock_cmfquery.return_value = mock_query_instance
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_server_call.return_value = mock_response
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(CmfServerNotAvailable):
            cmd.run(mock_live_spinner)


    @patch('cmflib.commands.metadata.push.server_interface.call_mlmd_push')
    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_internal_server_error(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_server_call,
        mock_args_metadata_push,
        mock_live_spinner
    ):
        """
        Test handling of 500 response (internal server error).
        """
        # Arrange
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{"name": "test-pipeline", "stages": []}]
        })
        mock_cmfquery.return_value = mock_query_instance
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_server_call.return_value = mock_response
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act & Assert
        with pytest.raises(InternalServerError):
            cmd.run(mock_live_spinner)


    # ============================================================================
    # OPTIONAL PARAMETERS TESTS
    # ============================================================================

    @patch('cmflib.commands.metadata.push.server_interface.call_mlmd_push')
    @patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
    @patch('cmflib.commands.metadata.push.CmfConfig.read_config')
    @patch('cmflib.commands.metadata.push.fetch_cmf_config_path')
    @patch('os.path.exists')
    def test_metadata_push_with_tensorboard_path(
        self,
        mock_exists,
        mock_fetch_config,
        mock_read_config,
        mock_cmfquery,
        mock_server_call,
        mock_args_metadata_push,
        mock_live_spinner,
        mock_server_response_success
    ):
        """
        Test metadata push with tensorboard path specified.
        
        Note: This tests that the command accepts the parameter.
        Actual tensorboard upload logic would need additional mocking.
        """
        # Arrange
        mock_args_metadata_push.tensorboard_path = ["/path/to/tensorboard/logs"]
        
        mock_exists.return_value = True
        mock_fetch_config.return_value = ("success", "/path/to/.cmfconfig")
        mock_read_config.return_value = {"cmf-server-url": "http://test-server:80"}
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.dumptojson.return_value = json.dumps({
            "Pipeline": [{"name": "test-pipeline", "stages": []}]
        })
        mock_query_instance.get_all_executions_in_pipeline.return_value = Mock(empty=True)
        mock_cmfquery.return_value = mock_query_instance
        
        mock_server_call.return_value = mock_server_response_success
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert - command should complete successfully
        assert result is not None


    # ============================================================================
    # HELPER METHOD TESTS
    # ============================================================================

    def test_search_files_method_finds_existing_file(self, temp_dir, mock_args_metadata_push):
        """
        Test the search_files helper method finds files correctly.
        """
        # Arrange
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.search_files(["test.txt"], str(temp_dir))
        
        # Assert
        assert "test.txt" in result
        assert result["test.txt"] == str(test_file)


    def test_search_files_method_file_not_found(self, temp_dir, mock_args_metadata_push):
        """
        Test search_files returns empty dict when file not found.
        """
        # Arrange
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.search_files(["nonexistent.txt"], str(temp_dir))
        
        # Assert
        assert result == {}


    def test_search_files_multiple_directories(self, temp_dir, mock_args_metadata_push):
        """
        Test search_files searches across multiple directories.
        """
        # Arrange
        dir1 = temp_dir / "dir1"
        dir2 = temp_dir / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        file1 = dir1 / "file1.txt"
        file2 = dir2 / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        
        cmd = CmdMetadataPush(mock_args_metadata_push)
        
        # Act
        result = cmd.search_files(
            ["file1.txt", "file2.txt"],
            str(dir1),
            str(dir2)
        )
        
        # Assert
        assert len(result) == 2
        assert "file1.txt" in result
        assert "file2.txt" in result
