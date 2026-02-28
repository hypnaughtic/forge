# Base Agent Protocol

> Shared protocol loaded by ALL Forge agents alongside their role-specific instruction file. Your role file defines WHAT you do; this file defines HOW you operate within the team.

---

## 1. File-Based Message Queue

Each agent has an inbox: `shared/.queue/{agent-name}-inbox/`. Messages are individual files named `msg-{unix-timestamp}-{sender}.md`.

**Writing** -- always atomic: write to temp, then move to prevent partial reads:
```bash
TEMP_FILE=$(mktemp /tmp/forge-msg-XXXXXX.md)
cat > "$TEMP_FILE" <<EOF   # write message content
EOF
mv "$TEMP_FILE" "shared/.queue/${TARGET}-inbox/msg-$(date +%s)-${MY_NAME}.md"
```

**Reading** -- process in timestamp order, delete after acknowledgment:
```bash
for msg in $(ls shared/.queue/${MY_NAME}-inbox/ | sort); do
  # process message...
  rm "shared/.queue/${MY_NAME}-inbox/$msg"
done
```

**Message format** -- YAML frontmatter with markdown body:
```markdown
---
id: msg-{unix-timestamp}-{sender}
from: {sender}
to: {target}
priority: normal          # normal | high | critical
timestamp: {ISO 8601}
type: status-update       # status-update | request | response | blocker | deliverable
                          # review-request | review-response | dependency-change
confidence: high          # high | medium | low (REQUIRED on deliverable & status-update)
---
## Subject: {brief subject}
{Body with details, artifact lists, and dependency needs}
```

## 2. Status Reporting

Maintain `shared/.status/{agent-name}.json` continuously. Update after every state change and at least every 5 minutes.

```json
{
  "agent": "{name}", "status": "working",
  "current_task": "", "blockers": [], "last_updated": "{ISO 8601}",
  "iteration": 2, "artifacts_produced": [],
  "estimated_completion": "30 minutes", "session_start": "{ISO 8601}",
  "messages_processed": 15,
  "usage_limits": { "warnings_detected": 0, "last_warning_at": null, "status": "normal" },
  "cost_estimate_usd": 1.25
}
```

**Valid statuses**: `idle` | `working` | `blocked` | `review` | `done` | `suspended` | `rate-limited` | `error` | `terminated`

## 3. Working Memory Mandate

Maintain `shared/.memory/{agent-name}-memory.md` with this structure:

```markdown
# Working Memory: {agent-name}
## Last Updated: {ISO 8601}
## Session Info
- Session started: {ts} | Current iteration: {N} | Messages processed: {count}
## Current Assignment
{What you are working on}
## Completed Work
- {task}: {status} -- {artifact}
## Key Decisions
- {decision}: {rationale}
## Dependencies Waiting On
- {agent}: {what needed}
## Important Context
{Domain knowledge, file modifications, patterns followed, gotchas -- anything lost on restart}
## Next Steps
1. {next task}
## Resume Context
{Populated during PREPARE_SHUTDOWN -- step-by-step resume instructions}
## Limit Save Context
{Populated during LIMIT_SAVE -- see Section 12}
```

**Update rules** -- update after every task, decision, and message. **Update at least every 10 minutes** during active work. This is NON-NEGOTIABLE -- it is your safety net for abrupt session kills. The file must be self-sufficient for full resume.

**Recovery**: on `--resume`, read memory + status + inbox, resume from "Next Steps", notify Team Leader.

## 4. Structured Logging

Append JSONL to `shared/.logs/{agent-name}.log`:
```json
{"timestamp":"{ISO}","agent":"{name}","level":"INFO","category":"task","message":"...","task_id":"TASK-001","iteration":2}
```
**Levels**: `INFO` | `WARN` | `ERROR`
**Categories** (with category-specific extra fields):
- `task` -- task_id, iteration
- `artifact` -- file_path
- `communication` -- target_agent, message_id
- `decision` -- decision_id, rationale
- `cost` -- tokens_in, tokens_out, estimated_cost_usd
- `error` -- details, stack_trace
- `recovery` -- recovery_type, memory_age

## 5. Shared Decision Log

Append-only at `shared/.decisions/decision-log.md`. Never edit/delete existing entries.
```markdown
### {DECISION-ID} -- {Title}
- **Date**: {ISO} | **Agent**: {name} | **Iteration**: {N} | **Confidence**: {high|medium|low}
- **Decision**: {what} | **Rationale**: {why} | **Alternatives**: {considered} | **Impact**: {downstream}
```

## 6. Git Workflow

**Branches**: `agent/{agent-name}/{task-id}-{short-description}`
**Commits**: `[{agent-name}] {type}: {description}` -- types: `feat`, `fix`, `refactor`, `test`, `docs`, `ci`, `chore`
**Only Team Leader merges to main.** After each verified iteration: `git tag iteration-{N}-verified`.

## 7. File Locking

Before editing shared source code, check/acquire lock at `shared/.locks/{md5-hash-of-filepath}.lock`:
```json
{ "locked_by":"{name}", "file_path":"{path}", "locked_at":"{ISO}",
  "reason":"{why}", "expected_duration_minutes": 30 }
```
1. No lock exists → create atomically (temp + `mv`).
2. Lock exists, fresh → message the locking agent; wait or request Team Leader mediation.
3. Lock exists, stale (> 2x expected duration) → notify Team Leader to decide.
4. After committing → delete lock. Config/docs/agent-specific files do not need locks.

## 8. Artifact Registration

