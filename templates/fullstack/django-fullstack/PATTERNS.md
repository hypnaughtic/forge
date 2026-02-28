# Django Fullstack Patterns

> These patterns describe architectural decisions for the Django fullstack template. No implementation is provided in this stub.

## 1. Fat Models, Thin Views

**WHY:** Placing business logic in model methods and managers rather than in views keeps logic reusable across API endpoints, admin actions, management commands, and Celery tasks. Views become simple dispatchers that validate input and call model methods, making them easy to test and replace.

## 2. Celery Task Idempotency

**WHY:** Celery tasks may be retried due to worker crashes, broker issues, or timeouts. Designing every task to be idempotent (safe to run multiple times with the same arguments) prevents duplicate charges, duplicate emails, and data corruption. This is achieved through database-level unique constraints and conditional state transitions.

## 3. Settings Module Split by Environment

**WHY:** A single settings.py that tries to handle development, testing, staging, and production with conditionals becomes unmaintainable. Splitting into base, development, testing, and production modules keeps each environment's configuration explicit, avoids debug-mode-in-production accidents, and makes it obvious which settings differ between environments.

## 4. DRF Serializer Layering

**WHY:** Using separate serializers for list, detail, create, and update operations prevents over-fetching and under-validation. List serializers return minimal fields for performance, detail serializers include nested relationships, and write serializers enforce strict validation -- all sharing a common base to avoid duplication.

## 5. Signal-Free Architecture

**WHY:** Django signals (post_save, pre_delete) create invisible coupling between models, making the codebase harder to debug and reason about. Explicitly calling service functions from views and tasks keeps the execution path visible and testable, avoiding the "action at a distance" problem signals introduce.
