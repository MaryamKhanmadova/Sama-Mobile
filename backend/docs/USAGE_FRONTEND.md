# Səma Mobile — Xərc və istifadə ekranı: frontend bələdçisi

> **Kimə:** frontend · **Tarix:** 9 okt 2026 · API müqaviləsi və cədvəl: [`USAGE_TABLE.md`](USAGE_TABLE.md)
> Backend hələ hazır deyil — mock fayllarla bu gün başlaya bilərsiniz; cavablar API ilə **eynidir**.

## 1. Tez başlamaq: mock data

`web/mock/usage/` — API cavabının dəqiq surəti:

| Fayl | Endpoint-in əvəzi |
|---|---|
| `994981000137.json` … `994981001370.json` (10 fayl) | `GET /v1/lines/{msisdn}/usage?months=6` |
| `summary.json` | `GET /v1/usage/summary?months=6` |

Yenidən yaratmaq: `python -m data.seed.usage --mock web/mock/usage` (DB-yə toxunmur).

```ts
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "1";

export async function getLineUsage(msisdn: string, months = 6): Promise<LineUsageResponse> {
  if (USE_MOCK) {
    const r = await fetch(`/mock/usage/${msisdn.replace("+", "")}.json`);
    const body: LineUsageResponse = await r.json();
    return { ...body, months: body.months.slice(0, months) };
  }
  return api(`/v1/lines/${encodeURIComponent(msisdn)}/usage?months=${months}`);
}

export async function getSummary(months = 6): Promise<SummaryResponse> {
  if (USE_MOCK) {
    const body: SummaryResponse = await (await fetch("/mock/usage/summary.json")).json();
    return { ...body, months: body.months.slice(0, months) };
  }
  return api(`/v1/usage/summary?months=${months}`);
}

async function api<T>(path: string): Promise<T> {
  const r = await fetch(`${import.meta.env.VITE_API_BASE}${path}`, {
    headers: { "X-API-Key": import.meta.env.VITE_API_KEY },
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new ApiError(r.status, err?.code ?? "unknown");   // body: {code, message}
  }
  return r.json();
}
```

> API açarı brauzerdə görünür — demo üçün qəbul olunandır, prod-da açar backend-for-frontend arxasında qalmalıdır.

## 2. TypeScript tipləri

```ts
export type Money = number;            // AZN, 2 onluq
export type Month = `${number}-${number}`; // "2026-10"
export type CostKey = "monthly_fee" | "packages" | "vas" | "roaming" | "out_of_bundle" | "intl_calls";
export type Category = "video" | "social" | "browsing" | "music" | "messaging" | "games" | "maps";

export interface UsageMonth {
  msisdn: string;
  month: Month;
  customer_id: string;
  full_name: string;
  tariff_id: "T_START" | "T_PLUS" | "T_MAX" | "T_GENC" | "T_PAYG" | "T_BIZNES";
  tariff_name: string;
  region: string;
  currency: "AZN";
  is_current: boolean;
  days_elapsed: number;
  days_in_month: number;
  costs: Record<CostKey, Money>;
  total: Money;
  credits: { reason: string; amount: Money }[];
  credits_total: Money;
  net_total: Money;
  forecast_total: Money;
  prev_month_total: Money | null;      // ən köhnə ayda null
  change_pct: number | null;           // forecast_total vs keçən ay; ən köhnə ayda null
  usage: {
    data_mb: number;
    data_limit_mb: number;             // Sərbəst (PAYG) tarifində 0
    data_pct: number | null;           // limit yoxdursa null
    voice_min: number;
    voice_limit_min: number;
    voice_pct: number | null;
    sms: number;
    sms_limit: number;
  };
  data_by_category: Partial<Record<Category, number>>;  // MB, çoxdan aza sıralı
  top_category: Category | null;
  daily_data_mb: number[];             // index 0 = ayın 1-i; uzunluq = days_elapsed
  peak_day: number | null;             // ayın günü (1-dən)
  packages: { package_id: string; name: string; price: Money }[];
  vas: { vas_id: string; name: string; amount: Money; period: "gün" | "ay" }[];
  roaming: {
    country: string; country_name: string; zone: "Z1" | "Z2" | "Z3"; days: number;
    package: string; package_price: Money; extra_charges: Money;
  } | null;
  insights: string[];                  // hazır Azərbaycan mətni, olduğu kimi göstərin
  potential_savings: Money;            // aylıq, AZN
}

export interface LineUsageResponse { msisdn: string; currency: "AZN"; months: UsageMonth[] } // [0] = ən yeni

export interface SummaryMonth {
  msisdn: "#ALL";
  month: Month;
  lines: number;
  currency: "AZN";
  is_current: boolean;
  avg_total: Money;
  avg_data_mb: number;
  avg_voice_min: number;
  revenue_total: Money;
  credits_total: Money;
  credits_count: number;
  potential_savings_total: Money;
  cost_breakdown: Record<CostKey, Money>;
  data_by_category: Partial<Record<Category, number>>;
  tariff_mix: Record<string, number>;  // tarif adı → abunəçi sayı
  roaming_trips: number;
}

export interface SummaryResponse { currency: "AZN"; months: SummaryMonth[] }
```

