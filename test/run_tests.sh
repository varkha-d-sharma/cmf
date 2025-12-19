#!/bin/bash
###
# Quick test runner script for CMF tests
# Usage: ./test/run_tests.sh [options]
###

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}CMF Test Runner${NC}"
echo "================================"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install test dependencies with:"
    echo "  pip install -r test/requirements-test.txt"
    exit 1
fi

# Default options
TEST_PATH="test/unit"
COVERAGE=false
VERBOSE=false
MARKERS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--marker)
            MARKERS="$2"
            shift 2
            ;;
        -p|--path)
            TEST_PATH="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage       Run with coverage report"
            echo "  -v, --verbose        Verbose output"
            echo "  -m, --marker MARKER  Run tests with specific marker"
            echo "  -p, --path PATH      Test path (default: test/unit)"
            echo "  -h, --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Run all unit tests"
            echo "  $0 -c                        # Run with coverage"
            echo "  $0 -m metadata               # Run metadata tests only"
            echo "  $0 -p test/unit/test_cli_parser.py  # Run specific file"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=cmflib --cov-report=term-missing --cov-report=html"
    echo -e "${YELLOW}Running with coverage...${NC}"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $MARKERS"
    echo -e "${YELLOW}Running tests with marker: $MARKERS${NC}"
fi

PYTEST_CMD="$PYTEST_CMD $TEST_PATH"

echo "Command: $PYTEST_CMD"
echo "================================"
echo ""

# Run tests
$PYTEST_CMD

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo -e "${YELLOW}Coverage report generated in htmlcov/index.html${NC}"
    fi
else
    echo ""
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
