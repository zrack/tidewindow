# TideWindow Roadmap

_Last updated: 2026-06-03._

Focus: **reliability and polish** — make the dashboard dependable and pleasant to live with day to day, before chasing new forecasting capabilities. Effort is sized roughly as S (a few hours), M (a day or two), L (multi-day).

## Where the project stands today

TideWindow aggregates NOAA tide and current data plus optional OpenWeather wind, scores 8 default + 5 optional Gig Harbor zones for kayaking and fishing, and presents it through a terminal UI and a web dashboard (Leaflet map, hourly timeline, best windows, tides/currents table). The data-source honesty — labeling tide/current/wind as live, predicted, derived, fallback, seed, or missing, and rolling that into a confidence level — remains a core strength.

The reliability foundation is now in place, and the first polish features have shipped. What's left is additional polish, a safety layer, and longer-term accuracy work.

## Shipped

The full reliability phase plus two polish features are done:

- **Server-side cache with TTL + stale-while-revalidate** — `marine_cache.MarineStateCache`; reloads and tabs no longer each hit NOAA/OpenWeather. _(commit 4c0615c)_
- **Last-good fallback instead of seed** — a brief upstream outage serves the last real reading, not static seed. _(4c0615c)_
- **Data age in the UI** — the summary panel shows how old each reading is and flags "last good reading." _(4c0615c)_
- **Current-station fix** — `PCT1601` was an invalid station, so current was always seed. Switched to `PUG1527` (The Narrows, 0.3 mi N of bridge); telemetry now degrades tide and current independently, tries real-time → `currents_predictions` → seed, and labels the source honestly. Added `scripts/check_current_station.py` and `scripts/find_current_station.py`. _(5e3c708)_
- **Web/API + cache tests** — `/api/state` serialization, cache TTL hit, and the last-good degraded path. _(c7f368a)_
- **High/low tide + slack table** — a "Tides & Currents" panel showing upcoming highs/lows and slack/max flood-ebb from NOAA `hilo` and `MAX_SLACK`. _(d8faf16)_
- **Daylight shading** — `sun_times.py` computes sunrise/sunset locally (no API key); the timeline shades night and golden-hour cells with a sun/moon glyph and a sunrise–sunset caption. _(3a79dad)_

Earlier: the refined marine-dark UI redesign _(131c7dc)_ and this roadmap.

## Next — polish, safety, and everyday usefulness

1. **NWS marine advisories (M).** Pull small-craft advisories / marine warnings for the Puget Sound zone (NWS API) and show them prominently. The highest *safety* value remaining — the app currently surfaces no official advisories. Recommended next.
2. **Multi-day "this weekend" view (M).** Extend `FORECAST_HOURS` beyond 24 and group the timeline by day so weekend planning doesn't require waiting for tomorrow. Pairs naturally with the best-windows and daylight work already done.
3. **Installable PWA with offline last-state (M).** Add a manifest + service worker that caches the shell and the last `/api/state`. This is a phone-on-the-dock app; opening it with no signal and seeing the last forecast is a real quality-of-life win.
4. **Daily best-window digest (M).** A "tomorrow's best window" summary on a schedule — turns the app from pull-only into something that tells you when to go.

## Later — accuracy and reach

5. **Real current predictions in forecast windows (M).** Telemetry now uses NOAA current predictions, but the forecast windows still *derive* current from the tide slope. Feed real `currents_predictions` into the windows to upgrade them from "derived" to "predicted" confidence.
6. **Wind-direction-aware exposure scoring (M–L).** Score each zone against wind *direction* relative to its fetch, not just speed — likely the largest single accuracy gain. OpenWeather already provides `wind_deg`.
7. **Config-driven thresholds + personalization (M).** Move the scoring thresholds out of the ~250-line `evaluate_*` ladder in `marine_engine` into `marine_config` per zone, then add a conservative/standard/aggressive risk-tolerance toggle. Cleaner, testable, and unlocks per-user tuning.
8. **Generalize beyond Gig Harbor (L).** If reach ever becomes the goal: parameterize stations/zones by region so the app isn't hardwired to one basin.

## Housekeeping

- `APP_VERSION` is still hardcoded to `0.1.0` — bump it as features land.
- Several `*.py.bak` files remain in the working tree and could be removed.
- Confidence is still computed from source labels only; it shows "High/Medium" even when the cache is serving stale last-good data (the age badge signals staleness instead). A small follow-up could downgrade confidence when stale.

## Suggested next step

**#1 (NWS marine advisories)** adds the most genuine value now: it's the one safety layer the dashboard lacks, and it complements the planning data already shipped. After that, the "this weekend" view is the highest everyday-usefulness item.
