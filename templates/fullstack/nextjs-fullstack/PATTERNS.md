# Next.js Fullstack — Architectural Patterns

This document explains the patterns used in this template and **why** each
one was chosen. These patterns leverage Next.js App Router capabilities to
build performant, maintainable fullstack applications.

---

## 1. Server Components by Default

**What:** All components are React Server Components (RSC) unless explicitly
marked with `"use client"`. Server components render on the server and send
HTML to the client, never shipping their JavaScript.

**Why this pattern:**

- **Smaller bundles** — Server component code never reaches the client
  bundle. A data-fetching component with heavy dependencies (date libraries,
  markdown parsers) adds zero bytes to the client.
- **Direct data access** — Server components can query the database, read
  files, or call internal services directly. No API route or fetch layer
  needed.
- **SEO and performance** — Content is rendered as HTML on the server,
  improving crawlability and first contentful paint.
- **Progressive enhancement** — The page works even before client JavaScript
  loads. Interactive components are hydrated independently.

Only add `"use client"` when a component needs browser APIs, event handlers,
or React hooks like `useState`/`useEffect`.

---

## 2. Server Actions for Mutations

**What:** Form submissions and data mutations use Next.js Server Actions
(`"use server"` functions) instead of API routes.

**Why this pattern:**

- **Type safety end-to-end** — The function signature is shared between
  client and server. No manual DTO serialization or API client needed.
- **Progressive enhancement** — Forms using server actions work without
  JavaScript. The browser submits the form as a standard POST request.
- **Colocation** — The mutation logic lives next to the UI that triggers it,
  making the code easier to follow.
- **Automatic revalidation** — Server actions integrate with Next.js cache
  revalidation, keeping displayed data fresh after mutations.

Use API routes (`route.ts`) only for webhooks, external integrations, or
endpoints consumed by non-browser clients.

---

## 3. Middleware-Based Authentication

**What:** NextAuth.js middleware runs on every request to protect routes,
redirect unauthenticated users, and inject session data.

**Why this pattern:**

- **Edge-compatible** — Middleware runs at the edge (before the request
  reaches your application), making auth checks extremely fast.
- **Centralized** — One middleware file protects all routes. No need to
  repeat auth checks in every page or layout.
- **Session management** — NextAuth handles token refresh, session
  persistence, and provider-specific flows. You configure; it executes.
- **Flexible providers** — OAuth (Google, GitHub), credentials, magic links,
  and custom providers are supported through a unified configuration.

---

## 4. Optimistic UI Updates

**What:** The UI updates immediately when a user performs an action, before
the server confirms the change. If the server rejects the change, the UI
rolls back.

**Why this pattern:**

- **Perceived performance** — The user sees immediate feedback. A "like"
  button increments instantly rather than showing a spinner.
- **React 18 support** — `useOptimistic` and `useTransition` provide
  framework-level primitives for optimistic updates.
- **Graceful degradation** — If the server action fails, the optimistic
  state is rolled back and an error is displayed.
- **Reduced loading states** — Fewer spinners and skeleton screens lead to
  a more fluid user experience.

---

## 5. Prisma Client Singleton

**What:** The Prisma client is instantiated once and reused across all
requests via a module-level singleton stored on `globalThis` in development.

**Why this pattern:**

- **Connection pooling** — A single Prisma client maintains a connection
  pool. Creating a new client per request would exhaust database connections.
- **Hot reload safety** — In development, Next.js hot-reloads modules
  frequently. Storing the client on `globalThis` prevents creating a new
  connection pool on every reload.
- **Consistency** — All server components and server actions share the same
  client instance, ensuring consistent connection behavior.

---

## 6. Health Check API Route

**What:** A `/api/health` route returns application and database status.

**Why this pattern:**

- **Deployment readiness** — Container orchestrators (Kubernetes, ECS)
  and hosting platforms (Vercel, Railway) use health endpoints to manage
  application lifecycle.
- **Database verification** — The health check queries the database to
  verify connectivity, catching configuration issues early.
- **Monitoring integration** — Uptime monitors can poll this endpoint to
  detect outages.
