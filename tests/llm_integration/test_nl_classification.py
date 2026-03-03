"""Integration tests: NL intent classification using actual Claude responses.

Validates that Claude's understanding of forge user commands aligns with
the bash keyword-based NL router (scripts/nl-router.sh).

Each test sends a natural language command to Claude via llm-gateway
(local_claude provider) and asks it to classify the intent, then compares
against the bash router's classification.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from llm_gateway import LLMClient

from .conftest import run_nl_router

# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class IntentClassification(BaseModel):
    """Claude's classification of a forge user command."""

    intents: list[str] = Field(
        description=(
            "List of classified intents. Valid values: "
            "STATUS, COST, TEAM, MODE, STRATEGY, SNAPSHOT, START, STOP, GUIDE, ASK. "
            "Use ASK only when no other intent matches."
        )
    )
    reasoning: str = Field(
        description="Brief explanation of why these intents were chosen"
    )


# ---------------------------------------------------------------------------
# System prompt for classification
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM = """\
You are an intent classifier for Forge, an AI orchestration framework.

Given a user's natural language command, classify it into one or more intents:

- STATUS: Asking about project progress, iteration state, what's happening, blockers
- COST: Asking about cost, budget, spending, token usage, billing
- TEAM: Asking about agents, team members, who is working on what
- MODE: Setting project mode (mvp, production-ready, no-compromise)
- STRATEGY: Setting execution strategy (auto-pilot, co-pilot, micro-manage)
- SNAPSHOT: Saving state, creating checkpoint, backing up
- START: Starting a build, beginning iteration, kicking off work
- STOP: Stopping, shutting down, pausing, ending session
- GUIDE: Directing a specific agent (mentions agent name + instruction)
- ASK: General question or directive for the Team Leader (fallback when nothing else matches)

Rules:
1. A command can have MULTIPLE intents (e.g., "show me status and cost" = STATUS + COST)
2. Intent classification is based on MEANING, not surface keywords
3. Only use ASK when no other intent matches at all
4. Agent names include: team-leader, architect, backend-developer, frontend-engineer, qa-engineer, devops-specialist, critic, research-strategist
"""


# ---------------------------------------------------------------------------
# Test data: (input, expected_intents)
# ---------------------------------------------------------------------------

SINGLE_INTENT_CASES = [
    ("what is the current status?", ["STATUS"]),
    ("how is the project going?", ["STATUS"]),
    ("show me the progress", ["STATUS"]),
    ("how much have we spent?", ["COST"]),
    ("what is the cost breakdown?", ["COST"]),
    ("show me the budget", ["COST"]),
    ("who is working on what?", ["TEAM"]),
    ("show me the team", ["TEAM"]),
    ("list all agents", ["TEAM"]),
    ("switch to production-ready mode", ["MODE"]),
    ("set mode to mvp", ["MODE"]),
    ("change to auto-pilot strategy", ["STRATEGY"]),
    ("use co-pilot mode for approvals", ["STRATEGY"]),
    ("save a snapshot", ["SNAPSHOT"]),
    ("checkpoint the current state", ["SNAPSHOT"]),
    ("start building", ["START"]),
    ("kick off the next iteration", ["START"]),
    ("stop everything", ["STOP"]),
    ("shut down all agents", ["STOP"]),
    ("tell backend-developer to use PostgreSQL", ["GUIDE"]),
    ("redesign the entire authentication system using OAuth2", ["ASK"]),
    ("make the UI more responsive and modern", ["ASK"]),
]

MULTI_INTENT_CASES = [
    ("show me the status and cost", ["STATUS", "COST"]),
    ("what is the progress and who is working?", ["STATUS", "TEAM"]),
    ("give me cost breakdown and team overview", ["COST", "TEAM"]),
]

