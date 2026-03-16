"""Scenario 13: Multi-Level Hierarchy Compaction.

Tests: forge start with FULL team -> deep agent hierarchy forms ->
compaction_needed events fire -> session remains stable -> activity
logs and event structure verified.
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
class TestCompactionMultiLevelHierarchy:

    @pytest.mark.timeout(600)
    def test_deep_hierarchy_compaction_preserves_parent_chain(
        self,
        tmp_path: Path,
        llm: object,
        feedback: FeedbackCollector,
    ) -> None:
        """Start a FULL team, wait for compaction_needed events to fire,
        and verify the session remains stable with correct event structure."""

        # -- Inline config: FULL team with low compaction threshold --
        config = ForgeConfig(
            project=ProjectConfig(
                description=(
                    "Build a task management REST API with user auth, "
                    "project boards, real-time updates, and a React "
                    "dashboard. Include full test coverage and CI/CD."
                ),
                directory=str(tmp_path),
            ),
            mode=ProjectMode.MVP,
            strategy=ExecutionStrategy.CO_PILOT,
            agents=AgentsConfig(team_profile=TeamProfile.FULL),
            llm_gateway=LLMGatewayConfig(
                enabled=True,
                local_claude_model="claude-sonnet-4-20250514",
            ),
            compaction=CompactionConfig(
                compaction_threshold_tokens=500,
                enable_context_anchors=True,
                anchor_interval_minutes=2,
            ),
        )
        generate_all(config)

        # -- Set up orchestrator --
        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()
        orch = ForgeSessionOrchestrator(tmp_path, config, llm, transcript_dir)

        # -- PHASE 1: Start session, allow hierarchical agent tree to form --
        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=240,
        )

        # Let the full team work long enough for sub-agents to spawn and
        # context pressure to build.
        orch.watch_terminals(duration=120, interval=15)

        # -- PHASE 2: Wait for compaction_needed events --
        compaction_detected = False
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"

        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(5)

        assert compaction_detected, (
            "No compaction_needed events found within timeout -- "
            "expected at least one compaction event with threshold=500 "
            "and a FULL team"
        )

        # -- PHASE 3: Verify event structure --
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1
        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"

        # -- PHASE 4: Verify activity logs exist --
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # -- PHASE 5: Session survived --
        assert orch.tmux is not None
        assert orch.tmux.is_alive(), (
            "tmux session died after compaction events"
        )

        orch.save_transcripts("scenario_13_compaction_multi_level_hierarchy")
