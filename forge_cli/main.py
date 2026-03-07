"""Forge CLI — Main entry point."""

import click
from rich.console import Console

from forge_cli import __version__

console = Console()


@click.command()
@click.version_option(__version__, prog_name="forge")
@click.option("--config", "config_path", type=click.Path(exists=True), required=True, help="Path to forge-config.yaml")
@click.option("--project-dir", type=click.Path(), default=".", help="Target project workspace directory")
@click.option("--validate-only", is_flag=True, help="Validate config and print summary without generating files")
@click.option("--refine/--no-refine", default=None, help="Override config refinement.enabled")
def cli(config_path: str, project_dir: str, validate_only: bool, refine: bool | None) -> None:
    """Forge — Generate agent instruction files for Claude Code CLI agent teams.

    Reads a forge-config.yaml and generates customized agent files, CLAUDE.md,
    skills, and team-init-plan.md in the target project directory.

    With --refine, files are scored by an LLM and iteratively improved until
    they meet the configured quality threshold (default 90%). All files are
    refined in parallel. Requires llm-gateway: pip install forge-init[refinement]
    """
    from forge_cli.config_loader import load_config

    try:
        config = load_config(config_path)
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise SystemExit(1)

    # Override refinement from CLI flag
    if refine is not None:
        config.refinement.enabled = refine

    if validate_only:
        agents = config.get_active_agents()
        console.print("[green]Configuration is valid.[/green]")
        console.print(f"  Mode: {config.mode.value}")
        console.print(f"  Strategy: {config.strategy.value}")
        console.print(f"  Team profile: {config.resolve_team_profile()}")
        console.print(f"  Active agents: {', '.join(agents)}")
        console.print(f"  Atlassian: {'enabled' if config.atlassian.enabled else 'disabled'}")
        console.print(f"  Sub-agent spawning: {'enabled' if config.agents.allow_sub_agent_spawning else 'disabled'}")
        console.print(f"  Refinement: {'enabled' if config.refinement.enabled else 'disabled'}")
        if config.non_negotiables:
            console.print(f"  Non-negotiables: {len(config.non_negotiables)} rules")
        return

    from forge_cli.generators.orchestrator import generate_all

    config.project.directory = project_dir
    generate_all(config)

    console.print()
    console.print("[bold green]Forge generation complete![/bold green]")
    console.print()
    console.print(f"Generated files in: [cyan]{config.project.directory}[/cyan]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Review the generated files in .claude/agents/")
    console.print("  2. Review CLAUDE.md and team-init-plan.md")
    console.print("  3. Run [cyan]claude[/cyan] in your project directory")
    console.print("  4. Tell Claude: [dim]\"Read team-init-plan.md and initialize the team\"[/dim]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
