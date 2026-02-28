# Kubernetes Helm Charts Patterns

> These patterns describe architectural decisions for the Kubernetes Helm charts template. No implementation is provided in this stub.

## 1. Library Chart for DRY Templates

**WHY:** Every microservice needs the same boilerplate (deployment, service, ingress, HPA). Copy-pasting these templates across charts leads to drift and inconsistent configuration. A library chart defines reusable template functions that application charts call, ensuring every service gets the same production-hardened configuration while only specifying what differs.

## 2. Values Hierarchy with Environment Overrides

**WHY:** Helm's default values.yaml works for a single environment but does not scale. Using a base values file with per-environment overrides (values-dev.yaml, values-prod.yaml) merged at deploy time keeps common configuration in one place while allowing environment-specific tuning (replica counts, resource limits, feature flags).

## 3. Resource Limits as Required Values

**WHY:** Kubernetes pods without resource limits can consume unbounded CPU and memory, destabilizing the entire node. Making resource requests and limits required chart values (with sensible defaults) ensures every deployment is resource-bounded. This prevents noisy-neighbor problems and enables the cluster autoscaler to make accurate scaling decisions.

## 4. GitOps-Ready Chart Structure

**WHY:** Manual `helm install` commands are unauditable and unreproducible. Structuring charts and values for GitOps tools (ArgoCD Application manifests, Flux HelmRelease CRDs) ensures every deployment is triggered by a git commit, providing audit trails, rollback capability, and self-healing when cluster state drifts from the declared configuration.

## 5. External Secrets for Credential Management

**WHY:** Storing secrets in Helm values files or Kubernetes secrets in git is a security vulnerability. The external-secrets-operator syncs secrets from a vault (AWS Secrets Manager, HashiCorp Vault) into Kubernetes secrets at runtime, keeping credentials out of version control while making them available to pods through the standard Kubernetes secrets interface.
