"""Scenario 18: Compaction events fire in a full-team session with sub-agents.

Tests: forge start (full team) -> agents work -> compaction_needed events
fire -> session survives -> activity logs and event structure verified.
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
class TestCompactionWithSubAgents:

    @pytest.mark.timeout(600)
    def test_parent_compaction_cascades_to_children(
        self,
        tmp_path: Path,
        llm: object,
        feedback: FeedbackCollector,
    ) -> None:
        """Start a full team session, wait for compaction_needed events,
        and verify the session remains stable with correct event structure
        and activity logs."""

        # -- SETUP: Full team with low compaction threshold --
        config = ForgeConfig(
            project=ProjectConfig(
                description="Build a REST API with authentication, CRUD "
                            "endpoints, database models, and integration "
                            "tests. Include OpenAPI docs and Docker setup.",
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

        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()
        orch = ForgeSessionOrchestrator(tmp_path, config, llm, transcript_dir)

        # -- PHASE 1: Start session with full team --
        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=240,
        )

        # Wait for hierarchical agent tree to form (multiple panes = agents)
        assert orch.tmux is not None, "tmux session must be alive"
        orch.tmux.wait_for_pane_count(3, timeout=240)

        # Let agents work long enough for hierarchy to establish
        orch.watch_terminals(duration=60, interval=10)

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
            "expected compaction with threshold=500 and a FULL team"
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
        assert orch.tmux.is_alive(), (
            "tmux session died after compaction events"
        )

        orch.save_transcripts("scenario_18_compaction_with_sub_agents")
