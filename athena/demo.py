"""A sample week for the demo children (Sita, Ram), so a visitor sees a lived-in parent view.

Generated when a family gets its copies (athena/store.py ensure_family), relative to now:
stories over the last 7 days with per-word readings, closed sessions with improving accuracy
and words per minute, letters learned and started, one letter that was hard twice (a struggle
alert), maths problems, help-card retries and one "Teach the cat" round.

Everything a child would read is real and checked: Nepali stories come from the verified
templates (athena/fallback.py), English sentences are kept only if the verifier passes them
for this child. Readings are scored by the real scorer (athena/assess/align.py) on a made-up
transcript with this child's kind of mistake. Learners carry profile["demo_copy"], and the
grown-up views say "sample data".
"""

import random
import time

from athena.assess.align import assess, tokens
from athena.fallback import template_story
from athena.lexicon import decodable_words, verifier_for
from athena.mastery import allowed
from athena.teach import en_changes, ne_changes

DAY = 86400.0

# Per demo child: levels, the mistake kind they make, a unit that keeps slipping, words/min range.
PLANS = {
    "Sita": {"level": {"ne": 1, "en": 1}, "maths": {"ne": 1, "en": 1}, "kind": "retroflex_dental",
             "slip": {"ne": "c:ड", "en": "g:d"}, "wcpm": (14, 24), "acc": (0.72, 0.92)},
    "Ram": {"level": {"ne": 2, "en": 2}, "maths": {"ne": 2, "en": 2}, "kind": "aspiration",
            "slip": {"ne": "m:ै", "en": "g:ay"}, "wcpm": (30, 44), "acc": (0.82, 0.96)},
    "Leo": {"level": {"ne": 1, "en": 2}, "maths": {"ne": 1, "en": 2}, "kind": "short_vowel",
            "slip": {"ne": "c:क", "en": "g:igh"}, "wcpm": (26, 40), "acc": (0.8, 0.95)},
}
EN_SENTENCES = [
    "Sita sat.", "Pat a pan.", "Tap the tin.", "The cat sat on a mat.", "A dog had a nap.", "Ram got a red hat.",
    "The sun is up.", "A big pig sat in the mud.", "Sit on the mat.", "Nan has a tin pan.", "The pup ran to Ram.",
    "Ram and the dog sat in the sun.", "Sit, pat the cat.", "Tip the pan.", "Ann can tap the pin.",
]


def _stories(lang: str, learner, rng: random.Random, n: int) -> list[tuple[str, list[str]]]:
    units = frozenset(allowed(learner.units[lang]))
    names = frozenset({learner.name[lang], learner.name[lang].lower()})
    v = verifier_for(lang, units, names)
    out: list[tuple[str, list[str]]] = []
    if lang == "ne":
        readable = decodable_words(lang, units)
        for i in range(n * 3):
            title, sents = template_story(lang, v, readable, [], random.Random(rng.random()))
            if sents and (title, sents) not in out:
                out.append((title or learner.name[lang], sents[:3]))
            if len(out) == n:
                break
    else:
        ok = [s for s in EN_SENTENCES if v.verify(s).ok]
        rng.shuffle(ok)
        for i in range(n):
            pick = ok[(2 * i) % len(ok):(2 * i) % len(ok) + 2] if len(ok) >= 2 else ok
            if pick:
                out.append((pick[0].rstrip("."), pick))
    return out


def _transcript(lang: str, sentences: list[str], kind: str, n_mistakes: int, rng: random.Random) -> str:
    """What the child "said": the story with a few mistakes of this child's kind, maybe a skip."""
    words = tokens(lang, " ".join(sentences))
    change = ne_changes if lang == "ne" else en_changes
    idx = list(range(len(words)))
    rng.shuffle(idx)
    said = list(words)
    made = 0
    for i in idx:
        if made >= n_mistakes:
            break
        options = [c for c in change(words[i]) if c[1] == kind] or change(words[i])
        if options and len(words[i]) > 1:
            said[i] = options[0][0]
            made += 1
    if n_mistakes > 1 and len(said) > 4:
        said.pop(rng.randrange(1, len(said)))  # one skipped word
    return " ".join(said)


