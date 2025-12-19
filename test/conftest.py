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
Pytest configuration file with shared fixtures for CMF tests.

This file contains fixtures that are available to all tests without explicit import.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pandas as pd


@pytest.fixture
def temp_dir():
    """
    Creates a temporary directory for test isolation.
    Automatically cleaned up after test completion.
    
    Usage:
        def test_something(temp_dir):
            file_path = temp_dir / "test.txt"
            file_path.write_text("content")
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_mlmd_path(temp_dir):
    """
    Creates a sample MLMD file path (not an actual database, just a path).
    Use this when you need to mock file existence checks.
    
    Usage:
        def test_with_mlmd(sample_mlmd_path):
            # sample_mlmd_path points to temp_dir/mlmd
            pass
    """
    mlmd_path = temp_dir / "mlmd"
    # Create an empty file to simulate existence
    mlmd_path.touch()
    return mlmd_path


@pytest.fixture
def sample_pipeline_name():
    """
    Provides a standard pipeline name for tests.
    """
    return "test-pipeline"


@pytest.fixture
def sample_execution_uuid():
    """
    Provides a sample execution UUID for tests.
    """
    return "f9da581c-d16c-11ef-9809-9350156ed1ac"


@pytest.fixture
def mock_cmf_config(temp_dir):
    """
    Creates a mock CMF config file with standard settings.
    
    Returns:
        Path to the config file
    """
    config_content = {
        "cmf-server-url": "http://127.0.0.1:80",
        "neo4j-uri": "bolt://localhost:7687",
        "neo4j-user": "neo4j",
        "neo4j-password": "password"
    }
    config_path = temp_dir / ".cmfconfig"
    config_path.write_text(json.dumps(config_content))
    return config_path


@pytest.fixture
def mock_cmfquery():
    """
    Creates a mock CmfQuery object with common methods.
    
    Usage:
        def test_with_query(mock_cmfquery):
            mock_cmfquery.get_pipeline_names.return_value = ["pipeline1"]
    """
    mock_query = MagicMock()
    mock_query.get_pipeline_names.return_value = ["test-pipeline"]
    mock_query.get_all_executions_in_pipeline.return_value = pd.DataFrame()
    mock_query.dumptojson.return_value = json.dumps({
        "Pipeline": [{
            "name": "test-pipeline",
            "stages": []
        }]
    })
    return mock_query


@pytest.fixture
def mock_server_response_success():
    """
    Creates a mock successful server response.
    
    Usage:
        def test_success(mock_server_response_success):
            # response.status_code == 200
            pass
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    return mock_response


@pytest.fixture
def mock_server_response_error():
    """
    Creates a mock error server response.
    """
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"status": "error", "message": "Server unavailable"}
    return mock_response


@pytest.fixture
def sample_artifact_dataframe():
    """
    Creates a sample DataFrame representing artifacts.
    Useful for testing artifact list commands.
    """
    return pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['artifact1', 'artifact2', 'artifact3'],
        'type': ['Dataset', 'Model', 'Metrics'],
        'uri': ['/path/to/artifact1', '/path/to/artifact2', '/path/to/artifact3'],
        'create_time_since_epoch': [1702649600000, 1702650000000, 1702650400000]
    })


@pytest.fixture
def sample_execution_dataframe():
    """
    Creates a sample DataFrame representing executions.
    """
    return pd.DataFrame({
        'id': [1, 2],
        'name': ['execution1', 'execution2'],
        'type': ['Training', 'Evaluation'],
        'properties': [
            {'Execution_uuid': 'uuid-1', 'Python_Env': 'env1.txt'},
            {'Execution_uuid': 'uuid-2', 'Python_Env': 'env2.txt'}
        ]
    })


@pytest.fixture
def mock_args_metadata_push():
    """
    Creates mock arguments for metadata push command.
    
    Usage:
        def test_metadata_push(mock_args_metadata_push):
            mock_args_metadata_push.pipeline_name = ["custom-pipeline"]
    """
    args = Mock()
    args.file_name = ["./mlmd"]
    args.pipeline_name = ["test-pipeline"]
    args.execution_uuid = None
    args.tensorboard_path = None
    return args


@pytest.fixture
def mock_args_artifact_list():
    """
    Creates mock arguments for artifact list command.
    """
    args = Mock()
    args.file_name = ["./mlmd"]
    args.pipeline_name = ["test-pipeline"]
    args.artifact_name = None
    return args


@pytest.fixture
def mock_live_spinner():
    """
    Creates a mock Live spinner object for commands that use it.
    
    Usage:
        def test_command(mock_live_spinner):
            cmd.run(mock_live_spinner)
    """
    mock_live = MagicMock()
    return mock_live


@pytest.fixture(autouse=True)
def reset_environment():
    """
    Resets environment variables before each test.
    This prevents test pollution from environment state.
    """
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def capture_print(monkeypatch):
    """
    Captures print statements during test execution.
    
    Usage:
        def test_with_print(capture_print):
            some_function_that_prints()
            assert "expected text" in capture_print.getvalue()
    """
    from io import StringIO
    output = StringIO()
    
    def mock_print(*args, **kwargs):
        print(*args, file=output, **kwargs)
    
    monkeypatch.setattr("builtins.print", mock_print)
    return output
