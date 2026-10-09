# Frontend üçün prompt — Məryəm API inteqrasiyası

> Aşağıdakı xətdən sonrakı hissəni frontend-i yazan AI-yə (və ya developerə) olduğu kimi verin.
> `BASE_URL` və `API_KEY` deploy-dan sonra doldurulur.

---

Build the frontend integration for **Məryəm**, a customer-support agent of the mobile operator "Səma Mobile". The backend is ready; integrate exactly with this contract.

## Config
```
BASE_URL = https://sema-care-production.up.railway.app
API_KEY  = <API_KEY — Railway-dəki API_KEYS dəyəri; repoya yazmayın>
```
**How to use the API key:** send it on every request as the header `X-API-Key: <API_KEY>` (or `Authorization: Bearer <API_KEY>`). For the WebSocket, pass it as a query parameter: `wss://sema-care-production.up.railway.app/v1/sessions/<id>/ws?api_key=<API_KEY>`. Requests without it get `401 {"code":"unauthorized"}`.

**Voice (optional, ElevenLabs widget):** agent ID `agent_6601m4g16s0afv8tk7c8x204x23b` — embed with
`<elevenlabs-convai agent-id="agent_6601m4g16s0afv8tk7c8x204x23b"></elevenlabs-convai><script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async></script>`.
The widget talks to ElevenLabs, which calls our backend itself; the frontend needs no other keys.

**Demo customer:** `+994981000548` (S04 — roaming deduction while roaming was off). Full list: `GET /v1/demo/cases`.
All requests/responses are JSON (UTF-8). Every response has an `X-Request-Id` header. Errors: `{"code": "...", "message": "..."}` with HTTP 400/401/404/409/500.

## Flow (send input → listen to the answer)
1. **Create a session** when the chat opens:
   `POST {BASE_URL}/v1/sessions`  body `{"msisdn": "+994981000548", "channel": "web"}`
   → `201 {"session_id", "case_id", "persona": {"name": "Məryəm"}, "greeting", "language"}`
   Show `greeting` as Məryəm's first message. (Demo phone numbers: `GET /v1/demo/cases` returns test scenarios with `msisdn`, `title` and sample `turns` — use it for a "pick a demo customer" dropdown.)
2. **Send a message and stream the answer in one request** (recommended for the browser):
   `POST {BASE_URL}/v1/sessions/{session_id}/messages:stream`  body `{"text": "..."}`
   Response is `text/event-stream`. Read it with `fetch` + `response.body.getReader()` (EventSource cannot send the API-key header). Parse SSE blocks (`event:` / `data:` lines, separated by a blank line).
3. **Alternative (WebSocket, bidirectional):** `wss://sema-care-production.up.railway.app/v1/sessions/{session_id}/ws?api_key=API_KEY`
   send `{"type":"message","text":"..."}` or `{"type":"interrupt","heard_text":"..."}`; receive `{"id","event","data"}` objects with the same events.
4. **Alternative (two calls):** `POST /v1/sessions/{id}/messages` → `202 {"message_id"}`, and keep `GET /v1/sessions/{id}/events` (SSE, supports `Last-Event-ID`) open.

## Events (same on SSE and WebSocket), in order
| event | data | UI |
|---|---|---|
| `ack` | `{message_id}` | show typing indicator |
| `status` | `{stage, label}` e.g. "Hesab araşdırılır…" | small grey status line under the typing indicator (replace on each new status) |
| `delta` | `{message_id, text}` | append `text` to Məryəm's current bubble (streaming) |
| `action` | `{name, ok, result}` e.g. `result.credited_azn`, `result.new_balance_azn` | green chip "✓ 10.00 AZN balansa qaytarıldı" / "✓ Rouminq aktivləşdirildi" |
| `handoff` | `{team, team_name, ticket_no, sla, priority}` | info card "Mütəxəssisə ötürüldü · SM-2026-12345 · 2 saat" |
| `final` | `{decision, root_cause, amount, case_id, citations[], rule_ids[], latency_ms, text}` | enable a "Niyə?" (Why?) button that reveals rule_ids + citations + latency |
| `error` | `{code, message, retryable}` | inline error with "Retry" |
| `done` | `{message_id, interrupted?}` | stop typing indicator, re-enable input |

`decision` ∈ `REFUND | GOODWILL | FIX | EXPLAIN | SPECIALIST | INFO | REFUSE | CLARIFY`.

## Other endpoints
- `GET /v1/sessions/{id}` → transcript + case
- `GET /v1/cases?status=&msisdn=` and `GET /v1/cases/{case_id}` → operator panel (list + detail with transcript, rule_ids, citations)
- `GET /v1/customers/{msisdn}/snapshot` → account summary (balance, tariff, packages, last deductions) for a side panel
- `POST /v1/sessions/{id}/interrupt` `{"heard_text": ""}` → stop the current answer (e.g., user starts typing a new message)
- `POST /v1/admin/reset-demo` → reset demo data (operator panel "Reset" button)
- `GET /health`

## Minimal streaming client (TypeScript)
```ts
async function sendAndListen(sessionId: string, text: string, on: (ev: string, data: any) => void) {
  const res = await fetch(`${BASE_URL}/v1/sessions/${sessionId}/messages:stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify({ text }),
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      let ev = "message", data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) ev = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) on(ev, JSON.parse(data));
    }
  }
}
```

## UX requirements
- Məryəm's bubble streams token by token; never show raw tags like `[calm]` (the web channel already strips them).
- Show `status` labels while tools run (feels like an agent investigating).
- After `final`, show a collapsible **"Niyə?"** panel: rule IDs (e.g. R-BILL-02), cited knowledge sections, latency.
- Do not send a new message while streaming; or call `/interrupt` first.
- Language: UI strings in Azerbaijani; Məryəm answers in the customer's language (AZ or RU).
- The API key is a demo key; do not log it to the console.
