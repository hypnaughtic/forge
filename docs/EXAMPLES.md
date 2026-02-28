# Forge Examples

End-to-end walkthroughs showing Forge in action across different project types, team sizes, and modes.

---

## Example 1: MVP SaaS App -- Task Management Tool

A greenfield MVP built from scratch with a lean team.

### Configuration

```yaml
project:
  description: "Task management app with teams, boards, and real-time updates"
  type: "new"
  directory: "~/projects/task-app"  # Where agents build the project (not inside forge repo)
mode: "mvp"
strategy: "auto-pilot"
cost:
  max_development_cost: 30
agents:
  team_profile: "lean"  # 8 agents with merged roles
tech_stack:
  languages: ["typescript"]
  frameworks: ["nextjs", "prisma"]
  databases: ["postgresql"]
```

You can also pass `--project-dir` on the command line:
```bash
./forge start --project-dir ~/projects/task-app
```

### What Happens When `./forge start` Runs

The start script resolves the lean profile (team-leader, research-strategist, architect, backend-developer, frontend-engineer, qa-engineer, devops-specialist, critic), creates tmux session `forge-task-management-app`, launches watchdog and log-aggregator daemons, and spawns the Team Leader. The Team Leader then spawns the remaining 7 agents.

### Sample Agent Messages

**Team Leader assigns strategy work:**
```markdown
---
from: team-leader | to: research-strategist | priority: high | type: request
---
## Subject: Initial Strategy and Iteration Plan
Analyze requirements for a task management app. Produce: (1) technical strategy,
(2) iteration plan (3-4 iterations for MVP), (3) risk assessment.
Mode: MVP. Focus on speed. Consider Next.js fullstack template.
```

**Backend Developer reports completion:**
```markdown
---
from: backend-developer | to: team-leader | type: deliverable | confidence: high
---
## Subject: User Authentication Complete
Implemented NextAuth.js with credentials + GitHub OAuth, Prisma User model,
login/register API routes, session middleware for protected routes.
Branch: agent/backend-developer/TASK-001-auth
```

### Iteration 1 Flow

**PLAN**: Team Leader decomposes into 5 tasks (auth, schema, board API, board UI, tests). Architect defines API contracts.

**EXECUTE**: Backend Developer implements auth and board API. Frontend Engineer builds board UI with drag-and-drop. DevOps sets up Docker Compose + PostgreSQL.

**TEST**: QA Engineer runs tests, finds 2 failures in board API validation. Backend Developer fixes them. In lean teams without QA, developers run their own tests and the Team Leader performs smoke testing (start the app, test endpoints with real HTTP requests, verify UI loads).

**INTEGRATE**: Team Leader merges all feature branches. Build passes.

**REVIEW**: Cross-review via messages. One WARNING: missing error handling on 404.

**CRITIQUE**: Critic scores -- Functional: 80%, Technical: 80%, User-Quality: 75%. All above MVP threshold of 70%.

**DECISION**: PROCEED. Tag `iteration-1-verified`. Team Leader reports to human:

```
Iteration 1 complete. Run locally: docker compose up -d && npm run dev
Features: auth, board CRUD, drag-and-drop UI. Cost: $8.20 / $30.00.
Iteration 2: board reordering, real-time updates, team management.
```

---

## Example 2: Adding AI Features to Existing Project

A brownfield project with established conventions and a `CLAUDE.md` file.

### Configuration

```yaml
project:
  description: "Add AI-powered search and recommendations to existing e-commerce platform"
  type: "existing"
  existing_project_path: "/home/user/ecommerce-platform"
  directory: "/home/user/ecommerce-platform"  # Same as existing path for brownfield
mode: "production-ready"
strategy: "co-pilot"
cost:
  max_development_cost: 80
agents:
  team_profile: "auto"  # Resolves to "full" for production-ready
  exclude: ["performance-engineer"]
claude_md:
  source: "both"
  priority: "project-first"  # Existing project conventions take precedence
```

### How Agents Handle Existing Code

