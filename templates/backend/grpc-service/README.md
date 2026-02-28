# gRPC Service Template (STUB)

> **Status:** Stub template -- not yet scaffolded. This document describes what a full implementation would provide.

## Overview

A production-ready gRPC service with Protocol Buffer definitions, support for unary and streaming RPCs, health check protocols, and reflection for service discovery. Available in Go, Python, and TypeScript.

## What a Full Scaffold Would Provide

- **Protobuf schema definitions** with versioned API contracts
- **Code generation pipeline** for server stubs and client libraries
- **Unary and streaming RPC** implementations (server, client, and bidirectional streaming)
- **gRPC health checking** protocol (grpc.health.v1) for load balancer integration
- **Reflection service** for dynamic service discovery and debugging with grpcurl
- **Interceptors/middleware** for logging, authentication, and distributed tracing
- **Deadline propagation** and cancellation handling
- **Error handling** with gRPC status codes and rich error details
- **TLS configuration** for secure transport
- **Load testing** setup with ghz or similar tools
- **Proto linting** with buf for schema quality enforcement
- **Docker packaging** with health check support

## Key Technologies

| Component       | Go            | Python         | TypeScript      |
|----------------|---------------|----------------|-----------------|
| gRPC Framework  | google.golang.org/grpc | grpcio  | @grpc/grpc-js   |
| Proto Tooling   | buf           | buf            | buf             |
| Health Check    | grpc-health   | grpc-health    | grpc-health     |
