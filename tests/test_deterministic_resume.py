"""Unit tests for hierarchy-aware resume prompt generation."""

from __future__ import annotations

import pytest

from forge_cli.models import AgentCheckpoint, AgentMeta, SessionState, TaskState
from forge_cli.session import (
    _get_direct_children,
    build_agent_resume_context,
    build_resume_prompt,
)


def _make_session(**kwargs) -> SessionState:
    defaults = dict(
        forge_session_id="test-session",
        project_dir="/tmp/test",
        project_name="test",
        config_hash="abc",
        started_at="2026-03-14T10:00:00Z",
        updated_at="2026-03-14T11:00:00Z",
        status="stopped",
        iteration=2,
        cost_usd=5.0,
        cost_cap_usd=50.0,
        stop_reason="explicit",
    )
    defaults.update(kwargs)
    return SessionState(**defaults)


def _make_cp(agent_type: str, name: str, **kwargs) -> AgentCheckpoint:
    defaults = dict(
        agent_type=agent_type,
        agent_name=name,
        iteration=2,
        phase="EXECUTE",
        context_summary="Working",
        handoff_notes="Continue",
    )
    defaults.update(kwargs)
    return AgentCheckpoint(**defaults)


class TestBuildResumePromptHierarchy:
    def test_lists_only_tl_direct_children(self):
        """11-agent tree: resume prompt should only list TL's 2 direct children."""
        tree = {
            "Commander": AgentMeta(
                agent_type="team-leader", agent_name="Commander",
                checkpoint_path=".forge/checkpoints/team-leader/Commander.json",
                status="active",
            ),
            "Atlas": AgentMeta(
                agent_type="sub-tl", agent_name="Atlas", parent_agent="Commander",
                checkpoint_path=".forge/checkpoints/sub-tl/Atlas.json",
                status="active",
            ),
            "Nova": AgentMeta(
                agent_type="sub-tl", agent_name="Nova", parent_agent="Commander",
                checkpoint_path=".forge/checkpoints/sub-tl/Nova.json",
                status="active",
            ),
            "Pixel": AgentMeta(agent_type="dev", agent_name="Pixel", parent_agent="Atlas", status="active"),
            "Spark": AgentMeta(agent_type="dev", agent_name="Spark", parent_agent="Atlas", status="active"),
            "Blaze": AgentMeta(agent_type="dev", agent_name="Blaze", parent_agent="Nova", status="active"),
            "Echo": AgentMeta(agent_type="dev", agent_name="Echo", parent_agent="Nova", status="active"),
            "W1": AgentMeta(agent_type="worker", agent_name="W1", parent_agent="Pixel", status="active"),
            "W2": AgentMeta(agent_type="worker", agent_name="W2", parent_agent="Spark", status="active"),
            "W3": AgentMeta(agent_type="worker", agent_name="W3", parent_agent="Blaze", status="active"),
            "W4": AgentMeta(agent_type="worker", agent_name="W4", parent_agent="Echo", status="active"),
        }
        session = _make_session(agent_tree=tree)
        checkpoints = {
            "Atlas": _make_cp("sub-tl", "Atlas"),
            "Nova": _make_cp("sub-tl", "Nova"),
        }

        prompt = build_resume_prompt(session, checkpoints, {})

        # Should mention Atlas and Nova (TL's direct children)
        assert "Atlas" in prompt
        assert "Nova" in prompt
        # Should NOT mention grandchildren directly
        assert "Pixel" not in prompt
        assert "W1" not in prompt

    def test_grandchild_count_annotation(self):
        """Direct children should show sub-agent count."""
        tree = {
            "Commander": AgentMeta(
                agent_type="team-leader", agent_name="Commander",
                checkpoint_path=".forge/checkpoints/team-leader/Commander.json",
                status="active",
            ),
            "Atlas": AgentMeta(
                agent_type="sub-tl", agent_name="Atlas", parent_agent="Commander",
                checkpoint_path=".forge/checkpoints/sub-tl/Atlas.json",
                status="active",
            ),
            "P1": AgentMeta(agent_type="dev", agent_name="P1", parent_agent="Atlas", status="active"),
            "P2": AgentMeta(agent_type="dev", agent_name="P2", parent_agent="Atlas", status="active"),
            "P3": AgentMeta(agent_type="dev", agent_name="P3", parent_agent="Atlas", status="active"),
        }
        session = _make_session(agent_tree=tree)
        checkpoints = {"Atlas": _make_cp("sub-tl", "Atlas")}

        prompt = build_resume_prompt(session, checkpoints, {})
        assert "3 sub-agent(s)" in prompt

    def test_tl_name_and_checkpoint_in_prompt(self):
        tree = {
            "Commander": AgentMeta(
                agent_type="team-leader", agent_name="Commander",
                checkpoint_path=".forge/checkpoints/team-leader/Commander.json",
                status="active",
            ),
        }
        session = _make_session(agent_tree=tree)
        prompt = build_resume_prompt(session, {}, {})

        assert "Your name is Commander" in prompt
        assert "team-leader/Commander.json" in prompt

    def test_same_type_different_levels_distinct_paths(self):
        """Two agents of same type at different tree levels have correct info."""
        tree = {
            "TL": AgentMeta(
                agent_type="team-leader", agent_name="TL",
                checkpoint_path=".forge/checkpoints/team-leader/TL.json",
                status="active",
            ),
            "Dev1": AgentMeta(
                agent_type="dev", agent_name="Dev1", parent_agent="TL",
                checkpoint_path=".forge/checkpoints/dev/Dev1.json",
                status="active",
            ),
            "Dev2": AgentMeta(
                agent_type="dev", agent_name="Dev2", parent_agent="Dev1",
                checkpoint_path=".forge/checkpoints/dev/Dev2.json",
                status="active",
            ),
        }
        session = _make_session(agent_tree=tree)
        checkpoints = {
            "Dev1": _make_cp("dev", "Dev1"),
        }

        prompt = build_resume_prompt(session, checkpoints, {})
        # Dev1 is TL's direct child — should appear
        assert "Dev1" in prompt
        # Dev2 is Dev1's child — should NOT appear in TL's prompt
        assert "Dev2" not in prompt


