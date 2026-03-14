"""Scenario 8: Agent Metadata Preservation (Comprehensive).

Tests: exhaustive verification that every checkpoint field survives a stop/resume cycle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestMetadataPreservation:

    def test_all_metadata_fields_survive_stop_resume_cycle(
        self, mvp_project, orchestrator, validator
    ):
        """Exhaustive verification that every checkpoint field survives a stop/resume cycle."""
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=90, interval=15)

        snap_before = orchestrator.capture_state()
        orchestrator.stop_gracefully()

        # Deep copy all checkpoint data before resume
        pre_checkpoints = {}
        for agent, cp in snap_before.checkpoints.items():
            pre_checkpoints[agent] = json.loads(json.dumps(cp))

        snap_after = orchestrator.resume_session(wait_for_agents=True)

        # -- Field-by-field verification for EVERY agent --
        for agent, pre_cp in pre_checkpoints.items():
            if agent not in snap_after.checkpoints:
                continue  # agent may have completed

            post_cp = snap_after.checkpoints[agent]

            # Identity fields (MUST be exact match)
            assert post_cp.get("agent_type") == pre_cp.get("agent_type"), \
                f"{agent}: agent_type changed"
            if pre_cp.get("agent_name"):
                assert post_cp.get("agent_name") == pre_cp.get("agent_name"), \
                    f"{agent}: agent_name changed"
            assert post_cp.get("parent_agent") == pre_cp.get("parent_agent"), \
                f"{agent}: parent_agent changed"

            # Iteration state (MUST NOT regress)
            pre_iter = pre_cp.get("iteration", 0) or 0
            post_iter = post_cp.get("iteration", 0) or 0
            assert post_iter >= pre_iter, \
                f"{agent}: iteration regressed {pre_iter} -> {post_iter}"

            # Phase (MUST NOT regress within same iteration)
            if post_cp.get("iteration") == pre_cp.get("iteration"):
                phases = ["PLAN", "EXECUTE", "TEST", "INTEGRATE", "REVIEW", "CRITIQUE", "DECISION"]
                pre_phase = pre_cp.get("phase", "PLAN")
                post_phase = post_cp.get("phase", "PLAN")
                if pre_phase in phases and post_phase in phases:
                    pre_idx = phases.index(pre_phase)
                    post_idx = phases.index(post_phase)
                    assert post_idx >= pre_idx, \
                        f"{agent}: phase regressed {pre_phase} -> {post_phase}"

            # Cost (MUST accumulate, never reset)
            pre_cost = pre_cp.get("cost_usd", 0) or 0
            post_cost = post_cp.get("cost_usd", 0) or 0
            assert post_cost >= pre_cost, \
                f"{agent}: cost reset {pre_cost} -> {post_cost}"

            # Decisions (MUST be superset - no decisions lost)
            pre_decisions = {
                d.get("decision", "") for d in pre_cp.get("decisions_made", [])
            }
            post_decisions = {
                d.get("decision", "") for d in post_cp.get("decisions_made", [])
            }
            lost_decisions = pre_decisions - post_decisions
            assert len(lost_decisions) == 0, \
                f"{agent}: lost decisions: {lost_decisions}"

            # Completed tasks (MUST be superset)
            pre_completed = {
                t.get("id", "") for t in pre_cp.get("completed_tasks", [])
            }
            post_completed = {
                t.get("id", "") for t in post_cp.get("completed_tasks", [])
            }
            lost_tasks = pre_completed - post_completed
            assert len(lost_tasks) == 0, \
                f"{agent}: lost completed tasks: {lost_tasks}"

            # Files modified (MUST be superset)
            pre_files = set(pre_cp.get("files_modified", []))
            post_files = set(post_cp.get("files_modified", []))
            lost_files = pre_files - post_files
            assert len(lost_files) == 0, \
                f"{agent}: lost file records: {lost_files}"

            # Branches (MUST be superset)
            pre_branches = set(pre_cp.get("branches", []))
            post_branches = set(post_cp.get("branches", []))
            lost_branches = pre_branches - post_branches
            assert len(lost_branches) == 0, \
                f"{agent}: lost branch records: {lost_branches}"

            # Context summary (MUST exist and be non-empty)
            assert post_cp.get("context_summary", "").strip(), \
                f"{agent}: empty context_summary after resume"

            # Handoff notes (MUST exist)
            assert post_cp.get("handoff_notes", "").strip(), \
                f"{agent}: empty handoff_notes after resume"

        orchestrator.save_transcripts("scenario_08_metadata")
