"""Constrained generation: writer proposes, verifier decides, up to MAX_ATTEMPTS.

Fallbacks are themselves verified, so final_violation_count is always 0:
  pruned    keep the sentences of the last draft that pass (>= 2)
  template  surviving sentences topped up with template sentences (Nepali)
  wordlist  nothing else fits: a decodable word list for practice (last resort)
"""

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path

from athena.agents import adk_writer, writer
from athena.config import settings
from athena import safety
from athena.fallback import template_story
from athena.lexicon import decodable_words, verifier_for
from athena.models import Attempt, GenerationResult, StoryDraft, StoryPlan, ViolationOut
from athena.progression import LEVELS
from athena.verifier.shape import check_shape

MAX_ATTEMPTS = 3
MIN_PRUNED_SENTENCES = 2
LOG = Path(__file__).resolve().parent.parent / "logs" / "generation.jsonl"
# The HTTP timeout only fires on a silent connection; a slow call can run past it
# (seen: 31.6s against a 20s budget). The budget is enforced here instead: the call
# runs on a worker and is abandoned at the deadline (its thread finishes on its own).
_calls = ThreadPoolExecutor(max_workers=8, thread_name_prefix="writer")


def _violations(result) -> list[ViolationOut]:
    return [ViolationOut(word=v.word, word_index=v.word_index, unit=v.unit, reason=v.reason) for v in result.violations]


MIN_CALL_MS = 5_000


