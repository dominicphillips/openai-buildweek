# Portable agent harness

This folder contains the smallest project-owned versions of the creative and review tools used during the hackathon. They use standard environment-variable names, explicit inputs, and repository-relative examples; they do not depend on a contributor's home directory or private configuration files.

Each skill is self-contained under `skills/<name>/`. Read its complete `SKILL.md`, run its script in `--dry-run` mode when available, and keep generated outputs in ignored runtime directories.

| Skill | Purpose |
| --- | --- |
| `create-image` | Generate or edit raster assets with OpenAI `gpt-image-2`, including reference-conditioned garment studies and clearly labeled editorial avatars. |
| `create-music` | Render an original instrumental or song with Replicate `google/lyria-3-pro` after inspecting a cost-free dry run. |
| `ask-gemini` | Send a focused question and explicit files to Gemini for an independent, verifiable second opinion. |
| `ask-claude` | Run a read-only Claude CLI review of a repository or architecture decision. |
| `copywriter` | Draft grounded UX, product, editorial, marketing, or technical copy through the OpenAI Responses API. |

No skill may print, persist, or commit a credential. Copy `.env.example` files to ignored local env files only when a contributor needs persistent local configuration.
