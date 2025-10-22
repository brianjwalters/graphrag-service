"""
Example Usage: Test Results Visualization Tool

This script demonstrates how to use the TestResultsVisualizer
for analyzing API parity test results.

Usage:
    python example_visualization_usage.py
"""

from visualize_test_results import TestResultsVisualizer
from rich.console import Console
import pandas as pd


def example_basic_usage():
    """Basic usage: Load and display results"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Usage - Load and Display Results")
    print("="*70 + "\n")

    # Create visualizer (assumes results.json exists)
    try:
        viz = TestResultsVisualizer('results.json')

        # Display all visualizations
        viz.display_all()

    except FileNotFoundError:
        console = Console()
        console.print("[yellow]⚠[/yellow] results.json not found. Run tests first:")
        console.print("pytest tests/test_api_parity_real_data.py --json=results.json -v")


def example_export_reports():
    """Export markdown and JSON reports"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Export Reports")
    print("="*70 + "\n")

    try:
        viz = TestResultsVisualizer('results.json')

        # Export markdown report
        viz.export_markdown_report('api_parity_test_report.md')

        # Export JSON data
        viz.export_json('api_parity_test_data.json')

        console = Console()
        console.print("[green]✓[/green] Reports exported successfully")

    except FileNotFoundError:
        console = Console()
        console.print("[yellow]⚠[/yellow] results.json not found")


def example_individual_sections():
    """Display individual visualization sections"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Display Individual Sections")
    print("="*70 + "\n")

    try:
        viz = TestResultsVisualizer('results.json')

        # Display summary only
        print("\n--- Test Summary ---")
        viz.display_summary()

        # Display performance metrics only
        print("\n--- Performance Metrics ---")
        viz.display_performance_metrics()

        # Display quality metrics only
        print("\n--- Quality Metrics ---")
        viz.display_quality_metrics()

    except FileNotFoundError:
        console = Console()
        console.print("[yellow]⚠[/yellow] results.json not found")


def example_pandas_analysis():
    """Advanced analysis using pandas DataFrame"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Advanced Analysis with Pandas")
    print("="*70 + "\n")

    try:
        viz = TestResultsVisualizer('results.json')

        # Convert to DataFrame
        df = viz.to_dataframe()

        console = Console()
        console.print("[bold cyan]Test Results DataFrame:[/bold cyan]")
        print(df.head())

        # Analyze by category
        console.print("\n[bold cyan]Statistics by Category:[/bold cyan]")
        category_stats = df.groupby('category').agg({
            'duration': ['count', 'mean', 'sum', 'max'],
            'outcome': lambda x: (x == 'passed').sum()
        })
        category_stats.columns = ['Total Tests', 'Avg Duration', 'Total Duration', 'Max Duration', 'Passed']
        print(category_stats)

        # Find slowest tests
        console.print("\n[bold cyan]Top 5 Slowest Tests:[/bold cyan]")
        slowest = df.nlargest(5, 'duration')[['name', 'category', 'duration']]
        print(slowest)

        # Calculate pass rate by category
        console.print("\n[bold cyan]Pass Rate by Category:[/bold cyan]")
        pass_rates = df.groupby('category').apply(
            lambda x: (x['outcome'] == 'passed').sum() / len(x) * 100
        ).round(1)
        for category, rate in pass_rates.items():
            status = "✓" if rate >= 90 else "⚠" if rate >= 70 else "✗"
            console.print(f"{status} {category}: {rate}%")

        # Failed tests analysis
        failed_tests = df[df['outcome'] == 'failed']
        if len(failed_tests) > 0:
            console.print("\n[bold red]Failed Tests:[/bold red]")
            for _, test in failed_tests.iterrows():
                console.print(f"✗ {test['name']} ({test['category']}) - {test['duration']:.3f}s")
                if test['error']:
                    console.print(f"  Error: {test['error']}")
        else:
            console.print("\n[bold green]✓ No failed tests[/bold green]")

    except FileNotFoundError:
        console = Console()
        console.print("[yellow]⚠[/yellow] results.json not found")
    except Exception as e:
        console = Console()
        console.print(f"[red]✗[/red] Error: {e}")


