"""Interactive CLI wizard for project configuration."""

from __future__ import annotations

from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from forge_cli.config_loader import load_config, save_config
from forge_cli.config_schema import (
    AgentNamingConfig,
    AgentsConfig,
    AtlassianConfig,
    CostConfig,
    ExecutionStrategy,
    ForgeConfig,
    ProjectConfig,
    ProjectMode,
    TechStack,
    TeamProfile,
)

console = Console()

AGENT_DESCRIPTIONS = {
    "team-leader": "Orchestrates the entire team, decomposes tasks, manages iteration lifecycle",
    "scrum-master": "Sprint planning, backlog refinement, Jira/Confluence management, ceremonies",
    "research-strategist": "Technical research, strategy formulation, iteration planning, risk assessment",
    "architect": "System design, API contracts, architecture decisions, cross-cutting concerns",
    "backend-developer": "Server-side implementation, APIs, database logic, integrations",
    "frontend-engineer": "Full frontend implementation (UI + logic), suitable for lean teams",
    "frontend-developer": "Frontend logic, state management, API integration",
    "frontend-designer": "UI/UX design, wireframes, design system, component specs",
    "qa-engineer": "Test strategy, test implementation, quality gates, bug tracking",
    "devops-specialist": "CI/CD, infrastructure, Docker, deployment, monitoring",
    "security-tester": "Security audits, vulnerability scanning, auth review, OWASP compliance",
    "performance-engineer": "Load testing, profiling, optimization, benchmark targets",
    "documentation-specialist": "API docs, architecture docs, user guides, ADRs",
    "critic": "Independent review, gap analysis, quality critique, devil's advocate",
}


def _print_banner() -> None:
    banner = Text()
    banner.append("FORGE", style="bold cyan")
    banner.append(" — Agent Team Initializer", style="dim")
    console.print()
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))
    console.print()
    console.print(
        "[dim]Configure your Claude Code agent team. Forge generates the instruction files,\n"
        "CLAUDE.md, skills, and team-init-plan.md for your project workspace.[/dim]"
    )
    console.print()


