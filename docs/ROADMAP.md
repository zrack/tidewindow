# TideWindow Roadmap

_Last updated: 2026-06-12._

Focus: **accuracy, personalization, and reach** — the reliability and everyday-usefulness foundation is now in place, so the next gains should make the recommendations more locally accurate and easier to tune. Effort is sized roughly as S (a few hours), M (a day or two), L (multi-day).

## Where the project stands today

TideWindow aggregates NOAA tide and current data plus optional OpenWeather wind, scores selectable regional spot catalogs for kayaking and fishing, and presents it through a terminal UI and a web dashboard (Leaflet map, mobile-friendly daily heatmap, best windows, tides/currents table, provider diagnostics, and risk tolerance). The data-source honesty — labeling tide/current/wind as live, predicted, derived, fallback, seed, or missing, and rolling that into confidence and provider-fit labels — remains a core strength.

The reliability foundation, safety banner, offline shell, multi-day planning view, regional selector/search, provider fallback execution, and mobile-first dashboard pass are now in place. What's left is proactive planning help, broader regional reach, and deeper spot review.

## Shipped

The full reliability phase and the first polish/safety/accuracy features are done:

- **Server-side cache with TTL + stale-while-revalidate** — `marine_cache.MarineStateCache`; reloads and tabs no longer each hit NOAA/OpenWeather. _(commit 4c0615c)_
- **Last-good fallback instead of seed** — a brief upstream outage serves the last real reading, not static seed. _(4c0615c)_
- **Data age in the UI** — the summary panel shows how old each reading is and flags "last good reading." _(4c0615c)_
- **Current-station fix** — `PCT1601` was an invalid station, so current was always seed. Switched to `PUG1527` (The Narrows, 0.3 mi N of bridge); telemetry now degrades tide and current independently, tries real-time → `currents_predictions` → seed, and labels the source honestly. Added `scripts/check_current_station.py` and `scripts/find_current_station.py`. _(5e3c708)_
- **Web/API + cache tests** — `/api/state` serialization, cache TTL hit, and the last-good degraded path. _(c7f368a)_
- **High/low tide + slack table** — a "Tides & Currents" panel showing upcoming highs/lows and slack/max flood-ebb from NOAA `hilo` and `MAX_SLACK`. _(d8faf16)_
- **Daylight shading** — `sun_times.py` computes sunrise/sunset locally (no API key); the planning timeline shades night and golden-hour cells with a sunrise–sunset caption. _(3a79dad)_
- **NWS marine advisories** — active Puget Sound marine alerts from the NWS API appear above the dashboard summary. _(df35a54)_
- **Multi-day planning view** — `FORECAST_HOURS` is 72, best-window counts are expanded, and the planning heatmap groups hours by day. _(df35a54)_
- **Installable PWA with offline last-state** — manifest + service worker cache the app shell and last `/api/state`. _(df35a54)_
- **NOAA predicted current in forecast windows** — best-window and timeline scoring now prefer NOAA `currents_predictions`; tide-slope-derived current remains the fallback. _(be93ef8)_
- **Confidence downgrade for stale last-good data** — source age still shows the detail, and the confidence note now reflects last-good staleness. _(be93ef8)_
- **Provider diagnostics panel** — the web dashboard and `/health` now expose each selected region's tide station, current station, current bin/depth, station type, and provider confidence. _(45073b5)_
- **Wind-direction-aware exposure scoring** — OpenWeather wind direction is carried into telemetry/forecast scoring, and modeled spots adjust effective wind by exposed, partial, or sheltered fetch. _(f8232c0)_
- **Regional place selector expansion** — Gig Harbor, Port Orchard, Bremerton, Silverdale, Tacoma Narrows, Carr Inlet, Case Inlet, Anderson Island, Steilacoom & Nisqually, Olympia & Budd Inlet, South Hood Canal, and Aberdeen now have selectable catalogs, all-spots-by-default map fitting, and region-scoped NOAA/OpenWeather provider context with explicit current bins. Chico and Gorst remain nearby spot references, not selectable regions, until they have station-quality provider context. _(825303b, e259d78, 0de8590, 75d83df, ceea9d8, 8dda6c5)_
- **Provider fallback strategies** — each region now carries tide/current priority lists, a derived-current fallback, more specific confidence labels, and special sparse-current / river-bar warnings for South Hood Canal and Aberdeen. _(64fd49a)_
- **Regional wind-exposure metadata** — newer regional spots now carry shoreline-family `wind_exposure_bearing` metadata, so wind-direction-aware scoring applies beyond the original Gig Harbor zones. _(367a864)_
- **Config-driven thresholds + risk tolerance** — kayaking/fishing thresholds now live in structured config with standard parity tests, generic regional profiles, and conservative/standard/aggressive risk tolerance selection in the web app. _(8075778)_
- **Mobile dashboard polish** — the mobile web app now uses a compact sticky header, tighter summary cards, a clearer map control row, a scrollable daily heatmap, and larger map marker tap targets. _(8979cfd)_
- **Daily heatmap planning view** — the hourly card wall has been replaced by a compact day-by-day heatmap with selected-hour detail, and the All/Kayak/Fish filter now drives the heatmap marks and color coding consistently with the map and windows.
- **Provider fallback execution** — NOAA tide/current fetches now try configured station candidates in priority order, record the active station source, and keep derived current as the final fallback.
- **Reviewed spot exposure bearings** — high-use regional spots now carry reviewed spot-specific wind-exposure bearings while the rest continue to use shoreline-family defaults.
- **Risk/threshold detail polish** — the active conservative/standard/aggressive risk profile is now shown in heatmap details, map popups, and full spot details.
- **Proportional map density controls** — region maps default to Full, with Compact and Standard presets showing about 50% and 75% of the regional spot catalog instead of fixed Fewer/More count steps.
- **Regional search/autocomplete** — the fixed region dropdown has been replaced by a place search backed by region aliases, city names, common launch names, and marine-area terms. Nearby recognized places such as Belfair, Union, Chico, and Gorst resolve to the closest supported region with a visible note.
- **Tomorrow's Best digest** — the web app now surfaces the best kayak and fish windows for tomorrow with spot, time, status, tide/current/wind, risk profile, and a short explanation.
- **PWA/offline mobile QA pass** — verified the manifest/app shell, service-worker control, 390px mobile layout, and offline reload behavior in a mobile browser context. Real iOS/Android install-prompt behavior still deserves a physical-device check before launch.

