# SaaS Multi-Tenant Patterns

> These patterns describe architectural decisions for the SaaS multi-tenant template. No implementation is provided in this stub.

## 1. Row-Level Security for Tenant Isolation

**WHY:** Sharing a database across tenants is cost-effective but risks data leakage between tenants. PostgreSQL Row-Level Security (RLS) policies enforce tenant isolation at the database engine level, making it impossible for application bugs to accidentally query another tenant's data. This is a defense-in-depth measure that protects against the most dangerous class of multi-tenant bugs.

## 2. Stripe Webhook-Driven Billing State

**WHY:** Storing billing state based on Stripe API responses at checkout time leads to drift when subscriptions are modified externally (Stripe dashboard, dunning, disputes). Using webhooks as the authoritative source for billing state ensures the application always reflects Stripe's reality, handling edge cases like failed renewals and plan changes automatically.

## 3. Tenant-Scoped Middleware

**WHY:** Every request in a multi-tenant system must be scoped to a tenant. Middleware that extracts the tenant from the request (subdomain, header, JWT claim) and sets it in the request context ensures downstream code always operates within a tenant boundary. Forgetting to scope a query is the most common multi-tenant vulnerability, and middleware makes the default behavior safe.

## 4. Plan-Based Feature Gating

**WHY:** Different subscription tiers need different feature access. Implementing feature gates tied to the tenant's plan (not hardcoded boolean flags) means upgrading a plan automatically unlocks features. This decouples feature development from billing logic and supports instant plan changes without code deployment.

## 5. Audit Trail for Compliance

**WHY:** SaaS products serving business customers must demonstrate who did what and when. An append-only audit log capturing every significant action (with actor, tenant, resource, and timestamp) satisfies SOC 2 requirements and enables security investigations without the cost of retrofitting logging after the fact.
