"""Shared data models for Forge checkpoint/session system.

All shared Pydantic models live here. Both session.py and checkpoint.py
import from this module — never from each other. This eliminates circular
import issues.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


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
    checkpoint_path: str = ""
    status: str = "registered"  # registered | active | stopping | stopped | complete | compaction_pending
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

    # Context rot reduction fields
    context_anchor_updated_at: str = ""
    compaction_count: int = 0
    essential_files: list[str] = Field(default_factory=list)

    @field_validator("essential_files")
    @classmethod
    def truncate_essential_files(cls, v: list[str]) -> list[str]:
        """Truncate essential_files to a maximum of 10 entries."""
        if len(v) > 10:
            logger.warning(
                "essential_files has %d entries, truncating to 10", len(v)
            )
            return v[:10]
        return v


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
