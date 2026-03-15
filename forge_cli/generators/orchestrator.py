"""Orchestrator — Coordinates all file generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from forge_cli.config_schema import ExecutionStrategy, ForgeConfig
from forge_cli.progress import ForgeProgress
from forge_cli.generators.agent_files import generate_agent_files
from forge_cli.generators.claude_md import generate_claude_md
from forge_cli.generators.mcp_config import generate_env_example, generate_mcp_config
from forge_cli.generators.settings_config import generate_settings_config
from forge_cli.generators.skills import generate_skills
from forge_cli.generators.team_init_plan import generate_team_init_plan

console = Console()


def _get_dry_run_provider() -> Any | None:
    """Return a FakeLLMProvider if FORGE_TEST_DRY_RUN=1, else None.

    This ensures dry-run mode NEVER makes real LLM requests — all calls
    go through llm-gateway's FakeLLMProvider.
    """
    import os
    if os.environ.get("FORGE_TEST_DRY_RUN", "0") != "1":
        return None
    try:
        from llm_gateway.testing import FakeLLMProvider
        return FakeLLMProvider()
    except ImportError:
        return None


def generate_all(
    config: ForgeConfig,
    llm_provider: Any | None = None,
) -> Any:
    """Generate all files for the project workspace.

    Args:
        config: Forge configuration.
        llm_provider: Optional LLM provider instance for refinement/summarization.
            In dry-run mode (FORGE_TEST_DRY_RUN=1), automatically uses
            FakeLLMProvider if no provider is given — guaranteeing zero
            real LLM requests.

    Returns:
        RefinementReport if refinement ran, else None.
    """
    # In dry-run mode, never make real LLM calls
    if llm_provider is None:
        llm_provider = _get_dry_run_provider()

    project_dir = Path(config.project.directory).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    active_agents = config.get_active_agents()
    progress = ForgeProgress(console)

    console.print()
    console.print(f"[bold]Generating files in [cyan]{project_dir}[/cyan][/bold]")
    console.print()

    # 0. Ensure .forge directory exists and .gitignore is updated
    from forge_cli.config_loader import ensure_forge_dir
    ensure_forge_dir(project_dir)

    # Save original requirements so re-runs are idempotent — the
    # summarizer always works from the user-authored text, not from
    # a previously derived summary.  We store the original on the
    # config object so it persists across calls.
    if not hasattr(config.project, "_original_requirements"):
        object.__setattr__(config.project, "_original_requirements", config.project.requirements)
    _original_requirements: str = getattr(config.project, "_original_requirements")

    with progress.live():
        # 0.5. Project context resolution — derive detailed requirements from
        # user-provided files/directories.  The summarized context replaces
        # config.project.requirements so all downstream generators use it.
        _has_context_sources = (
            config.project.context_files
            or config.project.plan_file
            or _original_requirements
        )
        if _has_context_sources:
            with progress.step("context", "Project context resolution"):
                from forge_cli.generators.context_summarizer import summarize_context
                # Reset to original so summarizer always gets user-authored input
                config.project.requirements = _original_requirements
                derived = summarize_context(
                    config, project_dir, llm_provider=llm_provider,
                    on_progress=progress.update,
                )
                # Strip the markdown header so generators get plain content
                _header = "# Project Context\n\n"
                if derived.startswith(_header):
                    derived = derived[len(_header):]
                config.project.requirements = derived
        else:
            progress.skip("context", "Project context resolution (no context sources)")

        # 1. Agent instruction files → .claude/agents/
        agents_dir = project_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        with progress.step("agents", f"Agent instruction files ({len(active_agents)} agents)", total_files=len(active_agents)):
            generate_agent_files(config, agents_dir, on_progress=progress.update)

        # 2. CLAUDE.md → project root
        with progress.step("claude_md", "CLAUDE.md"):
            generate_claude_md(config, project_dir)

        # 3. MCP configuration
        with progress.step("mcp", "MCP configuration (Playwright + integrations)"):
            generate_mcp_config(config, project_dir / ".claude")

        # 3.1. .env.example
        with progress.step("env", ".env.example"):
            generate_env_example(config, project_dir)

        # 3.5. Claude Code settings
        if config.strategy != ExecutionStrategy.MICRO_MANAGE:
            with progress.step("settings", "Claude Code settings (strategy permissions)"):
                generate_settings_config(config, project_dir / ".claude")
        else:
            progress.skip("settings", "Claude Code settings (micro-manage: uses defaults)")

        # 4. Skills
        skills_dir = project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_files = _count_skills(config)
        with progress.step("skills", f"Reusable skills ({skill_files} skills)", total_files=skill_files):
            generate_skills(config, skills_dir, on_progress=progress.update)

        # 5. team-init-plan.md
        with progress.step("init_plan", "team-init-plan.md"):
            generate_team_init_plan(config, project_dir)

        # 6. Hook scripts for checkpoint enforcement
        with progress.step("hooks", "Checkpoint hook scripts"):
            from forge_cli.generators.hooks import generate_hook_scripts
            forge_dir = project_dir / ".forge"
            generate_hook_scripts(config, forge_dir)

    # 7. Token report — build, display, and save
    try:
        from forge_cli.tokens import build_token_report, display_token_table, save_token_report
        token_report = build_token_report(config, project_dir)
        display_token_table(token_report, console)
        forge_dir = project_dir / ".forge"
        save_token_report(token_report, forge_dir)
    except ImportError:
        console.print("[dim]  Token report skipped (llm-gateway not available)[/dim]")
    except Exception as exc:
        console.print(f"[dim]  Token report skipped ({exc})[/dim]")

    console.print()
    return None


def _count_skills(config: ForgeConfig) -> int:
    """Count the number of skill files that will be generated."""
    count = 16  # base skills always generated (11 original + checkpoint + agent-init + respawn + handoff + context-reload)
    if config.agents.allow_sub_agent_spawning:
        count += 1  # spawn-agent
    if config.atlassian.enabled:
        count += 2  # jira-update, sprint-report
    if config.has_frontend_involvement():
        count += 1  # playwright-test
    return count


def run_refinement(
    config: ForgeConfig,
    project_dir: Path,
    llm_provider: Any | None = None,
) -> Any:
    """Run LLM refinement on previously generated files.

    Args:
        config: Forge configuration (refinement.enabled must be True).
        project_dir: Project directory containing generated files.
        llm_provider: Optional LLM provider instance.

    Returns:
        RefinementReport with per-file results.
    """
    if llm_provider is None:
        llm_provider = _get_dry_run_provider()

    from forge_cli.generators.refinement import refine_all
    from forge_cli.progress import ForgeRefinementProgress

    refinement_progress = ForgeRefinementProgress(console)
    report = refine_all(
        config, project_dir, llm_provider=llm_provider,
        progress=refinement_progress,
    )
    _save_refinement_report(report, project_dir, config)
    return report


def _save_refinement_report(
    report: Any,
    project_dir: Path,
    config: ForgeConfig,
) -> None:
    """Save refinement report to .forge/refinement-report.json and .md.

    The report includes per-file iteration details, suggestions, changes,
    scores, and next scope of improvement for the user to decide whether
    to run refine again.
    """
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)

    # JSON report
    report_data = report.to_dict()
    json_path = forge_dir / "refinement-report.json"
    json_path.write_text(json.dumps(report_data, indent=2))

    # Human-readable Markdown report
    md_lines: list[str] = [
        "# Forge Refinement Report",
        "",
        "## Summary",
        "",
        f"- **Total files processed**: {len(report.files)}",
        f"- **Files improved**: {report.files_improved}",
        f"- **Files already good**: {report.files_already_good}",
        f"- **All passed threshold ({config.refinement.score_threshold}%)**: "
        f"{'Yes' if report.all_passed else 'No'}",
        f"- **Total cost**: ${report.total_cost_usd:.4f}",
        f"- **Total LLM calls**: {report.total_llm_calls}",
        "",
    ]

    for file_result in report.files:
        md_lines.extend([
            f"## {file_result.file_path}",
            "",
            f"- **Type**: {file_result.file_type}",
            f"- **Initial score**: {file_result.initial_score}/100",
            f"- **Final score**: {file_result.final_score}/100",
            f"- **Cost**: ${file_result.total_cost_usd:.4f}",
            "",
            "### Iterations",
            "",
        ])

        for iteration in file_result.iterations:
            md_lines.extend([
                f"**Iteration {iteration.iteration}** — Score: {iteration.score}/100",
                "",
                f"> {iteration.reasoning}",
                "",
            ])

        # Improvement suggestions
        if file_result.final_score < config.refinement.score_threshold:
            md_lines.extend([
                "### Next Scope of Improvement",
                "",
                f"File is at {file_result.final_score}/100, below the "
                f"{config.refinement.score_threshold}% threshold. Running "
                "`forge refine` again may improve this file further.",
                "",
            ])

    # Token Impact section
    has_token_data = any(
        fr.initial_tokens > 0 or fr.final_tokens > 0
        for fr in report.files
    )
    if has_token_data:
        md_lines.extend([
            "## Token Impact",
            "",
            "| File | Before (tokens) | After (tokens) | Delta |",
            "|------|----------------|----------------|-------|",
        ])
        total_before = 0
        total_after = 0
        for file_result in report.files:
            if file_result.initial_tokens > 0 or file_result.final_tokens > 0:
                delta = file_result.final_tokens - file_result.initial_tokens
                sign = "+" if delta >= 0 else ""
                md_lines.append(
                    f"| {file_result.file_path} "
                    f"| {file_result.initial_tokens:,} "
                    f"| {file_result.final_tokens:,} "
                    f"| {sign}{delta:,} |"
                )
                total_before += file_result.initial_tokens
                total_after += file_result.final_tokens
        total_delta = total_after - total_before
        total_sign = "+" if total_delta >= 0 else ""
        md_lines.extend([
            f"| **Total** | **{total_before:,}** | **{total_after:,}** | **{total_sign}{total_delta:,}** |",
            "",
        ])

    md_lines.extend([
        "---",
        "",
        "*Run `forge refine` to continue improving files.*",
    ])

    md_path = forge_dir / "refinement-report.md"
    md_path.write_text("\n".join(md_lines))

    console.print(f"[green]  ✓[/green] Refinement report saved to .forge/")
