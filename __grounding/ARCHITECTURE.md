# Architecture

## System shape

```text
Browser — 127.0.0.1:43173
  Vite + React + TypeScript + Tailwind v4 + Motion
  ├── optional onboarding + safe local session seed
  ├── studio canvas + four-way candidate comparison + immutable chosen versions
  ├── clearly separated React/SVG interface illustrations
  ├── Inspiration catalog and Editorial presentation panels
  └── ChatKit surface or local read-only fallback
                     |
                     | Vite proxy: /api/*
                     v
FastAPI — 127.0.0.1:43174
  ├── /api/health and project/reference/presentation JSON APIs
  ├── LanceDB lexical catalogs: 30 authored studies + 600 sourced products
  ├── SQLite design-domain and ChatKit stores
  ├── custom ChatKit server adapter
  └── OpenAI Agents SDK design guide
          └── gpt-image-2 generation and edits
```

The product has one browser application and one local API. Conversation, design truth, reference search, and presentation renders have explicit boundaries even when their local persistence shares a process or database.

## Strict local ports

- Frontend development and preview: `http://127.0.0.1:43173`
- Backend API: `http://127.0.0.1:43174`

Vite uses `strictPort` and proxies relative `/api` requests to port `43174`. The backend allows the frontend origin on `43173`. Keep these high ports fixed in scripts, documentation, screenshots, and browser tests so a collision fails rather than silently changing the demo URL.

## Frontend experience and state

The onboarding sequence is optional. React owns in-progress ritual state. Once the studio opens, the browser persists a bounded seed under `somethings-on:studio-session:v1`:

- onboarding completion;
- up to five recognized label ids;
- the current durable object name; and
- safe link, catalog, or server-relative image references.

Blob-backed local upload previews are intentionally excluded because their object URLs cannot survive a reload. A returning designer opens the studio instead of replaying the tutorial. `New object` clears the current starting references and returns to the object stage while leaving onboarding complete.

Object names store durable garment categories such as `T-shirt`. Color, finish, fit, material, and construction belong to a `DesignVersion`; do not encode them into an object name such as `white T-shirt`.

The studio keeps the design conversation on the left and the active design centered. The conversation can collapse into a compact rail so the canvas reclaims its width. ChatKit stays mounted and becomes inert while hidden, preserving the active thread and version-bound request routing; the local collapsed preference survives reloads. A completed authored change opens a four-image comparison over the canvas; only the chosen candidate joins version history. Its transformed plane supports:

- pointer drag and arrow-key pan;
- pointer-anchored wheel zoom clamped to 35–400%;
- Shift-wheel or bracket-key tilt clamped to ±12 degrees;
- explicit zoom, tilt, center, and keyboard reset controls; and
- a position-clamped right-click menu with Inspiration, Editorial, Inspect at 170%, Detail at 400%, Straighten, and Fit actions.

Every context-menu item changes visible state. Closing the menu returns focus to the canvas. The current implementation is an infinite-feeling bounded plane; introduce graph/canvas infrastructure only after this interaction model proves insufficient.

### Inspiration

The `Inspiration` action in the studio header opens a full-width panel over the canvas. It browses a 600-product LanceDB catalog with exactly 30 sourced products for each of 20 labels. The backend returns complete brand/category facets and at most 30 contextual results per request; search and label/category filters stay server-side. Pulling a product creates a removable reference beside the design and includes its safe metadata in the local project seed.

This replaces floating brand-note cards as the primary discovery pattern. Product records link to their real source pages, while extracted traits stay neutral and never imply affiliation, endorsement, or an instruction to copy a label's style.

### Live illustrations

Editorial visuals are original React components, generally SVG composed with Motion. `LiveGarmentIllustration` can animate reusable garment-outline components during onboarding. These components honor reduced motion and keep necessary copy in semantic HTML at the 16px product floor.

Live illustrations are source code and product state, not exported screenshots or disguised third-party icons. Follow `__grounding/ICONOGRAPHY.md` and the live-illustration contract in `AGENTS.md`.

