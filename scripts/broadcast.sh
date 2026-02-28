#!/usr/bin/env bash
# ==============================================================================
# Forge — Broadcast Script
# ==============================================================================
# Sends a message to ALL active agents via their inbox directories.
# Uses atomic mv for each write to prevent partial reads.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHARED_DIR="${FORGE_DIR}/shared"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Broadcast]${NC} $*"; }
log_error() { echo -e "${RED}[Broadcast]${NC} $*" >&2; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/broadcast.sh --type <type> --message <message> [--priority <level>]"
    echo ""
    echo "Sends a message to all active agents' inbox directories."
    echo ""
    echo "Options:"
    echo "  --type <type>         Message type (e.g., PREPARE_SHUTDOWN, SHUTDOWN, PAUSE, directive)"
    echo "  --message <message>   Message body"
    echo "  --priority <level>    Priority level: normal, high, critical (default: high)"
    echo "  --from <sender>       Sender name (default: system)"
    exit 0
fi

MSG_TYPE=""
MSG_BODY=""
PRIORITY="high"
SENDER="system"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --type)     MSG_TYPE="$2"; shift 2 ;;
        --message)  MSG_BODY="$2"; shift 2 ;;
        --priority) PRIORITY="$2"; shift 2 ;;
        --from)     SENDER="$2"; shift 2 ;;
        *)          log_error "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$MSG_TYPE" || -z "$MSG_BODY" ]]; then
    log_error "--type and --message are required"
    exit 1
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
UNIX_TS=$(date +%s)
QUEUE_DIR="${SHARED_DIR}/.queue"
SENT_COUNT=0

# Find all agent inboxes
for inbox in "${QUEUE_DIR}"/*/; do
    if [[ -d "$inbox" ]]; then
        agent_name=$(basename "$inbox" | sed 's/-inbox$//')
        TEMP_FILE=$(mktemp /tmp/forge-msg-XXXXXX.md)

        cat > "$TEMP_FILE" <<EOF
---
id: msg-${UNIX_TS}-${SENDER}
from: ${SENDER}
to: ${agent_name}
priority: ${PRIORITY}
timestamp: ${TIMESTAMP}
type: ${MSG_TYPE}
---

## ${MSG_TYPE}

${MSG_BODY}
EOF

        mv "$TEMP_FILE" "${inbox}msg-${UNIX_TS}-${SENDER}.md"
        SENT_COUNT=$((SENT_COUNT + 1))
    fi
done

log_info "Broadcast sent to ${SENT_COUNT} agent(s): ${MSG_TYPE}"
