"""Interactive configuration wizard for forge init."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from forge_cli.config_schema import (
    AgentNamingConfig,
    AgentsConfig,
    AtlassianConfig,
    CostConfig,
    ExecutionStrategy,
    ForgeConfig,
    LLMGatewayConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
    TechStack,
)

console = Console()


def _is_interactive() -> bool:
    """Check if stdin is an interactive terminal."""
    return sys.stdin.isatty()


def run_wizard(output_path: str) -> ForgeConfig:
    """Run the interactive configuration wizard.

    Walks through 8 steps, builds a ForgeConfig, shows summary,
    saves to file, and optionally runs generation.

    Returns:
        The built ForgeConfig (for testing).
    """
    if not _is_interactive():
        console.print(
            "[red]forge init requires an interactive terminal. "
            "Use forge --config instead.[/red]"
        )
        raise SystemExit(1)

    console.print()
    console.print(
        Panel(
            "[bold]Forge — Interactive Configuration Builder[/bold]",
            expand=False,
        )
    )

    try:
        project = _prompt_project()
        mode = _prompt_mode()
        strategy = _prompt_strategy()
        tech_stack = _prompt_tech_stack()
        agents_cfg, naming_cfg, cost_cfg = _prompt_agents(mode)
        atlassian = _prompt_atlassian()
        llm_gateway = _prompt_llm_gateway()
        non_negotiables = _prompt_non_negotiables()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Aborted.[/yellow]")
        raise SystemExit(130)

    config = ForgeConfig(
        project=project,
        mode=mode,
        strategy=strategy,
        cost=cost_cfg,
        agents=agents_cfg,
        tech_stack=tech_stack,
        atlassian=atlassian,
        agent_naming=naming_cfg,
        llm_gateway=llm_gateway,
        non_negotiables=non_negotiables,
    )

    _show_summary(config)
    _confirm_and_save(config, output_path)

    return config


def _prompt_project() -> ProjectConfig:
    """Step 1/8: Project details."""
    console.print("\n  [bold]Step 1/8: Project Details[/bold]")
    console.print("  " + "─" * 24)

    description = ""
    while not description.strip():
        description = click.prompt("  Project description")
        if not description.strip():
            console.print("  [red]Description is required.[/red]")

    requirements = click.prompt(
        "  Detailed requirements (Enter to skip)", default="", show_default=False
    )

    project_type = click.prompt(
        "  Project type", type=click.Choice(["new", "existing"]), default="new"
    )

    existing_path = ""
    if project_type == "existing":
        existing_path = click.prompt("  Path to existing project")

    return ProjectConfig(
        description=description.strip(),
        requirements=requirements.strip(),
        type=project_type,
        existing_project_path=existing_path,
    )


def _prompt_mode() -> ProjectMode:
    """Step 2/8: Quality mode."""
    console.print("\n  [bold]Step 2/8: Quality Mode[/bold]")
    console.print("  " + "─" * 21)

    options = [
        ("mvp", "70% quality, happy-path tests, lean team (8 agents)"),
        ("production-ready", "90% quality, >90% coverage, full team (12 agents)"),
        ("no-compromise", "100% quality, exhaustive tests, full team (12 agents)"),
    ]
    for i, (name, desc) in enumerate(options, 1):
        console.print(f"    {i}. [cyan]{name}[/cyan] — {desc}")

    choice = click.prompt(
        "  Choice", type=click.IntRange(1, 3), default=1
    )
    return [ProjectMode.MVP, ProjectMode.PRODUCTION_READY, ProjectMode.NO_COMPROMISE][
        choice - 1
    ]


def _prompt_strategy() -> ExecutionStrategy:
    """Step 3/8: Execution strategy."""
    console.print("\n  [bold]Step 3/8: Execution Strategy[/bold]")
    console.print("  " + "─" * 28)

    options = [
        ("auto-pilot", "Full autonomy, agents make all decisions"),
        ("co-pilot", "Full tool access, agents ask on architecture/scope only"),
        ("micro-manage", "Every significant decision needs your approval"),
    ]
    for i, (name, desc) in enumerate(options, 1):
        console.print(f"    {i}. [cyan]{name}[/cyan] — {desc}")

    choice = click.prompt(
        "  Choice", type=click.IntRange(1, 3), default=2
    )
    return [
        ExecutionStrategy.AUTO_PILOT,
        ExecutionStrategy.CO_PILOT,
        ExecutionStrategy.MICRO_MANAGE,
    ][choice - 1]


def _prompt_tech_stack() -> TechStack:
    """Step 4/8: Tech stack."""
    console.print("\n  [bold]Step 4/8: Tech Stack[/bold]")
    console.print("  " + "─" * 20)

    def _parse_list(raw: str) -> list[str]:
        return [s.strip() for s in raw.split(",") if s.strip()] if raw.strip() else []

    languages = _parse_list(
        click.prompt("  Languages (comma-separated, Enter to skip)", default="", show_default=False)
    )
    frameworks = _parse_list(
        click.prompt("  Frameworks (comma-separated, Enter to skip)", default="", show_default=False)
    )
    databases = _parse_list(
        click.prompt("  Databases (comma-separated, Enter to skip)", default="", show_default=False)
    )
    infrastructure = _parse_list(
        click.prompt("  Infrastructure (comma-separated, Enter to skip)", default="", show_default=False)
    )

    return TechStack(
        languages=languages,
        frameworks=frameworks,
        databases=databases,
        infrastructure=infrastructure,
    )


def _prompt_agents(
    mode: ProjectMode,
) -> tuple[AgentsConfig, AgentNamingConfig, CostConfig]:
    """Step 5/8: Team configuration."""
    console.print("\n  [bold]Step 5/8: Team Configuration[/bold]")
    console.print("  " + "─" * 28)

    profile_choice = click.prompt(
        "  Team profile",
        type=click.Choice(["auto", "lean", "full", "custom"]),
        default="auto",
    )
    profile = TeamProfile(profile_choice)

    include: list[str] = []
    if profile == TeamProfile.CUSTOM:
        available = [
            "team-leader", "research-strategist", "architect",
            "backend-developer", "frontend-engineer", "frontend-designer",
            "frontend-developer", "qa-engineer", "devops-specialist",
            "security-tester", "performance-engineer",
            "documentation-specialist", "critic",
        ]
        console.print("  Available agents:")
        for agent in available:
            console.print(f"    - {agent}")
        raw = click.prompt("  Include agents (comma-separated)")
        include = [s.strip() for s in raw.split(",") if s.strip()]

    spawning = click.confirm("  Allow sub-agent spawning?", default=True)

    naming_choice = click.prompt(
        "  Agent naming style",
        type=click.Choice(["creative", "functional", "codename", "off"]),
        default="creative",
    )
    naming_enabled = naming_choice != "off"
    naming_style = naming_choice if naming_enabled else "creative"

    max_cost = click.prompt("  Max development cost in USD", type=int, default=50)

    agents_cfg = AgentsConfig(
        team_profile=profile,
        include=include,
        allow_sub_agent_spawning=spawning,
    )
    naming_cfg = AgentNamingConfig(enabled=naming_enabled, style=naming_style)
    cost_cfg = CostConfig(max_development_cost=max_cost)

    return agents_cfg, naming_cfg, cost_cfg


def _prompt_atlassian() -> AtlassianConfig:
    """Step 6/8: Atlassian integration."""
    console.print("\n  [bold]Step 6/8: Atlassian Integration[/bold]")
    console.print("  " + "─" * 31)

    enabled = click.confirm("  Enable Jira/Confluence integration?", default=False)
    if not enabled:
        return AtlassianConfig(enabled=False)

    jira_key = click.prompt("  Jira project key", default="", show_default=False)
    jira_url = click.prompt("  Jira base URL", default="", show_default=False)
    confluence_key = click.prompt("  Confluence space key", default="", show_default=False)
    confluence_url = click.prompt("  Confluence base URL", default="", show_default=False)

    return AtlassianConfig(
        enabled=True,
        jira_project_key=jira_key,
        jira_base_url=jira_url,
        confluence_space_key=confluence_key,
        confluence_base_url=confluence_url,
    )


def _prompt_llm_gateway() -> LLMGatewayConfig:
    """Step 7/8: LLM Gateway."""
    console.print("\n  [bold]Step 7/8: LLM Gateway[/bold]")
    console.print("  " + "─" * 21)

    enabled = click.confirm(
        "  Enable llm-gateway mandate in generated files?", default=True
    )
    return LLMGatewayConfig(enabled=enabled)


def _prompt_non_negotiables() -> list[str]:
    """Step 8/8: Non-negotiables."""
    console.print("\n  [bold]Step 8/8: Non-Negotiables (optional)[/bold]")
    console.print("  " + "─" * 35)
    console.print("  Enter absolute requirements (one per line, empty line to finish):")

    rules: list[str] = []
    while True:
        rule = click.prompt("  >", default="", show_default=False)
        if not rule.strip():
            break
        rules.append(rule.strip())

    return rules


def _show_summary(config: ForgeConfig) -> None:
    """Display configuration summary."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Project", config.project.description[:60])
    table.add_row("Mode", config.mode.value)
    table.add_row("Strategy", config.strategy.value)

    profile = config.resolve_team_profile()
    agent_count = len(config.get_active_agents())
    table.add_row("Team", f"{profile} — {agent_count} agents")

    tech_parts = []
    if config.tech_stack.languages:
        tech_parts.append(", ".join(config.tech_stack.languages))
    if config.tech_stack.frameworks:
        tech_parts.append(", ".join(config.tech_stack.frameworks))
    if config.tech_stack.databases:
        tech_parts.append(", ".join(config.tech_stack.databases))
    table.add_row("Tech Stack", " | ".join(tech_parts) if tech_parts else "not specified")

    table.add_row(
        "Atlassian", "enabled" if config.atlassian.enabled else "disabled"
    )
    table.add_row(
        "LLM Gateway", "enabled" if config.llm_gateway.enabled else "disabled"
    )
    if config.non_negotiables:
        table.add_row("Non-negotiables", f"{len(config.non_negotiables)} rules")

    console.print()
    console.print(Panel(table, title="Configuration Summary", expand=False))


def _confirm_and_save(config: ForgeConfig, output_path: str) -> None:
    """Save config and optionally run generation."""
    from pathlib import Path

    from forge_cli.config_loader import save_config

    save_path = click.prompt("  Save config to", default=output_path)

    # Check for existing file
    if Path(save_path).exists():
        overwrite = click.confirm(
            f"  {save_path} exists. Overwrite?", default=False
        )
        if not overwrite:
            save_path = click.prompt("  Save config to (new path)")

    save_config(config, save_path)
    console.print(f"  [green]Saved to {save_path}[/green]")

    run_now = click.confirm("  Run forge now with this config?", default=True)
    if run_now:
        project_dir = click.prompt("  Project directory", default=".")
        config.project.directory = project_dir

        from forge_cli.generators.orchestrator import generate_all

        generate_all(config)
        console.print()
        console.print("[bold green]Forge generation complete![/bold green]")
