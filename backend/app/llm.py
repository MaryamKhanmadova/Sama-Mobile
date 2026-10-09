"""OpenRouter chat-completions client (OpenAI-compatible) with streaming + tool calls.

stream_chat(...) yields:
  ("text", str)                       text delta
  ("tool_calls_started", None)        first tool call began (used to emit a voice filler)
  ("done", {"content", "tool_calls", "finish_reason", "usage", "reasoning_details"})
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

from app.config import settings

log = logging.getLogger("sema.llm")


class LLMError(RuntimeError):
    pass


_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def _get_client() -> httpx.AsyncClient:
    """One keep-alive client per event loop, so tool-loop iterations reuse the TLS connection."""
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not loop or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(settings.llm_timeout_s, connect=10),
                                    limits=httpx.Limits(max_keepalive_connections=20, keepalive_expiry=120))
        _client_loop = loop
    return _client


def _has_message_cache(messages: list[dict]) -> bool:
    return any(m.get("role") != "system" and isinstance(m.get("content"), list) for m in messages)


def _strip_cache_control(messages: list[dict]) -> list[dict]:
    """Fallback if the provider rejects cache_control on a message: plain-string content again."""
    out = []
    for m in messages:
        c = m.get("content")
        if m.get("role") != "system" and isinstance(c, list):
            m = {**m, "content": "".join(p.get("text", "") for p in c)}
        out.append(m)
    return out


async def stream_chat(model: str, effort: str, messages: list[dict], tools: list[dict],
                      max_tokens: int = 1500) -> AsyncIterator[tuple[str, object]]:
    if not settings.openrouter_key:
        raise LLMError("OPENROUTER_API_KEY is not set")
    body = {
        "model": model, "messages": messages, "tools": tools, "tool_choice": "auto", "stream": True,
        "max_tokens": max_tokens, "reasoning": {"effort": effort}, "usage": {"include": True},
        "provider": {"order": [p for p in settings.provider_order.split(",") if p], "allow_fallbacks": True},
    }
    if settings.fallback_model and settings.fallback_model != model:
        body["models"] = [model, settings.fallback_model]
    headers = {"Authorization": f"Bearer {settings.openrouter_key}", "X-Title": settings.app_title}
    if settings.referer:
        headers["HTTP-Referer"] = settings.referer

    content, tool_calls, reasoning, finish, usage = [], {}, [], None, None
    started_tools = False
    client = _get_client()
    for attempt in (1, 2):
        async with client.stream("POST", f"{settings.openrouter_url}/chat/completions", json=body, headers=headers) as r:
            if r.status_code == 400 and attempt == 1 and _has_message_cache(body["messages"]):
                err = (await r.aread())[:500]
                log.warning("OpenRouter 400, retrying without message cache_control: %r", err)
                body["messages"] = _strip_cache_control(body["messages"])
                continue
            if r.status_code >= 400:
                raise LLMError(f"OpenRouter {r.status_code}: {(await r.aread())[:500]!r}")
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if chunk.get("error"):
                    raise LLMError(f"OpenRouter error: {chunk['error']}")
                if chunk.get("usage"):
                    usage = chunk["usage"]
                for ch in chunk.get("choices", []):
                    delta = ch.get("delta") or {}
                    if delta.get("content"):
                        content.append(delta["content"])
                        yield "text", delta["content"]
                    for rd in delta.get("reasoning_details") or []:
                        reasoning.append(rd)
                    for tc in delta.get("tool_calls") or []:
                        slot = tool_calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                        slot["id"] = tc.get("id") or slot["id"]
                        fn = tc.get("function") or {}
                        slot["name"] += fn.get("name") or ""
                        slot["arguments"] += fn.get("arguments") or ""
                        if not started_tools:
                            started_tools = True
                            yield "tool_calls_started", None
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
        break
    yield "done", {"content": "".join(content), "tool_calls": [tool_calls[i] for i in sorted(tool_calls)],
                   "finish_reason": finish, "usage": usage, "reasoning_details": reasoning}
