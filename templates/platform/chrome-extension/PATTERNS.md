# Chrome Extension Patterns

> These patterns describe architectural decisions for the Chrome extension template. No implementation is provided in this stub.

## 1. Service Worker Event-Driven Architecture

**WHY:** Manifest V3 replaces persistent background pages with service workers that are terminated when idle. Designing all background logic as event listeners (onInstalled, onMessage, onAlarm) ensures the extension works correctly when the service worker restarts. Storing state in chrome.storage rather than in-memory variables prevents data loss between wake cycles.

## 2. Message Passing Protocol with Typed Channels

**WHY:** Chrome extensions have multiple isolated contexts (service worker, content script, popup) that cannot share memory. A typed message passing protocol with discriminated unions ensures each context sends and receives well-defined messages, preventing the silent failures that occur when message shapes change in one context but not another.

## 3. Content Script Isolation with Shadow DOM

**WHY:** Content scripts share the page's DOM, meaning the extension's UI can be broken by the page's CSS or vice versa. Using Shadow DOM for injected UI elements creates a style boundary that prevents conflicts, ensuring the extension looks correct on every website regardless of the page's stylesheet.

## 4. Minimal Permissions with Optional Requests

**WHY:** Users distrust extensions that request broad permissions at install time. Declaring only essential permissions in the manifest and using chrome.permissions.request for optional features at the point of use increases install rates and builds user trust. The extension gracefully degrades when optional permissions are denied.

## 5. Offline-First with Background Sync

**WHY:** Extensions must function when the user is offline. Queuing actions locally and syncing when connectivity returns (using chrome.alarms for retry) ensures the extension remains useful in all network conditions and avoids confusing error states.
