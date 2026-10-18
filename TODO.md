# Athena — TODO

Live tracker. PLAN.md is the plan; this is the state. Update on every commit.

## Done
- [x] H1 Nepali decomposer + verifier (C/M/K signatures), tests
- [x] H2 Nepali seed list (310 words), config, model smoke test
- [x] H2 GCP project `<project>`, billing, APIs, gcloud + ADC
- [x] H2 STT bake-off: `chirp_3` @ `us` + phrase hints chosen (scripts/stt_probe.py)
- [x] H3 English verifier + lexicon (1,334 words, 71 tricky), tests
- [x] H4 Generation loop: planner → writer → verifier, cumulative feedback, verified fallbacks, JSONL log

- [x] H5 Illustrator (Gemini image, 4:3), parallel with writer, DESIGN.md §8 style
- [x] H5 Media store (local dir dev / GCS prod), proxied via `/api/media/{id}`
- [x] H5 In-memory learner/story store, 2 seeded learners (sita, ram)
- [x] H5 FastAPI: learners, `POST /api/session/start`, `GET /api/stories/{id}`, SPA static
- [x] H5 Rate limit on story generation (6/min/IP, 40/min global)
- [x] H5 Frontend: Vite + React + TS + Tailwind v4, DESIGN.md tokens, WordToken / StoryCard / VerifierLog, learner pick + story screens

## Local dev
- API: `.venv/bin/uvicorn athena.api:app --port 8077` (port 8000 is taken on this machine)
- Frontend: `cd frontend && npm run dev` → http://localhost:3000 (proxies /api → 8077)
- Types: `npx openapi-typescript http://localhost:8077/openapi.json -o src/api-types.ts`

## Deferred — deploy (user will trigger)
- [x] Dockerfile (multi-stage: node build → python, ffmpeg, non-root), container e2e 11/11
- [x] scripts/deploy.sh: Secret Manager key, private GCS bucket, service account roles, Firestore env (not run yet)
- [ ] Run deploy.sh (MIN_INSTANCES=1 on demo days, 0 otherwise)
- [ ] **GATE: verified illustrated story on public URL**

## Submission (due 2026-10-18 23:00)
- [ ] README for judges: how to test (demo learners, walkthrough, Chrome mic permission, known limits/quotas), guarantees (verifier, safety, code-computed maths, eval numbers), speed (prefetch, budget, STT v1 vs Chirp, Flash vs Flash-Lite, picture cache), architecture diagram, Google services, safety + privacy
- [ ] Screenshots
- [ ] Fill pptx deck from presentation/DECK_PLAN.md
- [ ] Public GitHub repo (user go-ahead; re-check no secrets / project ID)
- [ ] Video script + recording
- [ ] Ask: video length, team name, image quota increase

