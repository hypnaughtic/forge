"""Skill description optimizer — improves frontmatter descriptions for trigger accuracy.

Generates trigger/non-trigger queries, evaluates current description,
and iteratively improves it using LLM feedback.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from forge_cli.config_schema import ForgeConfig

logger = logging.getLogger(__name__)


class TriggerQuery(BaseModel):
    """A query that should or shouldn't trigger a skill."""

    query: str
    should_trigger: bool


class TriggerEvalResult(BaseModel):
    """Result of evaluating trigger queries against a description."""

    query: str
    should_trigger: bool
    would_trigger: bool
    correct: bool


class OptimizationReport(BaseModel):
    """Report from description optimization."""

    skill_path: str
    original_description: str
    optimized_description: str
    original_accuracy: float
    optimized_accuracy: float
    iterations: int
    train_results: list[TriggerEvalResult] = Field(default_factory=list)
    test_results: list[TriggerEvalResult] = Field(default_factory=list)


class GeneratedQueries(BaseModel):
    """LLM-generated trigger queries."""

    queries: list[TriggerQuery]


class TriggerEvaluation(BaseModel):
    """LLM evaluation of whether queries would trigger a skill."""

    evaluations: list[bool]  # True = would trigger, False = would not


class ImprovedDescription(BaseModel):
    """LLM-proposed improved description."""

    description: str
    reasoning: str


