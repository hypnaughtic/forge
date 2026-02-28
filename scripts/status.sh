#!/usr/bin/env bash
# ==============================================================================
# Forge — Status Script
# ==============================================================================
# Reads all agent status files and prints a formatted summary table.
# Cross-references with tmux to detect dead/stale agents.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHARED_DIR="${FORGE_DIR}/shared"
STATUS_DIR="${SHARED_DIR}/.status"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/status.sh [--json]"
    echo ""
    echo "Shows status of all running agents with stale/dead detection."
    echo ""
    echo "Options:"
    echo "  --json    Output raw JSON instead of formatted table"
    exit 0
fi

JSON_MODE=false
if [[ "${1:-}" == "--json" ]]; then
    JSON_MODE=true
fi

if [[ ! -d "$STATUS_DIR" ]]; then
    echo "No status directory found. Is a session running?"
    exit 1
fi

# Get tmux windows for cross-reference
SESSION_NAME=$(tmux list-sessions 2>/dev/null | grep "^forge-" | head -1 | cut -d: -f1 || true)
TMUX_WINDOWS=""
if [[ -n "$SESSION_NAME" ]]; then
    TMUX_WINDOWS=$(tmux list-windows -t "$SESSION_NAME" -F '#{window_name}' 2>/dev/null || true)
fi

# Portable ISO date to epoch (works on both macOS and Linux)
iso_to_epoch() {
    local iso_date="$1"
    if [[ -z "$iso_date" || "$iso_date" == "null" ]]; then
        echo "0"
        return
    fi
    # Try GNU date first, then macOS date (with TZ=UTC for Z suffix), then python as fallback
    date -d "$iso_date" +%s 2>/dev/null \
        || TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%SZ" "$iso_date" +%s 2>/dev/null \
        || TZ=UTC date -j -f "%Y-%m-%dT%T%z" "$iso_date" +%s 2>/dev/null \
        || python3 -c "from datetime import datetime; print(int(datetime.fromisoformat('${iso_date}'.replace('Z','+00:00')).timestamp()))" 2>/dev/null \
        || echo "0"
}

CURRENT_TIME=$(date +%s)

if ! $JSON_MODE; then
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Forge Agent Status${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    printf "  %-25s %-14s %-35s %s\n" "AGENT" "STATUS" "CURRENT TASK" "FLAGS"
    printf "  %-25s %-14s %-35s %s\n" "─────" "──────" "────────────" "─────"
fi

for status_file in "${STATUS_DIR}"/*.json; do
    [[ -f "$status_file" ]] || continue

    agent_name=$(basename "$status_file" .json)

    # Parse JSON fields
    if command -v jq &>/dev/null; then
        status=$(jq -r '.status // "unknown"' "$status_file" 2>/dev/null)
        task=$(jq -r '.current_task // ""' "$status_file" 2>/dev/null)
        last_updated=$(jq -r '.last_updated // ""' "$status_file" 2>/dev/null)
        cost=$(jq -r '.cost_estimate_usd // 0' "$status_file" 2>/dev/null)
        limit_status=$(jq -r '.usage_limits.status // "normal"' "$status_file" 2>/dev/null)
    else
        status=$(grep -o '"status": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "unknown")
        task=$(grep -o '"current_task": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "")
        last_updated=$(grep -o '"last_updated": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "")
        cost="?"
        limit_status="?"
    fi

    # Truncate task for display
    if [[ ${#task} -gt 33 ]]; then
        task="${task:0:30}..."
    fi

    # Check flags
    flags=""

    # Check if tmux window exists
    if [[ -n "$SESSION_NAME" ]]; then
        if ! echo "$TMUX_WINDOWS" | grep -q "^${agent_name}$"; then
            flags="${RED}DEAD${NC} "
        fi
    fi

    # Check staleness
    if [[ -n "$last_updated" ]]; then
        updated_epoch=$(iso_to_epoch "$last_updated")
        age=$((CURRENT_TIME - updated_epoch))
        if [[ $age -gt 900 ]]; then
            flags="${flags}${RED}STALE(${age}s)${NC} "
        elif [[ $age -gt 300 ]]; then
            flags="${flags}${YELLOW}STALE(${age}s)${NC} "
        fi
    fi

    # Check rate limiting
    if [[ "$limit_status" == "rate-limited" ]]; then
        flags="${flags}${YELLOW}RATE-LIMITED${NC} "
    fi

    # Color the status
    case "$status" in
        idle)         status_colored="${GREEN}${status}${NC}" ;;
        working)      status_colored="${CYAN}${status}${NC}" ;;
        blocked)      status_colored="${RED}${status}${NC}" ;;
        review)       status_colored="${YELLOW}${status}${NC}" ;;
        done)         status_colored="${GREEN}${status}${NC}" ;;
        suspended)    status_colored="${YELLOW}${status}${NC}" ;;
        rate-limited) status_colored="${YELLOW}${status}${NC}" ;;
        error)        status_colored="${RED}${status}${NC}" ;;
        terminated)   status_colored="${RED}${status}${NC}" ;;
        *)            status_colored="$status" ;;
    esac

    if ! $JSON_MODE; then
        printf "  %-25s %-14b %-35s %b\n" "$agent_name" "$status_colored" "$task" "$flags"
    fi
done

if ! $JSON_MODE; then
    echo ""
    # Show cost summary if cost-tracker data exists
    COST_SUMMARY="${SHARED_DIR}/.logs/cost-summary.json"
    if [[ -f "$COST_SUMMARY" ]] && command -v jq &>/dev/null; then
        total=$(jq -r '.total_cost_usd // 0' "$COST_SUMMARY" 2>/dev/null)
        cap=$(jq -r '.cost_cap_usd // "no-cap"' "$COST_SUMMARY" 2>/dev/null)
        echo -e "  ${CYAN}Cost:${NC} \$${total} / \$${cap}"
    fi

    # Show snapshot info
    SNAPSHOTS_DIR="${SHARED_DIR}/.snapshots"
    if [[ -d "$SNAPSHOTS_DIR" ]]; then
        latest=$(ls -t "${SNAPSHOTS_DIR}"/snapshot-*.json 2>/dev/null | head -1 || true)
        if [[ -n "$latest" ]]; then
            echo -e "  ${CYAN}Last snapshot:${NC} $(basename "$latest")"
        fi
    fi

    echo ""
fi
