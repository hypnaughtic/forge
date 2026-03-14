"""Unit tests for forge_cli/checkpoint.py — models, I/O, hashing, resume."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from forge_cli.checkpoint import (
    AgentCheckpoint,
    AgentMeta,
    ConversationEntry,
    SessionState,
    TaskState,
    build_agent_resume_context,
    build_resume_prompt,
    cleanup_completed_checkpoints,
    cleanup_stale_activity_logs,
    clear_stop_signal,
    compute_file_hash,
    compute_instruction_hashes,
    detect_instruction_changes,
    is_stop_requested,
    read_all_checkpoints,
    read_checkpoint,
    read_session,
    signal_stop,
    wait_for_agents_stopped,
    write_checkpoint,
    write_session,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_task_state_creation(self):
        task = TaskState(
            id="task-1",
            description="Implement auth",
            started_at="2026-03-14T10:00:00Z",
            step_index=2,
            total_steps=5,
            step_description="Writing middleware",
        )
        assert task.id == "task-1"
        assert task.step_index == 2
        assert task.jira_ticket is None

    def test_task_state_with_jira(self):
        task = TaskState(
            id="task-2",
            description="Fix bug",
            jira_ticket="PROJ-42",
            started_at="2026-03-14T10:00:00Z",
            step_index=0,
            total_steps=3,
            step_description="Reproducing",
        )
        assert task.jira_ticket == "PROJ-42"

    def test_conversation_entry(self):
        entry = ConversationEntry(
            role="assistant",
            content="Working on auth module",
            timestamp="2026-03-14T10:00:00Z",
        )
        assert entry.tool_name is None

    def test_conversation_entry_with_tool(self):
        entry = ConversationEntry(
            role="assistant",
            content="Wrote file",
            timestamp="2026-03-14T10:00:00Z",
            tool_name="Write",
        )
        assert entry.tool_name == "Write"

    def test_agent_meta_defaults(self):
        meta = AgentMeta(agent_type="backend-developer", agent_name="Nova")
        assert meta.status == "active"
        assert meta.parent_agent is None
        assert meta.tmux_pane is None

    def test_agent_checkpoint_defaults(self):
        cp = AgentCheckpoint(agent_type="backend-developer", agent_name="Nova")
        assert cp.version == "1"
        assert cp.iteration == 1
        assert cp.phase == "PLAN"
        assert cp.phase_progress_pct == 0
        assert cp.current_task is None
        assert cp.completed_tasks == []
        assert cp.context_summary == ""
        assert cp.cost_usd == 0.0
        assert cp.handoff_notes == ""
        assert cp.sub_agents == []
        assert cp.error is None

    def test_agent_checkpoint_full(self):
        cp = AgentCheckpoint(
            agent_type="team-leader",
            agent_name="Orion",
            parent_agent=None,
            status="active",
            iteration=3,
            phase="EXECUTE",
            phase_progress_pct=60,
            current_task=TaskState(
                id="t1", description="Deploy", started_at="2026-03-14T10:00:00Z",
                step_index=1, total_steps=3, step_description="Building Docker image",
            ),
            completed_tasks=[
                TaskState(
                    id="t0", description="Setup", started_at="2026-03-14T09:00:00Z",
                    step_index=2, total_steps=2, step_description="Done",
                ),
            ],
            context_summary="Working on deployment pipeline",
            decisions_made=[{"decision": "Use Docker", "reasoning": "Standard", "timestamp": "2026-03-14T10:00:00Z"}],
            files_modified=["src/main.py"],
            branches=["feat-deploy"],
            cost_usd=1.23,
            handoff_notes="Next: push to registry",
        )
        assert cp.iteration == 3
        assert cp.current_task.description == "Deploy"
        assert len(cp.completed_tasks) == 1
        assert len(cp.decisions_made) == 1

    def test_session_state_defaults(self):
        session = SessionState(
            forge_session_id="abc",
            project_dir="/tmp/test",
            project_name="test",
            config_hash="sha256",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
        )
        assert session.version == "1"
        assert session.status == "running"
        assert session.iteration == 1
        assert session.agent_tree == {}
        assert session.cost_usd == 0.0
        assert session.stop_reason is None

    def test_session_state_with_agents(self):
        session = SessionState(
            forge_session_id="abc",
            project_dir="/tmp/test",
            project_name="test",
            config_hash="sha256",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
            agent_tree={
                "team-leader": AgentMeta(agent_type="team-leader", agent_name="Orion"),
                "backend-developer": AgentMeta(
                    agent_type="backend-developer", agent_name="Nova",
                    parent_agent="team-leader",
                ),
            },
        )
        assert len(session.agent_tree) == 2
        assert session.agent_tree["backend-developer"].parent_agent == "team-leader"


# ---------------------------------------------------------------------------
# I/O tests
# ---------------------------------------------------------------------------


class TestCheckpointIO:
    def test_write_and_read_checkpoint(self, tmp_path):
        cp = AgentCheckpoint(
            agent_type="backend-developer",
            agent_name="Nova",
            iteration=2,
            phase="TEST",
            context_summary="Running tests",
            handoff_notes="Check CI",
        )
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)

        result = read_checkpoint("backend-developer", checkpoints_dir)
        assert result is not None
        assert result.agent_name == "Nova"
        assert result.iteration == 2
        assert result.phase == "TEST"
        assert result.context_summary == "Running tests"

    def test_write_checkpoint_atomic(self, tmp_path):
        """Verify tmp file doesn't persist after write."""
        cp = AgentCheckpoint(agent_type="test-agent", agent_name="Test")
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)

        assert (checkpoints_dir / "test-agent.json").exists()
        assert not (checkpoints_dir / "test-agent.json.tmp").exists()

    def test_write_checkpoint_creates_dir(self, tmp_path):
        cp = AgentCheckpoint(agent_type="test", agent_name="Test")
        checkpoints_dir = tmp_path / "deep" / "nested" / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)
        assert (checkpoints_dir / "test.json").exists()

    def test_read_nonexistent_checkpoint(self, tmp_path):
        result = read_checkpoint("missing", tmp_path)
        assert result is None

    def test_read_corrupted_checkpoint(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not valid json {{{")
        result = read_checkpoint("bad", tmp_path)
        assert result is None

    def test_read_all_checkpoints(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        for name in ["agent-a", "agent-b", "agent-c"]:
            write_checkpoint(
                AgentCheckpoint(agent_type=name, agent_name=name.title()),
                checkpoints_dir,
            )
        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 3
        assert "agent-a" in result
        assert result["agent-b"].agent_name == "Agent-B"

    def test_read_all_checkpoints_skips_tmp(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir()
        write_checkpoint(
            AgentCheckpoint(agent_type="good", agent_name="Good"),
            checkpoints_dir,
        )
        (checkpoints_dir / "bad.json.tmp").write_text("{}")
        result = read_all_checkpoints(checkpoints_dir)
        assert len(result) == 1
        assert "good" in result

    def test_read_all_checkpoints_empty_dir(self, tmp_path):
        result = read_all_checkpoints(tmp_path / "nonexistent")
        assert result == {}

    def test_write_and_read_session(self, tmp_path):
        session = SessionState(
            forge_session_id="test-123",
            project_dir=str(tmp_path),
            project_name="test-project",
            config_hash="abc123",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
            status="running",
            cost_cap_usd=50.0,
        )
        write_session(session, tmp_path)

        result = read_session(tmp_path)
        assert result is not None
        assert result.forge_session_id == "test-123"
        assert result.status == "running"
        assert result.cost_cap_usd == 50.0

    def test_write_session_atomic(self, tmp_path):
        session = SessionState(
            forge_session_id="test",
            project_dir=str(tmp_path),
            project_name="test",
            config_hash="",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
        )
        write_session(session, tmp_path)
        assert (tmp_path / "session.json").exists()
        assert not (tmp_path / "session.json.tmp").exists()

    def test_read_nonexistent_session(self, tmp_path):
        result = read_session(tmp_path)
        assert result is None

    def test_read_corrupted_session(self, tmp_path):
        (tmp_path / "session.json").write_text("corrupt!!!")
        result = read_session(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# Hash tests
# ---------------------------------------------------------------------------


class TestHashing:
    def test_compute_file_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h = compute_file_hash(f)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex

    def test_compute_file_hash_deterministic(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        h1 = compute_file_hash(f)
        h2 = compute_file_hash(f)
        assert h1 == h2

    def test_compute_file_hash_different_content(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert compute_file_hash(f1) != compute_file_hash(f2)

    def test_compute_instruction_hashes(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "team-leader.md").write_text("# TL")
        (agents_dir / "backend-developer.md").write_text("# BD")

        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "checkpoint.md").write_text("# CP")

        (tmp_path / "CLAUDE.md").write_text("# CLAUDE")

        hashes = compute_instruction_hashes(tmp_path)
        assert ".claude/agents/team-leader.md" in hashes
        assert ".claude/agents/backend-developer.md" in hashes
        assert ".claude/skills/checkpoint.md" in hashes
        assert "CLAUDE.md" in hashes

    def test_detect_instruction_changes_no_changes(self):
        stored = {"a.md": "hash1", "b.md": "hash2"}
        current = {"a.md": "hash1", "b.md": "hash2"}
        changes = detect_instruction_changes(stored, current)
        assert changes == {}

    def test_detect_instruction_changes_modified(self):
        stored = {"a.md": "hash1"}
        current = {"a.md": "hash2"}
        changes = detect_instruction_changes(stored, current)
        assert changes == {"a.md": "modified"}

    def test_detect_instruction_changes_added(self):
        stored = {"a.md": "hash1"}
        current = {"a.md": "hash1", "b.md": "hash2"}
        changes = detect_instruction_changes(stored, current)
        assert changes == {"b.md": "added"}

    def test_detect_instruction_changes_removed(self):
        stored = {"a.md": "hash1", "b.md": "hash2"}
        current = {"a.md": "hash1"}
        changes = detect_instruction_changes(stored, current)
        assert changes == {"b.md": "removed"}

    def test_detect_instruction_changes_mixed(self):
        stored = {"a.md": "h1", "b.md": "h2", "c.md": "h3"}
        current = {"a.md": "h1", "b.md": "h2_changed", "d.md": "h4"}
        changes = detect_instruction_changes(stored, current)
        assert changes == {"b.md": "modified", "c.md": "removed", "d.md": "added"}


# ---------------------------------------------------------------------------
# Resume prompt tests
# ---------------------------------------------------------------------------


class TestResumePrompts:
    def _make_session(self, **kwargs) -> SessionState:
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

    def _make_checkpoint(self, agent_type: str, agent_name: str, **kwargs) -> AgentCheckpoint:
        defaults = dict(
            agent_type=agent_type,
            agent_name=agent_name,
            iteration=2,
            phase="EXECUTE",
            context_summary="Working on features",
            handoff_notes="Continue with task X",
        )
        defaults.update(kwargs)
        return AgentCheckpoint(**defaults)

    def test_build_resume_prompt_basic(self):
        session = self._make_session()
        checkpoints = {
            "team-leader": self._make_checkpoint("team-leader", "Orion"),
        }
        prompt = build_resume_prompt(session, checkpoints, {})
        assert "RESUMED SESSION" in prompt
        assert "test-session" in prompt
        assert "Orion" in prompt
        assert "iteration 2" in prompt

    def test_build_resume_prompt_with_changes(self):
        session = self._make_session()
        checkpoints = {}
        changes = {".claude/agents/backend-developer.md": "modified"}
        prompt = build_resume_prompt(session, checkpoints, changes)
        assert "Instruction files have been updated" in prompt
        assert "backend-developer.md" in prompt
        assert "modified" in prompt

    def test_build_resume_prompt_with_task(self):
        session = self._make_session()
        cp = self._make_checkpoint(
            "backend-developer", "Nova",
            current_task=TaskState(
                id="t1", description="Build auth API",
                started_at="2026-03-14T10:00:00Z",
                step_index=1, total_steps=3,
                step_description="Writing JWT middleware",
            ),
        )
        checkpoints = {"backend-developer": cp}
        prompt = build_resume_prompt(session, checkpoints, {})
        assert "Build auth API" in prompt

    def test_build_resume_prompt_no_checkpoints(self):
        session = self._make_session()
        prompt = build_resume_prompt(session, {}, {})
        assert "no agent checkpoints found" in prompt

    def test_build_agent_resume_context(self):
        cp = self._make_checkpoint(
            "backend-developer", "Nova",
            context_summary="Building REST API with JWT auth",
            handoff_notes="Next: implement user registration endpoint",
            decisions_made=[
                {"decision": "Use bcrypt for passwords", "reasoning": "Industry standard"},
            ],
            current_task=TaskState(
                id="t1", description="Auth API",
                started_at="2026-03-14T10:00:00Z",
                step_index=1, total_steps=3,
                step_description="JWT middleware",
            ),
        )
        context = build_agent_resume_context(cp)
        assert "Nova" in context
        assert "iteration 2" in context
        assert "EXECUTE" in context
        assert "Building REST API" in context
        assert "implement user registration" in context
        assert "bcrypt" in context
        assert "JWT middleware" in context

    def test_build_agent_resume_context_with_instruction_changes(self):
        cp = self._make_checkpoint("backend-developer", "Nova")
        changes = {".claude/agents/backend-developer.md": "modified"}
        context = build_agent_resume_context(cp, changes)
        assert "updated" in context.lower() or "modified" in context.lower()

    def test_build_agent_resume_context_with_conversation(self):
        cp = self._make_checkpoint(
            "backend-developer", "Nova",
            recent_conversation=[
                ConversationEntry(
                    role="user", content="Add rate limiting",
                    timestamp="2026-03-14T10:30:00Z",
                ),
                ConversationEntry(
                    role="assistant", content="Implementing token bucket",
                    timestamp="2026-03-14T10:31:00Z",
                ),
            ],
        )
        context = build_agent_resume_context(cp)
        assert "rate limiting" in context
        assert "token bucket" in context


# ---------------------------------------------------------------------------
# Stop signal tests
# ---------------------------------------------------------------------------


class TestStopSignal:
    def test_signal_stop_creates_sentinel(self, tmp_path):
        signal_stop(tmp_path)
        assert (tmp_path / "STOP_REQUESTED").exists()

    def test_is_stop_requested_true(self, tmp_path):
        signal_stop(tmp_path)
        assert is_stop_requested(tmp_path) is True

    def test_is_stop_requested_false(self, tmp_path):
        assert is_stop_requested(tmp_path) is False

    def test_clear_stop_signal(self, tmp_path):
        signal_stop(tmp_path)
        assert is_stop_requested(tmp_path) is True
        clear_stop_signal(tmp_path)
        assert is_stop_requested(tmp_path) is False

    def test_clear_stop_signal_idempotent(self, tmp_path):
        """Clearing when no sentinel exists should not error."""
        clear_stop_signal(tmp_path)
        assert is_stop_requested(tmp_path) is False

    def test_wait_for_agents_stopped_immediate(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(
            AgentCheckpoint(agent_type="a", agent_name="A", status="stopped"),
            checkpoints_dir,
        )
        write_checkpoint(
            AgentCheckpoint(agent_type="b", agent_name="B", status="complete"),
            checkpoints_dir,
        )
        stopped, timed_out = wait_for_agents_stopped(checkpoints_dir, timeout=1.0)
        assert set(stopped) == {"a", "b"}
        assert timed_out == []

    def test_wait_for_agents_stopped_timeout(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(
            AgentCheckpoint(agent_type="a", agent_name="A", status="active"),
            checkpoints_dir,
        )
        stopped, timed_out = wait_for_agents_stopped(
            checkpoints_dir, timeout=0.5, poll_interval=0.1,
        )
        assert "a" in timed_out

    def test_wait_for_agents_stopped_empty(self, tmp_path):
        stopped, timed_out = wait_for_agents_stopped(
            tmp_path / "empty", timeout=0.5, poll_interval=0.1,
        )
        assert stopped == []
        assert timed_out == []


# ---------------------------------------------------------------------------
# Cleanup tests
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_completed_checkpoints(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(
            AgentCheckpoint(agent_type="done", agent_name="Done", status="complete"),
            checkpoints_dir,
        )
        write_checkpoint(
            AgentCheckpoint(agent_type="active", agent_name="Active", status="active"),
            checkpoints_dir,
        )
        removed = cleanup_completed_checkpoints(checkpoints_dir)
        assert removed == ["done"]
        assert not (checkpoints_dir / "done.json").exists()
        assert (checkpoints_dir / "active.json").exists()

    def test_cleanup_completed_with_activity_log(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(
            AgentCheckpoint(agent_type="done", agent_name="Done", status="complete"),
            checkpoints_dir,
        )
        (checkpoints_dir / "done.activity.jsonl").write_text('{"tool": "Write"}\n')
        removed = cleanup_completed_checkpoints(checkpoints_dir)
        assert removed == ["done"]
        assert not (checkpoints_dir / "done.activity.jsonl").exists()

    def test_cleanup_empty_dir(self, tmp_path):
        removed = cleanup_completed_checkpoints(tmp_path / "nonexistent")
        assert removed == []

    def test_cleanup_stale_activity_logs(self, tmp_path):
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir()

        # Create an old log
        old_log = checkpoints_dir / "old.activity.jsonl"
        old_log.write_text('{"tool": "Write"}\n')
        # Set mtime to 10 days ago
        old_time = time.time() - (10 * 86400)
        import os
        os.utime(str(old_log), (old_time, old_time))

        # Create a recent log
        recent_log = checkpoints_dir / "recent.activity.jsonl"
        recent_log.write_text('{"tool": "Edit"}\n')

        removed = cleanup_stale_activity_logs(checkpoints_dir, max_age_days=7)
        assert "old.activity.jsonl" in removed
        assert recent_log.exists()


# ---------------------------------------------------------------------------
# Serialization roundtrip tests
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_checkpoint_roundtrip(self, tmp_path):
        """Full checkpoint survives write → read cycle."""
        cp = AgentCheckpoint(
            agent_type="backend-developer",
            agent_name="Nova",
            iteration=3,
            phase="REVIEW",
            phase_progress_pct=80,
            current_task=TaskState(
                id="t1", description="Auth",
                started_at="2026-03-14T10:00:00Z",
                step_index=2, total_steps=4,
                step_description="Testing",
            ),
            completed_tasks=[
                TaskState(
                    id="t0", description="Setup",
                    started_at="2026-03-14T09:00:00Z",
                    step_index=1, total_steps=1,
                    step_description="Done",
                ),
            ],
            pending_tasks=["Deploy", "Docs"],
            context_summary="Finishing auth module",
            decisions_made=[
                {"decision": "JWT", "reasoning": "Standard", "timestamp": "2026-03-14T10:00:00Z"},
            ],
            blockers=["Waiting for DB migration"],
            recent_conversation=[
                ConversationEntry(
                    role="user", content="Fix the auth bug",
                    timestamp="2026-03-14T10:00:00Z",
                ),
            ],
            files_modified=["src/auth.py", "src/db.py"],
            files_created=["src/auth.py"],
            branches=["feat-auth"],
            commits=["abc123"],
            sub_agents=[{"agent_type": "qa-engineer", "agent_name": "QA-1", "task": "Test auth", "status": "active"}],
            cost_usd=2.34,
            tool_call_count=42,
            handoff_notes="Review JWT expiry logic",
        )
        checkpoints_dir = tmp_path / "checkpoints"
        write_checkpoint(cp, checkpoints_dir)
        result = read_checkpoint("backend-developer", checkpoints_dir)

        assert result is not None
        assert result.agent_name == "Nova"
        assert result.iteration == 3
        assert result.phase == "REVIEW"
        assert result.current_task.description == "Auth"
        assert len(result.completed_tasks) == 1
        assert result.pending_tasks == ["Deploy", "Docs"]
        assert len(result.decisions_made) == 1
        assert result.blockers == ["Waiting for DB migration"]
        assert len(result.recent_conversation) == 1
        assert result.files_modified == ["src/auth.py", "src/db.py"]
        assert result.branches == ["feat-auth"]
        assert result.commits == ["abc123"]
        assert len(result.sub_agents) == 1
        assert result.cost_usd == 2.34
        assert result.tool_call_count == 42
        assert result.handoff_notes == "Review JWT expiry logic"

    def test_session_roundtrip(self, tmp_path):
        session = SessionState(
            forge_session_id=str(uuid4()),
            project_dir=str(tmp_path),
            project_name="my-project",
            config_hash="abc123",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T11:00:00Z",
            status="stopped",
            iteration=3,
            agent_tree={
                "team-leader": AgentMeta(
                    agent_type="team-leader", agent_name="Orion",
                ),
                "backend-developer": AgentMeta(
                    agent_type="backend-developer", agent_name="Nova",
                    parent_agent="team-leader",
                ),
            },
            cost_usd=12.34,
            cost_cap_usd=50.0,
            instruction_file_hashes={"a.md": "hash1"},
            stop_reason="explicit",
            tmux_session_name="forge-test",
        )
        write_session(session, tmp_path)
        result = read_session(tmp_path)

        assert result is not None
        assert result.project_name == "my-project"
        assert result.status == "stopped"
        assert result.iteration == 3
        assert len(result.agent_tree) == 2
        assert result.agent_tree["team-leader"].agent_name == "Orion"
        assert result.cost_usd == 12.34
        assert result.stop_reason == "explicit"
        assert result.tmux_session_name == "forge-test"
