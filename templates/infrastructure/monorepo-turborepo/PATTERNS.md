# Monorepo Turborepo Patterns

> These patterns describe architectural decisions for the monorepo Turborepo template. No implementation is provided in this stub.

## 1. Task Pipeline with Topological Ordering

**WHY:** In a monorepo, packages depend on each other. Building a package before its dependencies are built produces errors. Turborepo's pipeline configuration declares task dependencies (build depends on ^build), and the engine executes tasks in topological order with maximum parallelism. This is faster than sequential builds and more correct than manual ordering.

## 2. Remote Caching for CI Acceleration

**WHY:** CI pipelines rebuild every package on every commit, even when most packages have not changed. Turborepo's remote cache stores task outputs (build artifacts, test results, lint results) keyed by input hash. When inputs have not changed, the cache provides instant results, reducing CI times from 20 minutes to 2 minutes for typical changes.

## 3. Shared Configuration Packages

**WHY:** Duplicating ESLint, TypeScript, and Prettier configurations across packages leads to inconsistency and painful upgrades. Publishing these as internal packages (e.g., @repo/eslint-config, @repo/typescript-config) means every package extends a single source of truth. Updating the config package propagates changes to all consumers automatically.

## 4. Internal Packages with TypeScript Project References

**WHY:** Internal packages that publish compiled JavaScript add a build step to the development loop. TypeScript project references allow consuming packages to import directly from source (TypeScript files) with full type checking, enabling instant feedback during development while still producing optimized builds for production.

## 5. Pruned Docker Builds

**WHY:** Docker builds in a monorepo without pruning copy the entire workspace into the container, producing bloated images with code for unrelated packages. Turborepo's prune command generates a minimal workspace containing only the target package and its dependencies, creating focused Docker images that are fast to build and small to deploy.