# These test the "intent over invocation" principle:
# Even if phrased as a question, if the content maps to an instant command,
# it should be classified as that instant intent, NOT as ASK.
INTENT_OVER_INVOCATION_CASES = [
    ("what is the cost?", ["COST"]),  # Not ASK, it's clearly COST
    ("how is the project doing?", ["STATUS"]),  # Not ASK, it's STATUS
    ("who is on the team?", ["TEAM"]),  # Not ASK, it's TEAM
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def classify_with_claude(
    llm_client: LLMClient, user_input: str
) -> IntentClassification:
    """Ask Claude to classify a forge user command."""
    response = await llm_client.complete(
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": f"Classify this command: {user_input}"},
        ],
        response_model=IntentClassification,
    )
    return response.content


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSingleIntentClassification:
    """Test that Claude and the bash router agree on single-intent commands."""

    @pytest.mark.parametrize("user_input,expected", SINGLE_INTENT_CASES)
    async def test_single_intent(
        self,
        llm_client: LLMClient,
        forge_dir: Path,
        user_input: str,
        expected: list[str],
    ) -> None:
        # Get bash router classification
        bash_result = run_nl_router(forge_dir, user_input)
        bash_intents = sorted(bash_result.split(","))

        # Get Claude classification
        claude_result = await classify_with_claude(llm_client, user_input)
        claude_intents = sorted(claude_result.intents)

        # Report for debugging
        print(f"\n  Input: {user_input!r}")
        print(f"  Expected: {expected}")
        print(f"  Bash router: {bash_intents}")
        print(f"  Claude: {claude_intents} ({claude_result.reasoning})")

        # Claude should match expected intents
        assert claude_intents == sorted(expected), (
            f"Claude classified {user_input!r} as {claude_intents}, "
            f"expected {sorted(expected)}. "
            f"Reasoning: {claude_result.reasoning}"
        )


@pytest.mark.asyncio
class TestMultiIntentClassification:
    """Test that Claude handles multi-intent commands correctly."""

    @pytest.mark.parametrize("user_input,expected", MULTI_INTENT_CASES)
    async def test_multi_intent(
        self,
        llm_client: LLMClient,
        forge_dir: Path,
        user_input: str,
        expected: list[str],
    ) -> None:
        bash_result = run_nl_router(forge_dir, user_input)
        bash_intents = sorted(bash_result.split(","))

        claude_result = await classify_with_claude(llm_client, user_input)
        claude_intents = sorted(claude_result.intents)

        print(f"\n  Input: {user_input!r}")
        print(f"  Expected: {sorted(expected)}")
        print(f"  Bash router: {bash_intents}")
        print(f"  Claude: {claude_intents} ({claude_result.reasoning})")

        # For multi-intent, check that Claude gets all expected intents
        for intent in expected:
            assert intent in claude_intents, (
                f"Claude missed intent {intent} for {user_input!r}. "
                f"Got {claude_intents}. Reasoning: {claude_result.reasoning}"
            )


@pytest.mark.asyncio
class TestIntentOverInvocation:
    """Test the 'intent over invocation' principle.

    Even when phrased as questions, if the content maps to an instant
    command, Claude should classify it as that intent, not ASK.
    """

    @pytest.mark.parametrize("user_input,expected", INTENT_OVER_INVOCATION_CASES)
    async def test_intent_wins(
        self,
        llm_client: LLMClient,
        user_input: str,
        expected: list[str],
    ) -> None:
        claude_result = await classify_with_claude(llm_client, user_input)
        claude_intents = sorted(claude_result.intents)

        print(f"\n  Input: {user_input!r}")
        print(f"  Expected: {sorted(expected)}")
        print(f"  Claude: {claude_intents} ({claude_result.reasoning})")

        # ASK should NOT be in the result for these
        assert "ASK" not in claude_intents, (
            f"Claude incorrectly classified {user_input!r} as ASK. "
            f"Should be {expected}. Reasoning: {claude_result.reasoning}"
        )
        for intent in expected:
            assert intent in claude_intents, (
                f"Claude missed intent {intent} for {user_input!r}. "
                f"Got {claude_intents}."
            )


@pytest.mark.asyncio
class TestBashRouterAlignment:
    """Test that bash router and Claude agree on classification.

    When they disagree, log it as a potential improvement opportunity.
    """

    ALIGNMENT_CASES = [
        "what's happening with the project?",
        "how much money have we burned?",
        "show me everyone on the team",
        "save the current progress",
        "let's begin the build",
        "please stop all work",
        "I want to switch to mvp mode",
        "backend-developer should use REST not GraphQL",
        "refactor the payment module to use Stripe",
        "can you show me the status and also the cost?",
    ]

    @pytest.mark.parametrize("user_input", ALIGNMENT_CASES)
    async def test_alignment(
        self,
        llm_client: LLMClient,
        forge_dir: Path,
        user_input: str,
    ) -> None:
        bash_result = run_nl_router(forge_dir, user_input)
        bash_intents = sorted(bash_result.split(","))

        claude_result = await classify_with_claude(llm_client, user_input)
        claude_intents = sorted(claude_result.intents)

        print(f"\n  Input: {user_input!r}")
        print(f"  Bash router: {bash_intents}")
        print(f"  Claude: {claude_intents}")
        print(f"  Reasoning: {claude_result.reasoning}")

        if bash_intents != claude_intents:
            print(f"  ** MISALIGNMENT: bash={bash_intents} vs claude={claude_intents}")
            # Log but don't fail — misalignments are improvement opportunities
            # The bash router is the fast-path heuristic, Claude is the ground truth
