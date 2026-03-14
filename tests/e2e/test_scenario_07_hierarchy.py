"""Scenario 7: Hierarchical Agent Recovery.

Tests: forge start (with sub-agents) -> stop -> resume -> verify parent-child relationships preserved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestHierarchy:

    def test_multi_level_hierarchy_reconstructed_on_resume(
        self, mvp_project, orchestrator, validator
    ):
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)

        # Wait for sub-agents to potentially spawn
        orchestrator.watch_terminals(duration=120, interval=15)

        snap_before = orchestrator.capture_state()

        # Build hierarchy tree from checkpoints
        hierarchy = {}
        for agent, cp in snap_before.checkpoints.items():
            parent = cp.get("parent_agent")
            hierarchy[agent] = {
                "parent": parent,
                "name": cp.get("agent_name"),
                "sub_agents": cp.get("sub_agents", []),
            }

        orchestrator.stop_gracefully()
        snap_after = orchestrator.resume_session(wait_for_agents=True)

        # -- VERIFY: parent-child relationships preserved --
        for agent, pre_state in hierarchy.items():
            if agent in snap_after.checkpoints:
                post_cp = snap_after.checkpoints[agent]
                # Parent reference must be preserved
                assert post_cp.get("parent_agent") == pre_state["parent"], \
                    f"{agent} parent changed: {pre_state['parent']} -> {post_cp.get('parent_agent')}"
                # Agent name must be preserved
                if pre_state["name"]:
                    assert post_cp.get("agent_name") == pre_state["name"], \
                        f"{agent} name changed"

        # -- VERIFY: spawn order (parent before child) --
        for agent, post_cp in snap_after.checkpoints.items():
            parent = post_cp.get("parent_agent")
            if parent and parent in snap_after.checkpoints:
                parent_time = snap_after.checkpoints[parent].get("spawned_at", "")
                child_time = post_cp.get("spawned_at", "")
                if parent_time and child_time:
                    assert parent_time <= child_time, \
                        f"Parent {parent} spawned after child {agent}"

        orchestrator.save_transcripts("scenario_07_hierarchy")
