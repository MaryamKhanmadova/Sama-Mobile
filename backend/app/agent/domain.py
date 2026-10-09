"""Business logic the agent's tools call: snapshot, investigation, policy engine, actions, handoffs.
Deterministic — the LLM never computes money; it can only apply a resolution_id issued here."""
from __future__ import annotations

import hashlib
import random
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from app import catalog as C
from app.agent.detectors import detect
from app.store.base import Store

OPERATOR_FAULT_TYPES = {
    "DOUBLE_CHARGE": ["R-BILL-02"], "PACKAGE_NOT_ACTIVATED": ["R-PKG-02"], "VAS_NO_CONSENT": ["R-VAS-02"],
    "VAS_AFTER_UNSUBSCRIBE": ["R-VAS-03"], "ROAMING_WHILE_DISABLED": ["R-ROAM-03"], "OOB_CAP_EXCEEDED": ["R-OOB-02"],
    "TOPUP_NOT_CREDITED": ["R-PAY-01"], "OUTAGE_COMPENSATION": ["R-NET-02"], "PROMO_NOT_APPLIED": ["R-PROMO-01"],
    "AUTORENEW_AFTER_DISABLE": ["R-PKG-04"], "SMS_IN_PACKAGE_CHARGED": ["R-SMS-01"],
    "LOAN_FEE_DUPLICATE": ["R-LOAN-02"],
}
CASE_TYPES = sorted(OPERATOR_FAULT_TYPES) + ["GOODWILL_REQUEST"]
NOTABLE = {"PACKAGE_EXHAUSTED", "PACKAGE_EXPIRED", "PACKAGE_PURCHASE_REQUEST", "SETTING_CHANGE", "VAS_SUBSCRIBE",
           "VAS_UNSUBSCRIBE", "ROAMING_ATTACH", "ROAMING_DETACH", "DEVICE_CHANGE", "SIM_SWAP", "PIN_LOCK",
           "LOAN_TAKEN", "BALANCE_TRANSFER_OUT", "PROMO_ELIGIBLE", "PROMO_GRANTED", "TARIFF_CHANGE", "LINE_STATUS",
           "FUP_THROTTLED", "PORT_REQUEST", "TICKET", "INVOICE", "ADJUSTMENT", "APP_LOGIN", "PAYMENT"}


def r2(x: float) -> float:
    return round(x + 1e-9, 2)


def mask(msisdn: str) -> str:
    return msisdn[:6] + "***" + msisdn[-4:] if msisdn and len(msisdn) > 10 else msisdn


def new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


def compact(e: dict) -> dict:
    d = {k: v for k, v in e["data"].items() if v is not None and k not in ("puk",)}
    if "to_msisdn" in d:
        d["to_msisdn"] = mask(d["to_msisdn"])
    return {"id": e["event_id"], "ts": e["ts"][:16], "type": e["type"], **({"ch": e["channel"]} if e.get("channel") else {}), **d}


