# Cockpit Dashboard

The cockpit dashboard provides a live, auto-refreshing view of your Forge session using tmux panes.

## Layout

```text
┌──────────────────────────────────┬───────────────────────┐
│  FORGE COCKPIT v1.0.0            │  AGENT STATUS         │
│  ─────────────────────────────── │  ───────────────────  │
│  Project: MyApp                  │  ● TL: Planning Iter2 │
│  Mode: production-ready          │  ● AR: Designing API  │
│  Strategy: co-pilot              │  ● BE: Writing auth   │
│  Iteration: 2                    │  ● FE: Building login │
│  Cost: $1.25 / $10.00           │  ● QA: Idle           │
│  Agents: 6 active               │  ● DO: Setting up CI  │
│  Elapsed: 45m                    │                       │
├──────────────────────────────────┴───────────────────────┤
│  TEAM LEADER SUMMARY                                     │
│  Iteration 2 underway. Auth module 60% complete.         │
│                                                          │
│  RECENT ACTIVITY                                         │
│  [14:32] BE: Completed user registration endpoint        │
│  [14:28] AR: Delivered REST API contract v2              │
│  [14:25] QA: Waiting for auth endpoints to test          │
├──────────────────────────────────────────────────────────┤
│  claude> █                                               │
│  (Interactive session — commands, approvals, feedback)    │
└──────────────────────────────────────────────────────────┘
```

## Zones

| Zone | Pane | Refresh | Script |
|------|------|---------|--------|
| Top-left | Metrics panel | Every 3s | `scripts/cockpit/metrics-panel.sh` |
| Top-right | Agent status grid | Every 2s | `scripts/cockpit/agent-grid.sh` |
| Middle | Activity feed + TL summary | Every 5s | `scripts/cockpit/activity-feed.sh` |
| Bottom | Claude interactive session | Manual | `claude` |

## Launching

```bash
# Default: cockpit dashboard (requires tmux)
./forge

# Plain mode (no cockpit)
./forge --no-cockpit
```

## Navigation

The cockpit uses standard tmux keybindings:

| Key | Action |
|-----|--------|
| `Ctrl+B` then arrow key | Switch between panes |
| `Ctrl+B` then `D` | Detach from session (keeps running) |
| `Ctrl+B` then `z` | Zoom current pane (toggle fullscreen) |
| `Ctrl+B` then `[` | Enter scroll mode (use arrows/PgUp/PgDn) |
| `q` | Exit scroll mode |

## Color Coding

### Agent Status Indicators

| Color | Status |
|-------|--------|
| Green `●` | Working / Active |
| Yellow `●` | Idle / Waiting |
| Red `●` | Blocked / Error |
| Orange `●` | Rate-limited |
| Purple `●` | Suspended |
| Gray `●` | Done / Completed |
| Cyan `●` | In Review |

### Cost Indicators

| Color | Meaning |
|-------|---------|
| Green | Under 80% of budget |
| Yellow | 80-100% of budget |
| Red | Over budget |

## Agent Abbreviations

| Abbreviation | Agent |
|-------------|-------|
| TL | Team Leader |
| AR | Architect |
| BE | Backend Developer |
| FE | Frontend Engineer |
| FD | Frontend Designer |
| FV | Frontend Developer |
| QA | QA Engineer |
| DO | DevOps Specialist |
| CR | Critic |
| RS | Research-Strategist |
| RE | Researcher |
| ST | Strategist |
| SE | Security Tester |
| PE | Performance Engineer |
| DC | Documentation Specialist |

## Customization

### Refresh Intervals

Edit `scripts/cockpit/dashboard.sh` to change the `watch -n` intervals:

- Metrics: `-n 3` (every 3 seconds)
- Agent grid: `-n 2` (every 2 seconds)
- Activity feed: `-n 5` (every 5 seconds)

### Disabling the Cockpit

If tmux is not available, the cockpit falls back to a plain Claude session automatically. You can also force plain mode:

```bash
./forge --no-cockpit
```

## Scripts

All cockpit scripts are in `scripts/cockpit/`:

- `render.sh` — Shared color constants, box-drawing chars, formatting functions
- `metrics-panel.sh` — Project info, mode, strategy, cost, elapsed time
- `agent-grid.sh` — Color-coded agent status grid
- `activity-feed.sh` — Recent activity from logs + TL summary
- `dashboard.sh` — Main launcher, creates tmux layout
