# T3 Stack Patterns

> These patterns describe architectural decisions for the T3 stack template. No implementation is provided in this stub.

## 1. End-to-End Type Safety with tRPC

**WHY:** Traditional REST APIs require manual type definitions on both client and server, which inevitably drift. tRPC infers types directly from server router definitions, so any change to an API procedure is immediately reflected in client code at compile time. This eliminates an entire category of integration bugs without requiring code generation steps.

## 2. Prisma Schema as Single Source of Truth

**WHY:** The Prisma schema defines database structure, TypeScript types, and migration history in one file. This prevents the common problem where application types, database schema, and ORM models diverge over time. Every database change flows through a reviewed migration, ensuring environments stay consistent.

## 3. Server Components with Selective Hydration

**WHY:** Next.js Server Components render on the server and send zero JavaScript to the client by default. Only interactive components ("use client") ship JS. This dramatically reduces bundle size and initial load time while keeping the full React component model for developer ergonomics.

## 4. Procedure-Level Authorization

**WHY:** tRPC middleware runs before individual procedures, allowing auth checks to be composed declaratively (protectedProcedure, adminProcedure). This ensures every protected endpoint is guarded by construction rather than relying on developers remembering to add auth checks -- a common source of security vulnerabilities.

## 5. Optimistic Mutations with Cache Invalidation

**WHY:** tRPC's React Query integration enables optimistic UI updates that make the app feel instant. When a mutation succeeds, specific query caches are invalidated automatically. On failure, the optimistic update rolls back. This provides snappy UX without sacrificing data consistency.
