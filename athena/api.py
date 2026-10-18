"""FastAPI app: JSON API under /api, built React app served from frontend/dist."""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import asyncio

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import hashlib
import threading
import re
import time
from typing import Literal

from athena import media
from athena.dashboard import summarize, used_minutes_today
from athena.diagnostic import diagnostic, place
from athena.agents import illustrator
from athena.agents.planner import plan
from athena.assess import stt
from athena.assess.align import assess, fold, tokens
from athena.assess.parts import word_parts
from athena import tts
from athena.generate import generate
from athena.lexicon import verifier_for
from athena.mastery import Change, UnitState, allowed, apply_session, practice_targets
from athena.progression import MAX_PRACTICING, next_level, next_units, should_introduce
from athena.models import Language
from athena.ratelimit import RateLimit
from athena.profile import SETTINGS, AnimalId, FoodId, GenderId, SettingId, StartId, personal_themes
from athena.store import Learner, Story, new_learner, store
from athena.verifier.nepali import DecomposeError, decompose, normalize

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
    level: dict[str, int]
    recent_accuracy: dict[str, list[float]]  # last 5 sessions, oldest first
    profile: dict[str, str]
    settings: dict[str, int]
    maths_level: dict[str, int]


class LearnerCreate(BaseModel):
    """Fixed choices only: these values reach the model prompt."""

    name_ne: str = Field(min_length=1, max_length=20)
    name_en: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z][A-Za-z ]*$")
    favorite_animal: AnimalId
    favorite_food: FoodId
    gender: GenderId = "unspecified"
    setting: SettingId
    start: StartId

    @field_validator("name_ne")
    @classmethod
    def devanagari_name(cls, v: str) -> str:
        v = normalize(v.strip())
        try:
            for part in v.split():
                decompose(part)  # Devanagari letters only, well formed
        except DecomposeError as e:
            raise ValueError("name must be written in Devanagari") from e
        return v


class ChangeOut(BaseModel):
    unit: str
    before: str
    after: str


class CloseRequest(BaseModel):
    story_id: str


class CloseOut(BaseModel):
    story_id: str
    accuracy: float
    level_before: int
    level_after: int
    changes: list[ChangeOut]  # before "unseen" = newly introduced unit
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
    letters: list[dict] = []  # letter mode only: [{unit, example, practising}]


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
        level=learner.level,
        recent_accuracy={lang: [round(a, 2) for a in h[-5:]] for lang, h in learner.history.items()},
        profile=learner.profile,
        settings=learner.settings,
        maths_level={lang: st.get("level", 1) for lang, st in learner.maths.items()},
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


create_limit = RateLimit(per_ip=10, global_=60)


class CardOut(BaseModel):
    id: str
    text: str
    options: list[str] = []  # listen cards: tiles to tap


class TierOut(BaseModel):
    number: int
    name: str
    always: bool
    kind: str
    cards: list[CardOut]


class DiagnosticOut(BaseModel):
    language: Language
    pass_rate: float
    tiers: list[TierOut]


class PlacementRequest(BaseModel):
    language: Language
    responses: dict[str, bool]  # card id -> read it


class PlacementOut(BaseModel):
    level: int
    reached_tier: int
    mastered: int
    practicing: list[str]
    learner: LearnerOut


def _seed(learner_id: str) -> int:
    """Same learner, same cards: the placement is recomputed from the same deck."""
    return int(hashlib.sha256(learner_id.encode()).hexdigest()[:8], 16)


@app.get("/api/learners/{learner_id}/diagnostic/{language}", response_model=DiagnosticOut)
def get_diagnostic(learner_id: str, language: Language) -> DiagnosticOut:
    from athena.diagnostic import PASS

    if not store.get_learner(learner_id):
        raise HTTPException(404, "learner not found")
    tiers = diagnostic(language, seed=_seed(learner_id))
    return DiagnosticOut(
        language=language,
        pass_rate=PASS,
        tiers=[
            TierOut(number=t.number, name=t.name, always=t.always, kind=t.kind,
                    cards=[CardOut(id=c.id, text=c.text, options=list(c.options)) for c in t.cards])
            for t in tiers
        ],
    )


sound_limit = RateLimit(per_ip=60, global_=300)


@app.get("/api/diagnostic/{language}/sound/{text}", dependencies=[Depends(sound_limit)])
def diagnostic_sound(language: Language, text: str) -> Response:
    """Spoken letter for a listen-and-tap card. Only the diagnostic's own letters."""
    from athena.diagnostic import _EN_SET1, _EN_SET2, _NE_T1, _NE_T2

    allowed_texts = set(_NE_T1 + _NE_T2) if language == "ne" else set(_EN_SET1 + _EN_SET2)
    if text not in allowed_texts:
        raise HTTPException(404, "not a diagnostic letter")
    return Response(
        tts.speak_word(language, tts.letter_phrase(language, text)),
        media_type="audio/wav",
        headers={"Cache-Control": "no-cache"},  # phrasing may improve; the server caches the audio
    )


@app.post("/api/learners/{learner_id}/placement", response_model=PlacementOut)
def set_placement(learner_id: str, req: PlacementRequest) -> PlacementOut:
    """Score the card check and set the learner's starting units and level for that language."""
    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    tiers = diagnostic(req.language, seed=_seed(learner_id))
    known_ids = {c.id for t in tiers for c in t.cards}
    if not req.responses or not set(req.responses) <= known_ids:
        raise HTTPException(400, "responses must be card ids from this learner's diagnostic")
    p = place(req.language, tiers, req.responses)
    units = {u: UnitState("mastered", streak=3, seen=3) for u in p.mastered}
    units.update({u: UnitState("practicing", streak=0, seen=0) for u in p.practicing})
    learner.units[req.language] = units
    learner.level[req.language] = p.level
    learner.history[req.language] = []
    store.save()
    return PlacementOut(
        level=p.level,
        reached_tier=p.reached_tier,
        mastered=len(p.mastered),
        practicing=p.practicing,
        learner=learner_out(learner),
    )


