.PHONY: lint lint-shell lint-yaml lint-markdown lint-skills test-unit test-integration test-validation test-plugin test-cockpit test-all ci-local

# --- Linting ---
lint: lint-shell lint-yaml lint-markdown

lint-shell:
	@echo "==> Linting shell scripts..."
	shellcheck --severity=warning forge setup.sh scripts/*.sh scripts/cockpit/*.sh

lint-yaml:
	@echo "==> Linting YAML files..."
	find config templates -name '*.yaml' -o -name '*.yml' | xargs yamllint -c .yamllint.yml

lint-markdown:
	@echo "==> Linting Markdown files..."
	markdownlint-cli2 "docs/**/*.md" "README.md" "CHANGELOG.md" ".claude/commands/*.md" "skills/**/*.md"

lint-skills:
	@echo "==> Validating skill structure..."
	bats tests/validation/test_skill_structure.bats

# --- Testing ---
test-unit:
	@echo "==> Running unit tests..."
	bats tests/unit/

test-integration:
	@echo "==> Running integration tests..."
	bats tests/integration/

test-validation:
	@echo "==> Running validation tests..."
	bats tests/validation/

test-plugin:
	@echo "==> Running plugin tests..."
	bats tests/validation/test_skill_structure.bats tests/integration/test_plugin_structure.bats

test-cockpit:
	@echo "==> Running cockpit tests..."
	bats tests/unit/test_cockpit_render.bats tests/integration/test_cockpit_layout.bats

test-all: test-validation test-unit test-integration

# --- Full CI mirror ---
ci-local: lint test-all
	@echo "==> All checks passed!"
