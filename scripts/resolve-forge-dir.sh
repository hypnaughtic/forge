#!/usr/bin/env bash
# ==============================================================================
# Forge — Resolve FORGE_DIR Across Install Contexts
# ==============================================================================
# Determines the Forge installation directory regardless of how forge was
# installed: git clone, Homebrew, or Claude Code plugin.
#
# Priority:
#   1. FORGE_DIR environment variable (explicit override)
#   2. Script's own directory (git clone / direct invocation)
#   3. Homebrew libexec (brew install)
#
# Usage: source scripts/resolve-forge-dir.sh
#        echo "$FORGE_DIR"
set -euo pipefail

resolve_forge_dir() {
    # 1. Explicit env var takes priority
    if [[ -n "${FORGE_DIR:-}" ]]; then
        echo "$FORGE_DIR"
        return
    fi

    # 2. Resolve from this script's location (scripts/ is one level below FORGE_DIR)
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # If we're inside scripts/, go up one level
    if [[ "$(basename "$script_dir")" == "scripts" ]]; then
        local candidate
        candidate="$(cd "$script_dir/.." && pwd)"
        if [[ -f "${candidate}/forge" ]]; then
            echo "$candidate"
            return
        fi
    fi

    # 3. Check Homebrew libexec
    local brew_prefix
    if command -v brew &>/dev/null; then
        brew_prefix="$(brew --prefix 2>/dev/null || true)"
        if [[ -n "$brew_prefix" && -d "${brew_prefix}/opt/forge/libexec" ]]; then
            echo "${brew_prefix}/opt/forge/libexec"
            return
        fi
    fi

    # 4. Fallback: current working directory
    echo "$(pwd)"
}

# Export if sourced
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    FORGE_DIR="$(resolve_forge_dir)"
    export FORGE_DIR
else
    resolve_forge_dir
fi
