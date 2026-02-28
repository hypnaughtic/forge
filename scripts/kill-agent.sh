#!/usr/bin/env bash
# ==============================================================================
# Forge — Kill Agent Script
# ==============================================================================
# Gracefully stops an agent: sends SHUTDOWN message, waits for acknowledgment,
# then kills the tmux window.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHARED_DIR="${FORGE_DIR}/shared"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Kill]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[Kill]${NC} $*"; }
log_error() { echo -e "${RED}[Kill]${NC} $*" >&2; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/kill-agent.sh --agent <name> [--session <tmux-session>] [--force]"
    echo ""
    echo "Gracefully stops an agent:"
    echo "  - Writes a SHUTDOWN message to its inbox"
    echo "  - Waits up to 30 seconds for acknowledgment"
    echo "  - Kills the tmux window"
    echo ""
    echo "Options:"
    echo "  --agent <name>      Agent name (e.g., backend-developer-1)"
    echo "  --session <name>    tmux session name (default: auto-detect)"
    echo "  --force             Skip graceful shutdown, kill immediately"
    exit 0
fi

AGENT_NAME=""
SESSION_NAME=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --agent)    AGENT_NAME="$2"; shift 2 ;;
        --session)  SESSION_NAME="$2"; shift 2 ;;
        --force)    FORCE=true; shift ;;
        *)          log_error "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$AGENT_NAME" ]]; then
    log_error "--agent is required"
    exit 1
fi

# Auto-detect tmux session
if [[ -z "$SESSION_NAME" ]]; then
    SESSION_NAME=$(tmux list-sessions 2>/dev/null | grep "^forge-" | head -1 | cut -d: -f1 || true)
    if [[ -z "$SESSION_NAME" ]]; then
        log_error "No Forge tmux session found."
        exit 1
    fi
fi

INBOX_DIR="${SHARED_DIR}/.queue/${AGENT_NAME}-inbox"
STATUS_FILE="${SHARED_DIR}/.status/${AGENT_NAME}.json"

if ! $FORCE; then
    # --- Send SHUTDOWN message ---
    log_info "Sending SHUTDOWN to ${AGENT_NAME}..."
    mkdir -p "$INBOX_DIR"

    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    UNIX_TS=$(date +%s)
    TEMP_FILE=$(mktemp "${TMPDIR:-/tmp}/forge-msg-XXXXXXXX")

    cat > "$TEMP_FILE" <<EOF
---
id: msg-${UNIX_TS}-system
from: system
to: ${AGENT_NAME}
priority: critical
timestamp: ${TIMESTAMP}
type: directive
---

## SHUTDOWN

You are being shut down. Execute the following immediately:
1. Stop all current work
2. Update your working memory with full resume context
3. Commit any safe-to-commit work: \`[${AGENT_NAME}] chore: WIP checkpoint before shutdown\`
4. Release all file locks
5. Update your status to "terminated"
6. Acknowledge this message
EOF

    mv "$TEMP_FILE" "${INBOX_DIR}/msg-${UNIX_TS}-system.md"

    # --- Wait for acknowledgment (up to 30 seconds) ---
    log_info "Waiting for ${AGENT_NAME} to acknowledge (up to 30s)..."
    for i in $(seq 1 30); do
        if [[ -f "$STATUS_FILE" ]]; then
            local_status=$(grep -o '"status": *"[^"]*"' "$STATUS_FILE" 2>/dev/null | head -1 | cut -d'"' -f4 || echo "")
            if [[ "$local_status" == "terminated" || "$local_status" == "suspended" ]]; then
                log_info "${AGENT_NAME} acknowledged shutdown."
                break
            fi
        fi
        sleep 1
    done
fi

# --- Kill tmux window ---
log_info "Killing tmux window for ${AGENT_NAME}..."
tmux kill-window -t "${SESSION_NAME}:${AGENT_NAME}" 2>/dev/null || true

# --- Update status ---
if [[ -f "$STATUS_FILE" ]]; then
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    # Simple JSON update using sed (portable across macOS and Linux)
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s/\"status\": *\"[^\"]*\"/\"status\": \"terminated\"/" "$STATUS_FILE" 2>/dev/null || true
        sed -i '' "s/\"last_updated\": *\"[^\"]*\"/\"last_updated\": \"${TIMESTAMP}\"/" "$STATUS_FILE" 2>/dev/null || true
    else
        sed -i "s/\"status\": *\"[^\"]*\"/\"status\": \"terminated\"/" "$STATUS_FILE" 2>/dev/null || true
        sed -i "s/\"last_updated\": *\"[^\"]*\"/\"last_updated\": \"${TIMESTAMP}\"/" "$STATUS_FILE" 2>/dev/null || true
    fi
fi

log_info "${AGENT_NAME} terminated."
