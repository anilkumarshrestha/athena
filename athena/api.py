"""FastAPI app: JSON API under /api, built React app served from frontend/dist."""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from athena import media
from athena.agents import illustrator
from athena.agents.planner import plan
from athena.assess import stt
from athena.assess.align import assess, tokens
from athena.generate import generate
from athena.mastery import allowed, apply_session, practice_targets
from athena.models import Language
from athena.ratelimit import RateLimit
from athena.store import Learner, Story, store

log = logging.getLogger("athena")
app = FastAPI(title="Athena")
_pool = ThreadPoolExecutor(max_workers=8)
story_limit = RateLimit(per_ip=6, global_=40)
STORY_BUDGET_S = 20  # a child should not wait longer; past it the verified fallback is served

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


# --- schemas -------------------------------------------------------------------


class UnitOut(BaseModel):
    unit: str
    state: str  # mastered | practicing | unseen | excluded
    streak: int
    seen: int
    cooldown: int


class LearnerOut(BaseModel):
    id: str
    name: dict[str, str]
    avatar: str
    mastery: dict[str, list[str]]  # units stories may use now
    units: dict[str, list[UnitOut]]


class ChangeOut(BaseModel):
    unit: str
    before: str
    after: str


class CloseRequest(BaseModel):
    story_id: str


class CloseOut(BaseModel):
    story_id: str
    changes: list[ChangeOut]
    learner: LearnerOut


class ViolationLog(BaseModel):
    word: str
    unit: str | None
    index: int
    reason: str


class AttemptLog(BaseModel):
    n: int
    title: str
    sentences: list[str]
    violations: list[ViolationLog]
    ms: int
    model: str


class DisplayWord(BaseModel):
    text: str  # as shown, punctuation attached
    indices: list[int]  # reference word indices it covers (for read-aloud outcomes)


class StoryOut(BaseModel):
    id: str
    learner_id: str
    language: Language
    theme: str
    title: str
    sentences: list[str]
    outcome: str
    units_used: list[str]
    attempts: list[AttemptLog]
    total_latency_ms: int
    image_status: str
    image_url: str | None
    image_latency_ms: int | None
    display: list[list[DisplayWord]]


class WordOut(BaseModel):
    index: int
    expected: str
    heard: str | None
    outcome: str
    error_units: list[str]


class InsertionOut(BaseModel):
    word: str
    before_index: int


class ReadOut(BaseModel):
    story_id: str
    transcript: str
    engine: str
    stt_ms: int
    words: list[WordOut]
    insertions: list[InsertionOut]
    words_correct: int
    wcpm: float
    unit_errors: dict[str, int]
    unit_correct: dict[str, int]


class StartRequest(BaseModel):
    learner_id: str
    language: Language
    theme: str | None = None


def learner_out(learner: Learner) -> LearnerOut:
    return LearnerOut(
        id=learner.id,
        name=learner.name,
        avatar=learner.avatar,
        mastery={lang: sorted(units) for lang, units in learner.mastery.items()},
        units={
            lang: [UnitOut(unit=sig, **u.__dict__) for sig, u in sorted(units.items())]
            for lang, units in learner.units.items()
        },
    )


def display_words(language: str, sentences: list[str]) -> list[list[DisplayWord]]:
    """Whitespace chunks as shown on screen, mapped to reference token indices."""
    out, idx = [], 0
    for sentence in sentences:
        line = []
        for chunk in sentence.split():
            n = len(tokens(language, chunk))
            line.append(DisplayWord(text=chunk, indices=list(range(idx, idx + n))))
            idx += n
        out.append(line)
    return out


def story_out(s: Story) -> StoryOut:
    r = s.result
    return StoryOut(
        id=s.id,
        learner_id=s.learner_id,
        language=s.language,
        theme=r.plan.theme,
        title=r.title,
        sentences=r.sentences,
        outcome=r.outcome,
        units_used=r.units_used,
        attempts=[
            AttemptLog(
                n=a.n,
                title=a.title,
                sentences=a.sentences,
                violations=[
                    ViolationLog(word=v.word, unit=v.unit, index=v.word_index, reason=v.reason) for v in a.violations
                ],
                ms=a.latency_ms,
                model=a.usage.model,
            )
            for a in r.attempts
        ],
        total_latency_ms=r.total_latency_ms,
        image_status=s.image_status,
        image_url=f"/api/media/{s.image_id}" if s.image_id else None,
        image_latency_ms=s.image_latency_ms,
        display=display_words(s.language, r.sentences),
    )


