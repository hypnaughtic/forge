#!/usr/bin/env bash
# ==============================================================================
# Forge — Stop Script
# ==============================================================================
# Gracefully shuts down the entire agent fleet and captures a state snapshot
# for later resumption.
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

PAUSE_MODE=false
SNAPSHOT_ONLY=false

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/stop.sh [--pause] [--snapshot-only]"
    echo ""
    echo "Graceful fleet shutdown with state snapshot."
    echo ""
    echo "Options:"
    echo "  --pause          Stop agents but keep tmux session alive for inspection"
    echo "  --snapshot-only  Capture snapshot without broadcasting shutdown or killing tmux"
    echo "                   (used by /forge-stop in interactive mode)"
    echo ""
    echo "Sequence:"
    echo "  1. PREPARE_SHUTDOWN broadcast (grace period for agents to save state)"
    echo "  2. Capture fleet state snapshot"
    echo "  3. SHUTDOWN broadcast (skipped with --snapshot-only)"
    echo "  4. Force-kill remaining agents (skipped with --snapshot-only)"
    echo "  5. Cleanup daemons and tmux session (skipped with --snapshot-only)"
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pause)         PAUSE_MODE=true; shift ;;
        --snapshot-only) SNAPSHOT_ONLY=true; shift ;;
        *)               shift ;;
    esac
done

# Find active tmux session
SESSION_NAME=$(tmux list-sessions 2>/dev/null | grep "^forge-" | head -1 | cut -d: -f1 || true)
if [[ -z "$SESSION_NAME" ]]; then
    log_warn "No active Forge tmux session found."
fi

# Read grace period from config
GRACE_PERIOD=60
if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    GRACE_PERIOD=$(yq eval '.session.shutdown_grace_period_seconds // 60' "$CONFIG_FILE" 2>/dev/null || echo 60)
fi

SNAPSHOT_RETENTION=5
if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    SNAPSHOT_RETENTION=$(yq eval '.session.snapshot_retention // 5' "$CONFIG_FILE" 2>/dev/null || echo 5)
fi

# ==============================================================================
# Step 1: PREPARE_SHUTDOWN Broadcast (skipped in snapshot-only mode)
# ==============================================================================
if ! $SNAPSHOT_ONLY; then
    log_info "Step 1: Broadcasting PREPARE_SHUTDOWN (${GRACE_PERIOD}s grace period)..."

    if [[ -f "${SCRIPTS_DIR}/broadcast.sh" ]]; then
        bash "${SCRIPTS_DIR}/broadcast.sh" \
            --type "PREPARE_SHUTDOWN" \
            --message "Finalize working memory, commit in-progress work, release file locks, and update status to 'suspended'. You have ${GRACE_PERIOD} seconds." \
            --priority "critical" \
            --from "system" 2>/dev/null || true
    fi

    log_info "Waiting ${GRACE_PERIOD}s for agents to finalize..."
    sleep "$GRACE_PERIOD"
else
    log_info "Step 1: Skipped (snapshot-only mode)"
fi

# ==============================================================================
# Step 2: Capture Fleet State Snapshot
# ==============================================================================
log_info "Step 2: Capturing fleet state snapshot..."

mkdir -p "$SNAPSHOTS_DIR"
UNIX_TS=$(date +%s)
SNAPSHOT_FILE="${SNAPSHOTS_DIR}/snapshot-${UNIX_TS}.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Collect agent states
AGENTS_JSON="["
AGENT_COUNT=0

