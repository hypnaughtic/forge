"""Session state management and event inbox for Forge.

This module owns all session state logic: reading/writing session.json,
the event inbox (atomic file creation for concurrent writes), and
session materialization. Imports models from models.py.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from forge_cli.models import (
    AgentCheckpoint,
    AgentMeta,
    SessionState,
)

logger = logging.getLogger(__name__)

EVENTS_DIR_NAME = "events"
EVENTS_ARCHIVE_NAME = "events-archive.jsonl"


# ---------------------------------------------------------------------------
# Session I/O
# ---------------------------------------------------------------------------


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
# Event inbox
# ---------------------------------------------------------------------------


def write_event(forge_dir: Path, event: dict) -> Path:
    """Write a single event to the inbox as an individual file.

    File creation is atomic on all platforms — no locking needed.
    Filename format: {ISO-timestamp}-{pid}-{nonce}.json
    """
    events_dir = forge_dir / EVENTS_DIR_NAME
    events_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    ts = now.strftime("%Y%m%dT%H%M%S%fZ")
    pid = os.getpid()
    nonce = uuid.uuid4().hex[:8]
    filename = f"{ts}-{pid}-{nonce}.json"

    event_with_meta = {
        "timestamp": now.isoformat(),
        **event,
    }

    path = events_dir / filename
    tmp_path = events_dir / f"{filename}.tmp"
    tmp_path.write_text(json.dumps(event_with_meta, indent=2))
    tmp_path.rename(path)
    return path


def read_events(forge_dir: Path) -> tuple[list[dict], list[Path]]:
    """Read all pending events, sorted chronologically by filename.

    Returns (events, paths) — paths are the exact files read, used for
    targeted cleanup. This prevents a race where a new event written
    between read and cleanup would be deleted unprocessed.
    """
    events_dir = forge_dir / EVENTS_DIR_NAME
    if not events_dir.exists():
        return [], []
    events: list[dict] = []
    paths: list[Path] = []
    for path in sorted(events_dir.glob("*.json")):
        if path.name.endswith(".tmp"):
            continue
        try:
            events.append(json.loads(path.read_text()))
            paths.append(path)
        except (json.JSONDecodeError, ValueError):
            continue
    return events, paths


def materialize_session(forge_dir: Path) -> SessionState:
    """Materialize session.json from base state + pending events.

    This is the ONLY function that writes session.json. Called at:
    forge stop, forge resume, forge status.
    """
    session = read_session(forge_dir)
    if session is None:
        now = datetime.now(UTC).isoformat()
        session = SessionState(
            forge_session_id=uuid.uuid4().hex,
            project_dir=str(forge_dir.parent),
            project_name="",
            config_hash="",
            started_at=now,
            updated_at=now,
        )

    events, event_paths = read_events(forge_dir)
    for event in events:
        _apply_event(session, event)

    session.updated_at = datetime.now(UTC).isoformat()
    write_session(session, forge_dir)
    _archive_and_cleanup_events(forge_dir, events, event_paths)
    return session


def _apply_event(session: SessionState, event: dict) -> None:
    """Apply a single event. All handlers are idempotent (set operations)."""
    event_type = event.get("event")
    tree = session.agent_tree

    if event_type == "agent_registered":
        name = event.get("agent_name", "")
        if name and name not in tree:  # idempotent: no-op if already registered
            tree[name] = AgentMeta(
                agent_type=event.get("agent_type", "unknown"),
                agent_name=name,
                parent_agent=event.get("parent_agent"),
                checkpoint_path=event.get("checkpoint_path", ""),
                status="registered",
            )

    elif event_type == "agent_started":
        name = event.get("agent_name", "")
        if name and name in tree:  # idempotent: overwrites session_id
            tree[name].session_id = event.get("session_id", "")
            tree[name].status = "active"

    elif event_type == "agent_stopped":
        name = event.get("agent_name", "")
        if name and name in tree:  # idempotent: sets status
            tree[name].status = "stopped"

    elif event_type == "compaction_needed":
        name = event.get("agent_name", "")
        if name and name in tree:  # signals parent to respawn this agent
            tree[name].status = "compaction_pending"


def _archive_and_cleanup_events(
    forge_dir: Path,
    events: list[dict],
    event_paths: list[Path],
) -> None:
    """Archive processed events to JSONL, delete only the files that were read.

    Only deletes the specific files in event_paths — any new events written
    after read_events() are preserved for the next materialization cycle.
    """
    if not events:
        return

    archive_path = forge_dir / EVENTS_ARCHIVE_NAME

    with open(archive_path, "a") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    for path in event_paths:
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Hierarchy helpers
# ---------------------------------------------------------------------------


def _get_direct_children(
    agent_tree: dict[str, AgentMeta],
    parent_name: str | None,
) -> dict[str, AgentMeta]:
    """Return agents whose parent_agent == parent_name."""
    return {
        name: meta
        for name, meta in agent_tree.items()
        if meta.parent_agent == parent_name
    }


# ---------------------------------------------------------------------------
# Resume prompt building
# ---------------------------------------------------------------------------


def build_resume_prompt(
    session: SessionState,
    checkpoints: dict[str, AgentCheckpoint],
    changes: dict[str, str],
) -> str:
    """Construct the Team Leader resume prompt.

    Hierarchy-aware: only lists TL's direct children.
    """
    # Find TL name and checkpoint path
    tl_name = None
    tl_checkpoint_path = None
    for name, meta in session.agent_tree.items():
        if meta.agent_type == "team-leader":
            tl_name = name
            tl_checkpoint_path = meta.checkpoint_path
            break

    # Only list TL's DIRECT children
    direct_children = _get_direct_children(session.agent_tree, tl_name)
    agent_lines: list[str] = []
    for agent_name, meta in direct_children.items():
        cp = checkpoints.get(agent_name)
        status = cp.status if cp else "no-checkpoint"
        # Count this agent's own sub-agents for visibility
        grandchildren = _get_direct_children(session.agent_tree, agent_name)
        line = (
            f"  - {agent_name} ({meta.agent_type}): "
            f"checkpoint={meta.checkpoint_path}, status={status}"
        )
        if grandchildren:
            line += f", has {len(grandchildren)} sub-agent(s)"
        if cp and cp.current_task:
            line += f", working on: {cp.current_task.description[:80]}"
        agent_lines.append(line)
    agent_summary = "\n".join(agent_lines) if agent_lines else "  (no agents)"

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

Your name is {tl_name}.
Your checkpoint: {tl_checkpoint_path} — run /checkpoint load

Previous session state:
- Session ID: {session.forge_session_id}
- Iteration: {session.iteration}
- Status before stop: {session.status}
- Stop reason: {session.stop_reason or 'unknown'}
- Cost so far: ${session.cost_usd:.2f} / ${session.cost_cap_usd:.2f}

Re-spawn YOUR DIRECT agents with their EXACT names and checkpoint paths:
{agent_summary}
{change_notice}
After loading your checkpoint, re-spawn ONLY the agents listed above (your direct
reports). Each agent's checkpoint contains ITS OWN sub-agents — they will re-spawn
their children recursively. Use the EXACT names above.
Do NOT restart completed work. Do NOT generate new agent names.
Do NOT spawn agents that belong to a sub-team — let the sub-team leader handle them.
"""


