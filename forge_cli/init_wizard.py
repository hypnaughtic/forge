"""Interactive configuration wizard for forge init.

Uses prompt_toolkit for full readline-style text editing (cursor movement,
home/end, word navigation) and supports navigating between steps via 'back'.
"""

from __future__ import annotations

import sys
from pathlib import Path

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


def _pt_prompt(message: str, default: str = "", **kwargs: object) -> str:
    """Prompt with prompt_toolkit for full cursor/editing support.

    Falls back to click.prompt() in non-TTY environments (e.g., testing).
    Uses sys.stdin.isatty() directly so tests can patch _is_interactive for
    the command-level guard while still falling back to click.prompt.
    """
    if not sys.stdin.isatty():
        return click.prompt(message, default=default, **kwargs)

    try:
        from prompt_toolkit import prompt as pt_prompt_fn
        from prompt_toolkit.formatted_text import HTML

        suffix = f" [{default}]" if default else ""
        result = pt_prompt_fn(
            HTML(f"  <b>{message}</b>{suffix}: "),
            default=default,
        )
        return result
    except (ImportError, EOFError):
        return click.prompt(message, default=default, **kwargs)


def _pt_confirm(message: str, default: bool = True) -> bool:
    """Confirm prompt with prompt_toolkit.

    Falls back to click.confirm() in non-TTY or if prompt_toolkit unavailable.
    """
    if not sys.stdin.isatty():
        return click.confirm(message, default=default)

    try:
        from prompt_toolkit import prompt as pt_prompt_fn
        from prompt_toolkit.formatted_text import HTML

        default_str = "Y/n" if default else "y/N"
        result = pt_prompt_fn(
            HTML(f"  <b>{message}</b> [{default_str}]: "),
            default="y" if default else "n",
        )
        if not result.strip():
            return default
        return result.strip().lower() in ("y", "yes", "true", "1")
    except (ImportError, EOFError):
        return click.confirm(message, default=default)


def _pt_choice(message: str, choices: list[str], default: str = "") -> str:
    """Choice prompt with prompt_toolkit and validation.

    Falls back to click.prompt() in non-TTY.
    """
    if not sys.stdin.isatty():
        return click.prompt(message, type=click.Choice(choices), default=default)

    try:
        from prompt_toolkit import prompt as pt_prompt_fn
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.validation import Validator

        validator = Validator.from_callable(
            lambda text: text.strip() in choices or text.strip() == "",
            error_message=f"Choose from: {', '.join(choices)}",
        )
        choices_str = "/".join(choices)
        suffix = f" [{default}]" if default else ""
        result = pt_prompt_fn(
            HTML(f"  <b>{message}</b> ({choices_str}){suffix}: "),
            default=default,
            validator=validator,
        )
        return result.strip() or default
    except (ImportError, EOFError):
        return click.prompt(message, type=click.Choice(choices), default=default)


def _pt_int(message: str, default: int = 0, min_val: int = 0, max_val: int = 999) -> int:
    """Integer prompt with prompt_toolkit and validation.

    Falls back to click.prompt() in non-TTY.
    """
    if not sys.stdin.isatty():
        return click.prompt(message, type=click.IntRange(min_val, max_val), default=default)

    try:
        from prompt_toolkit import prompt as pt_prompt_fn
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.validation import Validator

        def _validate(text: str) -> bool:
            if not text.strip():
                return True  # use default
            try:
                val = int(text.strip())
                return min_val <= val <= max_val
            except ValueError:
                return False

        validator = Validator.from_callable(
            _validate,
            error_message=f"Enter a number between {min_val} and {max_val}",
        )
        result = pt_prompt_fn(
            HTML(f"  <b>{message}</b> [{default}]: "),
            default=str(default),
            validator=validator,
        )
        return int(result.strip()) if result.strip() else default
    except (ImportError, EOFError):
        return click.prompt(message, type=click.IntRange(min_val, max_val), default=default)


# Sentinel value to indicate "go back to previous step"
_BACK = "__BACK__"


