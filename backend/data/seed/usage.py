"""Monthly usage & cost summaries for the customer-facing dashboard (table: <prefix>usage_monthly).

One item per (msisdn, month): cost breakdown, bundle usage, data by category, daily data series,
month-over-month change, savings tips and credits issued by Məryəm. Items with msisdn="#ALL" hold
aggregates over all demo lines per month. All data is fictional; prices come from app/catalog.py.

    python -m data.seed.usage            # create table (if missing) and push to DynamoDB
    python -m data.seed.usage --dry-run  # print one item, write nothing
"""
from __future__ import annotations

import argparse
import calendar
import json
import random
from datetime import datetime
from decimal import Decimal

from app import catalog as C
from app.config import settings
from data.seed.world import World, r2

TABLE = "usage_monthly"
MONTHS = 6  # current month (partial) + 5 previous

# name, tariff, region, profile: data_use = share of bundle used; extras drive the story for the UI
LINES = [
    ("Aysel Məmmədova", "T_PLUS", "Bakı-Nəsimi", {"data_use": (0.85, 1.15), "vas": "V_FAL"}),
    ("Tural Əliyev", "T_MAX", "Bakı-Yasamal", {"data_use": (0.25, 0.45)}),
    ("Leyla Hüseynova", "T_START", "Sumqayıt", {"data_use": (1.1, 1.5)}),
    ("Orxan Quliyev", "T_PLUS", "Gəncə", {"data_use": (0.5, 0.75), "roaming": ("TR", 3)}),
    ("Nigar Rzayeva", "T_GENC", "Bakı-Xətai", {"data_use": (0.9, 1.3), "vas": "V_OYUN"}),
    ("Kamran Kərimov", "T_BIZNES", "Bakı-Nərimanov", {"data_use": (0.4, 0.7), "intl": True,
                                                       "roaming": ("DE", 1)}),
    ("Günay Abbasova", "T_PAYG", "Şəki", {"data_mb": (150, 700)}),
    ("Elvin Nəbiyev", "T_PLUS", "Lənkəran", {"data_use": (0.15, 0.35)}),
    ("Ирина Петрова", "T_MAX", "Bakı-Nəsimi", {"data_use": (0.8, 1.1), "roaming": ("GE", 4)}),
    ("Fidan Cəfərova", "T_START", "Quba", {"data_use": (0.6, 0.9), "vas": "V_XEBER"}),
]

CAT_WEIGHTS = {"video": 0.38, "social": 0.24, "browsing": 0.14, "music": 0.08, "messaging": 0.07,
               "games": 0.05, "maps": 0.04}


def month_list(now: datetime) -> list[tuple[str, int, int]]:
    """[(YYYY-MM, days_in_month, days_elapsed)] oldest first."""
    out, y, m = [], now.year, now.month
    for _ in range(MONTHS):
        dim = calendar.monthrange(y, m)[1]
        elapsed = now.day if (y, m) == (now.year, now.month) else dim
        out.append((f"{y:04d}-{m:02d}", dim, elapsed))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out[::-1]


def split_categories(rng: random.Random, mb: int) -> dict:
    w = {k: v * rng.uniform(0.6, 1.4) for k, v in CAT_WEIGHTS.items()}
    s = sum(w.values())
    return {k: int(mb * v / s) for k, v in sorted(w.items(), key=lambda kv: -kv[1])}


def daily_series(rng: random.Random, total_mb: int, days: int) -> list[int]:
    w = [rng.uniform(0.5, 1.5) for _ in range(days)]
    s = sum(w)
    return [int(total_mb * x / s) for x in w]


