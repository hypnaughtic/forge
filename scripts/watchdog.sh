#!/usr/bin/env bash
# ==============================================================================
# Forge — Watchdog Script
# ==============================================================================
# Background daemon that monitors agent health, detects dead/stale agents,
# monitors for usage limits, and notifies the Team Leader of issues.
# Runs in its own tmux window.
set -euo pipefail

FORGE_DIR=""
SESSION_NAME=""
POLL_INTERVAL=60  # seconds

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Watchdog]${NC} $(date '+%H:%M:%S') $*"; }
log_warn()  { echo -e "${YELLOW}[Watchdog]${NC} $(date '+%H:%M:%S') $*"; }
log_error() { echo -e "${RED}[Watchdog]${NC} $(date '+%H:%M:%S') $*"; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/watchdog.sh --forge-dir <path> --session <name>"
    echo ""
    echo "Background daemon for agent health monitoring."
    echo "Checks every 60 seconds for:"
    echo "  - Dead agents (tmux window gone)"
    echo "  - Stale agents (status not updated >5 min)"
    echo "  - Error spikes in logs"
    echo "  - Usage limit detection"
    echo "  - Auto-stop after configured hours"
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --forge-dir)  FORGE_DIR="$2"; shift 2 ;;
        --session)    SESSION_NAME="$2"; shift 2 ;;
        *)            shift ;;
    esac
done

FORGE_DIR="${FORGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SHARED_DIR="${FORGE_DIR}/shared"
STATUS_DIR="${SHARED_DIR}/.status"
LOGS_DIR="${SHARED_DIR}/.logs"
CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"

# Auto-detect session
if [[ -z "$SESSION_NAME" ]]; then
    SESSION_NAME=$(tmux list-sessions 2>/dev/null | grep "^forge-" | head -1 | cut -d: -f1 || true)
fi

# Read config
AUTO_STOP_HOURS=0
FLEET_LIMIT_THRESHOLD=3
REFRESH_WINDOW_HOURS=1
AUTO_RESUME_AFTER_LIMIT=true

if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    AUTO_STOP_HOURS=$(yq eval '.session.auto_stop_after_hours // 0' "$CONFIG_FILE" 2>/dev/null || echo 0)
    FLEET_LIMIT_THRESHOLD=$(yq eval '.usage_limits.fleet_limit_threshold // 3' "$CONFIG_FILE" 2>/dev/null || echo 3)
    REFRESH_WINDOW_HOURS=$(yq eval '.usage_limits.estimated_refresh_window_hours // 1' "$CONFIG_FILE" 2>/dev/null || echo 1)
    AUTO_RESUME_AFTER_LIMIT=$(yq eval '.usage_limits.auto_resume_after_limit // true' "$CONFIG_FILE" 2>/dev/null || echo true)
fi

SESSION_START=$(date +%s)
RATE_LIMITED_AGENTS=()

send_to_team_leader() {
    local priority="$1"
    local subject="$2"
    local body="$3"

    local inbox="${SHARED_DIR}/.queue/team-leader-inbox"
    mkdir -p "$inbox"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local unix_ts
    unix_ts=$(date +%s)
    local temp_file
    temp_file=$(mktemp /tmp/forge-msg-XXXXXX.md)

    cat > "$temp_file" <<EOF
---
id: msg-${unix_ts}-watchdog
from: watchdog
to: team-leader
priority: ${priority}
timestamp: ${timestamp}
type: status-update
---

## ${subject}

${body}
EOF

    mv "$temp_file" "${inbox}/msg-${unix_ts}-watchdog.md"
}

log_info "Watchdog started. Monitoring every ${POLL_INTERVAL}s."
log_info "Auto-stop after: ${AUTO_STOP_HOURS}h (0=disabled)"
log_info "Fleet limit threshold: ${FLEET_LIMIT_THRESHOLD}"