They are also not generated design truth. A React/SVG study cannot be stored as a `DesignVersion` or `PresentationRender`, cannot stand in for a successful Images API response, and cannot be the primary DevDay object. Any offline illustration visible near the studio is explicitly labeled `ILLUSTRATION / NON-PRODUCTION` and remains outside version lineage.

## DevDay live-raster target

`/?demo=devday` is intended to bypass onboarding and open project id `devday-swag` with John Elliott selected as a neutral research signal. Its reserved combined demo label is `DevDay distressed bomber + white T-shirt`; ordinary project object names remain durable categories, with finish and color stored as version properties. The acceptance target is three switchable `gpt-image-2` raster outputs with explicit lineage:

1. generate a canonical washed-charcoal flight-proportion version;
2. edit that exact raster into an inside-out construction with exposed seams and orange bartacks; and
3. edit the exact current raster by shortening only the bomber body to a high-hip crop.

Current status on 2026-07-17: the three switchable garment assets and V3 fictional-adult presentation are real `gpt-image-2` outputs produced through the direct OpenAI Images API. Version 01 is a generation; Version 02 edits the exact Version 01 PNG; Version 03 edits the exact Version 02 PNG. Their prompts, request ids, settings, and hashes are recorded in `DEV_DAY_IMAGE_GENERATION.md`. At backend startup, an idempotent importer verifies and copies those committed bytes into ignored runtime storage, materializes ready V1/V2/V3 records with exact parent lineage, and links the ready `edgy-european-guy` presentation to V3. It never calls the provider, fabricates output, or overwrites a diverged user-authored project. A verified live ChatKit turn created Version 04 by editing Version 03's exact stored raster through the same direct OpenAI path.

Each later edit must name one delta and preserve explicit invariants. Prepared demo assets may be committed only with model, prompt, settings, parent, and content-hash provenance. All other generated media remains outside Git.

The canonical garment raster should remain presentation-neutral enough to inspect. A fictional adult lookbook image is a separate `PresentationRender` linked to a chosen immutable version; casting never becomes the next garment version. The demo does not claim to render a John Elliott product, campaign, or recognizable model.

The demo is not ready when required raster generation fails. Billing, quota, authentication, moderation, timeout, or provider errors leave the previous version visible and produce an honest failure state; no SVG, placeholder, or cached unrelated image is promoted as the requested draft.

## Local reference catalog

`backend/seeds/reference_catalog.json` is the reviewable source of truth for exactly 30 project-authored reference studies. The matching SVG assets live under `app/public/reference-seeds/`. Each row records garment metadata, a local image URL, provenance, rights status, and a label association based on neutral trait overlap.

At API startup, `ReferenceCatalog.build()` validates the manifest, overwrites the ignored LanceDB `candidates` table, and creates a full-text index over composed lexical evidence. The adapter intentionally has no fake semantic-vector column: blank search returns manifest order, while nonblank search uses inspectable LanceDB FTS. Results may be filtered by label id, category, or object type and are capped at 30.

Rebuild or verify the committed SVGs and local index with `backend/scripts/build_reference_seeds.py`; runtime LanceDB files remain ignored.

## Product inspiration catalog

`backend/seeds/product_inspiration.json` is the runtime source of truth for 600 sourced product records: 30 each from the five core labels and fifteen adjacent labels in `BRANDS.md`. `__grounding/INSPIRATION_PRODUCTS_600.json` is the review copy; the core and adjacent research manifests retain their collection provenance.

At startup, `ProductCatalog.build()` requires 20 brands × 30 products, contiguous order, unique ids, unique source URLs, unique image URLs, and valid metadata before replacing the ignored LanceDB `official_products` table. It creates an FTS index over product identity and neutral construction evidence. `/api/inspiration/facets` exposes the complete browse vocabulary; `/api/inspiration` applies server-side search and filters and caps each response at 30. `scripts/cache_product_images.py` creates a validated, ignored WebP cache with a source-preserving index; `/api/inspiration/images/{product_id}` serves those files through same-origin versioned URLs so the browser never hotlinks a source host.

The external product images are shown only in the local hackathon research prototype. They remain third-party, all-rights-reserved material; production must obtain permission or replace them with licensed/project-owned assets rather than treating this manifest as a license.

## ChatKit and agent boundary

