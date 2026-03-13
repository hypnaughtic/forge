"""Tests for the eval framework — models, grading, runner, benchmark."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from forge_cli.config_schema import (
    AgentsConfig,
    AtlassianConfig,
    ForgeConfig,
    LLMGatewayConfig,
    ProjectConfig,
    ProjectMode,
    RefinementConfig,
    TechStack,
    TeamProfile,
)
from forge_cli.evals import (
    Assertion,
    BenchmarkReport,
    CheckType,
    EvalCase,
    EvalReport,
    Expectation,
    GradingResult,
)
from forge_cli.evals.eval_cases import get_all_eval_cases
from forge_cli.evals.eval_runner import (
    _check_applicable,
    grade_file,
    run_eval,
    split_eval_cases,
)
from forge_cli.evals.grading import (
    _check_config_fidelity,
    _check_contains,
    _check_frontmatter_field,
    _check_not_contains,
    _check_regex,
    _check_section_present,
    deterministic_grade,
)
from forge_cli.evals.benchmark import (
    aggregate_benchmark,
    compare_benchmarks,
    save_benchmark,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> ForgeConfig:
    """Create a ForgeConfig with sensible defaults."""
    kwargs = {
        "project": ProjectConfig(
            description="E-commerce API with React frontend",
            requirements="Build a REST API with product catalog",
        ),
        "mode": ProjectMode.MVP,
        "tech_stack": TechStack(
            languages=["python", "typescript"],
            frameworks=["fastapi", "react"],
            databases=["postgresql"],
        ),
        "atlassian": AtlassianConfig(enabled=False),
        "agents": AgentsConfig(team_profile=TeamProfile.LEAN),
        "llm_gateway": LLMGatewayConfig(enabled=True),
    }
    kwargs.update(overrides)
    return ForgeConfig(**kwargs)


def _make_cli_config() -> ForgeConfig:
    return _make_config(
        project=ProjectConfig(
            description="CLI data pipeline tool",
            requirements="Build a CLI tool with Click",
        ),
        tech_stack=TechStack(
            languages=["python"],
            frameworks=["click"],
        ),
    )


# ---------------------------------------------------------------------------
# Deterministic grading tests
# ---------------------------------------------------------------------------

class TestDeterministicGrading:
    """Tests for deterministic assertion checks."""

    def test_contains_pass(self):
        passed, evidence = _check_contains("Hello World", "hello")
        assert passed
        assert "Found" in evidence

    def test_contains_fail(self):
        passed, evidence = _check_contains("Hello World", "goodbye")
        assert not passed
        assert "not found" in evidence

    def test_not_contains_pass(self):
        passed, evidence = _check_not_contains("Hello World", "goodbye")
        assert passed

    def test_not_contains_fail(self):
        passed, evidence = _check_not_contains("Hello World", "hello")
        assert not passed

    def test_regex_pass(self):
        passed, evidence = _check_regex("Score: 95%", r"\d+%")
        assert passed
        assert "matched" in evidence

    def test_regex_fail(self):
        passed, evidence = _check_regex("Hello World", r"\d+%")
        assert not passed

    def test_regex_invalid(self):
        passed, evidence = _check_regex("text", "[invalid")
        assert not passed
        assert "Invalid regex" in evidence

    def test_section_present_pass(self):
        content = "# Header\n\n## Base Protocol\n\nSome content"
        passed, evidence = _check_section_present(content, "Base Protocol")
        assert passed

    def test_section_present_fail(self):
        content = "# Header\n\nSome content"
        passed, evidence = _check_section_present(content, "Base Protocol")
        assert not passed

    def test_section_present_different_level(self):
        content = "### Base Protocol\n\nContent"
        passed, evidence = _check_section_present(content, "Base Protocol")
        assert passed

    def test_frontmatter_field_pass(self):
        content = "---\nname: smoke-test\ndescription: Run tests\n---\n\nBody"
        passed, evidence = _check_frontmatter_field(content, "name")
        assert passed

    def test_frontmatter_field_fail(self):
        content = "---\nname: test\n---\n\nBody"
        passed, evidence = _check_frontmatter_field(content, "description")
        assert not passed

    def test_frontmatter_no_block(self):
        content = "No frontmatter here"
        passed, evidence = _check_frontmatter_field(content, "name")
        assert not passed
        assert "No YAML frontmatter" in evidence

    def test_config_fidelity_mode_match(self):
        config = _make_config()
        content = "This project uses mvp mode for fast delivery."
        passed, evidence = _check_config_fidelity(content, "mode=mvp", config)
        assert passed

    def test_config_fidelity_mode_mismatch(self):
        config = _make_config()
        content = "This project uses strict mode."
        passed, evidence = _check_config_fidelity(content, "mode=production-ready", config)
        assert not passed

    def test_config_fidelity_list_check(self):
        config = _make_config()
        content = "Languages: python, typescript. Frameworks: fastapi, react."
        passed, evidence = _check_config_fidelity(
            content, "tech_stack.languages", config,
        )
        assert passed

    def test_config_fidelity_list_missing(self):
        config = _make_config()
        content = "Languages: java, go, rust."
        passed, evidence = _check_config_fidelity(
            content, "tech_stack.languages", config,
        )
        assert not passed
        assert "missing" in evidence.lower()

    def test_deterministic_grade_full(self):
        config = _make_config()
        content = "## Base Protocol\n\nThis uses fastapi and react in mvp mode."
        assertions = [
            Assertion(text="Base Protocol present", check_type=CheckType.SECTION_PRESENT, value="Base Protocol"),
            Assertion(text="Contains fastapi", check_type=CheckType.CONTAINS, value="fastapi"),
            Assertion(text="No PCI-DSS", check_type=CheckType.NOT_CONTAINS, value="PCI-DSS"),
            Assertion(text="LLM check", check_type=CheckType.LLM_JUDGE, value="Is it good?"),
        ]
        results = deterministic_grade(content, "test.md", assertions, config)
        # Should skip LLM_JUDGE, process 3 deterministic
        assert len(results) == 3
        assert all(e.passed for e in results)


# ---------------------------------------------------------------------------
# Eval case applicability tests
# ---------------------------------------------------------------------------

class TestApplicability:
    """Tests for eval case applicability predicates."""

    def test_no_predicates(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
        )
        assert _check_applicable(case, _make_config())

    def test_cli_project_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"is_cli_project": True},
        )
        assert _check_applicable(case, _make_cli_config())
        assert not _check_applicable(case, _make_config())

    def test_web_backend_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"has_web_backend": True},
        )
        config = _make_config()
        assert _check_applicable(case, config)

    def test_atlassian_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"atlassian_enabled": True},
        )
        assert not _check_applicable(case, _make_config())
        assert _check_applicable(
            case, _make_config(atlassian=AtlassianConfig(enabled=True)),
        )

    def test_non_negotiables_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"has_non_negotiables": True},
        )
        assert not _check_applicable(case, _make_config())
        assert _check_applicable(
            case, _make_config(non_negotiables=["No mocks in integration"]),
        )

    def test_agent_in_roster_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"agent_in_roster": "security-tester"},
        )
        # Lean profile doesn't have security-tester
        assert not _check_applicable(case, _make_config())

    def test_multiple_predicates(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={
                "has_web_backend": True,
                "has_databases": True,
            },
        )
        assert _check_applicable(case, _make_config())

    def test_mode_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"mode": "mvp"},
        )
        assert _check_applicable(case, _make_config())
        assert not _check_applicable(
            case, _make_config(mode=ProjectMode.NO_COMPROMISE),
        )


# ---------------------------------------------------------------------------
# Train/test split tests
# ---------------------------------------------------------------------------

class TestTrainTestSplit:
    """Tests for deterministic eval case splitting."""

    def test_split_deterministic(self):
        """Same input always produces same split."""
        cases = [
            EvalCase(
                id=f"case-{i}", file_path="f.md", file_type="agent",
                description=f"Case {i}", assertions=[],
            )
            for i in range(20)
        ]
        train1, test1 = split_eval_cases(cases, ratio=0.6)
        train2, test2 = split_eval_cases(cases, ratio=0.6)

        assert [c.id for c in train1] == [c.id for c in train2]
        assert [c.id for c in test1] == [c.id for c in test2]

    def test_split_ratio_approximate(self):
        """Split ratio is approximately correct for large sets."""
        cases = [
            EvalCase(
                id=f"case-{i}", file_path="f.md", file_type="agent",
                description=f"Case {i}", assertions=[],
            )
            for i in range(100)
        ]
        train, test = split_eval_cases(cases, ratio=0.6)
        # Allow generous margin for hash-based split
        assert 40 <= len(train) <= 80
        assert 20 <= len(test) <= 60
        assert len(train) + len(test) == 100

    def test_split_no_overlap(self):
        """Train and test sets don't overlap."""
        cases = [
            EvalCase(
                id=f"case-{i}", file_path="f.md", file_type="agent",
                description=f"Case {i}", assertions=[],
            )
            for i in range(50)
        ]
        train, test = split_eval_cases(cases)
        train_ids = {c.id for c in train}
        test_ids = {c.id for c in test}
        assert train_ids.isdisjoint(test_ids)


