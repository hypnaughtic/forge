# Plan: `forge init` — Interactive Configuration Builder

## Context

Currently Forge requires a pre-written `forge-config.yaml`. Users must read the
README or example file, then manually author YAML. This is a barrier for new users
who don't know what options exist or what reasonable defaults look like.

`forge init` walks users through each option interactively, builds the config,
shows a summary for confirmation, and optionally runs generation immediately.

---

## UX Flow

```text
$ forge init

  Forge — Interactive Configuration Builder

  Step 1/8: Project Details
  ─────────────────────────
  Project description: E-commerce platform with payments
  Detailed requirements (press Enter to skip):
  > Full-stack e-commerce with auth, product catalog, cart, Stripe checkout
  Project type [new/existing] (new): new

  Step 2/8: Quality Mode
  ──────────────────────
  > mvp              — 70% quality, happy-path tests, lean team (8 agents)
    production-ready — 90% quality, >90% coverage, full team (12 agents)
    no-compromise    — 100% quality, exhaustive tests, full team (12 agents)

  Step 3/8: Execution Strategy
  ────────────────────────────
  > auto-pilot    — Full autonomy, agents make all decisions
    co-pilot      — Full tool access, agents ask you on architecture/scope only
    micro-manage  — Every significant decision needs your approval

  Step 4/8: Tech Stack
  ────────────────────
  Languages (comma-separated, or Enter to skip): python, typescript
  Frameworks (comma-separated, or Enter to skip): fastapi, react
  Databases (comma-separated, or Enter to skip): postgresql, redis
  Infrastructure (comma-separated, or Enter to skip): docker

  Step 5/8: Team Configuration
  ────────────────────────────
  Team profile [auto/lean/full/custom] (auto): auto
  Allow sub-agent spawning? [Y/n]: Y
  Agent naming style [creative/functional/codename/off] (creative): creative
  Max development cost in USD (50): 50

  Step 6/8: Atlassian Integration
  ───────────────────────────────
  Enable Jira/Confluence integration? [y/N]: N

  Step 7/8: LLM Gateway
  ─────────────────────
  Enable llm-gateway mandate in generated files? [Y/n]: Y

  Step 8/8: Non-Negotiables (optional)
  ─────────────────────────────────────
  Enter absolute requirements (one per line, empty line to finish):
  > All APIs must require authentication
  > 100% test coverage on core business logic
  >

  ═══════════════════════════════════════════
  Configuration Summary
  ═══════════════════════════════════════════
  Project:     E-commerce platform with payments
  Mode:        production-ready
  Strategy:    co-pilot
  Team:        auto (resolves to full) — 12 agents
  Tech Stack:  python, typescript | fastapi, react | postgresql, redis
  Atlassian:   disabled
  LLM Gateway: enabled
  Non-negotiables: 2 rules
  ═══════════════════════════════════════════

  Save config to [forge-config.yaml]: forge-config.yaml
  Run forge now with this config? [Y/n]: Y
  Project directory [.]: ./my-project

  Generating files in /path/to/my-project
    ✓ Agent instruction files
    ✓ CLAUDE.md
    ...
```

---

## Architecture

### CLI Changes — `forge_cli/main.py`

Convert from single `@click.command` to `@click.group` with two subcommands:

```python
@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="forge")
@click.pass_context
def cli(ctx):
    """Forge — Project initializer for Claude Code agent teams."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@cli.command()
@click.option("--config", ...)
@click.option("--project-dir", ...)
@click.option("--validate-only", ...)
@click.option("--refine/--no-refine", ...)
def generate(config_path, project_dir, validate_only, refine):
    """Generate agent files from an existing config."""
    # ... existing cli() body ...

@cli.command()
@click.option("--output", default="forge-config.yaml", help="Output config path")
def init(output):
    """Interactively build a forge-config.yaml."""
    from forge_cli.init_wizard import run_wizard
    run_wizard(output)
```

