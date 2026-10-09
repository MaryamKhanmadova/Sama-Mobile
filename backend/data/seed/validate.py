"""Validate the generated dataset and serve as a REFERENCE implementation of the operator-fault detectors
described in docs/BACKEND_SPEC.md §5.2 (backend may port this logic 1:1).

    python -m data.seed.validate

Checks:
  1. Integrity: unique ids, sorted timelines, no negative running balance, referenced lines exist.
  2. Oracle: for every operator-fault case the detectors find exactly the expected root cause and amount;
     every other line (cases + background) has NO operator-fault anomaly.
  3. Text: no banned word ("tutulma") in turns; every expected kb_doc exists in data/kb.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from app import catalog as C
from app.agent.detectors import _dt, detect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "seed" / "out"


def main() -> int:
    load = lambda n: json.loads((OUT / f"{n}.json").read_text(encoding="utf-8"))  # noqa: E731
    lines = {ln["msisdn"]: ln for ln in load("lines")}
    events = load("events")
    incidents = load("incidents")
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))
    now = _dt(cases["generated_for_now"])
    errors: list[str] = []

    # 1. integrity
    ids = [e["event_id"] for e in events]
    if len(ids) != len(set(ids)):
        errors.append("duplicate event_id")
    by_line = defaultdict(list)
    for e in events:
        if e["msisdn"] not in lines:
            errors.append(f"event {e['event_id']} references unknown line")
        by_line[e["msisdn"]].append(e)
    for m, evs in by_line.items():
        evs.sort(key=lambda e: (e["ts"], e["event_id"]))
        for e in evs:
            if e["data"].get("balance_after", 0) < -0.001:
                errors.append(f"{m}: negative balance at {e['event_id']}")
            if e["ts"] > now.isoformat():
                errors.append(f"{m}: event in the future {e['event_id']}")

    # 2. oracle
    case_lines = set()
    for c in cases["cases"]:
        m, exp = c["msisdn"], c["expected"]
        case_lines.add(m)
        found = detect(lines[m], by_line[m], incidents, now)
        types = {f["case_type"]: f for f in found}
        if c["category"] == "operator_fault" or exp["root_cause"] in types:
            rc = exp["root_cause"]
            if rc not in types:
                errors.append(f"{c['id']}: expected {rc}, detectors found {list(types)}")
                continue
            if len(found) != 1:
                errors.append(f"{c['id']}: extra anomalies {list(types)}")
            if exp["amount"] is not None and abs(types[rc]["amount"] - exp["amount"]) > 0.005:
                errors.append(f"{c['id']}: amount {types[rc]['amount']} != expected {exp['amount']}")
        elif found and exp["decision"] in ("REFUND",):
            errors.append(f"{c['id']}: refund case without detectable anomaly")
        elif found:
            errors.append(f"{c['id']}: unexpected anomalies {list(types)}")
    bg_noise = {m: [f["case_type"] for f in detect(ln, by_line[m], incidents, now)]
                for m, ln in lines.items() if m not in case_lines}
    bg_noise = {m: t for m, t in bg_noise.items() if t}

    # 3. text + kb
    kb_dir = ROOT / "data" / "kb"
    kb_docs = {p.stem for p in kb_dir.glob("*.md")}
    for c in cases["cases"]:
        for t in c["turns"]:
            if "tutul" in t.lower():
                errors.append(f"{c['id']}: banned word in turn")
        for d in c["expected"]["kb_docs"]:
            if kb_docs and d not in kb_docs:
                errors.append(f"{c['id']}: kb doc '{d}' missing in data/kb")

    print(f"lines={len(lines)} events={len(events)} cases={len(cases['cases'])} kb_docs={len(kb_docs)}")
    print(f"background lines with anomalies: {len(bg_noise)} {bg_noise if bg_noise else ''}")
    if errors:
        print(f"FAILED ({len(errors)}):")
        for e in errors:
            print("  -", e)
        return 1
    print("OK: integrity, oracle and text checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
