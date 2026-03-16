"""Scenario 15: Compaction during active work -- session survives.

Tests that when compaction fires while agents are mid-task (actively
modifying files), the session remains stable, compaction_needed events
are emitted, activity logs exist, and no corrupted half-written .tmp
files remain in the project directory.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestCompactionMidTask:

    @pytest.mark.timeout(300)
    def test_compaction_during_active_work_preserves_partial_state(
        self,
        compaction_project: tuple[Path, object],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: object,
    ) -> None:
        """Start session, let agents work, wait for compaction_needed events.

        Verify:
        1. Compaction events fire (compaction_needed type)
        2. Activity logs exist
        3. No corrupted/half-written files (.tmp) in project directory
        4. Session survived
        """
        project_dir, config = compaction_project
        orch = compaction_orchestrator

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True, agent_activity_timeout=180,
        )

        # -- Phase 1: Watch for active file operations --
        timeline = orch.watch_terminals(duration=60, interval=10)
        assert len(timeline) > 0, "Should have captured terminal snapshots"

        # -- Phase 2: Wait for compaction_needed events --
        compaction_detected = False
        checkpoints_dir = project_dir / ".forge" / "checkpoints"

        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(5)

        assert compaction_detected, (
            "No compaction_needed events found within timeout -- "
            "agent did not generate enough context to trigger compaction"
        )

        # -- Phase 3: Verify event structure --
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1
        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"

        # -- Phase 4: Verify activity logs exist --
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # -- Phase 5: No corrupted / half-written files --
        tmp_files = list(project_dir.rglob("*.tmp"))
        # Exclude .forge internals -- only check project source files
        project_tmp_files = [
            f for f in tmp_files
            if ".forge" not in str(f) and ".git" not in str(f)
        ]
        assert len(project_tmp_files) == 0, (
            f"Found {len(project_tmp_files)} .tmp files in project directory "
            f"(possible half-written files): {project_tmp_files}"
        )

        # -- Phase 6: Session survived --
        assert orch.tmux is not None
        assert orch.tmux.is_alive(), (
            "tmux session died after compaction during active work"
        )

        orch.save_transcripts("scenario_15_compaction_mid_task")