Earlier: the refined marine-dark UI redesign _(131c7dc)_ and this roadmap.

## Next — accuracy, personalization, and everyday usefulness

1. **Digest delivery options (M).** Add a way to save or receive the Tomorrow's Best digest, such as a daily email, SMS, push notification, or shareable summary link.
2. **Physical-device PWA install QA (S).** Verify install prompt behavior, home-screen icon rendering, and offline behavior on actual iOS and Android devices.
3. **Continue spot-level exposure review (M).** Expand the reviewed bearing table as local knowledge improves, especially for exposed launches and bar/river-influenced areas.
4. **Search ranking refinements (S-M).** The alias search is exact-match first; later, add typo tolerance, partial-match ranking, and richer unsupported-place routing when the catalog grows.

## Later — accuracy and reach

7. **Broader Puget Sound reach (L).** Add Central Sound, Bainbridge/Kingston, Vashon/Maury, North Hood Canal, and San Juan/Whidbey candidates after their provider contexts are reviewed.

## Housekeeping

- Keep `APP_VERSION`, README feature text, and this roadmap in sync as features land.
- Replace dated static query strings (`?v=...`) whenever frontend assets change, or move to an app-version constant/template if the app grows.

## Suggested next step

**#1 (digest delivery options)** is now the best next usefulness gain. The app can summarize tomorrow's best windows; the next step is letting users receive or share that summary without opening the dashboard first.
