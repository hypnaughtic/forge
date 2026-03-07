"""Comprehensive LLM-evaluated quality tests for Forge.

Each test case:
1. Defines a realistic project with specific config (mode, stack, atlassian, etc.)
2. Generates the full forge workspace into its own directory
3. Saves the config YAML and requirements file
4. Uses local_claude (opus) via llm-gateway to evaluate every generated file
5. Produces a detailed report in outputs/ for each test case
6. Scores forge on multiple dimensions; fails if overall score < 90%

The LLM judge evaluates:
- File completeness (are all expected sections present?)
- Config fidelity (does the output reflect the config accurately?)
- Instruction clarity (would an agent understand what to do?)
- Workflow enforcement (are PR, branch, Jira rules correctly embedded?)
- Role specificity (do different agents get different instructions?)
- Consistency (do files reference each other correctly?)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel

from forge_cli.config_schema import (
    AgentNamingConfig,
    AgentsConfig,
    AtlassianConfig,
    CostConfig,
    ExecutionStrategy,
    ForgeConfig,
    LLMGatewayConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
    TechStack,
)
from forge_cli.config_loader import save_config
from forge_cli.generators.orchestrator import generate_all


# ---------------------------------------------------------------------------
# Availability gate — skip entire module if local_claude unavailable
# ---------------------------------------------------------------------------

def _local_claude_available() -> bool:
    try:
        from llm_gateway import LLMClient, GatewayConfig  # noqa: F401
    except ImportError:
        return False
    if not shutil.which("claude"):
        return False
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        r = subprocess.run(
            ["claude", "-p", "hi", "--output-format", "json", "--max-budget-usd", "0.01"],
            capture_output=True, text=True, timeout=15, env=env,
        )
        if "Not logged in" in r.stdout or "Not logged in" in r.stderr:
            return False
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


pytestmark = pytest.mark.skipif(
    not _local_claude_available(),
    reason="local_claude not available (need claude CLI authenticated)",
)


# ---------------------------------------------------------------------------
# LLM judge helper
# ---------------------------------------------------------------------------

LLM_MODEL = "claude-opus-4-6"
LLM_MAX_TOKENS = 4096
LLM_TIMEOUT = 120


class LLMScore(BaseModel):
    """Structured score from the LLM judge."""
    score: int
    reasoning: str


class LLMScores(BaseModel):
    """Multi-dimension scoring response."""
    completeness: int
    config_fidelity: int
    instruction_clarity: int
    workflow_enforcement: int
    role_specificity: int
    cross_file_consistency: int
    overall: int
    findings: str


def _ask_llm(prompt: str, response_model: type[BaseModel] = LLMScore) -> BaseModel:
    """Send a prompt to local_claude opus and return a structured response."""
    from llm_gateway import LLMClient, GatewayConfig

    async def _call():
        config = GatewayConfig(
            provider="local_claude",
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            timeout_seconds=LLM_TIMEOUT,
        )
        llm = LLMClient(config=config)
        try:
            resp = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_model=response_model,
            )
            return resp.content
        finally:
            await llm.close()

    return asyncio.run(_call())


# ---------------------------------------------------------------------------
# Report helper
# ---------------------------------------------------------------------------

@dataclass
class DimensionResult:
    name: str
    score: int
    max_score: int = 100
    details: str = ""


@dataclass
class QualityReport:
    test_name: str
    project_description: str
    config_summary: dict = field(default_factory=dict)
    dimensions: list[DimensionResult] = field(default_factory=list)
    overall_score: float = 0.0
    llm_findings: str = ""
    timestamp: str = ""
    passed: bool = False

    def compute_overall(self) -> float:
        if not self.dimensions:
            return 0.0
        self.overall_score = sum(d.score for d in self.dimensions) / len(self.dimensions)
        self.passed = self.overall_score >= 90.0
        return self.overall_score

    def to_markdown(self) -> str:
        lines = [
            f"# Forge Quality Report: {self.test_name}",
            f"",
            f"**Timestamp**: {self.timestamp}",
            f"**Overall Score**: {self.overall_score:.1f}/100 {'PASS' if self.passed else 'FAIL'}",
            f"**Project**: {self.project_description}",
            f"",
            f"## Configuration",
            f"```yaml",
            yaml.dump(self.config_summary, default_flow_style=False).strip(),
            f"```",
            f"",
            f"## Dimension Scores",
            f"",
            f"| Dimension | Score | Status |",
            f"|---|---|---|",
        ]
        for d in self.dimensions:
            status = "PASS" if d.score >= 90 else "WARN" if d.score >= 70 else "FAIL"
            lines.append(f"| {d.name} | {d.score}/{d.max_score} | {status} |")
        lines += [
            f"",
            f"## Detailed Findings",
            f"",
        ]
        for d in self.dimensions:
            if d.details:
                lines.append(f"### {d.name} ({d.score}/100)")
                lines.append(f"")
                lines.append(d.details)
                lines.append(f"")
        if self.llm_findings:
            lines.append(f"## LLM Overall Assessment")
            lines.append(f"")
            lines.append(self.llm_findings)
        return "\n".join(lines)


def _write_report(output_dir: Path, report: QualityReport) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report.timestamp = datetime.now(timezone.utc).isoformat()
    report.compute_overall()
    (output_dir / "report.md").write_text(report.to_markdown())
    (output_dir / "scores.json").write_text(json.dumps({
        "test_name": report.test_name,
        "overall_score": report.overall_score,
        "passed": report.passed,
        "dimensions": {d.name: d.score for d in report.dimensions},
        "timestamp": report.timestamp,
    }, indent=2))


# ---------------------------------------------------------------------------
# Test case definitions — diverse configs
# ---------------------------------------------------------------------------

TEST_CASES: dict[str, dict] = {
    "fullstack_mvp_lean": {
        "description": "Real-time collaborative task management app with Kanban boards, due dates, and team chat",
        "requirements": (
            "Build a full-stack collaborative task management application. "
            "Features: user authentication (OAuth + email/password), real-time Kanban board with "
            "drag-and-drop, task assignments with due dates and priorities, team chat with @mentions, "
            "file attachments, activity feed, email notifications. "
            "Tech: React frontend with TypeScript, Python FastAPI backend, PostgreSQL, Redis for "
            "real-time events, WebSocket support."
        ),
        "mode": ProjectMode.MVP,
        "strategy": ExecutionStrategy.AUTO_PILOT,
        "profile": TeamProfile.LEAN,
        "tech_stack": TechStack(
            languages=["typescript", "python"],
            frameworks=["react", "fastapi", "tailwind"],
            databases=["postgresql", "redis"],
        ),
        "atlassian": False,
        "spawning": True,
        "naming": True,
        "naming_style": "creative",
    },
    "backend_api_production": {
        "description": "Financial transaction processing API with audit logging and compliance",
        "requirements": (
            "Build a production-grade financial transaction processing API. "
            "Features: transaction ingestion (debit/credit), double-entry bookkeeping, "
            "balance calculations, audit trail with immutable logs, role-based access control, "
            "rate limiting, webhook notifications for transaction events, "
            "PCI-DSS-aware data handling (no raw card numbers in logs). "
            "Tech: Python, FastAPI, PostgreSQL, Redis for rate limiting. "
            "No frontend — API only with OpenAPI docs."
        ),
        "mode": ProjectMode.PRODUCTION_READY,
        "strategy": ExecutionStrategy.CO_PILOT,
        "profile": TeamProfile.CUSTOM,
        "custom_agents": ["team-leader", "architect", "backend-developer", "qa-engineer", "devops-specialist", "security-tester", "critic"],
        "tech_stack": TechStack(
            languages=["python"],
            frameworks=["fastapi"],
            databases=["postgresql", "redis"],
        ),
        "atlassian": False,
        "spawning": True,
        "naming": True,
        "naming_style": "codename",
    },
    "enterprise_nocomp_atlassian": {
        "description": "Enterprise HR management platform with payroll, leave tracking, and org chart",
        "requirements": (
            "Build an enterprise HR management platform. "
            "Features: employee profiles with org hierarchy, payroll processing with tax calculations, "
            "leave management (PTO, sick, parental) with approval workflows, performance reviews, "
            "org chart visualization, document management (offer letters, contracts), "
            "SSO integration (SAML/OIDC), audit logging for all HR actions, "
            "reporting dashboard with charts. "
            "Tech: Next.js frontend, Go microservices backend, PostgreSQL, Elasticsearch for search, "
            "Redis for caching. Full Atlassian integration for project management."
        ),
        "mode": ProjectMode.NO_COMPROMISE,
        "strategy": ExecutionStrategy.CO_PILOT,
        "profile": TeamProfile.FULL,
        "tech_stack": TechStack(
            languages=["typescript", "go"],
            frameworks=["next.js", "tailwind"],
            databases=["postgresql", "redis", "elasticsearch"],
        ),
        "atlassian": True,
        "spawning": True,
        "naming": True,
        "naming_style": "creative",
    },
    "static_site_mvp_minimal": {
        "description": "Developer portfolio website with blog and project showcase",
        "requirements": (
            "Build a developer portfolio website. "
            "Features: landing page with hero section, about page, project showcase with screenshots, "
            "blog with markdown support, contact form, dark mode toggle, responsive design. "
            "Tech: Astro with React islands, Tailwind CSS, MDX for blog posts. "
            "No backend — static site with optional serverless functions for contact form. "
            "Deploy to Vercel."
        ),
        "mode": ProjectMode.MVP,
        "strategy": ExecutionStrategy.AUTO_PILOT,
        "profile": TeamProfile.LEAN,
        "tech_stack": TechStack(
            languages=["typescript"],
            frameworks=["astro", "react", "tailwind"],
            databases=[],
        ),
        "atlassian": False,
        "spawning": False,
        "naming": False,
    },
    "microservices_production_atlassian": {
        "description": "E-commerce marketplace with multi-vendor support and payment processing",
        "requirements": (
            "Build an e-commerce marketplace platform. "
            "Features: vendor onboarding and storefront, product catalog with search and filters, "
            "shopping cart and checkout, Stripe payment processing, order management with status tracking, "
            "vendor dashboard with sales analytics, customer reviews and ratings, "
            "inventory management, email notifications (order confirmation, shipping updates), "
            "admin panel for marketplace management. "
            "Tech: React + Next.js frontend, Python Django backend with DRF, PostgreSQL, "
            "Redis for caching/sessions, Celery for async tasks, S3 for media storage. "
            "Atlassian integration for team coordination."
        ),
        "mode": ProjectMode.PRODUCTION_READY,
        "strategy": ExecutionStrategy.MICRO_MANAGE,
        "profile": TeamProfile.FULL,
        "tech_stack": TechStack(
            languages=["typescript", "python"],
            frameworks=["next.js", "django", "tailwind"],
            databases=["postgresql", "redis"],
        ),
        "atlassian": True,
        "spawning": True,
        "naming": True,
        "naming_style": "functional",
    },
    "cli_tool_nocomp_no_frontend": {
        "description": "CLI data pipeline tool for ETL with plugin architecture",
        "requirements": (
            "Build a CLI data pipeline tool. "
            "Features: declarative YAML pipeline definitions, built-in extractors (CSV, JSON, API, DB), "
            "transformers (filter, map, aggregate, join), loaders (PostgreSQL, S3, BigQuery), "
            "plugin architecture for custom extractors/transformers/loaders, "
            "parallel execution with configurable concurrency, dry-run mode, "
            "progress reporting, error handling with dead-letter queue, "
            "pipeline versioning and migration support. "
            "Tech: Python with Click CLI, async I/O, no frontend."
        ),
        "mode": ProjectMode.NO_COMPROMISE,
        "strategy": ExecutionStrategy.AUTO_PILOT,
        "profile": TeamProfile.CUSTOM,
        "custom_agents": ["team-leader", "architect", "backend-developer", "qa-engineer", "devops-specialist", "documentation-specialist", "critic"],
        "tech_stack": TechStack(
            languages=["python"],
            frameworks=["click"],
            databases=["postgresql"],
        ),
        "atlassian": False,
        "spawning": True,
        "naming": True,
        "naming_style": "codename",
    },
}


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def _build_config(case: dict) -> ForgeConfig:
    agents_config = AgentsConfig(
        team_profile=case.get("profile", TeamProfile.LEAN),
        allow_sub_agent_spawning=case.get("spawning", True),
    )
    if case.get("profile") == TeamProfile.CUSTOM and case.get("custom_agents"):
        agents_config.include = case["custom_agents"]

    atlassian_enabled = case.get("atlassian", False)
    return ForgeConfig(
        project=ProjectConfig(
            description=case["description"],
            requirements=case["requirements"],
        ),
        mode=case.get("mode", ProjectMode.MVP),
        strategy=case.get("strategy", ExecutionStrategy.CO_PILOT),
        agents=agents_config,
        tech_stack=case.get("tech_stack", TechStack()),
        atlassian=AtlassianConfig(
            enabled=atlassian_enabled,
            jira_project_key="PROJ" if atlassian_enabled else "",
            jira_base_url="https://forge-test.atlassian.net" if atlassian_enabled else "",
            confluence_base_url="https://forge-test.atlassian.net/wiki" if atlassian_enabled else "",
            confluence_space_key="FORGETEST" if atlassian_enabled else "",
        ),
        agent_naming=AgentNamingConfig(
            enabled=case.get("naming", True),
            style=case.get("naming_style", "creative"),
        ),
        llm_gateway=LLMGatewayConfig(enabled=True, local_claude_model="claude-opus-4-6"),
    )


# ---------------------------------------------------------------------------
# Evaluation prompts
# ---------------------------------------------------------------------------

def _build_completeness_prompt(files_summary: str, config: ForgeConfig) -> str:
    agents = config.get_active_agents()
    expected_agents = ", ".join(agents)
    expected_skills = "team-status, iteration-review, smoke-test, screenshot-review, arch-review, create-pr, release"
    if config.agents.allow_sub_agent_spawning:
        expected_skills += ", spawn-agent"
    if config.atlassian.enabled:
        expected_skills += ", jira-update, sprint-report"

    return textwrap.dedent(f"""\
    You are evaluating the output of Forge, a tool that generates Claude Code agent instruction files.

    ## Expected Files
    - CLAUDE.md (team leader context)
    - team-init-plan.md (bootstrap document)
    - .claude/mcp.json (MCP server configuration)
    - Agent files for: {expected_agents}
    - Skill files for: {expected_skills}

    ## Generated Files Summary
    {files_summary}

    ## Evaluation Criteria
    Score 0-100 on COMPLETENESS:
    - Are ALL expected agent files present? (each missing = -10)
    - Are ALL expected skill files present? (each missing = -5)
    - Is CLAUDE.md present and non-empty? (-20 if missing)
    - Is team-init-plan.md present and non-empty? (-15 if missing)
    - Is .claude/mcp.json present? (-10 if missing)
    - Do agent files contain the required sections: Project Context, Base Agent Protocol, Workflow Enforcement Protocol, Workspace Detection? (each missing section across all agents = -3)
    - If atlassian enabled: do agent files have Atlassian Integration section? (-5 per missing)
    - If spawning enabled: do agent files have Sub-Agent Spawning Protocol? (-5 per missing)
    - If naming enabled: do agent files have Agent Naming Protocol? (-5 per missing)

    Be precise. Count actual files vs expected. Return your score and detailed reasoning.
    """)


def _build_config_fidelity_prompt(files_content: str, config_yaml: str) -> str:
    return textwrap.dedent(f"""\
    You are evaluating whether generated agent files accurately reflect the configuration.

    ## Configuration (YAML)
    ```yaml
    {config_yaml}
    ```

    ## Generated Files Content (truncated)
    {files_content}

    ## Evaluation Criteria
    Score 0-100 on CONFIG FIDELITY:
    - Does the mode (mvp/production-ready/no-compromise) appear correctly? (-10 if wrong)
    - Does the strategy (auto-pilot/co-pilot/micro-manage) appear correctly? (-10 if wrong)
    - Is the quality threshold correct for the mode (mvp=70%, production-ready=90%, no-compromise=100%)? (-15 if wrong)
    - Is the tech stack reflected? (-5 per missing language/framework)
    - Is the project description and requirements embedded? (-10 if missing)
    - Atlassian enabled/disabled state correct? (-15 if wrong)
    - Sub-agent spawning enabled/disabled state correct? (-10 if wrong)
    - Agent naming style matches config? (-5 if wrong)
    - Team profile agents match expected for the profile? (-10 if agents missing/extra)
    - Cost cap reflected? (-5 if missing)

    Be precise. Check each config value against the output. Return score and reasoning.
    """)


def _build_instruction_clarity_prompt(agent_file_content: str, agent_type: str) -> str:
    return textwrap.dedent(f"""\
    You are evaluating the clarity and actionability of an agent instruction file.

    ## Agent Type: {agent_type}

    ## Instruction File Content
    {agent_file_content}

    ## Evaluation Criteria
    Score 0-100 on INSTRUCTION CLARITY:
    - Is the agent's role and mission clearly defined? (-15 if unclear)
    - Are core responsibilities listed with specific, actionable items? (-10 if vague)
    - Is the git workflow (commit format, branch naming) clearly specified? (-10 if missing/unclear)
    - Is the communication protocol defined (how to report, what metadata to include)? (-5 if missing)
    - Are quality expectations clear for the agent's deliverables? (-5 if missing)
    - Would a Claude agent reading this know exactly what to do? (-15 if ambiguous)
    - Are there contradictions or confusing instructions? (-10 per contradiction)
    - Is the level of detail appropriate (not too sparse, not overwhelming)? (-5 if extreme)

    NOTE: If the content appears truncated, do NOT penalize for truncation — evaluate only the content shown.
    The full file is longer; you are seeing a representative portion.

    Evaluate as if you were the agent receiving these instructions. Return score and reasoning.
    """)


def _build_workflow_enforcement_prompt(files_content: str, config: ForgeConfig) -> str:
    atlassian_note = "Atlassian is ENABLED" if config.atlassian.enabled else "Atlassian is DISABLED"
    spawning_note = "Sub-agent spawning is ENABLED" if config.agents.allow_sub_agent_spawning else "Sub-agent spawning is DISABLED"

    return textwrap.dedent(f"""\
    You are evaluating workflow enforcement in the generated files.

    ## Config Context
    - {atlassian_note}
    - {spawning_note}
    - Mode: {config.mode.value}

    ## Generated Files Content (key excerpts)
    {files_content}

    ## Evaluation Criteria
    Score 0-100 on WORKFLOW ENFORCEMENT:
    - Is "Workflow Enforcement Protocol" present in agent files? (-15 if missing)
    - Is "Hierarchical PR Workflow" present with "No direct merges" rule? (-10 if missing)
    - Is "PR Review Quality Standards" present with big/small PR distinction? (-5 if missing)
    - Is "Release Management" section present? (-5 if missing)
    - If Atlassian ON: Is branch naming format `<type>-<JIRA-KEY>-<desc>`? (-10 if wrong format)
    - If Atlassian ON: Is "Jira Task Before Work" mandate present? (-15 if missing)
    - If Atlassian ON: Is "Linking PRs" with Jira key reference present? (-5 if missing)
    - If Atlassian OFF: Is fallback branch format `<type>/<agent>/<task>-<desc>`? (-10 if wrong)
    - If Atlassian OFF: Are there NO Jira references in workflow sections? (-10 if Jira references found)
    - Is team-leader's "Workflow Governance" section present? (-10 if missing)
    - Is critic's "Governance Oversight" section present? (-5 if missing)
    - If spawning ON: Is "Leadership Responsibilities" in spawning section? (-5 if missing)
    - If spawning ON: Is "Mandatory Sub-Team Critic" in spawning section? (-5 if missing)
    - If Atlassian ON and scrum-master present: Does scrum-master have "Workflow Enforcement"? (-5 if missing)

    Check each criterion. Return score and detailed reasoning.
    """)


def _build_role_specificity_prompt(all_agents_content: str, agent_count: int) -> str:
    return textwrap.dedent(f"""\
    You are evaluating whether different agents have appropriately differentiated instructions.

    Below are the ROLE-SPECIFIC sections of each agent file (the part before the shared Base Agent Protocol).
    Shared sections (Base Protocol, Workflow Enforcement, etc.) are excluded — they are identical across agents by design.
    All {agent_count} agents are shown below. Some may be truncated but the Identity & Role section is always included.

    ## Agent Role Sections
    {all_agents_content}

    ## Evaluation Criteria
    Score 0-100 on ROLE SPECIFICITY:
    - Does team-leader have orchestration/lifecycle/governance content unique to leaders? (-10 if generic)
    - Does backend-developer have backend-specific responsibilities (APIs, DB, etc.)? (-10 if generic)
    - If frontend agent exists: does it have UI-specific responsibilities? (-10 if generic)
    - Does qa-engineer have testing strategy and quality gates? (-10 if generic)
    - Does critic have independent review approach and governance oversight? (-10 if generic)
    - Does architect (if present) have design/cross-cutting concerns? (-5 if generic)
    - Does devops (if present) have CI/CD and infrastructure content? (-5 if generic)
    - Do role-specific sections genuinely differ between agents? (-10 if roles feel copy-pasted)
    - Is each agent's Identity (Role, Domain, Mission) unique and specific? (-5 if two agents have overlapping domains)

    NOTE: The shared sections (Base Protocol, Workflow Enforcement, Naming, etc.) are intentionally identical across agents.
    Do NOT penalize for shared sections being identical — that is correct behavior. Only evaluate the role-specific content shown above.

    Evaluate differentiation. Return score and reasoning.
    """)


def _build_consistency_prompt(claude_md: str, init_plan: str, tl_content: str, config: ForgeConfig) -> str:
    agents = ", ".join(config.get_active_agents())
    return textwrap.dedent(f"""\
    You are evaluating cross-file consistency between CLAUDE.md, team-init-plan.md, and team-leader.md.

    ## Expected active agents: {agents}
    ## Mode: {config.mode.value}
    ## Strategy: {config.strategy.value}

    ## CLAUDE.md
    {claude_md[:3000]}

    ## team-init-plan.md
    {init_plan[:3000]}

    ## team-leader.md (first 3000 chars)
    {tl_content[:3000]}

    ## Evaluation Criteria
    Score 0-100 on CROSS-FILE CONSISTENCY:
    - Does CLAUDE.md list the same agents as config expects? (-10 if mismatch)
    - Does team-init-plan list the same agents for spawning? (-10 if mismatch)
    - Do all three files show the same mode value? (-10 if inconsistent)
    - Do all three files show the same strategy? (-5 if inconsistent)
    - Does CLAUDE.md reference team-init-plan.md? (-5 if no reference)
    - Does team-init-plan reference CLAUDE.md? (-5 if no reference)
    - Is quality threshold consistent across files? (-10 if different values)
    - If Atlassian: do all files mention Atlassian/Jira? (-5 if some don't)
    - If spawning: do relevant files mention sub-agent spawning? (-5 if missing)
    - Does the workflow enforcement summary in CLAUDE.md match agent files? (-5 if contradictory)

    Return score and reasoning.
    """)


def _build_overall_prompt(test_name: str, dimension_scores: dict[str, int], config_summary: str) -> str:
    dim_lines = "\n".join(f"- {k}: {v}/100" for k, v in dimension_scores.items())
    return textwrap.dedent(f"""\
    You are providing a final overall assessment of Forge's output quality for a test case.

    ## Test Case: {test_name}
    ## Configuration Summary
    {config_summary}

    ## Dimension Scores
    {dim_lines}

    ## Task
    Provide a concise overall assessment:
    1. What Forge did well
    2. What needs improvement (focus on scores below 90)
    3. Specific, actionable recommendations for improving the generated files
    4. Whether this output would successfully guide a Claude agent team

    Keep it concise but specific. Reference actual content issues, not abstract quality.
    """)


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------

def _collect_files(project_dir: Path) -> dict[str, str]:
    """Collect all generated files into a dict of path -> content."""
    files = {}
    for f in project_dir.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            rel = str(f.relative_to(project_dir))
            try:
                files[rel] = f.read_text()
            except UnicodeDecodeError:
                files[rel] = "<binary file>"
    # Also include .claude/ files
    claude_dir = project_dir / ".claude"
    if claude_dir.exists():
        for f in claude_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(project_dir))
                if rel not in files:
                    try:
                        files[rel] = f.read_text()
                    except UnicodeDecodeError:
                        files[rel] = "<binary file>"
    return files


def _truncate(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [truncated] ..."


def _evaluate_test_case(
    test_name: str,
    project_dir: Path,
    config: ForgeConfig,
    output_dir: Path,
) -> QualityReport:
    """Run all LLM evaluations and produce a report."""
    report = QualityReport(
        test_name=test_name,
        project_description=config.project.description,
        config_summary={
            "mode": config.mode.value,
            "strategy": config.strategy.value,
            "team_profile": config.resolve_team_profile(),
            "agents": config.get_active_agents(),
            "atlassian_enabled": config.atlassian.enabled,
            "spawning_enabled": config.agents.allow_sub_agent_spawning,
            "naming_enabled": config.agent_naming.enabled,
            "naming_style": config.agent_naming.style,
            "tech_stack": {
                "languages": config.tech_stack.languages,
                "frameworks": config.tech_stack.frameworks,
                "databases": config.tech_stack.databases,
            },
            "has_frontend": config.has_frontend_involvement(),
        },
    )

    all_files = _collect_files(project_dir)
    agents_dir = project_dir / ".claude" / "agents"
    agents = config.get_active_agents()

    # Build files summary for completeness check
    files_summary_lines = []
    for path in sorted(all_files.keys()):
        size = len(all_files[path])
        files_summary_lines.append(f"- {path} ({size} chars)")
    files_summary = "\n".join(files_summary_lines)

    # Build config YAML
    config_yaml = yaml.dump(config.model_dump(mode="json"), default_flow_style=False)

    # Build agent content summaries
    agent_contents = {}
    for agent in agents:
        agent_path = agents_dir / f"{agent}.md"
        if agent_path.exists():
            agent_contents[agent] = agent_path.read_text()

    # ---- Dimension 1: Completeness ----
    prompt = _build_completeness_prompt(files_summary, config)
    result = _ask_llm(prompt)
    report.dimensions.append(DimensionResult(
        name="Completeness",
        score=max(0, min(100, result.score)),
        details=result.reasoning,
    ))

    # ---- Dimension 2: Config Fidelity ----
    # Build combined content for fidelity check
    key_files = []
    if "CLAUDE.md" in all_files:
        key_files.append(f"### CLAUDE.md\n{_truncate(all_files['CLAUDE.md'], 2000)}")
    if "team-init-plan.md" in all_files:
        key_files.append(f"### team-init-plan.md\n{_truncate(all_files['team-init-plan.md'], 2000)}")
    tl_key = ".claude/agents/team-leader.md"
    if tl_key in all_files:
        key_files.append(f"### team-leader.md\n{_truncate(all_files[tl_key], 2000)}")
    files_content = "\n\n".join(key_files)

    prompt = _build_config_fidelity_prompt(files_content, config_yaml)
    result = _ask_llm(prompt)
    report.dimensions.append(DimensionResult(
        name="Config Fidelity",
        score=max(0, min(100, result.score)),
        details=result.reasoning,
    ))

    # ---- Dimension 3: Instruction Clarity (sample 2 agents) ----
    clarity_scores = []
    # Always check team-leader, then pick one role-specific agent
    sample_agents = ["team-leader"]
    role_agents = [a for a in agents if a not in ("team-leader", "critic")]
    if role_agents:
        sample_agents.append(role_agents[0])

    for agent in sample_agents:
        if agent in agent_contents:
            prompt = _build_instruction_clarity_prompt(
                _truncate(agent_contents[agent], 8000), agent
            )
            result = _ask_llm(prompt)
            clarity_scores.append(result.score)

    avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0
    report.dimensions.append(DimensionResult(
        name="Instruction Clarity",
        score=max(0, min(100, int(avg_clarity))),
        details=f"Evaluated {len(sample_agents)} agents. Individual scores: {clarity_scores}",
    ))

    # ---- Dimension 4: Workflow Enforcement ----
    # Extract full workflow sections from key agents
    wf_excerpts = []

    # Get the full Workflow Enforcement Protocol from one agent (they're identical)
    sample_agent = "backend-developer" if "backend-developer" in agent_contents else agents[0]
    if sample_agent in agent_contents:
        content = agent_contents[sample_agent]
        wf_start = content.find("## Workflow Enforcement Protocol")
        if wf_start >= 0:
            # Find the next major section
            next_section = content.find("\n---\n", wf_start + 10)
            if next_section < 0:
                next_section = content.find("\n## ", wf_start + 10)
            wf_end = next_section if next_section > 0 else wf_start + 3000
            wf_excerpts.append(f"### Workflow Enforcement Protocol (from {sample_agent})\n{content[wf_start:wf_end]}")

    # Get team-leader governance
    if "team-leader" in agent_contents:
        content = agent_contents["team-leader"]
        gov_start = content.find("## Workflow Governance")
        if gov_start >= 0:
            gov_end = content.find("\n---\n", gov_start + 10)
            if gov_end < 0:
                gov_end = gov_start + 2000
            wf_excerpts.append(f"### Team Leader Governance\n{content[gov_start:gov_end]}")

    # Get critic governance
    if "critic" in agent_contents:
        content = agent_contents["critic"]
        for section_name in ["## Governance Oversight", "## Sub-Team Critic Role"]:
            idx = content.find(section_name)
            if idx >= 0:
                end = content.find("\n## ", idx + 10)
                if end < 0:
                    end = idx + 1500
                wf_excerpts.append(f"### Critic — {section_name.lstrip('#').strip()}\n{content[idx:end]}")

    # Get Jira-before-work from atlassian section
    if config.atlassian.enabled and sample_agent in agent_contents:
        content = agent_contents[sample_agent]
        jira_idx = content.find("### MANDATORY: Jira Task Before Work")
        if jira_idx >= 0:
            jira_end = content.find("\n### Your Jira Responsibilities", jira_idx + 10)
            if jira_end < 0:
                jira_end = jira_idx + 1500
            wf_excerpts.append(f"### Jira-Before-Work Mandate\n{content[jira_idx:jira_end]}")

    # Get spawning leadership/critic
    if config.agents.allow_sub_agent_spawning and sample_agent in agent_contents:
        content = agent_contents[sample_agent]
        for section_name in ["### Leadership Responsibilities", "### Mandatory Sub-Team Critic"]:
            idx = content.find(section_name)
            if idx >= 0:
                end = content.find("\n### ", idx + 10)
                if end < 0:
                    end = idx + 1500
                wf_excerpts.append(f"### Spawning — {section_name.lstrip('#').strip()}\n{content[idx:end]}")

    # Get scrum master
    if "scrum-master" in agent_contents:
        sm = agent_contents["scrum-master"]
        idx = sm.find("### Workflow Enforcement")
        if idx >= 0:
            end = sm.find("\n## ", idx + 10)
            if end < 0:
                end = idx + 1500
            wf_excerpts.append(f"### Scrum Master Workflow Enforcement\n{sm[idx:end]}")

    wf_content = "\n\n".join(wf_excerpts) if wf_excerpts else "No workflow sections found"
    prompt = _build_workflow_enforcement_prompt(wf_content, config)
    result = _ask_llm(prompt)
    report.dimensions.append(DimensionResult(
        name="Workflow Enforcement",
        score=max(0, min(100, result.score)),
        details=result.reasoning,
    ))

    # ---- Dimension 5: Role Specificity ----
    # Extract just the Identity & Role + Core Responsibilities for each agent.
    # Use compact format: Role, Domain, Mission + first few responsibilities.
    role_summaries = []
    for agent in agents:
        if agent in agent_contents:
            content = agent_contents[agent]
            # Extract from the "# <Agent Name>" header to "## Base Agent Protocol"
            base_idx = content.find("## Base Agent Protocol")
            if base_idx > 0:
                role_part = content[:base_idx]
            else:
                role_part = content[:3000]

            # Further compact: extract Identity & Core Responsibilities only
            identity_start = role_part.find("## Identity & Role")
            if identity_start < 0:
                identity_start = role_part.find("# ")
            if identity_start >= 0:
                role_part = role_part[identity_start:]

            role_summaries.append(f"### {agent}\n{_truncate(role_part, 1000)}")

    all_agents_content = "\n\n".join(role_summaries)
    prompt = _build_role_specificity_prompt(all_agents_content, len(agents))
    result = _ask_llm(prompt)
    report.dimensions.append(DimensionResult(
        name="Role Specificity",
        score=max(0, min(100, result.score)),
        details=result.reasoning,
    ))

    # ---- Dimension 6: Cross-File Consistency ----
    claude_md = all_files.get("CLAUDE.md", "")
    init_plan = all_files.get("team-init-plan.md", "")
    tl_content = agent_contents.get("team-leader", "")
    prompt = _build_consistency_prompt(claude_md, init_plan, tl_content, config)
    result = _ask_llm(prompt)
    report.dimensions.append(DimensionResult(
        name="Cross-File Consistency",
        score=max(0, min(100, result.score)),
        details=result.reasoning,
    ))

    # ---- Overall LLM Assessment ----
    dim_scores = {d.name: d.score for d in report.dimensions}
    config_summary_str = yaml.dump(report.config_summary, default_flow_style=False)
    prompt = _build_overall_prompt(test_name, dim_scores, config_summary_str)
    overall_result = _ask_llm(prompt)
    report.llm_findings = overall_result.reasoning

    # Write report
    _write_report(output_dir, report)
    return report


# ---------------------------------------------------------------------------
# Deterministic pre-LLM validation (fast, no LLM cost)
# ---------------------------------------------------------------------------

def _run_structural_checks(project_dir: Path, config: ForgeConfig) -> list[str]:
    """Run deterministic structural checks. Returns list of failures."""
    failures = []
    agents = config.get_active_agents()

    # Files exist
    if not (project_dir / "CLAUDE.md").exists():
        failures.append("CLAUDE.md missing")
    if not (project_dir / "team-init-plan.md").exists():
        failures.append("team-init-plan.md missing")
    if not (project_dir / ".claude" / "mcp.json").exists():
        failures.append(".claude/mcp.json missing")

    # Agent files
    agents_dir = project_dir / ".claude" / "agents"
    for agent in agents:
        if not (agents_dir / f"{agent}.md").exists():
            failures.append(f"Agent file missing: {agent}.md")

    # Skills
    skills_dir = project_dir / ".claude" / "skills"
    expected_skills = ["team-status.md", "iteration-review.md", "smoke-test.md",
                       "screenshot-review.md", "arch-review.md", "create-pr.md", "release.md"]
    if config.agents.allow_sub_agent_spawning:
        expected_skills.append("spawn-agent.md")
    if config.atlassian.enabled:
        expected_skills.extend(["jira-update.md", "sprint-report.md"])

    for skill in expected_skills:
        if not (skills_dir / skill).exists():
            failures.append(f"Skill file missing: {skill}")

    # Content checks on agent files
    for agent in agents:
        agent_file = agents_dir / f"{agent}.md"
        if not agent_file.exists():
            continue
        content = agent_file.read_text()

        # All agents must have these sections
        for section in ["Project Context", "Base Agent Protocol", "Workflow Enforcement Protocol", "Workspace Detection"]:
            if section not in content:
                failures.append(f"{agent}.md missing section: {section}")

        # Mode value
        if config.mode.value not in content:
            failures.append(f"{agent}.md doesn't mention mode: {config.mode.value}")

        # Spawning conditional
        if config.agents.allow_sub_agent_spawning:
            if "Sub-Agent Spawning Protocol" not in content:
                failures.append(f"{agent}.md missing Sub-Agent Spawning Protocol (spawning enabled)")
        else:
            if "Sub-Agent Spawning Protocol" in content:
                failures.append(f"{agent}.md has Sub-Agent Spawning Protocol (spawning disabled)")

        # Naming conditional
        if config.agent_naming.enabled:
            if "Agent Naming Protocol" not in content:
                failures.append(f"{agent}.md missing Agent Naming Protocol (naming enabled)")
        else:
            if "## Agent Naming Protocol" in content:
                failures.append(f"{agent}.md has Agent Naming Protocol (naming disabled)")

        # Atlassian conditional — check for the section header, not just the string
        # (the string "Atlassian Integration" also appears in Project Context as a status line)
        if config.atlassian.enabled:
            if "## Atlassian Integration" not in content:
                failures.append(f"{agent}.md missing Atlassian Integration section (atlassian enabled)")
        else:
            if "## Atlassian Integration" in content:
                failures.append(f"{agent}.md has Atlassian Integration section (atlassian disabled)")

    # Workflow enforcement specifics
    for agent in agents:
        agent_file = agents_dir / f"{agent}.md"
        if not agent_file.exists():
            continue
        content = agent_file.read_text()

        if "Hierarchical PR Workflow" not in content:
            failures.append(f"{agent}.md missing Hierarchical PR Workflow")

        if config.atlassian.enabled:
            project_key = config.atlassian.jira_project_key
            if project_key:
                # Check that the Jira project key appears in the workflow enforcement section
                wf_start = content.find("## Workflow Enforcement Protocol")
                if wf_start >= 0:
                    wf_section = content[wf_start:wf_start+2000]
                    if project_key not in wf_section:
                        failures.append(f"{agent}.md workflow doesn't reference Jira key {project_key}")

    # Team leader specific
    tl_file = agents_dir / "team-leader.md"
    if tl_file.exists():
        tl = tl_file.read_text()
        if "Workflow Governance (Enforcement)" not in tl:
            failures.append("team-leader.md missing Workflow Governance section")

    # Critic specific
    critic_file = agents_dir / "critic.md"
    if critic_file.exists():
        critic = critic_file.read_text()
        if "Governance Oversight" not in critic:
            failures.append("critic.md missing Governance Oversight")
        if "Sub-Team Critic Role" not in critic:
            failures.append("critic.md missing Sub-Team Critic Role")

    # Scrum master specific (only when Atlassian enabled)
    if config.atlassian.enabled:
        sm_file = agents_dir / "scrum-master.md"
        if sm_file.exists():
            sm = sm_file.read_text()
            if "Workflow Enforcement" not in sm:
                failures.append("scrum-master.md missing Workflow Enforcement")

    # Spawning sub-sections
    if config.agents.allow_sub_agent_spawning:
        for agent in agents:
            agent_file = agents_dir / f"{agent}.md"
            if not agent_file.exists():
                continue
            content = agent_file.read_text()
            if "Sub-Agent Spawning Protocol" in content:
                if "Leadership Responsibilities" not in content:
                    failures.append(f"{agent}.md spawning section missing Leadership Responsibilities")
                if "Mandatory Sub-Team Critic" not in content:
                    failures.append(f"{agent}.md spawning section missing Mandatory Sub-Team Critic")

    # CLAUDE.md checks
    if (project_dir / "CLAUDE.md").exists():
        claude = (project_dir / "CLAUDE.md").read_text()
        if "Workflow Enforcement" not in claude:
            failures.append("CLAUDE.md missing Workflow Enforcement section")
        if config.atlassian.enabled:
            if "Jira-First" not in claude:
                failures.append("CLAUDE.md missing Jira-First (atlassian enabled)")
        else:
            if "Jira-First" in claude:
                failures.append("CLAUDE.md has Jira-First (atlassian disabled)")
        # Sub-Team Critics should only appear when spawning enabled
        if not config.agents.allow_sub_agent_spawning:
            if "Sub-Team Critics" in claude:
                failures.append("CLAUDE.md mentions Sub-Team Critics but spawning is disabled")

    # team-init-plan.md checks
    if (project_dir / "team-init-plan.md").exists():
        plan = (project_dir / "team-init-plan.md").read_text()
        if "Workflow Rules" not in plan:
            failures.append("team-init-plan.md missing Workflow Rules")

    # Visual verification (frontend projects only)
    if config.has_frontend_involvement():
        frontend_agents = {"frontend-engineer", "frontend-developer", "frontend-designer", "qa-engineer"}
        for agent in agents:
            if agent in frontend_agents:
                agent_file = agents_dir / f"{agent}.md"
                if agent_file.exists():
                    content = agent_file.read_text()
                    if "Visual Verification Protocol" not in content:
                        failures.append(f"{agent}.md missing Visual Verification (frontend project)")

    return failures


# ---------------------------------------------------------------------------
# Pytest test class
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_suite_root(tmp_path_factory) -> Path:
    """Create a root directory for all test cases."""
    return tmp_path_factory.mktemp("forge_quality")


class TestForgeQuality:
    """Comprehensive quality evaluation of Forge output across diverse project types.

    Each test case generates a full project workspace, runs structural checks,
    then uses local_claude (opus) to evaluate quality across 6 dimensions.
    """

    @pytest.mark.parametrize("case_name", list(TEST_CASES.keys()))
    def test_forge_quality(self, case_name: str, test_suite_root: Path):
        """Evaluate forge output quality for a specific test case."""
        case = TEST_CASES[case_name]
        config = _build_config(case)

        # Create test case directory
        case_dir = test_suite_root / case_name
        project_dir = case_dir / "project"
        output_dir = case_dir / "outputs"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save config YAML
        config.project.directory = str(project_dir)
        save_config(config, case_dir / "forge-config.yaml")

        # Save requirements file
        (case_dir / "requirements.txt").write_text(
            f"Project: {case['description']}\n\n{case['requirements']}\n"
        )

        # ---- Phase 1: Generate ----
        generate_all(config)

        # ---- Phase 2: Structural checks (deterministic, fast) ----
        structural_failures = _run_structural_checks(project_dir, config)

        # Write structural check results
        (output_dir / "structural_checks.txt").write_text(
            f"Structural Checks for {case_name}\n"
            f"{'='*60}\n"
            f"Failures: {len(structural_failures)}\n\n"
            + ("\n".join(f"  FAIL: {f}" for f in structural_failures) if structural_failures else "All checks passed")
        )

        # Structural failures are hard failures
        assert not structural_failures, (
            f"Structural check failures for {case_name}:\n"
            + "\n".join(f"  - {f}" for f in structural_failures)
        )

        # ---- Phase 3: LLM evaluation ----
        report = _evaluate_test_case(case_name, project_dir, config, output_dir)

        # ---- Phase 4: Assert quality threshold ----
        overall = report.compute_overall()
        assert overall >= 90.0, (
            f"Forge quality score {overall:.1f}/100 < 90% for {case_name}.\n"
            f"Dimension scores: {', '.join(f'{d.name}={d.score}' for d in report.dimensions)}\n"
            f"Report: {output_dir / 'report.md'}"
        )
