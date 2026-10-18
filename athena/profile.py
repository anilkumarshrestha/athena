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
GenderId = Literal["boy", "girl", "unspecified"]  # Nepali past-tense verbs agree with gender
AgeId = Literal["4", "5", "6", "7", "8"]  # 8 = 8 or older
LanguagesId = Literal["ne", "en", "both"]  # what the child is learning to read
ActivityId = Literal["kite", "football", "dancing", "drawing", "singing", "cycling"]
BuddyId = Literal["cat", "dog", "goat", "bird", "rabbit"]  # the reading buddy: avatar + "teach the ..."
GoalId = Literal["5", "10", "15"]  # daily goal in minutes (the child's goal, not the parent's limit)

# buddy -> (Nepali, English): pictured nouns (athena/agents/picture.py)
BUDDIES: dict[str, tuple[str, str]] = {
    "cat": ("बिरालो", "cat"), "dog": ("कुकुर", "dog"), "goat": ("बाख्रा", "goat"),
    "bird": ("चरा", "bird"), "rabbit": ("खरायो", "rabbit"),
}


# The child's own picture (learner card, onboarding): cartoon animals, pictured nouns.
AvatarId = Literal["cat", "dog", "rabbit", "elephant", "monkey", "bear", "butterfly", "fish", "duck", "yak", "goat", "bird"]
AVATARS: dict[str, tuple[str, str]] = {
    "cat": ("बिरालो", "Cat"), "dog": ("कुकुर", "Dog"), "rabbit": ("खरायो", "Rabbit"), "elephant": ("हात्ती", "Elephant"),
    "monkey": ("बाँदर", "Monkey"), "bear": ("भालु", "Bear"), "butterfly": ("पुतली", "Butterfly"), "fish": ("माछा", "Fish"),
    "duck": ("हाँस", "Duck"), "yak": ("याक", "Yak"), "goat": ("बाख्रा", "Goat"), "bird": ("चरा", "Bird"),
}


def avatar_of(learner_id: str, chosen: str | None) -> str:
    """The chosen avatar, or a default picked steadily from the id (same every visit)."""
    if chosen in AVATARS:
        return chosen
    import hashlib

    ids = sorted(AVATARS)
    return ids[int(hashlib.sha256(learner_id.encode()).hexdigest(), 16) % len(ids)]


def avatar_url(learner_id: str, chosen: str | None) -> str:
    return f"/api/pictures/ne/{AVATARS[avatar_of(learner_id, chosen)][0]}"


def buddy(profile: dict) -> tuple[str, str]:
    return BUDDIES.get(profile.get("buddy", "cat"), BUDDIES["cat"])

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


def personal_themes(animal: str | None, food: str | None, activity: str | None = None) -> list[Theme]:
    """Themes built from the child's favourites (the planner keeps only readable ones)."""
    from athena.agents.planner import ACTIVITY_THEMES

    themes = [ACTIVITY_THEMES[activity]] if activity in ACTIVITY_THEMES else []
    if animal in ANIMALS:
        en, ne_words, en_words = ANIMALS[animal]
        themes.append(Theme(f"a day with the child's {en}", ne=[ne_words], en=[en_words] if en_words else []))
    if food in FOODS:
        en, ne_words, en_words = FOODS[food]
        themes.append(Theme(f"eating {en} with family", ne=[ne_words], en=[en_words] if en_words else []))
    return themes