@app.post("/api/learners", response_model=LearnerOut, status_code=201, dependencies=[Depends(create_limit)])
def create_learner(req: LearnerCreate) -> LearnerOut:
    profile = {
        "favorite_animal": req.favorite_animal,
        "favorite_food": req.favorite_food,
        "setting": req.setting,
        "gender": req.gender,
    }
    learner = new_learner(req.name_ne, req.name_en.strip(), profile, req.start)
    store.put_learner(learner)
    return learner_out(learner)


@app.delete("/api/learners/{learner_id}", status_code=204)
def delete_learner(learner_id: str) -> Response:
    """Remove a learner and everything stored about them (parent request / end of pilot)."""
    if not store.delete_learner(learner_id):
        raise HTTPException(404, "learner not found")
    return Response(status_code=204)


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
    limit = learner.settings.get("daily_minutes", 0)
    if limit and _used_today(learner) >= limit:
        # Parent's daily limit: a friendly stop, shown to the child as "see you tomorrow".
        raise HTTPException(403, "daily_limit")
    units = learner.units[req.language]
    # Too few readable words for any real story: letter practice instead (no model call).
    from athena.letters import MIN_STORY_WORDS, letter_cards
    from athena.lexicon import decodable_words

    if len(decodable_words(req.language, allowed(units))) < MIN_STORY_WORDS:
        return StoryOut(
            id="", learner_id=learner.id, language=req.language, theme="letters", title="", sentences=[],
            outcome="letters", units_used=[], attempts=[], total_latency_ms=0, image_status="failed",
            image_url=None, image_latency_ms=None, display=[], letters=letter_cards(req.language, units),
        )
    # Prepared while the child looked at their last result (see _prefetch_next)? Used when the
    # child did not pick a theme, or picked the prepared one.
    if (ready := _take_prefetched(learner, req.language, req.theme)):
        result, image_future = ready
    else:
        result, image_future = _compose(learner, req.language, req.theme)
    return story_out(_publish(learner, req.language, result, image_future))


PREFETCH_ENGINE = "adk"  # background stories: the ADK agent's better Nepali, its time hidden
PREFETCH_BUDGET_S = 45  # the child is on the result screen meanwhile


def _compose(learner: Learner, language: Language, theme: str | None = None, engine: str | None = None,
             budget_s: float = STORY_BUDGET_S):
    """Plan + generate + verify a story, with its picture started in parallel. Not stored yet."""
    units = learner.units[language]
    p = plan(
        language,
        allowed(units),
        learner.name[language],
        theme=theme,
        target_units=practice_targets(units)[:3] or None,  # practise what is being learned
        level=learner.level[language],
        personal=personal_themes(learner.profile.get("favorite_animal"), learner.profile.get("favorite_food")),
        setting=SETTINGS.get(learner.profile.get("setting", "")),
        child_gender=learner.profile.get("gender", "unspecified"),
    )
    # Image starts now from the theme; text is generated + verified meanwhile.
    image_future = _pool.submit(illustrator.illustrate, p.theme)
    return generate(p, budget_s=budget_s, engine=engine), image_future


def _publish(learner: Learner, language: Language, result, image_future) -> Story:
    """Store a composed story for this child, log it, attach its picture when ready."""
    story = store.add_story(learner.id, language, result)
    store.history.append(
        learner.id,
        {
            "type": "story",
            "story_id": story.id,
            "at": story.created_at,
            "lang": language,
            "title": result.title,
            "sentences": result.sentences,
            "theme": result.plan.theme,
            "level": result.plan.level,
            "outcome": result.outcome,
            "units_used": result.units_used,
            "attempts": [
                {"n": a.n, "ms": a.latency_ms, "violations": [[v.word, v.unit, v.reason] for v in a.violations]}
                for a in result.attempts
            ],
        },
    )

    def _done(fut) -> None:
        try:
            data, mime, _usage, ms = fut.result()
            image_id = media.save(data, mime)
            store.set_image(story.id, "ready", image_id, ms)
            store.history.append(learner.id, {"type": "image", "story_id": story.id, "image_id": image_id})
        except Exception:
            log.exception("illustration failed for story %s", story.id)
            store.set_image(story.id, "failed", None, None)

    image_future.add_done_callback(_done)
    _pool.submit(_prespeak, language, result.sentences)  # tapped words + "read to me" play instantly
    return story


def _prespeak(language: str, sentences: list[str]) -> None:
    """Synthesise the story's narration (sentences + word timings) and every word into the TTS
    cache, so "read to me" and word taps are instant (cheap; shared by all children)."""
    from athena.narration import narrate

    try:
        narrate(language, sentences)
    except Exception:  # noqa: BLE001 - built on demand instead
        log.warning("narration prebuild failed")
    for word in dict.fromkeys(tokens(language, " ".join(sentences))):
        try:
            tts.speak_word(language, word)
        except Exception:  # noqa: BLE001 - a tap will just synthesise it then
            log.warning("prespeak failed for %r", word)


# --- next story, prepared while the child looks at their result ---------------------

