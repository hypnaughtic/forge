# Homebrew Installation

Forge can be installed via Homebrew for system-wide access.

## Install

```bash
brew tap Rushabh1798/forge
brew install forge
```

## How It Works

The Homebrew formula:

1. Installs forge, scripts/, agents/, templates/, skills/, .claude-plugin/, .claude/, and config/ to `$(brew --prefix)/opt/forge/libexec`
2. Creates a `bin/forge` wrapper that sets `FORGE_DIR` and delegates to the real forge script
3. Declares dependencies: `yq`, `git` (required), `tmux` (recommended)

## Wrapper Script

The Homebrew wrapper (`bin/forge`) does:

```bash
export FORGE_DIR="$(brew --prefix)/opt/forge/libexec"
exec "${FORGE_DIR}/forge" "$@"
```

This means `FORGE_DIR` is always set correctly regardless of where you run `forge` from.

## Config Location

When installed via Homebrew, forge looks for project config in this order:

1. `./config/team-config.yaml` (current working directory)
2. `$FORGE_DIR/config/team-config.yaml` (Homebrew libexec)

Run `forge init` in your project directory to create a local config.

## Coexistence with Plugin Mode

Homebrew and plugin installations can coexist:

- **Homebrew**: Provides the `forge` CLI command system-wide
- **Plugin**: Provides `/forge` skills inside Claude Code sessions

Both share the same scripts and agent definitions. The `FORGE_DIR` resolution (`scripts/resolve-forge-dir.sh`) handles the path differences.

## Upgrading

```bash
brew update && brew upgrade forge
```

## Uninstall

```bash
brew uninstall forge
brew untap Rushabh1798/forge
```

## External Repository

The Homebrew tap lives at `github.com/Rushabh1798/homebrew-forge`. It contains:

- `Formula/forge.rb` — The Homebrew formula
- `README.md` — Tap documentation

The formula is updated automatically when a new GitHub release is tagged (`v*`).
