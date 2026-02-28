# GraphQL API Patterns

> These patterns describe architectural decisions for the GraphQL API template. No implementation is provided in this stub.

## 1. DataLoader Pattern for N+1 Prevention

**WHY:** GraphQL resolvers execute per-field, which naturally causes N+1 database queries when resolving lists of related entities. DataLoader batches these individual lookups into a single query per tick, turning O(N) database calls into O(1) without coupling resolvers to each other.

## 2. Schema-Driven Development

**WHY:** Defining the GraphQL schema as the contract between frontend and backend teams enables parallel development. The schema becomes the single source of truth for API capabilities, and type generation ensures both sides stay in sync without runtime surprises.

## 3. Cursor-Based Pagination (Relay Connection Spec)

**WHY:** Offset-based pagination breaks when data is inserted or deleted between pages. Cursor-based pagination provides stable, deterministic page boundaries that work correctly with real-time data and are cache-friendly for client-side stores.

## 4. Directive-Based Authorization

**WHY:** Declaring access control rules as schema directives (@auth, @hasRole) keeps authorization visible in the schema definition rather than buried in resolver logic. This makes security auditing straightforward and prevents developers from forgetting access checks on new fields.

## 5. Query Complexity Limiting

**WHY:** GraphQL's flexibility allows clients to craft deeply nested or extremely wide queries that can overwhelm the server. Assigning complexity costs to fields and rejecting queries exceeding a threshold protects the API from both accidental and malicious abuse.
