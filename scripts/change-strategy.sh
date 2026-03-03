#!/usr/bin/env bash
# ==============================================================================
# Forge — Change Execution Strategy
# ==============================================================================
# Updates the execution strategy in team-config.yaml and broadcasts
# the change to all agents.
#
# Valid strategies: auto-pilot, co-pilot, micro-manage
#
# Usage: scripts/change-strategy.sh <new-strategy>
set -euo pipefail

FORGE_DIR="${FORGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SCRIPTS_DIR="${FORGE_DIR}/scripts"
CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Forge]${NC} $*"; }
log_error() { echo -e "${RED}[Forge]${NC} $*" >&2; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/change-strategy.sh <auto-pilot|co-pilot|micro-manage>"
    echo ""
    echo "Switches the execution strategy and broadcasts the change."
    exit 0
fi

NEW_STRATEGY="${1:-}"

# Validate
case "$NEW_STRATEGY" in
    auto-pilot|co-pilot|micro-manage) ;;
    "")
        log_error "No strategy specified."
        echo "Valid strategies: auto-pilot, co-pilot, micro-manage"
        exit 1
        ;;
    *)
        log_error "Invalid strategy: ${NEW_STRATEGY}"
        echo "Valid strategies: auto-pilot, co-pilot, micro-manage"
        exit 1
        ;;
esac

if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "Config file not found: ${CONFIG_FILE}"
    exit 1
fi

if ! command -v yq &>/dev/null; then
    log_error "yq is required. Install: brew install yq"
    exit 1
fi

# Read current strategy
OLD_STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE" 2>/dev/null || echo "co-pilot")

if [[ "$OLD_STRATEGY" == "$NEW_STRATEGY" ]]; then
    log_info "Strategy is already set to '${NEW_STRATEGY}'. No change needed."
    exit 0
fi

# Update config
yq eval -i ".strategy = \"${NEW_STRATEGY}\"" "$CONFIG_FILE"

# Broadcast change
if [[ -x "${SCRIPTS_DIR}/broadcast.sh" ]]; then
    bash "${SCRIPTS_DIR}/broadcast.sh" \
        --type "STRATEGY_CHANGE" \
        --message "Execution strategy changed: ${OLD_STRATEGY} → ${NEW_STRATEGY}" \
        --priority "high" \
        --from "system" 2>/dev/null || true
fi

# Report
echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}  Strategy Change${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Previous:${NC}  ${OLD_STRATEGY}"
echo -e "  ${CYAN}New:${NC}       ${GREEN}${NEW_STRATEGY}${NC}"
echo ""

case "$NEW_STRATEGY" in
    auto-pilot)
        echo -e "  ${CYAN}Approval:${NC}  Fully autonomous — agents make all decisions"
        echo -e "  ${CYAN}Flags:${NC}     --dangerously-skip-permissions"
        ;;
    co-pilot)
        echo -e "  ${CYAN}Approval:${NC}  Routine work autonomous, architecture needs approval"
        echo -e "  ${CYAN}Flags:${NC}     --allowedTools 'Edit,Write,NotebookEdit'"
        ;;
    micro-manage)
        echo -e "  ${CYAN}Approval:${NC}  Every significant decision requires human approval"
        echo -e "  ${CYAN}Flags:${NC}     Default interactive permissions"
        ;;
esac
echo ""

log_info "Strategy updated. Change broadcast to all agents."
