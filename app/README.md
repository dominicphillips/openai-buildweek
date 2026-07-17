# SOMETHINGS-ON frontend

The guided ritual and visual fashion studio for SOMETHINGS-ON. It uses React,
TypeScript, Vite, Tailwind CSS v4, Motion, and OpenAI ChatKit without a component
kit.

## Run

```bash
npm install
npm run dev
```

The development server uses `http://127.0.0.1:43173` and proxies `/api` to the
FastAPI service on `http://127.0.0.1:43174`.

For the production-style local preview used during the hackathon:

```bash
npm run build
npm run preview
```

Run `npm run lint` and `npm run typecheck` before committing frontend changes.
