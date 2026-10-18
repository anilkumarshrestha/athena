"""Maths word problems the child can read: the Primer's arithmetic pillar on the same engine.

Code decides everything that must be right; the model only writes the words around it:
  - code picks the numbers and the operation (by level) and an object the child can read
  - the model writes 2-3 sentences around exactly those numbers, ending with a question
  - code checks: every word readable (digits allowed), the numbers in the text are exactly
    the chosen ones, a question at the end; code computes the answer (never the model)
  - fallback: a verified template, then a bare "३ + २ = ?"
"""

import random
import re
from dataclasses import dataclass, field

from google.genai import types
from pydantic import BaseModel

from athena.agents.picture import concrete_noun
from athena.agents.writer import _units_line
from athena.config import genai_client, settings
from athena.lexicon import decodable_words, verifier_for
from athena.models import StoryPlan
from athena.retry import with_retry

NE_DIGITS = "०१२३४५६७८९"
DIGITS = frozenset(NE_DIGITS) | frozenset("0123456789")
# level -> (max total, operations)
LEVELS = {1: (5, ("+",)), 2: (10, ("+", "-")), 3: (20, ("+", "-"))}
# countable things a child can picture, preferred in this order when readable
NE_OBJECTS = "केरा आँप स्याउ सुन्तला मकै अण्डा रोटी कुखुरा खसी चरा बिरालो कुकुर गाई बल कलम किताब".split()
EN_OBJECTS = "cats dogs hens pigs cups pens hats eggs ducks fish".split()
MAX_ATTEMPTS = 3
# Flash-Lite: ~1 s per draft without thinking (Flash thought ~1,800 tokens, 10-17 s, for 50
# tokens of output). Weaker first drafts are fine: the checks reject them and a retry is cheap.
MATHS_MODEL = "gemini-3.1-flash-lite"  # meaning check only: a yes/no judgement
QUESTION_WORDS = {"ne": frozenset({"कति"}), "en": frozenset({"how", "many"})}


def to_ne(n: int) -> str:
    return "".join(NE_DIGITS[int(d)] for d in str(n))


def numbers_in(text: str) -> list[int]:
    s = text.translate({ord(d): str(i) for i, d in enumerate(NE_DIGITS)})
    return [int(x) for x in re.findall(r"\d+", s)]


@dataclass
class Problem:
    language: str
    a: int
    b: int
    op: str
    noun: str  # what is counted (shown as pictures)
    sentences: list[str] = field(default_factory=list)
    source: str = "model"  # model | template | bare
    attempts: list[dict] = field(default_factory=list)

    @property
    def answer(self) -> int:
        return self.a + self.b if self.op == "+" else self.a - self.b


FAVOURITE_SHARE = 0.7  # how often the child's favourite (when readable) is what gets counted


def pick(
    language: str, level: int, readable: set[str], rng: random.Random, prefer: tuple[str, ...] = ()
) -> tuple[int, int, str, str]:
    top, ops = LEVELS.get(level, LEVELS[1])
    op = rng.choice(ops)
    # Pick the ANSWER uniformly first, then split it. (Picking a, then b "whatever still fits"
    # made the top total the most likely: ~52% of level-1 answers were 5.)
    if op == "+":
        total = rng.randint(2, top)
        a = rng.randint(1, total - 1)
        b = total - a
    else:
        a = rng.randint(2, top)
        answer = rng.randint(1, a - 1)
        b = a - answer
    pool = [w for w in (NE_OBJECTS if language == "ne" else EN_OBJECTS) if w in readable]
    fav = [w for w in pool if w in prefer]  # interest-based: count the child's favourite
    if fav and rng.random() < FAVOURITE_SHARE:
        noun = rng.choice(fav)
    else:
        noun = rng.choice(pool) if pool else ("केरा" if language == "ne" else "cats")
    return a, b, op, noun


class _Draft(BaseModel):
    sentences: list[str]


class _Meaning(BaseModel):
    meaning: str  # "adds" | "takes_away"


