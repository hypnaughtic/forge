"""LLM-powered post-generation refinement for forge output files.

Scores generated .md files against quality criteria and iteratively
refines them until they meet a configurable threshold (default 90%).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, Field as PydanticField

from forge_cli.config_schema import ForgeConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response models (structured output from LLM)
# ---------------------------------------------------------------------------

class FileScore(BaseModel):
    """LLM evaluation of a generated file."""

    score: int = PydanticField(ge=0, le=100)
    reasoning: str
    suggestions: list[str]


class RefinedContent(BaseModel):
    """LLM-refined file content."""

    content: str
    changes_made: list[str]


# ---------------------------------------------------------------------------
# Reporting dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RefinementIteration:
    iteration: int
    score: int
    reasoning: str
    cost_usd: float

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "score": self.score,
            "reasoning": self.reasoning,
            "cost_usd": self.cost_usd,
        }


@dataclass
class FileRefinementResult:
    file_path: str
    file_type: str  # "agent" | "claude_md" | "team_init_plan" | "skill"
    initial_score: int
    final_score: int
    iterations: list[RefinementIteration] = field(default_factory=list)
    total_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "initial_score": self.initial_score,
            "final_score": self.final_score,
            "iterations": [it.to_dict() for it in self.iterations],
            "total_cost_usd": self.total_cost_usd,
        }


@dataclass
class RefinementReport:
    files: list[FileRefinementResult] = field(default_factory=list)
    total_cost_usd: float = 0.0
    total_llm_calls: int = 0
    files_improved: int = 0
    files_already_good: int = 0
    all_passed: bool = True

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_files": len(self.files),
                "files_improved": self.files_improved,
                "files_already_good": self.files_already_good,
                "all_passed": self.all_passed,
                "total_cost_usd": self.total_cost_usd,
                "total_llm_calls": self.total_llm_calls,
            },
            "files": [f.to_dict() for f in self.files],
        }


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class CostLimitExceededError(Exception):
    """Raised when cumulative LLM cost exceeds the configured limit."""


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_project_context(config: ForgeConfig) -> str:
    """Build a concise project context string from config."""
    agents = config.get_active_agents()
    parts = [
        f"Project: {config.project.description}",
        f"Requirements: {config.project.requirements}",
        f"Mode: {config.mode.value}",
        f"Strategy: {config.strategy.value}",
        f"Team profile: {config.resolve_team_profile()}",
    ]
    if config.tech_stack.languages:
        parts.append(f"Languages: {', '.join(config.tech_stack.languages)}")
    if config.tech_stack.frameworks:
        parts.append(f"Frameworks: {', '.join(config.tech_stack.frameworks)}")
    if config.tech_stack.databases:
        parts.append(f"Databases: {', '.join(config.tech_stack.databases)}")
    parts.append(f"Agents: {', '.join(agents)}")
    if config.non_negotiables:
        parts.append(f"Non-negotiables: {'; '.join(config.non_negotiables)}")
    return "\n".join(parts)


def _build_score_prompt(
    content: str,
    config: ForgeConfig,
    file_path: str,
    file_type: str,
) -> str:
    """Build the scoring prompt for a file."""
    context = _build_project_context(config)
    return f"""You are evaluating a generated agent instruction file for quality.

PROJECT CONTEXT:
{context}

FILE: {file_path} (type: {file_type})

CONTENT:
{content}

SCORING CRITERIA (score 0-100, unified):
1. Completeness — Does it cover all responsibilities for this role/file type? (25 pts)
2. Config fidelity — Does it reflect the project config (mode, strategy, tech stack, agents)? (25 pts)
3. Specificity — Does it use project-specific details from the config above? (20 pts)
4. Clarity & Actionability — Are instructions clear enough for an AI agent to follow? (20 pts)
5. Consistency — Is it internally consistent and compatible with team structure? (10 pts)

IMPORTANT RULES:
- `$ARGUMENTS` is a Claude skill template variable — do NOT penalize its presence.
- Do NOT penalize for file length, density, or template-style formatting.
- Do NOT penalize for shared/base protocol sections being similar across agent files.
- A file that mentions the project's tech stack, requirements, mode, and agents by name IS project-specific — score accordingly.
- Focus on whether the content is USEFUL for an AI agent building this specific project.
- Only suggest improvements that would materially help an agent do its job better.

Return a structured response with:
- score: integer 0-100
- reasoning: 2-3 sentences explaining the score
- suggestions: list of 3-5 specific, actionable improvements (not generic observations)"""


def _build_refine_prompt(
    content: str,
    config: ForgeConfig,
    file_path: str,
    file_type: str,
    score_feedback: FileScore,
) -> str:
    """Build the refinement prompt for a file."""
    context = _build_project_context(config)
    suggestions_text = "\n".join(f"- {s}" for s in score_feedback.suggestions)
    return f"""You are improving a generated agent instruction file to score above 90/100.

