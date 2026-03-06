.PHONY: install dev lint test test-all ci-local clean

# --- Setup ---
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# --- Linting ---
lint:
	@echo "==> Linting Python code..."
	python3 -m py_compile forge_cli/main.py
	python3 -m py_compile forge_cli/wizard.py
	python3 -m py_compile forge_cli/config_schema.py
	python3 -m py_compile forge_cli/config_loader.py
	python3 -m py_compile forge_cli/generators/orchestrator.py
	python3 -m py_compile forge_cli/generators/agent_files.py
	python3 -m py_compile forge_cli/generators/claude_md.py
	python3 -m py_compile forge_cli/generators/mcp_config.py
	python3 -m py_compile forge_cli/generators/skills.py
	python3 -m py_compile forge_cli/generators/team_init_plan.py

# --- Testing ---
test:
	@echo "==> Running tests..."
	python3 -m pytest tests/ -v

test-all: lint test

# --- Full CI mirror ---
ci-local: test-all
	@echo "==> All checks passed!"

# --- Cleanup ---
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
