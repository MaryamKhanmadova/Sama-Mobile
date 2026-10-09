"""Operator-fault detectors (docs/BACKEND_SPEC.md §5.2). Pure functions, no LLM.
detect(line, events, incidents, now) -> [{case_type, amount, evidence}]"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from app import catalog as C


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _r2(x: float) -> float:
    return round(x + 1e-9, 2)


def setting_at(line: dict, events: list[dict], key: str, ts: str):
    changes = [e for e in events if e["type"] == "SETTING_CHANGE" and e["data"]["setting"] == key]
    before = [e for e in changes if e["ts"] <= ts]
    if before:
        return before[-1]["data"]["new"]
    after = [e for e in changes if e["ts"] > ts]
    if after:
        return after[0]["data"]["old"]
    return line["settings"][key]


def detect(line: dict, events: list[dict], incidents: list[dict], now: datetime) -> list[dict]:
    """Operator-fault detectors. Returns [{case_type, amount, evidence}]."""
    found = []
    # anything already refunded/fixed (ADJUSTMENT.refs) is excluded, so a re-check after resolution is clean
    adjusted = {r for e in events if e["type"] == "ADJUSTMENT" for r in e["data"].get("refs", [])}
    charges = [e for e in events if e["type"] == "CHARGE" and e["event_id"] not in adjusted]
    activations = [e for e in events if e["type"] == "PACKAGE_ACTIVATED"]
    activated_charge_ids = {e["data"].get("charge_event_id") for e in activations}

    # DOUBLE_CHARGE (packages within 10 min, monthly fee within 25 days) + PACKAGE_NOT_ACTIVATED
    dup_ids = set()
    pkg = [c for c in charges if c["data"]["reason"] == "package_purchase"]
    for i, a in enumerate(pkg):
        for b in pkg[i + 1:]:
            if (b["data"]["ref"] == a["data"]["ref"] and _dt(b["ts"]) - _dt(a["ts"]) <= timedelta(minutes=10)
                    and b["event_id"] not in activated_charge_ids and a["event_id"] in activated_charge_ids):
                dup_ids.add(b["event_id"])
    fees = [c for c in charges if c["data"]["reason"] == "monthly_fee"]
    for i, a in enumerate(fees):
        for b in fees[i + 1:]:
            if b["data"]["ref"] == a["data"]["ref"] and _dt(b["ts"]) - _dt(a["ts"]) < timedelta(days=25):
                dup_ids.add(b["event_id"])
    dup = [c for c in charges if c["event_id"] in dup_ids and c["event_id"] not in adjusted]
    if dup:
        found.append({"case_type": "DOUBLE_CHARGE", "amount": _r2(sum(c["data"]["amount"] for c in dup)),
                      "evidence": [c["event_id"] for c in dup]})
    na = [c for c in pkg if c["event_id"] not in activated_charge_ids and c["event_id"] not in dup_ids
          and now - _dt(c["ts"]) > timedelta(minutes=10)]
    if na:
        found.append({"case_type": "PACKAGE_NOT_ACTIVATED", "amount": _r2(sum(c["data"]["amount"] for c in na)),
                      "evidence": [c["event_id"] for c in na]})

    # VAS
    for sub in [e for e in events if e["type"] == "VAS_SUBSCRIBE"]:
        vid = sub["data"]["vas_id"]
        unsub = next((e for e in events if e["type"] == "VAS_UNSUBSCRIBE" and e["data"]["vas_id"] == vid
                      and e["ts"] > sub["ts"]), None)
        vas_ch = [c for c in charges if c["data"]["reason"] == "vas" and c["data"]["ref"] == vid and c["ts"] > sub["ts"]]
        if sub["event_id"] in adjusted:
            continue
        if not sub["data"]["consent_confirmed"]:
            if vas_ch:
                found.append({"case_type": "VAS_NO_CONSENT", "amount": _r2(sum(c["data"]["amount"] for c in vas_ch)),
                              "evidence": [sub["event_id"]] + [c["event_id"] for c in vas_ch]})
        elif unsub:
            after = [c for c in vas_ch if c["ts"] > unsub["ts"]]
            if after:
                found.append({"case_type": "VAS_AFTER_UNSUBSCRIBE",
                              "amount": _r2(sum(c["data"]["amount"] for c in after)),
                              "evidence": [unsub["event_id"]] + [c["event_id"] for c in after]})

    # ROAMING_WHILE_DISABLED
    roam = [c for c in charges if c["data"]["reason"] in ("roaming_data", "roaming_voice")
            and not setting_at(line, events, "roaming_enabled", c["ts"])]
    if roam:
        found.append({"case_type": "ROAMING_WHILE_DISABLED", "amount": _r2(sum(c["data"]["amount"] for c in roam)),
                      "evidence": [c["event_id"] for c in roam]})

    # OOB_CAP_EXCEEDED
    per_day = defaultdict(list)
    for c in charges:
        if c["data"]["reason"] == "oob_data":
            per_day[c["ts"][:10]].append(c)
    excess = sum(max(0.0, sum(c["data"]["amount"] for c in cs) - C.OOB["data_daily_cap"]) for cs in per_day.values())
    if excess > 0.004:
        found.append({"case_type": "OOB_CAP_EXCEEDED", "amount": _r2(excess), "evidence": []})

    # TOPUP_NOT_CREDITED
    credited = {e["data"]["payment_id"] for e in events if e["type"] == "TOPUP"}
    lost = [e for e in events if e["type"] == "PAYMENT" and e["data"]["status"] == "success"
            and e["data"]["purpose"] == "topup" and e["data"]["payment_id"] not in credited
            and e["event_id"] not in adjusted
            and now - _dt(e["ts"]) > timedelta(minutes=C.POLICY["topup_credit_grace_min"])]
    if lost:
        found.append({"case_type": "TOPUP_NOT_CREDITED", "amount": _r2(sum(e["data"]["amount"] for e in lost)),
                      "evidence": [e["event_id"] for e in lost]})

    # OUTAGE_COMPENSATION
    for inc in incidents:
        if inc["region"] != line["region"] or inc["status"] != "resolved":
            continue
        hours = (_dt(inc["end_ts"]) - _dt(inc["start_ts"])).total_seconds() / 3600
        if now - _dt(inc["end_ts"]) > timedelta(days=30) or inc["incident_id"] in adjusted:
            continue
        amt = next((a for h, a in C.POLICY["outage_tiers"] if hours >= h), 0)
        if amt:
            found.append({"case_type": "OUTAGE_COMPENSATION", "amount": amt, "evidence": [inc["incident_id"]]})

    # PROMO_NOT_APPLIED
    granted = {e["data"]["payment_id"] for e in events if e["type"] == "PROMO_GRANTED"}
    missing = [e for e in events if e["type"] == "PROMO_ELIGIBLE" and e["data"]["payment_id"] not in granted]
    if missing:
        found.append({"case_type": "PROMO_NOT_APPLIED", "amount": None, "evidence": [e["event_id"] for e in missing]})

    # AUTORENEW_AFTER_DISABLE
    off = [e for e in events if e["type"] == "SETTING_CHANGE" and e["data"]["setting"] == "auto_renew"
           and e["data"]["new"] is False]
    if off:
        bad = [c for c in pkg if c["data"].get("trigger") == "auto_renew" and c["ts"] > off[0]["ts"]]
        if bad:
            found.append({"case_type": "AUTORENEW_AFTER_DISABLE", "amount": _r2(sum(c["data"]["amount"] for c in bad)),
                          "evidence": [c["event_id"] for c in bad]})

    # SMS_IN_PACKAGE_CHARGED
    def sms_bundle_active(ts):
        for a in activations:
            if (a["data"].get("sms") and a["ts"] <= ts < a["data"]["expires_at"]
                    and not any(e["type"] == "PACKAGE_EXHAUSTED" and e["data"]["instance_id"] == a["data"]["instance_id"]
                                and e["data"]["resource"] == "sms" and e["ts"] <= ts for e in events)):
                return True
        return False
    sms = [c for c in charges if c["data"]["reason"] == "oob_sms" and sms_bundle_active(c["ts"])]
    if sms:
        found.append({"case_type": "SMS_IN_PACKAGE_CHARGED", "amount": _r2(sum(c["data"]["amount"] for c in sms)),
                      "evidence": [c["event_id"] for c in sms]})

    # LOAN_FEE_DUPLICATE
    fees_by_loan = defaultdict(list)
    for c in charges:
        if c["data"]["reason"] == "loan_fee":
            fees_by_loan[c["data"]["ref"]].append(c)
    extra = [c for cs in fees_by_loan.values() for c in cs[1:]]
    if extra:
        found.append({"case_type": "LOAN_FEE_DUPLICATE", "amount": _r2(sum(c["data"]["amount"] for c in extra)),
                      "evidence": [c["event_id"] for c in extra]})
    return found
