#!/bin/bash
# Verification script for Test Results Visualization Tool
# Run this to ensure everything is properly installed

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  Test Results Visualization Tool - Installation Verification"
echo "═══════════════════════════════════════════════════════════════"
echo

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if in correct directory
if [ ! -f "tests/visualize_test_results.py" ]; then
    echo -e "${RED}✗${NC} Error: Not in graphrag-service directory"
    echo "Please run from: /srv/luris/be/graphrag-service"
    exit 1
fi

echo -e "${GREEN}✓${NC} In correct directory: $(pwd)"
echo

# Check virtual environment
echo "Checking virtual environment..."
if [ ! -d "venv" ]; then
    echo -e "${RED}✗${NC} Virtual environment not found"
    exit 1
fi

# Activate venv
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"
echo

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python version: $PYTHON_VERSION"
echo

# Check dependencies
echo "Checking dependencies..."

# Check pandas
if python -c "import pandas" 2>/dev/null; then
    PANDAS_VERSION=$(python -c "import pandas; print(pandas.__version__)")
    echo -e "${GREEN}✓${NC} pandas: $PANDAS_VERSION"
else
    echo -e "${RED}✗${NC} pandas not installed"
    exit 1
fi

# Check rich
if python -c "import rich" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} rich: installed"
else
    echo -e "${RED}✗${NC} rich not installed"
    echo "Installing rich..."
    pip install rich
fi

# Check pytest-json-report
if python -c "import pytest_jsonreport" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} pytest-json-report: installed"
else
    echo -e "${YELLOW}⚠${NC} pytest-json-report not installed (optional)"
fi

echo

# Check visualization module
echo "Checking visualization module..."
if python -c "from tests.visualize_test_results import TestResultsVisualizer" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} TestResultsVisualizer imported successfully"
else
    echo -e "${RED}✗${NC} Failed to import TestResultsVisualizer"
    exit 1
fi
echo

# Check files
echo "Checking files..."
FILES=(
    "tests/visualize_test_results.py"
    "tests/example_visualization_usage.py"
    "tests/VISUALIZATION_README.md"
    "tests/QUICKSTART_VISUALIZATION.md"
    "tests/VISUALIZATION_SUMMARY.md"
    "tests/VISUALIZATION_INDEX.md"
    "tests/sample_results.json"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}✓${NC} $file ($SIZE)"
    else
        echo -e "${RED}✗${NC} Missing: $file"
        exit 1
    fi
done
echo

# Test with sample data
echo "Testing with sample data..."
if python tests/visualize_test_results.py --input tests/sample_results.json --no-display > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Sample visualization successful"
else
    echo -e "${RED}✗${NC} Failed to visualize sample results"
    exit 1
fi
echo

# Generate test report
echo "Generating test report..."
if python tests/visualize_test_results.py \
    --input tests/sample_results.json \
    --export-markdown tests/verification_report.md \
    --export-json tests/verification_data.json \
    --no-display > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Test report generated"
    echo "  - tests/verification_report.md"
    echo "  - tests/verification_data.json"
else
    echo -e "${RED}✗${NC} Failed to generate test report"
    exit 1
fi
echo

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ INSTALLATION VERIFIED SUCCESSFULLY${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo
echo "Next steps:"
echo "1. Read: tests/QUICKSTART_VISUALIZATION.md"
echo "2. Try:  python tests/visualize_test_results.py --input tests/sample_results.json"
echo "3. Run:  pytest tests/test_api_parity_real_data.py --json=results.json -v"
echo "4. Visualize: python tests/visualize_test_results.py --input results.json"
echo
echo "Documentation:"
echo "  Quick Start:  tests/QUICKSTART_VISUALIZATION.md"
echo "  Full Docs:    tests/VISUALIZATION_README.md"
echo "  Examples:     tests/example_visualization_usage.py"
echo
