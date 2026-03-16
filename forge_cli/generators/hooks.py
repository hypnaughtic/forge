"""Generate hook scripts for checkpoint enforcement.

Hook scripts are written to `.forge/hooks/` and referenced by
`.claude/settings.json`. They capture agent activity, remind agents
to checkpoint, and detect stop signals.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from forge_cli.config_schema import ForgeConfig


def generate_hook_scripts(config: ForgeConfig | None, forge_dir: Path) -> list[Path]:
    """Generate all hook scripts to `.forge/hooks/`.

    Also generates `.forge/scripts/resolve_identity.py` for agent
    identity resolution used by all hooks.

    Args:
        config: Forge configuration (None uses defaults).
        forge_dir: The `.forge/` directory.

    Returns:
        List of paths to generated hook scripts.
    """
    hooks_dir = forge_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Generate resolve_identity.py helper script
    scripts_dir = forge_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    identity_path = scripts_dir / "resolve_identity.py"
    identity_path.write_text(_resolve_identity_script())
    _make_executable(identity_path)

    # Extract compaction config with safe defaults for None config
    if config is not None:
        compaction_threshold = config.compaction.compaction_threshold_tokens
        anchor_interval = config.compaction.anchor_interval_minutes
    else:
        compaction_threshold = 100_000
        anchor_interval = 15

    scripts: list[Path] = []

    # Post-tool checkpoint (Write|Edit)
    path = hooks_dir / "post-tool-checkpoint.sh"
    path.write_text(_post_tool_checkpoint_script(compaction_threshold, anchor_interval))
    _make_executable(path)
    scripts.append(path)

    # Bash checkpoint reminder (with activity tracking + compaction)
    path = hooks_dir / "bash-checkpoint-reminder.sh"
    path.write_text(_bash_checkpoint_reminder_script(compaction_threshold, anchor_interval))
    _make_executable(path)
    scripts.append(path)

    # Pre-compact checkpoint
    path = hooks_dir / "pre-compact-checkpoint.sh"
    path.write_text(_pre_compact_checkpoint_script())
    _make_executable(path)
    scripts.append(path)

    # Generic activity tracking (Read|Glob|Grep|Agent — tools not covered above)
    path = hooks_dir / "generic-activity-tracker.sh"
    path.write_text(_generic_activity_tracker_script(compaction_threshold))
    _make_executable(path)
    scripts.append(path)

    # Subagent lifecycle
    path = hooks_dir / "subagent-lifecycle.sh"
    path.write_text(_subagent_lifecycle_script())
    _make_executable(path)
    scripts.append(path)

    # Stop checkpoint
    path = hooks_dir / "stop-checkpoint.sh"
    path.write_text(_stop_checkpoint_script())
    _make_executable(path)
    scripts.append(path)

    return scripts


def _make_executable(path: Path) -> None:
    """Add execute permission to a file."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _resolve_identity_script() -> str:
    """Generate .forge/scripts/resolve_identity.py.

    Two-tier identity resolution:
    1. Look up session_id in session.json agent_tree
    2. Scan .forge/events/ for agent_started events matching session_id
    Returns JSON: {"agent_type": "...", "agent_name": "..."}
    """
    return '''\
#!/usr/bin/env python3
"""Resolve agent identity from session_id.

Two-tier resolution:
1. session.json agent_tree lookup
2. .forge/events/ scan for agent_started events
"""
import json
import sys
from pathlib import Path


def resolve(forge_dir: str, session_id: str) -> dict:
    """Return {"agent_type": str, "agent_name": str}."""
    forge = Path(forge_dir)
    result = {"agent_type": "unknown", "agent_name": "unknown"}

    if not session_id:
        return result

    # Tier 1: session.json
    session_file = forge / "session.json"
    if session_file.exists():
        try:
            session = json.loads(session_file.read_text())
            for agent_type, meta in session.get("agent_tree", {}).items():
                if meta.get("session_id", "") == session_id:
                    result["agent_type"] = agent_type
                    result["agent_name"] = meta.get("agent_name", agent_type)
                    return result
        except (json.JSONDecodeError, OSError):
            pass

    # Tier 2: events directory scan
    events_dir = forge / "events"
    if events_dir.is_dir():
        try:
            for event_file in sorted(events_dir.glob("*.json"), reverse=True):
                event = json.loads(event_file.read_text())
                if (
                    (event.get("type") or event.get("event_type") or event.get("event")) == "agent_started"
                    and event.get("session_id") == session_id
                ):
                    result["agent_type"] = event.get("agent_type", "unknown")
                    result["agent_name"] = event.get("agent_name", "unknown")
                    return result
        except (json.JSONDecodeError, OSError):
            pass

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"agent_type": "unknown", "agent_name": "unknown"}))
        sys.exit(0)
    print(json.dumps(resolve(sys.argv[1], sys.argv[2])))
'''


