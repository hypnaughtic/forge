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


_LIFECYCLE_CEREMONY_SKILLS = {
    "agent-init", "respawn", "handoff", "context-reload", "checkpoint",
}


def _is_lifecycle_ceremony(file_path: str) -> bool:
    """Check if a file is a lifecycle/ceremony skill (project-agnostic)."""
    from pathlib import PurePosixPath
    name = PurePosixPath(file_path).stem
    return name in _LIFECYCLE_CEREMONY_SKILLS


# ---------------------------------------------------------------------------
# Scoring profiles — per-file-type criteria for LLM scoring/refinement
# ---------------------------------------------------------------------------

@dataclass
class ScoringProfile:
    """Defines scoring criteria, penalties, and refinement rules for a file category."""

    name: str
    criteria_text: str
    penalty_rules: str
    refinement_rules: str
    is_project_agnostic: bool = False


_COMMON_PENALTIES = """\
- DEDUCT 15-20 points if the file contains domain-specific checklists for a DIFFERENT domain than the project.
- DEDUCT 10-15 points if the file dumps the entire project requirements verbatim instead of distilling relevant details.
- DEDUCT 10 points if a section header exists but the section body is empty or contains only generic placeholders.
- DEDUCT 5 points if the file says "Stack: Not specified" or "Tech: Not specified" despite the PROJECT CONTEXT listing specific technologies."""