PREFETCH_TTL_S = 30 * 60
PREFETCH_WAIT_S = 5
_prefetch: dict[tuple[str, str], tuple[float, object]] = {}
_prefetch_lock = threading.Lock()


def _prefetch_next(learner: Learner, language: Language) -> None:
    """Called right after a reading updates mastery: compose the next story from the NEW state."""
    from athena.letters import MIN_STORY_WORDS
    from athena.lexicon import decodable_words

    if len(decodable_words(language, allowed(learner.units[language]))) < MIN_STORY_WORDS:
        return  # letter mode next: nothing to prepare
    key = (learner.id, language)
    with _prefetch_lock:
        if key in _prefetch:
            return
        _prefetch[key] = (
            time.time(),
            _pool.submit(_compose, learner, language, None, PREFETCH_ENGINE, PREFETCH_BUDGET_S),
        )


def _take_prefetched(learner: Learner, language: Language, theme: str | None = None):
    """The prepared story, if still valid for the child RIGHT NOW. The verifier re-checks it
    against current units and level: anything that changed since means compose afresh."""
    from athena.agents.planner import base_theme

    with _prefetch_lock:
        entry = _prefetch.get((learner.id, language))
        if entry and theme is not None:
            fut0 = entry[1]
            if not fut0.done() or fut0.exception() or base_theme(fut0.result()[0].plan.theme) != theme:
                return None  # child picked another story: keep the prepared one for later
        entry = _prefetch.pop((learner.id, language), None)
    if not entry:
        return None
    created, fut = entry
    if time.time() - created > PREFETCH_TTL_S:
        return None
    try:
        # Not ready yet: wait a little, then let the fast engine write a fresh story instead.
        result, image_future = fut.result(timeout=PREFETCH_WAIT_S)
    except Exception:  # noqa: BLE001 - compose afresh
        return None
    if result.plan.level != learner.level[language] or result.outcome == "wordlist":
        return None
    name = learner.name[language]
    names = frozenset(name.split()) | frozenset(name.lower().split())
    v = verifier_for(language, allowed(learner.units[language]), names)
    if not v.verify("\n".join([result.title, *result.sentences])).ok:
        log.info("prefetched story no longer readable for %s: discarded", learner.id)
        return None
    return result, image_future


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
    store.history.append(
        s.learner_id,
        {
            "type": "reading",
            "story_id": s.id,
            "at": time.time(),
            "transcript": t.text,  # what STT heard; the audio itself is never kept
            "engine": t.engine,
            "wcpm": a.wcpm,
            "words_correct": a.words_correct,
            "words": [w.__dict__ for w in a.words],
            "insertions": [i.__dict__ for i in a.insertions],
        },
    )

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


def _used_today(learner: Learner) -> int:
    """Reading + maths minutes today (the parent's limit covers both)."""
    from athena.dashboard import _same_day
    from athena.maths_progress import maths_seconds_today

    now = time.time()
    open_started = [s.created_at for s in store.stories.values() if s.learner_id == learner.id and s.changes is None]
    maths_s = maths_seconds_today(store.history.maths(learner.id), now, _same_day)
    return used_minutes_today(learner.sessions, open_started, now) + round(maths_s / 60)


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
    lang, units = s.language, learner.units[s.language]
    changes = apply_session(units, a.unit_correct, a.unit_errors)

    accuracy = a.words_correct / len(a.words) if a.words else 0.0
    history = learner.history[lang]
    history.append(accuracy)
    level_before = learner.level[lang]
    learner.level[lang] = next_level(level_before, history)

    # Ready for more? Introduce the unseen units that unlock the most words.
    if should_introduce(units, history):
        practicing = sum(u.state == "practicing" for u in units.values())
        for sig in next_units(lang, units, k=MAX_PRACTICING - practicing):
            units[sig] = UnitState("practicing", streak=0, seen=0)
            changes.append(Change(sig, "unseen", "practicing"))

    s.changes = changes
    learner.sessions.append(
        {
            "at": time.time(),
            "started": s.created_at,
            "lang": lang,
            "title": s.result.title,
            "accuracy": round(accuracy, 3),
            "wcpm": a.wcpm,
            "words": len(a.words),
            "changes": [[c.unit, c.before, c.after] for c in changes],
        }
    )
    store.save()
    store.history.append(
        learner.id,
        {
            "type": "close",
            "story_id": s.id,
            "at": time.time(),
            "accuracy": round(accuracy, 3),
            "level_before": level_before,
            "level_after": learner.level[lang],
            "changes": [[c.unit, c.before, c.after] for c in changes],
        },
    )
    _prefetch_next(learner, lang)  # next story is written while the child looks at this result
    return CloseOut(
        story_id=s.id,
        accuracy=round(accuracy, 2),
        level_before=level_before,
        level_after=learner.level[lang],
        changes=[ChangeOut(unit=c.unit, before=c.before, after=c.after) for c in changes],
        learner=learner_out(learner),
    )


# Fixed praise phrases (never free text to TTS). Child is addressed with the familiar
# तिमी forms (पढ्यौ), which is right for a child. Tier by accuracy of the reading.
PRAISE = {
    "ne": {"great": "धेरै राम्रो पढ्यौ!", "good": "राम्रो पढ्यौ! अझ अभ्यास गरौँ।", "try": "राम्रो प्रयास! सँगै फेरि पढौँ।"},
    "en": {"great": "Great reading!", "good": "Good reading! Let's practise a little more.", "try": "Good try! Let's read it together again."},
}


