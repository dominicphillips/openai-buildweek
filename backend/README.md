# SOMETHINGS-ON backend

The local FastAPI service owns the custom ChatKit endpoint, OpenAI Agents SDK design guide, immutable design records, controlled `gpt-image-2` edits, the 30-item LanceDB reference catalog, and lookbook presentations that never alter canonical garment versions.

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

## API surface

- `GET /api/health` — safe OpenAI/ChatKit readiness and configured model names
- `GET /api/references` — browse or search up to 30 local reference studies
- `GET /api/casting-presets` — eight fictional-adult art-direction presets and closed control vocabularies
- `GET /api/projects/{project_id}` — authoritative project snapshot
- `PUT /api/projects/{project_id}` — create or update the project seed
- `POST /api/projects/{project_id}/references` — validate and ingest an owned image
- `POST /api/projects/{project_id}/reference-links` — store a link card without fetching it
- `GET /api/assets/{asset_id}` — serve an owned local development asset
- `GET /api/projects/{project_id}/presentations` — list presentation renders
- `POST /api/projects/{project_id}/presentations` — create a separate lookbook view
- `POST /api/projects/{project_id}/chatkit` — custom ChatKit protocol for the project

## Design and presentation boundary

`DesignVersion` is immutable garment truth. `PresentationRender` is a separate record and asset linked to one version. Changing a fictional model, pose, place, lighting, or casting control creates another presentation and never mutates or appends a garment version.

`POST /api/projects/{project_id}/presentations` accepts a preset id, an optional canonical design version id, and closed-vocabulary casting controls. The selected version must already have a generated canonical asset. If it does not, the API returns `409` before calling the provider. Refer to `../__grounding/CASTING.md` for the prompt, originality, and garment-drift rules.

The frontend DevDay route uses a transparent local presentation fixture so the hackathon story remains deterministic and credit-free. It exercises presentation selection and the unchanged-design boundary, not the paid backend render path.

## Check

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

Tests use fake image providers and must not spend API credits. The catalog suite also checks the exact 30-item contract, deterministic SVG accessibility, complete neutral label coverage, and the DevDay white-tee/bomber retrieval case.

SQLite databases, LanceDB files, uploads, generated media, caches, logs, and real `.env` files are runtime-only and must not be committed.
