"""Eval runner — orchestrates deterministic and LLM grading of generated files.

Entry point: run_eval() generates an EvalReport by grading all generated files
against applicable eval cases from the registry.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Any

from forge_cli.config_schema import ForgeConfig
from forge_cli.evals import (
    Assertion,
    CheckType,
    EvalCase,
    EvalReport,
    Expectation,
    GradingResult,
)
from forge_cli.evals.grading import deterministic_grade, llm_grade

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Applicability checking
# ---------------------------------------------------------------------------

def _check_applicable(case: EvalCase, config: ForgeConfig) -> bool:
    """Check if an eval case applies to the given config.

    Evaluates predicates in case.applicable_when against config methods.
    """
    if not case.applicable_when:
        return True

    for predicate, expected in case.applicable_when.items():
        if predicate == "is_cli_project":
            if config.is_cli_project() != expected:
                return False
        elif predicate == "has_web_backend":
            if config.has_web_backend() != expected:
                return False
        elif predicate == "has_frontend_involvement":
            if config.has_frontend_involvement() != expected:
                return False
        elif predicate == "atlassian_enabled":
            if config.atlassian.enabled != expected:
                return False
        elif predicate == "has_ssh_auth":
            if config.has_ssh_auth() != expected:
                return False
        elif predicate == "sub_agent_spawning":
            if config.agents.allow_sub_agent_spawning != expected:
                return False
        elif predicate == "llm_gateway_enabled":
            if config.llm_gateway.enabled != expected:
                return False
        elif predicate == "agent_naming_enabled":
            if config.agent_naming.enabled != expected:
                return False
        elif predicate == "has_non_negotiables":
            if bool(config.non_negotiables) != expected:
                return False
        elif predicate == "has_databases":
            if bool(config.tech_stack.databases) != expected:
                return False
        elif predicate == "agent_in_roster":
            agents = config.get_active_agents()
            if isinstance(expected, str):
                if (expected in agents) is False:
                    return False
            elif isinstance(expected, list):
                if not any(a in agents for a in expected):
                    return False
        elif predicate == "agent_not_in_roster":
            agents = config.get_active_agents()
            if isinstance(expected, str):
                if expected in agents:
                    return False
        elif predicate == "mode":
            if config.mode.value != expected:
                return False
        elif predicate == "strategy":
            if config.strategy.value != expected:
                return False
        elif predicate == "is_static_site":
            is_static = (
                not config.has_web_backend()
                and not config.is_cli_project()
                and not config.has_frontend_involvement()
            )
            if is_static != expected:
                return False
        else:
            logger.warning("Unknown eval predicate: %s", predicate)

    return True


def _file_exists_in_project(file_path: str, project_dir: Path) -> bool:
    """Check if a file exists in the project directory."""
    return (project_dir / file_path).exists()


# ---------------------------------------------------------------------------
# Train/test split
# ---------------------------------------------------------------------------

def split_eval_cases(
    cases: list[EvalCase],
    ratio: float = 0.6,
) -> tuple[list[EvalCase], list[EvalCase]]:
    """Deterministic 60/40 split by hashing case.id.

    Train set failures go into refine prompts.
    Test set is used for version selection (prevents overfitting).
    """
    train: list[EvalCase] = []
    test: list[EvalCase] = []

    for case in cases:
        h = hashlib.md5(case.id.encode()).hexdigest()  # noqa: S324
        # Use first 8 hex chars as a fraction of 0xFFFFFFFF
        fraction = int(h[:8], 16) / 0xFFFFFFFF
        if fraction < ratio:
            train.append(case)
        else:
            test.append(case)

    return train, test


# ---------------------------------------------------------------------------
# File grading
# ---------------------------------------------------------------------------

async def grade_file(
    content: str,
    file_path: str,
    config: ForgeConfig,
    assertions: list[Assertion],
    llm: Any | None = None,
) -> GradingResult:
    """Grade a single file against its assertions.

    Runs deterministic checks first, then LLM judge assertions if llm is provided.
    """
    result = GradingResult(file_path=file_path)

    # Deterministic grading (instant, free)
    det_expectations = deterministic_grade(content, file_path, assertions, config)
    result.expectations.extend(det_expectations)

    # LLM grading (if LLM client provided and there are LLM assertions)
    llm_assertions = [a for a in assertions if a.check_type == CheckType.LLM_JUDGE]
    if llm is not None and llm_assertions:
        llm_expectations, cost = await llm_grade(
            llm, content, file_path, llm_assertions, config,
        )
        result.expectations.extend(llm_expectations)
        result.llm_cost_usd = cost

    result.compute_pass_rate()
    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_eval_async(
    project_dir: Path,
    config: ForgeConfig,
    llm: Any | None = None,
    eval_cases: list[EvalCase] | None = None,
) -> EvalReport:
    """Run eval suite against all generated files.

    Args:
        project_dir: Directory containing generated files.
        config: Forge configuration used for generation.
        llm: Optional LLM client for judge assertions. None = deterministic only.
        eval_cases: Optional list of cases. None = auto-select from registry.

    Returns:
        EvalReport with per-file grading results.
    """
    start_time = time.monotonic()

    # Load eval cases from registry if not provided
    if eval_cases is None:
        from forge_cli.evals.eval_cases import get_all_eval_cases
        eval_cases = get_all_eval_cases()

    # Filter to applicable cases
    applicable = [c for c in eval_cases if _check_applicable(c, config)]
    logger.info(
        "Eval: %d/%d cases applicable for config",
        len(applicable),
        len(eval_cases),
    )

    # Group cases by file
    file_cases: dict[str, list[EvalCase]] = {}
    for case in applicable:
        if _file_exists_in_project(case.file_path, project_dir):
            file_cases.setdefault(case.file_path, []).append(case)

    report = EvalReport(config_name=config.project.description[:60])
    total_cost = 0.0

    for file_path, cases in sorted(file_cases.items()):
        full_path = project_dir / file_path
        content = full_path.read_text()

        # Merge all assertions from all cases for this file
        all_assertions: list[Assertion] = []
        seen_texts: set[str] = set()
        for case in cases:
            for assertion in case.assertions:
                if assertion.text not in seen_texts:
                    all_assertions.append(assertion)
                    seen_texts.add(assertion.text)

        result = await grade_file(content, file_path, config, all_assertions, llm)
        report.files.append(result)
        total_cost += result.llm_cost_usd

    report.total_cost_usd = total_cost
    report.duration_seconds = time.monotonic() - start_time
    report.compute_overall_pass_rate()

    return report


def run_eval(
    project_dir: Path | str,
    config: ForgeConfig,
    use_llm: bool = False,
    eval_cases: list[EvalCase] | None = None,
    llm_provider: Any | None = None,
) -> EvalReport:
    """Synchronous entry point for running evals.

    Args:
        project_dir: Directory containing generated files.
        config: Forge configuration.
        use_llm: If True, creates an LLM client for judge assertions.
        eval_cases: Optional specific cases to run.
        llm_provider: Optional LLM provider instance (for testing).
    """
    project_dir = Path(project_dir)
    llm = None
    if use_llm:
        llm = _create_llm_client(config, llm_provider)

    try:
        return asyncio.run(
            run_eval_async(project_dir, config, llm, eval_cases)
        )
    finally:
        if llm is not None:
            asyncio.run(llm.close())


def _create_llm_client(
    config: ForgeConfig,
    provider: Any | None = None,
) -> Any:
    """Create LLM client for eval grading."""
    import os

    if provider is None and os.environ.get("FORGE_TEST_DRY_RUN", "0") == "1":
        try:
            from llm_gateway.testing import FakeLLMProvider
            provider = FakeLLMProvider()
        except ImportError:
            pass

    if provider is not None:
        from llm_gateway import LLMClient
        return LLMClient(provider_instance=provider)

    try:
        from llm_gateway import GatewayConfig, LLMClient
    except ImportError:
        raise ImportError(
            "llm-gateway is required for LLM-based evals. "
            "Install it with: pip install 'forge-init[refinement]'"
        )

    gw_config = GatewayConfig(
        provider=config.refinement.provider,
        model=config.refinement.model,
        max_tokens=4096,
        timeout_seconds=config.refinement.timeout_seconds,
    )
    return LLMClient(config=gw_config)


# ---------------------------------------------------------------------------
# Refinement integration helper
# ---------------------------------------------------------------------------

async def grade_file_for_refinement(
    content: str,
    file_path: str,
    file_type: str,
    config: ForgeConfig,
    llm: Any | None = None,
) -> GradingResult:
    """Grade a file during refinement using applicable eval cases.

    Selects eval cases matching the file_path and config, then grades.
    Used by refinement.py to get baseline/refined pass rates.
    """
    from forge_cli.evals.eval_cases import get_all_eval_cases

    all_cases = get_all_eval_cases()
    applicable = [
        c for c in all_cases
        if c.file_path == file_path and _check_applicable(c, config)
    ]

    if not applicable:
        return GradingResult(file_path=file_path, pass_rate=1.0)

    all_assertions: list[Assertion] = []
    seen: set[str] = set()
    for case in applicable:
        for a in case.assertions:
            if a.text not in seen:
                all_assertions.append(a)
                seen.add(a.text)

    return await grade_file(content, file_path, config, all_assertions, llm)
