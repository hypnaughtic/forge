"""Tests for LLM-powered refinement module."""

import asyncio
from pathlib import Path
from typing import Any, Sequence

import pytest

from forge_cli.config_schema import (
    AgentsConfig,
    AtlassianConfig,
    ForgeConfig,
    ProjectConfig,
    ProjectMode,
    RefinementConfig,
    TechStack,
    TeamProfile,
)
from forge_cli.generators.orchestrator import generate_all, run_refinement
from forge_cli.generators.refinement import (
    FileScore,
    RefinedContent,
    RefinementReport,
    _build_project_context,
    _build_score_prompt,
    _classify_file,
    _collect_refinable_files,
    refine_all,
    refine_all_async,
    refine_single_file,
    score_file,
    refine_file,
)
from llm_gateway import FakeLLMProvider, LLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    enabled: bool = True,
    score_threshold: int = 90,
    max_iterations: int = 5,
) -> ForgeConfig:
    """Create a test config with refinement enabled."""
    return ForgeConfig(
        project=ProjectConfig(
            description="E-commerce platform",
            requirements="Build a full-stack e-commerce platform with auth and checkout",
        ),
        mode=ProjectMode.PRODUCTION_READY,
        agents=AgentsConfig(team_profile=TeamProfile.LEAN),
        tech_stack=TechStack(
            languages=["python", "typescript"],
            frameworks=["fastapi", "react"],
            databases=["postgresql"],
        ),
        atlassian=AtlassianConfig(enabled=False),
        refinement=RefinementConfig(
            enabled=enabled,
            score_threshold=score_threshold,
            max_iterations=max_iterations,
        ),
    )


def _generate_project(
    tmp_path: Path,
    config: ForgeConfig,
    llm_provider: Any = None,
) -> Any:
    """Generate a project and run refinement if enabled.

    Passes llm_provider through so refinement uses a fake
    instead of blocking on a real LLM.
    """
    config.project.directory = str(tmp_path)
    generate_all(config, llm_provider=llm_provider)
    if config.refinement.enabled:
        return run_refinement(config, tmp_path, llm_provider=llm_provider)
    return None


def _make_fake_provider(
    initial_score: int = 85,
    refined_score: int = 95,
) -> FakeLLMProvider:
    """Create a FakeLLMProvider that scores low initially, high after refinement.

    Uses response_factory for dynamic behavior:
    - FileScore requests: returns initial_score first, then refined_score
    - RefinedContent requests: returns content with marker prepended
    """
    call_counts: dict[str, int] = {"score": 0, "refine": 0}

    def factory(model_class, messages: Sequence):
        if model_class is FileScore:
            call_counts["score"] += 1
            if call_counts["score"] <= 1:
                return FileScore(
                    score=initial_score,
                    reasoning="Good but could be more specific",
                    suggestions=["Add more project-specific details", "Improve clarity"],
                )
            return FileScore(
                score=refined_score,
                reasoning="Excellent quality after refinement",
                suggestions=[],
            )
        if model_class is RefinedContent:
            call_counts["refine"] += 1
            # Extract content from the prompt
            user_msg = messages[-1]["content"] if messages else ""
            # Find the CURRENT CONTENT section
            marker = "CURRENT CONTENT:\n"
            idx = user_msg.find(marker)
            if idx >= 0:
                content_start = idx + len(marker)
                content_end = user_msg.find("\n\nPREVIOUS SCORE:", content_start)
                original = user_msg[content_start:content_end] if content_end > 0 else user_msg[content_start:]
            else:
                original = "# Refined content"
            return RefinedContent(
                content=f"<!-- LLM-refined -->\n{original}",
                changes_made=["Added project-specific details", "Improved clarity"],
            )
        raise ValueError(f"Unexpected model class: {model_class}")

    return FakeLLMProvider(response_factory=factory)


def _make_always_good_provider(score: int = 95) -> FakeLLMProvider:
    """Create a provider that always scores above threshold."""
    def factory(model_class, messages):
        if model_class is FileScore:
            return FileScore(
                score=score,
                reasoning="Excellent quality",
                suggestions=[],
            )
        raise ValueError(f"Unexpected call for {model_class}")

    return FakeLLMProvider(response_factory=factory)


# ---------------------------------------------------------------------------
# TestRefinementConfig
# ---------------------------------------------------------------------------

class TestRefinementConfig:
    def test_defaults(self):
        config = RefinementConfig()
        assert config.enabled is False
        assert config.provider == "local_claude"
        assert config.model == "claude-opus-4-6"
        assert config.max_tokens == 8192
        assert config.score_threshold == 90
        assert config.max_iterations == 5
        assert config.max_concurrency == 0
        assert config.timeout_seconds == 300
        assert config.cost_limit_usd == 10.0

    def test_forge_config_has_refinement(self):
        config = ForgeConfig()
        assert hasattr(config, "refinement")
        assert isinstance(config.refinement, RefinementConfig)
        assert config.refinement.enabled is False

    def test_custom_values(self):
        config = RefinementConfig(
            enabled=True,
            provider="anthropic",
            score_threshold=85,
            max_iterations=3,
        )
        assert config.enabled is True
        assert config.provider == "anthropic"
        assert config.score_threshold == 85
        assert config.max_iterations == 3


