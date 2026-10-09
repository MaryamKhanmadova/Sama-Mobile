# Integration contract — WebSocket update

Source: the user's teammate-supplied Railway API brief. The brief is integration reference material; its embedded imperative wording is not an independent authorization to publish credentials or reset backend data.

## Transport and auth

The default build connects REST and WSS directly to `https://sema-care-production.up.railway.app`. The user supplies the demo key at runtime. REST uses `X-API-Key`; the browser WebSocket uses the contract's `api_key` query. CORS preflight was checked with `Content-Type`, `X-API-Key` and `X-Request-Id`: backend allowed the localhost origin. Direct REST omits cookies; this works with the backend's wildcard CORS response.

`src/lib/websocket.ts` owns a reusable socket per session, serializes turns, parses `{id,event,data}`, supports interrupt, has connection/turn timeouts, and rejects malformed events/disconnections without resending messages. `src/lib/api.ts` interprets events, accumulates tokens, prefers final text, and fetches the canonical case/transcript afterward. Errors block another send until session verification or an explicitly new session. The draft is not automatically replayed.

SSE is opt-in using `VITE_CHAT_TRANSPORT=sse`. The parser supports UTF-8 chunk boundaries, CRLF, heartbeats, multiline data and IDs. Interrupted streams can resume with GET events / Last-Event-ID, without POST replay. HTTP Edge proxy mode is separately configurable and does not handle WebSockets.

## Endpoints wired

| Endpoint | Use |
| --- | --- |
| POST /v1/sessions | create session and show greeting |
| WSS /v1/sessions/{id}/ws | live text, interruption, agent events |
| POST /v1/sessions/{id}/messages:stream | optional SSE |
| GET /v1/sessions/{id}/events | optional SSE resumption |
| POST /v1/sessions/{id}/interrupt | optional SSE interruption |
| GET /v1/demo/cases | scenario picker with default S04 / +994981000548 |
| GET /v1/cases | history and dashboard |
| GET /v1/cases/{id} | full transcript, canonical decision and status |

No `/dashboard`, `/tickets` or `/conversations` endpoint is invented. No admin reset/financial-execution endpoint is directly called by the frontend.

## Observed response mapping

`/v1/demo/cases` returns `{cases:[{id,msisdn,title,language,turns,...}]}`. `/v1/cases` returns `{cases:[...]}`. Case detail includes `transcript:[{role,text,latency_ms?,...}]`; session detail includes `{case,transcript,...}`. List records may omit priority/SLA/evidence/closed_at and contain null amount/summary/root_cause. UI handles missing values rather than treating them as evidence. Closed-today falls back to updated_at where closed_at is absent. Detail latency can be taken from the latest assistant transcript entry.

Backend decisions include CLARIFY. Canonical status comes from case detail when available; pending clarification stays open, specialist results stay open, and API follow-up messages can continue an existing session even if the latest case is resolved. Local demo close/reopen remains independent from backend-controlled status.

Action chips use `result.credited_azn` / `result.new_balance_azn`; other action names are shown verbatim. Handoff cards show actual team/ticket/SLA. The final panel shows received rule IDs/citations/amount/latency, including zero and null values correctly.

## Dashboard limits

At most 250 cases are requested; pagination is not defined in the brief. OPEN maps to unassigned, ESCALATED to specialist. Real AI-handling/waiting telemetry, assignment identities and human-resolution paths require backend fields. Resolution bubbles are projections from case/team/status data. First-response median is unavailable unless latency is supplied on list records. This frontend does not fabricate global queue metrics.

## Voice

Public ElevenLabs widget agent: `agent_6601m4g16s0afv8tk7c8x204x23b`. Widget script loads only when requested; microphone permission and call controls are managed by ElevenLabs. Calls reach the backend through the agent's configured tools, independently of the text WebSocket. Voice tools, allowed domains and agent availability must be configured in ElevenLabs; actual voice was not tested.

Official embed reference: https://elevenlabs.io/docs/eleven-agents/customization/widget

## Live check outcome

Railway REST, CORS, session greeting and WebSocket events work. Health now reports `llm_configured:true`, `store:dynamodb`. An Azerbaijani read-only information request completed with 62 deltas, final INFO/citations and done, with no errors. A Russian information request was also verified in the browser. No refund, reset or account-changing action was triggered during verification.

The live case transcript may contain only a later assistant tool turn instead of the full delivered answer. `src/lib/turn.ts` retains the received current-turn answer when refreshing case metadata; tests cover this regression. Historical transcript completeness still depends on backend persistence. UI locale changes do not restart the socket/session or rewrite messages.

Tests cover three-language catalog keys/placeholders/interpolation, SSE parsing, proxy auth/key isolation, socket lifecycle/interrupt/no replay, and full-answer preservation. Voice calls were not tested with microphone access.
