# TideWindow Roadmap

_Last updated: 2026-08-19._

This roadmap is forward-looking. Shipped history lives in the [changelog](../CHANGELOG.md).

## Product Direction

TideWindow already has the core planning foundation: regional spot catalogs, map-first exploration, 72-hour scoring, provider diagnostics, PWA/offline support, Tomorrow's Best, shareable digest export, hardened daily digest delivery, token-guarded scheduler runs, digest operations admin, and local launch-readiness QA for PWA/admin/scheduler paths.

The next phase should make the app launchable, then more locally accurate and easier to trust. Effort is sized roughly as S (a few hours), M (a day or two), L (multi-day), XL (larger product bet).

## Launch Blockers

1. **Physical-device PWA install QA (S).** Verify install prompt behavior, home-screen icon rendering, offline reopen behavior, map-tile failure behavior, and upgrade from an older installed shell on actual iOS and Android devices.
2. **Hosted SMTP and scheduler activation (S-M).** Set production email credentials and tokens, run the launch-readiness checklist, enable hosted cron, and monitor the first live audit records in `/admin`.
3. **First live digest acceptance pass (S).** Save a real preference, receive the scheduled email, open the digest, unsubscribe, and confirm the audit trail and duplicate-send guard.

## Next Product Work

1. **Spot-level exposure review (M).** Expand reviewed wind-exposure bearings for exposed launches, bar/river-influenced areas, and the highest-use regional spots.
2. **Station-quality review workflow (M-L).** Use the new provider context report as the baseline, then deepen the checklist with station confidence, fallback rules, bins/depth, and regional caveats.
3. **Provider comparison tools (M).** Extend the provider context report into side-by-side NOAA candidate comparison before promoting new regions into the app.
4. **Search ranking refinements (S-M).** Add partial-match ranking, typo tolerance, and richer unsupported-place routing as the catalog grows.
5. **Operator session hardening (M).** Replace simple env-token unlock with a stronger hosted auth story if `/admin` becomes multi-user or internet-facing.

## Later

1. **Broader Puget Sound reach (L).** Add Central Sound, Bainbridge/Kingston, Vashon/Maury, North Hood Canal, and San Juan/Whidbey candidates after provider contexts are reviewed.
2. **Saved planning presets (M).** Let users save preferred region, activity, risk tolerance, and map density as named planning views.
3. **Digest archive (M).** Keep recent generated digests locally or server-side so users can compare tomorrow's recommendation against previous days.
4. **Additional delivery channels (L).** Explore push notifications or SMS only after email delivery has real-world reliability data.

## Moonshots

1. **Personal water-window model (XL).** Let users rate past recommendations and gradually tune scoring to their own comfort, skill, boat, casting style, and wind tolerance.
2. **Trip-planning optimizer (XL).** Given a day, time budget, launch preference, and activity, suggest a ranked plan with spot sequence, arrival windows, tide/current transitions, and fallback options.
3. **Local knowledge graph (XL).** Model relationships between regions, launches, tide/current stations, wind exposure, shoreline orientation, hazards, access, and seasonal fishing patterns.
4. **Live nowcast layer (XL).** Blend NOAA, weather forecast, station history, NWS advisories, and recent observed error into short-term nowcasts that flag when a forecast may be drifting from reality.
5. **Community field reports (XL).** Add optional post-trip reports that can confirm conditions, flag access issues, and improve confidence without turning TideWindow into a social feed.

## Housekeeping

- Keep `APP_VERSION`, README feature text, changelog, and this roadmap in sync as work lands.
- Replace dated static query strings (`?v=...`) whenever frontend assets change, or move to an app-version constant/template if the app grows.
- Keep `docs/` organized by purpose: `assets/` for images, `planning/` for briefs/reviews/QA, and `reference/` for source research.
- Keep the [launch-readiness checklist](planning/LAUNCH_READINESS_CHECKLIST.md) current as hosted PWA and digest operations mature.
