# Backend integration — Səma Mobile v1.0

## Source of truth

The user-supplied backend technical brief dated 9 October 2026. The old provisional `/tickets`, `/dashboard`, `/conversations` routes were removed. No backend keys are embedded in browser assets.

## Model mapping

| Backend | UI |
| --- | --- |
| case_id / session_id | detail reference / chat session |
| status OPEN / ESCALATED / RESOLVED | open / open specialist / closed |
| channel web / voice / api | text / call / text |
| summary / root_cause / intent | title / subtitle / fallback title |
| amount / decision | AZN amount / REFUND, FIX, EXPLAIN, GOODWILL, SPECIALIST, NOT_CONFIRMED, INFO, REFUSE |
| team / priority P1–P3 / SLA / ticket_no | specialist team / urgent-high-normal / deadline / ticket |
| rule_ids / evidence / citations | exact IDs and references, without invented clause text or account facts |
| created_at / closed_at | case volume / resolved-today |
| latency_ms.first_token | first-token median, when supplied; unavailable values show a dash |

Dashboard reads at most 250 cases. Aggregates describe only that loaded set, not system-wide metrics. OPEN cases enter the unassigned bucket; ESCALATED cases enter the specialist bucket. Actual live AI-handling/waiting states are not exposed by the brief. Demo queue breakdowns are illustrative; production queue telemetry needs additional backend fields. The resolution bubbles classify resolved cases without a team, resolved cases with a team, and escalated cases. This cannot establish whether a human actually resolved a case without a backend resolution-path field.

## SSE

`src/lib/sse.ts`: UTF-8 chunk-safe frame parser, CRLF/LF handling, comments/heartbeat, multiline data, sequence ID.

`src/lib/api.ts`: creates a session, sends a unique client_msg_id via messages:stream, forwards progress callbacks, accumulates deltas, prefers final.text if provided, waits for done. On disconnection after a known event ID, reconnects using GET events and Last-Event-ID, up to two reconnections. No POST replay. A failed stream leaves the draft available; check case/session state before retrying a financial request manually. The sample final event omits text, so accumulated deltas are retained.

## API response gaps to confirm with backend team

- `/v1/cases` wrapper: this adapter accepts an array or `{cases: [...]}`. Pagination/cursor is not specified.
- Case-detail transcript envelope is not defined in the brief. Adapter accepts `transcript: [{role,text}]`. Tool-call details require the actual returned schema.
- Session meta/transcript response shape is not defined. Loaded case transcripts are shown when included; complete historic session navigation requires confirming that envelope.
- Assignment and close/reopen mutation endpoints are absent: controls are disabled in API mode.
- System metrics/queue status/assignee identity/confidence are absent: no fabricated API values are shown.
- ElevenLabs agent ID, signed conversation URL flow and widget/SDK transport were not supplied: real voice remains unconnected. `/v1/chat/completions` is a server-to-server ElevenLabs endpoint, not a browser recording endpoint.
- Session verified_level must ultimately come from real authenticated customer context. The bundled proxy restricts the hackathon to one configured synthetic line at level 1. Do not use this gate with real subscriber data.

## Netlify variables

See `.env.example`. VITE values are build-time; trigger a new deploy after changing DATA_MODE. Backend URL and key are runtime Edge variables; no key is stored in localStorage or browser source. Private demo access code is stored only in sessionStorage. The API key used by ElevenLabs remains in its own server-side configuration.

## Verification

Build/typecheck, SSE parser tests, gateway authorization/route/identity/key-isolation and streamed cursor forwarding tests. Real backend latency, policy accuracy, 63-case oracle/evals and live voice require the actual deployed services and supplied eval data.
