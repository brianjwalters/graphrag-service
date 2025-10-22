# Test Results Visualization Tool

Comprehensive visualization and reporting tool for GraphRAG API parity test results.

## Features

- **Rich Terminal Output** - Beautiful formatted tables with color coding
- **Performance Metrics** - Query performance analysis and benchmarks
- **Data Quality Assessment** - Quality metrics and validation status
- **Markdown Reports** - Export formatted documentation
- **JSON Export** - Structured data for further analysis
- **Pandas Integration** - Convert results to DataFrame for analysis

## Installation

### Dependencies

The tool requires the following packages (already in graphrag-service requirements):

```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
pip install pandas rich
```

## Usage

### Step 1: Run Tests with JSON Output

```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate

# Run API parity tests and save results
pytest tests/test_api_parity_real_data.py --json=results.json -v
```

### Step 2: Visualize Results

```bash
# Display all visualizations in terminal
python tests/visualize_test_results.py --input results.json

# Export markdown report
python tests/visualize_test_results.py --input results.json --export-markdown api_parity_report.md

# Export JSON data
python tests/visualize_test_results.py --input results.json --export-json results_data.json

# Export only (no terminal display)
python tests/visualize_test_results.py --input results.json --export-markdown report.md --no-display
```

## Output Examples

### Terminal Summary

```
╔═══════════════════════════════════════════════════════════════╗
║            API Parity Test Results Summary                    ║
╠═══════════════════════════════════════════════════════════════╣
║ Test Category              │ Passed │ Failed │ Skipped │ Time ║
╠═══════════════════════════════════════════════════════════════╣
║ QueryBuilder Tests         │   3/3  │   0    │    0    │ 0.5s ║
║ SelectQueryBuilder Tests   │   9/10 │   1    │    0    │ 2.3s ║
║ Cross-Schema Tests         │   3/3  │   0    │    0    │ 1.1s ║
║ CRUD Validation           │   4/4  │   0    │    0    │ 0.3s ║
║ Performance Tests         │   3/4  │   1    │    0    │ 8.2s ║
║ Multi-Tenant Tests        │   3/3  │   0    │    0    │ 0.8s ║
╠═══════════════════════════════════════════════════════════════╣
║ TOTAL                     │  25/27 │   2    │    0    │ 13.2s║
╚═══════════════════════════════════════════════════════════════╝
```

### Performance Metrics

```
╔═══════════════════════════════════════════════════════════════╗
║            Query Performance Analysis                         ║
╠═══════════════════════════════════════════════════════════════╣
║ Operation                  │ Count │ Avg(ms) │ Max(ms) │ Status║
╠═══════════════════════════════════════════════════════════════╣
║ SELECT law.documents       │   12  │   45    │   120   │ ✓ PASS║
║ SELECT graph.nodes (1K)    │    5  │  230    │   480   │ ✓ PASS║
║ SELECT graph.nodes (5K)    │    2  │ 1200    │  1850   │⚠ WARN ║
║ COUNT queries              │    8  │   85    │   180   │ ✓ PASS║
║ Cross-schema joins         │    3  │  340    │   520   │ ✓ PASS║
╚═══════════════════════════════════════════════════════════════╝
```

### Data Quality Metrics

```
╔═══════════════════════════════════════════════════════════════╗
║            Data Quality Metrics                               ║
╠═══════════════════════════════════════════════════════════════╣
║ Metric                     │ Value          │ Status          ║
╠═══════════════════════════════════════════════════════════════╣
║ Multi-tenant isolation     │ 100% validated │ ✓ PASS         ║
║ NULL handling              │ Correct        │ ✓ PASS         ║
║ Large dataset (>1K)        │ 5 tests        │ ✓ PASS         ║
║ Pagination accuracy        │ 100%           │ ✓ PASS         ║
║ Overall test pass rate     │ 92.6% (25/27)  │ ✓ PASS         ║
╚═══════════════════════════════════════════════════════════════╝
```

## Programmatic Usage

### Python API

```python
from visualize_test_results import TestResultsVisualizer

# Load and visualize results
viz = TestResultsVisualizer('results.json')

# Display individual sections
viz.display_summary()
viz.display_performance_metrics()
viz.display_quality_metrics()

# Or display everything
viz.display_all()

# Export reports
viz.export_markdown_report('my_report.md')
viz.export_json('my_data.json')

# Convert to pandas DataFrame for analysis
df = viz.to_dataframe()
print(df.groupby('category')['duration'].mean())
```

### Advanced Analysis with Pandas

