#!/usr/bin/env bash
# ==============================================================================
# Forge Cockpit — Metrics Panel
# ==============================================================================
# Renders the top-left metrics display: project info, mode, strategy,
# iteration progress, cost, and elapsed time.
# Designed to run under `watch --color -n 3`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORGE_DIR="${FORGE_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# shellcheck source=render.sh
source "${SCRIPT_DIR}/render.sh"

CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"
SHARED_DIR="${FORGE_DIR}/shared"
STATUS_DIR="${SHARED_DIR}/.status"
VERSION_FILE="${FORGE_DIR}/VERSION"

# Read version
VERSION="dev"
if [[ -f "$VERSION_FILE" ]]; then
    VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
fi

# Read config values
PROJECT_NAME="Forge Project"
MODE="mvp"
STRATEGY="co-pilot"
COST_CAP="no-cap"

if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    PROJECT_NAME=$(yq eval '.project.description // "Forge Project"' "$CONFIG_FILE" 2>/dev/null || echo "Forge Project")
    MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE" 2>/dev/null || echo "mvp")
    STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE" 2>/dev/null || echo "co-pilot")
    COST_CAP=$(yq eval '.cost.max_development_cost // "no-cap"' "$CONFIG_FILE" 2>/dev/null || echo "no-cap")
fi

# Read iteration info from TL status or latest snapshot
ITERATION="—"
PHASE="—"
TASKS_DONE=0
TASKS_TOTAL=0

if [[ -f "${STATUS_DIR}/team-leader.json" ]] && command -v jq &>/dev/null; then
    ITERATION=$(jq -r '.iteration // 0' "${STATUS_DIR}/team-leader.json" 2>/dev/null || echo "—")
    PHASE=$(jq -r '.current_task // "—"' "${STATUS_DIR}/team-leader.json" 2>/dev/null || echo "—")
fi

# Count active agents
AGENT_COUNT=0
if [[ -d "$STATUS_DIR" ]]; then
    AGENT_COUNT=$(find "$STATUS_DIR" -name '*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
fi

# Read cost data
TOTAL_COST="0.00"
COST_SUMMARY="${SHARED_DIR}/.logs/cost-summary.json"
if [[ -f "$COST_SUMMARY" ]] && command -v jq &>/dev/null; then
    TOTAL_COST=$(jq -r '.total_cost_usd // 0' "$COST_SUMMARY" 2>/dev/null || echo "0.00")
fi

# Calculate elapsed time from earliest agent session_start
ELAPSED="—"
if [[ -d "$STATUS_DIR" ]] && command -v jq &>/dev/null; then
    EARLIEST=""
    for sf in "${STATUS_DIR}"/*.json; do
        [[ -f "$sf" ]] || continue
        start_time=$(jq -r '.session_start // ""' "$sf" 2>/dev/null || true)
        if [[ -n "$start_time" && "$start_time" != "null" ]]; then
            epoch=$(iso_to_epoch "$start_time")
            if [[ -z "$EARLIEST" || "$epoch" -lt "$EARLIEST" ]]; then
                EARLIEST="$epoch"
            fi
        fi
    done
    if [[ -n "$EARLIEST" && "$EARLIEST" != "0" ]]; then
        NOW=$(date +%s)
        ELAPSED=$(format_elapsed $(( NOW - EARLIEST )))
    fi
fi

# --- Render ---
clear 2>/dev/null || true

echo -e "${CR_CYAN}${CR_BOLD}  FORGE COCKPIT v${VERSION}${CR_RESET}"
draw_separator 40
echo -e "  ${CR_CYAN}Project:${CR_RESET}    $(truncate "$PROJECT_NAME" 26)"
echo -e "  ${CR_CYAN}Mode:${CR_RESET}       ${CR_GREEN}${MODE}${CR_RESET}"
echo -e "  ${CR_CYAN}Strategy:${CR_RESET}   ${CR_GREEN}${STRATEGY}${CR_RESET}"
echo -e "  ${CR_CYAN}Iteration:${CR_RESET}  ${ITERATION}"

# Cost with color coding
if [[ "$COST_CAP" != "no-cap" && "$COST_CAP" != "0" ]] && command -v bc &>/dev/null; then
    OVER=$(echo "$TOTAL_COST > $COST_CAP" | bc 2>/dev/null || echo "0")
    NEAR=$(echo "$TOTAL_COST > ($COST_CAP * 0.8)" | bc 2>/dev/null || echo "0")
    if [[ "$OVER" == "1" ]]; then
        echo -e "  ${CR_CYAN}Cost:${CR_RESET}       ${CR_RED}\$${TOTAL_COST} / \$${COST_CAP}${CR_RESET}"
    elif [[ "$NEAR" == "1" ]]; then
        echo -e "  ${CR_CYAN}Cost:${CR_RESET}       ${CR_YELLOW}\$${TOTAL_COST} / \$${COST_CAP}${CR_RESET}"
    else
        echo -e "  ${CR_CYAN}Cost:${CR_RESET}       ${CR_GREEN}\$${TOTAL_COST} / \$${COST_CAP}${CR_RESET}"
    fi
else
    echo -e "  ${CR_CYAN}Cost:${CR_RESET}       \$${TOTAL_COST} / \$${COST_CAP}"
fi

echo -e "  ${CR_CYAN}Agents:${CR_RESET}     ${AGENT_COUNT} active"
echo -e "  ${CR_CYAN}Elapsed:${CR_RESET}    ${ELAPSED}"
