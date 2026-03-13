"""Summarize project context from user-provided files.

Reads plan files, spec documents, and architecture docs provided via
config.project.context_files, then produces a summarized project context
saved to .forge/project-context.md.

This context is used throughout generation, refinement, and scoring to
ensure forge files are tailored to the actual project requirements.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from forge_cli.config_schema import ForgeConfig

logger = logging.getLogger(__name__)

# Callback type: (detail_message: str) -> None
ProgressCallback = Callable[[str], None]

CONTEXT_FILENAME = "project-context.md"
MAX_FILE_SIZE = 100_000  # 100KB per file limit
# Use Opus for context summarization — higher quality for the foundational
# project context that all agents reference throughout development.
CONTEXT_MODEL = "claude-opus-4-6"
# Context summaries can be long (10+ sections) — use higher token limit than
# refinement's default 8192 to avoid mid-sentence truncation.
CONTEXT_MAX_TOKENS = 16384


def collect_context_files(
    config: ForgeConfig,
    on_progress: ProgressCallback | None = None,
) -> list[tuple[str, str]]:
    """Collect content from all configured context files and directories.

    Args:
        config: Forge configuration with context_files paths.
        on_progress: Optional callback for reporting which files are read.

    Returns:
        List of (relative_path, content) tuples.
    """
    files: list[tuple[str, str]] = []

    for path_str in config.project.context_files:
        path = Path(path_str).expanduser()

        # Resolve relative paths against project directory
        if not path.is_absolute():
            path = Path(config.project.directory).resolve() / path

        if path.is_file():
            if on_progress:
                on_progress(f"Reading {path.name}")
            _read_file(path, files)
        elif path.is_dir():
            # Read all .md, .txt, .yaml, .yml files recursively
            for ext in ("*.md", "*.txt", "*.yaml", "*.yml", "*.rst"):
                for f in sorted(path.rglob(ext)):
                    if on_progress:
                        on_progress(f"Reading {f.name}")
                    _read_file(f, files)
        else:
            logger.warning("Context file/dir not found: %s", path_str)

    return files


def _read_file(path: Path, files: list[tuple[str, str]]) -> None:
    """Read a single file into the files list, respecting size limits."""
    try:
        content = path.read_text(errors="replace")
        if len(content) > MAX_FILE_SIZE:
            content = content[:MAX_FILE_SIZE] + "\n\n[... truncated at 100KB ...]"
        files.append((str(path.name), content))
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Could not read %s: %s", path, e)


def build_raw_context(
    config: ForgeConfig,
    on_progress: ProgressCallback | None = None,
) -> str:
    """Build raw context string from config fields and context files.

    Returns:
        Combined text of project description, requirements, plan file,
        and all context file contents.
    """
    parts: list[str] = []

    if config.project.description:
        parts.append(f"## Project Description\n\n{config.project.description}")

    if config.project.requirements:
        parts.append(f"## Project Requirements\n\n{config.project.requirements}")

    # Include plan file content if configured
    if config.project.plan_file:
        plan_path = Path(config.project.plan_file).expanduser()
        if not plan_path.is_absolute():
            plan_path = Path(config.project.directory).resolve() / plan_path
        if plan_path.is_file():
            if on_progress:
                on_progress(f"Reading {plan_path.name}")
            try:
                plan_content = plan_path.read_text(errors="replace")
                if len(plan_content) > MAX_FILE_SIZE:
                    plan_content = plan_content[:MAX_FILE_SIZE] + "\n\n[... truncated at 100KB ...]"
                parts.append(f"## Implementation Plan: {plan_path.name}\n\n{plan_content}")
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Could not read plan file %s: %s", plan_path, e)
        else:
            logger.warning("Plan file not found: %s", config.project.plan_file)

    context_files = collect_context_files(config, on_progress=on_progress)
    for filename, content in context_files:
        parts.append(f"## File: {filename}\n\n{content}")

    return "\n\n---\n\n".join(parts)


def _build_summarize_prompt(raw_context: str, config: ForgeConfig) -> str:
    """Build the LLM prompt for project context summarization."""
    plan_note = ""
    if config.project.plan_file:
        plan_note = (
            "\n\nIMPORTANT: A plan file has been provided. This is an authoritative "
            "implementation blueprint. Ensure every phase, milestone, deliverable, "
            "and architectural decision from the plan is captured in the summary."
        )
    return f"""You are summarizing project context for an AI agent team that will build this project.
Your summary is the SINGLE SOURCE OF TRUTH that agents will reference — nothing from
the source material should be lost.

RAW PROJECT CONTEXT:
{raw_context}

PROJECT CONFIG (for your awareness only — do NOT include these values in the summary):
- Mode: {config.mode.value}
- Strategy: {config.strategy.value}
- Tech Stack: {', '.join(config.tech_stack.languages + config.tech_stack.frameworks + config.tech_stack.databases)}
- Team: {', '.join(config.get_active_agents())}
- Non-negotiables: {', '.join(config.non_negotiables) if config.non_negotiables else 'none'}
{plan_note}

INSTRUCTIONS:
Produce a comprehensive project context summary that captures EVERY detail from the
source material. Structure it as follows:

1. **Project Overview**: What is being built, its purpose, target users, and value proposition
2. **Architecture & System Design**: All system components, services, data flow diagrams,
   communication protocols (HTTP, WebSocket, gRPC, etc.), and tech decisions already made
3. **Data Model & Storage**: Database schemas, tables, relationships, indexes, migrations
4. **Key Features & Requirements**: Every functional requirement — enumerate each feature,
   endpoint, UI component, workflow, and interaction
