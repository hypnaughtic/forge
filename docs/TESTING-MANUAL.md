# Manual Testing Protocol

Step-by-step verification checklist for all Forge features.

## Prerequisites

- Claude Code CLI installed (`claude --version`)
- `yq`, `git`, `tmux`, `jq` installed
- Forge repository cloned with `./forge setup` run

## Test Checklist

### 1. Plugin Mode

```bash
claude --plugin-dir .
# Verify: 12 skills appear in /help or skill list
# Try: /forge:status, /forge:cost, /forge:team
```

- [ ] All 12 skills visible
- [ ] `/forge:status` returns formatted output
- [ ] `/forge:cost` returns cost report

### 2. NL Routing — Instant

```bash
# Inside Claude session or via CLI:
./forge ask "what is the status"
# Expected: runs status.sh directly, instant result
```

- [ ] Status query returns immediately (no TL queueing)
- [ ] Cost query returns immediately
- [ ] Team query returns immediately

### 3. NL Routing — Multi-Intent

```bash
./forge ask "cost and status"
# Expected: both cost and status results displayed
```

- [ ] Combined output from both scripts

### 4. Smart Classification (Intent Over Invocation)

```bash
# In plugin mode:
/forge:ask what is cost
# Expected: runs cost instantly (NOT queued as async)
```

- [ ] Recognized as COST intent despite `ask` invocation

### 5. Mode Change

```bash
./forge mode production-ready
# Expected: config updated, before/after report shown
```

- [ ] `config/team-config.yaml` mode field updated
- [ ] Report shows old → new mode
- [ ] Quality thresholds displayed

### 6. Strategy Change

```bash
./forge strategy co-pilot
# Expected: config updated, approval behavior shown
```

- [ ] `config/team-config.yaml` strategy field updated
- [ ] Report shows old → new strategy
- [ ] Permission flags displayed

### 7. Team View — All Agents

```bash
./forge team
# Expected: table with all agent statuses
```

- [ ] All active agents listed
- [ ] Status, task, cost columns displayed

### 8. Team View — Single Agent

```bash
./forge team backend-developer
# Expected: deep dive with memory, decisions, artifacts
```

- [ ] Agent details shown
- [ ] Working memory section displayed
- [ ] Recent decisions shown

### 9. Guide

```bash
./forge guide backend-developer "use PostgreSQL"
# Expected: override.md created with target_agent metadata
```

- [ ] `shared/.human/override.md` exists
- [ ] Contains `target_agent: backend-developer`
- [ ] Contains the message
- [ ] Confirmation displayed

### 10. Cockpit Dashboard

```bash
./forge
# Expected: tmux layout with 4 zones
```

- [ ] Metrics panel (top-left) shows project info, mode, cost
- [ ] Agent grid (top-right) shows color-coded agent statuses
- [ ] Activity feed (middle) shows recent activity
- [ ] Claude session (bottom) accepts input
- [ ] Panels auto-refresh (watch intervals)

### 11. No-Cockpit Fallback

```bash
./forge --no-cockpit
# Expected: plain Claude session (no tmux dashboard)
```

- [ ] Plain Claude session launches
- [ ] No tmux panes created

### 12. Deprecated Tell

```bash
./forge tell "hello team leader"
# Expected: deprecation notice + message queued
```

- [ ] Deprecation warning displayed
- [ ] Message still written to override.md

### 13. Version

```bash
./forge --version
# Expected: "Forge v1.0.0" (or current version)
```

- [ ] Version matches VERSION file

### 14. Homebrew (if tagged release exists)

```bash
brew tap Rushabh1798/forge
brew install forge
forge --help
forge --version
```

- [ ] Installation succeeds
- [ ] `forge --help` shows all commands
- [ ] `forge --version` shows correct version

## Automated Tests

Run all automated tests:

```bash
make ci-local        # Full CI mirror (lint + all tests)
make test-unit       # Unit tests only (~30s)
make test-validation # Validation tests (lint, schema)
make test-integration # Integration tests
```

## Test Coverage Summary

| Area | Unit Tests | Integration Tests | Manual |
|------|-----------|------------------|--------|
| NL Router | 25+ tests | Dry-run chain | NL routing |
| Skills/Plugin | Structure validation | Discovery, resolution | Plugin mode |
| Cockpit | Render utilities | Panel output | tmux layout |
| Mode/Strategy | Change scripts | Config lifecycle | Live switch |
| Team/Guide | Override writing | — | Agent targeting |
| Ask/Tell | Override format | — | Backward compat |
| CLI | Flags, help, version | — | Full workflow |
