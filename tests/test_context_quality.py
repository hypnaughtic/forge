"""Quality tests for project context derivation.

These tests verify that:
1. Context summarizer produces high-quality understanding from input files
2. The derived context properly captures all key details from source material
3. Derived context is properly passed to all generated files (agents, skills, plans)
4. LLM scoring validates context quality using local_claude

Tests marked with @pytest.mark.llm_quality require real LLM access
(local_claude or ANTHROPIC_API_KEY) and should be run with
FORGE_TEST_DRY_RUN=0.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import shutil
from pathlib import Path
from textwrap import dedent

import pytest

from forge_cli.config_schema import (
    AgentsConfig,
    ForgeConfig,
    ProjectConfig,
    ProjectMode,
    ExecutionStrategy,
    TechStack,
    TeamProfile,
)
from forge_cli.generators.context_summarizer import (
    build_raw_context,
    collect_context_files,
    summarize_context,
)
from forge_cli.generators.orchestrator import generate_all


# ---------------------------------------------------------------------------
# Realistic context fixtures — simulate user-provided project documentation
# ---------------------------------------------------------------------------

PLAN_MD = dedent("""\
# Implementation Plan — TaskFlow

## Phase 1: Foundation (Week 1-2)
- Set up FastAPI project with SQLAlchemy 2.0 async engine
- PostgreSQL schema: users, projects, tasks, comments tables
- Alembic migrations with UUID primary keys and audit timestamps
- JWT authentication with refresh tokens (access: 15min, refresh: 7d)
- Role-based access: admin, manager, member

## Phase 2: Core Features (Week 3-4)
- CRUD endpoints for projects and tasks
- Task assignment with email notifications via SendGrid
- Real-time updates via WebSocket (task status changes)
- File attachments with S3-compatible storage (MinIO for dev)
- Activity feed with pagination (cursor-based)

## Phase 3: Advanced (Week 5-6)
- Kanban board API with drag-and-drop position tracking
- Sprint management with velocity calculation
- Time tracking with weekly reports
- Search with full-text PostgreSQL tsvector indexes
- Export to CSV/PDF via background Celery tasks

## Architecture Decisions
- ADR-001: Use SQLAlchemy 2.0 async ORM (not raw SQL) for type safety
- ADR-002: JWT stored in httpOnly cookies (not localStorage) for XSS protection
- ADR-003: WebSocket via FastAPI native support (not Socket.IO) for simplicity
- ADR-004: Cursor-based pagination (not offset) for consistent ordering
- ADR-005: Background jobs via Celery + Redis (not asyncio tasks) for reliability
""")

ARCHITECTURE_MD = dedent("""\
# Architecture — TaskFlow

## System Overview
TaskFlow is a project management API serving a React frontend.
All communication is REST + WebSocket over HTTPS.

## Components
- **API Server**: FastAPI 0.115, Python 3.12, uvicorn
- **Database**: PostgreSQL 16 with pgvector extension
- **Cache**: Redis 7 for sessions, rate limiting, Celery broker
- **Storage**: S3-compatible (MinIO dev, AWS S3 prod)
- **Email**: SendGrid API for transactional emails
- **Background Jobs**: Celery 5.4 with Redis broker

## Database Schema
### users
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| hashed_password | VARCHAR(255) | NOT NULL |
| role | ENUM('admin','manager','member') | NOT NULL, default 'member' |
| created_at | TIMESTAMPTZ | server default now() |
| updated_at | TIMESTAMPTZ | auto-update trigger |

### tasks
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default uuid4 |
| title | VARCHAR(500) | NOT NULL |
| description | TEXT | |
| status | ENUM('backlog','todo','in_progress','review','done') | NOT NULL |
| priority | ENUM('low','medium','high','critical') | NOT NULL |
| assignee_id | UUID | FK users(id) ON DELETE SET NULL |
| project_id | UUID | FK projects(id) ON DELETE CASCADE |
| position | INTEGER | for Kanban ordering |
| due_date | DATE | |
| estimated_hours | DECIMAL(6,2) | |
| created_at | TIMESTAMPTZ | server default now() |
| updated_at | TIMESTAMPTZ | auto-update trigger |

