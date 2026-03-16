"""Collect, store, and aggregate LLM feedback across E2E test runs.

Feeds findings back into forge skill/protocol improvement loop.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tests.e2e.tmux_helpers import SessionSnapshot
from tests.e2e.transcript_analyzer import AnalysisResult


@dataclass
class ImprovementReport:
    """Aggregated improvement suggestions from feedback analysis."""

    skill_changes: list[str] = field(default_factory=list)
    protocol_changes: list[str] = field(default_factory=list)
    eval_case_additions: list[str] = field(default_factory=list)
    overall_score: float = 0.0


class FeedbackCollector:
    """Collects, stores, and aggregates LLM feedback across E2E test runs."""

    def __init__(self, feedback_dir: Path):
        self.feedback_dir = feedback_dir
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def record_test_result(self, test_name: str, scenario: str,
                           analysis: AnalysisResult,
                           snapshot_before: SessionSnapshot,
                           snapshot_after: SessionSnapshot) -> None:
        """Record a single test result with full context."""
        result = {
            "test_name": test_name,
            "scenario": scenario,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "score": analysis.score,
            "findings": analysis.findings,
            "missed_checkpoints": analysis.missed_checkpoints,
            "suggestions": analysis.suggestions,
            "agents_before": list(snapshot_before.checkpoints.keys()),
            "agents_after": list(snapshot_after.checkpoints.keys()),
            "checkpoint_count_before": len(snapshot_before.checkpoint_files),
            "checkpoint_count_after": len(snapshot_after.checkpoint_files),
        }

        output_path = self.feedback_dir / f"{test_name}_{scenario}.json"
        output_path.write_text(json.dumps(result, indent=2))

    def load_history(self) -> list[dict]:
        """Load all historical feedback."""
        results: list[dict] = []
        for path in sorted(self.feedback_dir.glob("*.json")):
            try:
                results.append(json.loads(path.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def generate_improvement_report(self, llm_provider: Any) -> ImprovementReport:
        """Analyze all feedback and produce actionable improvement plan."""
        history = self.load_history()
        if not history:
            return ImprovementReport()

        all_findings = []
        total_score = 0
        for entry in history:
            all_findings.extend(entry.get("findings", []))
            total_score += entry.get("score", 0)

        avg_score = total_score / len(history) if history else 0

        return ImprovementReport(
            overall_score=avg_score,
            skill_changes=[f"Address: {f}" for f in all_findings[:10]],
        )

    def get_regression_candidates(self) -> list[str]:
        """Find scenarios that previously passed but now fail."""
        history = self.load_history()
        scenario_results: dict[str, list[int]] = {}
        for entry in history:
            scenario = entry.get("scenario", "")
            score = entry.get("score", 0)
            scenario_results.setdefault(scenario, []).append(score)

        regressions = []
        for scenario, scores in scenario_results.items():
            if len(scores) >= 2 and scores[-1] < scores[-2]:
                regressions.append(scenario)
        return regressions

    def get_flaky_scenarios(self) -> list[str]:
        """Find scenarios with inconsistent pass/fail across runs."""
        history = self.load_history()
        scenario_results: dict[str, list[bool]] = {}
        for entry in history:
            scenario = entry.get("scenario", "")
            passed = entry.get("score", 0) >= 70
            scenario_results.setdefault(scenario, []).append(passed)

        flaky = []
        for scenario, results in scenario_results.items():
            if len(results) >= 2 and len(set(results)) > 1:
                flaky.append(scenario)
        return flaky

    def record_compaction_result(
        self, test_name: str, scenario: str,
        analysis: AnalysisResult,
        snapshot_before: SessionSnapshot,
        snapshot_after: SessionSnapshot,
        compaction_count: int = 0,
        essential_files_count: int = 0,
        context_anchor_age: float = 0.0,
        markers_before: int = 0,
        markers_after: int = 0,
        events_count: int = 0,
    ) -> None:
        """Record a compaction test result with compaction-specific telemetry."""
        result = {
            "test_name": test_name,
            "scenario": scenario,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "score": analysis.score,
            "findings": analysis.findings,
            "missed_checkpoints": analysis.missed_checkpoints,
            "suggestions": analysis.suggestions,
            "agents_before": list(snapshot_before.checkpoints.keys()),
            "agents_after": list(snapshot_after.checkpoints.keys()),
            "checkpoint_count_before": len(snapshot_before.checkpoint_files),
            "checkpoint_count_after": len(snapshot_after.checkpoint_files),
            # Compaction-specific telemetry
            "compaction_count": compaction_count,
            "essential_files_count": essential_files_count,
            "context_anchor_age": context_anchor_age,
            "markers_before": markers_before,
            "markers_after": markers_after,
            "compaction_events_count": events_count,
        }

        output_path = self.feedback_dir / f"{test_name}_{scenario}.json"
        output_path.write_text(json.dumps(result, indent=2))

    def export_metrics(self) -> dict:
        """Export aggregate metrics."""
        history = self.load_history()
        if not history:
            return {"total_tests": 0}

        scores = [e.get("score", 0) for e in history]
        return {
            "total_tests": len(history),
            "avg_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "scenarios": list({e.get("scenario", "") for e in history}),
        }
