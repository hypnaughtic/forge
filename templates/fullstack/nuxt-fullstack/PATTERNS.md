# Nuxt Fullstack Patterns

> These patterns describe architectural decisions for the Nuxt fullstack template. No implementation is provided in this stub.

## 1. Unified Server/Client Architecture

**WHY:** Nuxt 3 with Nitro allows API routes and pages to coexist in the same project with shared TypeScript types. This eliminates the API contract drift that occurs when frontend and backend are separate repositories, and enables $fetch to auto-infer response types from server routes.

## 2. Drizzle ORM with Push-Based Migrations

**WHY:** Drizzle provides SQL-like syntax with full TypeScript inference, avoiding the "magic" of active record patterns. Its push-based migration approach lets developers modify the schema in code and generate migrations automatically, reducing the gap between schema intent and database reality.

## 3. Hybrid Rendering Strategy

**WHY:** Not all pages have the same performance requirements. Product pages benefit from SSG for instant loads and SEO, dashboards need SSR for fresh data, and interactive widgets can be SPA-only. Nuxt's route rules allow per-route rendering strategies without architectural changes.

## 4. Server-Side Validation with Shared Schemas

**WHY:** Client-side validation improves UX but cannot be trusted for security. Defining validation schemas (with Zod) once and using them on both client and server ensures consistent rules. The server always re-validates, preventing tampered requests from bypassing business rules.

## 5. Composable Data Fetching with useFetch/useAsyncData

**WHY:** Nuxt's data fetching composables handle SSR hydration automatically -- data fetched on the server is serialized and reused on the client without duplicate requests. This prevents flash-of-loading-state issues and ensures SEO crawlers see fully rendered content.
