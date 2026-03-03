#!/usr/bin/env bash
# ==============================================================================
# Forge Cockpit — Agent Status Grid
# ==============================================================================
# Renders a compact, color-coded agent status grid.
# Each agent shows: status dot, abbreviation, status text, current task.
# Designed to run under `watch --color -n 2`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORGE_DIR="${FORGE_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# shellcheck source=render.sh
source "${SCRIPT_DIR}/render.sh"

SHARED_DIR="${FORGE_DIR}/shared"
STATUS_DIR="${SHARED_DIR}/.status"

# --- Render ---
clear 2>/dev/null || true

echo -e "${CR_CYAN}${CR_BOLD}  AGENT STATUS${CR_RESET}"
draw_separator 30

if [[ ! -d "$STATUS_DIR" ]]; then
    echo -e "  ${CR_DIM}No agents running${CR_RESET}"
    exit 0
fi

AGENT_COUNT=0
for status_file in "${STATUS_DIR}"/*.json; do
    [[ -f "$status_file" ]] || continue
    AGENT_COUNT=$((AGENT_COUNT + 1))

    agent_name=$(basename "$status_file" .json)
    abbrev=$(agent_abbrev "$agent_name")

    # Parse status fields
    status="unknown"
    task=""
    if command -v jq &>/dev/null; then
        status=$(jq -r '.status // "unknown"' "$status_file" 2>/dev/null || echo "unknown")
        task=$(jq -r '.current_task // ""' "$status_file" 2>/dev/null || echo "")
    else
        status=$(grep -o '"status": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "unknown")
        task=$(grep -o '"current_task": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "")
    fi

    # Truncate task for display
    task=$(truncate "$task" 22)

    # Render agent line
    dot=$(status_dot "$status")
    printf "  %b %s: %s\n" "$dot" "$abbrev" "$task"
done

if [[ $AGENT_COUNT -eq 0 ]]; then
    echo -e "  ${CR_DIM}No agents running${CR_RESET}"
fi
