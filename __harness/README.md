# Portable agent harness

This folder contains stripped-down, project-owned versions of the creative and review tools used during the hackathon. A contributor or agent can run them from the repository without inheriting anyone else's home-directory layout, shell aliases, global skill installation, or private configuration files.

Each skill is self-contained under `skills/<name>/` and contains only its concise contract, runnable script, agent metadata, and essential references.

| Skill | Purpose | Runtime setting |
| --- | --- | --- |
| `create-image` | Generate or edit raster assets with `gpt-image-2`, including reference-conditioned garment studies and clearly labeled editorial avatars. | `OPENAI_API_KEY` |
| `create-music` | Render an original track with Replicate `google/lyria-3-pro` after inspecting a cost-free dry run. | `REPLICATE_API_TOKEN` |
| `ask-gemini` | Send a focused question and explicit files to Gemini for an independent, verifiable second opinion. | `GEMINI_API_KEY` or supported ambient Google credentials |
| `ask-claude` | Run a read-only Claude CLI review of a repository or architecture decision. | authenticated `claude` CLI |
| `copywriter` | Draft grounded UX, product, editorial, marketing, or technical copy through the OpenAI Responses API. | `OPENAI_API_KEY` |
| `cache-product-images` | Build, resume, and verify the ignored 600-product local Inspiration image cache. | network access to build; none to verify |

## Usage contract

1. Read the selected skill's complete `SKILL.md` and any directly required reference.
2. Supply explicit repository-relative files and output paths. A skill must not discover personal files automatically.
3. Use `--dry-run` before any cost-bearing image or music request.
4. Write generated media to an ignored runtime directory such as `backend/generated/`; never put raw outputs into grounding by default.
5. Inspect the output and verify any code, architecture, source, or factual claim yourself. Reviewer responses are input to the orchestrator, not authority.
6. Record only non-sensitive provenance needed to reproduce an adopted result: model, prompt or question, explicit input files, settings, and repository-relative output.

## Portability and privacy

- Scripts read standard environment variables at runtime and never print, persist, or commit credentials.
- Examples use paths relative to the repository. Do not add absolute home-directory paths, private URLs, provider account ids, browser profiles, or shell-specific aliases.
- Install narrow Python dependencies at invocation time with `uv run --with ...` where the skill documents that pattern. Do not copy an entire machine-specific environment into this repository.
- Keep paid actions explicit. A dry run may resolve and display a payload, but it must not call the provider.
- Translate living artists, designers, labels, musicians, and campaigns into concrete editable attributes. Do not use a portable skill as an imitation or endorsement shortcut.
- Treat user references and generated media as private working material. Commit only sanitized documentation, intentionally approved project assets, and provenance that contains no secrets or personal machine data.

The repository copies are intentionally smaller than local power-user wrappers. Add a dependency or reference only when another contributor needs it to run the same project workflow safely.
