---
name: create-music
description: Generate an original MP3 from a detailed musical brief with Replicate's google/lyria-3-pro model. Use when the project needs an instrumental focus track, song, jingle, or image-conditioned mood piece and the user has authorized a paid generation call.
---

# Create Music

Use `scripts/create_music.py` for a portable Replicate workflow. It reads `REPLICATE_API_TOKEN` from the environment, supports prompt-only dry runs, and saves the returned audio to an explicit path.

## Workflow

1. Read `references/prompting.md` and express the direction through genre, mood, tempo, instrumentation, production, and structure.
2. Translate artist references into musical attributes instead of asking for imitation.
3. Run `--dry-run` before a paid request and show the resolved payload.
4. Generate only after the user has requested original audio or approved the cost-bearing action.
5. Audition the output and keep the prompt beside the project record for reproducibility.

```bash
uv run --with 'replicate>=1,<2' \
  __harness/skills/create-music/scripts/create_music.py \
  --prompt-file __grounding/music/quiet-cut.prompt.txt \
  --output backend/generated/quiet-cut.mp3 \
  --dry-run
```

The default model is `google/lyria-3-pro`. Pass up to ten `--image` references when the user owns or may use them.