def _meaning(language: str, sentences: list[str]) -> str:
    """What the story does to the first number. A draft that says "mother GAVE 3" for a
    subtraction would contradict the answer the code computes."""
    r = genai_client().models.generate_content(
        model=MATHS_MODEL,
        contents=(
            "A child's maths word problem:\n" + " ".join(sentences) + "\n\nDoes the story ADD to the first "
            "amount (more come, someone gives more) or TAKE AWAY from it (some are eaten, given away, run off)? "
            'Answer {"meaning": "adds"} or {"meaning": "takes_away"}.'
        ),
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=_Meaning, temperature=0),
    )
    m = r.parsed if isinstance(r.parsed, _Meaning) else _Meaning.model_validate_json(r.text or "")
    return m.meaning


NE_CASE = ("सँग", "सित", "लाई", "ले", "को", "का", "की", "मा")


def _near(a: str, b: str) -> bool:
    """One letter apart (a misspelt name: सीतो for सीता)."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = sorted((a, b), key=len)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def _name_problems(name: str, text: str) -> list[str]:
    """Nepali: the child's name spelt exactly, case endings attached (सीताले, not सीता ले)."""
    out = []
    words = re.findall(r"[^\s।?!,.]+", text)
    for i, w in enumerate(words):
        if w == name and i + 1 < len(words) and words[i + 1] in NE_CASE:
            out.append(f"write '{name}{words[i + 1]}' as one word, not '{name} {words[i + 1]}'")
        stem = next((w[: -len(c)] for c in NE_CASE if w.endswith(c) and len(w) > len(c)), w)
        if stem != name and _near(stem, name):
            out.append(f"'{w}': spell the name exactly '{name}'")
    return out


def _check(p: Problem, sentences: list[str], verifier, name: str = "") -> list[str]:
    """Problems with a draft, as short reasons (empty = accepted). Code decides."""
    problems = []
    text = " ".join(sentences)
    if p.language == "ne" and name:
        problems += _name_problems(name, text)
    r = verifier.verify(text)
    problems += [f"'{v.word}' uses {v.unit.split(':', 1)[1] if v.unit else v.reason}" for v in r.violations]
    if numbers_in(text) != [p.a, p.b]:
        problems.append(f"the numbers must be exactly {p.a} then {p.b}, nothing else (found {numbers_in(text)})")
    if not sentences or not sentences[-1].rstrip().endswith("?"):
        problems.append("the last sentence must be the question, ending with ?")
    # Nepali number agreement: more than one -> plural verb (कति किताब छन्?, not छ?).
    if p.language == "ne" and sentences and p.answer > 1 and re.search(r"(^|\s)(छ|थियो|भयो)\s*\?$", sentences[-1].strip()):
        problems.append("the answer is more than one: use the plural verb in the question (छन् / थिए / भए)")
    return problems


def _gender_line(plan: StoryPlan) -> str:
    n = plan.learner_name
    return {
        "boy": f"{n} is a BOY: his verbs are masculine ({n}ले दियो, {n}ले खायो).",
        "girl": f"{n} is a GIRL: her verbs are feminine ({n}ले दिइन्, {n}ले खाइन्), never दियो/खायो.",
    }.get(plan.child_gender, f"{n}'s gender is not given: do not make {n} the subject of a past-tense verb.")


def _prompt(p: Problem, plan: StoryPlan, feedback: list[str]) -> str:
    lang = "Nepali (Devanagari, digits as ०-९)" if p.language == "ne" else "simple English (digits 0-9)"
    a, b = (to_ne(p.a), to_ne(p.b)) if p.language == "ne" else (str(p.a), str(p.b))
    action = (
        "then gets MORE (someone gives more, more arrive)"
        if p.op == "+"
        else "then some go AWAY (eaten, given away by the child, run off): the amount gets SMALLER"
    )
    text = f"""Write a tiny maths word problem in {lang} for a child aged 5-8 in Nepal.
Child's name: {plan.learner_name} (spell it exactly; attach case endings: {plan.learner_name}ले, {plan.learner_name}सँग, {plan.learner_name}का). Thing being counted: {p.noun}.
{_gender_line(plan) if p.language == "ne" else ""}
Use exactly these numbers, in this order, and no other numbers: first {a}, then {b}.
Story: {plan.learner_name} (or someone in the family) has {a} {p.noun}, {action}: {b}.
2 or 3 very short sentences. The LAST sentence asks the question ("कति … ?" / "How many … ?").
Never write the answer. Warm and everyday. Polite honorific verbs for elders (आमाले दिनुभयो).
{"The answer is more than one, so the question takes the PLURAL verb: 'कति केरा छन्?', 'कति चरा भए?' (never छ? / भयो?)." if p.language == "ne" and p.answer > 1 else ""}

Every word must be readable for this child. Word bank: {" ".join(plan.word_bank[:120])}
{_units_line(plan)}"""
    if feedback:
        text += "\nYour last draft was rejected:\n- " + "\n- ".join(feedback) + "\nWrite a new one."
    return text


