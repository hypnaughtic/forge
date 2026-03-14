"""Eval-driven quality framework for Forge generated files.

Defines assertions, eval cases, and grading results for evaluating
generated agent/skill/config files against quality criteria.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CheckType(str, Enum):
    """Types of assertion checks."""

    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    SECTION_PRESENT = "section_present"
    FRONTMATTER_FIELD = "frontmatter_field"
    CONFIG_FIDELITY = "config_fidelity"
    LLM_JUDGE = "llm_judge"


class Assertion(BaseModel):
    """A single quality assertion against a generated file."""

    text: str  # Human-readable description, e.g. "backend-developer.md references FastAPI"
    check_type: CheckType
    value: str  # Pattern, section name, field name, or judge instruction
    weight: float = 1.0


class EvalCase(BaseModel):
    """An evaluation case targeting a specific generated file."""

    id: str  # e.g. "agent:backend-developer:cli-framework-ref"
    file_path: str  # Relative path, e.g. ".claude/agents/backend-developer.md"
    file_type: str  # "agent" | "skill" | "claude_md" | "team_init_plan"
    description: str  # Human-readable description
    assertions: list[Assertion]
    applicable_when: dict[str, Any] = Field(default_factory=dict)
    # Config predicates: {"is_cli_project": True, "has_web_backend": False}


class Expectation(BaseModel):
    """Result of evaluating a single assertion."""

    text: str  # The assertion text
    passed: bool
    evidence: str  # Why it passed/failed


class GradingResult(BaseModel):
    """Grading result for a single file."""

    file_path: str
    expectations: list[Expectation] = Field(default_factory=list)
    pass_rate: float = 0.0
    llm_cost_usd: float = 0.0

    def compute_pass_rate(self) -> None:
        """Compute weighted pass rate from expectations."""
        if not self.expectations:
            self.pass_rate = 0.0
            return
        passed = sum(1 for e in self.expectations if e.passed)
        self.pass_rate = passed / len(self.expectations)


class EvalReport(BaseModel):
    """Complete evaluation report across all files."""

    config_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    files: list[GradingResult] = Field(default_factory=list)
    overall_pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    duration_seconds: float = 0.0

    def compute_overall_pass_rate(self) -> None:
        """Compute overall pass rate across all files."""
        if not self.files:
            self.overall_pass_rate = 0.0
            return
        total = sum(len(f.expectations) for f in self.files)
        passed = sum(
            sum(1 for e in f.expectations if e.passed)
            for f in self.files
        )
        self.overall_pass_rate = passed / total if total > 0 else 0.0


class BenchmarkEntry(BaseModel):
    """Per-file benchmark entry."""

    file_path: str
    file_type: str
    pass_rate: float
    total_assertions: int
    passed_assertions: int
    failed_assertions: list[str] = Field(default_factory=list)


class BenchmarkSummary(BaseModel):
    """Aggregate benchmark statistics."""

    total_files: int = 0
    total_assertions: int = 0
    total_passed: int = 0
    avg_pass_rate: float = 0.0
    min_pass_rate: float = 0.0
    max_pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    duration_seconds: float = 0.0


class BenchmarkComparison(BaseModel):
    """Delta comparison between benchmark runs."""

    previous_avg_pass_rate: float = 0.0
    current_avg_pass_rate: float = 0.0
    delta: float = 0.0
    improved_files: list[str] = Field(default_factory=list)
    regressed_files: list[str] = Field(default_factory=list)


class BenchmarkReport(BaseModel):
    """Complete benchmark report for a quality case."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    config_name: str = ""
    entries: list[BenchmarkEntry] = Field(default_factory=list)
    summary: BenchmarkSummary = Field(default_factory=BenchmarkSummary)
    comparison: BenchmarkComparison | None = None