# ---------------------------------------------------------------------------
# Eval registry tests
# ---------------------------------------------------------------------------

class TestEvalRegistry:
    """Tests for the eval case registry."""

    def test_registry_has_many_cases(self):
        """Registry should have 200+ eval cases."""
        cases = get_all_eval_cases()
        assert len(cases) >= 200

    def test_all_cases_have_assertions(self):
        """Every eval case has at least one assertion."""
        for case in get_all_eval_cases():
            assert len(case.assertions) >= 1, f"Case {case.id} has no assertions"

    def test_unique_case_ids(self):
        """All case IDs are unique."""
        cases = get_all_eval_cases()
        ids = [c.id for c in cases]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found"

    def test_file_types_valid(self):
        """All file types are recognized."""
        valid_types = {"agent", "skill", "claude_md", "team_init_plan"}
        for case in get_all_eval_cases():
            assert case.file_type in valid_types, (
                f"Case {case.id} has invalid file_type: {case.file_type}"
            )

    def test_agent_cases_cover_core_agents(self):
        """Registry has cases for all core agent types."""
        cases = get_all_eval_cases()
        agent_files = {
            c.file_path for c in cases if c.file_type == "agent"
        }
        core_agents = [
            "team-leader", "backend-developer", "architect",
            "qa-engineer", "devops-specialist", "critic",
        ]
        for agent in core_agents:
            expected = f".claude/agents/{agent}.md"
            assert expected in agent_files, f"No cases for {agent}"

    def test_skill_cases_cover_core_skills(self):
        """Registry has cases for core skills."""
        cases = get_all_eval_cases()
        skill_files = {
            c.file_path for c in cases if c.file_type == "skill"
        }
        core_skills = [
            "smoke-test", "create-pr", "release",
            "screenshot-review", "code-review",
        ]
        for skill in core_skills:
            expected = f".claude/skills/{skill}.md"
            assert expected in skill_files, f"No cases for {skill}"

    def test_root_files_covered(self):
        """Registry has cases for CLAUDE.md and team-init-plan.md."""
        cases = get_all_eval_cases()
        root_files = {c.file_path for c in cases if c.file_type in ("claude_md", "team_init_plan")}
        assert "CLAUDE.md" in root_files
        assert "team-init-plan.md" in root_files

    def test_cases_per_file_minimum(self):
        """Each file in the registry has at least 3 eval cases."""
        cases = get_all_eval_cases()
        file_case_counts: dict[str, int] = {}
        for case in cases:
            file_case_counts[case.file_path] = file_case_counts.get(case.file_path, 0) + 1

        for fp, count in file_case_counts.items():
            assert count >= 3, f"{fp} has only {count} cases (minimum 3)"