The backend owns the custom/self-hosted ChatKit protocol at `/api/projects/{project_id}/chatkit` and connects it to an ephemeral streamed OpenAI Agents SDK runner. Do not invent a second conversation protocol or duplicate ChatKit history in an Agents SDK session.

ChatKit readiness requires two independent settings:

- `OPENAI_API_KEY` enables the design agent and image provider; and
- `SOMETHINGS_ON_CHATKIT_DOMAIN_KEY` is the public domain configuration consumed by the browser ChatKit component.

`GET /api/health` returns model names, the public ChatKit domain key, and `chatkit_ready`. Readiness is true only when both settings are present. If either is missing, the frontend does not mount the hosted ChatKit surface; it shows a local, read-only guide card while the rest of the studio and catalog remain usable. API credentials stay server-side and are never returned by health or bundled into browser code.

For each turn, the ChatKit adapter converts bounded recent thread history into agent input, supplies validated `project_id` context, and streams the runner response. A `design.version.created` client effect contains identifiers only and tells the browser to refetch authoritative project state.

### Design agent contract

Goal: help the designer articulate and perform one intentional, traceable design change.

Inputs:

- active project and object summary;
- selected immutable design version;
- selected references or pile;
- approved neutral taste traits; and
- the designer's message.

Tools:

- `analyze_inspiration` — extract neutral attributes from user-provided references;
- `propose_design_change` — return one delta, invariants, and an image prompt plan;
- `render_design_iteration` — resolve authoritative assets, call `gpt-image-2` for four candidates, and complete a persisted generation job without advancing version history; and
- `update_canvas_object` — emit a bounded client effect so the browser refetches authoritative state.

Image generation is a material side effect. The UI must make it explicit, preserve the current ready version during progress, comparison, dismissal, or failure, and record enough metadata for candidate provenance, accepted lineage, and undo.

### Raster iteration transaction

The first design image and every child use different Images API operations:

1. Version 01 candidates use `gpt-image-2` generation from the approved object brief, neutralized reference analysis, and constraints. Later requests resolve the asset owned by the selected `DesignVersion`; its exact raster bytes are the sole canonical edit input.
2. The prompt contains one requested delta and an explicit `KEEP` list for silhouette, construction, material, color, graphics, camera/view, and every other unchanged property that matters. Do not generate from text alone or substitute another ancestor.
3. Make one Image API request with `n=4`. Normalize and persist all four outputs as a durable candidate set tied to one job and parent; do not append versions yet.
4. Keep the parent visible while the designer compares the set. Choosing one candidate atomically appends the child `DesignVersion`, dismisses its siblings, and moves canvas selection. Keeping the current version dismisses the whole set.
5. Only the selected candidate receives concurrent back, left, and right technical views. On any generation, persistence, selection, or derived-view failure, do not mutate or discard the previous canonical version.

Inspiration images help the agent extract neutral traits before iteration. They are not competing canonical design images in the mutation call. Full rules and an acceptance checklist live in `__grounding/IMAGE_ITERATION.md`.

## Design truth and presentation boundary

SQLite stores the design domain separately from ChatKit conversation items. Core records include `Project`, `Asset`, `GenerationJob`, `DesignCandidate`, `DesignVersion`, `TechnicalView`, `CanvasNode`, and `PresentationRender`.

A `DesignVersion` is immutable garment truth. A `PresentationRender` links to exactly one design version and stores a preset/control snapshot, assembled prompt, status, and separate generated asset. Changing casting, pose, place, or light creates another presentation; it never appends or overwrites a garment version. A real presentation request requires an existing canonical generated garment asset and returns `409` before generation when that invariant is missing.

The eight committed casting presets are fictional-adult art-direction bundles. Their chooser names never enter the image prompt. Controls for body, stature, skin tone, presentation, adult age, pose/access, and continuity move independently. Follow `__grounding/CASTING.md` for originality, inclusion, garment-drift, and real-person boundaries.

## Runtime storage

For the hackathon, SQLite stores ChatKit and design-domain data, while ignored local directories store uploads, generated media, and the rebuilt LanceDB catalog. Logical stores remain separate even where they share one SQLite file. Generated records use relative artifact ids/paths rather than machine-specific absolute paths.

