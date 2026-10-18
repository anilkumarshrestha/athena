"""Eval M: maths word problems. Do the code checks hold, and how often does the model pass?

  python eval/maths_eval.py --n 20             # 20 problems per language
  python eval/maths_eval.py --n 20 --workers 2

For each problem: where it came from (model / template / bare), how many drafts, why drafts
were rejected (unreadable word, wrong numbers, no question, singular verb, meaning), latency.
Every shipped problem is re-checked in code: readable, exact numbers, a question at the end.
Writes eval/results/maths-<stamp>.jsonl and maths-<stamp>.summary.json.
"""

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from athena.agents.planner import plan  # noqa: E402
from athena.maths import _check, _verifier, make_problem, numbers_in, quick_problem  # noqa: E402
from athena.presets import preset  # noqa: E402

PRESETS = {"ne": ["ne_basic", "ne_mid", "ne_mid_conj"], "en": ["en_p2", "en_p3"]}
NAMES = {"ne": ("सीता", "girl"), "en": ("Sita", "girl")}


def reason_kind(text: str) -> str:
    if text.startswith("model error"):
        return "model_error"
    if "uses" in text:
        return "unreadable_word"
    if "numbers must be" in text:
        return "wrong_numbers"
    if "question" in text and "?" in text:
        return "no_question"
    if "spell the name" in text or "as one word" in text:
        return "name_form"
    if "plural verb" in text:
        return "singular_verb"
    if "ADD more" in text or "TAKE AWAY" in text or "meaning" in text:
        return "meaning"
    return "other"


def one(lang: str, i: int) -> dict:
    name = PRESETS[lang][i % len(PRESETS[lang])]
    level = 1 + i % 3
    _, mastery = preset(name)
    learner, gender = NAMES[lang]
    p_plan = plan(lang, mastery, learner, seed=i, level=level, child_gender=gender)
    t0 = time.perf_counter()
    p = make_problem(p_plan, seed=i)
    ms = int((time.perf_counter() - t0) * 1000)
    quick = quick_problem(p_plan, seed=i)
    # The shipped problem, re-checked in code (bare "३ + २ = ?" has no question words to check).
    recheck = [] if p.source == "bare" else _check(p, p.sentences, _verifier(p_plan, p), learner)
    return {
        "lang": lang, "preset": name, "level": level, "a": p.a, "b": p.b, "op": p.op, "answer": p.answer,
        "source": p.source, "drafts": len(p.attempts), "latency_ms": ms, "sentences": p.sentences,
        "rejections": [reason_kind(x) for a in p.attempts for x in a["problems"]],
        "recheck": recheck, "numbers_ok": p.source == "bare" or numbers_in(" ".join(p.sentences)) == [p.a, p.b],
        "quick_available": quick is not None,
    }


def summarize(rows: list[dict]) -> dict:
    out = {}
    for lang in ("ne", "en"):
        rs = [r for r in rows if r["lang"] == lang]
        if not rs:
            continue
        n = len(rs)
        model = [r for r in rs if r["source"] == "model"]
        lat = sorted(r["latency_ms"] for r in rs)
        out[lang] = {
            "n": n,
            "source": dict(Counter(r["source"] for r in rs)),
            "model_rate": round(len(model) / n, 2),
            "first_draft_rate": round(sum(1 for r in model if r["drafts"] == 1) / n, 2),
            "rejections": dict(Counter(k for r in rs for k in r["rejections"])),
            "shipped_failing_checks": sum(1 for r in rs if r["recheck"] or not r["numbers_ok"]),
            "quick_template_available": round(sum(r["quick_available"] for r in rs) / n, 2),
            "latency_ms_p50": int(statistics.median(lat)),
            "latency_ms_p90": lat[min(n - 1, int(0.9 * n))],
            "answers": dict(sorted(Counter(r["answer"] for r in rs).items())),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="problems per language")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    res_dir = ROOT / "eval" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(one, lang, i) for lang in ("ne", "en") for i in range(args.n)]
        for f in as_completed(futs):
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001 - count it, keep going
                r = {"lang": "?", "error": f"{type(e).__name__}: {e}"}
                print("ERROR", r["error"], flush=True)
            rows.append(r)
            if "source" in r:
                print(f"[{r['lang']} L{r['level']}] {r['source']:8} drafts={r['drafts']} {r['latency_ms']}ms  {' '.join(r['sentences'])}", flush=True)
    good = [r for r in rows if "source" in r]
    with (res_dir / f"maths-{stamp}.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {"stamp": stamp, "errors": len(rows) - len(good), **summarize(good)}
    (res_dir / f"maths-{stamp}.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    failing = sum(v.get("shipped_failing_checks", 0) for v in summary.values() if isinstance(v, dict))
    verdict = "SUCCESS" if not summary["errors"] and not failing else "FAIL"
    print(f"VERDICT: {verdict} ({len(good)}/{len(rows)} ran, {failing} shipped problems failing checks)")


if __name__ == "__main__":
    main()
