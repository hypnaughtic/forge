"""Scenario 10: Multi-Cycle Stop/Resume.

Tests: start -> stop -> resume -> stop -> resume -> stop (3 cycles).
Verify state accumulates correctly across cycles with no regressions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestMultiCycle:

    def test_three_stop_resume_cycles_maintain_state(
        self, mvp_project, orchestrator, validator
    ):
        """Start -> work -> stop -> resume -> work -> stop -> resume -> work -> stop.
        Verify state accumulates correctly across 3 cycles with no regressions."""
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        snapshots = []

        for cycle in range(3):
            # Start or resume
            if cycle == 0:
                orchestrator.start_session(wait_for_agents=True)
            else:
                orchestrator.resume_session(wait_for_agents=True)

            # Let agents work
            orchestrator.watch_terminals(duration=60, interval=15)
            snap_working = orchestrator.capture_state()
            snapshots.append(snap_working)

            # Stop
            orchestrator.stop_gracefully()

        # -- VERIFY: monotonic progress across all 3 cycles --
        for i in range(1, len(snapshots)):
            violations = validator.assert_state_continuity(snapshots[i - 1], snapshots[i])
            assert len(violations) == 0, \
                f"Cycle {i} state regression: {violations}"

        # -- VERIFY: agent names consistent across all cycles --
        all_names: dict[str, str] = {}
        for i, snap in enumerate(snapshots):
            for agent, cp in snap.checkpoints.items():
                name = cp.get("agent_name")
                if not name:
                    continue
                if agent in all_names:
                    assert all_names[agent] == name, \
                        f"{agent} name changed in cycle {i}: {all_names[agent]} -> {name}"
                else:
                    all_names[agent] = name

        # -- VERIFY: cost monotonically increasing --
        for agent in all_names:
            costs = [
                snap.checkpoints.get(agent, {}).get("cost_usd", 0) or 0
                for snap in snapshots
            ]
            for i in range(1, len(costs)):
                assert costs[i] >= costs[i - 1], \
                    f"{agent} cost decreased in cycle {i}: {costs[i - 1]} -> {costs[i]}"

        # -- VERIFY: completed tasks accumulate --
        for agent in all_names:
            task_counts = [
                len(snap.checkpoints.get(agent, {}).get("completed_tasks", []))
                for snap in snapshots
            ]
            for i in range(1, len(task_counts)):
                assert task_counts[i] >= task_counts[i - 1], \
                    f"{agent} lost completed tasks in cycle {i}"

        orchestrator.save_transcripts("scenario_10_multi_cycle")

    def test_mixed_stop_methods_across_cycles(
        self, mvp_project, orchestrator, validator
    ):
        """Cycle 1: forge stop. Cycle 2: terminal close.
        Both should produce recoverable state."""
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()

        # Cycle 1: forge stop CLI (graceful)
        orchestrator.start_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=45, interval=15)
        orchestrator.stop_gracefully()

        snap_1 = orchestrator.capture_state()
        validator.assert_session_status("stopped")

        # Cycle 2: terminal close (ungraceful)
        orchestrator.resume_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=45, interval=15)
        orchestrator.kill_terminal()

        snap_2 = orchestrator.capture_state()

        # Both snapshots should have session.json at minimum
        assert snap_1.session_json is not None, "Cycle 1 should have session.json"
        assert snap_2.session_json is not None, "Cycle 2 should have session.json"

        # Cycle 1 (graceful) should have stopped status
        assert snap_1.session_json.get("status") == "stopped"

        # Cycle 2 (ungraceful) should still say "running" (crash state)
        assert snap_2.session_json.get("status") in ("running", "stopped")

        # At least one cycle should have checkpoint files
        total_checkpoints = len(snap_1.checkpoint_files) + len(snap_2.checkpoint_files)
        assert total_checkpoints > 0, "Should have checkpoint files from at least one cycle"

        orchestrator.save_transcripts("scenario_10_mixed_stops")
