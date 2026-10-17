"""Synthetic mastery sets for demo learners and the eval harness."""

from athena.verifier.english import _PHASES


def _ne(consonants: str, matras: str, conjuncts: str = "") -> frozenset[str]:
    return frozenset(
        [f"c:{c}" for c in consonants.split()]
        + [f"m:{m}" for m in matras.split()]
        + [f"k:{k}" for k in conjuncts.split()]
    )


def _en(graphemes: str, tricky: str = "") -> frozenset[str]:
    return frozenset([f"g:{g}" for g in graphemes.split()] + [f"w:{w}" for w in tricky.split()])


_P2 = _PHASES[2]
_P3 = _PHASES[3]

PRESETS: dict[str, tuple[str, frozenset[str]]] = {
    # Nepali
    "ne_early": ("ne", _ne("क ग च छ ज त द न प ब म र ल स ह अ आ", "ा ि ो")),
    "ne_basic": ("ne", _ne("क ख ग घ च छ ज त थ द ध न प फ ब भ म य र ल व स ह अ आ इ उ ए", "ा ि ी ु े ो ं ्")),
    "ne_mid": (
        "ne",
        _ne(
            "क ख ग घ ङ च छ ज झ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह अ आ इ ई उ ऊ ए ऐ ओ औ",
            "ा ि ी ु ू े ै ो ौ ं ँ ्",
        ),
    ),
    "ne_mid_conj": (
        "ne",
        _ne(
            "क ख ग घ ङ च छ ज झ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह अ आ इ ई उ ऊ ए ऐ ओ औ",
            "ा ि ी ु ू े ै ो ौ ं ँ ्",
            "क्ष त्र स्त न्छ न्त र्म ल्ल ट्ट न्न म्म",
        ),
    ),
    # English
    "en_satpin": ("en", _en("s a t p i n")),
    "en_satpin_sh": ("en", _en("s a t p i n sh", "a the")),
    "en_p2": ("en", _en(_P2, "a the i to no go")),
    "en_p3": ("en", _en(f"{_P2} {_P3}", "a the i to no go he she we me be was you they my her said")),
    "en_p3_no_sh": ("en", _en(f"{_P2} {_P3}".replace(" sh ", " "), "a the i to no go he she we was you")),
}


def preset(name: str) -> tuple[str, frozenset[str]]:
    return PRESETS[name]