Register in `shared/.artifacts/registry.json`:
```json
{ "id":"{artifact-id}", "path":"{file-path}", "type":"{api-spec|code|config|doc|test}",
  "produced_by":"{agent}", "version":3, "last_updated":"{ISO}",
  "dependents":["{agent-list}"], "description":"{what}" }
```
On update: increment version, update timestamp, send `dependency-change` message to all dependents.

## 9. Error Handling

Unrecoverable errors → update status to `error` → write `PRIORITY: CRITICAL` message to `shared/.queue/team-leader-inbox/` with error details, what you were doing, and what you tried → update working memory → wait for instructions.

## 10. Human Override Monitoring

Check `shared/.human/override.md` modification time at the start of every task and after every major operation. If modified since last check: read immediately, comply with `pause`/`abort` directives at once, forward `directive` types to Team Leader via CRITICAL message if not already acknowledged.

## 11. Graceful Shutdown (PREPARE_SHUTDOWN)

On receiving PREPARE_SHUTDOWN (complete within the grace period, default 60s):
1. Stop new subtasks -- do not begin any new work unit
2. Update working memory with full Resume Context (step-by-step resume instructions)
3. Checkpoint commit: `[{agent-name}] chore: shutdown checkpoint`
4. Release ALL file locks in `shared/.locks/`
5. Update status to `suspended`
6. Acknowledge to Team Leader

## 12. Usage Limit Self-Monitoring (LIMIT_SAVE)

Monitor for: 429 errors, CLI "approaching limit"/"usage warning" messages, 2-3x latency spikes, explicit limit notifications, sessions >4 hours. When detected, execute immediately (under 30 seconds total):

1. **STOP** current work -- finish only the current atomic operation
2. **SAVE** working memory with Limit Save Context: trigger, in-flight operation, files being modified, checkpoint commit hash, uncommitted changes summary, step-by-step resume instructions, estimated limit refresh time
3. **COMMIT**: `[{agent-name}] chore: LIMIT_SAVE checkpoint` (partial work is better saved than lost)
4. **STATUS**: set to `rate-limited`, `usage_limits.status` to `rate-limited`, `last_warning_at` to now
5. **RELEASE** all file locks
6. **NOTIFY** Team Leader: CRITICAL message -- "LIMIT_SAVE executed. Resume from working memory when limits refresh."

## 13. Vendor-Agnostic Coding Mandate

All external dependencies (databases, caches, cloud services, LLM providers, auth, payments, email, etc.) MUST be behind abstract interfaces with pluggable implementations. Easy vendor switching is a non-negotiable project requirement.

## 14. LLM Gateway Mandate

Any LLM calls in the project MUST use `llm-gateway` (https://github.com/Rushabh1798/llm-gateway). No direct LLM provider calls. Use `local-claude` mode for integration testing when enabled.

## 15. CLAUDE.md Compliance

Respect project-level CLAUDE.md rules when present. Project conventions (coding style, patterns, architecture) override your defaults when they conflict. These rules may be merged into your generated instruction file by `init-project.sh`.

## 16. Secret Safety

Six rules, no exceptions:
1. **NEVER log secrets** -- reference by env var name only: `"Using DB_PASSWORD"`, never the value
2. **NEVER include secrets in messages** -- env var name only
3. **NEVER commit secrets** -- `.env` in `.gitignore`; only `.env.example` with placeholders is committed
4. **NEVER put secrets in working memory** -- plain text files readable by any agent
5. **Use `.env.example` pattern** -- list all required env vars with placeholders and comments
6. **Audit for leaks** -- verify no secret values in logs, error messages, API responses, or git history

## 17. Confidence Signaling

Every deliverable/status-update to Team Leader includes `confidence: high|medium|low`. Add `confidence_note` when medium/low.
- **high** → standard review | **medium** → specialist review requested | **low** → mandatory 2+ agent review; escalated to human in Co-Pilot/Micro-Manage

## 18. Memory Compaction

On `COMPACT_MEMORY` from Team Leader: compress completed tasks from 2+ iterations ago to one-line summaries, remove resolved dependencies and fixed bugs, summarize old context to 1-2 sentences with detail preserved in `shared/.decisions/` reference files. **Never compact**: current assignment, active dependencies, constraining decisions, lock state, resume/limit context, project-wide conventions. Ensure compacted memory remains self-sufficient for resume.

## 19. Code Review Protocol

Submit `review-request` messages with: scope (`architectural-compliance|security|performance|code-quality|test-coverage`), files to review, context, specific concerns, branch name.

**Severity levels**: `BLOCKER` (must fix, re-review) | `WARNING` (should fix, Team Leader decides if blocking) | `NOTE` (optional suggestion). Fix all BLOCKERs, address WARNINGs. **Max 2 review rounds** -- unresolved after 2 rounds, Team Leader decides.

## 20. Iteration Lifecycle

`PLAN → EXECUTE → TEST → INTEGRATE → REVIEW → CRITIQUE → DECISION`

DECISION outcomes: **PROCEED** (tag + compact memory) | **REWORK** (back to PLAN with corrections) | **ROLLBACK** (restore last verified tag) | **ESCALATE** (human approval needed). Mode thresholds per category: MVP 70% | Production Ready 90% | No Compromise 100%.

---

## Ongoing Obligations Summary

These are continuous, not one-time:
1. Check inbox regularly | 2. Update status every 5 min | 3. Update memory every 10 min
4. Check human override at every task boundary | 5. Monitor for usage limit signals
6. Log all significant actions | 7. Acquire locks before editing shared code
8. Register artifacts | 9. Include confidence in deliverables | 10. Never expose secrets
