"""Interactive configuration wizard for forge init.

Uses prompt_toolkit for full readline-style text editing (cursor movement,
home/end, word navigation) and supports navigating between steps via
up-arrow (go back) and down-arrow (proceed/accept).
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
    WorkspaceConfig,
    WorkspaceType,
)

console = Console()

# Sentinel value returned by prompt when user presses Up arrow (go back)
_BACK_SENTINEL = "__BACK__"


def _is_interactive() -> bool:
    """Check if stdin is an interactive terminal."""
    return sys.stdin.isatty()


def _make_nav_bindings():
    """Create key bindings for step navigation.

    Up arrow: go back to previous step (returns _BACK_SENTINEL).
    Down arrow: accept current input (same as Enter).
    """
    try:
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.keys import Keys
    except ImportError:
        return None

    kb = KeyBindings()

    @kb.add(Keys.Up)
    def _go_back(event):
        event.app.exit(result=_BACK_SENTINEL)

    @kb.add(Keys.Down)
    def _go_forward(event):
        event.current_buffer.validate_and_handle()

    return kb


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

        kb = _make_nav_bindings()
        suffix = f" [{default}]" if default else ""
        result = pt_prompt_fn(
            HTML(f"  <b>{message}</b>{suffix}: "),
            default=default,
            key_bindings=kb,
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

        kb = _make_nav_bindings()
        default_str = "Y/n" if default else "y/N"
        result = pt_prompt_fn(
            HTML(f"  <b>{message}</b> [{default_str}]: "),
            default="y" if default else "n",
            key_bindings=kb,
        )
        if result == _BACK_SENTINEL:
            return result  # type: ignore[return-value]
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

        kb = _make_nav_bindings()
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
            key_bindings=kb,
        )
        if result == _BACK_SENTINEL:
            return result
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

        kb = _make_nav_bindings()

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
            key_bindings=kb,
        )
        if result == _BACK_SENTINEL:
            return result  # type: ignore[return-value]
        return int(result.strip()) if result.strip() else default
    except (ImportError, EOFError):
        return click.prompt(message, type=click.IntRange(min_val, max_val), default=default)


def run_wizard(output_path: str) -> ForgeConfig:
    """Run the interactive configuration wizard.

    Supports step navigation: press Up arrow to go back, Down arrow to proceed.

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
            "[dim]Up arrow: go back  |  Down arrow / Enter: proceed[/dim]",
            expand=False,
        )
    )

    # Step functions in order
    step_fns = [
        _prompt_project,
        _prompt_mode,
        _prompt_strategy,
        _prompt_tech_stack,
        _prompt_workspace,
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
    workspace = results[4]
    agents_cfg, naming_cfg, cost_cfg = results[5]
    atlassian = results[6]
    llm_gateway = results[7]
    non_negotiables = results[8]

    config = ForgeConfig(
        project=project,
        mode=mode,
        strategy=strategy,
        cost=cost_cfg,
        agents=agents_cfg,
        tech_stack=tech_stack,
        workspace=workspace,
        atlassian=atlassian,
        agent_naming=naming_cfg,
        llm_gateway=llm_gateway,
        non_negotiables=non_negotiables,
    )

    _show_summary(config)
    _confirm_and_save(config, output_path)

    return config


class _BackSignal(Exception):
    """Raised when user presses Up arrow to go to previous step."""


def _check_back(value: object) -> str:
    """Check if value is the back sentinel and raise _BackSignal if so."""
    if value == _BACK_SENTINEL:
        raise _BackSignal()
    return str(value)


class _IntraStepBack(Exception):
    """Raised within _run_fields to go to the previous field.

    If at the first field, this is re-raised as _BackSignal to go to the
    previous step.
    """


def _run_fields(field_fns: list) -> list:
    """Run a sequence of field-prompt functions with intra-step back navigation.

    Each function in field_fns takes no arguments and returns a value.
    If any function raises _BackSignal (via _check_back), we go back to the
    previous field. If already at the first field, we propagate _BackSignal
    to go back to the previous step.

    Returns a list of results, one per field function.
    """
    results: list = [None] * len(field_fns)
    idx = 0
    while idx < len(field_fns):
        try:
            results[idx] = field_fns[idx]()
            idx += 1
        except _BackSignal:
            if idx > 0:
                idx -= 1
                console.print("[dim]  ↑ previous field[/dim]")
            else:
                raise  # propagate to step-level navigation
    return results


def _prompt_project() -> ProjectConfig:
    """Step 1/9: Project details."""
    console.print("\n  [bold]Step 1/9: Project Details[/bold]")
    console.print("  " + "─" * 24)

    def _get_description() -> str:
        desc = ""
        while not desc.strip():
            desc = _check_back(_pt_prompt("Project description"))
            if not desc.strip():
                console.print("  [red]Description is required.[/red]")
        return desc

    def _get_plan_file() -> str:
        console.print("  [dim]If you have a detailed plan, provide the path. Agents will follow it exactly.[/dim]")
        return _check_back(
            _pt_prompt("Plan file (path to implementation plan, Enter to skip)", default="")
        ).strip()

    def _get_context_files() -> list[str]:
        console.print("  [dim]Provide paths to spec/context files or directories for additional context.[/dim]")
        raw = _check_back(
            _pt_prompt("Context files (comma-separated paths, Enter to skip)", default="")
        )
        return [s.strip() for s in raw.split(",") if s.strip()] if raw.strip() else []

    def _get_project_type() -> str:
        return _check_back(
            _pt_choice("Project type", ["new", "existing"], default="new")
        )

    results = _run_fields([
        _get_description,
        _get_plan_file,
        _get_context_files,
        _get_project_type,
    ])

    description, plan_file, context_files, project_type = results

    existing_path = ""
    if project_type == "existing":
        existing_path = _check_back(_pt_prompt("Path to existing project"))

    return ProjectConfig(
        description=description.strip(),
        context_files=context_files,
        plan_file=plan_file,
        type=project_type,
        existing_project_path=existing_path,
    )


def _prompt_mode() -> ProjectMode:
    """Step 2/9: Quality mode."""
    console.print("\n  [bold]Step 2/9: Quality Mode[/bold]")
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
    """Step 3/9: Execution strategy."""
    console.print("\n  [bold]Step 3/9: Execution Strategy[/bold]")
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
    """Step 4/9: Tech stack."""
    console.print("\n  [bold]Step 4/9: Tech Stack[/bold]")
    console.print("  " + "─" * 20)

    def _parse_list(raw: str) -> list[str]:
        return [s.strip() for s in raw.split(",") if s.strip()] if raw.strip() else []

    def _get_languages() -> list[str]:
        return _parse_list(_check_back(
            _pt_prompt("Languages (comma-separated, Enter to skip)", default="")
        ))

    def _get_frameworks() -> list[str]:
        return _parse_list(_check_back(
            _pt_prompt("Frameworks (comma-separated, Enter to skip)", default="")
        ))

    def _get_databases() -> list[str]:
        return _parse_list(_check_back(
            _pt_prompt("Databases (comma-separated, Enter to skip)", default="")
        ))

    def _get_infrastructure() -> list[str]:
        return _parse_list(_check_back(
            _pt_prompt("Infrastructure (comma-separated, Enter to skip)", default="")
        ))

    results = _run_fields([
        _get_languages,
        _get_frameworks,
        _get_databases,
        _get_infrastructure,
    ])

    return TechStack(
        languages=results[0],
        frameworks=results[1],
        databases=results[2],
        infrastructure=results[3],
    )


def _prompt_workspace() -> WorkspaceConfig:
    """Step 5/9: Workspace type."""
    console.print("\n  [bold]Step 5/9: Workspace Type[/bold]")
    console.print("  " + "─" * 23)

    options = [
        ("single-repo", "Single git repository, single project"),
        ("monorepo", "Single git repository, multiple packages (auto-detected)"),
        ("workspace", "Multiple git repositories under one directory"),
    ]
    for i, (name, desc) in enumerate(options, 1):
        console.print(f"    {i}. [cyan]{name}[/cyan] — {desc}")

    choice = _check_back(str(_pt_int("Choice", default=1, min_val=1, max_val=3)))
    idx = int(choice) - 1 if choice.strip().isdigit() else 0
    workspace_type = [
        WorkspaceType.SINGLE_REPO,
        WorkspaceType.MONOREPO,
        WorkspaceType.WORKSPACE,
    ][idx]

    return WorkspaceConfig(type=workspace_type)


def _prompt_agents(
    mode: ProjectMode,
) -> tuple[AgentsConfig, AgentNamingConfig, CostConfig]:
    """Step 6/9: Team configuration."""
    console.print("\n  [bold]Step 6/9: Team Configuration[/bold]")
    console.print("  " + "─" * 28)

    # Mutable state shared across field closures
    _state: dict = {}

    def _get_profile() -> TeamProfile:
        choice = _check_back(
            _pt_choice("Team profile", ["auto", "lean", "full", "custom"], default="auto")
        )
        profile = TeamProfile(choice)
        _state["profile"] = profile
        return profile

    def _get_include() -> list[str]:
        if _state.get("profile") == TeamProfile.CUSTOM:
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
            return [s.strip() for s in raw.split(",") if s.strip()]
        return []

    def _get_spawning() -> bool:
        val = _pt_confirm("Allow sub-agent spawning?", default=True)
        _check_back(val)
        return val

    def _get_naming() -> tuple[bool, str]:
        choice = _check_back(
            _pt_choice("Agent naming style", ["creative", "functional", "codename", "off"], default="creative")
        )
        enabled = choice != "off"
        style = choice if enabled else "creative"
        return enabled, style

    def _get_cost() -> int:
        val = _pt_int("Max development cost in USD", default=50, min_val=1, max_val=10000)
        _check_back(val)
        return int(val)

    results = _run_fields([
        _get_profile,
        _get_include,
        _get_spawning,
        _get_naming,
        _get_cost,
    ])

    profile, include, spawning, (naming_enabled, naming_style), max_cost = results

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
    """Step 7/9: Atlassian integration."""
    console.print("\n  [bold]Step 7/9: Atlassian Integration[/bold]")
    console.print("  " + "─" * 31)

    enabled = _pt_confirm("Enable Jira/Confluence integration?", default=False)
    if enabled == _BACK_SENTINEL:
        raise _BackSignal()
    if not enabled:
        return AtlassianConfig(enabled=False)

    def _jira_key() -> str:
        return _check_back(_pt_prompt("Jira project key", default=""))

    def _jira_url() -> str:
        return _check_back(_pt_prompt("Jira base URL", default=""))

    def _conf_key() -> str:
        return _check_back(_pt_prompt("Confluence space key", default=""))

    def _conf_url() -> str:
        return _check_back(_pt_prompt("Confluence base URL", default=""))

    results = _run_fields([_jira_key, _jira_url, _conf_key, _conf_url])

    return AtlassianConfig(
        enabled=True,
        jira_project_key=results[0],
        jira_base_url=results[1],
        confluence_space_key=results[2],
        confluence_base_url=results[3],
    )


def _prompt_llm_gateway() -> LLMGatewayConfig:
    """Step 8/9: LLM Gateway."""
    console.print("\n  [bold]Step 8/9: LLM Gateway[/bold]")
    console.print("  " + "─" * 21)

    enabled = _pt_confirm("Enable llm-gateway mandate in generated files?", default=True)
    return LLMGatewayConfig(enabled=enabled)


def _prompt_non_negotiables() -> list[str]:
    """Step 9/9: Non-negotiables."""
    console.print("\n  [bold]Step 9/9: Non-Negotiables (optional)[/bold]")
    console.print("  " + "─" * 35)
    console.print("  Enter absolute requirements (one per line, empty line to finish):")

    rules: list[str] = []
    while True:
        rule = _pt_prompt(">", default="")
        if rule == _BACK_SENTINEL:
            raise _BackSignal()
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

    table.add_row("Workspace", config.workspace.type.value)

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
        console.print("  1. Review generated files in .claude/agents/, CLAUDE.md, team-init-plan.md")
        console.print("  2. Start building:")
        console.print("     [cyan]forge start[/cyan]  — launches Claude with the team init prompt")
        console.print("     OR run [cyan]claude[/cyan] and tell it: \"Read team-init-plan.md and initialize the team\"")
        console.print("  3. To improve generated file quality: [cyan]forge refine[/cyan]")
