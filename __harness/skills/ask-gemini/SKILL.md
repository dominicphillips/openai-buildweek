---
name: ask-gemini
description: Request an independent Gemini analysis with optional repository files attached as explicit context. Use for second opinions, research synthesis, long-context review, or a parallel critique that the orchestrating agent will independently verify.
---

# Ask Gemini

Use `scripts/ask_gemini.py` with a focused question and the files Gemini needs. It reads `GEMINI_API_KEY` or the Google SDK's supported ambient credential and does not discover personal files automatically.

```bash
uv run --with 'google-genai>=2.7,<3' \
  __harness/skills/ask-gemini/scripts/ask_gemini.py \
  'Find the three riskiest assumptions in this architecture.' \
  --file AGENTS.md \
  --file __grounding/ARCHITECTURE.md
```

Always provide code or documents for repository questions. Treat the response as input: inspect referenced files, verify current facts with primary sources, identify disagreements, and synthesize your own recommendation.
