"""Agent loop: OpenRouter (Claude) tool use with streaming, one brain for web + voice."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid

from app import catalog as C
from app.agent import domain
from app.agent.session import Session, SessionManager
from app.agent.tools import STATUS_LABELS, TOOLS, ToolExecutor
from app.agent.voice import FILLERS, StreamFilter
from app.config import settings
from app.llm import LLMError, stream_chat

log = logging.getLogger("sema.agent")
MAX_ITERS = 8


def load_prompt() -> str:
    text = settings.prompt_file.read_text(encoding="utf-8")
    m = re.search(r"```\n(.*?)```", text, flags=re.S)
    return (m.group(1) if m else text).strip()


def detect_language(text: str, default: str) -> str:
    cyr = len(re.findall(r"[а-яА-ЯёЁ]", text))
    lat = len(re.findall(r"[a-zA-Zəğıöüşç]", text))
    if cyr > lat:
        return "ru"
    if lat > cyr:
        return "az"
    return default


def greeting(name: str | None, lang: str) -> str:
    first = (name or "").split()[0] if name else ""
    if lang == "ru":
        return f"Здравствуйте{', ' + first if first else ''}! Я Марьям из Səma Mobile. Чем могу помочь?"
    return f"Salam{', ' + first if first else ''}! Mən Məryəm, Səma Mobile. Sizə necə kömək edə bilərəm?"


class Agent:
    def __init__(self, store, kb, llm=stream_chat):
        self.store, self.kb, self.llm = store, kb, llm
        self.sessions = SessionManager()
        self.prompt = load_prompt()

    # ---------------------------------------------------------------- sessions
    def start_session(self, msisdn: str, channel: str = "web", verified_level: int = 1,
                      language: str | None = None) -> Session:
        line = self.store.get_line(msisdn)
        if not line:
            raise KeyError(msisdn)
        cust = self.store.get_customer(line["customer_id"]) or {}
        lang = language or cust.get("language") or "az"
        case_id = "CS-" + uuid.uuid4().hex[:6].upper()
        s = self.sessions.create(msisdn=msisdn, channel=channel, language=lang, verified_level=verified_level,
                                 case_id=case_id, snapshot=domain.build_snapshot(self.store, msisdn, settings.now()))
        self.store.put_session_meta({"session_id": s.session_id, "msisdn": msisdn, "channel": channel,
                                     "language": lang, "verified_level": verified_level, "case_id": case_id,
                                     "created_at": settings.now().isoformat()})
        self.store.put_case({"case_id": case_id, "session_id": s.session_id, "msisdn": msisdn, "channel": channel,
                             "status": "OPEN", "created_at": settings.now().isoformat()})
        s.greeting = greeting(cust.get("full_name"), lang)
        return s

    def restore_session(self, session_id: str) -> Session | None:
        """Rebuild a session the in-memory manager lost (container restart/redeploy) from the stored
        meta + transcript, so clients holding an old session_id keep working instead of getting 404."""
        rec = self.store.get_session(session_id)
        meta = (rec or {}).get("meta") or {}
        if not meta.get("msisdn") or not self.store.get_line(meta["msisdn"]):
            return None
        if (s := self.sessions.get(session_id)) is not None:  # restored concurrently
            return s
        turns = sorted((rec.get("turns") or []), key=lambda x: int(x["seq"]))
        s = self.sessions.create(session_id=session_id, msisdn=meta["msisdn"], channel=meta.get("channel", "web"),
                                 language=meta.get("language", "az"), verified_level=int(meta.get("verified_level", 1)),
                                 case_id=meta.get("case_id") or "CS-" + uuid.uuid4().hex[:6].upper(),
                                 snapshot=domain.build_snapshot(self.store, meta["msisdn"], settings.now()))
        s.history = [{"role": t["role"], "content": t["text"]} for t in turns
                     if t.get("role") in ("user", "assistant") and t.get("text")]
        s.turns = (int(turns[-1]["seq"]) + 1) // 2 if turns else 0
        s.last_generated_text = next((t["text"] for t in reversed(turns) if t.get("role") == "assistant"), "")
        log.info("restored session %s from store (%d turns)", session_id, s.turns)
        return s

    def _system(self, s: Session) -> list[dict]:
        return [{"role": "system", "content": [
            {"type": "text", "text": self.prompt.replace("{{channel}}", s.channel), "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": "Hesab xülasəsi (snapshot, sessiya başlayanda):\n"
                                     + json.dumps(s.snapshot, ensure_ascii=False)},
        ]}]

    @staticmethod
    def _with_history_cache(history: list[dict]) -> list[dict]:
        """Moving cache breakpoint on the newest user/tool message (system prompt holds the other one),
        so each tool-loop iteration re-reads the conversation prefix from cache instead of re-processing it."""
        for i in range(len(history) - 1, -1, -1):
            m = history[i]
            if m.get("role") in ("user", "tool") and isinstance(m.get("content"), str) and m["content"]:
                cached = {**m, "content": [{"type": "text", "text": m["content"], "cache_control": {"type": "ephemeral"}}]}
                return history[:i] + [cached] + history[i + 1:]
        return history

    # ---------------------------------------------------------------- one turn
    async def run_turn(self, s: Session, text: str, message_id: str) -> dict | None:
        async with s.lock:
            try:
                return await self._turn(s, text, message_id)
            except asyncio.CancelledError:
                # barge-in: keep history valid (every tool_call needs a tool result) and close the stream
                last = s.history[-1] if s.history else None
                if last and last.get("role") == "assistant" and last.get("tool_calls"):
                    for c in last["tool_calls"]:
                        s.history.append({"role": "tool", "tool_call_id": c["id"], "content": '{"error":"interrupted"}'})
                elif last and last.get("role") == "user":
                    s.history.append({"role": "assistant", "content": "(cavab müştəri tərəfindən kəsildi)"})
                s.publish("done", {"message_id": message_id, "interrupted": True})
                raise

    async def _turn(self, s: Session, text: str, message_id: str) -> dict:
        t0 = time.perf_counter()
        s.turns += 1
        s.language = detect_language(text, s.language)
        s.citations, s.rule_ids, s.applied, s.actions, s.handoff, s.outcome = set(), set(), [], [], None, None
        s.publish("ack", {"message_id": message_id})
        user_content = text
        if s.interrupt_note:
            user_content = f"[Sistem qeydi: {s.interrupt_note}]\n{text}"
            s.interrupt_note = None
        s.history.append({"role": "user", "content": user_content})
        await asyncio.to_thread(self.store.append_session_turn, s.session_id, s.turns * 2 - 1,
                                {"role": "user", "text": text, "ts": settings.now().isoformat()})

        model, effort = settings.model_for(s.channel)
        flt = StreamFilter(s.channel, s.language)
        executor = ToolExecutor(s, self.store, self.kb)
        spoken, first_token_ms, tool_ms, usage_all = [], None, 0.0, []

        sep = {"pending": False}

        def emit(chunk: str):
            nonlocal first_token_ms
            if chunk:
                if sep["pending"] and spoken and not chunk[:1].isspace():
                    chunk = (" " if s.channel == "voice" else "\n\n") + chunk
                sep["pending"] = False
                if first_token_ms is None:
                    first_token_ms = int((time.perf_counter() - t0) * 1000)
                spoken.append(chunk)
                s.publish("delta", {"message_id": message_id, "text": chunk})

        error = None
        try:
            reply_since_tools, used_tools, nudged = False, False, False
            for _ in range(MAX_ITERS):
                final = None
                spoken_before = len(spoken)
                sep["pending"] = bool(spoken)
                async for kind, payload in self.llm(model, effort, self._system(s) + self._with_history_cache(s.history), TOOLS):
                    if kind == "text":
                        emit(flt.feed(payload))
                    elif kind == "tool_calls_started" and s.channel == "voice" and not spoken:
                        emit(FILLERS.get(s.language, FILLERS["az"]))
                    elif kind == "done":
                        final = payload
                emit(flt.feed("\n") if s.channel == "voice" else "")
                emit(flt.flush())
                if final.get("usage"):
                    usage_all.append(final["usage"])
                if len(spoken) > spoken_before and (final["content"] or "").strip():
                    reply_since_tools = True
                calls = final["tool_calls"]
                msg = {"role": "assistant", "content": final["content"] or None}
                if calls:
                    msg["tool_calls"] = [{"id": c["id"] or f"call_{uuid.uuid4().hex[:8]}", "type": "function",
                                          "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
                                         for c in calls]
                if final.get("reasoning_details"):
                    msg["reasoning_details"] = final["reasoning_details"]
                s.history.append(msg)
                if not calls:
                    if used_tools and not reply_since_tools and not nudged:
                        # the model acted but never told the customer — ask once for the visible reply
                        nudged = True
                        s.history.append({"role": "user", "content": "[Sistem qeydi: alət nəticələrinə əsasən müştəriyə "
                                          "yekun cavabı indi görünən mətn kimi yaz. Yeni alət çağırma.]"})
                        continue
                    break
                used_tools = True
                if final.get("finish_reason") == "length":
                    error = "max_tokens with pending tool call"
                    break
                for c in msg["tool_calls"]:
                    s.publish("status", {"stage": c["function"]["name"], "label": STATUS_LABELS.get(c["function"]["name"], "…")})
                t1 = time.perf_counter()
                results = await asyncio.gather(*[asyncio.to_thread(executor.run, c["function"]["name"], c["function"]["arguments"])
                                                 for c in msg["tool_calls"]])
                tool_ms += (time.perf_counter() - t1) * 1000
                for c, r in zip(msg["tool_calls"], results):
                    name = c["function"]["name"]
                    s.history.append({"role": "tool", "tool_call_id": c["id"],
                                      "content": json.dumps(r, ensure_ascii=False, default=str)[:8000]})
                    if name in ("apply_resolution", "perform_service_action"):
                        s.publish("action", {"name": name, "ok": bool(r.get("applied") or r.get("ok")), "result": r})
                    if name == "create_handoff" and r.get("ok"):
                        s.publish("handoff", {k: r[k] for k in ("team", "team_name", "ticket_no", "sla", "priority")})
                if all(c["function"]["name"] == "record_outcome" for c in msg["tool_calls"]) and reply_since_tools:
                    break
                reply_since_tools = False
        except LLMError as e:
            error = str(e)
            log.error("llm error: %s", e)
        except Exception as e:  # noqa: BLE001 — never leave a listener hanging
            error = f"internal: {e}"
            log.exception("turn failed")

        text_out = "".join(spoken).strip()
        if error and not text_out:
            text_out = ("Bağışlayın, qısa texniki gecikmə yarandı. Bir az sonra yenidən yazın."
                        if s.language != "ru" else "Извините, возникла короткая техническая задержка. Попробуйте ещё раз.")
            emit(text_out)
        s.last_generated_text = text_out
        result = self._finish(s, message_id, text_out, t0, first_token_ms, tool_ms, usage_all, model)
        if error:
            s.publish("error", {"code": "llm_error" if "OpenRouter" in error or "OPENROUTER" in error else "internal",
                                "message": error[:300], "retryable": True})
        s.publish("done", {"message_id": message_id})
        # persist after the client already has "done"; still inside the session lock so turns stay ordered.
        # A barge-in arriving now must not mark this already-finished answer as interrupted.
        try:
            await asyncio.shield(asyncio.to_thread(self._persist, s, result))
        except asyncio.CancelledError:
            pass
        return result

    def _finish(self, s: Session, message_id, text, t0, first_token_ms, tool_ms, usage_all, model) -> dict:
        credited = round(sum(a.get("credited_azn", 0) for a in s.applied), 2) or None
        if s.outcome:
            decision, root = s.outcome["decision"], s.outcome["root_cause"]
        elif s.handoff:
            decision, root = "SPECIALIST", None
        elif any(a["decision"] in ("REFUND", "GOODWILL") for a in s.applied):
            decision, root = s.applied[0]["decision"], None
        elif s.applied or s.actions:
            decision, root = "FIX", None
        else:
            decision, root = "INFO", None
        tokens = {"in": sum((u.get("prompt_tokens") or 0) for u in usage_all),
                  "cached": sum(((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0) for u in usage_all),
                  "out": sum((u.get("completion_tokens") or 0) for u in usage_all),
                  "cost_usd": round(sum((u.get("cost") or 0) for u in usage_all), 5)}
        total_ms = int((time.perf_counter() - t0) * 1000)
        final = {"message_id": message_id, "text": text, "voice_text": text if s.channel == "voice" else None,
                 "decision": decision, "root_cause": root, "amount": credited, "case_id": s.case_id,
                 "handoff": s.handoff, "actions": s.actions, "citations": sorted(s.citations), "rule_ids": sorted(s.rule_ids),
                 "latency_ms": {"first_token": first_token_ms, "tools": int(tool_ms), "total": total_ms},
                 "model": model, "tokens": tokens}
        s.publish("final", final)
        return final

    def _persist(self, s: Session, final: dict) -> None:
        """Blocking store writes for one finished turn (runs in a worker thread)."""
        decision, root, credited, text = final["decision"], final["root_cause"], final["amount"], final["text"]
        model, tokens = final["model"], final["tokens"]
        case = self.store.get_case(s.case_id) or {"case_id": s.case_id, "msisdn": s.msisdn, "channel": s.channel,
                                                  "created_at": settings.now().isoformat()}
        case.update({"session_id": s.session_id, "decision": decision, "root_cause": root,
                     "amount": round((case.get("amount") or 0) + (credited or 0), 2) or None,
                     "team": (s.handoff or {}).get("team") or case.get("team"),
                     "ticket_no": (s.handoff or {}).get("ticket_no") or case.get("ticket_no"),
                     "rule_ids": sorted(set(case.get("rule_ids", [])) | s.rule_ids),
                     "citations": sorted(set(case.get("citations", [])) | s.citations),
                     "summary": (s.outcome or {}).get("summary") or case.get("summary"),
                     "status": "ESCALATED" if s.handoff else ("RESOLVED" if decision in ("REFUND", "GOODWILL", "FIX", "EXPLAIN", "INFO", "REFUSE") else "OPEN"),
                     "updated_at": settings.now().isoformat()})
        self.store.put_case(case)
        self.store.append_session_turn(s.session_id, s.turns * 2, {"role": "assistant", "text": text, "decision": decision,
                                                                 "latency_ms": final["latency_ms"], "model": model,
                                                                 "tools": s.actions, "tokens": tokens})

    # ---------------------------------------------------------------- interruption
    def note_interruption(self, s: Session, heard_text: str) -> None:
        full = s.last_generated_text.strip()
        heard = (heard_text or "").strip()
        if not full or not heard or len(heard) >= len(full) - 3:
            return
        rest = full[len(heard):].strip() if full.startswith(heard) else full
        s.interrupt_note = (f"Müştəri sözünü kəsdi. Eşitdiyi: «{heard[-200:]}». Eşitmədiyi: «{rest[:300]}». "
                            "Əvvəlcə yeni sözünə cavab ver, eşitmədiyi hissə hələ vacibdirsə qısa davam et, təkrarlama.")


def team_names() -> dict:
    return {k: v["az"] for k, v in C.TEAMS.items()}
