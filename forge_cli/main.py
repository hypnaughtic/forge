"""Forge CLI — Main entry point."""

import logging
from pathlib import Path

import click
from rich.console import Console

from forge_cli import __version__

console = Console()


def _configure_logging(verbose: bool = False) -> None:
    """Configure logging for forge and its dependencies.

    When verbose is False (default), suppresses all library logs so the user
    only sees the Rich progress UI.  When verbose is True, shows DEBUG-level
    output for forge internals and INFO for llm_gateway.
    """
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )
        # llm_gateway can be noisy — keep at INFO even in verbose mode
        logging.getLogger("llm_gateway").setLevel(logging.INFO)
    else:
        # Silence everything — the Rich progress display is the only UX
        logging.disable(logging.CRITICAL)


HELP_TEXT = f"""\n
  Forge — Project Initialization Tool for Claude Code Agent Teams v{__version__}

  Reads a forge.yaml and generates customized agent instruction
  files, CLAUDE.md, skills, strategy-enforced permissions, and
  team-init-plan.md in the target project.

  Usage:
    forge init                                          Build config interactively
    forge generate                                      Generate (auto-detect config)
    forge generate --config .forge/forge.yaml           Generate from explicit config
    forge refine                                        LLM scoring + iterative refinement
    forge start                                         Launch Claude with team init
    forge --config .forge/forge.yaml --validate-only    Validate config only

  Config auto-detection (in order):
    1. .forge/forge.yaml         (canonical location)
    2. forge.yaml                (project root)
    3. .forge/forge-config.yaml  (legacy)
    4. forge-config.yaml         (legacy)

  Generated output:
    .claude/agents/*.md        Agent instruction files (one per team member)
    .claude/skills/*.md        Reusable skill procedures
    .claude/mcp.json           MCP server configuration (Playwright + Atlassian)
    .claude/settings.json      Strategy-enforced tool permissions
                               (auto-pilot & co-pilot: all tools allowed;
                                micro-manage: not generated, all tools prompt)
    .forge/project-context.md  Summarized project context (if context_files set)
    .forge/refinement-report   Refinement report (JSON + Markdown, if refined)
    CLAUDE.md                  Team Leader context (project root)
    team-init-plan.md          Bootstrap plan for first Claude session

  Lifecycle:
    forge init → forge generate → forge refine → forge start

  Getting started:
    Option A — Interactive (recommended for new users):
      1. Run: forge init
      2. Follow the wizard (use Up/Down arrows to navigate between steps)
      3. Confirm and generate — or save the config for later

    Option B — Config file:
      1. Copy examples/forge.yaml and customize it
      2. Run: forge generate --project-dir ./my-project

    Then start building:
      forge start
        Launches an interactive Claude session with the team init prompt.
      OR run: claude
        Then tell Claude: "Read team-init-plan.md and initialize the team"

    To improve generated files with LLM scoring + refinement:
      forge refine

  forge.yaml reference:
  ─────────────────────
    project:
      description: str             Project description
      context_files: [str]         Paths to spec/context files or directories
                                   (directories scanned for .md/.txt/.yaml)
                                   Forge derives detailed requirements from these
      plan_file: str               Path to implementation plan (followed exactly)
      requirements: str            (deprecated — use context_files instead)
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

    git:
      ssh_key_path: str              SSH key for git auth (default: "")

    refinement:
      enabled: bool                                (default: false)
      provider: str                (default: local_claude)
      model: str                   (default: claude-opus-4-6)
      max_tokens: int              (default: 8192)
      score_threshold: int         Quality 0-100 (default: 90)
      max_iterations: int          (default: 5)
      max_concurrency: int         0=unlimited (default: 0)
      timeout_seconds: int         (default: 300)
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


def _resolve_config(config_path: str | None, project_dir: str = ".") -> str:
    """Resolve config path: use explicit path or auto-detect.

    Args:
        config_path: Explicit path from --config flag, or None.
        project_dir: Project directory for auto-detection.

    Returns:
        Resolved config path string.

    Raises:
        SystemExit: If no config found.
    """
    if config_path:
        return config_path

    from forge_cli.config_loader import find_config

    found = find_config(project_dir)
    if found:
        console.print(f"  [dim]Auto-detected config: {found}[/dim]")
        return str(found)

    console.print(
        "[red]No config file found. Run [bold]forge init[/bold] to create one, "
        "or pass [bold]--config PATH[/bold].[/red]"
    )
    raise SystemExit(1)


class ForgeGroup(click.Group):
    """Custom group that routes bare `forge --config` to the generate subcommand.

    This preserves backward compatibility: `forge --config foo.yaml` works
    without requiring `forge generate --config foo.yaml`.
    """

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        formatter.write("Usage: forge [COMMAND] [OPTIONS]\n")
        formatter.write(HELP_TEXT)

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        # If first arg starts with -- (not a subcommand name), route to generate
        if args and args[0].startswith("--") and args[0] != "--help" and args[0] != "--version":
            args = ["generate"] + args
        return super().parse_args(ctx, args)


@click.group(cls=ForgeGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="forge")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Forge — Generate agent instruction files for Claude Code CLI agent teams."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option("--config", "config_path", type=click.Path(exists=True), required=False, default=None, help="Path to forge.yaml (auto-detected if omitted)")
@click.option("--project-dir", type=click.Path(), default=".", help="Target project workspace directory")
@click.option("--validate-only", is_flag=True, help="Validate config and print summary without generating files")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show detailed technical logs")
def generate(config_path: str | None, project_dir: str, validate_only: bool, verbose: bool) -> None:
    """Generate agent files from a forge.yaml config."""
    _configure_logging(verbose)
    from forge_cli.config_loader import load_config

    resolved = _resolve_config(config_path, project_dir)

    try:
        config = load_config(resolved)
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise SystemExit(1)

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
    console.print("  1. Review generated files in .claude/agents/, CLAUDE.md, team-init-plan.md")
    console.print("  2. Start building:")
    console.print("     [cyan]forge start[/cyan]  — launches Claude with the team init prompt")
    console.print("     OR run [cyan]claude[/cyan] and tell it: \"Read team-init-plan.md and initialize the team\"")
    console.print("  3. To improve generated file quality: [cyan]forge refine[/cyan]")


@cli.command()
@click.option("--config", "config_path", type=click.Path(exists=True), required=False, default=None, help="Path to forge.yaml (auto-detected if omitted)")
@click.option("--project-dir", type=click.Path(), default=".", help="Project directory")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show detailed technical logs")
def refine(config_path: str | None, project_dir: str, verbose: bool) -> None:
    """Refine generated files using LLM scoring and iterative improvement.

    Scores each generated file against quality criteria and iteratively
    refines them until they meet the configured threshold (default 90%).
    Requires llm-gateway to be installed: pip install forge-init[refinement]
    """
    _configure_logging(verbose)
    from forge_cli.config_loader import load_config

    resolved = _resolve_config(config_path, project_dir)

    try:
        config = load_config(resolved)
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise SystemExit(1)

    config.project.directory = project_dir
    project_path = Path(project_dir).resolve()

    # Verify generated files exist
    agents_dir = project_path / ".claude" / "agents"
    if not agents_dir.exists() or not any(agents_dir.glob("*.md")):
        console.print(
            "[red]No generated files found. Run [bold]forge generate[/bold] first.[/red]"
        )
        raise SystemExit(1)

    # Always enable refinement for this command
    config.refinement.enabled = True

    console.print()
    console.print(f"[bold]Refining files in [cyan]{project_path}[/cyan][/bold]")
    console.print(f"  [dim]Threshold: {config.refinement.score_threshold}% | "
                  f"Max iterations: {config.refinement.max_iterations} | "
                  f"Cost limit: ${config.refinement.cost_limit_usd}[/dim]")
    console.print()

    from forge_cli.generators.orchestrator import run_refinement

    report = run_refinement(config, project_path)

    if report:
        console.print()
        console.print("[bold green]Refinement complete![/bold green]")
        console.print(f"  Files improved: {report.files_improved}")
        console.print(f"  Total cost: ${report.total_cost_usd:.4f}")
        if not report.all_passed:
            console.print(
                f"[yellow]  ⚠ Some files below "
                f"{config.refinement.score_threshold}% threshold[/yellow]"
            )
        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print("  1. Review refinement report: [cyan].forge/refinement-report.md[/cyan]")
        console.print("  2. Start building: [cyan]forge start[/cyan]")


@cli.command()
@click.option("--output", default=None, help="Output config file path (default: .forge/forge.yaml)")
def init(output: str | None) -> None:
    """Interactively build a forge.yaml configuration."""
    from forge_cli.config_loader import FORGE_DIR, CONFIG_FILENAME

    if output is None:
        output = str(Path(FORGE_DIR) / CONFIG_FILENAME)

    from forge_cli.init_wizard import run_wizard

    run_wizard(output)


@cli.command()
@click.option("--config", "config_path", type=click.Path(exists=True), required=False, default=None, help="Path to forge.yaml (auto-detected if omitted)")
@click.option("--project-dir", type=click.Path(), default=".", help="Project directory")
@click.option("--tmux/--no-tmux", default=None, help="Use tmux for split-pane agent monitoring (auto-detected)")
def start(config_path: str | None, project_dir: str, tmux: bool | None) -> None:
    """Start an interactive Claude CLI session with the team init prompt.

    Launches `claude` in your project directory with the instruction to read
    team-init-plan.md and initialize the team. When tmux is available, creates
    a named session for monitoring agent activity in split panes.
    """
    import os
    import shutil
    import subprocess

    _resolve_config(config_path, project_dir)

    # Verify team-init-plan.md exists
    project_path = Path(project_dir).resolve()
    init_plan = project_path / "team-init-plan.md"
    if not init_plan.exists():
        console.print(
            "[red]team-init-plan.md not found. Run [bold]forge generate[/bold] first.[/red]"
        )
        raise SystemExit(1)

    # Check claude CLI is available
    claude_bin = shutil.which("claude")
    if not claude_bin:
        console.print(
            "[red]Claude CLI not found. Install it first: "
            "https://docs.anthropic.com/en/docs/claude-code[/red]"
        )
        raise SystemExit(1)

    # Determine tmux availability
    tmux_bin = shutil.which("tmux")
    use_tmux = tmux if tmux is not None else (tmux_bin is not None)

    if use_tmux and not tmux_bin:
        console.print("[yellow]tmux not found. Falling back to direct Claude session.[/yellow]")
        use_tmux = False

    init_prompt = (
        "Read team-init-plan.md and initialize the team. "
        "Follow the startup sequence and begin Iteration 1."
    )

    if use_tmux:
        session_name = f"forge-{project_path.name}"

        console.print(f"[bold]Starting forge session [cyan]{session_name}[/cyan] in tmux[/bold]")
        console.print(f"  [dim]Project: {project_path}[/dim]")
        console.print(f"  [dim]Attach: tmux attach -t {session_name}[/dim]")
        console.print()

        # Kill existing session if present
        subprocess.run(
            [tmux_bin, "kill-session", "-t", session_name],
            capture_output=True,
        )

        # Create new tmux session with Claude as the main command
        subprocess.run(
            [
                tmux_bin, "new-session",
                "-d",  # detached
                "-s", session_name,
                "-c", str(project_path),
                "-x", "200", "-y", "50",
                claude_bin, init_prompt,
            ],
            check=True,
        )

        # Set session environment for agent teams
        subprocess.run(
            [tmux_bin, "set-environment", "-t", session_name,
             "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "1"],
            capture_output=True,
        )

        # Attach to the session
        os.execvp(tmux_bin, [tmux_bin, "attach", "-t", session_name])
    else:
        console.print(f"[bold]Starting Claude session in [cyan]{project_path}[/cyan][/bold]")
        console.print()

        # Hand over to claude — replaces this process entirely
        os.chdir(str(project_path))
        os.execvp(claude_bin, [claude_bin, init_prompt])


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
