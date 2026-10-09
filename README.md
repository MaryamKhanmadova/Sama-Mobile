# Səma Mobile

React + TypeScript + Vite + Tailwind CSS + shadcn/ui. Two pages: customer chat/voice UI and support dashboard. Ayla is the customer assistant. Fictional telecom operator; all bundled data is synthetic.

## Start

```sh
npm ci
npm run dev
```

```sh
npm test
npm run build
```

Customer page: `/#/support`. Dashboard: `/#/dashboard` (also `/dashboard` with Netlify SPA rewrite).

## Deploy now — demo

Unzip `sema-mobile-deploy.zip` and drag the folder containing `index.html` into Netlify Drop. It is already built, requires no backend or environment variables, and runs with synthetic browser-local data. Chat history and dashboard share the same demo records. Voice controls are a UI simulation; no sound, telephone call or SMS is transmitted.

## Deploy from Git — connect backend later

Push the contents of this source folder to your repository. Netlify: build command `npm run build`, publish directory `dist`; `netlify.toml` is included. The Edge function in `netlify/edge-functions/sema-api.js` is deployed with the source build.

When the backend is ready, add the variables listed in `.env.example` to Netlify:

- `VITE_DATA_MODE=api`
- `VITE_API_BASE_URL=/api`
- `SEMA_BACKEND_URL`: backend base URL, without `/v1`
- `SEMA_API_KEY`: web API key (server only)
- `SEMA_ACCESS_TOKEN`: private access code for synthetic demo participants
- `SEMA_DEMO_MSISDN`: one synthetic seed line, default `+994981001644`

Rebuild/deploy. Enter the private demo access code on the customer page, then use chat or dashboard. Never put backend credentials in `VITE_*` variables. The proxy is gated with the private code, only forwards allowed routes, and forces the configured synthetic line at verification level 1. This is a hackathon access gate, not a production customer authentication system.

Static drag-and-drop deploys do not install this Edge function. Use a Git/Netlify source build when connecting the backend.

## API

The client follows the uploaded Səma Mobile backend specification v1.0:

- Creates `/v1/sessions`.
- Sends `/v1/sessions/{id}/messages:stream` and consumes SSE ack/status/delta/action/handoff/final/error/done.
- Resumes an interrupted event body via `/events` with `Last-Event-ID`; it never automatically resubmits the monetary request.
- Reads `/v1/cases` and `/v1/cases/{case_id}` for dashboard and evidence.
- Does not call unsupported status/assignment endpoints. Those controls are demo-only.

See `docs/INTEGRATION.md` for mapping and remaining backend contract gaps. Integration code and proxy are implemented and locally tested; no deployed backend has been verified. ElevenLabs voice transport, authentication for real customers, DB seeds, RAG and policy execution belong to the backend/voice team. No financial policy or detector is executed in the frontend.

## Branding and avatar

Səma Mobile uses purple `#5C2483`. Current image: `public/agent-avatar.png`. It is a temporary rendered avatar, not a live 3D model. Replace the avatar component in `src/App.tsx` when the user supplies the model and its format.
