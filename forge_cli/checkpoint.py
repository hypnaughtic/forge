"""Checkpoint/resume system for Forge agent teams.

Provides state persistence across sessions so agents can be stopped
and resumed with full context continuity. Session state and per-agent
checkpoints are stored in `.forge/` as JSON files.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TaskState(BaseModel):
    """State of a single agent task."""

    id: str
    description: str
    jira_ticket: str | None = None
    started_at: str  # ISO timestamp
    step_index: int
    total_steps: int
    step_description: str


class ConversationEntry(BaseModel):
    """A single entry in an agent's conversation history."""

    role: str  # user | assistant | system
    content: str  # Truncated to 500 chars
    timestamp: str
    tool_name: str | None = None


class AgentMeta(BaseModel):
    """Lightweight agent metadata stored in session.json."""

    agent_type: str
    agent_name: str
    parent_agent: str | None = None
    session_id: str | None = None
    status: str = "active"  # active | stopping | stopped | complete
    tmux_pane: str | None = None


class AgentCheckpoint(BaseModel):
    """Rich per-agent checkpoint with full context for resume."""

    version: str = "1"
    agent_type: str
    agent_name: str
    parent_agent: str | None = None
    session_id: str | None = None
    spawned_at: str = ""
    updated_at: str = ""
    status: str = "active"

    # Iteration state
    iteration: int = 1
    phase: str = "PLAN"
    phase_progress_pct: int = 0

    # Task tracking
    current_task: TaskState | None = None
    completed_tasks: list[TaskState] = Field(default_factory=list)
    pending_tasks: list[str] = Field(default_factory=list)

    # Context for reconstruction
    context_summary: str = ""
    decisions_made: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)

    # Conversation history
    recent_conversation: list[ConversationEntry] = Field(default_factory=list)
    conversation_summary: str = ""

    # Artifacts
    files_modified: list[str] = Field(default_factory=list)
    files_created: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    commits: list[str] = Field(default_factory=list)

    # Sub-agent hierarchy
    sub_agents: list[dict[str, Any]] = Field(default_factory=list)

    # Operational
    cost_usd: float = 0.0
    tool_call_count: int = 0
    error: str | None = None

    # Resume instructions
    handoff_notes: str = ""


class SessionState(BaseModel):
    """Root session state persisted to `.forge/session.json`."""

    version: str = "1"
    forge_session_id: str
    project_dir: str
    project_name: str
    config_hash: str
    started_at: str
    updated_at: str
    status: str = "running"  # running | stopped | complete
    iteration: int = 1
    agent_tree: dict[str, AgentMeta] = Field(default_factory=dict)
    cost_usd: float = 0.0
    cost_cap_usd: float = 50.0
    instruction_file_hashes: dict[str, str] = Field(default_factory=dict)
    stop_reason: str | None = None
    tmux_session_name: str | None = None


# ---------------------------------------------------------------------------
# I/O functions
# ---------------------------------------------------------------------------

_STOP_SENTINEL = "STOP_REQUESTED"


def _forge_dir(project_dir: Path) -> Path:
    return project_dir / ".forge"


def _checkpoints_dir(project_dir: Path) -> Path:
    return _forge_dir(project_dir) / "checkpoints"


def write_checkpoint(checkpoint: AgentCheckpoint, checkpoints_dir: Path) -> Path:
    """Atomically write an agent checkpoint (tmp + rename).

    Returns the final checkpoint path.
    """
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{checkpoint.agent_type}.json"
    final_path = checkpoints_dir / filename
    tmp_path = checkpoints_dir / f"{filename}.tmp"

    data = checkpoint.model_dump(mode="json")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.rename(final_path)
    return final_path


def read_checkpoint(agent_type: str, checkpoints_dir: Path) -> AgentCheckpoint | None:
    """Read an agent checkpoint with corruption recovery.

    Returns None if checkpoint doesn't exist or is corrupted.
    """
    path = checkpoints_dir / f"{agent_type}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return AgentCheckpoint.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def read_all_checkpoints(checkpoints_dir: Path) -> dict[str, AgentCheckpoint]:
    """Read all agent checkpoints from the checkpoints directory."""
    result: dict[str, AgentCheckpoint] = {}
    if not checkpoints_dir.exists():
        return result
    for path in checkpoints_dir.glob("*.json"):
        if path.name.endswith(".tmp"):
            continue
        agent_type = path.stem
        cp = read_checkpoint(agent_type, checkpoints_dir)
        if cp is not None:
            result[agent_type] = cp
    return result


