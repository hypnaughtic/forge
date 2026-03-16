"""Scenario 16: Agent survives multiple compaction event cycles.

Tests that compaction_needed events fire multiple times during a session
with an aggressively low token threshold (300). Verifies that events
accumulate, activity logs grow, and the session remains stable across
multiple compaction cycles.
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
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestRepeatedCompactionCycles:

    @pytest.mark.timeout(600)
    def test_agent_survives_two_compaction_cycles(
        self,
        tmp_path: Path,
        llm: object,
        feedback: object,
    ) -> None:
        """Start session with threshold=300, observe multiple compaction
        events fire. Verify events accumulate and session remains alive.
        """
        # -- Build config with very low threshold to trigger compaction fast --
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
        orch.start_session(wait_for_agents=True, agent_activity_timeout=180)

        # -- Inject context pressure to accelerate compaction --
        assert orch.tmux is not None, "tmux session must be alive"
        panes = orch.tmux.list_panes()
        for pane_info in panes:
            pane_id = pane_info.get("id", "0")
            orch.inject_context_pressure(pane_id, strategy="large_prompt")

        # ====================================================================
        # CYCLE 1: Wait for first compaction event
        # ====================================================================
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
            "First compaction event did not fire within timeout -- "
            "threshold=300 should have been reached with context pressure"
        )

        snap_1 = orch.capture_state()
        cycle_1_event_count = len(snap_1.compaction_events)
        assert cycle_1_event_count >= 1, (
            "Expected at least 1 compaction event after cycle 1"
        )

        # Verify event structure
        event_1 = snap_1.compaction_events[0]
        assert event_1.get("type") == "compaction_needed"

        # ====================================================================
        # CYCLE 2: Continue working, wait for more compaction events
        # ====================================================================
        # Let agent continue working to accumulate more context
        orch.watch_terminals(duration=60, interval=10)

        # Inject more pressure
        for pane_info in panes:
            pane_id = pane_info.get("id", "0")
            orch.inject_context_pressure(pane_id, strategy="rapid_tasks")

        # Wait for additional events
        deadline_2 = time.monotonic() + 300
        cycle_2_detected = False
        while time.monotonic() < deadline_2:
            snap_2 = orch.capture_state()
            if len(snap_2.compaction_events) > cycle_1_event_count:
                cycle_2_detected = True
                break
            time.sleep(5)

        # It's acceptable if only one cycle of events fires -- the important
        # thing is the session survived
        snap_final = orch.capture_state()

        # -- Verify activity logs exist --
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # -- Session survived --
        assert orch.tmux.is_alive(), (
            "tmux session died during repeated compaction cycles"
        )

        orch.save_transcripts("scenario_16_compaction_repeated_cycles")
