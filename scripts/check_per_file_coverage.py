#!/usr/bin/env python3
"""Check per-file test coverage against a minimum threshold.

Parses coverage JSON report and fails if any file falls below
the configured minimum (default: 90%).

Usage:
    python scripts/check_per_file_coverage.py [--min-coverage 90] [--coverage-file coverage.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Files that are allowed to be below the threshold (with justification).
# Each entry maps a file path prefix to its allowed minimum.
EXEMPTIONS: dict[str, float] = {
    # CLI entry point — Click commands with rich output, error branches,
    # and optimize-descriptions flow require subprocess or complex mocking
    "forge_cli/main.py": 65,
    # Async LLM-dependent optimizer — requires real LLM or complex mocking;
    # pure utility functions are tested, async flow needs integration tests
    "forge_cli/evals/description_optimizer.py": 45,
    # LLM-dependent grading paths — deterministic grading fully tested,
    # LLM judge flow requires real llm-gateway provider
    "forge_cli/evals/grading.py": 80,
    # LLM client creation and LLM grading path in grade_file/run_eval
    "forge_cli/evals/eval_runner.py": 83,
    # Interactive wizard — prompt_toolkit flows hard to test without TTY
    "forge_cli/init_wizard.py": 85,
    # LLM-dependent refinement loop — score/refine with real LLM
    "forge_cli/generators/refinement.py": 88,
    # LLM-dependent context summarizer — summarization requires real LLM
    "forge_cli/generators/context_summarizer.py": 80,
}


def check_coverage(
    coverage_file: Path,
    min_coverage: float = 90.0,
) -> tuple[bool, list[str]]:
    """Check per-file coverage against threshold.

    Returns (all_passed, list of failure messages).
    """
    with open(coverage_file) as f:
        data = json.load(f)

    failures: list[str] = []
    files = data.get("files", {})

    for filepath, file_data in sorted(files.items()):
        summary = file_data.get("summary", {})
        percent = summary.get("percent_covered", 0)
        stmts = summary.get("num_statements", 0)

        # Skip files with zero statements (empty __init__.py, etc.)
        if stmts == 0:
            continue

        # Check for exemptions
        threshold = min_coverage
        for prefix, exempted_min in EXEMPTIONS.items():
            if filepath.startswith(prefix) or filepath == prefix:
                threshold = exempted_min
                break

        if percent < threshold:
            failures.append(
                f"  {filepath}: {percent:.1f}% (minimum: {threshold:.0f}%, "
                f"missing {summary.get('missing_lines', 0)} lines)"
            )

    return len(failures) == 0, failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Check per-file test coverage")
    parser.add_argument(
        "--min-coverage", type=float, default=90.0,
        help="Minimum coverage percentage per file (default: 90)",
    )
    parser.add_argument(
        "--coverage-file", type=Path, default=Path("coverage.json"),
        help="Path to coverage JSON report (default: coverage.json)",
    )
    args = parser.parse_args()

    if not args.coverage_file.exists():
        print(f"Coverage file not found: {args.coverage_file}")
        print("Run tests with: pytest --cov=forge_cli --cov-report=json")
        sys.exit(1)

    passed, failures = check_coverage(args.coverage_file, args.min_coverage)

    if not passed:
        print(f"Per-file coverage check FAILED ({len(failures)} files below {args.min_coverage}%):")
        print()
        for msg in failures:
            print(msg)
        print()
        print("Fix by adding tests or, if justified, add an exemption in")
        print("scripts/check_per_file_coverage.py::EXEMPTIONS")
        sys.exit(1)

    print(f"Per-file coverage check passed (all files >= {args.min_coverage}%)")


if __name__ == "__main__":
    main()
