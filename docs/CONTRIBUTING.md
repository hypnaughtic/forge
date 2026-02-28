# Contributing to Forge

How to extend and improve the Forge framework itself. For internals, see [ARCHITECTURE.md](ARCHITECTURE.md). For agent communication, see [AGENT-PROTOCOL.md](AGENT-PROTOCOL.md).

---

## Adding a New Agent Type

1. **Create the agent markdown file** at `agents/{agent-name}.md` with all 12 required sections: (1) Identity & Role, (2) Core Responsibilities, (3) Skills & Tools, (4) Input Expectations, (5) Output Deliverables, (6) Communication Protocol, (7) Collaboration Guidelines, (8) Quality Standards, (9) Iteration Protocol, (10) Mode-Specific Behavior, (11) Memory & Context Management, (12) Artifact Registration. Follow the skeleton in `_base-agent.md`. Target 120-200 lines. Every section must have role-specific content -- the file must be self-contained so an agent reading only its own file plus `_base-agent.md` can operate independently.

2. **Register in team profiles** in `scripts/init-project.sh`. Find the `resolve_team_profile` function and add the agent to the `lean` profile, `full` profile, or both. Agents relevant only for production-ready or no-compromise modes go in `full` only.

3. **Update the Critic's awareness** in `agents/critic.md` if the new agent produces artifacts that need quality evaluation.

4. **Test** by setting `agents.team_profile: "custom"` in `config/team-config.yaml`, adding your agent to the `include` list, and running `./forge start`.

## Adding a New Template

Templates live under `templates/{category}/{template-name}/`. Each directory must contain:

| File | Required | Purpose |
|------|----------|---------|
| `README.md` | Yes | What this template provides (30-50 lines) |
| `PATTERNS.md` | Yes | Architectural patterns and conventions (40-80 lines) |
| `template-config.yaml` | Yes | Metadata: name, category, tags, tech stack |
| `scaffold/` | Yes | Full working code for priority templates, `placeholder.md` for stubs |

In `template-config.yaml`, set `priority: true` for templates with full scaffolds and `priority: false` for stubs. After creating the directory, add the template to `templates/_template-manifest.yaml`.

## Modifying Existing Agents

When updating agent files in `agents/`, pay attention to these sections:

- **Core Responsibilities (2)**: Ensure every duty is numbered and actionable.
- **Communication Protocol (6)**: Keep consistent with `_base-agent.md` and `docs/AGENT-PROTOCOL.md`.
- **Quality Standards (8)**: All criteria must be checkboxes. Update when raising or lowering the bar.
- **Mode-Specific Behavior (10)**: Update when mode thresholds change.

If modifying `_base-agent.md`, verify that the change works for ALL agents -- a bug here breaks the entire fleet.

## Adding New Scripts or CLI Commands

### New script

1. Create the script at `scripts/{script-name}.sh` following the bash style guide below.
2. Include a `--help` flag that prints usage, options, and a brief description.

### New CLI command

1. Add a `cmd_your_command()` function in the `forge` CLI file.
2. Add a case to the command router at the bottom of the file.
3. Update the `usage()` function to list the new command.
4. Ensure the function handles `--help` as its first argument.

## Bash Script Style Guide

```bash
#!/usr/bin/env bash
set -euo pipefail  # Always. No exceptions.

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[Component]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[Component]${NC} $*"; }
log_error() { echo -e "${RED}[Component]${NC} $*" >&2; }
```

Additional rules:

- Every script must support `--help` / `-h` as the first argument.
- Use `"${variable}"` with quotes, not bare `$variable`.
- Validate required arguments early with clear error messages.
- Use `command -v` to check for required tools before using them.
- Prefer `$(...)` over backticks for command substitution.
- Use `local` for function-scoped variables.
- Document non-obvious logic with inline comments.

### macOS Compatibility Requirements

Forge must work on both Linux and macOS. Watch for these common pitfalls:

| Linux only | Portable alternative |
|------------|---------------------|
| `date -d "$ts" +%s` | Use the `iso_to_epoch()` helper (GNU → macOS → Python fallback) |
| `stat -c%s file` | `stat -c%s file 2>/dev/null \|\| stat -f%z file 2>/dev/null` |
| `sed -i 's/.../.../'` | Check `uname` and use `sed -i ''` on Darwin |
| `mktemp /tmp/name-XXXXXX.ext` | `mktemp "${TMPDIR:-/tmp}/name-XXXXXXXX"` (no suffix after X's) |
| `tmux list-windows \| awk ... \| tr -d '*-'` | `tmux list-windows -F '#{window_name}'` |

## Testing Changes

1. **Syntax check**: `bash -n scripts/{your-script}.sh`
2. **Setup check**: `./forge setup` validates dependencies.
3. **Full session test**: `./forge start` with a simple config, verify agents spawn, `./forge stop` to verify snapshots.
4. **Resume test**: `./forge start` again to verify resume flow.
5. **Agent files**: Read end-to-end, confirm all 12 sections present, cross-references correct.

## Pull Request Guidelines

- **Title**: Descriptive summary (e.g., "Add data-engineer agent type" not "Update agents").
- **Description**: Explain **why**, not just what. Include testing context.
- **Scope**: One agent, one script, or one template per PR when possible.
- **Checklist**:
  - [ ] Modified scripts pass `bash -n` syntax check
  - [ ] Modified agent files have all 12 required sections
  - [ ] Cross-references between files are correct
  - [ ] `--help` flag works on new or modified scripts
  - [ ] No secrets or credentials in committed files
  - [ ] `forge` CLI router updated if adding a new command