## Next
- [x] H6 Eval harness: verdict line, retries, cost. Full runs 100/100 SUCCESS, 0 shipped (eval/results/)
- [x] Theme-aware planner (ne fallback 38%→28%) + 20s app generation budget
- [x] H7 Alignment (audible-only Nepali scoring), STT chirp_3 + Gemini fallback, /api/session/read, record button + word colours
- [ ] H7 **You: try read-aloud in a browser with a real mic** (headless can't)
- [ ] Eval C: human recordings with scripted errors (TTS 'fixes' scripted errors; non-words need humans)
- [x] H9 Mastery loop: rule (3 correct sessions → mastered; 2 errors in a session → practising + sits out 1 story), `/api/session/close`, change strip, `#/mastery/<learner>` grid
- [ ] Demo note: demotion needs the SAME unit wrong twice in one reading (e.g. misread two ब words)
- [ ] H10 Thin ADK wrap; Gemma safety pre-screen; cost/latency instrumentation
- [ ] H11 Teacher view, print pack, GitHub Action (tests + eval)
- [ ] H12 Eval run, charts

- [x] Dynamic progression: unit introduction by unlock value (2.7x readable words at 40 units), 3 difficulty levels enforced like letters, honorific-aware seed
- [ ] Deck chart: eval/results/coverage_ne.csv + coverage_en.csv (unlock vs teaching order)
- [ ] Eval re-run with levels (eval uses default level 2) and template fallback

- [x] Personalisation: name case endings (सीताले), learner profiles (favourite animal/food, general setting) → personal themes ~60% of stories; add-learner screen #/new for the pilot

- [x] Placement diagnostic: 2-min tiered card check (adult taps read / not yet), places units + level; runs after add-learner
- [x] Re-teach: tap word → hear (Gemini TTS, cached, story words only), parts with error unit marked, practice retry (no STT hint)
- [x] Persist learners: state/learners.json, atomic, delete endpoint + button (Firestore still needed for Cloud Run)
- [x] Parent dashboard #/parent/<id>: week stats, learned units, struggle alerts (demoted 2× in 30 days), home activities (model + verified child words), recent stories
- [x] Encouragement: spoken praise from fixed phrases, 'new letters you can read' strip, gentle 'let's practise'
- [x] Time controls: parent daily limit, friendly 'see you tomorrow'
- [x] Re-teach picture cue for concrete nouns

- [x] History: every story + per-word reading per learner (state/stories/*.jsonl, no audio), parent story review #/parent/<id>/story/<sid>
- [ ] Pilot data export for eval D (per-word error profiles from state/stories)

- [x] Safety check before display (blocklist + Flash-Lite), unsafe -> verified template
- [x] ADK writer engine (agent must pass verifier tool; WRITER_ENGINE=adk), benchmarked vs loop
- [x] Live follow-along (STT v1 streaming + hints, WebSocket), >60 s recordings chunked
- [x] Instant Next (prefetch after reading, re-verified), pre-spoken words, 30x smaller pictures
- [x] Profile insights (groups, mistake patterns, pace, parent note) + game-like card check (listen-and-tap, early stop)
- [x] Read to me (karaoke), child picks the story (3 tiles, prepared one ready), gender agreement, maths word problems
- [x] Maths: own level per language (4/5 first tries up, 3 misses down), English entry, daily limit covers maths, answers survive restarts (pid carries learner, rebuilt from history), parent + teacher maths sections, eval/maths_eval.py
- [ ] You: review ~10 Nepali maths problems (templates + model) in eval/results/maths-*.jsonl
- [ ] Deploy (evening): Dockerfile w/ ffmpeg, otel/api-core pin conflict, WebSocket timeout, Secret Manager

## Brief gaps (checked against the full brief, 18 Oct)
- [x] 1. Log re-teach use (hear / parts / picture / retry + did the retry work); open re-teach with the style that worked for this child; show in parent log ("Helps most" in profile, per-story practice log)
- [x] 2. Automatic re-teach: long pause on a word (live follow-along) or same unit missed twice -> gentle re-teach card
- [x] 3. "Teach the cat" (child-sized Feynman / protégé effect): cat reads a known story with 1-2 code-chosen mistakes from the child's own confusions (घ->ग, ट->त, ि<->ी); child taps the wrong word. Maths: cat answers with the child's own mistake kind; child says right / not right and shows the answer
- [x] 4. "Why this story" for parents: plain bilingual line per story (units practised, interest used, outcome, safety), built in code
- [x] 5. Response time in adaptation: slow-but-right maths does not count toward level up; long hesitations keep a word's units practising

- [x] 7. Content controls: maths on/off, pictures on/off, themes to avoid (fixed list); planner + learner card respect them
- [ ] 8. Story-based re-teach: letter mnemonic ("ख, खसीको ख"); maths step-by-step ("start with 3, count 2 more: 4, 5")
- [ ] 9. Interests in maths: prefer favourite animal/food when readable
- [ ] 10. Explicit skill graph: prerequisites (matra needs a consonant, conjunct needs both letters; maths +5 -> +10 -> -10 -> 20), shown in teacher view

## Tech debt / decisions pending
- [ ] Vertex quota: 429s above ~2 concurrent on gemini-3.8-flash (asia-south1). Request increase before public demo
- [ ] Gemma not served on Vertex as plain API → Model Garden GPU endpoint or Flash-Lite as cheap tier (H10)
- [x] ~~Move generation to Vertex AI~~ done (AQ. Vertex key)
- [x] Firestore store (STORE_BACKEND=firestore; round trip tested against real DB)
- [ ] Writer quality on tiny Nepali sets: pruned sentences can be ungrammatical (eval B)
- [ ] Grapheme mastery is spelling-level (ow cow/snow, oo moon/book): README limitation
- [ ] STT phrase hints may mask real child errors: eval C with/without hints
- [ ] TTS (H11): Cloud TTS has NO ne-NP voices → use gemini-3.8-flash-tts with bare text
- [ ] `rr` grapheme unused in lexicon

## Needs a human
- [ ] Native reader: spot-check `data/ne_seed_words.txt`
- [ ] Spot-check ~100 English segmentations in `data/en_lexicon_src.txt`
- [ ] Budget alert ($50) in GCP Billing
- [ ] Confirm exact submission deadline (time on 18 Oct)
- [ ] Pilot: 3–5 children, consent, Sunday midday


- [ ] Finmann technique
- [ ] onboarding screens like duolingo abc