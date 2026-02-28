.PHONY: lint lint-shell lint-yaml lint-markdown test-unit test-integration test-validation test-all ci-local

# --- Linting ---
lint: lint-shell lint-yaml lint-markdown

lint-shell:
	@echo "==> Linting shell scripts..."
	shellcheck --severity=warning forge setup.sh scripts/*.sh

lint-yaml:
	@echo "==> Linting YAML files..."
	find config templates -name '*.yaml' -o -name '*.yml' | xargs yamllint -c .yamllint.yml

lint-markdown:
	@echo "==> Linting Markdown files..."
	markdownlint-cli2 "docs/**/*.md" "README.md" "CHANGELOG.md" ".claude/commands/*.md"

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

test-all: test-validation test-unit test-integration

# --- Full CI mirror ---
ci-local: lint test-all
	@echo "==> All checks passed!"