def _since(now: datetime, days: int) -> str:
    return (now - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------- snapshot
def build_snapshot(store: Store, msisdn: str, now: datetime) -> dict:
    line = store.get_line(msisdn) or {}
    cust = store.get_customer(line.get("customer_id", "")) or {}
    events = store.list_events(msisdn, since=_since(now, 45))
    t = C.TARIFFS.get(line.get("tariff_id"), {})
    active = []
    for e in events:
        if e["type"] == "PACKAGE_ACTIVATED" and e["data"]["expires_at"] > now.isoformat():
            ended = any(x["type"] in ("PACKAGE_EXHAUSTED", "PACKAGE_EXPIRED")
                        and x["data"].get("instance_id") == e["data"]["instance_id"] for x in events)
            pid = e["data"]["package_id"]
            name = (C.PACKAGES.get(pid, {}).get("name") or (t.get("name") if pid.startswith("TARIFF") else None)
                    or ("Yüklə-Qazan bonus 2 GB" if pid.startswith("PROMO") else pid))
            active.append({"package_id": pid, "name": name, "activated": e["ts"][:16], "expires": e["data"]["expires_at"][:16],
                           "data_mb": e["data"].get("data_mb"), "status": "bitib" if ended else "aktiv"})
    charges = [compact(e) for e in events if e["type"] == "CHARGE"][-10:]
    topups = [compact(e) for e in events if e["type"] == "TOPUP"][-3:]
    settings_changes = [compact(e) for e in events if e["type"] == "SETTING_CHANGE" and e["ts"] >= _since(now, 14)]
    tickets = [compact(e) for e in events if e["type"] == "TICKET"]
    incidents = [{k: i[k] for k in ("incident_id", "start_ts", "end_ts", "status", "severity", "services", "summary_az", "eta")}
                 for i in store.list_incidents(line.get("region")) if i["start_ts"] >= _since(now, 30)]
    sim = {k: v for k, v in (line.get("sim") or {}).items() if k != "puk"}
    return {
        "now": now.isoformat()[:16],
        "customer": {"name": cust.get("full_name"), "language": cust.get("language"), "tenure_months": cust.get("tenure_months"),
                     "segment": cust.get("segment"), "vulnerable": cust.get("vulnerable"), "loyalty_tier": cust.get("loyalty_tier"),
                     "birth_year": cust.get("birth_year"), "notes": cust.get("notes") or None},
        "line": {"msisdn": mask(msisdn), "tariff": f'{line.get("tariff_id")} ({t.get("name")}, {t.get("monthly_fee")} AZN/ay)',
                 "status": line.get("status"), "balance_azn": line.get("balance"), "region": line.get("region"),
                 "settings": line.get("settings"), "device": line.get("device"), "sim": sim,
                 "active_vas": line.get("active_vas"), "postpaid": line.get("postpaid")},
        "packages": active, "last_charges": charges, "last_topups": topups,
        "setting_changes_14d": settings_changes, "tickets": tickets, "region_incidents_30d": incidents,
    }


# ---------------------------------------------------------------- investigation
def investigate(store: Store, msisdn: str, now: datetime, focus: str | None = None) -> dict:
    line = store.get_line(msisdn)
    events = store.list_events(msisdn, since=_since(now, 45))
    incidents = store.list_incidents(line["region"])
    anomalies = [{**f, "rule_ids": OPERATOR_FAULT_TYPES.get(f["case_type"], [])} for f in detect(line, events, incidents, now)]

    by_reason: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0, "items": []})
    for e in events:
        if e["type"] == "CHARGE" and e["ts"] >= _since(now, 30):
            b = by_reason[e["data"]["reason"]]
            b["total"] = r2(b["total"] + e["data"]["amount"])
            b["count"] += 1
            if len(b["items"]) < 6:
                b["items"].append(compact(e))
    cats: dict[str, int] = defaultdict(int)
    for e in events:
        if e["type"] == "DATA_USAGE" and e["ts"] >= _since(now, 7):
            for c, mb in (e["data"].get("by_category") or {}).items():
                cats[c] += mb

    flags = []
    s, d = line["settings"], line["device"]
    if not s.get("data_enabled", True):
        flags.append("DATA_DISABLED: mobil internet xətt üzrə söndürülüb")
    if s.get("volte") and not d.get("supports_volte"):
        flags.append(f'VOLTE_MISMATCH: {d.get("model")} VoLTE dəstəkləmir, amma VoLTE açıqdır')
    dev = [e for e in events if e["type"] == "DEVICE_CHANGE"]
    if dev and not any(e["type"] == "DATA_USAGE" and e["ts"] > dev[-1]["ts"] for e in events):
        flags.append(f'DEVICE_CHANGED_NO_DATA: {dev[-1]["ts"][:16]} cihaz dəyişib ({dev[-1]["data"]["model"]}), sonra internet istifadəsi yoxdur')
    swaps = [e for e in events if e["type"] == "SIM_SWAP" and e["ts"] >= _since(now, 14)]
    if swaps:
        flags.append(f'RECENT_SIM_SWAP: {swaps[-1]["ts"][:16]} {swaps[-1]["data"].get("store")}')
    if line.get("status") != "active":
        flags.append(f'LINE_STATUS: {line.get("status")}')
    if any(i["status"] == "ongoing" for i in incidents):
        flags.append("ONGOING_OUTAGE: regionda davam edən qəza var (check_network_status)")
    tickets = [e for e in events if e["type"] == "TICKET" and e["ts"] >= _since(now, 30)]
    if len(tickets) >= C.POLICY["repeat_contact_threshold"]:
        flags.append(f"REPEAT_CONTACT: son 30 gündə {len(tickets)} müraciət (R-ESC-02)")
    if line.get("sim", {}).get("pin_status") != "ok":
        flags.append(f'SIM: {line["sim"]["pin_status"]}')

    notable = [compact(e) for e in events if e["type"] in NOTABLE and e["ts"] >= _since(now, 30)][-25:]
    return {"anomalies_operator_fault": anomalies, "flags": flags, "charges_by_reason_30d": dict(by_reason),
            "data_by_category_mb_7d": dict(sorted(cats.items(), key=lambda kv: -kv[1])), "notable_events_30d": notable,
            "hint": "Anomaliya varsa evaluate_resolution(case_type) çağır. Yoxdursa kəsintini bu faktlarla izah et."}


