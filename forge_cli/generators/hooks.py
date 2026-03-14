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


def generate_hook_scripts(config: ForgeConfig, forge_dir: Path) -> list[Path]:
    """Generate all hook scripts to `.forge/hooks/`.

    Args:
        config: Forge configuration.
        forge_dir: The `.forge/` directory.

    Returns:
        List of paths to generated hook scripts.
    """
    hooks_dir = forge_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    scripts: list[Path] = []

    # Post-tool checkpoint (Write|Edit)
    path = hooks_dir / "post-tool-checkpoint.sh"
    path.write_text(_post_tool_checkpoint_script())
    _make_executable(path)
    scripts.append(path)

    # Bash checkpoint reminder
    path = hooks_dir / "bash-checkpoint-reminder.sh"
    path.write_text(_bash_checkpoint_reminder_script())
    _make_executable(path)
    scripts.append(path)

    # Pre-compact checkpoint
    path = hooks_dir / "pre-compact-checkpoint.sh"
    path.write_text(_pre_compact_checkpoint_script())
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


def _post_tool_checkpoint_script() -> str:
    """Hook for PostToolUse on Write|Edit — logs activity and reminds about checkpoints."""
    return '''\
#!/usr/bin/env bash
# Forge hook: PostToolUse (Write|Edit)
# Appends to activity log and reminds agent to checkpoint if stale.
set -euo pipefail

FORGE_DIR="$(pwd)/.forge"
CHECKPOINTS_DIR="${FORGE_DIR}/checkpoints"
mkdir -p "${CHECKPOINTS_DIR}"

# Read tool input from stdin
INPUT=$(cat)

TOOL_NAME=$(echo "${INPUT}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "${INPUT}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "${INPUT}" | python3 -c "import sys,json; d=json.load(sys.stdin); i=d.get('tool_input',{}); print(i.get('file_path', i.get('path','')))" 2>/dev/null || echo "")

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Append to activity log (best-effort detection of agent type from session)
# Default to "unknown" — the rich checkpoint skill will set proper agent type
AGENT_TYPE="unknown"
if [ -f "${FORGE_DIR}/session.json" ] && [ -n "${SESSION_ID}" ]; then
    AGENT_TYPE=$(python3 -c "
import json,sys
try:
    s=json.load(open('${FORGE_DIR}/session.json'))
    for at,meta in s.get('agent_tree',{}).items():
        if meta.get('session_id','') == '${SESSION_ID}':
            print(at); sys.exit(0)
    print('unknown')
except: print('unknown')
" 2>/dev/null || echo "unknown")
fi

LOG_FILE="${CHECKPOINTS_DIR}/${AGENT_TYPE}.activity.jsonl"

# Append activity entry (use flock for concurrency safety)
(
    flock -n 200 || exit 0
    echo "{\"timestamp\":\"${TIMESTAMP}\",\"tool\":\"${TOOL_NAME}\",\"file\":\"${FILE_PATH}\",\"session_id\":\"${SESSION_ID}\"}" >> "${LOG_FILE}"
) 200>"${LOG_FILE}.lock" 2>/dev/null || true

# Check if rich checkpoint is stale (>10 min old)
CHECKPOINT_FILE="${CHECKPOINTS_DIR}/${AGENT_TYPE}.json"
if [ -f "${CHECKPOINT_FILE}" ]; then
    CHECKPOINT_AGE=$(( $(date +%s) - $(stat -f %m "${CHECKPOINT_FILE}" 2>/dev/null || stat -c %Y "${CHECKPOINT_FILE}" 2>/dev/null || echo "0") ))
    if [ "${CHECKPOINT_AGE}" -gt 600 ]; then
        echo "CHECKPOINT REMINDER: Your last checkpoint is $((CHECKPOINT_AGE / 60)) min old. Run /checkpoint save now."
    fi
fi
'''


def _bash_checkpoint_reminder_script() -> str:
    """Hook for PostToolUse on Bash — longer threshold, stop signal detection."""
    return '''\
#!/usr/bin/env bash
# Forge hook: PostToolUse (Bash)
# Checks for stop signal and reminds about stale checkpoints.
set -euo pipefail

FORGE_DIR="$(pwd)/.forge"
CHECKPOINTS_DIR="${FORGE_DIR}/checkpoints"

# Check for stop signal FIRST
if [ -f "${FORGE_DIR}/STOP_REQUESTED" ]; then
    echo "STOP SIGNAL DETECTED: forge stop has been requested. Save your checkpoint NOW with /checkpoint save, commit WIP, and stop all work."
    exit 0
fi

# Read stdin (required even if not used)
cat > /dev/null

# Check if checkpoint is very stale (>15 min)
# Use a broader search since we may not know agent type
if [ -d "${CHECKPOINTS_DIR}" ]; then
    for CHECKPOINT_FILE in "${CHECKPOINTS_DIR}"/*.json; do
        [ -f "${CHECKPOINT_FILE}" ] || continue
        CHECKPOINT_AGE=$(( $(date +%s) - $(stat -f %m "${CHECKPOINT_FILE}" 2>/dev/null || stat -c %Y "${CHECKPOINT_FILE}" 2>/dev/null || echo "0") ))
        if [ "${CHECKPOINT_AGE}" -gt 900 ]; then
            AGENT=$(basename "${CHECKPOINT_FILE}" .json)
            echo "CHECKPOINT REMINDER: ${AGENT} checkpoint is $((CHECKPOINT_AGE / 60)) min old. Run /checkpoint save now."
            break
        fi
    done
fi
'''


