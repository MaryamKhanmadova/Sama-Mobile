# Sama Care — Ayla / WebSocket

React + TypeScript + Vite + Tailwind CSS + shadcn/ui. Customer chat/voice page and operator dashboard, with the existing light/purple and dark layouts preserved.

## Run

```sh
npm ci
npm run dev
npm test
npm run build
```

Use Node 22.18+ for the TypeScript source tests. Customer page: `/#/support`; dashboard: `/#/dashboard`.

## Deploy now

Unzip **sama-care-final-deploy.zip** and drag the folder containing `index.html` into Netlify Drop. The package is already built for the supplied Railway backend. Enter the teammate's demo API key in the password field and click **Bağlan**. A session opens with the backend's greeting. Select a synthetic customer scenario in the dropdown and write your complaint. No build variables are required for the default WebSocket demo.

For Git/Netlify deployment, put this source folder's contents at the repository root. Build command: `npm run build`; publish directory: `dist`. Commit the updated files, then push; Netlify rebuilds automatically. `.env.example` documents optional overrides. Never commit a real `.env` file or API key.

## Integration

- REST `X-API-Key`, WebSocket `api_key` query parameter, per the supplied contract.
- Session opened via `POST /v1/sessions` with `{msisdn, channel:"web"}`; backend greeting appears immediately.
- Direct WSS `.../v1/sessions/{id}/ws`; sends `{type:"message",text}` and `{type:"interrupt",heard_text}`.
- Streams `delta` into Ayla's bubble; displays `status`, `action`, `handoff`, `final` and `done`.
- **Niyə?** reveals actual rule IDs, citations, root cause, amount and latency. No invented policy references.
- One turn at a time. Disconnects/errors do not replay a financial request. **Sessiyanı yoxla** fetches the stored transcript before allowing another turn.
- Demo customers from `/v1/demo/cases`; case list/detail from `/v1/cases`.
- Null amounts/root causes and backend `updated_at` fallback are handled.
- ElevenLabs voice widget loads after clicking **Ayla ilə canlı danış** in the voice tab. The public agent ID is configured; use the widget's own call controls. Actual microphone permission is requested by ElevenLabs. Voice and web sessions are separate; voice cases appear in the dashboard when the backend records them.

## Credentials / hosting modes

Default is the **direct synthetic demo**. The API key is entered at runtime and saved only in the current tab's sessionStorage. It is not bundled into the built assets, source archive or screenshots, and is not logged. The backend requires it in the WebSocket URL, so it is visible to that browser's user/network inspector. Use only the provided demo key and synthetic customers. A production system needs backend-issued scoped/short-lived session authentication.

An optional **SSE + Netlify Edge proxy** keeps the backend key server-side. Set the proxy variables in `.env.example` and deploy from source; Netlify Drop does not deploy Edge functions. The proxy accepts a private access code, forwards allowed HTTP routes, and pins sessions to one synthetic line. It does not proxy WebSocket upgrades. SSE remains available as a configured transport; there is no automatic fallback or POST replay after a WebSocket turn has been sent.

## Verified / remaining work

On 9 October 2026, authenticated Railway REST, CORS, session creation and live WebSocket event delivery were verified. Health now reports **llm_configured: true** with DynamoDB storage. A read-only Azerbaijani information request received 62 text deltas, an INFO decision with citations, and done without errors. A Russian browser request also completed normally. No refund, reset or account-changing scenario was executed in verification.

A case snapshot can include only a later assistant tool turn. The client retains the complete answer received through final/delta events while refreshing canonical status and evidence from case detail. Regression tests cover this behavior. UI language switching preserves the open chat and response content.

Voice widget integration follows the public embed contract; an actual microphone/voice call was not tested. The supplied 3D model is still pending. Assignment and close/reopen controls stay disabled in API mode because mutation endpoints were not supplied. No admin reset is exposed.

Dashboard aggregates describe the loaded cases, not system-wide telemetry; the backend does not currently supply an explicit AI/waiting queue state or human resolution path. See `docs/INTEGRATION.md`.

## UI localization

Header controls switch **AZ / EN / RU** immediately on both pages. The selected UI language persists through navigation and reload. AZ/EN come from the user's actual supplied contents; RU was translated separately. All three catalogs are in `src/locales/`. Dates, filters, CSV headings, errors and Why panels are localized. Customer/agent messages retain their original language. See `docs/LOCALIZATION.md`.
