# CMF Testing Framework - Quick Start Guide

## What Has Been Created

### 1. Test Infrastructure (Layer 1 & 2)

```
test/
├── conftest.py                      # Shared pytest fixtures (20+ reusable fixtures)
├── pytest.ini                       # Pytest configuration
├── requirements-test.txt            # Test dependencies
├── run_tests.sh                     # Quick test runner script
└── unit/
    ├── README.md                    # Comprehensive testing documentation
    ├── test_cli_parser.py          # Layer 2: CLI parser tests (70+ tests)
    ├── test_example_template.py    # Template for new tests
    └── test_commands/
        ├── test_metadata_push.py   # Layer 1: Metadata push tests (25+ tests)
        └── test_artifact_list.py   # Layer 1: Artifact list tests (25+ tests)
```

## Getting Started

### Step 1: Install Test Dependencies

```bash
cd /home/sharvark/pane/cmf
pip install -r test/requirements-test.txt
```

### Step 2: Run Your First Tests

```bash
# Run all unit tests
pytest test/unit/

# Run with coverage report
pytest --cov=cmflib --cov-report=html test/unit/

# Run specific test file
pytest test/unit/test_cli_parser.py

# Run tests with verbose output
pytest -v test/unit/

# Using the convenience script
./test/run_tests.sh --coverage
```

### Step 3: View Coverage Report

After running with `--cov-report=html`:
```bash
# Open in browser
firefox htmlcov/index.html
# or
google-chrome htmlcov/index.html
```

## Test Files Explained

### `conftest.py` - Shared Fixtures
Contains 20+ reusable fixtures for all tests:
- **File system fixtures:** `temp_dir`, `sample_mlmd_path`
- **Mock objects:** `mock_cmfquery`, `mock_server_response_success`
- **Test data:** `sample_artifact_dataframe`, `sample_execution_dataframe`
- **Arguments:** `mock_args_metadata_push`, `mock_args_artifact_list`

**Usage in tests:**
```python
def test_something(temp_dir, mock_cmfquery):
    # Fixtures are automatically injected
    file = temp_dir / "test.txt"
    mock_cmfquery.get_pipeline_names.return_value = ["pipeline1"]
```

### `test_cli_parser.py` - Layer 2 Tests
Tests CLI argument parsing and routing (70+ test methods):
- Command routing verification
- Required/optional argument validation
- Invalid argument handling
- Help text functionality
- Edge cases

**Example:**
```python
def test_metadata_push_command_routing():
    args = parse_args(['metadata', 'push', '-p', 'pipeline', '-f', './mlmd'])
    assert args.cmd == 'metadata'
    assert args.func is not None
```

### `test_commands/test_metadata_push.py` - Layer 1 Tests
Tests `CmdMetadataPush` command class (25+ test methods):
- Success paths
- Error handling
- Server response codes
- File operations
- UUID validation

**Example:**
```python
@patch('cmflib.commands.metadata.push.cmfquery.CmfQuery')
@patch('os.path.exists')
def test_metadata_push_success(mock_exists, mock_cmfquery):
    mock_exists.return_value = True
    # ... test implementation
```

### `test_commands/test_artifact_list.py` - Layer 1 Tests
Tests `CmdArtifactsList` command class (25+ test methods):
- Artifact display logic
- DateTime conversion
- Filtering by artifact name
- Pagination handling
- Empty result handling

### `test_example_template.py` - Template
Complete template showing:
- Test organization patterns
- Mocking strategies
- Fixture usage
- Parameterized tests
- Best practices with extensive comments

## Quick Reference

### Running Specific Tests

```bash
# Run all tests in a file
pytest test/unit/test_cli_parser.py

# Run a specific test class
pytest test/unit/test_cli_parser.py::TestCLIParser

# Run a specific test method
pytest test/unit/test_cli_parser.py::TestCLIParser::test_metadata_push_command_routing

# Run tests matching a pattern
pytest -k "metadata" test/unit/
pytest -k "error" test/unit/
pytest -k "success" test/unit/
```

### Using Markers

```bash
# Run only unit tests
pytest -m unit test/

# Run only parser tests
pytest -m parser test/

# Run only metadata-related tests
pytest -m metadata test/
```

### Coverage Commands

```bash
# Basic coverage report
pytest --cov=cmflib test/unit/

# Coverage with HTML report
pytest --cov=cmflib --cov-report=html test/unit/

# Coverage with missing lines shown
pytest --cov=cmflib --cov-report=term-missing test/unit/

# Coverage for specific module
pytest --cov=cmflib.commands.metadata test/unit/
```

## Writing Your First Test

