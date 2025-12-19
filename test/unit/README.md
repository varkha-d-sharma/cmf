# CMF Unit Test Suite

This directory contains comprehensive unit tests for the CMF (Common Metadata Framework) project.

## Test Structure

```
test/
├── conftest.py                          # Shared pytest fixtures
├── unit/                                # Unit tests (Layer 1 & 2)
│   ├── test_cli_parser.py              # Layer 2: CLI argument parser tests
│   └── test_commands/                   # Layer 1: Core command tests
│       ├── test_metadata_push.py       # Metadata push command tests
│       └── test_artifact_list.py       # Artifact list command tests
├── integration/                         # Integration tests (Layer 3)
│   └── (to be added)
├── e2e/                                # End-to-end tests (Layer 5)
│   └── (to be added)
└── fixtures/                           # Test data and fixtures
    └── (to be added)
```

## Test Layers

### Layer 1: Core Command Unit Tests
**Location:** `test/unit/test_commands/`

Tests individual command classes in isolation with all external dependencies mocked.

**Current Coverage:**
- `test_metadata_push.py` - Tests for `CmdMetadataPush` command
- `test_artifact_list.py` - Tests for `CmdArtifactsList` command

**What to test:**
- Success paths with valid inputs
- Error handling for invalid inputs
- File operations (mocked)
- Server responses (mocked)
- Data transformations
- Optional vs required parameters

### Layer 2: CLI Parser Tests
**Location:** `test/unit/test_cli_parser.py`

Tests the argparse configuration and argument validation.

**Coverage:**
- Command routing to correct classes
- Required argument validation
- Optional argument handling
- Invalid argument rejection
- Argument format variations
- Help text functionality

## Running Tests

### Run all tests
```bash
pytest test/unit/
```

### Run specific test file
```bash
pytest test/unit/test_cli_parser.py
pytest test/unit/test_commands/test_metadata_push.py
```

### Run specific test class or method
```bash
pytest test/unit/test_cli_parser.py::TestCLIParser::test_metadata_push_command_routing
pytest test/unit/test_commands/test_metadata_push.py::TestCmdMetadataPush
```

### Run with coverage
```bash
pytest --cov=cmflib --cov-report=html test/unit/
```

### Run with verbose output
```bash
pytest -v test/unit/
```

### Run tests matching pattern
```bash
pytest -k "metadata" test/unit/
pytest -k "error" test/unit/
```

## Writing New Tests

### Adding a New Command Test (Layer 1)

1. Create file: `test/unit/test_commands/test_<command_name>.py`
2. Import the command class and exception types
3. Create test class: `class TestCmd<CommandName>:`
4. Write test methods following the pattern:
   ```python
   @patch('module.dependency')
   def test_command_success_scenario(self, mock_dep, fixtures):
       # Arrange
       # Act
       # Assert
   ```

### Adding Parser Tests (Layer 2)

1. Add test methods to `test/unit/test_cli_parser.py`
2. Test both positive and negative cases
3. Use `parse_args()` to test argument parsing
4. Use `pytest.raises(SystemExit)` for error cases

### Using Fixtures

Fixtures are defined in `conftest.py` and available to all tests:

```python
def test_with_fixtures(temp_dir, sample_mlmd_path, mock_cmfquery):
    # temp_dir: temporary directory
    # sample_mlmd_path: path to mock MLMD file
    # mock_cmfquery: mocked CmfQuery object
    pass
```

## Best Practices

### 1. Test Naming
- Use descriptive names: `test_<what>_<scenario>_<expected>`
- Example: `test_metadata_push_with_invalid_uuid_raises_error`

### 2. Test Organization
```python
class TestCmdMetadataPush:
    # ============================================================================
    # SUCCESS PATH TESTS
    # ============================================================================
    
    def test_success_case_1(self):
        pass
    
    # ============================================================================
    # ERROR PATH TESTS
    # ============================================================================
    
    def test_error_case_1(self):
        pass
```

### 3. Arrange-Act-Assert Pattern
```python
def test_something(self):
    # Arrange - set up test data and mocks
    mock_obj = Mock()
    mock_obj.method.return_value = "value"
    
    # Act - execute the code under test
    result = function_under_test(mock_obj)
    
    # Assert - verify expected outcomes
    assert result == "expected"
    mock_obj.method.assert_called_once()
```

### 4. Mocking External Dependencies
```python
@patch('cmflib.commands.metadata.push.os.path.exists')
@patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
def test_with_mocks(self, mock_query, mock_exists):
    mock_exists.return_value = True
    mock_query_instance = MagicMock()
    mock_query.return_value = mock_query_instance
```

### 5. Parameterized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("value1", "result1"),
    ("value2", "result2"),
])
def test_multiple_cases(self, input, expected):
    assert function(input) == expected
```

## Test Coverage Goals

- **Core commands (Layer 1):** >90%
- **CLI parser (Layer 2):** >85%
- **Overall codebase:** >85%

## Common Fixtures

### File System Fixtures
- `temp_dir` - Temporary directory
- `sample_mlmd_path` - Mock MLMD file path
- `mock_cmf_config` - Mock CMF config file

### Mock Objects
- `mock_cmfquery` - Mocked CmfQuery object
- `mock_server_response_success` - Mock successful server response
- `mock_server_response_error` - Mock error server response
- `mock_live_spinner` - Mock Live spinner

### Data Fixtures
- `sample_artifact_dataframe` - Sample artifact data
- `sample_execution_dataframe` - Sample execution data
- `sample_pipeline_name` - Standard pipeline name
- `sample_execution_uuid` - Standard execution UUID

### Argument Fixtures
- `mock_args_metadata_push` - Mock args for metadata push
- `mock_args_artifact_list` - Mock args for artifact list

## Troubleshooting

### Tests fail with import errors
Make sure CMF is installed in development mode:
```bash
pip install -e .
```

### Mocks not working as expected
Check the patch path - it should be where the object is used, not where it's defined:
```python
# Wrong
@patch('os.path.exists')

# Right
@patch('cmflib.commands.metadata.push.os.path.exists')
```

### Fixtures not found
Ensure `conftest.py` is in the test directory or parent directory.

## Next Steps

1. **Add more command tests** - Cover remaining commands (pull, export, init, etc.)
2. **Layer 3 tests** - Add integration tests for full CLI flow
3. **Layer 4 tests** - Add tests for function wrappers in `cmf_commands_wrapper.py`
4. **Layer 5 tests** - Add end-to-end tests with real workflows
5. **Improve coverage** - Identify untested code paths and add tests
6. **Add mutation testing** - Use `mutmut` to verify test quality

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
