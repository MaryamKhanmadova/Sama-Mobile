"""Generate the full synthetic dataset + eval cases.

    python -m data.seed.generate --now 2026-10-09T12:00:00+04:00

Writes data/seed/out/{customers,lines,events,incidents,catalog}.json and eval/cases.json.
Deterministic: same --now and --seed -> identical output.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from app import catalog as C
from data.seed.scenarios import HOLDOUT, SCENARIOS
from data.seed.world import DEVICES, LineBuilder, World

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "seed" / "out"
CASES = ROOT / "eval" / "cases.json"


def build_incidents(w: World) -> None:
    w.incident("Gəncə", w.ts(5, 8, 0), w.ts(5, 17, 30), "major", ["data", "voice"],
               "Gəncə şəhərində magistral optik xəttin zədələnməsi; mobil internet və zənglər işləmirdi.")
    w.incident("Sumqayıt", w.ts(0, 9, 30), None, "major", ["data"],
               "Sumqayıtda baza stansiyalarının elektrik təchizatında nasazlıq; mobil internet işləmir.",
               eta=(w.now.replace(hour=15, minute=0)).isoformat())
    w.incident("Şəki", w.ts(40, 6, 0), w.ts(40, 20, 0), "major", ["data", "voice"],
               "Şəki rayonunda güclü külək nəticəsində antena dirəyinin zədələnməsi.")
    w.incident("Bakı-Xətai", w.ts(3, 14, 0), w.ts(3, 16, 0), "minor", ["data"],
               "Xətai rayonunda planlı texniki işlər; internet sürəti aşağı idi.")


def background_customers(w: World, n: int = 25) -> None:
    rng = w.rng
    tariffs = ["T_START", "T_PLUS", "T_PLUS", "T_MAX", "T_GENC", "T_PAYG", "T_BIZNES"]
    for _ in range(n):
        tariff = rng.choice(tariffs)
        lb = LineBuilder(w, tariff=tariff, region=rng.choice(C.REGIONS), lang=rng.choice(["az"] * 4 + ["ru"]),
                         tenure_months=rng.randint(3, 120), renewal_days_ago=rng.randint(1, 28),
                         device=rng.choice(DEVICES), segment="postpaid" if tariff == "T_BIZNES" else "prepaid",
                         birth_year=rng.randint(1999, 2003) if tariff == "T_GENC" else None)
        if rng.random() < 0.3:  # consented VAS
            lb.vas_subscribe(w.ts(rng.randint(5, 30), 15, 0), rng.choice(["V_MELODIYA", "V_XEBER", "V_FAL"]),
                             "sms_optin", consent=True)
        if rng.random() < 0.35 and tariff not in ("T_PAYG", "T_BIZNES"):  # an add-on package
            d = rng.randint(2, 20)
            lb.topup(w.ts(d, 9, 0), 10, method=rng.choice(["card_app", "terminal"]))
            lb.buy_package(w.ts(d, 9, 5), rng.choice(["P_NET5", "P_SOSIAL", "P_GECE"]), channel="app")
        if rng.random() < 0.15 and tariff != "T_BIZNES":  # a legit trip with roaming enabled + country package
            d = rng.randint(8, 25)
            lb.set_setting(w.ts(d + 1, 20, 0), "roaming_enabled", True)
            lb.ev(w.ts(d, 8, 0), "ROAMING_ATTACH", channel="network", country="TR", zone="Z1")
            lb.topup(w.ts(d, 8, 10), 10, method="card_app")
            lb.buy_package(w.ts(d, 8, 15), "P_TR1", channel="app")
            lb.ev(w.ts(d - 4, 21, 0), "ROAMING_DETACH", channel="network", country="TR", zone="Z1")
        finalize(lb, w)


def finalize(lb: LineBuilder, w: World) -> dict:
    if C.TARIFFS[lb.tariff].get("postpaid") and lb.postpaid is None:
        lb.postpaid = {"due_date": (w.now + timedelta(days=20)).replace(hour=23, minute=59, second=0).isoformat(),
                       "amount_due": 0.0, "overdue_days": 0}
    return lb.finalize()


def catalog_items() -> list[dict]:
    items = []
    for kind, table in [("tariff", C.TARIFFS), ("package", C.PACKAGES), ("vas", C.VAS), ("promo", C.PROMOS)]:
        for item_id, v in table.items():
            items.append({"item_id": item_id, "item_type": kind, **v})
    for zone, v in C.ROAMING_ZONES.items():
        items.append({"item_id": zone, "item_type": "roaming_zone", **v})
    items.append({"item_id": "OOB", "item_type": "rates", **C.OOB})
    items.append({"item_id": "INTL_CALLS", "item_type": "rates", **C.INTL_CALL_RATES})
    items.append({"item_id": "LOAN", "item_type": "rates", "amounts": {str(k): v for k, v in C.LOAN["amounts"].items()},
                  "min_tenure_months": C.LOAN["min_tenure_months"]})
    items.append({"item_id": "BALANCE_TRANSFER", "item_type": "rates", **C.BALANCE_TRANSFER})
    items.append({"item_id": "POLICY", "item_type": "policy",
                  **{k: v for k, v in C.POLICY.items() if k != "outage_tiers"},
                  "outage_tiers": [{"min_hours": h, "amount": a} for h, a in C.POLICY["outage_tiers"]]})
    for team, v in C.TEAMS.items():
        items.append({"item_id": team, "item_type": "team", **v})
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default="2026-10-09T12:00:00+04:00")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    w = World(datetime.fromisoformat(args.now), seed=args.seed)
    build_incidents(w)

    cases = []
    for sid, category, title, fn in SCENARIOS:
        lb, turns, expected = fn(w)
        line = finalize(lb, w)
        cases.append({
            "id": sid, "category": category, "title": title, "holdout": sid in HOLDOUT,
            "msisdn": line["msisdn"], "customer_id": line["customer_id"], "channel": "web",
            "language": expected["language"], "turns": turns, "expected": expected,
        })
    background_customers(w)

    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"customers": w.customers, "lines": w.lines, "events": w.events, "incidents": w.incidents,
               "catalog": catalog_items()}
    for name, data in payload.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    CASES.parent.mkdir(parents=True, exist_ok=True)
    CASES.write_text(json.dumps({"generated_for_now": args.now, "cases": cases}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"customers={len(w.customers)} lines={len(w.lines)} events={len(w.events)} "
          f"incidents={len(w.incidents)} cases={len(cases)} holdout={sum(c['holdout'] for c in cases)}")


if __name__ == "__main__":
    main()
