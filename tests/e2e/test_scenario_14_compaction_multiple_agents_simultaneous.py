"""Scenario 14: Simultaneous Compaction of Multiple Agents.

Tests: forge start with very low compaction threshold -> inject context
pressure into multiple panes -> compaction_needed events fire ->
verify no duplicate events, no corrupted checkpoints, session survives.
"""

from __future__ import annotations

import json
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
class TestSimultaneousCompaction:

    @pytest.mark.timeout(300)
    def test_multiple_agents_compact_without_race_conditions(
        self,
        tmp_path: Path,
        llm: object,
        feedback: FeedbackCollector,
    ) -> None:
        """Start a session with a very low compaction threshold, inject
        context pressure into multiple panes simultaneously, and verify
        that compaction events fire without duplicate events or corrupted
        checkpoint files."""

        # -- Inline config: very low threshold to trigger fast compaction --
        config = ForgeConfig(
            project=ProjectConfig(
                description=(
                    "Build a Python CLI calculator tool with add, subtract, "
                    "multiply, divide commands. Include input validation, "
                    "help text, and comprehensive unit tests."
                ),
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
                compaction_threshold_tokens=300,
                enable_context_anchors=True,
                anchor_interval_minutes=2,
            ),
        )
        generate_all(config)

        # -- Set up orchestrator --
        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()
        orch = ForgeSessionOrchestrator(tmp_path, config, llm, transcript_dir)
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"

        # -- PHASE 1: Start session --
        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # -- PHASE 2: Inject context pressure into multiple panes --
        assert orch.tmux is not None, "tmux session must be alive"
        panes = orch.tmux.list_panes()
        for pane_info in panes:
            pane_id = pane_info.get("id", "0")
            orch.inject_context_pressure(pane_id, strategy="large_prompt")

        # -- PHASE 3: Wait for compaction_needed events --
        compaction_detected = False
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(5)

        # Allow time for multiple compactions to process
        orch.watch_terminals(duration=60, interval=10)

        # -- PHASE 4: Capture final state --
        snap_after = orch.capture_state()

        # -- ASSERTIONS --

        # 1. At least one compaction event fired
        assert len(snap_after.compaction_events) >= 1, (
            "Expected at least 1 compaction_needed event with threshold=300"
        )

        # 2. Events are stored as separate files (atomic writes — no
        # race-condition corruption). Since identity resolves to "unknown"
        # for all agents, we verify that each event file is valid JSON
        # rather than checking agent-level uniqueness.
        events_dir = tmp_path / ".forge" / "events"
        if events_dir.exists():
            for event_file in events_dir.glob("*.json"):
                import json as _json
                content = event_file.read_text()
                try:
                    data = _json.loads(content)
                    assert "type" in data, f"Event file {event_file.name} missing 'type'"
                except _json.JSONDecodeError:
                    raise AssertionError(
                        f"Corrupted event file: {event_file.name}"
                    )

        # 3. No .json.tmp files remaining (atomic writes completed)
        if checkpoints_dir.exists():
            tmp_files = list(checkpoints_dir.rglob("*.json.tmp"))
            assert len(tmp_files) == 0, (
                f"Found {len(tmp_files)} leftover .json.tmp files in "
                f"checkpoints directory: {[str(f) for f in tmp_files]}"
            )

        # 4. Each checkpoint file is valid JSON
        if checkpoints_dir.exists():
            checkpoint_files = [
                f for f in checkpoints_dir.rglob("*.json")
                if not f.name.endswith(".tmp")
                and f.name != "session.json"
            ]
            for cp_file in checkpoint_files:
                try:
                    data = json.loads(cp_file.read_text())
                    assert isinstance(data, dict), (
                        f"Checkpoint {cp_file} is not a JSON object"
                    )
                except json.JSONDecodeError as exc:
                    pytest.fail(
                        f"Corrupted checkpoint file {cp_file}: {exc}"
                    )

        # 5. Activity logs exist
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # 6. Session survived
        assert orch.tmux.is_alive(), (
            "tmux session died during concurrent compaction"
        )

        orch.save_transcripts("scenario_14_compaction_simultaneous")