_PROFILE_LIFECYCLE_CEREMONY = ScoringProfile(
    name="lifecycle_ceremony",
    criteria_text="SCORING CRITERIA for LIFECYCLE CEREMONY SKILL (score 0-100):\nThis is a lifecycle/ceremony skill. These define UNIVERSAL procedures that work identically regardless of project type.\n\n1. Procedure completeness — Does it cover all steps? (35 pts)\n2. Step clarity — Are steps clear, ordered, and unambiguous? (30 pts)\n3. Path/command correctness — Are file paths, commands, and JSON structures correct? (20 pts)\n4. Error handling — Does it handle edge cases (missing files, corrupted data)? (15 pts)",
    penalty_rules="- Do NOT penalize for LACK of project-specific content — ceremony skills are INTENTIONALLY generic.\n- Focus on whether the PROCEDURE is complete, correct, and followable.",
    refinement_rules="- This is a LIFECYCLE CEREMONY skill — do NOT add project-specific tech stack, domain details, or requirements.\n- Improvements should focus on: clearer steps, better error handling, more precise file paths.",
    is_project_agnostic=True,
)
_PROFILE_TEAM_LEADER = ScoringProfile(
    name="team_leader_agent",
    criteria_text="SCORING CRITERIA for TEAM LEADER AGENT (score 0-100):\n\n1. Iteration lifecycle phases — Does it define the 7-phase iteration lifecycle? (20 pts)\n2. Strategy-appropriate decision authority — Does it reflect the project's strategy? (20 pts)\n3. Agent coordination & spawning — Does it explain how to spawn, monitor, and sync agents? (20 pts)\n4. Cost cap awareness — Does it reference cost cap and resource management? (15 pts)\n5. Progressive work advancement — Does it describe progressive work patterns? (15 pts)\n6. Quality gate definition — Does it define quality gates with mode-appropriate thresholds? (10 pts)",
    penalty_rules="- DEDUCT 10 points if iteration lifecycle phases are missing or incomplete.",
    refinement_rules="- Focus on iteration lifecycle completeness and strategy-appropriate decision authority.\n- Ensure agent spawning instructions reference the actual agent roster from config.",
)
_PROFILE_SCRUM_MASTER = ScoringProfile(
    name="scrum_master_agent",
    criteria_text="SCORING CRITERIA for SCRUM MASTER AGENT (score 0-100):\n\n1. Sprint planning accuracy (20 pts)\n2. Backlog management (20 pts)\n3. Ceremony facilitation (20 pts)\n4. Jira/Confluence integration (20 pts)\n5. Team velocity tracking (10 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if Jira/Confluence references are present when Atlassian is disabled, or missing when enabled.",
    refinement_rules="- Ensure sprint planning reflects the project mode.\n- Jira/Confluence references must match config.atlassian.enabled status.",
)
_PROFILE_ARCHITECT = ScoringProfile(
    name="architect_agent",
    criteria_text="SCORING CRITERIA for ARCHITECT AGENT (score 0-100):\n\n1. System design specificity (20 pts)\n2. API contract patterns (20 pts)\n3. Tech-stack-informed architecture (20 pts)\n4. Workspace-type awareness (15 pts)\n5. Database schema guidance (15 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if architecture advice is generic and doesn't reference the actual tech stack.",
    refinement_rules="- Architecture guidance must be specific to the configured tech stack.\n- API patterns should match the framework.",
)
_PROFILE_RESEARCH_STRATEGIST = ScoringProfile(
    name="research_strategist_agent",
    criteria_text="SCORING CRITERIA for RESEARCH STRATEGIST AGENT (score 0-100):\n\n1. Domain research depth (25 pts)\n2. Tech-stack-aligned research areas (25 pts)\n3. Competitive analysis presence (15 pts)\n4. Deliverable clarity (15 pts)\n5. Risk assessment (10 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if research areas are generic and unrelated to the project domain.",
    refinement_rules="- Research areas must align with the project's domain and tech stack.\n- Deliverables should be concrete and actionable.",
)
_PROFILE_BACKEND_DEVELOPER = ScoringProfile(
    name="backend_developer_agent",
    criteria_text="SCORING CRITERIA for BACKEND DEVELOPER AGENT (score 0-100):\n\n1. Framework-specific patterns — Does it include patterns specific to the configured backend framework? (25 pts)\n2. Database integration patterns (20 pts)\n3. Mode-appropriate quality standards (15 pts)\n4. API design patterns (15 pts)\n5. Error handling patterns (15 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if framework advice is for a different framework than configured.",
    refinement_rules="- Framework patterns must match the actual configured framework.\n- Database patterns should reference the specific database and ORM.",
)
_PROFILE_FRONTEND = ScoringProfile(
    name="frontend_agent",
    criteria_text="SCORING CRITERIA for FRONTEND AGENT (score 0-100):\n\n1. Visual verification protocol (20 pts)\n2. Component architecture (20 pts)\n3. Responsive/accessibility coverage (20 pts)\n4. State management patterns (15 pts)\n5. Framework-specific guidance (15 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if frontend framework advice doesn't match the configured framework.",
    refinement_rules="- Visual verification protocol must reference Playwright/screenshot workflow.\n- Component patterns should be specific to the configured frontend framework.",
)
_PROFILE_DEVOPS = ScoringProfile(
    name="devops_agent",
    criteria_text="SCORING CRITERIA for DEVOPS SPECIALIST AGENT (score 0-100):\n\n1. Infrastructure specificity (25 pts)\n2. CI/CD pipeline accuracy (20 pts)\n3. Environment management (15 pts)\n4. Monitoring setup (15 pts)\n5. Deployment strategy (15 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if deployment advice is for a different platform than configured.",
    refinement_rules="- Infrastructure guidance must match the project type.\n- CI/CD steps should reference the actual tech stack tools.",
)
_PROFILE_QA_ENGINEER = ScoringProfile(
    name="qa_engineer_agent",
    criteria_text="SCORING CRITERIA for QA ENGINEER AGENT (score 0-100):\n\n1. Mode-appropriate coverage targets (MVP: 70%, production: 90%, enterprise: 100%) (25 pts)\n2. Test tier definition (unit/integration/e2e) (20 pts)\n3. Database testing methodology (15 pts)\n4. Framework-specific test commands (15 pts)\n5. Bug management process (15 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if coverage targets don't match the project mode.",
    refinement_rules="- Coverage targets must match the project mode.\n- Test commands must reference the actual testing framework.",
)
_PROFILE_CRITIC = ScoringProfile(
    name="critic_agent",
    criteria_text="SCORING CRITERIA for CRITIC AGENT (score 0-100):\n\n1. Independence and objectivity (25 pts)\n2. Blocker categorization (BLOCKER, WARNING, SUGGESTION) (20 pts)\n3. Cross-agent evaluation scope (20 pts)\n4. Quality gate enforcement (15 pts)\n5. Review methodology (10 pts)\n6. Config fidelity (10 pts)",
    penalty_rules="- DEDUCT 10 points if critic lacks clear blocker categorization.",
    refinement_rules="- Critic must maintain independent authority.\n- Quality gate thresholds should match the project mode.",
)
_PROFILE_QUALITY_SPECIALIST = ScoringProfile(
    name="quality_specialist_agent",
    criteria_text="SCORING CRITERIA for QUALITY SPECIALIST AGENT (score 0-100):\n\n1. Specialist methodology depth (25 pts)\n2. Mode-appropriate rigor (20 pts)\n3. Tool-specific guidance (20 pts)\n4. Deliverable format (15 pts)\n5. Config fidelity (10 pts)\n6. Actionability (10 pts)",
    penalty_rules="- DEDUCT 10 points if specialist tools don't match the configured tech stack.",
    refinement_rules="- Tools referenced must match the configured tech stack.\n- Deliverables should be concrete and actionable.",
)
_PROFILE_TECH_DEPENDENT_SKILL = ScoringProfile(
    name="tech_dependent_skill",
    criteria_text="SCORING CRITERIA for TECH-DEPENDENT SKILL (score 0-100):\n\n1. Tech-stack command correctness (30 pts)\n2. Project-type variants (CLI vs web vs frontend) (25 pts)\n3. Completeness (20 pts)\n4. Clarity (15 pts)\n5. Frontmatter (10 pts)",
    penalty_rules="- DEDUCT 15 points if commands reference tools not in the configured tech stack.",
    refinement_rules="- Commands must be correct for the configured tech stack.\n- Frontmatter must follow Claude skill format.",
)
_PROFILE_WORKFLOW_SKILL = ScoringProfile(
    name="workflow_skill",
    criteria_text="SCORING CRITERIA for WORKFLOW SKILL (score 0-100):\n\n1. Process accuracy (25 pts)\n2. Team integration references (25 pts)\n3. Completeness (20 pts)\n4. Clarity (15 pts)\n5. Frontmatter (15 pts)",
    penalty_rules="- DEDUCT 10 points if workflow references roles not in the configured team profile.",
    refinement_rules="- Workflow must reference actual team roles from config.\n- Process steps should be ordered and complete.",
)
_PROFILE_ANALYSIS_SKILL = ScoringProfile(
    name="analysis_skill",
    criteria_text="SCORING CRITERIA for ANALYSIS SKILL (score 0-100):\n\n1. Review criteria relevance (25 pts)\n2. Tech-stack alignment (25 pts)\n3. Completeness (20 pts)\n4. Clarity (15 pts)\n5. Frontmatter (15 pts)",
    penalty_rules="- DEDUCT 10 points if review criteria are irrelevant to the project domain.",
    refinement_rules="- Review criteria must align with the project's tech stack and domain.\n- Analysis outputs should be structured and actionable.",
)
_PROFILE_CLAUDE_MD = ScoringProfile(
    name="claude_md",
    criteria_text="SCORING CRITERIA for CLAUDE.md (score 0-100):\n\n1. Agent roster accuracy vs config (20 pts)\n2. Conditional section correctness (visual verification only if frontend, Atlassian only if enabled) (20 pts)\n3. Mode/strategy/cost clarity (20 pts)\n4. Project description embedding (20 pts)\n5. Lifecycle skills reference (20 pts)",
    penalty_rules="- DEDUCT 15 points if agent roster doesn't match config.\n- DEDUCT 10 points if conditional sections are wrong.",
    refinement_rules="- Agent roster must exactly match the configured team profile.\n- Conditional sections must match config.\n- Mode, strategy, and cost cap must be accurate.",
)
_PROFILE_TEAM_INIT_PLAN = ScoringProfile(
    name="team_init_plan",
    criteria_text="SCORING CRITERIA for team-init-plan.md (score 0-100):\n\n1. Phase structure (0→1→2→3) (20 pts)\n2. Agent spawn count matches config (20 pts)\n3. Workspace-type setup (20 pts)\n4. Task decomposition specificity (20 pts)\n5. Quick reference table (20 pts)",
    penalty_rules="- DEDUCT 15 points if agent count doesn't match team profile.\n- DEDUCT 10 points if workspace setup is for wrong workspace type.",
    refinement_rules="- Phase structure must follow 0→1→2→3 pattern.\n- Agent spawn count must match config.\n- Tasks should be specific to the project.",
)
_PROFILE_GENERAL = ScoringProfile(
    name="general",
    criteria_text="SCORING CRITERIA (score 0-100, unified):\n1. Completeness (25 pts)\n2. Config fidelity (25 pts)\n3. Specificity (20 pts)\n4. Clarity & Actionability (20 pts)\n5. Consistency (10 pts)",
    penalty_rules="",
    refinement_rules="- Focus on embedding project-specific details where they add value.\n- Do NOT add domain-specific content unless the PROJECT CONTEXT explicitly describes that domain.",
)