NE_FOOD = {"केरा", "आँप", "स्याउ", "सुन्तला", "मकै", "अण्डा", "रोटी"}
NE_ANIMALS = {"कुखुरा", "खसी", "चरा", "बिरालो", "कुकुर", "गाई"}


def _ne_templates(p: Problem, name: str, gender: str) -> list[list[str]]:
    """Grammatical Nepali problems, best first; the caller keeps the first readable one.
    Plural agrees with the number (३ केरा छन् / १ केरा छ), elders take honorifics, the child's
    verb agrees with gender (unknown: a younger brother acts instead)."""
    A, B, N = to_ne(p.a), to_ne(p.b), p.noun
    pl_a = p.a > 1
    have = [f"{name}सँग {A} वटा {N} {'छन्' if pl_a else 'छ'}।", f"{name}सँग {A} {N} {'छन्' if pl_a else 'छ'}।",
            f"{name}{'का' if pl_a else 'को'} {A} वटा {N} {'थिए' if pl_a else 'थियो'}।", f"{name}{'का' if pl_a else 'को'} {A} {N} {'थिए' if pl_a else 'थियो'}।"]
    if p.op == "+":
        act = [f"आमाले {B} {N} दिनुभयो।", f"बुबाले {B} {N} दिनुभयो।", f"बाबाले {B} {N} दिनुभयो।"]
        ask = [f"अब {name}सँग कति {N} छन्?", f"अब {name}का कति {N} भए?", f"अब कति {N} भए?"]
    else:
        pl_b = p.b > 1
        if N in NE_FOOD:
            child = {"boy": "खायो", "girl": "खाइन्"}.get(gender)
            act = ([f"{name}ले {B} {N} {child}।"] if child else []) + [f"भाइले {B} {N} खायो।"]
        elif N in NE_ANIMALS:
            act = [f"{B} {N} बाहिर {'गए' if pl_b else 'गयो'}।", f"{B} {N} बारीमा {'गए' if pl_b else 'गयो'}।"]
        else:
            act = [f"भाइले {B} {N} लियो।", f"बहिनीले {B} {N} लिई।"]
        ask = [f"अब {name}सँग कति {N} बाँकी छन्?", f"अब कति {N} बाँकी छन्?", f"अब कति {N} छन्?"]
    return [[h, a, q] for h in have for a in act for q in ask]


def _template(p: Problem, plan: StoryPlan, verifier) -> list[str] | None:
    name = plan.learner_name
    if p.language == "ne":
        options = _ne_templates(p, name, plan.child_gender)
    else:
        def n(k: int) -> str:  # "1 dog", "2 dogs" (fish stays fish)
            return p.noun if k != 1 or p.noun == "fish" else p.noun[:-1]

        options = [
            [f"{name} had {p.a} {n(p.a)}.", f"{name} got {p.b} {n(p.b)}.", f"How many {p.noun}?"]
            if p.op == "+"
            else [f"{name} had {p.a} {n(p.a)}.", f"{p.b} {n(p.b)} {'ran' if p.b > 1 else 'ran'} off.", f"How many {p.noun}?"],
            [f"{name} has {p.a} {n(p.a)}.", f"{p.b} more!", "How many?"]
            if p.op == "+"
            else [f"{name} has {p.a} {n(p.a)}.", f"{p.b} ran off.", "How many?"],
        ]
    return next((o for o in options if not _check(p, o, verifier, name)), None)


def quick_problem(plan: StoryPlan, seed: int | None = None, prefer: tuple[str, ...] = ()) -> Problem | None:
    """Instant, code-built problem (no model): the first problem of a session, while a model-
    written one is prepared in the background. None if no template is readable."""
    rng = random.Random(seed)
    readable = set(decodable_words(plan.language, frozenset(plan.mastery)))
    for _ in range(6):  # a few number/object draws until one reads
        a, b, op, noun = pick(plan.language, plan.level, readable, rng, prefer)
        p = Problem(plan.language, a, b, op, noun)
        if t := _template(p, plan, _verifier(plan, p)):
            p.sentences, p.source = t, "template"
            return p
    return None