**Backward compatibility:** `forge --config ...` must keep working. Two approaches:

1. **Option A — Default subcommand:** If `forge` is invoked with `--config`, treat it
   as `forge generate --config ...`. Implement via `invoke_without_command=True` +
   `ctx.invoked_subcommand` detection. Parse `sys.argv` to detect `--config` and
   redirect.

2. **Option B — Alias:** Keep `forge --config` as the primary command, add `forge init`
   as a subcommand only. Use `click.Group` with a custom `parse_args` that routes
   non-subcommand invocations to `generate`.

**Recommended: Option B** — less disruptive, preserves existing behavior exactly.

### New File — `forge_cli/init_wizard.py`

Single-file module containing the interactive wizard. Uses `rich` for formatting
(already a dependency) and raw `click.prompt` / `click.confirm` for input (no new
dependency needed — `click` has all the prompting primitives).

**Key functions:**

```python
def run_wizard(output_path: str) -> None:
    """Main wizard entry point. Walks through all steps, builds config, saves."""

def _prompt_project() -> ProjectConfig:
    """Step 1: Project details."""

def _prompt_mode() -> ProjectMode:
    """Step 2: Quality mode selection."""

def _prompt_strategy() -> ExecutionStrategy:
    """Step 3: Execution strategy selection."""

def _prompt_tech_stack() -> TechStack:
    """Step 4: Tech stack input."""

def _prompt_agents(mode: ProjectMode) -> tuple[AgentsConfig, AgentNamingConfig, CostConfig]:
    """Step 5: Team configuration."""

def _prompt_atlassian() -> AtlassianConfig:
    """Step 6: Atlassian integration."""

def _prompt_llm_gateway() -> LLMGatewayConfig:
    """Step 7: LLM gateway."""

def _prompt_non_negotiables() -> list[str]:
    """Step 8: Non-negotiables (multi-line input)."""

def _show_summary(config: ForgeConfig) -> None:
    """Print formatted summary table using rich."""

def _confirm_and_run(config: ForgeConfig, output_path: str) -> None:
    """Save config, optionally run generation."""
```

**Input patterns:**

| Input Type | Implementation |
|-----------|---------------|
| Free text | `click.prompt("Description")` |
| Enum selection | `rich` numbered list + `click.prompt("Choice", type=int)` |
| Comma-separated list | `click.prompt("Languages")` → `.split(",")` → `.strip()` |
| Yes/No | `click.confirm("Enable?", default=True)` |
| Multi-line (non-negotiables) | Loop: `click.prompt("Rule (empty to finish)")` until empty |
| Path | `click.prompt("Save to", default="forge-config.yaml")` |

**Enum selection with rich:**

For mode and strategy, use numbered choices with descriptions rendered via `rich`:

```python
def _prompt_mode() -> ProjectMode:
    console.print("\n  [bold]Step 2/8: Quality Mode[/bold]")
    console.print("  ──────────────────────")
    options = [
        ("mvp", "70% quality, happy-path tests, lean team (8 agents)"),
        ("production-ready", "90% quality, >90% coverage, full team (12 agents)"),
        ("no-compromise", "100% quality, exhaustive tests, full team (12 agents)"),
    ]
    for i, (name, desc) in enumerate(options, 1):
        console.print(f"    {i}. [cyan]{name}[/cyan] — {desc}")
    choice = click.prompt("  Choice", type=click.IntRange(1, 3), default=1)
    return [ProjectMode.MVP, ProjectMode.PRODUCTION_READY, ProjectMode.NO_COMPROMISE][choice - 1]
```

### Dependencies

**No new dependencies.** Everything uses `click` (prompts, confirms) and `rich`
(console formatting) — both already in `pyproject.toml`.

---

## Files to Create/Modify

### 1. NEW: `forge_cli/init_wizard.py` (~200 lines)

The interactive wizard module. All 8 steps + summary + confirm/run.

### 2. MODIFY: `forge_cli/main.py`

