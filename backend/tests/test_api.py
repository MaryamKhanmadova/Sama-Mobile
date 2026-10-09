"""End-to-end API tests with a scripted fake LLM (no network). Run: pytest -q"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.agent.voice import StreamFilter, az_words, normalize_for_voice

CASES = {c["id"]: c for c in json.loads((main.ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))["cases"]}


def scripted_llm(script):
    """script: list of steps; each step = (text, [ (tool_name, args_dict), ... ])."""
    steps = iter(script)

    async def fake(model, effort, messages, tools, max_tokens=1500):
        text, calls = next(steps)
        for part in text.split(" "):
            if part:
                yield "text", part + " "
        if calls:
            yield "tool_calls_started", None
        # resolve placeholders from previous tool results (resolution_id)
        last_tool = next((m for m in reversed(messages) if m["role"] == "tool"), None)
        rid = None
        if last_tool:
            try:
                c = last_tool["content"]
                c = c if isinstance(c, str) else "".join(part["text"] for part in c)  # cache_control parts
                rid = json.loads(c).get("resolution_id")
            except json.JSONDecodeError:
                pass
        tool_calls = [{"id": f"call_{i}", "name": n,
                       "arguments": json.dumps({k: (rid if v == "$RID" else v) for k, v in a.items()})}
                      for i, (n, a) in enumerate(calls)]
        yield "done", {"content": text, "tool_calls": tool_calls, "finish_reason": "tool_calls" if calls else "stop",
                       "usage": {"prompt_tokens": 100, "completion_tokens": 20}, "reasoning_details": []}
    return fake


@pytest.fixture()
def client():
    main.store.reset()
    keys = main.settings.api_keys
    return TestClient(main.app, headers={"X-API-Key": keys[0]} if keys else {})


def read_sse(resp) -> list[tuple[str, dict]]:
    out, ev = [], None
    for line in resp.iter_lines():
        if line.startswith("event:"):
            ev = line[6:].strip()
        elif line.startswith("data:") and ev:
            out.append((ev, json.loads(line[5:])))
    return out


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["rag_chunks"] > 50


def test_s01_double_charge_refund(client):
    main.agent.llm = scripted_llm([
        ("Bir saniyə, yoxlayıram.", [("investigate_account", {"focus": "billing"})]),
        ("", [("evaluate_resolution", {"case_type": "DOUBLE_CHARGE"})]),
        ("", [("apply_resolution", {"resolution_id": "$RID"})]),
        ("Yoxladım: paket üçün 10 AZN iki dəfə kəsilib. Artıq 10 AZN balansınıza qaytardım.",
         [("record_outcome", {"decision": "REFUND", "root_cause": "DOUBLE_CHARGE", "summary": "ikiqat kəsinti qaytarıldı"})]),
    ])
    msisdn = CASES["S01"]["msisdn"]
    before = main.store.get_line(msisdn)["balance"]
    sid = client.post("/v1/sessions", json={"msisdn": msisdn}).json()["session_id"]
    with client.stream("POST", f"/v1/sessions/{sid}/messages:stream", json={"text": CASES["S01"]["turns"][0]}) as r:
        events = read_sse(r)
    kinds = [e for e, _ in events]
    assert kinds[0] == "ack" and kinds[-1] == "done" and "final" in kinds and "action" in kinds
    final = next(d for e, d in events if e == "final")
    assert final["decision"] == "REFUND" and final["amount"] == 10.0
    assert main.store.get_line(msisdn)["balance"] == round(before + 10, 2)
    assert "R-BILL-02" in final["rule_ids"]


def test_refund_is_idempotent(client):
    from app.agent import domain
    from app.config import settings
    msisdn = CASES["S03"]["msisdn"]
    res = domain.evaluate(main.store, msisdn, "VAS_NO_CONSENT", settings.now())
    assert res["decision"] == "REFUND" and res["amount"] == 1.80
    assert domain.apply_resolution(main.store, msisdn, res["resolution_id"], settings.now(), "CS-T")["applied"]
    assert not domain.apply_resolution(main.store, msisdn, res["resolution_id"], settings.now(), "CS-T")["applied"]
    again = domain.evaluate(main.store, msisdn, "VAS_NO_CONSENT", settings.now())
    assert again["decision"] == "NOT_CONFIRMED"
    assert "V_FAL" not in main.store.get_line(msisdn)["active_vas"]


def test_limit_routes_to_specialist(client):
    from app.agent import domain
    from app.config import settings
    res = domain.evaluate(main.store, CASES["S10"]["msisdn"], "DOUBLE_CHARGE", settings.now())
    assert res["decision"] == "SPECIALIST" and res["team"] == "BILLING" and "R-ADJ-01" in res["rule_ids"]


def test_goodwill(client):
    from app.agent import domain
    from app.config import settings
    assert domain.evaluate(main.store, CASES["U02"]["msisdn"], "GOODWILL_REQUEST", settings.now())["amount"] == 1.40
    assert domain.evaluate(main.store, CASES["U01"]["msisdn"], "GOODWILL_REQUEST", settings.now())["decision"] == "EXPLAIN"


def test_confirmation_and_level2_required(client):
    from app.agent import domain
    from app.config import settings
    m = CASES["T04"]["msisdn"]
    assert not domain.perform_action(main.store, m, "reveal_puk", {}, True, 1, settings.now())["ok"]
    assert not domain.perform_action(main.store, CASES["T08"]["msisdn"], "set_roaming", {"enabled": True}, False, 1,
                                     settings.now())["ok"]
    assert domain.perform_action(main.store, CASES["T08"]["msisdn"], "set_roaming", {"enabled": True}, True, 1,
                                 settings.now())["ok"]


def test_openai_compat_stream(client):
    main.agent.llm = scripted_llm([("Salam! Rouminq kəsintinizə baxıram.", [])])
    body = {"messages": [{"role": "system", "content": f'msisdn {CASES["S04"]["msisdn"]}'},
                         {"role": "user", "content": "Rouminqi söndürmüşdüm, pul kəsilib"}], "stream": True}
    with client.stream("POST", "/v1/chat/completions", json=body) as r:
        lines = [l for l in r.iter_lines() if l.startswith("data:")]
    assert lines[-1] == "data: [DONE]"
    text = "".join(json.loads(l[5:])["choices"][0]["delta"].get("content", "") for l in lines[:-1])
    assert "Rouminq" in text


def test_voice_filter():
    assert az_words(350) == "üç yüz əlli"
    assert normalize_for_voice("3.50 AZN kəsilib, saat 14:02-də", "az") == "üç manat əlli qəpik kəsilib, saat on dörd sıfır iki-də"
    f = StreamFilter("web")
    assert f.feed("Salam [cal") == "Salam " and f.feed("m] dostum.") + f.flush() == " dostum."
    v = StreamFilter("voice")
    assert v.feed("[laughs] [calm] Yoxladım. Qa") == " [calm] Yoxladım. "


def test_session_survives_restart(client):
    """A redeploy wipes in-memory sessions; the next request must restore it from the store, not 404."""
    msisdn = CASES["S01"]["msisdn"]
    sid = client.post("/v1/sessions", json={"msisdn": msisdn}).json()["session_id"]
    main.agent.store.append_session_turn(sid, 1, {"role": "user", "text": "salam"})
    main.agent.store.append_session_turn(sid, 2, {"role": "assistant", "text": "Salam!"})
    main.agent.sessions.sessions.clear()  # simulate restart
    r = client.get(f"/v1/sessions/{sid}")
    assert r.status_code == 200 and r.json()["session_id"] == sid
    s = main.agent.sessions.get(sid)
    assert s.msisdn == msisdn and s.turns == 1 and [m["role"] for m in s.history] == ["user", "assistant"]
    assert client.get("/v1/sessions/ss_doesnotexist").status_code == 404


def test_usage_endpoints(client):
    r = client.get("/v1/lines/%2B994981000137/usage?months=2")
    assert r.status_code == 200
    body = r.json()
    assert body["msisdn"] == "+994981000137" and len(body["months"]) == 2
    assert body["months"][0]["month"] > body["months"][1]["month"]
    m = body["months"][0]["month"]
    assert client.get(f"/v1/lines/%2B994981000137/usage/{m}").json()["month"] == m
    assert client.get("/v1/lines/%2B994000000000/usage").status_code == 404
    assert client.get("/v1/lines/%2B994981000137/usage/1999-01").status_code == 404
    s = client.get("/v1/usage/summary?months=1").json()
    assert s["months"][0]["msisdn"] == "#ALL" and s["months"][0]["lines"] == 10
