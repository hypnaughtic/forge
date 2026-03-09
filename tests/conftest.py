"""Test configuration — ensures dry-run mode never makes real LLM calls.

When FORGE_TEST_DRY_RUN=1 (default), patches build_provider() to raise
an error if any code path tries to create a real LLM provider. This is
the network boundary — the function that creates Anthropic, local_claude,
etc. providers. FakeLLMProvider is injected directly via provider_instance
and never hits build_provider.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _guard_real_llm_in_dry_run(monkeypatch):
    """Block real LLM provider creation in dry-run mode.

    If FORGE_TEST_DRY_RUN=1, any attempt to call build_provider()
    (which creates real Anthropic/local_claude providers) will raise
    an error. FakeLLMProvider bypasses this entirely since it's injected
    directly via LLMClient(provider_instance=fake).
    """
    if os.environ.get("FORGE_TEST_DRY_RUN", "1") != "1":
        return  # Not dry-run — allow real LLM calls

    try:
        import llm_gateway
    except ImportError:
        return  # llm-gateway not installed — nothing to guard

    def _blocked_build_provider(config):
        raise RuntimeError(
            "FORGE_TEST_DRY_RUN=1 but build_provider() was called, "
            f"attempting to create a real '{config.provider}' LLM provider. "
            "Pass an explicit llm_provider (e.g., FakeLLMProvider) to prevent this."
        )

    monkeypatch.setattr(llm_gateway, "build_provider", _blocked_build_provider)