### 1. Create Test File
```bash
touch test/unit/test_commands/test_my_command.py
```

### 2. Copy Template Structure
```python
import pytest
from unittest.mock import Mock, patch
from cmflib.commands.my_module.my_command import CmdMyCommand

class TestCmdMyCommand:
    
    @patch('cmflib.commands.my_module.my_command.dependency')
    def test_my_command_success(self, mock_dep, mock_args_fixture):
        # Arrange
        mock_dep.return_value = "expected"
        cmd = CmdMyCommand(mock_args_fixture)
        
        # Act
        result = cmd.run(None)
        
        # Assert
        assert result is not None
        mock_dep.assert_called_once()
```

### 3. Run Your Test
```bash
pytest test/unit/test_commands/test_my_command.py -v
```

## Common Patterns

### Pattern 1: Testing with Mocks
```python
@patch('module.external_call')
def test_with_mock(mock_external, fixture):
    # Configure mock
    mock_external.return_value = "value"
    
    # Run test
    result = function_under_test()
    
    # Verify
    mock_external.assert_called_once_with("expected_arg")
    assert result == "expected"
```

### Pattern 2: Testing Exceptions
```python
def test_raises_exception(fixture):
    with pytest.raises(YourException) as exc_info:
        function_that_should_fail()
    
    assert "expected message" in str(exc_info.value)
```

### Pattern 3: Parameterized Testing
```python
@pytest.mark.parametrize("input,expected", [
    ("a", "A"),
    ("b", "B"),
])
def test_multiple_cases(input, expected):
    assert transform(input) == expected
```

### Pattern 4: Using Temp Files
```python
def test_with_file(temp_dir):
    # Create test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")
    
    # Test your function
    result = process_file(str(test_file))
    
    # Verify
    assert result is not None
```

## Test Statistics

### Current Coverage
- **Layer 1 (Core Commands):** 2 command classes, 50+ tests
- **Layer 2 (CLI Parser):** 70+ tests
- **Total Test Methods:** 120+ tests
- **Shared Fixtures:** 20+ reusable fixtures

### Test Categories
- Success path tests: ~40%
- Error handling tests: ~35%
- Validation tests: ~15%
- Edge case tests: ~10%

## Next Steps

### 1. Add More Layer 1 Tests
Create tests for remaining commands:
- `test_metadata_pull.py`
- `test_metadata_export.py`
- `test_artifact_push.py`
- `test_artifact_pull.py`
- `test_init_local.py`
- `test_execution_list.py`
- `test_pipeline_list.py`
- `test_repo_push.py`
- `test_repo_pull.py`

### 2. Add Layer 3 Tests (Integration)
Create `test/integration/` directory with:
- CLI main flow tests
- Command execution tests
- Response handling tests

### 3. Add Layer 4 Tests (Function Wrappers)
Create `test/unit/test_wrappers.py` to test:
- Function wrappers in `cmf_commands_wrapper.py`
- Exception handling decorator
- Optional parameter logic

### 4. Achieve Coverage Goals
- Run coverage: `pytest --cov=cmflib --cov-report=html test/`
- Identify gaps in coverage report
- Add tests for uncovered code paths
- Target: 85%+ overall coverage

### 5. Add CI/CD Integration
Create `.github/workflows/tests.yml`:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r test/requirements-test.txt
      - name: Run tests
        run: pytest --cov=cmflib test/
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Problem: Import Errors
**Solution:** Install CMF in development mode:
```bash
pip install -e .
```

### Problem: Fixtures Not Found
**Solution:** Ensure `conftest.py` exists in test directory

### Problem: Mocks Not Working
**Solution:** Check patch path - use where object is used, not defined:
```python
# Wrong
@patch('os.path.exists')

# Right  
@patch('cmflib.commands.metadata.push.os.path.exists')
```

### Problem: Tests Pass Individually But Fail Together
**Solution:** Tests may have shared state. Use fixtures for isolation:
```python
@pytest.fixture(autouse=True)
def reset_state():
    # Reset state before each test
    pass
```

## Resources

- **Documentation:** `test/unit/README.md`
- **Template:** `test/unit/test_example_template.py`
- **Fixtures:** `test/conftest.py`
- **Configuration:** `pytest.ini`

## Support

For questions or issues:
1. Check `test/unit/README.md` for detailed documentation
2. Review `test_example_template.py` for patterns
3. Look at existing tests for examples
4. Consult pytest documentation: https://docs.pytest.org/

---

**Remember:** Good tests are:
- ✅ Fast
- ✅ Isolated
- ✅ Repeatable
- ✅ Self-validating
- ✅ Timely

Happy testing! 🧪
