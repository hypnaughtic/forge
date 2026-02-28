# Go Microservice Patterns

> These patterns describe architectural decisions for the Go microservice template. No implementation is provided in this stub.

## 1. Clean Architecture (Hexagonal / Ports & Adapters)

**WHY:** Separating domain logic from infrastructure concerns (database, HTTP, external services) makes the codebase testable in isolation and allows swapping implementations without touching business rules. The domain layer has zero external dependencies, ensuring that Go interface satisfaction drives decoupling naturally.

## 2. Repository Pattern with GORM

**WHY:** Abstracting database access behind repository interfaces prevents ORM details from leaking into business logic. This allows unit-testing use cases with in-memory fakes and makes it straightforward to switch from PostgreSQL to another store without rewriting domain code.

## 3. Docker Multi-Stage Build

**WHY:** Go produces static binaries, so a multi-stage build compiles in a full Go image and copies the binary into a scratch or distroless image. This reduces container size from hundreds of megabytes to under 20 MB, shrinking the attack surface and speeding up deployments.

## 4. Graceful Shutdown with Context Propagation

**WHY:** Production services must drain in-flight requests before exiting. Using Go's context package to propagate cancellation from OS signals through the HTTP server and into database calls ensures no request is silently dropped during rolling deployments.

## 5. Structured Logging with Correlation IDs

**WHY:** In a microservice environment, correlating logs across services is essential for debugging. Injecting a request ID at the middleware layer and threading it through the context allows every log line to be traced back to a single user request across distributed systems.
