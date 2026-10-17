# Athena

A reading tutor for Nepali children (ages 5–8) learning to decode **Nepali and English**.
Athena generates illustrated stories that use **only** the letters, vowel signs and
conjuncts a child has already mastered. The model writes the story; a deterministic
verifier checks every word, so no story ever reaches a child with a unit they cannot read yet.

> Model proposes, code decides.

Status: story generation, verification, illustration and the child story screen work
locally. Reading aloud, mastery updates and deployment are in progress (see [TODO.md](TODO.md)).

---

## Quick start

```bash
# 1. Python backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env          # then fill it in, see "Configuration"

# 2. Frontend (Node 22)
cd frontend && npm install && cd ..

# 3. Run (two terminals)
.venv/bin/uvicorn athena.api:app --port 8077 --reload
cd frontend && npm run dev
```

Open **http://localhost:3000**, pick a learner, pick नेपाली or English.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | |
| Node | 22+ | Vite 8 needs ≥ 20.19. With nvm: `nvm install 22` |
| gcloud CLI | any | Only for Speech-to-Text, Firestore, GCS and deploy. Not needed to generate stories |

## Configuration

All settings come from `.env` (read by `athena/config.py`).

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `GEMINI_API_KEY` | yes | | Vertex AI API key (`AQ.…`) or AI Studio key (`AIza…`) |
| `GOOGLE_GENAI_USE_VERTEXAI` | yes | `false` | `true` for a Vertex key (recommended, billed to your project). `false` for an AI Studio key |
| `GOOGLE_CLOUD_PROJECT` | for GCP services | | Project ID |
| `GOOGLE_CLOUD_LOCATION` | no | `us-central1` | Used for Vertex via gcloud credentials (no key) |
| `WRITER_MODEL` | no | `gemini-3.8-flash` | Story writer |
| `IMAGE_MODEL` | no | `gemini-3.1-flash-image` | Illustrator |
| `WRITER_THINKING_LEVEL` | no | `low` | `low` keeps latency ~3s per attempt |
| `REQUEST_TIMEOUT_MS` | no | `30000` | Per model call; failed calls are retried with backoff |
| `MEDIA_BUCKET` | no | empty | GCS bucket for images. Empty = local `media/` folder |

**Which key?** A Vertex AI key (`AQ.…`) is restricted to `aiplatform.googleapis.com` and
**only works with `GOOGLE_GENAI_USE_VERTEXAI=true`**. With `false` it fails with
`403 API_KEY_SERVICE_BLOCKED`. AI Studio free-tier keys are limited to 5 requests/minute,
which is too low for the eval or a demo.

Without any key, Vertex can also use your gcloud login: leave `GEMINI_API_KEY` empty, set
`GOOGLE_GENAI_USE_VERTEXAI=true`, and run:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <project-id>
```

Never commit `.env`. It is git-ignored.

---

## Running

### Development (hot reload)

| Process | Command | URL |
|---|---|---|
| API | `.venv/bin/uvicorn athena.api:app --port 8077 --reload` | http://localhost:8077/docs |
| Frontend | `cd frontend && npm run dev` | http://localhost:3000 |

The Vite dev server proxies `/api` to `:8077`. To use another API port, change the proxy
in `frontend/vite.config.ts`.

### Production build, single server

```bash
cd frontend && npm run build && cd ..
.venv/bin/uvicorn athena.api:app --port 8077
```

FastAPI serves `frontend/dist` at http://localhost:8077 alongside the API.

### Stopping

`Ctrl+C` in each terminal. If a server was started in the background, find it by port:

```bash
ss -ltnp | grep -E ':(8077|3000) '   # shows pid=…
kill <pid>
```

### Pages

| URL | Page |
|---|---|
| `#/` | Learner pick |
| `#/read/sita/ne` | Story for learner `sita` in Nepali (`en` for English) |
| `#/styleguide` | Components from [DESIGN.md](DESIGN.md) |

Learners are saved to `state/learners.json` (atomic writes; survives restarts). Two demo learners
(`sita`, `ram`) are seeded on first run. The file holds children's first names and progress: it is
git-ignored, and a learner can be deleted from the teacher view (`DELETE /api/learners/{id}`).
To reset everything, stop the API and delete `state/`.

On the story screen, **"Show how this story was made"** opens the verifier log: every
attempt, the words that broke the rules, and the unit that broke them.

### API

| Method | Path | |
|---|---|---|
| GET | `/api/learners` | Learners with their mastery sets |
| GET | `/api/learners/{id}` | One learner |
| POST | `/api/session/start` | `{learner_id, language}` → verified story; the image fills in later |
| GET | `/api/stories/{id}` | Story with current image status (poll until `ready`) |
| GET | `/api/media/{id}` | Story image |

Story generation is rate-limited (6 per minute per IP, 40 per minute in total).
Full schema: http://localhost:8077/docs.

After changing API models, regenerate the frontend types with the API running:

```bash
cd frontend && npx openapi-typescript http://localhost:8077/openapi.json -o src/api-types.ts
```

---

## Tests