@app.get("/api/praise/{language}/{tier}")
def praise_audio(language: Language, tier: Literal["great", "good", "try"]) -> Response:
    """Spoken encouragement after a reading. Fixed phrases only; cached after first use."""
    return Response(tts.speak_word(language, PRAISE[language][tier]), media_type="audio/wav",
                    headers={"Cache-Control": "public, max-age=604800"})


class SettingsIn(BaseModel):
    daily_minutes: Literal[0, 10, 15, 20, 30]


class SummaryOut(BaseModel):
    days: int
    stories: int
    words_read: int
    mean_accuracy: float | None
    mean_wcpm: float | None
    mastered: list[str]
    introduced: list[str]
    struggling: list[str]
    per_day: list[int]


class DashboardOut(BaseModel):
    learner: LearnerOut
    week: dict[str, SummaryOut]  # per language
    used_today: int
    daily_minutes: int
    practicing: dict[str, list[str]]
    recent: list[dict]  # last sessions, newest first


@app.put("/api/learners/{learner_id}/settings", response_model=LearnerOut)
def set_settings(learner_id: str, req: SettingsIn) -> LearnerOut:
    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    learner.settings["daily_minutes"] = req.daily_minutes
    store.save()
    return learner_out(learner)


@app.get("/api/learners/{learner_id}/dashboard", response_model=DashboardOut)
def dashboard(learner_id: str) -> DashboardOut:
    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    now = time.time()
    return DashboardOut(
        learner=learner_out(learner),
        week={lang: SummaryOut(**summarize(learner.sessions, now, 7, lang).__dict__) for lang in ("ne", "en")},
        used_today=_used_today(learner),
        daily_minutes=learner.settings.get("daily_minutes", 0),
        practicing={lang: practice_targets(u) for lang, u in learner.units.items()},
        recent=list(reversed(learner.sessions[-8:])),
    )


class ActivitiesOut(BaseModel):
    language: Language
    practicing: list[str]
    practice_words: list[str]  # readable now, verified in code
    activities: list[dict]  # title_ne/en, how_ne/en, child_words (verified)


coach_limit = RateLimit(per_ip=10, global_=60)


@app.get("/api/learners/{learner_id}/activities/{language}", response_model=ActivitiesOut, dependencies=[Depends(coach_limit)])
def home_activities(learner_id: str, language: Language) -> ActivitiesOut:
    from athena.agents import coach
    from athena.profile import ANIMALS, FOODS

    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    units = learner.units[language]
    practicing = practice_targets(units) or [u for u, st in units.items() if st.state == "practicing"]
    pr = learner.profile
    interests = ", ".join(
        x for x in (ANIMALS.get(pr.get("favorite_animal", ""), ("",))[0], FOODS.get(pr.get("favorite_food", ""), ("",))[0]) if x
    ) or "animals and food"
    acts, words = coach.activities(learner.id, language, learner.name[language], allowed(units), practicing, interests)
    return ActivitiesOut(language=language, practicing=practicing, practice_words=words, activities=acts)


class HistoryItemOut(BaseModel):
    story_id: str
    at: float
    lang: Language
    title: str
    image_url: str | None
    read: bool
    accuracy: float | None


class HistoryStoryOut(BaseModel):
    story_id: str
    at: float
    lang: Language
    title: str
    theme: str
    level: int
    outcome: str
    sentences: list[str]
    display: list[list[DisplayWord]]
    image_url: str | None
    attempts: list[dict]
    readings: list[dict]  # each: transcript, wcpm, words (per-word outcomes), insertions
    close: dict | None
    reteach: list[dict]  # each retry from the re-teach card: word, ways used, read right or not


@app.get("/api/learners/{learner_id}/stories", response_model=list[HistoryItemOut])
def learner_stories(learner_id: str) -> list[HistoryItemOut]:
    """Every story this child got, newest first: the parent-reviewable log."""
    if not store.get_learner(learner_id):
        raise HTTPException(404, "learner not found")
    return [
        HistoryItemOut(
            story_id=r["story_id"],
            at=r["at"],
            lang=r["lang"],
            title=r.get("title", ""),
            image_url=f"/api/media/{r['image_id']}" if r.get("image_id") else None,
            read=bool(r["readings"]),
            accuracy=r["close"]["accuracy"] if r.get("close") else None,
        )
        for r in store.history.stories(learner_id)
    ]


@app.get("/api/learners/{learner_id}/stories/{story_id}", response_model=HistoryStoryOut)
def learner_story(learner_id: str, story_id: str) -> HistoryStoryOut:
    r = store.history.story(learner_id, story_id)
    if not r:
        raise HTTPException(404, "story not found")
    return HistoryStoryOut(
        story_id=r["story_id"],
        at=r["at"],
        lang=r["lang"],
        title=r.get("title", ""),
        theme=r.get("theme", ""),
        level=r.get("level", 1),
        outcome=r.get("outcome", ""),
        sentences=r.get("sentences", []),
        display=display_words(r["lang"], r.get("sentences", [])),
        image_url=f"/api/media/{r['image_id']}" if r.get("image_id") else None,
        attempts=r.get("attempts", []),
        readings=r["readings"],
        close=r.get("close"),
        reteach=r.get("reteach", []),
    )


letters_limit = RateLimit(per_ip=40, global_=200)


class LetterCheckIn(BaseModel):
    language: Language
    results: dict[str, bool]  # unit -> said it (adult marks, like the card check)


