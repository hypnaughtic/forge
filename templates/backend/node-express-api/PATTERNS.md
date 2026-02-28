# Node Express API — Architectural Patterns

This document explains the patterns used in this template and **why** each
one was chosen. The goal is to help you make informed decisions when
extending or adapting the architecture.

---

## 1. Repository Pattern (via Prisma)

**What:** Database access is encapsulated in repository modules that expose
domain-specific methods. Prisma acts as the underlying query engine, but
route handlers never call Prisma directly.

**Why this pattern:**

- **Testability** — Repositories can be mocked in unit tests without needing
  a live database. This keeps tests fast and deterministic.
- **Encapsulation** — Query logic lives in one place. If a query needs
  optimization or the schema changes, only the repository is modified.
- **Portability** — Switching from Prisma to another ORM or raw SQL requires
  changes only in the repository layer, not across every route handler.

---

## 2. Middleware Chain

**What:** Express middleware functions are composed in a pipeline: logging,
authentication, validation, route handler, error handling.

**Why this pattern:**

- **Separation of concerns** — Each middleware handles exactly one
  responsibility (auth, validation, error formatting). No single function
  does too much.
- **Reusability** — Auth middleware can be applied to any route with a
  single line. Validation middleware is parameterized by a Zod schema.
- **Predictable flow** — The middleware pipeline executes in a defined
  order. Developers can reason about what happens before and after their
  route handler.

---

## 3. DTO Validation with Zod

**What:** Request bodies, query parameters, and path parameters are validated
against Zod schemas before reaching the route handler.

**Why this pattern:**

- **Type safety at runtime** — TypeScript types are erased at runtime. Zod
  ensures that incoming data actually matches the expected shape.
- **Automatic type inference** — `z.infer<typeof schema>` generates
  TypeScript types from Zod schemas, eliminating type/validation drift.
- **Clear error messages** — Zod produces structured validation errors that
  the error middleware can format into consistent API responses.
- **Composability** — Schemas can be composed, extended, and refined,
  making it easy to share validation logic across endpoints.

---

## 4. Centralized Error Handling Middleware

**What:** A single Express error middleware at the end of the middleware chain
catches all errors and formats them into consistent JSON responses.

**Why this pattern:**

- **Consistency** — Every error response has the same shape, making the API
  predictable for consumers.
- **No try/catch duplication** — Route handlers throw errors (or let them
  propagate). The error middleware handles formatting and status codes.
- **Operational errors vs programmer errors** — The middleware distinguishes
  between expected errors (validation, not found) and unexpected errors
  (null reference, connection failure), logging them differently.
- **Security** — Stack traces and internal details are stripped from
  production responses automatically.

---

## 5. Environment Configuration Module

**What:** All environment variables are loaded, validated, and exported from
a single `config/index.ts` module.

**Why this pattern:**

- **Fail fast** — If a required environment variable is missing, the
  application crashes at startup with a clear message, not at the first
  request that tries to use it.
- **Type safety** — Configuration values are typed and coerced (e.g., port
  as a number, not a string).
- **Single source of truth** — No `process.env.XYZ` scattered across the
  codebase. All config access goes through the config module.

---

## 6. Health Check Endpoint

**What:** A `/health` endpoint returns application and dependency status.

**Why this pattern:**

- **Container orchestration** — Kubernetes, ECS, and Docker Compose use
  health checks to manage container lifecycle and readiness.
- **Operational visibility** — A single endpoint that verifies database
  connectivity and application health.
