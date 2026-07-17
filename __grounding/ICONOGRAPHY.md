# Garment iconography runbook

SOMETHINGS-ON garment icons are original construction-line studies of familiar clothing archetypes. They should feel precise, quiet, and useful rather than like brand marks, fashion illustrations, or generic interface glyphs.

The first set is source-free and consists of a front-view T-shirt, front-view pants, and a side-view low shoe. No vendor silhouette, logo, signature graphic, or branded panel layout was used to draw them.

## Drawing system

- **Canvas:** use the shared `viewBox="0 0 120 140"`. Draw on a 4-unit working grid, then make small optical corrections rather than forcing every point back onto the grid.
- **Safe area:** keep the primary contour between `x=8–112` and `y=8–132`. The vertical centerline is `x=60`.
- **Stroke:** use a 2-unit primary contour and 1.5-unit construction details at `0.55` stroke opacity. Use `currentColor`, no fill, and no fixed colors.
- **Ends and corners:** use round caps and round joins throughout. A mitred, technical-CAD look is outside this system.
- **Shape hierarchy:** one closed primary silhouette is preferred. Secondary paths may describe only construction that helps identify the garment: neckline, waistband, fly, pocket, hem, sole, collar, or lacing.
- **Detail limit:** keep a study to at most five secondary path groups and six distinct construction ideas. Do not add fabric texture, shadows, decorative prints, hardware inventories, or ornamental stitch maps.
- **SVG hygiene:** use paths and groups without internal IDs, masks, filters, embedded styles, or transforms. This prevents ID collisions and keeps the drawings easy to inspect and edit.

## Optical alignment

Geometry is a starting point; perceived weight decides the final position.

- Front-view garments use `x=60` as their actual axis and occupy roughly `y=16–125`.
- A horizontally weighted object should not be enlarged until its widest points match a vertical garment. The shoe sits around `y=46–106` so its visual center aligns with the taller garments while retaining the expected shallow silhouette.
- Keep paired features mathematically mirrored first. Adjust by no more than 1–2 units only when a curve looks visibly heavier on one side.
- Judge the icon inside its real component at 48, 96, and 160 CSS pixels. Avoid using the set below 48 pixels wide; the secondary construction lines are intentionally illustrative rather than micro-icon detail.
- Align a row by the shared SVG box, not by the physical garment hem or shoe sole.

## Component and file naming

- Use `<GarmentName>Icon.tsx` and export `<GarmentName>Icon`, for example `TShirtIcon` or `JacketIcon`.
- Use familiar garment nouns, not collection names or brand vocabulary.
- Add a view or construction qualifier only when multiple studies would otherwise collide: `JacketBackIcon`, `ShoeTopIcon`, or `SkirtPleatedIcon`.
- Re-export every public component from `icons/index.ts`. Keep shared rendering behavior in `GarmentIconFrame.tsx`.

All icons accept standard React SVG props plus an optional `title`. Width and height default to `1em`, so callers should set an explicit square or garment-study size when layout stability matters.

## Accessibility

The frame treats an unlabeled icon as decorative: it sets `aria-hidden="true"` and `focusable="false"`.

- When an icon repeats adjacent visible text, leave it unlabeled.
- When the icon conveys information by itself, pass `title="T-shirt"` or an `aria-label`. `title` creates an internal SVG title and exposes the SVG with `role="img"`.
- Prefer an explicit visible label on the parent button or card. A garment drawing must never be the only indication of an action, state, or selection.
- Do not pass both `title` and `aria-label`; choose one accessible naming route.
- Keep the SVG itself non-interactive. Put keyboard behavior, focus treatment, and selected state on the semantic parent control.

## Originality check

Run this check before adding an icon:

1. Begin from the garment noun and basic construction, not a designer image or shopping-page silhouette.
2. Sketch the primary contour on the shared grid without tracing. Use only anatomy that is common to the archetype.
3. Remove logos, signature graphics, distinctive sole patterns, proprietary hardware, and recognizable brand paneling.
4. Search the proposed shape against any references used during the product task. If the value comes from resembling one specific product, redraw it at a more general archetype level.
5. Review the icon in monochrome and without its label. It should identify the garment category, not suggest a maker.
6. Record any material reference used to understand unusual construction in `__grounding/`; never commit a licensed source asset merely to justify an icon.

## Adding a garment

1. Duplicate the public component pattern, not an existing garment path.
2. Draw one closed silhouette inside the 120×140 safe area and establish its optical center.
3. Add only the construction lines needed to disambiguate the archetype, using the secondary stroke treatment.
4. Check symmetry, edge clearance, joins, and apparent weight at 48, 96, and 160 pixels on both dark and light fields.
5. Test decorative use and a meaningful use with `title`; confirm the parent control still has a visible focus state.
6. Export the component from `icons/index.ts`, run the frontend type check, and capture a browser screenshot in the actual selection or study layout.
7. Perform the originality check above before shipping.

Example:

```tsx
import { TShirtIcon } from './components/icons'

<TShirtIcon width={96} height={112} aria-hidden="true" />
<TShirtIcon width={96} height={112} title="T-shirt" />
```
