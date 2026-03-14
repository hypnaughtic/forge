"""Benchmark aggregation and comparison for eval reports.

Aggregates eval results into benchmark reports, compares runs,
and saves results as JSON + Markdown for review.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from forge_cli.evals import (
    BenchmarkComparison,
    BenchmarkEntry,
    BenchmarkReport,
    BenchmarkSummary,
    EvalReport,
)

logger = logging.getLogger(__name__)


def aggregate_benchmark(
    eval_report: EvalReport,
    config_name: str = "",
) -> BenchmarkReport:
    """Convert an EvalReport into a BenchmarkReport with summary stats."""
    entries: list[BenchmarkEntry] = []

    for file_result in eval_report.files:
        passed = sum(1 for e in file_result.expectations if e.passed)
        failed = [
            e.text for e in file_result.expectations if not e.passed
        ]
        total = len(file_result.expectations)

        # Determine file type from path
        file_type = "unknown"
        if ".claude/agents/" in file_result.file_path:
            file_type = "agent"
        elif ".claude/skills/" in file_result.file_path:
            file_type = "skill"
        elif file_result.file_path == "CLAUDE.md":
            file_type = "claude_md"
        elif file_result.file_path == "team-init-plan.md":
            file_type = "team_init_plan"

        entries.append(BenchmarkEntry(
            file_path=file_result.file_path,
            file_type=file_type,
            pass_rate=file_result.pass_rate,
            total_assertions=total,
            passed_assertions=passed,
            failed_assertions=failed,
        ))

    # Compute summary
    pass_rates = [e.pass_rate for e in entries] if entries else [0.0]
    total_assertions = sum(e.total_assertions for e in entries)
    total_passed = sum(e.passed_assertions for e in entries)

    summary = BenchmarkSummary(
        total_files=len(entries),
        total_assertions=total_assertions,
        total_passed=total_passed,
        avg_pass_rate=sum(pass_rates) / len(pass_rates) if pass_rates else 0.0,
        min_pass_rate=min(pass_rates) if pass_rates else 0.0,
        max_pass_rate=max(pass_rates) if pass_rates else 0.0,
        total_cost_usd=eval_report.total_cost_usd,
        duration_seconds=eval_report.duration_seconds,
    )

    return BenchmarkReport(
        config_name=config_name or eval_report.config_name,
        entries=entries,
        summary=summary,
    )


def compare_benchmarks(
    current: BenchmarkReport,
    previous_path: Path | None = None,
) -> BenchmarkReport:
    """Compare current benchmark with a previous run.

    If previous_path points to a benchmark.json, loads it and computes deltas.
    Modifies current.comparison in place and returns it.
    """
    if previous_path is None or not previous_path.exists():
        return current

    try:
        prev_data = json.loads(previous_path.read_text())
        prev_avg = prev_data.get("summary", {}).get("avg_pass_rate", 0.0)
        prev_entries = {
            e["file_path"]: e["pass_rate"]
            for e in prev_data.get("entries", [])
        }
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to load previous benchmark: %s", e)
        return current

    improved = []
    regressed = []
    for entry in current.entries:
        prev_rate = prev_entries.get(entry.file_path)
        if prev_rate is not None:
            if entry.pass_rate > prev_rate:
                improved.append(entry.file_path)
            elif entry.pass_rate < prev_rate:
                regressed.append(entry.file_path)

    current.comparison = BenchmarkComparison(
        previous_avg_pass_rate=prev_avg,
        current_avg_pass_rate=current.summary.avg_pass_rate,
        delta=current.summary.avg_pass_rate - prev_avg,
        improved_files=improved,
        regressed_files=regressed,
    )

    return current


def save_benchmark(
    report: BenchmarkReport,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Save benchmark report as JSON and Markdown.

    Returns (json_path, md_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = output_dir / "benchmark.json"
    json_path.write_text(report.model_dump_json(indent=2))

    # Markdown report
    md_path = output_dir / "benchmark.md"
    md_content = _render_markdown(report)
    md_path.write_text(md_content)

    return json_path, md_path


def _render_markdown(report: BenchmarkReport) -> str:
    """Render benchmark report as readable Markdown."""
    lines = [
        f"# Benchmark Report: {report.config_name}",
        f"",
        f"**Generated:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total files | {report.summary.total_files} |",
        f"| Total assertions | {report.summary.total_assertions} |",
        f"| Passed assertions | {report.summary.total_passed} |",
        f"| Average pass rate | {report.summary.avg_pass_rate:.1%} |",
        f"| Min pass rate | {report.summary.min_pass_rate:.1%} |",
        f"| Max pass rate | {report.summary.max_pass_rate:.1%} |",
        f"| Total cost | ${report.summary.total_cost_usd:.4f} |",
        f"| Duration | {report.summary.duration_seconds:.1f}s |",
        f"",
    ]

    if report.comparison:
        c = report.comparison
        direction = "improved" if c.delta >= 0 else "regressed"
        lines.extend([
            f"## Comparison with Previous Run",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Previous avg | {c.previous_avg_pass_rate:.1%} |",
            f"| Current avg | {c.current_avg_pass_rate:.1%} |",
            f"| Delta | {c.delta:+.1%} ({direction}) |",
            f"| Improved files | {len(c.improved_files)} |",
            f"| Regressed files | {len(c.regressed_files)} |",
            f"",
        ])
        if c.regressed_files:
            lines.append("### Regressed Files")
            lines.append("")
            for f in c.regressed_files:
                lines.append(f"- {f}")
            lines.append("")

    lines.extend([
        f"## Per-File Results",
        f"",
        f"| File | Type | Pass Rate | Passed | Total | Failed Assertions |",
        f"|------|------|-----------|--------|-------|-------------------|",
    ])

    for entry in sorted(report.entries, key=lambda e: e.pass_rate):
        failed_str = ", ".join(entry.failed_assertions[:3])
        if len(entry.failed_assertions) > 3:
            failed_str += f" (+{len(entry.failed_assertions) - 3} more)"
        lines.append(
            f"| {entry.file_path} | {entry.file_type} "
            f"| {entry.pass_rate:.0%} | {entry.passed_assertions} "
            f"| {entry.total_assertions} | {failed_str} |"
        )

    lines.append("")
    return "\n".join(lines)
