# Prompt for Claude (pptx skill) — Məryəm pitch deck

> Copy everything below the line into Claude with the **pptx skill** enabled. Attach `docs/PITCH_DOCUMENTATION.md` as the content source.

---

Create a 10-slide pitch deck (`maryam_pitch.pptx`, 16:9) for the NeuroBridge Baku 2026 AI hackathon, Enterprise track. Use the pptx skill. The content source is the attached `PITCH_DOCUMENTATION.md`; use its numbers exactly — do not invent new numbers.

## Audience and hard rules
- First-round judges are **GPT and Claude reading the PDF**, final round is an international human jury. So:
  - Language: **English**. Customer quotes may stay in Azerbaijani with an English translation underneath.
  - **Every number must be real text** (never baked into an image). Each metric shows its N, e.g. "56/63".
  - Slide titles 3–6 must literally contain the scoring criteria names: "Value for the user", "Prototype & use of AI", "Quality testing", "Feasibility", "Originality".
  - **Minimal text**: max 25 words of body text per slide (excluding tables and numbers). One idea per slide. No marketing adjectives ("revolutionary", "seamless").
  - Any number marked ⏳ in the source is preliminary: render it normally but put a small amber pill "PRELIM" (8pt, #F59E0B on 15% amber fill) next to it, and list it in that slide's speaker notes under "REPLACE BEFORE SUBMISSION". Numbers marked ✅ get no pill.
- Every slide gets speaker notes (60–90 words) the presenter can read.

## Design system — purple & white glassmorphism
- **Background (all slides):** full-bleed gradient, deep purple `#1E0B3A` (top-left) → `#4C1D95` (center) → `#7C3AED` (bottom-right). Add 2–3 soft blurred "light orbs": large circles in `#A78BFA` and `#F0ABFC` at 25–35% opacity with heavy soft edges (render orbs as a pre-blurred PNG background generated with Pillow — gaussian blur radius ~120 px — so blur survives in PowerPoint). Vary orb positions slightly per slide so morph transitions feel alive.
- **Glass cards:** rounded rectangles (corner radius ~16 px), fill white at **12% opacity**, 1 px border white at **35% opacity**, soft outer shadow (black 25%, blur 30 px, distance 8 px). A subtle top highlight: thin white line at 50% opacity along the top edge. Content sits inside cards, never directly on the gradient except titles.
- **Typography:** "Manrope" (fallback "Segoe UI"). Titles 34–40 pt bold white; subtitles 18 pt `#E9D5FF`; body 14–16 pt white at 90%; big numbers 54–72 pt bold white with a lavender glow (`#C4B5FD` shadow, blur 12). Left-aligned, generous spacing.
- **Accents:** lavender `#C4B5FD`, orchid `#F0ABFC`. Status only: pass `#34D399`, fail `#FB7185`, prelim `#F59E0B`. No other colors.
- **Icons:** simple white line icons (1.5 px stroke) inside small glass circles.
- **Layout grid:** 0.6 in margins, 12-column grid, max 3 cards per row. Plenty of empty space.
- **Footer:** tiny `#E9D5FF` text "Məryəm · Səma Mobile — NeuroBridge Baku 2026" bottom-left, slide number bottom-right.

## Motion
- **Slide transitions:** Morph between all slides (duration 0.8 s). Keep the background orbs and the title placeholder as same-named shapes on every slide (`!!orb1`, `!!orb2`, `!!title`) so Morph animates them smoothly. Fallback: Fade 0.6 s.
- **Entrance animations (on click → after previous, 0.4 s each):** cards "Fade + Float in up" staggered 0.15 s; big numbers "Zoom" 0.5 s; table rows fade in one by one on slide 6.
- Implementation note: pptxgenjs/python-pptx don't expose transitions/animations — after building the deck, post-process the XML: insert `<p:transition spd="slow"><p159:morph option="byObject"/></p:transition>` (with the `p159` namespace `http://schemas.microsoft.com/office/powerpoint/2015/09/main` inside an `mc:AlternateContent` block and a `<p:fade/>` fallback) into each slide, and add `<p:timing>` entrance effects for the named card shapes. Validate the file opens without repair.

## Slides

**1 — Title**
- Big: "Məryəm" · subtitle: "Resolves telecom billing & connectivity issues — by chat and by voice — in under 2 minutes."
- Small line: "AI Enterprise Solutions · Team ___"
- Visual: a glass card with a mock chat bubble ("Balansımdan 2 dəfə 10 manat çıxılıb" → "Yoxladım. 10 manatı qaytardım.") and a sound-wave line.

**2 — Value for the user: the problem**
- Persona card: "Leyla, 34 — 'I was charged 10 AZN twice.'"
- Three number cards: "~12 min to resolve today" (PRELIM), "~30% transferred to another department" (PRELIM, label "estimate"), "3 systems an agent checks".
- One line: "One workflow: billing & connectivity disputes."

**3 — Value for the user: before → after**
- Two glass columns with an arrow: Today (call 111 → wait → transfer) vs Məryəm (ask → investigated → resolved, receipt + reason).
- Numbers: "< 2 min" (PRELIM) · "24/7, AZ + RU" · "0 wrong refunds by design".

**4 — Prototype & use of AI: what runs**
- Three demo cards with icons: Chat (S01 double charge → refund + evidence) · Voice call (S04 roaming charge, barge-in) · Honest identity (B03).
- Caption: "Live demo + 2-min video. Synthetic data, fictional operator Səma Mobile."

**5 — Prototype & use of AI: AI vs code**
- Split card: left "AI (Claude Sonnet 5.5 · Haiku 5.5)": understands AZ/RU mixed speech · picks tools · finds the policy (RAG) · explains with emotion. Right "Deterministic code": 20 detectors · policy engine (≤ 20 AZN, rule IDs) · idempotent refunds · confirmations · privacy.
- Bottom strip — architecture as 5 small glass chips connected by thin lines: Web / ElevenLabs → FastAPI orchestrator → Detectors + Policy + RAG → DynamoDB.
- Key line: "The LLM never decides money."

**6 — Quality testing: results**
- Top row of 3 big numbers: "63 test cases (13 held out)" ✅ · "56/63 correct decisions" PRELIM · "0 wrong refunds" PRELIM.
- Comparison table (glass, rows fade in): Metric | Məryəm | Rules-only | Plain LLM — rows: correct decision, holdout, wrong refunds, right specialist team, banned phrases. Use the exact values from the source.
- Footnote ✅: "Policy engine 63/63 · RAG recall@4 0.98 (BM25) · 0 false anomalies in background data".

**7 — Quality testing: where we fail**
- Title: "Quality testing — honest failures"
- 3–4 failure cards from the failure gallery: case ID, what happened, why, fix. Red `#FB7185` dot for open, green for fixed. All PRELIM until replaced.
- One line: "Failures found by the eval drove these fixes."

**8 — Feasibility**
- Three cards: Data (billing events, tariff catalog, policy docs — all exist at any operator; ours is synthetic) · Cost (chat ~$0.01–0.02 / case, voice ~$0.07 / call — PRELIM; vs 12 min of agent time) · Stack (AWS App Runner, DynamoDB on-demand, OpenRouter, ElevenLabs).
- Next step card (highlighted orchid border): "2-week shadow pilot on one billing-dispute queue. Success = ≥ 85% agreement, 0 wrong credits, < 3 min average."

**9 — Originality**
- Five short glass chips, one line each: "LLM never touches money" · "AZ/RU code-switching" · "One brain, two channels" · "Human-like voice that tells the truth" · "No 'transferring you to an operator' — routed to the right specialist with a ticket & SLA".

**10 — Disclosure & links**
- Small table: Models (Claude Sonnet 5.5 & Haiku 5.5 via OpenRouter; ElevenLabs Agents, Eleven v4 Turbo, Scribe; Cohere Embed Multilingual v3 on Bedrock) · Libraries (FastAPI, boto3, rank_bm25, numpy) · Data (100% synthetic, fictional operator) · AI assistance (Claude Code for specs, data generator, KB, tests; all built after 09 Oct 11:00).
- Links row: Demo · Repo · Video (placeholders "___").
- Closing line: "Ask: a 2-week shadow pilot."

## Output
- Save `maryam_pitch.pptx`, then export a **text-based PDF** (`maryam_pitch.pdf`) and check that all text is selectable.
- Render every slide to PNG and review: no text overflow, contrast ≥ 4.5:1 on glass cards, PRELIM pills visible, numbers identical to the source.
