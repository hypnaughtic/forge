# Flutter Mobile Patterns

> These patterns describe architectural decisions for the Flutter mobile template. No implementation is provided in this stub.

## 1. Riverpod for Dependency Injection and State

**WHY:** Riverpod provides compile-time safe dependency injection without relying on the widget tree (unlike Provider). Providers are globally accessible, independently testable via overrides, and automatically disposed when no longer observed -- eliminating an entire class of memory leak bugs common in Flutter apps.

## 2. Feature-First Project Structure

**WHY:** Organizing code by feature (auth/, profile/, settings/) rather than by layer (models/, views/, controllers/) keeps related files adjacent. This reduces cognitive load when working on a feature, makes features independently deletable, and scales better as the app grows beyond a dozen screens.

## 3. Immutable State with Freezed

**WHY:** Mutable state objects cause subtle bugs when references are shared across widgets. Freezed generates immutable data classes with copyWith, equality, and JSON serialization, making state transitions explicit and enabling reliable equality checks that Riverpod needs to avoid unnecessary rebuilds.

## 4. GoRouter Declarative Navigation

**WHY:** Imperative navigation (Navigator.push) scatters routing logic throughout the widget tree and makes deep linking difficult. GoRouter's declarative route definitions provide a single source of truth for navigation, support redirects for auth guards, and enable deep linking on all platforms with minimal configuration.

## 5. Repository Pattern with Offline Caching

**WHY:** Abstracting data sources behind repository interfaces lets the app seamlessly switch between network and local cache. When offline, the repository serves cached data transparently. This decoupling also enables testing business logic without network dependencies.
