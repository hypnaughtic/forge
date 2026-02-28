# React SPA — Architectural Patterns

This document explains the patterns used in this template and **why** each
one was chosen. Use this as a guide when extending the application.

---

## 1. Component Composition over Inheritance

**What:** UI is built by composing small, focused components rather than
creating deep inheritance hierarchies. Components accept `children` and
render props to remain flexible.

**Why this pattern:**

- **Reusability** — Small components can be combined in many ways. A `Card`
  component does not need to know whether it wraps a user profile or a
  product listing.
- **Readability** — Each component has a single responsibility. Reading the
  component tree in JSX tells you exactly what the page does.
- **Testing** — Small components with clear inputs (props) and outputs (JSX)
  are straightforward to test in isolation.
- **React alignment** — Composition is React's fundamental model. Fighting
  it with inheritance leads to brittle, hard-to-maintain code.

---

## 2. Custom Hooks for Logic Extraction

**What:** Stateful logic (API calls, form handling, auth checks) is extracted
into custom hooks (`useAuth`, `useFetch`, `useForm`) that can be reused
across components.

**Why this pattern:**

- **Separation of concerns** — Components handle rendering; hooks handle
  logic. Neither is burdened with the other's responsibilities.
- **Reuse without wrapper hell** — Before hooks, sharing logic required
  higher-order components or render props, creating deeply nested component
  trees. Hooks flatten this.
- **Testability** — Hooks can be tested independently using
  `renderHook()` from testing-library, without mounting full components.
- **Colocation** — Related state and effects live together in one hook
  rather than being scattered across lifecycle methods.

---

## 3. API Client Abstraction

**What:** All HTTP communication goes through an abstract `ApiClient` class
in `src/api/client.ts`. Components never call `fetch` or `axios` directly.

**Why this pattern:**

- **Single configuration point** — Base URL, auth headers, error handling,
  and retry logic are configured once, not duplicated across every component.
- **Backend independence** — Swapping from REST to GraphQL or changing the
  base URL requires modifying one file.
- **Interceptors** — Auth token refresh, request logging, and error
  normalization happen in the client layer, invisible to consumers.
- **Testability** — The API client can be mocked at the module level,
  making component tests fast and deterministic.

---

## 4. Route-Based Code Splitting

**What:** Each page-level component is loaded with `React.lazy()` and
wrapped in `<Suspense>`, so the browser only downloads the code for the
page the user is visiting.

**Why this pattern:**

- **Faster initial load** — The main bundle contains only the shell and
  the first page. Other pages load on demand.
- **Proportional cost** — As the application grows, adding pages does not
  increase the initial bundle size.
- **Built-in support** — React and Vite handle lazy loading and chunk
  splitting natively. No extra libraries required.
- **User experience** — A `<Suspense>` fallback shows a loading indicator
  during chunk downloads, keeping the UI responsive.

---

## 5. Tailwind CSS for Styling

**What:** Styling uses Tailwind utility classes directly in JSX rather than
separate CSS files or CSS-in-JS libraries.

**Why this pattern:**

- **No naming overhead** — No need to invent class names or manage CSS
  module scoping. Utility classes describe what they do.
- **Dead code elimination** — Tailwind's purge step removes unused styles,
  keeping the production CSS bundle minimal.
- **Consistency** — Tailwind's design tokens (spacing scale, color palette,
  breakpoints) enforce visual consistency across the application.
- **Performance** — No runtime style computation. All styles are static CSS
  resolved at build time.

---

## 6. Environment Configuration via Vite

**What:** Environment variables are defined in `.env` files and accessed
via `import.meta.env.VITE_*` in application code.

**Why this pattern:**

- **Build-time safety** — Vite injects env vars at build time. Only
  `VITE_`-prefixed variables are exposed, preventing accidental leaks of
  server-side secrets.
- **Environment parity** — `.env.development`, `.env.production`, and
  `.env.local` allow per-environment configuration without code changes.
- **Type safety** — Env vars can be typed via `vite-env.d.ts`, catching
  typos at compile time.