# ---------------------------------------------------------------------------
# GradingResult tests
# ---------------------------------------------------------------------------

class TestGradingResult:

    def test_compute_pass_rate(self):
        result = GradingResult(
            file_path="test.md",
            expectations=[
                Expectation(text="a", passed=True, evidence="ok"),
                Expectation(text="b", passed=False, evidence="fail"),
                Expectation(text="c", passed=True, evidence="ok"),
            ],
        )
        result.compute_pass_rate()
        assert abs(result.pass_rate - 2 / 3) < 0.001

    def test_compute_pass_rate_empty(self):
        result = GradingResult(file_path="test.md")
        result.compute_pass_rate()
        assert result.pass_rate == 0.0


# ---------------------------------------------------------------------------
# EvalReport tests
# ---------------------------------------------------------------------------

class TestEvalReport:

    def test_compute_overall_pass_rate(self):
        report = EvalReport(
            files=[
                GradingResult(
                    file_path="a.md",
                    expectations=[
                        Expectation(text="a", passed=True, evidence=""),
                        Expectation(text="b", passed=True, evidence=""),
                    ],
                    pass_rate=1.0,
                ),
                GradingResult(
                    file_path="b.md",
                    expectations=[
                        Expectation(text="c", passed=True, evidence=""),
                        Expectation(text="d", passed=False, evidence=""),
                    ],
                    pass_rate=0.5,
                ),
            ],
        )
        report.compute_overall_pass_rate()
        assert abs(report.overall_pass_rate - 0.75) < 0.001

    def test_compute_overall_empty(self):
        report = EvalReport()
        report.compute_overall_pass_rate()
        assert report.overall_pass_rate == 0.0


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------