def run_wizard(config_path: str | None = None, project_dir: str = ".") -> ForgeConfig:
    """Run the interactive configuration wizard."""
    _print_banner()

    # Load existing config if provided
    if config_path and Path(config_path).exists():
        config = load_config(config_path)
        console.print(f"[dim]Loaded existing config from {config_path}[/dim]")
    else:
        config = ForgeConfig()

    # Step 1: Project basics
    console.print("[bold]1. Project Setup[/bold]")
    console.print()

    description = questionary.text(
        "Project description (what are you building?):",
        default=config.project.description or "",
    ).ask()

    console.print()
    console.print("[dim]Enter your project requirements in detail.[/dim]")
    console.print("[dim]Describe features, constraints, tech preferences, anything the agents should know.[/dim]")
    console.print("[dim](Press Enter twice to finish)[/dim]")
    console.print()

    requirements_lines: list[str] = []
    empty_count = 0
    while True:
        line = questionary.text("", default="").ask()
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
            requirements_lines.append("")
        else:
            empty_count = 0
            requirements_lines.append(line)
    requirements = "\n".join(requirements_lines).strip()

    proj_type = questionary.select(
        "Project type:",
        choices=[
            questionary.Choice("New project (start fresh)", value="new"),
            questionary.Choice("Existing project (enhance/refactor)", value="existing"),
        ],
    ).ask()

    existing_path = ""
    if proj_type == "existing":
        existing_path = questionary.path(
            "Path to existing project:",
            default=project_dir,
        ).ask()
        project_dir = existing_path

    if proj_type == "new":
        project_dir = questionary.path(
            "Project workspace directory:",
            default=project_dir,
        ).ask()

    config.project = ProjectConfig(
        description=description or "",
        requirements=requirements,
        type=proj_type or "new",
        existing_project_path=existing_path or "",
        directory=project_dir,
    )

    # Step 2: Mode and Strategy
    console.print()
    console.print("[bold]2. Development Mode & Strategy[/bold]")
    console.print()

    mode = questionary.select(
        "Development mode:",
        choices=[
            questionary.Choice(
                "MVP — Working prototype, minimal tests, speed over polish",
                value="mvp",
            ),
            questionary.Choice(
                "Production Ready — CI/CD, >90% coverage, industrial standards",
                value="production-ready",
            ),
            questionary.Choice(
                "No Compromise — Zero tolerance, full security audit, launch-ready",
                value="no-compromise",
            ),
        ],
    ).ask()
    config.mode = ProjectMode(mode)

    strategy = questionary.select(
        "Execution strategy (how much human oversight?):",
        choices=[
            questionary.Choice(
                "Auto-Pilot — Agents make all decisions autonomously",
                value="auto-pilot",
            ),
            questionary.Choice(
                "Co-Pilot — Agents handle technical decisions, humans approve design choices",
                value="co-pilot",
            ),
            questionary.Choice(
                "Micro-Manage — Every significant decision needs human approval",
                value="micro-manage",
            ),
        ],
    ).ask()
    config.strategy = ExecutionStrategy(strategy)

    # Step 3: Cost
    console.print()
    console.print("[bold]3. Budget[/bold]")
    console.print()

    cost_input = questionary.text(
        "Max development cost in USD (or 'no-cap'):",
        default=str(config.cost.max_development_cost),
    ).ask()
    config.cost = CostConfig(max_development_cost=cost_input or "50")

    # Step 4: Tech Stack
    console.print()
    console.print("[bold]4. Tech Stack[/bold]")
    console.print("[dim]Leave empty for agents to decide based on requirements.[/dim]")
    console.print()

    languages = questionary.text(
        "Preferred languages (comma-separated):",
        default=", ".join(config.tech_stack.languages),
    ).ask()
    frameworks = questionary.text(
        "Preferred frameworks (comma-separated):",
        default=", ".join(config.tech_stack.frameworks),
    ).ask()
    databases = questionary.text(
        "Preferred databases (comma-separated):",
        default=", ".join(config.tech_stack.databases),
    ).ask()

    config.tech_stack = TechStack(
        languages=[x.strip() for x in (languages or "").split(",") if x.strip()],
        frameworks=[x.strip() for x in (frameworks or "").split(",") if x.strip()],
        databases=[x.strip() for x in (databases or "").split(",") if x.strip()],
    )

    # Step 5: Team Composition
    console.print()
    console.print("[bold]5. Agent Team Composition[/bold]")
    console.print()

    profile = questionary.select(
        "Team profile:",
        choices=[
            questionary.Choice(
                "Auto — Lean for MVP, Full for Production/No-Compromise",
                value="auto",
            ),
            questionary.Choice(
                "Lean — Core team (8 agents): leader, strategist, architect, backend, frontend, QA, devops, critic",
                value="lean",
            ),
            questionary.Choice(
                "Full — Complete team (12+ agents): adds designer, security, performance, docs",
                value="full",
            ),
            questionary.Choice(
                "Custom — Hand-pick your agents",
                value="custom",
            ),
        ],
    ).ask()

    config.agents.team_profile = TeamProfile(profile)

    if profile == "custom":
        all_agents = list(AGENT_DESCRIPTIONS.keys())
        selected = questionary.checkbox(
            "Select agents for your team:",
            choices=[
                questionary.Choice(
                    f"{agent} — {AGENT_DESCRIPTIONS[agent]}",
                    value=agent,
                    checked=agent in ("team-leader", "architect", "backend-developer"),
                )
                for agent in all_agents
            ],
        ).ask()
        config.agents.include = selected or []

    # Sub-agent spawning
    console.print()
    allow_spawning = questionary.confirm(
        "Allow agents to spawn sub-agents for parallel task execution?",
        default=config.agents.allow_sub_agent_spawning,
    ).ask()
    config.agents.allow_sub_agent_spawning = allow_spawning if allow_spawning is not None else True

    # Step 6: Atlassian Integration
    console.print()
    console.print("[bold]6. Project Management (Jira & Confluence)[/bold]")
    console.print()

    atlassian_enabled = questionary.confirm(
        "Enable Jira/Confluence integration for project tracking?",
        default=config.atlassian.enabled,
    ).ask()

    if atlassian_enabled:
        console.print()
        console.print("[dim]Agents will use Atlassian MCP to manage tickets, sprints, and documentation.[/dim]")
        console.print("[dim]You'll see real-time updates on your Jira board and living docs in Confluence.[/dim]")
        console.print()

        jira_url = questionary.text(
            "Jira base URL (e.g., https://yourteam.atlassian.net):",
            default=config.atlassian.jira_base_url,
        ).ask()
        jira_key = questionary.text(
            "Jira project key (e.g., PROJ):",
            default=config.atlassian.jira_project_key,
        ).ask()
        confluence_url = questionary.text(
            "Confluence base URL (same as Jira for cloud):",
            default=config.atlassian.confluence_base_url or (jira_url or ""),
        ).ask()
        confluence_space = questionary.text(
            "Confluence space key:",
            default=config.atlassian.confluence_space_key,
        ).ask()
        scrum = questionary.confirm(
            "Enable full Scrum ceremonies (sprint planning, standups, retros)?",
            default=config.atlassian.scrum_ceremonies,
        ).ask()

        config.atlassian = AtlassianConfig(
            enabled=True,
            jira_base_url=jira_url or "",
            jira_project_key=jira_key or "",
            confluence_base_url=confluence_url or "",
            confluence_space_key=confluence_space or "",
            create_sprint_board=True,
            create_confluence_space=True,
            scrum_ceremonies=scrum if scrum is not None else True,
        )
    else:
        config.atlassian = AtlassianConfig(enabled=False)

    # Step 7: Agent naming
    console.print()
    console.print("[bold]7. Agent Identity[/bold]")
    console.print()

    naming_enabled = questionary.confirm(
        "Give agents unique names for commits, Jira, and traceability?",
        default=config.agent_naming.enabled,
    ).ask()

    if naming_enabled:
        naming_style = questionary.select(
            "Agent naming style:",
            choices=[
                questionary.Choice(
                    "Creative — Cool, memorable names (e.g., 'Nova', 'Cipher', 'Blaze')",
                    value="creative",
                ),
                questionary.Choice(
                    "Codename — Military/spy style (e.g., 'Falcon', 'Shadow', 'Vortex')",
                    value="codename",
                ),
                questionary.Choice(
                    "Functional — Role-based names (e.g., 'BackendBot-1', 'QA-Prime')",
                    value="functional",
                ),
            ],
        ).ask()
        config.agent_naming = AgentNamingConfig(enabled=True, style=naming_style or "creative")
    else:
        config.agent_naming = AgentNamingConfig(enabled=False)

    # Step 8: Per-agent customization
    console.print()
    customize = questionary.confirm(
        "Customize individual agent behaviors? (Advanced)",
        default=False,
    ).ask()

    if customize:
        active_agents = config.get_active_agents()
        for agent in active_agents:
            if agent == "team-leader":
                continue
            console.print()
            console.print(f"[bold]{agent}[/bold]: {AGENT_DESCRIPTIONS.get(agent, 'Custom agent')}")
            custom = questionary.text(
                f"  Additional instructions for {agent} (or Enter to skip):",
                default=config.agents.custom_instructions.get(agent, ""),
            ).ask()
            if custom and custom.strip():
                config.agents.custom_instructions[agent] = custom.strip()

    # Summary
    _print_summary(config)

    # Confirm
    console.print()
    proceed = questionary.confirm("Generate files with this configuration?", default=True).ask()

    if not proceed:
        console.print("[yellow]Aborted. No files were generated.[/yellow]")
        raise SystemExit(0)

    # Save config
    config_save_path = Path(config.project.directory) / "forge-config.yaml"
    save_config(config, config_save_path)
    console.print(f"[dim]Configuration saved to {config_save_path}[/dim]")

    return config