## 3. Ekran: abunəçinin "Xərclərim" paneli

`months[0]` = cari ay, `months.slice(0, 6).reverse()` = qrafiklər üçün köhnədən yeniyə.

| Blok | Sahələr | Necə göstərmək |
|---|---|---|
| Başlıq | `full_name`, `tariff_name`, `msisdn`, `region` | Nömrəni maskalayın: `+994 98 100 •• 37` |
| Bu ay — böyük rəqəm | `total`, `forecast_total`, `days_elapsed/days_in_month` | "16,80 ₼ · ay sonu təxminən 21,20 ₼" + "9/31 gün" progress |
| Dəyişiklik nişanı | `change_pct` | `▼ 11,7%` yaşıl (xərc azalıb), `▲` qırmızı; `null` → gizlət |
| Məryəm qaytardı | `credits[]`, `credits_total` | `credits_total > 0` olduqda yaşıl kart: "Məryəm sizə 3,00 ₼ qaytardı" + səbəblər |
| Xərc bölgüsü | `costs` | Donut və ya üfüqi bar; `0` olan açarları gizlədin |
| Paket istifadəsi | `usage.*_pct` | 3 progress bar (İnternet / Dəqiqə / SMS); `pct >= 90` narıncı, `>= 100` qırmızı; `null` → "Limitsiz"/"Paket yoxdur" |
| İnternet kateqoriyaları | `data_by_category`, `top_category` | Üfüqi bar və ya ikonlu siyahı; MB → GB |
| Gündəlik qrafik | `daily_data_mb`, `peak_day` | Sparkline / bar; `peak_day`-i vurğulayın |
| 6 aylıq tarixçə | `months[].total`, `months[].credits_total` | Bar chart; cari ay üçün `forecast_total` kölgəli/şəffaf bar |
| Tövsiyələr | `insights[]`, `potential_savings` | Kart: "Ayda 6,20 ₼ qənaət edə bilərsiniz" + mətnlər; boşdursa gizlət |
| Əlavələr | `packages[]`, `vas[]`, `roaming` | Kiçik siyahı; `roaming` varsa bayraq + ölkə adı |

**Cari ay haqqında:** `is_current = true` olduqda `usage` və `costs` yalnız keçən günlər üçündür (məs. 9/31).
Faizləri "aylıq limitin X%-i istifadə olunub" kimi göstərin, `forecast_total` isə xətti proqnozdur (əlavə paketləri nəzərə almır).

## 4. Ekran: ümumi statistika (jüri / demo)

`getSummary()` → `months[0]`:

| Blok | Sahə |
|---|---|
| KPI kartları | `lines` abunəçi · `avg_total` orta hesab · `credits_total` (`credits_count` hal) qaytarılıb · `potential_savings_total` qənaət imkanı |
| Xərc strukturu | `cost_breakdown` (stacked bar, 6 ay) |
| Ən çox nəyə internet gedir | `data_by_category` |
| Tarif paylanması | `tariff_mix` (donut) |
| Trend | `months[].avg_total`, `months[].credits_total` (line chart) |

## 5. Label-lər (AZ)

```ts
export const COST_LABELS: Record<CostKey, string> = {
  monthly_fee: "Aylıq abunə haqqı",
  packages: "Əlavə paketlər",
  vas: "Əlavə xidmətlər",
  roaming: "Rouminq",
  out_of_bundle: "Paketdən kənar istifadə",
  intl_calls: "Beynəlxalq zənglər",
};

export const CATEGORY_LABELS: Record<Category, string> = {
  video: "Video", social: "Sosial şəbəkələr", browsing: "Sayt gəzintisi", music: "Musiqi",
  messaging: "Mesajlaşma", games: "Oyunlar", maps: "Xəritələr",
};

export const CATEGORY_ICONS: Record<Category, string> = {
  video: "🎬", social: "💬", browsing: "🌐", music: "🎵", messaging: "✉️", games: "🎮", maps: "🗺️",
};
```

