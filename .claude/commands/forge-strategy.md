# /forge-strategy — Switch Execution Strategy

Parse `$ARGUMENTS` for the new strategy value.
Valid strategies: `auto-pilot`, `co-pilot`, `micro-manage`

Run the strategy change script:

```bash
bash $FORGE_DIR/scripts/change-strategy.sh "$ARGUMENTS"
```

Report what changed: old strategy → new strategy, approval behavior change.

**Note:** To switch the project quality mode, use `/forge-mode` instead.

Usage: `/forge-strategy co-pilot`, `/forge-strategy auto-pilot`

$ARGUMENTS
