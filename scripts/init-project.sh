#!/usr/bin/env bash
# ==============================================================================
# Forge — Init Project Script
# ==============================================================================
# Reads config, resolves team profile, resolves CLAUDE.md sources, generates
# project-specific agent files, and bootstraps the project directory.
# Can also run as an interactive wizard with --wizard flag.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${FORGE_DIR}/config/team-config.yaml"
PROJECT_DIR=""
WIZARD_MODE=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Init]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[Init]${NC} $*"; }
log_error() { echo -e "${RED}[Init]${NC} $*" >&2; }

usage() {
    echo "Usage: scripts/init-project.sh [options]"
    echo ""
    echo "Options:"
    echo "  --config <path>       Path to team-config.yaml (default: config/team-config.yaml)"
    echo "  --project-dir <path>  Project directory (default: current directory)"
    echo "  --wizard              Run interactive setup wizard"
    echo "  --help                Show this help"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)       CONFIG_FILE="$2"; shift 2 ;;
        --project-dir)  PROJECT_DIR="$2"; shift 2 ;;
        --wizard)       WIZARD_MODE=true; shift ;;
        --help|-h)      usage ;;
        *)              shift ;;
    esac
done

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"

# ==============================================================================
# Interactive Wizard Mode
# ==============================================================================
if $WIZARD_MODE; then
    echo -e "${CYAN}"
    echo "  Forge — Project Setup Wizard"
    echo "  ============================="
    echo -e "${NC}"

    # 1. Project workspace directory
    local default_workspace="${HOME}/forge-projects"
    echo "Where should the project be created?"
    echo "  (This should be OUTSIDE the forge repo)"
    read -rp "Project workspace directory (default: ${default_workspace}/<project-name>): " workspace_dir

    # 2. Project description
    read -rp "Project description (short): " proj_desc
    proj_desc="${proj_desc:-My project}"

    # 2. Detailed requirements
    echo ""
    echo "Enter detailed project requirements (press Ctrl+D when done):"
    echo "(Or just press Ctrl+D to use the template)"
    proj_requirements=""
    proj_requirements=$(cat 2>/dev/null || true)
    if [[ -z "$proj_requirements" ]]; then
        proj_requirements="# Project Requirements\n\nDescribe your project in detail here."
    fi

    # 3. New or existing?
    echo ""
    read -rp "Is this a new or existing project? [new/existing] (default: new): " proj_type
    proj_type="${proj_type:-new}"
    existing_path=""
    if [[ "$proj_type" == "existing" ]]; then
        read -rp "Path to existing project: " existing_path
    fi

    # 4. Mode
    echo ""
    echo "Project modes:"
    echo "  1) mvp              — Working prototype, minimal tests"
    echo "  2) production-ready — CI/CD, >90% coverage, industrial standards"
    echo "  3) no-compromise    — Zero tolerance, IaC, single-click deploy"
    read -rp "Select mode [1/2/3] (default: 1): " mode_choice
    case "${mode_choice:-1}" in
        1) mode="mvp" ;;
        2) mode="production-ready" ;;
        3) mode="no-compromise" ;;
        *) mode="mvp" ;;
    esac

    # 5. Strategy
    echo ""
    echo "Execution strategies:"
    echo "  1) auto-pilot   — Zero human intervention"
    echo "  2) co-pilot     — Design approvals required"
    echo "  3) micro-manage — Every decision needs approval"
    read -rp "Select strategy [1/2/3] (default: 2): " strategy_choice
    case "${strategy_choice:-2}" in
        1) strategy="auto-pilot" ;;
        2) strategy="co-pilot" ;;
        3) strategy="micro-manage" ;;
        *) strategy="co-pilot" ;;
    esac

    # 6. Cost cap
    echo ""
    read -rp "Max development cost in USD (or 'no-cap') (default: 50): " cost_cap
    cost_cap="${cost_cap:-50}"

    # 7. Tech preferences
    echo ""
    read -rp "Preferred languages (comma-separated, or empty): " tech_langs
    read -rp "Preferred frameworks (comma-separated, or empty): " tech_frameworks
    read -rp "Preferred databases (comma-separated, or empty): " tech_dbs

    # 8. Template
    echo ""
    read -rp "Bootstrap template (auto/specific name/empty): " template
    template="${template:-auto}"

    # Format arrays
    fmt_array() {
        local input="$1"
        if [[ -z "$input" ]]; then
            echo "[]"
        else
            echo "[$(echo "$input" | sed 's/,/", "/g' | sed 's/^/"/' | sed 's/$/"/' )]"
        fi
    }

    # Resolve workspace directory
    if [[ -z "$workspace_dir" ]]; then
        # Generate from project description
        local proj_slug
        proj_slug=$(echo "$proj_desc" | head -c 30 | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g')
        proj_slug="${proj_slug:-my-project}"
        workspace_dir="${default_workspace}/${proj_slug}"
    fi
    # Resolve relative paths
    if [[ "$workspace_dir" != /* ]]; then
        workspace_dir="$(pwd)/${workspace_dir}"
    fi

    # Generate team-config.yaml
    log_info "Generating config/team-config.yaml..."
    log_info "Project workspace: ${workspace_dir}"

    cat > "${FORGE_DIR}/config/team-config.yaml" <<EOF
# ==============================================================================
# Forge — AI Software Forge — Project Configuration
# Generated by: ./forge init
# ==============================================================================

project:
  description: "${proj_desc}"
  requirements_file: "config/project-requirements.md"
  type: "${proj_type}"
  existing_project_path: "${existing_path}"
  directory: "${workspace_dir}"

mode: "${mode}"
strategy: "${strategy}"

cost:
  max_development_cost: ${cost_cap}
  max_project_runtime_cost: "no-cap"

agents:
  team_profile: "auto"
  exclude: []
  additional: []
  include: []

claude_md:
  source: "both"
  priority: "project-first"
  global_path: ""
  project_path: ""

tech_stack:
  languages: $(fmt_array "$tech_langs")
  frameworks: $(fmt_array "$tech_frameworks")
  databases: $(fmt_array "$tech_dbs")
  infrastructure: []

llm_gateway:
  local_claude_model: "claude-sonnet-4-20250514"
  enable_local_claude: true
  cost_tracking: true

bootstrap_template: "${template}"

session:
  snapshot_retention: 5
  auto_stop_after_hours: 0
  shutdown_grace_period_seconds: 60

usage_limits:
  proactive_save_interval_hours: 4
  estimated_refresh_window_hours: 1
  auto_resume_after_limit: true
  fleet_limit_threshold: 3
  scheduled_resume_time: ""
EOF

    # Generate project-requirements.md
    log_info "Generating config/project-requirements.md..."
    echo -e "$proj_requirements" > "${FORGE_DIR}/config/project-requirements.md"

    log_info "Configuration saved! Next: ./forge start"
    exit 0
fi

# ==============================================================================
# Non-wizard mode: Generate project-specific agent files
# ==============================================================================

if [[ ! -f "$CONFIG_FILE" ]]; then
    log_error "Config file not found: $CONFIG_FILE"
    exit 1
fi

if ! command -v yq &>/dev/null; then
    log_error "yq is required. Install: brew install yq | snap install yq"
    exit 1
fi

# --- Read config values ---
MODE=$(yq eval '.mode // "mvp"' "$CONFIG_FILE")
STRATEGY=$(yq eval '.strategy // "co-pilot"' "$CONFIG_FILE")
TEAM_PROFILE=$(yq eval '.agents.team_profile // "auto"' "$CONFIG_FILE")
PROJECT_TYPE=$(yq eval '.project.type // "new"' "$CONFIG_FILE")
CLAUDE_MD_SOURCE=$(yq eval '.claude_md.source // "both"' "$CONFIG_FILE")
CLAUDE_MD_PRIORITY=$(yq eval '.claude_md.priority // "project-first"' "$CONFIG_FILE")
GLOBAL_CLAUDE_PATH=$(yq eval '.claude_md.global_path // ""' "$CONFIG_FILE")
PROJECT_CLAUDE_PATH=$(yq eval '.claude_md.project_path // ""' "$CONFIG_FILE")
BOOTSTRAP_TEMPLATE=$(yq eval '.bootstrap_template // "auto"' "$CONFIG_FILE")

# Read tech stack
TECH_LANGUAGES=$(yq eval '.tech_stack.languages // []' "$CONFIG_FILE")
TECH_FRAMEWORKS=$(yq eval '.tech_stack.frameworks // []' "$CONFIG_FILE")

# Read project description
PROJ_DESC=$(yq eval '.project.description // ""' "$CONFIG_FILE")
REQ_FILE=$(yq eval '.project.requirements_file // ""' "$CONFIG_FILE")
if [[ -n "$REQ_FILE" && -f "${FORGE_DIR}/${REQ_FILE}" ]]; then
    PROJ_REQUIREMENTS=$(cat "${FORGE_DIR}/${REQ_FILE}")
elif [[ -n "$PROJ_DESC" ]]; then
    PROJ_REQUIREMENTS="$PROJ_DESC"
else
    PROJ_REQUIREMENTS="No project requirements specified."
fi

log_info "Mode: ${MODE} | Strategy: ${STRATEGY} | Team Profile: ${TEAM_PROFILE}"

# --- Resolve team profile ---
resolve_team_profile() {
    if [[ "$TEAM_PROFILE" == "auto" ]]; then
        case "$MODE" in
            mvp)              echo "lean" ;;
            production-ready) echo "full" ;;
            no-compromise)    echo "full" ;;
            *)                echo "lean" ;;
        esac
    else
        echo "$TEAM_PROFILE"
    fi
}

RESOLVED_PROFILE=$(resolve_team_profile)
log_info "Resolved team profile: ${RESOLVED_PROFILE}"

# Define agent rosters
LEAN_AGENTS="team-leader research-strategist architect backend-developer frontend-engineer qa-engineer devops-specialist critic"
FULL_AGENTS="team-leader researcher strategist architect backend-developer frontend-designer frontend-developer qa-engineer devops-specialist security-tester performance-engineer documentation-specialist critic"

case "$RESOLVED_PROFILE" in
    lean)   ACTIVE_AGENTS="$LEAN_AGENTS" ;;
    full)   ACTIVE_AGENTS="$FULL_AGENTS" ;;
    custom)
        INCLUDE=$(yq eval '.agents.include | join(" ")' "$CONFIG_FILE" 2>/dev/null || echo "")
        if [[ -z "$INCLUDE" ]]; then
            log_error "team_profile is 'custom' but agents.include is empty."
            exit 1
        fi
        ACTIVE_AGENTS="$INCLUDE"
        ;;
    *)
        ACTIVE_AGENTS="$LEAN_AGENTS"
        ;;
esac

# Apply exclude list
EXCLUDE=$(yq eval '.agents.exclude | join(" ")' "$CONFIG_FILE" 2>/dev/null || echo "")
for agent in $EXCLUDE; do
    ACTIVE_AGENTS=$(echo "$ACTIVE_AGENTS" | sed "s/\b${agent}\b//g" | tr -s ' ')
done

# Apply additional list
ADDITIONAL=$(yq eval '.agents.additional | join(" ")' "$CONFIG_FILE" 2>/dev/null || echo "")
for agent in $ADDITIONAL; do
    if ! echo "$ACTIVE_AGENTS" | grep -qw "$agent"; then
        ACTIVE_AGENTS="$ACTIVE_AGENTS $agent"
    fi
done

# Trim whitespace
ACTIVE_AGENTS=$(echo "$ACTIVE_AGENTS" | xargs)
log_info "Active agents: ${ACTIVE_AGENTS}"

# --- Resolve CLAUDE.md sources ---
CLAUDE_MD_CONTENT=""

resolve_claude_md() {
    local global_md=""
    local project_md=""

    # Global CLAUDE.md
    local global_path="${GLOBAL_CLAUDE_PATH:-$HOME/.claude/CLAUDE.md}"
    if [[ -f "$global_path" ]]; then
        global_md=$(cat "$global_path")
    fi

    # Project CLAUDE.md
    local proj_path="${PROJECT_CLAUDE_PATH:-${PROJECT_DIR}/CLAUDE.md}"
    if [[ -f "$proj_path" ]]; then
        project_md=$(cat "$proj_path")
    fi

    case "$CLAUDE_MD_SOURCE" in
        none)
            CLAUDE_MD_CONTENT=""
            ;;
        global)
            if [[ -n "$global_md" ]]; then
                CLAUDE_MD_CONTENT="$global_md"
            fi
            ;;
        project)
            if [[ -n "$project_md" ]]; then
                CLAUDE_MD_CONTENT="$project_md"
            elif [[ -n "$global_md" ]]; then
                CLAUDE_MD_CONTENT="$global_md"  # fallback
            fi
            ;;
        both)
            if [[ -n "$project_md" && -n "$global_md" ]]; then
                if [[ "$CLAUDE_MD_PRIORITY" == "project-first" ]]; then
                    CLAUDE_MD_CONTENT="${project_md}

---
<!-- Global conventions (lower priority) -->
${global_md}"
                else
                    CLAUDE_MD_CONTENT="${global_md}

---
<!-- Project conventions (lower priority) -->
${project_md}"
                fi
            elif [[ -n "$project_md" ]]; then
                CLAUDE_MD_CONTENT="$project_md"
            elif [[ -n "$global_md" ]]; then
                CLAUDE_MD_CONTENT="$global_md"
            fi
            ;;
    esac
}

resolve_claude_md
if [[ -n "$CLAUDE_MD_CONTENT" ]]; then
    log_info "CLAUDE.md resolved (source: ${CLAUDE_MD_SOURCE})"
else
    log_info "No CLAUDE.md content to inject"
fi

# --- Generate project-specific agent files ---
GENERATED_DIR="${PROJECT_DIR}/.forge/agents"
mkdir -p "$GENERATED_DIR"

for agent in $ACTIVE_AGENTS; do
    TEMPLATE_MD="${FORGE_DIR}/agents/${agent}.md"

    if [[ ! -f "$TEMPLATE_MD" ]]; then
        log_warn "Agent template not found: ${agent}.md — skipping"
        continue
    fi

    OUTPUT_MD="${GENERATED_DIR}/${agent}.md"

    {
        # Prepend project context
        echo "<!-- Generated by init-project.sh — DO NOT EDIT MANUALLY -->"
        echo "<!-- Regenerate with: ./forge init --config config/team-config.yaml --project-dir ${PROJECT_DIR} -->"
        echo ""

        # Add CLAUDE.md conventions if present
        if [[ -n "$CLAUDE_MD_CONTENT" ]]; then
            echo "## Project-Wide Conventions (from CLAUDE.md)"
            echo ""
            echo "$CLAUDE_MD_CONTENT"
            echo ""
            echo "---"
            echo ""
        fi

        # Add project context header
        echo "## Project Context"
        echo ""
        echo "- **Mode**: ${MODE}"
        echo "- **Strategy**: ${STRATEGY}"
        echo "- **Team Profile**: ${RESOLVED_PROFILE}"
        echo "- **Project Type**: ${PROJECT_TYPE}"
        echo "- **Tech Stack**: Languages: ${TECH_LANGUAGES} | Frameworks: ${TECH_FRAMEWORKS}"
        echo ""
        echo "### Project Requirements"
        echo ""
        echo "$PROJ_REQUIREMENTS"
        echo ""
        echo "---"
        echo ""

        # Add the agent template
        cat "$TEMPLATE_MD"
    } > "$OUTPUT_MD"

    log_info "Generated: .forge/agents/${agent}.md"
done

# --- Initialize git for new projects ---
if [[ "$PROJECT_TYPE" == "new" && ! -d "${PROJECT_DIR}/.git" ]]; then
    log_info "Initializing git repository..."
    git -C "$PROJECT_DIR" init -q 2>/dev/null || true
fi

# --- Set up secret vault directory ---
SECRETS_DIR="${FORGE_DIR}/shared/.secrets"
mkdir -p "$SECRETS_DIR"
echo "*" > "${SECRETS_DIR}/.gitignore"

log_info "Project initialization complete."
log_info "Generated ${ACTIVE_AGENTS// /, } agent files in .forge/agents/"
