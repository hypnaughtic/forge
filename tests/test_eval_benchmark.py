"""Benchmark tests — run full eval suite against all quality cases.

These tests are designed to run with FORGE_TEST_DRY_RUN=0 for real LLM grading,
but also support dry-run mode for CI with deterministic-only checks.

Usage:
    # Fast (deterministic only, CI-safe):
    pytest tests/test_eval_benchmark.py -v

    # Full (real LLM grading via local_claude):
    FORGE_TEST_DRY_RUN=0 pytest tests/test_eval_benchmark.py -v --timeout=1800
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from forge_cli.config_loader import load_config
from forge_cli.config_schema import ForgeConfig
from forge_cli.evals.benchmark import aggregate_benchmark, save_benchmark
from forge_cli.evals.eval_runner import run_eval
from forge_cli.generators.orchestrator import generate_all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_QUALITY_CASES_DIR = Path(__file__).parent / "quality_cases"


def _find_quality_cases() -> list[Path]:
    """Find all quality case config files."""
    cases = []
    if _QUALITY_CASES_DIR.exists():
        for d in sorted(_QUALITY_CASES_DIR.iterdir()):
            cfg = d / "forge-config.yaml"
            if cfg.exists():
                cases.append(cfg)
    return cases


def _is_dry_run() -> bool:
    return os.environ.get("FORGE_TEST_DRY_RUN", "1") == "1"


def _case_id(path: Path) -> str:
    return path.parent.name


# ---------------------------------------------------------------------------
# Parametrized tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "config_path",
    _find_quality_cases(),
    ids=[_case_id(p) for p in _find_quality_cases()],
)
class TestQualityCaseEval:
    """Run eval suite against each quality case."""

    def test_eval_pass_rate(self, tmp_path: Path, config_path: Path):
        """Generate files and evaluate with deterministic assertions.

        In dry-run mode (default), only deterministic checks run.
        With FORGE_TEST_DRY_RUN=0, LLM grading is also enabled.
        """
        os.environ.setdefault("FORGE_TEST_DRY_RUN", "1")

        config = load_config(str(config_path))
        config.project.directory = str(tmp_path)

        # Generate files
        generate_all(config)

        # Run eval
        use_llm = not _is_dry_run()
        report = run_eval(tmp_path, config, use_llm=use_llm)

        assert len(report.files) > 0, "No files were evaluated"

        # Save benchmark in quality case directory
        benchmark = aggregate_benchmark(report, config_name=config_path.parent.name)
        save_benchmark(benchmark, config_path.parent)

        # Assert minimum pass rates per file
        for file_result in report.files:
            # Minimum threshold: 60% for deterministic, 70% for LLM
            min_rate = 0.60 if _is_dry_run() else 0.70
            assert file_result.pass_rate >= min_rate, (
                f"{file_result.file_path}: pass_rate={file_result.pass_rate:.0%}\n"
                f"Failed: {[e.text for e in file_result.expectations if not e.passed]}"
            )

    def test_overall_pass_rate(self, tmp_path: Path, config_path: Path):
        """Overall pass rate should be above minimum threshold."""
        os.environ.setdefault("FORGE_TEST_DRY_RUN", "1")

        config = load_config(str(config_path))
        config.project.directory = str(tmp_path)
        generate_all(config)

        report = run_eval(tmp_path, config, use_llm=False)

        min_rate = 0.65
        assert report.overall_pass_rate >= min_rate, (
            f"Overall pass rate {report.overall_pass_rate:.0%} < {min_rate:.0%}\n"
            f"Worst files: {sorted(report.files, key=lambda f: f.pass_rate)[:3]}"
        )


@pytest.mark.parametrize(
    "config_path",
    _find_quality_cases(),
    ids=[_case_id(p) for p in _find_quality_cases()],
)
class TestEvalConsistency:
    """Verify eval consistency properties."""

    def test_no_duplicate_expectations(self, tmp_path: Path, config_path: Path):
        """Each file should not have duplicate expectation texts."""
        os.environ.setdefault("FORGE_TEST_DRY_RUN", "1")

        config = load_config(str(config_path))
        config.project.directory = str(tmp_path)
        generate_all(config)

        report = run_eval(tmp_path, config, use_llm=False)

        for file_result in report.files:
            texts = [e.text for e in file_result.expectations]
            assert len(texts) == len(set(texts)), (
                f"{file_result.file_path} has duplicate expectations: "
                f"{[t for t in texts if texts.count(t) > 1]}"
            )

    def test_applicable_cases_match_generated_files(self, tmp_path: Path, config_path: Path):
        """All evaluated files actually exist in the generated project."""
        os.environ.setdefault("FORGE_TEST_DRY_RUN", "1")

        config = load_config(str(config_path))
        config.project.directory = str(tmp_path)
        generate_all(config)

        report = run_eval(tmp_path, config, use_llm=False)

        for file_result in report.files:
            full_path = tmp_path / file_result.file_path
            assert full_path.exists(), (
                f"Evaluated file does not exist: {file_result.file_path}"
            )
