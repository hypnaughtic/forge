"""Tests for the progress display module."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from forge_cli.progress import (
    ForgeProgress,
    ForgeRefinementProgress,
    RefinementFileState,
    StepInfo,
)


# =============================================================================
# StepInfo dataclass
# =============================================================================


class TestStepInfo:
    """Tests for the StepInfo dataclass."""

    def test_defaults(self):
        """Verify default values."""
        info = StepInfo(name="test", description="Test step")
        assert info.status == "pending"
        assert info.detail == ""
        assert info.files_total == 0
        assert info.files_done == 0

    def test_custom_values(self):
        """Verify custom values are set."""
        info = StepInfo(
            name="gen",
            description="Generating",
            status="running",
            detail="agents",
            files_total=8,
            files_done=3,
        )
        assert info.name == "gen"
        assert info.files_total == 8
        assert info.files_done == 3


# =============================================================================
# ForgeProgress
# =============================================================================


class TestForgeProgress:
    """Tests for the generation progress display."""

    def test_disabled_progress(self):
        """Disabled progress does nothing but still yields."""
        progress = ForgeProgress(enabled=False)
        with progress.live() as p:
            assert p is progress
            with p.step("test", "Test step") as info:
                assert info.status == "running"
            assert info.status == "done"

    def test_step_lifecycle(self):
        """Step transitions from running to done."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        progress = ForgeProgress(console=console, enabled=False)
        with progress.live():
            with progress.step("gen", "Generating files") as info:
                assert info.status == "running"
            assert info.status == "done"

    def test_step_error_handling(self):
        """Step transitions to error on exception."""
        progress = ForgeProgress(enabled=False)
        with progress.live():
            with (
                __import__("pytest").raises(ValueError),
                progress.step("fail", "Failing step") as info,
            ):
                raise ValueError("test error")
            assert info.status == "error"

    def test_update_changes_detail(self):
        """update() modifies current step detail."""
        progress = ForgeProgress(enabled=False)
        with progress.live():
            with progress.step("gen", "Generating", total_files=5) as info:
                progress.update(detail="agent-1.md", files_done=1)
                assert info.detail == "agent-1.md"
                assert info.files_done == 1

    def test_update_without_active_step(self):
        """update() is a no-op when no step is running."""
        progress = ForgeProgress(enabled=False)
        with progress.live():
            progress.update(detail="orphan")  # should not crash

    def test_skip_marks_step(self):
        """skip() adds a skipped step."""
        progress = ForgeProgress(enabled=False)
        with progress.live():
            progress.skip("ctx", "Context summarization")
        assert any(s.status == "skipped" for s in progress._steps)

    def test_build_display_all_states(self):
        """_build_display handles all step statuses."""
        progress = ForgeProgress(enabled=False)
        progress._steps = [
            StepInfo(name="a", description="Done step", status="done", detail="ok"),
            StepInfo(name="b", description="Running step", status="running", detail="file.md", files_total=5, files_done=2),
            StepInfo(name="c", description="Error step", status="error", detail="failed"),
            StepInfo(name="d", description="Skipped step", status="skipped"),
            StepInfo(name="e", description="Pending step", status="pending"),
        ]
        table = progress._build_display()
        assert table.row_count == 5

    def test_live_prints_final_table(self):
        """Live context manager prints final display after exiting."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = ForgeProgress(console=console, enabled=True)
        with progress.live():
            with progress.step("gen", "Generating") as info:
                progress.update(detail="done")
        # After live exits, final table is printed
        text = output.getvalue()
        assert "Generating" in text


# =============================================================================
# RefinementFileState dataclass
# =============================================================================


class TestRefinementFileState:
    """Tests for the RefinementFileState dataclass."""

    def test_defaults(self):
        """Verify default values."""
        state = RefinementFileState(file_name="test.md")
        assert state.current_score == 0
        assert state.initial_score == 0
        assert state.target_score == 90
        assert state.status == "waiting"
        assert state.iteration == 0

    def test_custom_values(self):
        """Verify custom values."""
        state = RefinementFileState(
            file_name="agent.md",
            current_score=85,
            initial_score=70,
            target_score=90,
            iteration=2,
            max_iterations=5,
            status="refining",
            last_change="Added domain patterns",
        )
        assert state.current_score == 85
        assert state.last_change == "Added domain patterns"


# =============================================================================
# ForgeRefinementProgress
# =============================================================================


class TestForgeRefinementProgress:
    """Tests for the refinement progress display."""

    def _make_progress(self) -> ForgeRefinementProgress:
        """Create a progress instance with captured output."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        return ForgeRefinementProgress(console=console)

    def test_register_and_start_file(self):
        """register_file + start_file transitions correctly."""
        progress = self._make_progress()
        progress.register_file("agents/test.md")
        assert progress._files["agents/test.md"].status == "waiting"

        progress.start_file("agents/test.md")
        assert progress._files["agents/test.md"].status == "scoring"

    def test_start_file_without_register(self):
        """start_file auto-registers if not already registered."""
        progress = self._make_progress()
        progress.start_file("agents/new.md", target_score=85)
        assert "agents/new.md" in progress._files
        assert progress._files["agents/new.md"].status == "scoring"

    def test_update_score(self):
        """update_score tracks scores and iterations."""
        progress = self._make_progress()
        progress.start_file("test.md")
        progress.update_score("test.md", score=75, iteration=1, detail="needs work")
        fp = progress._files["test.md"]
        assert fp.current_score == 75
        assert fp.initial_score == 75  # first score sets initial
        assert fp.iteration == 1
        assert fp.last_change == "needs work"

        progress.update_score("test.md", score=85, iteration=2)
        assert fp.current_score == 85
        assert fp.initial_score == 75  # initial doesn't change

    def test_update_score_unknown_file(self):
        """update_score is a no-op for unknown files."""
        progress = self._make_progress()
        progress.update_score("unknown.md", score=80, iteration=1)  # no crash

    def test_complete_file_passed(self):
        """complete_file marks file as done and tracks passed."""
        progress = self._make_progress()
        progress.start_file("test.md", target_score=90)
        progress.update_score("test.md", score=85, iteration=1)
        progress.complete_file("test.md", final_score=92)
        assert progress._files["test.md"].status == "done"
        assert progress._completed_files == 1
        assert progress._passed_files == 1
        assert progress._below_files == 0

    def test_complete_file_below_threshold(self):
        """complete_file tracks below-threshold files."""
        progress = self._make_progress()
        progress.start_file("test.md", target_score=90)
        progress.complete_file("test.md", final_score=80)
        assert progress._below_files == 1
        assert progress._passed_files == 0

    def test_complete_unknown_file(self):
        """complete_file is a no-op for unknown files."""
        progress = self._make_progress()
        progress.complete_file("unknown.md", final_score=95)  # no crash

    def test_fail_file(self):
        """fail_file marks file as failed."""
        progress = self._make_progress()
        progress.start_file("test.md")
        progress.fail_file("test.md", reason="LLM timeout")
        assert progress._files["test.md"].status == "failed"
        assert progress._failed_files == 1
        assert progress._completed_files == 1

    def test_fail_unknown_file(self):
        """fail_file is a no-op for unknown files."""
        progress = self._make_progress()
        progress.fail_file("unknown.md", reason="test")  # no crash

    def test_render_file_row_all_statuses(self):
        """_render_file_row handles all status types."""
        # Done + passed
        fp = RefinementFileState("test.md", current_score=95, initial_score=80, target_score=90, status="done")
        icon, status, score_str, _, detail, _ = ForgeRefinementProgress._render_file_row(fp, "test.md")
        assert "✓" in icon.plain
        assert "passed" in detail.plain

        # Done + below threshold
        fp.current_score = 85
        icon, status, score_str, _, detail, _ = ForgeRefinementProgress._render_file_row(fp, "test.md")
        assert "▲" in icon.plain
        assert "best: 85" in detail.plain

        # Failed
        fp.status = "failed"
        fp.last_change = "timeout"
        icon, status, _, _, detail, _ = ForgeRefinementProgress._render_file_row(fp, "test.md")
        assert "✗" in icon.plain
        assert "timeout" in detail.plain

        # Scoring (with initial score)
        fp.status = "scoring"
        fp.initial_score = 80
        icon, status, score_str, _, _, _ = ForgeRefinementProgress._render_file_row(fp, "test.md")
        assert "80" in score_str

        # Scoring (no initial score)
        fp.initial_score = 0
        icon, status, score_str, _, _, _ = ForgeRefinementProgress._render_file_row(fp, "test.md")
        assert "…" in score_str

        # Refining
        fp.status = "refining"
        fp.initial_score = 80
        fp.current_score = 85
        icon, status, score_str, _, _, _ = ForgeRefinementProgress._render_file_row(fp, "test.md")
        assert "85" in score_str

        # Waiting
        fp.status = "waiting"
        icon, status, score_str, _, _, iter_str = ForgeRefinementProgress._render_file_row(fp, "test.md")
        assert iter_str == ""

    def test_build_live_display(self):
        """_build_live_display shows only active files."""
        progress = self._make_progress()
        progress.register_file("a.md")
        progress.start_file("b.md")
        progress.update_score("b.md", score=80, iteration=1, status="refining")
        progress.start_file("c.md")

        table = progress._build_live_display()
        # Should show b.md (refining) and c.md (scoring) + summary row
        assert table.row_count >= 2

    def test_build_final_display(self):
        """_build_final_display shows all files."""
        progress = self._make_progress()
        progress.start_file("a.md")
        progress.complete_file("a.md", final_score=95)
        progress.start_file("b.md")
        progress.fail_file("b.md", reason="error")

        table = progress._build_final_display()
        # All files + summary row
        assert table.row_count >= 2

    def test_track_context_manager(self):
        """track() context manager works end-to-end."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = ForgeRefinementProgress(console=console)

        with progress.track(total_files=2):
            progress.register_file("a.md")
            progress.register_file("b.md")
            progress.start_file("a.md")
            progress.update_score("a.md", score=92, iteration=1)
            progress.complete_file("a.md", final_score=92)
            progress.start_file("b.md")
            progress.complete_file("b.md", final_score=95)

        text = output.getvalue()
        assert "2 passed" in text or "2/2" in text

    def test_print_completed_row_long_error(self):
        """_print_completed_row truncates long error messages."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = ForgeRefinementProgress(console=console)

        fp = RefinementFileState(
            file_name="test.md",
            status="failed",
            last_change="A" * 100,
            iteration=1,
            max_iterations=3,
        )
        progress._print_completed_row(fp)
        text = output.getvalue()
        assert "..." in text

    def test_print_completed_row_non_terminal_status(self):
        """_print_completed_row skips non-terminal statuses."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = ForgeRefinementProgress(console=console)

        fp = RefinementFileState(file_name="test.md", status="scoring")
        progress._print_completed_row(fp)
        assert output.getvalue() == ""