def _post_tool_checkpoint_script(
    compaction_threshold: int,
    anchor_interval: int,
) -> str:
    """Hook for PostToolUse on Write|Edit.

    Logs activity, reminds about checkpoints, tracks tokens for
    cooperative compaction, and checks anchor freshness.
    """
    return f'''\
#!/usr/bin/env bash
# Forge hook: PostToolUse (Write|Edit)
# Appends to activity log, reminds about checkpoints, tracks tokens,
# checks anchor freshness.
set -euo pipefail

FORGE_DIR="${{CLAUDE_PROJECT_DIR:-.}}/.forge"
CHECKPOINTS_DIR="${{FORGE_DIR}}/checkpoints"
mkdir -p "${{CHECKPOINTS_DIR}}"

# Read tool input from stdin
INPUT=$(cat)

TOOL_NAME=$(echo "${{INPUT}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "${{INPUT}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "${{INPUT}}" | python3 -c "import sys,json; d=json.load(sys.stdin); i=d.get('tool_input',{{}}); print(i.get('file_path', i.get('path','')))" 2>/dev/null || echo "")

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Resolve agent identity via resolve_identity.py
IDENTITY=$(python3 "${{FORGE_DIR}}/scripts/resolve_identity.py" "${{FORGE_DIR}}" "${{SESSION_ID}}" 2>/dev/null || echo '{{"agent_type":"unknown","agent_name":"unknown"}}')
AGENT_TYPE=$(echo "${{IDENTITY}}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_type','unknown'))" 2>/dev/null || echo "unknown")
AGENT_NAME=$(echo "${{IDENTITY}}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_name','unknown'))" 2>/dev/null || echo "unknown")

# Ensure hierarchical checkpoint directory exists
AGENT_CKPT_DIR="${{CHECKPOINTS_DIR}}/${{AGENT_TYPE}}"
mkdir -p "${{AGENT_CKPT_DIR}}"

LOG_FILE="${{AGENT_CKPT_DIR}}/${{AGENT_NAME}}.activity.jsonl"

# Append activity entry
echo "{{\\"timestamp\\":\\"${{TIMESTAMP}}\\",\\"tool\\":\\"${{TOOL_NAME}}\\",\\"file\\":\\"${{FILE_PATH}}\\",\\"session_id\\":\\"${{SESSION_ID}}\\"}}" >> "${{LOG_FILE}}" 2>/dev/null || true

# Check if rich checkpoint is stale (>10 min old)
CHECKPOINT_FILE="${{AGENT_CKPT_DIR}}/${{AGENT_NAME}}.json"
if [ -f "${{CHECKPOINT_FILE}}" ]; then
    CHECKPOINT_AGE=$(( $(date +%s) - $(stat -f %m "${{CHECKPOINT_FILE}}" 2>/dev/null || stat -c %Y "${{CHECKPOINT_FILE}}" 2>/dev/null || echo "0") ))
    if [ "${{CHECKPOINT_AGE}}" -gt 600 ]; then
        echo "CHECKPOINT REMINDER: Your last checkpoint is $((${{CHECKPOINT_AGE}} / 60)) min old. Run /checkpoint save now."
    fi
fi

# Token tracking — cooperative compaction trigger
# Heuristic: bytes/4 for token estimation
COMPACTION_THRESHOLD={compaction_threshold}
if [ -f "${{LOG_FILE}}" ]; then
    LOG_BYTES=$(wc -c < "${{LOG_FILE}}" 2>/dev/null || echo "0")
    ESTIMATED_TOKENS=$(( LOG_BYTES / 4 ))
    if [ "${{ESTIMATED_TOKENS}}" -gt "${{COMPACTION_THRESHOLD}}" ]; then
        # Emit compaction_needed event
        EVENTS_DIR="${{FORGE_DIR}}/events"
        mkdir -p "${{EVENTS_DIR}}"
        EVENT_FILE="${{EVENTS_DIR}}/$(date +%s%N)-compaction-needed.json"
        TMP_EVENT="${{EVENT_FILE}}.tmp"
        echo "{{\\"type\\":\\"compaction_needed\\",\\"event\\":\\"compaction_needed\\",\\"agent_type\\":\\"${{AGENT_TYPE}}\\",\\"agent_name\\":\\"${{AGENT_NAME}}\\",\\"estimated_tokens\\":${{ESTIMATED_TOKENS}},\\"threshold\\":{compaction_threshold},\\"timestamp\\":\\"${{TIMESTAMP}}\\"}}" > "${{TMP_EVENT}}"
        mv "${{TMP_EVENT}}" "${{EVENT_FILE}}" 2>/dev/null || true
        echo "COMPACTION WARNING: Estimated token usage (${{ESTIMATED_TOKENS}}) exceeds threshold ({compaction_threshold}). Run /handoff compaction to preserve context before compaction occurs."
    fi
fi

# Anchor freshness check
ANCHOR_INTERVAL={anchor_interval}
ANCHOR_FILE="${{AGENT_CKPT_DIR}}/${{AGENT_NAME}}.context-anchor.md"
if [ -f "${{ANCHOR_FILE}}" ]; then
    ANCHOR_AGE=$(( $(date +%s) - $(stat -f %m "${{ANCHOR_FILE}}" 2>/dev/null || stat -c %Y "${{ANCHOR_FILE}}" 2>/dev/null || echo "0") ))
    ANCHOR_MAX=$(( ANCHOR_INTERVAL * 60 ))
    if [ "${{ANCHOR_AGE}}" -gt "${{ANCHOR_MAX}}" ]; then
        echo "ANCHOR REMINDER: Your context anchor is $((${{ANCHOR_AGE}} / 60)) min old (interval: {anchor_interval} min). Run /context-reload anchor to refresh."
    fi
fi
'''


