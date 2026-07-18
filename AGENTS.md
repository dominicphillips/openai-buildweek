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
5. `COPY.md` for anything a designer reads
6. Any task-specific reference in `__grounding/`

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

## Preview and release loop

- Keep the backend on strict port `43174` and the Vite development or production-style preview on strict port `43173` while visual work is in progress. Rebuild the production bundle before judging a source change through `vite preview`.
- Use Playwright against the running production-style preview to verify every browser-visible change. Exercise the real interaction path, inspect browser console and failed network requests, and visually review screenshots at the target viewport; a type check or successful render alone is not UI verification.
- Use `http://127.0.0.1:43173/?demo=devday` for the canonical DevDay story. Exercise the imported direct-OpenAI V1–V3 lineage, at least one live ChatKit image edit, the Inspiration and Editorial panels, direct canvas drag, 35–400% zoom, tilt, reset, and every right-click tool before calling the demo ready.
- Before Inspiration QA, run `uv run python scripts/cache_product_images.py` from `backend/` and verify it with `--verify`. Product imagery must load from the same-origin cache route; do not silently fall back to browser hotlinks.
- Verify a clean browser session separately from the returning-designer path. Completing onboarding must reopen the studio after reload; `New object` returns to object selection without replaying the optional ritual.
- Test fixtures may prove visual and state behavior without spending credits, but they never count as DevDay design output and never prove a live ChatKit or image-provider call. The canonical DevDay run uses assets returned by real `gpt-image-2` API calls; if generation is unavailable, show and report that failure instead of substituting an illustration.
- Inspect screenshots at representative desktop sizes and at least one narrow onboarding size. Check spacing, clipping, focus, contrast, reduced motion, and the 16px text floor—not only whether the route renders.

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
- Stack: Vite, React, TypeScript, Tailwind CSS v4, and Motion. Bespoke composition is the default. Selectively copy a small shadcn-style primitive when its behavior materially helps—currently the local Radix `ScrollArea` and `Select`—and keep it visually owned by this product; do not import a generic component system or theme.
- Preview URL: `http://127.0.0.1:43173` with a strict port.
- The interface is dark by default, typographic, tactile, and editorial. Prefer custom components and intentional composition over dashboard patterns.
- Support keyboard navigation, visible focus, semantic controls, sufficient contrast, reduced motion, and an immediate route past optional music/breathing rituals.
- Product text starts at `1rem` / 16px. Do not shrink metadata, captions, SVG labels, controls, version history, or responsive layouts below the base size; make more space or remove secondary copy instead.
- Action-button labels stay on one line. Give them enough width or shorten the label; never stack a close mark, shortcut, count, or arrow beneath the action.
- Every visible tag, eyebrow, badge, count, and status must help the designer decide, compare, or act. Do not surface implementation terms, model/provider names, compliance reassurance, provenance boilerplate, or decorative taxonomy in the interface.
- Persist onboarding completion and the last safe project seed locally. A returning designer reopens the studio; only an explicit replay should restart the optional ritual.
- The workspace keeps chat on the left and the current design centered. Chat is collapsible without remounting or losing conversation/version context, and the canvas expands into the released space. References collect around the design as movable piles on an expansive canvas.
- The canvas must support pointer and keyboard pan, pointer-anchored zoom from 35–400%, restrained tilt, reset/fit, and an in-bounds right-click tool menu. Native browser image dragging is disabled so starting a gesture on any raster still pans or tilts the canvas. Every displayed tool must produce an observable result.
- The selected canonical `DesignVersion` raster always remains a visible primary canvas object. Editorials are separate linked canvas objects beside it; they never replace, cover, blur, or become the raw design.
- A completed authored change opens a four-image candidate comparison outside ChatKit. Candidate assets are drafts: they do not appear in version history, become edit parents, or receive technical views until the designer explicitly chooses one. `Keep current` dismisses the set without changing the canvas or lineage.

## Live illustration contract

“Live illustration” means an original React component—normally SVG composed with Motion—that acts as editorial artwork while responding to product state. It is not a static decorative screenshot and not a disguised third-party icon.

Live illustrations are interface art, not garment truth. They must never occupy a `DesignVersion` or `PresentationRender`, masquerade as an Images API result, or appear as a successful DevDay draft. When an offline or non-production illustration is shown near the studio, label it plainly as `ILLUSTRATION / NON-PRODUCTION`; it cannot satisfy an image-generation request.

- Build reusable scenes from the project iconography in `app/src/components/icons/` and follow `__grounding/ICONOGRAPHY.md`.
- Keep geometry, silhouettes, and motion original; never trace a branded garment, campaign, photograph, or signature product.
- Let state changes alter an illustration only to explain interaction or vocabulary—selection, progress, material, or construction—not to render or replace a design version.
- Honor `prefers-reduced-motion`; the still composition must remain complete and intentional.
- Decorative scenes are hidden from assistive technology. Informative scenes accept a concise accessible label.
- Do not embed microcopy below the 16px product floor inside SVGs. Put necessary copy in semantic HTML beside the illustration.