def _print_summary(config: ForgeConfig) -> None:
    """Print a summary of the configuration."""
    console.print()
    console.print("[bold]Configuration Summary[/bold]")
    console.print()

    table = Table(show_header=False, border_style="dim")
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("Project", config.project.description)
    table.add_row("Directory", config.project.directory)
    table.add_row("Type", config.project.type)
    table.add_row("Mode", config.mode.value)
    table.add_row("Strategy", config.strategy.value)
    table.add_row("Budget", f"${config.cost.max_development_cost}")
    table.add_row("Team Profile", config.resolve_team_profile())
    table.add_row("Active Agents", ", ".join(config.get_active_agents()))
    table.add_row("Sub-agent Spawning", "Enabled" if config.agents.allow_sub_agent_spawning else "Disabled")
    table.add_row("Jira/Confluence", "Enabled" if config.atlassian.enabled else "Disabled")
    table.add_row("Agent Naming", f"Enabled ({config.agent_naming.style})" if config.agent_naming.enabled else "Disabled")

    if config.tech_stack.languages:
        table.add_row("Languages", ", ".join(config.tech_stack.languages))
    if config.tech_stack.frameworks:
        table.add_row("Frameworks", ", ".join(config.tech_stack.frameworks))
    if config.tech_stack.databases:
        table.add_row("Databases", ", ".join(config.tech_stack.databases))

    console.print(table)
