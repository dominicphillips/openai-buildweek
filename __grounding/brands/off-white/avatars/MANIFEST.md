# Off-White avatar generation manifest

Run date: **2026-07-17**. The complete repository skill instructions and prompting reference were read before execution. Both plans passed dry runs with `__harness/skills/create-image/scripts/create_image.py` using `gpt-image-2`, `1024x1024`, `low` quality, PNG output, and the local licensed portrait as an edit reference.

## Current status

Both live requests returned OpenAI HTTP 400 with error code `billing_hard_limit_reached`. Per the skill's retry rule, the same requests were not repeated and no alternative provider was substituted. **No avatar images exist.** The intended paths below are documentation, not claims that artifacts were created.

## IB Kamara

- Role: current creative director.
- Intended output: `ib-kamara.png`
- Operation: reference-image edit.
- Model / size / quality / format: `gpt-image-2` / `1024x1024` / `low` / `png`.
- Identity reference: `../sourced/portraits/ib-kamara-2024.jpg`, author field `TomosWalesLondon`, described as a Kamara self-portrait, CC BY-SA 4.0.
- Downstream license: treat a generated adaptation as CC BY-SA 4.0; retain both parts of the source credit, link the license, and state that the image is AI-generated and modified.
- Dry run: passed.
- Live run: attempted; blocked by account billing limit.
- AI-generated artifact: **No; planned but absent.**
- Visual inspection: not applicable because no output was returned.

Prompt:

> Using the supplied legally reusable self-portrait only as an identity reference, create a square, clearly illustrated editorial head-and-shoulders portrait of IB Kamara. Preserve his recognizable facial structure, braided hair pattern, and direct gaze. High-contrast black and white, restrained halftone and photocopier grain, clean silhouette, neutral light-gray background, centered composition. Remove all text, logos, brand marks, clothing graphics, watermarks, and symbols. Change the raised-arm pose to a simple frontal portrait. Clearly an illustration, not a documentary photograph.

## Virgil Abloh

- Role: founder and historical creative author, 1980–2021.
- Intended output: `virgil-abloh.png`
- Operation: reference-image edit.
- Model / size / quality / format: `gpt-image-2` / `1024x1024` / `low` / `png`.
- Identity reference: `../sourced/portraits/virgil-abloh-2019.jpg`, Myles Kalus Anak Jihem, CC BY-SA 4.0.
- Downstream license: treat a generated adaptation as CC BY-SA 4.0; retain creator attribution, link the license, and state that the image is AI-generated and modified.
- Dry run: passed.
- Live run: attempted; blocked by account billing limit.
- AI-generated artifact: **No; planned but absent.**
- Visual inspection: not applicable because no output was returned.

Prompt:

> Using the supplied legally reusable portrait only as an identity reference, create a square, clearly illustrated editorial head-and-shoulders portrait of Virgil Abloh. Preserve his recognizable facial structure, shaved head, close beard, and direct gaze. High-contrast black and white, restrained halftone and photocopier grain, clean silhouette, neutral light-gray background, centered composition. Remove all text, logos, brand marks, clothing graphics, necklace, watermarks, and symbols. Do not recreate the source clothing or background. Clearly an illustration, not a documentary photograph.

## Acceptance gate when billing is restored

Re-run through the repository skill, then inspect identity, crop, logo removal, text artifacts, hands, and background. Retain all CC BY-SA attribution in artifact metadata and the UI. Keep an avatar only if it is recognizable, clearly illustrated, and free of copied brand marks. Neither profile may imply endorsement, provide generated opinions, or simulate a living or deceased designer's voice.
