# Regional Spot Selection Brief

## Summary

TideWindow should evolve from a Gig Harbor-specific dashboard into a Puget Sound regional planner. A user chooses a Puget Sound region, the app recenters the map on that area, selects the nearest/highest-relevance fishing and paddling spots, and scores those spots with the same tide, current, wind, daylight, and advisory context used today.

This is a fundamental change because zones can no longer be hardcoded as one fixed set. Regions, stations, spots, scoring context, map viewport, and user-visible spot count need to become data-driven.

## User Experience

The primary workflow:

1. User opens TideWindow and selects a region, such as Gig Harbor, Tacoma Narrows, Hood Canal, Central Sound, South Sound, or San Juan Islands.
2. The map moves to that region's default center and zoom.
3. The app automatically displays the top 10 nearby spots for that region.
4. If more spots are available, the user can show more. If the map feels too crowded, the user can show fewer.
5. Location controls list the region's spots in relevance order, with visible spots at the top and additional nearby spots available below.
6. Best windows, timeline recommendations, map markers, and spot details all update to match the selected region and visible spot set.

The default should feel decisive: pick a region, immediately see the most useful nearby spots. The controls should be there for tuning, not required setup.

## Product Requirements

- Add a region picker as a first-class control near the map and activity filter.
- Define region records with name, map center, default zoom, relevant NOAA tide/current stations, NWS marine zone, weather coordinate, and default search radius.
- Define spot records independently from regions. Each spot should include title, coordinates, activity tags, shoreline/exposure metadata, current/tide/wind multipliers or thresholds, and optional launch/access notes.
- Rank spots for a selected region by distance plus relevance. Relevance can initially be manual priority, then later include popularity, activity match, safety confidence, or data quality.
- Show the top 10 ranked spots by default.
- Provide "show fewer" and "show more" controls, probably stepping through 5, 10, 15, 20, and "all in region."
- Keep user choices persistent per region: selected activity, visible count, hidden spots, and optionally favorite spots.
- Fit the map bounds to the currently visible spots, not to the entire Puget Sound catalog.
- If a region has fewer than 10 spots, show all and avoid empty-feeling controls.
- If the selected region has no station-quality confidence, clearly label derived/fallback assumptions.

## Data Model

Recommended new concepts:

- `Region`: stable id, display name, map center, zoom, bounds/radius, tide station, current station, NWS zone, weather lat/lon.
- `Spot`: stable id, title, lat/lon, region hints, activity tags, priority, local notes, access notes, scoring metadata.
- `SpotSelection`: selected region id, visible count, hidden spot ids, pinned/favorite spot ids.
- `ProviderContext`: station and weather configuration resolved from the selected region.

The current `ZONES`, `OPTIONAL_ZONES`, and `ALL_ZONES` dictionaries should become a starter spot catalog. Gig Harbor would become the first region backed by that catalog.

## API Impact

The API should accept or resolve a selected region:

- `GET /api/regions` returns the available regions and defaults.
- `GET /api/state?region=gig_harbor&limit=10` returns region-scoped state, ranked spots, visible spots, provider metadata, map viewport hints, windows, timeline, events, alerts, and confidence.
- The cache key must include region id and probably spot limit, because provider context and scoring can change by region.
- Health should expose configured region count and provider coverage, not just one hardcoded station pair.

Short term, the frontend can pass the region query parameter. Longer term, the backend can remember no state and let the browser persist region/limit choices.

## Frontend Impact

- Add a compact region selector.
- Replace "Locations" with region-aware spot controls.
- Add show fewer/show more controls for visible spot count.
- Keep the map large and fit it to the currently visible spot set.
- Keep marker popups as the detailed spot surface.
- Make empty and degraded states region-specific, such as "No scored spots for this region yet" or "Using derived current for Hood Canal."
- Avoid loading every Puget Sound marker at once; visible markers should match the selected spot count.

## Scoring Impact

Regionalization should not be only a map filter. The selected region changes the physical interpretation of the data:

- Tide station may change.
- Current station may change or be unavailable.
- NWS marine zone may change.
- Wind exposure may change by shoreline orientation.
- Spot thresholds may need to vary by region and activity.

This pairs naturally with the existing roadmap item for wind-direction-aware exposure scoring and the config-driven threshold work.

## Rollout Plan

Phase 1: Data model and Gig Harbor parity

- Introduce `Region` and `Spot` configuration while preserving current Gig Harbor behavior.
- Add one `gig_harbor` region that produces the same default spots and map view as today.
- Update tests around region-scoped API payloads.

Phase 2: Region picker and spot count controls

- Add the region selector and visible-count controls.
- Make the map fit visible spots.
- Persist selected region and visible count in local storage.

Phase 3: Puget Sound catalog expansion

- Add additional Puget Sound regions and spot catalogs.
- Start with manually curated spots and priorities.
- Keep station and confidence labels honest where current predictions are weaker.

Phase 4: Accuracy upgrades

- Add wind-direction exposure metadata per spot.
- Move thresholds into configuration.
- Support per-region station fallback strategies.

## Open Questions

- What is the first region list: broad marine forecast zones, named Puget Sound subregions, or user-friendly places?
- Should "top 10" mean closest to the region center, best-scored right now, manually prioritized, or a blend?
- Should users be able to search by town/launch instead of choosing from predefined regions?
- Do fishing and kayaking share the same spot catalog, or should each activity rank spots differently?
- How should privately accessed or sensitive fishing spots be handled?

## Recommended Next Step

Build Phase 1 first: introduce regions and spots behind the scenes while keeping the current Gig Harbor UI behavior unchanged. Once parity is tested, add the region picker and top-10 controls without risking the existing dashboard.