class TestBenchmark:

    def _make_report(self) -> EvalReport:
        return EvalReport(
            config_name="test",
            files=[
                GradingResult(
                    file_path=".claude/agents/backend-developer.md",
                    expectations=[
                        Expectation(text="a", passed=True, evidence="ok"),
                        Expectation(text="b", passed=False, evidence="fail"),
                    ],
                    pass_rate=0.5,
                ),
                GradingResult(
                    file_path="CLAUDE.md",
                    expectations=[
                        Expectation(text="c", passed=True, evidence="ok"),
                    ],
                    pass_rate=1.0,
                ),
            ],
            overall_pass_rate=0.67,
            total_cost_usd=0.01,
            duration_seconds=5.0,
        )

    def test_aggregate_benchmark(self):
        report = self._make_report()
        benchmark = aggregate_benchmark(report, "test-config")

        assert benchmark.config_name == "test-config"
        assert len(benchmark.entries) == 2
        assert benchmark.summary.total_files == 2
        assert benchmark.summary.total_assertions == 3
        assert benchmark.summary.total_passed == 2
        assert benchmark.summary.min_pass_rate == 0.5
        assert benchmark.summary.max_pass_rate == 1.0

    def test_save_benchmark(self, tmp_path):
        report = self._make_report()
        benchmark = aggregate_benchmark(report, "test-config")
        json_path, md_path = save_benchmark(benchmark, tmp_path)

        assert json_path.exists()
        assert md_path.exists()

        # Verify JSON is valid
        data = json.loads(json_path.read_text())
        assert data["config_name"] == "test-config"
        assert len(data["entries"]) == 2

        # Verify Markdown has content
        md_content = md_path.read_text()
        assert "# Benchmark Report" in md_content
        assert "test-config" in md_content

    def test_compare_benchmarks(self, tmp_path):
        report = self._make_report()
        benchmark = aggregate_benchmark(report, "test-config")

        # Save as "previous"
        save_benchmark(benchmark, tmp_path)

        # Create a "current" with different rates
        for entry in benchmark.entries:
            entry.pass_rate += 0.1
        benchmark.summary.avg_pass_rate += 0.1

        current = compare_benchmarks(benchmark, tmp_path / "benchmark.json")
        assert current.comparison is not None
        assert current.comparison.delta > 0

    def test_compare_no_previous(self, tmp_path):
        report = self._make_report()
        benchmark = aggregate_benchmark(report, "test-config")
        result = compare_benchmarks(benchmark, tmp_path / "nonexistent.json")
        assert result.comparison is None


# ---------------------------------------------------------------------------
# Run eval integration test (deterministic only)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Config fidelity edge cases
# ---------------------------------------------------------------------------

class TestConfigFidelityEdgeCases:

    def test_config_fidelity_path_not_found(self):
        config = _make_config()
        passed, evidence = _check_config_fidelity("content", "nonexistent.path", config)
        assert not passed
        assert "not found" in evidence

    def test_config_fidelity_bool_value(self):
        config = _make_config()
        passed, evidence = _check_config_fidelity("content", "atlassian.enabled", config)
        assert passed  # Bool always returns True (the value exists)

    def test_config_fidelity_enum_value(self):
        config = _make_config()
        content = "Using mvp mode for this project"
        passed, evidence = _check_config_fidelity(content, "mode", config)
        assert passed

    def test_config_fidelity_string_not_found(self):
        config = _make_config()
        content = "No description here"
        passed, evidence = _check_config_fidelity(content, "strategy", config)
        assert not passed

    def test_config_fidelity_equals_mismatch_value(self):
        config = _make_config()
        content = "Using production-ready mode"
        passed, evidence = _check_config_fidelity(content, "mode=no-compromise", config)
        assert not passed

    def test_config_fidelity_equals_value_not_in_content(self):
        config = _make_config()
        content = "No mode mentioned here"
        passed, evidence = _check_config_fidelity(content, "mode=mvp", config)
        assert not passed


# ---------------------------------------------------------------------------
# Grading edge cases
# ---------------------------------------------------------------------------

class TestGradingEdgeCases:

    def test_section_present_with_indentation(self):
        """Section headers with leading whitespace should be found."""
        content = "    ## Base Agent Protocol\n\nContent here"
        passed, evidence = _check_section_present(content, "Base Agent Protocol")
        assert passed

    def test_deterministic_grade_empty_assertions(self):
        config = _make_config()
        results = deterministic_grade("content", "test.md", [], config)
        assert len(results) == 0

    def test_deterministic_grade_only_llm(self):
        config = _make_config()
        assertions = [
            Assertion(text="LLM only", check_type=CheckType.LLM_JUDGE, value="Is it good?"),
        ]
        results = deterministic_grade("content", "test.md", assertions, config)
        assert len(results) == 0  # LLM assertions skipped