def _bash_checkpoint_reminder_script(
    compaction_threshold: int = 100_000,
    anchor_interval: int = 15,
) -> str:
    """Hook for PostToolUse on Bash — activity logging, token tracking, stop signal."""
    return f'''\
#!/usr/bin/env bash
# Forge hook: PostToolUse (Bash)
# Logs activity, tracks tokens, checks stop signal, reminds about checkpoints.
set -euo pipefail

FORGE_DIR="${{CLAUDE_PROJECT_DIR:-.}}/.forge"
CHECKPOINTS_DIR="${{FORGE_DIR}}/checkpoints"
mkdir -p "${{CHECKPOINTS_DIR}}"

# Check for stop signal FIRST
if [ -f "${{FORGE_DIR}}/STOP_REQUESTED" ]; then
    echo "STOP SIGNAL DETECTED: forge stop has been requested. Save your checkpoint NOW with /checkpoint save, commit WIP, and stop all work."
    exit 0
fi

# Read tool input from stdin
INPUT=$(cat)

TOOL_NAME=$(echo "${{INPUT}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name','Bash'))" 2>/dev/null || echo "Bash")
SESSION_ID=$(echo "${{INPUT}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Resolve agent identity
IDENTITY=$(python3 "${{FORGE_DIR}}/scripts/resolve_identity.py" "${{FORGE_DIR}}" "${{SESSION_ID}}" 2>/dev/null || echo '{{"agent_type":"unknown","agent_name":"unknown"}}')
AGENT_TYPE=$(echo "${{IDENTITY}}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_type','unknown'))" 2>/dev/null || echo "unknown")
AGENT_NAME=$(echo "${{IDENTITY}}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_name','unknown'))" 2>/dev/null || echo "unknown")

# Ensure hierarchical checkpoint directory exists
AGENT_CKPT_DIR="${{CHECKPOINTS_DIR}}/${{AGENT_TYPE}}"
mkdir -p "${{AGENT_CKPT_DIR}}"

LOG_FILE="${{AGENT_CKPT_DIR}}/${{AGENT_NAME}}.activity.jsonl"

# Append activity entry
echo "{{\\"timestamp\\":\\"${{TIMESTAMP}}\\",\\"tool\\":\\"${{TOOL_NAME}}\\",\\"session_id\\":\\"${{SESSION_ID}}\\"}}" >> "${{LOG_FILE}}" 2>/dev/null || true

# Token tracking — cooperative compaction trigger
COMPACTION_THRESHOLD={compaction_threshold}
if [ -f "${{LOG_FILE}}" ]; then
    LOG_BYTES=$(wc -c < "${{LOG_FILE}}" 2>/dev/null || echo "0")
    ESTIMATED_TOKENS=$(( LOG_BYTES / 4 ))
    if [ "${{ESTIMATED_TOKENS}}" -gt "${{COMPACTION_THRESHOLD}}" ]; then
        EVENTS_DIR="${{FORGE_DIR}}/events"
        mkdir -p "${{EVENTS_DIR}}"
        EVENT_FILE="${{EVENTS_DIR}}/$(date +%s%N)-compaction-needed.json"
        TMP_EVENT="${{EVENT_FILE}}.tmp"
        echo "{{\\"type\\":\\"compaction_needed\\",\\"event\\":\\"compaction_needed\\",\\"agent_type\\":\\"${{AGENT_TYPE}}\\",\\"agent_name\\":\\"${{AGENT_NAME}}\\",\\"estimated_tokens\\":${{ESTIMATED_TOKENS}},\\"threshold\\":{compaction_threshold},\\"timestamp\\":\\"${{TIMESTAMP}}\\"}}" > "${{TMP_EVENT}}"
        mv "${{TMP_EVENT}}" "${{EVENT_FILE}}" 2>/dev/null || true
        echo "COMPACTION WARNING: Estimated token usage (${{ESTIMATED_TOKENS}}) exceeds threshold ({compaction_threshold}). Run /handoff compaction to preserve context before compaction occurs."
    fi
fi

# Check if checkpoint is very stale (>15 min)
if [ -d "${{CHECKPOINTS_DIR}}" ]; then
    FOUND_STALE=0
    while IFS= read -r -d \\'\\' CHECKPOINT_FILE; do
        [ -f "${{CHECKPOINT_FILE}}" ] || continue
        CHECKPOINT_AGE=$(( $(date +%s) - $(stat -f %m "${{CHECKPOINT_FILE}}" 2>/dev/null || stat -c %Y "${{CHECKPOINT_FILE}}" 2>/dev/null || echo "0") ))
        if [ "${{CHECKPOINT_AGE}}" -gt 900 ]; then
            AGENT=$(basename "${{CHECKPOINT_FILE}}" .json)
            echo "CHECKPOINT REMINDER: ${{AGENT}} checkpoint is $((${{CHECKPOINT_AGE}} / 60)) min old. Run /checkpoint save now."
            FOUND_STALE=1
            break
        fi
    done < <(find "${{CHECKPOINTS_DIR}}" -name "*.json" -not -name "*.tmp" -print0 2>/dev/null)

    if [ "${{FOUND_STALE}}" -eq 0 ]; then
        while IFS= read -r -d \\'\\' MARKER_FILE; do
            if [ -f "${{MARKER_FILE}}" ]; then
                AGENT=$(basename "${{MARKER_FILE}}" .compaction-marker)
                echo "COMPACTION MARKER: ${{AGENT}} has a pending compaction request. Run /handoff compaction or /context-reload reload."
                break
            fi
        done < <(find "${{CHECKPOINTS_DIR}}" -name "*.compaction-marker" -print0 2>/dev/null)
    fi
fi
'''