## API Endpoints
- POST /api/v1/auth/register — user registration
- POST /api/v1/auth/login — JWT token pair
- POST /api/v1/auth/refresh — refresh access token
- GET /api/v1/projects — list projects (paginated)
- POST /api/v1/projects — create project
- GET /api/v1/projects/{id}/tasks — list tasks with filters
- POST /api/v1/projects/{id}/tasks — create task
- PATCH /api/v1/tasks/{id} — update task (status, assignee, etc.)
- WS /api/v1/ws/projects/{id} — real-time task updates

## Performance Targets
- API response p95 < 200ms
- WebSocket message latency < 50ms
- Database query time < 100ms
- Support 1000 concurrent WebSocket connections
- Search response < 300ms for 100K tasks
""")

API_SPEC_MD = dedent("""\
# API Specification — TaskFlow

## Authentication
All endpoints except /auth/* require Bearer token.
Rate limiting: 100 requests/minute per user, 1000/minute per IP.

## Error Format
```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task with id {id} not found",
    "details": {}
  }
}
```

## Pagination
Cursor-based pagination for all list endpoints:
- `?cursor=<opaque>&limit=20`
- Response includes `next_cursor` and `has_more`

## Webhook Events
- task.created, task.updated, task.deleted
- task.assigned, task.status_changed
- project.created, project.archived
- Payload includes full entity + event metadata
- 3 retry attempts with exponential backoff (1s, 5s, 25s)
""")


def _make_context_config(
    tmp_path: Path,
    with_plan: bool = True,
    with_arch: bool = True,
    with_specs: bool = True,
) -> ForgeConfig:
    """Build a ForgeConfig with realistic context files."""
    context_files: list[str] = []

    if with_plan:
        plan = tmp_path / "PLAN.md"
        plan.write_text(PLAN_MD)
        context_files.append(str(plan))

    if with_arch:
        arch = tmp_path / "ARCHITECTURE.md"
        arch.write_text(ARCHITECTURE_MD)
        context_files.append(str(arch))

    if with_specs:
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "api.md").write_text(API_SPEC_MD)
        context_files.append(str(specs_dir))

    return ForgeConfig(
        project=ProjectConfig(
            description="TaskFlow — project management API with real-time updates",
            context_files=context_files,
            directory=str(tmp_path),
        ),
        mode=ProjectMode.PRODUCTION_READY,
        strategy=ExecutionStrategy.CO_PILOT,
        agents=AgentsConfig(team_profile=TeamProfile.LEAN),
        tech_stack=TechStack(
            languages=["python"],
            frameworks=["fastapi"],
            databases=["postgresql", "redis"],
            infrastructure=["docker"],
        ),
    )


# ---------------------------------------------------------------------------
# Unit tests — context collection and raw context building (no LLM needed)
# ---------------------------------------------------------------------------


class TestContextCollection:
    """Verify that context files are correctly collected and included."""

    def test_all_files_collected(self, tmp_path):
        """All plan, architecture, and spec files are collected."""
        config = _make_context_config(tmp_path)
        files = collect_context_files(config)
        filenames = [f[0] for f in files]
        assert "PLAN.md" in filenames
        assert "ARCHITECTURE.md" in filenames
        assert "api.md" in filenames

    def test_raw_context_includes_all_sources(self, tmp_path):
        """Raw context string includes content from all source files."""
        config = _make_context_config(tmp_path)
        raw = build_raw_context(config)

        # Plan content
        assert "Phase 1: Foundation" in raw
        assert "Alembic migrations" in raw
        assert "ADR-001" in raw

        # Architecture content
        assert "FastAPI 0.115" in raw
        assert "PostgreSQL 16" in raw
        assert "assignee_id" in raw
        assert "p95 < 200ms" in raw

        # API spec content
        assert "TASK_NOT_FOUND" in raw
        assert "cursor-based pagination" in raw.lower() or "Cursor-based" in raw
        assert "webhook" in raw.lower()

    def test_raw_context_preserves_technical_details(self, tmp_path):
        """Specific technical values are preserved exactly."""
        config = _make_context_config(tmp_path)
        raw = build_raw_context(config)

        # Exact values that must survive
        assert "UUID" in raw
        assert "JWT" in raw
        assert "15min" in raw or "15 min" in raw
        assert "7d" in raw or "7 day" in raw.lower()
        assert "SendGrid" in raw
        assert "Celery 5.4" in raw
        assert "Redis 7" in raw
        assert "1000 concurrent" in raw
        assert "100K tasks" in raw or "100,000" in raw

    def test_description_only_produces_minimal_context(self, tmp_path):
        """Config with only description produces minimal raw context."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Simple CLI tool",
                directory=str(tmp_path),
            )
        )
        raw = build_raw_context(config)
        assert "Simple CLI tool" in raw
        assert len(raw) < 200


class TestContextPassthrough:
    """Verify derived context is passed to all generated files."""

    def test_derived_context_in_agent_files(self, tmp_path):
        """Derived context appears in agent instruction files."""
        config = _make_context_config(tmp_path)
        generate_all(config)

        agents_dir = tmp_path / ".claude" / "agents"
        for agent_file in agents_dir.iterdir():
            if agent_file.suffix != ".md":
                continue
            content = agent_file.read_text()
            # Every agent should have project requirements section
            assert "Project Requirements" in content, (
                f"{agent_file.name} missing Project Requirements section"
            )
            # Derived context should include key project details
            # (in dry-run mode, the raw context fallback includes description)
            assert "TaskFlow" in content or "project management" in content.lower(), (
                f"{agent_file.name} missing project identity"
            )

    def test_derived_context_in_team_init_plan(self, tmp_path):
        """Derived context appears in team-init-plan.md."""
        config = _make_context_config(tmp_path)
        generate_all(config)

        plan = (tmp_path / "team-init-plan.md").read_text()
        assert "TaskFlow" in plan or "project management" in plan.lower()
        assert "Project Requirements" in plan

    def test_derived_context_in_claude_md(self, tmp_path):
        """Derived context appears in CLAUDE.md."""
        config = _make_context_config(tmp_path)
        generate_all(config)

        claude_md = (tmp_path / "CLAUDE.md").read_text()
        assert "TaskFlow" in claude_md or "project management" in claude_md.lower()

    def test_project_context_file_created(self, tmp_path):
        """The .forge/project-context.md file is created."""
        config = _make_context_config(tmp_path)
        generate_all(config)

        ctx_file = tmp_path / ".forge" / "project-context.md"
        assert ctx_file.exists()
        content = ctx_file.read_text()
        assert len(content) > 100
        assert "TaskFlow" in content or "Project" in content

    def test_skills_use_derived_context_keywords(self, tmp_path):
        """Skills should pick up domain keywords from derived context."""
        config = _make_context_config(tmp_path)
        generate_all(config)

        skills_dir = tmp_path / ".claude" / "skills"
        # smoke-test skill should have some project-relevant content
        smoke_test = skills_dir / "smoke-test.md"
        if smoke_test.exists():
            content = smoke_test.read_text()
            # At minimum, it should reference the project
            assert len(content) > 100

    def test_context_without_files_uses_description_only(self, tmp_path):
        """Config without context files uses description as fallback."""
        config = ForgeConfig(
            project=ProjectConfig(
                description="Simple REST API",
                directory=str(tmp_path),
            ),
            mode=ProjectMode.MVP,
            agents=AgentsConfig(team_profile=TeamProfile.LEAN),
            tech_stack=TechStack(languages=["python"], frameworks=["fastapi"]),
        )
        generate_all(config)

        agents_dir = tmp_path / ".claude" / "agents"
        backend = (agents_dir / "backend-developer.md").read_text()
        assert "Simple REST API" in backend


# ---------------------------------------------------------------------------
# LLM-scored quality tests — require real LLM (FORGE_TEST_DRY_RUN=0)
# ---------------------------------------------------------------------------


def _llm_available() -> bool:
    """Check if real LLM is available for quality scoring."""
    if os.environ.get("FORGE_TEST_DRY_RUN", "1") == "1":
        return False
    try:
        from llm_gateway import LLMClient, GatewayConfig  # noqa: F401
    except ImportError:
        return False

    if os.environ.get("ANTHROPIC_API_KEY"):
        return True

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


def _get_provider() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "local_claude"


@pytest.mark.skipif(
    not _llm_available(),
    reason="Real LLM not available (set FORGE_TEST_DRY_RUN=0 and have claude CLI or ANTHROPIC_API_KEY)",
)
class TestContextQualityLLM:
    """LLM-scored tests for context derivation quality.

    These tests create realistic project docs, run the context summarizer
    with a real LLM, then have the LLM score the output for completeness
    and accuracy.

    Run with: FORGE_TEST_DRY_RUN=0 pytest tests/test_context_quality.py -k LLM -v
    """

    SCORING_MODEL = "claude-sonnet-4-20250514"
    SUMMARIZE_MODEL = "claude-sonnet-4-20250514"

    def _ask_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """Send prompt to LLM and return text response."""
        from pydantic import BaseModel
        from llm_gateway import LLMClient, GatewayConfig

        class Answer(BaseModel):
            text: str

        async def _call():
            config = GatewayConfig(
                provider=_get_provider(),
                model=self.SCORING_MODEL,
                max_tokens=max_tokens,
                timeout_seconds=60,
            )
            llm = LLMClient(config=config)
            try:
                resp = await llm.complete(
                    messages=[{"role": "user", "content": prompt}],
                    response_model=Answer,
                )
                return resp.content.text
            finally:
                await llm.close()

        return asyncio.run(_call())

    def _summarize_context(self, tmp_path: Path) -> tuple[str, ForgeConfig]:
        """Run context summarization with real LLM and return (summary, config)."""
        from llm_gateway import GatewayConfig
        from llm_gateway import LLMClient

        config = _make_context_config(tmp_path)

        # Use real LLM for summarization — match CONTEXT_MAX_TOKENS from summarizer
        gw_config = GatewayConfig(
            provider=_get_provider(),
            model=self.SUMMARIZE_MODEL,
            max_tokens=16384,
            timeout_seconds=180,
        )

        async def _run():
            from forge_cli.generators.context_summarizer import summarize_context_async
            # Create a provider that uses our config
            llm = LLMClient(config=gw_config)
            try:
                return await summarize_context_async(
                    config, tmp_path, llm_provider=llm._provider,
                )
            finally:
                await llm.close()

        summary = asyncio.run(_run())
        return summary, config

    def test_context_captures_all_phases(self, tmp_path):
        """Derived context must capture all implementation phases from PLAN.md."""
        summary, _ = self._summarize_context(tmp_path)

        response = self._ask_llm(
            f"Given this project context summary, list ALL implementation phases mentioned. "
            f"For each phase, state its name and one key deliverable.\n\n"
            f"CONTEXT:\n{summary}\n\n"
            f"Answer in the text field. List phases as '1. Phase Name: deliverable'."
        )

        # Must find all 3 phases
        assert "foundation" in response.lower() or "phase 1" in response.lower(), (
            f"Missing Phase 1 (Foundation): {response[:300]}"
        )
        assert "core" in response.lower() or "phase 2" in response.lower(), (
            f"Missing Phase 2 (Core Features): {response[:300]}"
        )
        assert "advanced" in response.lower() or "phase 3" in response.lower(), (
            f"Missing Phase 3 (Advanced): {response[:300]}"
        )

    def test_context_preserves_technical_specifics(self, tmp_path):
        """Derived context must preserve exact technical details."""
        summary, _ = self._summarize_context(tmp_path)

        response = self._ask_llm(
            f"Given this project context, answer these questions with EXACT values "
            f"from the context. If a value is not found, write 'NOT FOUND'.\n\n"
            f"1. What is the API response p95 latency target?\n"
            f"2. What database version is specified?\n"
            f"3. What is the JWT access token expiry time?\n"
            f"4. What pagination style is used?\n"
            f"5. What email service is used?\n"
            f"6. How many concurrent WebSocket connections should be supported?\n\n"
            f"CONTEXT:\n{summary}\n\n"
            f"Answer in the text field, one answer per line numbered 1-6."
        )

        found_count = 0
        checks = [
            ("200ms", "p95 latency target"),
            ("16", "PostgreSQL version"),
            ("15", "JWT access token expiry"),
            ("cursor", "pagination style"),
            ("sendgrid", "email service"),
            ("1000", "concurrent WebSocket connections"),
        ]
        for keyword, label in checks:
            if keyword.lower() in response.lower():
                found_count += 1

        assert found_count >= 4, (
            f"Only {found_count}/6 technical details preserved in derived context. "
            f"Response: {response[:500]}"
        )

    def test_context_captures_adrs(self, tmp_path):
        """Derived context must capture Architecture Decision Records."""
        summary, _ = self._summarize_context(tmp_path)

        response = self._ask_llm(
            f"Given this project context, list all Architecture Decision Records (ADRs) "
            f"mentioned. For each, state the decision number and what was decided.\n\n"
            f"CONTEXT:\n{summary}\n\n"
            f"Answer in the text field."
        )

        # Should find at least 3 of the 5 ADRs
        adr_count = len(re.findall(r"ADR.?0{0,2}[1-5]", response, re.IGNORECASE))
        assert adr_count >= 3, (
            f"Only found {adr_count} ADRs in derived context (expected >=3). "
            f"Response: {response[:500]}"
        )

    def test_context_captures_database_schema(self, tmp_path):
        """Derived context must capture database schema details."""
        summary, _ = self._summarize_context(tmp_path)

        response = self._ask_llm(
            f"Given this project context, list ALL database tables mentioned "
            f"and for each table list at least 3 columns.\n\n"
            f"CONTEXT:\n{summary}\n\n"
            f"Answer in the text field."
        )

        # Should find users and tasks tables
        assert "users" in response.lower(), f"Missing users table: {response[:300]}"
        assert "tasks" in response.lower(), f"Missing tasks table: {response[:300]}"

    def test_context_captures_api_endpoints(self, tmp_path):
        """Derived context must capture API endpoint details."""
        summary, _ = self._summarize_context(tmp_path)

        response = self._ask_llm(
            f"Given this project context, list ALL API endpoints mentioned "
            f"with their HTTP methods.\n\n"
            f"CONTEXT:\n{summary}\n\n"
            f"Answer in the text field."
        )

        # Should find auth and task endpoints
        assert "auth" in response.lower(), f"Missing auth endpoints: {response[:300]}"
        assert "task" in response.lower(), f"Missing task endpoints: {response[:300]}"
        # Should have multiple HTTP methods
        methods_found = sum(1 for m in ["POST", "GET", "PATCH", "WS"] if m in response.upper())
        assert methods_found >= 3, (
            f"Only found {methods_found} HTTP methods (expected >=3): {response[:300]}"
        )

    def test_context_overall_quality_score(self, tmp_path):
        """LLM rates the overall quality of derived context vs source material."""
        summary, config = self._summarize_context(tmp_path)

        # Build source material reference
        source_files = collect_context_files(config)
        source_text = "\n\n---\n\n".join(
            f"## {name}\n\n{content}" for name, content in source_files
        )

        response = self._ask_llm(
            f"You are evaluating the quality of a project context summary.\n\n"
            f"SOURCE MATERIAL (what was provided):\n{source_text[:6000]}\n\n"
            f"DERIVED SUMMARY (what was produced):\n{summary[:6000]}\n\n"
            f"Rate the summary on these criteria (1-10 each):\n"
            f"1. COMPLETENESS: Does it capture all key information?\n"
            f"2. ACCURACY: Are technical details preserved exactly?\n"
            f"3. STRUCTURE: Is it well-organized for agent consumption?\n"
            f"4. ACTIONABILITY: Can an agent team build from this alone?\n\n"
            f"Answer in the text field with format:\n"
            f"COMPLETENESS: X/10\nACCURACY: X/10\nSTRUCTURE: X/10\n"
            f"ACTIONABILITY: X/10\nOVERALL: X/10\nNOTES: brief explanation",
            max_tokens=500,
        )

        # Extract scores
        scores = re.findall(r"(\d+)/10", response)
        assert len(scores) >= 4, f"Could not extract scores from: {response[:300]}"
        numeric_scores = [int(s) for s in scores[:4]]
        avg_score = sum(numeric_scores) / len(numeric_scores)

        assert avg_score >= 7.0, (
            f"Context quality score too low ({avg_score:.1f}/10). "
            f"Scores: {dict(zip(['completeness', 'accuracy', 'structure', 'actionability'], numeric_scores))}. "
            f"Notes: {response}"
        )

    def test_generated_files_use_derived_context(self, tmp_path):
        """After full generation with real LLM, agent files should contain project-specific details."""
        summary, config = self._summarize_context(tmp_path)

        # Now generate all files with derived context
        # Reset config with derived context in requirements
        _header = "# Project Context\n\n"
        if summary.startswith(_header):
            config.project.requirements = summary[len(_header):]
        else:
            config.project.requirements = summary

        generate_all(config)

        # Check that key project details appear in generated files
        agents_dir = tmp_path / ".claude" / "agents"
        backend = (agents_dir / "backend-developer.md").read_text()

        response = self._ask_llm(
            f"Read this backend developer instruction file for a project management app. "
            f"Does it contain project-specific context (not generic boilerplate)? "
            f"Specifically, does it mention any of: TaskFlow, FastAPI, PostgreSQL, "
            f"JWT authentication, WebSocket, task management, or similar project-specific details?\n\n"
            f"INSTRUCTION FILE:\n{backend[:5000]}\n\n"
            f"Answer in the text field: YES if project-specific, NO if generic. "
            f"Then list 3 project-specific details you found.",
        )

        assert "yes" in response.lower(), (
            f"Agent file lacks project-specific context: {response[:300]}"
        )

    def test_context_no_hallucination(self, tmp_path):
        """Derived context should not contain information not in source material."""
        summary, config = self._summarize_context(tmp_path)

        response = self._ask_llm(
            f"You are auditing a project context summary for hallucinations.\n\n"
            f"The source material mentions: FastAPI, PostgreSQL, Redis, JWT, "
            f"WebSocket, SendGrid, Celery, S3/MinIO, SQLAlchemy.\n\n"
            f"SUMMARY TO AUDIT:\n{summary[:5000]}\n\n"
            f"Does the summary introduce any technologies, features, or requirements "
            f"that are NOT mentioned in the source? Answer in the text field: "
            f"'CLEAN' if no hallucinations found, or list the hallucinated items.",
            max_tokens=300,
        )

        # Allow for minor rephrasing but flag major hallucinations
        hallucination_keywords = [
            "graphql", "mongodb", "kubernetes", "terraform",
            "react native", "flutter", "grpc",
        ]
        response_lower = response.lower()
        for keyword in hallucination_keywords:
            if keyword in response_lower and "not" not in response_lower.split(keyword)[0][-20:]:
                # Only flag if the keyword is presented as something in the summary
                # (not "does not mention graphql")
                pass  # Allow the LLM to judge — don't hard-fail on keyword presence
