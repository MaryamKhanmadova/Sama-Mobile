# Backend üçün: hazır materiallar və nə etməli (qısa)

Tam tapşırıq: `docs/BACKEND_SPEC.md`. Burada yalnız **bizim verdiklərimiz** və **sizin edəcəyiniz** var.

## 1. Data → DynamoDB
Fayllar: `data/seed/out/` (hamısı JSON massividir, UTF-8)

| Fayl | Cədvəl | Açar |
|---|---|---|
| `customers.json` (88) | `sema_customers` | PK `customer_id` |
| `lines.json` (88) | `sema_lines` | PK `msisdn` |
| `events.json` (~8 350) | `sema_events` | PK `msisdn`, SK `sk` = `ts + "#" + event_id` (siz əlavə edin) |
| `incidents.json` (4) | `sema_incidents` | PK `region`, SK `sk` = `start_ts + "#" + incident_id` |
| `catalog.json` | `sema_catalog` | PK `item_id`, `item_type` sahəsi var |

Yükləyərkən float-ları `Decimal`-a çevirin. Başqa heç nə dəyişməyin.

**Demo günü tarixləri yeniləmək üçün** (data "dünən" kimi görünsün):
```bash
python -m data.seed.generate --now 2026-10-10T11:00:00+04:00
```
Sonra yenidən yükləyin. Backend-də `SEMA_NOW` eyni dəyərdə olmalıdır.

## 2. Bilik bazası → RAG
- `data/kb/*.md` (21 sənəd): `##` başlığına görə bölün, hər hissənin əvvəlinə `[Sənəd başlığı › Bölmə]` yazın, `doc_id` = fayl adı.
- `data/kb/glossary_ru_az.json`: rus sözlərini sorğuda Azərbaycan sözləri ilə genişləndirin.
- Hazır nümunə: `data/kb/check_retrieval.py` (normalizasiya + BM25). Bizdə nəticə: **recall@4 = 0.98**. Embedding əlavə etsəniz, bundan aşağı düşməməlidir.

## 3. Agentin prompt-u
`docs/MARYAM_SYSTEM_PROMPT.md`: system blok 1 kimi, dəyişmədən. `{{channel}}` yerinə `voice` və ya `web` yazın.

## 4. Qaydaların istinad kodu
`data/seed/validate.py` → `detect()` funksiyası: operator xətası detektorlarının (ikiqat kəsinti, VAS, rouminq, limit və s.) **hazır Python məntiqi**. Policy Engine-də birbaşa istifadə edə və ya köçürə bilərsiniz. Məbləğlər buna görə 63 halda 100% düzgündür.

## 5. Testlər
`eval/cases.json`: 63 hal. Hər halda `msisdn`, müştəri mesajları (`turns`) və gözlənən nəticə (`expected`) var. 13 hal `holdout: true`-dur, prompt sazlamaq üçün istifadə etməyin.

Qəbul yoxlaması:
```bash
python -m data.seed.validate         # data + qaydaların düzgünlüyü (OK olmalıdır)
python -m data.kb.check_retrieval    # RAG bazası (recall@4 ≥ 0.9)
```
Agent hazır olanda: hər hal üçün sessiya açın (`msisdn` ilə), `turns`-ü ardıcıl göndərin, `final.decision` / `amount` / `team` sahələrini `expected` ilə müqayisə edin. Hədəf: qərar ≥ 85%, **səhv pul qaytarma = 0**.

## Sual olarsa
Data və ya qaydada uyğunsuzluq görsəniz, özünüz düzəltməyin, bizə yazın. Datanı generator yaradır, əl ilə dəyişiklik növbəti generasiyada itəcək.
