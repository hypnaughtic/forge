# Changelog

All notable changes to the Forge project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [3.1.0] — 2026-03-08

### Added

- **LLM-powered refinement layer** — Optional post-generation step that scores each
  `.md` file against weighted quality criteria (completeness 25%, config fidelity 25%,
  specificity 20%, clarity 20%, consistency 10%) and iteratively refines until meeting
  a configurable threshold (default 90%). Uses `llm-gateway` with `local_claude` or
  `anthropic` provider. All files refined in parallel (~4-7 min for 18 files).
- **`refinement` config section** — New top-level config with `enabled`, `provider`,
  `model`, `max_tokens`, `score_threshold`, `max_iterations`, `max_concurrency`,
  `timeout_seconds`, `cost_limit_usd`. Disabled by default for backward compatibility.
- **`--refine/--no-refine` CLI flag** — Override `refinement.enabled` from command line.
- **`[refinement]` optional dependency** — `pip install forge-init[refinement]` to
  install `llm-gateway` for the refinement feature.
- **Parallel refinement** — `refine_all_async` uses `asyncio.Semaphore` with
  `max_concurrency` (default 0 = all files in parallel). Each file is scored and
  refined concurrently, with best-version tracking across iterations.
- **Refinement unit tests** — `tests/test_refinement.py` with `FakeLLMProvider` for
  deterministic, offline testing of scoring, refinement loop, and full pipeline.
- **Refinement integration tests** — `TestRefinementIntegration` and
  `TestRefinementQualityCases` in `tests/test_integration.py` with dual-mode:
  `FORGE_TEST_DRY_RUN=1` (default, fake provider) and `FORGE_TEST_DRY_RUN=0`
  (real LLM via `local_claude` with sonnet model).
- **Quality case refinement reports** — Each quality case saves a
  `refinement-report.json` with timing, config, and per-file score details.

### Changed

- **Skill generators are now config-aware** — All skill templates inject project
  description, requirements, tech stack, mode, strategy, and agent list. Skills
  now score 82–95 on initial generation (up from 50–78 with generic templates).
- **Skill file whitespace normalization** — `_write_skill` strips template
  indentation from Python source nesting so all skill files start with clean
  `---` YAML frontmatter.
- **Refined scoring prompt** — Weighted criteria, explicit rules for `$ARGUMENTS`
  template variable, no penalty for shared protocol sections or file length.
- **Refined improvement prompt** — Focused on concise targeted improvements using
  project config details, not verbose expansion.
- **Version bumped to 3.1.0** across `pyproject.toml`, `VERSION`, `forge_cli/__init__.py`,
  and Homebrew formula.

## [3.0.0] — 2026-03-07

### BREAKING CHANGES

- **Single-command CLI** — `forge init`, `forge generate`, `forge validate` subcommands
  replaced with a single command: `forge --config PATH [--project-dir DIR] [--validate-only]`.
  The `--config` flag is now required.
- **Interactive wizard removed** — `forge_cli/wizard.py` deleted. All configuration is
  done via `forge-config.yaml` (no more `questionary` prompts).
- **Dependencies removed** — `questionary` and `jinja2` no longer required.

### Added

- **`non_negotiables` config field** — List of absolute requirements injected into all
  generated files with role-appropriate framing:
  - Team Leader: enforcement (reject violating work, compliance checks in iteration reviews)
  - Critic: evaluation (PASS/FAIL scoring per rule, any FAIL = automatic BLOCKER)
  - All other agents: compliance (verify before reporting complete)
  - CLAUDE.md and team-init-plan.md include non-negotiables sections when configured
  - Quick Reference table shows rule count

### Removed

- `forge_cli/wizard.py` — Interactive questionary wizard
- `shared/` directory — v1 runtime artifacts
- `tests/test_helper/` — BATS test helpers and submodules
- `.gitmodules` — BATS git submodule references
- `.shellcheckrc` — Shell linting config
- `.claude-plugin/plugin.json` — v1 Claude plugin manifest
- `skills/` directory (repo-root) — v1 plugin skills

### Changed

- CLI rewritten as single `@click.command()` with `--config`, `--project-dir`, `--validate-only`
- Version bumped to 3.0.0 across `pyproject.toml`, `VERSION`, `forge_cli/__init__.py`
- CI workflow rewritten for Python (removed BATS, shellcheck, submodule checkout)
- Release workflow tarball includes only `forge`, `forge_cli/`, `pyproject.toml`, `VERSION`, etc.
- Pre-commit hooks: removed shellcheck, updated pytest entry to include all test files
- Homebrew formula: removed questionary and jinja2 resources, updated to v3.0.0
- README.md: rewritten for v3 config-driven CLI

## [2.1.0] — 2026-03-06

### Added

- **LLMGatewayConfig in config schema** — New `llm_gateway` section in `ForgeConfig`
  with fields: `enabled`, `local_claude_model`, `enable_local_claude`, `cost_tracking`.
  Controls whether generated agent files include the LLM Gateway Integration mandate.

- **LLM Gateway sections in generated files** — When `llm_gateway.enabled` is true,
  every agent file includes an "LLM Gateway Integration (MANDATORY)" section with
  `LLMClient`/`GatewayConfig` usage patterns, `FakeLLMProvider` test instructions
  (QA agent), `local_claude` dev setup, and cost tracking requirements.
  CLAUDE.md and team-init-plan.md also reference llm-gateway configuration.

### Changed

- **Vendor-agnostic mandate strengthened** — Architect agent template now says
  "MUST use llm-gateway" instead of "gateway pattern (use llm-gateway if applicable)".

- **Project context section** — All agent files now show LLM Gateway status
  (enabled/disabled, local_claude on/off) in the project context header.