# ---------------------------------------------------------------- policy engine
def evaluate(store: Store, msisdn: str, case_type: str, now: datetime) -> dict:
    line = store.get_line(msisdn)
    cust = store.get_customer(line["customer_id"])
    events = store.list_events(msisdn, since=_since(now, 45))
    res = {"resolution_id": new_id("RS-"), "msisdn": msisdn, "case_type": case_type, "amount": None, "rule_ids": [],
           "evidence_event_ids": [], "allowed_actions": [], "requires_confirmation": False, "team": None,
           "applied": False, "created_at": now.isoformat(), "expires_at": (now + timedelta(minutes=30)).isoformat()}
    recent_adj = [e for e in events if e["type"] == "ADJUSTMENT" and e["ts"] >= _since(now, 30)
                  and e["data"].get("kind") != "fix"]

    if case_type == "GOODWILL_REQUEST":
        oob = [e for e in events if e["type"] == "CHARGE" and e["data"]["reason"] == "oob_data" and e["ts"] >= _since(now, 7)]
        gw_recent = [e for e in store.list_events(msisdn, since=_since(now, C.POLICY["goodwill_cooldown_days"]))
                     if e["type"] == "ADJUSTMENT" and e["data"].get("rule_id") == "R-GW-01"]
        total = r2(sum(e["data"]["amount"] for e in oob))
        if cust["tenure_months"] >= C.POLICY["goodwill_min_tenure_months"] and not gw_recent and total > 0:
            res.update(decision="GOODWILL", amount=min(r2(total * C.POLICY["goodwill_share"]), C.POLICY["goodwill_max"]),
                       rule_ids=["R-GW-01"], evidence_event_ids=[e["event_id"] for e in oob], allowed_actions=["credit_balance"],
                       facts={"oob_7d_total": total, "tenure_months": cust["tenure_months"]})
        else:
            res.update(decision="EXPLAIN", rule_ids=["R-GW-01"],
                       facts={"reason": "jest krediti şərtləri ödənmir", "tenure_months": cust["tenure_months"],
                              "oob_7d_total": total, "goodwill_in_180d": bool(gw_recent)})
        store.put_resolution(res)
        return res

    if case_type not in OPERATOR_FAULT_TYPES:
        res.update(decision="NOT_CONFIRMED", facts={"reason": f"naməlum case_type; mümkün olanlar: {CASE_TYPES}"})
        return res

    finding = next((f for f in detect(line, events, store.list_incidents(line["region"]), now) if f["case_type"] == case_type), None)
    if not finding:
        res.update(decision="NOT_CONFIRMED", facts={"reason": "məlumatlarda bu problem təsdiqlənmir"})
        store.put_resolution(res)
        return res

    res.update(rule_ids=OPERATOR_FAULT_TYPES[case_type], evidence_event_ids=finding["evidence"], amount=finding["amount"])
    if case_type == "PROMO_NOT_APPLIED":
        res.update(decision="FIX", amount=None, allowed_actions=["grant_promo"])
    elif case_type == "PACKAGE_NOT_ACTIVATED":
        charge = next(e for e in events if e["event_id"] == finding["evidence"][0])
        if now - datetime.fromisoformat(charge["ts"]) <= timedelta(days=7):
            res.update(decision="FIX", amount=None, allowed_actions=["reprovision_package"])
        else:
            res.update(decision="REFUND", allowed_actions=["credit_balance"])
    else:
        res.update(decision="REFUND", allowed_actions=["credit_balance"])
        if case_type in ("VAS_NO_CONSENT", "VAS_AFTER_UNSUBSCRIBE"):
            res["allowed_actions"].append("unsubscribe_vas")

    if res["decision"] == "REFUND":
        if res["amount"] > C.POLICY["auto_credit_max_per_case"]:
            res.update(decision="SPECIALIST", team="BILLING", allowed_actions=[], rule_ids=res["rule_ids"] + ["R-ADJ-01"])
        elif len(recent_adj) >= C.POLICY["auto_credits_per_30d"]:
            res.update(decision="SPECIALIST", team="BILLING", allowed_actions=[], rule_ids=res["rule_ids"] + ["R-ADJ-02"])
    store.put_resolution(res)
    return res


