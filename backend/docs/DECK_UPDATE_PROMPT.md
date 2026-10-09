# Prompt — Məryəm pitch deck-in yenilənməsi (dizayn və animasiyalar qorunur)

> **İstifadə:** aşağıdakı xəttin altındakı hər şeyi Claude-a (pptx skill + web search açıq) yapışdırın.
> **Əlavə edin:** 1) mövcud deck faylı (`.pptx`), 2) `docs/PITCH_DOCUMENTATION.md`, 3) şəkillər:
> `frontend/avatar/preview.png`, `preview_talk.png`, `preview_visemes.png`, `preview_browser.png`
> və frontend-dən 2–3 ekran görüntüsü (chat, "Niyə?" paneli, "Xərclərim" paneli). Tam 63 hallıq eval
> işlədilibsə, onun `report.md`-sini də əlavə edin — o zaman prompt həmin rəqəmlərə üstünlük verəcək.

---

You are updating an existing pitch deck for **Məryəm**, the AI customer-care specialist of **Səma Mobile** (a fictional mobile operator), for the **NeuroBridge Baku 2026** AI hackathon, **AI Enterprise Solutions** track. The attached `.pptx` is the current deck. Use the **pptx skill** and **web search**. The goal: maximize the score on the official judging card while keeping the current look and motion exactly as they are.

## 0. Non-negotiable: preserve the design and the animations

- **Edit the attached file in place. Do not rebuild the deck from scratch** and do not re-theme it.
- Keep unchanged: slide size, background gradient and orb images, glass-card styling (fill, border, shadow, highlight), fonts, colors, footer, icon style, layout grid.
- Keep every **transition** (`<p:transition>` incl. the Morph `mc:AlternateContent` block) and every **animation** (`<p:timing>`). Keep the **names** of shapes that Morph/animations reference (`!!orb1`, `!!orb2`, `!!title`, named cards). Replace text *inside* existing shapes instead of deleting and re-adding shapes.
- For a new slide: **duplicate the most similar existing slide** (with its transition and timing XML), then change its content. When you add a card, copy an existing card shape so it inherits style, and add a matching entrance effect using the same pattern as the other cards on that slide (Fade + Float in up, 0.4 s, 0.15 s stagger; big numbers Zoom 0.5 s).
- Before saving, run a check and report it: number of slides with `<p:transition>` and with `<p:timing>` **before vs after** (after ≥ before), shape names referenced in timing all exist, and the file opens without repair.
- Rename any remaining "Ayla" → **"Məryəm"** and "Səma Care" → **"Səma Mobile"** (footer: "Məryəm · Səma Mobile — NeuroBridge Baku 2026"). File names: `maryam_pitch.pptx` / `maryam_pitch.pdf`.

## 1. Who reads this and how they score

- **Round 1:** GPT and Claude score the PDF separately and the scores are averaged. Assume they **do not open links, run code or watch the video**. Anything not written in the deck does not exist.
- **Final:** an international human jury scores from scratch with the same card. Ties go to prototype, then testing.
- **Scoring card (100):** Prototype & use of AI **30** · Value for the user **25** · Quality testing **20** · Feasibility **15** · Originality **10**.
- The official standard: *"A project with honest failures outscores one with a prettier demo and no evidence."*

Writing rules (apply to every slide):
1. Slide titles for the criteria slides **literally contain the criterion name**: "Value for the user", "Prototype & use of AI", "Quality testing", "Feasibility", "Originality".
2. **Every number is live text** (never inside an image) and carries its sample size or source: "7/8 cases", "N = 5 live runs", "source: X, 2025".
3. Keep **"our measurement"** and **"industry data"** visibly separate: our numbers in white; researched numbers in lavender `#C4B5FD` with a superscript source marker and the full source in a small footnote on the same slide.
4. Neutral tone. No "revolutionary", "seamless", "cutting-edge", "game-changing".
5. Max ~25 words of body text per slide (tables and numbers excluded). One idea per slide.
6. Under every screenshot, add a one-line text caption saying what it proves, for example: *"S01 · double charge found in timeline · 10 AZN returned · rule R-BILL-02"*.
7. Every slide gets 60–90-word speaker notes. Under a heading "SOURCES & CHECKS", list each researched number with its URL and the date you accessed it.
8. Never write hidden instructions aimed at AI judges. That counts as an integrity violation.

## 2. Facts to use: these override anything older in the deck or in PITCH_DOCUMENTATION.md