def build_month(rng, msisdn, cust_id, name, tariff_id, region, prof, month, dim, elapsed, idx) -> dict:
    t = C.TARIFFS[tariff_id]
    partial = elapsed < dim
    frac = elapsed / dim
    limit_mb = t.get("data_mb") or t.get("fup_mb") or 0
    costs = {"monthly_fee": t["monthly_fee"], "packages": 0.0, "vas": 0.0, "roaming": 0.0,
             "out_of_bundle": 0.0, "intl_calls": 0.0}
    packages: list[dict] = []

    if tariff_id == "T_PAYG":
        data_mb = int(rng.randint(*prof["data_mb"]) * frac)
        costs["out_of_bundle"] += min(data_mb * C.OOB["data_per_mb"], C.OOB["data_daily_cap"] * elapsed)
    else:
        data_mb = int(limit_mb * rng.uniform(*prof["data_use"]) * frac)
    over = max(0, data_mb - limit_mb) if limit_mb else 0
    while over > 0:  # extra data bought as packages
        pid = "P_FUP10" if tariff_id == "T_MAX" else "P_NET5"
        p = C.PACKAGES[pid]
        packages.append({"package_id": pid, "name": p["name"], "price": p["price"]})
        costs["packages"] += p["price"]
        over -= p["data_mb"]

    voice_lim, sms_lim = t["voice_min"], t["sms"]
    voice_min = int(voice_lim * rng.uniform(0.2, 1.05) * frac) if tariff_id != "T_PAYG" else int(rng.randint(40, 160) * frac)
    sms = int(rng.randint(5, 60) * frac)
    if tariff_id == "T_PAYG":
        costs["out_of_bundle"] += voice_min * C.OOB["voice_per_min"] + sms * C.OOB["sms"]
    else:
        costs["out_of_bundle"] += max(0, voice_min - voice_lim) * C.OOB["voice_per_min"]

    vas_items = []
    if prof.get("vas"):
        v = C.VAS[prof["vas"]]
        amt = v["price"] * (elapsed if v["period"] == "gün" else 1)
        vas_items.append({"vas_id": prof["vas"], "name": v["name"], "amount": r2(amt), "period": v["period"]})
        costs["vas"] += amt

    roaming = None
    if prof.get("roaming") and idx == prof["roaming"][1]:
        country = prof["roaming"][0]
        zone = C.zone_for(country)
        pid = {"TR": "P_TR1", "GE": "P_GE1"}.get(country, "P_EU2")
        p = C.PACKAGES[pid]
        extra_mb = rng.randint(80, 400)
        extra = extra_mb * C.ROAMING_ZONES[zone]["data_per_mb"] * 0.1
        roaming = {"country": country, "country_name": C.COUNTRY_NAMES[country], "zone": zone, "days": rng.randint(4, 9),
                   "package": p["name"], "package_price": p["price"], "extra_charges": r2(extra)}
        costs["roaming"] += p["price"] + extra

    if prof.get("intl"):
        mins = int(rng.randint(30, 90) * frac)
        costs["intl_calls"] += mins * C.INTL_CALL_RATES["TR"]

    costs = {k: r2(v) for k, v in costs.items()}
    total = r2(sum(costs.values()))

    credits = []
    if rng.random() < 0.3:
        credits.append({"reason": "Şəbəkə kəsintisinə görə kompensasiya", "amount": rng.choice([1.0, 3.0])})
    if vas_items and idx == MONTHS - 2:
        credits.append({"reason": f"{vas_items[0]['name']} razılıq olmadan aktivləşdirildi — qaytarıldı",
                        "amount": r2(vas_items[0]["amount"])})
    credit_total = r2(sum(c["amount"] for c in credits))

    cats = split_categories(rng, data_mb)
    daily = daily_series(rng, data_mb, elapsed)
    item = {
        "msisdn": msisdn, "month": month, "customer_id": cust_id, "full_name": name,
        "tariff_id": tariff_id, "tariff_name": t["name"], "region": region, "currency": C.CURRENCY,
        "is_current": partial, "days_elapsed": elapsed, "days_in_month": dim,
        "costs": costs, "total": total, "credits": credits, "credits_total": credit_total,
        "net_total": r2(total - credit_total),
        "forecast_total": r2(costs["monthly_fee"] + (total - costs["monthly_fee"]) / frac) if partial else total,
        "usage": {
            "data_mb": data_mb, "data_limit_mb": limit_mb,
            "data_pct": round(100 * data_mb / limit_mb, 1) if limit_mb else None,
            "voice_min": voice_min, "voice_limit_min": voice_lim,
            "voice_pct": round(100 * voice_min / voice_lim, 1) if voice_lim else None,
            "sms": sms, "sms_limit": sms_lim,
        },
        "data_by_category": cats,
        "top_category": next(iter(cats)) if data_mb else None,
        "daily_data_mb": daily,
        "peak_day": (daily.index(max(daily)) + 1) if daily else None,
        "packages": packages, "vas": vas_items, "roaming": roaming,
    }
    return item


