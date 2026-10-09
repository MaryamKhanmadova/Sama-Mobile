# Səma Mobile — necə test etmək

Hamısı layihə qovluğundan işlədilir (`C:\Users\alien\Desktop\AI\CODES\sema-care`). Açarlar `.env`-dən götürülür.

| # | Nəyi yoxlayır | Əmr | Gözlənən |
|---|---|---|---|
| 1 | Data + qaydalar (LLM-siz) | `python -m data.seed.validate` | `OK` |
| 2 | RAG axtarışı | `python -m data.kb.check_retrieval` | recall@4 ≥ 0.9 (indi 0.98) |
| 3 | Backend məntiqi (saxta LLM) | `python -m pytest -q tests` | 8 passed |
| 4 | **LLM pipeline — 63 hal, real Claude** | `python -m eval.run` (alt dəst: `--ids S01,S04,B03`) | nəticə `eval/results/<vaxt>-agent/report.md` |
| 5 | Baseline (LLM-siz) | `python -m eval.run --mode rules` | müqayisə üçün |
| 6 | **Səs: ElevenLabs → backend + TTS → STT** | `python -m eval.voice_check` | simulyasiya dialoqu + gecikmə + oxşarlıq, səs faylı `eval/results/voice_check.mp3` |
| 7 | Canlı backend | brauzerdə `https://sema-care-production.up.railway.app/health` | `"llm_configured": true` |
| 8 | Canlı səs (insan) | ElevenLabs panel → **Səma Mobile - Məryəm → Test AI agent** | Məryəm Azərbaycan dilində cavab verir |

## Canlı chat (curl)
```bash
KEY=sk-sema-...   # .env -> API_KEYS
U=https://sema-care-production.up.railway.app
SID=$(curl -s -X POST $U/v1/sessions -H "X-API-Key: $KEY" -H 'Content-Type: application/json' -d '{"msisdn":"+994981000548"}' | python -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
curl -N -X POST "$U/v1/sessions/$SID/messages:stream" -H "X-API-Key: $KEY" -H 'Content-Type: application/json' -d '{"text":"Rouminqi söndürmüşdüm, 4 manat 50 qəpik kəsilib"}'
```
Başqa ssenarilər: `GET /v1/demo/cases` (hər halın nömrəsi və nümunə mesajları).

## Səsli test ssenarisi (ElevenLabs "Test AI agent")
Səs agenti demo nömrəsi kimi **S04** müştərisini (Aysel, rouminq kəsintisi) götürür.
1. "Salam, Gürcüstanda idim, rouminqi söndürmüşdüm, yenə də pul kəsilib." → Məryəm "Bir saniyə, yoxlayıram" deyib araşdırır, 4.50 AZN qaytarır.
2. Məryəm danışarkən sözünü kəsin ("Dayan, neçə manat?") → dayanmalı, yeni suala cavab verməlidir.
3. "Siz robotsunuz?" → "virtual müştəri mütəxəssisi" cavabı.
4. Rus dilində: "А сколько стоит роуминг в Грузии?" → rus dilində cavab.

## Demonu sıfırlamaq
Hər ssenari bir dəfə işləyir (pul bir dəfə qaytarılır). Təkrar üçün:
```bash
curl -X POST https://sema-care-production.up.railway.app/v1/admin/reset-demo -H "X-API-Key: $KEY"
```
DynamoDB rejimində bu, cədvəlləri seed dataya qaytarır (~15 s). Lokal: `python -m infra.load_seed --reset`.

## DB (DynamoDB, prefiks `paralos.`)
- Yükləmə/yeniləmə: `python -m infra.load_seed` (upsert, ~20 s)
- Railway: `STORE=dynamodb`; data restartdan sonra qalır.

## Ölçülmüş ilk nəticələr (9 okt, canlı)
- Chat (S04, Railway): ilk söz 0.9 s, tam cavab ~16 s, 6 alət addımı, ~$0.07.
- Səs: ElevenLabs simulyasiyası işləyir (Haiku 5.5, Azərbaycan dili); TTS ilk səs ~1.8 s (Bakıdan), STT oxşarlıq 0.82.
- Smoke eval (8 hal: S01, S04, S09, U01, H02, H05, B03, T01): 7/8 keçdi, səhv kredit 0. T01-də agent interneti açmazdan əvvəl təsdiq istədi (düzgün davranış) — test halına təsdiq növbəsi əlavə olundu, yenidən işlədilməyib. Tam 63 hal hələ işlədilməyib.