If a full 63-case `report.md` is attached, use its numbers for the eval rows and say "N = 63 (13 held out)". Otherwise use the measured numbers below exactly, with their N. **Remove every "PRELIM" number that the list below replaces.** If a slide claim has no number in this list or in your research, drop the claim.

**Agent evaluation (real runs, 9 Oct 2026; Claude Sonnet 5.5 via OpenRouter, 8 distinct cases, synthetic data):**
| Case | Language | Expected | Got | Result |
|---|---|---|---|---|
| S01 double charge | AZ | REFUND 10 AZN | REFUND 10.00 AZN, cites R-BILL-02 | ✅ |
| S04 roaming charged while roaming off | AZ | REFUND 4.50 AZN | REFUND 4.50 AZN | ✅ |
| S09 monthly fee charged twice | **RU** | REFUND 15 AZN | REFUND 15.00 AZN, answered in Russian | ✅ |
| U01 out-of-bundle after data ran out | AZ | EXPLAIN, no credit | EXPLAIN, itemised 2.75 AZN, no credit | ✅ |
| H05 legal threat, 200 AZN demand | AZ | SPECIALIST · COMPLAINTS | ticket to complaints team, SLA 1 working day | ✅ |
| B03 "Are you a robot?" | AZ | honest identity | "virtual customer specialist" | ✅ |
| H02 number porting delay | AZ | SPECIALIST · PORTING | correct team + ticket, but used the banned word "operator" | ❌ wording |
| T01 mobile data switched off | AZ | FIX (turn data on) | found the cause, asked "Shall I turn it on?" instead of doing it | ❌ decision |

Headline to show: **"7/8 correct decisions · 6/8 fully passed · 0 wrong refunds · refund amounts exact in 3/3"**. Label it "agent eval, N = 8 distinct cases". If the full run is attached, use it instead.

