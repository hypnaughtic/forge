#!/usr/bin/env bash
# ==============================================================================
# Forge — Cost Tracker Script
# ==============================================================================
# Reads structured logs and status files to estimate token usage and costs
# per agent and total. Alerts if approaching the configured cost cap.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHARED_DIR="${FORGE_DIR}/shared"
LOGS_DIR="${SHARED_DIR}/.logs"
STATUS_DIR="${SHARED_DIR}/.status"
CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"
COST_SUMMARY="${LOGS_DIR}/cost-summary.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: scripts/cost-tracker.sh [--report] [--json]"
    echo ""
    echo "Tracks and reports estimated token usage and costs."
    echo ""
    echo "Options:"
    echo "  --report    Print a formatted cost report"
    echo "  --json      Output raw JSON summary"
    exit 0
fi

REPORT_MODE=false
JSON_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --report) REPORT_MODE=true; shift ;;
        --json)   JSON_MODE=true; shift ;;
        *)        shift ;;
    esac
done

# Read cost cap from config
COST_CAP="no-cap"
if command -v yq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    COST_CAP=$(yq eval '.cost.max_development_cost // "no-cap"' "$CONFIG_FILE" 2>/dev/null || echo "no-cap")
fi

# Collect cost data from status files
TOTAL_COST=0
AGENT_COSTS=""

if [[ -d "$STATUS_DIR" ]]; then
    for status_file in "${STATUS_DIR}"/*.json; do
        [[ -f "$status_file" ]] || continue

        agent_name=$(basename "$status_file" .json)
        agent_cost=0

        if command -v jq &>/dev/null; then
            agent_cost=$(jq -r '.cost_estimate_usd // 0' "$status_file" 2>/dev/null || echo "0")
        else
            agent_cost=$(grep -o '"cost_estimate_usd": *[0-9.]*' "$status_file" | head -1 | awk '{print $2}' || echo "0")
        fi

        # Handle non-numeric values
        if ! [[ "$agent_cost" =~ ^[0-9.]+$ ]]; then
            agent_cost=0
        fi

        TOTAL_COST=$(echo "$TOTAL_COST + $agent_cost" | bc 2>/dev/null || echo "$TOTAL_COST")
        AGENT_COSTS="${AGENT_COSTS}\"${agent_name}\": ${agent_cost}, "
    done
fi

# Also check logs for cost entries
if [[ -d "$LOGS_DIR" ]]; then
    for log_file in "${LOGS_DIR}"/*.log; do
        [[ -f "$log_file" ]] || continue
        [[ "$log_file" == *"combined.log" || "$log_file" == *"-session.log" ]] && continue

        if command -v jq &>/dev/null; then
            log_cost=$(grep '"category": *"cost"' "$log_file" 2>/dev/null | \
                       jq -r '.estimated_cost_usd // 0' 2>/dev/null | \
                       awk '{sum += $1} END {print sum+0}' || echo "0")
            if [[ -n "$log_cost" && "$log_cost" != "0" ]]; then
                TOTAL_COST=$(echo "$TOTAL_COST + $log_cost" | bc 2>/dev/null || echo "$TOTAL_COST")
            fi
        fi
    done
fi

# Remove trailing comma from agent costs
AGENT_COSTS="${AGENT_COSTS%, }"

# Write summary JSON
cat > "$COST_SUMMARY" <<EOF
{
  "total_cost_usd": ${TOTAL_COST},
  "cost_cap_usd": "${COST_CAP}",
  "per_agent": { ${AGENT_COSTS} },
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Check cost cap
if [[ "$COST_CAP" != "no-cap" && "$COST_CAP" != "0" ]]; then
    # Compare using bc
    if command -v bc &>/dev/null; then
        OVER_CAP=$(echo "$TOTAL_COST > $COST_CAP" | bc 2>/dev/null || echo "0")
        NEAR_CAP=$(echo "$TOTAL_COST > ($COST_CAP * 0.8)" | bc 2>/dev/null || echo "0")

        if [[ "$OVER_CAP" == "1" ]]; then
            echo -e "${RED}[Cost] WARNING: Over budget! \$${TOTAL_COST} / \$${COST_CAP}${NC}" >&2
        elif [[ "$NEAR_CAP" == "1" ]]; then
            echo -e "${YELLOW}[Cost] Approaching budget: \$${TOTAL_COST} / \$${COST_CAP}${NC}" >&2
        fi
    fi
fi

# Output
if $JSON_MODE; then
    cat "$COST_SUMMARY"
elif $REPORT_MODE; then
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  Forge Cost Report${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Total Cost:${NC}  \$${TOTAL_COST}"
    echo -e "  ${CYAN}Budget Cap:${NC}  \$${COST_CAP}"
    echo ""

    if [[ -n "$AGENT_COSTS" ]]; then
        echo -e "  ${CYAN}Per Agent:${NC}"
        # Parse and display agent costs
        if [[ -d "$STATUS_DIR" ]]; then
            printf "    %-30s %s\n" "Agent" "Cost (USD)"
            printf "    %-30s %s\n" "─────" "──────────"
            for status_file in "${STATUS_DIR}"/*.json; do
                [[ -f "$status_file" ]] || continue
                agent_name=$(basename "$status_file" .json)
                agent_cost=0
                if command -v jq &>/dev/null; then
                    agent_cost=$(jq -r '.cost_estimate_usd // 0' "$status_file" 2>/dev/null || echo "0")
                fi
                printf "    %-30s \$%s\n" "$agent_name" "$agent_cost"
            done
        fi
    fi
    echo ""
fi
