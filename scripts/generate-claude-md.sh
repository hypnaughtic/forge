#!/usr/bin/env bash
# ==============================================================================
# Forge — Generate CLAUDE.md for Project Directory
# ==============================================================================
# Assembles a composite CLAUDE.md that gives the Team Leader full context
# when running as an interactive Claude Code session.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"
SHARED_DIR="${FORGE_DIR}/shared"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Forge]${NC} $*"; }
log_error() { echo -e "${RED}[Forge]${NC} $*" >&2; }

PROJECT_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir) PROJECT_DIR="$2"; shift 2 ;;
        --config)      CONFIG_FILE="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: scripts/generate-claude-md.sh --project-dir <path>"
            echo "  Generates a CLAUDE.md in the project directory for the Team Leader."
            exit 0
            ;;
        *) shift ;;
    esac
done

if [[ -z "$PROJECT_DIR" ]]; then
    log_error "Missing --project-dir argument"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "Config file not found: $CONFIG_FILE"
    exit 1
fi

if ! command -v yq &>/dev/null; then
    log_error "yq is required. Install: brew install yq"
    exit 1
fi

# --- Read configuration ---
PROJECT_NAME=$(yq eval '.project.description // "Forge Project"' "$CONFIG_FILE")
MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE")
STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE")
ORCHESTRATION=$(yq eval '.orchestration // "agent-teams"' "$CONFIG_FILE")
COST_CAP=$(yq eval '.cost.max_development_cost // "no-cap"' "$CONFIG_FILE")
TEAM_PROFILE=$(yq eval '.agents.team_profile // "auto"' "$CONFIG_FILE")

# Read tech stack
TECH_LANGS=$(yq eval '.tech_stack.languages | join(", ")' "$CONFIG_FILE" 2>/dev/null || echo "")
TECH_FRAMEWORKS=$(yq eval '.tech_stack.frameworks | join(", ")' "$CONFIG_FILE" 2>/dev/null || echo "")

# Read requirements
REQ_FILE=$(yq eval '.project.requirements_file // ""' "$CONFIG_FILE")
REQUIREMENTS=""
if [[ -n "$REQ_FILE" && -f "${FORGE_DIR}/${REQ_FILE}" ]]; then
    REQUIREMENTS=$(cat "${FORGE_DIR}/${REQ_FILE}")
elif [[ -n "$PROJECT_NAME" ]]; then
    REQUIREMENTS="$PROJECT_NAME"
fi

# --- Resolve team profile ---
RESOLVED_PROFILE="$TEAM_PROFILE"
if [[ "$TEAM_PROFILE" == "auto" ]]; then
    case "$MODE" in
        mvp)              RESOLVED_PROFILE="lean" ;;
        production-ready) RESOLVED_PROFILE="full" ;;
        no-compromise)    RESOLVED_PROFILE="full" ;;
        *)                RESOLVED_PROFILE="lean" ;;
    esac
fi

# Define agent rosters
LEAN_AGENTS="team-leader research-strategist architect backend-developer frontend-engineer qa-engineer devops-specialist critic"
FULL_AGENTS="team-leader researcher strategist architect backend-developer frontend-designer frontend-developer qa-engineer devops-specialist security-tester performance-engineer documentation-specialist critic"

case "$RESOLVED_PROFILE" in
    lean) ACTIVE_AGENTS="$LEAN_AGENTS" ;;
    full) ACTIVE_AGENTS="$FULL_AGENTS" ;;
    custom)
        ACTIVE_AGENTS=$(yq eval '.agents.include | join(" ")' "$CONFIG_FILE" 2>/dev/null || echo "$LEAN_AGENTS")
        ;;
    *) ACTIVE_AGENTS="$LEAN_AGENTS" ;;
esac

# Apply exclude/additional
EXCLUDE=$(yq eval '.agents.exclude | join(" ")' "$CONFIG_FILE" 2>/dev/null || echo "")
for agent in $EXCLUDE; do
    ACTIVE_AGENTS=$(echo "$ACTIVE_AGENTS" | sed "s/\b${agent}\b//g" | tr -s ' ')
done
ADDITIONAL=$(yq eval '.agents.additional | join(" ")' "$CONFIG_FILE" 2>/dev/null || echo "")
for agent in $ADDITIONAL; do
    echo "$ACTIVE_AGENTS" | grep -qw "$agent" || ACTIVE_AGENTS="$ACTIVE_AGENTS $agent"
done
ACTIVE_AGENTS=$(echo "$ACTIVE_AGENTS" | xargs)

# --- Build orchestration instructions ---
ORCH_INSTRUCTIONS=""
if [[ "$ORCHESTRATION" == "agent-teams" ]]; then
    ORCH_INSTRUCTIONS="### Agent Teams Mode (Active)