def example_custom_analysis():
    """Custom analysis example: Performance trends"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Custom Performance Analysis")
    print("="*70 + "\n")

    try:
        viz = TestResultsVisualizer('results.json')
        df = viz.to_dataframe()

        console = Console()

        # Analyze test duration distribution
        console.print("[bold cyan]Test Duration Distribution:[/bold cyan]")
        duration_bins = [0, 0.1, 0.5, 1.0, 5.0, float('inf')]
        duration_labels = ['< 100ms', '100ms-500ms', '500ms-1s', '1s-5s', '> 5s']

        df['duration_category'] = pd.cut(df['duration'], bins=duration_bins, labels=duration_labels)
        duration_dist = df['duration_category'].value_counts().sort_index()

        for category, count in duration_dist.items():
            percentage = (count / len(df) * 100)
            bar = "█" * int(percentage / 2)
            console.print(f"{category:15s} │ {bar} {count} tests ({percentage:.1f}%)")

        # Category performance comparison
        console.print("\n[bold cyan]Category Performance Comparison:[/bold cyan]")
        category_perf = df.groupby('category').agg({
            'duration': ['mean', 'median', 'std', 'max']
        }).round(3)
        category_perf.columns = ['Mean', 'Median', 'StdDev', 'Max']

        for category in category_perf.index:
            stats = category_perf.loc[category]
            console.print(f"\n{category}:")
            console.print(f"  Mean: {stats['Mean']:.3f}s | Median: {stats['Median']:.3f}s")
            console.print(f"  StdDev: {stats['StdDev']:.3f}s | Max: {stats['Max']:.3f}s")

    except FileNotFoundError:
        console = Console()
        console.print("[yellow]⚠[/yellow] results.json not found")
    except Exception as e:
        console = Console()
        console.print(f"[red]✗[/red] Error: {e}")


def example_summary_metrics():
    """Display high-level summary metrics"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Summary Metrics and KPIs")
    print("="*70 + "\n")

    try:
        viz = TestResultsVisualizer('results.json')
        summary = viz.summary

        console = Console()

        # Overall KPIs
        console.print("[bold cyan]Key Performance Indicators:[/bold cyan]\n")

        pass_rate = (summary.passed / summary.total_tests * 100) if summary.total_tests > 0 else 0
        avg_duration = summary.total_duration / summary.total_tests if summary.total_tests > 0 else 0

        # Pass rate status
        if pass_rate >= 95:
            pass_status = "[green]Excellent[/green]"
        elif pass_rate >= 90:
            pass_status = "[green]Good[/green]"
        elif pass_rate >= 80:
            pass_status = "[yellow]Acceptable[/yellow]"
        else:
            pass_status = "[red]Needs Attention[/red]"

        console.print(f"  Pass Rate: {pass_rate:.1f}% - {pass_status}")
        console.print(f"  Total Tests: {summary.total_tests}")
        console.print(f"  Passed: [green]{summary.passed}[/green]")
        console.print(f"  Failed: [red]{summary.failed}[/red]")
        console.print(f"  Skipped: [yellow]{summary.skipped}[/yellow]")
        console.print(f"  Total Duration: {summary.total_duration:.2f}s")
        console.print(f"  Average Duration: {avg_duration:.3f}s per test")

        # Category summary
        console.print("\n[bold cyan]Category Summary:[/bold cyan]\n")
        for category in sorted(summary.categories.keys()):
            stats = summary.categories[category]
            cat_pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0

            if cat_pass_rate == 100:
                status = "[green]✓[/green]"
            elif cat_pass_rate >= 80:
                status = "[yellow]⚠[/yellow]"
            else:
                status = "[red]✗[/red]"

            console.print(f"{status} {category}: {stats['passed']}/{stats['total']} ({cat_pass_rate:.0f}%)")

    except FileNotFoundError:
        console = Console()
        console.print("[yellow]⚠[/yellow] results.json not found")
    except Exception as e:
        console = Console()
        console.print(f"[red]✗[/red] Error: {e}")


def main():
    """Run all examples"""
    console = Console()

    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Test Results Visualization Tool - Example Usage[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")

    console.print("[yellow]NOTE:[/yellow] These examples require results.json file.")
    console.print("Generate it by running:")
    console.print("  pytest tests/test_api_parity_real_data.py --json=results.json -v\n")

    # Run examples
    example_basic_usage()
    example_export_reports()
    example_individual_sections()
    example_pandas_analysis()
    example_custom_analysis()
    example_summary_metrics()

    console.print("\n[bold green]✓ All examples completed[/bold green]\n")


if __name__ == '__main__':
    main()
