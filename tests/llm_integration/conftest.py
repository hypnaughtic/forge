"""Shared fixtures for llm-gateway integration tests."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from llm_gateway import GatewayConfig, LLMClient

FORGE_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def forge_dir() -> Path:
    """Return the forge project root directory."""
    return FORGE_ROOT


@pytest.fixture(scope="session")
def llm_config() -> GatewayConfig:
    """Build a GatewayConfig for local_claude with cost guardrails."""
    return GatewayConfig(
        provider="local_claude",
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        temperature=0.0,
        cost_limit_usd=2.0,
        cost_warn_usd=1.0,
        log_level="WARNING",
        log_format="console",
    )


@pytest.fixture(scope="session")
def llm_client(llm_config: GatewayConfig) -> LLMClient:
    """Create a session-scoped LLMClient with local_claude provider."""
    return LLMClient(config=llm_config)


def run_nl_router(forge_dir: Path, text: str) -> str:
    """Run the bash NL router and return its output."""
    script = forge_dir / "scripts" / "nl-router.sh"
    result = subprocess.run(
        ["bash", str(script), text],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "FORGE_DIR": str(forge_dir)},
    )
    return result.stdout.strip()