@app.post("/api/learners/{learner_id}/letters/close", response_model=CloseOut)
def close_letters(learner_id: str, req: LetterCheckIn) -> CloseOut:
    """Letter-mode session: the same mastery rule as a story reading, so pre-readers progress
    into stories. A letter not yet said counts as one error (resets the streak, no demotion)."""
    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    lang, units = req.language, learner.units[req.language]
    if not req.results or any(not re.fullmatch(r"[cmkgw]:[^\s/]{1,8}", u) for u in req.results):
        raise HTTPException(400, "results must be unit signatures")
    correct = {u: 1 for u, ok in req.results.items() if ok}
    errors = {u: 1 for u, ok in req.results.items() if not ok}
    changes = apply_session(units, correct, errors)
    accuracy = len(correct) / len(req.results)
    learner.history[lang].append(accuracy)
    if should_introduce(units, learner.history[lang]):
        practicing = sum(u.state == "practicing" for u in units.values())
        for sig in next_units(lang, units, k=MAX_PRACTICING - practicing):
            units[sig] = UnitState("practicing", streak=0, seen=0)
            changes.append(Change(sig, "unseen", "practicing"))
    _prefetch_next(learner, lang)  # if this session crossed into stories, the first one is ready
    learner.sessions.append(
        {"at": time.time(), "started": time.time() - 60, "lang": lang, "title": "letters", "accuracy": round(accuracy, 3),
         "wcpm": 0.0, "words": 0, "changes": [[c.unit, c.before, c.after] for c in changes]}
    )
    store.save()
    return CloseOut(
        story_id="", accuracy=round(accuracy, 2), level_before=learner.level[lang], level_after=learner.level[lang],
        changes=[ChangeOut(unit=c.unit, before=c.before, after=c.after) for c in changes], learner=learner_out(learner),
    )


@app.get("/api/letters/{language}/{unit}/audio", dependencies=[Depends(letters_limit)])
def letter_audio(language: Language, unit: str) -> Response:
    """Speak the example word for a letter card. The text comes from the server's own
    example list for a valid unit, never from the client."""
    from athena.letters import example_word

    if not re.fullmatch(r"[cmkgw]:[^\s/]{1,8}", unit):
        raise HTTPException(404, "unknown unit")
    word = example_word(language, unit)
    if not word:
        raise HTTPException(404, "no example for this unit")
    return Response(tts.speak_word(language, word), media_type="audio/wav", headers={"Cache-Control": "public, max-age=604800"})


class GroupOut(BaseModel):
    name: str
    total: int
    mastered: int
    practicing: list[str]
    status: str


class PatternOut(BaseModel):
    kind: str
    count: int
    examples: list[list[str]]
    label_en: str
    label_ne: str


class PaceOut(BaseModel):
    sessions_14d: int
    mastered_14d: int
    wcpm_first: float | None
    wcpm_last: float | None
    trend: str


class InsightsOut(BaseModel):
    language: Language
    groups: list[GroupOut]
    patterns: list[PatternOut]
    pace: PaceOut
    helps_most: dict | None = None  # {"style", "worked", "tries"}: re-teach way that works best


def _insights(learner: Learner, language: Language) -> InsightsOut:
    from athena.insights import error_patterns, pace, skill_groups
    from athena.reteach import best_style

    readings = [r for st in store.history.stories(learner.id) if st["lang"] == language for r in st["readings"]]
    return InsightsOut(
        language=language,
        groups=[GroupOut(**g.__dict__) for g in skill_groups(language, learner.units[language])],
        patterns=[PatternOut(**{**p.__dict__, "examples": [list(e) for e in p.examples]}) for p in error_patterns(language, readings)],
        pace=PaceOut(**pace(language, learner.sessions, time.time()).__dict__),
        helps_most=best_style(_reteach_events(learner.id, language)),
    )


@app.get("/api/learners/{learner_id}/insights/{language}", response_model=InsightsOut)
def learner_insights(learner_id: str, language: Language) -> InsightsOut:
    """Strengths and gaps by skill group, error patterns, pace: computed in code."""
    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    return _insights(learner, language)


@app.get("/api/learners/{learner_id}/summary/{language}", dependencies=[Depends(coach_limit)])
def learner_summary(learner_id: str, language: Language) -> dict:
    """A short parent note (ne + en). The model phrases the computed facts; it adds nothing."""
    from athena.agents import coach

    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    ins = _insights(learner, language)
    facts = {
        "strong": [g.name for g in ins.groups if g.status == "strong"],
        "learning": [{"group": g.name, "practising": g.practicing} for g in ins.groups if g.status == "learning"],
        "not_started": [g.name for g in ins.groups if g.status == "not_started"],
        "mistake_patterns": [{"what": p.label_en, "times": p.count} for p in ins.patterns],
        "last_14_days": ins.pace.model_dump(),
    }
    version = len([x for x in learner.sessions if x["lang"] == language])
    return coach.summary(learner.id, language, learner.name[language], facts, version)


class NarrationWord(BaseModel):
    index: int
    start: float
    end: float


class NarrationSentence(BaseModel):
    text: str
    audio_url: str
    words: list[NarrationWord]


narrate_limit = RateLimit(per_ip=20, global_=100)


@app.get("/api/stories/{story_id}/narration", response_model=list[NarrationSentence], dependencies=[Depends(narrate_limit)])
def story_narration(story_id: str) -> list[NarrationSentence]:
    """"Read to me": the story read aloud per sentence, with word timings for karaoke."""
    from athena.narration import narrate

    s = store.get_story(story_id)
    if not s:
        raise HTTPException(404, "story not found")
    try:
        parts = narrate(s.language, s.result.sentences)
    except Exception:  # noqa: BLE001
        log.exception("narration failed")
        raise HTTPException(503, "reading aloud is not available right now") from None
    return [
        NarrationSentence(text=p["text"], audio_url=f"/api/narration/{p['audio_key']}", words=p["words"]) for p in parts
    ]


