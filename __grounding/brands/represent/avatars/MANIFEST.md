# Represent avatar generation manifest

Run date: **2026-07-17**. Both plans passed dry runs with `__harness/skills/create-image/scripts/create_image.py` using `gpt-image-2`, `1024x1024`, `low` quality, and PNG output.

## Current status

The live requests were not sent after four other avatar requests in this batch returned OpenAI HTTP 400 with error code `billing_hard_limit_reached`. Stopping avoided redundant failures and followed the repository skill's retry rule. No alternative provider was substituted. **No avatar images exist.**

## George Heaton

- Role: co-founder and creative director.
- Intended output: `george-heaton.png`
- Operation: text-to-image generation.
- Model / size / quality / format: `gpt-image-2` / `1024x1024` / `low` / `png`.
- Identity reference: none. Located portraits did not have open reuse licenses; see `../sourced/MANIFEST.md`.
- Dry run: passed.
- Live run: not attempted after the account-level blocker was confirmed.
- AI-generated artifact: **No; planned but absent.**
- Visual inspection: not applicable because no output was generated.

Prompt:

> Create a square, clearly illustrated editorial head-and-shoulders portrait of public fashion designer George Heaton of Represent, recognizable from his broadly documented public appearance but not photorealistic. High-contrast black and white, restrained halftone and photocopier grain, clean silhouette, neutral light-gray background, centered direct gaze. No text, logos, brand marks, clothing graphics, watermarks, or symbols. No documentary event; clearly an illustration.

## Michael Heaton

- Role: co-founder and creative director.
- Intended output: `michael-heaton.png`
- Operation: text-to-image generation.
- Model / size / quality / format: `gpt-image-2` / `1024x1024` / `low` / `png`.
- Identity reference: none. Located portraits did not have open reuse licenses; see `../sourced/MANIFEST.md`.
- Dry run: passed.
- Live run: not attempted after the account-level blocker was confirmed.
- AI-generated artifact: **No; planned but absent.**
- Visual inspection: not applicable because no output was generated.

Prompt:

> Create a square, clearly illustrated editorial head-and-shoulders portrait of public fashion designer Michael Heaton of Represent, recognizable from his broadly documented public appearance but not photorealistic. High-contrast black and white, restrained halftone and photocopier grain, clean silhouette, neutral light-gray background, centered direct gaze. No text, logos, brand marks, clothing graphics, watermarks, or symbols. No documentary event; clearly an illustration.

## Acceptance gate when billing is restored

Run each request through the repository skill and verify identity against multiple public pages without importing their imagery. Evaluate the two portraits independently so the brothers are not conflated. Reject generic faces, text artifacts, logos, and documentary styling. Label accepted outputs as AI-generated illustrations and never present either profile as an endorsement or simulated speaker.
