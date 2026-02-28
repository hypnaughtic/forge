#!/usr/bin/env bash
# ==============================================================================
# Forge — Setup Script
# ==============================================================================
# One-time setup: validates dependencies, creates runtime directories,
# and prepares the environment for running Forge.
set -euo pipefail

FORGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="${FORGE_DIR}/shared"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[Setup]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[Setup]${NC} $*"; }
log_error() { echo -e "${RED}[Setup]${NC} $*" >&2; }
log_ok()    { echo -e "${GREEN}  ✓${NC} $*"; }
log_fail()  { echo -e "${RED}  ✗${NC} $*"; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: ./forge setup"
    echo ""
    echo "One-time setup for Forge:"
    echo "  - Validates required dependencies (claude, tmux, git, yq)"
    echo "  - Creates the shared/ runtime directory structure"
    echo "  - Makes all scripts executable"
    echo "  - Validates team-config.yaml"
    exit 0
fi

echo -e "${CYAN}"
echo "  Forge — Setup"
echo "  ============="
echo -e "${NC}"

ERRORS=0

# --- Check prerequisites ---
log_info "Checking prerequisites..."

# Required tools
check_tool() {
    local tool="$1"
    local install_hint="${2:-}"
    if command -v "$tool" &>/dev/null; then
        local version
        version=$("$tool" --version 2>/dev/null | head -1 || echo "installed")
        log_ok "$tool: $version"
    else
        log_fail "$tool: NOT FOUND"
        if [[ -n "$install_hint" ]]; then
            echo "      Install: $install_hint"
        fi
        ERRORS=$((ERRORS + 1))
    fi
}

check_tool "git" "https://git-scm.com/downloads"
check_tool "claude" "npm install -g @anthropic-ai/claude-code"
check_tool "yq" "brew install yq (macOS) | snap install yq (Ubuntu) | go install github.com/mikefarah/yq/v4@latest"

# tmux is required for tmux orchestration mode, optional for Agent Teams mode
ORCHESTRATION="agent-teams"
if command -v yq &>/dev/null && [[ -f "${FORGE_DIR}/config/team-config.yaml" ]]; then
    ORCHESTRATION=$(yq eval '.orchestration // "agent-teams"' "${FORGE_DIR}/config/team-config.yaml" 2>/dev/null || echo "agent-teams")
fi

if [[ "$ORCHESTRATION" == "tmux" ]]; then
    check_tool "tmux" "brew install tmux (macOS) | apt install tmux (Ubuntu)"
else
    # tmux is optional in Agent Teams mode
    if command -v tmux &>/dev/null; then
        log_ok "tmux: $(tmux -V 2>/dev/null) (optional in Agent Teams mode)"
    else
        log_warn "tmux: NOT FOUND (optional — required only for tmux orchestration mode)"
        echo "      Install: brew install tmux (macOS) | apt install tmux (Ubuntu)"
    fi
fi

# Optional tools (needed for Production Ready+)
echo ""
log_info "Checking optional dependencies (needed for Production Ready+ modes)..."

if command -v docker &>/dev/null; then
    log_ok "docker: $(docker --version 2>/dev/null | head -1)"
else
    log_warn "docker: NOT FOUND (required for Production Ready and No Compromise modes)"
    echo "      Install: https://docs.docker.com/get-docker/"
fi

if command -v jq &>/dev/null; then
    log_ok "jq: $(jq --version 2>/dev/null)"
else
    log_warn "jq: NOT FOUND (recommended for JSON parsing in scripts)"
    echo "      Install: brew install jq (macOS) | apt install jq (Ubuntu)"
fi

# --- Create shared/ directory structure ---
echo ""
log_info "Creating shared/ runtime directory structure..."

SHARED_DIRS=(
    "${SHARED_DIR}/.queue"
    "${SHARED_DIR}/.status"
    "${SHARED_DIR}/.memory"
    "${SHARED_DIR}/.decisions"
    "${SHARED_DIR}/.iterations"
    "${SHARED_DIR}/.artifacts"
    "${SHARED_DIR}/.locks"
    "${SHARED_DIR}/.logs"
    "${SHARED_DIR}/.logs/archive"
    "${SHARED_DIR}/.snapshots"
    "${SHARED_DIR}/.secrets"
    "${SHARED_DIR}/.human"
)

for dir in "${SHARED_DIRS[@]}"; do
    mkdir -p "$dir"
    log_ok "Created: ${dir#"${FORGE_DIR}"/}"
done

# Create .gitignore in shared/.secrets/ to prevent accidental commits
echo "*" > "${SHARED_DIR}/.secrets/.gitignore"
log_ok "Created: shared/.secrets/.gitignore (blocks all files)"

# Create vault.env.example
if [[ ! -f "${SHARED_DIR}/.secrets/vault.env.example" ]]; then
    cat > "${SHARED_DIR}/.secrets/vault.env.example" <<'VAULT'
# ==============================================================================
# Forge Secret Vault — Example
# ==============================================================================
# Copy this file to vault.env and fill in actual values.
# vault.env is NEVER committed to git.

# --- Database ---
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myproject
DB_USER=postgres
DB_PASSWORD=changeme

# --- API Keys ---
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# --- LLM Gateway ---
LLM_GATEWAY_MODE=local-claude
LLM_GATEWAY_MODEL=claude-sonnet-4-20250514

# --- Cloud Provider ---
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_REGION=us-east-1

# --- Docker Registry ---
# DOCKER_REGISTRY_URL=
# DOCKER_REGISTRY_USER=
# DOCKER_REGISTRY_TOKEN=
VAULT
    log_ok "Created: shared/.secrets/vault.env.example"
fi

# Create agent-access.yaml
if [[ ! -f "${SHARED_DIR}/.secrets/agent-access.yaml" ]]; then
    cat > "${SHARED_DIR}/.secrets/agent-access.yaml" <<'ACCESS'
# Defines least-privilege access: each agent only gets the secrets it needs.
access:
  backend-developer:
    - database
    - api-keys
    - llm-gateway
  frontend-engineer:
    - api-keys-public
  devops-specialist:
    - cloud
    - docker-registry
    - database
    - monitoring
  qa-engineer:
    - database-test
    - api-keys
    - llm-gateway
  security-tester:
    - all
ACCESS
    log_ok "Created: shared/.secrets/agent-access.yaml"
fi

# Initialize empty artifact registry
if [[ ! -f "${SHARED_DIR}/.artifacts/registry.json" ]]; then
    echo '{"artifacts": []}' > "${SHARED_DIR}/.artifacts/registry.json"
    log_ok "Created: shared/.artifacts/registry.json"
fi

# --- Make all scripts executable ---
echo ""
log_info "Making scripts executable..."

chmod +x "${FORGE_DIR}/forge" 2>/dev/null && log_ok "forge" || true
for script in "${FORGE_DIR}/scripts/"*.sh; do
    if [[ -f "$script" ]]; then
        chmod +x "$script"
        log_ok "scripts/$(basename "$script")"
    fi
done
chmod +x "${FORGE_DIR}/setup.sh" 2>/dev/null && log_ok "setup.sh" || true

# --- Validate config ---
echo ""
log_info "Validating configuration..."

if [[ -f "${FORGE_DIR}/config/team-config.yaml" ]]; then
    if command -v yq &>/dev/null; then
        if yq eval '.' "${FORGE_DIR}/config/team-config.yaml" >/dev/null 2>&1; then
            log_ok "config/team-config.yaml: valid YAML"
        else
            log_fail "config/team-config.yaml: invalid YAML syntax"
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_warn "Cannot validate YAML (yq not installed). Skipping."
    fi
else
    log_warn "config/team-config.yaml not found. Run './forge init' to create it."
fi

# --- Summary ---
echo ""
echo "─────────────────────────────────────"
if [[ $ERRORS -gt 0 ]]; then
    log_error "Setup completed with ${ERRORS} error(s). Fix the issues above before running './forge start'."
    exit 1
else
    log_info "Setup complete! Next steps:"
    echo ""
    echo "  1. Edit config/team-config.yaml (or run ./forge init)"
    echo "  2. Edit config/project-requirements.md with your project details"
    echo "  3. Run: ./forge start"
    echo ""
fi
