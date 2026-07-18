# Image iteration contract

This is the design-truth loop for SOMETHINGS-ON. The product makes fashion through inspectable raster versions, not through a React illustration or a new text-only render on every turn.

## Core invariant

A valid `DesignVersion` is immutable. Version 01 becomes valid only after a real `gpt-image-2` generation call returns, its raster is persisted, and the designer chooses it. Every later valid version is one chosen output from a real Images API edit call whose edit target is the exact raster owned by the selected current version.

Do not reconstruct a child from its ancestor's prompt. Do not silently swap in an older image, a presentation render, an SVG, a placeholder, or a deterministic fixture. The current raster is the sole canonical design image for the mutation.

## One edit transaction

1. Resolve and lock the selected current version and its owned raster asset.
2. Ask for one observable delta. If the request contains several independent changes, split it or obtain explicit approval for the larger scope.
3. Assemble `CHANGE /` with that delta and `KEEP /` with the named invariants. Cover silhouette, proportion, material, construction, finish, color, graphics, garment placement, and image view when each must remain stable.
4. Call the `gpt-image-2` Image API once with `n=4` and the exact current raster bytes as the edit target. All four candidates share the same prompt, parent, and invariants. Neutral traits extracted from inspiration may inform the text; inspiration must not replace the canonical design image.
5. Keep the parent visible while the job runs. Normalize and persist all four complete returned rasters as a candidate set. A candidate is a draft asset, not a version, edit parent, editorial, or history entry.
6. Show the four candidates together and let the designer choose one or keep the current version. Selection atomically appends one child containing `parent_id`, prompt, delta, invariants, model, settings, source lineage, and provider request id when available; its siblings become dismissed. `Keep current` dismisses the entire set without changing lineage.
7. Move the canvas to the child only after the selection transaction succeeds. Generate its linked back, left, and right technical views only after it is canonical. Undo, compare, and branch operate on accepted lineage rather than overwriting it.

The next request repeats the loop from whichever immutable version the designer has selected. A branch edits the selected ancestor's exact raster and records that ancestor as its parent. An unselected candidate can never be used as the next edit target.

## Failure behavior

The current ready version survives every failure. Billing limits, missing or invalid credentials, quota, rate limits, moderation, timeout, provider unavailability, invalid output, and persistence errors fail the `GenerationJob`; they do not create a version or advance the current pointer.

Report the category honestly in product-safe language and in demo readiness notes. If any returned image is missing, invalid, or cannot be persisted, fail the candidate set instead of presenting an incomplete choice as a successful four-way comparison. Keep raw provider bodies and credentials server-side. Never cover a failed live call with an SVG or label an offline illustration as the requested result.

## Garment truth versus presentation

Changing the garment creates a `DesignVersion`. Changing the fictional adult model, body controls, pose, camera, setting, or light creates a `PresentationRender` linked to one unchanged design version. A presentation uses the selected garment raster as its reference but never becomes the canonical input for the next garment edit.

The canonical raster stays visible as the primary canvas object even when one or more editorials exist. Editorials are separate linked objects placed beside it; selecting an editorial never swaps it into, overwrites, or hides the raw design.

## Technical view set

Every successful canonical version owns a four-view product set:

1. `front` is the canonical `DesignVersion` raster returned by the authored generation/edit transaction;
2. `back` is a separate edit of that exact canonical raster;
3. `left` is a separate edit of that exact canonical raster; and
4. `right` is a separate edit of that exact canonical raster.

Back, left, and right are medium-quality `TechnicalViewRecord` assets, never child versions and never editorial presentations. Their prompts change only the neutral product camera/viewpoint and explicitly preserve garment identity, silhouette, construction, material, color, finish, graphics, trims, and scale. They show the full garment on the same neutral product background with no person.

Launch the three edit calls concurrently after the canonical asset and version are durable. A derived-view failure must not roll back, hide, or invalidate the canonical version or any successful sibling view. Record status and a safe error category per view, and retry only the failed or missing role against the same canonical raster. Never use one generated side/back view as the input for another view.

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