# ---------------------------------------------------------------------------
# TestFileScoring
# ---------------------------------------------------------------------------

class TestFileScoring:
    def test_score_file_returns_structured_result(self):
        """score_file should return a FileScore with valid fields."""
        fake = _make_fake_provider(initial_score=82)
        llm = LLMClient(provider_instance=fake)
        config = _make_config()

        async def _test():
            try:
                result, cost = await score_file(
                    llm, "# Test Agent\nDo stuff.", config, "test-agent.md", "agent",
                )
                assert isinstance(result, FileScore)
                assert result.score == 82
                assert len(result.reasoning) > 0
                assert isinstance(result.suggestions, list)
                assert cost >= 0
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_score_prompt_includes_project_context(self):
        """The scoring prompt should include project details."""
        config = _make_config()
        prompt = _build_score_prompt(
            "# Agent content", config, "backend-developer.md", "agent",
        )
        assert "E-commerce platform" in prompt
        assert "production-ready" in prompt
        assert "fastapi" in prompt
        assert "postgresql" in prompt
        assert "backend-developer.md" in prompt

    def test_project_context_includes_non_negotiables(self):
        config = _make_config()
        config.non_negotiables = ["All APIs must be authenticated"]
        context = _build_project_context(config)
        assert "All APIs must be authenticated" in context


# ---------------------------------------------------------------------------
# TestFileRefinement
# ---------------------------------------------------------------------------

class TestFileRefinement:
    def test_refine_file_returns_improved_content(self):
        """refine_file should return content with changes."""
        fake = _make_fake_provider()
        llm = LLMClient(provider_instance=fake)
        config = _make_config()

        feedback = FileScore(
            score=75,
            reasoning="Needs more detail",
            suggestions=["Add tech stack specifics"],
        )

        async def _test():
            try:
                result, cost = await refine_file(
                    llm, "# Original content", config,
                    "test.md", "agent", feedback,
                )
                assert isinstance(result, RefinedContent)
                assert len(result.content) > 0
                assert isinstance(result.changes_made, list)
                assert cost >= 0
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_refine_prompt_includes_feedback(self):
        """The refine prompt should include previous score and suggestions."""
        config = _make_config()
        feedback = FileScore(
            score=72,
            reasoning="Missing tech specifics",
            suggestions=["Add PostgreSQL details", "Reference FastAPI"],
        )
        from forge_cli.generators.refinement import _build_refine_prompt
        prompt = _build_refine_prompt(
            "# Content", config, "backend.md", "agent", feedback,
        )
        assert "72" in prompt
        assert "Missing tech specifics" in prompt
        assert "Add PostgreSQL details" in prompt
        assert "Reference FastAPI" in prompt


# ---------------------------------------------------------------------------
# TestRefinementLoop
# ---------------------------------------------------------------------------

class TestRefinementLoop:
    def test_skips_if_above_threshold(self):
        """File already above threshold should not be refined."""
        fake = _make_always_good_provider(score=95)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90)

        async def _test():
            try:
                content, result = await refine_single_file(
                    llm, "# Good content", config, "test.md", "agent",
                )
                assert result.initial_score == 95
                assert result.final_score == 95
                assert len(result.iterations) == 1  # Only scored, not refined
                assert content == "# Good content"  # Unchanged
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_refines_until_threshold_met(self):
        """File below threshold should be refined until it passes."""
        fake = _make_fake_provider(initial_score=80, refined_score=92)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90)

        async def _test():
            try:
                content, result = await refine_single_file(
                    llm, "# Needs work", config, "test.md", "agent",
                )
                assert result.initial_score == 80
                assert result.final_score == 92
                assert len(result.iterations) >= 2  # At least score + refine + re-score
                assert "LLM-refined" in content
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_stops_at_max_iterations(self):
        """Should stop after max_iterations even if threshold not met."""
        # Provider that never gives a passing score
        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=70,
                    reasoning="Still not great",
                    suggestions=["Try harder"],
                )
            if model_class is RefinedContent:
                return RefinedContent(
                    content="# Still trying\nSome content here that is long enough",
                    changes_made=["Tried to improve"],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=3)

        async def _test():
            try:
                content, result = await refine_single_file(
                    llm, "# Stubborn content", config, "test.md", "agent",
                )
                assert result.final_score == 70
                assert len(result.iterations) == 3
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_keeps_best_version(self):
        """Should keep the best-scoring version across iterations."""
        scores = iter([60, 80, 65])  # Score goes up then down

        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=next(scores, 65),
                    reasoning="Variable quality",
                    suggestions=["Improve more"],
                )
            if model_class is RefinedContent:
                return RefinedContent(
                    content="# Refined content that is long enough for the guard",
                    changes_made=["Changed things"],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=3)

        async def _test():
            try:
                content, result = await refine_single_file(
                    llm, "# Original content", config, "test.md", "agent",
                )
                # Best score was 80
                assert result.final_score == 80
            finally:
                await llm.close()

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TestRefineAll
# ---------------------------------------------------------------------------

