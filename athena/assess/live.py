"""Live follow-along: map a growing transcript onto the story while the child reads.

Only a visual guide (which word is next, which words were heard). It never scores:
the final reading is still assessed from the full recording (athena/assess/align.py).

Greedy forward matching on the pronunciation fold, with a small look-ahead so a
skipped word does not stall the highlight, and no going backwards (re-reading a
word does not move the pointer back).
"""

import difflib

from athena.assess.align import fold, tokens

LOOKAHEAD = 3  # how many story words ahead a heard word may match (skips)
SIM = 0.75  # near-miss still counts as "reached" for the highlight


class LiveTracker:
    def __init__(self, language: str, reference: str) -> None:
        self.lang = language
        self.ref = [fold(language, w) for w in tokens(language, reference)]

    def update(self, transcript: str) -> tuple[list[int], int]:
        """(story word indices heard so far, index of the next word to read)."""
        heard: list[int] = []
        p = 0
        hyp = [fold(self.lang, w) for w in tokens(self.lang, transcript)]
        for k, h in enumerate(hyp):
            # The last word of a live transcript may still be mid-word ("बिरा…"): exact only.
            fuzzy = k < len(hyp) - 1
            for j in range(p, min(p + LOOKAHEAD + 1, len(self.ref))):
                if h == self.ref[j] or (fuzzy and difflib.SequenceMatcher(a=h, b=self.ref[j]).ratio() >= SIM):
                    heard.append(j)
                    p = j + 1
                    break
        return heard, p
