"""Unit tests for forge_cli/checkpoint.py — models, I/O, hashing, resume."""

from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

import pytest

from forge_cli.models import (
    AgentCheckpoint,
    AgentMeta,
    ConversationEntry,
    SessionState,
    TaskState,
)
from forge_cli.checkpoint import (
    cleanup_completed_checkpoints,
    cleanup_stale_activity_logs,
    compute_file_hash,
    compute_instruction_hashes,
    detect_instruction_changes,
    read_all_checkpoints,
    read_checkpoint,
    validate_checkpoints_against_tree,
    write_checkpoint,
)
from forge_cli.session import (
    build_agent_resume_context,
    build_resume_prompt,
    clear_stop_signal,
    is_stop_requested,
    read_session,
    signal_stop,
    wait_for_agents_stopped,
    write_session,
)


class TestModels:
    def test_task_state_creation(self):
        task = TaskState(id="task-1", description="Implement auth", started_at="2026-03-14T10:00:00Z", step_index=2, total_steps=5, step_description="Writing middleware")
        assert task.id == "task-1"
        assert task.jira_ticket is None

    def test_conversation_entry(self):
        entry = ConversationEntry(role="assistant", content="Working", timestamp="2026-03-14T10:00:00Z")
        assert entry.tool_name is None

    def test_agent_meta_defaults(self):
        meta = AgentMeta(agent_type="backend-developer", agent_name="Nova")
        assert meta.status == "registered"
        assert meta.checkpoint_path == ""

    def test_agent_checkpoint_defaults(self):
        cp = AgentCheckpoint(agent_type="backend-developer", agent_name="Nova")
        assert cp.version == "1"
        assert cp.essential_files == []
        assert cp.compaction_count == 0

    def test_agent_checkpoint_essential_files_truncation(self):
        files = [f"file_{i}.py" for i in range(15)]
        cp = AgentCheckpoint(agent_type="test", agent_name="Test", essential_files=files)
        assert len(cp.essential_files) == 10

    def test_session_state_defaults(self):
        session = SessionState(forge_session_id="abc", project_dir="/tmp", project_name="test", config_hash="sha256", started_at="2026-03-14T10:00:00Z", updated_at="2026-03-14T10:00:00Z")
        assert session.status == "running"
        assert session.agent_tree == {}