@app.get("/api/narration/{key}")
def narration_audio(key: str) -> Response:
    from athena.narration import audio_path

    if not re.fullmatch(r"[0-9a-f]{24}", key):
        raise HTTPException(404, "not found")
    path = audio_path(key)
    if not path:
        raise HTTPException(404, "not found")
    return Response(path.read_bytes(), media_type="audio/wav", headers={"Cache-Control": "public, max-age=604800, immutable"})


class ChoiceOut(BaseModel):
    theme: str
    label_ne: str
    label_en: str
    picture_url: str
    ready: bool  # the prepared next story: picking it is instant


@app.get("/api/learners/{learner_id}/choices/{language}", response_model=list[ChoiceOut])
def story_choices(learner_id: str, language: Language) -> list[ChoiceOut]:
    """Three stories the child can pick from, all readable for them. The prepared next story
    (if any) is always one of them. Empty in letter mode."""
    import random as _random

    from athena.agents.planner import base_theme, readable_themes, tile_for
    from athena.letters import MIN_STORY_WORDS
    from athena.lexicon import decodable_words

    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    units = allowed(learner.units[language])
    if len(decodable_words(language, units)) < MIN_STORY_WORDS:
        return []
    personal = personal_themes(learner.profile.get("favorite_animal"), learner.profile.get("favorite_food"))
    themes = readable_themes(language, units, personal)
    ready_text = None
    entry = _prefetch.get((learner.id, language))
    if entry and entry[1].done() and not entry[1].exception():
        ready_text = base_theme(entry[1].result()[0].plan.theme)
    first = [t for t in themes if t.text == ready_text]
    rest = [t for t in themes if t.text != ready_text]
    rng = _random.Random()
    personal_rest = [t for t in rest if t in personal]
    others = [t for t in rest if t not in personal]
    rng.shuffle(personal_rest)
    rng.shuffle(others)
    picked = (first + personal_rest[:1] + others)[:3]  # ready one, a favourite, then variety
    out = []
    for t in picked:
        ne, en, noun = tile_for(t)
        out.append(ChoiceOut(theme=t.text, label_ne=ne, label_en=en, picture_url=f"/api/pictures/ne/{noun}", ready=t.text == ready_text))
    return out


# --- maths: word problems the child can read; code picks numbers and checks answers ------

class MathsStart(BaseModel):
    learner_id: str
    language: Language


class MathsOut(BaseModel):
    id: str
    language: Language
    sentences: list[str]
    display: list[list[DisplayWord]]
    a: int
    b: int
    op: str
    picture_url: str | None  # what is counted, shown as a groups of pictures
    choices: list[int]  # answer tiles (the answer is among them; the server keeps which)
    source: str


class MathsAnswer(BaseModel):
    answer: int = Field(ge=0, le=100)


class MathsResult(BaseModel):
    correct: bool
    tries: int
    answer: int | None  # revealed when found, or after 2 tries ("let's count together")
    level_change: Literal["up", "down"] | None = None  # maths level moved after this problem


_maths: dict[str, dict] = {}  # open problems; rebuilt from history after a restart
_maths_lock = threading.Lock()
MATHS_KEEP_S = 2 * 3600  # open problems older than this are dropped from memory
maths_limit = RateLimit(per_ip=10, global_=60)


_maths_next: dict[tuple[str, str], tuple[int, object]] = {}  # (learner, lang) -> (level, Future[Problem])


def _maths_level(learner: Learner, language: Language) -> int:
    return learner.maths.setdefault(language, {"level": 1, "recent": []})["level"]


def _maths_plan(learner: Learner, language: Language):
    units = learner.units[language]
    return plan(language, allowed(units), learner.name[language], level=_maths_level(learner, language),
                child_gender=learner.profile.get("gender", "unspecified"))


def _maths_get(pid: str) -> dict | None:
    """An open problem: from memory, else rebuilt from the learner's history (Cloud Run may
    have restarted or scaled to zero since it was shown). The pid carries the learner id."""
    from athena.maths import Problem

    if m := _maths.get(pid):
        return m
    learner_id = pid.rsplit("-", 1)[0]
    if "-" not in pid or not store.get_learner(learner_id):
        return None
    r = next((r for r in store.history.maths(learner_id) if r["id"] == pid), None)
    if not r:
        return None
    prob = Problem(r["lang"], r["a"], r["b"], r["op"], noun="", sentences=r["sentences"], source=r["source"])
    m = {"learner": learner_id, "problem": prob, "tries": len(r["answers"]), "solved": r["solved"], "at": r["at"]}
    with _maths_lock:
        _maths[pid] = m
    return m