```bash
.venv/bin/pytest            # verifier tests (Nepali + English), no network
cd frontend && npm run build   # type-checks the frontend
```

The verifier is the one part that must be correct. Its tests run offline in under a second.

---

## Scripts

| Command | What it does | Calls models |
|---|---|---|
| `.venv/bin/python scripts/generate.py ne_basic --name सीता` | Generate one story from a preset and print the verifier log | yes |
| `.venv/bin/python scripts/smoke.py` | One call each to writer, Gemma, image model; checks STT credentials. Gemma fails on Vertex (not served as a plain API) | yes |
| `.venv/bin/python scripts/stt_probe.py` | Nepali speech-to-text comparison on a synthesized sentence | yes |
| `.venv/bin/python scripts/build_ne_seed.py` | Rebuild `data/ne_seed.json` from `data/ne_seed_words.txt` | no |
| `.venv/bin/python scripts/build_en_lexicon.py` | Rebuild `data/en_lexicon.json` from the English sources | no |

Presets (synthetic mastery sets) are defined in `athena/presets.py`:
`ne_early`, `ne_basic`, `ne_mid`, `ne_mid_conj`, `en_satpin`, `en_satpin_sh`, `en_p2`, `en_p3`, `en_p3_no_sh`.

Every generation is appended to `logs/generation.jsonl` (prompt, attempts, violations, latency, tokens).

---

## Eval

```bash
.venv/bin/python -u eval/run_eval.py --n 50 --workers 2
```

- `--n`: stories per language. Presets and themes rotate with fixed seeds.
- `--workers`: parallel calls. Keep it at 2: Vertex returns 429 above about 2 concurrent calls.
- Text only, no images. A full run (`--n 50`) takes about 20 minutes.
- **The last line is the verdict:** `EVAL SUCCESS: 100/100 completed` or `EVAL FAILED: …`, and
  the exit code matches. A run fails if any job errored or is missing, or if any shipped
  story has a violation.
- Output: `eval/results/<stamp>.summary.json` (committed) and `<stamp>.jsonl` (per-story detail, git-ignored).
- Cost uses the prices in `eval/prices.json`.

Latest full run (`eval/results/20261017-191030.summary.json`, 50 stories per language):

| | Nepali | English |
|---|---|---|
| Clean on first attempt | 30% | 74% |
| Mean attempts | 2.22 | 1.32 |
| Verified fallback (pruned sentences / word list) | 38% | 2% |
| **Violations shipped** | **0** | **0** |
| Latency p50 / p95 | 12.9s / 85.4s | 4.5s / 82.1s |
| Cost per story, text + image | $0.070 | $0.068 |

Native-speaker review of generated Nepali (grammar, idiom) is logged by hand in
[eval/human_review.md](eval/human_review.md).

---

## Editing the word data

**Nepali seed words:** edit `data/ne_seed_words.txt` (one word per token, `# category` headers),
then run `scripts/build_ne_seed.py`. The decomposer tags every word; a malformed word stops the build.

**English lexicon:** words are written as grapheme splits in `data/en_lexicon_src.txt`, for example `sh.i.p`.
The spelling is built from the splits, so tags and spellings cannot disagree.
- Silent-e words: tag the vowel and mark the e, for example `c.a_e.k._e`.
- Plurals: `+s` after a word also adds the word with an `s`.
- Tricky words: `data/en_tricky.txt`, optionally followed by a split if the word becomes decodable later.

Then run `scripts/build_en_lexicon.py` and `pytest`.

---

## Project layout

```
athena/
  verifier/       base.py, nepali.py, english.py   pure stdlib, the guarantee
  agents/         planner.py, writer.py, illustrator.py
  generate.py     writer → verifier loop, retries, verified fallbacks
  api.py          FastAPI app (+ serves frontend/dist)
  config.py       settings + Gemini clients
  presets.py      synthetic mastery sets
  store.py        in-memory learners/stories
  media.py        image storage (local or GCS)
  retry.py        backoff on 429/5xx
frontend/         Vite + React + TypeScript + Tailwind v4 (tokens from DESIGN.md)
data/             Nepali seed words, English lexicon + tricky words
eval/             run_eval.py, prices.json, results/, human_review.md
scripts/          CLI tools (see Scripts)
tests/            verifier tests
PLAN.md           build plan and decisions log
DESIGN.md         visual system
TODO.md           live task tracker
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `403 API_KEY_SERVICE_BLOCKED` | Vertex key used against AI Studio | `GOOGLE_GENAI_USE_VERTEXAI=true` |
| `429 RESOURCE_EXHAUSTED … free_tier` | AI Studio free-tier key | Use a Vertex key, or a key from a billed project |
| `429` during eval on Vertex | Too many parallel calls | `--workers 2` |
| `404 … gemini-flash-latest` on Vertex | Alias only exists on AI Studio | Use an explicit model ID (default `gemini-3.8-flash`) |
| `address already in use` | Port taken by another process | Use another port and update the Vite proxy |
| First story after API start takes ~15s | Cold client and TLS | Expected; later stories take ~3–6s |
| Image never appears | Image call failed (see API log) | The story still shows; `image_status` becomes `failed` |