def _generic_activity_tracker_script(compaction_threshold: int = 100_000) -> str:
    """Lightweight activity tracker for Read|Glob|Grep|Agent tools.

    Appends to activity log and checks compaction threshold.
    """
    return f'''\
#!/usr/bin/env bash
# Forge hook: PostToolUse (Read|Glob|Grep|Agent)
# Lightweight activity logging + compaction token tracking.
set -euo pipefail

FORGE_DIR="${{CLAUDE_PROJECT_DIR:-.}}/.forge"
CHECKPOINTS_DIR="${{FORGE_DIR}}/checkpoints"
mkdir -p "${{CHECKPOINTS_DIR}}"

INPUT=$(cat)

TOOL_NAME=$(echo "${{INPUT}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name','unknown'))" 2>/dev/null || echo "unknown")
SESSION_ID=$(echo "${{INPUT}}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

IDENTITY=$(python3 "${{FORGE_DIR}}/scripts/resolve_identity.py" "${{FORGE_DIR}}" "${{SESSION_ID}}" 2>/dev/null || echo '{{"agent_type":"unknown","agent_name":"unknown"}}')
AGENT_TYPE=$(echo "${{IDENTITY}}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_type','unknown'))" 2>/dev/null || echo "unknown")
AGENT_NAME=$(echo "${{IDENTITY}}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_name','unknown'))" 2>/dev/null || echo "unknown")

AGENT_CKPT_DIR="${{CHECKPOINTS_DIR}}/${{AGENT_TYPE}}"
mkdir -p "${{AGENT_CKPT_DIR}}"

LOG_FILE="${{AGENT_CKPT_DIR}}/${{AGENT_NAME}}.activity.jsonl"

echo "{{\\"timestamp\\":\\"${{TIMESTAMP}}\\",\\"tool\\":\\"${{TOOL_NAME}}\\",\\"session_id\\":\\"${{SESSION_ID}}\\"}}" >> "${{LOG_FILE}}" 2>/dev/null || true

# Token tracking
COMPACTION_THRESHOLD={compaction_threshold}
if [ -f "${{LOG_FILE}}" ]; then
    LOG_BYTES=$(wc -c < "${{LOG_FILE}}" 2>/dev/null || echo "0")
    ESTIMATED_TOKENS=$(( LOG_BYTES / 4 ))
    if [ "${{ESTIMATED_TOKENS}}" -gt "${{COMPACTION_THRESHOLD}}" ]; then
        EVENTS_DIR="${{FORGE_DIR}}/events"
        mkdir -p "${{EVENTS_DIR}}"
        EVENT_FILE="${{EVENTS_DIR}}/$(date +%s%N)-compaction-needed.json"
        TMP_EVENT="${{EVENT_FILE}}.tmp"
        echo "{{\\"type\\":\\"compaction_needed\\",\\"event\\":\\"compaction_needed\\",\\"agent_type\\":\\"${{AGENT_TYPE}}\\",\\"agent_name\\":\\"${{AGENT_NAME}}\\",\\"estimated_tokens\\":${{ESTIMATED_TOKENS}},\\"threshold\\":{compaction_threshold},\\"timestamp\\":\\"${{TIMESTAMP}}\\"}}" > "${{TMP_EVENT}}"
        mv "${{TMP_EVENT}}" "${{EVENT_FILE}}" 2>/dev/null || true
        echo "COMPACTION WARNING: Estimated token usage (${{ESTIMATED_TOKENS}}) exceeds threshold ({compaction_threshold}). Run /handoff compaction to preserve context before compaction occurs."
    fi
fi
'''


