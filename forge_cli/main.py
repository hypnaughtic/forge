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
    forge eval                                          Evaluate generated files (300+ assertions)
    forge eval --no-llm                                 Deterministic checks only (no LLM cost)
    forge start                                         Launch Claude with team init
    forge stop                                          Gracefully stop all agents and checkpoint
    forge resume                                        Resume a stopped session from checkpoints
    forge --config .forge/forge.yaml --validate-only    Validate config only

  Config auto-detection (in order):
    1. .forge/forge.yaml         (canonical location)
    2. forge.yaml                (project root)
    3. .forge/forge-config.yaml  (legacy)
    4. forge-config.yaml         (legacy)

  Generated output:
    .claude/agents/*.md        Agent instruction files (one per team member)
    .claude/skills/*.md        Reusable skill procedures (including /checkpoint)
    .claude/mcp.json           MCP server configuration (Playwright + Atlassian)
    .claude/settings.json      Strategy-enforced tool permissions + hooks config
                               (auto-pilot & co-pilot: all tools allowed;
                                micro-manage: not generated, all tools prompt)
    .forge/hooks/*.sh          Hook scripts for automatic checkpoint enforcement
    .forge/session.json        Session state (created by forge start)
    .forge/checkpoints/*.json  Agent checkpoint files (for stop/resume)
    .forge/project-context.md  Summarized project context (if context_files set)
    .forge/refinement-report   Refinement report (JSON + Markdown, if refined)
    .forge/benchmark.json      Eval benchmark data (if eval was run)
    .forge/benchmark.md        Eval benchmark report (human-readable)
    CLAUDE.md                  Team Leader context (project root)
    team-init-plan.md          Bootstrap plan for first Claude session

  Lifecycle:
    forge init → forge generate → forge refine → forge eval → forge start
    forge stop → (edit config, refine, etc.) → forge resume

  Getting started:
    Option A — Interactive (recommended for new users):
      1. Run: forge init
      2. Follow the wizard (use Up/Down arrows to navigate between steps)
      3. Confirm and generate — or save the config for later

    Option B — Config file:
      1. Copy examples/forge.yaml and customize it
      2. Run: forge generate --project-dir ./my-project

    Then start building:
      forge start                 Launch Claude with the team init prompt
      forge start --tmux          Launch in a tmux session (recommended)

    Session management (stop/resume across sessions):
      forge stop                  Gracefully stop all agents and checkpoint state
      forge stop --timeout 120    Wait up to 120s for agents to checkpoint
      forge resume                Resume from last checkpoint (detects file changes)
      forge resume --tmux         Resume in a tmux session

    To improve generated files with LLM scoring + refinement:
      forge refine

    To evaluate generated files against 300+ quality assertions:
      forge eval                  Full eval (deterministic + LLM grading)
      forge eval --no-llm         Deterministic checks only (instant, free)
      forge eval --optimize-descriptions   Also optimize skill trigger descriptions

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

        # Run eval validation after refinement
        console.print()
        console.print("[dim]Running eval validation...[/dim]")
        try:
            from forge_cli.evals.eval_runner import run_eval
            from forge_cli.evals.benchmark import aggregate_benchmark, save_benchmark

            eval_report = run_eval(project_path, config, use_llm=False)
            console.print(
                f"  Eval pass rate: "
                f"[{'green' if eval_report.overall_pass_rate >= 0.85 else 'yellow'}]"
                f"{eval_report.overall_pass_rate:.1%}[/]"
            )

            benchmark = aggregate_benchmark(eval_report, config.project.description[:60])
            forge_dir = project_path / ".forge"
            forge_dir.mkdir(parents=True, exist_ok=True)
            save_benchmark(benchmark, forge_dir)
        except Exception as e:
            console.print(f"  [dim]Eval validation skipped: {e}[/dim]")

        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print("  1. Review refinement report: [cyan].forge/refinement-report.md[/cyan]")
        console.print("  2. Run detailed eval: [cyan]forge eval[/cyan]")
        console.print("  3. Start building: [cyan]forge start[/cyan]")


@cli.command(name="eval")
@click.option("--config", "config_path", type=click.Path(exists=True), required=False, default=None, help="Path to forge.yaml (auto-detected if omitted)")
@click.option("--project-dir", type=click.Path(), default=".", help="Project directory")
@click.option("--no-llm", is_flag=True, help="Deterministic checks only (no LLM cost)")
@click.option("--optimize-descriptions", is_flag=True, help="Optimize skill descriptions for trigger accuracy")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show detailed technical logs")
def eval_cmd(config_path: str | None, project_dir: str, no_llm: bool, optimize_descriptions: bool, verbose: bool) -> None:
    """Evaluate generated files against quality assertions.

    Runs 350+ eval assertions (deterministic + LLM-judged) against
    all generated files to assess quality. Results are saved as
    benchmark.json and benchmark.md in .forge/.
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

    use_llm = not no_llm

    console.print()
    console.print(f"[bold]Evaluating files in [cyan]{project_path}[/cyan][/bold]")
    console.print(f"  [dim]LLM grading: {'enabled' if use_llm else 'disabled (deterministic only)'}[/dim]")
    console.print()

    from forge_cli.evals.eval_runner import run_eval
    from forge_cli.evals.benchmark import aggregate_benchmark, save_benchmark

    report = run_eval(project_path, config, use_llm=use_llm)

    # Display results
    console.print(f"[bold]Eval Results:[/bold]")
    console.print(f"  Overall pass rate: [{'green' if report.overall_pass_rate >= 0.85 else 'yellow' if report.overall_pass_rate >= 0.7 else 'red'}]{report.overall_pass_rate:.1%}[/]")
    console.print(f"  Files evaluated: {len(report.files)}")
    console.print(f"  Duration: {report.duration_seconds:.1f}s")
    if report.total_cost_usd > 0:
        console.print(f"  LLM cost: ${report.total_cost_usd:.4f}")
    console.print()

    # Show per-file results
    for file_result in sorted(report.files, key=lambda f: f.pass_rate):
        color = "green" if file_result.pass_rate >= 0.85 else "yellow" if file_result.pass_rate >= 0.7 else "red"
        failed = [e for e in file_result.expectations if not e.passed]
        console.print(f"  [{color}]{file_result.pass_rate:.0%}[/] {file_result.file_path}", end="")
        if failed:
            console.print(f" [dim]({len(failed)} failed)[/dim]")
            if verbose:
                for f in failed[:3]:
                    console.print(f"       [dim]- {f.text}: {f.evidence[:60]}[/dim]")
        else:
            console.print()

    # Save benchmark
    benchmark = aggregate_benchmark(report, config_name=config.project.description[:60])
    forge_dir = project_path / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)

    # Check for previous benchmark for comparison
    prev_path = forge_dir / "benchmark.json"
    if prev_path.exists():
        from forge_cli.evals.benchmark import compare_benchmarks
        benchmark = compare_benchmarks(benchmark, prev_path)
        if benchmark.comparison:
            delta = benchmark.comparison.delta
            console.print()
            console.print(f"  [dim]vs previous: {delta:+.1%}[/dim]")

    json_path, md_path = save_benchmark(benchmark, forge_dir)
    console.print()
    console.print(f"[bold green]Benchmark saved:[/bold green]")
    console.print(f"  JSON: [cyan]{json_path}[/cyan]")
    console.print(f"  Report: [cyan]{md_path}[/cyan]")

    # Optional: optimize descriptions
    if optimize_descriptions and use_llm:
        import asyncio
        from forge_cli.evals.description_optimizer import optimize_description
        from forge_cli.evals.eval_runner import _create_llm_client

        console.print()
        console.print("[bold]Optimizing skill descriptions...[/bold]")
        llm = _create_llm_client(config)

        skills_dir = project_path / ".claude" / "skills"
        if skills_dir.exists():
            for skill_path in sorted(skills_dir.glob("*.md")):
                try:
                    opt_report = asyncio.run(
                        optimize_description(skill_path, config, llm)
                    )
                    delta = opt_report.optimized_accuracy - opt_report.original_accuracy
                    if delta > 0:
                        # Update file with optimized description
                        content = skill_path.read_text()
                        from forge_cli.evals.description_optimizer import _update_description
                        new_content = _update_description(content, opt_report.optimized_description)
                        skill_path.write_text(new_content)
                        console.print(
                            f"  [green]+{delta:.0%}[/green] {skill_path.name}: "
                            f"'{opt_report.original_description[:40]}' -> "
                            f"'{opt_report.optimized_description[:40]}'"
                        )
                    else:
                        console.print(f"  [dim]={opt_report.original_accuracy:.0%}[/dim] {skill_path.name}: no improvement")
                except Exception as e:
                    console.print(f"  [red]Error optimizing {skill_path.name}: {e}[/red]")

            asyncio.run(llm.close())


@cli.command()
@click.option("--output", default=None, help="Output config file path (default: .forge/forge.yaml)")
def init(output: str | None) -> None:
    """Interactively build a forge.yaml configuration."""
    from forge_cli.config_loader import FORGE_DIR, CONFIG_FILENAME

    if output is None:
        output = str(Path(FORGE_DIR) / CONFIG_FILENAME)

    from forge_cli.init_wizard import run_wizard

    run_wizard(output)


def _generate_creative_name() -> str:
    """Generate a creative agent name for the team leader."""
    import random
    adjectives = [
        "swift", "bright", "keen", "bold", "sharp",
        "sage", "prime", "noble", "vivid", "agile",
        "steady", "lucid", "deft", "grand", "astute",
    ]
    nouns = [
        "falcon", "phoenix", "atlas", "cipher", "beacon",
        "nexus", "forge", "herald", "vanguard", "sentinel",
        "oracle", "corsair", "titan", "ember", "zenith",
    ]
    return f"{random.choice(adjectives)}-{random.choice(nouns)}"  # noqa: S311


def clean_session_state(forge_dir: Path) -> None:
    """Remove all ephemeral session state. Called at the start of every ``forge start``."""
    import shutil as _shutil

    paths_to_remove = [
        forge_dir / "session.json",
        forge_dir / "events-archive.jsonl",
        forge_dir / "token-report.json",
    ]
    dirs_to_remove = [
        forge_dir / "checkpoints",
        forge_dir / "events",
    ]

    for path in paths_to_remove:
        path.unlink(missing_ok=True)

    for dir_path in dirs_to_remove:
        if dir_path.exists():
            _shutil.rmtree(dir_path)

    (forge_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (forge_dir / "events").mkdir(parents=True, exist_ok=True)


@cli.command()
@click.option("--config", "config_path", type=click.Path(exists=True), required=False, default=None, help="Path to forge.yaml (auto-detected if omitted)")
@click.option("--project-dir", type=click.Path(), default=".", help="Project directory")
@click.option("--tmux/--no-tmux", default=None, help="Use tmux for split-pane agent monitoring (auto-detected)")
def start(config_path: str | None, project_dir: str, tmux: bool | None) -> None:
    """Start an interactive Claude CLI session with the team init prompt."""
    import os
    import shutil
    import subprocess

    resolved = _resolve_config(config_path, project_dir)

    project_path = Path(project_dir).resolve()
    init_plan = project_path / "team-init-plan.md"
    if not init_plan.exists():
        console.print("[red]team-init-plan.md not found. Run [bold]forge generate[/bold] first.[/red]")
        raise SystemExit(1)

    claude_bin = shutil.which("claude")
    if not claude_bin:
        console.print("[red]Claude CLI not found.[/red]")
        raise SystemExit(1)

    tmux_bin = shutil.which("tmux")
    use_tmux = tmux if tmux is not None else (tmux_bin is not None)
    if use_tmux and not tmux_bin:
        console.print("[yellow]tmux not found. Falling back to direct Claude session.[/yellow]")
        use_tmux = False

    from forge_cli.checkpoint import compute_config_hash, compute_instruction_hashes
    from forge_cli.models import SessionState
    from forge_cli.session import write_event, write_session
    from forge_cli.generators.hooks import generate_hook_scripts
    from uuid import uuid4
    from datetime import datetime, timezone

    forge_dir = project_path / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)

    clean_session_state(forge_dir)

    try:
        from forge_cli.config_loader import load_config
        config = load_config(resolved)
        generate_hook_scripts(config, forge_dir)
    except Exception:
        generate_hook_scripts(None, forge_dir)

    tl_name = _generate_creative_name()
    tl_checkpoint_path = f".forge/checkpoints/team-leader/{tl_name}.json"

    write_event(forge_dir, {
        "type": "agent_registered",
        "event": "agent_registered",
        "agent_name": tl_name,
        "agent_type": "team-leader",
        "parent_agent": None,
        "checkpoint_path": tl_checkpoint_path,
    })

    config_file = Path(resolved)
    session = SessionState(
        forge_session_id=str(uuid4()),
        project_dir=str(project_path),
        project_name=project_path.name,
        config_hash=compute_config_hash(config_file),
        started_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        status="running",
        instruction_file_hashes=compute_instruction_hashes(project_path),
        tmux_session_name=f"forge-{project_path.name}" if use_tmux else None,
    )
    write_session(session, forge_dir)

    init_prompt = (
        f"You are {tl_name}, the team-leader. "
        "Read team-init-plan.md and initialize the team. "
        "FIRST ACTION: Run /agent-init detect. "
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


@cli.command()
@click.option("--project-dir", type=click.Path(), default=".", help="Project directory")
@click.option("--timeout", default=60, help="Seconds to wait for graceful stop")
def stop(project_dir: str, timeout: int) -> None:
    """Signal all agents to gracefully stop and checkpoint."""
    import shutil
    from datetime import datetime, timezone

    from forge_cli.session import (
        clear_stop_signal, materialize_session, read_session, signal_stop,
        wait_for_agents_stopped, write_session,
    )

    project_path = Path(project_dir).resolve()
    forge_dir = project_path / ".forge"

    session = read_session(forge_dir)
    if session is None:
        console.print("[red]No session found. Is forge running?[/red]")
        raise SystemExit(1)

    session = materialize_session(forge_dir)

    if session.status not in ("running",):
        console.print(f"[yellow]Session status is '{session.status}', not 'running'.[/yellow]")

    console.print("[bold]Stopping forge session...[/bold]")

    signal_stop(forge_dir)
    console.print("  Stop signal sent (STOP_REQUESTED)")

    tmux_bin = shutil.which("tmux")
    if session.tmux_session_name and tmux_bin:
        import subprocess
        try:
            subprocess.run(
                [tmux_bin, "send-keys", "-t", f"{session.tmux_session_name}:0",
                 "Stop working for the day. All agents must run /handoff complete and stop.", "Enter"],
                capture_output=True, timeout=5,
            )
            console.print("  Stop message sent to Team Leader")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass

    console.print(f"  Waiting for agents to stop (timeout: {timeout}s)...")
    checkpoints_dir = forge_dir / "checkpoints"
    stopped, timed_out = wait_for_agents_stopped(
        checkpoints_dir,
        agent_tree=session.agent_tree,
        timeout=float(timeout),
    )

    if timed_out:
        console.print(f"  [yellow]Timed out waiting for: {', '.join(timed_out)}[/yellow]")
        # Force-kill tmux session if it exists
        if session.tmux_session_name and tmux_bin:
            import subprocess
            subprocess.run(
                [tmux_bin, "kill-session", "-t", session.tmux_session_name],
                capture_output=True,
            )
            console.print("  Forced tmux session kill")
    else:
        console.print(f"  All agents stopped ({len(stopped)} agents)")

    # Update session state
    session.status = "stopped"
    session.stop_reason = "explicit"
    session.updated_at = datetime.now(timezone.utc).isoformat()
    write_session(session, forge_dir)

    # Clean up sentinel
    clear_stop_signal(forge_dir)

    # Kill tmux session (agents have checkpointed, session is no longer needed)
    if session.tmux_session_name and tmux_bin:
        import subprocess
        subprocess.run(
            [tmux_bin, "kill-session", "-t", session.tmux_session_name],
            capture_output=True,
        )

    console.print()
    console.print("[bold green]Session stopped.[/bold green]")
    console.print(f"  {len(stopped)} agents checkpointed")
    if timed_out:
        console.print(f"  {len(timed_out)} agents timed out (will use last periodic checkpoint)")
    console.print(f"  Checkpoints: {checkpoints_dir}")
    console.print()
    console.print("  Resume with: [cyan]forge resume[/cyan]")


@cli.command()
@click.option("--config", "config_path", type=click.Path(exists=True), required=False, default=None, help="Path to forge.yaml (auto-detected if omitted)")
@click.option("--project-dir", type=click.Path(), default=".", help="Project directory")
@click.option("--tmux/--no-tmux", default=None, help="Use tmux for split-pane agent monitoring")
def resume(config_path: str | None, project_dir: str, tmux: bool | None) -> None:
    """Resume a previously stopped forge session from checkpoints."""
    import os
    import shutil
    import subprocess
    from datetime import datetime, timezone

    from forge_cli.checkpoint import (
        compute_instruction_hashes,
        detect_instruction_changes,
        read_all_checkpoints,
        validate_checkpoints_against_tree,
    )
    from forge_cli.session import (
        build_resume_prompt,
        materialize_session,
        read_session,
        write_session,
    )

    project_path = Path(project_dir).resolve()
    forge_dir = project_path / ".forge"

    session = read_session(forge_dir)
    if session is None:
        console.print("[red]No session found. Run [bold]forge start[/bold] first.[/red]")
        raise SystemExit(1)

    session = materialize_session(forge_dir)

    if session.status not in ("stopped", "running"):
        console.print(f"[yellow]Session status is '{session.status}'. Expected 'stopped' or 'running' (crash recovery).[/yellow]")

    checkpoints_dir = forge_dir / "checkpoints"
    checkpoints = read_all_checkpoints(checkpoints_dir)

    if session.agent_tree:
        orphans, missing, ghosts = validate_checkpoints_against_tree(
            checkpoints, session.agent_tree, checkpoints_dir,
        )
        if orphans:
            console.print(f"  [yellow]Orphan checkpoints: {', '.join(orphans)}[/yellow]")
        if ghosts:
            console.print(f"  [dim]Ghost agents: {', '.join(ghosts)}[/dim]")
        if missing:
            console.print(f"  [yellow]Missing checkpoints: {', '.join(missing)}[/yellow]")

    console.print("[bold]Resuming forge session[/bold]")
    console.print(f"  Session: {session.forge_session_id[:8]}...")
    console.print(f"  Status: {session.status}")
    console.print(f"  Agents with checkpoints: {len(checkpoints)}")

    # Detect instruction file changes
    current_hashes = compute_instruction_hashes(project_path)
    changes = detect_instruction_changes(
        session.instruction_file_hashes, current_hashes,
    )
    if changes:
        console.print(f"  [yellow]Instruction files changed: {len(changes)} files[/yellow]")
        for path, change_type in changes.items():
            console.print(f"    {change_type}: {path}")

    # If config changed, suggest running forge generate
    if config_path:
        from forge_cli.config_loader import load_config
        from forge_cli.checkpoint import compute_config_hash
        new_hash = compute_config_hash(Path(config_path))
        if new_hash != session.config_hash:
            console.print("  [yellow]Config file has changed since last session.[/yellow]")
            console.print("  [dim]Consider running 'forge generate' to regenerate instruction files.[/dim]")

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
        console.print("[yellow]tmux not found. Falling back to direct session.[/yellow]")
        use_tmux = False

    # Build resume prompt
    resume_prompt = build_resume_prompt(session, checkpoints, changes)

    # Update session state
    session.status = "running"
    session.updated_at = datetime.now(timezone.utc).isoformat()
    session.instruction_file_hashes = current_hashes
    if use_tmux:
        session.tmux_session_name = f"forge-{project_path.name}"
    write_session(session, forge_dir)

    if use_tmux:
        session_name = f"forge-{project_path.name}"

        console.print()
        console.print(f"[bold]Resuming in tmux session [cyan]{session_name}[/cyan][/bold]")

        # Kill existing session if present
        subprocess.run(
            [tmux_bin, "kill-session", "-t", session_name],
            capture_output=True,
        )

        # Create new tmux session with resume prompt
        subprocess.run(
            [
                tmux_bin, "new-session",
                "-d",
                "-s", session_name,
                "-c", str(project_path),
                "-x", "200", "-y", "50",
                claude_bin, resume_prompt,
            ],
            check=True,
        )

        subprocess.run(
            [tmux_bin, "set-environment", "-t", session_name,
             "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "1"],
            capture_output=True,
        )

        os.execvp(tmux_bin, [tmux_bin, "attach", "-t", session_name])
    else:
        console.print()
        console.print(f"[bold]Resuming Claude session in [cyan]{project_path}[/cyan][/bold]")
        console.print()

        os.chdir(str(project_path))
        os.execvp(claude_bin, [claude_bin, resume_prompt])


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
