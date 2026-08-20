# Regional Spot Selection Brief

## Summary

TideWindow should evolve from a Gig Harbor-specific dashboard into a place-based marine planner. A user chooses a region, city, town, or named marine area, the app recenters the map on that place, selects the nearest/highest-relevance fishing and paddling spots, and scores those spots with the same tide, current, wind, daylight, and advisory context used today.

This is a fundamental change because zones can no longer be hardcoded as one fixed set. Regions, stations, spots, scoring context, map viewport, and user-visible spot count need to become data-driven.

## User Experience

The primary workflow:

1. User opens TideWindow and selects a place/region, such as Gig Harbor, Port Orchard, Aberdeen, Tacoma Narrows, Hood Canal, Central Sound, South Sound, or San Juan Islands.
2. The map moves to that region's default center and zoom.
3. The app automatically displays all ranked nearby spots for that region.
4. If the map feels too crowded, the user can switch to a lower density preset, then return to the full regional view when they want every spot.
5. The map and spot details become the primary regional surface; lower-page location controls should not duplicate the region selector.
6. Best windows, timeline recommendations, map markers, and spot details all update to match the selected region and visible spot set.

The default should feel decisive: pick a region, immediately see the most useful nearby spots. The controls should be there for tuning, not required setup.

## Product Requirements

- Add a region picker as a first-class control near the map and activity filter.
- Treat cities and towns as valid regions. For example, Port Orchard or Aberdeen should be selectable and should populate nearby spots around that city.
- Define region records with name, type (`city`, `subregion`, `marine_area`, etc.), map center, default zoom, relevant NOAA tide/current stations, NWS marine zone, weather coordinate, and default search radius.
- Define spot records independently from regions. Each spot should include title, coordinates, activity tags, shoreline/exposure metadata, current/tide/wind multipliers or thresholds, and optional launch/access notes.
- Rank spots for a selected region by distance plus relevance. Relevance can initially be manual priority, then later include popularity, activity match, safety confidence, or data quality.
- Show all ranked spots in the selected region by default.
- Provide proportional density controls: Compact at about half the regional catalog, Standard at about three quarters, and Full for every spot in the selected region.
- Keep user choices persistent: selected activity, density preset, and optionally favorite spots.
- Fit the map bounds to the currently visible spots, not to the entire Puget Sound catalog.
- If a region has only a small catalog, Full should remain the default and lower density choices should still keep the map useful.
- If the selected region has no station-quality confidence, clearly label derived/fallback assumptions.

## Data Model

Recommended new concepts:

- `Region`: stable id, display name, type, map center, zoom, bounds/radius, tide station, current station, NWS zone, weather lat/lon.
- `Spot`: stable id, title, lat/lon, region hints, activity tags, priority, local notes, access notes, scoring metadata.
- `SpotSelection`: selected region id, visible count, pinned/favorite spot ids.
- `ProviderContext`: station and weather configuration resolved from the selected region.

The current `ZONES`, `OPTIONAL_ZONES`, and `ALL_ZONES` dictionaries should become a starter spot catalog. Gig Harbor would become the first region backed by that catalog.

Important naming note: "Region" is a product term, not only a geographic scale. A city can be a region if it is the user's natural selection point. `port_orchard`, `aberdeen`, `gig_harbor`, and `hood_canal` should all be valid region ids even though they represent different geographic scales.

## API Impact

The API should accept or resolve a selected region:

- `GET /api/regions` returns the available regions and defaults.
- `GET /api/state?region=port_orchard&limit=13` returns region-scoped state, ranked spots, visible spots, provider metadata, map viewport hints, windows, timeline, events, alerts, and confidence.
- The cache key must include region id and visible spot limit, because provider context and scoring can change by region.
- Health should expose configured region count and provider coverage, not just one hardcoded station pair.

Short term, the frontend can pass the region query parameter. Longer term, the backend can remember no state and let the browser persist region/limit choices.

## Frontend Impact

