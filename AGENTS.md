# Project agent guide

## Mission

Build **SOMETHINGS-ON**, a guided creative workspace for emerging fashion designers. The product helps a designer collect references, identify the qualities they care about, and iteratively change one intentional detail at a time while keeping authorship and final judgment with the designer.

The name is an homage to Virgil Abloh and Nike's *Something's Off* while deliberately turning the phrase toward creative momentum. Do not imply endorsement or reproduce the book's identity system.

## Read first

Before changing product behavior or visual direction, read:

1. `__grounding/README.md`
2. `__grounding/PRODUCT.md`
3. `__grounding/DESIGN_PRINCIPLES.md`
4. `__grounding/ARCHITECTURE.md`
5. Any task-specific reference in `__grounding/`

Treat `__grounding/` as the shared project memory. Add sources, decisions, screenshots, and research there when they materially affect future work. Never place secrets, private user data, licensed assets, or personal machine paths in it.

## Work loop

Use this loop for every coherent slice of work:

1. **Ground** — read the relevant source, code, and current product decisions.
2. **Frame** — state the smallest outcome that proves the next part of the experience.
3. **Delegate** — split independent research, copy, review, and implementation work across subagents when useful.
4. **Build** — make the smallest complete change; keep speculative abstractions out.
5. **Verify** — run focused tests, type checks, builds, and a browser pass proportional to the change.
6. **Record** — update grounding or architecture notes when a decision changed.
7. **Commit** — stage only the intended files, review the diff, and commit the validated slice.

Loop again until the requested outcome is genuinely complete.

## Orchestration and parallel work

The root agent acts as orchestrator and owns the plan, integration, verification, and final judgment. Give subagents bounded tasks with explicit outputs; avoid assigning overlapping files, and never accept a subagent claim without checking the relevant artifact or source.

Good parallel work includes research, UX copy, architecture review, isolated components, test authoring, and visual QA. Keep dependent edits sequential. If two tasks touch the same state contract or file, designate one owner and ask the other agent for a read-only review.

## Git discipline

- Commit after each coherent, verified layer instead of accumulating one large diff.
- Use concise, imperative messages that explain the outcome, such as `Add guided creative ritual`.
- Stage specific paths; do not use broad staging commands when unrelated work exists.
- Review the staged diff and run `git diff --cached --check` before committing.
- Never add AI attribution, generated-by footers, or co-author trailers.
- Do not rewrite or discard user changes. Work around unrelated edits.

## Security and privacy

- Never commit API keys, tokens, cookies, account identifiers, private URLs, user uploads, or personal environment details.
- Keep secrets server-side. Browser code may only receive public configuration and short-lived product/session data intended for it.
- `.env`, `.env.*`, local databases, uploads, generated media, logs, and build output are ignored. Commit only sanitized `.env.example` files.
- Use environment-variable names in documentation, never example values that resemble real credentials.
- Before committing, scan the staged diff for secret-shaped strings and absolute home-directory paths.
- Treat uploaded inspiration as user-owned working material. Preserve source metadata and avoid training, publication, or reuse claims.

## Product boundaries

- Translate references and selected brands into editable traits; do not reproduce logos, signature graphics, or an exact living designer/brand style.
- Attribute and retain source lineage. The product should show what was kept, what changed, and why.
- Every generated edit must be previewable, rejectable, undoable, and versioned.
- The designer chooses. The agent suggests and operates only on the visible object or pile currently in scope.
- Do not frame the product as endorsed by, affiliated with, or impersonating Virgil Abloh or any listed brand.

## Frontend contract

- Location: `app/`
- Stack: Vite, React, TypeScript, Tailwind CSS v4, and Motion. Do not add shadcn.
- Preview URL: `http://127.0.0.1:43173` with a strict port.
- The interface is dark by default, typographic, tactile, and editorial. Prefer custom components and intentional composition over dashboard patterns.
- Support keyboard navigation, visible focus, semantic controls, sufficient contrast, reduced motion, and an immediate route past optional music/breathing rituals.
- The workspace keeps chat on the left and the current design centered. References collect around the design as movable piles on an expansive canvas.

## Backend contract

- Location: `backend/`
- Stack: Python, FastAPI, OpenAI Agents SDK, and the self-hosted/custom ChatKit server protocol.
- API URL: `http://127.0.0.1:43174` with a strict port.
- Start with one fashion design agent and narrow function tools. Add specialists only after the single-agent flow demonstrates a real need.
- Use `gpt-5.6` for the guided agent and `gpt-image-2` for direct image generation/editing unless current official guidance or evals justify a change.
- Image edits use the current design and explicit reference images. Store generated artifacts outside Git and return metadata sufficient to place a new version on the canvas.
- Expose `/health`. Keep API failures legible and never leak upstream error bodies or credentials to the browser.

## Repository skills

Prefer these portable skills under `__harness/skills/` over machine-specific wrappers. Read the selected skill's complete `SKILL.md` before using it.

- **create-image** — Generate a new concept or edit an existing design with `gpt-image-2`, preserving references and writing outputs to ignored local storage. Use it for garment studies, reference-conditioned iterations, and visual variations.
- **create-music** — Render an optional original focus track with Replicate's `google/lyria-3-pro` from a concrete musical brief. Use it only when original audio is requested; dry-run the payload before spending credits.
- **ask-gemini** — Request an independent Gemini research or large-context review and provide the relevant files. Treat its response as input, then verify material claims against primary sources or the repository.
- **ask-claude** — Run a read-only Claude architecture or code review from the repository context. Use it for a second opinion, then inspect every referenced file and synthesize the result yourself.
- **copywriter** — Draft restrained product, UX, editorial, or technical copy from explicit grounding. Review the output for accuracy, tone, and unwanted imitation before shipping it.

## Definition of done

A slice is done when the behavior works through its real path, relevant checks pass, the visible result has been inspected, accessibility and error states are accounted for, grounding is current, and the work is committed with a meaningful message. A rendered shell with disconnected controls is not complete.
