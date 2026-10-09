"""Tool definitions (OpenAI/OpenRouter format) + executor bound to one session.
msisdn is never a tool parameter: every tool works on the session's verified line only."""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from app import catalog as C
from app.agent import domain
from app.config import settings

ACTIONS = ["set_data_enabled", "set_roaming", "set_volte", "unsubscribe_vas", "disable_auto_renew", "block_premium_sms",
           "send_apn_settings", "reveal_puk", "send_esim_qr", "block_line_temporarily"]
DECISIONS = ["REFUND", "FIX", "EXPLAIN", "GOODWILL", "SPECIALIST", "INFO", "REFUSE", "CLARIFY"]


def _fn(name: str, desc: str, props: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required, "additionalProperties": False}}}


TOOLS = [
    _fn("get_timeline", "Müştərinin son N gündəki hadisələri (kəsintilər, paketlər, ayarlar, istifadə). Ən çox 60 hadisə.",
        {"days": {"type": "integer", "minimum": 1, "maximum": 45},
         "types": {"type": "array", "items": {"type": "string"}, "description": "məs. CHARGE, PACKAGE_ACTIVATED, SETTING_CHANGE"}},
        ["days"]),
    _fn("investigate_account", "Hesabı avtomatik araşdır: operator xətası anomaliyaları, bayraqlar, kəsintilərin səbəb üzrə bölgüsü, "
        "internetin kateqoriya bölgüsü, son vacib hadisələr. Problemi anlamaq üçün ilk addım.",
        {"focus": {"type": "string", "enum": ["billing", "data", "roaming", "vas", "device", "security", "all"]}}, []),
    _fn("search_knowledge", "Səma bilik bazasında (qaydalar, qiymətlər, prosedurlar) axtarış. Qaydanı deməzdən əvvəl istifadə et.",
        {"query": {"type": "string"}}, ["query"]),
    _fn("check_network_status", "Müştərinin regionunda aktiv və son qəzalar.", {}, []),
    _fn("evaluate_resolution", "Policy Engine: pulla bağlı problemi qaydalarla yoxlayır və qərar + resolution_id qaytarır. "
        "Pul məsələsində MƏCBURİDİR. GOODWILL_REQUEST: kəsinti düzgündür, amma müştəri qaytarma istəyir.",
        {"case_type": {"type": "string", "enum": domain.CASE_TYPES}}, ["case_type"]),
    _fn("apply_resolution", "evaluate_resolution-un REFUND/GOODWILL/FIX qərarını tətbiq edir (pul balansa, paket aktivləşir və s.).",
        {"resolution_id": {"type": "string"}}, ["resolution_id"]),
    _fn("perform_service_action", "Xidmət hərəkəti. set_roaming(enabled=true), set_volte(enabled=false), block_line_temporarily, "
        "reveal_puk, send_esim_qr müştərinin açıq 'bəli'si ilə (user_confirmed=true). PUK/eSIM üçün əvvəl verify_identity.",
        {"action": {"type": "string", "enum": ACTIONS},
         "params": {"type": "object", "description": "məs. {\"enabled\": true} və ya {\"vas_id\": \"V_FAL\"}"},
         "user_confirmed": {"type": "boolean"}}, ["action"]),
    _fn("verify_identity", "2-ci səviyyə yoxlama: FİN-in son 4 rəqəmi və doğum ili.",
        {"fin_last4": {"type": "string"}, "birth_year": {"type": "integer"}}, ["fin_last4", "birth_year"]),
    _fn("create_handoff", "Mütəxəssis komandasına bilet aç. Cavabda komanda adı, SLA və bilet nömrəsi gəlir — müştəriyə onları de.",
        {"team": {"type": "string", "enum": sorted(C.TEAMS)}, "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
         "summary": {"type": "string"}, "reason": {"type": "string"}}, ["team", "priority", "summary", "reason"]),
    _fn("record_outcome", "Müştəriyə yekun cavabını GÖRÜNƏN MƏTN kimi yazdıqdan SONRA bir dəfə çağır (cavabsız çağırma). Müraciətin nəticəsini qeyd edir.",
        {"decision": {"type": "string", "enum": DECISIONS}, "root_cause": {"type": "string"},
         "summary": {"type": "string"}, "language": {"type": "string", "enum": ["az", "ru"]}},
        ["decision", "root_cause", "summary"]),
]
STATUS_LABELS = {
    "get_timeline": "Hesab tarixçəsinə baxılır…", "investigate_account": "Hesab araşdırılır…",
    "search_knowledge": "Qaydalar yoxlanılır…", "check_network_status": "Şəbəkə vəziyyəti yoxlanılır…",
    "evaluate_resolution": "Qərar hesablanır…", "apply_resolution": "Həll tətbiq olunur…",
    "perform_service_action": "Ayar dəyişdirilir…", "verify_identity": "Şəxsiyyət yoxlanılır…",
    "create_handoff": "Mütəxəssisə bilet açılır…", "record_outcome": "Nəticə qeyd olunur…",
}


