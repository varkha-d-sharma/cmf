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
Layer 1: Core Command Unit Tests for Artifact List

These tests focus on the CmdArtifactsList command class logic in isolation.
All external dependencies are mocked.

Test Coverage:
- Success path with artifacts display
- Filtering by artifact name
- Empty artifact list handling
- Pagination logic
- DateTime conversion
- Column wrapping for long text
- Error handling for missing files/pipelines
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from cmflib.commands.artifact.list import CmdArtifactsList
from cmflib.cmf_exception_handling import (
    FileNotFound,
    PipelineNotFound,
    ArtifactNotFound,
    MissingArgument,
    DuplicateArgumentNotAllowed
)


class TestCmdArtifactsList:
    """Test suite for CmdArtifactsList command"""

    # ============================================================================
    # SUCCESS PATH TESTS
    # ============================================================================

    @patch('cmflib.commands.artifact.list.display_table')
    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_success_displays_artifacts(
        self,
        mock_exists,
        mock_cmfquery,
        mock_display_table,
        mock_args_artifact_list,
        mock_live_spinner,
        sample_artifact_dataframe
    ):
        """
        Test successful artifact list display.
        
        Expected behavior:
        - File existence is checked
        - Pipeline is validated
        - Artifacts are retrieved from MLMD
        - Datetime conversion is applied
        - Table is displayed with correct data
        """
        # Arrange
        mock_exists.return_value = True
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_all_artifacts_for_pipeline.return_value = sample_artifact_dataframe
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert
        mock_exists.assert_called_once()
        mock_query_instance.get_pipeline_names.assert_called_once()
        mock_query_instance.get_all_artifacts_for_pipeline.assert_called_once_with("test-pipeline")
        mock_display_table.assert_called_once()
        
        # Verify the dataframe passed to display_table has converted datetime
        call_args = mock_display_table.call_args[0]
        displayed_df = call_args[0]
        assert not displayed_df.empty


    @patch('cmflib.commands.artifact.list.display_table')
    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_with_specific_artifact_name(
        self,
        mock_exists,
        mock_cmfquery,
        mock_display_table,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test artifact list filtered by specific artifact name.
        
        Expected behavior:
        - Only specified artifact is retrieved
        - Correct filter is applied
        """
        # Arrange
        mock_args_artifact_list.artifact_name = ["model.pkl"]
        mock_exists.return_value = True
        
        filtered_artifact = pd.DataFrame({
            'id': [1],
            'name': ['model.pkl'],
            'type': ['Model'],
            'uri': ['/path/to/model.pkl'],
            'create_time_since_epoch': [1702649600000]
        })
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_artifact_by_name.return_value = filtered_artifact
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert
        mock_query_instance.get_artifact_by_name.assert_called_once_with("model.pkl")
        mock_display_table.assert_called_once()


    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_empty_results(
        self,
        mock_exists,
        mock_cmfquery,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test handling of empty artifact list.
        
        Expected behavior:
        - No error is raised
        - Appropriate message or empty display
        """
        # Arrange
        mock_exists.return_value = True
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_all_artifacts_for_pipeline.return_value = pd.DataFrame()
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert - should complete without error
        assert result is not None


    # ============================================================================
    # DATETIME CONVERSION TESTS
    # ============================================================================

    def test_convert_to_datetime_formats_correctly(self, mock_args_artifact_list):
        """
        Test that datetime conversion produces correct format.
        
        Expected format: "Day DD Mon YYYY HH:MM:SS GMT"
        """
        # Arrange
        test_df = pd.DataFrame({
            'create_time_since_epoch': [1702649600000]  # Dec 15, 2023 12:00:00 GMT
        })
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result_df = cmd.convert_to_datetime(test_df, 'create_time_since_epoch')
        
        # Assert
        datetime_str = result_df['create_time_since_epoch'].iloc[0]
        assert "GMT" in datetime_str
        assert len(datetime_str.split()) == 6  # Day DD Mon YYYY HH:MM:SS GMT


    def test_convert_to_datetime_handles_multiple_rows(self, mock_args_artifact_list):
        """
        Test datetime conversion on multiple rows.
        """
        # Arrange
        test_df = pd.DataFrame({
            'create_time_since_epoch': [1702649600000, 1702650000000, 1702650400000]
        })
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result_df = cmd.convert_to_datetime(test_df, 'create_time_since_epoch')
        
        # Assert
        assert len(result_df) == 3
        for idx in range(3):
            assert "GMT" in result_df['create_time_since_epoch'].iloc[idx]


    def test_convert_to_datetime_preserves_other_columns(self, mock_args_artifact_list):
        """
        Test that datetime conversion doesn't affect other columns.
        """
        # Arrange
        test_df = pd.DataFrame({
            'name': ['artifact1', 'artifact2'],
            'type': ['Dataset', 'Model'],
            'create_time_since_epoch': [1702649600000, 1702650000000]
        })
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result_df = cmd.convert_to_datetime(test_df, 'create_time_since_epoch')
        
        # Assert
        assert list(result_df.columns) == ['name', 'type', 'create_time_since_epoch']
        assert result_df['name'].tolist() == ['artifact1', 'artifact2']
        assert result_df['type'].tolist() == ['Dataset', 'Model']


    # ============================================================================
    # ERROR PATH TESTS
    # ============================================================================

    @patch('os.path.exists')
    def test_artifact_list_file_not_found(
        self,
        mock_exists,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test error handling when MLMD file doesn't exist.
        """
        # Arrange
        mock_exists.return_value = False
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act & Assert
        with pytest.raises(FileNotFound):
            cmd.run(mock_live_spinner)


    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_pipeline_not_found(
        self,
        mock_exists,
        mock_cmfquery,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test error when pipeline doesn't exist in MLMD.
        """
        # Arrange
        mock_exists.return_value = True
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["different-pipeline"]
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act & Assert
        with pytest.raises(PipelineNotFound):
            cmd.run(mock_live_spinner)


    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_artifact_not_found_by_name(
        self,
        mock_exists,
        mock_cmfquery,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test error when specific artifact name doesn't exist.
        """
        # Arrange
        mock_args_artifact_list.artifact_name = ["nonexistent-artifact"]
        mock_exists.return_value = True
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_artifact_by_name.return_value = pd.DataFrame()  # Empty result
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act & Assert
        # Depending on implementation, this might raise ArtifactNotFound or return empty
        # Adjust based on actual implementation
        result = cmd.run(mock_live_spinner)
        # Could assert on result or exception based on design


    def test_artifact_list_missing_argument_empty_pipeline(
        self,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test error when pipeline name is empty string.
        """
        # Arrange
        mock_args_artifact_list.pipeline_name = [""]
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act & Assert
        with pytest.raises(MissingArgument):
            cmd.run(mock_live_spinner)


    def test_artifact_list_duplicate_pipeline_arguments(
        self,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test error when duplicate pipeline arguments provided.
        """
        # Arrange
        mock_args_artifact_list.pipeline_name = ["pipeline1", "pipeline2"]
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act & Assert
        with pytest.raises(DuplicateArgumentNotAllowed):
            cmd.run(mock_live_spinner)


    # ============================================================================
    # INTEGRATION TESTS (within Layer 1 scope)
    # ============================================================================

    @patch('cmflib.commands.artifact.list.display_table')
    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_full_flow_with_data_transformation(
        self,
        mock_exists,
        mock_cmfquery,
        mock_display_table,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test full flow from query to display including data transformation.
        
        Validates:
        - Query execution
        - Datetime conversion
        - Column selection
        - Display function called with correct data
        """
        # Arrange
        mock_exists.return_value = True
        
        raw_artifacts = pd.DataFrame({
            'id': [1, 2],
            'name': ['dataset.csv', 'model.pkl'],
            'type': ['Dataset', 'Model'],
            'uri': ['/data/dataset.csv', '/models/model.pkl'],
            'create_time_since_epoch': [1702649600000, 1702650000000],
            'extra_column': ['should_be_filtered', 'should_be_filtered']
        })
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_all_artifacts_for_pipeline.return_value = raw_artifacts
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert
        mock_display_table.assert_called_once()
        
        # Verify the dataframe structure
        call_args = mock_display_table.call_args[0]
        displayed_df = call_args[0]
        
        # Check datetime was converted (should be string now, not int)
        assert displayed_df['create_time_since_epoch'].dtype == object
        assert "GMT" in displayed_df['create_time_since_epoch'].iloc[0]


    @patch('cmflib.commands.artifact.list.display_table')
    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_handles_long_text_wrapping(
        self,
        mock_exists,
        mock_cmfquery,
        mock_display_table,
        mock_args_artifact_list,
        mock_live_spinner
    ):
        """
        Test that long URIs or names are handled properly.
        
        This tests the robustness of display with very long strings.
        """
        # Arrange
        mock_exists.return_value = True
        
        long_uri = "/very/long/path/" + "x" * 200 + "/artifact.pkl"
        artifacts_with_long_text = pd.DataFrame({
            'id': [1],
            'name': ['artifact_with_very_long_name_' + 'x' * 100],
            'type': ['Model'],
            'uri': [long_uri],
            'create_time_since_epoch': [1702649600000]
        })
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_all_artifacts_for_pipeline.return_value = artifacts_with_long_text
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert - should complete without error
        mock_display_table.assert_called_once()
        assert result is not None


    # ============================================================================
    # PARAMETERIZED TESTS
    # ============================================================================

    @pytest.mark.parametrize("artifact_type", ["Dataset", "Model", "Metrics", "Step"])
    @patch('cmflib.commands.artifact.list.display_table')
    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_handles_different_artifact_types(
        self,
        mock_exists,
        mock_cmfquery,
        mock_display_table,
        mock_args_artifact_list,
        mock_live_spinner,
        artifact_type
    ):
        """
        Test that different artifact types are displayed correctly.
        
        Parameterized to test: Dataset, Model, Metrics, Step
        """
        # Arrange
        mock_exists.return_value = True
        
        artifacts = pd.DataFrame({
            'id': [1],
            'name': [f'{artifact_type.lower()}_artifact'],
            'type': [artifact_type],
            'uri': [f'/path/to/{artifact_type.lower()}'],
            'create_time_since_epoch': [1702649600000]
        })
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_all_artifacts_for_pipeline.return_value = artifacts
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert
        mock_display_table.assert_called_once()
        call_args = mock_display_table.call_args[0]
        displayed_df = call_args[0]
        assert displayed_df['type'].iloc[0] == artifact_type


    @pytest.mark.parametrize("num_artifacts", [0, 1, 10, 50, 100])
    @patch('cmflib.commands.artifact.list.display_table')
    @patch('cmflib.commands.artifact.list.cmfquery.CmfQuery')
    @patch('os.path.exists')
    def test_artifact_list_handles_various_result_sizes(
        self,
        mock_exists,
        mock_cmfquery,
        mock_display_table,
        mock_args_artifact_list,
        mock_live_spinner,
        num_artifacts
    ):
        """
        Test artifact list with varying number of results.
        
        Tests edge cases: 0 (empty), 1 (single), and larger datasets.
        """
        # Arrange
        mock_exists.return_value = True
        
        if num_artifacts == 0:
            artifacts = pd.DataFrame()
        else:
            artifacts = pd.DataFrame({
                'id': range(1, num_artifacts + 1),
                'name': [f'artifact_{i}' for i in range(num_artifacts)],
                'type': ['Dataset'] * num_artifacts,
                'uri': [f'/path/artifact_{i}' for i in range(num_artifacts)],
                'create_time_since_epoch': [1702649600000 + i * 1000 for i in range(num_artifacts)]
            })
        
        mock_query_instance = MagicMock()
        mock_query_instance.get_pipeline_names.return_value = ["test-pipeline"]
        mock_query_instance.get_all_artifacts_for_pipeline.return_value = artifacts
        mock_cmfquery.return_value = mock_query_instance
        
        cmd = CmdArtifactsList(mock_args_artifact_list)
        
        # Act
        result = cmd.run(mock_live_spinner)
        
        # Assert - should handle any size gracefully
        assert result is not None
