# TideWindow Roadmap

Focus for this phase: **reliability and polish** — make the dashboard dependable and pleasant to live with day to day, before chasing new forecasting capabilities. Effort is sized roughly as S (a few hours), M (a day or two), L (multi-day).

## Where the project stands today

TideWindow already does a lot well. It aggregates NOAA tide and current observations plus optional OpenWeather wind, derives current strength from the tide slope for forecast windows, scores 8 default + 5 optional Gig Harbor zones for kayaking and fishing, and presents it through both a terminal UI and a web dashboard (Leaflet map, hourly timeline, best windows, zone cards). The data-source honesty — labeling tide/current/wind as live, derived, fallback, seed, or missing, and rolling that into a confidence level — is a genuine strength most hobby projects skip.

The gaps that matter most for reliability and polish are below.

## Review findings worth acting on

A few concrete observations from reading `noaa_client.py`, `marine_engine.py`, and `web_app.py`:

- **No server-side caching.** Every `GET /api/state` triggers fresh NOAA + OpenWeather calls (4–6s timeouts), and the browser auto-refreshes every 5 minutes. Each tab, reload, and user multiplies upstream calls. A slow or rate-limited provider directly degrades the page. This is the single biggest reliability risk.
- **Failure drops straight to static seed.** When NOAA blips, the app serves fixed `SEEDED_*` constants and shows "Seed data active." There's no memory of the last *good* reading, so a 30-second outage makes the dashboard look broken rather than slightly stale.
- **The current station may never return live data — worth verifying.** `fetch_telemetry` calls the NOAA `currents` (real-time) product against `PCT1601`, which is a current *prediction* station. Real-time `currents` data generally comes from stations with a deployed sensor. If `PCT1601` returns an empty payload, "Current: live" silently falls back to seed on every load. Confirm with a one-off API call; if confirmed, switch to the `currents_predictions` product.
- **Scoring thresholds are a hardcoded if/elif ladder.** `evaluate_kayaking` / `evaluate_fly_fishing` bake per-zone numbers into ~250 lines of branching. It works, but it blocks personalization, makes the rules hard to test in isolation, and is error-prone to edit.
- **Minor housekeeping.** `APP_VERSION` is hardcoded to `0.1.0`; several `*.py.bak` files sit in the working tree; the web/API layer has lighter test coverage than the engine.

## Now — reliability foundation

1. **Server-side cache with TTL + stale-while-revalidate (M).** Cache the assembled `/api/state` payload for ~`refresh_seconds`. Serve cached data instantly and refresh upstream in the background; if upstream fails, keep serving the last good payload. Decouples user-facing speed from NOAA/OpenWeather latency and protects against rate limits. Highest-leverage item.
2. **Persist and serve last-good data instead of seed (M).** Remember the last successful telemetry/forecast in memory (and optionally on disk). On upstream failure, return it with an "as of HH:MM (N min ago)" age label and a degraded-but-not-broken state. Big jump in perceived reliability over the current seed fallback.
3. **Surface data age in the UI (S).** The redesigned summary panel has room — show how old each reading is. Turns the existing source labels into something actionable ("current is 18 min old").
4. **Verify the current-station data path and fix if needed (S).** Resolve the `PCT1601` question above so "live current" means what it says.
5. **Add web/API + caching tests (M).** Extend `tests/` to cover `/api/state` serialization, the cache TTL behavior, and the last-good fallback. Locks reliability in so future changes don't regress it.

## Next — polish and everyday usefulness

6. **Installable PWA with offline last-state (M).** Add a manifest + service worker that caches the shell and the last `/api/state`. This is a phone-on-the-dock app; opening it with no signal and seeing the last forecast is a real quality-of-life win.
7. **High/low tide + slack table (S–M).** Surface next high, next low, and slack times. NOAA predictions support `interval=hilo` directly. Core planning info that the hourly curve only implies today.
8. **Multi-day "this weekend" view (M).** Extend `FORECAST_HOURS` beyond 24 and group the timeline by day so weekend planning doesn't require refreshing tomorrow. Pairs naturally with the best-windows panel.
9. **Daylight shading on the timeline (S).** OpenWeather One Call already returns sunrise/sunset (currently excluded from the request). Shade non-daylight hours and flag golden hour — useful for both safe paddling and dawn/dusk fishing, cheap to add.
10. **Daily best-window digest (M).** A "tomorrow's best window" summary, generated on a schedule. Could be a simple endpoint/email or wired to an external scheduler; turns the app from pull-only into something that tells you when to go.

## Later — accuracy and reach

11. **Real NOAA current predictions (M).** Replace the tide-slope-derived current with the station's published current predictions, upgrading forecast windows from "derived" to "live" confidence.
12. **Wind-direction-aware exposure scoring (M–L).** Score each zone against wind *direction* relative to its fetch, not just speed — likely the largest single accuracy gain. OpenWeather already provides `wind_deg`.
13. **NWS marine advisories (M).** Pull small-craft advisories / marine warnings for the Puget Sound zone and show them prominently. A real safety layer the app currently lacks.
14. **Config-driven thresholds + personalization (M).** Move the scoring thresholds out of the engine into `marine_config` per zone, then add a conservative/standard/aggressive risk-tolerance toggle that scales them. Cleaner, testable, and unlocks per-user tuning.
15. **Generalize beyond Gig Harbor (L).** If reach ever becomes the goal: parameterize stations/zones by region so the app isn't hardwired to one basin.

## Suggested starting point

If you want the fastest path to a dashboard that feels rock-solid: do **#1 (caching), #2 (last-good data), and #3 (data age)** together as one reliability pass, then **#4** to confirm the current data is real. That sequence removes the "seed data" failure mode that's most likely to undercut trust, and it's all server-side — no changes to the freshly redesigned frontend beyond a small age label.
