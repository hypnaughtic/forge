#!/usr/bin/env bash
# ==============================================================================
# Forge — Resume Script
# ==============================================================================
# Restores a Forge session from a snapshot file. Spawns Team Leader with
# --resume flag, which then restores the full agent fleet.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="${FORGE_DIR}/scripts"
SHARED_DIR="${FORGE_DIR}/shared"
CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"
SNAPSHOTS_DIR="${SHARED_DIR}/.snapshots"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Forge]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[Forge]${NC} $*"; }
log_error() { echo -e "${RED}[Forge]${NC} $*" >&2; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/resume.sh [--snapshot <path>]"
    echo ""
    echo "Restores a Forge session from a snapshot."
    echo ""
    echo "Options:"
    echo "  --snapshot <path>   Path to snapshot file (default: most recent)"
    echo ""
    echo "Sequence:"
    echo "  1. Load and validate snapshot"
    echo "  2. Start tmux session and daemons"
    echo "  3. Spawn Team Leader with --resume"
    echo "  4. Team Leader restores the agent fleet"
    exit 0
fi

SNAPSHOT_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --snapshot) SNAPSHOT_PATH="$2"; shift 2 ;;
        *)          shift ;;
    esac
done

# --- Find snapshot ---
if [[ -z "$SNAPSHOT_PATH" ]]; then
    SNAPSHOT_PATH=$(ls -t "${SNAPSHOTS_DIR}"/snapshot-*.json 2>/dev/null | head -1 || true)
    if [[ -z "$SNAPSHOT_PATH" ]]; then
        log_error "No snapshot files found in ${SNAPSHOTS_DIR}/"
        log_error "Run './forge start' for a fresh session."
        exit 1
    fi
fi

if [[ ! -f "$SNAPSHOT_PATH" ]]; then
    log_error "Snapshot file not found: ${SNAPSHOT_PATH}"
    exit 1
fi

log_info "Loading snapshot: $(basename "$SNAPSHOT_PATH")"

# --- Validate prerequisites ---
for cmd in tmux claude; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Required tool not found: $cmd. Run './forge setup' first."
        exit 1
    fi
done

# --- Parse snapshot ---
if command -v jq &>/dev/null; then
    SNAP_TIMESTAMP=$(jq -r '.timestamp // "unknown"' "$SNAPSHOT_PATH")
    SNAP_MODE=$(jq -r '.project.mode // "mvp"' "$SNAPSHOT_PATH")
    SNAP_STRATEGY=$(jq -r '.project.strategy // "co-pilot"' "$SNAPSHOT_PATH")
    SNAP_PROJECT_DIR=$(jq -r '.project.project_dir // "."' "$SNAPSHOT_PATH")
    SNAP_ITERATION=$(jq -r '.iteration.current // 0' "$SNAPSHOT_PATH")
    SNAP_PHASE=$(jq -r '.iteration.phase // "UNKNOWN"' "$SNAPSHOT_PATH")
    SNAP_COST=$(jq -r '.costs.total_development_cost_usd // 0' "$SNAPSHOT_PATH")
    SNAP_COST_CAP=$(jq -r '.costs.cost_cap_usd // "no-cap"' "$SNAPSHOT_PATH")
    AGENT_COUNT=$(jq -r '.agents | length' "$SNAPSHOT_PATH")
else
    log_error "jq is required for resume. Install: brew install jq (macOS) | apt install jq (Ubuntu)"
    exit 1
fi

PROJECT_DIR="${SNAP_PROJECT_DIR}"
if [[ ! -d "$PROJECT_DIR" ]]; then
    log_warn "Project directory from snapshot not found: ${PROJECT_DIR}"
    log_info "Using current directory instead."
    PROJECT_DIR=$(pwd)
fi

log_info "Snapshot from: ${SNAP_TIMESTAMP}"
log_info "  Mode: ${SNAP_MODE} | Strategy: ${SNAP_STRATEGY}"
log_info "  Iteration: ${SNAP_ITERATION} (phase: ${SNAP_PHASE})"
log_info "  Agents: ${AGENT_COUNT} | Cost: \$${SNAP_COST} / \$${SNAP_COST_CAP}"

# --- Check for config changes since snapshot ---
if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    CURRENT_MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE" 2>/dev/null)
    CURRENT_STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE" 2>/dev/null)

    if [[ "$CURRENT_MODE" != "$SNAP_MODE" ]]; then
        log_warn "Mode changed since snapshot: ${SNAP_MODE} → ${CURRENT_MODE}"
    fi
    if [[ "$CURRENT_STRATEGY" != "$SNAP_STRATEGY" ]]; then
        log_warn "Strategy changed since snapshot: ${SNAP_STRATEGY} → ${CURRENT_STRATEGY}"
    fi
fi

