# Reference iconography runbook

The reference thumbnails are project-authored garment studies, not borrowed product imagery.
They give the catalog a consistent visual language while keeping every source and tag reviewable.

## Drawing contract

- Use a `480 × 360` SVG view box.
- Draw the object as a front or side outline with no body, mannequin, logo, wordmark, or signature
  graphic.
- Use `#f1efe9` at `2.5px` for the main silhouette and `#85847f` for seams, closures, panels,
  and construction evidence.
- Keep the background `#0a0a09` and the guide rules `#3b3b38`. Do not embed visible text in the SVG; semantic HTML supplies every label at the 16px product floor.
- Prefer a few legible construction lines over photoreal texture. The thumbnail should still read
  at roughly `240 × 180`.
- Include an SVG `<title>` and `<desc>` that agree with the manifest's `image_alt`.

## Change or add a study

1. Edit `reference_catalog.json`. Keep the catalog at exactly 30 items; replace a slot instead of
   silently growing the onboarding set. Keep `image_url` browser-relative and `image_path`
   repository-relative.
2. Associate the study with one selector label using its stable `label_association.id`. The
   `matched_traits` must explain neutral editorial overlap; it must never imply that the study is
   an official product, a collaboration, or a copy. Keep all 20 selector labels represented so
   the Studio's Inspiration filter has a local result for each label.
   Keep the item's `provenance_id` and `rights_status` linked to the top-level provenance record;
   do not reuse this project-authored status for imported or user-owned references.
3. Choose an existing `illustration.template` and variant, or add a renderer to
   `../scripts/build_reference_seeds.py`. Geometry must be deterministic—no timestamps, random
   numbers, external fonts, remote images, or machine-specific paths.
4. From `backend/`, rebuild the assets and ignored local database:

   ```bash
   uv run python scripts/build_reference_seeds.py
   ```

   To rebuild only the committed SVG sources:

   ```bash
   uv run python scripts/build_reference_seeds.py --skip-db
   ```

5. Check that the committed files exactly match the renderer:

   ```bash
   uv run python scripts/build_reference_seeds.py --check
   uv run pytest tests/test_reference_catalog.py
   ```

6. Inspect all 30 thumbnails together on the dark product background. Check recognition at small
   size, consistent optical weight, intentional whitespace, no clipped strokes, and meaningful
   differences between variants.

Do not hand-edit files in `app/public/reference-seeds/`; change the renderer or manifest and rebuild.
The runtime LanceDB artifact lives at `backend/data/reference-catalog.lancedb` and remains ignored.
