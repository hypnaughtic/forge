#!/usr/bin/env bash
# ==============================================================================
# Forge — Team View Script
# ==============================================================================
# Renders detailed per-agent information: status, current task, recent
# decisions, working memory summary, and cost.
#
# Usage: scripts/team-view.sh              # All agents
#        scripts/team-view.sh backend-developer  # Single agent deep dive
set -euo pipefail

FORGE_DIR="${FORGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SHARED_DIR="${FORGE_DIR}/shared"
STATUS_DIR="${SHARED_DIR}/.status"
MEMORY_DIR="${SHARED_DIR}/.memory"
DECISIONS_FILE="${SHARED_DIR}/.decisions/decision-log.md"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/team-view.sh [agent-name]"
    echo ""
    echo "Without arguments: overview of all agents."
    echo "With agent name: detailed view for one agent."
    exit 0
fi

TARGET_AGENT="${1:-}"

# Color-code status
color_status() {
    local status="$1"
    case "$status" in
        working|active)     echo -e "${GREEN}${status}${NC}" ;;
        idle|waiting)       echo -e "${YELLOW}${status}${NC}" ;;
        blocked|error)      echo -e "${RED}${status}${NC}" ;;
        done|completed)     echo -e "${DIM}${status}${NC}" ;;
        suspended|review)   echo -e "${YELLOW}${status}${NC}" ;;
        rate-limited)       echo -e "${YELLOW}${status}${NC}" ;;
        *)                  echo "$status" ;;
    esac
}

# --- Single agent deep dive ---
if [[ -n "$TARGET_AGENT" ]]; then
    STATUS_FILE="${STATUS_DIR}/${TARGET_AGENT}.json"
    MEMORY_FILE="${MEMORY_DIR}/${TARGET_AGENT}-memory.md"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Agent Deep Dive: ${BOLD}${TARGET_AGENT}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # Status
    if [[ -f "$STATUS_FILE" ]]; then
        if command -v jq &>/dev/null; then
            status=$(jq -r '.status // "unknown"' "$STATUS_FILE" 2>/dev/null)
            task=$(jq -r '.current_task // "—"' "$STATUS_FILE" 2>/dev/null)
            iteration=$(jq -r '.iteration // 0' "$STATUS_FILE" 2>/dev/null)
            cost=$(jq -r '.cost_estimate_usd // 0' "$STATUS_FILE" 2>/dev/null)
            last_updated=$(jq -r '.last_updated // "—"' "$STATUS_FILE" 2>/dev/null)
            artifacts=$(jq -r '.artifacts_produced // [] | join(", ")' "$STATUS_FILE" 2>/dev/null)
            blockers=$(jq -r '.blockers // [] | join(", ")' "$STATUS_FILE" 2>/dev/null)
            limit_status=$(jq -r '.usage_limits.status // "normal"' "$STATUS_FILE" 2>/dev/null)
        else
            status="unknown"
            task="—"
            iteration="?"
            cost="?"
            last_updated="—"
            artifacts=""
            blockers=""
            limit_status="?"
        fi

        echo -e "  ${CYAN}Status:${NC}       $(color_status "$status")"
        echo -e "  ${CYAN}Task:${NC}         ${task}"
        echo -e "  ${CYAN}Iteration:${NC}    ${iteration}"
        echo -e "  ${CYAN}Cost:${NC}         \$${cost}"
        echo -e "  ${CYAN}Updated:${NC}      ${last_updated}"
        if [[ -n "$artifacts" && "$artifacts" != "null" ]]; then
            echo -e "  ${CYAN}Artifacts:${NC}    ${artifacts}"
        fi
        if [[ -n "$blockers" && "$blockers" != "null" ]]; then
            echo -e "  ${CYAN}Blockers:${NC}     ${RED}${blockers}${NC}"
        fi
        if [[ "$limit_status" != "normal" ]]; then
            echo -e "  ${CYAN}Limits:${NC}       ${YELLOW}${limit_status}${NC}"
        fi
    else
        echo -e "  ${DIM}No status file found for ${TARGET_AGENT}${NC}"
    fi

    # Memory
    echo ""
    echo -e "  ${CYAN}${BOLD}Working Memory:${NC}"
    echo -e "  ${DIM}─────────────────────────────────────────────${NC}"
    if [[ -f "$MEMORY_FILE" ]]; then
        # Show first 20 lines of memory
        head -20 "$MEMORY_FILE" | while IFS= read -r line; do
            echo "  $line"
        done
        total_lines=$(wc -l < "$MEMORY_FILE" | tr -d ' ')
        if [[ $total_lines -gt 20 ]]; then
            echo -e "  ${DIM}... (${total_lines} total lines)${NC}"
        fi
    else
        echo -e "  ${DIM}No memory file found${NC}"
    fi

    # Recent decisions by this agent
    echo ""
    echo -e "  ${CYAN}${BOLD}Recent Decisions:${NC}"
    echo -e "  ${DIM}─────────────────────────────────────────────${NC}"
    if [[ -f "$DECISIONS_FILE" ]]; then
        grep -i "${TARGET_AGENT}" "$DECISIONS_FILE" 2>/dev/null | tail -5 | while IFS= read -r line; do
            echo "  $line"
        done || echo -e "  ${DIM}No decisions found for this agent${NC}"
    else
        echo -e "  ${DIM}No decision log found${NC}"
    fi

    echo ""
    exit 0
fi

# --- All agents overview ---
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Forge Team Overview${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if [[ ! -d "$STATUS_DIR" ]]; then
    echo -e "  ${DIM}No agents running. Start a session first.${NC}"
    echo ""
    exit 0
fi

printf "  %-25s %-12s %-30s %s\n" "AGENT" "STATUS" "CURRENT TASK" "COST"
printf "  %-25s %-12s %-30s %s\n" "─────" "──────" "────────────" "────"

for status_file in "${STATUS_DIR}"/*.json; do
    [[ -f "$status_file" ]] || continue

    agent_name=$(basename "$status_file" .json)
    status="unknown"
    task=""
    cost="0"

    if command -v jq &>/dev/null; then
        status=$(jq -r '.status // "unknown"' "$status_file" 2>/dev/null || echo "unknown")
        task=$(jq -r '.current_task // ""' "$status_file" 2>/dev/null || echo "")
        cost=$(jq -r '.cost_estimate_usd // 0' "$status_file" 2>/dev/null || echo "0")
    else
        status=$(grep -o '"status": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "unknown")
        task=$(grep -o '"current_task": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "")
        cost="?"
    fi

    # Truncate task
    if [[ ${#task} -gt 28 ]]; then
        task="${task:0:25}..."
    fi

    printf "  %-25s %-12b %-30s \$%s\n" "$agent_name" "$(color_status "$status")" "$task" "$cost"
done

echo ""
echo -e "  ${DIM}Use './forge team <agent-name>' for a detailed view of a specific agent.${NC}"
echo ""