PROJECT CONTEXT (use these details to make content project-specific):
{context}

FILE: {file_path} (type: {file_type})
PREVIOUS SCORE: {score_feedback.score}/100

FEEDBACK: {score_feedback.reasoning}

SUGGESTIONS TO ADDRESS:
{suggestions_text}

CURRENT CONTENT:
{content}

RULES:
- Return the COMPLETE improved file content (not a diff).
- ONLY use details from the PROJECT CONTEXT above — do NOT invent fictional details.
- Preserve `$ARGUMENTS` placeholders, section headers, and `---` separators.
- Address each suggestion concisely. Do NOT over-expand — add targeted improvements, not walls of text.
- Keep the file roughly the same length. Improve quality, not quantity.
- Focus on embedding project-specific details (tech stack, requirements, mode, agents) where they add value.

Return a structured response with:
- content: the complete improved file content
- changes_made: list of changes applied"""


# ---------------------------------------------------------------------------
# Cost tracking helper
# ---------------------------------------------------------------------------

_COST_PER_1K_INPUT = 0.003  # rough estimate, conservative
_COST_PER_1K_OUTPUT = 0.015


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from token counts."""
    return (input_tokens / 1000) * _COST_PER_1K_INPUT + (output_tokens / 1000) * _COST_PER_1K_OUTPUT


# ---------------------------------------------------------------------------
# Core async functions
# ---------------------------------------------------------------------------

async def score_file(
    llm: Any,
    content: str,
    config: ForgeConfig,
    file_path: str,
    file_type: str,
) -> tuple[FileScore, float]:
    """Score a file's quality. Returns (FileScore, cost_usd)."""
    prompt = _build_score_prompt(content, config, file_path, file_type)
    resp = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        response_model=FileScore,
        max_tokens=config.refinement.max_tokens,
    )
    cost = _estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens)
    return resp.content, cost


async def refine_file(
    llm: Any,
    content: str,
    config: ForgeConfig,
    file_path: str,
    file_type: str,
    feedback: FileScore,
) -> tuple[RefinedContent, float]:
    """Refine a file based on scoring feedback. Returns (RefinedContent, cost_usd)."""
    prompt = _build_refine_prompt(content, config, file_path, file_type, feedback)
    resp = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        response_model=RefinedContent,
        max_tokens=config.refinement.max_tokens,
    )
    cost = _estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens)
    return resp.content, cost


async def refine_single_file(
    llm: Any,
    content: str,
    config: ForgeConfig,
    file_path: str,
    file_type: str,
) -> tuple[str, FileRefinementResult]:
    """Score and iteratively refine a single file until threshold is met.

    Returns (final_content, FileRefinementResult).
    """
    threshold = config.refinement.score_threshold
    max_iter = config.refinement.max_iterations

    result = FileRefinementResult(
        file_path=file_path,
        file_type=file_type,
        initial_score=0,
        final_score=0,
    )

    best_content = content
    best_score = 0
    current_content = content
    cumulative_cost = 0.0

    for i in range(max_iter):
        # Score current content
        file_score, score_cost = await score_file(
            llm, current_content, config, file_path, file_type,
        )
        cumulative_cost += score_cost

        iteration = RefinementIteration(
            iteration=i + 1,
            score=file_score.score,
            reasoning=file_score.reasoning,
            cost_usd=score_cost,
        )

        if i == 0:
            result.initial_score = file_score.score

        # Track best version
        if file_score.score > best_score:
            best_score = file_score.score
            best_content = current_content

        # Met threshold — done
        if file_score.score >= threshold:
            iteration.cost_usd = score_cost
            result.iterations.append(iteration)
            break

        # Refine
        refined, refine_cost = await refine_file(
            llm, current_content, config, file_path, file_type, file_score,
        )
        cumulative_cost += refine_cost
        iteration.cost_usd = score_cost + refine_cost
        result.iterations.append(iteration)

        # Hallucination guard: reject if refined is < 50% of original length
        if len(refined.content) < len(content) * 0.5:
            logger.warning(
                "Refined content too short (%.0f%% of original), keeping previous version",
                len(refined.content) / len(content) * 100,
            )
            continue

        current_content = refined.content

        # Track best after refinement
        if file_score.score > best_score:
            best_score = file_score.score
            best_content = current_content
    else:
        # Loop completed without break — do a final score of current content
        # (already scored in last iteration, use that)
        pass

    result.final_score = best_score
    result.total_cost_usd = cumulative_cost
    return best_content, result


