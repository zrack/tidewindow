# Station Quality Review Workflow

_Last updated: 2026-08-19._

This workflow makes regional accuracy work repeatable before adding more Puget Sound catalogs. It complements the user-facing provider diagnostics by giving the operator a checklist for station confidence, fallback behavior, wind exposure, and caveats.

## Goal

Every selectable region should have a clear answer to:

- Which tide station is being used, and is it reference or subordinate?
- Which current station/bin/depth is being used, and how local is it to the spot cluster?
- What fallback path is used when NOAA current predictions are missing?
- Which spots have reviewed wind-exposure bearings versus broad shoreline-family defaults?
- What caveats should users see before trusting the score?

## Region Review Pass

Run the provider context report:

```bash
.venv/bin/python scripts/report_provider_contexts.py
```

For lower-confidence regions:

```bash
.venv/bin/python scripts/report_provider_contexts.py --low-confidence-only
```

Review each row for:

- **Profile.** Station-backed regions are the baseline. Subordinate, sparse-current, river/bar, or derived-current profiles need visible caveats.
- **Confidence.** Medium and low confidence regions should stay in the catalog only when caveats and conservative scoring are strong enough.
- **Current bin/depth.** Confirm the configured bin represents useful surface/current behavior for the user activity.
- **Exposure basis.** Prefer reviewed spot-level bearings for exposed launches, bars, river mouths, long fetches, and high-use spots.
- **Warnings.** Warnings should be concise enough for the UI and specific enough to change user behavior.

## Promotion Checklist For New Regions

Before adding a new selectable region:

- Add tide/current station metadata in `marine_regions.py`.
- Add a provider context with tide station, current station, current bin, bin depth, NWS zone, and weather coordinates.
- Add provider profile and warnings when station fit is not straightforward.
- Add region spots with activity tags, priorities, shoreline families, and access notes.
- Run `scripts/report_provider_contexts.py` and confirm the new row is understandable.
- Add or update tests for region summaries, provider context payloads, and search aliases.
- Only then expose the region in the picker.

## Spot Exposure Review

Prioritize reviewed wind-exposure bearings for:

- Open-water launches and long fetch shorelines.
- Bar, river-mouth, and inlet-entrance spots.
- High-use kayak launches.
- Fishing spots where wind direction strongly changes drift/casting quality.
- Any spot whose shoreline-family default feels too broad.

Use `wind_exposure_basis` as the progress signal:

- `spot_reviewed`: explicitly reviewed after catalog creation.
- `spot`: explicit spot-level bearing at creation time.
- `shoreline_family`: default from shoreline family; acceptable for sheltered or lower-risk spots, but not a final review for exposed locations.

## Exit Criteria

A region is ready for broader use when:

- Provider confidence is high, or medium/low confidence caveats are visible and conservative.
- The current station/bin/depth choice is documented.
- Important spot exposure bearings have been reviewed.
- The provider report has no surprising gaps.
- User-facing provider diagnostics explain the remaining uncertainty.
