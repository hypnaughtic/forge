"""Scenario 21: Compaction + stop/resume interaction.

Tests that compaction events and activity logs survive a full stop/resume
cycle. Verifies that compaction_needed events persist on disk across both
transitions, session.json remains valid, and the session can be resumed.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.feedback_collector import FeedbackCollector
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestCompactionPlusStopResume:

    @pytest.mark.timeout(600)
    def test_compaction_survives_stop_resume_cycle(
        self,
        compaction_project: tuple[Path, object],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: FeedbackCollector,
    ) -> None:
        """Start session, wait for compaction events, stop, resume, and
        verify that events and session.json persist across the cycle."""
        project_dir, config = compaction_project
        orch = compaction_orchestrator
        val = compaction_validator

        # -- PHASE 1: Start session and wait for compaction events --
        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # Wait for compaction_needed events
        assert orch.tmux is not None, "tmux session must be alive"
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
            "No compaction_needed events found within timeout -- "
            "compaction should trigger with threshold=500"
        )

        # -- PHASE 2: Verify event structure before stop --
        snap_after_compaction = orch.capture_state()
        assert len(snap_after_compaction.compaction_events) >= 1
        event = snap_after_compaction.compaction_events[0]
        assert event.get("type") == "compaction_needed"
        event_count_before_stop = len(snap_after_compaction.compaction_events)

        # Verify activity logs exist
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # -- PHASE 3: Stop gracefully --
        orch.stop_gracefully(timeout=90)

        # Verify session.json persisted after stop
        val.assert_session_exists()

        # -- PHASE 4: Resume --
        snap_resumed = orch.resume_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # -- ASSERTIONS --

        # 1. Session is running after resume
        val.assert_session_status("running")

        # 2. Events persist across stop/resume (they're files on disk)
        snap_after_resume = orch.capture_state()
        assert len(snap_after_resume.compaction_events) >= event_count_before_stop, (
            f"Compaction events lost across stop/resume: "
            f"before={event_count_before_stop}, "
            f"after={len(snap_after_resume.compaction_events)}"
        )

        # 3. session.json survived
        assert snap_after_resume.session_json is not None, (
            "session.json missing after resume"
        )

        # 4. Activity logs persist
        activity_logs_after = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs_after) >= 1, (
            "Activity logs should persist across stop/resume"
        )

        orch.save_transcripts("scenario_21_compaction_plus_stop_resume")