def _pre_compact_checkpoint_script() -> str:
    """Hook for PreCompact — urgent checkpoint before context compression."""
    return '''\
#!/usr/bin/env bash
# Forge hook: PreCompact
# CRITICAL: Context is about to be compressed. Last chance to capture state.
set -euo pipefail

FORGE_DIR="$(pwd)/.forge"
CHECKPOINTS_DIR="${FORGE_DIR}/checkpoints"
mkdir -p "${CHECKPOINTS_DIR}"

# Read input from stdin (may contain transcript_path)
INPUT=$(cat)

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Write a compaction marker to activity logs
for LOG_FILE in "${CHECKPOINTS_DIR}"/*.activity.jsonl; do
    [ -f "${LOG_FILE}" ] || continue
    echo "{\"timestamp\":\"${TIMESTAMP}\",\"tool\":\"_COMPACTION_WARNING\",\"file\":\"\",\"session_id\":\"\"}" >> "${LOG_FILE}" 2>/dev/null || true
done

echo "URGENT: Context compaction imminent. Save your full checkpoint NOW with /checkpoint save. Include a detailed context_summary and handoff_notes — this is your last chance to preserve context before compression."
'''


def _subagent_lifecycle_script() -> str:
    """Hook for SubagentStart/SubagentStop — tracks hierarchy."""
    return '''\
#!/usr/bin/env bash
# Forge hook: SubagentStart / SubagentStop
# Records agent spawn/completion events for hierarchy reconstruction.
set -euo pipefail

FORGE_DIR="$(pwd)/.forge"
CHECKPOINTS_DIR="${FORGE_DIR}/checkpoints"
mkdir -p "${CHECKPOINTS_DIR}"

INPUT=$(cat)

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EVENT_TYPE="${CLAUDE_HOOK_EVENT_NAME:-unknown}"

# Extract agent info from input
AGENT_NAME=$(echo "${INPUT}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agent_name', d.get('subagent_id','')))" 2>/dev/null || echo "")

HIERARCHY_LOG="${CHECKPOINTS_DIR}/hierarchy.jsonl"

(
    flock -n 200 || exit 0
    echo "{\"timestamp\":\"${TIMESTAMP}\",\"event\":\"${EVENT_TYPE}\",\"agent\":\"${AGENT_NAME}\"}" >> "${HIERARCHY_LOG}"
) 200>"${HIERARCHY_LOG}.lock" 2>/dev/null || true
'''


def _stop_checkpoint_script() -> str:
    """Standalone stop detection script (called by forge stop via tmux)."""
    return '''\
#!/usr/bin/env bash
# Forge: Stop signal detection
# Called by forge stop to verify all agents have checkpointed.
set -euo pipefail

FORGE_DIR="$(pwd)/.forge"
CHECKPOINTS_DIR="${FORGE_DIR}/checkpoints"

if [ ! -d "${CHECKPOINTS_DIR}" ]; then
    echo "No checkpoints directory found."
    exit 1
fi

# Count agents by status
TOTAL=0
STOPPED=0
for CHECKPOINT_FILE in "${CHECKPOINTS_DIR}"/*.json; do
    [ -f "${CHECKPOINT_FILE}" ] || continue
    [[ "${CHECKPOINT_FILE}" == *.tmp ]] && continue
    TOTAL=$((TOTAL + 1))
    STATUS=$(python3 -c "import json; print(json.load(open('${CHECKPOINT_FILE}')).get('status',''))" 2>/dev/null || echo "")
    if [ "${STATUS}" = "stopped" ] || [ "${STATUS}" = "complete" ]; then
        STOPPED=$((STOPPED + 1))
    fi
done

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
    return {
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".forge/hooks/post-tool-checkpoint.sh",
                        "timeout": 5,
                    }
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".forge/hooks/bash-checkpoint-reminder.sh",
                        "timeout": 5,
                    }
                ],
            },
        ],
        "PreCompact": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": ".forge/hooks/pre-compact-checkpoint.sh",
                        "timeout": 10,
                    }
                ],
            },
        ],
        "SubagentStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": ".forge/hooks/subagent-lifecycle.sh",
                        "timeout": 5,
                    }
                ],
            },
        ],
        "SubagentStop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": ".forge/hooks/subagent-lifecycle.sh",
                        "timeout": 5,
                    }
                ],
            },
        ],
    }
