"""Token counting utilities for Forge context management.

Uses llm-gateway for provider-aware exact token counting.
All reporting uses exact counts. Compaction triggering in hooks
uses a heuristic estimate (bytes/4) for performance.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from llm_gateway import count_tokens as gateway_count_tokens

logger = logging.getLogger(__name__)


def count_tokens(text: str, provider: str = "anthropic") -> int:
    """Count tokens using llm-gateway's provider-aware tokenizer."""
    return gateway_count_tokens(text, provider=provider)


CLAUDE_SYSTEM_PROMPT_TOKENS = 2000


def estimate_global_claude_md_tokens(provider: str = "anthropic") -> int:
    """Read ~/.claude/CLAUDE.md if present, count tokens."""
    path = Path.home() / ".claude" / "CLAUDE.md"
    if not path.exists():
        return 0
    try:
        return count_tokens(path.read_text(), provider=provider)
    except OSError:
        return 0


@dataclass
class FileTokenCount:
    """Token count for a single generated file."""

    file_path: str
    file_type: str  # "agent", "claude_md", "skill", "plan", "global_claude_md"
    tokens: int
    agent_type: str | None = None


@dataclass
class AgentContextBudget:
    """Context usage at startup — exact token counts, no percentages."""

    agent_type: str
    agent_file_tokens: int
    claude_md_tokens: int
    team_init_plan_tokens: int  # non-zero only for team-leader
    system_overhead_tokens: int
    total_startup_tokens: int  # sum of all above


@dataclass
class TokenReport:
    """Complete token report for all generated files."""

    files: list[FileTokenCount] = field(default_factory=list)
    agent_budgets: list[AgentContextBudget] = field(default_factory=list)
    total_generated_tokens: int = 0
    compaction_threshold_tokens: int = 100_000
    timestamp: str = ""
    provider: str = "anthropic"
    tokenizer_name: str = "anthropic"


def build_token_report(
    config: object,
    project_dir: Path,
    provider: str = "anthropic",
) -> TokenReport:
    """Build token report by reading ALL generated files from disk.

    Reads: .claude/agents/*.md, CLAUDE.md, team-init-plan.md,
    .claude/skills/*.md, ~/.claude/CLAUDE.md.
    """
    from forge_cli.config_schema import ForgeConfig

    if not isinstance(config, ForgeConfig):
        logger.warning("config is not ForgeConfig, using defaults")
        threshold = 100_000
    else:
        threshold = config.compaction.compaction_threshold_tokens

    files: list[FileTokenCount] = []
    total_tokens = 0

    # Count agent files
    agents_dir = project_dir / ".claude" / "agents"
    if agents_dir.exists():
        for md_file in sorted(agents_dir.glob("*.md")):
            tokens = count_tokens(md_file.read_text(), provider=provider)
            agent_type = md_file.stem
            files.append(FileTokenCount(
                file_path=str(md_file.relative_to(project_dir)),
                file_type="agent",
                tokens=tokens,
                agent_type=agent_type,
            ))
            total_tokens += tokens

    # Count CLAUDE.md
    claude_md = project_dir / "CLAUDE.md"
    claude_md_tokens = 0
    if claude_md.exists():
        claude_md_tokens = count_tokens(claude_md.read_text(), provider=provider)
        files.append(FileTokenCount(
            file_path="CLAUDE.md",
            file_type="claude_md",
            tokens=claude_md_tokens,
        ))
        total_tokens += claude_md_tokens

    # Count team-init-plan.md
    plan_file = project_dir / "team-init-plan.md"
    plan_tokens = 0
    if plan_file.exists():
        plan_tokens = count_tokens(plan_file.read_text(), provider=provider)
        files.append(FileTokenCount(
            file_path="team-init-plan.md",
            file_type="plan",
            tokens=plan_tokens,
        ))
        total_tokens += plan_tokens

    # Count skills
    skills_dir = project_dir / ".claude" / "skills"
    skills_total = 0
    if skills_dir.exists():
        for md_file in sorted(skills_dir.glob("*.md")):
            tokens = count_tokens(md_file.read_text(), provider=provider)
            files.append(FileTokenCount(
                file_path=str(md_file.relative_to(project_dir)),
                file_type="skill",
                tokens=tokens,
            ))
            skills_total += tokens
            total_tokens += tokens

    # Global CLAUDE.md
    global_tokens = estimate_global_claude_md_tokens(provider=provider)
    if global_tokens > 0:
        files.append(FileTokenCount(
            file_path="~/.claude/CLAUDE.md",
            file_type="global_claude_md",
            tokens=global_tokens,
        ))

    # Build per-agent context budgets
    agent_budgets: list[AgentContextBudget] = []
    for fc in files:
        if fc.file_type == "agent" and fc.agent_type:
            is_tl = fc.agent_type == "team-leader"
            system_overhead = CLAUDE_SYSTEM_PROMPT_TOKENS + global_tokens
            startup = (
                fc.tokens
                + claude_md_tokens
                + (plan_tokens if is_tl else 0)
                + system_overhead
            )
            agent_budgets.append(AgentContextBudget(
                agent_type=fc.agent_type,
                agent_file_tokens=fc.tokens,
                claude_md_tokens=claude_md_tokens,
                team_init_plan_tokens=plan_tokens if is_tl else 0,
                system_overhead_tokens=system_overhead,
                total_startup_tokens=startup,
            ))

    return TokenReport(
        files=files,
        agent_budgets=agent_budgets,
        total_generated_tokens=total_tokens,
        compaction_threshold_tokens=threshold,
        timestamp=datetime.now(UTC).isoformat(),
        provider=provider,
        tokenizer_name=provider,
    )


