# Səma Mobile — Məryəm

Telekom abunəçisinin hesab və bağlantı problemlərini chat və səsli zəngdə həll edən AI müştəri mütəxəssisi.
NeuroBridge Bakı 2026, AI Enterprise Solutions. Bütün data sintetikdir, Səma Mobile fiktiv operatordur.

| Qovluq | Nə var | Deploy |
|---|---|---|
| [`frontend/`](frontend/) | React + TypeScript + Vite: chat/səs səhifəsi, dashboard, AZ/EN/RU | Netlify (kökdəki `netlify.toml`, `base = "frontend"`) |
| [`backend/`](backend/) | FastAPI: agent orchestrator (Claude via OpenRouter), detektorlar, policy engine, RAG, DynamoDB, ElevenLabs Custom LLM endpoint, usage API | Railway (`backend/Dockerfile`, `backend/railway.json`) |

- Backend API müqaviləsi: [`backend/docs/BACKEND_SPEC.md`](backend/docs/BACKEND_SPEC.md), frontend inteqrasiyası: [`frontend/docs/INTEGRATION.md`](frontend/docs/INTEGRATION.md)
- Xərc/istifadə paneli: [`backend/docs/USAGE_TABLE.md`](backend/docs/USAGE_TABLE.md), [`backend/docs/USAGE_FRONTEND.md`](backend/docs/USAGE_FRONTEND.md)
- Testlər: `cd backend && pytest -q tests` · `cd frontend && npm test`

Açarlar repoda saxlanılmır: backend üçün `.env` (bax `backend/docs/TESTING.md`), frontend üçün Netlify environment ([`frontend/docs/PUBLIC-NETLIFY.md`](frontend/docs/PUBLIC-NETLIFY.md)).
