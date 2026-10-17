"""FastAPI app: JSON API under /api, built React app served from frontend/dist."""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from athena import media
from athena.agents import illustrator
from athena.agents.planner import plan
from athena.generate import generate
from athena.models import Language
from athena.ratelimit import RateLimit
from athena.store import Learner, Story, store

log = logging.getLogger("athena")
app = FastAPI(title="Athena")
_pool = ThreadPoolExecutor(max_workers=8)
story_limit = RateLimit(per_ip=6, global_=40)

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


# --- schemas -------------------------------------------------------------------


class LearnerOut(BaseModel):
    id: str
    name: dict[str, str]
    avatar: str
    mastery: dict[str, list[str]]


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
    )


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
    p = plan(req.language, frozenset(learner.mastery[req.language]), learner.name[req.language], theme=req.theme)

    # Image starts now from the theme; text is generated + verified meanwhile.
    image_future = _pool.submit(illustrator.illustrate, p.theme)
    result = generate(p)
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