```python
from visualize_test_results import TestResultsVisualizer
import pandas as pd

# Load results
viz = TestResultsVisualizer('results.json')
df = viz.to_dataframe()

# Analyze by category
category_stats = df.groupby('category').agg({
    'duration': ['count', 'mean', 'sum'],
    'outcome': lambda x: (x == 'passed').sum()
})

print(category_stats)

# Find slowest tests
slowest = df.nlargest(10, 'duration')[['name', 'category', 'duration']]
print("\nSlowest Tests:")
print(slowest)

# Calculate pass rate by category
pass_rates = df.groupby('category').apply(
    lambda x: (x['outcome'] == 'passed').sum() / len(x) * 100
)
print("\nPass Rates by Category:")
print(pass_rates)
```

## Output Files

### Markdown Report

The markdown report includes:

- Test summary with totals
- Results breakdown by category
- Performance metrics table
- Data quality metrics
- Failed test details (if any)
- Overall status

Example: `api_parity_test_report.md`

### JSON Export

The JSON export contains structured data:

```json
{
  "summary": {
    "total_tests": 27,
    "passed": 25,
    "failed": 2,
    "skipped": 0,
    "total_duration": 13.2,
    "pass_rate": 92.6
  },
  "categories": {
    "QueryBuilder Tests": {
      "passed": 3,
      "failed": 0,
      "skipped": 0,
      "total": 3,
      "duration": 0.5
    }
  },
  "tests": [
    {
      "name": "test_basic_select",
      "category": "QueryBuilder Tests",
      "outcome": "passed",
      "duration": 0.123,
      "error": null
    }
  ],
  "generated_at": "2025-01-20T10:30:00"
}
```

## Color Coding

### Terminal Output

- **Green** - Tests passed, good performance
- **Yellow** - Warnings, partial failures
- **Red** - Tests failed, critical issues

### Performance Thresholds

- **Green** - Max query time < 500ms
- **Yellow** - Max query time 500ms - 1000ms
- **Red** - Max query time > 1000ms

### Pass Rate Thresholds

- **Green** - Pass rate ≥ 90%
- **Yellow** - Pass rate 70-89%
- **Red** - Pass rate < 70%

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run API Parity Tests
  run: |
    cd /srv/luris/be/graphrag-service
    source venv/bin/activate
    pytest tests/test_api_parity_real_data.py --json=results.json -v

- name: Generate Test Report
  run: |
    cd /srv/luris/be/graphrag-service
    source venv/bin/activate
    python tests/visualize_test_results.py \
      --input results.json \
      --export-markdown api_parity_report.md \
      --export-json api_parity_data.json

- name: Upload Reports
  uses: actions/upload-artifact@v3
  with:
    name: test-reports
    path: |
      /srv/luris/be/graphrag-service/api_parity_report.md
      /srv/luris/be/graphrag-service/api_parity_data.json
```

## Customization

### Adding Custom Performance Metrics

Edit the `generate_performance_chart()` method to include actual query metrics:

```python
def generate_performance_chart(self) -> Table:
    # Parse actual performance data from test results
    perf_tests = [t for t in self.test_results if t.category == 'Performance Tests']

    for test in perf_tests:
        # Extract query metrics from test
        if hasattr(test, 'performance_data'):
            query_time = test.performance_data.get('query_time_ms', 0)
            # Add to table
```

### Custom Categories

Modify `_extract_category()` to match your test naming patterns:

```python
def _extract_category(self, nodeid: str) -> str:
    if 'TestMyCustomTests' in nodeid:
        return 'Custom Test Category'
    # ... existing categories
```

## Troubleshooting

### Issue: No results.json file

**Solution**: Make sure to run pytest with `--json` flag:
```bash
pytest tests/test_api_parity_real_data.py --json=results.json -v
```

### Issue: Import errors

**Solution**: Activate venv before running:
```bash
source venv/bin/activate
python tests/visualize_test_results.py --input results.json
```

### Issue: Missing dependencies

**Solution**: Install required packages:
```bash
pip install pandas rich
```

### Issue: Empty performance metrics

**Solution**: The current implementation uses simulated performance data. To show real metrics, you need to capture them in your test code and include them in the pytest JSON output.

## Future Enhancements

Planned features:

1. **Live Monitoring** - Real-time test progress display
2. **HTML Reports** - Web-viewable interactive reports
3. **Trend Analysis** - Compare results across multiple test runs
4. **Performance Regression Detection** - Alert on performance degradation
5. **Custom Thresholds** - Configurable pass/fail thresholds
6. **Test History** - Track test results over time
7. **Comparison Mode** - Side-by-side comparison of test runs

## Support

For issues or questions:

1. Check this README for common solutions
2. Review the tool's help: `python tests/visualize_test_results.py --help`
3. Examine the source code for customization options
4. Consult GraphRAG service documentation

## License

This tool is part of the Luris backend services suite.

---

**Last Updated**: 2025-01-20
**Version**: 1.0.0
**Maintainer**: Luris Development Team