class TestCheckpointIO:
    def test_write_and_read_checkpoint(self, tmp_path):
        cp = AgentCheckpoint(agent_type="backend-developer", agent_name="Nova", iteration=2, phase="TEST")
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)
        assert (checkpoints_dir / "backend-developer" / "Nova.json").exists()
        result = read_checkpoint("backend-developer", checkpoints_dir, agent_name="Nova")
        assert result is not None
        assert result.agent_name == "Nova"
        assert result.iteration == 2

    def test_write_checkpoint_atomic(self, tmp_path):
        cp = AgentCheckpoint(agent_type="test-agent", agent_name="Test")
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)
        assert (checkpoints_dir / "test-agent" / "Test.json").exists()
        assert not (checkpoints_dir / "test-agent" / "Test.json.tmp").exists()

    def test_write_checkpoint_creates_dir(self, tmp_path):
        cp = AgentCheckpoint(agent_type="test", agent_name="Test")
        checkpoints_dir = tmp_path / "deep" / "nested" / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)
        assert (checkpoints_dir / "test" / "Test.json").exists()

    def test_read_nonexistent_checkpoint(self, tmp_path):
        assert read_checkpoint("missing", tmp_path, agent_name="nobody") is None

    def test_read_all_checkpoints_hierarchical(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        for t, n in [("type-a", "Alpha"), ("type-b", "Beta"), ("type-c", "Gamma")]:
            write_checkpoint(AgentCheckpoint(agent_type=t, agent_name=n), checkpoints_dir)
        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 3
        assert "Alpha" in result

    def test_read_all_checkpoints_skips_tmp(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(AgentCheckpoint(agent_type="good", agent_name="Good"), checkpoints_dir)
        (checkpoints_dir / "good" / "Bad.json.tmp").write_text("{}")
        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 1
        assert "Good" in result

    def test_read_all_checkpoints_empty_dir(self, tmp_path):
        assert read_all_checkpoints(tmp_path / "nonexistent") == {}

    def test_write_and_read_session(self, tmp_path):
        session = SessionState(forge_session_id="test-123", project_dir=str(tmp_path), project_name="test", config_hash="abc123", started_at="2026-03-14T10:00:00Z", updated_at="2026-03-14T10:00:00Z", cost_cap_usd=50.0)
        write_session(session, tmp_path)
        result = read_session(tmp_path)
        assert result is not None
        assert result.forge_session_id == "test-123"

    def test_read_nonexistent_session(self, tmp_path):
        assert read_session(tmp_path) is None

    def test_read_corrupted_session(self, tmp_path):
        (tmp_path / "session.json").write_text("corrupt!!!")
        assert read_session(tmp_path) is None


class TestHashing:
    def test_compute_file_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h = compute_file_hash(f)
        assert len(h) == 64

    def test_compute_file_hash_deterministic(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert compute_file_hash(f) == compute_file_hash(f)

    def test_detect_instruction_changes_no_changes(self):
        assert detect_instruction_changes({"a.md": "h1"}, {"a.md": "h1"}) == {}

    def test_detect_instruction_changes_modified(self):
        assert detect_instruction_changes({"a.md": "h1"}, {"a.md": "h2"}) == {"a.md": "modified"}

    def test_detect_instruction_changes_added(self):
        assert detect_instruction_changes({"a.md": "h1"}, {"a.md": "h1", "b.md": "h2"}) == {"b.md": "added"}

    def test_detect_instruction_changes_removed(self):
        assert detect_instruction_changes({"a.md": "h1", "b.md": "h2"}, {"a.md": "h1"}) == {"b.md": "removed"}


class TestResumePrompts:
    def _make_session(self, **kwargs):
        defaults = dict(forge_session_id="test-session", project_dir="/tmp/test", project_name="test", config_hash="abc", started_at="2026-03-14T10:00:00Z", updated_at="2026-03-14T11:00:00Z", status="stopped", iteration=2, cost_usd=5.0, cost_cap_usd=50.0, stop_reason="explicit")
        defaults.update(kwargs)
        return SessionState(**defaults)

    def _make_cp(self, agent_type, agent_name, **kwargs):
        defaults = dict(agent_type=agent_type, agent_name=agent_name, iteration=2, phase="EXECUTE", context_summary="Working", handoff_notes="Continue")
        defaults.update(kwargs)
        return AgentCheckpoint(**defaults)

    def test_build_resume_prompt_basic(self):
        session = self._make_session(agent_tree={
            "Orion": AgentMeta(agent_type="team-leader", agent_name="Orion", checkpoint_path=".forge/checkpoints/team-leader/Orion.json", status="active"),
            "Nova": AgentMeta(agent_type="dev", agent_name="Nova", parent_agent="Orion", checkpoint_path=".forge/checkpoints/dev/Nova.json", status="active"),
        })
        checkpoints = {"Nova": self._make_cp("dev", "Nova")}
        prompt = build_resume_prompt(session, checkpoints, {})
        assert "RESUMED SESSION" in prompt
        assert "Orion" in prompt
        assert "Nova" in prompt

    def test_build_resume_prompt_with_changes(self):
        session = self._make_session(agent_tree={"Orion": AgentMeta(agent_type="team-leader", agent_name="Orion", status="active")})
        prompt = build_resume_prompt(session, {}, {".claude/agents/backend-developer.md": "modified"})
        assert "modified" in prompt

    def test_build_resume_prompt_with_task(self):
        session = self._make_session(agent_tree={
            "Orion": AgentMeta(agent_type="team-leader", agent_name="Orion", status="active"),
            "Nova": AgentMeta(agent_type="dev", agent_name="Nova", parent_agent="Orion", status="active"),
        })
        cp = self._make_cp("dev", "Nova", current_task=TaskState(id="t1", description="Build auth API", started_at="2026-03-14T10:00:00Z", step_index=1, total_steps=3, step_description="Writing JWT"))
        prompt = build_resume_prompt(session, {"Nova": cp}, {})
        assert "Build auth API" in prompt

    def test_build_resume_prompt_no_agents(self):
        session = self._make_session(agent_tree={"Orion": AgentMeta(agent_type="team-leader", agent_name="Orion", status="active")})
        prompt = build_resume_prompt(session, {}, {})
        assert "no agents" in prompt

    def test_build_agent_resume_context(self):
        cp = self._make_cp("dev", "Nova", context_summary="Building REST API", handoff_notes="Next: user registration", decisions_made=[{"decision": "bcrypt", "reasoning": "Industry standard"}], current_task=TaskState(id="t1", description="Auth", started_at="2026-03-14T10:00:00Z", step_index=1, total_steps=3, step_description="JWT middleware"))
        context = build_agent_resume_context(cp, checkpoint_path=".forge/checkpoints/dev/Nova.json")
        assert "Nova" in context
        assert "Building REST API" in context
        assert "bcrypt" in context

    def test_build_agent_resume_context_with_conversation(self):
        cp = self._make_cp("dev", "Nova", recent_conversation=[
            ConversationEntry(role="user", content="Add rate limiting", timestamp="2026-03-14T10:30:00Z"),
            ConversationEntry(role="assistant", content="token bucket", timestamp="2026-03-14T10:31:00Z"),
        ])
        context = build_agent_resume_context(cp, checkpoint_path=".forge/checkpoints/dev/Nova.json")
        assert "rate limiting" in context
        assert "token bucket" in context


class TestStopSignal:
    def test_signal_stop_creates_sentinel(self, tmp_path):
        signal_stop(tmp_path)
        assert (tmp_path / "STOP_REQUESTED").exists()

    def test_is_stop_requested(self, tmp_path):
        assert is_stop_requested(tmp_path) is False
        signal_stop(tmp_path)
        assert is_stop_requested(tmp_path) is True

    def test_clear_stop_signal(self, tmp_path):
        signal_stop(tmp_path)
        clear_stop_signal(tmp_path)
        assert is_stop_requested(tmp_path) is False

    def test_clear_stop_signal_idempotent(self, tmp_path):
        clear_stop_signal(tmp_path)

    def test_wait_for_agents_stopped_immediate(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(AgentCheckpoint(agent_type="type-a", agent_name="A", status="stopped"), checkpoints_dir)
        write_checkpoint(AgentCheckpoint(agent_type="type-b", agent_name="B", status="complete"), checkpoints_dir)
        stopped, timed_out = wait_for_agents_stopped(checkpoints_dir, timeout=1.0)
        assert set(stopped) == {"A", "B"}
        assert timed_out == []

    def test_wait_for_agents_stopped_timeout(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(AgentCheckpoint(agent_type="type-a", agent_name="A", status="active"), checkpoints_dir)
        stopped, timed_out = wait_for_agents_stopped(checkpoints_dir, timeout=0.5, poll_interval=0.1)
        assert "A" in timed_out

    def test_wait_for_agents_stopped_empty(self, tmp_path):
        stopped, timed_out = wait_for_agents_stopped(tmp_path / "empty", timeout=0.5, poll_interval=0.1)
        assert stopped == []
        assert timed_out == []


class TestCleanup:
    def test_cleanup_completed_checkpoints(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(AgentCheckpoint(agent_type="done-type", agent_name="Done", status="complete"), checkpoints_dir)
        write_checkpoint(AgentCheckpoint(agent_type="active-type", agent_name="Active", status="active"), checkpoints_dir)
        removed = cleanup_completed_checkpoints(checkpoints_dir)
        assert "Done" in removed
        assert not (checkpoints_dir / "done-type" / "Done.json").exists()
        assert (checkpoints_dir / "active-type" / "Active.json").exists()

    def test_cleanup_completed_with_activity_log(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(AgentCheckpoint(agent_type="done-type", agent_name="Done", status="complete"), checkpoints_dir)
        (checkpoints_dir / "done-type" / "Done.activity.jsonl").write_text('{"tool": "Write"}\n')
        removed = cleanup_completed_checkpoints(checkpoints_dir)
        assert "Done" in removed
        assert not (checkpoints_dir / "done-type" / "Done.activity.jsonl").exists()

    def test_cleanup_empty_dir(self, tmp_path):
        assert cleanup_completed_checkpoints(tmp_path / "nonexistent") == []

    def test_cleanup_stale_activity_logs(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        type_dir = checkpoints_dir / "some-type"
        type_dir.mkdir(parents=True)
        old_log = type_dir / "old.activity.jsonl"
        old_log.write_text('{"tool": "Write"}\n')
        import os
        old_time = time.time() - (10 * 86400)
        os.utime(str(old_log), (old_time, old_time))
        recent_log = type_dir / "recent.activity.jsonl"
        recent_log.write_text('{"tool": "Edit"}\n')
        removed = cleanup_stale_activity_logs(checkpoints_dir, max_age_days=7)
        assert "old.activity.jsonl" in removed
        assert recent_log.exists()


class TestSerialization:
    def test_checkpoint_roundtrip(self, tmp_path):
        cp = AgentCheckpoint(agent_type="dev", agent_name="Nova", iteration=3, phase="REVIEW", essential_files=["src/auth.py"], compaction_count=1, context_anchor_updated_at="2026-03-14T10:30:00Z", handoff_notes="Review JWT")
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)
        result = read_checkpoint("dev", checkpoints_dir, agent_name="Nova")
        assert result is not None
        assert result.agent_name == "Nova"
        assert result.essential_files == ["src/auth.py"]
        assert result.compaction_count == 1
        assert result.handoff_notes == "Review JWT"

    def test_session_roundtrip(self, tmp_path):
        session = SessionState(forge_session_id=str(uuid4()), project_dir=str(tmp_path), project_name="my-project", config_hash="abc123", started_at="2026-03-14T10:00:00Z", updated_at="2026-03-14T11:00:00Z", status="stopped", iteration=3, agent_tree={"Orion": AgentMeta(agent_type="team-leader", agent_name="Orion", checkpoint_path=".forge/checkpoints/team-leader/Orion.json")}, cost_usd=12.34, stop_reason="explicit")
        write_session(session, tmp_path)
        result = read_session(tmp_path)
        assert result is not None
        assert result.project_name == "my-project"
        assert result.agent_tree["Orion"].checkpoint_path == ".forge/checkpoints/team-leader/Orion.json"


class TestLegacyAndEdgeCases:
    """Additional tests for legacy fallback paths and error branches."""

    def test_read_checkpoint_legacy_flat_path(self, tmp_path):
        """Read from legacy {type}.json path when agent_name is None."""
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir()
        cp = AgentCheckpoint(agent_type="backend-developer", agent_name="Nova")
        # Write as flat file (legacy format)
        (checkpoints_dir / "backend-developer.json").write_text(
            json.dumps(cp.model_dump(mode="json"), indent=2)
        )
        result = read_checkpoint("backend-developer", checkpoints_dir)
        assert result is not None
        assert result.agent_name == "Nova"

    def test_read_checkpoint_corrupted_hierarchical(self, tmp_path):
        """Corrupted JSON in hierarchical path returns None."""
        checkpoints_dir = tmp_path / "checkpoints"
        type_dir = checkpoints_dir / "dev"
        type_dir.mkdir(parents=True)
        (type_dir / "Broken.json").write_text("not valid json {{{")
        result = read_checkpoint("dev", checkpoints_dir, agent_name="Broken")
        assert result is None

    def test_read_all_skips_corrupted_hierarchical(self, tmp_path):
        """Corrupted files in type dirs are skipped."""
        checkpoints_dir = tmp_path / "checkpoints"
        type_dir = checkpoints_dir / "dev"
        type_dir.mkdir(parents=True)
        (type_dir / "corrupt.json").write_text("bad json")
        write_checkpoint(AgentCheckpoint(agent_type="dev", agent_name="Good"), checkpoints_dir)
        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 1
        assert "Good" in result

    def test_read_all_skips_tmp_in_type_dirs(self, tmp_path):
        """Tmp files in hierarchical dirs are skipped."""
        checkpoints_dir = tmp_path / "checkpoints"
        type_dir = checkpoints_dir / "dev"
        type_dir.mkdir(parents=True)
        (type_dir / "Orphan.json.tmp").write_text("{}")
        result = read_all_checkpoints(checkpoints_dir)
        assert result == {}

    def test_read_all_legacy_flat_fallback(self, tmp_path):
        """Legacy flat files at root are discovered."""
        import json as _json
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir()
        cp = AgentCheckpoint(agent_type="legacy", agent_name="OldAgent")
        (checkpoints_dir / "legacy.json").write_text(
            _json.dumps(cp.model_dump(mode="json"), indent=2)
        )
        result = read_all_checkpoints(checkpoints_dir)
        assert "OldAgent" in result

    def test_read_all_legacy_skips_corrupted(self, tmp_path):
        """Corrupted legacy flat files are skipped."""
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir()
        (checkpoints_dir / "bad.json").write_text("not json")
        result = read_all_checkpoints(checkpoints_dir)
        assert result == {}

    def test_read_all_legacy_skips_duplicate(self, tmp_path):
        """Legacy file with same agent_name as hierarchical is skipped."""
        import json as _json
        checkpoints_dir = tmp_path / "checkpoints"
        cp = AgentCheckpoint(agent_type="dev", agent_name="Alpha")
        # Write hierarchical
        write_checkpoint(cp, checkpoints_dir)
        # Write legacy flat with same agent_name
        (checkpoints_dir / "dev.json").write_text(
            _json.dumps(cp.model_dump(mode="json"), indent=2)
        )
        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 1  # no duplicates