def _extract_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Extract frontmatter fields and body from skill file.

    Returns (frontmatter_dict, body_text).
    """
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not fm_match:
        return {}, content

    fm_text = fm_match.group(1)
    body = fm_match.group(2)

    fields: dict[str, str] = {}
    for line in fm_text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"').strip("'")

    return fields, body


def _update_description(content: str, new_description: str) -> str:
    """Update the description field in frontmatter."""
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return content

    fm_text = fm_match.group(1)
    # Replace description line
    new_fm = re.sub(
        r'^description:\s*.*$',
        f'description: "{new_description}"',
        fm_text,
        flags=re.MULTILINE,
    )
    return content[:fm_match.start(1)] + new_fm + content[fm_match.end(1):]


async def optimize_description(
    skill_path: Path,
    config: ForgeConfig,
    llm: Any,
    max_iterations: int = 5,
) -> OptimizationReport:
    """Optimize a skill's frontmatter description for trigger accuracy.

    Flow:
    1. Generate 20 trigger queries (10 should-trigger, 10 shouldn't)
    2. Split 60/40 train/test
    3. Evaluate current description accuracy
    4. LLM proposes improved description based on train-set failures
    5. Re-evaluate on both splits
    6. Select best by test accuracy
    """
    content = skill_path.read_text()
    fields, body = _extract_frontmatter(content)
    original_desc = fields.get("description", "")
    skill_name = fields.get("name", skill_path.stem)

    # Step 1: Generate trigger queries
    queries = await _generate_queries(llm, skill_name, original_desc, body, config)

    # Step 2: Split train/test (60/40 deterministic)
    import hashlib
    train_queries = []
    test_queries = []
    for q in queries:
        h = hashlib.md5(q.query.encode()).hexdigest()  # noqa: S324
        if int(h[:8], 16) / 0xFFFFFFFF < 0.6:
            train_queries.append(q)
        else:
            test_queries.append(q)

    # Ensure both sets are non-empty
    if not train_queries:
        train_queries = queries[:len(queries) // 2]
        test_queries = queries[len(queries) // 2:]
    if not test_queries:
        test_queries = train_queries[-4:]
        train_queries = train_queries[:-4]

    # Step 3: Evaluate current description
    current_desc = original_desc
    best_desc = original_desc
    best_test_accuracy = await _evaluate_accuracy(
        llm, skill_name, current_desc, test_queries,
    )
    original_accuracy = best_test_accuracy

    train_results: list[TriggerEvalResult] = []
    test_results: list[TriggerEvalResult] = []

    # Step 4-5: Iterate
    for i in range(max_iterations):
        # Evaluate on train set
        train_evals = await _evaluate_queries(llm, skill_name, current_desc, train_queries)
        failures = [e for e in train_evals if not e.correct]

        if not failures:
            logger.info("Iteration %d: 100%% train accuracy, stopping", i + 1)
            break

        # Propose improved description
        improved = await _propose_improvement(
            llm, skill_name, current_desc, body, failures, config,
        )
        current_desc = improved.description

        # Evaluate on test set
        test_accuracy = await _evaluate_accuracy(
            llm, skill_name, current_desc, test_queries,
        )

        if test_accuracy >= best_test_accuracy:
            best_test_accuracy = test_accuracy
            best_desc = current_desc

    # Final evaluation for report
    train_results = await _evaluate_queries(llm, skill_name, best_desc, train_queries)
    test_results = await _evaluate_queries(llm, skill_name, best_desc, test_queries)

    return OptimizationReport(
        skill_path=str(skill_path),
        original_description=original_desc,
        optimized_description=best_desc,
        original_accuracy=original_accuracy,
        optimized_accuracy=best_test_accuracy,
        iterations=min(i + 1, max_iterations) if 'i' in dir() else 0,
        train_results=train_results,
        test_results=test_results,
    )


async def _generate_queries(
    llm: Any,
    skill_name: str,
    description: str,
    body: str,
    config: ForgeConfig,
) -> list[TriggerQuery]:
    """Generate trigger/non-trigger test queries."""
    prompt = f"""Generate exactly 20 test queries for a Claude Code skill.
The skill is named "{skill_name}" with description: "{description}"

Skill body (first 2000 chars):
{body[:2000]}

Project context: {config.project.description}

Generate:
- 10 queries that SHOULD trigger this skill (things a user would say when they want this skill)
- 10 queries that SHOULD NOT trigger this skill (similar-sounding but different intents)

Return a structured response with a 'queries' list, each with 'query' and 'should_trigger' fields."""

    resp = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        response_model=GeneratedQueries,
        max_tokens=2048,
    )
    return resp.content.queries


async def _evaluate_queries(
    llm: Any,
    skill_name: str,
    description: str,
    queries: list[TriggerQuery],
) -> list[TriggerEvalResult]:
    """Evaluate whether each query would trigger the skill."""
    queries_text = "\n".join(
        f"{i + 1}. {q.query}" for i, q in enumerate(queries)
    )

    prompt = f"""Given a Claude Code skill with:
- Name: "{skill_name}"
- Description: "{description}"

For each query below, determine if a user saying this would cause you to invoke this skill.
Return a list of booleans (True = would trigger, False = would not trigger).

Queries:
{queries_text}"""

    resp = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        response_model=TriggerEvaluation,
        max_tokens=1024,
    )

    results = []
    for i, q in enumerate(queries):
        would_trigger = resp.content.evaluations[i] if i < len(resp.content.evaluations) else False
        results.append(TriggerEvalResult(
            query=q.query,
            should_trigger=q.should_trigger,
            would_trigger=would_trigger,
            correct=(would_trigger == q.should_trigger),
        ))
    return results


async def _evaluate_accuracy(
    llm: Any,
    skill_name: str,
    description: str,
    queries: list[TriggerQuery],
) -> float:
    """Evaluate trigger accuracy as a float 0-1."""
    results = await _evaluate_queries(llm, skill_name, description, queries)
    if not results:
        return 0.0
    return sum(1 for r in results if r.correct) / len(results)


async def _propose_improvement(
    llm: Any,
    skill_name: str,
    current_desc: str,
    body: str,
    failures: list[TriggerEvalResult],
    config: ForgeConfig,
) -> ImprovedDescription:
    """Ask LLM to propose an improved description based on failures."""
    failure_text = "\n".join(
        f"- Query: '{f.query}' — should_trigger={f.should_trigger}, "
        f"would_trigger={f.would_trigger}"
        for f in failures[:10]
    )

    prompt = f"""Improve the description for a Claude Code skill to better distinguish
when it should vs. shouldn't be triggered.

Skill name: "{skill_name}"
Current description: "{current_desc}"

Skill body (first 1500 chars):
{body[:1500]}

Project context: {config.project.description}

These queries are being incorrectly classified:
{failure_text}

Write an improved description that would correctly handle these cases.
The description should be:
- Concise (1-2 sentences)
- Specific about what triggers this skill
- Clear about what does NOT trigger it
- "Pushy" enough to activate on true positives but not false positives

Return a structured response with 'description' and 'reasoning' fields."""

    resp = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        response_model=ImprovedDescription,
        max_tokens=1024,
    )
    return resp.content
