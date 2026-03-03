#!/usr/bin/env bash
# ==============================================================================
# Forge — Change Project Mode
# ==============================================================================
# Updates the project quality mode in team-config.yaml and broadcasts
# the change to all agents.
#
# Valid modes: mvp, production-ready, no-compromise
#
# Usage: scripts/change-mode.sh <new-mode>
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
    echo "Usage: scripts/change-mode.sh <mvp|production-ready|no-compromise>"
    echo ""
    echo "Switches the project quality mode and broadcasts the change."
    exit 0
fi

NEW_MODE="${1:-}"

# Validate
case "$NEW_MODE" in
    mvp|production-ready|no-compromise) ;;
    "")
        log_error "No mode specified."
        echo "Valid modes: mvp, production-ready, no-compromise"
        exit 1
        ;;
    *)
        log_error "Invalid mode: ${NEW_MODE}"
        echo "Valid modes: mvp, production-ready, no-compromise"
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

# Read current mode
OLD_MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE" 2>/dev/null || echo "mvp")

if [[ "$OLD_MODE" == "$NEW_MODE" ]]; then
    log_info "Mode is already set to '${NEW_MODE}'. No change needed."
    exit 0
fi

# Update config
yq eval -i ".mode = \"${NEW_MODE}\"" "$CONFIG_FILE"

# Broadcast change
if [[ -x "${SCRIPTS_DIR}/broadcast.sh" ]]; then
    bash "${SCRIPTS_DIR}/broadcast.sh" \
        --type "MODE_CHANGE" \
        --message "Project mode changed: ${OLD_MODE} → ${NEW_MODE}" \
        --priority "high" \
        --from "system" 2>/dev/null || true
fi

# Report
echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}  Mode Change${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Previous:${NC}  ${OLD_MODE}"
echo -e "  ${CYAN}New:${NC}       ${GREEN}${NEW_MODE}${NC}"
echo ""

case "$NEW_MODE" in
    mvp)
        echo -e "  ${CYAN}Quality:${NC}   70% critic pass rate"
        echo -e "  ${CYAN}Testing:${NC}   Happy-path + smoke tests"
        echo -e "  ${CYAN}Team:${NC}      Lean (8 agents)"
        ;;
    production-ready)
        echo -e "  ${CYAN}Quality:${NC}   90% critic pass rate"
        echo -e "  ${CYAN}Testing:${NC}   >90% coverage + integration"
        echo -e "  ${CYAN}Team:${NC}      Full (12 agents)"
        ;;
    no-compromise)
        echo -e "  ${CYAN}Quality:${NC}   100% critic pass rate"
        echo -e "  ${CYAN}Testing:${NC}   Exhaustive + chaos testing"
        echo -e "  ${CYAN}Team:${NC}      Full (12 agents)"
        ;;
esac
echo ""

log_info "Mode updated. Change broadcast to all agents."