Minimum generation-job behavior is `queued → running → succeeded | failed`, with an expected parent version and idempotency/tool-call key. Allow one in-flight edit per project and never replace the last ready version on failure.

Do not commit runtime databases, uploads, generated assets, logs, credentials, or browser profile data.

## API surface

- `GET /api/health` — safe readiness, configured model names, and public ChatKit domain configuration
- `GET /api/references` — browse/search up to 30 local studies; optional label/category/object filters
- `GET /api/inspiration` — browse/search up to 30 real product records; optional brand/category/object filters
- `GET /api/inspiration/facets` — complete product-library brand/category/object counts
- `GET /api/inspiration/images/{product_id}` — serve a validated same-origin product research image
- `GET /api/casting-presets` — committed fictional-adult presentation directions and closed control vocabularies
- `GET /api/projects/{project_id}` — authoritative project, canvas, version, and presentation snapshot
- `PUT /api/projects/{project_id}` — create or update the bounded project seed
- `POST /api/projects/{project_id}/versions` — generate the first raster or edit an exact selected raster into a new immutable child
- `POST /api/projects/{project_id}/candidate-sets` — request four draft rasters from one exact prompt and parent without creating a version
- `POST /api/projects/{project_id}/candidate-sets/{job_id}/select/{candidate_id}` — atomically promote one candidate into a canonical version
- `POST /api/projects/{project_id}/candidate-sets/{job_id}/dismiss` — discard a candidate set while preserving the current version
- `GET /api/projects/{project_id}/versions/{version_id}/technical-views` — list back, left, and right views derived from one canonical version
- `POST /api/projects/{project_id}/versions/{version_id}/technical-views/{role}` — render or retry one derived view from the exact canonical raster
- `POST /api/projects/{project_id}/references` — validate, sanitize, and ingest a local image
- `POST /api/projects/{project_id}/reference-links` — save a link card without server-fetching its URL
- `GET /api/assets/{asset_id}` — serve an owned local development asset
- `GET /api/projects/{project_id}/presentations` — list separate lookbook renders
- `POST /api/projects/{project_id}/presentations` — generate a presentation from an immutable canonical garment version
- `POST /api/projects/{project_id}/chatkit` — custom ChatKit protocol with validated project context

## Error and safety states

- Missing OpenAI or ChatKit configuration keeps the shell and local catalog usable.
- Unsupported uploads preserve the rest of the selection and identify the failed item.
- Uploads stream to a byte cap, decode and re-encode with Pillow, strip metadata, cap pixels, and reject SVG/GIF/HTML/polyglots.
- Pasted URLs are stored as cards and are never fetched server-side, avoiding an SSRF path.
- Moderation blocks are neutral, user-correctable states with no automatic identical retry.
- Billing, quota, authentication, rate-limit, timeout, and provider failures are recorded under a safe error category and reported honestly in development/demo readiness. The browser receives a useful product state, never a fabricated success or raw upstream body.
- Stale generation requests whose expected parent is no longer current are rejected.
- A presentation that changes the garment should be rejected as garment drift, not stored as a design version.
- Upstream bodies and credentials never pass through to the browser.

## Validation

- Frontend: type check, lint, production build, and browser QA against `127.0.0.1:43173`.
- Backend: Ruff formatting/linting, pytest, import smoke, `/api/health`, and mocked agent/image-provider contracts.
- Catalogs: validate the 30 deterministic authored SVG studies; validate 600 unique sourced products with exactly 30 per label; verify facets, search/filter behavior, and the DevDay white-tee/bomber context.
- Canvas: verify direct garment drag, pointer-anchored 35–400% zoom, tilt, reset, keyboard controls, and in-bounds context menus at representative desktop sizes.
- Demo: verify version 01 has real generation provenance, versions 02 and 03 each point to the exact preceding raster, then switch all three looks, pull and remove real Inspiration products, create a separate presentation render, and reload without replaying onboarding.
- Integration: create/upsert a project, open ChatKit when configured, submit one change, verify a real Images API edit appends an immutable child and the client effect refetches it, then force a provider failure and verify the parent survives without exposing secrets.
