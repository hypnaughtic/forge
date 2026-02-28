# /forge-start — Start Building

Read the project configuration and requirements. Then:

1. Initialize working memory at `shared/.memory/team-leader-memory.md`
2. Initialize decision log at `shared/.decisions/decision-log.md`
3. Spawn the research-strategist agent and request an initial strategy + iteration plan based on the project requirements and mode
4. Once strategy is received, decompose Iteration 1 into tasks with IDs, descriptions, assignees, dependencies, and acceptance criteria
5. Spawn the remaining team agents as needed based on the team profile
6. Report to the user: team composition, Iteration 1 goals, estimated approach

Use the orchestration backend specified in your CLAUDE.md context (Agent Teams or tmux) for spawning agents.

$ARGUMENTS can optionally specify focus areas, e.g.: `/forge-start "focus on auth first"`