def _pre_compact_checkpoint_script() -> str:
    """Hook for PreCompact — urgent checkpoint before context compression."""
    return '''\
#!/usr/bin/env bash
# Forge hook: PreCompact
# CRITICAL: Context is about to be compressed. Last chance to capture state.
set -euo pipefail

FORGE_DIR="${CLAUDE_PROJECT_DIR:-.}/.forge"
CHECKPOINTS_DIR="${FORGE_DIR}/checkpoints"
mkdir -p "${CHECKPOINTS_DIR}"

# Read input from stdin (may contain transcript_path)
INPUT=$(cat)

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_ID=$(echo "${INPUT}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")

# Resolve agent identity
IDENTITY=$(python3 "${FORGE_DIR}/scripts/resolve_identity.py" "${FORGE_DIR}" "${SESSION_ID}" 2>/dev/null || echo '{"agent_type":"unknown","agent_name":"unknown"}')
AGENT_TYPE=$(echo "${IDENTITY}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_type','unknown'))" 2>/dev/null || echo "unknown")
AGENT_NAME=$(echo "${IDENTITY}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_name','unknown'))" 2>/dev/null || echo "unknown")

# Write compaction marker
AGENT_CKPT_DIR="${CHECKPOINTS_DIR}/${AGENT_TYPE}"
mkdir -p "${AGENT_CKPT_DIR}"
echo "${TIMESTAMP}" > "${AGENT_CKPT_DIR}/${AGENT_NAME}.compaction-marker" 2>/dev/null || true

# Write compaction warning to activity logs (recursive)
while IFS= read -r -d '' LOG_FILE; do
    [ -f "${LOG_FILE}" ] || continue
    echo "{\"timestamp\":\"${TIMESTAMP}\",\"tool\":\"_COMPACTION_WARNING\",\"file\":\"\",\"session_id\":\"${SESSION_ID}\"}" >> "${LOG_FILE}" 2>/dev/null || true
done < <(find "${CHECKPOINTS_DIR}" -name "*.activity.jsonl" -print0 2>/dev/null)

echo "URGENT: Context compaction imminent. Run /context-reload reload after compaction to restore your context. Save your full checkpoint NOW with /checkpoint save. Include a detailed context_summary and handoff_notes — this is your last chance to preserve context before compression."
'''


