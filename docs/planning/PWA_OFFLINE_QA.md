# TideWindow PWA and Offline QA

_Last checked: 2026-06-27._

## Scope

This pass verified the install/offline foundation in a mobile browser context:

- Manifest link is present on the web dashboard.
- iOS web-app metadata is present.
- Service worker cache version is current and includes the app, digest, unsubscribe, admin, manifest, and icon shell assets.
- Mobile layout at 390px wide has no horizontal overflow across the dashboard, digest, unsubscribe, locked admin, and unlocked admin routes.
- Admin unlock strips `admin_token` from the URL after storing the session token.
- Offline shell behavior remains covered by the previous Playwright pass; this Browser-plugin pass could not toggle a true installed-device offline state.

## Result

Passed in local mobile browser QA against `http://localhost:8770` with production-style admin and scheduler tokens configured.

- Viewport: `390 x 844`
- Dashboard route: no overflow; manifest and iOS metadata present; Area Map and Tomorrow's Best visible.
- Digest route: no overflow; manifest and iOS metadata present.
- Unsubscribe route: no overflow.
- Admin route, locked and unlocked: no overflow after the admin grid responsive fix.
- Asset version: `pwa-launch-20260627`
- Service worker cache: `tidewindow-v31`
- Manifest description: regional Puget Sound wording

The same browser profile still had older `127.0.0.1` shell assets cached from a prior pass. A clean origin loaded the current files correctly, which confirms the new service worker/cache bump is necessary before installed-device testing.

## Remaining Real-Device Checks

Before public launch, verify on physical devices and the hosted origin:

- iOS Safari Add to Home Screen icon rendering.
- Android Chrome install prompt behavior.
- Offline behavior after killing and reopening the installed app.
- Map-tile behavior when offline, since third-party map tiles are not guaranteed to be cached.
- Upgrade behavior from an older installed shell to `tidewindow-v31`.