# ---------------------------------------------------------------------------
# Benchmark edge cases
# ---------------------------------------------------------------------------

class TestBenchmarkEdgeCases:

    def test_aggregate_empty_report(self):
        report = EvalReport(config_name="empty")
        benchmark = aggregate_benchmark(report)
        assert benchmark.summary.total_files == 0
        assert benchmark.summary.avg_pass_rate == 0.0

    def test_benchmark_file_type_detection(self):
        report = EvalReport(
            files=[
                GradingResult(file_path=".claude/agents/test.md", pass_rate=0.9, expectations=[]),
                GradingResult(file_path=".claude/skills/test.md", pass_rate=0.8, expectations=[]),
                GradingResult(file_path="CLAUDE.md", pass_rate=1.0, expectations=[]),
                GradingResult(file_path="team-init-plan.md", pass_rate=0.95, expectations=[]),
                GradingResult(file_path="other.md", pass_rate=0.7, expectations=[]),
            ],
        )
        benchmark = aggregate_benchmark(report)
        type_map = {e.file_path: e.file_type for e in benchmark.entries}
        assert type_map[".claude/agents/test.md"] == "agent"
        assert type_map[".claude/skills/test.md"] == "skill"
        assert type_map["CLAUDE.md"] == "claude_md"
        assert type_map["team-init-plan.md"] == "team_init_plan"
        assert type_map["other.md"] == "unknown"

    def test_compare_with_invalid_json(self, tmp_path):
        (tmp_path / "benchmark.json").write_text("invalid json")
        report = EvalReport(config_name="test")
        benchmark = aggregate_benchmark(report)
        result = compare_benchmarks(benchmark, tmp_path / "benchmark.json")
        assert result.comparison is None  # Gracefully handles bad JSON

    def test_compare_with_regressed_files(self, tmp_path):
        """Comparison detects regressed files."""
        # Save "previous" with high pass rates
        prev = {
            "summary": {"avg_pass_rate": 0.9},
            "entries": [
                {"file_path": "a.md", "pass_rate": 0.95},
                {"file_path": "b.md", "pass_rate": 0.90},
            ],
        }
        (tmp_path / "benchmark.json").write_text(json.dumps(prev))

        # Current has lower rate for b.md
        report = EvalReport(
            files=[
                GradingResult(file_path="a.md", pass_rate=1.0, expectations=[]),
                GradingResult(file_path="b.md", pass_rate=0.5, expectations=[]),
            ],
        )
        benchmark = aggregate_benchmark(report)
        result = compare_benchmarks(benchmark, tmp_path / "benchmark.json")
        assert result.comparison is not None
        assert "b.md" in result.comparison.regressed_files
        assert "a.md" in result.comparison.improved_files

    def test_markdown_rendering_with_comparison(self, tmp_path):
        """Verify Markdown rendering includes comparison section."""
        prev = {
            "summary": {"avg_pass_rate": 0.8},
            "entries": [{"file_path": "a.md", "pass_rate": 0.8}],
        }
        (tmp_path / "benchmark.json").write_text(json.dumps(prev))

        report = EvalReport(
            files=[
                GradingResult(
                    file_path="a.md", pass_rate=0.9,
                    expectations=[
                        Expectation(text="test", passed=True, evidence="ok"),
                    ],
                ),
            ],
        )
        benchmark = aggregate_benchmark(report, "test")
        benchmark = compare_benchmarks(benchmark, tmp_path / "benchmark.json")

        _, md_path = save_benchmark(benchmark, tmp_path / "output")
        md = md_path.read_text()
        assert "Comparison with Previous Run" in md
        assert "improved" in md.lower()

    def test_markdown_rendering_with_many_failures(self, tmp_path):
        """Markdown truncates failures beyond 3."""
        report = EvalReport(
            files=[
                GradingResult(
                    file_path="a.md", pass_rate=0.2,
                    expectations=[
                        Expectation(text=f"check_{i}", passed=False, evidence=f"fail {i}")
                        for i in range(5)
                    ],
                ),
            ],
        )
        benchmark = aggregate_benchmark(report, "test")
        _, md_path = save_benchmark(benchmark, tmp_path)
        md = md_path.read_text()
        assert "+2 more" in md


# ---------------------------------------------------------------------------
# Applicability edge cases
# ---------------------------------------------------------------------------