def apply_resolution(store: Store, msisdn: str, resolution_id: str, now: datetime, case_id: str) -> dict:
    res = store.get_resolution(resolution_id)
    if not res or res["msisdn"] != msisdn:
        return {"applied": False, "error": "resolution tapılmadı"}
    if res["expires_at"] < now.isoformat():
        return {"applied": False, "error": "resolution-un vaxtı keçib, yenidən evaluate_resolution çağır"}
    if res["decision"] not in ("REFUND", "GOODWILL", "FIX"):
        return {"applied": False, "error": f'{res["decision"]} qərarı tətbiq olunmur'}
    if not store.mark_resolution_applied(resolution_id):
        return {"applied": False, "error": "artıq tətbiq olunub"}
    line = store.get_line(msisdn)
    events, patch, result = [], {}, {}
    ts = now.isoformat()
    if res["decision"] in ("REFUND", "GOODWILL"):
        key = hashlib.sha1((res["case_type"] + "|" + ",".join(sorted(res["evidence_event_ids"]))).encode()).hexdigest()
        adj = {"msisdn": msisdn, "ts": ts, "adj_id": new_id("ADJ-"), "amount": res["amount"], "case_id": case_id,
               "resolution_id": resolution_id, "rule_id": res["rule_ids"][0], "idempotency_key": key}
        if not store.put_adjustment(adj):
            return {"applied": False, "error": "bu kəsinti artıq qaytarılıb"}
        new_bal = r2(line["balance"] + res["amount"])
        events.append({"msisdn": msisdn, "ts": ts, "event_id": new_id("X"), "type": "ADJUSTMENT", "channel": "agent",
                       "data": {"amount": res["amount"], "case_id": case_id, "rule_id": res["rule_ids"][0],
                                "resolution_id": resolution_id, "refs": res["evidence_event_ids"], "balance_after": new_bal}})
        patch["balance"] = new_bal
        result = {"credited_azn": res["amount"], "new_balance_azn": new_bal}
    if "unsubscribe_vas" in res["allowed_actions"]:
        vas_ids = {e["data"]["vas_id"] for e in store.list_events(msisdn) if e["event_id"] in res["evidence_event_ids"]
                   and e["type"] in ("VAS_SUBSCRIBE", "VAS_UNSUBSCRIBE")}
        for v in vas_ids:
            events.append({"msisdn": msisdn, "ts": ts, "event_id": new_id("X"), "type": "VAS_UNSUBSCRIBE", "channel": "agent",
                           "data": {"vas_id": v}})
        patch["active_vas"] = [v for v in line["active_vas"] if v not in vas_ids]
        result["unsubscribed"] = sorted(vas_ids)
    if "reprovision_package" in res["allowed_actions"]:
        charge = next(e for e in store.list_events(msisdn) if e["event_id"] == res["evidence_event_ids"][0])
        p = C.PACKAGES[charge["data"]["ref"]]
        events.append({"msisdn": msisdn, "ts": ts, "event_id": new_id("X"), "type": "PACKAGE_ACTIVATED", "channel": "agent",
                       "data": {"package_id": charge["data"]["ref"], "instance_id": new_id("PI-"),
                                "charge_event_id": charge["event_id"], "expires_at": (now + timedelta(days=p["days"])).isoformat(),
                                "data_mb": p.get("data_mb"), "sms": p.get("sms"), "kind": "addon"}})
        events.append({"msisdn": msisdn, "ts": ts, "event_id": new_id("X"), "type": "ADJUSTMENT", "channel": "agent",
                       "data": {"amount": 0, "kind": "fix", "rule_id": "R-PKG-02", "case_id": case_id, "refs": res["evidence_event_ids"]}})
        result["reprovisioned"] = {"package": p["name"], "expires": (now + timedelta(days=p["days"])).isoformat()[:16]}
    if "grant_promo" in res["allowed_actions"]:
        ev = next(e for e in store.list_events(msisdn) if e["event_id"] in res["evidence_event_ids"])
        promo = C.PROMOS[ev["data"]["promo_id"]]
        events.append({"msisdn": msisdn, "ts": ts, "event_id": new_id("X"), "type": "PROMO_GRANTED", "channel": "agent",
                       "data": {"promo_id": ev["data"]["promo_id"], "payment_id": ev["data"]["payment_id"], "bonus_mb": promo["bonus_mb"]}})
        events.append({"msisdn": msisdn, "ts": ts, "event_id": new_id("X"), "type": "PACKAGE_ACTIVATED", "channel": "agent",
                       "data": {"package_id": "PROMO:" + ev["data"]["promo_id"], "instance_id": new_id("PI-"), "charge_event_id": None,
                                "expires_at": (now + timedelta(days=promo["days"])).isoformat(), "data_mb": promo["bonus_mb"], "kind": "promo"}})
        result["promo_granted"] = {"bonus_mb": promo["bonus_mb"], "days": promo["days"]}
    store.apply_mutation(msisdn, events, patch)
    return {"applied": True, "decision": res["decision"], "rule_ids": res["rule_ids"], **result}


