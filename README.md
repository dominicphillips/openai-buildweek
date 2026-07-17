# SOMETHINGS-ON

SOMETHINGS-ON is a guided creative workspace for emerging fashion designers. It turns references and half-formed preferences into a visible loop: collect evidence, name what must stay, change one intentional detail, compare, and continue.

The name is an homage to Virgil Abloh and Nike's *Something's Off*, redirected toward creative momentum. This project is not endorsed by Virgil Abloh's estate, Nike, John Elliott, or any label represented as a research signal. It translates references into neutral traits; it does not reproduce products, campaigns, logos, or a living designer's style.

## Prototype

The current build includes:

- an optional, dark onboarding ritual with locally persisted completion, selected labels, object, and safe references;
- an inspectable 30-item catalog of project-authored garment illustrations, indexed locally with LanceDB full-text search;
- a top-level Inspiration panel that filters and pulls catalog studies onto the canvas;
- an expansive studio with pointer and keyboard pan, pointer-anchored 35–400% zoom, restrained tilt, fit/reset, and an in-bounds right-click tool menu;
- original live React/SVG illustrations composed with Motion and reduced-motion support;
- a separate fictional-adult casting layer that presents an immutable garment version without changing it; and
- a deterministic OpenAI DevDay demo with a distressed bomber, white T-shirt, fictional adult model, and three switchable authored looks.

Chat stays on the left, the current design stays centered, and references remain within reach.

## Run locally

Requirements: Node.js with npm, Python 3.12–3.14, and [uv](https://docs.astral.sh/uv/). The visual shell, local catalog, canvas, and DevDay demo run without paid API calls.

Start the API in one terminal:

```bash
cd backend
uv sync
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

Open `http://127.0.0.1:43173/?demo=devday` for the five-minute hackathon story. It bypasses onboarding and opens three authored React/SVG studies of OpenAI DevDay swag:

1. a washed-charcoal flight bomber over a white T-shirt;
2. an inside-out construction study with exposed seams and orange bartacks; and
3. a cropped mineral-olive utility version.

John Elliott is used only as a taste signal translated into refined essentials, fabric focus, layered neutrals, and restrained proportion. The garments, model, setting, and illustrations are original project work. Selecting a casting direction in this deterministic demo applies a local presentation fixture; it does not spend image credits or alter the selected garment version.

## Studio controls

- Drag anywhere outside an interactive control to pan.
- Scroll to zoom around the pointer from 35% to 400%.
- Hold Shift while scrolling, or use `[` and `]`, to tilt.
- Use arrow keys to pan; hold Shift for a larger step.
- Use `+` / `-` to zoom and `0` to fit the composition.
- Press `I` for Inspiration and `M` for the fictional-model presentation panel.
- Right-click for Inspiration, Model, Inspect at 170%, Detail at 400%, Straighten, and Fit tools.

The top Inspiration panel searches all 30 local studies. Selected labels and the active object influence relevance, while every association remains a neutral trait overlap rather than an official product claim.

## OpenAI and ChatKit configuration

Copy `backend/.env.example` to the ignored `backend/.env` only when you need OpenAI-backed chat or generation. Never put credentials in the frontend.

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

- `app/` — Vite, React, TypeScript, Tailwind CSS v4, Motion, ChatKit, and the local Radix ScrollArea primitive
- `backend/` — FastAPI, OpenAI Agents SDK, custom ChatKit server protocol, SQLite domain storage, and LanceDB catalog
- `__grounding/` — product decisions, architecture, sources, casting rules, brand research, and iconography
- `__harness/skills/` — stripped-down, project-owned creative and review skills that use explicit inputs and standard environment variables
- `AGENTS.md` — work loop, orchestration, visual, security, and commit contracts for contributors and agents

Read `AGENTS.md` and the grounding index before changing product behavior or visual direction.
