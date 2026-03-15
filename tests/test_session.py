"""Unit tests for forge_cli/session.py — session I/O and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from forge_cli.models import AgentMeta, SessionState
from forge_cli.session import (
    _get_direct_children,
    read_session,
    write_session,
)


class TestSessionIO:
    def test_write_and_read_session(self, tmp_path):
        session = SessionState(
            forge_session_id="sess-1",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="abc",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
        )
        write_session(session, tmp_path)
        result = read_session(tmp_path)
        assert result is not None
        assert result.forge_session_id == "sess-1"

    def test_read_nonexistent(self, tmp_path):
        assert read_session(tmp_path) is None

    def test_read_corrupted(self, tmp_path):
        (tmp_path / "session.json").write_text("not json!!!")
        assert read_session(tmp_path) is None


class TestAgentMetaLifecycle:
    def test_status_transitions(self):
        """Verify all expected statuses are accepted."""
        for status in ["registered", "active", "stopping", "stopped", "complete", "compaction_pending"]:
            meta = AgentMeta(agent_type="test", agent_name="t", status=status)
            assert meta.status == status

    def test_default_status_registered(self):
        meta = AgentMeta(agent_type="test", agent_name="t")
        assert meta.status == "registered"


class TestGetDirectChildren:
    def test_returns_direct_children_only(self):
        tree = {
            "TL": AgentMeta(agent_type="team-leader", agent_name="TL"),
            "A": AgentMeta(agent_type="dev", agent_name="A", parent_agent="TL"),
            "B": AgentMeta(agent_type="dev", agent_name="B", parent_agent="TL"),
            "C": AgentMeta(agent_type="worker", agent_name="C", parent_agent="A"),
            "D": AgentMeta(agent_type="worker", agent_name="D", parent_agent="A"),
        }
        children = _get_direct_children(tree, "TL")
        assert set(children.keys()) == {"A", "B"}

        children_a = _get_direct_children(tree, "A")
        assert set(children_a.keys()) == {"C", "D"}

        children_c = _get_direct_children(tree, "C")
        assert children_c == {}

    def test_four_level_hierarchy(self):
        """4-level tree: TL -> sub-TL -> dev -> worker."""
        tree = {
            "Commander": AgentMeta(agent_type="team-leader", agent_name="Commander"),
            "Atlas": AgentMeta(agent_type="sub-tl", agent_name="Atlas", parent_agent="Commander"),
            "Nova": AgentMeta(agent_type="sub-tl", agent_name="Nova", parent_agent="Commander"),
            "Pixel": AgentMeta(agent_type="dev", agent_name="Pixel", parent_agent="Atlas"),
            "Spark": AgentMeta(agent_type="dev", agent_name="Spark", parent_agent="Atlas"),
            "Blaze": AgentMeta(agent_type="dev", agent_name="Blaze", parent_agent="Nova"),
            "Echo": AgentMeta(agent_type="dev", agent_name="Echo", parent_agent="Nova"),
            "W1": AgentMeta(agent_type="worker", agent_name="W1", parent_agent="Pixel"),
            "W2": AgentMeta(agent_type="worker", agent_name="W2", parent_agent="Spark"),
            "W3": AgentMeta(agent_type="worker", agent_name="W3", parent_agent="Blaze"),
            "W4": AgentMeta(agent_type="worker", agent_name="W4", parent_agent="Echo"),
        }
        # Commander's direct children
        assert set(_get_direct_children(tree, "Commander").keys()) == {"Atlas", "Nova"}
        # Atlas's direct children
        assert set(_get_direct_children(tree, "Atlas").keys()) == {"Pixel", "Spark"}
        # Pixel's direct children
        assert set(_get_direct_children(tree, "Pixel").keys()) == {"W1"}
        # Worker has no children
        assert _get_direct_children(tree, "W1") == {}

    def test_none_parent(self):
        tree = {
            "Root": AgentMeta(agent_type="tl", agent_name="Root"),
        }
        # Root has parent_agent=None, looking for parent=None should find it
        children = _get_direct_children(tree, None)
        assert "Root" in children


class TestCleanSessionState:
    def test_cleans_all_ephemeral_state(self, tmp_path):
        from forge_cli.main import clean_session_state

        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        (forge_dir / "session.json").write_text("{}")
        (forge_dir / "events-archive.jsonl").write_text("")
        (forge_dir / "token-report.json").write_text("{}")
        cp_dir = forge_dir / "checkpoints"
        cp_dir.mkdir()
        (cp_dir / "test.json").write_text("{}")
        ev_dir = forge_dir / "events"
        ev_dir.mkdir()
        (ev_dir / "event.json").write_text("{}")

        clean_session_state(forge_dir)

        assert not (forge_dir / "session.json").exists()
        assert not (forge_dir / "events-archive.jsonl").exists()
        assert not (forge_dir / "token-report.json").exists()
        # Dirs recreated empty
        assert (forge_dir / "checkpoints").exists()
        assert (forge_dir / "events").exists()
        assert not list((forge_dir / "checkpoints").iterdir())
        assert not list((forge_dir / "events").iterdir())

    def test_preserves_scripts(self, tmp_path):
        from forge_cli.main import clean_session_state

        forge_dir = tmp_path / ".forge"
        scripts_dir = forge_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "resolve_identity.py").write_text("# script")

        clean_session_state(forge_dir)

        assert (scripts_dir / "resolve_identity.py").exists()

    def test_idempotent(self, tmp_path):
        from forge_cli.main import clean_session_state

        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        clean_session_state(forge_dir)
        clean_session_state(forge_dir)  # second call should not error

    def test_handles_missing_forge_dir(self, tmp_path):
        from forge_cli.main import clean_session_state

        forge_dir = tmp_path / ".forge"
        # Should not raise even if dir doesn't exist
        clean_session_state(forge_dir)