@app.post("/api/maths/start", response_model=MathsOut, dependencies=[Depends(maths_limit)])
def maths_start(req: MathsStart) -> MathsOut:
    """A problem now: the one prepared in the background if ready, else an instant code-built
    one. Then the next model-written problem is prepared while the child solves this one."""
    import random as _random
    import uuid as _uuid

    from athena.maths import make_problem, picture_noun, quick_problem

    learner = store.get_learner(req.learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    limit = learner.settings.get("daily_minutes", 0)
    if limit and _used_today(learner) >= limit:
        raise HTTPException(403, "daily_limit")  # same friendly stop as stories
    key, level = (learner.id, req.language), _maths_level(learner, req.language)
    prob = None
    entry = _maths_next.pop(key, None)
    if entry and entry[0] == level and entry[1].done() and not entry[1].exception():
        prob = entry[1].result()
    if prob is None:
        prob = quick_problem(_maths_plan(learner, req.language)) or make_problem(_maths_plan(learner, req.language))
    _maths_next[key] = (level, _pool.submit(make_problem, _maths_plan(learner, req.language)))

    pid = f"{learner.id}-{_uuid.uuid4().hex[:12]}"
    rng = _random.Random()
    choices = {prob.answer}
    while len(choices) < 4:
        choices.add(max(0, prob.answer + rng.choice([-2, -1, 1, 2, 3])))
    now = time.time()
    with _maths_lock:
        for old in [k for k, v in _maths.items() if now - v["at"] > MATHS_KEEP_S]:
            del _maths[old]
        _maths[pid] = {"learner": learner.id, "problem": prob, "tries": 0, "solved": False, "at": now}
    store.history.append(learner.id, {"type": "maths", "story_id": pid, "at": now, "lang": req.language,
                                      "sentences": prob.sentences, "a": prob.a, "b": prob.b, "op": prob.op,
                                      "source": prob.source, "level": level})
    noun = picture_noun(req.language, prob.noun)
    return MathsOut(
        id=pid, language=req.language, sentences=prob.sentences, display=display_words(req.language, prob.sentences),
        a=prob.a, b=prob.b, op=prob.op, picture_url=f"/api/pictures/ne/{noun}" if noun else None,
        choices=sorted(choices), source=prob.source,
    )


@app.post("/api/maths/{pid}/answer", response_model=MathsResult)
def maths_answer(pid: str, req: MathsAnswer) -> MathsResult:
    from athena.maths_progress import next_maths_level

    m = _maths_get(pid)
    if not m:
        raise HTTPException(404, "problem not found")
    m["tries"] += 1
    correct = req.answer == m["problem"].answer  # code decides
    if correct:
        m["solved"] = True
    store.history.append(m["learner"], {"type": "maths_answer", "story_id": pid, "at": time.time(),
                                        "answer": req.answer, "correct": correct, "try": m["tries"]})
    change = None
    learner = store.get_learner(m["learner"])
    if learner and m["tries"] == 1:  # the level follows first tries only
        lang = m["problem"].language
        state = learner.maths.setdefault(lang, {"level": 1, "recent": []})
        state["recent"] = (state["recent"] + [correct])[-10:]
        new = next_maths_level(state["level"], state["recent"])
        if new != state["level"]:
            change = "up" if new > state["level"] else "down"
            state["level"], state["recent"] = new, []
            _maths_next.pop((learner.id, lang), None)  # prepared at the old level
        store.save()
    reveal = correct or m["tries"] >= 2
    return MathsResult(correct=correct, tries=m["tries"], answer=m["problem"].answer if reveal else None,
                       level_change=change)


@app.get("/api/maths/{pid}/audio", dependencies=[Depends(narrate_limit)])
def maths_audio(pid: str) -> Response:
    """The problem read aloud (its own text only; cached)."""
    m = _maths_get(pid)
    if not m:
        raise HTTPException(404, "problem not found")
    prob = m["problem"]
    return Response(tts.speak_word(prob.language, " ".join(prob.sentences)), media_type="audio/wav",
                    headers={"Cache-Control": "public, max-age=86400"})


class MathsWeekOut(BaseModel):
    problems: int
    answered: int
    solved: int
    first_try: float | None
    per_day: list[int]


class MathsOpOut(BaseModel):
    problems: int
    first_try: float | None


class MathsProblemOut(BaseModel):
    id: str
    at: float
    sentences: list[str]
    a: int
    b: int
    op: str
    answer: int
    answers: list[int]  # what the child tapped, in order
    solved: bool
    first_try: bool


class MathsProgressOut(BaseModel):
    lang: Language
    level: int  # maths level 1-3 (athena.maths.LEVELS)
    total: int
    week: MathsWeekOut
    all_first_try: float | None
    by_op: dict[str, MathsOpOut]  # "+" / "-"
    struggling: list[str]  # ops with a low first-try rate
    mistakes: dict[str, int]  # off_by_one, wrong_operation
    largest_solved: int | None
    recent: list[MathsProblemOut]


@app.get("/api/learners/{learner_id}/maths/{language}", response_model=MathsProgressOut)
def learner_maths(learner_id: str, language: Language) -> MathsProgressOut:
    """Maths progress for the parent and teacher views. Computed from the child's taps."""
    from athena.maths_progress import summarize_maths

    learner = store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "learner not found")
    return MathsProgressOut(**summarize_maths(store.history.maths(learner_id), language, time.time(),
                                              level=_maths_level(learner, language)))


class PartOut(BaseModel):
    text: str
    units: list[str]
    tricky: bool  # behind this child's error in the latest reading


class WordHelpOut(BaseModel):
    index: int
    word: str
    picture_url: str | None  # concrete nouns only; stable per word
    outcome: str | None
    heard: str | None
    parts: list[PartOut]
    styles: list[str]  # ways to re-teach, best first for this child (athena/reteach.py)


class RetryOut(BaseModel):
    correct: bool
    heard: str


tts_limit = RateLimit(per_ip=40, global_=200)


def _story_word(story_id: str, index: int) -> tuple[Story, str]:
    s = store.get_story(story_id)
    if not s:
        raise HTTPException(404, "story not found")
    words = tokens(s.language, " ".join(s.result.sentences))
    if not 0 <= index < len(words):
        raise HTTPException(404, "no such word")
    return s, words[index]


