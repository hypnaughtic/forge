"""Generate MCP configuration for Playwright and Atlassian integration."""

from __future__ import annotations

import json
from pathlib import Path

from forge_cli.config_schema import ForgeConfig


def generate_mcp_config(config: ForgeConfig, claude_dir: Path) -> None:
    """Generate .claude/mcp.json with MCP server configurations.

    Always includes Playwright MCP for visual verification.
    Conditionally includes Atlassian MCP if enabled.
    """
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Check if mcp.json already exists and merge
    mcp_path = claude_dir / "mcp.json"
    existing: dict = {}
    if mcp_path.exists():
        try:
            with open(mcp_path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    mcpServers = existing.get("mcpServers", {})

    # Playwright MCP server (always included — used for visual verification)
    mcpServers["playwright"] = {
        "command": "npx",
        "args": ["@anthropic-ai/playwright-mcp@latest"],
    }

    # Atlassian MCP server (conditional)
    if config.atlassian.enabled:
        atlassian_config: dict = {
            "command": "uvx",
            "args": ["mcp-atlassian"],
            "env": {
                "ATLASSIAN_URL": config.atlassian.jira_base_url or "${ATLASSIAN_URL}",
                "ATLASSIAN_USERNAME": "${ATLASSIAN_USERNAME}",
                "ATLASSIAN_API_TOKEN": "${ATLASSIAN_API_TOKEN}",
            },
        }

        if config.atlassian.confluence_base_url and config.atlassian.confluence_base_url != config.atlassian.jira_base_url:
            atlassian_config["env"]["CONFLUENCE_URL"] = config.atlassian.confluence_base_url

        mcpServers["atlassian"] = atlassian_config

    mcp_data = {"mcpServers": mcpServers}

    with open(mcp_path, "w") as f:
        json.dump(mcp_data, f, indent=2)
        f.write("\n")



def generate_env_example(config: ForgeConfig, project_dir: Path) -> None:
    """Generate .env.example with required environment variables.

    Aggregates env vars from all features that need them:
    - GH_TOKEN when SSH git auth is configured
    - Atlassian vars when Atlassian integration is enabled

    Idempotent: checks for existing vars before appending.
    """
    needs_gh_token = config.has_ssh_auth()
    needs_atlassian = config.atlassian.enabled

    if not needs_gh_token and not needs_atlassian:
        return

    env_example_path = project_dir / ".env.example"
    env_lines: list[str] = []
    if env_example_path.exists():
        env_lines = env_example_path.read_text().splitlines()

    if needs_gh_token and not any("GH_TOKEN" in line for line in env_lines):
        env_lines.extend([
            "",
            "# GitHub CLI Authentication (required for PR creation, releases, workflow monitoring)",
            "# Generate at: https://github.com/settings/tokens",
            "GH_TOKEN=ghp_your-personal-access-token-here",
        ])

    if needs_atlassian and not any("ATLASSIAN_URL" in line for line in env_lines):
        env_lines.extend([
            "",
            "# Atlassian MCP Configuration (required for Jira/Confluence integration)",
            f"ATLASSIAN_URL={config.atlassian.jira_base_url or 'https://yourteam.atlassian.net'}",
            "ATLASSIAN_USERNAME=your-email@company.com",
            "ATLASSIAN_API_TOKEN=your-api-token-here",
        ])

    env_example_path.write_text("\n".join(env_lines) + "\n")
