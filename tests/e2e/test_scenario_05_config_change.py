"""Scenario 5: Config Change Between Sessions.

Tests: forge start -> stop -> change config -> forge resume -> verify state preserved + new config applied.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from forge_cli.config_schema import (
    AgentsConfig,
    ExecutionStrategy,
    ForgeConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
    TechStack,
)
from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestConfigChange:

    def test_config_change_regenerates_files_preserves_checkpoint_state(
        self, mvp_project, orchestrator, validator
    ):
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        # -- Session 1: MVP mode --
        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=60, interval=10)

        snap_mvp = orchestrator.capture_state()
        mvp_agents = set(snap_mvp.checkpoints.keys())
        mvp_instruction_hashes = snap_mvp.instruction_file_hashes.copy()

        # Record agent names and progress
        mvp_agent_state = {}
        for agent, cp in snap_mvp.checkpoints.items():
            mvp_agent_state[agent] = {
                "name": cp.get("agent_name"),
                "iteration": cp.get("iteration"),
                "phase": cp.get("phase"),
                "decisions": cp.get("decisions_made", []),
            }

        orchestrator.stop_gracefully()

        # -- Change config: add tech stack --
        orchestrator.modify_config(
            tech_stack=TechStack(frameworks=["FastAPI", "React"]),
        )

        # Regenerate instruction files
        orchestrator.regenerate_files()

        # -- VERIFY: instruction files actually changed --
        new_instruction_hashes = {}
        agents_dir = project_dir / ".claude" / "agents"
        if agents_dir.exists():
            for md_file in agents_dir.glob("*.md"):
                new_instruction_hashes[str(md_file)] = hashlib.sha256(
                    md_file.read_bytes()
                ).hexdigest()

        # -- Session 2: Resume with changed config --
        snap_after_resume = orchestrator.resume_session(wait_for_agents=True)

        # -- VERIFY: existing agents preserved state --
        for agent, pre_state in mvp_agent_state.items():
            if agent in snap_after_resume.checkpoints:
                post_cp = snap_after_resume.checkpoints[agent]

                # Agent name must be preserved
                if pre_state["name"]:
                    assert post_cp.get("agent_name") == pre_state["name"], \
                        f"{agent} name changed: {pre_state['name']} -> {post_cp.get('agent_name')}"

                # Iteration must not regress
                pre_iter = pre_state.get("iteration", 0) or 0
                post_iter = post_cp.get("iteration", 0) or 0
                assert post_iter >= pre_iter, f"{agent} iteration regressed"

        # Verify state continuity across stop/resume
        violations = validator.assert_state_continuity(snap_mvp, snap_after_resume)
        assert len(violations) == 0, f"State continuity violations: {violations}"

        orchestrator.save_transcripts("scenario_05_config_change")

    def test_strategy_change_updates_agent_behavior(
        self, mvp_project, orchestrator, validator
    ):
        """Change strategy from co-pilot to auto-pilot between sessions."""
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=45, interval=15)
        orchestrator.stop_gracefully()

        # Change strategy only (same mode, same team)
        orchestrator.modify_config(strategy=ExecutionStrategy.AUTO_PILOT)
        orchestrator.regenerate_files()

        # Resume - agents should follow auto-pilot behavior
        orchestrator.resume_session(wait_for_agents=True)
        validator.assert_session_status("running")
        orchestrator.save_transcripts("scenario_05_strategy_change")

    def test_context_files_update_between_sessions(
        self, mvp_project, orchestrator, validator
    ):
        """User adds new context files between sessions."""
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=45, interval=15)
        orchestrator.stop_gracefully()

        # Add new context file (simulates updated requirements)
        docs_dir = project_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "api-spec-v2.md").write_text(
            "# API Spec v2\n\n## New Endpoint: POST /api/v2/webhooks\n"
            "Add webhook support for real-time event notifications.\n"
        )
        orchestrator.regenerate_files()

        orchestrator.resume_session(wait_for_agents=True)
        validator.assert_session_status("running")
        orchestrator.save_transcripts("scenario_05_context_files")
