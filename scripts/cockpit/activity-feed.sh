#!/usr/bin/env bash
# ==============================================================================
# Forge Cockpit — Activity Feed
# ==============================================================================
# Renders recent activity from combined logs and Team Leader memory.
# Shows timestamped entries with agent abbreviations.
# Designed to run under `watch --color -n 5`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORGE_DIR="${FORGE_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# shellcheck source=render.sh
source "${SCRIPT_DIR}/render.sh"

SHARED_DIR="${FORGE_DIR}/shared"
LOGS_DIR="${SHARED_DIR}/.logs"
MEMORY_DIR="${SHARED_DIR}/.memory"
MAX_ENTRIES="${1:-10}"

# --- Render ---
clear 2>/dev/null || true

# Team Leader Summary (if available)
TL_MEMORY="${MEMORY_DIR}/team-leader-memory.md"
if [[ -f "$TL_MEMORY" ]]; then
    echo -e "${CR_CYAN}${CR_BOLD}  TEAM LEADER SUMMARY${CR_RESET}"
    draw_separator 50
    # Extract the first meaningful paragraph (skip YAML frontmatter and headers)
    SUMMARY=""
    IN_CONTENT=false
    while IFS= read -r line; do
        # Skip empty lines at start
        [[ -z "$line" && "$IN_CONTENT" == false ]] && continue
        # Skip markdown headers
        [[ "$line" == "#"* ]] && continue
        # Skip YAML frontmatter
        [[ "$line" == "---" ]] && continue
        IN_CONTENT=true
        SUMMARY="${SUMMARY}  ${line}\n"
        # Show first 3 content lines
        line_count=$((${line_count:-0} + 1))
        if [[ ${line_count:-0} -ge 3 ]]; then
            break
        fi
    done < "$TL_MEMORY"
    if [[ -n "$SUMMARY" ]]; then
        echo -e "$SUMMARY"
    else
        echo -e "  ${CR_DIM}No summary available${CR_RESET}"
    fi
    echo ""
fi

# Recent Activity from combined log
echo -e "${CR_CYAN}${CR_BOLD}  RECENT ACTIVITY${CR_RESET}"
draw_separator 50

COMBINED_LOG="${LOGS_DIR}/combined.log"
if [[ -f "$COMBINED_LOG" ]]; then
    # Read last N entries, format with colors
    ENTRY_COUNT=0
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue

        # Try to parse as JSONL
        if command -v jq &>/dev/null; then
            ts=$(echo "$line" | jq -r '.timestamp // ""' 2>/dev/null || true)
            agent=$(echo "$line" | jq -r '.agent // ""' 2>/dev/null || true)
            event=$(echo "$line" | jq -r '.event // .message // ""' 2>/dev/null || true)
        else
            ts=""
            agent=""
            event="$line"
        fi

        # Format timestamp (show HH:MM only)
        if [[ -n "$ts" && "$ts" != "null" ]]; then
            time_display=$(echo "$ts" | grep -o '[0-9][0-9]:[0-9][0-9]' | head -1 || echo "")
        else
            time_display=""
        fi

        # Get agent abbreviation
        if [[ -n "$agent" && "$agent" != "null" ]]; then
            abbrev=$(agent_abbrev "$agent")
        else
            abbrev="SYS"
        fi

        # Truncate event
        event=$(truncate "${event:-$line}" 45)

        if [[ -n "$time_display" ]]; then
            echo -e "  ${CR_DIM}[${time_display}]${CR_RESET} ${CR_BOLD}${abbrev}:${CR_RESET} ${event}"
        else
            echo -e "  ${CR_BOLD}${abbrev}:${CR_RESET} ${event}"
        fi

        ENTRY_COUNT=$((ENTRY_COUNT + 1))
        [[ $ENTRY_COUNT -ge $MAX_ENTRIES ]] && break
    done < <(tail -n "$MAX_ENTRIES" "$COMBINED_LOG" 2>/dev/null)

    if [[ $ENTRY_COUNT -eq 0 ]]; then
        echo -e "  ${CR_DIM}No recent activity${CR_RESET}"
    fi
else
    echo -e "  ${CR_DIM}No activity log found${CR_RESET}"
fi