def sample_week(learner, now: float | None = None) -> tuple[list[dict], list[dict], dict]:
    """(sessions, history events, overrides) for a demo child. Pure: nothing is written here."""
    now = now or time.time()
    name = learner.name.get("en", "")
    plan = PLANS.get(name, PLANS["Sita"])
    rng = random.Random(sum(map(ord, name)))  # each child their own stories, same every time
    sessions: list[dict] = []
    events: list[dict] = []
    accs: dict[str, list[float]] = {"ne": [], "en": []}
    learns = learner.profile.get("languages", "both")
    langs = ["en"] * 6 if learns == "en" else ["ne"] * 6 if learns == "ne" else ["ne", "en", "ne", "ne", "en", "ne"]
    primary = langs[0]  # the language whose letter slips twice (the struggle alert)
    stories = {lang: _stories(lang, learner, rng, langs.count(lang)) for lang in ("ne", "en")}
    used = {"ne": 0, "en": 0}
    lo, hi = plan["acc"]
    w_lo, w_hi = plan["wcpm"]
    for k, lang in enumerate(langs):
        if used[lang] >= len(stories[lang]):
            continue
        title, sents = stories[lang][used[lang]]
        used[lang] += 1
        day = 6 - k  # one story a day, oldest first, today last
        at = now - day * DAY - rng.uniform(2, 6) * 3600
        sid = f"demo{k}{rng.randrange(10**6):06d}"
        events.append({"type": "story", "story_id": sid, "at": at, "lang": lang, "title": title, "sentences": sents,
                       "theme": "a day with the child's pet", "level": plan["level"][lang], "outcome": "first_pass",
                       "units_used": [], "target_units": [plan["slip"][lang]], "attempts": [{"n": 1, "ms": 2100, "violations": []}],
                       "safety": {"safe": True, "stage": "model", "reason": "", "ms": 400, "replaced": False}})
        n_mistakes = 2 if k < 3 and lang == primary else 1  # fewer mistakes as the week goes on
        heard = _transcript(lang, sents, plan["kind"], n_mistakes, rng)
        n_words = len(tokens(lang, " ".join(sents)))
        wcpm = round(w_lo + (w_hi - w_lo) * k / (len(langs) - 1) + rng.uniform(-1.5, 1.5), 1)
        a = assess(lang, " ".join(sents), heard, max(4.0, n_words / max(wcpm, 1) * 60))
        acc = a.words_correct / len(a.words) if a.words else 1.0
        accs[lang].append(round(acc, 2))
        events.append({"type": "reading", "story_id": sid, "at": at + 60, "transcript": heard, "engine": "demo",
                       "wcpm": a.wcpm, "words_correct": a.words_correct, "words": [w.__dict__ for w in a.words],
                       "insertions": [], "paused": []})
        slip = plan["slip"][lang]
        changes: list[list[str]] = []
        nth = langs[:k + 1].count(primary)  # this is the nth session in the main language
        if lang == primary and nth in (2, 3):  # the same letter slips twice: a struggle alert for the parent
            changes.append([slip, "mastered", "practicing"])
        if k == 4:  # a unit learned this week (the slipping one, if it is the other language)
            done = slip if lang != primary else next(iter(sorted(
                u for u, st in learner.units[lang].items() if st.state == "practicing" and u != slip)), None)
            if done:
                changes.append([done, "practicing", "mastered"])
        learned = {c[0] for ss in sessions for c in ss["changes"]} | {c[0] for c in changes}
        new_unit = sorted(u for u, st in learner.units[lang].items() if st.state == "unseen" and u not in learned)[:1] or \
            sorted(u for u, st in learner.units[lang].items() if st.state == "practicing" and u != slip and u not in learned)[:1]
        if k == 5 and new_unit:
            changes.append([new_unit[0], "unseen", "practicing"])
        events.append({"type": "close", "story_id": sid, "at": at + 90, "accuracy": round(acc, 2),
                       "level_before": plan["level"][lang], "level_after": plan["level"][lang], "changes": changes})
        sessions.append({"at": at + 90, "started": at, "lang": lang, "title": title, "accuracy": round(acc, 2),
                         "wcpm": a.wcpm, "words": len(a.words), "changes": changes, "demo": True})
        # a help-card retry on the first mistake: hearing it didn't help, the parts did
        wrong = next((w for w in a.words if w.outcome in ("substituted", "omitted")), None)
        if wrong:
            for styles, ok in ((["hear"], False), (["hear", "parts"], True)):
                events.append({"type": "reteach", "story_id": sid, "at": at + 120, "index": wrong.index,
                               "word": wrong.expected, "styles": styles, "correct": ok, "trigger": "tap"})

    # maths: a few problems a day at this child's level, one counting slip
    for d in range(5):
        a_, b_ = rng.randint(1, 3), rng.randint(1, 2)
        pid = f"demo-m{d}{rng.randrange(10**6):06d}"
        at = now - (5 - d) * DAY - 3 * 3600
        right = a_ + b_
        events.append({"type": "maths", "story_id": pid, "at": at, "lang": primary, "sentences": [f"{a_} + {b_} = ?"],
                       "a": a_, "b": b_, "op": "+", "source": "template", "level": plan["maths"][primary], "cat_answer": None})
        taps = [right + 1, right] if d == 1 else [right]
        for t, x in enumerate(taps, 1):
            events.append({"type": "maths_answer", "story_id": pid, "at": at + 15 * t, "answer": x,
                           "correct": x == right, "try": t, "secs": 15.0 * t})

    overrides = {"level": dict(plan["level"]),
                 "maths": {lang: {"level": lvl, "recent": []} for lang, lvl in plan["maths"].items()},
                 "history": accs}
    return sessions, events, overrides
