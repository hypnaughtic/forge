# /forge-stop — Save State and Stop

1. Instruct all agents to save their working memory and finalize in-progress work
2. Update your own working memory with full resume context (iteration, phase, active agents, pending tasks, cost, next steps)
3. Checkpoint commit any uncommitted work: `git add -A && git commit -m "chore: forge session checkpoint"`
4. Run: `bash $FORGE_DIR/scripts/stop.sh --snapshot-only`
5. Run: `bash $FORGE_DIR/scripts/cost-tracker.sh --report` and display the cost summary
6. Report to the user: iteration, phase, snapshot path, and the cost breakdown above
7. Tell the user the session is saved

$ARGUMENTS: none
