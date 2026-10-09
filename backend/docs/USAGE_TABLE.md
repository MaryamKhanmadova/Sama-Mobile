# Səma Mobile — `usage_monthly` cədvəli və API (v1.0)

> **Kimə:** backend / DB · **Kimdən:** məhsul/AI komandası · **Tarix:** 9 okt 2026
> Abunəçinin aylıq xərc, istifadə və statistikalarını UI-da (dashboard) göstərmək üçün. Data demo üçündür, uydurmadır;
> qiymətlər `app/catalog.py`-dan gəlir. Datanı biz yükləyirik (`python -m data.seed.usage`), backend yalnız oxuyur.

## 1. Cədvəli yaratmaq (DB dev)

| Parametr | Dəyər |
|---|---|
| Ad | `paralos.usage_monthly` (`TABLE_PREFIX` + `usage_monthly`) |
| Region | `eu-central-1` |
| Partition key | `msisdn` — String (məs. `+994981000137`; ümumi statistika üçün `#ALL`) |
| Sort key | `month` — String, `YYYY-MM` (məs. `2026-10`) |
| Billing | On-demand (`PAY_PER_REQUEST`) |
| GSI | Yoxdur |

```bash
aws dynamodb create-table \
  --region eu-central-1 \
  --table-name paralos.usage_monthly \
  --attribute-definitions AttributeName=msisdn,AttributeType=S AttributeName=month,AttributeType=S \
  --key-schema AttributeName=msisdn,KeyType=HASH AttributeName=month,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

**IAM:**
- Data yükləmək üçün `Paralos` user-ə: `dynamodb:DescribeTable`, `dynamodb:PutItem`, `dynamodb:BatchWriteItem`.
- Backend servisinə: `dynamodb:GetItem`, `dynamodb:Query`.
- Resource: `arn:aws:dynamodb:eu-central-1:825500924904:table/paralos.usage_monthly`

## 2. Item strukturu

### 2.1 Abunəçi-ay (`msisdn` = nömrə)

| Sahə | Tip | Mənası |
|---|---|---|
| `msisdn`, `month` | S | Açar |
| `customer_id`, `full_name`, `region` | S | Abunəçi |
| `tariff_id`, `tariff_name` | S | Tarif (`T_PLUS`, "Səma Plus") |
| `currency` | S | `AZN` |
| `is_current` | BOOL | Cari (yarımçıq) aydır |
| `days_elapsed`, `days_in_month` | N | Ayın neçə günü keçib |
| `costs` | M | `monthly_fee`, `packages`, `vas`, `roaming`, `out_of_bundle`, `intl_calls` (AZN) |
| `total` | N | Bu aya qədər cəmi xərc |
| `credits` | L | `[{reason, amount}]` — Məryəmin qaytardığı məbləğlər |
| `credits_total`, `net_total` | N | Qaytarılan cəm; `total - credits_total` |
| `forecast_total` | N | Ay sonu proqnozu (keçmiş aylarda = `total`) |
| `prev_month_total`, `change_pct` | N / null | Keçən ayla müqayisə (%) |
| `usage` | M | `data_mb`, `data_limit_mb`, `data_pct`, `voice_min`, `voice_limit_min`, `voice_pct`, `sms`, `sms_limit` (`*_pct` limitsiz tarifdə null) |
| `data_by_category` | M | MB: `video`, `social`, `browsing`, `music`, `messaging`, `games`, `maps` (çoxdan aza) |
| `top_category` | S | Ən çox internet istifadə olunan kateqoriya |
| `daily_data_mb` | L\<N\> | Gündəlik MB (1-ci gündən `days_elapsed`-ə qədər) — qrafik üçün |
| `peak_day` | N | Ən çox istifadə olunan gün |
| `packages` | L | `[{package_id, name, price}]` alınmış əlavə paketlər |
| `vas` | L | `[{vas_id, name, amount, period}]` |
| `roaming` | M / null | `{country, country_name, zone, days, package, package_price, extra_charges}` |
| `insights` | L\<S\> | Azərbaycan dilində tövsiyələr (UI-da birbaşa göstərilir) |
| `potential_savings` | N | Tövsiyələrə əməl etsə, aylıq qənaət (AZN) |

### 2.2 Ümumi statistika (`msisdn` = `#ALL`)

`month`, `lines`, `currency`, `is_current`, `avg_total`, `avg_data_mb`, `avg_voice_min`, `revenue_total`,
`credits_total`, `credits_count`, `potential_savings_total`, `cost_breakdown` (M, `costs` ilə eyni açarlar),
`data_by_category` (M), `tariff_mix` (M: tarif adı → say), `roaming_trips` (N).

## 3. API (backend → frontend)

Auth və xətalar `BACKEND_SPEC.md` §8 ilə eynidir: `X-API-Key: <key>` və ya `Authorization: Bearer <key>`.
`msisdn` path-da URL-encode olunur: `+` → `%2B`. Cavabda pul məbləğləri ədəd (number), JSON-da `Decimal` → `float`.

| Endpoint | DynamoDB əməliyyatı | 404 |
|---|---|---|
| `GET /v1/lines/{msisdn}/usage?months=6` | `Query msisdn = :m`, `ScanIndexForward=false`, `Limit=months` (1–12, default 6) | Heç bir sətir yoxdursa `line_not_found` |
| `GET /v1/lines/{msisdn}/usage/{month}` | `GetItem {msisdn, month}` | `usage_not_found` |
| `GET /v1/usage/summary?months=6` | `Query msisdn = "#ALL"`, `ScanIndexForward=false` | — |

