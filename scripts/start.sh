#!/usr/bin/env bash
# ==============================================================================
# Forge — Start Script
# ==============================================================================
# Starts a fresh Forge session: reads config, initializes project, starts tmux,
# spawns the Team Leader, and launches background daemons.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="${FORGE_DIR}/scripts"
SHARED_DIR="${FORGE_DIR}/shared"
CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Forge]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[Forge]${NC} $*"; }
log_error() { echo -e "${RED}[Forge]${NC} $*" >&2; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/start.sh"
    echo ""
    echo "Starts a fresh Forge session:"
    echo "  - Reads config/team-config.yaml"
    echo "  - Creates tmux session"
    echo "  - Initializes project (generates agent files)"
    echo "  - Starts watchdog and log-aggregator daemons"
    echo "  - Spawns Team Leader in interactive mode"
    echo ""
    echo "This script is called by './forge start' — use that instead."
    exit 0
fi

# --- Validate prerequisites ---
for cmd in tmux claude yq; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Required tool not found: $cmd. Run './forge setup' first."
        exit 1
    fi
done

if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "Config file not found: $CONFIG_FILE"
    log_error "Run './forge init' to create it."
    exit 1
fi

# --- Read config ---
log_info "Reading configuration..."

PROJECT_NAME=$(yq eval '.project.description // "forge-project"' "$CONFIG_FILE" | head -c 30 | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g')
if [[ -z "$PROJECT_NAME" || "$PROJECT_NAME" == "forge-project" ]]; then
    PROJECT_NAME="forge-project"
fi

PROJECT_TYPE=$(yq eval '.project.type // "new"' "$CONFIG_FILE")
EXISTING_PATH=$(yq eval '.project.existing_project_path // ""' "$CONFIG_FILE")
MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE")
STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE")

# Determine project directory
if [[ "$PROJECT_TYPE" == "existing" && -n "$EXISTING_PATH" ]]; then
    PROJECT_DIR="$EXISTING_PATH"
else
    PROJECT_DIR=$(pwd)
fi

SESSION_NAME="forge-${PROJECT_NAME}"

log_info "Project: ${PROJECT_NAME}"
log_info "Mode: ${MODE} | Strategy: ${STRATEGY}"
log_info "Project directory: ${PROJECT_DIR}"

# --- Ensure shared/ directory exists ---
mkdir -p "${SHARED_DIR}/.queue" "${SHARED_DIR}/.status" "${SHARED_DIR}/.memory" \
         "${SHARED_DIR}/.decisions" "${SHARED_DIR}/.iterations" "${SHARED_DIR}/.artifacts" \
         "${SHARED_DIR}/.locks" "${SHARED_DIR}/.logs" "${SHARED_DIR}/.logs/archive" \
         "${SHARED_DIR}/.snapshots" "${SHARED_DIR}/.secrets" "${SHARED_DIR}/.human"

# Initialize artifact registry if not present
if [[ ! -f "${SHARED_DIR}/.artifacts/registry.json" ]]; then
    echo '{"artifacts": []}' > "${SHARED_DIR}/.artifacts/registry.json"
fi

# --- Kill existing session if any ---
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    log_warn "Existing tmux session '${SESSION_NAME}' found. Killing it..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
fi

# --- Run init-project.sh ---
log_info "Initializing project..."
bash "${SCRIPTS_DIR}/init-project.sh" --config "$CONFIG_FILE" --project-dir "$PROJECT_DIR"

# --- Create tmux session ---
log_info "Creating tmux session: ${SESSION_NAME}"
tmux new-session -d -s "$SESSION_NAME" -n "forge-main" "bash"

# --- Start watchdog daemon ---
log_info "Starting watchdog daemon..."
tmux new-window -t "$SESSION_NAME" -n "watchdog" \
    "bash '${SCRIPTS_DIR}/watchdog.sh' --forge-dir '${FORGE_DIR}' --session '${SESSION_NAME}'; bash"

# --- Start log aggregator daemon ---
log_info "Starting log aggregator daemon..."
tmux new-window -t "$SESSION_NAME" -n "log-aggregator" \
    "bash '${SCRIPTS_DIR}/log-aggregator.sh' --forge-dir '${FORGE_DIR}'; bash"

# --- Start monitoring loop for human overrides ---
log_info "Starting human override monitor..."
OVERRIDE_FILE="${SHARED_DIR}/.human/override.md"
touch "$OVERRIDE_FILE"
OVERRIDE_MTIME=$(stat -c %Y "$OVERRIDE_FILE" 2>/dev/null || stat -f %m "$OVERRIDE_FILE" 2>/dev/null || echo "0")

# --- Spawn Team Leader (interactive mode) ---
log_info "Spawning Team Leader in interactive mode..."
bash "${SCRIPTS_DIR}/spawn-agent.sh" \
    --agent-type "team-leader" \
    --instance-id "1" \
    --project-dir "$PROJECT_DIR" \
    --session "$SESSION_NAME" \
    --forge-dir "$FORGE_DIR" \
    --mode "$MODE" \
    --strategy "$STRATEGY"

# --- Summary ---
echo ""
log_info "═══════════════════════════════════════"
log_info "Forge session started: ${SESSION_NAME}"
log_info "Mode: ${MODE} | Strategy: ${STRATEGY}"
log_info ""
log_info "The Team Leader is now running in tmux."
log_info "  Attach: ./forge attach"
log_info "  Status: ./forge status"
log_info "  Tell:   ./forge tell \"your message\""
log_info "  Stop:   ./forge stop"
log_info "═══════════════════════════════════════"
