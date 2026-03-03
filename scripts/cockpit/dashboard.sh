#!/usr/bin/env bash
# ==============================================================================
# Forge Cockpit — Dashboard Launcher
# ==============================================================================
# Creates a tmux layout with 4 zones:
#   Top-left:  Metrics panel (auto-refresh every 3s)
#   Top-right: Agent status grid (auto-refresh every 2s)
#   Middle:    Activity feed (auto-refresh every 5s)
#   Bottom:    Interactive Claude session (user control)
#
# Usage: scripts/cockpit/dashboard.sh [--project-dir <path>] [--permission-flags <flags>]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORGE_DIR="${FORGE_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export FORGE_DIR

# Parse arguments
PROJECT_DIR=""
PERMISSION_FLAGS=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir)    PROJECT_DIR="$2"; shift 2 ;;
        --permission-flags) PERMISSION_FLAGS="$2"; shift 2 ;;
        *)                shift ;;
    esac
done

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
SESSION_NAME="forge-cockpit-$$"

# Detect terminal size for layout calculations
TERM_COLS=$(tput cols 2>/dev/null || echo 120)
TERM_LINES=$(tput lines 2>/dev/null || echo 40)

# Calculate pane sizes
# Top row: ~35% height, split 60/40 horizontally
# Middle: ~30% height
# Bottom: ~35% height (Claude session)
TOP_HEIGHT=$(( TERM_LINES * 35 / 100 ))
MID_HEIGHT=$(( TERM_LINES * 30 / 100 ))
LEFT_WIDTH=$(( TERM_COLS * 60 / 100 ))

# Create tmux session with the cockpit layout
tmux new-session -d -s "$SESSION_NAME" -x "$TERM_COLS" -y "$TERM_LINES"

# Bottom pane (pane 0): Claude interactive session
# We'll move Claude to the bottom after creating other panes

# Top-left pane: Metrics panel with auto-refresh
tmux send-keys -t "${SESSION_NAME}" \
    "cd '${PROJECT_DIR}' && watch --color -n 3 'FORGE_DIR=\"${FORGE_DIR}\" bash \"${SCRIPT_DIR}/metrics-panel.sh\"'" C-m

# Split horizontally: top-right pane for agent grid
tmux split-window -h -t "${SESSION_NAME}" -p $(( 100 - LEFT_WIDTH * 100 / TERM_COLS ))
tmux send-keys -t "${SESSION_NAME}" \
    "cd '${PROJECT_DIR}' && watch --color -n 2 'FORGE_DIR=\"${FORGE_DIR}\" bash \"${SCRIPT_DIR}/agent-grid.sh\"'" C-m

# Split the left pane vertically: middle pane for activity feed
tmux select-pane -t "${SESSION_NAME}.0"
tmux split-window -v -t "${SESSION_NAME}" -p $(( 100 - TOP_HEIGHT * 100 / TERM_LINES ))
tmux send-keys -t "${SESSION_NAME}" \
    "cd '${PROJECT_DIR}' && watch --color -n 5 'FORGE_DIR=\"${FORGE_DIR}\" bash \"${SCRIPT_DIR}/activity-feed.sh\"'" C-m

# Split activity pane: bottom pane for Claude session
tmux split-window -v -t "${SESSION_NAME}" -p $(( 100 - MID_HEIGHT * 100 / (TERM_LINES - TOP_HEIGHT) ))

# Launch Claude in the bottom pane
# shellcheck disable=SC2086
tmux send-keys -t "${SESSION_NAME}" \
    "cd '${PROJECT_DIR}' && claude ${PERMISSION_FLAGS}" C-m

# Select the Claude pane (bottom) as the active pane
tmux select-pane -t "${SESSION_NAME}" -D

# Attach to the session
exec tmux attach-session -t "$SESSION_NAME"