# ---------------------------------------------------------------- service actions
CONFIRM_REQUIRED = {"set_roaming:true", "block_line_temporarily", "set_volte:false", "reveal_puk", "send_esim_qr"}
LEVEL2 = {"reveal_puk", "send_esim_qr"}


def perform_action(store: Store, msisdn: str, action: str, params: dict, confirmed: bool, verified_level: int,
                   now: datetime) -> dict:
    line = store.get_line(msisdn)
    key = action + (f':{str(params.get("enabled")).lower()}' if "enabled" in params else "")
    if (key in CONFIRM_REQUIRED or action in CONFIRM_REQUIRED) and not confirmed:
        return {"ok": False, "error": "müştərinin açıq təsdiqi lazımdır (user_confirmed=true)"}
    if action in LEVEL2 and verified_level < 2:
        return {"ok": False, "error": "əvvəlcə verify_identity (2-ci səviyyə)"}
    ts = now.isoformat()
    ev = lambda t, **d: {"msisdn": msisdn, "ts": ts, "event_id": new_id("X"), "type": t, "channel": "agent", "data": d}  # noqa: E731

    def setting(name: str, value):
        old = line["settings"].get(name)
        store.apply_mutation(msisdn, [ev("SETTING_CHANGE", setting=name, old=old, new=value)], {f"settings.{name}": value})
        return {"ok": True, "result": {name: value}}

    if action == "set_data_enabled":
        return setting("data_enabled", bool(params.get("enabled", True)))
    if action == "set_roaming":
        return setting("roaming_enabled", bool(params.get("enabled")))
    if action == "set_volte":
        return setting("volte", bool(params.get("enabled")))
    if action == "disable_auto_renew":
        return setting("auto_renew", False)
    if action == "block_premium_sms":
        return setting("premium_sms_blocked", True)
    if action == "unsubscribe_vas":
        vid = params.get("vas_id")
        if vid not in line["active_vas"]:
            return {"ok": False, "error": f"aktiv VAS: {line['active_vas']}"}
        store.apply_mutation(msisdn, [ev("VAS_UNSUBSCRIBE", vas_id=vid)],
                             {"active_vas": [v for v in line["active_vas"] if v != vid]})
        return {"ok": True, "result": {"unsubscribed": vid, "name": C.VAS[vid]["name"]}}
    if action == "send_apn_settings":
        store.apply_mutation(msisdn, [ev("SMS_SENT", template="APN_SETTINGS", apn="sema.net")])
        return {"ok": True, "result": {"sms_sent": "APN ayarları (sema.net)"}}
    if action == "reveal_puk":
        return {"ok": True, "result": {"puk": line["sim"]["puk"], "note": "PUK-u yalnız müştəriyə de, heç yerə yazma"}}
    if action == "send_esim_qr":
        store.apply_mutation(msisdn, [ev("ESIM_QR_SENT", to="registered_email")])
        cust = store.get_customer(line["customer_id"])
        return {"ok": True, "result": {"sent_to": cust.get("email_masked"), "valid_minutes": 60}}
    if action == "block_line_temporarily":
        store.apply_mutation(msisdn, [ev("LINE_STATUS", status="blocked", reason="customer_request_security")],
                             {"status": "blocked"})
        return {"ok": True, "result": {"status": "blocked"}}
    return {"ok": False, "error": f"naməlum hərəkət: {action}"}


