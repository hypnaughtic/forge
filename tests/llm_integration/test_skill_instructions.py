"""Integration tests: Skill instruction clarity using actual Claude responses.

Validates that Claude can correctly interpret SKILL.md files and produce
appropriate actions. Tests that the skill instructions are clear enough
for Claude to follow without ambiguity.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from llm_gateway import LLMClient

FORGE_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class SkillAction(BaseModel):
    """What Claude would do after reading a skill's instructions."""

    bash_commands: list[str] = Field(
        description="List of bash commands to execute, in order"
    )
    is_instant: bool = Field(
        description="Whether this is an instant command (no AI reasoning needed) or async"
    )
    requires_arguments: bool = Field(
        description="Whether the skill requires user-provided arguments"
    )
    summary: str = Field(
        description="One-sentence summary of what this skill does"
    )


class RouteDecision(BaseModel):
    """How Claude would route a /forge command after reading the skill."""

    route_type: str = Field(
        description="Either 'instant' or 'async'"
    )
    scripts_to_run: list[str] = Field(
        description="Script paths that would be executed"
    )
    writes_override: bool = Field(
        description="Whether this writes to override.md for Team Leader"
    )
    explanation: str = Field(
        description="Brief explanation of the routing decision"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def read_skill(skill_name: str) -> str:
    """Read a SKILL.md file and return its content."""
    skill_path = FORGE_ROOT / "skills" / skill_name / "SKILL.md"
    return skill_path.read_text()


# ---------------------------------------------------------------------------
# Tests: Skill comprehension
# ---------------------------------------------------------------------------


SKILL_COMPREHENSION_SYSTEM = """\
You are Claude reading a Forge skill definition (SKILL.md).
Analyze the skill instructions and determine:
1. What bash commands it tells you to run
2. Whether it's instant (just runs a script) or async (requires AI reasoning)
3. Whether it needs user arguments
4. A brief summary

For bash commands, replace variables like $FORGE_DIR with literal "$FORGE_DIR"
and $ARGUMENTS with "$ARGUMENTS". List only the actual commands, not pseudo-code.
"""


@pytest.mark.asyncio
class TestSkillComprehension:
    """Test that Claude correctly understands skill instructions."""

    @pytest.mark.parametrize(
        "skill_name,expected_instant,expected_requires_args",
        [
            ("status", True, False),
            ("cost", True, False),
            ("snapshot", True, False),
            ("stop", True, False),
            ("mode", True, True),
            ("strategy", True, True),
            ("start", False, False),
            ("ask", False, True),
            ("guide", False, True),
            ("team", True, False),
        ],
    )
    async def test_skill_understanding(
        self,
        llm_client: LLMClient,
        skill_name: str,
        expected_instant: bool,
        expected_requires_args: bool,
    ) -> None:
        skill_content = read_skill(skill_name)

        response = await llm_client.complete(
            messages=[
                {"role": "system", "content": SKILL_COMPREHENSION_SYSTEM},
                {
                    "role": "user",
                    "content": f"Analyze this skill:\n\n{skill_content}",
                },
            ],
            response_model=SkillAction,
        )
        result = response.content

        print(f"\n  Skill: {skill_name}")
        print(f"  Commands: {result.bash_commands}")
        print(f"  Instant: {result.is_instant} (expected: {expected_instant})")
        print(f"  Requires args: {result.requires_arguments} (expected: {expected_requires_args})")
        print(f"  Summary: {result.summary}")

        # Verify Claude correctly identifies instant vs async
        assert result.is_instant == expected_instant, (
            f"Skill '{skill_name}': Claude says instant={result.is_instant}, "
            f"expected {expected_instant}. Summary: {result.summary}"
        )

        # Verify argument requirement
        assert result.requires_arguments == expected_requires_args, (
            f"Skill '{skill_name}': Claude says requires_args={result.requires_arguments}, "
            f"expected {expected_requires_args}. Summary: {result.summary}"
        )

        # Verify at least one bash command is identified
        assert len(result.bash_commands) > 0, (
            f"Skill '{skill_name}': Claude found no bash commands. "
            f"Summary: {result.summary}"
        )


# ---------------------------------------------------------------------------
# Tests: /forge default skill routing
# ---------------------------------------------------------------------------


ROUTING_SYSTEM = """\
You are Claude executing the /forge default skill (the NL router).
Given the skill instructions below and a user command, determine:
1. Whether to route as 'instant' or 'async'
2. Which scripts to run
3. Whether to write to override.md

Here are the skill instructions:

{skill_content}
"""


@pytest.mark.asyncio
class TestForgeRouting:
    """Test that Claude correctly routes /forge commands."""

    INSTANT_COMMANDS = [
        ("what is the status?", "status.sh"),
        ("show me the cost", "cost-tracker.sh"),
        ("team overview", "team-view.sh"),
        ("save a snapshot", "stop.sh"),
    ]

    ASYNC_COMMANDS = [
        "refactor the authentication module",
        "make the UI more accessible",
        "add dark mode support to the frontend",
        "improve the error handling across all services",
    ]

    @pytest.mark.parametrize("user_input,expected_script", INSTANT_COMMANDS)
    async def test_instant_routing(
        self,
        llm_client: LLMClient,
        user_input: str,
        expected_script: str,
    ) -> None:
        forge_skill = read_skill("forge")
        system = ROUTING_SYSTEM.format(skill_content=forge_skill)

        response = await llm_client.complete(
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Route this command: {user_input}",
                },
            ],
            response_model=RouteDecision,
        )
        result = response.content

        print(f"\n  Input: {user_input!r}")
        print(f"  Route: {result.route_type}")
        print(f"  Scripts: {result.scripts_to_run}")
        print(f"  Writes override: {result.writes_override}")
        print(f"  Explanation: {result.explanation}")

        assert result.route_type == "instant", (
            f"Command {user_input!r} should route as instant, "
            f"got {result.route_type}. Explanation: {result.explanation}"
        )
        assert not result.writes_override, (
            f"Instant command {user_input!r} should not write override.md"
        )

    @pytest.mark.parametrize("user_input", ASYNC_COMMANDS)
    async def test_async_routing(
        self,
        llm_client: LLMClient,
        user_input: str,
    ) -> None:
        forge_skill = read_skill("forge")
        system = ROUTING_SYSTEM.format(skill_content=forge_skill)

        response = await llm_client.complete(
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Route this command: {user_input}",
                },
            ],
            response_model=RouteDecision,
        )
        result = response.content

        print(f"\n  Input: {user_input!r}")
        print(f"  Route: {result.route_type}")
        print(f"  Writes override: {result.writes_override}")
        print(f"  Explanation: {result.explanation}")

        assert result.route_type == "async", (
            f"Command {user_input!r} should route as async, "
            f"got {result.route_type}. Explanation: {result.explanation}"
        )
        assert result.writes_override, (
            f"Async command {user_input!r} should write to override.md"
        )