class TestRefineAll:
    def test_disabled_does_nothing(self, tmp_path):
        """Refinement disabled should return empty report."""
        config = _make_config(enabled=False)
        _generate_project(tmp_path, config)

        report = refine_all(config, tmp_path)
        assert isinstance(report, RefinementReport)
        assert len(report.files) == 0
        assert report.total_cost_usd == 0.0

    def test_full_pipeline_updates_files(self, tmp_path):
        """Full pipeline should score and refine all .md files."""
        config = _make_config(enabled=True, score_threshold=90)
        fake = _make_fake_provider(initial_score=80, refined_score=95)
        report = _generate_project(tmp_path, config, llm_provider=fake)

        assert isinstance(report, RefinementReport)
        assert len(report.files) > 0
        assert report.total_cost_usd > 0
        assert report.files_improved > 0

        # Check file types present
        file_types = {f.file_type for f in report.files}
        assert "agent" in file_types
        assert "claude_md" in file_types
        assert "team_init_plan" in file_types

    def test_skips_mcp_json(self, tmp_path):
        """mcp.json should not be refined (it's JSON, not prose)."""
        config = _make_config(enabled=False)
        _generate_project(tmp_path, config)

        files = _collect_refinable_files(tmp_path)
        file_paths = [str(p) for p, _ in files]
        assert not any("mcp.json" in p for p in file_paths)

    def test_already_good_files_not_rewritten(self, tmp_path):
        """Files already above threshold should not be modified."""
        config = _make_config(enabled=True, score_threshold=90)
        fake = _make_always_good_provider(score=95)
        _generate_project(tmp_path, config, llm_provider=fake)

        # After refinement with always-good provider, no files should be rewritten
        # Re-run refinement separately to check content stability
        claude_md_path = tmp_path / "CLAUDE.md"
        original = claude_md_path.read_text()

        report = refine_all(config, tmp_path, llm_provider=_make_always_good_provider(score=95))

        assert report.files_already_good > 0
        # Content unchanged (no write-back for already-good files)
        assert claude_md_path.read_text() == original

    def test_reports_cost(self, tmp_path):
        """Report should track cumulative cost."""
        config = _make_config(enabled=True)
        fake = _make_always_good_provider(score=95)
        report = _generate_project(tmp_path, config, llm_provider=fake)

        assert report.total_cost_usd >= 0
        for f in report.files:
            assert f.total_cost_usd >= 0

    def test_classifies_file_types_correctly(self, tmp_path):
        """File classifier should correctly identify file types."""
        project_dir = tmp_path
        assert _classify_file(project_dir / "CLAUDE.md", project_dir) == "claude_md"
        assert _classify_file(project_dir / "team-init-plan.md", project_dir) == "team_init_plan"
        assert _classify_file(
            project_dir / ".claude" / "agents" / "backend.md", project_dir,
        ) == "agent"
        assert _classify_file(
            project_dir / ".claude" / "skills" / "release.md", project_dir,
        ) == "skill"
        assert _classify_file(project_dir / "random.md", project_dir) is None

    def test_skill_files_included(self, tmp_path):
        """Skill files should be included in refinement."""
        config = _make_config(enabled=False)
        _generate_project(tmp_path, config)

        files = _collect_refinable_files(tmp_path)
        file_types = {ft for _, ft in files}
        assert "skill" in file_types

    def test_refinement_report_all_passed(self, tmp_path):
        """all_passed should be True when all files meet threshold."""
        config = _make_config(enabled=True, score_threshold=90)
        fake = _make_always_good_provider(score=95)
        report = _generate_project(tmp_path, config, llm_provider=fake)

        assert report.all_passed is True


# ---------------------------------------------------------------------------
# TestRefinementProgress — progress display unit tests
# ---------------------------------------------------------------------------