# --- routes --------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/learners", response_model=list[LearnerOut])
def list_learners() -> list[LearnerOut]:
    return [learner_out(x) for x in store.list_learners()]


@app.get("/api/learners/{learner_id}", response_model=LearnerOut)
def get_learner(learner_id: str) -> LearnerOut:
    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    return learner_out(learner)


@app.post("/api/session/start", response_model=StoryOut, dependencies=[Depends(story_limit)])
def start_session(req: StartRequest) -> StoryOut:
    learner = store.get_learner(req.learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    units = learner.units[req.language]
    p = plan(
        req.language,
        allowed(units),
        learner.name[req.language],
        theme=req.theme,
        target_units=practice_targets(units)[:3] or None,  # practise what is being learned
    )

    # Image starts now from the theme; text is generated + verified meanwhile.
    image_future = _pool.submit(illustrator.illustrate, p.theme)
    result = generate(p, budget_s=STORY_BUDGET_S)
    story = store.add_story(learner.id, req.language, result)

    def _done(fut) -> None:
        try:
            data, mime, _usage, ms = fut.result()
            store.set_image(story.id, "ready", media.save(data, mime), ms)
        except Exception:
            log.exception("illustration failed for story %s", story.id)
            store.set_image(story.id, "failed", None, None)

    image_future.add_done_callback(_done)
    return story_out(story)


MAX_AUDIO_BYTES = 8 * 1024 * 1024  # ~4 min of opus; a story read takes < 1 min
read_limit = RateLimit(per_ip=12, global_=60)


@app.post("/api/session/read", response_model=ReadOut, dependencies=[Depends(read_limit)])
def read_session(
    story_id: str = Form(...),
    duration_s: float = Form(..., gt=0, le=300),
    hints: bool = Form(True),
    audio: UploadFile = File(...),
) -> ReadOut:
    """Score one read-aloud. Audio stays in memory and is dropped after scoring (no retention)."""
    s = store.get_story(story_id)
    if not s:
        raise HTTPException(404, "story not found")
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise HTTPException(400, "empty audio")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "recording too long")

    learner = store.get_learner(s.learner_id)
    name = learner.name[s.language] if learner else ""
    names = frozenset(name.split()) | frozenset(name.lower().split())
    reference = " ".join(s.result.sentences)
    phrases = sorted(set(tokens(s.language, reference)))

    t = stt.transcribe(s.language, data, audio.content_type or "audio/webm", phrases, hints=hints)
    del data  # no audio retention beyond this request
    a = assess(s.language, reference, t.text, duration_s, allowed_words=names)
    s.readings.append(a)

    return ReadOut(
        story_id=s.id,
        transcript=t.text,
        engine=t.engine,
        stt_ms=t.latency_ms,
        words=[WordOut(**w.__dict__) for w in a.words],
        insertions=[InsertionOut(**i.__dict__) for i in a.insertions],
        words_correct=a.words_correct,
        wcpm=a.wcpm,
        unit_errors=a.unit_errors,
        unit_correct=a.unit_correct,
    )


@app.post("/api/session/close", response_model=CloseOut)
def close_session(req: CloseRequest) -> CloseOut:
    """Apply the latest reading of a story to the learner's mastery (PLAN §5). Once per story."""
    s = store.get_story(req.story_id)
    if not s:
        raise HTTPException(404, "story not found")
    learner = store.get_learner(s.learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    if s.changes is not None:
        raise HTTPException(409, "session already closed")
    if not s.readings:
        raise HTTPException(400, "no reading to score yet")
    a = s.readings[-1]
    changes = apply_session(learner.units[s.language], a.unit_correct, a.unit_errors)
    s.changes = changes
    return CloseOut(
        story_id=s.id,
        changes=[ChangeOut(unit=c.unit, before=c.before, after=c.after) for c in changes],
        learner=learner_out(learner),
    )


@app.get("/api/stories/{story_id}", response_model=StoryOut)
def get_story(story_id: str) -> StoryOut:
    s = store.get_story(story_id)
    if not s:
        raise HTTPException(404, "story not found")
    return story_out(s)


@app.get("/api/media/{media_id}")
def get_media(media_id: str) -> Response:
    found = media.load(media_id)
    if not found:
        raise HTTPException(404, "not found")
    data, mime = found
    return Response(data, media_type=mime, headers={"Cache-Control": "public, max-age=86400, immutable"})


# --- SPA -----------------------------------------------------------------------

if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404)
        f = DIST / path
        return FileResponse(f if path and f.is_file() and DIST in f.resolve().parents else DIST / "index.html")
