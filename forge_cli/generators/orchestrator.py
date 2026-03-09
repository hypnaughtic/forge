"""Orchestrator — Coordinates all file generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from forge_cli.config_schema import ExecutionStrategy, ForgeConfig
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

    console.print()
    console.print(f"[bold]Generating files in [cyan]{project_dir}[/cyan][/bold]")
    console.print()

    # 0. Ensure .forge directory exists and .gitignore is updated
    from forge_cli.config_loader import ensure_forge_dir
    ensure_forge_dir(project_dir)

    # 0.5. Project context summarization (if context files or plan file provided)
    # Only triggers LLM summarization when there are actual files to process.
    # Requirements-only projects get a basic context without LLM calls.
    _has_context_sources = config.project.context_files or config.project.plan_file
    if _has_context_sources:
        from forge_cli.generators.context_summarizer import summarize_context
        summarize_context(config, project_dir, llm_provider=llm_provider)
        console.print("[green]  ✓[/green] Project context summarization")

    # 1. Agent instruction files → .claude/agents/
    agents_dir = project_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    generate_agent_files(config, agents_dir)
    console.print("[green]  ✓[/green] Agent instruction files")

    # 2. CLAUDE.md → project root
    generate_claude_md(config, project_dir)
    console.print("[green]  ✓[/green] CLAUDE.md")

    # 3. MCP configuration → .claude/mcp.json (Playwright always, Atlassian if enabled)
    generate_mcp_config(config, project_dir / ".claude")
    console.print("[green]  ✓[/green] MCP configuration")

    # 3.1. .env.example → project root (GH_TOKEN, Atlassian vars)
    generate_env_example(config, project_dir)
    if (project_dir / ".env.example").exists():
        console.print("[green]  ✓[/green] .env.example")

    # 3.5. Claude Code settings → .claude/settings.json (strategy-based permissions)
    generate_settings_config(config, project_dir / ".claude")
    if config.strategy != ExecutionStrategy.MICRO_MANAGE:
        console.print("[green]  ✓[/green] Claude Code settings (strategy permissions)")

    # 4. Skills → .claude/skills/
    skills_dir = project_dir / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    generate_skills(config, skills_dir)
    console.print("[green]  ✓[/green] Reusable skills")

    # 5. team-init-plan.md → project root
    generate_team_init_plan(config, project_dir)
    console.print("[green]  ✓[/green] team-init-plan.md")

    # 6. Optional LLM refinement
    refinement_report = None
    if config.refinement.enabled:
        from forge_cli.generators.refinement import refine_all

        refinement_report = refine_all(config, project_dir, llm_provider=llm_provider)
        console.print(
            f"[green]  ✓[/green] LLM refinement "
            f"({refinement_report.files_improved} files improved, "
            f"${refinement_report.total_cost_usd:.4f})"
        )
        if not refinement_report.all_passed:
            console.print(
                f"[yellow]  ⚠[/yellow] Some files below "
                f"{config.refinement.score_threshold}% threshold"
            )

        # Save refinement report to .forge/
        _save_refinement_report(refinement_report, project_dir, config)

    console.print()
    return refinement_report


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
                "`forge generate --refine` again may improve this file further.",
                "",
            ])

    md_lines.extend([
        "---",
        "",
        "*Run `forge generate --refine` to continue improving files.*",
    ])

    md_path = forge_dir / "refinement-report.md"
    md_path.write_text("\n".join(md_lines))

    console.print(f"[green]  ✓[/green] Refinement report saved to .forge/")
