"""Run the 63 eval cases against the real agent (in-process, fresh data copy per case).

    python -m eval.run                      # all cases
    python -m eval.run --ids S01,S04,B03    # subset
    python -m eval.run --mode rules         # LLM-free baseline (keyword router + policy engine)

Writes eval/results/<run_id>/{results.json, report.md}.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import time
from pathlib import Path

from app.agent import domain
from app.agent.orchestrator import Agent, detect_language
from app.config import settings
from app.rag.index import KnowledgeBase
from app.store.local import LocalStore

ROOT = Path(__file__).resolve().parents[1]
BASE = LocalStore(settings.seed_dir)
KB = KnowledgeBase(settings.kb_dir)
APPLY_KEYS = {"unsubscribed": "unsubscribe_vas", "reprovisioned": "reprovision_package", "promo_granted": "grant_promo"}


async def run_agent_case(case: dict) -> dict:
    store = BASE.clone()
    agent = Agent(store, KB)
    s = agent.start_session(case["msisdn"], case.get("channel", "web"))
    finals, t0 = [], time.perf_counter()
    for i, turn in enumerate(case["turns"]):
        finals.append(await agent.run_turn(s, turn, f"m{i}"))
    case_rec = store.get_case(s.case_id) or {}
    actions = set()
    for f in finals:
        actions |= set(f.get("actions") or [])
    for e in store.list_events(case["msisdn"], since=settings.now().isoformat()):
        if e["type"] == "VAS_UNSUBSCRIBE":
            actions.add("unsubscribe_vas")
        if e["type"] == "PACKAGE_ACTIVATED" and e["channel"] == "agent":
            actions.add("grant_promo" if e["data"]["kind"] == "promo" else "reprovision_package")
    last = finals[-1]
    credited = round(sum((f.get("amount") or 0) for f in finals), 2)
    decision = last["decision"]
    if case_rec.get("team") or any(f.get("handoff") for f in finals):
        decision = "SPECIALIST"
    elif credited > 0 and decision != "GOODWILL":
        decision = "REFUND"
    return {"decision": decision, "credited": credited, "team": case_rec.get("team"), "actions": sorted(actions),
            "texts": [f["text"] for f in finals], "citations": sorted({c for f in finals for c in f.get("citations", [])}),
            "first_token_ms": [f["latency_ms"]["first_token"] for f in finals],
            "total_ms": [f["latency_ms"]["total"] for f in finals],
            "cost_usd": round(sum(f["tokens"]["cost_usd"] for f in finals), 5), "wall_s": round(time.perf_counter() - t0, 1)}


KEYWORDS = [  # rules-only baseline: crude intent routing, no LLM
    (r"iki dəfə|2 dəfə|дважды|ikiqat", "DOUBLE_CHARGE"), (r"rouminq|роуминг", "ROAMING_WHILE_DISABLED"),
    (r"abunə|подпис|fal|melodiya|qoruma|xəbər", "VAS_NO_CONSENT"), (r"çıxmışdım|ləğv", "VAS_AFTER_UNSUBSCRIBE"),
    (r"limit", "OOB_CAP_EXCEEDED"), (r"yüklədim|balansa gəlmə", "TOPUP_NOT_CREDITED"), (r"kompensasiya", "OUTAGE_COMPENSATION"),
    (r"bonus", "PROMO_NOT_APPLIED"), (r"avtomatik yenilə", "AUTORENEW_AFTER_DISABLE"), (r"sms", "SMS_IN_PACKAGE_CHARGED"),
    (r"komissiya", "LOAN_FEE_DUPLICATE"), (r"paket.*(görünmür|yoxdu)", "PACKAGE_NOT_ACTIVATED"),
]


def run_rules_case(case: dict) -> dict:
    store = BASE.clone()
    text = " ".join(case["turns"]).lower()
    ct = next((c for pat, c in KEYWORDS if re.search(pat, text)), None)
    out = {"decision": "INFO", "credited": 0.0, "team": None, "actions": [], "texts": [], "citations": [],
           "first_token_ms": [0], "total_ms": [0], "cost_usd": 0.0, "wall_s": 0.0}
    if ct:
        res = domain.evaluate(store, case["msisdn"], ct, settings.now())
        if res["decision"] in ("REFUND", "FIX"):
            a = domain.apply_resolution(store, case["msisdn"], res["resolution_id"], settings.now(), "CS-RULES")
            out.update(decision=res["decision"], credited=a.get("credited_azn", 0.0),
                       actions=[v for k, v in APPLY_KEYS.items() if k in a])
        elif res["decision"] == "SPECIALIST":
            out.update(decision="SPECIALIST", team=res["team"])
        else:
            out["decision"] = "EXPLAIN"
    return out


def score(case: dict, got: dict) -> dict:
    exp = case["expected"]
    texts = " ".join(got["texts"]).lower()
    banned = [b for b in exp["must_not_contain"] if b.lower() in texts]
    lang_ok = True
    if got["texts"] and exp["language"] in ("az", "ru"):
        lang_ok = all(detect_language(t, exp["language"]) == exp["language"] for t in got["texts"])
    amount_ok = exp["amount"] is None or abs(got["credited"] - exp["amount"]) < 0.011
    wrong_credit = got["credited"] > 0 and (exp["forbid_credit"] or (exp["amount"] is not None and got["credited"] > exp["amount"] + 0.011))
    return {
        "decision_ok": got["decision"] == exp["decision"],
        "amount_ok": amount_ok,
        "wrong_credit": wrong_credit,
        "team_ok": exp["team"] is None or got["team"] == exp["team"],
        "actions_ok": set(exp["actions"]) <= set(got["actions"]),
        "language_ok": lang_ok,
        "banned": banned,
        "contains_ok": not exp["must_contain_any"] or any(x.lower() in texts for x in exp["must_contain_any"]),
        "kb_hit": not exp["kb_docs"] or any(c.split("#")[0] in exp["kb_docs"] for c in got["citations"]),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--mode", default="agent", choices=["agent", "rules"])
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))["cases"]
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    sem = asyncio.Semaphore(args.concurrency)

    async def one(c):
        async with sem:
            try:
                got = await run_agent_case(c) if args.mode == "agent" else run_rules_case(c)
            except Exception as e:  # noqa: BLE001 — a crashed case is a failed case, keep going
                got = {"decision": "ERROR", "credited": 0.0, "team": None, "actions": [], "texts": [str(e)], "citations": [],
                       "first_token_ms": [None], "total_ms": [None], "cost_usd": 0.0, "wall_s": 0.0}
            sc = score(c, got)
            ok = sc["decision_ok"] and sc["amount_ok"] and not sc["wrong_credit"] and sc["team_ok"]
            print(f'{c["id"]:4} {"PASS" if ok else "FAIL"} exp={c["expected"]["decision"]:10} got={got["decision"]:10} '
                  f'cr={got["credited"]:<5} {"" if sc["actions_ok"] else "actions-missing "}{"banned:" + ",".join(sc["banned"]) if sc["banned"] else ""}',
                  flush=True)
            return {"id": c["id"], "category": c["category"], "holdout": c["holdout"], "expected": c["expected"], "got": got,
                    "score": sc, "pass": ok}

    results = await asyncio.gather(*[one(c) for c in cases])
    n = len(results)
    hold = [r for r in results if r["holdout"]]
    ft = [x for r in results for x in r["got"]["first_token_ms"] if x]
    tot = [x for r in results for x in r["got"]["total_ms"] if x]
    pct = lambda xs, p: (sorted(xs)[min(len(xs) - 1, int(len(xs) * p))] if xs else None)  # noqa: E731
    summary = {
        "mode": args.mode, "cases": n, "now": settings.now().isoformat(),
        "decision_correct": sum(r["score"]["decision_ok"] for r in results),
        "passed": sum(r["pass"] for r in results),
        "holdout_passed": f'{sum(r["pass"] for r in hold)}/{len(hold)}',
        "wrong_credits": sum(r["score"]["wrong_credit"] for r in results),
        "specialist_team_ok": f'{sum(r["score"]["team_ok"] and r["got"]["decision"] == "SPECIALIST" for r in results if r["expected"]["team"])}/'
                              f'{sum(1 for r in results if r["expected"]["team"])}',
        "actions_ok": sum(r["score"]["actions_ok"] for r in results),
        "language_ok": sum(r["score"]["language_ok"] for r in results),
        "banned_phrase_cases": sum(bool(r["score"]["banned"]) for r in results),
        "kb_hit": sum(r["score"]["kb_hit"] for r in results),
        "first_token_ms_p50": statistics.median(ft) if ft else None, "total_ms_p50": statistics.median(tot) if tot else None,
        "total_ms_p95": pct(tot, 0.95), "cost_usd_total": round(sum(r["got"]["cost_usd"] for r in results), 4),
        "by_category": {cat: f'{sum(r["pass"] for r in results if r["category"] == cat)}/{sum(1 for r in results if r["category"] == cat)}'
                        for cat in sorted({r["category"] for r in results})},
    }
    run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{args.mode}"
    out = ROOT / "eval" / "results" / run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Eval {run_id}", "", "```", json.dumps(summary, ensure_ascii=False, indent=1), "```", "", "## Failures", ""]
    for r in results:
        if not r["pass"] or r["score"]["banned"] or not r["score"]["actions_ok"]:
            lines.append(f'- **{r["id"]}** exp {r["expected"]["decision"]} {r["expected"]["amount"]} {r["expected"]["team"] or ""} → '
                         f'got {r["got"]["decision"]} {r["got"]["credited"]} {r["got"]["team"] or ""}; actions {r["got"]["actions"]}; '
                         f'banned {r["score"]["banned"]}\n  > {(r["got"]["texts"] or [""])[-1][:300]}')
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
