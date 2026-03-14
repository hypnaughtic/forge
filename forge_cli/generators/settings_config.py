"""Generate Claude Code settings.json with strategy-based permissions."""

from __future__ import annotations

import json
from pathlib import Path

from forge_cli.config_schema import ExecutionStrategy, ForgeConfig
from forge_cli.generators.hooks import generate_hooks_config

# Both auto-pilot and co-pilot grant full tool access. The difference between
# them is behavioral (instructions in agent files), not permission-based.
# Co-pilot agents have full autonomy for ALL implementation work (edit, write,
# bash, test, deploy) — they only pause for architectural/design decisions.
_FULL_TOOL_ALLOW: list[str] = [
    "Bash(*)",
    "Read(*)",
    "Edit(*)",
    "Write(*)",
    "WebFetch(*)",
    "WebSearch(*)",
    "Agent(*)",
    "Glob(*)",
    "Grep(*)",
    "mcp__*",
]


def generate_settings_config(config: ForgeConfig, claude_dir: Path) -> None:
    """Generate .claude/settings.json with strategy-based permission rules.

    auto-pilot: allow all tools, make all decisions autonomously.
    co-pilot: allow all tools, but agents ask human for architectural/design input.
    micro-manage: no settings.json generated (Claude Code defaults prompt everything).
    """
    if config.strategy == ExecutionStrategy.MICRO_MANAGE:
        return

    claude_dir.mkdir(parents=True, exist_ok=True)

    settings_path = claude_dir / "settings.json"
    existing: dict = {}
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    new_allow = _FULL_TOOL_ALLOW

    # Merge with existing permissions
    permissions = existing.get("permissions", {})
    existing_allow = permissions.get("allow", [])
    existing_deny = permissions.get("deny", [])

    # Deduplicate allow rules while preserving order
    merged_allow = list(dict.fromkeys(existing_allow + new_allow))

    permissions["allow"] = merged_allow
    permissions["deny"] = existing_deny

    existing["permissions"] = permissions

    # Enable experimental agent teams for split-pane multi-agent sessions
    if config.agents.allow_sub_agent_spawning:
        existing.setdefault("env", {})
        existing["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

    # Add checkpoint hooks configuration (replace entirely on each generation)
    existing["hooks"] = generate_hooks_config()

    with open(settings_path, "w") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")
