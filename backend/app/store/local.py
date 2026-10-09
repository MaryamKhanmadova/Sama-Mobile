"""In-memory store loaded from the seed JSON files. Used for local dev, tests and eval
(each eval case gets a fresh clone, because actions mutate the data)."""
from __future__ import annotations

import copy
import json
import threading
from collections import defaultdict
from pathlib import Path

from .base import Store, apply_patch


class LocalStore(Store):
    def __init__(self, seed_dir: Path | None = None, *, _data: dict | None = None):
        self._lock = threading.RLock()
        if _data is None:
            _data = self._load(seed_dir)
        self._pristine = _data
        self._reset_from(_data)

    @staticmethod
    def _load(seed_dir: Path | None) -> dict:
        data = {"customers": [], "lines": [], "events": [], "incidents": [], "catalog": {}, "kb_chunks": []}
        if seed_dir is None or not Path(seed_dir).exists():
            return data
        for name in data:
            f = Path(seed_dir) / f"{name}.json"
            if f.exists():
                data[name] = json.loads(f.read_text(encoding="utf-8"))
        return data

    def _reset_from(self, data: dict) -> None:
        d = copy.deepcopy(data)
        self.customers = {c["customer_id"]: c for c in d["customers"]}
        self.lines = {ln["msisdn"]: ln for ln in d["lines"]}
        self.events: dict[str, list[dict]] = defaultdict(list)
        for e in d["events"]:
            self.events[e["msisdn"]].append(e)
        for evs in self.events.values():
            evs.sort(key=lambda e: (e["ts"], e["event_id"]))
        self.incidents = d["incidents"]
        self.catalog = d["catalog"]
        self.kb_chunks = d.get("kb_chunks", [])
        self.resolutions: dict[str, dict] = {}
        self.adjustments: dict[str, list[dict]] = defaultdict(list)
        self.adj_keys: set[str] = set()
        self.cases: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}

    def clone(self) -> "LocalStore":
        """Fresh copy of the pristine seed data (for isolated eval runs)."""
        return LocalStore(_data=self._pristine)

    def reset(self) -> None:
        with self._lock:
            self._reset_from(self._pristine)

    # ---- reads ----
    def get_line(self, msisdn):
        return copy.deepcopy(self.lines.get(msisdn))

    def get_customer(self, customer_id):
        return copy.deepcopy(self.customers.get(customer_id))

    def list_events(self, msisdn, since=None, until=None, types=None):
        out = []
        for e in self.events.get(msisdn, []):
            if since and e["ts"] < since:
                continue
            if until and e["ts"] > until:
                continue
            if types and e["type"] not in types:
                continue
            out.append(e)
        return copy.deepcopy(out)

    def list_incidents(self, region=None):
        return [copy.deepcopy(i) for i in self.incidents if region is None or i["region"] == region]

    def get_catalog(self):
        return self.catalog

    # ---- writes ----
    def apply_mutation(self, msisdn, events, line_patch=None):
        with self._lock:
            for e in events:
                self.events[msisdn].append(copy.deepcopy(e))
            self.events[msisdn].sort(key=lambda e: (e["ts"], e["event_id"]))
            if line_patch:
                apply_patch(self.lines[msisdn], line_patch)

    def put_resolution(self, res):
        with self._lock:
            self.resolutions[res["resolution_id"]] = copy.deepcopy(res)

    def get_resolution(self, resolution_id):
        return copy.deepcopy(self.resolutions.get(resolution_id))

    def mark_resolution_applied(self, resolution_id):
        with self._lock:
            r = self.resolutions.get(resolution_id)
            if not r or r.get("applied"):
                return False
            r["applied"] = True
            return True

    def put_adjustment(self, adj):
        with self._lock:
            if adj["idempotency_key"] in self.adj_keys:
                return False
            self.adj_keys.add(adj["idempotency_key"])
            self.adjustments[adj["msisdn"]].append(copy.deepcopy(adj))
            return True

    def list_adjustments(self, msisdn, since=None):
        return [copy.deepcopy(a) for a in self.adjustments.get(msisdn, []) if not since or a["ts"] >= since]

    def put_case(self, case):
        with self._lock:
            self.cases[case["case_id"]] = copy.deepcopy(case)

    def get_case(self, case_id):
        return copy.deepcopy(self.cases.get(case_id))

    def list_cases(self, status=None, msisdn=None, limit=100):
        cs = [c for c in self.cases.values()
              if (status is None or c.get("status") == status) and (msisdn is None or c.get("msisdn") == msisdn)]
        cs.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return copy.deepcopy(cs[:limit])

    def put_session_meta(self, meta):
        with self._lock:
            s = self.sessions.setdefault(meta["session_id"], {"turns": []})
            s["meta"] = copy.deepcopy(meta)

    def append_session_turn(self, session_id, seq, turn):
        with self._lock:
            s = self.sessions.setdefault(session_id, {"turns": [], "meta": {}})
            s["turns"].append({"seq": seq, **copy.deepcopy(turn)})

    def get_session(self, session_id):
        return copy.deepcopy(self.sessions.get(session_id))

    def list_kb_chunks(self):
        return self.kb_chunks

    def put_kb_chunks(self, chunks):
        self.kb_chunks = list(chunks)
