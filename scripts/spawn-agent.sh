#!/usr/bin/env bash
# ==============================================================================
# Forge — Spawn Agent Script
# ==============================================================================
# Spawns a named agent in a new tmux window with the correct Claude Code
# invocation, context loading, and session configuration.
set -euo pipefail

FORGE_DIR=""
SESSION_NAME=""
AGENT_TYPE=""
INSTANCE_ID="1"
PROJECT_DIR=""
RESUME=false
MODE="mvp"
STRATEGY="co-pilot"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Spawn]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[Spawn]${NC} $*"; }
log_error() { echo -e "${RED}[Spawn]${NC} $*" >&2; }

usage() {
    echo "Usage: scripts/spawn-agent.sh [options]"
    echo ""
    echo "Options:"
    echo "  --agent-type <type>     Agent type (e.g., team-leader, backend-developer)"
    echo "  --instance-id <id>      Instance ID for multiple instances (default: 1)"
    echo "  --project-dir <path>    Project directory"
    echo "  --session <name>        tmux session name"
    echo "  --forge-dir <path>      Forge installation directory"
    echo "  --mode <mode>           Project mode (mvp|production-ready|no-compromise)"
    echo "  --strategy <strategy>   Execution strategy (auto-pilot|co-pilot|micro-manage)"
    echo "  --resume                Resume from working memory"
    echo "  --help                  Show this help"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --agent-type)     AGENT_TYPE="$2"; shift 2 ;;
        --instance-id)    INSTANCE_ID="$2"; shift 2 ;;
        --project-dir)    PROJECT_DIR="$2"; shift 2 ;;
        --session)        SESSION_NAME="$2"; shift 2 ;;
        --forge-dir)      FORGE_DIR="$2"; shift 2 ;;
        --mode)           MODE="$2"; shift 2 ;;
        --strategy)       STRATEGY="$2"; shift 2 ;;
        --resume)         RESUME=true; shift ;;
        --help|-h)        usage ;;
        *)                log_error "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate required params
if [[ -z "$AGENT_TYPE" ]]; then
    log_error "--agent-type is required"
    exit 1
fi

# Set defaults
FORGE_DIR="${FORGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
SESSION_NAME="${SESSION_NAME:-forge-project}"

SHARED_DIR="${FORGE_DIR}/shared"
AGENT_NAME="${AGENT_TYPE}-${INSTANCE_ID}"

# Simplify agent name if instance is 1 and it's a unique agent type
if [[ "$INSTANCE_ID" == "1" ]]; then
    AGENT_NAME="${AGENT_TYPE}"
fi

# --- Resolve agent MD file ---
BASE_PROTOCOL="${FORGE_DIR}/agents/_base-agent.md"
GENERATED_AGENT_MD="${PROJECT_DIR}/.forge/agents/${AGENT_TYPE}.md"
TEMPLATE_AGENT_MD="${FORGE_DIR}/agents/${AGENT_TYPE}.md"

AGENT_MD="${GENERATED_AGENT_MD}"
if [[ ! -f "$AGENT_MD" ]]; then
    AGENT_MD="${TEMPLATE_AGENT_MD}"
fi

if [[ ! -f "$AGENT_MD" ]]; then
    log_error "Agent definition file not found: ${AGENT_TYPE}.md"
    log_error "Checked: ${GENERATED_AGENT_MD}"
    log_error "Checked: ${TEMPLATE_AGENT_MD}"
    exit 1
fi

if [[ ! -f "$BASE_PROTOCOL" ]]; then
    log_error "Base protocol not found: ${BASE_PROTOCOL}"
    exit 1
fi

# --- Create agent inbox ---
INBOX_DIR="${SHARED_DIR}/.queue/${AGENT_NAME}-inbox"
mkdir -p "$INBOX_DIR"

# --- Create agent working memory file if not exists ---
MEMORY_FILE="${SHARED_DIR}/.memory/${AGENT_NAME}-memory.md"

# --- Build initial prompt ---
log_info "Building context for ${AGENT_NAME}..."

INSTRUCTION_FILE=$(mktemp "${TMPDIR:-/tmp}/forge-init-XXXXXXXX")

{
    echo "You are ${AGENT_NAME}. You are part of a Forge AI development team."
    echo "Project mode: ${MODE} | Strategy: ${STRATEGY}"
    echo "Project directory: ${PROJECT_DIR}"
    echo "Forge directory: ${FORGE_DIR}"
    echo ""
    echo "Read and follow these instruction files carefully."
    echo ""
    echo "========================================="
    echo "YOUR AGENT INSTRUCTIONS"
    echo "========================================="
    cat "$AGENT_MD"
    echo ""
    echo "========================================="
    echo "BASE PROTOCOL (all agents follow this)"
    echo "========================================="
    cat "$BASE_PROTOCOL"
} > "$INSTRUCTION_FILE"