- Add a compact region/place selector that supports city-style choices as well as broader marine areas.
- Replace "Locations" with region-aware spot controls.
- Add density controls for visible spot count, with all region spots visible by default.
- Keep the map large and fit it to the currently visible spot set.
- Keep marker popups as the detailed spot surface.
- Make empty and degraded states region-specific, such as "No scored spots near Port Orchard yet" or "Using derived current for Hood Canal."
- Avoid loading every Puget Sound marker at once; visible markers should match the selected regional density.

## Scoring Impact

Regionalization should not be only a map filter. The selected region changes the physical interpretation of the data:

- Tide station may change.
- Current station may change or be unavailable.
- NWS marine zone may change.
- Wind exposure may change by shoreline orientation.
- Spot thresholds may need to vary by region and activity.

This pairs naturally with the existing roadmap item for wind-direction-aware exposure scoring and the config-driven threshold work.

## Rollout Plan

Phase 1: Data model and Gig Harbor parity — shipped

- Introduce `Region` and `Spot` configuration while preserving current Gig Harbor behavior.
- Add one `gig_harbor` region that produces the same default spots and map view as today.
- Update tests around region-scoped API payloads.

Phase 2: Region picker and spot density controls — shipped

- Add the region selector/search surface and proportional density controls.
- Make the map fit visible spots.
- Persist selected region and density preset in local storage.
- Add a searchable alias index for supported regions, city-style place names, common launches, and marine-area terms.
- Route recognized nearby places such as Belfair, Union, Chico, and Gorst to their closest supported region with a visible note.

Phase 3: Puget Sound catalog expansion — expanded

- Added Port Orchard, Bremerton, and Silverdale as selectable city regions with station-backed provider context.
- Skipped Chico and Gorst as selectable regions for now because they do not have their own station-quality provider context in the catalog.
- Added Tacoma Narrows, Carr Inlet, Case Inlet, Anderson Island, Steilacoom & Nisqually, and Olympia & Budd Inlet as the first South Sound region set.
- Added explicit current-bin metadata to provider context so each region can request and label the NOAA current bin/depth being scored.
- Added South Hood Canal with Union tide predictions (`9445478`) and Hazel Point Hood Canal current predictions (`PUG1601`, bin 21).
- Added Aberdeen with Aberdeen tide predictions (`9441187`), Grays Harbor entrance current predictions (`ACT8496`, bin 1), and Grays Harbor Bar marine alerts (`PZZ110`).
- Added provider diagnostics and station-confidence labels so region-specific station choices are visible.
- Added provider priority/fallback metadata, derived-current fallback labeling, and special warnings for sparse Hood Canal current coverage and river/bar-influenced Aberdeen conditions.
- Started with manually curated Kitsap spots and priorities.
- Wired each region to tide/current/weather provider context so station choices can vary by place.
- Continue with broader Puget Sound marine areas.

Phase 4: Accuracy upgrades — started

- Added wind-direction-aware exposure scoring for modeled spots.
- Added shoreline-family wind-exposure bearings across the newer regional spot catalogs.
- Added reviewed spot-specific bearings for high-use regional spots where the shoreline-family default is too broad.
- Moved kayak/fish thresholds into configuration and added conservative/standard/aggressive risk tolerance selection.
- Added risk-profile copy to heatmap details, map popups, and full spot details.
- Executed per-region alternate station fallback in the fetcher, using the priority metadata now present in provider context.

## Open Questions

- What is the first place list: cities/towns, broad marine forecast zones, named Puget Sound subregions, or a combined selector?
- Should ranking mean closest to the region center, best-scored right now, manually prioritized, or a blend?
- Should users be able to search by town/launch instead of choosing from predefined regions?
- Do fishing and kayaking share the same spot catalog, or should each activity rank spots differently?
- How should privately accessed or sensitive fishing spots be handled?

## Recommended Next Step

Regional search/autocomplete has shipped. The next regional-planning step is spot confidence and local accuracy: continue spot-level exposure review, formalize station-quality review, and add provider comparison tooling before expanding to broader Puget Sound catalogs.
