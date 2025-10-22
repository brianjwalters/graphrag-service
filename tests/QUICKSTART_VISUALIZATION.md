# Quick Start: Test Results Visualization

Fast guide to visualizing API parity test results.

## 1. Install Dependencies

```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
pip install -r requirements.txt
```

This installs:
- `pandas>=2.0.0` - Data analysis
- `rich>=13.0.0` - Terminal formatting
- `pytest-json-report>=1.5.0` - JSON test results

## 2. Run Tests with JSON Output

```bash
# Activate venv (if not already active)
source venv/bin/activate

# Run API parity tests and save JSON results
pytest tests/test_api_parity_real_data.py --json=results.json -v
```

## 3. Visualize Results

### Option A: Quick Display (Terminal)

```bash
python tests/visualize_test_results.py --input results.json
```

**Output:**
- Test summary table
- Performance metrics
- Data quality assessment
- Failed test details (if any)

### Option B: Export Markdown Report

```bash
python tests/visualize_test_results.py \
  --input results.json \
  --export-markdown api_parity_report.md
```

### Option C: Export Both

```bash
python tests/visualize_test_results.py \
  --input results.json \
  --export-markdown report.md \
  --export-json data.json
```

## 4. View Results

### Terminal Output

Displays rich formatted tables with color coding:
- **Green** - Tests passed, good performance
- **Yellow** - Warnings, needs attention
- **Red** - Tests failed, critical issues

### Markdown Report

Open the markdown file:
```bash
cat api_parity_report.md
# Or open in your favorite markdown viewer
```

### JSON Data

Load in Python for custom analysis:
```python
import json
with open('data.json') as f:
    results = json.load(f)
print(results['summary'])
```

## 5. Advanced Analysis

### Python REPL

```python
from visualize_test_results import TestResultsVisualizer

# Load results
viz = TestResultsVisualizer('results.json')

# Convert to pandas DataFrame
df = viz.to_dataframe()

# Analyze
print(df.groupby('category')['duration'].describe())
```

### Example Script

```bash
python tests/example_visualization_usage.py
```

This runs 6 complete examples showing different analysis techniques.

## Common Commands

### Full Workflow

```bash
# 1. Activate venv
cd /srv/luris/be/graphrag-service
source venv/bin/activate

# 2. Run tests
pytest tests/test_api_parity_real_data.py --json=results.json -v

# 3. Visualize
python tests/visualize_test_results.py --input results.json

# 4. Export reports
python tests/visualize_test_results.py \
  --input results.json \
  --export-markdown report.md \
  --export-json data.json
```

### Test Specific Categories

```bash
# Test only QueryBuilder
pytest tests/test_api_parity_real_data.py::TestQueryBuilder --json=qb_results.json -v
python tests/visualize_test_results.py --input qb_results.json

# Test only Performance
pytest tests/test_api_parity_real_data.py::TestPerformance --json=perf_results.json -v
python tests/visualize_test_results.py --input perf_results.json
```

### Continuous Testing

```bash
# Watch for file changes and re-run tests
watch -n 5 'pytest tests/test_api_parity_real_data.py --json=results.json -v && \
  python tests/visualize_test_results.py --input results.json --no-display \
  --export-markdown latest_report.md'
```

## Output Files Structure

```
/srv/luris/be/graphrag-service/
├── results.json                    # Pytest JSON output
├── api_parity_report.md           # Markdown report
├── api_parity_test_data.json      # Structured JSON data
└── tests/
    ├── visualize_test_results.py           # Main tool
    ├── example_visualization_usage.py      # Examples
    ├── VISUALIZATION_README.md             # Full documentation
    └── QUICKSTART_VISUALIZATION.md         # This file
```

## Troubleshooting

### "results.json not found"

Run tests first:
```bash
pytest tests/test_api_parity_real_data.py --json=results.json -v
```

### "ModuleNotFoundError: No module named 'rich'"

Install dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "No such file or directory"

Check you're in the correct directory:
```bash
cd /srv/luris/be/graphrag-service
pwd  # Should show /srv/luris/be/graphrag-service
```

## Next Steps

1. **Review Full Documentation**: `tests/VISUALIZATION_README.md`
2. **Run Examples**: `python tests/example_visualization_usage.py`
3. **Customize Analysis**: Edit `visualize_test_results.py` for your needs
4. **Integrate with CI/CD**: See VISUALIZATION_README.md for examples

## Help

```bash
# Get help
python tests/visualize_test_results.py --help

# Check tool version
python tests/visualize_test_results.py --version  # (not yet implemented)
```

---

**Last Updated**: 2025-01-20
