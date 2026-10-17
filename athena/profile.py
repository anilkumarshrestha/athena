"""Learner profile: what makes a story *theirs*. Fixed choices only.

Everything here reaches the model prompt, so nothing is free text except the name,
which is validated by script and length (athena/api.py). No exact location: a
general setting keeps PLAN §11 "avatar + first name only" intact.
"""

from typing import Literal

from athena.agents.planner import Theme

AnimalId = Literal["goat", "cat", "dog", "hen", "cow", "buffalo", "bird", "yak"]
FoodId = Literal["dal_bhat", "momo", "roti", "mango", "banana", "milk", "corn", "egg"]
SettingId = Literal["hills", "terai", "mountains", "city"]
StartId = Literal["beginner", "some", "reads"]

# id -> (English for the image/theme, Nepali words most natural first, English story words)
ANIMALS: dict[str, tuple[str, list[str], list[str]]] = {
    "goat": ("goat", ["बाख्रा", "खसी", "बोका"], ["goat", "goats"]),
    "cat": ("cat", ["बिरालो"], ["cat", "cats"]),
    "dog": ("dog", ["कुकुर"], ["dog", "dogs"]),
    "hen": ("hen", ["कुखुरा"], ["hen", "hens"]),
    "cow": ("cow", ["गाई"], ["cow", "cows"]),
    "buffalo": ("water buffalo", ["भैंसी"], []),
    "bird": ("little bird", ["चरा"], ["bird", "birds"]),
    "yak": ("yak", ["याक"], ["yak"]),
}
FOODS: dict[str, tuple[str, list[str], list[str]]] = {
    "dal_bhat": ("dal bhat", ["भात", "दाल"], []),
    "momo": ("momo dumplings", ["मोमो"], []),
    "roti": ("roti", ["रोटी"], []),
    "mango": ("mangoes", ["आँप"], []),
    "banana": ("bananas", ["केरा"], []),
    "milk": ("a glass of milk", ["दूध"], ["milk"]),
    "corn": ("roasted corn", ["मकै"], ["corn"]),
    "egg": ("eggs", ["अण्डा"], ["egg", "eggs"]),
}
SETTINGS: dict[str, str] = {
    "hills": "a hill village in Nepal",
    "terai": "a farming village in the Terai plains of Nepal",
    "mountains": "a mountain village in Nepal",
    "city": "a neighbourhood in Kathmandu",
}
# start -> (Nepali preset, English preset, level)
STARTS: dict[str, tuple[str, str, int]] = {
    "beginner": ("ne_early", "en_satpin_sh", 1),
    "some": ("ne_basic", "en_p2", 1),
    "reads": ("ne_mid", "en_p3", 2),
}


def personal_themes(animal: str | None, food: str | None) -> list[Theme]:
    """Themes built from the child's favourites (the planner keeps only readable ones)."""
    themes = []
    if animal in ANIMALS:
        en, ne_words, en_words = ANIMALS[animal]
        themes.append(Theme(f"a day with the child's {en}", ne=[ne_words], en=[en_words] if en_words else []))
    if food in FOODS:
        en, ne_words, en_words = FOODS[food]
        themes.append(Theme(f"eating {en} with family", ne=[ne_words], en=[en_words] if en_words else []))
    return themes
