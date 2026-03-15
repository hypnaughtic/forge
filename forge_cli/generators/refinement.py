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
    suggestions: list[str] = field(default_factory=list)
    changes_made: list[str] = field(default_factory=list)
    eval_pass_rate: float = 0.0
    eval_expectations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "score": self.score,
            "reasoning": self.reasoning,
            "suggestions": self.suggestions,
            "changes_made": self.changes_made,
            "cost_usd": self.cost_usd,
            "eval_pass_rate": self.eval_pass_rate,
        }


@dataclass
class FileRefinementResult:
    file_path: str
    file_type: str  # "agent" | "claude_md" | "team_init_plan" | "skill"
    initial_score: int
    final_score: int
    iterations: list[RefinementIteration] = field(default_factory=list)
    total_cost_usd: float = 0.0
    baseline_eval_pass_rate: float = 0.0
    final_eval_pass_rate: float = 0.0
    initial_tokens: int = 0
    final_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "initial_score": self.initial_score,
            "final_score": self.final_score,
            "baseline_eval_pass_rate": self.baseline_eval_pass_rate,
            "final_eval_pass_rate": self.final_eval_pass_rate,
            "iterations": [it.to_dict() for it in self.iterations],
            "total_cost_usd": self.total_cost_usd,
            "initial_tokens": self.initial_tokens,
            "final_tokens": self.final_tokens,
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

def _build_project_context(config: ForgeConfig, project_dir: Path | None = None) -> str:
    """Build a concise project context string from config.

    If a .forge/project-context.md exists, includes its content for
    richer context during scoring and refinement.
    """
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

    # Include summarized project context if available
    if project_dir:
        from forge_cli.generators.context_summarizer import load_project_context
        context = load_project_context(project_dir)
        if context:
            # Truncate to avoid token limits — first 4000 chars
            truncated = context[:4000]
            parts.append(f"\nDetailed Project Context:\n{truncated}")

    return "\n".join(parts)


def _build_score_prompt(
    content: str,
    config: ForgeConfig,
    file_path: str,
    file_type: str,
    project_dir: Path | None = None,
    eval_failures: list[str] | None = None,
) -> str:
    """Build the scoring prompt for a file.

    If eval_failures is provided, includes them to guide the scorer
    toward concrete issues identified by automated assertions.
    """
    context = _build_project_context(config, project_dir=project_dir)

    eval_section = ""
    if eval_failures:
        failures_text = "\n".join(f"- {f}" for f in eval_failures[:15])
        eval_section = f"""

EVAL ASSERTION FAILURES (from automated quality checks — these are objective issues):
{failures_text}

Factor these failures into your score. Each unaddressed failure should reduce the score."""

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