class TestApplicabilityEdgeCases:

    def test_frontend_involvement_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"has_frontend_involvement": True},
        )
        assert _check_applicable(case, _make_config())  # fastapi+react has frontend

    def test_sub_agent_spawning_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"sub_agent_spawning": True},
        )
        assert _check_applicable(case, _make_config())  # default is True

    def test_llm_gateway_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"llm_gateway_enabled": True},
        )
        assert _check_applicable(case, _make_config())

    def test_agent_naming_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"agent_naming_enabled": True},
        )
        assert _check_applicable(case, _make_config())

    def test_has_databases_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"has_databases": True},
        )
        assert _check_applicable(case, _make_config())  # has postgresql

    def test_strategy_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"strategy": "co-pilot"},
        )
        assert _check_applicable(case, _make_config())

    def test_ssh_auth_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"has_ssh_auth": True},
        )
        assert not _check_applicable(case, _make_config())  # no ssh by default

    def test_agent_in_roster_list(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"agent_in_roster": ["backend-developer", "security-tester"]},
        )
        assert _check_applicable(case, _make_config())  # backend-developer is in lean

    def test_agent_not_in_roster_predicate(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"agent_not_in_roster": "security-tester"},
        )
        assert _check_applicable(case, _make_config())  # not in lean profile

    def test_unknown_predicate_warned(self):
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"unknown_predicate": True},
        )
        # Unknown predicates are skipped (logged), case still applies
        assert _check_applicable(case, _make_config())

    def test_static_site_predicate(self):
        config = _make_config(
            project=ProjectConfig(description="A simple brochure site"),
            tech_stack=TechStack(languages=[], frameworks=[]),
            agents=AgentsConfig(
                team_profile=TeamProfile.CUSTOM,
                include=["architect", "backend-developer", "qa-engineer"],
            ),
        )
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"is_static_site": True},
        )
        assert _check_applicable(case, config)


# ---------------------------------------------------------------------------
# Grade file async
# ---------------------------------------------------------------------------

class TestGradeFileAsync:

    def test_grade_file_deterministic(self):
        """grade_file with no LLM only runs deterministic assertions."""
        import asyncio
        config = _make_config()
        assertions = [
            Assertion(text="has hello", check_type=CheckType.CONTAINS, value="hello"),
            Assertion(text="no goodbye", check_type=CheckType.NOT_CONTAINS, value="goodbye"),
            Assertion(text="llm check", check_type=CheckType.LLM_JUDGE, value="Is it good?"),
        ]
        result = asyncio.run(grade_file("hello world", "test.md", config, assertions))
        # Only deterministic assertions should be evaluated (LLM skipped)
        assert len(result.expectations) == 2
        assert all(e.passed for e in result.expectations)
        assert result.llm_cost_usd == 0.0


# ---------------------------------------------------------------------------
# Run eval integration test (deterministic only)
# ---------------------------------------------------------------------------

class TestRunEval:
    """Tests that run_eval works end-to-end with deterministic checks."""

    def test_run_eval_with_generated_files(self, tmp_path):
        """Run eval against a minimal set of generated files."""
        import os
        os.environ["FORGE_TEST_DRY_RUN"] = "1"

        config = _make_config()
        config.project.directory = str(tmp_path)

        # Generate files
        from forge_cli.generators.orchestrator import generate_all
        generate_all(config)

        # Run deterministic eval
        report = run_eval(tmp_path, config, use_llm=False)

        assert len(report.files) > 0
        assert report.overall_pass_rate > 0
        assert report.duration_seconds >= 0
        assert report.total_cost_usd == 0.0  # No LLM

        # Check specific files were evaluated
        evaluated_paths = {f.file_path for f in report.files}
        assert "CLAUDE.md" in evaluated_paths
        assert "team-init-plan.md" in evaluated_paths

    def test_run_eval_cli_config(self, tmp_path):
        """Run eval against CLI project config."""
        import os
        os.environ["FORGE_TEST_DRY_RUN"] = "1"

        config = _make_cli_config()
        config.project.directory = str(tmp_path)

        from forge_cli.generators.orchestrator import generate_all
        generate_all(config)

        report = run_eval(tmp_path, config, use_llm=False)
        assert len(report.files) > 0
        # CLI-specific assertions should be present
        for fr in report.files:
            if "backend-developer" in fr.file_path:
                # Should have CLI-specific expectations
                texts = [e.text for e in fr.expectations]
                assert any("cli" in t.lower() or "click" in t.lower() for t in texts)
                break


# ---------------------------------------------------------------------------
# Description optimizer tests
# ---------------------------------------------------------------------------