- Convert `@click.command` → `@click.group` with backward-compatible routing
- Add `init` subcommand that calls `run_wizard()`
- Move existing `cli()` body into `generate` subcommand
- Preserve `forge --config` backward compatibility

### 3. MODIFY: `pyproject.toml`

Entry point stays the same (`forge = "forge_cli.main:cli"`). No change needed
if the group's `invoke_without_command` handles it.

### 4. MODIFY: `tests/test_generators.py` (or new `tests/test_init_wizard.py`)

Unit tests for wizard logic:

- Each `_prompt_*` function builds correct config objects from inputs
- Summary output includes all configured options
- Config saved matches what was built
- Running generation after init uses the built config

### 5. MODIFY: `tests/test_integration.py`

Integration tests:

- `forge init` with simulated stdin produces valid config
- Config saved by wizard round-trips through `load_config`
- `forge init` → confirm → generation produces same output as `forge --config`

### 6. MODIFY: `README.md`

Add `forge init` section to Quick Start and document the interactive flow.

### 7. MODIFY: `CHANGELOG.md`

Add entry for `forge init` feature.

### 8. MODIFY: `forge_cli/main.py` HELP_TEXT

Add `forge init` to usage examples and workflow section.

---

## Implementation Order

```text
Step 1: Create forge_cli/init_wizard.py with all prompt functions
Step 2: Refactor main.py — click.group + generate + init subcommands
Step 3: Ensure backward compat — `forge --config` still works
Step 4: Unit tests for wizard logic (mock click.prompt)
Step 5: Integration tests for CLI flow (subprocess with stdin)
Step 6: Update README, CHANGELOG, HELP_TEXT
Step 7: Run full test suite + pre-commit hooks
```

---

## Backward Compatibility Strategy

The critical constraint: `forge --config forge-config.yaml` must keep working
without requiring `forge generate --config ...`.

**Implementation approach:**

```python
class ForgeGroup(click.Group):
    """Custom group that routes bare `forge --config` to the generate subcommand."""

    def parse_args(self, ctx, args):
        # If first arg is --config or --validate-only (not a subcommand name),
        # inject "generate" as the subcommand
        if args and args[0].startswith("--"):
            args = ["generate"] + args
        return super().parse_args(ctx, args)
```

This means:

- `forge --config foo.yaml` → `forge generate --config foo.yaml` (backward compat)
- `forge init` → interactive wizard
- `forge generate --config foo.yaml` → explicit subcommand (also works)
- `forge --help` → shows both subcommands
- `forge --version` → version info

---

## Edge Cases

1. **Ctrl+C during wizard** — catch `KeyboardInterrupt`, print friendly exit message
2. **Empty description** — reject, re-prompt (description is the only required field)
3. **Invalid tech stack items** — accept anything, no validation (users know their stack)
4. **Existing output file** — ask to overwrite: "forge-config.yaml exists. Overwrite? [y/N]"
5. **Custom team profile** — prompt for agent list from available agents
6. **Atlassian enabled** — prompt for Jira/Confluence details only when enabled
7. **Non-TTY stdin** — detect with `sys.stdin.isatty()`, error with message:
   "forge init requires an interactive terminal. Use forge --config instead."

---

## Key Design Decisions

1. **No new dependency** — `click.prompt` + `rich` is sufficient. No questionary.
2. **Steps are sequential, not a tree** — every user goes through all 8 steps. Optional
   sections (Atlassian, non-negotiables) have quick skip paths (Enter/N).
3. **Summary before save** — user sees exactly what will be saved before confirming.
4. **Optional immediate run** — after saving, user can run generation without a
   separate command. Reduces friction for the common case.
5. **Config saved first, then run** — even if user says "run now", the config file
   is written first. If generation fails, the config is preserved.
6. **Refinement not in wizard** — refinement is an advanced feature. Wizard creates
   config with `refinement.enabled: false`. Users can edit the file or use `--refine`.
