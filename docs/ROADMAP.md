# TideWindow Roadmap

_Last updated: 2026-06-05._

Focus: **accuracy, personalization, and reach** — the reliability and everyday-usefulness foundation is now in place, so the next gains should make the recommendations more locally accurate and easier to tune. Effort is sized roughly as S (a few hours), M (a day or two), L (multi-day).

## Where the project stands today

TideWindow aggregates NOAA tide and current data plus optional OpenWeather wind, scores selectable regional spot catalogs for kayaking and fishing, and presents it through a terminal UI and a web dashboard (Leaflet map, mobile-friendly hourly timeline, best windows, tides/currents table, provider diagnostics, and risk tolerance). The data-source honesty — labeling tide/current/wind as live, predicted, derived, fallback, seed, or missing, and rolling that into confidence and provider-fit labels — remains a core strength.

The reliability foundation, safety banner, offline shell, multi-day planning view, regional selector, and mobile-first dashboard pass are now in place. What's left is deeper provider fallback execution, spot-level tuning, and broader regional reach.

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
- **NOAA predicted current in forecast windows** — best-window and timeline scoring now prefer NOAA `currents_predictions`; tide-slope-derived current remains the fallback. _(be93ef8)_
- **Confidence downgrade for stale last-good data** — source age still shows the detail, and the confidence note now reflects last-good staleness. _(be93ef8)_
- **Provider diagnostics panel** — the web dashboard and `/health` now expose each selected region's tide station, current station, current bin/depth, station type, and provider confidence. _(45073b5)_
- **Wind-direction-aware exposure scoring** — OpenWeather wind direction is carried into telemetry/forecast scoring, and modeled spots adjust effective wind by exposed, partial, or sheltered fetch. _(f8232c0)_
- **Regional place selector expansion** — Gig Harbor, Port Orchard, Bremerton, Silverdale, Tacoma Narrows, Carr Inlet, Case Inlet, Anderson Island, Steilacoom & Nisqually, Olympia & Budd Inlet, South Hood Canal, and Aberdeen now have selectable catalogs, all-spots-by-default map fitting, and region-scoped NOAA/OpenWeather provider context with explicit current bins. Chico and Gorst remain nearby spot references, not selectable regions, until they have station-quality provider context. _(825303b, e259d78, 0de8590, 75d83df, ceea9d8, 8dda6c5)_
- **Provider fallback strategies** — each region now carries tide/current priority lists, a derived-current fallback, more specific confidence labels, and special sparse-current / river-bar warnings for South Hood Canal and Aberdeen. _(64fd49a)_
- **Regional wind-exposure metadata** — newer regional spots now carry shoreline-family `wind_exposure_bearing` metadata, so wind-direction-aware scoring applies beyond the original Gig Harbor zones. _(367a864)_
- **Config-driven thresholds + risk tolerance** — kayaking/fishing thresholds now live in structured config with standard parity tests, generic regional profiles, and conservative/standard/aggressive risk tolerance selection in the web app. _(8075778)_
- **Mobile dashboard polish** — the mobile web app now uses a compact sticky header, tighter summary cards, a clearer fewer/count/more control row, a vertical hourly timeline, and larger map marker tap targets. _(8979cfd)_

Earlier: the refined marine-dark UI redesign _(131c7dc)_ and this roadmap.

## Next — accuracy, personalization, and everyday usefulness

1. **Provider fallback execution (M-L).** The metadata model exists; next, let regions define multiple usable station candidates that the fetcher can try in order before using derived current.
2. **Spot-level exposure refinement (M).** Replace shoreline-family bearings with spot-reviewed bearings where local knowledge says the default fetch direction is too broad.
3. **Threshold tuning UI/details (M).** Surface rule profile details per spot and add clearer copy showing how conservative/standard/aggressive shifts safety thresholds.
4. **Regional search/autocomplete (M-L).** Region choices are predefined today; next, let users search towns/launches and map those choices to the nearest supported region or future dynamic spot cluster.
5. **Daily best-window digest (M).** A "tomorrow's best window" summary on a schedule — turns the app from pull-only into something that tells you when to go.
6. **PWA install/offline QA (S-M).** The PWA exists; the next pass should verify install prompts, iOS icon behavior, service-worker upgrades, and offline map/data behavior on a phone.

## Later — accuracy and reach

7. **Broader Puget Sound reach (L).** Add Central Sound, Bainbridge/Kingston, Vashon/Maury, North Hood Canal, and San Juan/Whidbey candidates after their provider contexts are reviewed.

## Housekeeping

- Keep `APP_VERSION`, README feature text, and this roadmap in sync as features land.
- Replace dated static query strings (`?v=...`) whenever frontend assets change, or move to an app-version constant/template if the app grows.

## Suggested next step

**#1 (provider fallback execution)** is still the biggest accuracy gain. The metadata model can describe fallback priority; the fetcher should now use that priority before falling back to derived current.
