---
name: create-image
description: Generate new raster concepts or edit user-provided design and portrait references with OpenAI gpt-image-2. Use for garment iterations, reference-conditioned visual studies, editorial avatars, and other image tasks that need a saved local artifact and provenance record.
---

# Create Image

Use `scripts/create_image.py` for a small, portable direct OpenAI Image API workflow. It reads `OPENAI_API_KEY` and never stores or prints the key. A successful run saves the image and a provenance sidecar next to it (`<output>.json` with the resolved settings, request id, SHA-256, and token usage). A failed API call prints a structured record with `status: failed` and the provider `error_code`, and exits non-zero.

## Workflow

1. Confirm the user has the right to use every input and choose an ignored output directory.
2. Translate brands or designers into concrete attributes; do not request exact logo, signature-artwork, or living-artist imitation.
3. Run `--dry-run` and inspect the resolved operation, references, size, quality, and output path.
4. Generate without references or edit with one or more `--reference` files. Use the current design as the first reference for iterative work.
5. Inspect the output for identity, construction, text, and unintended changes. Reject weak results instead of silently shipping them.
6. Adopt an accepted result by copying its `<output>.json` sidecar (model, prompt, inputs, settings, request id, SHA-256, usage) into the calling project's provenance data.

## Commands

```bash
uv run --with 'openai>=2.38,<3' \
  __harness/skills/create-image/scripts/create_image.py \
  'Studio product study of a white heavyweight cotton T-shirt' \
  --output backend/generated/white-tee.png \
  --quality medium \
  --dry-run
```

```bash
uv run --with 'openai>=2.38,<3' \
  __harness/skills/create-image/scripts/create_image.py \
  'Preserve the body and fabric. Widen only the neckline by 12 percent.' \
  --reference backend/uploads/current.png \
  --reference backend/uploads/neckline-reference.png \
  --output backend/generated/white-tee-v2.png \
  --quality medium
```

Read `references/prompting.md` before writing a fashion edit or portrait prompt.

## Constraints

- Default to `gpt-image-2`, portrait `1024x1536`, and `medium` for inspectable fashion work.
- Use `low` only for explicitly disposable thumbnails; never promote one as the canonical garment.
- Do not set `input_fidelity`; `gpt-image-2` already processes references at high fidelity.
- Do not request transparency; `gpt-image-2` does not support it.
- Keep source portraits and generated portraits clearly labeled. Never present an illustrated avatar as a documentary photograph.
- Treat moderation blocks and invalid inputs as user-correctable errors; report the failure record's `error_code` (billing, quota, moderation) honestly and do not retry the same request indefinitely.