_AGENT_PROFILE_MAP: dict[str, str] = {
    "team-leader": "team_leader_agent", "scrum-master": "scrum_master_agent",
    "architect": "architect_agent", "research-strategist": "research_strategist_agent",
    "backend-developer": "backend_developer_agent",
    "frontend-engineer": "frontend_agent", "frontend-developer": "frontend_agent",
    "frontend-designer": "frontend_agent", "devops-specialist": "devops_agent",
    "qa-engineer": "qa_engineer_agent", "critic": "critic_agent",
    "security-tester": "quality_specialist_agent",
    "performance-engineer": "quality_specialist_agent",
    "documentation-specialist": "quality_specialist_agent",
}

_SKILL_PROFILE_MAP: dict[str, str] = {
    "smoke-test": "tech_dependent_skill", "playwright-test": "tech_dependent_skill",
    "screenshot-review": "tech_dependent_skill",
    "create-pr": "workflow_skill", "release": "workflow_skill",
    "jira-update": "workflow_skill", "sprint-report": "workflow_skill",
    "spawn-agent": "workflow_skill",
    "arch-review": "analysis_skill", "code-review": "analysis_skill",
    "dependency-audit": "analysis_skill", "benchmark": "analysis_skill",
    "iteration-review": "analysis_skill", "team-status": "analysis_skill",
    "excalidraw-diagram": "analysis_skill",
}