> **Təhlükəsizlik:** demo-da `msisdn` path-dadır. Prod-da (spec §7: başqasının nömrəsinə çıxış mümkün olmamalıdır)
> nömrə sessiyanın təsdiqlənmiş xəttindən götürülməlidir, məs. `GET /v1/sessions/{session_id}/usage`.

### 3.1 Nümunə: abunəçinin son aylar

```bash
curl -s "https://<backend>/v1/lines/%2B994981000137/usage?months=2" \
  -H "X-API-Key: $API_KEY"
```

```js
const res = await fetch(
  `${API_BASE}/v1/lines/${encodeURIComponent(msisdn)}/usage?months=6`,
  { headers: { "X-API-Key": API_KEY } }
);
if (!res.ok) throw new Error((await res.json()).error?.code ?? res.status);
const { months } = await res.json();   // months[0] = cari ay
```

Cavab `200` (qısaldılıb):

```json
{
  "msisdn": "+994981000137",
  "currency": "AZN",
  "months": [
    {
      "month": "2026-10",
      "full_name": "Aysel Məmmədova",
      "tariff_id": "T_PLUS",
      "tariff_name": "Səma Plus",
      "is_current": true,
      "days_elapsed": 9,
      "days_in_month": 31,
      "costs": { "monthly_fee": 15.0, "packages": 0.0, "vas": 1.8, "roaming": 0.0, "out_of_bundle": 0.0, "intl_calls": 0.0 },
      "total": 16.8,
      "credits": [],
      "credits_total": 0.0,
      "net_total": 16.8,
      "forecast_total": 21.2,
      "prev_month_total": 24.0,
      "change_pct": -11.7,
      "usage": {"data_mb": 7058, "data_limit_mb": 25600, "data_pct": 27.6, "voice_min": 204, "voice_limit_min": 800, "voice_pct": 25.5, "sms": 14, "sms_limit": 300},
      "data_by_category": {"video": 2380, "social": 2215, "browsing": 1123, "music": 400, "maps": 360, "messaging": 333, "games": 245},
      "top_category": "video",
      "daily_data_mb": [1029, 508, 1044, 1165, 911, 669, 825, 496, 405],
      "peak_day": 4,
      "packages": [],
      "vas": [{ "vas_id": "V_FAL", "name": "Ulduz Falı", "amount": 1.8, "period": "gün" }],
      "roaming": null,
      "insights": ["Ulduz Falı abunəliyi bu ay 1.80 AZN tutub. İstifadə etmirsinizsə, ləğv edə bilərsiniz."],
      "potential_savings": 6.2
    },
    { "month": "2026-09", "is_current": false, "total": 24.0, "...": "..." }
  ]
}
```

### 3.2 Nümunə: ümumi statistika

```bash
curl -s "https://<backend>/v1/usage/summary?months=1" -H "X-API-Key: $API_KEY"
```

```json
{
  "currency": "AZN",
  "months": [
    {
      "month": "2026-10",
      "lines": 10,
      "is_current": true,
      "avg_total": 16.76,
      "avg_data_mb": 5549,
      "avg_voice_min": 146,
      "revenue_total": 167.6,
      "credits_total": 4.0,
      "credits_count": 2,
      "potential_savings_total": 36.12,
      "cost_breakdown": {"monthly_fee": 150.0, "packages": 0.0, "vas": 5.4, "roaming": 0.0, "out_of_bundle": 7.7, "intl_calls": 4.5},
      "data_by_category": {"video": 21198, "social": 14186, "browsing": 7276, "music": 4227, "messaging": 3555, "games": 2867, "maps": 2154},
      "tariff_mix": { "Səma Plus": 3, "Səma Max": 2, "Səma Start": 2, "Səma Gənc": 1, "Səma Biznes": 1, "Səma Sərbəst": 1 },
      "roaming_trips": 0
    }
  ]
}
```

### 3.3 Backend üçün nümunə (FastAPI + boto3)

```python
from decimal import Decimal
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.table_prefix + "usage_monthly")

def plain(x):
    if isinstance(x, Decimal): return int(x) if x == x.to_integral_value() else float(x)
    if isinstance(x, list): return [plain(i) for i in x]
    if isinstance(x, dict): return {k: plain(v) for k, v in x.items()}
    return x

@router.get("/v1/lines/{msisdn}/usage")
def line_usage(msisdn: str, months: int = Query(6, ge=1, le=12)):
    items = table.query(KeyConditionExpression=Key("msisdn").eq(msisdn),
                        ScanIndexForward=False, Limit=months)["Items"]
    if not items:
        raise HTTPException(404, {"code": "line_not_found", "message": "No usage for this line", "retryable": False})
    return {"msisdn": msisdn, "currency": "AZN", "months": [plain(i) for i in items]}
```

## 4. Demo nömrələri

`+994981000137` … `+994981001370` (addım 137): 10 abunəçi, may–oktyabr 2026. Maraqlı hallar:
`…0137` Ulduz Falı VAS · `…0411` limitdən çox internet, əlavə paketlər · `…0548` Türkiyə rouminqi ·
`…0959` Sərbəst (PAYG) · `…0822` Biznes, Almaniya rouminqi.