PENALTY RULES (apply these strictly):
- DEDUCT 15-20 points if the file contains domain-specific checklists for a DIFFERENT domain than the project (e.g., payment/PCI checklists in a non-financial project, HR/payroll in a diagram tool, leave management in an API project). This is a critical quality issue.
- DEDUCT 10-15 points if the file dumps the entire project requirements verbatim instead of distilling relevant details into actionable instructions.
- DEDUCT 10 points if a section header exists but the section body is empty or contains only generic placeholders.
- DEDUCT 5 points if the file says "Stack: Not specified" or "Tech: Not specified" despite the PROJECT CONTEXT listing specific technologies.
{eval_section}
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
    previous_iterations: list[RefinementIteration] | None = None,
    project_dir: Path | None = None,
    eval_failures: list[str] | None = None,
) -> str:
    """Build the refinement prompt for a file.

    Includes accumulated feedback from previous iterations to prevent
    re-introducing problems that were already identified.
    """
    context = _build_project_context(config, project_dir=project_dir)
    suggestions_text = "\n".join(f"- {s}" for s in score_feedback.suggestions)

    # Build accumulated feedback section from previous iterations
    history_section = ""
    if previous_iterations:
        history_parts = []
        for it in previous_iterations:
            parts = [f"Iteration {it.iteration} (score: {it.score}): {it.reasoning}"]
            if it.changes_made:
                parts.append("  Changes applied: " + "; ".join(it.changes_made[:3]))
            history_parts.append("\n".join(parts))
        history_text = "\n".join(history_parts)
        history_section = f"""
PREVIOUS ITERATION HISTORY (do NOT re-introduce problems that were already identified):
{history_text}

"""

    eval_section = ""
    if eval_failures:
        failures_text = "\n".join(f"- {f}" for f in eval_failures[:15])
        eval_section = f"""
EVAL ASSERTION FAILURES (must address these — they are objective test results, not opinions):
{failures_text}

"""

    return f"""You are improving a generated agent instruction file to score above 90/100.

PROJECT CONTEXT (use these details to make content project-specific):
{context}

FILE: {file_path} (type: {file_type})
CURRENT SCORE: {score_feedback.score}/100

FEEDBACK: {score_feedback.reasoning}

SUGGESTIONS TO ADDRESS:
{suggestions_text}
{eval_section}{history_section}CURRENT CONTENT:
{content}

RULES:
- Return the COMPLETE improved file content (not a diff).
- ONLY use details from the PROJECT CONTEXT above — do NOT invent fictional details.
- Preserve `$ARGUMENTS` placeholders, section headers, and `---` separators.
- Address each suggestion concisely. Do NOT over-expand — add targeted improvements, not walls of text.
- Keep the file roughly the same length. Improve quality, not quantity.
- Focus on embedding project-specific details (tech stack, requirements, mode, agents) where they add value.
- PRESERVE sections that are NOT mentioned in the suggestions — only modify what needs improvement.
- Do NOT add domain-specific content (HR, payment, e-commerce) unless the PROJECT CONTEXT explicitly describes that domain.
- Do NOT copy-paste the project requirements verbatim — distill relevant details into actionable instructions.

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
    project_dir: Path | None = None,
    eval_failures: list[str] | None = None,
) -> tuple[FileScore, float]:
    """Score a file's quality. Returns (FileScore, cost_usd)."""
    prompt = _build_score_prompt(
        content, config, file_path, file_type,
        project_dir=project_dir,
        eval_failures=eval_failures,
    )
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
    previous_iterations: list[RefinementIteration] | None = None,
    project_dir: Path | None = None,
    eval_failures: list[str] | None = None,
) -> tuple[RefinedContent, float]:
    """Refine a file based on scoring feedback. Returns (RefinedContent, cost_usd)."""
    prompt = _build_refine_prompt(
        content, config, file_path, file_type, feedback,
        previous_iterations=previous_iterations,
        project_dir=project_dir,
        eval_failures=eval_failures,
    )
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
    project_dir: Path | None = None,
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
            project_dir=project_dir,
        )
        cumulative_cost += score_cost

        iteration = RefinementIteration(
            iteration=i + 1,
            score=file_score.score,
            reasoning=file_score.reasoning,
            suggestions=file_score.suggestions,
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

        # Refine — pass accumulated iteration history to prevent regression
        refined, refine_cost = await refine_file(
            llm, current_content, config, file_path, file_type, file_score,
            previous_iterations=result.iterations,
            project_dir=project_dir,
        )
        cumulative_cost += refine_cost
        iteration.cost_usd = score_cost + refine_cost
        iteration.changes_made = refined.changes_made
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
    progress: Any | None = None,
) -> tuple[Path, str, FileRefinementResult]:
    """Refine a single file, reporting progress.

    Returns (file_path, refined_content, result).
    """
    rel_path = str(file_path.relative_to(project_dir))
    if progress is not None:
        progress.start_file(rel_path, target_score=config.refinement.score_threshold)

    content = file_path.read_text()
    refined_content, result = await _refine_single_file_with_progress(
        llm, content, config, rel_path, file_type, progress,
        project_dir=project_dir,
    )

    if progress is not None:
        progress.complete_file(rel_path, result.final_score)

    return file_path, refined_content, result


async def _refine_single_file_with_progress(
    llm: Any,
    content: str,
    config: ForgeConfig,
    file_path: str,
    file_type: str,
    progress: Any | None = None,
    project_dir: Path | None = None,
) -> tuple[str, FileRefinementResult]:
    """Score and iteratively refine a file, reporting progress at each step."""
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

    # Get eval failures for this file (deterministic only — free)
    eval_failures: list[str] = []
    try:
        from forge_cli.evals.eval_runner import grade_file_for_refinement
        baseline_grade = await grade_file_for_refinement(
            content, file_path, file_type, config,
        )
        result.baseline_eval_pass_rate = baseline_grade.pass_rate
        eval_failures = [
            f"{e.text}: {e.evidence}"
            for e in baseline_grade.expectations
            if not e.passed
        ]
    except Exception:
        pass  # Eval not available — continue without

    for i in range(max_iter):
        # Report scoring start
        if progress is not None:
            progress.update_score(
                file_path, best_score, i + 1,
                status="scoring",
                detail=f"evaluating (iter {i + 1})",
            )

        # Score current content (pass eval failures to guide scorer)
        file_score, score_cost = await score_file(
            llm, current_content, config, file_path, file_type,
            project_dir=project_dir,
            eval_failures=eval_failures if i == 0 else None,
        )
        cumulative_cost += score_cost

        iteration = RefinementIteration(
            iteration=i + 1,
            score=file_score.score,
            reasoning=file_score.reasoning,
            suggestions=file_score.suggestions,
            cost_usd=score_cost,
        )

        if i == 0:
            result.initial_score = file_score.score

        # Track best version
        if file_score.score > best_score:
            best_score = file_score.score
            best_content = current_content

        # Report score
        if progress is not None:
            first_suggestion = file_score.suggestions[0] if file_score.suggestions else ""
            # Truncate suggestion for display
            if len(first_suggestion) > 60:
                first_suggestion = first_suggestion[:57] + "..."
            progress.update_score(
                file_path, file_score.score, i + 1,
                status="scoring",
                detail=first_suggestion or f"score: {file_score.score}",
            )

        # Met threshold — done
        if file_score.score >= threshold:
            iteration.cost_usd = score_cost
            result.iterations.append(iteration)
            break

        # Report refining start
        if progress is not None:
            progress.update_score(
                file_path, file_score.score, i + 1,
                status="refining",
                detail="applying improvements",
            )

        # Refine (pass eval failures to guide improvements)
        refined, refine_cost = await refine_file(
            llm, current_content, config, file_path, file_type, file_score,
            previous_iterations=result.iterations,
            project_dir=project_dir,
            eval_failures=eval_failures if eval_failures else None,
        )
        cumulative_cost += refine_cost
        iteration.cost_usd = score_cost + refine_cost
        iteration.changes_made = refined.changes_made
        result.iterations.append(iteration)

        # Hallucination guard: reject if refined is < 50% of original length
        if len(refined.content) < len(content) * 0.5:
            logger.warning(
                "Refined content too short (%.0f%% of original), keeping previous version",
                len(refined.content) / len(content) * 100,
            )
            if progress is not None:
                progress.update_score(
                    file_path, file_score.score, i + 1,
                    status="refining",
                    detail="rejected (content too short), retrying",
                )
            continue

        current_content = refined.content

        # Report improvement
        if progress is not None and refined.changes_made:
            first_change = refined.changes_made[0]
            if len(first_change) > 60:
                first_change = first_change[:57] + "..."
            progress.update_score(
                file_path, file_score.score, i + 1,
                status="refining",
                detail=first_change,
            )

        # Track best after refinement
        if file_score.score > best_score:
            best_score = file_score.score
            best_content = current_content

    result.final_score = best_score
    result.total_cost_usd = cumulative_cost

    # Compute final eval pass rate on best content
    try:
        from forge_cli.evals.eval_runner import grade_file_for_refinement
        final_grade = await grade_file_for_refinement(
            best_content, file_path, file_type, config,
        )
        result.final_eval_pass_rate = final_grade.pass_rate
    except Exception:
        pass

    return best_content, result


