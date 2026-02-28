# gRPC Service Patterns

> These patterns describe architectural decisions for the gRPC service template. No implementation is provided in this stub.

## 1. Contract-First API Design with Protobuf

**WHY:** Defining services in .proto files before writing code creates an unambiguous, language-neutral contract. Code generation from these contracts eliminates serialization bugs, provides compile-time type safety across languages, and ensures backward compatibility can be validated mechanically with tools like buf breaking.

## 2. Interceptor Chain (Middleware Pattern)

**WHY:** gRPC interceptors provide a composable way to add cross-cutting concerns (auth, logging, tracing, rate limiting) without modifying individual RPC handlers. This keeps handler code focused on business logic while ensuring every request passes through consistent infrastructure.

## 3. Streaming with Backpressure

**WHY:** gRPC's HTTP/2-based streaming naturally supports flow control, preventing fast producers from overwhelming slow consumers. Using server streaming for large result sets and bidirectional streaming for real-time communication avoids the overhead of polling or long-lived HTTP connections.

## 4. Health Check Protocol (grpc.health.v1)

**WHY:** The standardized gRPC health check protocol allows load balancers and orchestrators (Kubernetes, Envoy) to determine service readiness without custom endpoints. Implementing per-service health status enables granular dependency checking rather than binary up/down signals.

## 5. Deadline Propagation

**WHY:** In microservice chains, a deadline set by the originating client must be propagated through every downstream call. Without this, a slow downstream service can cause upstream services to hold resources long after the client has given up, wasting capacity across the entire system.
