# SOMETHINGS-ON backend

The local FastAPI service owns the custom ChatKit endpoint, OpenAI Agents SDK design guide, immutable design records, controlled `gpt-image-2` edits, a 30-study authored reference catalog, a 600-product Inspiration catalog, and editorial presentations that never alter canonical garment versions.

## Run

From this directory:

```bash
uv sync
uv run uvicorn somethings_on.main:app --host 127.0.0.1 --port 43174
```

The API uses the strict high port `43174`. Start the Vite frontend on `127.0.0.1:43173`; its development and preview servers proxy relative `/api` requests here.

The service can start without provider credentials. Project persistence, the local catalog, casting presets, deterministic frontend demo, and non-generation API paths remain available.

## Local configuration

Copy `.env.example` to the ignored `.env` only when you need to override defaults or enable OpenAI-backed behavior. Keep credentials server-side.

For local runs, this project-owned `backend/.env` is intentionally read before inherited shell variables so a stale global key cannot silently select another account. Explicit `Settings(...)` values used by tests or an embedding host still take highest priority; if the local file is absent, normal environment variables are used.

- `OPENAI_API_KEY` enables the Agents SDK guide and the OpenAI image provider.
- `SOMETHINGS_ON_CHATKIT_DOMAIN_KEY` is the public browser domain configuration for the hosted ChatKit component.
- `SOMETHINGS_ON_AGENT_MODEL` defaults to `gpt-5.6`.
- `SOMETHINGS_ON_IMAGE_MODEL` defaults to `gpt-image-2`.
- `SOMETHINGS_ON_DATABASE_PATH` and `SOMETHINGS_ON_ASSET_PATH` point to ignored local runtime storage.
- `SOMETHINGS_ON_ALLOWED_ORIGIN` defaults to the frontend on port `43173`.

`GET /api/health` returns safe model/readiness data and the public ChatKit domain key. `chatkit_ready` is true only when both the OpenAI API key and ChatKit domain key are configured. Without both, the frontend deliberately uses its local read-only conversation fallback instead of mounting ChatKit. The OpenAI API key is never returned.

## Local reference catalog

`seeds/reference_catalog.json` contains exactly 30 project-authored garment studies. At application startup, the service validates that manifest, rebuilds the ignored LanceDB `candidates` table, and creates a full-text index over inspectable lexical metadata. The committed matching SVGs live in `../app/public/reference-seeds/`.

Blank search preserves manifest order. Nonblank search uses LanceDB FTS; optional label, category, and object-type filters operate over stable metadata. The catalog does not use placeholder semantic vectors and never claims its label associations are official products or endorsements.

Regenerate the deterministic SVGs and runtime index:

```bash
uv run python scripts/build_reference_seeds.py
```

Verify committed SVGs without writing them:

```bash
uv run python scripts/build_reference_seeds.py --check
```

Use `--skip-db` when only the committed SVG assets should be rebuilt. Runtime LanceDB data stays outside Git.

## Product inspiration catalog

`seeds/product_inspiration.json` contains 600 sourced products: exactly 30 for each of 20 labels. Startup validation requires unique ids, unique product pages, unique image URLs, contiguous order, complete string/list fields, and the exact per-brand contract before rebuilding the ignored LanceDB `official_products` table.

`GET /api/inspiration/facets` returns complete brand/category/object counts. `GET /api/inspiration` applies FTS plus optional brand/category/object filters and returns at most 30 products, keeping the browser responsive without returning the full manifest. Records retain their source page and neutral construction metadata.

Build the ignored local research-image cache before opening Inspiration:

```bash
uv run python scripts/cache_product_images.py
uv run python scripts/cache_product_images.py --verify
```

The importer is resumable, validates every raster, resizes it to WebP, and writes a source-preserving SHA-256 index under `data/product-images/`. `GET /api/inspiration/images/{product_id}` then serves versioned same-origin images; the browser does not hotlink brand CDNs. These copies remain third-party, all-rights-reserved research material and are never committed or licensed for production use.

## API surface

