# Forge Plugin Architecture

Forge can be used as a Claude Code plugin, providing 12 skills accessible via `/forge` commands in any Claude Code session.

## Installation

Place the forge directory where Claude Code can discover it, then launch with:

```bash
claude --plugin-dir /path/to/forge
```

Or install as a registered plugin (when marketplace support is available).

## Plugin Manifest

`.claude-plugin/plugin.json` declares the plugin metadata:

```json
{
  "name": "forge",
  "version": "1.0.0",
  "description": "AI Software Forge — Orchestrate a team of Claude Code agents",
  "author": { "name": "Rushabh Thakkar" },
  "homepage": "https://github.com/Rushabh1798/forge",
  "license": "MIT"
}
```

## Skills Reference

| Skill | Invocation | Type | Description |
|-------|-----------|------|-------------|
| forge | `/forge <NL>` | Router | Smart NL classifier, routes to instant or async |
| status | `/forge:status` | Instant | Iteration, agents, tasks, blockers + cost brief |
| cost | `/forge:cost` | Instant | Detailed cost breakdown by agent |
| snapshot | `/forge:snapshot` | Instant | Save state without stopping |
| start | `/forge:start` | Lifecycle | Spawn team, begin iteration 1 |
| stop | `/forge:stop` | Lifecycle | Save state, graceful shutdown |
| mode | `/forge:mode` | Instant | Switch project mode |
| strategy | `/forge:strategy` | Instant | Switch execution strategy |
| init | `/forge:init` | Setup | Interactive project configuration |
| ask | `/forge:ask` | Smart | Message Team Leader (with NL routing) |
| guide | `/forge:guide` | Async | Direct a specific agent via Team Leader |
| team | `/forge:team` | Instant | Detailed per-agent view |

## NL Router

The default `/forge` skill uses `scripts/nl-router.sh` for keyword-based intent classification. This fast path avoids AI reasoning for instant commands.

**Intent classification flow:**

1. Lowercase input, split on "and" / "&" / ","
2. Pattern-match each segment against known intent keywords
3. Return comma-separated intents

**Multi-intent support:** `/forge what is the cost and status` returns `COST,STATUS` and both are executed.

**Intent over invocation:** Even `/forge:ask what is cost` recognizes "cost" as instant.

## FORGE_DIR Resolution

`scripts/resolve-forge-dir.sh` resolves the installation directory across contexts:

1. `FORGE_DIR` environment variable (explicit override)
2. Script's own directory (git clone)
3. Homebrew libexec (`brew --prefix`/opt/forge/libexec)
4. Current working directory (fallback)

## Plugin Mode vs CLI Mode

| Feature | Plugin Mode | CLI Mode |
|---------|------------|----------|
| Cockpit dashboard | Formatted text blocks | tmux panes with auto-refresh |
| Skills | `/forge:status` etc. | `./forge status` etc. |
| Agent spawning | Agent Teams only | Agent Teams or tmux |
| tmux dependency | None | Optional (cockpit) |
