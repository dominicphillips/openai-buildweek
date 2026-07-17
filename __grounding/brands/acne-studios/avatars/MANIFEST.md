# Acne Studios avatar generation manifest

Run date: **2026-07-17**. The plan passed a dry run with `__harness/skills/create-image/scripts/create_image.py` using `gpt-image-2`, `1024x1024`, `low` quality, and PNG output.

## Current status

The live request was not sent after four other avatar requests in this batch returned OpenAI HTTP 400 with error code `billing_hard_limit_reached`. Stopping avoided redundant failures and followed the repository skill's retry rule. No alternative provider was substituted. **No avatar image exists.**

## Jonny Johansson

- Role: founder and current creative director.
- Intended output: `jonny-johansson.png`
- Operation: text-to-image generation.
- Model / size / quality / format: `gpt-image-2` / `1024x1024` / `low` / `png`.
- Identity reference: none. The located Architectural Digest portrait has no open reuse license; see `../sourced/MANIFEST.md`.
- Dry run: passed.
- Live run: not attempted after the account-level blocker was confirmed.
- AI-generated artifact: **No; planned but absent.**
- Visual inspection: not applicable because no output was generated.

Prompt:

> Create a square, clearly illustrated editorial head-and-shoulders portrait of public fashion designer Jonny Johansson of Acne Studios, recognizable from his broadly documented public appearance but not photorealistic. High-contrast black and white, restrained halftone and photocopier grain, clean silhouette, neutral light-gray background, centered direct gaze. No text, logos, brand marks, clothing graphics, watermarks, or symbols. No documentary event; clearly an illustration.

## Acceptance gate when billing is restored

Run the live request through the repository skill and verify identity against multiple public pages without importing their imagery. Reject generic or misidentified output, text artifacts, logos, and photorealistic event framing. Label the final image as an AI-generated illustration and do not imply endorsement or simulate the designer's voice.
