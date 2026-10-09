"""FastAPI app: REST input + SSE/WebSocket listening + OpenAI-compatible endpoint for ElevenLabs."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.agent import domain
from app.agent.orchestrator import Agent
from app.config import ROOT, settings
from app.rag.index import KnowledgeBase
from app.store import get_store
from app.usage import SUMMARY_KEY, get_usage_repo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("sema.api")

app = FastAPI(title="Səma Mobile — Məryəm API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["X-Request-Id"])

store = get_store()
kb = KnowledgeBase(settings.kb_dir, {"enabled": settings.embeddings == "openrouter", "model": settings.embed_model,
                                     "api_key": settings.openrouter_key, "base_url": settings.openrouter_url})
agent = Agent(store, kb)


@app.on_event("startup")
async def _warm() -> None:
    await asyncio.to_thread(kb.warm)


@app.middleware("http")
async def request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
    resp = await call_next(request)
    resp.headers["X-Request-Id"] = rid
    return resp


def auth(x_api_key: str | None = Header(default=None), authorization: str | None = Header(default=None)) -> None:
    if not settings.api_keys:
        return
    token = x_api_key or (authorization[7:] if authorization and authorization.lower().startswith("bearer ") else None)
    if token not in settings.api_keys:
        raise HTTPException(401, {"code": "unauthorized", "message": "invalid API key"})


def session_or_404(sid: str):
    s = agent.sessions.get(sid) or agent.restore_session(sid)
    if not s:
        raise HTTPException(404, {"code": "session_not_found", "message": sid})
    return s


# ------------------------------------------------------------------ models
class SessionIn(BaseModel):
    msisdn: str
    channel: str = Field("web", pattern="^(web|voice|api)$")
    verified_level: int = Field(1, ge=1, le=2)
    language: str | None = Field(None, pattern="^(az|ru)$")


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    client_msg_id: str | None = None


class InterruptIn(BaseModel):
    heard_text: str = ""


# ------------------------------------------------------------------ helpers
def start_turn(s, text: str) -> str:
    message_id = "m_" + uuid.uuid4().hex[:8]
    s.task = asyncio.create_task(agent.run_turn(s, text, message_id))
    return message_id


def sse_format(item: dict) -> str:
    return f'id: {item["id"]}\nevent: {item["event"]}\ndata: {json.dumps(item["data"], ensure_ascii=False, default=str)}\n\n'


async def sse_stream(s, last_id: int | None, until_done_of: str | None = None):
    q = s.subscribe(last_id)
    try:
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
                continue
            yield sse_format(item)
            if until_done_of and item["event"] == "done" and item["data"].get("message_id") == until_done_of:
                return
    finally:
        s.unsubscribe(q)


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


# ------------------------------------------------------------------ routes
@app.get("/health")
def health():
    return {"status": "ok", "store": settings.store, "rag_chunks": len(kb.chunks), "rag_dense": bool(kb.vectors),
            "llm_configured": bool(settings.openrouter_key), "chat_model": settings.chat_model,
            "voice_model": settings.voice_model, "now": settings.now().isoformat()}


@app.post("/v1/sessions", status_code=201, dependencies=[Depends(auth)])
def create_session(body: SessionIn):
    try:
        s = agent.start_session(body.msisdn, body.channel, body.verified_level, body.language)
    except KeyError:
        raise HTTPException(404, {"code": "line_not_found", "message": body.msisdn})
    return {"session_id": s.session_id, "case_id": s.case_id, "persona": {"name": "Məryəm"}, "greeting": s.greeting,
            "language": s.language}


@app.post("/v1/sessions/{sid}/messages", status_code=202, dependencies=[Depends(auth)])
def post_message(sid: str, body: MessageIn):
    s = session_or_404(sid)
    if s.task and not s.task.done():
        s.task.cancel()  # new input interrupts the previous answer
    return {"message_id": start_turn(s, body.text)}


@app.get("/v1/sessions/{sid}/events", dependencies=[Depends(auth)])
async def events(sid: str, request: Request, last_event_id: int | None = Query(None)):
    s = session_or_404(sid)
    hdr = request.headers.get("Last-Event-ID")
    last = int(hdr) if hdr and hdr.isdigit() else last_event_id
    return StreamingResponse(sse_stream(s, last), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/v1/sessions/{sid}/messages:stream", dependencies=[Depends(auth)])
async def post_and_stream(sid: str, body: MessageIn):
    s = session_or_404(sid)
    if s.task and not s.task.done():
        raise HTTPException(409, {"code": "session_busy", "message": "previous message still processing"})
    last = s.seq
    message_id = start_turn(s, body.text)
    return StreamingResponse(sse_stream(s, last, until_done_of=message_id), media_type="text/event-stream",
                             headers=SSE_HEADERS)


@app.post("/v1/sessions/{sid}/interrupt", dependencies=[Depends(auth)])
def interrupt(sid: str, body: InterruptIn):
    s = session_or_404(sid)
    if s.task and not s.task.done():
        s.task.cancel()
    agent.note_interruption(s, body.heard_text)
    return {"ok": True}


@app.get("/v1/sessions/{sid}", dependencies=[Depends(auth)])
def get_session(sid: str):
    s = session_or_404(sid)
    return {"session_id": s.session_id, "msisdn": domain.mask(s.msisdn), "channel": s.channel, "language": s.language,
            "verified_level": s.verified_level, "case": store.get_case(s.case_id),
            "transcript": (store.get_session(sid) or {}).get("turns", [])}


@app.websocket("/v1/sessions/{sid}/ws")
async def ws(websocket: WebSocket, sid: str, api_key: str | None = Query(None)):
    if settings.api_keys and api_key not in settings.api_keys:
        await websocket.close(code=4401)
        return
    s = agent.sessions.get(sid) or await asyncio.to_thread(agent.restore_session, sid)
    if not s:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    q = s.subscribe()

    async def pump():
        while True:
            item = await q.get()
            await websocket.send_text(json.dumps(item, ensure_ascii=False, default=str))

    sender = asyncio.create_task(pump())
    try:
        while True:
            msg = json.loads(await websocket.receive_text())
            if msg.get("type") == "message" and msg.get("text"):
                if s.task and not s.task.done():
                    s.task.cancel()
                start_turn(s, msg["text"])
            elif msg.get("type") == "interrupt":
                if s.task and not s.task.done():
                    s.task.cancel()
                agent.note_interruption(s, msg.get("heard_text", ""))
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        sender.cancel()
        s.unsubscribe(q)


@app.get("/v1/cases", dependencies=[Depends(auth)])
def list_cases(status: str | None = None, msisdn: str | None = None, limit: int = 100):
    return {"cases": store.list_cases(status=status, msisdn=msisdn, limit=limit)}


@app.get("/v1/cases/{case_id}", dependencies=[Depends(auth)])
def get_case(case_id: str):
    c = store.get_case(case_id)
    if not c:
        raise HTTPException(404, {"code": "case_not_found", "message": case_id})
    return {**c, "transcript": (store.get_session(c.get("session_id", "")) or {}).get("turns", [])}


@app.get("/v1/customers/{msisdn}/snapshot", dependencies=[Depends(auth)])
def snapshot(msisdn: str):
    if not store.get_line(msisdn):
        raise HTTPException(404, {"code": "line_not_found", "message": msisdn})
    return domain.build_snapshot(store, msisdn, settings.now())


# ------------------------------------------------------------------ usage dashboard (docs/USAGE_TABLE.md §3)
@app.get("/v1/lines/{msisdn}/usage", dependencies=[Depends(auth)])
def line_usage(msisdn: str, months: int = Query(6, ge=1, le=12)):
    items = get_usage_repo().months(msisdn, months)
    if not items:
        raise HTTPException(404, {"code": "line_not_found", "message": msisdn})
    return {"msisdn": msisdn, "currency": "AZN", "months": items}


@app.get("/v1/lines/{msisdn}/usage/{month}", dependencies=[Depends(auth)])
def line_usage_month(msisdn: str, month: str):
    item = get_usage_repo().month(msisdn, month)
    if not item:
        raise HTTPException(404, {"code": "usage_not_found", "message": f"{msisdn} {month}"})
    return item


@app.get("/v1/usage/summary", dependencies=[Depends(auth)])
def usage_summary(months: int = Query(6, ge=1, le=12)):
    return {"currency": "AZN", "months": get_usage_repo().months(SUMMARY_KEY, months)}


@app.get("/v1/demo/cases", dependencies=[Depends(auth)])
def demo_cases():
    """Test scenarios with their phone numbers — for the demo UI / eval."""
    f = ROOT / "eval" / "cases.json"
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"cases": []}
    return {"cases": [{k: c[k] for k in ("id", "category", "title", "msisdn", "language", "turns", "holdout")}
                      for c in data["cases"]]}


@app.post("/v1/admin/reset-demo", dependencies=[Depends(auth)])
def reset_demo():
    if hasattr(store, "reset"):
        store.reset()
    agent.sessions.sessions.clear()
    agent.sessions.by_external.clear()
    return {"ok": True}


# ------------------------------------------------------------------ ElevenLabs Custom LLM (OpenAI-compatible)
MSISDN_RE = re.compile(r"\+?994\d{9}")


@app.post("/v1/chat/completions", dependencies=[Depends(auth)])
async def chat_completions(request: Request):
    body = await request.json()
    msgs = body.get("messages", [])
    extra = body.get("elevenlabs_extra_body") or {}
    users = [m for m in msgs if m.get("role") == "user"]
    if not users:
        raise HTTPException(400, {"code": "invalid_request", "message": "no user message"})
    first_text = json.dumps(msgs[:2], ensure_ascii=False)
    key = extra.get("conversation_id") or body.get("user") or hashlib.sha1(first_text.encode()).hexdigest()[:16]
    s = agent.sessions.by_key(key)
    if not s:
        system_text = " ".join(str(m.get("content")) for m in msgs if m.get("role") == "system")
        found = MSISDN_RE.search(json.dumps(extra) + " " + system_text)
        msisdn = extra.get("msisdn") or (("+" + found.group(0).lstrip("+")) if found else settings.default_voice_msisdn)
        try:
            s = await asyncio.to_thread(agent.start_session, msisdn, "voice", 1, extra.get("language"))
        except KeyError:
            raise HTTPException(404, {"code": "line_not_found", "message": str(msisdn)})
        agent.sessions.link_external(key, s.session_id)
    last_assistant = next((m.get("content") for m in reversed(msgs) if m.get("role") == "assistant"), None)
    if isinstance(last_assistant, str):
        agent.note_interruption(s, last_assistant)
    content = users[-1].get("content")
    text = content if isinstance(content, str) else " ".join(p.get("text", "") for p in content or [])
    if s.task and not s.task.done():
        s.task.cancel()
    last = s.seq
    message_id = start_turn(s, text)
    created = int(time.time())

    async def gen():
        q = s.subscribe(last)
        try:
            while True:
                item = await q.get()
                if item["event"] == "delta" and item["data"]["message_id"] == message_id:
                    chunk = {"id": message_id, "object": "chat.completion.chunk", "created": created, "model": "maryam",
                             "choices": [{"index": 0, "delta": {"content": item["data"]["text"]}, "finish_reason": None}]}
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                if item["event"] == "done" and item["data"]["message_id"] == message_id:
                    end = {"id": message_id, "object": "chat.completion.chunk", "created": created, "model": "maryam",
                           "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                    yield f"data: {json.dumps(end)}\n\ndata: [DONE]\n\n"
                    return
        finally:
            s.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.exception_handler(HTTPException)
async def http_error(_, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=detail)
