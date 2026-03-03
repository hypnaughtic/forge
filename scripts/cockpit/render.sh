#!/usr/bin/env bash
# ==============================================================================
# Forge Cockpit — Shared Rendering Utilities
# ==============================================================================
# Color constants, box-drawing characters, and formatting functions
# used by all cockpit panel scripts.
# Usage: source scripts/cockpit/render.sh
set -euo pipefail

# --- ANSI Color Constants ---
# Uses tput where available, falls back to raw ANSI codes

if command -v tput &>/dev/null && [[ -n "${TERM:-}" ]] && tput colors &>/dev/null; then
    CR_RESET="$(tput sgr0)"
    CR_BOLD="$(tput bold)"
    CR_DIM="$(tput dim)"
    CR_RED="$(tput setaf 1)"
    CR_GREEN="$(tput setaf 2)"
    CR_YELLOW="$(tput setaf 3)"
    CR_BLUE="$(tput setaf 4)"
    CR_MAGENTA="$(tput setaf 5)"
    CR_CYAN="$(tput setaf 6)"
    CR_WHITE="$(tput setaf 7)"
    CR_ORANGE="$(tput setaf 208 2>/dev/null || tput setaf 3)"
    CR_GRAY="$(tput setaf 245 2>/dev/null || tput setaf 7)"
    CR_PURPLE="$(tput setaf 141 2>/dev/null || tput setaf 5)"
else
    CR_RESET='\033[0m'
    CR_BOLD='\033[1m'
    CR_DIM='\033[2m'
    CR_RED='\033[0;31m'
    CR_GREEN='\033[0;32m'
    CR_YELLOW='\033[1;33m'
    CR_BLUE='\033[0;34m'
    CR_MAGENTA='\033[0;35m'
    CR_CYAN='\033[0;36m'
    CR_WHITE='\033[0;37m'
    CR_ORANGE='\033[0;33m'
    CR_GRAY='\033[0;90m'
    CR_PURPLE='\033[0;35m'
fi

# Export for subshells
export CR_RESET CR_BOLD CR_DIM CR_RED CR_GREEN CR_YELLOW CR_BLUE
export CR_MAGENTA CR_CYAN CR_WHITE CR_ORANGE CR_GRAY CR_PURPLE

# --- Box-Drawing Characters ---
BOX_H="─"
BOX_V="│"
BOX_TL="┌"
BOX_TR="┐"
BOX_BL="└"
BOX_BR="┘"
BOX_LT="├"
BOX_RT="┤"
BOX_TT="┬"
BOX_BT="┴"
BOX_CROSS="┼"
BOX_DH="═"
BOX_DV="║"

export BOX_H BOX_V BOX_TL BOX_TR BOX_BL BOX_BR BOX_LT BOX_RT BOX_TT BOX_BT
export BOX_CROSS BOX_DH BOX_DV

# --- Agent Abbreviations (bash 3 compatible) ---
# Usage: agent_abbrev "backend-developer" → "BE"
agent_abbrev() {
    local name="$1"
    case "$name" in
        team-leader)                echo "TL" ;;
        architect)                  echo "AR" ;;
        backend-developer)          echo "BE" ;;
        frontend-engineer)          echo "FE" ;;
        frontend-designer)          echo "FD" ;;
        frontend-developer)         echo "FV" ;;
        qa-engineer)                echo "QA" ;;
        devops-specialist)          echo "DO" ;;
        critic)                     echo "CR" ;;
        research-strategist)        echo "RS" ;;
        researcher)                 echo "RE" ;;
        strategist)                 echo "ST" ;;
        security-tester)            echo "SE" ;;
        performance-engineer)       echo "PE" ;;
        documentation-specialist)   echo "DC" ;;
        *)                          echo "${name:0:2}" ;;
    esac
}

# --- Formatting Functions ---

# Get terminal width, default to 80
get_term_width() {
    tput cols 2>/dev/null || echo 80
}

# Get terminal height, default to 24
get_term_height() {
    tput lines 2>/dev/null || echo 24
}

