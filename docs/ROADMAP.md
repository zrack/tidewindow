# TideWindow Roadmap

_Last updated: 2026-06-04._

Focus: **accuracy, personalization, and reach** — the reliability and everyday-usefulness foundation is now in place, so the next gains should make the recommendations more locally accurate and easier to tune. Effort is sized roughly as S (a few hours), M (a day or two), L (multi-day).

## Where the project stands today

TideWindow aggregates NOAA tide and current data plus optional OpenWeather wind, scores 8 default + 5 optional Gig Harbor zones for kayaking and fishing, and presents it through a terminal UI and a web dashboard (Leaflet map, hourly timeline, best windows, tides/currents table). The data-source honesty — labeling tide/current/wind as live, predicted, derived, fallback, seed, or missing, and rolling that into a confidence level — remains a core strength.

The reliability foundation, safety banner, offline shell, and multi-day planning view are now in place. What's left is accuracy work, personalization, and longer-term regionalization.

## Shipped

The full reliability phase and the first polish/safety/accuracy features are done:

- **Server-side cache with TTL + stale-while-revalidate** — `marine_cache.MarineStateCache`; reloads and tabs no longer each hit NOAA/OpenWeather. _(commit 4c0615c)_
- **Last-good fallback instead of seed** — a brief upstream outage serves the last real reading, not static seed. _(4c0615c)_
- **Data age in the UI** — the summary panel shows how old each reading is and flags "last good reading." _(4c0615c)_
- **Current-station fix** — `PCT1601` was an invalid station, so current was always seed. Switched to `PUG1527` (The Narrows, 0.3 mi N of bridge); telemetry now degrades tide and current independently, tries real-time → `currents_predictions` → seed, and labels the source honestly. Added `scripts/check_current_station.py` and `scripts/find_current_station.py`. _(5e3c708)_
- **Web/API + cache tests** — `/api/state` serialization, cache TTL hit, and the last-good degraded path. _(c7f368a)_
- **High/low tide + slack table** — a "Tides & Currents" panel showing upcoming highs/lows and slack/max flood-ebb from NOAA `hilo` and `MAX_SLACK`. _(d8faf16)_
- **Daylight shading** — `sun_times.py` computes sunrise/sunset locally (no API key); the timeline shades night and golden-hour cells with a sun/moon glyph and a sunrise–sunset caption. _(3a79dad)_
- **NWS marine advisories** — active Puget Sound marine alerts from the NWS API appear above the dashboard summary. _(df35a54)_
- **Multi-day planning view** — `FORECAST_HOURS` is 72, best-window counts are expanded, and the timeline groups hours by day. _(df35a54)_
- **Installable PWA with offline last-state** — manifest + service worker cache the app shell and last `/api/state`. _(df35a54)_
- **NOAA predicted current in forecast windows** — best-window and timeline scoring now prefer NOAA `currents_predictions`; tide-slope-derived current remains the fallback. _(current work)_
- **Confidence downgrade for stale last-good data** — source age still shows the detail, and the confidence note now reflects last-good staleness. _(current work)_
- **Provider diagnostics panel** — the web dashboard and `/health` now expose each selected region's tide station, current station, current bin/depth, station type, and provider confidence. _(45073b5)_
- **Wind-direction-aware exposure scoring** — OpenWeather wind direction is carried into telemetry/forecast scoring, and modeled spots adjust effective wind by exposed, partial, or sheltered fetch. _(f8232c0)_
- **Regional place selector expansion** — Gig Harbor, Port Orchard, Bremerton, Silverdale, Tacoma Narrows, Carr Inlet, Case Inlet, Anderson Island, Steilacoom & Nisqually, Olympia & Budd Inlet, South Hood Canal, and Aberdeen now have selectable catalogs, top-10 spot limits, map fitting, and region-scoped NOAA/OpenWeather provider context with explicit current bins. Chico and Gorst remain nearby spot references, not selectable regions, until they have station-quality provider context. _(current work)_
- **Provider fallback strategies** — each region now carries tide/current priority lists, a derived-current fallback, more specific confidence labels, and special sparse-current / river-bar warnings for South Hood Canal and Aberdeen. _(current work)_

Earlier: the refined marine-dark UI redesign _(131c7dc)_ and this roadmap.

## Next — accuracy, personalization, and everyday usefulness

1. **Spot-level exposure metadata expansion (M).** Add reviewed fetch bearings and local current notes to the newer regional catalogs so wind-direction scoring covers more than the original Gig Harbor zones.
2. **Config-driven thresholds + personalization (M).** Move scoring thresholds out of the long `evaluate_*` ladder into `marine_config`, then add a conservative/standard/aggressive risk-tolerance toggle.
3. **Provider fallback execution (M-L).** The metadata model exists; next, let regions define multiple usable station candidates that the fetcher can try in order before using derived current.
4. **Daily best-window digest (M).** A "tomorrow's best window" summary on a schedule — turns the app from pull-only into something that tells you when to go.
5. **PWA install/offline QA (S-M).** The PWA exists; the next pass should verify install prompts, iOS icon behavior, service-worker upgrades, and offline map/data behavior on a phone.

## Later — accuracy and reach

6. **Broader Puget Sound reach (L).** Add Central Sound, Bainbridge/Kingston, Vashon/Maury, and North Hood Canal after their provider contexts are reviewed.

## Housekeeping

- Keep `APP_VERSION`, README feature text, and this roadmap in sync as features land.
- Replace dated static query strings (`?v=...`) whenever frontend assets change, or move to an app-version constant/template if the app grows.

## Suggested next step

**#1 (spot-level exposure metadata expansion)** is now the biggest accuracy gain. Wind direction is wired through, but the newer regional catalogs need reviewed bearings and local notes so the scoring reads each shoreline more honestly.