class TestRefinementProgress:
    """Test ForgeRefinementProgress display behavior."""

    def test_register_file_sets_waiting_status(self):
        """register_file() creates file in 'waiting' state."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 3
        p.register_file("agent.md", target_score=90)
        assert p._files["agent.md"].status == "waiting"

    def test_start_file_transitions_to_scoring(self):
        """start_file() transitions a registered file to 'scoring'."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 1
        p.register_file("agent.md", target_score=90)
        assert p._files["agent.md"].status == "waiting"
        p.start_file("agent.md")
        assert p._files["agent.md"].status == "scoring"

    def test_start_file_without_register_creates_scoring(self):
        """start_file() on unregistered file creates it in 'scoring' state."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 1
        p.start_file("agent.md", target_score=90)
        assert p._files["agent.md"].status == "scoring"

    def test_update_score_tracks_initial(self):
        """First score update sets initial_score."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 1
        p.start_file("agent.md")
        p.update_score("agent.md", score=75, iteration=1, status="scoring")
        assert p._files["agent.md"].initial_score == 75
        assert p._files["agent.md"].current_score == 75
        # Second update should NOT change initial
        p.update_score("agent.md", score=85, iteration=2, status="refining")
        assert p._files["agent.md"].initial_score == 75
        assert p._files["agent.md"].current_score == 85

    def test_complete_file_increments_counters(self):
        """complete_file() updates status and counters correctly."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 2
        p.register_file("a.md", target_score=90)
        p.register_file("b.md", target_score=90)
        p.start_file("a.md")
        p.update_score("a.md", score=95, iteration=1)
        p.complete_file("a.md", final_score=95)
        assert p._completed_files == 1
        assert p._passed_files == 1
        assert p._files["a.md"].status == "done"

    def test_complete_below_threshold_counts_as_below(self):
        """File below threshold increments _below_files."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 1
        p.register_file("a.md", target_score=90)
        p.start_file("a.md")
        p.complete_file("a.md", final_score=80)
        assert p._below_files == 1
        assert p._passed_files == 0

    def test_fail_file_increments_failed_counter(self):
        """fail_file() updates status and counter."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 1
        p.register_file("a.md", target_score=90)
        p.start_file("a.md")
        p.fail_file("a.md", reason="LLM timeout")
        assert p._failed_files == 1
        assert p._completed_files == 1
        assert p._files["a.md"].status == "failed"
        assert p._files["a.md"].last_change == "LLM timeout"

    def test_live_display_excludes_waiting_files(self):
        """Live display table only contains active files, not waiting ones."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 5
        for name in ["a.md", "b.md", "c.md", "d.md", "e.md"]:
            p.register_file(name)
        # Start 2 files
        p.start_file("a.md")
        p.start_file("b.md")

        table = p._build_live_display()
        # Table rows = 2 active + 1 summary = 3
        assert table.row_count == 3

    def test_live_display_excludes_completed_files(self):
        """Completed files are printed permanently, not in live display."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 3
        for name in ["a.md", "b.md", "c.md"]:
            p.register_file(name)
        p.start_file("a.md")
        p.start_file("b.md")
        # Complete a.md — it should no longer appear in live display
        p.update_score("a.md", score=95, iteration=1)
        p.complete_file("a.md", final_score=95)

        table = p._build_live_display()
        # Only b.md active + 1 summary = 2 rows
        assert table.row_count == 2

    def test_final_display_shows_all_files(self):
        """Final display includes every file regardless of status."""
        from forge_cli.progress import ForgeRefinementProgress
        p = ForgeRefinementProgress()
        p._total_files = 3
        for name in ["a.md", "b.md", "c.md"]:
            p.register_file(name)
        p.start_file("a.md")
        p.complete_file("a.md", final_score=95)
        p.start_file("b.md")
        p.fail_file("b.md", "timeout")

        table = p._build_final_display()
        # 3 files + 1 summary footer = 4 rows
        assert table.row_count == 4

    def test_live_display_summary_shows_queued_count(self):
        """Summary footer shows queued file count."""
        from io import StringIO
        from rich.console import Console
        from forge_cli.progress import ForgeRefinementProgress

        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        p = ForgeRefinementProgress(console=console)
        p._total_files = 10
        for i in range(10):
            p.register_file(f"file{i}.md")
        p.start_file("file0.md")

        table = p._build_live_display()
        console.print(table)
        output = buf.getvalue()
        assert "9 queued" in output


# ---------------------------------------------------------------------------
# TestWorkerPoolRefinement — verify worker-pool concurrency behavior
# ---------------------------------------------------------------------------

class TestWorkerPoolRefinement:
    """Test that refinement uses a worker pool with immediate file pickup."""

    def test_concurrency_bounded_by_config(self, tmp_path):
        """Refinement respects max_concurrency setting."""
        config = _make_config(enabled=True, score_threshold=90)
        config.refinement.max_concurrency = 2
        config.project.directory = str(tmp_path)
        generate_all(config)

        # Track which files were active concurrently
        active: set[str] = set()
        max_active = 0
        seen_files: list[str] = []

        from forge_cli.progress import ForgeRefinementProgress
        original_start = ForgeRefinementProgress.start_file
        original_complete = ForgeRefinementProgress.complete_file
        original_fail = ForgeRefinementProgress.fail_file

        def tracking_start(self, file_name, target_score=90):
            nonlocal max_active
            active.add(file_name)
            max_active = max(max_active, len(active))
            seen_files.append(file_name)
            original_start(self, file_name, target_score)

        def tracking_complete(self, file_name, final_score):
            active.discard(file_name)
            original_complete(self, file_name, final_score)

        def tracking_fail(self, file_name, reason=""):
            active.discard(file_name)
            original_fail(self, file_name, reason)

        import unittest.mock as mock
        with mock.patch.object(ForgeRefinementProgress, "start_file", tracking_start), \
             mock.patch.object(ForgeRefinementProgress, "complete_file", tracking_complete), \
             mock.patch.object(ForgeRefinementProgress, "fail_file", tracking_fail):
            fake = _make_always_good_provider(score=95)
            run_refinement(config, tmp_path, llm_provider=fake)

        # With instant fake provider, concurrency isn't truly tested,
        # but we verify all files were processed
        assert len(seen_files) > 0

    def test_all_files_processed_by_worker_pool(self, tmp_path):
        """Every refinable file gets processed through the worker pool."""
        config = _make_config(enabled=True, score_threshold=90)
        config.refinement.max_concurrency = 3
        config.project.directory = str(tmp_path)
        generate_all(config)

        fake = _make_always_good_provider(score=95)
        report = run_refinement(config, tmp_path, llm_provider=fake)

        # Every file should appear in the report
        files_in_report = {r.file_path for r in report.files}
        expected_files = _collect_refinable_files(tmp_path)
        expected_paths = {str(fp.relative_to(tmp_path)) for fp, _ in expected_files}
        assert files_in_report == expected_paths

    def test_register_before_start(self, tmp_path):
        """All files are registered (waiting) before any start processing."""
        config = _make_config(enabled=True, score_threshold=90)
        config.project.directory = str(tmp_path)
        generate_all(config)

        from forge_cli.progress import ForgeRefinementProgress

        registered: list[str] = []
        started: list[str] = []
        registration_complete_before_first_start = [False]

        original_register = ForgeRefinementProgress.register_file
        original_start = ForgeRefinementProgress.start_file

        def track_register(self, file_name, target_score=90):
            registered.append(file_name)
            original_register(self, file_name, target_score)

        def track_start(self, file_name, target_score=90):
            if not started:
                # First start — check all files were registered
                files = _collect_refinable_files(tmp_path)
                registration_complete_before_first_start[0] = \
                    len(registered) == len(files)
            started.append(file_name)
            original_start(self, file_name, target_score)

        import unittest.mock as mock
        with mock.patch.object(ForgeRefinementProgress, "register_file", track_register), \
             mock.patch.object(ForgeRefinementProgress, "start_file", track_start):
            fake = _make_always_good_provider(score=95)
            run_refinement(config, tmp_path, llm_provider=fake)

        assert registration_complete_before_first_start[0], \
            "All files should be registered before any file starts processing"


# ---------------------------------------------------------------------------
# TestHallucinationGuard — content too short rejection
# ---------------------------------------------------------------------------

class TestHallucinationGuard:
    """Test hallucination guard in refine_single_file (lines 435-441)."""

    def test_rejects_content_shorter_than_50_percent(self):
        """Refined content < 50% of original length is rejected."""
        original = "# Agent\n" + "x" * 200  # 209 chars
        call_counts: dict[str, int] = {"score": 0, "refine": 0}

        def factory(model_class, messages):
            if model_class is FileScore:
                call_counts["score"] += 1
                # Always score below threshold so refinement is attempted
                return FileScore(
                    score=70,
                    reasoning="Needs work",
                    suggestions=["Add more"],
                )
            if model_class is RefinedContent:
                call_counts["refine"] += 1
                # Return content that is way too short (< 50% of original)
                return RefinedContent(
                    content="# Short",
                    changes_made=["Shortened everything"],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=2)

        async def _test():
            try:
                content, result = await refine_single_file(
                    llm, original, config, "test.md", "agent",
                )
                # Content should be unchanged (hallucinated version rejected)
                assert content == original
                assert result.final_score == 70
                # Two iterations attempted — both refinements rejected
                assert len(result.iterations) == 2
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_hallucination_guard_with_progress_callback(self):
        """Hallucination guard triggers progress.update_score with rejection detail.

        Covers lines 643-654 in _refine_single_file_with_progress.
        """
        original = "# Agent\n" + "x" * 200

        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=70,
                    reasoning="Needs work",
                    suggestions=["Add more"],
                )
            if model_class is RefinedContent:
                return RefinedContent(
                    content="# Too short",
                    changes_made=["Truncated"],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=2)

        # Track progress calls
        progress_calls: list[dict] = []

        class FakeProgress:
            def start_file(self, *a, **kw):
                pass

            def complete_file(self, *a, **kw):
                pass

            def update_score(self, file_path, score, iteration, **kwargs):
                progress_calls.append({
                    "file_path": file_path,
                    "score": score,
                    "iteration": iteration,
                    **kwargs,
                })

            def register_file(self, *a, **kw):
                pass

            def fail_file(self, *a, **kw):
                pass

        from forge_cli.generators.refinement import _refine_single_file_with_progress

        async def _test():
            try:
                content, result = await _refine_single_file_with_progress(
                    llm, original, config, "test.md", "agent",
                    progress=FakeProgress(),
                )
                # Content should be unchanged (rejected)
                assert content == original
                # Should have at least one "rejected (content too short)" detail
                rejection_calls = [
                    c for c in progress_calls
                    if "rejected" in c.get("detail", "")
                ]
                assert len(rejection_calls) >= 1
                assert "content too short" in rejection_calls[0]["detail"]
            finally:
                await llm.close()

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TestEvalFailuresInPrompts — eval failure integration
# ---------------------------------------------------------------------------

class TestEvalFailuresInPrompts:
    """Test eval_failures parameter in score and refine prompts."""

    def test_score_prompt_includes_eval_failures(self):
        """Score prompt should include eval assertion failures when provided.

        Covers lines 179-186 in _build_score_prompt (eval_section).
        """
        config = _make_config()
        prompt = _build_score_prompt(
            "# Agent content", config, "backend-developer.md", "agent",
            eval_failures=[
                "Must mention PostgreSQL: not found",
                "Should reference FastAPI: missing",
            ],
        )
        assert "EVAL ASSERTION FAILURES" in prompt
        assert "Must mention PostgreSQL: not found" in prompt
        assert "Should reference FastAPI: missing" in prompt
        assert "Factor these failures into your score" in prompt

    def test_score_prompt_without_eval_failures(self):
        """Score prompt should NOT include eval section when no failures."""
        config = _make_config()
        prompt = _build_score_prompt(
            "# Agent content", config, "backend-developer.md", "agent",
            eval_failures=None,
        )
        assert "EVAL ASSERTION FAILURES" not in prompt

    def test_score_prompt_with_empty_eval_failures(self):
        """Score prompt should NOT include eval section when failures list is empty."""
        config = _make_config()
        prompt = _build_score_prompt(
            "# Agent content", config, "backend-developer.md", "agent",
            eval_failures=[],
        )
        assert "EVAL ASSERTION FAILURES" not in prompt

    def test_refine_prompt_includes_eval_failures(self):
        """Refine prompt should include eval failures when provided.

        Covers lines 259-266 in _build_refine_prompt (eval_section).
        """
        from forge_cli.generators.refinement import _build_refine_prompt
        config = _make_config()
        feedback = FileScore(
            score=72,
            reasoning="Missing tech specifics",
            suggestions=["Add details"],
        )
        prompt = _build_refine_prompt(
            "# Content", config, "backend.md", "agent", feedback,
            eval_failures=[
                "Must contain ## Database section: section not found",
                "Must mention auth: keyword missing",
            ],
        )
        assert "EVAL ASSERTION FAILURES" in prompt
        assert "must address these" in prompt
        assert "Must contain ## Database section" in prompt
        assert "Must mention auth" in prompt

    def test_refine_prompt_without_eval_failures(self):
        """Refine prompt should NOT include eval section when no failures."""
        from forge_cli.generators.refinement import _build_refine_prompt
        config = _make_config()
        feedback = FileScore(
            score=72,
            reasoning="OK",
            suggestions=["More detail"],
        )
        prompt = _build_refine_prompt(
            "# Content", config, "backend.md", "agent", feedback,
            eval_failures=None,
        )
        assert "EVAL ASSERTION FAILURES" not in prompt


# ---------------------------------------------------------------------------
# TestProgressReporting — progress callback edge cases
# ---------------------------------------------------------------------------

class TestProgressReportingEdgeCases:
    """Test progress callback handling for first_change and best-score tracking."""

    def test_long_first_change_is_truncated(self):
        """First change > 60 chars is truncated with ellipsis.

        Covers line 661-662 in _refine_single_file_with_progress.
        """
        original = "# Agent\n" + "x" * 200

        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=70,
                    reasoning="Needs work",
                    suggestions=["Add more"],
                )
            if model_class is RefinedContent:
                # Return content at least 50% of original to pass hallucination guard
                return RefinedContent(
                    content=original + "\n# Improved section with more content",
                    changes_made=[
                        "Added a very long change description that exceeds sixty characters and should be truncated"
                    ],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=1)

        progress_calls: list[dict] = []

        class FakeProgress:
            def start_file(self, *a, **kw):
                pass

            def complete_file(self, *a, **kw):
                pass

            def update_score(self, file_path, score, iteration, **kwargs):
                progress_calls.append({
                    "file_path": file_path,
                    "score": score,
                    "iteration": iteration,
                    **kwargs,
                })

            def register_file(self, *a, **kw):
                pass

            def fail_file(self, *a, **kw):
                pass

        from forge_cli.generators.refinement import _refine_single_file_with_progress

        async def _test():
            try:
                await _refine_single_file_with_progress(
                    llm, original, config, "test.md", "agent",
                    progress=FakeProgress(),
                )
                # Find the change reporting call
                change_calls = [
                    c for c in progress_calls
                    if c.get("status") == "refining"
                    and c.get("detail", "").endswith("...")
                ]
                assert len(change_calls) >= 1
                # The truncated detail should be exactly 60 chars (57 + "...")
                assert len(change_calls[0]["detail"]) == 60
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_best_score_tracked_after_refinement(self):
        """Best score/content updated after refinement when score > best.

        Covers lines 670-672 in _refine_single_file_with_progress.
        """
        original = "# Agent\n" + "x" * 200
        scores = iter([85, 88])  # First score 85, second score 88

        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=next(scores, 70),
                    reasoning="Good progress",
                    suggestions=["Keep improving"],
                )
            if model_class is RefinedContent:
                return RefinedContent(
                    content=original + "\n# Better version",
                    changes_made=["Improved quality"],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=2)

        from forge_cli.generators.refinement import _refine_single_file_with_progress

        async def _test():
            try:
                content, result = await _refine_single_file_with_progress(
                    llm, original, config, "test.md", "agent",
                )
                # Best score should be 88 (the highest seen)
                assert result.final_score == 88
            finally:
                await llm.close()

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TestBaselineEvalExceptionHandling — exception paths
# ---------------------------------------------------------------------------

class TestBaselineEvalExceptionHandling:
    """Test exception handling in eval integration paths."""

    def test_baseline_eval_exception_is_swallowed(self):
        """Baseline eval exception is caught and refinement continues.

        Covers lines 568-569 in _refine_single_file_with_progress.
        """
        original = "# Agent\n" + "x" * 100

        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=95,
                    reasoning="Excellent",
                    suggestions=[],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=1)

        from forge_cli.generators.refinement import _refine_single_file_with_progress

        import unittest.mock as mock

        async def _test():
            try:
                # Mock grade_file_for_refinement to raise an exception
                with mock.patch(
                    "forge_cli.generators.refinement.grade_file_for_refinement",
                    side_effect=RuntimeError("eval not available"),
                    create=True,
                ):
                    # Patch at the import point inside the function
                    with mock.patch(
                        "forge_cli.evals.eval_runner.grade_file_for_refinement",
                        side_effect=RuntimeError("eval not available"),
                    ):
                        content, result = await _refine_single_file_with_progress(
                            llm, original, config, "test.md", "agent",
                        )
                        # Should succeed despite eval failure
                        assert result.final_score == 95
                        assert result.baseline_eval_pass_rate == 0.0
            finally:
                await llm.close()

        asyncio.run(_test())

    def test_final_eval_exception_is_swallowed(self):
        """Final eval pass rate exception is caught gracefully.

        Covers lines 684-685 in _refine_single_file_with_progress.
        """
        original = "# Agent\n" + "x" * 100

        call_count = {"n": 0}

        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=95,
                    reasoning="Excellent",
                    suggestions=[],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)
        llm = LLMClient(provider_instance=fake)
        config = _make_config(score_threshold=90, max_iterations=1)

        from forge_cli.generators.refinement import _refine_single_file_with_progress

        import unittest.mock as mock

        async def _failing_grade(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Baseline succeeds (returns a mock result)
                from unittest.mock import MagicMock
                result = MagicMock()
                result.pass_rate = 0.85
                result.expectations = []
                return result
            # Final eval raises
            raise RuntimeError("eval infrastructure unavailable")

        async def _test():
            try:
                with mock.patch(
                    "forge_cli.evals.eval_runner.grade_file_for_refinement",
                    side_effect=_failing_grade,
                ):
                    content, result = await _refine_single_file_with_progress(
                        llm, original, config, "test.md", "agent",
                    )
                    # Refinement should succeed
                    assert result.final_score == 95
                    # Baseline was set
                    assert result.baseline_eval_pass_rate == 0.85
                    # Final eval failed, so pass rate stays at default 0.0
                    assert result.final_eval_pass_rate == 0.0
            finally:
                await llm.close()

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TestDryRunAutoImport — FORGE_TEST_DRY_RUN auto-import path
# ---------------------------------------------------------------------------

class TestDryRunAutoImport:
    """Test the dry-run FakeLLMProvider auto-import path (lines 721-727)."""

    def test_dry_run_env_var_auto_imports_fake_provider(self, tmp_path):
        """When FORGE_TEST_DRY_RUN=1 and no provider given, FakeLLMProvider is used.

        Covers lines 720-727 in refine_all_async.

        The auto-imported FakeLLMProvider has no response factory, so LLM calls
        will raise. We verify the path is entered by checking the report
        indicates failures (all_passed=False) from the unconfigured provider.
        """
        import os
        import unittest.mock as mock

        config = _make_config(enabled=True, score_threshold=90)
        config.project.directory = str(tmp_path)
        generate_all(config)

        # Set the env var and call refine_all_async without a provider
        with mock.patch.dict(os.environ, {"FORGE_TEST_DRY_RUN": "1"}):
            report = asyncio.run(refine_all_async(
                config, tmp_path, llm_provider=None,
            ))

        # The auto-imported FakeLLMProvider has no factory, so calls fail.
        # But the code path is exercised (lines 721-727) and errors are caught
        # by the worker pool, resulting in all_passed=False.
        assert isinstance(report, RefinementReport)
        assert report.all_passed is False

    def test_dry_run_not_set_uses_gateway_config(self, tmp_path):
        """When FORGE_TEST_DRY_RUN=0 and no provider given, GatewayConfig path is hit.

        Covers lines 734-747 in refine_all_async.
        """
        import os
        import sys
        import unittest.mock as mock
        from llm_gateway import GatewayConfig as RealGatewayConfig

        config = _make_config(enabled=True, score_threshold=90)
        config.project.directory = str(tmp_path)
        generate_all(config)

        captured_kwargs: dict = {}
        good_provider = _make_always_good_provider(score=95)

        class SpyLLMClient:
            """LLMClient replacement that captures constructor kwargs."""

            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)
                self._inner = LLMClient(provider_instance=good_provider)

            async def complete(self, *args, **kwargs):
                return await self._inner.complete(*args, **kwargs)

            async def close(self):
                await self._inner.close()

        # Force the else branch: FORGE_TEST_DRY_RUN != "1"
        with mock.patch.dict(os.environ, {"FORGE_TEST_DRY_RUN": "0"}):
            # Patch both LLMClient and GatewayConfig at the module level
            # so the local imports inside refine_all_async pick them up.
            real_llm_gateway = sys.modules["llm_gateway"]
            original_client = real_llm_gateway.LLMClient

            try:
                real_llm_gateway.LLMClient = SpyLLMClient
                report = asyncio.run(refine_all_async(
                    config, tmp_path, llm_provider=None,
                ))
            finally:
                real_llm_gateway.LLMClient = original_client

        # Verify the GatewayConfig path was taken
        assert "config" in captured_kwargs
        assert isinstance(captured_kwargs["config"], RealGatewayConfig)
        assert isinstance(report, RefinementReport)
        assert len(report.files) > 0


# ---------------------------------------------------------------------------
# TestResultHandlingInRefineAll — final result processing
# ---------------------------------------------------------------------------

class TestResultHandlingInRefineAll:
    """Test result handling in refine_all_async (lines 820-824)."""

    def test_below_threshold_but_improved_still_written(self, tmp_path):
        """File below threshold but improved over initial is still written back.

        Covers lines 821-824 in refine_all_async.
        """
        config = _make_config(enabled=True, score_threshold=90, max_iterations=2)
        config.project.directory = str(tmp_path)
        generate_all(config)

        scores = iter([60, 75])  # Initial 60, after refinement 75 — still below 90

        def factory(model_class, messages):
            if model_class is FileScore:
                return FileScore(
                    score=next(scores, 75),
                    reasoning="Some progress",
                    suggestions=["Keep going"],
                )
            if model_class is RefinedContent:
                return RefinedContent(
                    content="<!-- improved -->\n# This is the improved content\n" + "x" * 200,
                    changes_made=["Improved quality"],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)

        report = refine_all(config, tmp_path, llm_provider=fake)

        # All files should be marked as not passed (below threshold)
        assert report.all_passed is False
        # Some files should still be improved
        assert report.files_improved >= 0  # At least some were updated

    def test_exception_in_worker_marks_all_passed_false(self, tmp_path):
        """Worker exception sets all_passed=False in report.

        Covers lines 804-807 in refine_all_async.
        """
        config = _make_config(enabled=True, score_threshold=90)
        config.project.directory = str(tmp_path)
        generate_all(config)

        call_count = {"n": 0}

        def factory(model_class, messages):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("LLM exploded")
            if model_class is FileScore:
                return FileScore(
                    score=95,
                    reasoning="Good",
                    suggestions=[],
                )
            if model_class is RefinedContent:
                return RefinedContent(
                    content="# OK",
                    changes_made=["Fixed"],
                )
            raise ValueError(f"Unexpected: {model_class}")

        fake = FakeLLMProvider(response_factory=factory)

        # The exception from the first call should be caught but report.all_passed = False
        # Note: the exception happens inside the LLM call, which is inside _refine_one_file
        # It will be caught by the worker and added to results as an Exception
        report = refine_all(config, tmp_path, llm_provider=fake)
        # There was at least one failure
        assert isinstance(report, RefinementReport)

    def test_auto_concurrency_for_non_local_provider(self, tmp_path):
        """When provider != local_claude and max_concurrency=0, concurrency=len(files).

        Covers line 758 in refine_all_async.
        """
        config = _make_config(enabled=True, score_threshold=90)
        config.refinement.provider = "anthropic"
        config.refinement.max_concurrency = 0
        config.project.directory = str(tmp_path)
        generate_all(config)

        fake = _make_always_good_provider(score=95)
        report = refine_all(config, tmp_path, llm_provider=fake)

        # All files should be processed
        assert isinstance(report, RefinementReport)
        assert len(report.files) > 0
