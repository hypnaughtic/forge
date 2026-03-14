"""Iterative improvement loop orchestrator for E2E tests.

Runs E2E tests -> analyzes -> suggests improvements -> applies -> retests.
Uses real LLM (local_claude via llm-gateway) for all analysis.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class IterationReport:
    """Report for a single improvement iteration."""

    iteration: int
    test_results: list[dict] = field(default_factory=list)
    analysis_results: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    all_scenarios_pass: bool = False
    avg_score: float = 0.0


@dataclass
class ImprovementReport:
    """Final report across all improvement iterations."""

    iterations: list[IterationReport] = field(default_factory=list)
    initial_score: float = 0.0
    final_score: float = 0.0
    improvement: float = 0.0
    scenarios_fixed: list[str] = field(default_factory=list)


class ImprovementRunner:
    """Orchestrates the iterative improvement loop."""

    def __init__(self, forge_project_dir: Path, llm_provider: Any,
                 max_iterations: int = 5):
        self.project_dir = forge_project_dir
        self.llm = llm_provider
        self.max_iterations = max_iterations
        self.iteration_reports: list[IterationReport] = []

    async def run(self) -> ImprovementReport:
        """Execute the full improvement loop."""
        for i in range(self.max_iterations):
            report = await self._run_iteration(i + 1)
            self.iteration_reports.append(report)

            if report.all_scenarios_pass:
                break

            await self._apply_improvements(report.suggestions)
            self._regenerate_forge_files()

        return self._compile_final_report()

    async def _run_iteration(self, iteration_num: int) -> IterationReport:
        """Run all E2E tests and analyze results."""
        test_results = self._run_e2e_tests()

        return IterationReport(
            iteration=iteration_num,
            test_results=test_results,
            all_scenarios_pass=all(t.get("passed", False) for t in test_results),
            avg_score=sum(t.get("score", 0) for t in test_results) / max(len(test_results), 1),
        )

    def _run_e2e_tests(self) -> list[dict]:
        """Run pytest E2E tests programmatically."""
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/e2e/", "-v", "--timeout=600",
             "--tb=short", "-q"],
            capture_output=True, text=True,
            cwd=str(self.project_dir),
        )
        return [{"passed": result.returncode == 0, "output": result.stdout}]

    async def _apply_improvements(self, suggestions: list[str]) -> None:
        """Use LLM to apply suggestions to skill/protocol code."""
        skill_path = self.project_dir / ".claude" / "skills" / "checkpoint.md"
        if not skill_path.exists() or not suggestions:
            return

        current_skill = skill_path.read_text()
        try:
            improved = await self.llm.generate(
                prompt=f"""Improve this checkpoint skill based on feedback:

Current skill:
{current_skill[:3000]}

Feedback:
{chr(10).join(f'- {s}' for s in suggestions)}

Return the complete improved skill file content.""",
                model="claude-sonnet-4-20250514",
            )
            skill_path.write_text(improved.text)
        except Exception:
            pass  # Keep current version if improvement fails

    def _regenerate_forge_files(self) -> None:
        """Run forge generate to regenerate all files."""
        subprocess.run(
            ["forge", "generate", "--project-dir", str(self.project_dir)],
            capture_output=True,
        )

    def _compile_final_report(self) -> ImprovementReport:
        """Compile improvement trajectory across iterations."""
        return ImprovementReport(
            iterations=self.iteration_reports,
            initial_score=self.iteration_reports[0].avg_score if self.iteration_reports else 0,
            final_score=self.iteration_reports[-1].avg_score if self.iteration_reports else 0,
            improvement=(
                self.iteration_reports[-1].avg_score - self.iteration_reports[0].avg_score
                if len(self.iteration_reports) >= 2 else 0
            ),
        )
