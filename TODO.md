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
- [ ] Dockerfile (multi-stage: node build → python)
- [ ] Secret Manager for GEMINI_API_KEY; private GCS bucket for media
- [ ] Cloud Run: min-instances=1, max-instances=1 (in-memory store), startup warm-up call (cold first request ~14s)
- [ ] **GATE: verified illustrated story on public URL**

## Next
- [ ] H6 Eval harness v1: 50 req/lang × 10 mastery sets; first-pass vs final violation, attempts, fallback %
- [ ] H7–8 Record → STT (chirp_3 + hints) → alignment → per-word outcomes
- [ ] H9 Mastery update rule, `/api/session/close`, MasteryGrid
- [ ] H10 Thin ADK wrap; Gemma safety pre-screen; cost/latency instrumentation
- [ ] H11 Teacher view, print pack, GitHub Action (tests + eval)
- [ ] H12 Eval run, charts

## Tech debt / decisions pending
- [ ] Move generation to **Vertex AI** (brief names it; currently AI Studio key). Check model availability on Vertex
- [ ] Firestore store (in-memory needs `max-instances=1` until then)
- [ ] Writer quality on tiny Nepali sets: pruned sentences can be ungrammatical (eval B)
- [ ] Grapheme mastery is spelling-level (ow cow/snow, oo moon/book): README limitation
- [ ] STT phrase hints may mask real child errors: eval C with/without hints
- [ ] TTS prompt reads the instruction aloud; use bare text
- [ ] `rr` grapheme unused in lexicon

## Needs a human
- [ ] Native reader: spot-check `data/ne_seed_words.txt`
- [ ] Spot-check ~100 English segmentations in `data/en_lexicon_src.txt`
- [ ] Budget alert ($50) in GCP Billing
- [ ] Confirm exact submission deadline (time on 18 Oct)
- [ ] Pilot: 3–5 children, consent, Sunday midday