With `type: "existing"`, `init-project.sh` reads the project's `CLAUDE.md` and merges it (project-first priority) with `~/.claude/CLAUDE.md` into each generated agent file. The Research Strategist analyzes existing code structure before proposing changes. The Architect documents existing patterns and proposes additions that align -- not replacements. If the project's `CLAUDE.md` specifies Black formatter, `/api/v2/` prefix, repository pattern, and RFC 7807 errors, all produced code must comply.

### Sample Corrective Message

When the Backend Developer writes raw SQL in a route handler, the Architect catches it:

```markdown
---
from: architect | to: backend-developer | priority: high | type: review-response
---
## Subject: BLOCKER -- Convention Violation in Search Endpoint
File: packages/api/routes/search.py, lines 45-62
Issue: Raw SQL in route handler. Project CLAUDE.md mandates repository pattern.
Fix: Move vector similarity query to packages/api/repositories/search_repo.py.
Severity: BLOCKER
```

The key difference from greenfield: every agent must respect existing file structure, naming conventions, import patterns, test frameworks, and CI/CD configuration.

---

## Example 3: Production-Ready with Full Team

Demonstrating full team composition, specialized agents, and No Compromise mode.

### Lean vs Full Team

The full team splits merged roles (research-strategist becomes researcher + strategist; frontend-engineer becomes frontend-designer + frontend-developer) and adds security-tester, performance-engineer, and documentation-specialist -- growing from 8 to 12 agents.

### Configuration

```yaml
project:
  description: "Enterprise payment processing platform"
  type: "new"
  directory: "/home/user/projects/payment-platform"
mode: "no-compromise"
strategy: "co-pilot"
cost:
  max_development_cost: "no-cap"
agents:
  team_profile: "full"  # All 12 agents
tech_stack:
  languages: ["typescript", "python"]
  frameworks: ["nestjs", "fastapi"]
  databases: ["postgresql", "redis", "elasticsearch"]
```

### How Specialized Agents Add Value

**Security Tester** reviews payment endpoints:
```
BLOCKER: SQL injection in payment_repo.py:89 -- Fix: parameterized query.
BLOCKER: Missing rate limiting on /api/v1/payments/process -- Fix: 10 req/min/user.
WARNING: Weak HMAC (SHA-1) for webhooks -- upgrade to SHA-256.
Verdict: FAIL (2 BLOCKERs must be resolved).
```

**Performance Engineer** runs load tests:
```
GET /api/v1/analytics/summary: p95=1.2s (target <500ms) -- FAIL
  Fix: materialized view + composite index (merchant_id, created_at).
POST /api/v1/payments/process: p95=210ms -- PASS
```

### No Compromise Critic Review

In No Compromise mode, the threshold is 100% per category. A single FAIL blocks progress:

```
Critique Report: Iteration 3 -- Verdict: FAIL

Functional: 18/18 (100%) PASS | Technical: 14/15 (93%) FAIL | User-Quality: 11/12 (92%) FAIL

TECH-015 FAIL: Analytics endpoint at 1.2s p95 (target <500ms).
  Action: Implement materialized view per Performance Engineer recommendation.
UQ-009 FAIL: Search "refund pending March" returns all March transactions
  regardless of refund status. Generic full-text matching insufficient.
  Action: Implement semantic query parsing (status filters, date ranges).

Recommendation: REWORK. Two criteria must be resolved.
```

The Team Leader decides REWORK, sends targeted assignments to the Backend Developer, waits for fixes, runs a focused TEST-CRITIQUE cycle on the affected criteria, and once both pass, tags `iteration-3-verified`.

---

## Key Takeaways

| Aspect | MVP (Ex. 1) | Brownfield (Ex. 2) | No Compromise (Ex. 3) |
|--------|-------------|--------------------|-----------------------|
| Team | 8 (lean) | 11 (full minus 1) | 12 (full) |
| Critic threshold | 70% | 90% | 100% |
| CLAUDE.md | none | project-first merge | global |
| Strategy | auto-pilot | co-pilot | co-pilot |
| Focus | Speed | Convention compliance | Zero tolerance |
