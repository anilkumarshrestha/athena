"""Why this story: plain reasons for parents, built only from what was logged."""

from athena.why import explain

NAME = {"en": "Sita", "ne": "सीता"}


def test_reasons_follow_the_log():
    r = {"theme": "a day with the child's cat, in a hill village", "outcome": "regenerated", "level": 2,
         "target_units": ["c:छ", "m:ि"], "attempts": [{}, {}], "safety": {"safe": True, "replaced": False}}
    w = explain(r, NAME, {"favorite_animal": "cat"})
    assert w["en"][0] == "Practises छ ◌ि: letters Sita is learning now."
    assert "About Sita's favourite: cat." in w["en"]
    assert any("2 drafts" in x for x in w["en"]) and any("Checked by code" in x for x in w["en"])
    assert any("बिरालो" in x for x in w["ne"]) and len(w["en"]) == len(w["ne"])


def test_old_records_and_replacements():
    w = explain({"outcome": "template", "theme": "market day"}, NAME, {})
    assert not any("Practises" in x or "favourite" in x or "safety" in x for x in w["en"])  # not logged: not claimed
    w = explain({"outcome": "first_pass", "safety": {"safe": False, "replaced": True}}, NAME, {})
    assert any("replaced with a safe one" in x for x in w["en"])
    w = explain({"outcome": "wordlist"}, NAME, {})
    assert w["en"][0].startswith("A word list") and not any("Checked by code" in x for x in w["en"])
