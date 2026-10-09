# Current backend connection

Base URL: https://sema-care-production.up.railway.app

Verified on 9 October 2026 with the same original user-provided API key:
- Health: HTTP 200.
- All 10 demo lines: GET /v1/lines/{encoded-msisdn}/usage?months=6 returns HTTP 200, six months, valid schema.
- GET /v1/usage/summary?months=6: HTTP 200, six months, valid schema.
- OpenAPI now lists usage routes.
- Frontend and local server-side proxy read real backend data. Production uses the same Netlify proxy and existing SEMA_BACKEND_URL / SEMA_API_KEY environment variables. Keep VITE_USE_MOCK unset.

No key is included in this source archive. Retain the existing Netlify server environment variables when committing these files to the existing repository.
