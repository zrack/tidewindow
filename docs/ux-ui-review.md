# TideWindow — UX/UI Review

A review of the web dashboard (`static/index.html`, `styles.css`, `app.js`), focused on visual polish and usability. The redesign that accompanies this review is a drop-in `styles.css` replacement — no markup or JavaScript changes required.

## Overall read

The dashboard is well-structured and information-dense in a good way: confidence, data sources, a tide curve, a map, an hourly timeline, best windows, and zone cards form a logical top-to-bottom flow. The bones are solid. What holds it back from looking "pretty" is almost entirely surface treatment — flat panels, a single corner radius, hairline borders doing all the visual separation, status communicated by text color alone, and a type scale that competes with itself. These are exactly the things a CSS-only pass can fix.

## What's working

The reading order is sound — you scan from "should I go out at all" (confidence/sources) down to "where and when specifically" (windows/zones). The status color vocabulary (green/yellow/red) is consistent across map, timeline, pills, and cards. The layout is genuinely responsive with sensible breakpoints. And the data-source honesty (live / derived / seed / fallback labels) is a thoughtful UX touch that builds trust.

## Priority issues

### 1. Everything sits on one visual plane (highest impact)

Every panel uses the same `#151b1f` fill, the same 1px `#2b3a40` border, and the same 8px radius. Nothing reads as nearer or more important than anything else, so the eye has no anchor. The fix is depth: a darker page background, slightly lighter panels, soft shadows, and a hairline top highlight so cards feel lit from above. This single change does most of the "pretty" work.

### 2. Status is encoded by color alone

Green/yellow/red text on a dark panel is the only signal for SAFE / CAUTION / DANGER. That fails WCAG (color is the sole channel) and is hard to scan quickly. Status pills should be filled, tinted chips with a subtle border, and status cards should carry a faint colored wash plus the colored left border — so condition is legible from a glance and from peripheral vision, not just by reading the word.

### 3. Typography is loud and flat

The `<h1>` scales up to 4rem while section `<h2>`s are 1.2rem and metric numbers fight the labels. Headings use weight 800–900 almost everywhere, which removes the contrast that weight is supposed to create. A tighter type scale, lighter heading weights, tabular-figure numbers for all the metrics, and slightly more line-height on body copy make the data feel calmer and more premium. (Also: the CSS names Inter as the font but never loads it, so most users see the system fallback — the redesign actually imports it.)

### 4. The hero is oversized relative to its value

A 4rem "TideWindow" wordmark eats the most valuable real estate while the actually-decision-driving content (confidence, the tide curve) sits below it. Toning the title down and giving the topbar a subtle frosted, sticky treatment keeps branding present without it dominating the first screen.

### 5. Interactive affordances are weak

Buttons (Refresh, Add, Details, Hide, filters) are mostly transparent with a thin border, and the only hover state is a border-color swap. The primary action (Refresh) doesn't look primary; the active filter is a flat cyan block. Give the primary action an accent gradient, make the segmented control's active state feel inset/lifted, and add consistent hover/active transitions so the UI feels responsive to touch.

### 6. Smaller polish items

The tide chart is drawn flat — a gradient fill under the curve and a softer baseline would make it feel like a finished sparkline rather than a debug plot. The map's hard 8px corners clash with everything around it once panels get rounder. The dialog's "Close" is a floated text button rather than a recognizable close affordance. Loading/empty states use a dashed border that reads as broken rather than intentional. Focus rings rely on border-color changes, which is too subtle for keyboard users.

## Recommendations, prioritized

The redesigned `styles.css` addresses all of the above, in this order of impact: (1) introduce depth and a cohesive surface system, (2) make status legible beyond color with tinted chips and washes, (3) refine the type scale and load Inter, (4) restrain the hero and add a sticky frosted topbar, (5) give buttons real primary/secondary/hover states, and (6) polish the chart, map, dialog, and empty states. Everything is driven by CSS custom properties (radii, shadows, spacing, status tints) so future tuning is one-line edits.

## Accessibility notes

Beyond the color-alone status issue, the redesign adds visible `:focus-visible` rings, preserves the `color-scheme: dark` hint, keeps tap targets at 40px+, and maintains contrast ratios for muted text against the new darker panels. A future pass could add `prefers-reduced-motion` handling if more animation is introduced, and ensure the Leaflet markers expose status in text (they already do via tooltips).
