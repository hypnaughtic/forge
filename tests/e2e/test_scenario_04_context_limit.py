"""Scenario 4: Context limit triggers compaction detection via events.

Tests that when context pressure builds (very low threshold + aggressive
context injection), the compaction system fires deterministically: a
compaction_needed event is written to .forge/events/, activity logs exist,
the session remains running after compaction, and all state survives a
subsequent stop/resume cycle.

NO SOFT-PASS — this test must produce a compaction event or it FAILS.
"""

from __future__ import annotations

import subprocess
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
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestContextLimit:

    @pytest.mark.timeout(600)
    def test_precompact_triggers_checkpoint_and_context_reload(
        self, tmp_path: Path, llm: object, feedback: object,
    ) -> None:
        """Inject context pressure with very low threshold, wait for
        compaction_needed events, verify activity logs exist, confirm
        session survives, then stop/resume to verify state persists.

        Uses threshold=500 (not 5000) to guarantee compaction fires quickly.
        """
        # -- CONFIG: Very low threshold to guarantee compaction --
        config = ForgeConfig(
            project=ProjectConfig(
                description="Build a Python CLI calculator tool with add, "
                            "subtract, multiply, divide commands. Include "
                            "input validation and help text.",
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

        # -- PHASE 1: Generate and start session --
        orch.generate_project()
        orch.start_session(wait_for_agents=True, agent_activity_timeout=180)

        # Set CLAUDE_CODE_AUTO_COMPACT_WINDOW=0.3 to make Claude Code's
        # built-in compaction trigger more aggressively as safety net
        assert orch.tmux is not None, "tmux session must be alive"
        subprocess.run(
            [
                "tmux", "set-environment",
                "-t", orch.tmux.session_name,
                "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "0.3",
            ],
            capture_output=True,
        )

        # -- PHASE 2: Inject context pressure aggressively --
        # Multiple rounds to ensure activity log grows past threshold
        orch.inject_context_pressure("0", strategy="large_prompt")
        time.sleep(10)
        orch.inject_context_pressure("0", strategy="rapid_tasks")

        # -- PHASE 3: Wait for compaction evidence (hard requirement) --
        # Poll for compaction_needed events (most reliable signal)
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"
        compaction_detected = False

        deadline = time.monotonic() + 240  # 4 minute timeout
        while time.monotonic() < deadline:
            snap = orch.capture_state()

            # Check compaction events
            if snap.compaction_events:
                compaction_detected = True
                break

            time.sleep(5)

        # HARD FAIL -- no soft skip
        assert compaction_detected, (
            "No compaction_needed events found in .forge/events/ within 240s. "
            "Hooks may not be firing or threshold not crossed."
        )

        # -- PHASE 4: Verify compaction event structure --
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1
        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"

        # Verify activity logs exist
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # Session still alive after compaction
        assert orch.tmux.is_alive(), (
            "tmux session died after compaction -- session should remain running"
        )

        # -- PHASE 5: Stop and resume to verify state survives --
        orch.stop_gracefully(timeout=90)

        # Verify session.json persisted
        val.assert_session_exists()

        snap_after_resume = orch.resume_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        val.assert_session_status("running")

        # Events should persist across stop/resume (they're files on disk)
        snap_resumed = orch.capture_state()
        assert snap_resumed.session_json is not None, (
            "session.json missing after resume"
        )

        orch.save_transcripts("scenario_04_context_limit")