5. **Non-Functional Requirements**: Performance targets, scalability, security, reliability,
   observability, monitoring
6. **Current State & Phases**: What has been completed vs. what remains. If there are
   phases/milestones, detail deliverables and dependencies for each
7. **Technical Decisions & Constraints**: Technology choices, design patterns, ADRs,
   library versions, API contracts
8. **Integration Points**: External services, APIs, databases, message queues, protocols,
   authentication/authorization flows
9. **Quality Standards**: Testing strategy, coverage requirements, performance benchmarks,
   CI/CD pipeline expectations
10. **Domain-Specific Concepts**: All domain terminology, business rules, algorithms,
    and domain models mentioned in the source material

CRITICAL RULES:
- Do NOT include PROJECT CONFIG metadata (mode, strategy, team roster, non-negotiables)
  in the summary — those are for your awareness only, not part of the source material
- Do NOT invent or embellish details not present in the RAW PROJECT CONTEXT above
- Do NOT summarize away specifics — preserve EXACT technical details:
  - Library names and versions (e.g., "React Flow v12", "FastAPI 0.115")
  - API endpoints and routes (e.g., "POST /api/v1/suggestions")
  - Database table/column names (e.g., "suggestion_cache table with wl_hash column")
  - Configuration values (e.g., "800ms debounce", "3-tier cache", "90% coverage")
  - Algorithm names (e.g., "WL hash", "VF2 isomorphism", "exponential backoff")
- Include ALL domain-specific terminology and concepts without simplification
- Note every explicit ADR (Architecture Decision Record) or design decision
- Keep ALL numerical targets and thresholds exact
- If multiple source files discuss the same topic, merge details without duplication
- The summary must be self-contained — an agent reading only this summary should
  understand the full project scope without needing the original files

Return a structured response with:
- summary: the complete project context summary in Markdown format"""


async def summarize_context_async(
    config: ForgeConfig,
    project_dir: str | Path,
    llm_provider: Any | None = None,
    on_progress: ProgressCallback | None = None,
) -> str:
    """Summarize project context using LLM and save to .forge/project-context.md.

    If no context_files are configured, returns a basic context from
    description + requirements without calling the LLM.

    Args:
        config: Forge configuration.
        project_dir: Project workspace directory.
        llm_provider: Optional LLM provider instance (for testing).
        on_progress: Optional callback for progress updates.

    Returns:
        The summarized project context string.
    """
    from pydantic import BaseModel, Field as PydanticField

    class SummaryResponse(BaseModel):
        summary: str = PydanticField(description="Project context summary in Markdown")

    project_dir = Path(project_dir)
    forge_dir = project_dir / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)
    context_path = forge_dir / CONTEXT_FILENAME

    raw_context = build_raw_context(config, on_progress=on_progress)

    # If no context files and minimal description, just use raw context
    if not config.project.context_files and not config.project.requirements:
        summary = f"# Project Context\n\n{raw_context}"
        context_path.write_text(summary)
        return summary

    # In dry-run mode, auto-use FakeLLMProvider if no provider given
    if llm_provider is None:
        import os
        if os.environ.get("FORGE_TEST_DRY_RUN", "0") == "1":
            try:
                from llm_gateway.testing import FakeLLMProvider
                llm_provider = FakeLLMProvider()
            except ImportError:
                pass

    # Use LLM to summarize
    if llm_provider is not None:
        from llm_gateway import LLMClient
        llm = LLMClient(provider_instance=llm_provider)
    else:
        try:
            from llm_gateway import LLMClient, GatewayConfig
        except ImportError:
            # No LLM available — fall back to raw context
            summary = f"# Project Context\n\n{raw_context}"
            context_path.write_text(summary)
            return summary

        gw_config = GatewayConfig(
            provider=config.refinement.provider,
            model=CONTEXT_MODEL,
            max_tokens=CONTEXT_MAX_TOKENS,
            timeout_seconds=config.refinement.timeout_seconds,
        )
        llm = LLMClient(config=gw_config)

    try:
        if on_progress:
            ctx_size = f"{len(raw_context) / 1024:.1f} KB"
            on_progress(f"Summarizing with LLM ({ctx_size} input)")
        prompt = _build_summarize_prompt(raw_context, config)
        resp = await llm.complete(
            messages=[{"role": "user", "content": prompt}],
            response_model=SummaryResponse,
            max_tokens=CONTEXT_MAX_TOKENS,
        )
        summary = f"# Project Context\n\n{resp.content.summary}"
        if on_progress:
            summary_size = f"{len(summary) / 1024:.1f} KB"
            on_progress(f"Context derived ({summary_size})")
    except Exception as e:
        logger.warning("LLM summarization failed, using raw context: %s", e)
        summary = f"# Project Context\n\n{raw_context}"
        if on_progress:
            on_progress("Using raw context (LLM unavailable)")
    finally:
        await llm.close()

    context_path.write_text(summary)
    return summary


def summarize_context(
    config: ForgeConfig,
    project_dir: str | Path,
    llm_provider: Any | None = None,
    on_progress: ProgressCallback | None = None,
) -> str:
    """Synchronous wrapper around summarize_context_async."""
    import asyncio
    return asyncio.run(summarize_context_async(
        config, project_dir, llm_provider, on_progress=on_progress,
    ))


def load_project_context(project_dir: str | Path) -> str | None:
    """Load existing project context from .forge/project-context.md.

    Returns:
        Context string if file exists, None otherwise.
    """
    path = Path(project_dir) / ".forge" / CONTEXT_FILENAME
    if path.is_file():
        return path.read_text()
    return None