def _subagent_lifecycle_script() -> str:
    """Hook for SubagentStart/SubagentStop — event-based tracking."""
    return '''\
#!/usr/bin/env bash
# Forge hook: SubagentStart / SubagentStop
# Event-based agent lifecycle tracking using atomic writes to .forge/events/.
set -euo pipefail

FORGE_DIR="${CLAUDE_PROJECT_DIR:-.}/.forge"
EVENTS_DIR="${FORGE_DIR}/events"
mkdir -p "${EVENTS_DIR}"

INPUT=$(cat)

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EVENT_TYPE="${CLAUDE_HOOK_EVENT_NAME:-unknown}"

# Extract agent info from input
AGENT_NAME=$(echo "${INPUT}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent_name', d.get('subagent_id','')))" 2>/dev/null || echo "")
SESSION_ID=$(echo "${INPUT}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")

# Map hook event to forge event type
if [ "${EVENT_TYPE}" = "SubagentStart" ]; then
    FORGE_EVENT="agent_started"
elif [ "${EVENT_TYPE}" = "SubagentStop" ]; then
    FORGE_EVENT="agent_stopped"
else
    FORGE_EVENT="${EVENT_TYPE}"
fi

# Atomic write: write to tmp file then rename
EVENT_FILE="${EVENTS_DIR}/$(date +%s%N)-${FORGE_EVENT}.json"
TMP_FILE="${EVENT_FILE}.tmp"

echo "{\"type\":\"${FORGE_EVENT}\",\"event\":\"${FORGE_EVENT}\",\"agent_name\":\"${AGENT_NAME}\",\"session_id\":\"${SESSION_ID}\",\"timestamp\":\"${TIMESTAMP}\"}" > "${TMP_FILE}"
mv "${TMP_FILE}" "${EVENT_FILE}" 2>/dev/null || true
'''


def _stop_checkpoint_script() -> str:
    """Standalone stop detection script (called by forge stop via tmux)."""
    return '''\
#!/usr/bin/env bash
# Forge: Stop signal detection
# Called by forge stop to verify all agents have checkpointed.
set -euo pipefail

FORGE_DIR="${CLAUDE_PROJECT_DIR:-.}/.forge"
CHECKPOINTS_DIR="${FORGE_DIR}/checkpoints"

if [ ! -d "${CHECKPOINTS_DIR}" ]; then
    echo "No checkpoints directory found."
    exit 1
fi

# Count agents by status — recursive search through subdirectories
TOTAL=0
STOPPED=0
while IFS= read -r -d '' CHECKPOINT_FILE; do
    [ -f "${CHECKPOINT_FILE}" ] || continue
    [[ "${CHECKPOINT_FILE}" == *.tmp ]] && continue
    TOTAL=$((TOTAL + 1))
    STATUS=$(python3 -c "import json; print(json.load(open('${CHECKPOINT_FILE}')).get('status',''))" 2>/dev/null || echo "")
    if [ "${STATUS}" = "stopped" ] || [ "${STATUS}" = "complete" ]; then
        STOPPED=$((STOPPED + 1))
    fi
done < <(find "${CHECKPOINTS_DIR}" -name "*.json" -not -name "*.tmp" -not -name "*.activity.jsonl" -print0 2>/dev/null)

echo "${STOPPED}/${TOTAL} agents stopped"

if [ "${STOPPED}" -eq "${TOTAL}" ] && [ "${TOTAL}" -gt 0 ]; then
    exit 0
else
    exit 1
fi
'''


def generate_hooks_config() -> dict:
    """Generate hooks configuration for settings.json.

    Returns the hooks dict to merge into `.claude/settings.json`.
    """
    # Relative paths from project root — Claude Code sets CWD to project dir
    prefix = ".forge/hooks"
    return {
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{prefix}/post-tool-checkpoint.sh",
                        "timeout": 30,
                    }
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{prefix}/bash-checkpoint-reminder.sh",
                        "timeout": 30,
                    }
                ],
            },
            {
                "matcher": "Read|Glob|Grep|Agent",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{prefix}/generic-activity-tracker.sh",
                        "timeout": 30,
                    }
                ],
            },
        ],
        "PreCompact": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{prefix}/pre-compact-checkpoint.sh",
                        "timeout": 60,
                    }
                ],
            },
        ],
        "SubagentStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{prefix}/subagent-lifecycle.sh",
                        "timeout": 30,
                    }
                ],
            },
        ],
        "SubagentStop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{prefix}/subagent-lifecycle.sh",
                        "timeout": 30,
                    }
                ],
            },
        ],
    }
