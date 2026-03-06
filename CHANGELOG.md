# Changelog

All notable changes to the Forge project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

- **Comprehensive integration tests** — 191 tests covering all configuration
  combinations, file quality scoring, CLI end-to-end flows, agent behavioral
  verification, cross-file consistency, visual verification, llm-gateway integration,
  and edge cases. LLM-verified tests use llm-gateway `local_claude` mode.

- **TestLLMGatewayIntegration test class** — 11 offline tests using `FakeLLMProvider`
  that verify llm-gateway sections appear in agent files, CLAUDE.md, and
  team-init-plan.md; vendor-agnostic mandate in architect file; QA testing
  instructions; local_claude config; cost tracking; and config schema defaults.

- **TestLLMVerification test class** — 7 tests using llm-gateway `local_claude` or
  `anthropic` provider to validate generated file quality with actual LLM responses.

### Changed

- **Vendor-agnostic mandate strengthened** — Architect agent template now says
  "MUST use llm-gateway" instead of "gateway pattern (use llm-gateway if applicable)".

- **Project context section** — All agent files now show LLM Gateway status
  (enabled/disabled, local_claude on/off) in the project context header.

## [1.0.0] — 2026-03-03

### Added

- **Claude Code plugin distribution** — `.claude-plugin/plugin.json` manifest and 12
  skill files in `skills/` directory. Use `/forge`, `/forge:status`, `/forge:cost`,
  `/forge:team`, `/forge:ask`, `/forge:guide`, `/forge:mode`, `/forge:strategy`,
  `/forge:snapshot`, `/forge:start`, `/forge:stop`, `/forge:init`.

- **Cockpit dashboard** — tmux-based live display with auto-refreshing metrics panel,
  color-coded agent status grid, activity feed, and interactive Claude session.
  Launch with `./forge` (requires tmux). Fallback to plain session with `--no-cockpit`.

- **Natural language routing** — `/forge what is the cost and status?` classifies
  intent by keywords and runs instant commands directly. Multi-intent support.
  Smart classification: intent always wins over invocation path.

- **Separate mode and strategy** — `forge mode` and `forge strategy` are now
  independent commands. Previously combined in `/forge-mode`.

- **Per-agent guidance** — `forge guide <agent> "message"` sends prioritized
  directives through the Team Leader.

- **Team view** — `forge team` shows all agents overview. `forge team <name>`
  shows deep dive with memory, decisions, artifacts, and cost.

- **ask command** — `forge ask "message"` replaces `forge tell` with smart NL
  routing. `tell` preserved as deprecated alias.

- **Homebrew distribution** — Release workflow creates GitHub releases on `v*` tags.
  Homebrew formula (external repo) wraps `FORGE_DIR` resolution.

- **`--version` flag** — `forge --version` shows version from `VERSION` file.

- **`FORGE_DIR` env support** — `forge` script respects `FORGE_DIR` environment
  variable for Homebrew and plugin contexts.

- **Comprehensive documentation** — `docs/PLUGIN.md`, `docs/HOMEBREW.md`,
  `docs/COCKPIT.md` cover all new features.

## [Unreleased]

### Fixed

- **Project directory isolation** — Previously, running `./forge start` from
  the forge repo itself would create agent-generated project files (src/,
  tests/, etc.) inside the forge repository, polluting it. Now forge asks for
  a separate workspace directory and creates it if it doesn't exist. The
  directory is saved to `project.directory` in config so it only asks once.
  Safety check warns if project dir equals forge dir.

- **Snapshot project_dir was `$(pwd)` not configured dir** — `stop.sh` saved
  the current working directory in snapshots instead of the configured project
  directory. Fixed to read `project.directory` from config. Also fixed git
  state collection to check the project dir, not the forge dir.

- **`stop.sh` PROJECT_DIR used before set** — Git state collection referenced
  `PROJECT_DIR` before the config read block that sets it. Reordered so config
  is read first. Also fixed newline in git branch name breaking snapshot JSON
  (happens when project dir has no commits yet).

- **`init-project.sh` `local` outside function** — Wizard mode used `local`
  keyword at the top level of the script (lines 58 and 143), which fails with
  "local: can only be used in a function". Removed `local` qualifiers.

- **CLI: `./forge setup` path resolution** — `cmd_setup()` referenced
  `scripts/setup.sh` but the file lives at the repo root (`setup.sh`). Fixed to
  use `${FORGE_DIR}/setup.sh`.