def verify_identity(store: Store, msisdn: str, fin_last4: str, birth_year: int) -> dict:
    cust = store.get_customer_by_msisdn(msisdn)
    ok = cust and str(cust["fin_last4"]) == str(fin_last4).strip() and int(cust["birth_year"]) == int(birth_year)
    return {"verified": bool(ok), "level": 2 if ok else 1}


def create_handoff(store: Store, msisdn: str, team: str, priority: str, summary: str, reason: str, language: str,
                   now: datetime, case_id: str) -> dict:
    if team not in C.TEAMS:
        return {"ok": False, "error": f"komandalar: {sorted(C.TEAMS)}"}
    t = C.TEAMS[team]
    lang = "ru" if language == "ru" else "az"
    ticket = f"SM-2026-{random.randint(40000, 99999)}"
    store.apply_mutation(msisdn, [{"msisdn": msisdn, "ts": now.isoformat(), "event_id": new_id("X"), "type": "TICKET",
                                   "channel": "agent", "data": {"ticket_id": ticket, "topic": reason[:60], "status": "open",
                                                                "team": team, "priority": priority, "case_id": case_id}}])
    return {"ok": True, "ticket_no": ticket, "team": team, "team_name": t[lang], "sla": t[f"sla_{lang}"], "priority": priority}
