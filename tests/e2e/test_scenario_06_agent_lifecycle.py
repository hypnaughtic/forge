"""Scenario 6: Agent Lifecycle Complete.

Tests: forge start -> work long enough for agents to complete -> stop -> resume -> verify completed agents not respawned.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestAgentLifecycle:

    def test_completed_agents_not_respawned_after_resume(
        self, mvp_project, orchestrator, validator
    ):
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)

        # Let agents work long enough for some to potentially complete
        orchestrator.watch_terminals(duration=120, interval=15)

        snap_before = orchestrator.capture_state()

        # Identify completed vs active agents
        completed_agents = [
            a for a, cp in snap_before.checkpoints.items()
            if cp.get("status") == "complete"
        ]
        active_agents = [
            a for a, cp in snap_before.checkpoints.items()
            if cp.get("status") not in ("complete", None)
        ]

        orchestrator.stop_gracefully()

        # Resume
        snap_after = orchestrator.resume_session(wait_for_agents=True)

        # Completed agents should NOT be respawned
        for agent in completed_agents:
            # Their checkpoint may still exist (cleanup happens after iteration tag)
            # But they should not be actively working
            if agent in snap_after.checkpoints:
                assert snap_after.checkpoints[agent].get("status") == "complete", \
                    f"Completed agent {agent} was respawned"

        # Active agents MUST be respawned
        for agent in active_agents:
            assert agent in snap_after.checkpoints, \
                f"Active agent {agent} not respawned after resume"

        orchestrator.save_transcripts("scenario_06_lifecycle")
