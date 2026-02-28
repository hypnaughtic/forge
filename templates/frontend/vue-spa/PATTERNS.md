# Vue SPA Patterns

> These patterns describe architectural decisions for the Vue SPA template. No implementation is provided in this stub.

## 1. Composables for Reusable Logic

**WHY:** Vue 3's Composition API enables extracting stateful logic into reusable composable functions (useAuth, useFetch, useForm). Unlike mixins, composables have explicit inputs and outputs, avoid naming collisions, and provide full TypeScript inference -- making shared logic transparent and type-safe.

## 2. Route-Level Code Splitting

**WHY:** Bundling the entire application into a single file forces users to download code for pages they may never visit. Dynamic imports at the route level create separate chunks loaded on demand, dramatically improving initial load time while keeping navigation seamless after the first visit.

## 3. Pinia Store Composition

**WHY:** Pinia stores can reference each other, enabling composition of small, focused stores rather than a monolithic state tree. This keeps each store independently testable, avoids circular coupling, and makes it clear which parts of the UI depend on which slices of state.

## 4. Render-Layer and Logic-Layer Separation

**WHY:** Separating presentational components (pure rendering, props-driven) from container components (data fetching, store interaction) makes the UI testable without mocking API calls. Presentational components can be developed in isolation using Storybook or Histoire, speeding up design iteration.

## 5. API Layer Abstraction

**WHY:** Centralizing HTTP calls behind a typed API layer prevents fetch logic from scattering across components. When the backend contract changes, updates happen in one place. Interceptors in this layer handle token refresh, error normalization, and retry logic consistently.