# --- Check for external code changes ---
LAST_TAG=$(jq -r '.git.last_tag // "none"' "$SNAPSHOT_PATH")
if [[ "$LAST_TAG" != "none" ]]; then
    external_commits=$(git -C "$PROJECT_DIR" log --oneline "${LAST_TAG}..HEAD" 2>/dev/null | wc -l || echo "0")
    if [[ $external_commits -gt 0 ]]; then
        log_warn "Found ${external_commits} commits since last session. Team Leader will be notified."
    fi
fi

# --- Validate shared/ state ---
if [[ ! -d "${SHARED_DIR}/.memory" ]]; then
    log_warn "shared/.memory not found. Creating directory structure..."
    mkdir -p "${SHARED_DIR}/.queue" "${SHARED_DIR}/.status" "${SHARED_DIR}/.memory" \
             "${SHARED_DIR}/.decisions" "${SHARED_DIR}/.iterations" "${SHARED_DIR}/.artifacts" \
             "${SHARED_DIR}/.locks" "${SHARED_DIR}/.logs" "${SHARED_DIR}/.snapshots" \
             "${SHARED_DIR}/.secrets" "${SHARED_DIR}/.human"
fi

# --- Kill existing session if any ---
SESSION_NAME="forge-$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    log_warn "Existing tmux session found. Killing it..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
fi

# --- Create tmux session ---
log_info "Creating tmux session: ${SESSION_NAME}"
tmux new-session -d -s "$SESSION_NAME" -n "forge-main" "bash"

# --- Start watchdog daemon ---
log_info "Starting watchdog daemon..."
tmux new-window -t "$SESSION_NAME" -n "watchdog" \
    "bash '${SCRIPTS_DIR}/watchdog.sh' --forge-dir '${FORGE_DIR}' --session '${SESSION_NAME}'; bash"

# --- Start log aggregator ---
log_info "Starting log aggregator..."
tmux new-window -t "$SESSION_NAME" -n "log-aggregator" \
    "bash '${SCRIPTS_DIR}/log-aggregator.sh' --forge-dir '${FORGE_DIR}'; bash"

# --- Write resume context for Team Leader ---
RESUME_CONTEXT="${SHARED_DIR}/.memory/resume-context.md"
cat > "$RESUME_CONTEXT" <<EOF
# Resume Context

## Snapshot Info
- **Snapshot**: $(basename "$SNAPSHOT_PATH")
- **Timestamp**: ${SNAP_TIMESTAMP}
- **Mode**: ${SNAP_MODE}
- **Strategy**: ${SNAP_STRATEGY}
- **Iteration**: ${SNAP_ITERATION} (phase: ${SNAP_PHASE})

## Agents to Restore
$(jq -r '.agents[] | "- \(.name) (\(.type)) — Status: \(.status) — Task: \(.current_task)"' "$SNAPSHOT_PATH" 2>/dev/null || echo "- See snapshot file for agent list")

## Cost State
- Total: \$${SNAP_COST} / \$${SNAP_COST_CAP}

## Instructions
1. Read your working memory at shared/.memory/team-leader-memory.md
2. Restore each agent listed above using scripts/spawn-agent.sh --resume
3. Send SESSION_RESUMED to all restored agents
4. Verify all agents are operational (check status updates within 2 minutes)
5. Greet the human with a status summary
6. Continue from where the fleet left off
EOF

# --- Spawn Team Leader with --resume ---
log_info "Spawning Team Leader with --resume..."

# Read current mode/strategy from config (may have changed)
RESUME_MODE="${SNAP_MODE}"
RESUME_STRATEGY="${SNAP_STRATEGY}"
if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    RESUME_MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE" 2>/dev/null || echo "$SNAP_MODE")
    RESUME_STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE" 2>/dev/null || echo "$SNAP_STRATEGY")
fi

bash "${SCRIPTS_DIR}/spawn-agent.sh" \
    --agent-type "team-leader" \
    --instance-id "1" \
    --project-dir "$PROJECT_DIR" \
    --session "$SESSION_NAME" \
    --forge-dir "$FORGE_DIR" \
    --mode "$RESUME_MODE" \
    --strategy "$RESUME_STRATEGY" \
    --resume

# --- Summary ---
echo ""
log_info "═══════════════════════════════════════════════"
log_info "Session resumed from: $(basename "$SNAPSHOT_PATH")"
log_info "Mode: ${RESUME_MODE} | Strategy: ${RESUME_STRATEGY}"
log_info "Iteration: ${SNAP_ITERATION} (phase: ${SNAP_PHASE})"
log_info ""
log_info "The Team Leader is restoring the agent fleet."
log_info "  Attach: ./forge attach"
log_info "  Status: ./forge status"
log_info "  Stop:   ./forge stop"
log_info "═══════════════════════════════════════════════"