def add_insights(items: list[dict]) -> None:
    """Month-over-month change and Azerbaijani tips, computed from the line's own history."""
    for i, it in enumerate(items):
        prev = items[i - 1] if i else None
        it["prev_month_total"] = prev["total"] if prev else None
        base = it["forecast_total"]
        it["change_pct"] = round(100 * (base - prev["total"]) / prev["total"], 1) if prev and prev["total"] else None
        tips, saving = [], 0.0
        u, tid = it["usage"], it["tariff_id"]
        if it["vas"]:
            v = it["vas"][0]
            tips.append(f"{v['name']} abunəliyi bu ay {v['amount']:.2f} AZN tutub. İstifadə etmirsinizsə, ləğv edə bilərsiniz.")
            saving += v["amount"] / (it["days_elapsed"] / it["days_in_month"])
        if it["costs"]["packages"] >= 6 and tid in ("T_START", "T_GENC", "T_PLUS"):
            nxt = {"T_START": "T_PLUS", "T_GENC": "T_PLUS", "T_PLUS": "T_MAX"}[tid]
            diff = C.TARIFFS[nxt]["monthly_fee"] - C.TARIFFS[tid]["monthly_fee"]
            if it["costs"]["packages"] > diff:
                tips.append(f"Bu ay əlavə paketlərə {it['costs']['packages']:.2f} AZN xərclədiniz. "
                            f"{C.TARIFFS[nxt]['name']} tarifinə keçsəniz, daha sərfəli olar.")
                saving += it["costs"]["packages"] - diff
        if u["data_pct"] is not None and u["data_pct"] < 40 and not it["is_current"] and tid in ("T_MAX", "T_PLUS"):
            lower = {"T_MAX": "T_PLUS", "T_PLUS": "T_START"}[tid]
            diff = C.TARIFFS[tid]["monthly_fee"] - C.TARIFFS[lower]["monthly_fee"]
            tips.append(f"İnternet paketinizin yalnız {u['data_pct']:.0f}%-ni istifadə edirsiniz. "
                        f"{C.TARIFFS[lower]['name']} tarifi ilə ayda {diff:.2f} AZN qənaət edə bilərsiniz.")
            saving += diff
        if tid == "T_PAYG" and it["forecast_total"] > C.TARIFFS["T_START"]["monthly_fee"]:
            tips.append(f"Bu ay təxminən {it['forecast_total']:.2f} AZN xərcləyəcəksiniz. "
                        f"Səma Start (9 AZN, 10 GB) tarifi daha sərfəlidir.")
            saving += it["forecast_total"] - C.TARIFFS["T_START"]["monthly_fee"]
        if it["roaming"]:
            r = it["roaming"]
            tips.append(f"{r['country_name']} səfərində rouminq paketi ilə {r['package_price']:.2f} AZN ödədiniz.")
        it["insights"] = tips
        it["potential_savings"] = r2(saving)


