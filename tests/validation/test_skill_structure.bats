#!/usr/bin/env bats
# ==============================================================================
# Validation: Skill Structure
# ==============================================================================
# Validates that all skill files have correct frontmatter, plugin.json is valid,
# no name conflicts, and all expected skills are present.

load '../test_helper/common'

setup() {
    create_test_environment
    # Use real jq for JSON validation
    export MOCK_JQ_PASSTHROUGH=true
    # Copy skills and plugin manifest to test environment
    if [[ -d "${FORGE_ROOT}/skills" ]]; then
        cp -r "${FORGE_ROOT}/skills" "${FORGE_DIR}/skills"
    fi
    if [[ -d "${FORGE_ROOT}/.claude-plugin" ]]; then
        cp -r "${FORGE_ROOT}/.claude-plugin" "${FORGE_DIR}/.claude-plugin"
    fi
    if [[ -f "${FORGE_ROOT}/VERSION" ]]; then
        cp "${FORGE_ROOT}/VERSION" "${FORGE_DIR}/VERSION"
    fi
}

teardown() {
    destroy_test_environment
}

# --- Plugin manifest ---

@test "plugin.json exists" {
    assert_file_exists "${FORGE_DIR}/.claude-plugin/plugin.json"
}

@test "plugin.json is valid JSON" {
    run jq empty "${FORGE_DIR}/.claude-plugin/plugin.json"
    assert_success
}

@test "plugin.json has required fields" {
    run jq -r '.name' "${FORGE_DIR}/.claude-plugin/plugin.json"
    assert_success
    assert_output "forge"

    run jq -r '.version' "${FORGE_DIR}/.claude-plugin/plugin.json"
    assert_success
    refute_output ""

    run jq -r '.description' "${FORGE_DIR}/.claude-plugin/plugin.json"
    assert_success
    refute_output ""
}

# --- VERSION file ---

@test "VERSION file exists" {
    assert_file_exists "${FORGE_DIR}/VERSION"
}

@test "VERSION file contains semver" {
    run cat "${FORGE_DIR}/VERSION"
    assert_success
    # Match semver pattern (x.y.z)
    [[ "$output" =~ ^[0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$ ]]
}

# --- Skill files ---

EXPECTED_SKILLS=(forge status cost snapshot start stop mode strategy init ask guide team)

@test "all 12 expected skills exist" {
    for skill in "${EXPECTED_SKILLS[@]}"; do
        assert_file_exists "${FORGE_DIR}/skills/${skill}/SKILL.md"
    done
}

@test "skill files have YAML frontmatter with name field" {
    for skill in "${EXPECTED_SKILLS[@]}"; do
        local skill_file="${FORGE_DIR}/skills/${skill}/SKILL.md"
        # Check file starts with ---
        local first_line
        first_line=$(head -1 "$skill_file")
        [[ "$first_line" == "---" ]]

        # Check name field exists in frontmatter
        run grep -m1 "^name:" "$skill_file"
        assert_success
    done
}

@test "skill files have description in frontmatter" {
    for skill in "${EXPECTED_SKILLS[@]}"; do
        local skill_file="${FORGE_DIR}/skills/${skill}/SKILL.md"
        run grep -m1 "^description:" "$skill_file"
        assert_success
    done
}

@test "skill names in frontmatter match directory names" {
    for skill in "${EXPECTED_SKILLS[@]}"; do
        local skill_file="${FORGE_DIR}/skills/${skill}/SKILL.md"
        # Extract name from frontmatter (between --- markers)
        local name
        name=$(sed -n '2,/^---$/p' "$skill_file" | grep "^name:" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")
        [[ "$name" == "$skill" ]]
    done
}

@test "no duplicate skill names" {
    local names=()
    for skill_dir in "${FORGE_DIR}"/skills/*/; do
        [[ -d "$skill_dir" ]] || continue
        local skill_file="${skill_dir}/SKILL.md"
        [[ -f "$skill_file" ]] || continue
        local name
        name=$(awk '/^---$/,/^---$/{if(/^name:/){print $2}}' "$skill_file" | tr -d '"' | tr -d "'")
        # Check for duplicates
        for existing in "${names[@]}"; do
            [[ "$existing" != "$name" ]]
        done
        names+=("$name")
    done
}

@test "skill files contain markdown content after frontmatter" {
    for skill in "${EXPECTED_SKILLS[@]}"; do
        local skill_file="${FORGE_DIR}/skills/${skill}/SKILL.md"
        # Count lines after second ---
        local content_lines
        content_lines=$(awk 'BEGIN{c=0} /^---$/{c++; next} c>=2{print}' "$skill_file" | wc -l | tr -d ' ')
        [[ $content_lines -gt 0 ]]
    done
}