def display_token_table(report: TokenReport, console: object) -> None:
    """Rich table: Agent | Agent File | CLAUDE.md | System | Startup Tokens.

    Header shows tokenizer name. Footer shows compaction threshold from config.
    No percentages — exact token counts only.
    """
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        return

    if not isinstance(console, Console):
        return

    table = Table(
        title=f"Context Usage at Startup ({report.tokenizer_name} tokenizer — exact)",
        show_footer=True,
    )
    table.add_column("Agent", footer_style="bold")
    table.add_column("Agent File", justify="right")
    table.add_column("CLAUDE.md", justify="right")
    table.add_column("System", justify="right")
    table.add_column("Startup Tokens", justify="right", footer_style="bold")

    total_startup = 0
    for budget in report.agent_budgets:
        plan_note = ""
        if budget.team_init_plan_tokens > 0:
            plan_note = f" +plan:{budget.team_init_plan_tokens:,}"
        table.add_row(
            budget.agent_type,
            f"{budget.agent_file_tokens:,}",
            f"{budget.claude_md_tokens:,}{plan_note}",
            f"{budget.system_overhead_tokens:,}",
            f"{budget.total_startup_tokens:,}",
        )
        total_startup += budget.total_startup_tokens

    # Skills row
    skills_tokens = sum(f.tokens for f in report.files if f.file_type == "skill")
    if skills_tokens > 0:
        table.add_row(
            "Skills (on-demand)",
            f"{skills_tokens:,}",
            "—",
            "—",
            f"{skills_tokens:,}",
        )

    table.columns[0].footer = "Total"
    table.columns[4].footer = f"{total_startup + skills_tokens:,}"

    console.print(table)
    console.print(
        f"  Tokenizer: {report.tokenizer_name} (exact) via llm-gateway\n"
        f"  Compaction threshold: {report.compaction_threshold_tokens:,} tokens\n"
        f"  Total generated content: {report.total_generated_tokens:,} tokens "
        f"across {len(report.files)} files"
    )


def save_token_report(report: TokenReport, forge_dir: Path) -> Path:
    """Write .forge/token-report.json."""
    forge_dir.mkdir(parents=True, exist_ok=True)
    path = forge_dir / "token-report.json"
    data = {
        "timestamp": report.timestamp,
        "provider": report.provider,
        "tokenizer_name": report.tokenizer_name,
        "compaction_threshold_tokens": report.compaction_threshold_tokens,
        "total_generated_tokens": report.total_generated_tokens,
        "files": [
            {
                "file_path": f.file_path,
                "file_type": f.file_type,
                "tokens": f.tokens,
                "agent_type": f.agent_type,
            }
            for f in report.files
        ],
        "agent_budgets": [
            {
                "agent_type": b.agent_type,
                "agent_file_tokens": b.agent_file_tokens,
                "claude_md_tokens": b.claude_md_tokens,
                "team_init_plan_tokens": b.team_init_plan_tokens,
                "system_overhead_tokens": b.system_overhead_tokens,
                "total_startup_tokens": b.total_startup_tokens,
            }
            for b in report.agent_budgets
        ],
    }
    path.write_text(json.dumps(data, indent=2))
    return path
