"""Scenario 17: Team Leader compaction detection via events.

Tests the Team Leader's compaction path. Uses a low compaction threshold
(300 tokens) and sets CLAUDE_CODE_AUTO_COMPACT_WINDOW=0.3 via tmux
environment to trigger compaction early. Verifies that compaction_needed
events fire, activity logs exist, session.json remains valid, and the
session survives.
"""

from __future__ import annotations

import json
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
class TestTLCompactionFallback:

    @pytest.mark.timeout(600)
    def test_team_leader_uses_precompact_fallback(
        self,
        tmp_path: Path,
        llm: object,
        feedback: object,
    ) -> None:
        """Trigger compaction via low threshold, verify events fire and
        session remains stable.

        Steps:
        1. Create config with threshold=300, minimal team
        2. Start session (TL + agents)
        3. Set tmux env CLAUDE_CODE_AUTO_COMPACT_WINDOW=0.3
        4. Inject context pressure into TL pane (large_prompt)
        5. Wait for compaction_needed events

        Assertions:
        - Compaction events fire with correct structure
        - Activity logs exist
        - session.json exists and status is valid
        - Session survived
        """
        # -- Build config with very low threshold --
        project_dir = tmp_path
        config = ForgeConfig(
            project=ProjectConfig(
                description="Build a Python CLI calculator tool with add, subtract, "
                            "multiply, divide commands. Include input validation, "
                            "help text, and comprehensive unit tests.",
                directory=str(project_dir),
            ),
            mode=ProjectMode.MVP,
            strategy=ExecutionStrategy.CO_PILOT,
            agents=AgentsConfig(team_profile=TeamProfile.LEAN),
            llm_gateway=LLMGatewayConfig(
                enabled=True,
                local_claude_model="claude-sonnet-4-20250514",
            ),
            compaction=CompactionConfig(
                compaction_threshold_tokens=300,
                enable_context_anchors=True,
                anchor_interval_minutes=1,
            ),
        )
        generate_all(config)

        transcript_dir = project_dir / "transcripts"
        transcript_dir.mkdir()
        orch = ForgeSessionOrchestrator(project_dir, config, llm, transcript_dir)

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True, agent_activity_timeout=180,
        )

        # -- Set tmux env to trigger Claude Code auto-compact early --
        assert orch.tmux is not None, "tmux session must be active"
        session_name = orch.tmux.session_name
        subprocess.run(
            ["tmux", "set-environment", "-t", session_name,
             "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "0.3"],
            check=True, capture_output=True,
        )

        # -- Inject context pressure into TL pane --
        orch.inject_context_pressure(pane="0", strategy="large_prompt")

        # Allow time for pressure to register
        orch.watch_terminals(duration=30, interval=10)

        # -- Wait for compaction_needed events --
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
            "compaction should trigger with threshold=300"
        )

        # -- Verify event structure --
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1
        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"

        # -- Verify activity logs exist --
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # -- Verify session.json exists and status is valid --
        session_path = project_dir / ".forge" / "session.json"
        assert session_path.exists(), "session.json should exist"
        session_data = json.loads(session_path.read_text())
        assert session_data.get("status") in ("running", "stopped", "complete"), (
            f"Session status should be valid, got '{session_data.get('status')}'"
        )

        # -- Session survived --
        assert orch.tmux.is_alive(), (
            "tmux session died after compaction -- session should remain running"
        )

        orch.save_transcripts("scenario_17_compaction_tl_fallback")
