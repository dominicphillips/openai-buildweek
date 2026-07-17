# Vetements avatar generation manifest

Run date: **2026-07-17**. The complete repository skill instructions and prompting reference were read before execution. Every plan passed a dry run with `__harness/skills/create-image/scripts/create_image.py` using `gpt-image-2`, `1024x1024`, `low` quality, and PNG output.

## Current status

Both live requests returned OpenAI HTTP 400 with error code `billing_hard_limit_reached`. Per the skill's retry rule, the same request was not repeated and no alternative provider was substituted. **No avatar image exists.** The intended paths below are documentation, not claims that artifacts were created.

## Guram Gvasalia

- Role: current creative director and co-founder.
- Intended output: `guram-gvasalia.png`
- Operation: text-to-image generation.
- Model / size / quality / format: `gpt-image-2` / `1024x1024` / `low` / `png`.
- Identity reference: none. The available Vogue portrait has no open reuse license; see `../sourced/MANIFEST.md`.
- Dry run: passed.
- Live run: attempted; blocked by account billing limit.
- AI-generated artifact: **No; planned but absent.**
- Visual inspection: not applicable because no output was returned.

Prompt:

> Create a square, clearly illustrated editorial head-and-shoulders portrait of public fashion designer Guram Gvasalia, recognizable from his broadly documented public appearance but not photorealistic. High-contrast black and white, restrained halftone and photocopier grain, clean silhouette, neutral light-gray background, centered direct gaze. No text, logos, brand marks, clothing graphics, watermarks, or symbols. No documentary event; clearly an illustration.

## Demna

- Role: historical founding design lead; not current Vetements creative director.
- Intended output: `demna.png`
- Operation: reference-image edit.
- Model / size / quality / format: `gpt-image-2` / `1024x1024` / `low` / `png`.
- Identity reference: `../sourced/portraits/demna-gvasalia-2022.jpg`, Presidential Administration of Ukraine / President.gov.ua, CC BY 4.0. Downstream use must retain attribution and identify the generated portrait as a modification.
- Dry run: passed.
- Live run: attempted; blocked by account billing limit.
- AI-generated artifact: **No; planned but absent.**
- Visual inspection: not applicable because no output was returned.

Prompt:

> Using the supplied legally reusable portrait only as an identity reference, create a square, clearly illustrated editorial head-and-shoulders portrait of Demna. Preserve his recognizable facial structure, head shape, close beard, and direct gaze. High-contrast black and white, restrained halftone and photocopier grain, clean silhouette, neutral light-gray background, centered composition. Remove all text, logos, brand marks, clothing graphics, earbuds, watermarks, and symbols. Do not recreate the source setting. Clearly an illustration, not a documentary photograph.

## Acceptance gate when billing is restored

Re-run the documented commands through the repository skill, then inspect identity, crop, logo removal, text artifacts, hands, and background. Keep the avatar only if it is recognizably the named public figure, plainly illustrated, and carries the source attribution where required. The profile must never imply endorsement or speak as the designer.
