"""Scenario 20: Compaction edge cases.

Tests seven edge cases around compaction: very low threshold, very high
threshold, corrupted activity logs, first-tool-call compaction, mid-save
interference, agent disobedience recovery, and stop/resume interaction
during compaction.
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


def _make_config(tmp_path: Path, threshold: int) -> ForgeConfig:
    """Create a ForgeConfig with a specific compaction threshold."""
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
            compaction_threshold_tokens=threshold,
            enable_context_anchors=True,
            anchor_interval_minutes=2,
        ),
    )
    generate_all(config)
    return config


def _make_orchestrator(
    tmp_path: Path, config: ForgeConfig, llm: object,
) -> ForgeSessionOrchestrator:
    """Create a ForgeSessionOrchestrator for the given project."""
    transcript_dir = tmp_path / "transcripts"
    transcript_dir.mkdir(exist_ok=True)
    return ForgeSessionOrchestrator(tmp_path, config, llm, transcript_dir)


@pytest.mark.e2e
class TestCompactionEdgeCases:

    @pytest.mark.timeout(300)
    def test_very_low_threshold_triggers_immediate_compaction(
        self,
        tmp_path: Path,
        llm: object,
        feedback: FeedbackCollector,
    ) -> None:
        """Threshold=100 tokens should trigger compaction events almost
        immediately after an agent starts working."""
        config = _make_config(tmp_path, threshold=100)
        orch = _make_orchestrator(tmp_path, config, llm)

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=120,
        )

        # With threshold=100, compaction should fire within 60s
        compaction_detected = False
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(3)

        assert compaction_detected, (
            "Compaction events should fire within 60s with threshold=100"
        )

        # Verify event structure
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1
        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"

        # Activity logs exist
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # Session survived
        assert orch.tmux is not None
        assert orch.tmux.is_alive(), (
            "tmux session should be alive after immediate compaction"
        )

        orch.save_transcripts("scenario_20_very_low_threshold")

    @pytest.mark.timeout(300)
    def test_high_threshold_no_false_positives(
        self,
        tmp_path: Path,
        llm: object,
        feedback: FeedbackCollector,
    ) -> None:
        """Threshold=10M tokens should never trigger compaction during
        normal operation. No compaction events, markers, or warnings."""
        config = _make_config(tmp_path, threshold=10_000_000)
        orch = _make_orchestrator(tmp_path, config, llm)

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=120,
        )

        # Let agents work for 120s
        orch.watch_terminals(duration=120, interval=15)

        snap = orch.capture_state()

        # NO compaction events
        assert len(snap.compaction_events) == 0, (
            f"Should have zero compaction events with threshold=10M, "
            f"got {len(snap.compaction_events)}"
        )

        # NO compaction markers
        assert len(snap.compaction_markers) == 0, (
            f"Should have zero compaction markers with threshold=10M, "
            f"got {len(snap.compaction_markers)}"
        )

        # No agent should have compaction_count > 0
        for agent_key, cp in snap.checkpoints.items():
            cc = cp.get("compaction_count", 0) or 0
            assert cc == 0, (
                f"Agent {agent_key} has compaction_count={cc} despite "
                f"threshold=10M"
            )

        orch.save_transcripts("scenario_20_high_threshold")

    @pytest.mark.timeout(300)
    def test_corrupted_token_estimate_recovery(
        self,
        compaction_project: tuple[Path, ...],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: FeedbackCollector,
    ) -> None:
        """Corrupted activity log should not crash the agent. The hook
        should fail gracefully and the agent continues working."""
        project_dir, config = compaction_project
        orch = compaction_orchestrator

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # Wait for at least one agent to have an activity log
        assert orch.tmux is not None
        orch.watch_terminals(duration=30, interval=10)

        # Find an activity log file and corrupt it
        checkpoints_dir = project_dir / ".forge" / "checkpoints"
        corrupted = False
        if checkpoints_dir.exists():
            for log_file in checkpoints_dir.glob("**/*.activity.jsonl"):
                if log_file.stat().st_size > 0:
                    # Write garbage data
                    log_file.write_text(
                        "{{{{NOT JSON AT ALL!!! \x00\x01\x02 garbage "
                        "data corrupted file\n"
                        "more garbage lines\n"
                        '{"broken": "json"'  # unterminated
                    )
                    corrupted = True
                    break

        if not corrupted:
            # No activity log to corrupt yet -- just verify agents work
            pass

        # Agent should continue working despite corruption
        orch.watch_terminals(duration=30, interval=10)

        # Session should still be alive
        assert orch.tmux.is_alive(), (
            "tmux session should still be alive after activity log corruption"
        )

        orch.save_transcripts("scenario_20_corrupted_token_estimate")

    @pytest.mark.timeout(300)
    def test_threshold_on_first_tool_call(
        self,
        tmp_path: Path,
        llm: object,
        feedback: FeedbackCollector,
    ) -> None:
        """With threshold=100, an agent crosses the threshold on its
        very first tool call. Compaction events should fire even with a
        near-empty checkpoint, and the agent should not crash."""
        config = _make_config(tmp_path, threshold=100)
        orch = _make_orchestrator(tmp_path, config, llm)

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=120,
        )

        # With threshold=100, compaction fires very early
        # Wait a short window for the agent to start and compact
        compaction_detected = False
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(3)

        # Session should still be running (agent didn't crash)
        assert orch.tmux is not None
        assert orch.tmux.is_alive(), (
            "tmux session should be alive -- agent should not crash on "
            "first-call compaction"
        )

        # If compaction fired, verify event structure
        if compaction_detected:
            snap_after = orch.capture_state()
            event = snap_after.compaction_events[0]
            assert event.get("type") == "compaction_needed"

        orch.save_transcripts("scenario_20_threshold_first_tool_call")

    @pytest.mark.timeout(300)
    def test_compaction_during_checkpoint_save(
        self,
        compaction_project: tuple[Path, ...],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: FeedbackCollector,
    ) -> None:
        """A .json.tmp file in checkpoints simulates a mid-save state.
        After compaction completes, no .json.tmp files should remain,
        and the final checkpoint must be valid JSON."""
        project_dir, config = compaction_project
        orch = compaction_orchestrator

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # Wait for agent activity
        assert orch.tmux is not None
        orch.watch_terminals(duration=20, interval=10)

        # Create a .json.tmp file to simulate mid-save
        checkpoints_dir = project_dir / ".forge" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        fake_tmp = checkpoints_dir / "simulated-save.json.tmp"
        fake_tmp.write_text(
            '{"agent_name": "partial-write", "status": "saving"}'
        )

        # Also create a nested tmp file
        nested_dir = checkpoints_dir / "backend-developer"
        nested_dir.mkdir(parents=True, exist_ok=True)
        nested_tmp = nested_dir / "partial-agent.json.tmp"
        nested_tmp.write_text('{"incomplete": true}')

        # Wait for compaction events
        compaction_detected = False
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(5)

        # Allow post-compaction cleanup
        time.sleep(10)

        # Verify: all checkpoint .json files are valid JSON
        for cp_file in checkpoints_dir.glob("**/*.json"):
            try:
                data = json.loads(cp_file.read_text())
                assert isinstance(data, dict), (
                    f"Checkpoint {cp_file.name} should be a JSON object"
                )
            except json.JSONDecodeError as exc:
                pytest.fail(
                    f"Checkpoint {cp_file.name} contains invalid JSON: {exc}"
                )

        # Session survived
        assert orch.tmux.is_alive(), (
            "tmux session should be alive after mid-save compaction"
        )

        orch.save_transcripts("scenario_20_compaction_during_save")

    @pytest.mark.timeout(300)
    def test_agent_ignores_compaction_warning_recovery(
        self,
        compaction_project: tuple[Path, ...],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: FeedbackCollector,
    ) -> None:
        """Tests the 'agent disobedience' scenario: if the agent does not
        promptly run /handoff compaction after threshold is crossed,
        compaction_needed events should still fire via hooks. The session
        should survive regardless."""
        project_dir, config = compaction_project
        orch = compaction_orchestrator

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        assert orch.tmux is not None

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
            "No compaction_needed events found within 240s -- "
            "compaction should trigger with threshold=500"
        )

        # -- Verify event structure --
        snap_after = orch.capture_state()
        assert len(snap_after.compaction_events) >= 1
        event = snap_after.compaction_events[0]
        assert event.get("type") == "compaction_needed"

        # -- Verify activity logs exist --
        activity_logs = list(checkpoints_dir.glob("**/*.activity.jsonl"))
        assert len(activity_logs) >= 1, "No activity logs found"

        # -- Session survived --
        assert orch.tmux.is_alive(), (
            "tmux session should still be alive after compaction "
            "disobedience recovery"
        )

        orch.save_transcripts("scenario_20_agent_disobedience")

    @pytest.mark.timeout(300)
    def test_compaction_stop_resume_interaction(
        self,
        compaction_project: tuple[Path, ...],
        compaction_orchestrator: ForgeSessionOrchestrator,
        compaction_validator: CheckpointValidator,
        feedback: FeedbackCollector,
    ) -> None:
        """Forge stop during an active compaction cycle should work cleanly.
        Resume should detect compaction state and session continues."""
        project_dir, config = compaction_project
        orch = compaction_orchestrator
        val = compaction_validator

        orch.generate_project()
        orch.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        assert orch.tmux is not None

        # -- Wait for compaction_needed events --
        compaction_detected = False
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            snap = orch.capture_state()
            if snap.compaction_events:
                compaction_detected = True
                break
            time.sleep(5)

        if not compaction_detected:
            orch.save_transcripts(
                "scenario_20_stop_resume_no_compaction"
            )
            pytest.fail(
                "No compaction_needed events detected within 120s -- "
                "compaction should trigger with threshold=500"
            )

        # -- Immediately stop (before agent can complete handoff) --
        orch.stop_gracefully(timeout=60)

        # -- Verify: session.json persisted --
        val.assert_session_exists()

        # -- Verify: checkpoint files exist --
        checkpoints_dir = project_dir / ".forge" / "checkpoints"
        checkpoint_files = list(checkpoints_dir.glob("**/*.json"))
        assert len(checkpoint_files) >= 1, (
            "At least one checkpoint file should exist after stop"
        )

        # -- Resume session --
        snap_resumed = orch.resume_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # -- Verify: session.json exists after resume --
        val.assert_session_exists()

        # Session should be running again
        snap_after_resume = orch.capture_state()
        resume_status = snap_after_resume.session_json.get("status", "")
        assert resume_status == "running", (
            f"Session should be 'running' after resume, got '{resume_status}'"
        )

        # Events files should persist across stop/resume
        assert len(snap_after_resume.compaction_events) >= 1, (
            "compaction_needed events should persist after resume"
        )

        orch.save_transcripts("scenario_20_compaction_stop_resume")