- `GET /api/health` — safe OpenAI/ChatKit readiness and configured model names
- `GET /api/references` — browse or search up to 30 local reference studies
- `GET /api/inspiration` — browse or search up to 30 contextual products from the 600-product catalog
- `GET /api/inspiration/facets` — complete product-library browse facets
- `GET /api/inspiration/images/{product_id}` — serve a validated local research-cache image
- `GET /api/casting-presets` — eight fictional-adult art-direction presets and closed control vocabularies
- `GET /api/projects/{project_id}` — authoritative project snapshot
- `PUT /api/projects/{project_id}` — create or update the project seed
- `POST /api/projects/{project_id}/versions` — generate a first raster or append an exact-reference edit
- `POST /api/projects/{project_id}/references` — validate and ingest an owned image
- `POST /api/projects/{project_id}/reference-links` — store a link card without fetching it
- `GET /api/assets/{asset_id}` — serve an owned local development asset
- `GET /api/projects/{project_id}/presentations` — list presentation renders
- `POST /api/projects/{project_id}/presentations` — create a separate lookbook view
- `POST /api/projects/{project_id}/chatkit` — custom ChatKit protocol for the project

## Iterative design versions

The reserved local demo project `devday-swag` is ready on startup without spending API credits.
The service verifies the documented `gpt-image-2` outputs in `../app/public/devday/`, copies them
into ignored runtime asset storage, and exposes canonical V1 → V2 → V3 lineage plus the separate
V3 `edgy-european-guy` presentation through the normal project and asset APIs. Repeated startups
and matching project PUTs reuse the same records. If that project contains diverged user-authored
versions or presentations, the importer leaves it untouched. See
`../__grounding/DEV_DAY_IMAGE_GENERATION.md` for prompts, parent inputs, settings, and hashes.

The ChatKit design agent exposes the typed `create_design_revision` tool with one
`requested_change` plus optional `preserve` and `avoid` lists. The first confirmed
raster revision calls `gpt-image-2` generation because the latest concept has no
asset. After the output validates, that provisional concept becomes ready version
01 in place; a failed first attempt leaves it provisional. Every later revision
appends version 02, 03, and so on, resolves the selected immutable version's stored
PNG, and submits that exact file to the Images API edit path. Its prompt treats
the supplied raster as the sole visual truth and permits only the confirmed detail
to move.

Pass the visible canvas selection as
`POST /api/projects/{project_id}/chatkit?base_version_id=ver_<12 lowercase hex>`.
The route rejects an unknown or cross-project id with `404`, a selected concept
without a raster with `409`, and a malformed id with `422`. A valid id is carried
as local agent context and becomes the new version's `parent_version_id`, so an
older selection creates a real branch. Omitting the parameter preserves the
latest-version behavior; omit it for the first generate-only revision.

Provider output must decode as a safe raster before the service writes an asset,
materializes or appends a `DesignVersion`, or marks its `GenerationJob` successful.
SVG, empty, or otherwise unreadable output fails the job and leaves the current
and prior versions untouched. `GET /api/projects/{project_id}` returns the complete
version lineage; each ready version's `asset_url` resolves through
`GET /api/assets/{asset_id}` for comparison or rollback in the client.

Upstream ChatKit agent failures are converted into persisted assistant messages.
Authentication, model access, quota/billing, ordinary rate limits, timeout,
connection, provider availability, and request-configuration failures each receive
short corrective copy. Unfinished streamed items are removed, while raw provider
messages, response bodies, and credentials never enter the event stream.

## Design and presentation boundary

`DesignVersion` is immutable garment truth. `PresentationRender` is a separate record and asset linked to one version. Changing a fictional model, pose, place, lighting, or casting control creates another presentation and never mutates or appends a garment version.

`POST /api/projects/{project_id}/presentations` accepts a preset id, an optional canonical design version id, and closed-vocabulary casting controls. The selected version must already have a generated canonical asset. If it does not, the API returns `409` before calling the provider. Refer to `../__grounding/CASTING.md` for the prompt, originality, and garment-drift rules.

The frontend never fabricates a successful presentation. Editorial views always call the real
presentation endpoint and require a canonical generated raster first. If provider access is
unavailable, the current garment remains visible and the panel reports the provider error.

## Check

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Tests use fake image providers and must not spend API credits. The catalog suites check the exact 30-study authored contract, the 600-product/20-label/30-per-label contract, uniqueness, deterministic SVG accessibility, complete facets, and the DevDay white-tee/bomber retrieval case.

SQLite databases, LanceDB files, uploads, generated media, caches, logs, and real `.env` files are runtime-only and must not be committed.
