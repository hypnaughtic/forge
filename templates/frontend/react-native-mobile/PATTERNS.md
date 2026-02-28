# React Native Mobile Patterns

> These patterns describe architectural decisions for the React Native mobile template. No implementation is provided in this stub.

## 1. Expo Managed Workflow with Ejection Path

**WHY:** The managed workflow eliminates native build toolchain complexity during early development, letting teams focus on features. Expo's config plugins allow limited native customization without ejecting, and a clear ejection path ensures the app can adopt custom native modules when requirements demand it.

## 2. Optimistic UI with TanStack Query

**WHY:** Mobile users expect instant feedback. Optimistic updates modify the UI immediately while the network request proceeds in the background, with automatic rollback on failure. TanStack Query's mutation/invalidation model makes this pattern straightforward while keeping cache consistency.

## 3. Platform-Adaptive Component Abstraction

**WHY:** iOS and Android have different UX conventions (navigation patterns, gestures, system UI). Abstracting platform differences behind a shared component interface lets feature code remain platform-agnostic while each platform renders its native-feeling experience.

## 4. Secure Token Storage

**WHY:** Mobile apps cannot rely on httpOnly cookies for auth tokens. Storing tokens in the platform keychain (via expo-secure-store) prevents them from being extracted by other apps or exposed in backups, which is critical for user security on shared or compromised devices.

## 5. Offline-First Data Strategy

**WHY:** Mobile devices frequently lose connectivity. Designing data access to read from local cache first and sync when connectivity returns ensures the app remains functional in elevators, subways, and rural areas -- which dramatically improves perceived reliability.
