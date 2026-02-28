# /forge-mode — Switch Mode or Strategy

Parse `$ARGUMENTS` for the new mode or strategy value.
Valid modes: `mvp`, `production-ready`, `no-compromise`
Valid strategies: `auto-pilot`, `co-pilot`, `micro-manage`

Update `config/team-config.yaml` using `yq` and notify agents of the change.
Report what changed.

Usage: `/forge-mode mvp`, `/forge-mode auto-pilot`