# --- Main monitoring loop ---
while true; do
    sleep "$POLL_INTERVAL"

    [[ -d "$STATUS_DIR" ]] || continue

    CURRENT_TIME=$(date +%s)

    # Get tmux windows
    TMUX_WINDOWS=""
    if [[ -n "$SESSION_NAME" ]]; then
        TMUX_WINDOWS=$(tmux list-windows -t "$SESSION_NAME" 2>/dev/null | awk '{print $2}' | tr -d '*-' || true)
    fi

    RATE_LIMITED_COUNT=0

    for status_file in "${STATUS_DIR}"/*.json; do
        [[ -f "$status_file" ]] || continue

        agent_name=$(basename "$status_file" .json)

        # Skip system agents
        [[ "$agent_name" == "watchdog" || "$agent_name" == "log-aggregator" ]] && continue

        # Parse status
        if command -v jq &>/dev/null; then
            status=$(jq -r '.status // "unknown"' "$status_file" 2>/dev/null)
            last_updated=$(jq -r '.last_updated // ""' "$status_file" 2>/dev/null)
            limit_status=$(jq -r '.usage_limits.status // "normal"' "$status_file" 2>/dev/null)
        else
            status=$(grep -o '"status": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "unknown")
            last_updated=$(grep -o '"last_updated": *"[^"]*"' "$status_file" | head -1 | cut -d'"' -f4 || echo "")
            limit_status="unknown"
        fi

        # Skip terminated agents
        [[ "$status" == "terminated" ]] && continue

        # --- Check 1: Dead agent (tmux window gone) ---
        if [[ -n "$SESSION_NAME" ]] && [[ "$status" != "terminated" && "$status" != "suspended" ]]; then
            if ! echo "$TMUX_WINDOWS" | grep -q "^${agent_name}$"; then
                # Check if it's a limit-related death
                local_log="${LOGS_DIR}/${agent_name}.log"
                if [[ -f "$local_log" ]] && tail -5 "$local_log" 2>/dev/null | grep -qi "rate.limit\|429\|usage.limit\|too.many.requests"; then
                    log_error "CRITICAL (LIMIT): ${agent_name} - session killed by usage limit"
                    send_to_team_leader "critical" "LIMIT_DETECTED: ${agent_name}" \
                        "Agent ${agent_name} appears to have been killed by a usage limit. Its tmux window is gone and logs show rate limit errors. Do NOT respawn immediately. Wait for limit refresh (estimated: ${REFRESH_WINDOW_HOURS}h)."
                    RATE_LIMITED_COUNT=$((RATE_LIMITED_COUNT + 1))
                else
                    log_error "CRITICAL: ${agent_name} - tmux window DEAD"
                    send_to_team_leader "critical" "AGENT_DEAD: ${agent_name}" \
                        "Agent ${agent_name} has died (tmux window not found). Working memory should be at shared/.memory/${agent_name}-memory.md. Consider respawning with --resume."
                fi
                continue
            fi
        fi

        # --- Check 2: Stale agent ---
        if [[ -n "$last_updated" && "$status" != "suspended" && "$status" != "rate-limited" ]]; then
            updated_epoch=$(date -d "$last_updated" +%s 2>/dev/null || echo "0")
            age=$((CURRENT_TIME - updated_epoch))

            if [[ $age -gt 900 ]]; then  # >15 minutes
                log_error "CRITICAL: ${agent_name} - status stale for ${age}s (>15min)"
                send_to_team_leader "critical" "AGENT_STALE_CRITICAL: ${agent_name}" \
                    "Agent ${agent_name} has not updated its status for ${age} seconds (>15 min). May need restart."
            elif [[ $age -gt 300 ]]; then  # >5 minutes
                log_warn "WARNING: ${agent_name} - status stale for ${age}s (>5min)"
                send_to_team_leader "normal" "AGENT_STALE_WARNING: ${agent_name}" \
                    "Agent ${agent_name} has not updated its status for ${age} seconds. May be stuck."
            fi
        fi

        # --- Check 3: Rate-limited agents ---
        if [[ "$limit_status" == "rate-limited" || "$status" == "rate-limited" ]]; then
            RATE_LIMITED_COUNT=$((RATE_LIMITED_COUNT + 1))
            log_warn "Rate-limited: ${agent_name}"
        fi

        # --- Check 4: Error status ---
        if [[ "$status" == "error" ]]; then
            log_error "CRITICAL: ${agent_name} - explicit error status"
            send_to_team_leader "critical" "AGENT_ERROR: ${agent_name}" \
                "Agent ${agent_name} has status 'error'. Check its working memory and logs."
        fi

        # --- Check 5: Error spike in logs ---
        if [[ -f "${LOGS_DIR}/${agent_name}.log" ]]; then
            recent_errors=$(tail -50 "${LOGS_DIR}/${agent_name}.log" 2>/dev/null | grep -c '"level": *"ERROR"' || echo "0")
            if [[ $recent_errors -gt 5 ]]; then
                log_warn "WARNING: ${agent_name} - ${recent_errors} errors in recent logs"
                send_to_team_leader "high" "ERROR_SPIKE: ${agent_name}" \
                    "Agent ${agent_name} has ${recent_errors} ERROR entries in recent logs. May be having issues."
            fi
        fi
    done

    # --- Fleet-wide limit check ---
    if [[ $RATE_LIMITED_COUNT -ge $FLEET_LIMIT_THRESHOLD ]]; then
        log_error "FLEET LIMIT THRESHOLD REACHED: ${RATE_LIMITED_COUNT} agents rate-limited"
        send_to_team_leader "critical" "FLEET_LIMIT_THRESHOLD" \
            "${RATE_LIMITED_COUNT} agents are rate-limited (threshold: ${FLEET_LIMIT_THRESHOLD}). Consider executing full fleet stop to preserve state."
    fi

    # --- Auto-stop check ---
    if [[ $AUTO_STOP_HOURS -gt 0 ]]; then
        elapsed=$(( (CURRENT_TIME - SESSION_START) / 3600 ))
        if [[ $elapsed -ge $AUTO_STOP_HOURS ]]; then
            log_warn "Auto-stop triggered after ${elapsed}h (cap: ${AUTO_STOP_HOURS}h)"
            send_to_team_leader "critical" "AUTO_STOP" \
                "Fleet has been running for ${elapsed} hours (auto_stop_after_hours: ${AUTO_STOP_HOURS}). Triggering graceful shutdown."
            bash "${FORGE_DIR}/scripts/stop.sh" 2>/dev/null || true
            exit 0
        fi
    fi

    # --- Rate limit refresh check (every cycle for rate-limited agents) ---
    if [[ "$AUTO_RESUME_AFTER_LIMIT" == "true" ]]; then
        for status_file in "${STATUS_DIR}"/*.json; do
            [[ -f "$status_file" ]] || continue
            agent_name=$(basename "$status_file" .json)

            if command -v jq &>/dev/null; then
                limit_status=$(jq -r '.usage_limits.status // "normal"' "$status_file" 2>/dev/null)
                last_warning=$(jq -r '.usage_limits.last_warning_at // ""' "$status_file" 2>/dev/null)
            else
                continue
            fi

            if [[ "$limit_status" == "rate-limited" && -n "$last_warning" && "$last_warning" != "null" ]]; then
                warning_epoch=$(date -d "$last_warning" +%s 2>/dev/null || echo "0")
                refresh_seconds=$((REFRESH_WINDOW_HOURS * 3600))
                if [[ $((CURRENT_TIME - warning_epoch)) -gt $refresh_seconds ]]; then
                    log_info "Limit refresh likely for ${agent_name} (>${REFRESH_WINDOW_HOURS}h since limit)"
                    send_to_team_leader "high" "LIMIT_REFRESH_LIKELY: ${agent_name}" \
                        "Agent ${agent_name} was rate-limited ${REFRESH_WINDOW_HOURS}+ hours ago. Limits may have refreshed. Consider respawning with --resume."
                fi
            fi
        done
    fi
done
