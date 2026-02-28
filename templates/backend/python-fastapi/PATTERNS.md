# Python FastAPI — Architectural Patterns

This document explains the patterns used in this template and, critically,
**why** each pattern was chosen. Understanding the reasoning lets you adapt
the architecture as your project grows rather than cargo-culting structure.

---

## 1. Repository Pattern

**What:** Data access is abstracted behind repository classes that expose
domain-oriented methods (`find_by_id`, `create`, `list_active`) instead of
raw SQL or ORM queries.

**Why this pattern:**

- **Testability** — Repositories can be replaced with in-memory fakes during
  testing, eliminating the need for a live database in unit tests.
- **Single Responsibility** — Routers handle HTTP concerns; repositories
  handle persistence concerns. Neither leaks into the other.
- **Migration safety** — If you switch from PostgreSQL to another store, only
  the repository implementation changes. Router code stays untouched.

The `BaseRepository` in `repositories/base.py` defines the abstract interface.
Concrete repositories inherit from it and implement storage-specific logic.

---

## 2. Dependency Injection via FastAPI

**What:** FastAPI's `Depends()` system wires repositories, database sessions,
and configuration into route handlers at request time.

**Why this pattern:**

- **No global state** — Each request gets its own database session and
  repository instance, preventing cross-request data leaks.
- **Composability** — Dependencies can depend on other dependencies, forming
  a clean dependency graph that FastAPI resolves automatically.
- **Framework-native** — Using FastAPI's built-in DI avoids third-party
  containers and keeps the learning curve low.

---

## 3. Async Request Handlers

**What:** All route handlers and database operations use `async/await`.

**Why this pattern:**

- **Concurrency under load** — An async handler waiting on a database query
  releases the event loop to serve other requests. Under I/O-heavy workloads
  this yields significantly higher throughput than synchronous handlers.
- **Ecosystem alignment** — FastAPI, SQLAlchemy 2.0, and the asyncpg driver
  all support native async. Using sync would waste this capability.
- **Consistency** — Mixing sync and async handlers in FastAPI leads to subtle
  thread-pool exhaustion bugs. Going fully async avoids that class of errors.

---

## 4. Pydantic v2 Models for Validation and Serialization

**What:** Request bodies, response schemas, and application settings are all
defined as Pydantic models.

**Why this pattern:**

- **Automatic validation** — Invalid data is rejected at the API boundary
  with clear error messages before it reaches business logic.
- **Documentation** — Pydantic models feed directly into the OpenAPI schema,
  keeping docs in sync with code automatically.
- **Performance** — Pydantic v2's Rust-based core is an order of magnitude
  faster than v1, making validation overhead negligible.
- **Settings management** — `pydantic-settings` loads environment variables
  into typed, validated settings objects, catching misconfiguration at startup
  rather than at runtime.

---

## 5. Multi-Stage Docker Build

**What:** The Dockerfile uses a builder stage to install dependencies and a
slim runtime stage for the final image.

**Why this pattern:**

- **Smaller images** — Build tools and caches stay out of the production
  image, reducing image size by 60-80%.
- **Security** — Fewer packages in the runtime image means a smaller attack
  surface.
- **Reproducibility** — Pinned base images and dependency locks ensure the
  same build produces the same image regardless of when or where it runs.

---

## 6. Health Check Endpoint

**What:** A `/health` endpoint returns application and dependency status.

**Why this pattern:**

- **Orchestration integration** — Kubernetes, ECS, and Docker Compose all
  use health checks to manage container lifecycle.
- **Observability** — The health endpoint can verify database connectivity,
  giving operators a single URL to check system readiness.
