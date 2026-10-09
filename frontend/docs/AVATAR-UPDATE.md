# Məryəm avatarı — yeniləmə və yoxlama qeydləri

2026-10-09. Məhsul adı AZ-da Səma Mobile, EN/RU-da Sama Mobile; agent Məryəm / Maryam olaraq qalır. Backend müqaviləsi və Netlify server dəyişənləri dəyişmir.

## Dəyişikliklər

- Statik üz → göndərilən Meshopt GLB + Three.js 0.170.0. Model və `src/vendor/maryam/maryam-avatar.js` dəyişdirilmədən köçürülüb.
- Bir kök `AvatarProvider` model instansiyasını saxlayır. Eyni canvas ana ekran, çat başlığı və səhifədaxili zəng arasında `mount()` ilə daşınır; dashboardda gizli yerdə saxlanır. Model/app yalnız kök unmount zamanı dispose edilir.
- Three.js və vendor ayrıca lazy chunkdır. Dəstək səhifəsində GLB preload edilir; birbaşa dashboard girişində yüklənmir. Hash versiyalı URL, Netlify immutable cache. Mobil/zəif cihazlarda DPR cap 1, digər cihazlarda 2.
- Yüklənmədə ölçüsü ayrılmış shimmer; WebGL/model xətasında göndərilən portret. OS reduced-motion vendor tərəfindən nəzərə alınır.
- Fokus/yazı → listening, ack/status → thinking, delta → reactToText, uğurlu action → happy, handoff → empathetic, error → concerned, tamamlanan mətn cavabı → silent speakText. Aktiv səsli zəngdə mətn lipsync-i işə düşmür.
- Zəng FFT-si SDK-nın getOutputByteFrequencyData metodu ilə, range dəyişdirilmədən, avatarı idarə edir. Şəffaf fon, FFT halqası, dodaq hərəkəti, timer, səs səviyyəsi, altyazı, mute düyməsi/M qısayolu, Escape ilə bitirmə təsdiqi. Emosiya tag-ları altyazıdan çıxarılır.
- Zəng müştəri `msisdn`-i və hər start üçün yeni UUID `conversation_id` göndərir. Mikrofon mute əvvəlcə capture track-i dayandırır, sonra transport əməliyyatını gözləyir. Unmute capture-ı yenidən açır. Unmount/pagehide sessiyanı bağlayır.
- Mövcud işləyən `@elevenlabs/client` inteqrasiyası saxlanıb; əlavə React SDK qatına keçilməyib. Public agent ID eynidir. ElevenLabs açarı frontendə əlavə olunmur.
- Əvvəlki istəyinə uyğun zəng əsas səhifədə qalır. Xarici tab/widget və əlavə zəng modalı açılmır. Çata qayıdarkən seçilmiş söhbət saxlanır.
- Sistem (default), İşıqlı, Qaranlıq temaları, yadda saxlanan seçim, head-da ilk rəngi təyin edən skript, semantik rənglər; dashboard/çat/kartlar üçün oxunaqlı secondary rənglər.
- Başlıq səhifələrdən kənarda sticky qalır. Naviqasiya lazy/prefetch, uyğun brauzerdə View Transitions, yeni h1 fokus və screen-reader elanları. Mobil menyu native dialog/fokus/Escape, tarixçə drawer və scroll lock.
- Çat aşağıda olduqda auto-scroll; əvvəlki yazıları oxuyanda yeni mesaj düyməsi. Giriş sahəsi qısa/mobil ekranlarda görünür, Enter göndərir, Shift+Enter yeni sətir.

## Yoxlama nəticələri

- `npm run build`: TypeScript strict + Vite production build uğurludur. Avatar və səs SDK-sının böyük lazy chunk-ları üçün Vite ölçü xəbərdarlığı verir.
- `npm test`: 40/40. Model instansiyasının tək yaradılması/yüklənməsi, 20 host dəyişməsi, voice FFT ownership, fallback, dəyişməyən vendor/model hash-ləri, lokalizasiya açarları, tema tokenlərində mətn/status kontrastı, mute/cancel/unmount yarışları, SSE/WS, server proxy və usage müqaviləsi.
- Yerli production build + real Railway proxy: model WebGL-də görünür, mətn agenti təqdimat cavabı qaytarır. Bu yoxlamada hesab dəyişiklikləri tələb edilməyib.
- Brauzerdə 20 support/dashboard keçidi: bir avatar canvası, bir header, bir h1, fokus h1 üzərində; konsol xətası/xəbərdarlığı görünməyib. GLB once/factory davranışı unit test ilə də yoxlanıb. GPU heap və uzunmüddətli memory artımı ölçülməyib.
- Desktop 1440×900 və mobil 390×844 ekranlar: çat və sample-zəng hər iki temada. 320×640-da giriş sahəsi görünür; çox qısa ekranlarda welcome sahəsi ayrıca scroll edə bilir.
- Səs nümunəsi: handoff `sample.mp3` yalnız ayrıca `/tmp` QA build-də oxudulub, WebAudio FFT-si SDK ilə eyni 100–8000 Hz diapazonuna uyğunlaşdırılıb. Mouth/ring, caption tag stripping, captions hide, mute UI, timer, volume yoxlanıb. Bu adapter və audio production paketində yoxdur.
- 30 saniyəlik GIF həmin səs nümunəsinin ekran qeydidir, canlı zəng sübutu deyil; GIF audio saxlamır.

## Ölçülməmiş və cihazda yoxlanmalı hissələr

Canlı ElevenLabs/WebRTC zəngi və fiziki mikrofon icazəsi/capture bu avtomatik yoxlamada açılmayıb. SDK ilə real mic stop/reacquire davranışını istifadəçinin cihazında yoxlamaq lazımdır. Məntiqi track stop əməliyyatları və yarışlar unit testlə yoxlanıb. Chrome/Edge/Firefox/Safari/iOS cihaz matrisi, Lighthouse, real 4G Core Web Vitals və tam WCAG audit nəticəsi təqdim edilmir; bu göstəricilər ölçülməyib. Əsas tema rənglərinin AA kontrastı testlə yoxlanıb, görünən çat/dashboard mətnlərində aşağı kontrastlı legacy rənglər düzəldilib.

Vendorun public API-sində `speakText` cancellation yoxdur; daxili timer qısa boş track çağırışından sonra da tam oxuma müddətinə qədər qala bilər. Wrapper mətn oxumalarını ardıcıl saxlayır və səsli zəngə başlayanda text track-i boşaldır, timer bitəndə aktiv vəziyyəti yenidən bərpa edir. Modul dəyişdirilməyib. Tam timer cancellation və exhaustive WebGL resource cleanup vendor tərəfində əlavə edilməlidir.

## Mövcud repo və Netlify

ZIP-in içindəkiləri mövcud repository-nin kökünə köçürün; `.git` və öz environment fayllarınızı saxlayın. Yeni repo lazım deyil. `package.json` və `package-lock.json` da yenilənməlidir. `npm ci`, `npm run build`, sonra commit/push. Netlify Git integration auto-deploy edir.

Build: `npm run build`. Publish: `dist`. `netlify.toml`, `netlify/edge-functions/` və `public/avatar/` faylları commit olunmalıdır. Mövcud `SEMA_BACKEND_URL` və `SEMA_API_KEY` server environment dəyişənlərini saxlayın. API açarı və ElevenLabs açarı bundle-a yazılmır. `VITE_ELEVENLABS_AGENT_ID` public ID-dir və mövcud default işləyir. Yalnız `dist`-i Netlify Drop-a atmaq server proxy-ni yerləşdirmir.