async def refine_all_async(
    config: ForgeConfig,
    project_dir: str | Path,
    llm_provider: Any | None = None,
    progress: Any | None = None,
) -> RefinementReport:
    """Refine all generated .md files in the project directory.

    Uses a worker-pool pattern: exactly `max_concurrency` workers pull files
    from a queue.  When a worker finishes a file it immediately picks up the
    next one, so concurrency stays at the configured level until the queue is
    drained.

    Args:
        config: Forge configuration (includes refinement settings).
        project_dir: Path to the generated project directory.
        llm_provider: Optional LLM provider instance (for testing).
            If None, creates one from config.refinement settings.
        progress: Optional ForgeRefinementProgress for live progress display.

    Returns:
        RefinementReport with per-file results and aggregate stats.
    """
    project_dir = Path(project_dir)
    report = RefinementReport()

    if not config.refinement.enabled:
        return report

    # In dry-run mode, auto-use FakeLLMProvider if no provider given
    if llm_provider is None:
        import os
        if os.environ.get("FORGE_TEST_DRY_RUN", "0") == "1":
            try:
                from llm_gateway.testing import FakeLLMProvider
                llm_provider = FakeLLMProvider()
            except ImportError:
                pass

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
        # max_concurrency=0 means "auto": use 5 for local_claude (CLI-based),
        # unlimited for API-based providers.
        if config.refinement.max_concurrency > 0:
            concurrency = config.refinement.max_concurrency
        elif config.refinement.provider == "local_claude":
            concurrency = min(5, len(files))
        else:
            concurrency = len(files)

        # Register all files in progress display as "waiting"
        if progress is not None:
            for fp, _ft in files:
                rel = str(fp.relative_to(project_dir))
                progress.register_file(rel, target_score=config.refinement.score_threshold)

        # Build work queue
        queue: asyncio.Queue[tuple[Path, str] | None] = asyncio.Queue()
        for item in files:
            queue.put_nowait(item)
        # Sentinel values to signal workers to stop
        for _ in range(concurrency):
            queue.put_nowait(None)

        # Collect results from workers (thread-safe for single event loop)
        results: list[tuple[Path, str, FileRefinementResult] | Exception] = []

        async def _worker() -> None:
            while True:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    break
                fp, ft = item
                try:
                    outcome = await _refine_one_file(
                        llm, fp, ft, config, project_dir, progress,
                    )
                    results.append(outcome)
                except Exception as exc:
                    rel = str(fp.relative_to(project_dir))
                    if progress is not None:
                        progress.fail_file(rel, str(exc)[:60])
                    results.append(exc)
                finally:
                    queue.task_done()

        # Spawn exactly `concurrency` workers — each immediately picks up
        # the next file when done, maintaining max concurrency at all times.
        workers = [asyncio.create_task(_worker()) for _ in range(concurrency)]
        await asyncio.gather(*workers)

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
    progress: Any | None = None,
) -> RefinementReport:
    """Synchronous wrapper around refine_all_async."""
    if progress is not None:
        files = _collect_refinable_files(Path(project_dir))
        with progress.track(len(files)):
            return asyncio.run(refine_all_async(
                config, project_dir, llm_provider, progress,
            ))
    return asyncio.run(refine_all_async(config, project_dir, llm_provider))