- **macOS: `mktemp` template suffix bug** — All scripts used
  `mktemp /tmp/forge-*-XXXXXX.md` but macOS `mktemp` does not replace X's when
  there is a suffix after them. Files were created with literal `XXXXXX` in the
  name, causing collisions when multiple agents spawn concurrently. Fixed to use
  `mktemp "${TMPDIR:-/tmp}/forge-*-XXXXXXXX"` (no suffix after X's).

- **macOS: `date -d` incompatibility** — `status.sh` and `watchdog.sh` used
  GNU `date -d` for ISO-to-epoch conversion, which does not exist on macOS.
  Added a portable `iso_to_epoch()` helper that tries GNU date, then macOS
  `date -j -f`, then Python 3 as a final fallback.

- **macOS: UTC timezone in ISO date parsing** — macOS `date -j -f` parses
  times in the local timezone by default. Timestamps ending in `Z` (UTC) were
  parsed incorrectly, causing agents to be reported as stale when they were not.
  Fixed by prefixing macOS date calls with `TZ=UTC`.

- **tmux window name detection** — `status.sh` and `watchdog.sh` used
  `awk '{print $2}' | tr -d '*-'` to extract tmux window names, which stripped
  all hyphens from names like `team-leader` (→ `teamleader`). This caused
  every agent with a hyphenated name to be reported as `DEAD`. Fixed by using
  `tmux list-windows -F '#{window_name}'` which returns clean names.

- **macOS: `sed -i` incompatibility** — `kill-agent.sh` used `sed -i` (GNU
  syntax) for in-place edits. macOS `sed -i` requires an empty string argument
  (`sed -i ''`). Added platform detection to use the correct syntax.

- **Nested Claude Code session error** — When forge is invoked from within a
  Claude Code session (common during development), spawned agents failed with
  "Cannot be launched inside another Claude Code session". Fixed by unsetting
  `CLAUDECODE` and `CLAUDE_CODE_ENTRY_TOOL` environment variables in spawned
  tmux windows.

### Added

- **`project.directory` config field** — New field in `team-config.yaml` under
  `project:` that specifies where the project should be built. When empty,
  `./forge start` prompts for a directory (or uses `~/forge-projects/<name>`
  in auto-pilot mode). The choice is persisted to config for future sessions.

- **`./forge start --project-dir <path>`** — CLI flag to override the project
  workspace directory. Takes priority over config. Useful for one-off runs or
  CI pipelines.

- **`./forge init` workspace prompt** — The interactive wizard now asks for
  the project workspace directory as the first question, saving it to config.

- **Strategy-based permission modes** — `spawn-agent.sh` now maps the
  configured execution strategy to Claude Code permission flags:
  - `auto-pilot` → `--dangerously-skip-permissions` (fully autonomous)
  - `co-pilot` → `--permission-mode acceptEdits` (auto-approve edits)
  - `micro-manage` → default (interactive approval for everything)

- **Auto-pilot headless Team Leader** — In auto-pilot mode, the Team Leader
  now runs in `--print` mode (same as other agents) to avoid the interactive
  bypass-permissions confirmation prompt. This enables fully unattended
  operation.

- **MVP chatbot project requirements** — Added a complete example
  `config/project-requirements.md` for an MVP chatbot with FastAPI backend,
  HTML/JS frontend, and llm-gateway local-claude integration.

- **Smoke Test Protocol for Team Leader** — Added a mandatory Smoke Test
  Protocol section to `team-leader.md`. Before marking any iteration complete,
  the Team Leader must start the application, test endpoints with real HTTP
  requests, verify the UI loads and functions, and test integrations end-to-end.
  This is non-negotiable in all modes. In MVP without QA Engineer, the Team
  Leader is personally responsible for smoke testing.

- **Output Verification Mandate (_base-agent.md Section 14)** — New universal
  rule: every agent that produces runnable code must verify it actually runs.
  Passing unit tests is necessary but NOT sufficient. Agents must start the
  application and exercise their feature before marking work as done.

- **MVP testing enforcement for developers** — `backend-developer.md` and
  `frontend-developer.md` now explicitly require starting the server and
  verifying endpoints/UI respond correctly before marking tasks done. Unit
  tests alone are no longer sufficient even in MVP mode.

- **Lean team TEST phase fallback** — Team Leader's TEST phase now has
  explicit instructions for when QA Engineer is not in the team: developer
  agents run their own tests, then Team Leader executes the Smoke Test
  Protocol as QA fallback.

### Changed

- **team-config.yaml** — Updated with MVP chatbot description and tech stack
  preferences (Python, FastAPI, Docker) for end-to-end testing.

- **_base-agent.md section numbering** — Inserted Section 14 (Output
  Verification Mandate). Sections 14-20 shifted to 15-21. Updated all
  cross-references in agent files.

## [0.1.0] — 2026-02-28

### Added

- Initial Forge framework implementation (12-phase build from plan.md).
- CLI entry point (`./forge`) with setup, init, start, stop, status, cost,
  tell, attach, and logs commands.
- 16 agent definition files covering lean (8) and full (12) team profiles.
- 34 project templates across 8 categories.
- File-based messaging system (`shared/.queue/`).
- tmux-based process isolation for agents.
- Watchdog daemon for agent health monitoring.
- Log aggregator daemon with rotation.
- Snapshot-based stop/resume workflow.
- Cost tracking and budget enforcement.
- Human override via `./forge tell` and `shared/.human/override.md`.
- CLAUDE.md integration (global, project, both, none).
- Interactive setup wizard (`./forge init`).
