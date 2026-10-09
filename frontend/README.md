# Sama Care

React + TypeScript + Vite + Tailwind CSS + shadcn/ui. Mətn/səsli dəstək səhifəsi və dashboard. AZ, EN, RU interfeys dilləri.

## Mövcud repo ilə deploy

Source fayllarını mövcud repository-yə köçürün, `.git` qovluğunu saxlayın, commit/push edin. Netlify build: `npm run build`; publish: `dist`.

**Bir dəfə Netlify environment dəyişənlərini əlavə edin:** [PUBLIC-NETLIFY.md](docs/PUBLIC-NETLIFY.md). API açarı serverdə qalır, istifadəçi giriş forması olmadan AI işləyir. Bu versiya Netlify Edge Function tələb edir; yalnız dist qovluğunu Netlify Drop-a yükləmək kifayət etmir.

## Development

`npm install`, `npm run dev`, `npm run build`, `npm test`.

Standart `/api` Netlify proxy-si yerli Netlify runtime tələb edir. Adi Vite ilə birbaşa backend testi üçün `.env.local` daxilində `VITE_API_AUTH=direct`, `VITE_API_BASE_URL=https://sema-care-production.up.railway.app`, `VITE_CHAT_TRANSPORT=websocket` yazın; yalnız həmin development rejimində açar UI-da daxil edilir.

## İnteqrasiya

İctimai prod rejimində eyni domenin `/api` endpoint-i REST/SSE axınını Railway backendinə yönləndirir. Demo müştəri sağ yuxarıdakı menyudan seçilir. Yeni session yalnız backend tərəfindən verilən sintetik demo xəttinə açılır. Səsli ElevenLabs widget ayrıca işləyir. Backend cavabları öz dilində saxlanır; UI dili onları tərcümə etmir. 3D model təqdim ediləndə hazır avatar dəyişdirilə bilər.

Pul qaytarma və real səsli zəng bu frontend yoxlamasına daxil deyil. Backend texniki müqaviləsi üçün `docs/INTEGRATION.md`, dil strukturu üçün `docs/LOCALIZATION.md`.