def aggregate(month: str, items: list[dict]) -> dict:
    n = len(items)
    cats: dict[str, int] = {}
    for it in items:
        for k, v in it["data_by_category"].items():
            cats[k] = cats.get(k, 0) + v
    tariff_mix: dict[str, int] = {}
    for it in items:
        tariff_mix[it["tariff_name"]] = tariff_mix.get(it["tariff_name"], 0) + 1
    return {
        "msisdn": "#ALL", "month": month, "lines": n, "currency": C.CURRENCY,
        "is_current": items[0]["is_current"],
        "avg_total": r2(sum(i["total"] for i in items) / n),
        "avg_data_mb": int(sum(i["usage"]["data_mb"] for i in items) / n),
        "avg_voice_min": int(sum(i["usage"]["voice_min"] for i in items) / n),
        "revenue_total": r2(sum(i["total"] for i in items)),
        "credits_total": r2(sum(i["credits_total"] for i in items)),
        "credits_count": sum(len(i["credits"]) for i in items),
        "potential_savings_total": r2(sum(i["potential_savings"] for i in items)),
        "cost_breakdown": {k: r2(sum(i["costs"][k] for i in items)) for k in items[0]["costs"]},
        "data_by_category": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "tariff_mix": tariff_mix,
        "roaming_trips": sum(1 for i in items if i["roaming"]),
    }


def build(now: datetime, seed: int = 7) -> list[dict]:
    w = World(now, seed=seed)
    rng = w.rng
    months = month_list(now)
    by_month: dict[str, list[dict]] = {m: [] for m, _, _ in months}
    out = []
    for name, tariff_id, region, prof in LINES:
        msisdn, cust_id = w.next_msisdn(), w.next_customer_id()
        hist = [build_month(rng, msisdn, cust_id, name, tariff_id, region, prof, m, dim, el, i)
                for i, (m, dim, el) in enumerate(months)]
        add_insights(hist)
        for it in hist:
            by_month[it["month"]].append(it)
        out += hist
    out += [aggregate(m, its) for m, its in by_month.items()]
    return out


def to_ddb(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False), parse_float=Decimal)


def push(items: list[dict]) -> None:
    import boto3
    name = settings.table_prefix + TABLE
    client = boto3.client("dynamodb", region_name=settings.aws_region)
    try:
        client.describe_table(TableName=name)
        print(f"table {name} exists")
    except client.exceptions.ResourceNotFoundException:
        client.create_table(
            TableName=name, BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "msisdn", "AttributeType": "S"},
                                  {"AttributeName": "month", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "msisdn", "KeyType": "HASH"},
                       {"AttributeName": "month", "KeyType": "RANGE"}])
        client.get_waiter("table_exists").wait(TableName=name)
        print(f"table {name} created")
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(name)
    with table.batch_writer(overwrite_by_pkeys=["msisdn", "month"]) as bw:
        for it in items:
            bw.put_item(Item=to_ddb(it))
    print(f"pushed {len(items)} items to {name}")


def write_mock(items: list[dict], out_dir: str) -> None:
    """Same JSON the API returns (docs/USAGE_TABLE.md §3), newest month first."""
    from pathlib import Path
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    by_line: dict[str, list[dict]] = {}
    for it in items:
        by_line.setdefault(it["msisdn"], []).append(it)
    for msisdn, its in by_line.items():
        its = sorted(its, key=lambda i: i["month"], reverse=True)
        if msisdn == "#ALL":
            body, fname = {"currency": C.CURRENCY, "months": its}, "summary.json"
        else:
            body, fname = {"msisdn": msisdn, "currency": C.CURRENCY, "months": its}, f"{msisdn.lstrip('+')}.json"
        (out / fname).write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(by_line)} files to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", metavar="DIR", help="write API-shaped JSON responses for the frontend, no DB")
    args = ap.parse_args()
    items = build(settings.now())
    if args.mock:
        write_mock(items, args.mock)
    elif args.dry_run:
        print(json.dumps(items[MONTHS - 1], ensure_ascii=False, indent=2))
        print(json.dumps(items[-1], ensure_ascii=False, indent=2))
        print(f"{len(items)} items")
    else:
        push(items)
