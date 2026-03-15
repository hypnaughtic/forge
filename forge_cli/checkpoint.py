"""Checkpoint I/O for Forge agent teams.

Provides checkpoint persistence (write/read/scan) with hierarchical
directory structure: {checkpoints_dir}/{agent_type}/{agent_name}.json

All data models are imported from models.py. Session-related functions
are in session.py. This module handles only checkpoint file I/O.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

from forge_cli.models import (
    AgentCheckpoint,
    AgentMeta,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Re-exports for backward compatibility during migration
# ---------------------------------------------------------------------------

from forge_cli.models import (  # noqa: E402, F811
    AgentCheckpoint as AgentCheckpoint,
    AgentMeta as AgentMeta,
    ConversationEntry as ConversationEntry,
    SessionState as SessionState,
    TaskState as TaskState,
)

from forge_cli.session import (  # noqa: E402
    build_agent_resume_context as build_agent_resume_context,
    build_resume_prompt as build_resume_prompt,
    clear_stop_signal as clear_stop_signal,
    is_stop_requested as is_stop_requested,
    read_session as read_session,
    signal_stop as signal_stop,
    wait_for_agents_stopped as wait_for_agents_stopped,
    write_session as write_session,
)


# ---------------------------------------------------------------------------
# Checkpoint I/O (hierarchical paths)
# ---------------------------------------------------------------------------


def write_checkpoint(checkpoint: AgentCheckpoint, checkpoints_dir: Path) -> Path:
    """Atomically write an agent checkpoint to hierarchical path.

    Path: {checkpoints_dir}/{agent_type}/{agent_name}.json
    """
    type_dir = checkpoints_dir / checkpoint.agent_type
    type_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{checkpoint.agent_name}.json"
    final_path = type_dir / filename
    tmp_path = type_dir / f"{filename}.tmp"

    data = checkpoint.model_dump(mode="json")
    tmp_path.write_text(json.dumps(data, indent=2))
    tmp_path.rename(final_path)
    return final_path


def read_checkpoint(
    agent_type: str,
    checkpoints_dir: Path,
    agent_name: str | None = None,
) -> AgentCheckpoint | None:
    """Read an agent checkpoint with corruption recovery.

    Supports both hierarchical ({type}/{name}.json) and legacy ({type}.json) paths.
    """
    if agent_name:
        path = checkpoints_dir / agent_type / f"{agent_name}.json"
    else:
        path = checkpoints_dir / f"{agent_type}.json"

    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return AgentCheckpoint.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def read_all_checkpoints(checkpoints_dir: Path) -> dict[str, AgentCheckpoint]:
    """Read all agent checkpoints from hierarchical directory structure.

    Scans type subdirectories, returns dict keyed by agent_name.
    Also scans root for legacy flat checkpoints.
    """
    result: dict[str, AgentCheckpoint] = {}
    if not checkpoints_dir.exists():
        return result

    for type_dir in checkpoints_dir.iterdir():
        if type_dir.is_dir():
            for path in type_dir.glob("*.json"):
                if path.name.endswith(".tmp"):
                    continue
                try:
                    data = json.loads(path.read_text())
                    cp = AgentCheckpoint.model_validate(data)
                    result[cp.agent_name] = cp
                except (json.JSONDecodeError, ValueError):
                    continue

    for path in checkpoints_dir.glob("*.json"):
        if path.name.endswith(".tmp"):
            continue
        if path.stem not in result:
            try:
                data = json.loads(path.read_text())
                cp = AgentCheckpoint.model_validate(data)
                if cp.agent_name not in result:
                    result[cp.agent_name] = cp
            except (json.JSONDecodeError, ValueError):
                continue

    return result


def validate_checkpoints_against_tree(
    checkpoints: dict[str, AgentCheckpoint],
    agent_tree: dict[str, AgentMeta],
    checkpoints_dir: Path,
) -> tuple[list[str], list[str], list[str]]:
    """Validate checkpoint files against agent_tree.

    Returns (orphan_checkpoints, missing_checkpoints, ghost_agents).
    """
    checkpoint_names = set(checkpoints.keys())
    tree_names = {
        name for name, meta in agent_tree.items() if meta.status != "complete"
    }
    orphans = list(checkpoint_names - set(agent_tree.keys()))
    missing_names = tree_names - checkpoint_names

    ghosts: list[str] = []
    missing: list[str] = []
    for name in missing_names:
        meta = agent_tree[name]
        activity_path = (
            checkpoints_dir / meta.agent_type / f"{name}.activity.jsonl"
        )
        if meta.status == "registered" and not activity_path.exists():
            ghosts.append(name)
        else:
            missing.append(name)

    return orphans, missing, ghosts


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
    """Compute SHA256 hashes for all instruction files."""
    hashes: dict[str, str] = {}
    claude_dir = project_dir / ".claude"

    for subdir in ("agents", "skills"):
        target = claude_dir / subdir
        if target.exists():
            for md_file in sorted(target.glob("*.md")):
                rel = str(md_file.relative_to(project_dir))
                hashes[rel] = compute_file_hash(md_file)

    for root_file in ("CLAUDE.md", "team-init-plan.md"):
        p = project_dir / root_file
        if p.exists():
            hashes[root_file] = compute_file_hash(p)

    return hashes


def detect_instruction_changes(
    stored_hashes: dict[str, str],
    current_hashes: dict[str, str],
) -> dict[str, str]:
    """Detect which instruction files changed between sessions."""
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
# Cleanup functions
# ---------------------------------------------------------------------------


def cleanup_completed_checkpoints(checkpoints_dir: Path) -> list[str]:
    """Remove checkpoints for agents with status=complete. Scans hierarchical structure."""
    removed: list[str] = []
    if not checkpoints_dir.exists():
        return removed

    for path in checkpoints_dir.glob("**/*.json"):
        if path.name.endswith(".tmp"):
            continue
        try:
            data = json.loads(path.read_text())
            if data.get("status") == "complete":
                agent_name = data.get("agent_name", path.stem)
                path.unlink()
                removed.append(agent_name)
                activity = path.with_name(f"{path.stem}.activity.jsonl")
                if activity.exists():
                    activity.unlink()
        except (json.JSONDecodeError, OSError):
            continue

    return removed


def cleanup_stale_activity_logs(
    checkpoints_dir: Path,
    max_age_days: int = 7,
) -> list[str]:
    """Remove activity logs older than max_age_days. Scans hierarchical structure."""
    removed: list[str] = []
    if not checkpoints_dir.exists():
        return removed

    cutoff = time.time() - (max_age_days * 86400)

    for path in checkpoints_dir.glob("**/*.activity.jsonl"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path.name)

    return removed
