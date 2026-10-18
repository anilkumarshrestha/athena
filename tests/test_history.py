"""Story/reading history: append-only events folded into records. Temp dir."""

from athena.history import History


def test_events_fold_into_story_records(tmp_path):
    h = History(tmp_path)
    h.append("a1", {"type": "story", "story_id": "s1", "at": 1.0, "title": "पहिलो", "sentences": ["आमा।"]})
    h.append("a1", {"type": "story", "story_id": "s2", "at": 2.0, "title": "दोस्रो", "sentences": ["बाबा।"]})
    h.append("a1", {"type": "image", "story_id": "s1", "image_id": "img.png"})
    h.append("a1", {"type": "reading", "story_id": "s1", "at": 1.5, "words": [{"index": 0, "outcome": "correct"}]})
    h.append("a1", {"type": "close", "story_id": "s1", "at": 1.6, "accuracy": 1.0})
    stories = h.stories("a1")
    assert [s["story_id"] for s in stories] == ["s2", "s1"]  # newest first
    s1 = h.story("a1", "s1")
    assert s1["image_id"] == "img.png" and len(s1["readings"]) == 1 and s1["close"]["accuracy"] == 1.0
    assert "पहिलो" in (tmp_path / "a1.jsonl").read_text(encoding="utf-8")


def test_torn_last_line_is_skipped(tmp_path):
    h = History(tmp_path)
    h.append("a1", {"type": "story", "story_id": "s1", "at": 1.0})
    with (tmp_path / "a1.jsonl").open("a") as f:
        f.write('{"type": "reading", "story_')  # crash mid-write
    assert len(h.stories("a1")) == 1


def test_delete_and_bad_ids(tmp_path):
    h = History(tmp_path)
    h.append("a1", {"type": "story", "story_id": "s1", "at": 1.0})
    h.delete("a1")
    assert h.stories("a1") == []
    h.append("../escape", {"type": "story", "story_id": "x", "at": 1.0})  # ignored, no file outside
    assert not (tmp_path.parent / "escape.jsonl").exists()


def test_reteach_events_fold_and_choose_the_way_that_works(tmp_path):
    from athena.reteach import best_style, style_order

    h = History(tmp_path)
    h.append("a1", {"type": "story", "story_id": "s1", "at": 1.0, "lang": "ne"})
    # parts never helps this child; the picture does
    for i, (styles, ok) in enumerate([(["hear", "parts"], False), (["parts"], False), (["hear", "picture"], True),
                                      (["picture"], True), (["parts", "picture"], True)]):
        h.append("a1", {"type": "reteach", "story_id": "s1", "at": 2.0 + i, "index": i, "word": "खसी", "styles": styles, "correct": ok})
    events = h.story("a1", "s1")["reteach"]
    assert len(events) == 5
    assert style_order(events, has_picture=True)[0] == "picture"
    assert style_order(events, has_picture=True)[-1] == "parts"
    assert "picture" not in style_order(events, has_picture=False)
    assert best_style(events) == {"style": "picture", "worked": 3, "tries": 3}
    assert style_order([], has_picture=True) == ["hear", "parts", "picture"]  # no evidence: default
    assert best_style([]) is None


def test_auto_reteach_picks_repeat_then_pause():
    from athena.reteach import auto_target

    w = lambda i, outcome, units=(): {"index": i, "outcome": outcome, "error_units": list(units)}  # noqa: E731
    words = [w(0, "correct"), w(1, "substituted", ["c:घ"]), w(2, "omitted"), w(3, "substituted", ["c:घ", "m:ा"])]
    assert auto_target(words, set()) == {"index": 1, "reason": "repeat"}  # घ behind two misses
    words = [w(0, "correct"), w(1, "substituted", ["c:घ"]), w(2, "omitted")]
    assert auto_target(words, {2}) == {"index": 2, "reason": "pause"}
    assert auto_target(words, {0}) is None  # paused but read it right: no interruption
    assert auto_target([w(0, "correct")], set()) is None


def test_anchor_ties_the_tricky_letter_to_a_known_word():
    from athena.assess.parts import word_parts
    from athena.reteach import anchors, style_order

    parts = [(list(p.units), i == 0) for i, p in enumerate(word_parts("ne", "खरायो"))]
    a = anchors("ne", "खरायो", parts)
    assert a and a[0]["glyph"] == "ख" and a[0]["phrase"].startswith("ख, ") and a[0]["word"] != "खरायो"
    assert "anchor" in style_order([], has_picture=False, has_anchor=True)
    assert "anchor" not in style_order([], has_picture=False)


def test_anchor_shown_is_the_anchor_spoken():
    from athena.assess.parts import word_parts
    from athena.reteach import anchors

    parts = [(list(p.units), True) for p in word_parts("en", "tap")]
    a = anchors("en", "tap", parts)
    assert [(x["glyph"], x["word"], x["phrase"]) for x in a] == [("t", "tent", "t for tent"), ("a", "apple", "a for apple")]
    assert all(x["phrase"].endswith(x["word"]) for x in a)  # what the child hears matches what they see
