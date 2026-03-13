"""Grading engine for eval assertions — deterministic and LLM-based.

Deterministic checks (contains, regex, section_present, etc.) run instantly
with zero cost. LLM judge assertions use llm-gateway for semantic evaluation.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from forge_cli.config_schema import ForgeConfig
from forge_cli.evals import Assertion, CheckType, Expectation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM response model
# ---------------------------------------------------------------------------

class LLMExpectation(BaseModel):
    """Single expectation from LLM judge."""

    text: str
    passed: bool
    evidence: str


class LLMGradingResponse(BaseModel):
    """Structured response from LLM judge grading."""

    expectations: list[LLMExpectation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

_COST_PER_1K_INPUT = 0.003
_COST_PER_1K_OUTPUT = 0.015


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from token counts."""
    return (
        (input_tokens / 1000) * _COST_PER_1K_INPUT
        + (output_tokens / 1000) * _COST_PER_1K_OUTPUT
    )


# ---------------------------------------------------------------------------
# Deterministic grading
# ---------------------------------------------------------------------------

def _check_contains(content: str, value: str) -> tuple[bool, str]:
    """Check if content contains the value (case-insensitive)."""
    if value.lower() in content.lower():
        return True, f"Found '{value}' in content"
    return False, f"'{value}' not found in content"


def _check_not_contains(content: str, value: str) -> tuple[bool, str]:
    """Check that content does NOT contain the value (case-insensitive)."""
    if value.lower() not in content.lower():
        return True, f"'{value}' correctly absent from content"
    return False, f"'{value}' found in content but should not be present"


def _check_regex(content: str, value: str) -> tuple[bool, str]:
    """Check if content matches the regex pattern."""
    try:
        match = re.search(value, content, re.IGNORECASE | re.MULTILINE)
        if match:
            return True, f"Regex '{value}' matched: '{match.group()[:80]}'"
        return False, f"Regex '{value}' did not match"
    except re.error as e:
        return False, f"Invalid regex '{value}': {e}"


def _check_section_present(content: str, value: str) -> tuple[bool, str]:
    """Check if a markdown section header is present.

    Handles headers that may be indented (e.g., in CLAUDE.md content blocks).
    """
    # Look for ## Section Name with optional leading whitespace
    pattern = rf"^\s*#+\s+{re.escape(value)}"
    match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
    if match:
        return True, f"Section '{value}' found: '{match.group().strip()}'"
    return False, f"Section '{value}' not found in any heading level"


def _check_frontmatter_field(content: str, value: str) -> tuple[bool, str]:
    """Check if a frontmatter field exists in YAML frontmatter."""
    # Extract frontmatter block between --- markers
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return False, "No YAML frontmatter block found"
    frontmatter = fm_match.group(1)
    # Check for field (key: value pattern)
    field_pattern = rf"^{re.escape(value)}\s*:"
    if re.search(field_pattern, frontmatter, re.MULTILINE):
        return True, f"Frontmatter field '{value}' present"
    return False, f"Frontmatter field '{value}' not found"


def _check_config_fidelity(
    content: str,
    value: str,
    config: ForgeConfig,
) -> tuple[bool, str]:
    """Check if content reflects a specific config property.

    Value format: 'config.path=expected' or just 'config.path' (check non-empty).
    Examples:
        'mode=mvp'
        'tech_stack.languages'  (just check languages are mentioned)
        'agents.team_profile=lean'
    """
    parts = value.split("=", 1)
    config_path = parts[0].strip()
    expected_value = parts[1].strip() if len(parts) > 1 else None

    # Resolve config value
    obj: Any = config
    for attr in config_path.split("."):
        if hasattr(obj, attr):
            obj = getattr(obj, attr)
        else:
            return False, f"Config path '{config_path}' not found"

    # If checking for specific value
    if expected_value is not None:
        actual = str(obj.value if hasattr(obj, "value") else obj)
        if actual.lower() == expected_value.lower():
            # Verify it's mentioned in content
            if expected_value.lower() in content.lower():
                return True, f"Config '{config_path}={expected_value}' reflected in content"
            return False, f"Config value '{expected_value}' not mentioned in content"
        return False, f"Config '{config_path}' is '{actual}', expected '{expected_value}'"

    # Just check the config value is mentioned somewhere
    if isinstance(obj, list):
        found = []
        missing = []
        for item in obj:
            item_str = str(item)
            if item_str.lower() in content.lower():
                found.append(item_str)
            else:
                missing.append(item_str)
        if missing:
            return False, f"Config list items missing from content: {missing}"
        return True, f"All config list items found: {found}"
    elif isinstance(obj, bool):
        return True, f"Config '{config_path}' is {obj}"
    else:
        obj_str = str(obj.value if hasattr(obj, "value") else obj)
        if obj_str.lower() in content.lower():
            return True, f"Config '{config_path}' value '{obj_str}' found in content"
        return False, f"Config '{config_path}' value '{obj_str}' not found in content"