- Spawn agents as Agent Teams subagents using the Agent tool with their instruction files as context
- Use Agent Teams task management for work assignments
- Use Agent Teams messaging for inter-agent communication
- Monitor teammate status via Agent Teams native tracking
- File locking is handled natively by Agent Teams
- To spawn an agent: use the Agent tool with the agent's instruction file from \`${FORGE_DIR}/agents/{type}.md\`
- For tmux-dependent scripts (watchdog, log-aggregator), these run as background processes only if needed"
else
    ORCH_INSTRUCTIONS="### tmux Mode (Active)
- Spawn agents via: \`bash ${FORGE_DIR}/scripts/spawn-agent.sh --agent-type {type} --mode ${MODE} --strategy ${STRATEGY}\`
- Send messages via file queue: \`shared/.queue/{agent}-inbox/\`
- Monitor status via: \`shared/.status/{agent}.json\`
- Use file locks: \`shared/.locks/\`
- Run watchdog: it monitors agent health in background
- Broadcast to all agents: \`bash ${FORGE_DIR}/scripts/broadcast.sh --type {type} --message {msg}\`
- Kill agents: \`bash ${FORGE_DIR}/scripts/kill-agent.sh --agent {name}\`"
fi

# --- Check for snapshot / resume context ---
RESUME_SECTION=""
if [[ -d "${SHARED_DIR}/.snapshots" ]]; then
    LATEST_SNAPSHOT=$(ls -t "${SHARED_DIR}/.snapshots"/snapshot-*.json 2>/dev/null | head -1 || true)
    if [[ -n "$LATEST_SNAPSHOT" ]] && command -v jq &>/dev/null; then
        SNAP_TIME=$(jq -r '.timestamp // "unknown"' "$LATEST_SNAPSHOT" 2>/dev/null || echo "unknown")
        SNAP_ITER=$(jq -r '.iteration.current // "?"' "$LATEST_SNAPSHOT" 2>/dev/null || echo "?")
        SNAP_PHASE=$(jq -r '.iteration.phase // "?"' "$LATEST_SNAPSHOT" 2>/dev/null || echo "?")
        SNAP_AGENTS=$(jq -r '.agents | length // 0' "$LATEST_SNAPSHOT" 2>/dev/null || echo "0")
        SNAP_COST=$(jq -r '.costs.total_development_cost_usd // 0' "$LATEST_SNAPSHOT" 2>/dev/null || echo "0")

        RESUME_SECTION="## Resume Context (Previous Session Found)
A previous session snapshot exists from ${SNAP_TIME}.
- Iteration: ${SNAP_ITER} (phase: ${SNAP_PHASE})
- Agents: ${SNAP_AGENTS} were active
- Cost so far: \$${SNAP_COST}
- Snapshot path: ${LATEST_SNAPSHOT}

When starting, offer to resume from this snapshot. If resuming:
1. Read \`shared/.memory/team-leader-memory.md\` for your previous state
2. Restore agents from the snapshot roster
3. Continue from the last known phase"
    fi
fi

# --- Resolve user's CLAUDE.md conventions ---
CLAUDE_MD_SOURCE=$(yq eval '.claude_md.source // "both"' "$CONFIG_FILE")
CLAUDE_MD_PRIORITY=$(yq eval '.claude_md.priority // "project-first"' "$CONFIG_FILE")
GLOBAL_CLAUDE_PATH=$(yq eval '.claude_md.global_path // ""' "$CONFIG_FILE")
USER_CONVENTIONS=""

if [[ "$CLAUDE_MD_SOURCE" != "none" ]]; then
    local_global="${GLOBAL_CLAUDE_PATH:-$HOME/.claude/CLAUDE.md}"
    local_project="${PROJECT_DIR}/CLAUDE.md"

    # Back up existing project CLAUDE.md before we overwrite it
    if [[ -f "$local_project" ]]; then
        cp "$local_project" "${PROJECT_DIR}/.claude-md-user-backup.md" 2>/dev/null || true
        user_project_md=$(cat "${PROJECT_DIR}/.claude-md-user-backup.md" 2>/dev/null || true)
    fi

    global_md=""
    if [[ -f "$local_global" ]]; then
        global_md=$(cat "$local_global" 2>/dev/null || true)
    fi

    case "$CLAUDE_MD_SOURCE" in
        global)
            [[ -n "$global_md" ]] && USER_CONVENTIONS="$global_md"
            ;;
        project)
            [[ -n "${user_project_md:-}" ]] && USER_CONVENTIONS="${user_project_md}"
            ;;
        both)
            if [[ -n "${user_project_md:-}" && -n "$global_md" ]]; then
                if [[ "$CLAUDE_MD_PRIORITY" == "project-first" ]]; then
                    USER_CONVENTIONS="${user_project_md}

---
${global_md}"
                else
                    USER_CONVENTIONS="${global_md}

---
${user_project_md}"
                fi
            elif [[ -n "${user_project_md:-}" ]]; then
                USER_CONVENTIONS="${user_project_md}"
            elif [[ -n "$global_md" ]]; then
                USER_CONVENTIONS="$global_md"
            fi
            ;;
    esac
fi

# --- Build agent roster section ---
AGENT_ROSTER=""
for agent in $ACTIVE_AGENTS; do
    if [[ "$agent" == "team-leader" ]]; then
        continue  # That's you
    fi
    # Prefer generated agent files (with project context) over templates
    if [[ -f "${PROJECT_DIR}/.forge/agents/${agent}.md" ]]; then
        AGENT_ROSTER="${AGENT_ROSTER}
- **${agent}**: \`${PROJECT_DIR}/.forge/agents/${agent}.md\`"
    else
        AGENT_ROSTER="${AGENT_ROSTER}
- **${agent}**: \`${FORGE_DIR}/agents/${agent}.md\`"
    fi
done

# --- Write CLAUDE.md ---
mkdir -p "$PROJECT_DIR"

cat > "${PROJECT_DIR}/CLAUDE.md" <<CLAUDEMD
# Forge — Team Leader Context

> This file is auto-generated by Forge. Do not edit manually.
> Regenerate with: \`bash ${FORGE_DIR}/scripts/generate-claude-md.sh --project-dir ${PROJECT_DIR}\`

## Project Configuration
- **Project**: ${PROJECT_NAME}
- **Mode**: ${MODE} | **Strategy**: ${STRATEGY}
- **Orchestration**: ${ORCHESTRATION}
- **Cost cap**: \$${COST_CAP}
- **Team profile**: ${RESOLVED_PROFILE} (${ACTIVE_AGENTS// /, })
- **Tech stack**: ${TECH_LANGS:-(auto-detect)} | ${TECH_FRAMEWORKS:-(auto-detect)}

## Your Identity

You are the **Team Leader** of a Forge agent team. You ARE this interactive
Claude Code session. The user talks directly to you — there is no tmux attach
needed, you are already here.

When the user asks a question, answer directly. When they give a directive,
act on it. The \`/forge-*\` slash commands are available for structured operations.

**CRITICAL: Command Priority**
User commands and slash commands take ABSOLUTE priority. When the user types
anything, respond immediately. Do not wait for agent tasks to complete.
Agent work continues in the background.

## Available Slash Commands
- \`/forge-start\` — Begin building (spawn team, start Iteration 1)
- \`/forge-stop\` — Save all state, snapshot, gracefully end
- \`/forge-status\` — Show iteration, agents, tasks, cost
- \`/forge-cost\` — Detailed cost breakdown
- \`/forge-mode\` — Switch mode or strategy
- \`/forge-snapshot\` — Manual state save
- \`/forge-init\` — Interactive project configuration

## Orchestration Backend: ${ORCHESTRATION}

${ORCH_INSTRUCTIONS}

## Agent Roster

Available agents (spawn as needed via the orchestration backend):
${AGENT_ROSTER}

Base protocol for all agents: \`${FORGE_DIR}/agents/_base-agent.md\`

## Forge Directory

The Forge framework is installed at: \`${FORGE_DIR}\`

Key paths:
- Scripts: \`${FORGE_DIR}/scripts/\`
- Agent definitions: \`${FORGE_DIR}/agents/\`
- Config: \`${FORGE_DIR}/config/team-config.yaml\`
- Shared runtime: \`${FORGE_DIR}/shared/\`
- Slash commands: \`${FORGE_DIR}/.claude/commands/\`

## Project Requirements

${REQUIREMENTS}

## Team Leader Instructions

Refer to \`${FORGE_DIR}/agents/team-leader.md\` for your full instruction set,
including:
- Startup sequence and ongoing orchestration
- 7-phase iteration lifecycle (PLAN → EXECUTE → TEST → INTEGRATE → REVIEW → CRITIQUE → DECISION)
- Quality gates per mode (MVP: 70%, Production Ready: 90%, No Compromise: 100%)
- Smoke test protocol (mandatory for all modes)
- Natural language command handling
- Mode-specific behavior
- Confidence-based routing
- Parallel work streams
- Rollback protocol

Refer to \`${FORGE_DIR}/agents/_base-agent.md\` for the base protocol:
- Communication protocol, status reporting, working memory
- Git workflow, file contention, artifact registration
- Error handling, shutdown protocol, usage limit monitoring

${RESUME_SECTION}

CLAUDEMD

# Append user conventions if present
if [[ -n "$USER_CONVENTIONS" ]]; then
    cat >> "${PROJECT_DIR}/CLAUDE.md" <<CONVENTIONS
## User's CLAUDE.md Conventions

${USER_CONVENTIONS}
CONVENTIONS
fi

log_info "Generated CLAUDE.md at ${PROJECT_DIR}/CLAUDE.md"
