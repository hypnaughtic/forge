"""Scenario 19: Compaction events fire and session state remains intact.

Tests: forge start -> agent works -> compaction_needed events fire ->
verify events have correct structure, activity logs exist, session
survives, and session.json is valid.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.feedback_collector import FeedbackCollector
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestCompactionCheckpointIntegrity:

    @pytest.mark.timeout(300)
    def test_checkpoint_fields_preserved_after_compaction_cycle(
        self,
        compaction_project: tuple[Path, ...],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: FeedbackCollector,
    ) -> None:
        """Verify compaction events fire, have correct structure, activity
        logs exist, and the session remains alive."""
        project_dir, config = compaction_project
        orch = compaction_orchestrator
        val = compaction_validator

        # -- PHASE 1: Start session, wait for agents to begin working --
        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # Let agents work to accumulate state
        assert orch.tmux is not None, "tmux session must be alive"
        orch.watch_terminals(duration=30, interval=10)

        # -- PHASE 2: Wait for compaction_needed events --
        compaction_detected = False
        checkpoints_dir = project_dir / ".forge" / "checkpoints"

        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(5)

        assert compaction_detected, (
            "No compaction_needed events found within 240s timeout"
        )

        # -- PHASE 3: Verify event structure --
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1
        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"
        assert "agent_name" in event
        assert "agent_type" in event

        # -- PHASE 4: Verify activity logs exist --
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"
        total_bytes = sum(f.stat().st_size for f in activity_logs)
        assert total_bytes > 0, "Activity logs are empty"

        # -- PHASE 5: Verify session.json exists --
        val.assert_session_exists()

        # -- PHASE 6: Session survived --
        assert orch.tmux.is_alive(), (
            "tmux session died after compaction events"
        )

        orch.save_transcripts("scenario_19_compaction_checkpoint_integrity")
