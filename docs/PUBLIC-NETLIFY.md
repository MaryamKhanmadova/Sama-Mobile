# Hamı üçün avtomatik AI bağlantısı

Mövcud repository-yə bu source fayllarını köçürüb commit/push edin. Netlify Git deploy istifadə edin: server Edge Function manual dist/Drop deploy ilə daxil edilmir.

Netlify → Project configuration → Environment variables bölməsində:

- `SEMA_BACKEND_URL`: `https://sema-care-production.up.railway.app`
- `SEMA_API_KEY`: backend komandasının verdiyi mövcud API açarı (Functions scope).
- `SEMA_ACCESS_TOKEN`: silin / təyin etməyin; hamı üçün avtomatik giriş açılır.

Köhnə `VITE_API_AUTH=direct`, Railway ünvanlı `VITE_API_BASE_URL` və `VITE_CHAT_TRANSPORT=websocket` project dəyişənlərini silin və ya uyğun olaraq `proxy`, `/api`, `sse` ilə dəyişin. `netlify.toml` artıq bu dəyərləri təyin edir. Redeploy edin.

Açar `VITE_*` dəyişəninə qoyulmur və source/build-də yoxdur. Brauzer eyni domenin `/api` gateway-inə bağlanır; Netlify backend açarını serverdə əlavə edir. Cavab SSE ilə canlı axır. WebSocket yalnız açar tələb edən explicit direct development rejimində saxlanıb.

İctimai endpoint sintetik demo case-ləri ilə məhdudlaşır. Yeni sessiya yalnız backend demo siyahısında olan müştəriyə açılır. Demo müştəri seçimi sağ yuxarıda açılan menyudadır. Dashboard tarixçəsi mövcud ortaq sintetik məlumatları göstərir.

Build, 17 test, yerli gateway üzərindən real backend demo siyahısı, case seçimi və canlı SSE AI cavabı yoxlanıb. Netlify environment hesabınıza giriş olmadığı üçün dəyişənləri özünüz bir dəfə əlavə etməlisiniz.
