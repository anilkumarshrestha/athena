"""Writer: Gemini drafts the story. It proposes; the verifier decides."""

import time

from google.genai import errors, types
from pydantic import ValidationError

from athena.config import genai_client, settings
from athena.models import StoryDraft, StoryPlan, Usage, ViolationOut
from athena.progression import LEVELS
from athena.retry import with_retry

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
    gender_rule = {
        "boy": f"- {plan.learner_name} is a BOY: masculine past verbs for him: \"{plan.learner_name} बजार गयो\", \"{plan.learner_name} खुसी भयो\", \"{plan.learner_name}ले भात खायो\". Never गइन्/भइन्/खाइन् for him.\n",
        "girl": f"- {plan.learner_name} is a GIRL: feminine past verbs for her: \"{plan.learner_name} बजार गइन्\", \"{plan.learner_name} खुसी भइन्\", \"{plan.learner_name}ले भात खाइन्\". Never गयो/भयो/खायो for her.\n",
    }.get(plan.child_gender, f"- {plan.learner_name}'s gender is not given: avoid gendered past-tense verbs for {plan.learner_name}; use present tense (\"{plan.learner_name} खुसी छ\", \"{plan.learner_name} बजार जान्छ\").\n")
    grammar = (
        """
Nepali grammar and idiom (a native speaker will read this):
- Transitive verbs in the past tense take the ergative -ले on the subject: "रामले झोला लियो", "आमाले भात पकाउनुभयो". Never "राम झोला लियो".
- RESPECT: elders and older siblings (आमा, बुबा, बाबा, हजुरआमा, हजुरबुबा, काका, काकी, मामा, गुरु, दाइ, दिदी) ALWAYS take honorific verbs: "आमा आउनुभयो", "दाइले खाना खानुभयो", "हजुरआमा घरमा हुनुहुन्छ", "बुबा बजार जानुहुन्छ". Never "आमा आयो" or "दाइले खायो". The child, younger siblings (भाइ, बहिनी) and animals take plain forms ("भाइ खेल्यो", "बिरालो सुत्यो"). If the honorific form is not allowed, write a sentence where the elder is not the subject of a verb.
- Use the natural verb for each noun, never a near-synonym: rain falls "पानी पर्यो" (not "पानी आयो").
- Prefer the lively idiomatic verb: "राम रमायो" over "राम खुसी भयो" where it fits.
- If the natural word is not allowed, REPHRASE the whole sentence around a different idea. Never swap in an unnatural or ungrammatical word to satisfy the letter rules. A shorter correct story beats a longer wrong one.
"""
        if plan.language == "ne"
        else ""
    )
    if plan.language == "ne":
        grammar = grammar.replace("- RESPECT:", gender_rule + "- RESPECT:", 1)
    lim = LEVELS[plan.level]
    key_line = ""
    if plan.key_words:
        key_line += f"Key words for this theme (the child can read these; use them): {' '.join(plan.key_words)}\n"
    if plan.avoid_words:
        key_line += f"Do NOT write these even though they are natural (the child cannot read them yet): {' '.join(plan.avoid_words)}\n"
    prompt = f"""You write decodable reading stories for a {lang} beginner reader aged 5-8 in Nepal.

Child's name: {plan.learner_name} (always allowed; spell it EXACTLY like this. In Nepali you may attach case endings: {plan.learner_name}ले, {plan.learner_name}को, {plan.learner_name}लाई, {plan.learner_name}मा, {plan.learner_name}सँग)
Theme: {plan.theme}
Focus units to practise often: {", ".join(u.split(":", 1)[1] for u in plan.target_units)}
{key_line}
{bank_rule}
{_units_line(plan)}

Word bank:
{" ".join(plan.word_bank)}

Rules:
- {f"exactly {lim.sentences[0]}" if lim.sentences[0] == lim.sentences[1] else f"{lim.sentences[0]} to {lim.sentences[1]}"} short sentences, at most {lim.max_words} words each. Simple, warm, coherent. Repetition is good.
- Every word at most {lim.max_len_ne if plan.language == "ne" else lim.max_len_en} {"aksharas (letter clusters)" if plan.language == "ne" else "sounds"} long (the child's name is exempt). Prefer short words.
- A short title using the same constraints.
- Everyday Nepali child life: family, village, animals, food, school.
- No violence, fear, danger, sadness or adult themes.
- "scene": one English sentence describing a picture for the story (animals and objects, no detailed faces).
{grammar}"""
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


class WriterFailed(Exception):
    """The writer produced no usable draft. generate() counts it as a failed attempt."""

    def __init__(self, reason: str, prompt: str, usage: Usage, latency_ms: int) -> None:
        super().__init__(reason)
        self.reason, self.prompt, self.usage, self.latency_ms = reason, prompt, usage, latency_ms


def write(
    plan: StoryPlan, feedback: list[ViolationOut] | None = None, timeout_ms: int | None = None
) -> tuple[StoryDraft, str, Usage, int]:
    s = settings()
    prompt = build_prompt(plan, feedback)
    t0 = time.perf_counter()
    try:
        r = with_retry(
            lambda: genai_client().models.generate_content(
                model=s.writer_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StoryDraft,
                    thinking_config=types.ThinkingConfig(thinking_level=s.writer_thinking_level),
                    temperature=0.9,
                    # Thinking counts toward this cap on Gemini 3; 2048 truncated the JSON.
                    # Runaways are bounded by the request timeout instead.
                    max_output_tokens=4096,
                    # Per-call override so generate() can enforce its time budget.
                    http_options=types.HttpOptions(timeout=timeout_ms) if timeout_ms else None,
                ),
            ),
            "writer",
            deadline=time.monotonic() + timeout_ms / 1000 if timeout_ms else None,
        )
    except errors.APIError as e:
        ms = int((time.perf_counter() - t0) * 1000)
        raise WriterFailed(f"model error {e.code}", prompt, Usage(model=s.writer_model), ms) from e

    latency_ms = int((time.perf_counter() - t0) * 1000)
    um = r.usage_metadata
    usage = Usage(
        model=r.model_version or s.writer_model,
        input_tokens=um.prompt_token_count or 0,
        output_tokens=um.candidates_token_count or 0,
        thinking_tokens=um.thoughts_token_count or 0,
    )
    try:
        draft = r.parsed if isinstance(r.parsed, StoryDraft) else StoryDraft.model_validate_json(r.text or "")
    except ValidationError as e:
        finish = r.candidates[0].finish_reason if r.candidates else None
        raise WriterFailed(f"malformed output (finish={finish})", prompt, usage, latency_ms) from e
    return draft, prompt, usage, latency_ms
