# Architecture

## System shape

```text
Browser — 127.0.0.1:43173
  Vite + React + TypeScript + Tailwind v4 + Motion
  ├── optional onboarding + safe local session seed
  ├── studio canvas + live React/SVG illustrations
  ├── Inspiration catalog and fictional-model presentation panels
  └── ChatKit surface or local read-only fallback
                     |
                     | Vite proxy: /api/*
                     v
FastAPI — 127.0.0.1:43174
  ├── /api/health and project/reference/presentation JSON APIs
  ├── LanceDB lexical catalog built from 30 committed studies
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
- the current object name; and
- safe link, catalog, or server-relative image references.

Blob-backed local upload previews are intentionally excluded because their object URLs cannot survive a reload. A returning designer opens the studio instead of replaying the tutorial. `New object` clears the current starting references and returns to the object stage while leaving onboarding complete.

The studio keeps the design conversation on the left and the active design centered. Its transformed plane supports:

- pointer drag and arrow-key pan;
- pointer-anchored wheel zoom clamped to 35–400%;
- Shift-wheel or bracket-key tilt clamped to ±12 degrees;
- explicit zoom, tilt, center, and keyboard reset controls; and
- a position-clamped right-click menu with Inspiration, Model, Inspect at 170%, Detail at 400%, Straighten, and Fit actions.

Every context-menu item changes visible state. Closing the menu returns focus to the canvas. The current implementation is an infinite-feeling bounded plane; introduce graph/canvas infrastructure only after this interaction model proves insufficient.

### Inspiration

The `Inspiration` action in the studio header opens a full-width panel over the canvas. It loads all 30 local studies, searches title/form/material/construction metadata, filters by a selected label, and ranks object and label overlap for the current project. Pulling a study creates a removable catalog reference on the canvas and includes it in the safe local project seed.

This replaces floating brand-note cards as the primary discovery pattern. Label associations are neutral trait metadata, never official product records, affiliation claims, or style-transfer instructions.

### Live illustrations

Editorial visuals are original React components, generally SVG composed with Motion. `LiveGarmentIllustration` animates reusable garment-outline components during onboarding; `DevDayLookStudy` changes garment geometry, material, and construction with the selected demo version. Both honor reduced motion and keep necessary copy in semantic HTML at the 16px product floor.

Live illustrations are source code and product state, not exported screenshots or disguised third-party icons. Follow `__grounding/ICONOGRAPHY.md` and the live-illustration contract in `AGENTS.md`.

## Deterministic DevDay demo

`/?demo=devday` bypasses onboarding and opens project id `devday-swag` with John Elliott selected as a neutral research signal and `DevDay distressed bomber + white T-shirt` as the object. Three switchable, original React/SVG looks make the demo deterministic and credit-free:

1. washed-charcoal flight proportions;
2. inside-out construction with exposed seams and orange bartacks; and
3. cropped mineral-olive utility construction.

The same original fictional adult and white tee make the garment delta legible across versions. The demo does not claim to render a John Elliott product, campaign, or recognizable model. Its casting action creates a local presentation fixture and status change; the real presentation endpoint remains available for projects with a canonical generated garment asset.

## Local reference catalog

`backend/seeds/reference_catalog.json` is the reviewable source of truth for exactly 30 project-authored reference studies. The matching SVG assets live under `app/public/reference-seeds/`. Each row records garment metadata, a local image URL, provenance, rights status, and a label association based on neutral trait overlap.

At API startup, `ReferenceCatalog.build()` validates the manifest, overwrites the ignored LanceDB `candidates` table, and creates a full-text index over composed lexical evidence. The adapter intentionally has no fake semantic-vector column: blank search returns manifest order, while nonblank search uses inspectable LanceDB FTS. Results may be filtered by label id, category, or object type and are capped at 30.

Rebuild or verify the committed SVGs and local index with `backend/scripts/build_reference_seeds.py`; runtime LanceDB files remain ignored.

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
- `render_design_iteration` — resolve authoritative assets, call `gpt-image-2`, append an immutable version, and complete a persisted generation job; and
- `update_canvas_object` — emit a bounded client effect so the browser refetches authoritative state.

Image generation is a material side effect. The UI must make it explicit, preserve the current ready version during progress or failure, and record enough metadata for lineage and undo.

## Design truth and presentation boundary

SQLite stores the design domain separately from ChatKit conversation items. Core records include `Project`, `Asset`, `DesignVersion`, `StyleProfile`, `CanvasNode`, `GenerationJob`, and `PresentationRender`.

A `DesignVersion` is immutable garment truth. A `PresentationRender` links to exactly one design version and stores a preset/control snapshot, assembled prompt, status, and separate generated asset. Changing casting, pose, place, or light creates another presentation; it never appends or overwrites a garment version. A real presentation request requires an existing canonical generated garment asset and returns `409` before generation when that invariant is missing.

The eight committed casting presets are fictional-adult art-direction bundles. Their chooser names never enter the image prompt. Controls for body, stature, skin tone, presentation, adult age, pose/access, and continuity move independently. Follow `__grounding/CASTING.md` for originality, inclusion, garment-drift, and real-person boundaries.

## Runtime storage

For the hackathon, SQLite stores ChatKit and design-domain data, while ignored local directories store uploads, generated media, and the rebuilt LanceDB catalog. Logical stores remain separate even where they share one SQLite file. Generated records use relative artifact ids/paths rather than machine-specific absolute paths.

Minimum generation-job behavior is `queued → running → succeeded | failed`, with an expected parent version and idempotency/tool-call key. Allow one in-flight edit per project and never replace the last ready version on failure.

Do not commit runtime databases, uploads, generated assets, logs, credentials, or browser profile data.

## API surface

- `GET /api/health` — safe readiness, configured model names, and public ChatKit domain configuration
- `GET /api/references` — browse/search up to 30 local studies; optional label/category/object filters
- `GET /api/casting-presets` — committed fictional-adult presentation directions and closed control vocabularies
- `GET /api/projects/{project_id}` — authoritative project, canvas, version, and presentation snapshot
- `PUT /api/projects/{project_id}` — create or update the bounded project seed
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
- Stale generation requests whose expected parent is no longer current are rejected.
- A presentation that changes the garment should be rejected as garment drift, not stored as a design version.
- Upstream bodies and credentials never pass through to the browser.

## Validation

- Frontend: type check, lint, production build, and browser QA against `127.0.0.1:43173`.
- Backend: Ruff formatting/linting, pytest, import smoke, `/api/health`, and mocked agent/image-provider contracts.
- Catalog: validate exactly 30 manifest rows, 30 deterministic SVGs, full category/label coverage, and the DevDay white-tee/bomber search case.
- Canvas: verify direct garment drag, pointer-anchored 35–400% zoom, tilt, reset, keyboard controls, and in-bounds context menus at representative desktop sizes.
- Demo: switch all three looks, pull and remove Inspiration studies, apply a local casting fixture, and reload without replaying onboarding.
- Integration: create/upsert a project, open ChatKit when configured, submit one change, and verify the client effect refetches the authoritative version without exposing secrets.
