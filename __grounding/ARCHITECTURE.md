# Architecture

## Shape

```text
Browser
  app/ — Vite + React + TypeScript + Tailwind v4 + Motion
    |
    | custom ChatKit protocol + JSON/file endpoints
    v
backend/ — FastAPI
  ChatKitServer adapter
    |
    v
  OpenAI Agents SDK — one design guide agent + narrow function tools
    |                         |
    |                         +-- canvas/client tool requests
    +-- reference analysis
    +-- gpt-image-2 generation and edits
```

## Local ports

- Frontend preview: `127.0.0.1:43173`
- Backend API: `127.0.0.1:43174`

Both are strict so a collision fails visibly instead of silently selecting another port. The frontend build reads only the public `VITE_API_BASE_URL`, defaulting to the backend URL above.

## ChatKit decision

Use the custom/self-hosted ChatKit server integration for new work. The backend owns the ChatKit protocol endpoint and connects it to an Agents SDK runner; do not build a new dependency on an Agent Builder workflow during its transition window.

ChatKit is the conversation surface and its store is canonical for thread/items. A separate design store owns projects, references, piles, selection, generation jobs, and immutable versions. Link the two with `project_id` and `thread_id`; do not use an Agents SDK session at the same time or duplicate history.

For each turn, the ChatKit adapter converts the bounded recent thread history into agent input and runs an ephemeral streamed `Runner`. Keep all SDK-specific conversion and protocol code behind `backend/chatkit/` adapters.

## Initial agent contract

Goal: help the designer articulate and perform one intentional, traceable design change.

Inputs:

- active project and object summary
- selected design version
- selected references or pile
- approved taste traits
- user message

Tools:

- `analyze_inspiration` — extract neutral attributes from user-provided references
- `propose_design_change` — return the single delta, invariants, and an image prompt plan
- `render_design_iteration` — resolve authoritative asset bytes, call `gpt-image-2`, append an immutable version, and complete a persisted generation job
- `update_canvas_object` — emit a small client effect containing only project/version ids so the browser refetches authoritative state

The image tool is a material side effect. It must be explicit in the UI, show progress, and return enough metadata for provenance and undo.

## Runtime storage

For the hackathon, use SQLite-backed ChatKit and domain state plus ignored local directories for uploads and generated media. ChatKit tables and design-domain tables remain logically separate even when they share one database. Keep storage interfaces narrow so object storage and a production database can replace them later.

Minimum domain records are `Project`, `Asset`, `DesignVersion`, `StyleProfile`, `CanvasNode`, and `GenerationJob`. A job records `queued → running → succeeded|failed`, its expected parent version, and an idempotency/tool-call key. Allow one in-flight image edit per project and never replace the last ready version on failure.

Never commit runtime data. A generated design record stores a relative artifact id/path, not a machine-specific absolute path.

## API surface

- `GET /health` — readiness and safe configuration summary
- `POST /chatkit` — self-hosted ChatKit protocol
- `POST /api/projects` — create the initial project and taste profile
- `GET /api/projects/{project_id}` — authoritative project/canvas/version snapshot
- `POST /api/projects/{project_id}/assets` — validated image upload owned by the project
- `POST /api/projects/{project_id}/chatkit` — self-hosted ChatKit protocol with validated project context
- `GET /api/assets/{asset_id}` — authorized local asset delivery in development

The exact ChatKit store/file-store methods follow the installed SDK version and official examples. Avoid inventing a second conversation protocol beside ChatKit.

## Frontend state boundary

Keep transient onboarding UI state in React, then persist the project before entering the studio. Isolate API calls in `src/lib/api.ts` and domain types in `src/lib/types.ts`; components should not know OpenAI request shapes.

The canvas begins as an infinite-feeling but bounded transformed plane rather than unbounded graph infrastructure. Introduce a canvas dependency only after pan/zoom, piles, selection, and centered-design behavior prove the need.

Disable ChatKit composer attachments for the first slice so there is one upload path. Do not server-fetch arbitrary pasted URLs; save them as link cards until a sandboxed fetcher with SSRF protections exists.

## Error and safety states

- missing server configuration: keep the visual shell usable and show a concise setup state in chat
- unsupported/failed upload: preserve the rest of the selection and identify the failed item
- image generation in progress: stable current version plus non-blocking progress
- moderation block: neutral correction prompt; no automatic identical retry
- rate limit/transient upstream failure: bounded retry guidance and preserved request plan
- lost ChatKit connection: reconnect without discarding local canvas work
- stale edit: reject an image request whose expected parent version is no longer current
- unsafe upload: stream to a size cap, decode and re-encode with Pillow, strip metadata, cap pixels, and reject SVG/GIF/HTML/polyglots

## Validation

- frontend: lint, type check, production build, and browser pass at the preview URL
- backend: Ruff, pytest, import smoke, `/health`, and mocked agent/image tool contract tests
- integration: create/open a ChatKit thread, submit a message, and verify a client effect can refetch the selected canvas object without exposing secrets
- browser: intro → brands → upload → generate → edit current version → reload, with a deterministic fake image provider for the default test path