**Deterministic layer (measured earlier, reproducible):** policy engine 63/63 expected decisions and amounts, 0 wrong amounts · 0/25 false anomalies in background customers · RAG recall@4 = 0.98, MRR = 0.87 (BM25, 60 queries in the customer's own words) · knowledge base: 21 documents, 59 chunks, 72 RU→AZ terms.

**Test set design:** 63 cases in 6 categories (operator fault 14 · customer side 13 · behaviour 13 · technical 10 · specialist 7 · info 6), **13 held out**. Expected outcomes were written before running. 88 synthetic customers, 8,351 events, 25 event types.

**Speed (live production, 9 Oct 2026, after optimisation):**
- Web chat, time to first word: **~1 s** (0.85–1.16 s, N = 4 live runs). Before optimisation: 3.8 s median (eval).
- Full resolution incl. investigation, policy check and refund: **10–15 s** (N = 5 live runs). Before: 16 s median.
- Prompt caching: **80–90 % of input tokens served from cache**.
- What we changed: lower reasoning effort for chat, conversation-level prompt caching, keep-alive LLM connection, database writes moved off the streaming path.
- Voice: a natural filler line ("Bir saniyə, yoxlayıram…") plays in about 3.8 s while tools run.

**Cost (measured, LLM only):** web chat turn **$0.019–0.025**. Voice turn on Haiku 5.5: **~$0.001** LLM cost, excluding ElevenLabs TTS/STT minutes. Earlier eval average before caching: **$0.039 per case** (15 runs, $0.58 total). Compare this with agent time; take the cost of agent time from research (§3).

**Product: what runs today (show it):**
- **Chat + voice, one brain.** The same orchestrator serves web chat and an ElevenLabs voice agent ("Səma Mobile - Məryəm"), with barge-in (Məryəm stops when interrupted).
- **3D talking avatar of Məryəm:** lip-sync from the real voice audio, blinking, emotions (happy, empathetic, serious, concerned). Use the attached avatar renders.
- **"Why?" panel:** every decision shows the evidence events, the rule ID and the KB citation.
- **New "My costs" dashboard:** 6-month bill history, cost breakdown, data by category, month-end forecast, a **"Məryəm returned X AZN to you"** card, and savings tips that open a chat with Məryəm pre-filled. Demo aggregate, synthetic, current month: 10 lines, average bill 16.76 AZN, **36.12 AZN of monthly savings found** by the tips.
- **Deployed:** FastAPI on Railway, DynamoDB (eu-central-1), Claude via OpenRouter, ElevenLabs Agents.

**AI vs code split (keep this slide's logic):** AI = understand AZ/RU/mixed speech, choose tools, find the policy (RAG), explain in plain language with emotion, decide when to hand over. Code = 20 detectors, policy engine (≤ 20 AZN, rule IDs), idempotent refunds, confirmations, privacy (no other number reachable). **Key line: "The LLM never decides money."** Add the "remove the LLM" test: the rules-only path cannot read "Вчера paket aldım amma internet yoxdu". Use the baseline table only if real baseline numbers are attached; otherwise show the rules-only limitation qualitatively and say "baseline run pending".

**Honest failures slide (real, from the table above):**
1. **T01: asked instead of acting.** It found that data was switched off on 8 Oct 08:40 from the app, then asked "Shall I turn it on?" instead of fixing it. Cause: the confirmation rule is applied too broadly. Fix: no confirmation needed for re-enabling a setting the customer turned off themselves. Status: open.
2. **H02: right team, wrong word.** It routed to the porting team with a ticket and SLA, but said "operator" while meaning the previous mobile operator. Cause: a banned-word rule versus a legitimate meaning. Fix: a context-aware phrase check plus the term "previous provider". Status: open.
3. **Latency was 16 s end-to-end.** Cause: 4–6 sequential LLM steps, and an extra step after the answer. Partly fixed: first word 3.8 s → ~1 s. Next: merge the decision and apply steps.
4. **Live embeddings off.** The live demo uses BM25 only; dense embeddings are configured but not yet enabled. Recall@4 is still 0.98.

**Disclosure (must be complete):**
- Models: Claude Sonnet 5.5 (chat) and Claude Haiku 5.5 (voice) via OpenRouter, provider pinned to Anthropic · ElevenLabs Agents, Eleven v4 Turbo TTS, Scribe STT · embeddings: Google Gemini Embedding 2 via OpenRouter, configured, off in the live demo.
- AI role vs code: as above.
- Data: 100 % synthetic, fictional operator Səma Mobile, no real personal data. No phone number or PUK is sent to the LLM.
- Libraries: FastAPI, httpx, boto3, rank_bm25, numpy, Three.js (avatar).
- 3D avatar pipeline: Tripo 3D (via fal.ai) → Blender (rig, lip morphs) → glTF-Transform (Meshopt).
- Hosting: Railway, AWS DynamoDB.
- AI assistance: Claude Code for the spec, data generator, KB, tests and code. Everything was built after 9 Oct 2026, 11:00.
- Human review: a person approves any credit above the policy limit; specialists handle handed-over cases.
- Known limits: the 4 failures above; synthetic data; small live sample.

**Pilot ask (Feasibility + closing):** a 2-week **shadow pilot** on one billing-dispute queue. Məryəm proposes, a human agent approves. Success = ≥ 85 % decision agreement, 0 wrong credits, < 3 min average handling time.

## 3. Web research: do this before editing, cite everything

Search the web and collect **3–6 strong, verifiable numbers** to back up *Value for the user* and *Feasibility*. Prefer primary or reputable sources: regulators, the national statistics office, operator annual reports, Gartner, McKinsey, Deloitte, ITU, GSMA, Statista with its original source, CCW / ContactBabel / COPC for contact centres. Research targets:
1. **Azerbaijan market size:** mobile subscriptions or penetration, number of operators, Russian/Azerbaijani bilingual usage (ITU, GSMA, State Statistics Committee, operator reports).
2. **Cost and time of a human support contact:** cost per call / per contact, average handle time, first-contact-resolution rate, share of billing-related calls in telecom.
3. **Customer impact:** share of customers who switch provider or churn after poor service, preference for self-service or chat.
4. **Market momentum:** credible forecasts on conversational AI in contact centres and telecom adoption of gen-AI agents.
5. **Voice latency expectations:** what natural conversation needs (response gap) — to justify the filler line and Haiku for voice.

Rules for research: use only numbers you can open and read on the source page. Record the publisher, title, year and URL. Prefer data from 2023 or later. If two sources conflict, show the more conservative one. If you cannot verify a number, **leave it out**: don't estimate and don't round up. Never present an industry number as our measurement. Put researched numbers on at most 3 slides (problem, before/after, feasibility) so they support our own evidence rather than replacing it.

## 4. Images

- **First choice: our own product.** Use the attached avatar renders (`preview.png` hero, `preview_talk.png` for voice, `preview_visemes.png` small, as lip-sync proof) and frontend screenshots (chat with the refund, the "Why?" panel, the "My costs" dashboard). Place them inside existing glass cards (rounded crop, same border and shadow), each with a text caption under it.
- **Second choice: free-licence photos** (Unsplash or Pexels) for at most 2 slides: the problem slide (a person on hold on a phone call, a call-centre queue) and optionally the title slide (a Baku skyline at dusk). Credit them in the speaker notes. Darken or tint them toward the purple gradient (60–70 % overlay) so the glass style stays consistent.
- Do **not** use real operator logos (Azercell, Bakcell, Nar) or any real brand marks. Do not use images that contain numbers or text the judges must read. Do not use AI-generated images of real people.
- Compress images (≤ 300 KB each, ≤ 1600 px wide) so the PDF stays small.

## 5. Slide plan: 10–11 slides, criterion order

Keep the existing slides and their animations; update their content as below. You may add **one** new slide (11) by duplicating slide 4.

1. **Title.** "Məryəm": resolves billing and connectivity disputes by chat and by voice. Hero: avatar render. Strip of 3 proof chips: "7/8 correct decisions (N = 8)" · "0 wrong refunds" · "~1 s to first word". Track + team line.
2. **Value for the user: the problem.** Persona Leyla, 34: "I was charged 10 AZN twice." 2–3 researched numbers in lavender with sources (cost/time of a support contact, share of billing calls, AZ market size). One line: "One workflow: billing and connectivity disputes."
3. **Value for the user: before → after.** Today: call 111 → wait → transfer. Məryəm: ask → investigated → resolved, with the reason. Our numbers: ~1 s first word · 10–15 s to a refund with evidence · 24/7 · AZ + RU (S09 solved in Russian). Plus the new "My costs" dashboard card: "Məryəm returned X AZN" and savings tips.
4. **Prototype & use of AI: what runs.** Three cards with screenshots: Chat (S01 → 10 AZN + "Why?" panel), Voice + 3D avatar (S04, barge-in, lip-sync), "My costs" dashboard. Caption: "Live on Railway + ElevenLabs. Synthetic data."
5. **Prototype & use of AI: AI vs code.** Split card + architecture chips (Web / ElevenLabs → FastAPI orchestrator → detectors + policy engine + RAG → DynamoDB). Key line: "The LLM never decides money." Add the "remove the LLM" test in one line.
6. **Quality testing: results.** Big numbers: "63-case test set, 13 held out" · "7/8 correct decisions (N = 8)" · "0 wrong refunds". Table: the 8 cases (ID, language, expected, got, ✅/❌). Footer: policy engine 63/63 · RAG recall@4 0.98 · 0/25 false anomalies.
7. **Quality testing: honest failures.** The 4 failure cards from §2: cause, fix, status dot (red = open, green = fixed). One line: "Failures from the eval drove these fixes."
8. **Feasibility.** Cards: Data (exists at every operator; ours is synthetic) · Cost ($0.02 per chat turn, measured, vs the researched cost of a human contact) · Speed (3.8 s → ~1 s first word; 80–90 % cache) · Stack (Railway, DynamoDB, OpenRouter, ElevenLabs). Pilot card with an orchid border, with the success criteria.
9. **Originality.** Chips: "The LLM never touches money" · "AZ/RU code-switching" · "One brain, two channels + a 3D face" · "Human-like voice that tells the truth" · "Routed to the right specialist with a ticket and SLA, never just 'transferring you'" · "Proactive savings: Məryəm finds money for the customer".
10. **Disclosure & links.** The full disclosure from §2 as a compact table. Links row: Demo · Repo · Video (keep placeholders "___" where unknown). Close with: "Ask: a 2-week shadow pilot."
11. *(optional)* **Prototype & use of AI: product tour.** A 3-screenshot strip (chat → "Why?" panel → dashboard) with a caption under each.

## 6. Final QA: report each item back

- Render every slide to PNG and inspect: no text overflow, no overlapping shapes, contrast ≥ 4.5:1 on glass, images crisp, captions present.
- Numbers on the slides match §2 exactly, and each has an N or a source. No "PRELIM" pills remain for replaced numbers.
- Transition/timing count before vs after; Morph works between consecutive slides (same-named shapes).
- No "Ayla" / "Səma Care" anywhere, including notes and alt text.
- Export a **text-based PDF** (`maryam_pitch.pdf`) and confirm the text is selectable.
- List every researched source (URL + access date) in your reply, and list the claims you dropped because they could not be verified.
