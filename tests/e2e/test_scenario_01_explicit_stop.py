"""Scenario 1: Explicit Stop via `forge stop` CLI.

Tests: forge start → work → forge stop → verify checkpoints → forge resume → verify continuity.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.feedback_collector import FeedbackCollector
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestExplicitStop:

    def test_forge_stop_creates_checkpoints_and_resume_restores_state(
        self, mvp_project, orchestrator, validator, feedback
    ):
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        # -- PHASE 1: Start and let agents work --
        orchestrator.generate_project()
        snap_start = orchestrator.start_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # Watch terminals for 60s to let agents do real work
        timeline = orchestrator.watch_terminals(duration=60, interval=10)
        assert len(timeline) >= 1, "Should have captured terminal state at least once"

        snap_before_stop = orchestrator.capture_state()

        # -- PHASE 2: Stop gracefully --
        snap_after_stop = orchestrator.stop_gracefully(timeout=90)

        # -- DETERMINISTIC ASSERTIONS --
        validator.assert_session_exists()
        validator.assert_session_status("stopped")
        validator.assert_sentinel_cleaned()

        # Every active agent must have a checkpoint
        if snap_before_stop.session_json:
            active_agents = [
                a for a, meta in snap_before_stop.session_json.get("agent_tree", {}).items()
                if meta.get("status") == "active"
            ]
            if active_agents:
                validator.assert_all_agents_checkpointed(active_agents)

                for agent in active_agents:
                    validator.assert_agent_status(agent, "stopped")
                    validator.assert_checkpoint_fresh(agent, max_age_seconds=120)

        # Record agent state for comparison after resume
        pre_stop_agents = {}
        checkpoints_dir = project_dir / ".forge" / "checkpoints"
        if checkpoints_dir.exists():
            for cp_file in checkpoints_dir.glob("*.json"):
                if cp_file.name.endswith(".tmp"):
                    continue
                cp = json.loads(cp_file.read_text())
                pre_stop_agents[cp_file.stem] = {
                    "name": cp.get("agent_name"),
                    "iteration": cp.get("iteration"),
                    "phase": cp.get("phase"),
                    "cost": cp.get("cost_usd", 0),
                }

        # tmux session should be dead
        assert not orchestrator.tmux.is_alive()

        # -- PHASE 3: Resume --
        snap_after_resume = orchestrator.resume_session(
            wait_for_agents=True,
            agent_activity_timeout=180,
        )

        # -- RESUME ASSERTIONS --
        validator.assert_session_status("running")

        # Agent names must be preserved
        for agent, pre_state in pre_stop_agents.items():
            if agent in snap_after_resume.checkpoints:
                validator.assert_agent_name_preserved(agent, pre_state["name"])
                validator.assert_iteration_preserved(agent, pre_state["iteration"])

        # Verify state continuity
        violations = validator.assert_state_continuity(snap_before_stop, snap_after_resume)
        assert len(violations) == 0, f"State continuity violations: {violations}"

        orchestrator.save_transcripts("scenario_01_explicit_stop")