## 6. Formatlama

```ts
const azn = new Intl.NumberFormat("az-AZ", { style: "currency", currency: "AZN" });
azn.format(16.8);                                   // "16,80 ₼"

const gb = (mb: number) => mb >= 1024 ? `${(mb / 1024).toFixed(1).replace(".", ",")} GB` : `${mb} MB`;

const monthLabel = (m: string) =>
  new Intl.DateTimeFormat("az-AZ", { month: "long", year: "numeric" }).format(new Date(`${m}-01T00:00:00`));
// "oktyabr 2026" (brauzer dəstəkləmirsə öz massivinizi istifadə edin)

const pct = (x: number | null) => (x == null ? "—" : `${x.toFixed(0)}%`);
```

- Pul məbləğləri həmişə 2 onluq; `0` olan xərcləri gizlədin.
- `change_pct`: xərclər üçün **azalma yaxşıdır** (yaşıl), artım qırmızı.
- Saat qurşağı Bakı (+04:00); tarixləri brauzerin saat qurşağına çevirməyin.

## 7. Boş, null və xəta halları

| Hal | UI |
|---|---|
| `change_pct` / `prev_month_total` = `null` | Nişanı gizlət |
| `usage.data_pct` = `null` (PAYG) | "Paket yoxdur — hər MB ödənişlidir" |
| `insights` boş | Tövsiyə kartını gizlət |
| `credits` boş | "Məryəm qaytardı" kartını gizlət |
| `roaming` = `null`, `packages`/`vas` boş | Bölməni gizlət |
| `daily_data_mb` boş (ayın 1-i) | "Hələ data yoxdur" |
| `401 unauthorized` | Açar səhvdir — konfiqurasiya xətası göstər |
| `404 line_not_found` | "Bu nömrə üçün məlumat tapılmadı" |
| `429` / `5xx` | Skeleton + "Yenidən cəhd et" düyməsi |

## 8. Jüri üçün təsir yaradan anlar

- **"Məryəm sizə qaytardı" kartı** ən öndə: agentin real pul qaytardığını göstərir (`credits[]`, `…0137` sentyabr: Ulduz Falı qaytarılması).
- **Tövsiyə → söhbət:** hər `insight` yanında "Məryəm ilə danış" düyməsi; chat-i hazır mətnlə açın
  (məs. "Ulduz Falı abunəliyimi ləğv etmək istəyirəm") — agent eyni problemi canlı həll edir.
- **Proqnoz barı:** cari ay üçün `total` dolu, `forecast_total` şəffaf — "ay sonu nə qədər ödəyəcəm" sualına cavab.
- **Demo nömrə seçici** (dropdown) — aşağıdakı ssenarilər arasında tez keçid.

## 9. Demo nömrələri

| Nömrə | Ad | Tarif | Nə göstərir |
|---|---|---|---|
| `+994981000137` | Aysel Məmmədova | Səma Plus | Ulduz Falı VAS (gündəlik ödəniş) → tövsiyə + sentyabrda qaytarılma |
| `+994981000274` | Tural Əliyev | Səma Max | İnterneti az istifadə edir → ucuz tarifə keçid tövsiyəsi |
| `+994981000411` | Leyla Hüseynova | Səma Start | Limiti hər ay keçir → əlavə 5 GB paketlər |
| `+994981000548` | Orxan Quliyev | Səma Plus | Avqustda Türkiyə rouminqi |
| `+994981000685` | Nigar Rzayeva | Səma Gənc | Oyun Klubu VAS → tövsiyə + qaytarılma |
| `+994981000822` | Kamran Kərimov | Səma Biznes | Beynəlxalq zənglər, iyunda Almaniya rouminqi |
| `+994981000959` | Günay Abbasova | Səma Sərbəst | PAYG — hər MB ödənişli → Səma Start tövsiyəsi |
| `+994981001096` | Elvin Nəbiyev | Səma Plus | Paketin çox az hissəsi istifadə olunur → qənaət tövsiyəsi |
| `+994981001233` | Ирина Петрова | Səma Max | Sentyabrda Gürcüstan rouminqi (rus dilli abunəçi) |
| `+994981001370` | Fidan Cəfərova | Səma Start | Xəbər+ VAS → tövsiyə + qaytarılma |