class TestBuildAgentResumeContextHierarchy:
    def test_mid_level_agent_sees_own_children(self):
        """A mid-level agent's resume context should list its direct children."""
        cp = _make_cp("sub-tl", "Atlas", parent_agent="Commander")
        tree = {
            "Commander": AgentMeta(agent_type="team-leader", agent_name="Commander", status="active"),
            "Atlas": AgentMeta(agent_type="sub-tl", agent_name="Atlas", parent_agent="Commander", status="active"),
            "Pixel": AgentMeta(
                agent_type="dev", agent_name="Pixel", parent_agent="Atlas",
                checkpoint_path=".forge/checkpoints/dev/Pixel.json", status="active",
            ),
            "Spark": AgentMeta(
                agent_type="dev", agent_name="Spark", parent_agent="Atlas",
                checkpoint_path=".forge/checkpoints/dev/Spark.json", status="active",
            ),
        }
        child_cps = {
            "Pixel": _make_cp("dev", "Pixel"),
            "Spark": _make_cp("dev", "Spark"),
        }

        context = build_agent_resume_context(
            cp,
            checkpoint_path=".forge/checkpoints/sub-tl/Atlas.json",
            agent_tree=tree,
            checkpoints=child_cps,
        )
        assert "Pixel" in context
        assert "Spark" in context
        assert "re-spawn" in context.lower()

    def test_leaf_agent_has_no_children_section(self):
        """A leaf agent without children should not have sub-agent section."""
        cp = _make_cp("dev", "Pixel", parent_agent="Atlas")
        tree = {
            "Atlas": AgentMeta(agent_type="sub-tl", agent_name="Atlas", status="active"),
            "Pixel": AgentMeta(agent_type="dev", agent_name="Pixel", parent_agent="Atlas", status="active"),
        }

        context = build_agent_resume_context(
            cp,
            checkpoint_path=".forge/checkpoints/dev/Pixel.json",
            agent_tree=tree,
            checkpoints={},
        )
        assert "re-spawn" not in context.lower()

    def test_resume_context_includes_agent_init(self):
        """Resume context should tell agent to run /agent-init resume."""
        cp = _make_cp("dev", "Pixel")
        context = build_agent_resume_context(
            cp,
            checkpoint_path=".forge/checkpoints/dev/Pixel.json",
        )
        assert "/agent-init resume" in context
