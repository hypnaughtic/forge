#!/usr/bin/env bash
# ==============================================================================
# Forge — Log Aggregator Script
# ==============================================================================
# Background daemon that tails all agent log files and produces a combined,
# chronologically ordered log. Handles log rotation when files exceed 10MB.
set -euo pipefail

FORGE_DIR=""
MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB in bytes
POLL_INTERVAL=5  # seconds

GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[LogAgg]${NC} $(date '+%H:%M:%S') $*"; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/log-aggregator.sh --forge-dir <path>"
    echo ""
    echo "Background daemon that:"
    echo "  - Tails all agent log files in shared/.logs/"
    echo "  - Produces combined chronological log at shared/.logs/combined.log"
    echo "  - Rotates logs when they exceed 10MB"
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --forge-dir) FORGE_DIR="$2"; shift 2 ;;
        *)           shift ;;
    esac
done

FORGE_DIR="${FORGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOGS_DIR="${FORGE_DIR}/shared/.logs"
ARCHIVE_DIR="${LOGS_DIR}/archive"
COMBINED_LOG="${LOGS_DIR}/combined.log"

mkdir -p "$LOGS_DIR" "$ARCHIVE_DIR"
touch "$COMBINED_LOG"

log_info "Log aggregator started. Watching: ${LOGS_DIR}"

rotate_log() {
    local log_file="$1"
    local basename_file
    basename_file=$(basename "$log_file")
    local timestamp
    timestamp=$(date +%s)
    local archive_name="${ARCHIVE_DIR}/${basename_file%.log}-${timestamp}.log"

    log_info "Rotating ${basename_file} (>10MB) → ${archive_name}"
    mv "$log_file" "$archive_name"
    touch "$log_file"

    # Compress archived log
    if command -v gzip &>/dev/null; then
        gzip "$archive_name" 2>/dev/null &
    fi
}

# Track file positions for incremental reading
declare -A FILE_POSITIONS

while true; do
    NEW_ENTRIES=false

    for log_file in "${LOGS_DIR}"/*.log; do
        [[ -f "$log_file" ]] || continue
        [[ "$log_file" == "$COMBINED_LOG" ]] && continue
        [[ "$log_file" == *"-session.log" ]] && continue

        # Check for rotation
        file_size=$(stat -c%s "$log_file" 2>/dev/null || stat -f%z "$log_file" 2>/dev/null || echo "0")
        if [[ $file_size -gt $MAX_LOG_SIZE ]]; then
            rotate_log "$log_file"
            unset "FILE_POSITIONS[$log_file]"
            continue
        fi

        # Read new lines since last position
        current_lines=$(wc -l < "$log_file" 2>/dev/null || echo "0")
        last_pos="${FILE_POSITIONS[$log_file]:-0}"

        if [[ $current_lines -gt $last_pos ]]; then
            # Append new lines to combined log
            tail -n "+$((last_pos + 1))" "$log_file" >> "$COMBINED_LOG"
            FILE_POSITIONS[$log_file]=$current_lines
            NEW_ENTRIES=true
        fi
    done

    # Rotate combined log if needed
    if [[ -f "$COMBINED_LOG" ]]; then
        combined_size=$(stat -c%s "$COMBINED_LOG" 2>/dev/null || stat -f%z "$COMBINED_LOG" 2>/dev/null || echo "0")
        if [[ $combined_size -gt $MAX_LOG_SIZE ]]; then
            rotate_log "$COMBINED_LOG"
        fi
    fi

    sleep "$POLL_INTERVAL"
done
