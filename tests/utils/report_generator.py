"""
Report Generator for GraphRAG E2E Testing

Generates comprehensive test reports in multiple formats:
- HTML: Visual report with charts and tables
- CSV: Tabular data for Excel/analysis
- JSON: Structured data for programmatic use
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class E2ETestReport:
    """Complete E2E test report data structure."""
    test_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    document_name: str
    client_id: str
    case_id: str
    service_health: Dict[str, Any]
    stage_results: List[Dict[str, Any]]
    database_validation: Dict[str, Any]
    performance_benchmark: Dict[str, Any]
    overall_status: str  # "PASSED" or "FAILED"
    total_stages: int
    passed_stages: int
    failed_stages: int


class ReportGenerator:
    """
    Generates comprehensive test reports in multiple formats.

    Output formats:
    - HTML: Visual report with Bootstrap styling
    - CSV: Tabular metrics data
    - JSON: Complete structured data
    """

    def __init__(self, output_dir: Path):
        """
        Initialize report generator.

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(self, report: E2ETestReport) -> Path:
        """
        Generate HTML report with visual formatting.

        Args:
            report: E2E test report data

        Returns:
            Path to generated HTML file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.output_dir / f"e2e_test_report_{timestamp}.html"

        # Build stage results table
        stage_rows = ""
        for stage in report.stage_results:
            status_icon = "✅" if stage["passed"] else "❌"
            status_class = "table-success" if stage["passed"] else "table-danger"
            stage_rows += f"""
                <tr class="{status_class}">
                    <td>{stage['stage_number']}</td>
                    <td>{stage['stage_name']}</td>
                    <td>{status_icon} {stage['status']}</td>
                    <td>{stage['duration_seconds']:.2f}s</td>
                    <td>{stage.get('details', 'N/A')}</td>
                </tr>
            """

        # Build database validation table
        db_rows = ""
        for validation in report.database_validation.get("validations", []):
            status_icon = "✅" if validation["passed"] else "❌"
            status_class = "table-success" if validation["passed"] else "table-danger"
            db_rows += f"""
                <tr class="{status_class}">
                    <td>{validation['table']}</td>
                    <td>{validation['row_count']}</td>
                    <td>{validation['expected_min']}</td>
                    <td>{status_icon}</td>
                    <td>{validation['message']}</td>
                </tr>
            """

        # Build performance comparison table
        perf_rows = ""
        for comparison in report.performance_benchmark.get("comparisons", []):
            old_p50 = comparison["old_method"].p50_ms
            new_p50 = comparison["new_method"].p50_ms
            improvement = comparison["improvement_p50_pct"]
            status_class = "table-success" if improvement >= 50 else "table-warning"

            perf_rows += f"""
                <tr class="{status_class}">
                    <td>{comparison['table']}</td>
                    <td>{old_p50:.2f}ms</td>
                    <td>{new_p50:.2f}ms</td>
                    <td>{improvement:.1f}%</td>
                    <td>{comparison['speedup_factor_p50']:.2f}x</td>
                </tr>
            """

        # Service health table
        service_rows = ""
        for service_name, service_info in report.service_health.get("services", {}).items():
            status_icon = "✅" if service_info["overall_healthy"] else "❌"
            status_class = "table-success" if service_info["overall_healthy"] else "table-danger"
            service_rows += f"""
                <tr class="{status_class}">
                    <td>{service_name}</td>
                    <td>{service_info['systemd_unit']}</td>
                    <td>{service_info['port']}</td>
                    <td>{status_icon}</td>
                    <td>{service_info.get('response_time_ms', 'N/A')}ms</td>
                </tr>
            """

        # Overall status styling
        overall_class = "alert-success" if report.overall_status == "PASSED" else "alert-danger"
        overall_icon = "✅" if report.overall_status == "PASSED" else "❌"

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GraphRAG E2E Test Report - {timestamp}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 20px; background-color: #f8f9fa; }}
        .report-header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .metric-value {{ font-size: 2rem; font-weight: bold; color: #667eea; }}
        .metric-label {{ color: #6c757d; font-size: 0.9rem; }}
        .section-title {{ margin-top: 30px; margin-bottom: 20px; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .pass-rate {{ font-size: 3rem; font-weight: bold; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Header -->
        <div class="report-header">
            <h1>{overall_icon} GraphRAG E2E Test Report</h1>
            <p class="mb-0">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>

        <!-- Overall Status -->
        <div class="alert {overall_class}" role="alert">
            <h3 class="alert-heading">{overall_icon} Overall Status: {report.overall_status}</h3>
            <hr>
            <p><strong>Document:</strong> {report.document_name}</p>
            <p><strong>Test Duration:</strong> {report.duration_seconds:.2f} seconds</p>
            <p><strong>Stages Passed:</strong> {report.passed_stages}/{report.total_stages}</p>
        </div>

        <!-- Key Metrics -->
        <div class="row">
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value pass-rate">{int((report.passed_stages/report.total_stages)*100)}%</div>
                    <div class="metric-label">PASS RATE</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value">{report.database_validation.get('total_rows', 0)}</div>
                    <div class="metric-label">TOTAL DB ROWS</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value">{report.performance_benchmark.get('avg_improvement_p50_pct', 0):.0f}%</div>
                    <div class="metric-label">AVG PERFORMANCE GAIN</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value">{report.performance_benchmark.get('avg_speedup_factor', 0):.1f}x</div>
                    <div class="metric-label">AVG SPEEDUP</div>
                </div>
            </div>
        </div>

        <!-- Service Health -->
        <h2 class="section-title">1. Service Health Status</h2>
        <div class="table-responsive">
            <table class="table table-bordered table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Service Name</th>
                        <th>Systemd Unit</th>
                        <th>Port</th>
                        <th>Status</th>
                        <th>Response Time</th>
                    </tr>
                </thead>
                <tbody>
                    {service_rows}
                </tbody>
            </table>
        </div>

        <!-- Stage Results -->
        <h2 class="section-title">2. Pipeline Stage Results</h2>
        <div class="table-responsive">
            <table class="table table-bordered table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Stage</th>
                        <th>Name</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {stage_rows}
                </tbody>
            </table>
        </div>

        <!-- Database Validation -->
        <h2 class="section-title">3. Database Validation Results</h2>
        <div class="table-responsive">
            <table class="table table-bordered table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Table Name</th>
                        <th>Row Count</th>
                        <th>Expected Min</th>
                        <th>Status</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    {db_rows}
                </tbody>
            </table>
        </div>

        <!-- Performance Benchmark -->
        <h2 class="section-title">4. Performance Benchmark Results</h2>
        <div class="alert alert-info">
            <strong>Target:</strong> ≥50% improvement from UUID column filtering vs metadata JSONB filtering
        </div>
        <div class="table-responsive">
            <table class="table table-bordered table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Table</th>
                        <th>Old (JSONB) p50</th>
                        <th>New (UUID) p50</th>
                        <th>Improvement</th>
                        <th>Speedup</th>
                    </tr>
                </thead>
                <tbody>
                    {perf_rows}
                </tbody>
            </table>
        </div>

        <!-- Test Configuration -->
        <h2 class="section-title">5. Test Configuration</h2>
        <pre>{json.dumps({
            "test_id": report.test_id,
            "client_id": report.client_id,
            "case_id": report.case_id,
            "document_name": report.document_name,
            "start_time": report.start_time,
            "end_time": report.end_time
        }, indent=2)}</pre>

        <footer class="text-center mt-5 text-muted">
            <p>GraphRAG E2E Test Report - Generated by Luris Testing Framework</p>
        </footer>
    </div>
</body>
</html>
        """

        html_file.write_text(html_content)
        print(f"\n✅ HTML report saved: {html_file}")
        return html_file

    def generate_csv_report(self, report: E2ETestReport) -> Path:
        """
        Generate CSV report with metrics data.

        Args:
            report: E2E test report data

        Returns:
            Path to generated CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = self.output_dir / f"e2e_test_metrics_{timestamp}.csv"

        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(["GraphRAG E2E Test Metrics"])
            writer.writerow(["Test ID", report.test_id])
            writer.writerow(["Document", report.document_name])
            writer.writerow(["Duration (s)", report.duration_seconds])
            writer.writerow([])

            # Stage Results
            writer.writerow(["STAGE RESULTS"])
            writer.writerow(["Stage", "Name", "Status", "Passed", "Duration (s)", "Details"])
            for stage in report.stage_results:
                writer.writerow([
                    stage["stage_number"],
                    stage["stage_name"],
                    stage["status"],
                    "YES" if stage["passed"] else "NO",
                    f"{stage['duration_seconds']:.2f}",
                    stage.get("details", "")
                ])
            writer.writerow([])

            # Database Validation
            writer.writerow(["DATABASE VALIDATION"])
            writer.writerow(["Table", "Row Count", "Expected Min", "Passed", "Message"])
            for validation in report.database_validation.get("validations", []):
                writer.writerow([
                    validation["table"],
                    validation["row_count"],
                    validation["expected_min"],
                    "YES" if validation["passed"] else "NO",
                    validation["message"]
                ])
            writer.writerow([])

            # Performance Benchmark
            writer.writerow(["PERFORMANCE BENCHMARK"])
            writer.writerow(["Table", "Old (JSONB) p50 (ms)", "New (UUID) p50 (ms)", "Improvement (%)", "Speedup (x)"])
            for comparison in report.performance_benchmark.get("comparisons", []):
                writer.writerow([
                    comparison["table"],
                    f"{comparison['old_method'].p50_ms:.2f}",
                    f"{comparison['new_method'].p50_ms:.2f}",
                    f"{comparison['improvement_p50_pct']:.1f}",
                    f"{comparison['speedup_factor_p50']:.2f}"
                ])

        print(f"✅ CSV report saved: {csv_file}")
        return csv_file

    def generate_json_report(self, report: E2ETestReport) -> Path:
        """
        Generate JSON report with complete structured data.

        Args:
            report: E2E test report data

        Returns:
            Path to generated JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"e2e_test_data_{timestamp}.json"

        # Convert report to dict (handling nested dataclasses)
        report_dict = {
            "test_id": report.test_id,
            "start_time": report.start_time,
            "end_time": report.end_time,
            "duration_seconds": report.duration_seconds,
            "document_name": report.document_name,
            "client_id": report.client_id,
            "case_id": report.case_id,
            "service_health": report.service_health,
            "stage_results": report.stage_results,
            "database_validation": report.database_validation,
            "performance_benchmark": {
                **report.performance_benchmark,
                "comparisons": [
                    {
                        "table": c["table"],
                        "old_method": {
                            "p50_ms": c["old_method"].p50_ms,
                            "p95_ms": c["old_method"].p95_ms,
                            "p99_ms": c["old_method"].p99_ms,
                            "mean_ms": c["old_method"].mean_ms,
                        },
                        "new_method": {
                            "p50_ms": c["new_method"].p50_ms,
                            "p95_ms": c["new_method"].p95_ms,
                            "p99_ms": c["new_method"].p99_ms,
                            "mean_ms": c["new_method"].mean_ms,
                        },
                        "improvement_p50_pct": c["improvement_p50_pct"],
                        "improvement_p95_pct": c["improvement_p95_pct"],
                        "speedup_factor_p50": c["speedup_factor_p50"]
                    }
                    for c in report.performance_benchmark.get("comparisons", [])
                ]
            },
            "overall_status": report.overall_status,
            "total_stages": report.total_stages,
            "passed_stages": report.passed_stages,
            "failed_stages": report.failed_stages
        }

        json_file.write_text(json.dumps(report_dict, indent=2))
        print(f"✅ JSON report saved: {json_file}")
        return json_file

    def generate_all_reports(self, report: E2ETestReport) -> Dict[str, Path]:
        """
        Generate all report formats (HTML, CSV, JSON).

        Args:
            report: E2E test report data

        Returns:
            Dictionary mapping format to file path
        """
        print("\n" + "=" * 80)
        print("GENERATING REPORTS")
        print("=" * 80)

        html_file = self.generate_html_report(report)
        csv_file = self.generate_csv_report(report)
        json_file = self.generate_json_report(report)

        print("=" * 80)

        return {
            "html": html_file,
            "csv": csv_file,
            "json": json_file
        }
