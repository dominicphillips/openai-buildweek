---
name: copywriter
description: Draft natural product, UX, editorial, marketing, or technical copy with an OpenAI Responses API model and explicit source files. Use when interface language or project prose needs a focused writing pass grounded in existing decisions rather than invented claims.
---

# Copywriter

Use `scripts/copywriter.py` with a mode and the smallest set of grounding files that establish facts and voice. It reads `OPENAI_API_KEY` from the environment and defaults to the efficient `gpt-5.6-luna` model.

```bash
uv run --with 'openai>=2.38,<3' \
  __harness/skills/copywriter/scripts/copywriter.py \
  --mode ux \
  --file __grounding/PRODUCT.md \
  'Write the skip, error, and completion copy for the 30-second pause.'
```

Read `references/voice.md` first. Check every fact, remove generic hype, and edit the returned draft by hand before shipping it.
