# TideWindow PWA and Offline QA

_Last checked: 2026-06-12._

## Scope

This pass verified the install/offline foundation in a mobile browser context:

- Manifest link is present on the web dashboard.
- iOS web-app metadata is present.
- Service worker controls the loaded page after reload.
- Service worker cache version is current.
- Mobile layout at 390px wide has no horizontal overflow.
- Offline browser reload serves the TideWindow app shell from the service worker.

## Result

Passed in local Playwright mobile emulation against `http://127.0.0.1:8765`.

- Viewport: `390 x 844`
- Service worker controlled page: yes
- Offline reload returned app shell: yes
- Digest section visible offline shell: yes
- Horizontal overflow: none
- Manifest description: regional Puget Sound wording

## Remaining Real-Device Checks

Before public launch, verify on physical devices:

- iOS Safari Add to Home Screen icon rendering.
- Android Chrome install prompt behavior.
- Offline behavior after killing and reopening the installed app.
- Map-tile behavior when offline, since third-party map tiles are not guaranteed to be cached.