def write_session(session: SessionState, forge_dir: Path) -> Path:
    """Atomically write session state."""
    forge_dir.mkdir(parents=True, exist_ok=True)
    final_path = forge_dir / "session.json"
    tmp_path = forge_dir / "session.json.tmp"

    data = session.model_dump(mode="json")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.rename(final_path)
    return final_path


def read_session(forge_dir: Path) -> SessionState | None:
    """Read session state with validation.

    Returns None if session doesn't exist or is corrupted.
    """
    path = forge_dir / "session.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return SessionState.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Hash functions
# ---------------------------------------------------------------------------


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_config_hash(config_path: Path) -> str:
    """Compute SHA256 hash of the forge config file."""
    if not config_path.exists():
        return ""
    return compute_file_hash(config_path)


def compute_instruction_hashes(project_dir: Path) -> dict[str, str]:
    """Compute SHA256 hashes for all instruction files.

    Covers `.claude/agents/*.md` and `.claude/skills/*.md`.
    """
    hashes: dict[str, str] = {}
    claude_dir = project_dir / ".claude"

    for subdir in ("agents", "skills"):
        target = claude_dir / subdir
        if target.exists():
            for md_file in sorted(target.glob("*.md")):
                rel = str(md_file.relative_to(project_dir))
                hashes[rel] = compute_file_hash(md_file)

    # Also hash CLAUDE.md and team-init-plan.md
    for root_file in ("CLAUDE.md", "team-init-plan.md"):
        p = project_dir / root_file
        if p.exists():
            hashes[root_file] = compute_file_hash(p)

    return hashes


def detect_instruction_changes(
    stored_hashes: dict[str, str],
    current_hashes: dict[str, str],
) -> dict[str, str]:
    """Detect which instruction files changed between sessions.

    Returns a dict of {path: change_type} where change_type is
    'modified', 'added', or 'removed'.
    """
    changes: dict[str, str] = {}
    all_paths = set(stored_hashes) | set(current_hashes)

    for path in all_paths:
        if path not in stored_hashes:
            changes[path] = "added"
        elif path not in current_hashes:
            changes[path] = "removed"
        elif stored_hashes[path] != current_hashes[path]:
            changes[path] = "modified"

    return changes


# ---------------------------------------------------------------------------
# Resume prompt building
# ---------------------------------------------------------------------------


def build_resume_prompt(
    session: SessionState,
    checkpoints: dict[str, AgentCheckpoint],
    changes: dict[str, str],
) -> str:
    """Construct the Team Leader resume prompt.

    This prompt is injected when `forge resume` launches Claude,
    giving the TL full context to reconstruct the agent team.
    """
    # Build agent summary
    agent_lines: list[str] = []
    for agent_type, cp in checkpoints.items():
        status = cp.status
        line = (
            f"  - {agent_type} ({cp.agent_name}): "
            f"iteration {cp.iteration}, phase {cp.phase}, "
            f"status={status}"
        )
        if cp.current_task:
            line += f", working on: {cp.current_task.description[:80]}"
        agent_lines.append(line)
    agent_summary = "\n".join(agent_lines) if agent_lines else "  (no agent checkpoints found)"

    # Build change notice
    change_notice = ""
    if changes:
        change_lines = [f"  - {path}: {change}" for path, change in changes.items()]
        change_notice = (
            "\nNOTE: Instruction files have been updated since last session:\n"
            + "\n".join(change_lines)
            + "\nUse the LATEST instruction files from `.claude/agents/` — "
            "they may contain improved guidance.\n"
        )

    return f"""\
THIS IS A RESUMED SESSION. Read CLAUDE.md and your instruction file first.

Previous session state:
- Session ID: {session.forge_session_id}
- Iteration: {session.iteration}
- Status before stop: {session.status}
- Stop reason: {session.stop_reason or 'unknown'}
- Cost so far: ${session.cost_usd:.2f} / ${session.cost_cap_usd:.2f}

Active agents and their checkpoints:
{agent_summary}
{change_notice}
Your checkpoint is at .forge/checkpoints/team-leader.json — run /checkpoint load

After loading your checkpoint, re-spawn all agents that were active, injecting
their checkpoint context into their spawn prompts. Resume from where you left off.
Do NOT restart completed work. Do NOT generate new agent names — use the names
from the checkpoints.
"""


