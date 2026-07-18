# SOMETHINGS-ON

SOMETHINGS-ON is a guided creative workspace for emerging fashion designers. It turns references and half-formed preferences into a visible loop: collect evidence, name what must stay, change one intentional detail, compare, and continue.

The name is an homage to Virgil Abloh and Nike's *Something's Off*, redirected toward creative momentum. This project is not endorsed by Virgil Abloh's estate, Nike, John Elliott, or any label represented as a research signal. It translates references into neutral traits; it does not reproduce products, campaigns, logos, or a living designer's style.

## Prototype

The current build includes:

- an optional, dark onboarding ritual with locally persisted completion, selected labels, object, and safe references;
- a 600-product Inspiration library—30 sourced products for each of 20 labels—indexed locally with LanceDB full-text search and complete browse facets;
- a top-level Inspiration panel that filters real product references and pulls them beside the current design;
- an expansive studio with pointer and keyboard pan, pointer-anchored 35–400% zoom, restrained tilt, fit/reset, and an in-bounds right-click tool menu;
- a four-candidate compare step for each authored image change, where only the designer's choice becomes the next immutable version;
- linked back, left, and right inspection views generated from the exact chosen canonical raster;
- original live React/SVG interface illustrations composed with Motion and reduced-motion support, kept separate from generated design truth;
- a separate fictional-adult Editorial layer that presents an immutable garment version without changing it; and
- a ready OpenAI DevDay story with three real direct-OpenAI garment rasters, exact edit lineage, a real editorial raster, and a working live ChatKit edit loop.

Chat can collapse on the left, the current design stays centered, and candidates, technical views, editorials, and references remain distinct canvas objects.

## Run locally

Requirements: Node.js with npm, Python 3.12–3.14, and [uv](https://docs.astral.sh/uv/). The visual shell, 600-product local index, canvas, and prepared DevDay V1–V3/editorial story start without making a paid API call. New chat-guided edits and Editorial renders use the configured OpenAI account.

Start the API in one terminal:

```bash
cd backend
uv sync
uv run python scripts/cache_product_images.py
uv run python scripts/cache_product_images.py --verify
uv run uvicorn somethings_on.main:app --host 127.0.0.1 --port 43174
```

Start the frontend in a second terminal:

```bash
cd app
npm ci
npm run dev
```

Open `http://127.0.0.1:43173`. Both processes use strict high ports: the frontend is always `43173`, and the API is always `43174`. A collision fails visibly instead of moving the service to another port.

For the production-style preview used during visual QA:

```bash
cd app
npm run build
npm run preview
```

## Demo route

Open `http://127.0.0.1:43173/?demo=devday` for the five-minute hackathon story. It bypasses onboarding and opens three immutable `gpt-image-2` garment versions imported through the same backend asset/version APIs used by live work:

1. a washed-charcoal flight bomber over a white T-shirt;
2. an inside-out construction study with exposed seams and orange bartacks; and
3. the exact Version 02 raster edited only to shorten the bomber body to a high-hip crop.

Version 01 is a direct OpenAI generation. Version 02 edits Version 01's exact PNG, and Version 03 edits Version 02's exact PNG. The prepared fictional-adult editorial is a separate real `gpt-image-2` output linked to Version 03. Prompts, OpenAI request ids, hashes, and parent inputs are recorded in `__grounding/DEV_DAY_IMAGE_GENERATION.md`. A new ChatKit instruction sends the selected current raster through one direct OpenAI edit request with four outputs. Those candidates stay outside version history until the designer chooses one; only the selected image becomes the immutable child and receives its technical views.

John Elliott is used only as a taste signal translated into refined essentials, fabric focus, layered neutrals, and restrained proportion. The generated garments and fictional model are original project work; the app does not claim a John Elliott product, campaign, or endorsement. Selecting a new Editorial direction calls the real presentation endpoint, spends image credits, and never alters the garment version.

## Studio controls

- Drag anywhere outside an interactive control to pan.
- Scroll to zoom around the pointer from 35% to 400%.
- Hold Shift while scrolling, or use `[` and `]`, to tilt.
- Use arrow keys to pan; hold Shift for a larger step.
- Use `+` / `-` to zoom and `0` to fit the composition.
- Press `I` for Inspiration and `M` for the Editorial panel.
- Right-click for Inspiration, Editorial, Inspect at 170%, Detail at 400%, Straighten, and Fit tools.

The top Inspiration panel searches the 600-product library. The default view returns up to 30 references related to the active object; choose a label plus “All objects” to browse all 30 products for that label. Product cards retain their real source URL, while any extracted traits remain neutral observations rather than affiliation or style-transfer instructions. The cache command above downloads private local research copies into ignored `backend/data/product-images/`; the browser then loads versioned same-origin images instead of hotlinking brand sites. Re-run the command to resume missing downloads, or use `--verify` for an offline integrity check.

## OpenAI and ChatKit configuration

Copy `backend/.env.example` to the ignored `backend/.env` only when you need OpenAI-backed chat or generation. Never put credentials in the frontend.

For local runs, `backend/.env` takes precedence over inherited shell variables so an unrelated global key cannot silently select another OpenAI account.

- `OPENAI_API_KEY` enables the Agents SDK design guide and `gpt-image-2` generation.
- `SOMETHINGS_ON_CHATKIT_DOMAIN_KEY` supplies the public browser domain configuration required by the hosted ChatKit surface.
- `/api/health` reports `chatkit_ready: true` only when both values are configured. Otherwise, the app keeps the studio usable and shows a local read-only conversation fallback.

Uploaded references, generated assets, SQLite files, and the runtime LanceDB directory stay in ignored backend storage. Onboarding completion and the last safe project seed are kept in browser local storage; object URLs for unsaved local uploads are deliberately not restored after a reload.

## Verify

Frontend:

```bash
cd app
npm run typecheck
npm run lint
npm run build
```

Backend:

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

The backend tests use fake image providers and must not spend API credits. Finish visible changes with a browser pass against the strict preview URL.

## Repository map

- `app/` — Vite, React, TypeScript, Tailwind CSS v4, Motion, ChatKit, and locally owned Radix ScrollArea/Select primitives
- `backend/` — FastAPI, OpenAI Agents SDK, custom ChatKit server protocol, SQLite domain storage, and separate LanceDB reference/product catalogs
- `__grounding/` — product decisions, architecture, sources, casting rules, brand research, and iconography
- `__harness/skills/` — stripped-down, project-owned creative and review skills that use explicit inputs and standard environment variables
- `AGENTS.md` — work loop, orchestration, visual, security, and commit contracts for contributors and agents

Read `AGENTS.md` and the grounding index before changing product behavior or visual direction.