def build_agent_resume_context(
    checkpoint: AgentCheckpoint,
    checkpoint_path: str,
    agent_tree: dict[str, AgentMeta] | None = None,
    checkpoints: dict[str, AgentCheckpoint] | None = None,
    instruction_changes: dict[str, str] | None = None,
) -> str:
    """Build resume context for a single agent spawn.

    Includes the agent's own sub-agents (direct children) so mid-level
    agents can re-spawn their teams recursively.
    """
    # Build children section if agent_tree provided
    child_section = ""
    if agent_tree and checkpoints:
        children = _get_direct_children(agent_tree, checkpoint.agent_name)
        child_lines: list[str] = []
        for name, meta in children.items():
            cp = checkpoints.get(name)
            status = cp.status if cp else "no-checkpoint"
            child_lines.append(
                f"  - {name} ({meta.agent_type}): "
                f"checkpoint={meta.checkpoint_path}, status={status}"
            )
        if child_lines:
            child_section = (
                "\nYour sub-agents to re-spawn (YOUR direct reports only):\n"
                + "\n".join(child_lines)
                + "\n\nRe-spawn these with their EXACT names. Their checkpoints contain their own\n"
                "sub-agents — they will handle recursive re-spawning.\n"
            )

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

    base_context = f"""\
You are {checkpoint.agent_name}, a {checkpoint.agent_type}.
Your checkpoint: {checkpoint_path} — run /checkpoint load
Your parent: {checkpoint.parent_agent or 'team-leader'}

You are RESUMING. You were on iteration \
{checkpoint.iteration}, phase {checkpoint.phase} ({checkpoint.phase_progress_pct}% complete).

Your previous context: {checkpoint.context_summary}
{decisions_text}
Your handoff notes: {checkpoint.handoff_notes}
{conversation_text}
{child_section}
{change_note}
Resume from: {checkpoint.current_task.step_description if checkpoint.current_task else 'your last checkpoint state'}

FIRST ACTION: Run /agent-init resume
"""
    return base_context


# ---------------------------------------------------------------------------
# Stop signal management
# ---------------------------------------------------------------------------

_STOP_SENTINEL = "STOP_REQUESTED"


def signal_stop(forge_dir: Path) -> Path:
    """Write the STOP_REQUESTED sentinel file."""
    forge_dir.mkdir(parents=True, exist_ok=True)
    sentinel = forge_dir / _STOP_SENTINEL
    sentinel.write_text(
        f"Stop requested at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
    )
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
    agent_tree: dict[str, AgentMeta] | None = None,
    timeout: float = 60.0,
    poll_interval: float = 2.0,
) -> tuple[list[str], list[str]]:
    """Poll checkpoints until all agents reach stopped/complete status.

    Returns (stopped_agents, timed_out_agents).
    Uses agent_tree for authoritative roster if provided.
    """
    from forge_cli.checkpoint import read_all_checkpoints

    deadline = time.monotonic() + timeout
    stopped: set[str] = set()

    if agent_tree:
        expected_agents = {
            name for name, meta in agent_tree.items() if meta.status == "active"
        }
    else:
        expected_agents = None

    while time.monotonic() < deadline:
        checkpoints = read_all_checkpoints(checkpoints_dir)

        if expected_agents is not None:
            stopped = {
                name
                for name, cp in checkpoints.items()
                if name in expected_agents
                and cp.status in ("stopped", "complete")
            }
            if stopped == expected_agents:
                return list(stopped), []
        else:
            all_agents = set(checkpoints.keys())
            stopped = {
                agent_name
                for agent_name, cp in checkpoints.items()
                if cp.status in ("stopped", "complete")
            }
            if stopped == all_agents and all_agents:
                return list(stopped), []

        time.sleep(poll_interval)

    # Timeout — report who didn't stop
    if expected_agents is not None:
        timed_out = list(expected_agents - stopped)
    else:
        timed_out = list(set(checkpoints.keys()) - stopped) if checkpoints else []
    return list(stopped), timed_out