class TestDescriptionOptimizer:
    """Tests for forge_cli.evals.description_optimizer."""

    def test_extract_frontmatter_with_fields(self):
        from forge_cli.evals.description_optimizer import _extract_frontmatter
        content = '---\nname: smoke-test\ndescription: "Run smoke tests"\n---\n# Body'
        fields, body = _extract_frontmatter(content)
        assert fields["name"] == "smoke-test"
        assert fields["description"] == "Run smoke tests"
        assert body.strip() == "# Body"

    def test_extract_frontmatter_no_frontmatter(self):
        from forge_cli.evals.description_optimizer import _extract_frontmatter
        content = "# Just a heading\nSome content"
        fields, body = _extract_frontmatter(content)
        assert fields == {}
        assert body == content

    def test_extract_frontmatter_quoted_values(self):
        from forge_cli.evals.description_optimizer import _extract_frontmatter
        content = "---\nname: 'test-skill'\ndescription: \"A test skill\"\n---\nbody"
        fields, body = _extract_frontmatter(content)
        assert fields["name"] == "test-skill"
        assert fields["description"] == "A test skill"

    def test_update_description(self):
        from forge_cli.evals.description_optimizer import _update_description
        content = '---\nname: smoke-test\ndescription: old desc\n---\n# Body'
        updated = _update_description(content, "new desc")
        assert 'description: "new desc"' in updated
        assert "name: smoke-test" in updated
        assert "# Body" in updated

    def test_update_description_no_frontmatter(self):
        from forge_cli.evals.description_optimizer import _update_description
        content = "# No frontmatter"
        assert _update_description(content, "new") == content

    def test_models(self):
        from forge_cli.evals.description_optimizer import (
            TriggerQuery,
            TriggerEvalResult,
            OptimizationReport,
            GeneratedQueries,
            TriggerEvaluation,
            ImprovedDescription,
        )
        q = TriggerQuery(query="run tests", should_trigger=True)
        assert q.query == "run tests"
        assert q.should_trigger is True

        r = TriggerEvalResult(query="q", should_trigger=True, would_trigger=True, correct=True)
        assert r.correct is True

        o = OptimizationReport(
            skill_path="/a.md",
            original_description="old",
            optimized_description="new",
            original_accuracy=0.5,
            optimized_accuracy=0.8,
            iterations=3,
        )
        assert o.iterations == 3
        assert o.optimized_accuracy > o.original_accuracy

        g = GeneratedQueries(queries=[q])
        assert len(g.queries) == 1

        e = TriggerEvaluation(evaluations=[True, False])
        assert len(e.evaluations) == 2

        d = ImprovedDescription(description="better", reasoning="because")
        assert d.description == "better"


# ---------------------------------------------------------------------------
# LLM grading paths (mocked)
# ---------------------------------------------------------------------------

class TestLLMGradingMocked:
    """Tests for LLM grading code paths with mocked LLM."""

    def test_llm_grade_no_assertions(self):
        """llm_grade with no LLM_JUDGE assertions returns empty."""
        import asyncio
        from forge_cli.evals.grading import llm_grade
        assertions = [
            Assertion(text="contains check", check_type=CheckType.CONTAINS, value="x"),
        ]
        config = _make_config()
        expectations, cost = asyncio.run(llm_grade(None, "content", "f.md", assertions, config))
        assert expectations == []
        assert cost == 0.0

    def test_build_project_context(self):
        """_build_project_context produces sensible output."""
        from forge_cli.evals.grading import _build_project_context
        config = _make_config()
        ctx = _build_project_context(config)
        assert "E-commerce API" in ctx
        assert "python" in ctx
        assert "fastapi" in ctx
        assert "postgresql" in ctx

    def test_build_project_context_minimal(self):
        """_build_project_context with minimal config."""
        from forge_cli.evals.grading import _build_project_context
        config = _make_config(
            tech_stack=TechStack(languages=[], frameworks=[], databases=[]),
            non_negotiables=["no mocks"],
        )
        ctx = _build_project_context(config)
        assert "no mocks" in ctx

    def test_estimate_cost(self):
        """_estimate_cost computes expected values."""
        from forge_cli.evals.grading import _estimate_cost
        cost = _estimate_cost(1000, 1000)
        assert cost == pytest.approx(0.003 + 0.015)
        assert _estimate_cost(0, 0) == 0.0


# ---------------------------------------------------------------------------
# Eval runner edge cases
# ---------------------------------------------------------------------------