# Truncate string to max length with ellipsis
# Usage: truncate "long string" 20
truncate() {
    local str="$1"
    local max="${2:-30}"
    if [[ ${#str} -gt $max ]]; then
        echo "${str:0:$((max - 3))}..."
    else
        echo "$str"
    fi
}

# Color-code a status string
# Usage: color_status "working" → green "working"
color_status() {
    local status="$1"
    case "$status" in
        working|active)     echo -e "${CR_GREEN}${status}${CR_RESET}" ;;
        idle|waiting)       echo -e "${CR_YELLOW}${status}${CR_RESET}" ;;
        blocked|error)      echo -e "${CR_RED}${status}${CR_RESET}" ;;
        rate-limited)       echo -e "${CR_ORANGE}${status}${CR_RESET}" ;;
        suspended)          echo -e "${CR_PURPLE}${status}${CR_RESET}" ;;
        done|completed)     echo -e "${CR_GRAY}${status}${CR_RESET}" ;;
        review)             echo -e "${CR_CYAN}${status}${CR_RESET}" ;;
        *)                  echo -e "${CR_WHITE}${status}${CR_RESET}" ;;
    esac
}

# Status indicator dot with color
# Usage: status_dot "working" → "● " (green)
status_dot() {
    local status="$1"
    case "$status" in
        working|active)     echo -e "${CR_GREEN}●${CR_RESET}" ;;
        idle|waiting)       echo -e "${CR_YELLOW}●${CR_RESET}" ;;
        blocked|error)      echo -e "${CR_RED}●${CR_RESET}" ;;
        rate-limited)       echo -e "${CR_ORANGE}●${CR_RESET}" ;;
        suspended)          echo -e "${CR_PURPLE}●${CR_RESET}" ;;
        done|completed)     echo -e "${CR_GRAY}●${CR_RESET}" ;;
        review)             echo -e "${CR_CYAN}●${CR_RESET}" ;;
        *)                  echo -e "${CR_WHITE}●${CR_RESET}" ;;
    esac
}

# Draw a header line with title
# Usage: draw_header "FORGE COCKPIT" 40
draw_header() {
    local title="$1"
    local width="${2:-$(get_term_width)}"
    local title_len=${#title}
    local pad=$(( (width - title_len - 2) / 2 ))

    printf "%s" "${CR_CYAN}${CR_BOLD}"
    printf "%${pad}s" "" | tr ' ' "$BOX_H"
    printf " %s " "$title"
    printf "%$(( width - title_len - pad - 2 ))s" "" | tr ' ' "$BOX_H"
    printf "%s\n" "${CR_RESET}"
}

# Draw a horizontal separator
# Usage: draw_separator 40
draw_separator() {
    local width="${1:-$(get_term_width)}"
    printf "%s" "${CR_DIM}"
    printf "%${width}s" "" | tr ' ' "$BOX_H"
    printf "%s\n" "${CR_RESET}"
}

# Format elapsed time from seconds
# Usage: format_elapsed 2700 → "45m"
format_elapsed() {
    local seconds="$1"
    if [[ $seconds -lt 60 ]]; then
        echo "${seconds}s"
    elif [[ $seconds -lt 3600 ]]; then
        echo "$(( seconds / 60 ))m"
    else
        local h=$(( seconds / 3600 ))
        local m=$(( (seconds % 3600) / 60 ))
        echo "${h}h ${m}m"
    fi
}

# Portable ISO date to epoch (works on both macOS and Linux)
iso_to_epoch() {
    local iso_date="$1"
    if [[ -z "$iso_date" || "$iso_date" == "null" ]]; then
        echo "0"
        return
    fi
    date -d "$iso_date" +%s 2>/dev/null \
        || TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%SZ" "$iso_date" +%s 2>/dev/null \
        || TZ=UTC date -j -f "%Y-%m-%dT%T%z" "$iso_date" +%s 2>/dev/null \
        || python3 -c "from datetime import datetime; print(int(datetime.fromisoformat('${iso_date}'.replace('Z','+00:00')).timestamp()))" 2>/dev/null \
        || echo "0"
}
