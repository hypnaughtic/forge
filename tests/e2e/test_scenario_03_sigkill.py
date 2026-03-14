"""Scenario 3: SIGKILL (Laptop Death Simulation).

Tests: forge start -> work -> kill -9 -> verify activity logs -> forge resume -> verify recovery.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestSigkill:

    def test_sigkill_recovery_from_activity_logs_and_git_state(
        self, mvp_project, orchestrator, validator
    ):
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=60, interval=10)

        snap_before = orchestrator.capture_state()

        # -- SIGKILL all Claude processes --
        snap_after_kill = orchestrator.kill_processes()

        # -- VERIFY: activity logs have entries (written by hooks) --
        checkpoints_dir = project_dir / ".forge" / "checkpoints"
        if checkpoints_dir.exists():
            for activity_file in checkpoints_dir.glob("*.activity.jsonl"):
                lines = activity_file.read_text().strip().split("\n")
                assert len(lines) > 0, \
                    f"Activity log {activity_file.name} should have entries"
                for line in lines:
                    if line.strip():
                        entry = json.loads(line)
                        assert "timestamp" in entry
                        assert "tool" in entry

        # -- Resume from activity logs + git state --
        snap_after_resume = orchestrator.resume_session(wait_for_agents=True)

        # Git state should be intact (committed work survives SIGKILL)
        assert len(snap_after_resume.git_log) >= len(snap_before.git_log), \
            "Git commits should survive SIGKILL"

        validator.assert_session_status("running")
        orchestrator.save_transcripts("scenario_03_sigkill")
