"""Writer: Gemini drafts the story. It proposes; the verifier decides."""

import time

from google.genai import types

from athena.config import genai_client, settings
from athena.models import StoryDraft, StoryPlan, Usage, ViolationOut

_LANG = {"ne": "Nepali (Devanagari script)", "en": "simple English"}

_NE_LETTERS = "क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह अ आ इ ई उ ऊ ए ऐ ओ औ".split()
_NE_SIGNS = "ा ि ी ु ू े ै ो ौ ं ँ ः ्".split()


def _units_line(plan: StoryPlan) -> str:
    if plan.language == "ne":
        letters = [u[2:] for u in plan.mastery if u.startswith("c:")]
        signs = [u[2:] for u in plan.mastery if u.startswith("m:")]
        conj = [u[2:] for u in plan.mastery if u.startswith("k:")]
        no_letters = [c for c in _NE_LETTERS if c not in letters]
        no_signs = [m for m in _NE_SIGNS if m not in signs]
        return (
            f"ALLOWED letters: {' '.join(letters)}\n"
            f"ALLOWED vowel signs/marks: {' '.join(signs) or '(none)'}\n"
            f"ALLOWED conjuncts: {' '.join(conj) or '(none: never join two consonants)'}\n"
            f"FORBIDDEN letters: {' '.join(no_letters) or '(none)'}\n"
            f"FORBIDDEN vowel signs/marks: {' '.join(no_signs) or '(none)'}\n"
            "Check every word letter by letter before you answer."
        )
    return "Use ONLY words from the word bank. No other words at all, not even small ones."


def build_prompt(plan: StoryPlan, feedback: list[ViolationOut] | None = None) -> str:
    lang = _LANG[plan.language]
    bank_rule = (
        "Prefer words from the word bank. You may use other words ONLY if they are spelled entirely "
        "with the allowed letters, signs and conjuncts below."
        if plan.language == "ne"
        else "Every word in the title and story MUST come from the word bank (case-insensitive)."
    )
    prompt = f"""You write decodable reading stories for a {lang} beginner reader aged 5-8 in Nepal.

Child's name: {plan.learner_name} (always allowed; write it EXACTLY like this, no suffixes attached)
Theme: {plan.theme}
Focus units to practise often: {", ".join(u.split(":", 1)[1] for u in plan.target_units)}

{bank_rule}
{_units_line(plan)}

Word bank:
{" ".join(plan.word_bank)}

Rules:
- 3 to 5 very short sentences, each 3-7 words. Simple, warm, coherent. Repetition is good.
- A short title using the same constraints.
- Everyday Nepali child life: family, village, animals, food, school.
- No violence, fear, danger, sadness or adult themes.
- "scene": one English sentence describing a picture for the story (animals and objects, no detailed faces).
"""
    if feedback:
        lines = []
        for v in feedback:
            if v.unit is None:
                lines.append(f"- '{v.word}': {v.reason}")
            else:
                lines.append(f"- '{v.word}': uses {v.unit.split(':', 1)[1]} which the child cannot read yet")
        prompt += (
            "\nYour previous draft broke the rules. These words are NOT allowed:\n"
            + "\n".join(lines)
            + "\nWrite a new draft that avoids them. Do not just delete words; keep sentences natural.\n"
        )
    return prompt


def write(plan: StoryPlan, feedback: list[ViolationOut] | None = None) -> tuple[StoryDraft, str, Usage, int]:
    s = settings()
    prompt = build_prompt(plan, feedback)
    t0 = time.perf_counter()
    r = genai_client().models.generate_content(
        model=s.writer_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=StoryDraft,
            thinking_config=types.ThinkingConfig(thinking_level=s.writer_thinking_level),
            temperature=0.9,
        ),
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    draft = r.parsed if isinstance(r.parsed, StoryDraft) else StoryDraft.model_validate_json(r.text)
    um = r.usage_metadata
    usage = Usage(
        model=r.model_version or s.writer_model,
        input_tokens=um.prompt_token_count or 0,
        output_tokens=um.candidates_token_count or 0,
        thinking_tokens=um.thoughts_token_count or 0,
    )
    return draft, prompt, usage, latency_ms