def run_wizard(output_path: str) -> ForgeConfig:
    """Run the interactive configuration wizard.

    Supports navigating back to previous steps by typing 'back'.

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
            "[bold]Forge — Interactive Configuration Builder[/bold]\n"
            "[dim]Type 'back' at any prompt to return to the previous step.[/dim]",
            expand=False,
        )
    )

    # Step functions in order
    step_fns = [
        _prompt_project,
        _prompt_mode,
        _prompt_strategy,
        _prompt_tech_stack,
        _prompt_agents_wrapper,
        _prompt_atlassian,
        _prompt_llm_gateway,
        _prompt_non_negotiables,
    ]
    results: list[object] = [None] * len(step_fns)
    step_idx = 0

    try:
        while step_idx < len(step_fns):
            try:
                results[step_idx] = step_fns[step_idx]()
                step_idx += 1
            except _BackSignal:
                if step_idx > 0:
                    step_idx -= 1
                    console.print("[dim]  Going back...[/dim]")
                else:
                    console.print("[dim]  Already at first step.[/dim]")
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Aborted.[/yellow]")
        raise SystemExit(130)

    project = results[0]
    mode = results[1]
    strategy = results[2]
    tech_stack = results[3]
    agents_cfg, naming_cfg, cost_cfg = results[4]
    atlassian = results[5]
    llm_gateway = results[6]
    non_negotiables = results[7]

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


class _BackSignal(Exception):
    """Raised when user types 'back' to go to previous step."""


def _check_back(value: str) -> str:
    """Check if user typed 'back' and raise _BackSignal if so."""
    if value.strip().lower() == "back":
        raise _BackSignal()
    return value


def _prompt_project() -> ProjectConfig:
    """Step 1/8: Project details."""
    console.print("\n  [bold]Step 1/8: Project Details[/bold]")
    console.print("  " + "─" * 24)

    description = ""
    while not description.strip():
        description = _check_back(_pt_prompt("Project description"))
        if not description.strip():
            console.print("  [red]Description is required.[/red]")

    requirements = _check_back(
        _pt_prompt("Detailed requirements (Enter to skip)", default="")
    )

    # Context files
    console.print("  [dim]Provide paths to plan/spec/context files or directories.[/dim]")
    console.print("  [dim]These help forge understand your project better.[/dim]")
    context_raw = _check_back(
        _pt_prompt("Context files (comma-separated paths, Enter to skip)", default="")
    )
    context_files = [s.strip() for s in context_raw.split(",") if s.strip()] if context_raw.strip() else []

    project_type = _check_back(
        _pt_choice("Project type", ["new", "existing"], default="new")
    )

    existing_path = ""
    if project_type == "existing":
        existing_path = _check_back(_pt_prompt("Path to existing project"))

    return ProjectConfig(
        description=description.strip(),
        requirements=requirements.strip(),
        context_files=context_files,
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

    choice = _check_back(str(_pt_int("Choice", default=1, min_val=1, max_val=3)))
    idx = int(choice) - 1 if choice.strip().isdigit() else 0
    return [ProjectMode.MVP, ProjectMode.PRODUCTION_READY, ProjectMode.NO_COMPROMISE][idx]


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

    choice = _check_back(str(_pt_int("Choice", default=2, min_val=1, max_val=3)))
    idx = int(choice) - 1 if choice.strip().isdigit() else 1
    return [
        ExecutionStrategy.AUTO_PILOT,
        ExecutionStrategy.CO_PILOT,
        ExecutionStrategy.MICRO_MANAGE,
    ][idx]


def _prompt_tech_stack() -> TechStack:
    """Step 4/8: Tech stack."""
    console.print("\n  [bold]Step 4/8: Tech Stack[/bold]")
    console.print("  " + "─" * 20)

    def _parse_list(raw: str) -> list[str]:
        return [s.strip() for s in raw.split(",") if s.strip()] if raw.strip() else []

    languages = _parse_list(_check_back(
        _pt_prompt("Languages (comma-separated, Enter to skip)", default="")
    ))
    frameworks = _parse_list(_check_back(
        _pt_prompt("Frameworks (comma-separated, Enter to skip)", default="")
    ))
    databases = _parse_list(_check_back(
        _pt_prompt("Databases (comma-separated, Enter to skip)", default="")
    ))
    infrastructure = _parse_list(_check_back(
        _pt_prompt("Infrastructure (comma-separated, Enter to skip)", default="")
    ))

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

    profile_choice = _check_back(
        _pt_choice("Team profile", ["auto", "lean", "full", "custom"], default="auto")
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
        raw = _check_back(_pt_prompt("Include agents (comma-separated)"))
        include = [s.strip() for s in raw.split(",") if s.strip()]

    spawning = _pt_confirm("Allow sub-agent spawning?", default=True)

    naming_choice = _check_back(
        _pt_choice("Agent naming style", ["creative", "functional", "codename", "off"], default="creative")
    )
    naming_enabled = naming_choice != "off"
    naming_style = naming_choice if naming_enabled else "creative"

    max_cost = _pt_int("Max development cost in USD", default=50, min_val=1, max_val=10000)

    agents_cfg = AgentsConfig(
        team_profile=profile,
        include=include,
        allow_sub_agent_spawning=spawning,
    )
    naming_cfg = AgentNamingConfig(enabled=naming_enabled, style=naming_style)
    cost_cfg = CostConfig(max_development_cost=max_cost)

    return agents_cfg, naming_cfg, cost_cfg


def _prompt_agents_wrapper() -> tuple[AgentsConfig, AgentNamingConfig, CostConfig]:
    """Wrapper for _prompt_agents to work with step navigation."""
    return _prompt_agents(ProjectMode.MVP)


def _prompt_atlassian() -> AtlassianConfig:
    """Step 6/8: Atlassian integration."""
    console.print("\n  [bold]Step 6/8: Atlassian Integration[/bold]")
    console.print("  " + "─" * 31)

    enabled = _pt_confirm("Enable Jira/Confluence integration?", default=False)
    if not enabled:
        return AtlassianConfig(enabled=False)

    jira_key = _check_back(_pt_prompt("Jira project key", default=""))
    jira_url = _check_back(_pt_prompt("Jira base URL", default=""))
    confluence_key = _check_back(_pt_prompt("Confluence space key", default=""))
    confluence_url = _check_back(_pt_prompt("Confluence base URL", default=""))

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

    enabled = _pt_confirm("Enable llm-gateway mandate in generated files?", default=True)
    return LLMGatewayConfig(enabled=enabled)


def _prompt_non_negotiables() -> list[str]:
    """Step 8/8: Non-negotiables."""
    console.print("\n  [bold]Step 8/8: Non-Negotiables (optional)[/bold]")
    console.print("  " + "─" * 35)
    console.print("  Enter absolute requirements (one per line, empty line to finish):")

    rules: list[str] = []
    while True:
        rule = _pt_prompt(">", default="")
        if not rule.strip():
            break
        if rule.strip().lower() == "back":
            raise _BackSignal()
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
    if config.project.context_files:
        table.add_row("Context files", f"{len(config.project.context_files)} files/dirs")
    if config.non_negotiables:
        table.add_row("Non-negotiables", f"{len(config.non_negotiables)} rules")

    console.print()
    console.print(Panel(table, title="Configuration Summary", expand=False))


def _confirm_and_save(config: ForgeConfig, output_path: str) -> None:
    """Save config and optionally run generation."""
    from forge_cli.config_loader import ensure_forge_dir, save_config

    save_path = _pt_prompt("Save config to", default=output_path)

    # Check for existing file
    if Path(save_path).exists():
        overwrite = _pt_confirm(f"{save_path} exists. Overwrite?", default=False)
        if not overwrite:
            save_path = _pt_prompt("Save config to (new path)")

    # Ensure .forge dir exists and .gitignore is updated
    project_dir = str(Path(save_path).parent)
    if Path(save_path).parent.name == ".forge":
        project_dir = str(Path(save_path).parent.parent)
    ensure_forge_dir(project_dir)

    save_config(config, save_path)
    console.print(f"  [green]Saved to {save_path}[/green]")

    run_now = _pt_confirm("Run forge now with this config?", default=True)
    if run_now:
        proj_dir = _pt_prompt("Project directory", default=".")
        config.project.directory = proj_dir

        from forge_cli.generators.orchestrator import generate_all

        generate_all(config)
        console.print()
        console.print("[bold green]Forge generation complete![/bold green]")
        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print("  1. Review the generated files in .claude/agents/")
        console.print("  2. Run [cyan]forge start[/cyan] OR [cyan]claude[/cyan] in your project directory")
        console.print("  3. Tell Claude: [dim]\"Read team-init-plan.md and initialize the team\"[/dim]")