class ToolExecutor:
    def __init__(self, session, store, kb):
        self.s, self.store, self.kb = session, store, kb

    def run(self, name: str, raw_args: str) -> dict:
        try:
            args: dict[str, Any] = json.loads(raw_args or "{}")
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
        except (json.JSONDecodeError, ValueError) as e:
            return {"error": f"INVALID_JSON: {e}"}
        try:
            return getattr(self, f"t_{name}")(**args)
        except AttributeError:
            return {"error": f"naməlum alət {name}"}
        except TypeError as e:
            return {"error": f"yanlış parametrlər: {e}"}

    @property
    def now(self):
        return settings.now()

    def t_get_timeline(self, days: int = 14, types: list[str] | None = None):
        since = (self.now - timedelta(days=min(max(int(days), 1), 45))).isoformat()
        evs = self.store.list_events(self.s.msisdn, since=since, types=set(types) if types else None)
        evs = [e for e in evs if types or e["type"] not in ("DATA_USAGE", "VOICE_USAGE", "SMS_USAGE")] or evs
        return {"count": len(evs), "events": [domain.compact(e) for e in evs[-60:]]}

    def t_investigate_account(self, focus: str = "all"):
        return domain.investigate(self.store, self.s.msisdn, self.now, focus)

    def t_search_knowledge(self, query: str):
        hits = self.kb.search(query, k=4)
        self.s.citations.update(h["chunk_id"] for h in hits)
        return {"results": [{"chunk_id": h["chunk_id"], "text": h["text"][:1400], "rule_ids": h["rule_ids"]} for h in hits]}

    def t_check_network_status(self):
        line = self.store.get_line(self.s.msisdn)
        inc = [i for i in self.store.list_incidents(line["region"])
               if i["status"] == "ongoing" or i["start_ts"] >= (self.now - timedelta(days=30)).isoformat()]
        return {"region": line["region"], "incidents": inc}

    def t_evaluate_resolution(self, case_type: str):
        res = domain.evaluate(self.store, self.s.msisdn, case_type, self.now)
        self.s.rule_ids.update(res.get("rule_ids", []))
        if res.get("decision") == "SPECIALIST":
            res["next"] = f'create_handoff(team="{res["team"]}") çağır; pulu özün vəd etmə'
        return {k: v for k, v in res.items() if k not in ("msisdn", "applied", "created_at")}

    def t_apply_resolution(self, resolution_id: str, user_confirmed: bool = False):
        out = domain.apply_resolution(self.store, self.s.msisdn, resolution_id, self.now, self.s.case_id)
        if out.get("applied"):
            self.s.applied.append(out)
        return out

    def t_perform_service_action(self, action: str, params: dict | None = None, user_confirmed: bool = False):
        out = domain.perform_action(self.store, self.s.msisdn, action, params or {}, bool(user_confirmed),
                                    self.s.verified_level, self.now)
        if out.get("ok"):
            self.s.actions.append(action)
        return out

    def t_verify_identity(self, fin_last4: str, birth_year: int):
        out = domain.verify_identity(self.store, self.s.msisdn, fin_last4, birth_year)
        if out["verified"]:
            self.s.verified_level = 2
        return out

    def t_create_handoff(self, team: str, priority: str, summary: str, reason: str):
        out = domain.create_handoff(self.store, self.s.msisdn, team, priority, summary, reason, self.s.language,
                                    self.now, self.s.case_id)
        if out.get("ok"):
            self.s.handoff = out
        return out

    def t_record_outcome(self, decision: str, root_cause: str, summary: str, language: str | None = None):
        self.s.outcome = {"decision": decision, "root_cause": root_cause, "summary": summary}
        if language:
            self.s.language = language
        return {"ok": True}
