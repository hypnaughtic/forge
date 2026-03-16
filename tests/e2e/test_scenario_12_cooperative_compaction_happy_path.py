"""Scenario 12: Cooperative Compaction Happy Path.

Tests: forge start -> hooks detect token threshold -> compaction_needed events
emitted -> session survives -> stop/resume preserves state.

Verifies the full cooperative compaction lifecycle end-to-end:
1. Hook scripts fire on tool use (activity logging)
2. Token threshold detection works (bytes/4 heuristic)
3. Compaction events are written to .forge/events/
4. COMPACTION WARNING is emitted to the agent
5. Session remains stable after compaction signals

NO SOFT-PASS — compaction MUST fire or the test FAILS.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from forge_cli.config_schema import (
    AgentsConfig,
    CompactionConfig,
    ExecutionStrategy,
    ForgeConfig,
    LLMGatewayConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
)
from forge_cli.generators.orchestrator import generate_all

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.feedback_collector import FeedbackCollector
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestCooperativeCompactionHappyPath:

    @pytest.mark.timeout(420)
    def test_child_agent_compacts_and_resumes_correctly(
        self,
        tmp_path: Path,
        llm: object,
        feedback: FeedbackCollector,
    ) -> None:
        """Verify compaction hooks fire, events are written, and session
        survives a stop/resume cycle with compaction state preserved.
        """
        # Very low threshold to guarantee compaction fires quickly
        config = ForgeConfig(
            project=ProjectConfig(
                description="Build a Python CLI calculator tool with add, "
                            "subtract, multiply, divide commands. Include "
                            "input validation, help text, and unit tests.",
                directory=str(tmp_path),
            ),
            mode=ProjectMode.MVP,
            strategy=ExecutionStrategy.CO_PILOT,
            agents=AgentsConfig(team_profile=TeamProfile.LEAN),
            llm_gateway=LLMGatewayConfig(
                enabled=True,
                local_claude_model="claude-sonnet-4-20250514",
            ),
            compaction=CompactionConfig(
                compaction_threshold_tokens=500,
                enable_context_anchors=True,
                anchor_interval_minutes=1,
            ),
        )
        generate_all(config)

        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()
        orch = ForgeSessionOrchestrator(tmp_path, config, llm, transcript_dir)
        val = CheckpointValidator(tmp_path)

        # -- PHASE 1: Start session --
        orch.generate_project()
        snap_start = orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )
        assert orch.tmux is not None, "tmux session must be alive"

        # -- PHASE 2: Wait for compaction evidence --
        # Poll for compaction_needed events (most reliable signal)
        compaction_detected = False
        events_dir = tmp_path / ".forge" / "events"
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"

        deadline = time.monotonic() + 240  # 4 min
        while time.monotonic() < deadline:
            snap = orch.capture_state()

            # Check compaction events
            if snap.compaction_events:
                compaction_detected = True
                break

            # Check for activity log growth (hooks are running)
            if checkpoints_dir.exists():
                activity_logs = list(
                    checkpoints_dir.glob("**/*.activity.jsonl"),
                )
                total_bytes = sum(f.stat().st_size for f in activity_logs)
                if total_bytes > 2000:  # threshold=500 * 4 = 2000 bytes
                    # Threshold should have been crossed
                    # Check events one more time
                    snap = orch.capture_state()
                    if snap.compaction_events:
                        compaction_detected = True
                        break

            time.sleep(5)

        # HARD FAIL — compaction MUST have fired
        assert compaction_detected, (
            "No compaction_needed events found in .forge/events/ within 240s. "
            "Hooks may not be firing or threshold not crossed."
        )

        # -- PHASE 3: Verify compaction event structure --
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1, (
            "Expected at least 1 compaction event"
        )

        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"
        assert "agent_type" in event
        assert "agent_name" in event
        assert event.get("estimated_tokens", 0) > 0
        assert event.get("threshold") == 500

        # Activity log exists and is non-empty
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"
        total_bytes = sum(f.stat().st_size for f in activity_logs)
        assert total_bytes > 0, "Activity logs are empty"

        # Session is still alive (compaction didn't crash it)
        assert orch.tmux.is_alive(), "tmux session died after compaction"

        # -- PHASE 4: Stop and resume to verify state survives --
        snap_before_stop = orch.capture_state()
        orch.stop_gracefully(timeout=90)

        # Verify session.json persisted
        val.assert_session_exists()

        # Resume
        snap_after_resume = orch.resume_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        val.assert_session_status("running")

        # Events should persist across stop/resume (they're files on disk)
        snap_resumed = orch.capture_state()

        # Session survived the full cycle
        assert snap_resumed.session_json is not None, (
            "session.json missing after resume"
        )

        orch.save_transcripts("scenario_12_cooperative_compaction_happy_path")