def build_agent_resume_context(
    checkpoint: AgentCheckpoint,
    instruction_changes: dict[str, str] | None = None,
) -> str:
    """Build resume context for a single agent's spawn prompt."""
    change_note = ""
    agent_file = f".claude/agents/{checkpoint.agent_type}.md"
    if instruction_changes and agent_file in instruction_changes:
        change_note = (
            f"\nNOTE: Your instruction file ({agent_file}) has been "
            f"{instruction_changes[agent_file]} since your last session. "
            "Follow the updated guidance while preserving your task state.\n"
        )

    decisions_text = ""
    if checkpoint.decisions_made:
        decision_lines = []
        for d in checkpoint.decisions_made[:10]:
            decision_lines.append(
                f"  - {d.get('decision', 'unknown')}: {d.get('reasoning', '')[:100]}"
            )
        decisions_text = "\nYour previous decisions:\n" + "\n".join(decision_lines)

    conversation_text = ""
    if checkpoint.recent_conversation:
        conv_lines = []
        for entry in checkpoint.recent_conversation[-10:]:
            content_preview = entry.content[:200]
            conv_lines.append(f"  [{entry.role}]: {content_preview}")
        conversation_text = "\nRecent conversation context:\n" + "\n".join(conv_lines)

    return f"""\
You are RESUMING. Your name is {checkpoint.agent_name}. You were on iteration \
{checkpoint.iteration}, phase {checkpoint.phase} ({checkpoint.phase_progress_pct}% complete).

Your previous context: {checkpoint.context_summary}
{decisions_text}
Your handoff notes: {checkpoint.handoff_notes}
{conversation_text}
{change_note}
Resume from: {checkpoint.current_task.step_description if checkpoint.current_task else 'your last checkpoint state'}

Run /checkpoint load for full state.
"""


# ---------------------------------------------------------------------------
# Stop signal management
# ---------------------------------------------------------------------------


def signal_stop(forge_dir: Path) -> Path:
    """Write the STOP_REQUESTED sentinel file."""
    forge_dir.mkdir(parents=True, exist_ok=True)
    sentinel = forge_dir / _STOP_SENTINEL
    sentinel.write_text(f"Stop requested at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    return sentinel


def is_stop_requested(forge_dir: Path) -> bool:
    """Check if the STOP_REQUESTED sentinel exists."""
    return (forge_dir / _STOP_SENTINEL).exists()


def clear_stop_signal(forge_dir: Path) -> None:
    """Remove the STOP_REQUESTED sentinel file."""
    sentinel = forge_dir / _STOP_SENTINEL
    if sentinel.exists():
        sentinel.unlink()


def wait_for_agents_stopped(
    checkpoints_dir: Path,
    timeout: float = 60.0,
    poll_interval: float = 2.0,
) -> tuple[list[str], list[str]]:
    """Poll checkpoints until all agents reach stopped/complete status.

    Returns (stopped_agents, timed_out_agents).
    """
    deadline = time.monotonic() + timeout
    stopped: set[str] = set()
    all_agents: set[str] = set()

    while time.monotonic() < deadline:
        checkpoints = read_all_checkpoints(checkpoints_dir)
        all_agents = set(checkpoints.keys())

        stopped = {
            agent_type
            for agent_type, cp in checkpoints.items()
            if cp.status in ("stopped", "complete")
        }

        if stopped == all_agents and all_agents:
            return list(stopped), []

        time.sleep(poll_interval)

    # Timeout — report who didn't stop
    timed_out = list(all_agents - stopped)
    return list(stopped), timed_out


# ---------------------------------------------------------------------------
# Cleanup functions
# ---------------------------------------------------------------------------


def cleanup_completed_checkpoints(checkpoints_dir: Path) -> list[str]:
    """Remove checkpoints for agents with status=complete.

    Returns list of removed agent types.
    """
    removed: list[str] = []
    if not checkpoints_dir.exists():
        return removed

    for path in checkpoints_dir.glob("*.json"):
        if path.name.endswith(".tmp"):
            continue
        try:
            data = json.loads(path.read_text())
            if data.get("status") == "complete":
                path.unlink()
                removed.append(path.stem)
                # Also remove activity log
                activity = path.with_suffix(".activity.jsonl")
                if activity.exists():
                    activity.unlink()
        except (json.JSONDecodeError, OSError):
            continue

    return removed


def cleanup_stale_activity_logs(
    checkpoints_dir: Path,
    max_age_days: int = 7,
) -> list[str]:
    """Remove activity logs older than max_age_days.

    Returns list of removed filenames.
    """
    removed: list[str] = []
    if not checkpoints_dir.exists():
        return removed

    cutoff = time.time() - (max_age_days * 86400)

    for path in checkpoints_dir.glob("*.activity.jsonl"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path.name)

    return removed