_PROFILE_REGISTRY: dict[str, ScoringProfile] = {
    "lifecycle_ceremony": _PROFILE_LIFECYCLE_CEREMONY, "team_leader_agent": _PROFILE_TEAM_LEADER,
    "scrum_master_agent": _PROFILE_SCRUM_MASTER, "architect_agent": _PROFILE_ARCHITECT,
    "research_strategist_agent": _PROFILE_RESEARCH_STRATEGIST,
    "backend_developer_agent": _PROFILE_BACKEND_DEVELOPER,
    "frontend_agent": _PROFILE_FRONTEND, "devops_agent": _PROFILE_DEVOPS,
    "qa_engineer_agent": _PROFILE_QA_ENGINEER, "critic_agent": _PROFILE_CRITIC,
    "quality_specialist_agent": _PROFILE_QUALITY_SPECIALIST,
    "tech_dependent_skill": _PROFILE_TECH_DEPENDENT_SKILL,
    "workflow_skill": _PROFILE_WORKFLOW_SKILL, "analysis_skill": _PROFILE_ANALYSIS_SKILL,
    "claude_md": _PROFILE_CLAUDE_MD, "team_init_plan": _PROFILE_TEAM_INIT_PLAN,
    "general": _PROFILE_GENERAL,
}


def _resolve_scoring_profile(file_path: str, file_type: str, config: ForgeConfig | None = None) -> ScoringProfile:
    """Resolve the scoring profile for a given file."""
    from pathlib import PurePosixPath
    stem = PurePosixPath(file_path).stem
    if file_type == "skill" and stem in _LIFECYCLE_CEREMONY_SKILLS:
        return _PROFILE_LIFECYCLE_CEREMONY
    if file_type == "agent":
        pn = _AGENT_PROFILE_MAP.get(stem)
        if pn and pn in _PROFILE_REGISTRY:
            return _PROFILE_REGISTRY[pn]
    if file_type == "skill":
        pn = _SKILL_PROFILE_MAP.get(stem)
        if pn and pn in _PROFILE_REGISTRY:
            return _PROFILE_REGISTRY[pn]
    if file_type == "claude_md":
        return _PROFILE_CLAUDE_MD
    if file_type == "team_init_plan":
        return _PROFILE_TEAM_INIT_PLAN
    return _PROFILE_GENERAL


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
    profile = _resolve_scoring_profile(file_path, file_type, config)

    eval_section = ""
    if eval_failures:
        failures_text = "\n".join(f"- {f}" for f in eval_failures[:15])
        eval_section = f"""

EVAL ASSERTION FAILURES (from automated quality checks — these are objective issues):
{failures_text}

Factor these failures into your score. Each unaddressed failure should reduce the score."""

    penalties = _COMMON_PENALTIES
    if profile.penalty_rules:
        penalties = f"{_COMMON_PENALTIES}\n{profile.penalty_rules}"

    return f"""You are evaluating a generated agent instruction file for quality.

PROJECT CONTEXT:
{context}

FILE: {file_path} (type: {file_type}, profile: {profile.name})

CONTENT:
{content}

{profile.criteria_text}

IMPORTANT RULES:
- `$ARGUMENTS` is a Claude skill template variable — do NOT penalize its presence.
- Do NOT penalize for file length, density, or template-style formatting.
- Do NOT penalize for shared/base protocol sections being similar across agent files.
- A file that mentions the project's tech stack, requirements, mode, and agents by name IS project-specific — score accordingly.
- Focus on whether the content is USEFUL for an AI agent building this specific project.
- Only suggest improvements that would materially help an agent do its job better.

PENALTY RULES (apply these strictly):
{penalties}
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
    profile = _resolve_scoring_profile(file_path, file_type, config)
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

    if profile.is_project_agnostic:
        context_instruction = (
            f"PROJECT CONTEXT (for reference only — this is a {profile.name} file "
            "that should NOT embed project-specific details):"
        )
    else:
        context_instruction = "PROJECT CONTEXT (use these details to make content project-specific):"

    return f"""You are improving a generated agent instruction file to score above 90/100.

{context_instruction}
{context}

FILE: {file_path} (type: {file_type}, profile: {profile.name})
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
- PRESERVE sections that are NOT mentioned in the suggestions — only modify what needs improvement.
{profile.refinement_rules}

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
