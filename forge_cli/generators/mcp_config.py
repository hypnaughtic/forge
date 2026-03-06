"""Generate MCP configuration for Atlassian integration."""

from __future__ import annotations

import json
from pathlib import Path

from forge_cli.config_schema import ForgeConfig


def generate_mcp_config(config: ForgeConfig, claude_dir: Path) -> None:
    """Generate .claude/mcp.json with Atlassian MCP server configuration."""
    if not config.atlassian.enabled:
        return

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

    # Atlassian MCP server configuration
    # Uses the official Atlassian MCP server: https://github.com/sooperset/mcp-atlassian
    atlassian_config: dict = {
        "command": "uvx",
        "args": ["mcp-atlassian"],
        "env": {
            "ATLASSIAN_URL": config.atlassian.jira_base_url or "${ATLASSIAN_URL}",
            "ATLASSIAN_USERNAME": "${ATLASSIAN_USERNAME}",
            "ATLASSIAN_API_TOKEN": "${ATLASSIAN_API_TOKEN}",
        },
    }

    # Add Confluence-specific env vars if configured separately
    if config.atlassian.confluence_base_url and config.atlassian.confluence_base_url != config.atlassian.jira_base_url:
        atlassian_config["env"]["CONFLUENCE_URL"] = config.atlassian.confluence_base_url

    mcpServers["atlassian"] = atlassian_config

    mcp_data = {"mcpServers": mcpServers}

    with open(mcp_path, "w") as f:
        json.dump(mcp_data, f, indent=2)
        f.write("\n")

    # Also generate .env.example with required environment variables
    env_example_path = claude_dir.parent / ".env.example"
    env_lines = []
    if env_example_path.exists():
        env_lines = env_example_path.read_text().splitlines()

    atlassian_vars = [
        "",
        "# Atlassian MCP Configuration (required for Jira/Confluence integration)",
        f"ATLASSIAN_URL={config.atlassian.jira_base_url or 'https://yourteam.atlassian.net'}",
        "ATLASSIAN_USERNAME=your-email@company.com",
        "ATLASSIAN_API_TOKEN=your-api-token-here",
    ]

    # Only add if not already present
    if not any("ATLASSIAN_URL" in line for line in env_lines):
        env_lines.extend(atlassian_vars)
        env_example_path.write_text("\n".join(env_lines) + "\n")
