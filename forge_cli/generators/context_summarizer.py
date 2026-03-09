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
from typing import Any

from forge_cli.config_schema import ForgeConfig

logger = logging.getLogger(__name__)

CONTEXT_FILENAME = "project-context.md"
MAX_FILE_SIZE = 100_000  # 100KB per file limit


def collect_context_files(config: ForgeConfig) -> list[tuple[str, str]]:
    """Collect content from all configured context files and directories.

    Args:
        config: Forge configuration with context_files paths.

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
            _read_file(path, files)
        elif path.is_dir():
            # Read all .md, .txt, .yaml, .yml files recursively
            for ext in ("*.md", "*.txt", "*.yaml", "*.yml", "*.rst"):
                for f in sorted(path.rglob(ext)):
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


def build_raw_context(config: ForgeConfig) -> str:
    """Build raw context string from config fields and context files.

    Returns:
        Combined text of project description, requirements, and all
        context file contents.
    """
    parts: list[str] = []

    if config.project.description:
        parts.append(f"## Project Description\n\n{config.project.description}")

    if config.project.requirements:
        parts.append(f"## Project Requirements\n\n{config.project.requirements}")

    context_files = collect_context_files(config)
    for filename, content in context_files:
        parts.append(f"## File: {filename}\n\n{content}")

    return "\n\n---\n\n".join(parts)


def _build_summarize_prompt(raw_context: str, config: ForgeConfig) -> str:
    """Build the LLM prompt for project context summarization."""
    return f"""You are summarizing project context for an AI agent team that will build this project.

RAW PROJECT CONTEXT:
{raw_context}

PROJECT CONFIG:
- Mode: {config.mode.value}
- Strategy: {config.strategy.value}
- Tech Stack: {', '.join(config.tech_stack.languages + config.tech_stack.frameworks + config.tech_stack.databases)}
- Team: {', '.join(config.get_active_agents())}

INSTRUCTIONS:
Produce a comprehensive project context summary that captures:
1. **Project Overview**: What is being built, its purpose, and target users
2. **Architecture**: System components, data flow, tech decisions already made
3. **Key Requirements**: Functional and non-functional requirements
4. **Current State**: What has been completed vs. what remains (if applicable)
5. **Constraints & Decisions**: Technology choices, design patterns, ADRs
6. **Integration Points**: External services, APIs, databases, protocols
7. **Quality Standards**: Testing strategy, coverage requirements, performance targets

CRITICAL RULES:
- Do NOT invent details not present in the source material
- Preserve specific technical details (exact library names, version numbers, API endpoints)
- Include all domain-specific terminology and concepts
- Note any explicit ADRs (Architecture Decision Records) or design decisions
- Keep numerical targets and thresholds exact (e.g., "90% coverage", "800ms debounce")
- If the project has phases/milestones, summarize what was delivered in each
- This summary will be used by AI agents as their primary project reference

Return a structured response with:
- summary: the complete project context summary in Markdown format"""


async def summarize_context_async(
    config: ForgeConfig,
    project_dir: str | Path,
    llm_provider: Any | None = None,
) -> str:
    """Summarize project context using LLM and save to .forge/project-context.md.

    If no context_files are configured, returns a basic context from
    description + requirements without calling the LLM.

    Args:
        config: Forge configuration.
        project_dir: Project workspace directory.
        llm_provider: Optional LLM provider instance (for testing).

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

    raw_context = build_raw_context(config)

    # If no context files and minimal description, just use raw context
    if not config.project.context_files and not config.project.requirements:
        summary = f"# Project Context\n\n{raw_context}"
        context_path.write_text(summary)
        return summary

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
            model=config.refinement.model,
            max_tokens=config.refinement.max_tokens,
            timeout_seconds=config.refinement.timeout_seconds,
        )
        llm = LLMClient(config=gw_config)

    try:
        prompt = _build_summarize_prompt(raw_context, config)
        resp = await llm.complete(
            messages=[{"role": "user", "content": prompt}],
            response_model=SummaryResponse,
            max_tokens=config.refinement.max_tokens,
        )
        summary = f"# Project Context\n\n{resp.content.summary}"
    except Exception as e:
        logger.warning("LLM summarization failed, using raw context: %s", e)
        summary = f"# Project Context\n\n{raw_context}"
    finally:
        await llm.close()

    context_path.write_text(summary)
    return summary


def summarize_context(
    config: ForgeConfig,
    project_dir: str | Path,
    llm_provider: Any | None = None,
) -> str:
    """Synchronous wrapper around summarize_context_async."""
    import asyncio
    return asyncio.run(summarize_context_async(config, project_dir, llm_provider))


def load_project_context(project_dir: str | Path) -> str | None:
    """Load existing project context from .forge/project-context.md.

    Returns:
        Context string if file exists, None otherwise.
    """
    path = Path(project_dir) / ".forge" / CONTEXT_FILENAME
    if path.is_file():
        return path.read_text()
    return None