class TestEvalRunnerEdgeCases:

    def test_grade_file_for_refinement_no_cases(self):
        """grade_file_for_refinement returns 1.0 when no cases match."""
        import asyncio
        from forge_cli.evals.eval_runner import grade_file_for_refinement
        config = _make_config()
        result = asyncio.run(
            grade_file_for_refinement("content", "nonexistent.md", "agent", config)
        )
        assert result.pass_rate == 1.0

    def test_grade_file_for_refinement_with_cases(self):
        """grade_file_for_refinement finds and grades matching cases."""
        import asyncio
        from forge_cli.evals.eval_runner import grade_file_for_refinement
        config = _make_config()
        result = asyncio.run(
            grade_file_for_refinement(
                "# Team Leader\n## Base Agent Protocol\n## Getting Started",
                ".claude/agents/team-leader.md",
                "agent",
                config,
            )
        )
        assert len(result.expectations) > 0

    def test_unknown_predicate_logs_warning(self):
        """Unknown predicates are warned about but don't crash."""
        config = _make_config()
        case = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"unknown_predicate": True},
        )
        # Should not raise, unknown predicates are skipped
        result = _check_applicable(case, config)
        assert result is True  # Unknown predicate is ignored (warned)

    def test_strategy_predicate(self):
        """strategy predicate filters correctly."""
        config = _make_config()
        case_match = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"strategy": "co-pilot"},
        )
        case_no = EvalCase(
            id="test2", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"strategy": "auto-pilot"},
        )
        assert _check_applicable(case_match, config) is True
        assert _check_applicable(case_no, config) is False

    def test_mode_predicate(self):
        """mode predicate filters correctly."""
        config = _make_config()
        case_match = EvalCase(
            id="test", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"mode": "mvp"},
        )
        case_no = EvalCase(
            id="test2", file_path="f.md", file_type="agent",
            description="test", assertions=[],
            applicable_when={"mode": "no_compromise"},
        )
        assert _check_applicable(case_match, config) is True
        assert _check_applicable(case_no, config) is False


# ---------------------------------------------------------------------------
# CLI eval command tests
# ---------------------------------------------------------------------------

class TestEvalCLI:
    """Tests for the forge eval CLI command."""

    def test_eval_no_generated_files(self, tmp_path):
        """eval command fails gracefully when no generated files exist."""
        from click.testing import CliRunner
        from forge_cli.main import cli
        from forge_cli.config_loader import save_config

        config = _make_config()
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "eval",
            "--config", str(config_path),
            "--project-dir", str(tmp_path),
            "--no-llm",
        ])
        assert result.exit_code != 0 or "No generated files" in result.output

    def test_eval_with_generated_files(self, tmp_path):
        """eval command runs successfully against generated files."""
        import os
        os.environ["FORGE_TEST_DRY_RUN"] = "1"

        from click.testing import CliRunner
        from forge_cli.main import cli
        from forge_cli.config_loader import save_config
        from forge_cli.generators.orchestrator import generate_all

        config = _make_config()
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)
        config.project.directory = str(tmp_path)
        generate_all(config)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "eval",
            "--config", str(config_path),
            "--project-dir", str(tmp_path),
            "--no-llm",
        ])
        assert result.exit_code == 0, f"Exit code: {result.exit_code}\nOutput: {result.output}"
        assert "Eval Results" in result.output
        assert "pass rate" in result.output.lower() or "%" in result.output
        # Verify benchmark files were saved
        assert (tmp_path / ".forge" / "benchmark.json").exists()
        assert (tmp_path / ".forge" / "benchmark.md").exists()

    def test_eval_verbose_flag(self, tmp_path):
        """eval command with --verbose shows detailed output."""
        import os
        os.environ["FORGE_TEST_DRY_RUN"] = "1"

        from click.testing import CliRunner
        from forge_cli.main import cli
        from forge_cli.config_loader import save_config
        from forge_cli.generators.orchestrator import generate_all

        config = _make_config()
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)
        config.project.directory = str(tmp_path)
        generate_all(config)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "eval",
            "--config", str(config_path),
            "--project-dir", str(tmp_path),
            "--no-llm",
            "-v",
        ])
        assert result.exit_code == 0

    def test_eval_second_run_compares(self, tmp_path):
        """Second eval run shows comparison with previous."""
        import os
        os.environ["FORGE_TEST_DRY_RUN"] = "1"

        from click.testing import CliRunner
        from forge_cli.main import cli
        from forge_cli.config_loader import save_config
        from forge_cli.generators.orchestrator import generate_all

        config = _make_config()
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)
        config.project.directory = str(tmp_path)
        generate_all(config)

        runner = CliRunner()
        # First run
        runner.invoke(cli, [
            "eval", "--config", str(config_path),
            "--project-dir", str(tmp_path), "--no-llm",
        ])
        # Second run — should compare
        result = runner.invoke(cli, [
            "eval", "--config", str(config_path),
            "--project-dir", str(tmp_path), "--no-llm",
        ])
        assert result.exit_code == 0
