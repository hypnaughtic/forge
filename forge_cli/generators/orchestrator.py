"""Orchestrator — Coordinates all file generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from forge_cli.config_schema import ForgeConfig
from forge_cli.generators.agent_files import generate_agent_files
from forge_cli.generators.claude_md import generate_claude_md
from forge_cli.generators.mcp_config import generate_mcp_config
from forge_cli.generators.skills import generate_skills
from forge_cli.generators.team_init_plan import generate_team_init_plan

console = Console()


def generate_all(
    config: ForgeConfig,
    llm_provider: Any | None = None,
) -> Any:
    """Generate all files for the project workspace.

    Args:
        config: Forge configuration.
        llm_provider: Optional LLM provider instance for refinement.
            If None and refinement is enabled, creates one from config.

    Returns:
        RefinementReport if refinement ran, else None.
    """
    project_dir = Path(config.project.directory).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    console.print()
    console.print(f"[bold]Generating files in [cyan]{project_dir}[/cyan][/bold]")
    console.print()

    # 1. Agent instruction files → .claude/agents/
    agents_dir = project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    generate_agent_files(config, agents_dir)
    console.print("[green]  ✓[/green] Agent instruction files")

    # 2. CLAUDE.md → project root
    generate_claude_md(config, project_dir)
    console.print("[green]  ✓[/green] CLAUDE.md")

    # 3. MCP configuration → .claude/mcp.json (Playwright always, Atlassian if enabled)
    generate_mcp_config(config, project_dir / ".claude")
    console.print("[green]  ✓[/green] MCP configuration")

    # 4. Skills → .claude/skills/
    skills_dir = project_dir / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    generate_skills(config, skills_dir)
    console.print("[green]  ✓[/green] Reusable skills")

    # 5. team-init-plan.md → project root
    generate_team_init_plan(config, project_dir)
    console.print("[green]  ✓[/green] team-init-plan.md")

    # 6. Optional LLM refinement
    refinement_report = None
    if config.refinement.enabled:
        from forge_cli.generators.refinement import refine_all

        refinement_report = refine_all(config, project_dir, llm_provider=llm_provider)
        console.print(
            f"[green]  ✓[/green] LLM refinement "
            f"({refinement_report.files_improved} files improved, "
            f"${refinement_report.total_cost_usd:.4f})"
        )
        if not refinement_report.all_passed:
            console.print(
                f"[yellow]  ⚠[/yellow] Some files below "
                f"{config.refinement.score_threshold}% threshold"
            )

    console.print()
    return refinement_report