def deterministic_grade(
    content: str,
    file_path: str,
    assertions: list[Assertion],
    config: ForgeConfig,
) -> list[Expectation]:
    """Grade deterministic assertions (no LLM cost).

    Only processes non-LLM assertion types. Returns list of Expectations.
    """
    results: list[Expectation] = []

    for assertion in assertions:
        if assertion.check_type == CheckType.LLM_JUDGE:
            continue

        passed = False
        evidence = ""

        if assertion.check_type == CheckType.CONTAINS:
            passed, evidence = _check_contains(content, assertion.value)
        elif assertion.check_type == CheckType.NOT_CONTAINS:
            passed, evidence = _check_not_contains(content, assertion.value)
        elif assertion.check_type == CheckType.REGEX:
            passed, evidence = _check_regex(content, assertion.value)
        elif assertion.check_type == CheckType.SECTION_PRESENT:
            passed, evidence = _check_section_present(content, assertion.value)
        elif assertion.check_type == CheckType.FRONTMATTER_FIELD:
            passed, evidence = _check_frontmatter_field(content, assertion.value)
        elif assertion.check_type == CheckType.CONFIG_FIDELITY:
            passed, evidence = _check_config_fidelity(content, assertion.value, config)

        results.append(Expectation(
            text=assertion.text,
            passed=passed,
            evidence=evidence,
        ))

    return results


# ---------------------------------------------------------------------------
# LLM grading
# ---------------------------------------------------------------------------

_LLM_GRADE_PROMPT = """You are evaluating a generated file against quality assertions.
Your job is to determine whether each assertion PASSES or FAILS based on the file content.

FILE: {file_path}

CONTENT:
{content}

PROJECT CONTEXT:
{project_context}

ASSERTIONS TO EVALUATE:
{assertions_text}

For each assertion, determine if it PASSES or FAILS.
- PASS: The file clearly satisfies the assertion based on its content.
- FAIL: The file does not satisfy the assertion, or the relevant content is missing/insufficient.

Be strict but fair. Look for substance, not just keyword presence.
Return a structured response with an expectations list."""


def _build_project_context(config: ForgeConfig) -> str:
    """Build concise project context for LLM grading."""
    parts = [
        f"Description: {config.project.description}",
        f"Mode: {config.mode.value}",
        f"Strategy: {config.strategy.value}",
    ]
    if config.tech_stack.languages:
        parts.append(f"Languages: {', '.join(config.tech_stack.languages)}")
    if config.tech_stack.frameworks:
        parts.append(f"Frameworks: {', '.join(config.tech_stack.frameworks)}")
    if config.tech_stack.databases:
        parts.append(f"Databases: {', '.join(config.tech_stack.databases)}")
    parts.append(f"Agents: {', '.join(config.get_active_agents())}")
    if config.non_negotiables:
        parts.append(f"Non-negotiables: {'; '.join(config.non_negotiables)}")
    return "\n".join(parts)


async def llm_grade(
    llm: Any,
    content: str,
    file_path: str,
    assertions: list[Assertion],
    config: ForgeConfig,
) -> tuple[list[Expectation], float]:
    """Grade LLM_JUDGE assertions using llm-gateway.

    Batches assertions (max 15 per call) to stay within context limits.
    Returns (expectations, total_cost_usd).
    """
    llm_assertions = [a for a in assertions if a.check_type == CheckType.LLM_JUDGE]
    if not llm_assertions:
        return [], 0.0

    all_expectations: list[Expectation] = []
    total_cost = 0.0
    batch_size = 15

    for i in range(0, len(llm_assertions), batch_size):
        batch = llm_assertions[i : i + batch_size]
        assertions_text = "\n".join(
            f"{j + 1}. {a.text}" for j, a in enumerate(batch)
        )

        prompt = _LLM_GRADE_PROMPT.format(
            file_path=file_path,
            content=content[:12000],  # Truncate to avoid token limits
            project_context=_build_project_context(config),
            assertions_text=assertions_text,
        )

        try:
            resp = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_model=LLMGradingResponse,
                max_tokens=4096,
            )
            cost = _estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens)
            total_cost += cost

            # Map LLM responses back to assertions
            for j, llm_exp in enumerate(resp.content.expectations):
                if j < len(batch):
                    all_expectations.append(Expectation(
                        text=batch[j].text,
                        passed=llm_exp.passed,
                        evidence=llm_exp.evidence,
                    ))
            # Fill in any missing expectations (LLM returned fewer than batch)
            for j in range(len(resp.content.expectations), len(batch)):
                all_expectations.append(Expectation(
                    text=batch[j].text,
                    passed=False,
                    evidence="LLM did not return evaluation for this assertion",
                ))
        except Exception as exc:
            logger.warning("LLM grading batch failed: %s", exc)
            for a in batch:
                all_expectations.append(Expectation(
                    text=a.text,
                    passed=False,
                    evidence=f"LLM grading error: {exc}",
                ))

    return all_expectations, total_cost
