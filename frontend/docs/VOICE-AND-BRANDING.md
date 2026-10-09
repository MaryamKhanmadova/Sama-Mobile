# Sama Mobile — səs və brend yeniləməsi

Mövcud reponuzdakı source fayllarını bu paketlə əvəz edib commit/push edin. `.git` və yerli `.env` saxlanılır. Netlify server dəyişənləri eynidir; yeni dependency package.json və package-lock.json ilə gəlir.

## Frontend

- Verilmiş SVG logo header, tarixçə rail, agent mesaj avatarı, dashboard və favicon-da istifadə edilir.
- UI AZ/EN/RU dillərində Sama Mobile / Maryam Agent göstərir. Köhnə server cavablarındakı brend adları yalnız assistant mətninin ekranda göstərilməsində dəyişdirilir; istifadəçinin mesajı və saxlanan server faktları dəyişdirilmir.
- Səsli SDK WebRTC sessiyası birbaşa ana ekranda işləyir; kənar widget/modal və vendor adları göstərilmir.
- Danışıq göstəricisi SDK-nın agent speaking/listening hadisələrindən və giriş/çıxış audio analizindən gəlir. Mikrofon susdurulduqda giriş animasiyası dayanır, agent danışırsa onun çıxış animasiyası davam edir.
- Mikrofon düyməsi setMicMuted çağırır; zəngi bitirmək və səhifədən çıxmaq endSession ilə audio sessiyasını bağlayır. Gözləyən bağlantı ləğv edilirsə, açıldığı anda bağlanır. Mikrofon icazəsi zəngə başlama düyməsindən sonra brauzer tərəfindən istənilir.
- Səsli transkript ana ekranda göstərilir. Səsli SDK-nın transcript event-ləri agentdə aktiv olmalıdır. Səsli sessiya ilə REST text-case tarixçəsinin əlaqəsi backend-in məsuliyyətidir; frontend səsli zəngi özündən tamamlanmış case kimi yazmır.

## Agentin səsdə dediyi ad

Frontend ekrandakı təqdimatı dəyişir, artıq sintez olunmuş səsi dəyişə bilmir. Backend komandasına və səsli agentin ayarlarını idarə edən şəxsinə bu məlumatı verin:

- Agentin adı: Maryam Agent.
- Şirkət/product: Sama Mobile.
- First message nümunəsi: “Salam! Mən Maryam Agent, Sama Mobile müştəri dəstəyi. Sizə necə kömək edə bilərəm?”
- System prompt və məlumat mənbələrində əvvəlki Ayla / Sama Care / Səma Mobile təqdimatlarını yeniləyin. Müştərinin dilində cavablandırma, qayda və alət müqavilələrini saxlayın.

Bu ayar hesabınıza giriş olmadığı üçün frontend paketində dəyişdirilməyib; çağırışda məcburi prompt override göndərilmir, çünki agent icazəsi olmayan override zəngi bloklaya bilər.

## Yoxlama

Build və 22 test keçib. Sessiya testləri mock SDK ilə mute/unmute, bağlanma, gec açılan bağlantının ləğvi və mute xətasında cleanup-u yoxlayır. Brauzerdə logo, input fokus görünüşü və ana-ekran səsli paneli yoxlanıb. Real istifadəçi mikrofonu/səsli provider zəngi bu yoxlamada istifadə edilməyib; Netlify HTTPS saytında danışıb mikrofonu susdurma və zəngi bitirmə testini edin.
