# Sama Mobile — usage dashboard

Dashboard uses the provided usage contract. The previous support operations metrics were replaced by cost/usage panels, keeping the dark rounded-card layout and purple brand accents.

## API

- Line: GET /v1/lines/{encodeURIComponent(msisdn)}/usage?months=6
- Aggregate: GET /v1/usage/summary?months=6

The browser calls /api/v1/... on Netlify. The Edge Function injects SEMA_API_KEY on the server. Existing Netlify environment variables remain unchanged. Public reads allow only the ten documented synthetic demo lines, and months=1..6. To support authenticated real subscribers later, backend authentication/ownership rules must replace the demo allowlist.

The latest month is selected from months[0]. Graphs sort months oldest to newest. Customer and month selection reset stale data during fetches. API error/empty/loading states do not substitute invented statistics. Requests can be retried. CSV exports the loaded period.

## Line screen

Identity and masked number; selected-month spending, forecast, refunds and net spending; positive/negative change badge; elapsed days; itemised nonzero costs; six-month actual/forecast/refund chart; data/minute/SMS meters; categories and peak-day chart; savings insights; packages, VAS and roaming details. Empty credits, insights, roaming and extras are hidden. Percentage is not capped in text, but visual progress is capped at 100%; 90% orange, 100% red. No data package is shown for null limits. Insights are rendered exactly as supplied, regardless of UI language.

Recommendations open support with the selected msisdn and insight prefilled, without automatically performing an account action. Template prompt auto-send remains unchanged.

## Aggregate screen

Subscriber count, average bill, refunded amount/count and savings opportunity; total spending; stacked six-month cost chart; data categories; tariff distribution; average-bill/refund trend using separately labelled scales; roaming trips and average usage.

## Mock files

The brief mentions backend-generated mock files but these were not attached. Add them to public/mock/usage/ and set VITE_USE_MOCK=1 for a build. Expected filenames: number without +, plus summary.json. Missing mock files show an error instead of falling back to synthetic numbers. Default mode reads the real API.

Synthetic QA-only fixtures under tests/fixtures were created to verify the layout and contract. They are not production API data. Screenshots marked “Mock məlumatlar” use these test fixtures.

## Current backend status

On 9 October 2026, the updated Railway deployment responded HTTP 200 for all ten demo line usage endpoints and the aggregate summary. Each returns six months and passes the frontend schema validation. These calls were also verified through the same server-side proxy with the original user-provided API key. Browser checks displayed actual backend data, month selection, credits and summary statistics. The earlier HTTP 404 limitation has been resolved.

## Validation

Build and tests verify the contract, chart ordering, masks, null limits, thresholds and server-side usage proxy. Browser checks cover customer/month changes, refunds, PAYG, hidden empty blocks, AZ/RU language switching, mobile overflow and recommendation → support handoff. No account-changing API operation was used for these checks.