# ---------------------------------------------------------------------------
# Tests: Intent-over-invocation via /forge:ask
# ---------------------------------------------------------------------------


ASK_SKILL_SYSTEM = """\
You are Claude executing the /forge:ask skill.
Given the skill instructions below and a user message, determine
whether to execute an instant command or queue as async.

Remember the critical rule: "intent always wins over invocation path"

Here are the skill instructions:

{skill_content}
"""


@pytest.mark.asyncio
class TestIntentOverInvocation:
    """Test that Claude follows the 'intent over invocation' rule.

    Even when invoked via /forge:ask, if the message content maps to
    an instant command (like cost or status), Claude should execute
    it instantly rather than queuing it.
    """

    INSTANT_VIA_ASK = [
        ("what is the cost?", False),   # Should NOT write override
        ("show me the status", False),  # Should NOT write override
        ("team overview please", False), # Should NOT write override
    ]

    ASYNC_VIA_ASK = [
        ("redesign the database schema", True),   # SHOULD write override
        ("add caching to the API layer", True),    # SHOULD write override
    ]

    @pytest.mark.parametrize("user_input,should_write_override", INSTANT_VIA_ASK + ASYNC_VIA_ASK)
    async def test_ask_routing(
        self,
        llm_client: LLMClient,
        user_input: str,
        should_write_override: bool,
    ) -> None:
        ask_skill = read_skill("ask")
        system = ASK_SKILL_SYSTEM.format(skill_content=ask_skill)

        response = await llm_client.complete(
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"The user invoked /forge:ask with this message: {user_input}\n"
                        f"Should this be executed instantly or queued as async?"
                    ),
                },
            ],
            response_model=RouteDecision,
        )
        result = response.content

        print(f"\n  /forge:ask input: {user_input!r}")
        print(f"  Route: {result.route_type}")
        print(f"  Writes override: {result.writes_override}")
        print(f"  Explanation: {result.explanation}")

        if should_write_override:
            assert result.route_type == "async", (
                f"/forge:ask {user_input!r} should be async. "
                f"Explanation: {result.explanation}"
            )
        else:
            assert result.route_type == "instant", (
                f"/forge:ask {user_input!r} should be instant (intent over invocation). "
                f"Explanation: {result.explanation}"
            )