if [[ -d "${SHARED_DIR}/.status" ]]; then
    for status_file in "${SHARED_DIR}/.status"/*.json; do
        [[ -f "$status_file" ]] || continue
        agent_name=$(basename "$status_file" .json)

        # Skip system processes
        [[ "$agent_name" == "watchdog" || "$agent_name" == "log-aggregator" ]] && continue

        if command -v jq &>/dev/null; then
            status=$(jq -r '.status // "unknown"' "$status_file" 2>/dev/null)
            task=$(jq -r '.current_task // ""' "$status_file" 2>/dev/null)
            last_updated=$(jq -r '.last_updated // ""' "$status_file" 2>/dev/null)
            cost=$(jq -r '.cost_estimate_usd // 0' "$status_file" 2>/dev/null)
        else
            status="unknown"
            task=""
            last_updated=""
            cost=0
        fi

        agent_type=$(echo "$agent_name" | sed 's/-[0-9]*$//')
        instance_id=$(echo "$agent_name" | grep -o '[0-9]*$' || echo "1")

        # Check unprocessed messages
        inbox="${SHARED_DIR}/.queue/${agent_name}-inbox"
        unprocessed=0
        if [[ -d "$inbox" ]]; then
            unprocessed=$(ls -1 "$inbox" 2>/dev/null | wc -l || echo 0)
        fi

        # Check file locks
        locks_json="[]"

        [[ $AGENT_COUNT -gt 0 ]] && AGENTS_JSON="${AGENTS_JSON},"
        AGENTS_JSON="${AGENTS_JSON}
    {
      \"name\": \"${agent_name}\",
      \"type\": \"${agent_type}\",
      \"instance_id\": \"${instance_id}\",
      \"status\": \"${status}\",
      \"current_task\": \"${task}\",
      \"memory_file\": \"shared/.memory/${agent_name}-memory.md\",
      \"last_updated\": \"${last_updated}\",
      \"unprocessed_messages\": ${unprocessed},
      \"file_locks_held\": ${locks_json}
    }"
        AGENT_COUNT=$((AGENT_COUNT + 1))
    done
fi
AGENTS_JSON="${AGENTS_JSON}
  ]"

# Read mode/strategy/project_dir from config
MODE="mvp"
STRATEGY="co-pilot"
PROJECT_DIR=""
if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE" 2>/dev/null || echo "mvp")
    STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE" 2>/dev/null || echo "co-pilot")
    PROJECT_DIR=$(yq eval '.project.directory // ""' "$CONFIG_FILE" 2>/dev/null || echo "")
fi
# Fallback to pwd if not configured
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"

# Collect git state from the project directory (not the forge repo)
# Use tr to strip any newlines/control chars that could break JSON
GIT_BRANCH=$(git -C "${PROJECT_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null | tr -d '\n\r' || true)
GIT_BRANCH="${GIT_BRANCH:-unknown}"
GIT_TAG=$(git -C "${PROJECT_DIR}" describe --tags --abbrev=0 2>/dev/null | tr -d '\n\r' || true)
GIT_TAG="${GIT_TAG:-none}"
GIT_DIRTY=$(git -C "${PROJECT_DIR}" diff --quiet 2>/dev/null && echo "false" || echo "true")

# Get cost data
TOTAL_COST=0
if [[ -f "${SHARED_DIR}/.logs/cost-summary.json" ]] && command -v jq &>/dev/null; then
    TOTAL_COST=$(jq -r '.total_cost_usd // 0' "${SHARED_DIR}/.logs/cost-summary.json" 2>/dev/null || echo 0)
fi

COST_CAP="no-cap"
if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    COST_CAP=$(yq eval '.cost.max_development_cost // "no-cap"' "$CONFIG_FILE" 2>/dev/null || echo "no-cap")
fi

# Write snapshot
cat > "$SNAPSHOT_FILE" <<EOF
{
  "snapshot_id": "snapshot-${UNIX_TS}",
  "timestamp": "${TIMESTAMP}",
  "project": {
    "name": "$(basename "${PROJECT_DIR}")",
    "mode": "${MODE}",
    "strategy": "${STRATEGY}",
    "project_dir": "${PROJECT_DIR}",
    "config_path": "config/team-config.yaml"
  },
  "iteration": {
    "current": 0,
    "phase": "UNKNOWN",
    "last_verified_tag": "${GIT_TAG}",
    "summary": "Fleet stopped at ${TIMESTAMP}"
  },
  "agents": ${AGENTS_JSON},
  "git": {
    "current_branch": "${GIT_BRANCH}",
    "active_branches": [],
    "uncommitted_changes": ${GIT_DIRTY},
    "last_tag": "${GIT_TAG}"
  },
  "costs": {
    "total_development_cost_usd": ${TOTAL_COST},
    "cost_cap_usd": "${COST_CAP}",
    "per_agent_costs": {}
  },
  "pending_decisions": [],
  "human_overrides_pending": false
}
EOF

log_info "Snapshot saved: ${SNAPSHOT_FILE}"

# ==============================================================================
# Steps 3-5: Shutdown & cleanup (skipped in snapshot-only mode)
# ==============================================================================
if ! $SNAPSHOT_ONLY; then
    # Step 3: SHUTDOWN Broadcast
    log_info "Step 3: Broadcasting SHUTDOWN..."

    if [[ -f "${SCRIPTS_DIR}/broadcast.sh" ]]; then
        bash "${SCRIPTS_DIR}/broadcast.sh" \
            --type "SHUTDOWN" \
            --message "Shutdown now. Exit immediately." \
            --priority "critical" \
            --from "system" 2>/dev/null || true
    fi

    # Wait for graceful exits (up to 30s)
    log_info "Waiting up to 30s for agents to exit..."
    sleep 5  # Brief wait

    # Step 4: Force-kill remaining
    if [[ -n "$SESSION_NAME" ]] && ! $PAUSE_MODE; then
        log_info "Step 4: Cleaning up tmux session..."

        # Kill all windows except the main one
        for window in $(tmux list-windows -t "$SESSION_NAME" 2>/dev/null | grep -v "forge-main" | cut -d: -f1 | sort -rn); do
            tmux kill-window -t "${SESSION_NAME}:${window}" 2>/dev/null || true
        done

        # Destroy the session
        tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
        log_info "tmux session destroyed."
    elif $PAUSE_MODE; then
        log_info "Pause mode: tmux session kept alive for inspection."
    fi

    # Step 5: Cleanup file locks
    if [[ -d "${SHARED_DIR}/.locks" ]]; then
        rm -f "${SHARED_DIR}/.locks"/*.lock 2>/dev/null || true
        log_info "All file locks released."
    fi
else
    log_info "Steps 3-5: Skipped (snapshot-only mode)"
fi

# ==============================================================================
# Step 6: Snapshot retention
# ==============================================================================
if [[ -d "$SNAPSHOTS_DIR" ]]; then
    snapshot_count=$(ls -1 "${SNAPSHOTS_DIR}"/snapshot-*.json 2>/dev/null | wc -l || echo 0)
    if [[ $snapshot_count -gt $SNAPSHOT_RETENTION ]]; then
        to_delete=$((snapshot_count - SNAPSHOT_RETENTION))
        ls -t "${SNAPSHOTS_DIR}"/snapshot-*.json 2>/dev/null | tail -n "$to_delete" | xargs rm -f 2>/dev/null || true
        log_info "Cleaned up ${to_delete} old snapshot(s)."
    fi
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
log_info "═══════════════════════════════════════════════"
log_info "Fleet stopped at ${TIMESTAMP}"
log_info "Snapshot saved: $(basename "$SNAPSHOT_FILE")"
log_info "Agents stopped: ${AGENT_COUNT}"
log_info "Total cost so far: \$${TOTAL_COST} / \$${COST_CAP}"
log_info ""
log_info "To resume: ./forge start"
log_info "To resume from specific snapshot:"
log_info "  ./forge start --snapshot ${SNAPSHOT_FILE}"
log_info "═══════════════════════════════════════════════"
