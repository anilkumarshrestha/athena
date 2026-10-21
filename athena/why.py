""""Why this story": a plain explanation for parents of what the AI made and why. Pure code.

Built only from what was logged when the story was made (history "story" event) and the
child's profile: which letters it practises, which favourite it uses, how it was checked,
how many drafts it took, and the safety check. No model writes this text, so it cannot
claim anything that did not happen.
"""

from athena.profile import ANIMALS, FOODS


def _ne_num(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", "०१२३४५६७८९"))


def _glyph(sig: str) -> str:
    kind, _, u = sig.partition(":")
    return f"◌{u}" if kind == "m" else u


def _favourite(theme: str, profile: dict) -> tuple[str, str] | None:
    """(English, Nepali) name of the favourite the theme was built on, if any."""
    for key, table in (("favorite_animal", ANIMALS), ("favorite_food", FOODS)):
        fav = table.get(profile.get(key, ""))
        if fav and fav[0] in theme:
            return fav[0], fav[1][0]
    return None


def explain(record: dict, name: dict[str, str], profile: dict) -> dict[str, list[str]]:
    """{"en": [...], "ne": [...]}: one short line per reason, same order in both languages."""
    n_en, n_ne = name.get("en", ""), name.get("ne", "")
    en, ne = [], []

    target = [_glyph(u) for u in record.get("target_units", [])]
    if target:
        t = " ".join(target)
        en.append(f"Practises {t}: letters {n_en} is learning now.")
        ne.append(f"{n_ne}ले अहिले सिक्दै गरेका अक्षर {t} अभ्यास गराउँछ।")

    text = " ".join([record.get("title", ""), *record.get("sentences", [])])
    used = [w for w in record.get("revisit_words", []) if w in text]  # claimed only if really in the story
    if used:
        w = ", ".join(used)
        en.append(f"Brings back {w}: words {n_en} found hard in recent readings.")
        ne.append(f"{n_ne}लाई हालै पढ्दा गाह्रो भएका शब्द {w} फेरि अभ्यास गराउँछ।")

    fav = _favourite(record.get("theme", ""), profile)
    if fav:
        en.append(f"About {n_en}'s favourite: {fav[0]}.")
        ne.append(f"{n_ne}को मनपर्ने {fav[1]}बारे।")

    outcome = record.get("outcome")
    if outcome == "wordlist":
        en.append(f"A word list, not a story: {n_en} can read too few words for a story yet.")
        ne.append(f"कथा होइन, शब्दको सूची: {n_ne}ले कथाका लागि पुग्ने शब्द अझै पढ्न सक्दैन।")
    else:
        en.append(f"Every word uses only letters {n_en} can read. Checked by code, not by the AI.")
        ne.append(f"हरेक शब्दमा {n_ne}ले पढ्न सक्ने अक्षर मात्र छन्। AI ले होइन, कोडले जाँचेको।")

    drafts = len(record.get("attempts", []))
    if outcome == "first_pass":
        en.append("The AI's first draft passed the check.")
        ne.append("AI को पहिलो मस्यौदा नै जाँचमा पास भयो।")
    elif outcome == "regenerated":
        en.append(f"Rewritten: the AI needed {drafts} drafts; earlier ones used letters {n_en} can't read yet.")
        ne.append(f"फेरि लेखियो: AI लाई {_ne_num(drafts)} मस्यौदा लाग्यो; पहिलेकामा {n_ne}ले पढ्न नसक्ने अक्षर थिए।")
    elif outcome == "pruned":
        en.append("Sentences that used letters not learned yet were removed.")
        ne.append("नसिकेका अक्षर भएका वाक्य हटाइए।")
    elif outcome == "template":
        en.append("The AI's drafts did not fit, so a ready-made story with the same letters was used.")
        ne.append("AI का मस्यौदा नमिलेकाले उही अक्षरको तयारी कथा दिइयो।")

    safety = record.get("safety") or {}
    if safety.get("replaced"):
        en.append("The first story did not pass the child-safety check and was replaced with a safe one.")
        ne.append("पहिलो कथा बाल-सुरक्षा जाँचमा पास नभएकाले सुरक्षित कथा दिइयो।")
    elif safety:
        en.append("Checked for child safety before it was shown.")
        ne.append("देखाउनुअघि बाल-सुरक्षाका लागि जाँचियो।")

    level = record.get("level")
    if level:
        en.append(f"Story size: level {level} of 3.")
        ne.append(f"कथाको आकार: तह {_ne_num(level)}/३।")
    return {"en": en, "ne": ne}
