<<<<<<< HEAD
# Səma Mobile — Məryəm
=======
Usage dashboard inteqrasiyası: [USAGE-DASHBOARD.md](docs/USAGE-DASHBOARD.md). Dashboard xərc/istifadə API müqaviləsi ilə işləyir; backend bu endpoint-lərə 200 qaytarır və real 6 aylıq məlumatla yoxlanılıb.

Yeni səsli panel, logo və brend qeydləri: [VOICE-AND-BRANDING.md](docs/VOICE-AND-BRANDING.md).

# Sama Mobile / Səma Mobile
>>>>>>> 0038ed1 (final deploy)

Telekom abunəçisinin hesab və bağlantı problemlərini chat və səsli zəngdə həll edən AI müştəri mütəxəssisi.
NeuroBridge Bakı 2026, AI Enterprise Solutions. Bütün data sintetikdir, Səma Mobile fiktiv operatordur.

| Qovluq | Nə var | Deploy |
|---|---|---|
| [`frontend/`](frontend/) | React + TypeScript + Vite: chat/səs səhifəsi, dashboard, AZ/EN/RU | Netlify (kökdəki `netlify.toml`, `base = "frontend"`) |
| [`backend/`](backend/) | FastAPI: agent orchestrator (Claude via OpenRouter), detektorlar, policy engine, RAG, DynamoDB, ElevenLabs Custom LLM endpoint, usage API | Railway (`backend/Dockerfile`, `backend/railway.json`) |

- Backend API müqaviləsi: [`backend/docs/BACKEND_SPEC.md`](backend/docs/BACKEND_SPEC.md), frontend inteqrasiyası: [`frontend/docs/INTEGRATION.md`](frontend/docs/INTEGRATION.md)
- Xərc/istifadə paneli: [`backend/docs/USAGE_TABLE.md`](backend/docs/USAGE_TABLE.md), [`backend/docs/USAGE_FRONTEND.md`](backend/docs/USAGE_FRONTEND.md)
- Testlər: `cd backend && pytest -q tests` · `cd frontend && npm test`

<<<<<<< HEAD
Açarlar repoda saxlanılmır: backend üçün `.env` (bax `backend/docs/TESTING.md`), frontend üçün Netlify environment ([`frontend/docs/PUBLIC-NETLIFY.md`](frontend/docs/PUBLIC-NETLIFY.md)).
=======
**Bir dəfə Netlify environment dəyişənlərini əlavə edin:** [PUBLIC-NETLIFY.md](docs/PUBLIC-NETLIFY.md). API açarı serverdə qalır, istifadəçi giriş forması olmadan AI işləyir. Bu versiya Netlify Edge Function tələb edir; yalnız dist qovluğunu Netlify Drop-a yükləmək kifayət etmir.

## Development

`npm install`, `npm run dev`, `npm run build`, `npm test`.

Standart `/api` Netlify proxy-si yerli Netlify runtime tələb edir. Adi Vite ilə birbaşa backend testi üçün `.env.local` daxilində `VITE_API_AUTH=direct`, `VITE_API_BASE_URL=https://sema-care-production.up.railway.app`, `VITE_CHAT_TRANSPORT=websocket` yazın; yalnız həmin development rejimində açar UI-da daxil edilir.

## İnteqrasiya

İctimai prod rejimində eyni domenin `/api` endpoint-i REST/SSE axınını Railway backendinə yönləndirir. Demo müştəri sağ yuxarıdakı menyudan seçilir. Yeni session yalnız backend tərəfindən verilən sintetik demo xəttinə açılır. Səsli SDK paneli ana ekranda işləyir. Backend cavabları öz dilində saxlanır; UI dili onları tərcümə etmir. Göndərilən Məryəm GLB modeli artıq çat və səhifədaxili zəng ekranında qoşulub. Avatar inteqrasiyası və yoxlama qeydləri: [AVATAR-UPDATE.md](docs/AVATAR-UPDATE.md).

Pul qaytarma və real səsli zəng bu frontend yoxlamasına daxil deyil. Backend texniki müqaviləsi üçün `docs/INTEGRATION.md`, dil strukturu üçün `docs/LOCALIZATION.md`.
>>>>>>> 0038ed1 (final deploy)
