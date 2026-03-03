#!/usr/bin/env bats
# ==============================================================================
# Integration Tests: Plugin Structure
# ==============================================================================
# Tests that the plugin can be discovered, skills are loadable, and
# FORGE_DIR resolution works across contexts.

load '../test_helper/common'

setup() {
    create_test_environment
    # Use real jq for JSON validation
    export MOCK_JQ_PASSTHROUGH=true
    # Copy full plugin and skills structure
    if [[ -d "${FORGE_ROOT}/skills" ]]; then
        cp -r "${FORGE_ROOT}/skills" "${FORGE_DIR}/skills"
    fi
    if [[ -d "${FORGE_ROOT}/.claude-plugin" ]]; then
        cp -r "${FORGE_ROOT}/.claude-plugin" "${FORGE_DIR}/.claude-plugin"
    fi
    if [[ -f "${FORGE_ROOT}/VERSION" ]]; then
        cp "${FORGE_ROOT}/VERSION" "${FORGE_DIR}/VERSION"
    fi
    cp "${FORGE_ROOT}/scripts/resolve-forge-dir.sh" "${FORGE_DIR}/scripts/"
    chmod +x "${FORGE_DIR}/scripts/resolve-forge-dir.sh"
}

teardown() {
    destroy_test_environment
}

# --- Plugin discovery ---

@test "plugin: plugin.json exists in .claude-plugin/" {
    assert_file_exists "${FORGE_DIR}/.claude-plugin/plugin.json"
}

@test "plugin: all 12 skill directories exist" {
    local expected=(forge status cost snapshot start stop mode strategy init ask guide team)
    for skill in "${expected[@]}"; do
        assert_file_exists "${FORGE_DIR}/skills/${skill}/SKILL.md"
    done
}

@test "plugin: skill files are non-empty" {
    for skill_file in "${FORGE_DIR}"/skills/*/SKILL.md; do
        [[ -f "$skill_file" ]] || continue
        local size
        size=$(wc -c < "$skill_file" | tr -d ' ')
        [[ $size -gt 50 ]]
    done
}

# --- FORGE_DIR resolution ---

@test "resolve-forge-dir: from scripts/ directory" {
    local result
    result=$(cd "${FORGE_DIR}/scripts" && bash resolve-forge-dir.sh)
    [[ "$result" == "$FORGE_DIR" ]]
}

@test "resolve-forge-dir: FORGE_DIR env takes priority" {
    local result
    result=$(FORGE_DIR="/custom/path" bash "${FORGE_DIR}/scripts/resolve-forge-dir.sh")
    [[ "$result" == "/custom/path" ]]
}

@test "resolve-forge-dir: source mode exports FORGE_DIR" {
    local result
    result=$(cd "${FORGE_DIR}" && source scripts/resolve-forge-dir.sh && echo "$FORGE_DIR")
    [[ "$result" == "$FORGE_DIR" ]]
}

# --- Version ---

@test "plugin: VERSION matches plugin.json version" {
    local file_version
    file_version=$(cat "${FORGE_DIR}/VERSION" | tr -d '[:space:]')
    local json_version
    json_version=$(jq -r '.version' "${FORGE_DIR}/.claude-plugin/plugin.json")
    [[ "$file_version" == "$json_version" ]]
}

# --- Skill frontmatter consistency ---

@test "plugin: all skills have argument-hint in frontmatter" {
    for skill_file in "${FORGE_DIR}"/skills/*/SKILL.md; do
        [[ -f "$skill_file" ]] || continue
        # argument-hint should be present (even if empty string)
        run grep "argument-hint:" "$skill_file"
        assert_success
    done
}
