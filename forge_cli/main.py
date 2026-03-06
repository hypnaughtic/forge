"""Forge CLI — Main entry point."""

import click
from rich.console import Console

from forge_cli import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="forge")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Forge — Project initialization tool for Claude Code CLI agent teams.

    Generate agent instruction files, CLAUDE.md, skills, and team-init-plan.md
    for your project workspace. Configure once, then let Claude Code agents
    build your project with precision.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(init_cmd)


@cli.command("init")
@click.option("--config", "config_path", type=click.Path(), default=None, help="Path to existing forge-config.yaml")
@click.option("--project-dir", type=click.Path(), default=".", help="Target project workspace directory")
@click.option("--non-interactive", is_flag=True, help="Skip interactive wizard, use config file only")
def init_cmd(config_path: str | None, project_dir: str, non_interactive: bool) -> None:
    """Initialize a project with Claude Code agent team configuration.

    Runs an interactive wizard to configure your agent team, then generates
    all necessary files in the project workspace.
    """
    from forge_cli.wizard import run_wizard
    from forge_cli.generators.orchestrator import generate_all

    if non_interactive and config_path:
        from forge_cli.config_loader import load_config

        config = load_config(config_path)
        config.project.directory = project_dir
    else:
        config = run_wizard(config_path, project_dir)

    generate_all(config)

    console.print()
    console.print("[bold green]Forge initialization complete![/bold green]")
    console.print()
    console.print(f"Generated files in: [cyan]{config.project.directory}[/cyan]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Review the generated files in .claude/agents/")
    console.print("  2. Review CLAUDE.md and team-init-plan.md")
    console.print("  3. Run [cyan]claude[/cyan] in your project directory")
    console.print("  4. Tell Claude: [dim]\"Read team-init-plan.md and initialize the team\"[/dim]")


@cli.command("generate")
@click.option("--config", "config_path", type=click.Path(exists=True), required=True, help="Path to forge-config.yaml")
@click.option("--project-dir", type=click.Path(), default=".", help="Target project workspace directory")
def generate_cmd(config_path: str, project_dir: str) -> None:
    """Generate agent files from an existing configuration.

    Use this to regenerate files after editing forge-config.yaml manually.
    """
    from forge_cli.config_loader import load_config
    from forge_cli.generators.orchestrator import generate_all

    config = load_config(config_path)
    config.project.directory = project_dir
    generate_all(config)

    console.print("[bold green]Files regenerated successfully.[/bold green]")


@cli.command("validate")
@click.option("--config", "config_path", type=click.Path(exists=True), required=True, help="Path to forge-config.yaml")
def validate_cmd(config_path: str) -> None:
    """Validate a forge-config.yaml file."""
    from forge_cli.config_loader import load_config

    try:
        config = load_config(config_path)
        agents = config.get_active_agents()
        console.print("[green]Configuration is valid.[/green]")
        console.print(f"  Mode: {config.mode.value}")
        console.print(f"  Strategy: {config.strategy.value}")
        console.print(f"  Team profile: {config.resolve_team_profile()}")
        console.print(f"  Active agents: {', '.join(agents)}")
        console.print(f"  Atlassian: {'enabled' if config.atlassian.enabled else 'disabled'}")
        console.print(f"  Sub-agent spawning: {'enabled' if config.agents.allow_sub_agent_spawning else 'disabled'}")
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise SystemExit(1)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
