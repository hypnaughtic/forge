"""Scenario 23: Full project build with compaction -- THE MOST IMPORTANT TEST.

Tests that a real project build (calculator CLI) survives compaction cycles
without degradation. Agents should produce actual .py files, compaction
events should fire at least once with the low threshold, Python files should
remain valid (compile-able) and non-truncated, and agents should continue
working after compaction rather than stalling or crashing.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.feedback_collector import FeedbackCollector
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestFullProjectBuildWithCompaction:

    @pytest.mark.timeout(600)
    def test_real_project_build_survives_compaction(
        self,
        compaction_project: tuple[Path, object],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: FeedbackCollector,
    ) -> None:
        """Start a compaction-configured session (calculator CLI project),
        let it run for up to 8 minutes, and verify that:
        1. Project files are actually created (.py files)
        2. At least one compaction event occurred
        3. Code quality is not degraded -- .py files are valid Python
        4. Activity logs exist (agents were working)
        5. Session is still running or complete (not crashed)
        """
        project_dir, config = compaction_project
        orch = compaction_orchestrator
        val = compaction_validator

        # -- PHASE 1: Start session --
        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # -- PHASE 2: Let agents build for up to 8 minutes --
        orch.watch_terminals(duration=480, interval=30)

        # -- PHASE 3: Capture final state --
        snap_final = orch.capture_state()

        # -- ASSERTION 1: Project files actually created --
        # Glob for .py files in project_dir (excluding .forge internals,
        # .git, __pycache__, and node_modules)
        all_py_files = [
            f for f in project_dir.rglob("*.py")
            if ".forge" not in str(f)
            and ".git" not in str(f)
            and "__pycache__" not in str(f)
            and "node_modules" not in str(f)
            and "transcripts" not in str(f)
        ]
        assert len(all_py_files) > 0, (
            "No .py files were created in the project directory -- "
            "agents failed to produce any code"
        )

        # -- ASSERTION 2: At least one compaction event occurred --
        assert len(snap_final.compaction_events) >= 1, (
            "No compaction_needed events occurred during the 8-minute build -- "
            "threshold may be too high or agents did not generate enough "
            "context"
        )

        # Verify event structure
        event = snap_final.compaction_events[0]
        assert event.get("type") == "compaction_needed"

        # -- ASSERTION 3: Code quality not degraded by compaction --
        # Check that .py files are valid Python (compile-able) and not
        # truncated (size > 10 bytes)
        invalid_files: list[str] = []
        truncated_files: list[str] = []

        for py_file in all_py_files:
            # __init__.py files are legitimately 0 bytes
            if py_file.name == "__init__.py":
                continue

            # Check for truncation
            file_size = py_file.stat().st_size
            if file_size <= 10:
                truncated_files.append(
                    f"{py_file.relative_to(project_dir)} ({file_size} bytes)"
                )
                continue

            # Check for valid Python syntax
            try:
                source = py_file.read_text(encoding="utf-8")
                compile(source, str(py_file), "exec")
            except (SyntaxError, UnicodeDecodeError) as exc:
                invalid_files.append(
                    f"{py_file.relative_to(project_dir)}: {exc}"
                )

        assert len(truncated_files) == 0, (
            f"Found {len(truncated_files)} truncated .py files (<=10 bytes): "
            f"{truncated_files}"
        )
        assert len(invalid_files) == 0, (
            f"Found {len(invalid_files)} .py files with invalid Python "
            f"syntax: {invalid_files}"
        )

        # -- ASSERTION 4: Activity logs exist (agents were working) --
        checkpoints_dir = project_dir / ".forge" / "checkpoints"
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"
        total_bytes = sum(f.stat().st_size for f in activity_logs)
        assert total_bytes > 0, "Activity logs are empty"

        # -- ASSERTION 5: Session still running or complete (not crashed) --
        session_data = val.assert_session_exists()
        session_status = session_data.get("status", "")
        assert session_status in ("running", "complete", "stopped"), (
            f"Session status is '{session_status}' -- expected 'running', "
            f"'complete', or 'stopped' (not crashed/error)"
        )

        # If tmux is still alive, the session is running
        if orch.tmux and orch.tmux.is_alive():
            assert session_status in ("running", "complete"), (
                f"tmux session is alive but session status is "
                f"'{session_status}'"
            )

        orch.save_transcripts("scenario_23_full_project_build")