# Add project CLAUDE.md if it exists
PROJECT_CLAUDE_MD="${PROJECT_DIR}/CLAUDE.md"
if [[ -f "$PROJECT_CLAUDE_MD" ]]; then
    {
        echo ""
        echo "========================================="
        echo "PROJECT CLAUDE.md (respect these conventions)"
        echo "========================================="
        cat "$PROJECT_CLAUDE_MD"
    } >> "$INSTRUCTION_FILE"
fi

# Add working memory for session recovery
if $RESUME && [[ -f "$MEMORY_FILE" ]]; then
    {
        echo ""
        echo "========================================="
        echo "YOUR PREVIOUS SESSION STATE (resume from here)"
        echo "========================================="
        cat "$MEMORY_FILE"
    } >> "$INSTRUCTION_FILE"
fi

# Add pending inbox messages
if [[ -d "$INBOX_DIR" ]] && [[ "$(ls -A "$INBOX_DIR" 2>/dev/null)" ]]; then
    {
        echo ""
        echo "========================================="
        echo "PENDING MESSAGES IN YOUR INBOX"
        echo "========================================="
        for msg in $(ls "$INBOX_DIR" | sort); do
            echo "--- MESSAGE: $msg ---"
            cat "$INBOX_DIR/$msg"
            echo ""
        done
    } >> "$INSTRUCTION_FILE"
fi

# --- Initialize status file ---
STATUS_FILE="${SHARED_DIR}/.status/${AGENT_NAME}.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$STATUS_FILE" <<EOF
{
  "agent": "${AGENT_NAME}",
  "status": "idle",
  "current_task": "Initializing",
  "blockers": [],
  "iteration": 0,
  "last_updated": "${TIMESTAMP}",
  "session_start": "${TIMESTAMP}",
  "artifacts_produced": [],
  "estimated_completion": "",
  "messages_processed": 0,
  "usage_limits": {
    "warnings_detected": 0,
    "last_warning_at": null,
    "status": "normal"
  },
  "cost_estimate_usd": 0.0
}
EOF

# --- Build permission flags based on strategy ---
# Claude Code permission modes:
#   --dangerously-skip-permissions    Bypass ALL checks (shows one-time warning)
#   --permission-mode bypassPermissions  Same via mode flag
#   --permission-mode acceptEdits     Auto-approve edits, prompt for shell ops
#   --permission-mode default         Normal interactive permissions
CLAUDE_PERM_FLAGS=""
case "$STRATEGY" in
    auto-pilot)
        # Full autonomy: bypass all permission checks.
        # Uses --dangerously-skip-permissions for complete non-interactive operation.
        CLAUDE_PERM_FLAGS="--dangerously-skip-permissions"
        ;;
    co-pilot)
        # Balanced: auto-approve file edits and reads, prompt only for
        # potentially destructive shell operations.
        CLAUDE_PERM_FLAGS="--permission-mode acceptEdits"
        ;;
    micro-manage)
        # Every significant decision requires approval (default Claude behavior)
        CLAUDE_PERM_FLAGS=""
        ;;
esac

# --- Launch in tmux ---
log_info "Launching ${AGENT_NAME} in tmux window..."

# Unset CLAUDECODE to prevent "nested session" errors when forge is invoked
# from within a Claude Code session (e.g., during development/testing).
UNSET_CLAUDE_ENV="unset CLAUDECODE; unset CLAUDE_CODE_ENTRY_TOOL;"

if [[ "${AGENT_TYPE}" == "team-leader" && "$STRATEGY" != "auto-pilot" ]]; then
    # Interactive mode: Team Leader runs in interactive Claude Code session
    # Human can type directly to the Team Leader
    tmux new-window -t "$SESSION_NAME" -n "$AGENT_NAME" \
        "${UNSET_CLAUDE_ENV} cd '${PROJECT_DIR}' && cat '${INSTRUCTION_FILE}' | claude ${CLAUDE_PERM_FLAGS} || echo 'Claude Code session ended. Press Enter to exit.' && read"
else
    # Headless mode: agent works autonomously (also Team Leader in auto-pilot)
    # In auto-pilot, --print bypasses the interactive bypass-permissions prompt.
    tmux new-window -t "$SESSION_NAME" -n "$AGENT_NAME" \
        "${UNSET_CLAUDE_ENV} cd '${PROJECT_DIR}' && cat '${INSTRUCTION_FILE}' | claude --print --output-format text ${CLAUDE_PERM_FLAGS} > '${SHARED_DIR}/.logs/${AGENT_NAME}-session.log' 2>&1; echo 'Agent session ended.' >> '${SHARED_DIR}/.logs/${AGENT_NAME}-session.log'"
fi

log_info "${AGENT_NAME} spawned successfully in tmux session '${SESSION_NAME}'"

# Cleanup temp file after a delay (let tmux read it first)
(sleep 10 && rm -f "$INSTRUCTION_FILE") &
