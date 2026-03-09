"""Forge CLI — Main entry point."""

import click
from rich.console import Console

from forge_cli import __version__

console = Console()


class ForgeCommand(click.Command):
    """Custom command that prints pre-formatted help text."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        formatter.write("Usage: forge [OPTIONS]\n")
        formatter.write(HELP_TEXT)
        self.format_options(ctx, formatter)


HELP_TEXT = f"""\n
  Forge — Project Initialization Tool for Claude Code Agent Teams v{__version__}

  Reads a forge-config.yaml and generates customized agent instruction
  files, CLAUDE.md, skills, strategy-enforced permissions, and
  team-init-plan.md in the target project.

  Usage:
    forge init                                          Build config interactively
    forge --config forge-config.yaml                    Generate from config
    forge --config forge-config.yaml --project-dir ./my-project
    forge --config forge-config.yaml --validate-only
    forge --config forge-config.yaml --refine

  Generated output:
    .claude/agents/*.md        Agent instruction files (one per team member)
    .claude/skills/*.md        Reusable skill procedures
    .claude/mcp.json           MCP server configuration (Playwright + Atlassian)
    .claude/settings.json      Strategy-enforced tool permissions
                               (auto-pilot & co-pilot: all tools allowed;
                                micro-manage: not generated, all tools prompt)
    CLAUDE.md                  Team Leader context (project root)
    team-init-plan.md          Bootstrap plan for first Claude session

  Getting started:
    Option A — Interactive (recommended for new users):
      1. Run: forge init
      2. Follow the 8-step wizard to configure your project
      3. Confirm and generate — or save the config for later

    Option B — Config file:
      1. Copy examples/forge-config.yaml and customize it
      2. Run: forge --config forge-config.yaml --project-dir ./my-project

    Then:
      1. cd into your project and run: claude
      2. Tell Claude: "Read team-init-plan.md and initialize the team"

  forge init:
  ──────────
    Interactive configuration builder. Walks you through every option
    step by step: project details, mode, strategy, tech stack, team
    configuration, Atlassian integration, LLM gateway, and non-negotiables.
    Shows a summary for confirmation, saves the config, and optionally
    runs generation immediately.

  forge-config.yaml reference:
  ─────────────────────────────
    project:
      description: str             Project description
      requirements: str            Detailed requirements
      type: new|existing           Project type (default: new)
      existing_project_path: str   Path if type=existing
      directory: str               Project directory (default: .)

    mode: mvp|production-ready|no-compromise      (default: mvp)
      mvp              70% quality, happy-path tests, lean team (8 agents)
      production-ready 90% quality, >90% coverage, full team (12 agents)
      no-compromise    100% quality, exhaustive tests, full team (12 agents)

    strategy: auto-pilot|co-pilot|micro-manage    (default: co-pilot)
      auto-pilot       Full autonomy, all decisions made by agents, no prompts.
                       Generates .claude/settings.json allowing all tools.
      co-pilot         Full tool access (edit, bash, write, etc.), agents only
                       ask human for architecture/scope/domain decisions.
                       Generates .claude/settings.json allowing all tools.
      micro-manage     Every significant decision needs approval. No settings.json
                       generated — Claude Code defaults prompt for all tools.

    cost:
      max_development_cost: int    Max dev cost in USD (default: 50)

    agents:
      team_profile: auto|lean|full|custom          (default: auto)
      include: [str]               Agent list (for team_profile: custom)
      exclude: [str]               Agents to exclude
      additional: [str]            Extra agents to add
      allow_sub_agent_spawning: bool               (default: true)
      custom_instructions:
        agent-name: str            Per-agent custom instructions

    tech_stack:
      languages: [str]             e.g. [python, typescript]
      frameworks: [str]            e.g. [fastapi, react]
      databases: [str]             e.g. [postgresql, redis]
      infrastructure: [str]        e.g. [docker, kubernetes]

    atlassian:
      enabled: bool                                (default: true)
      jira_project_key: str        Jira project key
      jira_base_url: str           Jira base URL
      confluence_space_key: str    Confluence space key
      confluence_base_url: str     Confluence base URL
      create_sprint_board: bool                    (default: true)
      create_confluence_space: bool                (default: true)
      scrum_ceremonies: bool                       (default: true)

    agent_naming:
      enabled: bool                                (default: true)
      style: creative|functional|codename          (default: creative)

    llm_gateway:
      enabled: bool                                (default: true)
      local_claude_model: str      (default: claude-sonnet-4-20250514)
      enable_local_claude: bool                    (default: true)
      cost_tracking: bool                          (default: true)

    refinement:
      enabled: bool                                (default: false)
      provider: str                (default: local_claude)
      model: str                   (default: claude-opus-4-6)
      max_tokens: int              (default: 8192)
      score_threshold: int         Quality 0-100 (default: 90)
      max_iterations: int          (default: 5)
      max_concurrency: int         0=unlimited (default: 0)
      timeout_seconds: int         (default: 180)
      cost_limit_usd: float        (default: 10.0)

    non_negotiables: [str]         Absolute requirements list

  Available agents:
  ─────────────────
    team-leader              Orchestrates work, reviews deliverables (always)
    research-strategist      Analyzes requirements, plans approach
    architect                System design, API contracts, data models
    backend-developer        Backend services implementation
    frontend-engineer        UI/UX implementation (lean profile)
    frontend-designer        UI/UX design specialist (full profile)
    frontend-developer       Frontend implementation (full profile)
    qa-engineer              Testing and validation
    devops-specialist        Infrastructure and deployment
    security-tester          Security testing (full profile)
    performance-engineer     Performance optimization (full profile)
    documentation-specialist Technical docs (full profile)
    critic                   Quality assurance, evaluates work
    scrum-master             Jira management (auto-added if atlassian.enabled)

  Minimal config:
  ───────────────
    project:
      description: My project
      type: new
    mode: mvp
    strategy: co-pilot
"""


@click.command(cls=ForgeCommand)
@click.version_option(__version__, prog_name="forge")
@click.option("--config", "config_path", type=click.Path(exists=True), required=True, help="Path to forge-config.yaml")
@click.option("--project-dir", type=click.Path(), default=".", help="Target project workspace directory")
@click.option("--validate-only", is_flag=True, help="Validate config and print summary without generating files")
@click.option("--refine/--no-refine", default=None, help="Override config refinement.enabled")
def cli(config_path: str, project_dir: str, validate_only: bool, refine: bool | None) -> None:
    """Forge — Generate agent instruction files for Claude Code CLI agent teams."""
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
