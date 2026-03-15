"""Eval case registry — 350+ assertions across all generated file types.

Each function returns eval cases for a specific generated file.
Cases include applicability predicates so they only run for relevant configs.
"""

from __future__ import annotations

from forge_cli.evals import Assertion, CheckType, EvalCase

CT = CheckType  # alias for brevity


def _a(text: str, check: CheckType, value: str, weight: float = 1.0) -> Assertion:
    """Shorthand assertion builder."""
    return Assertion(text=text, check_type=check, value=value, weight=weight)


# ===========================================================================
# Agent file eval cases
# ===========================================================================


def _team_leader_cases() -> list[EvalCase]:
    """10+ eval cases for team-leader.md."""
    fp = ".claude/agents/team-leader.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:team-leader:iteration-lifecycle",
            file_path=fp, file_type=ft,
            description="Contains 7-phase iteration lifecycle",
            assertions=[
                _a("Team leader describes iteration lifecycle phases", CT.CONTAINS, "PLAN"),
                _a("Lifecycle includes EXECUTE phase", CT.CONTAINS, "EXECUTE"),
                _a("Lifecycle includes TEST phase", CT.CONTAINS, "TEST"),
                _a("Lifecycle includes REVIEW phase", CT.CONTAINS, "REVIEW"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:quality-threshold",
            file_path=fp, file_type=ft,
            description="Quality threshold matches mode",
            assertions=[
                _a("Quality threshold value is present", CT.REGEX, r"\b(70|90|100)\s*%"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:agent-roster",
            file_path=fp, file_type=ft,
            description="Agent roster lists active agents",
            assertions=[
                _a("References agent roster or team members", CT.REGEX, r"(?i)(agent|team\s+member|roster)"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:team-init-plan-ref",
            file_path=fp, file_type=ft,
            description="References team-init-plan.md for startup",
            assertions=[
                _a("References team-init-plan.md", CT.CONTAINS, "team-init-plan"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:progressive-work",
            file_path=fp, file_type=ft,
            description="Progressive work advancement instructions",
            assertions=[
                _a("Describes progressive or parallel work advancement", CT.LLM_JUDGE,
                 "Does the file instruct the team leader to advance work progressively, not waiting for all agents to finish before starting new work?"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:smoke-test",
            file_path=fp, file_type=ft,
            description="Smoke test protocol present",
            assertions=[
                _a("Smoke test protocol described", CT.REGEX, r"(?i)smoke\s*test"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:cost-cap",
            file_path=fp, file_type=ft,
            description="Cost cap matches config",
            assertions=[
                _a("Cost cap or budget mentioned", CT.REGEX, r"(?i)(cost|budget|\$\d+)"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:strategy-decision",
            file_path=fp, file_type=ft,
            description="Strategy-appropriate decision authority",
            assertions=[
                _a("Strategy-appropriate decision authority described", CT.LLM_JUDGE,
                 "Does the file describe the team leader's decision-making authority in a way that matches the project strategy (auto-pilot=full autonomy, co-pilot=ask for architecture, micro-manage=ask for everything)?"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:project-description",
            file_path=fp, file_type=ft,
            description="Project description embedded",
            assertions=[
                _a("Project description is embedded, not a generic placeholder", CT.LLM_JUDGE,
                 "Does the file contain the actual project description rather than a generic placeholder like 'your project' or 'the application'?"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiables enforcement section present",
            assertions=[
                _a("Non-negotiables section present", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="agent:team-leader:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section present",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
        ),
    ]


def _backend_developer_cases() -> list[EvalCase]:
    """12 eval cases for backend-developer.md."""
    fp = ".claude/agents/backend-developer.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:backend-dev:cli-framework",
            file_path=fp, file_type=ft,
            description="CLI project backend dev references CLI framework",
            assertions=[
                _a("References CLI framework (Click/Typer/argparse)", CT.REGEX,
                 r"(?i)(click|typer|argparse|command.line|cli)"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="agent:backend-dev:web-framework",
            file_path=fp, file_type=ft,
            description="Web project backend dev references API framework",
            assertions=[
                _a("References API framework (FastAPI/Django/Flask/Express)", CT.REGEX,
                 r"(?i)(fastapi|django|flask|express|api\s+framework)"),
            ],
            applicable_when={"has_web_backend": True},
        ),
        EvalCase(
            id="agent:backend-dev:static-site-role",
            file_path=fp, file_type=ft,
            description="Static site backend dev has redefined role",
            assertions=[
                _a("Role redefined for SSG/build tooling context", CT.LLM_JUDGE,
                 "Is the backend developer role redefined for static site generation, build tooling, or content pipeline rather than traditional backend API development?"),
            ],
            applicable_when={"is_static_site": True},
        ),
        EvalCase(
            id="agent:backend-dev:tech-stack",
            file_path=fp, file_type=ft,
            description="Tech stack languages listed correctly",
            assertions=[
                _a("Programming languages from config are mentioned", CT.LLM_JUDGE,
                 "Does the file mention the project's programming languages from the config context?"),
            ],
        ),
        EvalCase(
            id="agent:backend-dev:database",
            file_path=fp, file_type=ft,
            description="Database-specific patterns mentioned",
            assertions=[
                _a("Database technology referenced", CT.REGEX, r"(?i)(postgres|mysql|mongo|redis|sqlite|database|db)"),
            ],
            applicable_when={"has_databases": True},
        ),
        EvalCase(
            id="agent:backend-dev:llm-gateway",
            file_path=fp, file_type=ft,
            description="LLM Gateway section present",
            assertions=[
                _a("LLM Gateway section or reference present", CT.REGEX, r"(?i)llm.gateway"),
            ],
            applicable_when={"llm_gateway_enabled": True},
        ),
        EvalCase(
            id="agent:backend-dev:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiables compliance section",
            assertions=[
                _a("Non-negotiables compliance section present", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="agent:backend-dev:base-protocol",
            file_path=fp, file_type=ft,
            description="Base Protocol section present",
            assertions=[
                _a("Base Protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
        ),
        EvalCase(
            id="agent:backend-dev:git-workflow",
            file_path=fp, file_type=ft,
            description="Git Workflow section present",
            assertions=[
                _a("Git or workflow section present", CT.REGEX, r"(?i)(git\s+workflow|workflow\s+enforcement|branch|commit)"),
            ],
        ),
        EvalCase(
            id="agent:backend-dev:no-wrong-domain",
            file_path=fp, file_type=ft,
            description="No domain-specific content for wrong domain",
            assertions=[
                _a("No PCI-DSS references in non-financial project", CT.NOT_CONTAINS, "PCI-DSS"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="agent:backend-dev:quality-standards",
            file_path=fp, file_type=ft,
            description="Mode-appropriate quality standards",
            assertions=[
                _a("Quality or mode standards referenced", CT.REGEX, r"(?i)(quality|mode|standard|mvp|production|no.compromise)"),
            ],
        ),
        EvalCase(
            id="agent:backend-dev:project-context",
            file_path=fp, file_type=ft,
            description="Project context section present",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
        ),
    ]


def _architect_cases() -> list[EvalCase]:
    """10 eval cases for architect.md."""
    fp = ".claude/agents/architect.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:architect:cli-design",
            file_path=fp, file_type=ft,
            description="CLI project architecture design",
            assertions=[
                _a("References CLI component architecture or plugin system", CT.REGEX,
                 r"(?i)(component|plugin|module|command|cli\s+arch)"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="agent:architect:web-api-design",
            file_path=fp, file_type=ft,
            description="Web project API contracts and DB schema",
            assertions=[
                _a("References API contracts or database schema design", CT.REGEX,
                 r"(?i)(api\s+contract|schema\s+design|endpoint|database\s+design)"),
            ],
            applicable_when={"has_web_backend": True},
        ),
        EvalCase(
            id="agent:architect:tech-stack-design",
            file_path=fp, file_type=ft,
            description="Tech stack frameworks in design patterns",
            assertions=[
                _a("Tech stack informs design patterns", CT.LLM_JUDGE,
                 "Does the file reference the project's configured tech stack frameworks in its design guidance?"),
            ],
        ),
        EvalCase(
            id="agent:architect:db-schema",
            file_path=fp, file_type=ft,
            description="Database choices reflected in schema guidance",
            assertions=[
                _a("Database technology mentioned in schema/data guidance", CT.REGEX,
                 r"(?i)(schema|data\s+model|migration|database)"),
            ],
            applicable_when={"has_databases": True},
        ),
        EvalCase(
            id="agent:architect:mode-rigor",
            file_path=fp, file_type=ft,
            description="Mode-appropriate design rigor",
            assertions=[
                _a("Design rigor appropriate to mode", CT.LLM_JUDGE,
                 "Does the file adjust its design rigor to the project mode (MVP=pragmatic, production-ready=thorough, no-compromise=exhaustive)?"),
            ],
        ),
        EvalCase(
            id="agent:architect:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiables as architectural constraints",
            assertions=[
                _a("Non-negotiables section present", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="agent:architect:workspace-awareness",
            file_path=fp, file_type=ft,
            description="Workspace type awareness",
            assertions=[
                _a("Design responsibilities or system design section present", CT.LLM_JUDGE,
                 "Does the file include system design responsibilities such as component boundaries, data flow, or module organization?"),
            ],
        ),
        EvalCase(
            id="agent:architect:integration-patterns",
            file_path=fp, file_type=ft,
            description="Integration patterns for infrastructure",
            assertions=[
                _a("Integration or infrastructure patterns described", CT.REGEX,
                 r"(?i)(integration|infrastructure|deployment|docker|ci.cd)"),
            ],
        ),
        EvalCase(
            id="agent:architect:project-context",
            file_path=fp, file_type=ft,
            description="Project context section present",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
        ),
        EvalCase(
            id="agent:architect:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section present",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
        ),
    ]


def _research_strategist_cases() -> list[EvalCase]:
    """10 eval cases for research-strategist.md."""
    fp = ".claude/agents/research-strategist.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:research:cli-research",
            file_path=fp, file_type=ft,
            description="CLI project research areas",
            assertions=[
                _a("References CLI UX research or ecosystem analysis", CT.REGEX,
                 r"(?i)(cli|command.line|terminal|plugin\s+ecosystem)"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="agent:research:web-research",
            file_path=fp, file_type=ft,
            description="Web project research areas",
            assertions=[
                _a("References API design patterns or scaling", CT.REGEX,
                 r"(?i)(api|scal|endpoint|performance|load)"),
            ],
            applicable_when={"has_web_backend": True},
        ),
        EvalCase(
            id="agent:research:project-description",
            file_path=fp, file_type=ft,
            description="Project description informs research",
            assertions=[
                _a("Research agenda informed by project description", CT.LLM_JUDGE,
                 "Does the file's research agenda specifically address the project's domain and requirements rather than generic research topics?"),
            ],
        ),
        EvalCase(
            id="agent:research:tech-stack-research",
            file_path=fp, file_type=ft,
            description="Tech stack drives research",
            assertions=[
                _a("Tech stack mentioned in research areas", CT.LLM_JUDGE,
                 "Does the file reference the project's configured tech stack in its research topics?"),
            ],
        ),
        EvalCase(
            id="agent:research:competitive-analysis",
            file_path=fp, file_type=ft,
            description="Competitive analysis approach",
            assertions=[
                _a("Competitive or market analysis mentioned", CT.REGEX,
                 r"(?i)(competitive|market|alternative|comparison|landscape|ecosystem|survey|prior\s+art|existing\s+solution)"),
            ],
        ),
        EvalCase(
            id="agent:research:requirements-questions",
            file_path=fp, file_type=ft,
            description="Requirements distilled into research questions",
            assertions=[
                _a("Research questions or investigation areas defined", CT.LLM_JUDGE,
                 "Does the file distill project requirements into specific research questions or investigation areas?"),
            ],
        ),
        EvalCase(
            id="agent:research:mode-depth",
            file_path=fp, file_type=ft,
            description="Mode-appropriate research depth",
            assertions=[
                _a("Research depth appropriate to mode", CT.REGEX,
                 r"(?i)(mvp|production|no.compromise|mode|quality)"),
            ],
        ),
        EvalCase(
            id="agent:research:deliverables",
            file_path=fp, file_type=ft,
            description="Deliverables defined",
            assertions=[
                _a("Research deliverables or outputs defined", CT.REGEX,
                 r"(?i)(deliverable|output|document|report|recommendation|strategy)"),
            ],
        ),
        EvalCase(
            id="agent:research:project-context",
            file_path=fp, file_type=ft,
            description="Project context section present",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
        ),
        EvalCase(
            id="agent:research:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section present",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
        ),
    ]


def _frontend_engineer_cases() -> list[EvalCase]:
    """10 eval cases for frontend-engineer.md."""
    fp = ".claude/agents/frontend-engineer.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:frontend-eng:framework",
            file_path=fp, file_type=ft,
            description="Frontend framework referenced",
            assertions=[
                _a("Frontend framework mentioned (React/Vue/Next.js/etc)", CT.REGEX,
                 r"(?i)(react|vue|angular|next|svelte|frontend\s+framework)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer"},
        ),
        EvalCase(
            id="agent:frontend-eng:visual-verification",
            file_path=fp, file_type=ft,
            description="Visual Verification Protocol present",
            assertions=[
                _a("Visual verification or screenshot protocol present", CT.REGEX,
                 r"(?i)(visual\s+verif|screenshot|playwright)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer"},
        ),
        EvalCase(
            id="agent:frontend-eng:responsive",
            file_path=fp, file_type=ft,
            description="Responsive design requirements",
            assertions=[
                _a("Responsive design or mobile mentioned", CT.REGEX,
                 r"(?i)(responsive|mobile|breakpoint|viewport)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer", "has_frontend_involvement": True},
        ),
        EvalCase(
            id="agent:frontend-eng:accessibility",
            file_path=fp, file_type=ft,
            description="Accessibility standards",
            assertions=[
                _a("Accessibility (a11y/WCAG) mentioned", CT.REGEX,
                 r"(?i)(accessib|a11y|wcag|aria|screen\s+reader)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer", "has_frontend_involvement": True},
        ),
        EvalCase(
            id="agent:frontend-eng:component-architecture",
            file_path=fp, file_type=ft,
            description="Component architecture patterns",
            assertions=[
                _a("Component architecture or patterns described", CT.REGEX,
                 r"(?i)(component|pattern|architecture|design\s+system)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer"},
        ),
        EvalCase(
            id="agent:frontend-eng:testing",
            file_path=fp, file_type=ft,
            description="Frontend testing approach",
            assertions=[
                _a("Testing approach described (unit + visual)", CT.REGEX,
                 r"(?i)(test|spec|jest|vitest|cypress|playwright)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer"},
        ),
        EvalCase(
            id="agent:frontend-eng:build-tooling",
            file_path=fp, file_type=ft,
            description="Build tooling awareness",
            assertions=[
                _a("Build tooling referenced (webpack/vite/etc)", CT.REGEX,
                 r"(?i)(build|webpack|vite|bundle|transpil|compile)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer"},
        ),
        EvalCase(
            id="agent:frontend-eng:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer"},
        ),
        EvalCase(
            id="agent:frontend-eng:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer"},
        ),
        EvalCase(
            id="agent:frontend-eng:state-management",
            file_path=fp, file_type=ft,
            description="State management approach",
            assertions=[
                _a("State management referenced", CT.REGEX,
                 r"(?i)(state\s+manag|redux|zustand|context|store|signal)"),
            ],
            applicable_when={"agent_in_roster": "frontend-engineer", "has_frontend_involvement": True},
        ),
    ]


def _qa_engineer_cases() -> list[EvalCase]:
    """10 eval cases for qa-engineer.md."""
    fp = ".claude/agents/qa-engineer.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:qa:cli-testing",
            file_path=fp, file_type=ft,
            description="CLI project command testing",
            assertions=[
                _a("References command/CLI testing approach", CT.REGEX,
                 r"(?i)(command|cli|terminal|subprocess|pipeline).{0,40}(test|verif|validat)"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="agent:qa:web-testing",
            file_path=fp, file_type=ft,
            description="Web project API and visual testing",
            assertions=[
                _a("References API contract testing", CT.REGEX,
                 r"(?i)(api|endpoint|contract|integration)\s*(test|verif)"),
            ],
            applicable_when={"has_web_backend": True},
        ),
        EvalCase(
            id="agent:qa:test-tiers",
            file_path=fp, file_type=ft,
            description="Test tier architecture",
            assertions=[
                _a("Test tier architecture defined (unit/integration/e2e)", CT.REGEX,
                 r"(?i)(unit|integration|e2e|end.to.end)"),
            ],
        ),
        EvalCase(
            id="agent:qa:db-testing",
            file_path=fp, file_type=ft,
            description="Database testing approach",
            assertions=[
                _a("Database testing approach described", CT.LLM_JUDGE,
                 "Does the file describe a testing approach for database operations, including any of: database testing, migration testing, schema validation, integration tests with real DB, or test data management?"),
            ],
            applicable_when={"has_databases": True},
        ),
        EvalCase(
            id="agent:qa:dry-run",
            file_path=fp, file_type=ft,
            description="Dry-run capability mentioned",
            assertions=[
                _a("Dry-run or mock testing mentioned", CT.REGEX,
                 r"(?i)(dry.run|mock|fake|stub|test\s+double)"),
            ],
        ),
        EvalCase(
            id="agent:qa:quality-gates",
            file_path=fp, file_type=ft,
            description="Quality gate thresholds",
            assertions=[
                _a("Quality gate thresholds referenced", CT.REGEX,
                 r"(?i)(quality\s+gate|threshold|coverage|pass\s+rate)"),
            ],
        ),
        EvalCase(
            id="agent:qa:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiable test requirements",
            assertions=[
                _a("Non-negotiables section present", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="agent:qa:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
        ),
        EvalCase(
            id="agent:qa:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
        ),
        EvalCase(
            id="agent:qa:mode-coverage",
            file_path=fp, file_type=ft,
            description="Mode-appropriate coverage requirements",
            assertions=[
                _a("Coverage or quality standards match mode", CT.REGEX,
                 r"(?i)(coverage|quality|70|90|100)\s*%?"),
            ],
        ),
    ]


def _devops_specialist_cases() -> list[EvalCase]:
    """10 eval cases for devops-specialist.md."""
    fp = ".claude/agents/devops-specialist.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:devops:cli-pipeline",
            file_path=fp, file_type=ft,
            description="CLI project publishing pipeline",
            assertions=[
                _a("References CLI publishing (PyPI/npm) or CI pipeline", CT.REGEX,
                 r"(?i)(pypi|npm\s+publish|pip|package|distribut|ci.cd)"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="agent:devops:web-deploy",
            file_path=fp, file_type=ft,
            description="Web project Docker/CI/CD",
            assertions=[
                _a("References Docker or containerized deployment", CT.REGEX,
                 r"(?i)(docker|container|kubernetes|k8s|deploy)"),
            ],
            applicable_when={"has_web_backend": True},
        ),
        EvalCase(
            id="agent:devops:infra-match",
            file_path=fp, file_type=ft,
            description="Infrastructure matches config",
            assertions=[
                _a("Infrastructure references match config", CT.LLM_JUDGE,
                 "Does the file reference infrastructure technologies that match or relate to the project's configured infrastructure?"),
            ],
        ),
        EvalCase(
            id="agent:devops:db-deploy",
            file_path=fp, file_type=ft,
            description="Database deployment",
            assertions=[
                _a("Database deployment or migration mentioned", CT.REGEX,
                 r"(?i)(database|db|migration|schema|postgres|mysql)"),
            ],
            applicable_when={"has_databases": True},
        ),
        EvalCase(
            id="agent:devops:env-management",
            file_path=fp, file_type=ft,
            description="Environment management",
            assertions=[
                _a("Environment management described (dev/staging/prod)", CT.REGEX,
                 r"(?i)(environment|dev|staging|prod|env)"),
            ],
        ),
        EvalCase(
            id="agent:devops:monitoring",
            file_path=fp, file_type=ft,
            description="Monitoring and observability",
            assertions=[
                _a("Monitoring or observability mentioned", CT.REGEX,
                 r"(?i)(monitor|observ|log|metric|alert|health\s*check)"),
            ],
        ),
        EvalCase(
            id="agent:devops:security-ci",
            file_path=fp, file_type=ft,
            description="Security in CI pipeline",
            assertions=[
                _a("Security scanning in CI", CT.REGEX,
                 r"(?i)(security|scan|audit|vulnerab|secret|gitleaks)"),
            ],
        ),
        EvalCase(
            id="agent:devops:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
        ),
        EvalCase(
            id="agent:devops:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
        ),
        EvalCase(
            id="agent:devops:mode-rigor",
            file_path=fp, file_type=ft,
            description="Mode-appropriate deployment rigor",
            assertions=[
                _a("Deployment rigor matches mode", CT.REGEX,
                 r"(?i)(mode|quality|mvp|production|no.compromise)"),
            ],
        ),
    ]


def _critic_cases() -> list[EvalCase]:
    """10 eval cases for critic.md."""
    fp = ".claude/agents/critic.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:critic:eval-criteria",
            file_path=fp, file_type=ft,
            description="Evaluation criteria match mode",
            assertions=[
                _a("Evaluation criteria or quality standards described", CT.REGEX,
                 r"(?i)(evaluat|criteria|quality|standard|review)"),
            ],
        ),
        EvalCase(
            id="agent:critic:agent-review",
            file_path=fp, file_type=ft,
            description="References agents for review",
            assertions=[
                _a("References team agents for review", CT.REGEX,
                 r"(?i)(agent|team\s+member|developer|engineer|architect)"),
            ],
        ),
        EvalCase(
            id="agent:critic:visual-review",
            file_path=fp, file_type=ft,
            description="Visual verification review for frontend",
            assertions=[
                _a("Visual verification review included", CT.REGEX,
                 r"(?i)(visual|screenshot|ui|interface)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
        EvalCase(
            id="agent:critic:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiable compliance checking",
            assertions=[
                _a("Non-negotiables evaluation section present", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="agent:critic:code-quality",
            file_path=fp, file_type=ft,
            description="Code quality standards",
            assertions=[
                _a("Code quality standards described", CT.REGEX,
                 r"(?i)(code\s+quality|lint|format|type\s+check|clean\s+code)"),
            ],
        ),
        EvalCase(
            id="agent:critic:architecture-review",
            file_path=fp, file_type=ft,
            description="Architecture review criteria",
            assertions=[
                _a("Architecture review criteria", CT.REGEX,
                 r"(?i)(architect|design|pattern|structure|modular)"),
            ],
        ),
        EvalCase(
            id="agent:critic:testing-coverage",
            file_path=fp, file_type=ft,
            description="Testing coverage verification",
            assertions=[
                _a("Testing or coverage verification", CT.REGEX,
                 r"(?i)(test|coverage|verif|validat)"),
            ],
        ),
        EvalCase(
            id="agent:critic:security-review",
            file_path=fp, file_type=ft,
            description="Security review criteria",
            assertions=[
                _a("Security review criteria", CT.REGEX,
                 r"(?i)(security|vulnerab|injection|auth|secret)"),
            ],
        ),
        EvalCase(
            id="agent:critic:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
        ),
        EvalCase(
            id="agent:critic:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
        ),
    ]


def _scrum_master_cases() -> list[EvalCase]:
    """10 eval cases for scrum-master.md (Atlassian-only)."""
    fp = ".claude/agents/scrum-master.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:scrum:jira-key",
            file_path=fp, file_type=ft,
            description="Jira project key referenced",
            assertions=[
                _a("Jira project or project key referenced", CT.REGEX, r"(?i)(jira|project\s+key|ticket|issue)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:confluence",
            file_path=fp, file_type=ft,
            description="Confluence space referenced",
            assertions=[
                _a("Confluence mentioned", CT.REGEX, r"(?i)(confluence|wiki|documentation\s+space)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:sprint-ceremonies",
            file_path=fp, file_type=ft,
            description="Sprint ceremony definitions",
            assertions=[
                _a("Sprint ceremonies defined (standup/planning/retro)", CT.REGEX,
                 r"(?i)(sprint|standup|planning|retrospective|ceremony)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:workflow",
            file_path=fp, file_type=ft,
            description="Jira workflow described",
            assertions=[
                _a("Workflow states or transitions described", CT.REGEX,
                 r"(?i)(workflow|status|transition|backlog|in.progress|done)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:sprint-planning",
            file_path=fp, file_type=ft,
            description="Sprint planning approach",
            assertions=[
                _a("Sprint planning approach described", CT.REGEX,
                 r"(?i)(sprint\s+plan|planning|story\s+point|estimat)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:backlog",
            file_path=fp, file_type=ft,
            description="Backlog management",
            assertions=[
                _a("Backlog grooming or management", CT.REGEX,
                 r"(?i)(backlog|groom|priorit|refinement)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:velocity",
            file_path=fp, file_type=ft,
            description="Velocity tracking",
            assertions=[
                _a("Velocity or metrics tracking", CT.REGEX,
                 r"(?i)(velocity|metric|throughput|burndown|progress)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:board",
            file_path=fp, file_type=ft,
            description="Board management",
            assertions=[
                _a("Board or Kanban management", CT.REGEX,
                 r"(?i)(board|kanban|column|swim\s*lane)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="agent:scrum:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
    ]


def _security_tester_cases() -> list[EvalCase]:
    """10 eval cases for security-tester.md."""
    fp = ".claude/agents/security-tester.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:security:owasp",
            file_path=fp, file_type=ft,
            description="OWASP Top 10 referenced",
            assertions=[
                _a("OWASP Top 10 methodology referenced", CT.REGEX, r"(?i)(owasp|top\s*10|security\s+standard)"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
        EvalCase(
            id="agent:security:auth-testing",
            file_path=fp, file_type=ft,
            description="Authentication testing",
            assertions=[
                _a("Authentication testing described", CT.REGEX, r"(?i)(auth|login|session|token|credential)"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
        EvalCase(
            id="agent:security:input-validation",
            file_path=fp, file_type=ft,
            description="Input validation testing",
            assertions=[
                _a("Input validation testing", CT.REGEX, r"(?i)(input\s+valid|sanitiz|injection|xss)"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
        EvalCase(
            id="agent:security:sql-injection",
            file_path=fp, file_type=ft,
            description="SQL injection prevention testing",
            assertions=[
                _a("SQL injection prevention", CT.REGEX, r"(?i)(sql\s+inject|parameteriz|prepared\s+statement)"),
            ],
            applicable_when={"agent_in_roster": "security-tester", "has_databases": True},
        ),
        EvalCase(
            id="agent:security:dependency-audit",
            file_path=fp, file_type=ft,
            description="Dependency audit approach",
            assertions=[
                _a("Dependency auditing mentioned", CT.REGEX, r"(?i)(depend|audit|vulnerab|cve|advisory)"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
        EvalCase(
            id="agent:security:secret-scanning",
            file_path=fp, file_type=ft,
            description="Secret scanning methodology",
            assertions=[
                _a("Secret scanning methodology", CT.REGEX, r"(?i)(secret|scan|gitleaks|credential|leak)"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
        EvalCase(
            id="agent:security:rate-limiting",
            file_path=fp, file_type=ft,
            description="Rate limiting verification",
            assertions=[
                _a("Rate limiting verification", CT.REGEX, r"(?i)(rate\s+limit|throttl|dos|brute\s*force)"),
            ],
            applicable_when={"agent_in_roster": "security-tester", "has_web_backend": True},
        ),
        EvalCase(
            id="agent:security:mode-depth",
            file_path=fp, file_type=ft,
            description="Mode-appropriate security depth",
            assertions=[
                _a("Security depth matches mode", CT.REGEX, r"(?i)(mode|quality|mvp|production|no.compromise)"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
        EvalCase(
            id="agent:security:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
        EvalCase(
            id="agent:security:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
            applicable_when={"agent_in_roster": "security-tester"},
        ),
    ]


def _performance_engineer_cases() -> list[EvalCase]:
    """10 eval cases for performance-engineer.md."""
    fp = ".claude/agents/performance-engineer.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:perf:cli-throughput",
            file_path=fp, file_type=ft,
            description="CLI throughput and memory profiling",
            assertions=[
                _a("CLI throughput or memory profiling mentioned", CT.REGEX,
                 r"(?i)(throughput|memory|profil|benchmark|cli\s+perf)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer", "is_cli_project": True},
        ),
        EvalCase(
            id="agent:perf:api-latency",
            file_path=fp, file_type=ft,
            description="API latency and load testing",
            assertions=[
                _a("API latency or load testing mentioned", CT.REGEX,
                 r"(?i)(latency|load\s+test|response\s+time|rps|throughput)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer", "has_web_backend": True},
        ),
        EvalCase(
            id="agent:perf:db-optimization",
            file_path=fp, file_type=ft,
            description="Database query optimization",
            assertions=[
                _a("Database query optimization mentioned", CT.REGEX,
                 r"(?i)(query\s+optim|index|explain|slow\s+query|n\+1)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer", "has_databases": True},
        ),
        EvalCase(
            id="agent:perf:caching",
            file_path=fp, file_type=ft,
            description="Caching strategy",
            assertions=[
                _a("Caching strategy described", CT.REGEX,
                 r"(?i)(cach|redis|memcach|cdn|invalidat)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer"},
        ),
        EvalCase(
            id="agent:perf:benchmarking",
            file_path=fp, file_type=ft,
            description="Benchmarking methodology",
            assertions=[
                _a("Benchmarking methodology described", CT.REGEX,
                 r"(?i)(benchmark|baseline|metric|measure|profil)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer"},
        ),
        EvalCase(
            id="agent:perf:budgets",
            file_path=fp, file_type=ft,
            description="Performance budgets defined",
            assertions=[
                _a("Performance budgets or targets defined", CT.REGEX,
                 r"(?i)(budget|target|threshold|sla|slo|p99|p95)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer"},
        ),
        EvalCase(
            id="agent:perf:monitoring",
            file_path=fp, file_type=ft,
            description="Monitoring/APM recommendations",
            assertions=[
                _a("Monitoring or APM tool recommendations", CT.REGEX,
                 r"(?i)(monitor|apm|observ|metric|grafana|datadog|newrelic)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer"},
        ),
        EvalCase(
            id="agent:perf:scalability",
            file_path=fp, file_type=ft,
            description="Scalability testing approach",
            assertions=[
                _a("Scalability testing approach", CT.REGEX,
                 r"(?i)(scal|horizontal|vertical|shard|partition|replicate)"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer"},
        ),
        EvalCase(
            id="agent:perf:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer"},
        ),
        EvalCase(
            id="agent:perf:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
            applicable_when={"agent_in_roster": "performance-engineer"},
        ),
    ]


def _documentation_specialist_cases() -> list[EvalCase]:
    """10 eval cases for documentation-specialist.md."""
    fp = ".claude/agents/documentation-specialist.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:docs:cli-reference",
            file_path=fp, file_type=ft,
            description="CLI project command reference",
            assertions=[
                _a("Command reference or --help generation mentioned", CT.REGEX,
                 r"(?i)(command\s+ref|help|usage|man\s+page|cli\s+doc)"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist", "is_cli_project": True},
        ),
        EvalCase(
            id="agent:docs:api-docs",
            file_path=fp, file_type=ft,
            description="API documentation",
            assertions=[
                _a("API documentation approach (OpenAPI/Swagger)", CT.REGEX,
                 r"(?i)(openapi|swagger|api\s+doc|endpoint\s+doc)"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist", "has_web_backend": True},
        ),
        EvalCase(
            id="agent:docs:readme",
            file_path=fp, file_type=ft,
            description="README template included",
            assertions=[
                _a("README template or structure described", CT.REGEX,
                 r"(?i)(readme|getting\s+started|installation|quick\s+start)"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
        EvalCase(
            id="agent:docs:architecture-docs",
            file_path=fp, file_type=ft,
            description="Architecture documentation",
            assertions=[
                _a("Architecture documentation approach", CT.REGEX,
                 r"(?i)(architect|design\s+doc|adr|decision\s+record|diagram)"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
        EvalCase(
            id="agent:docs:deploy-docs",
            file_path=fp, file_type=ft,
            description="Deployment documentation",
            assertions=[
                _a("Deployment documentation mentioned", CT.REGEX,
                 r"(?i)(deploy|setup|configur|install|environment)"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
        EvalCase(
            id="agent:docs:contributing",
            file_path=fp, file_type=ft,
            description="Contributing guide",
            assertions=[
                _a("Contributing guide or team docs", CT.REGEX,
                 r"(?i)(contribut|develop|team\s+guide|onboard)"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
        EvalCase(
            id="agent:docs:mode-depth",
            file_path=fp, file_type=ft,
            description="Mode-appropriate documentation depth",
            assertions=[
                _a("Documentation depth matches mode", CT.REGEX,
                 r"(?i)(mode|mvp|production|no.compromise|quality)"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
        EvalCase(
            id="agent:docs:domain-specific",
            file_path=fp, file_type=ft,
            description="Domain-specific documentation",
            assertions=[
                _a("Domain-specific documentation needs addressed", CT.LLM_JUDGE,
                 "Does the file address documentation needs specific to the project's domain rather than only generic documentation patterns?"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
        EvalCase(
            id="agent:docs:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
        EvalCase(
            id="agent:docs:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
            applicable_when={"agent_in_roster": "documentation-specialist"},
        ),
    ]


def _frontend_designer_cases() -> list[EvalCase]:
    """10 eval cases for frontend-designer.md."""
    fp = ".claude/agents/frontend-designer.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:frontend-design:framework",
            file_path=fp, file_type=ft,
            description="Frontend framework referenced",
            assertions=[
                _a("Frontend framework mentioned", CT.REGEX,
                 r"(?i)(react|vue|angular|next|svelte|frontend|ui)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:visual-verification",
            file_path=fp, file_type=ft,
            description="Visual verification protocol",
            assertions=[
                _a("Visual verification or screenshot protocol", CT.REGEX,
                 r"(?i)(visual\s+verif|screenshot|playwright)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:design-system",
            file_path=fp, file_type=ft,
            description="Design system guidance",
            assertions=[
                _a("Design system or UI library guidance", CT.REGEX,
                 r"(?i)(design\s+system|ui\s+library|component\s+library|style\s+guide)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:responsive",
            file_path=fp, file_type=ft,
            description="Responsive design",
            assertions=[
                _a("Responsive design mentioned", CT.REGEX,
                 r"(?i)(responsive|mobile|breakpoint|viewport|media\s+quer)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:accessibility",
            file_path=fp, file_type=ft,
            description="Accessibility standards",
            assertions=[
                _a("Accessibility mentioned", CT.REGEX,
                 r"(?i)(accessib|a11y|wcag|aria|screen\s+reader)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:ux-principles",
            file_path=fp, file_type=ft,
            description="UX design principles",
            assertions=[
                _a("UX or user experience principles", CT.REGEX,
                 r"(?i)(ux|user\s+experience|usability|interaction|wireframe)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:css-framework",
            file_path=fp, file_type=ft,
            description="CSS framework referenced",
            assertions=[
                _a("CSS framework or styling approach", CT.REGEX,
                 r"(?i)(tailwind|css|sass|scss|styled|emotion|style)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
        EvalCase(
            id="agent:frontend-design:color-typography",
            file_path=fp, file_type=ft,
            description="Color and typography guidelines",
            assertions=[
                _a("Color, typography, or visual design mentioned", CT.REGEX,
                 r"(?i)(color|typograph|font|palette|theme|visual\s+design)"),
            ],
            applicable_when={"agent_in_roster": "frontend-designer"},
        ),
    ]


def _frontend_developer_cases() -> list[EvalCase]:
    """10 eval cases for frontend-developer.md."""
    fp = ".claude/agents/frontend-developer.md"
    ft = "agent"
    return [
        EvalCase(
            id="agent:frontend-dev:framework",
            file_path=fp, file_type=ft,
            description="Frontend framework referenced",
            assertions=[
                _a("Frontend framework mentioned", CT.REGEX,
                 r"(?i)(react|vue|angular|next|svelte|frontend)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:visual-verification",
            file_path=fp, file_type=ft,
            description="Visual verification protocol",
            assertions=[
                _a("Visual verification or screenshot protocol", CT.REGEX,
                 r"(?i)(visual\s+verif|screenshot|playwright)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:component-architecture",
            file_path=fp, file_type=ft,
            description="Component architecture",
            assertions=[
                _a("Component architecture described", CT.REGEX,
                 r"(?i)(component|module|pattern|architect)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:testing",
            file_path=fp, file_type=ft,
            description="Frontend testing approach",
            assertions=[
                _a("Frontend testing approach", CT.REGEX,
                 r"(?i)(test|spec|jest|vitest|cypress|playwright)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:state-management",
            file_path=fp, file_type=ft,
            description="State management",
            assertions=[
                _a("State management referenced", CT.REGEX,
                 r"(?i)(state|redux|zustand|context|store|signal)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:build-tooling",
            file_path=fp, file_type=ft,
            description="Build tooling",
            assertions=[
                _a("Build tooling mentioned", CT.REGEX,
                 r"(?i)(build|webpack|vite|bundle|compile)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:responsive",
            file_path=fp, file_type=ft,
            description="Responsive design",
            assertions=[
                _a("Responsive design mentioned", CT.REGEX,
                 r"(?i)(responsive|mobile|breakpoint|viewport)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:accessibility",
            file_path=fp, file_type=ft,
            description="Accessibility",
            assertions=[
                _a("Accessibility mentioned", CT.REGEX,
                 r"(?i)(accessib|a11y|wcag|aria)"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:project-context",
            file_path=fp, file_type=ft,
            description="Project context section",
            assertions=[
                _a("Project context section present", CT.SECTION_PRESENT, "Project Context"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
        EvalCase(
            id="agent:frontend-dev:base-protocol",
            file_path=fp, file_type=ft,
            description="Base protocol section",
            assertions=[
                _a("Base protocol section present", CT.REGEX, r"(?i)##\s+base\s+(agent\s+)?protocol"),
            ],
            applicable_when={"agent_in_roster": "frontend-developer"},
        ),
    ]


# ===========================================================================
# Skill file eval cases
# ===========================================================================


def _smoke_test_skill_cases() -> list[EvalCase]:
    """10 eval cases for smoke-test.md skill."""
    fp = ".claude/skills/smoke-test.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:smoke-test:cli-tests",
            file_path=fp, file_type=ft,
            description="CLI project command execution tests",
            assertions=[
                _a("CLI command execution tests described", CT.REGEX,
                 r"(?i)(command|cli|subprocess|execute|terminal)"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="skill:smoke-test:web-tests",
            file_path=fp, file_type=ft,
            description="Web project API endpoint tests",
            assertions=[
                _a("API endpoint tests described", CT.REGEX,
                 r"(?i)(api|endpoint|http|request|response|curl|status\s+code)"),
            ],
            applicable_when={"has_web_backend": True},
        ),
        EvalCase(
            id="skill:smoke-test:frontend-tests",
            file_path=fp, file_type=ft,
            description="Frontend browser-based tests",
            assertions=[
                _a("Browser-based tests with Playwright mentioned", CT.REGEX,
                 r"(?i)(browser|playwright|visual|screenshot|render)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
        EvalCase(
            id="skill:smoke-test:tech-stack-commands",
            file_path=fp, file_type=ft,
            description="Test commands match tech stack",
            assertions=[
                _a("Test commands reference configured tech stack", CT.LLM_JUDGE,
                 "Do the test commands or procedures reference the project's configured programming languages and frameworks?"),
            ],
        ),
        EvalCase(
            id="skill:smoke-test:quality-gates",
            file_path=fp, file_type=ft,
            description="Quality gates match mode threshold",
            assertions=[
                _a("Quality or pass criteria mentioned", CT.REGEX,
                 r"(?i)(quality|pass|fail|threshold|gate|criteria)"),
            ],
        ),
        EvalCase(
            id="skill:smoke-test:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiable checks",
            assertions=[
                _a("Non-negotiable checks included", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="skill:smoke-test:db-connectivity",
            file_path=fp, file_type=ft,
            description="Database connectivity test",
            assertions=[
                _a("Database connectivity or migration test", CT.REGEX,
                 r"(?i)(database|db|connect|migration|schema)"),
            ],
            applicable_when={"has_databases": True},
        ),
        EvalCase(
            id="skill:smoke-test:arguments-placeholder",
            file_path=fp, file_type=ft,
            description="$ARGUMENTS placeholder preserved",
            assertions=[
                _a("$ARGUMENTS placeholder present", CT.CONTAINS, "$ARGUMENTS"),
            ],
        ),
        EvalCase(
            id="skill:smoke-test:frontmatter-name",
            file_path=fp, file_type=ft,
            description="Frontmatter name matches",
            assertions=[
                _a("Frontmatter name field present", CT.FRONTMATTER_FIELD, "name"),
            ],
        ),
        EvalCase(
            id="skill:smoke-test:frontmatter-description",
            file_path=fp, file_type=ft,
            description="Frontmatter description present",
            assertions=[
                _a("Frontmatter description field present", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
    ]


def _screenshot_review_skill_cases() -> list[EvalCase]:
    """10 eval cases for screenshot-review.md skill."""
    fp = ".claude/skills/screenshot-review.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:screenshot:cli-variant",
            file_path=fp, file_type=ft,
            description="CLI project terminal output capture",
            assertions=[
                _a("Terminal output capture variant for CLI", CT.REGEX,
                 r"(?i)(terminal|output|command|cli|console)"),
            ],
            applicable_when={"is_cli_project": True},
        ),
        EvalCase(
            id="skill:screenshot:web-variant",
            file_path=fp, file_type=ft,
            description="Web project API docs screenshot",
            assertions=[
                _a("API docs or Swagger screenshot", CT.REGEX,
                 r"(?i)(api\s+doc|swagger|openapi|endpoint)"),
            ],
            applicable_when={"has_web_backend": True, "has_frontend_involvement": False},
        ),
        EvalCase(
            id="skill:screenshot:frontend-variant",
            file_path=fp, file_type=ft,
            description="Frontend browser screenshot",
            assertions=[
                _a("Browser screenshot with Playwright", CT.REGEX,
                 r"(?i)(browser|playwright|screenshot|visual|render)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
        EvalCase(
            id="skill:screenshot:arguments-placeholder",
            file_path=fp, file_type=ft,
            description="$ARGUMENTS placeholder preserved",
            assertions=[
                _a("$ARGUMENTS placeholder present", CT.CONTAINS, "$ARGUMENTS"),
            ],
        ),
        EvalCase(
            id="skill:screenshot:frontmatter-name",
            file_path=fp, file_type=ft,
            description="Frontmatter name matches",
            assertions=[
                _a("Frontmatter name field present", CT.FRONTMATTER_FIELD, "name"),
            ],
        ),
        EvalCase(
            id="skill:screenshot:frontmatter-description",
            file_path=fp, file_type=ft,
            description="Frontmatter description present",
            assertions=[
                _a("Frontmatter description field present", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
        EvalCase(
            id="skill:screenshot:visual-methodology",
            file_path=fp, file_type=ft,
            description="Visual comparison methodology",
            assertions=[
                _a("Visual comparison or review methodology", CT.REGEX,
                 r"(?i)(visual|compare|review|inspect|check|verify)"),
            ],
        ),
        EvalCase(
            id="skill:screenshot:responsive-checks",
            file_path=fp, file_type=ft,
            description="Responsive layout checks",
            assertions=[
                _a("Responsive or viewport checks", CT.REGEX,
                 r"(?i)(responsive|viewport|mobile|tablet|desktop|breakpoint)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
        EvalCase(
            id="skill:screenshot:storage-path",
            file_path=fp, file_type=ft,
            description="Screenshot storage path defined",
            assertions=[
                _a("Screenshot storage path or directory mentioned", CT.REGEX,
                 r"(?i)(screenshot|save|store|docs/|output|path)"),
            ],
        ),
        EvalCase(
            id="skill:screenshot:accessibility-visual",
            file_path=fp, file_type=ft,
            description="Accessibility visual checks",
            assertions=[
                _a("Accessibility or contrast checks mentioned", CT.REGEX,
                 r"(?i)(accessib|contrast|color|a11y|aria)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
    ]


def _create_pr_skill_cases() -> list[EvalCase]:
    """10 eval cases for create-pr.md skill."""
    fp = ".claude/skills/create-pr.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:create-pr:summary-section",
            file_path=fp, file_type=ft,
            description="PR template includes summary",
            assertions=[
                _a("PR template with summary section", CT.REGEX,
                 r"(?i)(summary|description|overview|what\s+changed)"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:team-reviewers",
            file_path=fp, file_type=ft,
            description="References team agents for reviewers",
            assertions=[
                _a("References agents or reviewers", CT.REGEX,
                 r"(?i)(review|agent|team|critic|architect|lead)"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:branch-naming",
            file_path=fp, file_type=ft,
            description="Branch naming convention",
            assertions=[
                _a("Branch naming convention described", CT.REGEX,
                 r"(?i)(branch|naming|convention|format|prefix)"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:quality-checks",
            file_path=fp, file_type=ft,
            description="Quality checks before PR",
            assertions=[
                _a("Quality checks before PR creation", CT.REGEX,
                 r"(?i)(quality|check|test|lint|verify|before|pre)"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:commit-format",
            file_path=fp, file_type=ft,
            description="Commit message format",
            assertions=[
                _a("Commit message format described", CT.REGEX,
                 r"(?i)(commit|conventional|message|format)"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:jira-link",
            file_path=fp, file_type=ft,
            description="Linked Jira ticket for Atlassian",
            assertions=[
                _a("Jira ticket linking mentioned", CT.REGEX, r"(?i)(jira|ticket|issue|link)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="skill:create-pr:test-evidence",
            file_path=fp, file_type=ft,
            description="Test evidence requirements",
            assertions=[
                _a("Test evidence or proof required", CT.REGEX,
                 r"(?i)(test|evidence|proof|pass|coverage|screenshot)"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:arguments-placeholder",
            file_path=fp, file_type=ft,
            description="$ARGUMENTS placeholder preserved",
            assertions=[
                _a("$ARGUMENTS placeholder present", CT.CONTAINS, "$ARGUMENTS"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:frontmatter-name",
            file_path=fp, file_type=ft,
            description="Frontmatter name matches",
            assertions=[
                _a("Frontmatter name field present", CT.FRONTMATTER_FIELD, "name"),
            ],
        ),
        EvalCase(
            id="skill:create-pr:frontmatter-description",
            file_path=fp, file_type=ft,
            description="Frontmatter description present",
            assertions=[
                _a("Frontmatter description field present", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
    ]


def _release_skill_cases() -> list[EvalCase]:
    """10 eval cases for release.md skill."""
    fp = ".claude/skills/release.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:release:versioning",
            file_path=fp, file_type=ft,
            description="Versioning strategy",
            assertions=[
                _a("Versioning strategy (semver)", CT.REGEX, r"(?i)(version|semver|semantic|v\d+\.\d+)"),
            ],
        ),
        EvalCase(
            id="skill:release:notes",
            file_path=fp, file_type=ft,
            description="Release notes format",
            assertions=[
                _a("Release notes format described", CT.REGEX, r"(?i)(release\s+note|changelog|what'?s\s+new)"),
            ],
        ),
        EvalCase(
            id="skill:release:git-tag",
            file_path=fp, file_type=ft,
            description="Git tagging approach",
            assertions=[
                _a("Git tagging mentioned", CT.REGEX, r"(?i)(tag|git\s+tag|release\s+tag)"),
            ],
        ),
        EvalCase(
            id="skill:release:jira-release",
            file_path=fp, file_type=ft,
            description="Jira release creation",
            assertions=[
                _a("Jira release creation or update", CT.REGEX, r"(?i)(jira|release\s+version|fix\s+version)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="skill:release:deploy-checklist",
            file_path=fp, file_type=ft,
            description="Deployment checklist",
            assertions=[
                _a("Deployment checklist or steps", CT.REGEX, r"(?i)(deploy|checklist|step|verify)"),
            ],
        ),
        EvalCase(
            id="skill:release:rollback",
            file_path=fp, file_type=ft,
            description="Rollback procedure",
            assertions=[
                _a("Rollback procedure described", CT.REGEX, r"(?i)(rollback|revert|undo|previous\s+version)"),
            ],
        ),
        EvalCase(
            id="skill:release:pre-release-verify",
            file_path=fp, file_type=ft,
            description="Pre-release verification",
            assertions=[
                _a("Pre-release verification steps", CT.REGEX, r"(?i)(pre.release|verify|check|test\s+before)"),
            ],
        ),
        EvalCase(
            id="skill:release:changelog",
            file_path=fp, file_type=ft,
            description="Changelog generation",
            assertions=[
                _a("Changelog generation or update", CT.REGEX, r"(?i)(changelog|change\s+log|history|commit\s+log|release\s+note|what.?s\s+(new|changed))"),
            ],
        ),
        EvalCase(
            id="skill:release:arguments-placeholder",
            file_path=fp, file_type=ft,
            description="$ARGUMENTS placeholder preserved",
            assertions=[
                _a("$ARGUMENTS placeholder present", CT.CONTAINS, "$ARGUMENTS"),
            ],
        ),
        EvalCase(
            id="skill:release:frontmatter-name",
            file_path=fp, file_type=ft,
            description="Frontmatter name matches",
            assertions=[
                _a("Frontmatter name field present", CT.FRONTMATTER_FIELD, "name"),
            ],
        ),
    ]


def _common_skill_cases(skill_name: str, requires_arguments: bool = True) -> list[EvalCase]:
    """Common eval cases for skills that share similar patterns."""
    fp = f".claude/skills/{skill_name}.md"
    ft = "skill"
    cases = [
        EvalCase(
            id=f"skill:{skill_name}:frontmatter-name",
            file_path=fp, file_type=ft,
            description=f"{skill_name} frontmatter name",
            assertions=[
                _a("Frontmatter name field present", CT.FRONTMATTER_FIELD, "name"),
            ],
        ),
        EvalCase(
            id=f"skill:{skill_name}:frontmatter-description",
            file_path=fp, file_type=ft,
            description=f"{skill_name} frontmatter description",
            assertions=[
                _a("Frontmatter description field present", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
    ]
    if requires_arguments:
        cases.append(
            EvalCase(
                id=f"skill:{skill_name}:arguments-placeholder",
                file_path=fp, file_type=ft,
                description=f"{skill_name} $ARGUMENTS placeholder",
                assertions=[
                    _a("$ARGUMENTS placeholder or argument-hint present", CT.REGEX,
                     r"(\$ARGUMENTS|argument-hint)"),
                ],
            ),
        )
    return cases


def _arch_review_skill_cases() -> list[EvalCase]:
    """Eval cases for arch-review.md skill."""
    fp = ".claude/skills/arch-review.md"
    ft = "skill"
    cases = _common_skill_cases("arch-review")
    cases.extend([
        EvalCase(
            id="skill:arch-review:architecture-criteria",
            file_path=fp, file_type=ft,
            description="Architecture review criteria",
            assertions=[
                _a("Architecture review criteria defined", CT.REGEX,
                 r"(?i)(architect|design|pattern|modularity|coupling|cohesion)"),
            ],
        ),
        EvalCase(
            id="skill:arch-review:tech-stack-review",
            file_path=fp, file_type=ft,
            description="Tech stack in review criteria",
            assertions=[
                _a("Reviews tech stack fit", CT.LLM_JUDGE,
                 "Does the skill review architecture decisions against the project's configured tech stack?"),
            ],
        ),
        EvalCase(
            id="skill:arch-review:scalability",
            file_path=fp, file_type=ft,
            description="Scalability considerations",
            assertions=[
                _a("Scalability or performance considerations", CT.REGEX,
                 r"(?i)(scal|perform|bottleneck|capacity)"),
            ],
        ),
        EvalCase(
            id="skill:arch-review:security-review",
            file_path=fp, file_type=ft,
            description="Security in architecture review",
            assertions=[
                _a("Security considerations in review", CT.REGEX,
                 r"(?i)(security|auth|access\s+control|vulnerab)"),
            ],
        ),
    ])
    return cases


def _code_review_skill_cases() -> list[EvalCase]:
    """Eval cases for code-review.md skill."""
    fp = ".claude/skills/code-review.md"
    ft = "skill"
    cases = _common_skill_cases("code-review", requires_arguments=False)
    cases.extend([
        EvalCase(
            id="skill:code-review:quality-criteria",
            file_path=fp, file_type=ft,
            description="Code quality criteria",
            assertions=[
                _a("Code quality criteria defined", CT.REGEX,
                 r"(?i)(quality|clean|readab|maintain|naming|convention)"),
            ],
        ),
        EvalCase(
            id="skill:code-review:testing-check",
            file_path=fp, file_type=ft,
            description="Testing check in review",
            assertions=[
                _a("Testing or coverage check included", CT.REGEX,
                 r"(?i)(test|coverage|spec|assert)"),
            ],
        ),
        EvalCase(
            id="skill:code-review:security-check",
            file_path=fp, file_type=ft,
            description="Security check in review",
            assertions=[
                _a("Security check in code review", CT.REGEX,
                 r"(?i)(security|inject|xss|vulnerab|secret)"),
            ],
        ),
    ])
    return cases


def _dependency_audit_skill_cases() -> list[EvalCase]:
    """Eval cases for dependency-audit.md skill."""
    fp = ".claude/skills/dependency-audit.md"
    ft = "skill"
    cases = _common_skill_cases("dependency-audit")
    cases.extend([
        EvalCase(
            id="skill:dependency-audit:vulnerability-scan",
            file_path=fp, file_type=ft,
            description="Vulnerability scanning",
            assertions=[
                _a("Vulnerability scanning approach", CT.REGEX,
                 r"(?i)(vulnerab|cve|advisory|audit|scan)"),
            ],
        ),
        EvalCase(
            id="skill:dependency-audit:outdated-check",
            file_path=fp, file_type=ft,
            description="Outdated dependency check",
            assertions=[
                _a("Outdated dependency checking", CT.REGEX,
                 r"(?i)(outdat|updat|upgrade|version|deprecat)"),
            ],
        ),
        EvalCase(
            id="skill:dependency-audit:license-check",
            file_path=fp, file_type=ft,
            description="License compliance check",
            assertions=[
                _a("License compliance checking", CT.REGEX,
                 r"(?i)(license|licens|compliance|legal|mit|apache)"),
            ],
        ),
    ])
    return cases


def _benchmark_skill_cases() -> list[EvalCase]:
    """Eval cases for benchmark.md skill."""
    fp = ".claude/skills/benchmark.md"
    ft = "skill"
    cases = _common_skill_cases("benchmark")
    cases.extend([
        EvalCase(
            id="skill:benchmark:methodology",
            file_path=fp, file_type=ft,
            description="Benchmarking methodology",
            assertions=[
                _a("Benchmarking methodology described", CT.REGEX,
                 r"(?i)(benchmark|baseline|measure|metric|performance)"),
            ],
        ),
        EvalCase(
            id="skill:benchmark:comparison",
            file_path=fp, file_type=ft,
            description="Before/after comparison",
            assertions=[
                _a("Before/after comparison approach", CT.REGEX,
                 r"(?i)(before|after|compar|delta|improvement|regression)"),
            ],
        ),
        EvalCase(
            id="skill:benchmark:report-format",
            file_path=fp, file_type=ft,
            description="Report format",
            assertions=[
                _a("Report or output format described", CT.REGEX,
                 r"(?i)(report|output|result|table|chart|summary)"),
            ],
        ),
    ])
    return cases


def _excalidraw_diagram_skill_cases() -> list[EvalCase]:
    """Eval cases for excalidraw-diagram.md skill."""
    fp = ".claude/skills/excalidraw-diagram.md"
    ft = "skill"
    cases = _common_skill_cases("excalidraw-diagram")
    cases.extend([
        EvalCase(
            id="skill:excalidraw:diagram-types",
            file_path=fp, file_type=ft,
            description="Diagram types described",
            assertions=[
                _a("Diagram types mentioned (architecture, flow, sequence)", CT.REGEX,
                 r"(?i)(diagram|architecture|flow|sequence|class|er\b|entity)"),
            ],
        ),
        EvalCase(
            id="skill:excalidraw:json-format",
            file_path=fp, file_type=ft,
            description="Excalidraw JSON format",
            assertions=[
                _a("Excalidraw JSON format referenced", CT.REGEX,
                 r"(?i)(excalidraw|json|\.excalidraw)"),
            ],
        ),
    ])
    return cases


def _team_status_skill_cases() -> list[EvalCase]:
    """Eval cases for team-status.md skill."""
    fp = ".claude/skills/team-status.md"
    ft = "skill"
    cases = _common_skill_cases("team-status", requires_arguments=False)
    cases.extend([
        EvalCase(
            id="skill:team-status:agent-status",
            file_path=fp, file_type=ft,
            description="Agent status tracking",
            assertions=[
                _a("Agent status or progress tracking", CT.REGEX,
                 r"(?i)(agent|status|progress|task|assign|working)"),
            ],
        ),
        EvalCase(
            id="skill:team-status:blockers",
            file_path=fp, file_type=ft,
            description="Blockers and risks",
            assertions=[
                _a("Blockers or risks tracking", CT.REGEX,
                 r"(?i)(blocker|risk|issue|impediment|stuck)"),
            ],
        ),
    ])
    return cases


def _iteration_review_skill_cases() -> list[EvalCase]:
    """Eval cases for iteration-review.md skill."""
    fp = ".claude/skills/iteration-review.md"
    ft = "skill"
    cases = _common_skill_cases("iteration-review")
    cases.extend([
        EvalCase(
            id="skill:iteration-review:deliverables",
            file_path=fp, file_type=ft,
            description="Deliverables review",
            assertions=[
                _a("Deliverables or output review", CT.REGEX,
                 r"(?i)(deliver|output|complet|done|achiev|result)"),
            ],
        ),
        EvalCase(
            id="skill:iteration-review:quality-assessment",
            file_path=fp, file_type=ft,
            description="Quality assessment",
            assertions=[
                _a("Quality assessment or criteria", CT.REGEX,
                 r"(?i)(quality|assess|evaluat|score|criteria|gate)"),
            ],
        ),
        EvalCase(
            id="skill:iteration-review:next-steps",
            file_path=fp, file_type=ft,
            description="Next steps or recommendations",
            assertions=[
                _a("Next steps or recommendations", CT.REGEX,
                 r"(?i)(next|recommend|action|todo|plan|proceed)"),
            ],
        ),
    ])
    return cases


def _spawn_agent_skill_cases() -> list[EvalCase]:
    """Eval cases for spawn-agent.md skill."""
    fp = ".claude/skills/spawn-agent.md"
    ft = "skill"
    cases = _common_skill_cases("spawn-agent")
    cases.extend([
        EvalCase(
            id="skill:spawn-agent:agent-types",
            file_path=fp, file_type=ft,
            description="Agent types referenced",
            assertions=[
                _a("Agent types or roster referenced", CT.REGEX,
                 r"(?i)(agent|type|roster|team|specialist|developer|engineer)"),
            ],
            applicable_when={"sub_agent_spawning": True},
        ),
        EvalCase(
            id="skill:spawn-agent:task-assignment",
            file_path=fp, file_type=ft,
            description="Task assignment flow",
            assertions=[
                _a("Task assignment or delegation flow", CT.REGEX,
                 r"(?i)(task|assign|delegat|instruction|context)"),
            ],
            applicable_when={"sub_agent_spawning": True},
        ),
        EvalCase(
            id="skill:spawn-agent:instruction-file",
            file_path=fp, file_type=ft,
            description="Instruction file reference",
            assertions=[
                _a("Agent instruction file reference", CT.REGEX,
                 r"(?i)(instruction|\.claude/agents|\.md|agent\s+file)"),
            ],
            applicable_when={"sub_agent_spawning": True},
        ),
    ])
    return cases


def _jira_update_skill_cases() -> list[EvalCase]:
    """Eval cases for jira-update.md skill."""
    fp = ".claude/skills/jira-update.md"
    ft = "skill"
    cases = _common_skill_cases("jira-update")
    cases.extend([
        EvalCase(
            id="skill:jira-update:status-transition",
            file_path=fp, file_type=ft,
            description="Status transition flow",
            assertions=[
                _a("Status transition or workflow update", CT.REGEX,
                 r"(?i)(status|transition|update|move|progress|done)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="skill:jira-update:comment",
            file_path=fp, file_type=ft,
            description="Comment or notes",
            assertions=[
                _a("Comment or notes on ticket", CT.REGEX,
                 r"(?i)(comment|note|update|log|description)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="skill:jira-update:fields",
            file_path=fp, file_type=ft,
            description="Field updates",
            assertions=[
                _a("Field updates (assignee, priority, etc.)", CT.REGEX,
                 r"(?i)(field|assign|priority|label|component|sprint)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
    ])
    return cases


def _sprint_report_skill_cases() -> list[EvalCase]:
    """Eval cases for sprint-report.md skill."""
    fp = ".claude/skills/sprint-report.md"
    ft = "skill"
    cases = _common_skill_cases("sprint-report")
    cases.extend([
        EvalCase(
            id="skill:sprint-report:metrics",
            file_path=fp, file_type=ft,
            description="Sprint metrics",
            assertions=[
                _a("Sprint metrics or velocity", CT.REGEX,
                 r"(?i)(metric|velocity|burndown|story\s+point|throughput)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="skill:sprint-report:completed-items",
            file_path=fp, file_type=ft,
            description="Completed items summary",
            assertions=[
                _a("Completed items or deliverables summary", CT.REGEX,
                 r"(?i)(complet|deliver|done|achiev|finish)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="skill:sprint-report:blockers",
            file_path=fp, file_type=ft,
            description="Blockers and risks",
            assertions=[
                _a("Blockers or risks identified", CT.REGEX,
                 r"(?i)(blocker|risk|issue|impediment|carry.over)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
    ])
    return cases


def _playwright_test_skill_cases() -> list[EvalCase]:
    """Eval cases for playwright-test.md skill."""
    fp = ".claude/skills/playwright-test.md"
    ft = "skill"
    cases = _common_skill_cases("playwright-test")
    cases.extend([
        EvalCase(
            id="skill:playwright:browser-testing",
            file_path=fp, file_type=ft,
            description="Browser testing approach",
            assertions=[
                _a("Browser testing or automation approach", CT.REGEX,
                 r"(?i)(browser|playwright|automat|headless|chromium)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
        EvalCase(
            id="skill:playwright:visual-regression",
            file_path=fp, file_type=ft,
            description="Visual regression testing",
            assertions=[
                _a("Visual regression or screenshot comparison", CT.REGEX,
                 r"(?i)(visual|regression|screenshot|snapshot|compar)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
        EvalCase(
            id="skill:playwright:selectors",
            file_path=fp, file_type=ft,
            description="Element selectors or interactions",
            assertions=[
                _a("Element selectors or user interactions", CT.REGEX,
                 r"(?i)(selector|click|fill|assert|locator|page\.)"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
    ])
    return cases


# ===========================================================================
# Root file eval cases
# ===========================================================================


def _claude_md_cases() -> list[EvalCase]:
    """12 eval cases for CLAUDE.md."""
    fp = "CLAUDE.md"
    ft = "claude_md"
    return [
        EvalCase(
            id="root:claude-md:agent-roster",
            file_path=fp, file_type=ft,
            description="All active agents listed in roster",
            assertions=[
                _a("Agent roster section present", CT.SECTION_PRESENT, "Agent Roster"),
            ],
        ),
        EvalCase(
            id="root:claude-md:mode-stated",
            file_path=fp, file_type=ft,
            description="Mode value stated correctly",
            assertions=[
                _a("Mode value mentioned", CT.REGEX, r"(?i)(mode|mvp|production.ready|no.compromise)"),
            ],
        ),
        EvalCase(
            id="root:claude-md:strategy-stated",
            file_path=fp, file_type=ft,
            description="Strategy value stated correctly",
            assertions=[
                _a("Strategy value mentioned", CT.REGEX, r"(?i)(strategy|auto.pilot|co.pilot|micro.manage)"),
            ],
        ),
        EvalCase(
            id="root:claude-md:tech-stack",
            file_path=fp, file_type=ft,
            description="Tech stack listed",
            assertions=[
                _a("Tech stack or technology mentioned", CT.REGEX,
                 r"(?i)(tech\s+stack|language|framework|technolog)"),
            ],
        ),
        EvalCase(
            id="root:claude-md:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiable requirements section",
            assertions=[
                _a("Non-negotiables section present", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="root:claude-md:visual-verification",
            file_path=fp, file_type=ft,
            description="Visual Verification section for frontend",
            assertions=[
                _a("Visual Verification section present", CT.SECTION_PRESENT, "Visual Verification"),
            ],
            applicable_when={"has_frontend_involvement": True},
        ),
        EvalCase(
            id="root:claude-md:atlassian",
            file_path=fp, file_type=ft,
            description="Atlassian Integration section",
            assertions=[
                _a("Atlassian Integration section present", CT.SECTION_PRESENT, "Atlassian Integration"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="root:claude-md:no-atlassian",
            file_path=fp, file_type=ft,
            description="No Atlassian section when disabled",
            assertions=[
                _a("No Atlassian Integration section when disabled", CT.NOT_CONTAINS, "## Atlassian Integration"),
            ],
            applicable_when={"atlassian_enabled": False},
        ),
        EvalCase(
            id="root:claude-md:git-auth",
            file_path=fp, file_type=ft,
            description="Git Authentication section",
            assertions=[
                _a("Git authentication section present", CT.REGEX, r"(?i)(git\s+auth|ssh|credential)"),
            ],
            applicable_when={"has_ssh_auth": True},
        ),
        EvalCase(
            id="root:claude-md:llm-gateway",
            file_path=fp, file_type=ft,
            description="LLM Gateway section",
            assertions=[
                _a("LLM Gateway section present", CT.SECTION_PRESENT, "LLM Gateway"),
            ],
            applicable_when={"llm_gateway_enabled": True},
        ),
        EvalCase(
            id="root:claude-md:project-description",
            file_path=fp, file_type=ft,
            description="Project description embedded",
            assertions=[
                _a("Project description embedded (not generic)", CT.LLM_JUDGE,
                 "Does the CLAUDE.md contain the actual project description and requirements rather than generic placeholder text?"),
            ],
        ),
        EvalCase(
            id="root:claude-md:completion-rule",
            file_path=fp, file_type=ft,
            description="Project Completion Rule present",
            assertions=[
                _a("Project Completion Rule section present", CT.REGEX,
                 r"(?i)(project\s+completion|completion\s+rule|non.negotiable)"),
            ],
        ),
        EvalCase(
            id="root:claude-md:sub-agent-spawning",
            file_path=fp, file_type=ft,
            description="Sub-Agent Spawning section",
            assertions=[
                _a("Sub-Agent Spawning section present", CT.SECTION_PRESENT, "Sub-Agent Spawning"),
            ],
            applicable_when={"sub_agent_spawning": True},
        ),
    ]


def _team_init_plan_cases() -> list[EvalCase]:
    """12 eval cases for team-init-plan.md."""
    fp = "team-init-plan.md"
    ft = "team_init_plan"
    return [
        EvalCase(
            id="root:team-init:git-auth",
            file_path=fp, file_type=ft,
            description="Phase 0 git auth setup",
            assertions=[
                _a("Git auth setup in Phase 0", CT.REGEX, r"(?i)(git\s+auth|ssh|credential)"),
            ],
            applicable_when={"has_ssh_auth": True},
        ),
        EvalCase(
            id="root:team-init:agent-count",
            file_path=fp, file_type=ft,
            description="Agent count matches config",
            assertions=[
                _a("Agent spawning instructions present", CT.REGEX,
                 r"(?i)(spawn|agent|team\s+member|initializ)"),
            ],
        ),
        EvalCase(
            id="root:team-init:quality-threshold",
            file_path=fp, file_type=ft,
            description="Quality threshold matches mode",
            assertions=[
                _a("Quality threshold or gate mentioned", CT.REGEX,
                 r"(?i)(quality|threshold|gate|\d+\s*%)"),
            ],
        ),
        EvalCase(
            id="root:team-init:atlassian-setup",
            file_path=fp, file_type=ft,
            description="Atlassian setup phase",
            assertions=[
                _a("Atlassian/Jira/Confluence setup phase", CT.REGEX,
                 r"(?i)(atlassian|jira|confluence|sprint\s+board)"),
            ],
            applicable_when={"atlassian_enabled": True},
        ),
        EvalCase(
            id="root:team-init:project-type-tasks",
            file_path=fp, file_type=ft,
            description="Project-type-aware tasks",
            assertions=[
                _a("Implementation tasks present", CT.REGEX,
                 r"(?i)(implement|build|develop|create|task)"),
            ],
        ),
        EvalCase(
            id="root:team-init:workspace-setup",
            file_path=fp, file_type=ft,
            description="Workspace setup matches config",
            assertions=[
                _a("Workspace or project setup described", CT.REGEX,
                 r"(?i)(workspace|project\s+setup|directory|structure)"),
            ],
        ),
        EvalCase(
            id="root:team-init:agent-locations",
            file_path=fp, file_type=ft,
            description="Agent file locations listed",
            assertions=[
                _a("Agent file locations or paths mentioned", CT.REGEX,
                 r"(?i)(\.claude/agents|agent.*\.md|instruction\s+file)"),
            ],
        ),
        EvalCase(
            id="root:team-init:quick-reference",
            file_path=fp, file_type=ft,
            description="Quick reference table",
            assertions=[
                _a("Quick reference or summary section present", CT.REGEX,
                 r"(?i)(quick\s+ref|reference|summary|overview)"),
            ],
        ),
        EvalCase(
            id="root:team-init:non-negotiables",
            file_path=fp, file_type=ft,
            description="Non-negotiable requirements section",
            assertions=[
                _a("Non-negotiables section present", CT.REGEX, r"(?i)non.negotiable"),
            ],
            applicable_when={"has_non_negotiables": True},
        ),
        EvalCase(
            id="root:team-init:agent-naming",
            file_path=fp, file_type=ft,
            description="Agent naming protocol",
            assertions=[
                _a("Agent naming protocol mentioned", CT.REGEX,
                 r"(?i)(agent\s+nam|naming|name\s+.*agent|creative|codename)"),
            ],
            applicable_when={"agent_naming_enabled": True},
        ),
        EvalCase(
            id="root:team-init:iteration-continuation",
            file_path=fp, file_type=ft,
            description="Iteration continuation mandate",
            assertions=[
                _a("Iteration continuation or looping mandate", CT.REGEX,
                 r"(?i)(iteration|continu|next\s+iteration|loop|repeat|proceed)"),
            ],
        ),
        EvalCase(
            id="root:team-init:phase-structure",
            file_path=fp, file_type=ft,
            description="Multi-phase startup structure",
            assertions=[
                _a("Multi-phase startup structure (Phase 0/1/2/3)", CT.REGEX,
                 r"(?i)(phase\s+[0-4]|step\s+[0-4]|stage\s+[0-4])"),
            ],
        ),
    ]


# ===========================================================================
# Checkpoint skill eval cases
# ===========================================================================


def _checkpoint_skill_cases() -> list[EvalCase]:
    """Eval cases for the checkpoint skill."""
    fp = ".claude/skills/checkpoint.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:checkpoint:save-command",
            file_path=fp, file_type=ft,
            description="Save command with JSON schema documented",
            assertions=[
                _a("Checkpoint save command documented", CT.CONTAINS, "save"),
                _a("JSON schema fields described", CT.CONTAINS, "agent_name"),
                _a("Schema includes context_summary", CT.CONTAINS, "context_summary"),
                _a("Schema includes handoff_notes", CT.CONTAINS, "handoff_notes"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:load-command",
            file_path=fp, file_type=ft,
            description="Load/resume command documented",
            assertions=[
                _a("Checkpoint load command documented", CT.CONTAINS, "load"),
                _a("Resume from checkpoint described", CT.REGEX, r"(?i)resum"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:stop-signal",
            file_path=fp, file_type=ft,
            description="Stop signal detection documented",
            assertions=[
                _a("Stop signal check documented", CT.CONTAINS, "check-stop"),
                _a("STOP_REQUESTED sentinel referenced", CT.CONTAINS, "STOP_REQUESTED"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:file-path",
            file_path=fp, file_type=ft,
            description="Checkpoint file path referenced",
            assertions=[
                _a("Checkpoints directory referenced", CT.CONTAINS, ".forge/checkpoints"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:atomic-write",
            file_path=fp, file_type=ft,
            description="Atomic write pattern documented",
            assertions=[
                _a("Atomic write via tmp+rename described", CT.REGEX, r"(?i)(atomic|\.tmp|rename)"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:agent-name-preservation",
            file_path=fp, file_type=ft,
            description="Agent name must survive resume",
            assertions=[
                _a("Agent name preservation emphasized", CT.REGEX,
                 r"(?i)(agent.name.*consistent|MUST.*(be|remain).*(consistent|same|identical)|never.*change.*(name|it))"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:conversation-history",
            file_path=fp, file_type=ft,
            description="Conversation history capture documented",
            assertions=[
                _a("Recent conversation field mentioned", CT.CONTAINS, "recent_conversation"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:sub-agent-hierarchy",
            file_path=fp, file_type=ft,
            description="Sub-agent tracking documented",
            assertions=[
                _a("Sub-agent tracking field mentioned", CT.CONTAINS, "sub_agents"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:frontmatter",
            file_path=fp, file_type=ft,
            description="Skill has proper frontmatter",
            assertions=[
                _a("Has name field", CT.FRONTMATTER_FIELD, "name"),
                _a("Name is checkpoint", CT.CONTAINS, "name: checkpoint"),
                _a("Has description field", CT.FRONTMATTER_FIELD, "description"),
                _a("Has argument-hint", CT.FRONTMATTER_FIELD, "argument-hint"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:non-negotiable",
            file_path=fp, file_type=ft,
            description="Checkpoint rules marked as non-negotiable",
            assertions=[
                _a("Non-negotiable checkpoint rules", CT.REGEX, r"(?i)non.negotiable"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:first-checkpoint",
            file_path=fp, file_type=ft,
            description="First checkpoint urgency is documented",
            assertions=[
                _a("First checkpoint guidance present", CT.REGEX, r"(?i)first.*(checkpoint|action|thing)"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:frequency",
            file_path=fp, file_type=ft,
            description="Checkpoint frequency guidance present",
            assertions=[
                _a("When to checkpoint is described", CT.REGEX, r"(?i)(frequency|when to|after.*(task|phase|decision))"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:project-aware",
            file_path=fp, file_type=ft,
            description="Project-type-specific checkpoint content",
            assertions=[
                _a("Checkpoint guidance is project-type-aware", CT.LLM_JUDGE,
                 "Does the checkpoint skill include project-type-specific guidance "
                 "(e.g., different checkpoint frequencies for CLI vs web vs full-stack projects)?"),
            ],
        ),
        EvalCase(
            id="skill:checkpoint:strategy-aware",
            file_path=fp, file_type=ft,
            description="Strategy-appropriate checkpoint behavior",
            assertions=[
                _a("Checkpoint behavior adapts to strategy", CT.LLM_JUDGE,
                 "Does the checkpoint skill mention strategy-specific behavior "
                 "(e.g., silent saves for auto-pilot, announcing saves for micro-manage)?"),
            ],
        ),
    ]


def _checkpoint_agent_cases() -> list[EvalCase]:
    """Eval cases for checkpoint protocol in agent files."""
    cases: list[EvalCase] = []

    # All agents should have checkpoint protocol
    for agent_type in [
        "team-leader", "backend-developer", "architect", "qa-engineer",
        "critic", "devops-specialist", "research-strategist",
    ]:
        fp = f".claude/agents/{agent_type}.md"
        ft = "agent"
        cases.append(EvalCase(
            id=f"agent:{agent_type}:checkpoint-protocol",
            file_path=fp, file_type=ft,
            description=f"{agent_type} references checkpoint protocol",
            assertions=[
                _a("Agent file includes checkpoint protocol or lifecycle skills", CT.REGEX,
                 r"(?i)(checkpoint\s+protocol|lifecycle\s+skill|decision\s+tree|/checkpoint\s+save)"),
            ],
            applicable_when={"agent_in_roster": agent_type},
        ))

    # Team leader specific cases
    fp = ".claude/agents/team-leader.md"
    ft = "agent"
    cases.extend([
        EvalCase(
            id="agent:team-leader:session-management",
            file_path=fp, file_type=ft,
            description="Team leader has session management section",
            assertions=[
                _a("Session management section present", CT.REGEX,
                 r"(?i)session\s+management"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:stop-cascade",
            file_path=fp, file_type=ft,
            description="Team leader describes cascading stop",
            assertions=[
                _a("Describes stop cascade to agents", CT.REGEX,
                 r"(?i)(stop.*signal|stopping.*session|cascade.*stop|STOP_REQUESTED)"),
            ],
        ),
        EvalCase(
            id="agent:team-leader:resume-reconstruction",
            file_path=fp, file_type=ft,
            description="Team leader describes agent reconstruction on resume",
            assertions=[
                _a("Resume/reconstruction process described", CT.REGEX,
                 r"(?i)(resum.*agent|re-spawn|reconstruct)"),
            ],
        ),
    ])

    return cases


def _checkpoint_claude_md_cases() -> list[EvalCase]:
    """Eval cases for checkpoint in CLAUDE.md."""
    fp = "CLAUDE.md"
    ft = "claude_md"
    return [
        EvalCase(
            id="claude-md:session-management",
            file_path=fp, file_type=ft,
            description="CLAUDE.md has session management section",
            assertions=[
                _a("Session management section present", CT.SECTION_PRESENT, "Session Management"),
            ],
        ),
        EvalCase(
            id="claude-md:checkpoint-reference",
            file_path=fp, file_type=ft,
            description="CLAUDE.md references checkpoint directory",
            assertions=[
                _a("Checkpoint directory referenced", CT.CONTAINS, ".forge/checkpoints"),
            ],
        ),
    ]


def _checkpoint_team_init_plan_cases() -> list[EvalCase]:
    """Eval cases for checkpoint in team-init-plan.md."""
    fp = "team-init-plan.md"
    ft = "team_init_plan"
    return [
        EvalCase(
            id="team-init-plan:session-persistence",
            file_path=fp, file_type=ft,
            description="Session persistence section present",
            assertions=[
                _a("Session persistence section present", CT.SECTION_PRESENT, "Session Persistence"),
            ],
        ),
        EvalCase(
            id="team-init-plan:resume-detection",
            file_path=fp, file_type=ft,
            description="Resume detection described",
            assertions=[
                _a("Resume detection from session.json", CT.REGEX,
                 r"(?i)(resume.*detect|session\.json.*exist|checkpoint.*load)"),
            ],
        ),
    ]


# ===========================================================================
# Lifecycle skill eval cases (context rot reduction)
# ===========================================================================


def _agent_init_skill_cases() -> list[EvalCase]:
    """Eval cases for agent-init.md lifecycle skill."""
    fp = ".claude/skills/agent-init.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:agent-init:frontmatter",
            file_path=fp, file_type=ft,
            description="agent-init skill has correct frontmatter",
            assertions=[
                _a("Has description field", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:fresh-mode",
            file_path=fp, file_type=ft,
            description="agent-init has fresh startup mode",
            assertions=[
                _a("Documents fresh mode", CT.REGEX, r"(?i)(fresh|first.?time|new.?agent|no.?checkpoint)"),
                _a("Reads instruction file", CT.REGEX, r"(?i)(instruction.?file|\.claude/agents/)"),
                _a("Reads CLAUDE.md", CT.CONTAINS, "CLAUDE.md"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:resume-mode",
            file_path=fp, file_type=ft,
            description="agent-init has resume mode",
            assertions=[
                _a("Documents resume mode", CT.REGEX, r"(?i)(resume|existing.?checkpoint|reload)"),
                _a("Loads checkpoint", CT.REGEX, r"(?i)(/checkpoint\s+load|checkpoint.*load)"),
                _a("Reads context anchor", CT.REGEX, r"(?i)(context.?anchor|\.context-anchor\.md)"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:detect-mode",
            file_path=fp, file_type=ft,
            description="agent-init has auto-detect mode",
            assertions=[
                _a("Documents detect mode", CT.REGEX, r"(?i)(detect|auto.?detect|check.*exist)"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:essential-files",
            file_path=fp, file_type=ft,
            description="agent-init references essential_files for context recovery",
            assertions=[
                _a("References essential_files", CT.REGEX, r"(?i)(essential.?files|must.?reload|working.?files)"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:identity-confirmation",
            file_path=fp, file_type=ft,
            description="agent-init confirms agent identity from spawn prompt",
            assertions=[
                _a("Identity confirmation", CT.REGEX, r"(?i)(identity|name|type|parent|confirm|spawn.?prompt)"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:first-checkpoint",
            file_path=fp, file_type=ft,
            description="agent-init creates first checkpoint on fresh start",
            assertions=[
                _a("Creates first checkpoint", CT.REGEX, r"(?i)(/checkpoint\s+save|save.*first|initial.*checkpoint)"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:context-anchor-write",
            file_path=fp, file_type=ft,
            description="agent-init writes context anchor",
            assertions=[
                _a("Writes context anchor", CT.REGEX, r"(?i)(/context-reload\s+anchor|write.*anchor|context.?anchor)"),
            ],
        ),
        EvalCase(
            id="skill:agent-init:quality",
            file_path=fp, file_type=ft,
            description="agent-init is comprehensive and actionable",
            assertions=[
                _a(
                    "Agent-init skill provides clear, step-by-step instructions for agent "
                    "initialization covering both fresh starts and resume scenarios. It should "
                    "include identity confirmation, instruction file loading, checkpoint "
                    "management, and context anchor creation.",
                    CT.LLM_JUDGE,
                    "Evaluate whether this skill file gives an AI agent everything it needs "
                    "to initialize correctly in both fresh-start and resume scenarios.",
                ),
            ],
        ),
    ]


def _respawn_skill_cases() -> list[EvalCase]:
    """Eval cases for respawn.md lifecycle skill."""
    fp = ".claude/skills/respawn.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:respawn:frontmatter",
            file_path=fp, file_type=ft,
            description="respawn skill has correct frontmatter",
            assertions=[
                _a("Has description field", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
        EvalCase(
            id="skill:respawn:checkpoint-validation",
            file_path=fp, file_type=ft,
            description="respawn validates child checkpoint before respawning",
            assertions=[
                _a("Validates checkpoint exists", CT.REGEX,
                 r"(?i)(verif|validat|check|confirm).*checkpoint"),
            ],
        ),
        EvalCase(
            id="skill:respawn:token-reset",
            file_path=fp, file_type=ft,
            description="respawn resets token counter",
            assertions=[
                _a("Resets token counter/estimate", CT.REGEX,
                 r"(?i)(reset|delete|clear|remove).*(token|counter|estimate|\.token-estimate)"),
            ],
        ),
        EvalCase(
            id="skill:respawn:context-anchor-read",
            file_path=fp, file_type=ft,
            description="respawn reads child's context anchor",
            assertions=[
                _a("Reads context anchor", CT.REGEX,
                 r"(?i)(read|load|context.?anchor|\.context-anchor\.md)"),
            ],
        ),
        EvalCase(
            id="skill:respawn:agent-init-resume",
            file_path=fp, file_type=ft,
            description="respawn instructs child to run /agent-init resume",
            assertions=[
                _a("References /agent-init resume", CT.REGEX,
                 r"(?i)/agent-init\s+(resume|detect)"),
            ],
        ),
        EvalCase(
            id="skill:respawn:name-preservation",
            file_path=fp, file_type=ft,
            description="respawn preserves agent name across respawn",
            assertions=[
                _a("Name preservation", CT.REGEX,
                 r"(?i)(same\s+name|exact\s+name|preserv.*name|name.*preserv)"),
            ],
        ),
        EvalCase(
            id="skill:respawn:sub-agent-discovery",
            file_path=fp, file_type=ft,
            description="respawn handles child's own sub-agents",
            assertions=[
                _a("Sub-agent discovery", CT.REGEX,
                 r"(?i)(sub.?agent|child|children|recursive|hierarchy)"),
            ],
        ),
        EvalCase(
            id="skill:respawn:quality",
            file_path=fp, file_type=ft,
            description="respawn skill is comprehensive",
            assertions=[
                _a(
                    "Respawn skill clearly instructs a parent agent on how to respawn "
                    "a child after compaction, including checkpoint validation, context "
                    "anchor loading, token counter reset, and spawn prompt construction.",
                    CT.LLM_JUDGE,
                    "Evaluate whether this skill provides complete, unambiguous instructions "
                    "for respawning an agent after compaction threshold is reached.",
                ),
            ],
        ),
    ]


def _handoff_skill_cases() -> list[EvalCase]:
    """Eval cases for handoff.md lifecycle skill."""
    fp = ".claude/skills/handoff.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:handoff:frontmatter",
            file_path=fp, file_type=ft,
            description="handoff skill has correct frontmatter",
            assertions=[
                _a("Has description field", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
        EvalCase(
            id="skill:handoff:complete-mode",
            file_path=fp, file_type=ft,
            description="handoff has complete mode for finished work",
            assertions=[
                _a("Documents complete mode", CT.REGEX, r"(?i)(complete|finish|done|all.?work)"),
                _a("Sets status to complete", CT.REGEX, r"(?i)(status.*complete|complete.*status)"),
            ],
        ),
        EvalCase(
            id="skill:handoff:compaction-mode",
            file_path=fp, file_type=ft,
            description="handoff has compaction mode for threshold reached",
            assertions=[
                _a("Documents compaction mode", CT.REGEX,
                 r"(?i)(compaction|threshold|requesting.?respawn)"),
                _a("Increments compaction count", CT.REGEX,
                 r"(?i)(compaction.?count|increment)"),
            ],
        ),
        EvalCase(
            id="skill:handoff:blocked-mode",
            file_path=fp, file_type=ft,
            description="handoff has blocked mode for stuck work",
            assertions=[
                _a("Documents blocked mode", CT.REGEX,
                 r"(?i)(block|stuck|cannot.?proceed|unable)"),
            ],
        ),
        EvalCase(
            id="skill:handoff:handoff-report",
            file_path=fp, file_type=ft,
            description="handoff produces structured report",
            assertions=[
                _a("Structured handoff report", CT.REGEX,
                 r"(?i)(handoff.?report|structured.*report|summary|status)"),
                _a("Lists files modified", CT.REGEX,
                 r"(?i)(files.?modified|files.?created|artifacts)"),
            ],
        ),
        EvalCase(
            id="skill:handoff:checkpoint-save",
            file_path=fp, file_type=ft,
            description="handoff saves checkpoint before returning",
            assertions=[
                _a("Saves checkpoint", CT.REGEX,
                 r"(?i)(/checkpoint\s+save|save.*checkpoint)"),
            ],
        ),
        EvalCase(
            id="skill:handoff:context-anchor",
            file_path=fp, file_type=ft,
            description="handoff writes context anchor before returning",
            assertions=[
                _a("Writes context anchor", CT.REGEX,
                 r"(?i)(/context-reload\s+anchor|context.?anchor)"),
            ],
        ),
        EvalCase(
            id="skill:handoff:quality",
            file_path=fp, file_type=ft,
            description="handoff skill is comprehensive",
            assertions=[
                _a(
                    "Handoff skill provides clear instructions for three distinct modes: "
                    "complete (all work done), compaction (threshold reached, requesting "
                    "respawn), and blocked (cannot proceed). Each mode should specify "
                    "checkpoint save behavior, context anchor writing, and report format.",
                    CT.LLM_JUDGE,
                    "Evaluate whether this skill covers all three handoff scenarios with "
                    "clear, actionable steps and proper state preservation.",
                ),
            ],
        ),
    ]


def _context_reload_skill_cases() -> list[EvalCase]:
    """Eval cases for context-reload.md lifecycle skill."""
    fp = ".claude/skills/context-reload.md"
    ft = "skill"
    return [
        EvalCase(
            id="skill:context-reload:frontmatter",
            file_path=fp, file_type=ft,
            description="context-reload skill has correct frontmatter",
            assertions=[
                _a("Has description field", CT.FRONTMATTER_FIELD, "description"),
            ],
        ),
        EvalCase(
            id="skill:context-reload:reload-subcommand",
            file_path=fp, file_type=ft,
            description="context-reload has reload sub-command",
            assertions=[
                _a("Documents reload sub-command", CT.REGEX, r"(?i)(reload|full.*reload|restore.*context)"),
                _a("Loads instruction file", CT.REGEX, r"(?i)(instruction.?file|\.claude/agents/)"),
                _a("Loads CLAUDE.md", CT.CONTAINS, "CLAUDE.md"),
                _a("Loads checkpoint", CT.REGEX, r"(?i)(/checkpoint\s+load|load.*checkpoint)"),
            ],
        ),
        EvalCase(
            id="skill:context-reload:anchor-subcommand",
            file_path=fp, file_type=ft,
            description="context-reload has anchor sub-command",
            assertions=[
                _a("Documents anchor sub-command", CT.REGEX, r"(?i)(anchor|write.*anchor|context.?anchor)"),
                _a("Anchor includes current task", CT.REGEX, r"(?i)(current.?task|working.?on|active.?task)"),
                _a("Anchor includes essential files", CT.REGEX, r"(?i)(essential.?files|critical.?files|working.?files)"),
            ],
        ),
        EvalCase(
            id="skill:context-reload:status-subcommand",
            file_path=fp, file_type=ft,
            description="context-reload has status sub-command",
            assertions=[
                _a("Documents status sub-command", CT.REGEX, r"(?i)(status|check|staleness|health)"),
                _a("Reports token estimate", CT.REGEX, r"(?i)(token|estimate|usage|threshold)"),
            ],
        ),
        EvalCase(
            id="skill:context-reload:essential-files",
            file_path=fp, file_type=ft,
            description="context-reload handles essential_files list",
            assertions=[
                _a("References essential_files", CT.REGEX, r"(?i)(essential.?files|5.?10|curated|must.?reload)"),
            ],
        ),
        EvalCase(
            id="skill:context-reload:compaction-marker",
            file_path=fp, file_type=ft,
            description="context-reload handles compaction marker cleanup",
            assertions=[
                _a("Handles compaction marker", CT.REGEX, r"(?i)(compaction.?marker|\.compaction-marker|delete.*marker|clean.*marker)"),
            ],
        ),
        EvalCase(
            id="skill:context-reload:quality",
            file_path=fp, file_type=ft,
            description="context-reload skill is comprehensive",
            assertions=[
                _a(
                    "Context-reload skill provides clear instructions for three sub-commands: "
                    "reload (full context restoration), anchor (write context snapshot), and "
                    "status (check staleness). It should reference essential_files, checkpoint "
                    "loading, and compaction marker cleanup.",
                    CT.LLM_JUDGE,
                    "Evaluate whether this skill provides a complete context recovery system "
                    "with all three sub-commands clearly documented.",
                ),
            ],
        ),
    ]


def _context_management_claude_md_cases() -> list[EvalCase]:
    """Eval cases for Context Management section in CLAUDE.md."""
    fp = "CLAUDE.md"
    ft = "claude_md"
    return [
        EvalCase(
            id="claude-md:context-management-section",
            file_path=fp, file_type=ft,
            description="CLAUDE.md has context management section",
            assertions=[
                _a("Context management section present", CT.SECTION_PRESENT, "Context Management"),
            ],
        ),
        EvalCase(
            id="claude-md:compaction-threshold",
            file_path=fp, file_type=ft,
            description="CLAUDE.md documents compaction threshold",
            assertions=[
                _a("Compaction threshold documented", CT.REGEX, r"(?i)(compaction.?threshold|100.?000|threshold.*token)"),
            ],
        ),
        EvalCase(
            id="claude-md:lifecycle-skills-section",
            file_path=fp, file_type=ft,
            description="CLAUDE.md lists lifecycle skills",
            assertions=[
                _a("Lifecycle skills section present", CT.SECTION_PRESENT, "Lifecycle Skills"),
                _a("References /agent-init", CT.CONTAINS, "/agent-init"),
                _a("References /handoff", CT.CONTAINS, "/handoff"),
                _a("References /context-reload", CT.CONTAINS, "/context-reload"),
            ],
        ),
    ]


def _checkpoint_protocol_decision_tree_cases() -> list[EvalCase]:
    """Eval cases for Skill Decision Tree in agent instruction files."""
    cases: list[EvalCase] = []
    for agent_type in [
        "team-leader", "backend-developer", "architect",
        "qa-engineer", "devops-specialist", "critic",
    ]:
        fp = f".claude/agents/{agent_type}.md"
        ft = "agent"
        cases.append(EvalCase(
            id=f"agent:{agent_type}:decision-tree",
            file_path=fp, file_type=ft,
            description=f"{agent_type} has skill decision tree",
            assertions=[
                _a("Has decision tree or lifecycle skills reference", CT.REGEX,
                 r"(?i)(decision.?tree|lifecycle.?skill|/agent-init|JUST SPAWNED)"),
                _a("References /handoff", CT.REGEX, r"(?i)/handoff"),
                _a("References /checkpoint save", CT.REGEX, r"(?i)/checkpoint\s+save"),
            ],
            applicable_when={"agent_in_roster": agent_type},
        ))
    return cases


# ===========================================================================
# Registry aggregation
# ===========================================================================


def get_all_eval_cases() -> list[EvalCase]:
    """Return the complete eval case registry (400+ cases)."""
    cases: list[EvalCase] = []

    # Agent file cases
    cases.extend(_team_leader_cases())
    cases.extend(_backend_developer_cases())
    cases.extend(_architect_cases())
    cases.extend(_research_strategist_cases())
    cases.extend(_frontend_engineer_cases())
    cases.extend(_qa_engineer_cases())
    cases.extend(_devops_specialist_cases())
    cases.extend(_critic_cases())
    cases.extend(_scrum_master_cases())
    cases.extend(_security_tester_cases())
    cases.extend(_performance_engineer_cases())
    cases.extend(_documentation_specialist_cases())
    cases.extend(_frontend_designer_cases())
    cases.extend(_frontend_developer_cases())

    # Checkpoint protocol in agent files
    cases.extend(_checkpoint_agent_cases())

    # Skill file cases
    cases.extend(_smoke_test_skill_cases())
    cases.extend(_screenshot_review_skill_cases())
    cases.extend(_create_pr_skill_cases())
    cases.extend(_release_skill_cases())
    cases.extend(_arch_review_skill_cases())
    cases.extend(_code_review_skill_cases())
    cases.extend(_dependency_audit_skill_cases())
    cases.extend(_benchmark_skill_cases())
    cases.extend(_excalidraw_diagram_skill_cases())
    cases.extend(_team_status_skill_cases())
    cases.extend(_iteration_review_skill_cases())
    cases.extend(_spawn_agent_skill_cases())
    cases.extend(_jira_update_skill_cases())
    cases.extend(_sprint_report_skill_cases())
    cases.extend(_playwright_test_skill_cases())
    cases.extend(_checkpoint_skill_cases())

    # Lifecycle skill cases (context rot reduction)
    cases.extend(_agent_init_skill_cases())
    cases.extend(_respawn_skill_cases())
    cases.extend(_handoff_skill_cases())
    cases.extend(_context_reload_skill_cases())

    # Root file cases
    cases.extend(_claude_md_cases())
    cases.extend(_team_init_plan_cases())

    # Checkpoint in root files
    cases.extend(_checkpoint_claude_md_cases())
    cases.extend(_checkpoint_team_init_plan_cases())

    # Context management in root files
    cases.extend(_context_management_claude_md_cases())

    # Decision tree in agent files
    cases.extend(_checkpoint_protocol_decision_tree_cases())

    return cases
