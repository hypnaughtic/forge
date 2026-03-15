"""Unit tests for forge_cli/session.py — event inbox operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge_cli.models import AgentMeta, SessionState
from forge_cli.session import (
    materialize_session,
    read_events,
    write_event,
    write_session,
)


class TestWriteEvent:
    def test_creates_event_file(self, tmp_path):
        path = write_event(tmp_path, {"event": "test", "data": "hello"})
        assert path.exists()
        assert path.suffix == ".json"

    def test_atomic_write(self, tmp_path):
        """No .tmp files should remain."""
        write_event(tmp_path, {"event": "test"})
        events_dir = tmp_path / "events"
        tmp_files = list(events_dir.glob("*.tmp"))
        assert tmp_files == []

    def test_event_has_timestamp(self, tmp_path):
        path = write_event(tmp_path, {"event": "test"})
        data = json.loads(path.read_text())
        assert "timestamp" in data

    def test_multiple_events_unique_filenames(self, tmp_path):
        paths = [
            write_event(tmp_path, {"event": "test", "n": i})
            for i in range(5)
        ]
        names = {p.name for p in paths}
        assert len(names) == 5


class TestReadEvents:
    def test_reads_chronologically(self, tmp_path):
        write_event(tmp_path, {"event": "first", "order": 1})
        write_event(tmp_path, {"event": "second", "order": 2})
        write_event(tmp_path, {"event": "third", "order": 3})

        events, paths = read_events(tmp_path)
        assert len(events) == 3
        assert len(paths) == 3
        assert events[0]["order"] == 1
        assert events[2]["order"] == 3

    def test_skips_tmp_files(self, tmp_path):
        write_event(tmp_path, {"event": "real"})
        events_dir = tmp_path / "events"
        (events_dir / "orphan.json.tmp").write_text('{"event": "orphan"}')

        events, paths = read_events(tmp_path)
        assert len(events) == 1
        assert events[0]["event"] == "real"

    def test_skips_corrupted(self, tmp_path):
        write_event(tmp_path, {"event": "good"})
        events_dir = tmp_path / "events"
        (events_dir / "zzz-corrupt.json").write_text("not json!!!")

        events, paths = read_events(tmp_path)
        assert len(events) == 1

    def test_empty_dir(self, tmp_path):
        events, paths = read_events(tmp_path)
        assert events == []
        assert paths == []

    def test_nonexistent_dir(self, tmp_path):
        events, paths = read_events(tmp_path / "nope")
        assert events == []


class TestMaterializeSession:
    def test_applies_agent_registered_event(self, tmp_path):
        # Create base session
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        write_session(session, tmp_path)

        # Write agent_registered event
        write_event(tmp_path, {
            "event": "agent_registered",
            "agent_name": "Nova",
            "agent_type": "backend-developer",
            "parent_agent": "Commander",
            "checkpoint_path": ".forge/checkpoints/backend-developer/Nova.json",
        })

        result = materialize_session(tmp_path)
        assert "Nova" in result.agent_tree
        assert result.agent_tree["Nova"].agent_type == "backend-developer"
        assert result.agent_tree["Nova"].parent_agent == "Commander"
        assert result.agent_tree["Nova"].status == "registered"

    def test_applies_agent_started_event(self, tmp_path):
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            agent_tree={
                "Nova": AgentMeta(
                    agent_type="backend-developer",
                    agent_name="Nova",
                    status="registered",
                ),
            },
        )
        write_session(session, tmp_path)
        write_event(tmp_path, {
            "event": "agent_started",
            "agent_name": "Nova",
            "session_id": "sid-123",
        })

        result = materialize_session(tmp_path)
        assert result.agent_tree["Nova"].status == "active"
        assert result.agent_tree["Nova"].session_id == "sid-123"

    def test_applies_agent_stopped_event(self, tmp_path):
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            agent_tree={
                "Nova": AgentMeta(agent_type="dev", agent_name="Nova", status="active"),
            },
        )
        write_session(session, tmp_path)
        write_event(tmp_path, {"event": "agent_stopped", "agent_name": "Nova"})

        result = materialize_session(tmp_path)
        assert result.agent_tree["Nova"].status == "stopped"

    def test_applies_compaction_needed_event(self, tmp_path):
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            agent_tree={
                "Nova": AgentMeta(agent_type="dev", agent_name="Nova", status="active"),
            },
        )
        write_session(session, tmp_path)
        write_event(tmp_path, {"event": "compaction_needed", "agent_name": "Nova"})

        result = materialize_session(tmp_path)
        assert result.agent_tree["Nova"].status == "compaction_pending"

    def test_idempotent_registration(self, tmp_path):
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        write_session(session, tmp_path)
        # Register same agent twice
        write_event(tmp_path, {"event": "agent_registered", "agent_name": "Nova", "agent_type": "dev"})
        write_event(tmp_path, {"event": "agent_registered", "agent_name": "Nova", "agent_type": "dev"})

        result = materialize_session(tmp_path)
        assert len(result.agent_tree) == 1

    def test_archives_processed_events(self, tmp_path):
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        write_session(session, tmp_path)
        write_event(tmp_path, {"event": "agent_registered", "agent_name": "A", "agent_type": "dev"})

        materialize_session(tmp_path)

        # Events should be archived
        archive = tmp_path / "events-archive.jsonl"
        assert archive.exists()
        lines = archive.read_text().strip().split("\n")
        assert len(lines) == 1

        # Events dir should be empty
        events, _ = read_events(tmp_path)
        assert events == []

    def test_multi_level_hierarchy_from_events(self, tmp_path):
        """Register a 3-level tree from events, verify structure."""
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        write_session(session, tmp_path)

        write_event(tmp_path, {
            "event": "agent_registered",
            "agent_name": "Commander",
            "agent_type": "team-leader",
            "parent_agent": None,
        })
        write_event(tmp_path, {
            "event": "agent_registered",
            "agent_name": "Atlas",
            "agent_type": "sub-tl",
            "parent_agent": "Commander",
        })
        write_event(tmp_path, {
            "event": "agent_registered",
            "agent_name": "Pixel",
            "agent_type": "dev",
            "parent_agent": "Atlas",
        })

        result = materialize_session(tmp_path)
        assert len(result.agent_tree) == 3
        assert result.agent_tree["Commander"].parent_agent is None
        assert result.agent_tree["Atlas"].parent_agent == "Commander"
        assert result.agent_tree["Pixel"].parent_agent == "Atlas"

    def test_creates_session_when_none_exists(self, tmp_path):
        """materialize_session should create a new session if none exists."""
        write_event(tmp_path, {
            "event": "agent_registered",
            "agent_name": "Solo",
            "agent_type": "dev",
        })
        result = materialize_session(tmp_path)
        assert result is not None
        assert "Solo" in result.agent_tree