## Backend contract

- Location: `backend/`
- Stack: Python, FastAPI, OpenAI Agents SDK, and the self-hosted/custom ChatKit server protocol.
- API URL: `http://127.0.0.1:43174` with a strict port.
- Start with one fashion design agent and narrow function tools. Add specialists only after the single-agent flow demonstrates a real need.
- Use `gpt-5.6` for the guided agent and `gpt-image-2` for direct image generation/editing unless current official guidance or evals justify a change.
- Create the first canonical design study with the real `gpt-image-2` Image API. Every later garment change must call the edit path with the exact selected immutable raster as its sole canonical image input, one requested delta, and explicit invariants; never recreate a later version from text alone.
- Request four candidates in one Image API call with `n=4`. Persist the returned rasters as a durable candidate set tied to the same generation job, prompt, and exact parent. Candidates are not versions. Only the designer's atomic selection promotes one candidate asset into a new immutable `DesignVersion`; dismissing the set leaves the parent active and unchanged. Preserve the parent on billing, quota, authentication, moderation, timeout, malformed output, or persistence failure. Follow `__grounding/IMAGE_ITERATION.md`.
- After a selected candidate becomes a canonical version, create three medium-quality `TechnicalViewRecord` edits from that exact chosen raster: back, left side, and right side. Unselected candidates receive no derived views. Run the three calls concurrently, preserve the canonical version through partial failure, expose per-view status, and allow a failed or missing view to be retried without regenerating the garment.
- The LanceDB reference catalog is local, inspectable, and seeded only with project-authored illustrations. Label associations describe neutral trait overlap and never claim an official product, affiliation, or endorsement.
- The Inspiration library is a separate LanceDB catalog backed by `backend/seeds/product_inspiration.json`: 30 real sourced products for each of 20 labels. Enforce unique product, source, and image URLs; expose complete brand/category facets; return at most 30 contextual results per browse request; and retain product-page provenance. Never replace real product results with unsourced illustration cards.
- An Editorial render is a separate `PresentationRender` linked to one immutable `DesignVersion`; changing casting, pose, place, or light must never create or overwrite a garment version. The UI places it beside the canonical raster instead of swapping it into the canonical frame. Follow `__grounding/CASTING.md`.
- Expose `/api/health`. Keep API failures legible and never leak upstream error bodies or credentials to the browser.

## Canonical demo

The planned five-minute hackathon story is OpenAI DevDay swag: a distressed bomber over a white T-shirt. Durable object names are `Bomber jacket` and `T-shirt`; `FINISH / distressed` and `COLOR / white` belong to their active versions rather than the object names. The acceptance target is three authored raster versions: version 01 from a real `gpt-image-2` generation call, followed by versions 02 and 03 as successive Images API edits of the exact preceding raster.

Current status on 2026-07-17: three prepared `gpt-image-2` garment rasters and one fictional-adult editorial raster have an exact direct OpenAI generation/edit lineage recorded in `__grounding/DEV_DAY_IMAGE_GENERATION.md`. The startup importer checksum-verifies them into real local `DesignVersion` and `PresentationRender` records. ChatKit then made and persisted Version 04 through the same direct OpenAI edit path using Version 03's exact raster. Live failures must preserve the current view and report the blocked state. John Elliott remains only a neutral research signal—refined essentials, fabric focus, layered neutrals, and restrained proportion. The fictional adult presentation must not reproduce a John Elliott garment, campaign, or recognizable model.

## Repository skills

Prefer these portable skills under `__harness/skills/` over machine-specific wrappers. Read the selected skill's complete `SKILL.md` before using it.

- **create-image** — Generate a new concept or edit an existing design with `gpt-image-2`, preserving references and writing outputs to ignored local storage. Use it for garment studies, reference-conditioned iterations, and visual variations.
- **create-music** — Render an optional original focus track with Replicate's `google/lyria-3-pro` from a concrete musical brief. Use it only when original audio is requested; dry-run the payload before spending credits.
- **ask-gemini** — Request an independent Gemini research or large-context review and provide the relevant files. Treat its response as input, then verify material claims against primary sources or the repository.
- **ask-claude** — Run a read-only Claude architecture or code review from the repository context. Use it for a second opinion, then inspect every referenced file and synthesize the result yourself.
- **copywriter** — Draft restrained product, UX, editorial, or technical copy from explicit grounding. Review the output for accuracy, tone, and unwanted imitation before shipping it.

Keep each portable skill stripped to its runnable core: one concise instruction file, explicit repository-relative inputs, a small script, and only the references required to use it safely. Use standard environment-variable names, install dependencies at invocation time when practical, dry-run paid operations, and never encode a contributor's home directory, shell profile, provider account, or credential.

## Definition of done

A slice is done when the behavior works through its real path, relevant checks pass, the visible result has been inspected, accessibility and error states are accounted for, grounding is current, and the work is committed with a meaningful message. A rendered shell with disconnected controls is not complete.