def _verifier(plan: StoryPlan, p: Problem):
    names = frozenset(plan.learner_name.split()) | frozenset(plan.learner_name.lower().split())
    return verifier_for(plan.language, frozenset(plan.mastery), names | DIGITS | _digit_words(p.a, p.b) | QUESTION_WORDS[plan.language])


def make_problem(plan: StoryPlan, seed: int | None = None, prefer: tuple[str, ...] = ()) -> Problem:
    rng = random.Random(seed)
    names = frozenset(plan.learner_name.split()) | frozenset(plan.learner_name.lower().split())
    readable = set(decodable_words(plan.language, frozenset(plan.mastery)))
    a, b, op, noun = pick(plan.language, plan.level, readable, rng, prefer)
    p = Problem(plan.language, a, b, op, noun)
    # The fixed question phrase is allowed in maths ("How many?"/"कति"): the child can tap to hear it.
    question = QUESTION_WORDS[plan.language]
    verifier = verifier_for(plan.language, frozenset(plan.mastery), names | DIGITS | _digit_words(a, b) | question)
    feedback: list[str] = []
    for _ in range(MAX_ATTEMPTS):
        try:
            r = with_retry(
                lambda: genai_client().models.generate_content(
                    # Flash: Flash-Lite was 10x faster but its Nepali was not good enough
                    # ("आमा ले", "खानु भयो", "बाकी"). Its time is hidden by preparing the next
                    # problem in the background (athena/api.py).
                    model=settings().writer_model,
                    contents=_prompt(p, plan, feedback),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=_Draft,
                        thinking_config=types.ThinkingConfig(thinking_level="low"),
                        temperature=0.8,
                        max_output_tokens=4096,
                    ),
                ),
                "maths",
            )
            draft = r.parsed if isinstance(r.parsed, _Draft) else _Draft.model_validate_json(r.text or "")
        except Exception as e:  # noqa: BLE001
            p.attempts.append({"sentences": [], "problems": [f"model error: {type(e).__name__}"]})
            continue
        feedback = _check(p, draft.sentences, verifier, plan.learner_name)
        if not feedback:
            want = "adds" if p.op == "+" else "takes_away"
            try:
                if _meaning(p.language, draft.sentences) != want:
                    feedback = [f"the story must {'ADD more to' if p.op == '+' else 'TAKE AWAY from'} the first amount"]
            except Exception:  # noqa: BLE001 - cannot confirm the meaning: do not risk it
                feedback = ["meaning could not be checked"]
        p.attempts.append({"sentences": draft.sentences, "problems": feedback})
        if not feedback:
            # "थियो ।" -> "थियो।": no space before the full stop or question mark
            p.sentences, p.source = [re.sub(r"\s+([।?!.])", r"\1", x).strip() for x in draft.sentences], "model"
            return p
    if t := _template(p, plan, verifier):
        p.sentences, p.source = t, "template"
        return p
    a_s, b_s = (to_ne(a), to_ne(b)) if plan.language == "ne" else (str(a), str(b))
    p.sentences, p.source = [f"{a_s} {op} {b_s} = ?"], "bare"
    return p


def _digit_words(a: int, b: int) -> frozenset[str]:
    """Multi-digit numbers are single tokens: allow exactly the chosen ones."""
    return frozenset({str(a), str(b), to_ne(a), to_ne(b)})


def picture_noun(language: str, noun: str) -> str | None:
    """A word picture to show the objects being counted (Nepali nouns carry the pictures)."""
    if language == "ne":
        return concrete_noun("ne", noun)
    en_to_ne = {"cats": "बिरालो", "dogs": "कुकुर", "hens": "कुखुरा", "cups": "गिलास", "pens": "कलम", "hats": "टोपी",
                "eggs": "अण्डा", "ducks": "हाँस", "fish": "माछा", "pigs": "बङ्गुर"}
    return concrete_noun("ne", en_to_ne.get(noun, "")) if noun in en_to_ne else None
