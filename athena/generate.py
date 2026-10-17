"""Constrained generation: writer proposes, verifier decides, up to MAX_ATTEMPTS.

Fallbacks are themselves verified, so final_violation_count is always 0:
  pruned    keep only the sentences of the last draft that pass
  wordlist  no sentence survives: a decodable word list for practice
"""

import json
import time
from pathlib import Path

from athena.agents import writer
from athena.lexicon import verifier_for
from athena.models import Attempt, GenerationResult, StoryPlan, ViolationOut

MAX_ATTEMPTS = 3
MIN_PRUNED_SENTENCES = 2
LOG = Path(__file__).resolve().parent.parent / "logs" / "generation.jsonl"


def _violations(result) -> list[ViolationOut]:
    return [ViolationOut(word=v.word, word_index=v.word_index, unit=v.unit, reason=v.reason) for v in result.violations]


MIN_CALL_MS = 5_000


def generate(plan: StoryPlan, log: bool = True, budget_s: float | None = None) -> GenerationResult:
    """budget_s: total time for model attempts. Past it, go straight to the verified fallback."""
    t0 = time.perf_counter()
    mastery = frozenset(plan.mastery)
    names = frozenset(plan.learner_name.split()) | frozenset(plan.learner_name.lower().split())
    verifier = verifier_for(plan.language, mastery, names)

    attempts: list[Attempt] = []
    banned: dict[str, ViolationOut] = {}  # cumulative, so later drafts don't reintroduce old mistakes
    draft = None
    outcome = None

    for n in range(1, MAX_ATTEMPTS + 1):
        timeout_ms = None
        if budget_s is not None:
            remaining_ms = int((budget_s - (time.perf_counter() - t0)) * 1000)
            if remaining_ms < MIN_CALL_MS:
                break  # out of time: verified fallback below
            timeout_ms = remaining_ms
        try:
            draft, prompt, usage, latency = writer.write(plan, list(banned.values()) or None, timeout_ms)
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
        # The child reads the title too, so it is verified with the story.
        result = verifier.verify("\n".join([draft.title, *draft.sentences]))
        violations = _violations(result)
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
        if result.ok:
            outcome = "first_pass" if n == 1 else "regenerated"
            title, sentences, units = draft.title, draft.sentences, result.units_used
            break

    if outcome is None:
        # draft is the last usable one, or None if every attempt failed outright
        kept = [s for s in draft.sentences if verifier.verify(s).ok] if draft else []
        title = draft.title if draft and verifier.verify(draft.title).ok else plan.learner_name
        if len(kept) >= MIN_PRUNED_SENTENCES:
            outcome, sentences = "pruned", kept
        else:
            outcome, sentences = "wordlist", [" ".join(plan.word_bank[:12])]
        units = verifier.verify("\n".join([title, *sentences])).units_used

    final = verifier.verify("\n".join([title, *sentences]))
    assert final.ok, f"verifier guarantee broken: {final.violations}"  # never ship a violation

    res = GenerationResult(
        plan=plan,
        attempts=attempts,
        outcome=outcome,
        title=title,
        sentences=sentences,
        scene=draft.scene if draft else plan.theme,
        units_used=sorted(units),
        first_pass_violations=len(attempts[0].violations),
        final_violation_count=len(final.violations),
        total_latency_ms=int((time.perf_counter() - t0) * 1000),
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
