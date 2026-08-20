# Changelog

Notable project changes are listed here in reverse chronological order. This project is still pre-1.0, so entries are grouped by product milestone rather than formal releases.

## Current

- Reworked the README visual story with a map-first TideWindow infographic and refreshed desktop/mobile dashboard screenshots.
- Added launch-readiness and station-quality review checklists, local launch/provider checker scripts, refreshed the roadmap around launch blockers versus next product work, and retired stale regional planning guidance.
- Ran production-style local scheduler/admin/PWA launch QA, fixed mobile admin overflow, bumped PWA shell assets, and lazy-loaded the NOAA client for admin/scheduler startup.
- Added token guards for digest admin operations and hosted scheduler runs, plus an admin unlock flow for production use.
- Added a digest operations admin view with delivery health, scheduler readiness, saved preference controls, send-test actions, and audit review.
- Hardened daily digest delivery with signed unsubscribe links, delivery/test/unsubscribe audit records, scheduler run ids, duplicate-run locking, and deployment documentation.
- Added daily digest delivery MVP with saved preferences, local outbox email fallback, optional SMTP sender, due-delivery endpoint, opt-in UI, and delivery smoke scripts.
- Added shareable Tomorrow's Best digest exports: `/digest`, filtered `/api/digest`, `.ics` calendar export, copy/share actions, and refreshed docs/screenshots. _(9f5ba3c)_
- Added Tomorrow's Best recommendations for the next day with spot, time, status, tide/current/wind, risk profile, and explanation. _(2ebbd38)_
- Replaced the fixed region dropdown with place search/autocomplete backed by regions, aliases, city names, common launches, and marine-area terms. _(115fc13)_
- Changed map density controls from fixed counts to proportional Compact, Standard, and Full presets. _(0636cf8)_
- Executed provider fallback strategies in NOAA fetches, recorded active station sources, and polished the heatmap/risk/detail experience. _(83d4d99)_
- Made region maps default to all spots instead of the earlier card-era 10-spot baseline. _(dcc5226)_
- Refreshed dashboard docs and screenshots after the regional/map work. _(7cce93f)_
- Polished the mobile dashboard layout, map controls, marker tap targets, and daily heatmap ergonomics. _(8979cfd)_

## Regional Planning Foundation

- Added configurable thresholds and conservative/standard/aggressive risk tolerance. _(8075778)_
- Added regional wind-exposure bearings and reviewed spot-specific bearings for high-use locations. _(367a864)_
- Added provider fallback strategies, confidence labels, and region caveats. _(64fd49a)_
- Added South Hood Canal and Aberdeen regions. _(8dda6c5)_
- Added wind-direction-aware exposure scoring. _(f8232c0)_
- Added provider diagnostics for station fit, station/bin/depth, and provider context. _(45073b5)_
- Added South Sound regions and current bins. _(ceea9d8)_
- Skipped Chico and Gorst as selectable regions until they have station-quality provider context. _(75d83df)_
- Added Kitsap regional spot catalogs. _(0de8590)_
- Added regional spot controls and all-spots map fitting. _(e259d78)_
- Added the first Gig Harbor region spot model. _(825303b)_
- Clarified the city-based regional spot selection brief. _(d36d0d6)_

## Reliability, Forecasting, And PWA

- Added NOAA predicted currents to forecast windows and timeline scoring. _(be93ef8)_
- Added source confidence downgrade for stale last-good data. _(be93ef8)_
- Added active NWS marine advisories. _(df35a54)_
- Expanded planning to 72 hours and grouped the planning timeline by day. _(df35a54)_
- Added installable PWA shell and offline last-state behavior. _(df35a54)_
- Added local sunrise/sunset calculation and daylight/golden-hour timeline shading. _(3a79dad)_
- Added high/low tide and slack/max current event tables. _(d8faf16)_
- Added web/API cache tests for state serialization, cache TTL, and last-good degraded paths. _(c7f368a)_
- Fixed the invalid current station fallback path and switched to a valid Tacoma Narrows current station. _(5e3c708)_
- Added server-side cache with TTL plus stale-while-revalidate behavior. _(4c0615c)_
- Served last-good data during brief upstream outages instead of falling back directly to static seed data. _(4c0615c)_
- Added data-age and last-good labels in the UI. _(4c0615c)_

## Early UI

- Refined the marine-dark web dashboard UI. _(131c7dc)_