def generate(
    plan: StoryPlan,
    log: bool = True,
    budget_s: float | None = None,
    check_safety: bool = True,
    engine: str | None = None,
) -> GenerationResult:
    """budget_s: total time for model attempts. Past it, go straight to the verified fallback."""
    t0 = time.perf_counter()
    mastery = frozenset(plan.mastery)
    names = frozenset(plan.learner_name.split()) | frozenset(plan.learner_name.lower().split())
    verifier = verifier_for(plan.language, mastery, names)
    limits = LEVELS[plan.level]

    def shape_ok(sentences: list[str]) -> bool:
        return not check_shape(plan.language, sentences, limits, names)

    attempts: list[Attempt] = []
    banned: dict[str, ViolationOut] = {}  # cumulative, so later drafts don't reintroduce old mistakes
    draft = None
    outcome = None

    def code_check(title: str, sentences: list[str]) -> list[ViolationOut]:
        """The same gate for both engines: letters the child can read + story shape."""
        result = verifier.verify("\n".join([title, *sentences]))
        shape = check_shape(plan.language, [title, *sentences], limits, names)
        return _violations(result) + [
            ViolationOut(word=v.word, word_index=v.word_index, unit=None, reason=v.reason) for v in shape
        ]

    engine = engine or settings().writer_engine
    if engine == "adk":
        # ADK agent: drafts, calls the verifier tool, code ends the turn on acceptance.
        checks: list[dict] = []  # filled live, so drafts made before a timeout are kept for pruning
        try:
            fut = _calls.submit(adk_writer.write_with_tool, plan, code_check, checks)
            accepted, checks, usage, latency = fut.result(timeout=budget_s)
        except Exception as e:  # noqa: BLE001 - timeout / model error: verified fallback below
            accepted, usage, latency = None, writer.Usage(), int((time.perf_counter() - t0) * 1000)
            checks = list(checks)
            stopped = Attempt(n=len(checks) + 1, prompt="adk", title="", sentences=[], latency_ms=0, usage=usage,
                              violations=[ViolationOut(word="", word_index=-1, unit=None, reason=f"agent: {type(e).__name__}")])
        else:
            stopped = None
        per = latency // max(1, len(checks))
        for i, c in enumerate(checks, 1):
            attempts.append(Attempt(n=i, prompt="adk:verify_story", title=c["title"], sentences=c["sentences"],
                                    violations=c["violations"], latency_ms=per,
                                    usage=usage if i == 1 else writer.Usage(model=usage.model)))
        if stopped:
            if not checks:
                stopped.latency_ms = latency
            attempts.append(stopped)
        if checks:
            last = checks[-1]
            draft = accepted or StoryDraft(title=last["title"], sentences=last["sentences"], scene=plan.theme)
        if accepted:
            final_check = verifier.verify("\n".join([accepted.title, *accepted.sentences]))
            outcome = "first_pass" if len(checks) == 1 else "regenerated"
            title, sentences, units = accepted.title, accepted.sentences, final_check.units_used

    for n in range(1, MAX_ATTEMPTS + 1):
        if engine == "adk":
            break  # the agent made its own attempts
        timeout_ms = None
        if budget_s is not None:
            remaining_ms = int((budget_s - (time.perf_counter() - t0)) * 1000)
            if remaining_ms < MIN_CALL_MS:
                break  # out of time: verified fallback below
            timeout_ms = remaining_ms
        try:
            fut = _calls.submit(writer.write, plan, list(banned.values()) or None, timeout_ms)
            try:
                draft, prompt, usage, latency = fut.result(timeout=timeout_ms / 1000 if timeout_ms else None)
            except FutureTimeout:
                raise writer.WriterFailed(
                    "time budget exceeded", writer.build_prompt(plan), writer.Usage(), timeout_ms or 0
                ) from None
        except writer.WriterFailed as e:
            # No usable draft (truncated JSON, model error): a failed attempt, not a crash.
            attempts.append(
                Attempt(
                    n=n,
                    prompt=e.prompt,
                    title="",
                    sentences=[],
                    violations=[ViolationOut(word="", word_index=-1, unit=None, reason=e.reason)],
                    latency_ms=e.latency_ms,
                    usage=e.usage,
                )
            )
            continue
        draft.sentences = draft.sentences[: limits.sentences[1]]  # too many sentences: keep the first
        # The child reads the title too, so it is verified with the story.
        result = verifier.verify("\n".join([draft.title, *draft.sentences]))
        # Shape (word length, words per sentence) is enforced like letters: fed back, never shipped.
        shape = check_shape(plan.language, [draft.title, *draft.sentences], limits, names)
        violations = _violations(result) + [
            ViolationOut(word=v.word, word_index=v.word_index, unit=None, reason=v.reason) for v in shape
        ]
        for v in violations:
            banned.setdefault(v.word, v)
        attempts.append(
            Attempt(
                n=n,
                prompt=prompt,
                title=draft.title,
                sentences=draft.sentences,
                violations=violations,
                latency_ms=latency,
                usage=usage,
            )
        )
        if result.ok and not shape:
            outcome = "first_pass" if n == 1 else "regenerated"
            title, sentences, units = draft.title, draft.sentences, result.units_used
            break

    if outcome is None:
        # draft is the last usable one, or None if every attempt failed outright
        kept = [s for s in draft.sentences if verifier.verify(s).ok and shape_ok([s])] if draft else []
        title = draft.title if draft and verifier.verify(draft.title).ok and shape_ok([draft.title]) else plan.learner_name
        if len(kept) >= MIN_PRUNED_SENTENCES:
            outcome, sentences = "pruned", kept
        else:
            readable = decodable_words(plan.language, mastery)
            t_title, extra = template_story(plan.language, verifier, readable, plan.key_words, random.Random(), plan.learner_name)
            extra = [x for x in extra if x not in kept and shape_ok([x])]
            if t_title and not shape_ok([t_title]):
                t_title = ""
            if len(kept) + len(extra) >= MIN_PRUNED_SENTENCES:
                outcome, sentences = "template", (kept + extra)[: limits.sentences[1]]
                if title == plan.learner_name and t_title:
                    title = t_title
            else:
                short = [w for w in plan.word_bank if shape_ok([w])]
                outcome, sentences = "wordlist", [" ".join(short[:12])]
        units = verifier.verify("\n".join([title, *sentences])).units_used

    final = verifier.verify("\n".join([title, *sentences]))
    assert final.ok, f"verifier guarantee broken: {final.violations}"  # never ship a violation
    if outcome != "wordlist":  # a word list is not sentences; its words were length-filtered above
        assert shape_ok([title, *sentences]), "shape limits broken"

    # Safety before display (PLAN §11). Model-written text gets blocklist + model screen;
    # curated templates and word lists get the blocklist. Unsafe -> curated template.
    safety_info: dict = {}
    if check_safety:
        ts = time.perf_counter()
        verdict = safety.check(plan.language, title, sentences, model=outcome in ("first_pass", "regenerated", "pruned"))
        replaced = False
        if not verdict.safe:
            readable = decodable_words(plan.language, mastery)
            t_title, extra = template_story(plan.language, verifier, readable, plan.key_words, random.Random(1), plan.learner_name)
            extra = [x for x in extra if shape_ok([x])][: limits.sentences[1]]
            if len(extra) >= MIN_PRUNED_SENTENCES and safety.check(plan.language, t_title, extra, model=False).safe:
                title, sentences, outcome = (t_title if shape_ok([t_title]) else plan.learner_name), extra, "template"
            else:
                short = [w for w in plan.word_bank if shape_ok([w]) and not safety.blocklisted(plan.language, [w])]
                title, sentences, outcome = plan.learner_name, [" ".join(short[:12])], "wordlist"
            final = verifier.verify("\n".join([title, *sentences]))
            assert final.ok, "replacement broke the verifier guarantee"
            units = final.units_used
            replaced = True
        safety_info = {
            "safe": verdict.safe,
            "stage": verdict.stage,
            "reason": verdict.reason,
            "ms": int((time.perf_counter() - ts) * 1000),
            "replaced": replaced,
        }

    res = GenerationResult(
        plan=plan,
        attempts=attempts,
        outcome=outcome,
        title=title,
        sentences=sentences,
        scene=draft.scene if draft else plan.theme,
        units_used=sorted(units),
        first_pass_violations=len(attempts[0].violations) if attempts else 0,
        final_violation_count=len(final.violations),
        total_latency_ms=int((time.perf_counter() - t0) * 1000),
        safety=safety_info,
    )
    if log:
        LOG.parent.mkdir(exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(res.model_dump_json() + "\n")
    return res


def summary(res: GenerationResult) -> str:
    lines = [f"[{res.plan.language}] theme: {res.plan.theme}  focus: {' '.join(res.plan.target_units)}"]
    for a in res.attempts:
        bad = ", ".join(f"{v.word}({v.unit or v.reason})" for v in a.violations[:8])
        more = f" +{len(a.violations) - 8}" if len(a.violations) > 8 else ""
        lines.append(
            f"  attempt {a.n}: {len(a.violations)} violations  {a.latency_ms}ms  "
            f"think={a.usage.thinking_tokens}  {bad}{more}"
        )
    lines.append(f"  outcome: {res.outcome}  final violations: {res.final_violation_count}  total {res.total_latency_ms}ms")
    lines.append(f"  « {res.title} »")
    lines += [f"    {s}" for s in res.sentences]
    lines.append(f"  scene: {res.scene}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps({"log": str(LOG)}))