def _classify_file(file_path: Path, project_dir: Path) -> str | None:
    """Classify a .md file by type. Returns None for non-refinable files."""
    rel = file_path.relative_to(project_dir)
    parts = rel.parts

    if file_path.name == "CLAUDE.md" and len(parts) == 1:
        return "claude_md"
    if file_path.name == "team-init-plan.md" and len(parts) == 1:
        return "team_init_plan"
    if len(parts) >= 3 and parts[0] == ".claude" and parts[1] == "agents":
        return "agent"
    if len(parts) >= 3 and parts[0] == ".claude" and parts[1] == "skills":
        return "skill"
    return None


def _collect_refinable_files(project_dir: Path) -> list[tuple[Path, str]]:
    """Collect all .md files eligible for refinement."""
    files: list[tuple[Path, str]] = []

    # Root-level files
    for name in ("CLAUDE.md", "team-init-plan.md"):
        p = project_dir / name
        if p.exists():
            file_type = _classify_file(p, project_dir)
            if file_type:
                files.append((p, file_type))

    # Agent files
    agents_dir = project_dir / ".claude" / "agents"
    if agents_dir.is_dir():
        for p in sorted(agents_dir.glob("*.md")):
            files.append((p, "agent"))

    # Skill files
    skills_dir = project_dir / ".claude" / "skills"
    if skills_dir.is_dir():
        for p in sorted(skills_dir.glob("*.md")):
            files.append((p, "skill"))

    return files


async def _refine_one_file(
    llm: Any,
    file_path: Path,
    file_type: str,
    config: ForgeConfig,
    project_dir: Path,
    semaphore: asyncio.Semaphore,
) -> tuple[Path, str, FileRefinementResult]:
    """Refine a single file under a concurrency semaphore.

    Returns (file_path, refined_content, result).
    """
    async with semaphore:
        content = file_path.read_text()
        rel_path = str(file_path.relative_to(project_dir))
        refined_content, result = await refine_single_file(
            llm, content, config, rel_path, file_type,
        )
        return file_path, refined_content, result


async def refine_all_async(
    config: ForgeConfig,
    project_dir: str | Path,
    llm_provider: Any | None = None,
) -> RefinementReport:
    """Refine all generated .md files in the project directory.

    Files are processed in parallel with bounded concurrency
    (config.refinement.max_concurrency, default 5).

    Args:
        config: Forge configuration (includes refinement settings).
        project_dir: Path to the generated project directory.
        llm_provider: Optional LLM provider instance (for testing).
            If None, creates one from config.refinement settings.

    Returns:
        RefinementReport with per-file results and aggregate stats.
    """
    project_dir = Path(project_dir)
    report = RefinementReport()

    if not config.refinement.enabled:
        return report

    # Create LLM client
    if llm_provider is not None:
        from llm_gateway import LLMClient
        llm = LLMClient(provider_instance=llm_provider)
    else:
        try:
            from llm_gateway import LLMClient, GatewayConfig
        except ImportError:
            raise ImportError(
                "llm-gateway is required for refinement. "
                "Install it with: pip install 'forge-init[refinement]'"
            )
        gw_config = GatewayConfig(
            provider=config.refinement.provider,
            model=config.refinement.model,
            max_tokens=config.refinement.max_tokens,
            timeout_seconds=config.refinement.timeout_seconds,
        )
        llm = LLMClient(config=gw_config)

    try:
        files = _collect_refinable_files(project_dir)
        concurrency = config.refinement.max_concurrency or len(files)
        semaphore = asyncio.Semaphore(concurrency)

        # Launch all file refinements concurrently (bounded by semaphore)
        tasks = [
            _refine_one_file(llm, fp, ft, config, project_dir, semaphore)
            for fp, ft in files
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        cumulative_cost = 0.0
        for outcome in results:
            if isinstance(outcome, Exception):
                logger.warning("Refinement failed for a file: %s", outcome)
                report.all_passed = False
                continue

            file_path, refined_content, result = outcome
            report.files.append(result)
            cumulative_cost += result.total_cost_usd
            report.total_llm_calls += len(result.iterations) * 2

            if result.final_score >= config.refinement.score_threshold:
                if result.initial_score >= config.refinement.score_threshold:
                    report.files_already_good += 1
                else:
                    report.files_improved += 1
                    file_path.write_text(refined_content)
            else:
                report.all_passed = False
                if result.final_score > result.initial_score:
                    report.files_improved += 1
                    file_path.write_text(refined_content)

        report.total_cost_usd = cumulative_cost

    finally:
        await llm.close()

    return report


def refine_all(
    config: ForgeConfig,
    project_dir: str | Path,
    llm_provider: Any | None = None,
) -> RefinementReport:
    """Synchronous wrapper around refine_all_async."""
    return asyncio.run(refine_all_async(config, project_dir, llm_provider))
