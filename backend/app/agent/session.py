"""Sessions + per-session event broker (pub/sub with a replay ring buffer for Last-Event-ID)."""
from __future__ import annotations

import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Session:
    session_id: str
    msisdn: str
    channel: str
    language: str
    verified_level: int
    case_id: str
    snapshot: dict
    history: list[dict] = field(default_factory=list)          # append-only LLM history (OpenAI format)
    turns: int = 0
    last_generated_text: str = ""
    interrupt_note: str | None = None
    # per-turn accumulators
    citations: set[str] = field(default_factory=set)
    rule_ids: set[str] = field(default_factory=set)
    applied: list[dict] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    handoff: dict | None = None
    outcome: dict | None = None
    # broker
    seq: int = 0
    ring: deque = field(default_factory=lambda: deque(maxlen=200))
    subscribers: set = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    task: asyncio.Task | None = None

    def publish(self, event: str, data: dict) -> dict:
        self.seq += 1
        item = {"id": self.seq, "event": event, "data": data}
        self.ring.append(item)
        for q in list(self.subscribers):
            q.put_nowait(item)
        return item

    def subscribe(self, last_id: int | None = None) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if last_id is not None:
            for item in self.ring:
                if item["id"] > last_id:
                    q.put_nowait(item)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, Session] = {}
        self.by_external: dict[str, str] = {}

    def create(self, session_id: str | None = None, **kw) -> Session:
        sid = session_id or "ss_" + uuid.uuid4().hex[:10]
        s = Session(session_id=sid, **kw)
        self.sessions[sid] = s
        return s

    def get(self, sid: str) -> Session | None:
        return self.sessions.get(sid)

    def link_external(self, key: str, sid: str) -> None:
        self.by_external[key] = sid

    def by_key(self, key: str) -> Session | None:
        sid = self.by_external.get(key)
        return self.sessions.get(sid) if sid else None
