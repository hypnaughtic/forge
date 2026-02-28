# Pulumi Multi-Cloud Patterns

> These patterns describe architectural decisions for the Pulumi multi-cloud template. No implementation is provided in this stub.

## 1. Component Resources for Reusable Abstractions

**WHY:** Cloud resources rarely exist in isolation -- a "service" involves compute, networking, IAM, monitoring, and DNS. Pulumi component resources group related resources into a single logical unit with a typed interface. This enables expressing infrastructure as high-level concepts ("deploy a service") rather than low-level resource declarations, dramatically reducing configuration complexity.

## 2. Real Language Testing with Mocked Providers

**WHY:** Infrastructure code is rarely tested because HCL lacks a native testing story. Pulumi programs are real TypeScript/Python, so standard testing frameworks (Jest, pytest) can validate infrastructure logic with mocked providers. Unit tests verify resource creation, naming, and configuration without provisioning real cloud resources.

## 3. Stack-Per-Environment with Shared Program

**WHY:** Each environment (dev, staging, production) runs the same Pulumi program with different stack configuration. This ensures infrastructure parity while allowing environment-specific sizing. Unlike Terraform workspaces, Pulumi stacks have isolated state and configuration, preventing accidental cross-environment operations.

## 4. Policy as Code with CrossGuard

**WHY:** Security and compliance rules (no public S3 buckets, encryption at rest required, approved instance types only) are traditionally enforced by manual review. CrossGuard policies run automatically during `pulumi preview`, blocking non-compliant resources before they are created. This shifts compliance left into the development workflow.

## 5. Multi-Cloud Abstraction Layer

**WHY:** While multi-cloud is often premature, some organizations genuinely deploy across providers. A thin abstraction layer that maps high-level concepts (object storage, managed database, container orchestration) to provider-specific resources allows workloads to be deployed to any cloud with configuration changes rather than rewrites.
