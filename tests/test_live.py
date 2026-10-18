"""Live follow-along tracker. Offline."""

from athena.assess.live import LiveTracker

STORY = "आमा र बिरालो घरमा छन्। बिरालो दूध पिउँछ।"


def test_pointer_follows_reading():
    t = LiveTracker("ne", STORY)
    assert t.update("") == ([], 0)
    assert t.update("आमा र") == ([0, 1], 2)
    assert t.update("आमा र बिरा")[1] == 2  # partial word: not reached yet
    assert t.update("आमा र बिरालो घरमा")[1] == 4


def test_spelling_variants_from_stt_count():
    # streaming STT writes दुध / पिउछ for दूध / पिउँछ: same sound
    heard, nxt = LiveTracker("ne", STORY).update("आमा र बिरालो घरमा छन् बिरालो दुध पिउछ")
    assert heard == list(range(8)) and nxt == 8


def test_skipped_word_does_not_stall():
    heard, nxt = LiveTracker("ne", STORY).update("आमा बिरालो घरमा")
    assert heard == [0, 2, 3] and nxt == 4


def test_repeat_does_not_move_back():
    _, nxt = LiveTracker("ne", STORY).update("आमा र बिरालो आमा")
    assert nxt == 3


def test_english():
    heard, nxt = LiveTracker("en", "Sam sat in a ship.").update("sam sat in a")
    assert heard == [0, 1, 2, 3] and nxt == 4