@app.get("/api/stories/{story_id}/words/{index}", response_model=WordHelpOut)
def word_help(story_id: str, index: int) -> WordHelpOut:
    """Re-teach view of one word: its parts, with the ones behind the child's error marked."""
    s, word = _story_word(story_id, index)
    result = next((w for w in s.readings[-1].words if w.index == index), None) if s.readings else None
    wrong = set(result.error_units) if result else set()
    from athena.agents.picture import concrete_noun

    from athena.reteach import style_order

    noun = concrete_noun(s.language, word)
    return WordHelpOut(
        index=index,
        word=word,
        picture_url=f"/api/pictures/{s.language}/{noun}" if noun else None,
        outcome=result.outcome if result else None,
        heard=result.heard if result else None,
        parts=[PartOut(text=p.text, units=list(p.units), tricky=bool(wrong & set(p.units))) for p in word_parts(s.language, word)],
        styles=style_order(_reteach_events(s.learner_id, s.language), has_picture=bool(noun)),
    )


def _reteach_events(learner_id: str, language: str) -> list[dict]:
    return [e for st in store.history.stories(learner_id) if st["lang"] == language for e in st.get("reteach", [])]


@app.get("/api/stories/{story_id}/words/{index}/audio", dependencies=[Depends(tts_limit)])
def word_audio(story_id: str, index: int) -> Response:
    """Speak one word of a story. Only story words: never arbitrary text (no open TTS proxy)."""
    s, word = _story_word(story_id, index)
    return Response(tts.speak_word(s.language, word), media_type="audio/wav", headers={"Cache-Control": "public, max-age=86400"})


picture_limit = RateLimit(per_ip=20, global_=100)


@app.get("/api/pictures/{language}/{noun}", dependencies=[Depends(picture_limit)])
def noun_picture(language: Language, noun: str) -> Response:
    """Picture cue for a concrete noun. One stable URL per word, so browsers and the disk
    cache share it across every story and child. Only whitelisted nouns: never an open
    image generator."""
    from athena.agents.picture import concrete_noun, picture

    base = concrete_noun(language, noun)
    if base != noun:
        raise HTTPException(404, "no picture for this word")
    try:
        data, mime = picture(language, noun)
    except Exception:  # noqa: BLE001 - quota/model error: the help card just shows no picture
        log.warning("picture unavailable for %s", noun)
        raise HTTPException(503, "picture not available right now") from None
    return Response(data, media_type=mime, headers={"Cache-Control": "public, max-age=2592000, immutable"})


@app.post("/api/stories/{story_id}/words/{index}/read", response_model=RetryOut, dependencies=[Depends(read_limit)])
def word_retry(story_id: str, index: int, audio: UploadFile = File(...), styles: str = Form("")) -> RetryOut:
    """Try one word again. Practice only: mastery is not changed. No STT hint (a hint would
    pull the transcript toward the expected word and hide a repeat mistake). Audio not kept.
    styles: the re-teach ways used before this try, in order ("hear,parts"): logged so the
    card learns which way works for this child."""
    from athena.reteach import STYLES

    s, word = _story_word(story_id, index)
    used = [x for x in styles.split(",") if x in STYLES][:10]
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(400, "bad recording")
    t = stt.transcribe(s.language, data, audio.content_type or "audio/webm", [word], hints=False)
    del data
    heard = tokens(s.language, t.text)
    correct = any(fold(s.language, h) == fold(s.language, word) for h in heard)
    store.history.append(s.learner_id, {"type": "reteach", "story_id": s.id, "at": time.time(), "index": index,
                                        "word": word, "styles": used, "correct": correct})
    return RetryOut(correct=correct, heard=t.text)


live_limit = RateLimit(per_ip=12, global_=60)


@app.websocket("/api/stories/{story_id}/live")
async def live_follow(ws: WebSocket, story_id: str) -> None:
    """Live follow-along while the child reads: the browser streams 16 kHz PCM, we stream it
    to speech-to-text and send back which story words were heard and which is next.
    A visual guide only; the reading is still scored from the full recording. Audio is not kept."""
    from athena.assess.live import LiveTracker
    from athena.assess.stream import StreamSession

    s = store.get_story(story_id)
    if not s:
        await ws.close(code=4404)
        return
    try:
        live_limit(ws)  # same per-IP / global caps as other model endpoints
    except HTTPException:
        await ws.close(code=4429)
        return
    await ws.accept()
    tracker = LiveTracker(s.language, " ".join(s.result.sentences))
    loop = asyncio.get_running_loop()
    out: asyncio.Queue = asyncio.Queue()
    session = StreamSession(
        s.language,
        on_text=lambda text: loop.call_soon_threadsafe(out.put_nowait, ("text", text)),
        on_done=lambda err: loop.call_soon_threadsafe(out.put_nowait, ("done", err)),
        phrases=sorted(set(tokens(s.language, " ".join(s.result.sentences)))),
    )
    session.start()

    async def send_updates() -> None:
        last = None
        while True:
            kind, value = await out.get()
            if kind == "done":
                await ws.send_json({"done": True, "error": value})
                return
            heard, nxt = tracker.update(value)
            if (heard, nxt) != last:
                last = (heard, nxt)
                await ws.send_json({"heard": heard, "next": nxt, "text": value})

    sender = asyncio.create_task(send_updates())
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes"):
                if not session.feed(msg["bytes"]):
                    break  # audio cap reached
            elif msg.get("text") == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        session.close()
        try:
            await asyncio.wait_for(sender, timeout=5)
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            sender.cancel()
        try:
            await ws.close()
        except Exception:  # noqa: BLE001 - already closed
            pass


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
