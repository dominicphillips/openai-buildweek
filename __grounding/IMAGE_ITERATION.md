# Image iteration contract

This is the design-truth loop for SOMETHINGS-ON. The product makes fashion through inspectable raster versions, not through a React illustration or a new text-only render on every turn.

## Core invariant

A valid `DesignVersion` is immutable. Version 01 becomes valid only after a real `gpt-image-2` generation call returns and its raster is persisted. Every later valid version is returned by a real Images API edit call whose edit target is the exact raster owned by the selected current version.

Do not reconstruct a child from its ancestor's prompt. Do not silently swap in an older image, a presentation render, an SVG, a placeholder, or a deterministic fixture. The current raster is the sole canonical design image for the mutation.

## One edit transaction

1. Resolve and lock the selected current version and its owned raster asset.
2. Ask for one observable delta. If the request contains several independent changes, split it or obtain explicit approval for the larger scope.
3. Assemble `CHANGE /` with that delta and `KEEP /` with the named invariants. Cover silhouette, proportion, material, construction, finish, color, graphics, garment placement, and image view when each must remain stable.
4. Call the `gpt-image-2` edit operation with the exact current raster bytes as the edit target. Neutral traits extracted from inspiration may inform the text; inspiration must not replace the canonical design image.
5. Keep the parent visible while the job runs. Persist the complete returned raster as a new asset, then append a child version containing `parent_id`, prompt, delta, invariants, model, settings, source lineage, and provider request id when available.
6. Move the canvas to the child only after both asset and version records succeed. Accept, reject, undo, compare, and branch operate on this lineage rather than overwriting it.

The next request repeats the loop from whichever immutable version the designer has selected. A branch edits the selected ancestor's exact raster and records that ancestor as its parent.

## Failure behavior

The current ready version survives every failure. Billing limits, missing or invalid credentials, quota, rate limits, moderation, timeout, provider unavailability, invalid output, and persistence errors fail the `GenerationJob`; they do not create a version or advance the current pointer.

Report the category honestly in product-safe language and in demo readiness notes. Keep raw provider bodies and credentials server-side. Never cover a failed live call with an SVG or label an offline illustration as the requested result.

## Garment truth versus presentation

Changing the garment creates a `DesignVersion`. Changing the fictional adult model, body controls, pose, camera, setting, or light creates a `PresentationRender` linked to one unchanged design version. A presentation uses the selected garment raster as its reference but never becomes the canonical input for the next garment edit.

## DevDay acceptance

Current status on 2026-07-17: the DevDay lineage meets the checks below through three prepared direct OpenAI `gpt-image-2` responses, an imported fictional-adult presentation, and a fourth live ChatKit edit of Version 03's exact raster. See `DEV_DAY_IMAGE_GENERATION.md`. The prepared outputs are checksum-verified into the backend's real `DesignVersion` and `PresentationRender` stores at startup; subsequent work uses the same live direct OpenAI path.

The canonical three-look story is complete only when:

- version 01 has real `gpt-image-2` generation provenance;
- versions 02 and 03 have real Images API edit provenance and each records the exact preceding raster as parent;
- every prompt exposes one delta and its invariants;
- all three raster assets load and compare at useful inspection zoom;
- a forced API failure leaves the prior version intact; and
- model casting produces a separate presentation render.

React/SVG live illustrations may support onboarding or explain interaction. Near the studio they must be labeled `ILLUSTRATION / NON-PRODUCTION`, and they never satisfy any item above.
