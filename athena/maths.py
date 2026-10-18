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
MAX_ATTEMPTS = 2
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


def pick(language: str, level: int, readable: set[str], rng: random.Random) -> tuple[int, int, str, str]:
    top, ops = LEVELS.get(level, LEVELS[1])
    op = rng.choice(ops)
    if op == "+":
        a = rng.randint(1, top - 1)
        b = rng.randint(1, top - a)
    else:
        a = rng.randint(2, top)
        b = rng.randint(1, a - 1)
    pool = [w for w in (NE_OBJECTS if language == "ne" else EN_OBJECTS) if w in readable]
    noun = rng.choice(pool) if pool else ("केरा" if language == "ne" else "cats")
    return a, b, op, noun


class _Draft(BaseModel):
    sentences: list[str]


def _check(p: Problem, sentences: list[str], verifier) -> list[str]:
    """Problems with a draft, as short reasons (empty = accepted). Code decides."""
    problems = []
    text = " ".join(sentences)
    r = verifier.verify(text)
    problems += [f"'{v.word}' uses {v.unit.split(':', 1)[1] if v.unit else v.reason}" for v in r.violations]
    if numbers_in(text) != [p.a, p.b]:
        problems.append(f"the numbers must be exactly {p.a} then {p.b}, nothing else (found {numbers_in(text)})")
    if not sentences or not sentences[-1].rstrip().endswith("?"):
        problems.append("the last sentence must be the question, ending with ?")
    return problems


def _prompt(p: Problem, plan: StoryPlan, feedback: list[str]) -> str:
    lang = "Nepali (Devanagari, digits as ०-९)" if p.language == "ne" else "simple English (digits 0-9)"
    a, b = (to_ne(p.a), to_ne(p.b)) if p.language == "ne" else (str(p.a), str(p.b))
    action = "gets more" if p.op == "+" else "gives some away / some go away"
    text = f"""Write a tiny maths word problem in {lang} for a child aged 5-8 in Nepal.
Child's name: {plan.learner_name}. Thing being counted: {p.noun}.
Use exactly these numbers, in this order, and no other numbers: first {a}, then {b}.
Story: {plan.learner_name} (or someone in the family) has {a} {p.noun}, then {action}: {b}.
2 or 3 very short sentences. The LAST sentence asks the question ("कति … ?" / "How many … ?").
Never write the answer. Warm and everyday. Polite honorific verbs for elders (आमाले दिनुभयो).

Every word must be readable for this child. Word bank: {" ".join(plan.word_bank[:120])}
{_units_line(plan)}"""
    if feedback:
        text += "\nYour last draft was rejected:\n- " + "\n- ".join(feedback) + "\nWrite a new one."
    return text


def _template(p: Problem, plan: StoryPlan, verifier) -> list[str] | None:
    name = plan.learner_name
    if p.language == "ne":
        a, b = to_ne(p.a), to_ne(p.b)
        variants = (
            [f"{name}सँग {a} {p.noun} छ।", f"आमाले {b} {p.noun} दिनुभयो।", "अब कति भयो?"]
            if p.op == "+"
            else [f"{name}सँग {a} {p.noun} छ।", f"{b} {p.noun} गयो।", "अब कति बाँकी छ?"]
        )
    else:
        variants = (
            [f"{name} has {p.a} {p.noun}.", f"Dad gets {p.b} {p.noun}.", "How many?"]
            if p.op == "+"
            else [f"{name} has {p.a} {p.noun}.", f"{p.b} {p.noun} ran off.", "How many?"]
        )
        variants = (
            [f"{name} had {p.a} {p.noun}.", f"{name} got {p.b} {p.noun}.", f"How many {p.noun}?"]
            if p.op == "+"
            else [f"{name} had {p.a} {p.noun}.", f"{p.b} {p.noun} ran off.", f"How many {p.noun}?"]
        )
    return variants if not _check(p, variants, verifier) else None


def make_problem(plan: StoryPlan, seed: int | None = None) -> Problem:
    rng = random.Random(seed)
    names = frozenset(plan.learner_name.split()) | frozenset(plan.learner_name.lower().split())
    readable = set(decodable_words(plan.language, frozenset(plan.mastery)))
    a, b, op, noun = pick(plan.language, plan.level, readable, rng)
    p = Problem(plan.language, a, b, op, noun)
    # The fixed question phrase is allowed in maths ("How many?"/"कति"): the child can tap to hear it.
    question = QUESTION_WORDS[plan.language]
    verifier = verifier_for(plan.language, frozenset(plan.mastery), names | DIGITS | _digit_words(a, b) | question)
    feedback: list[str] = []
    for _ in range(MAX_ATTEMPTS):
        try:
            r = with_retry(
                lambda: genai_client().models.generate_content(
                    model=settings().writer_model,
                    contents=_prompt(p, plan, feedback),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=_Draft,
                        thinking_config=types.ThinkingConfig(thinking_level="low"),
                        temperature=0.8,
                        max_output_tokens=2048,
                    ),
                ),
                "maths",
            )
            draft = r.parsed if isinstance(r.parsed, _Draft) else _Draft.model_validate_json(r.text or "")
        except Exception as e:  # noqa: BLE001
            p.attempts.append({"sentences": [], "problems": [f"model error: {type(e).__name__}"]})
            continue
        feedback = _check(p, draft.sentences, verifier)
        p.attempts.append({"sentences": draft.sentences, "problems": feedback})
        if not feedback:
            p.sentences, p.source = draft.sentences, "model"
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
