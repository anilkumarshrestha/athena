"""Eval A: constraint satisfaction + cost/latency, per language.

  python eval/run_eval.py --n 3            # 3 generations per language
  python eval/run_eval.py --n 50 --workers 4

Cycles through mastery presets and themes with fixed seeds. Text only (no images):
the illustrator is irrelevant to the constraint numbers.
Writes eval/results/<stamp>.jsonl (one GenerationResult per line) and <stamp>.summary.json.
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from athena.agents.planner import plan  # noqa: E402
from athena.generate import generate  # noqa: E402
from athena.models import GenerationResult  # noqa: E402
from athena.presets import preset  # noqa: E402

RESULTS = ROOT / "eval" / "results"
PRICES = ROOT / "eval" / "prices.json"

SETS = {
    "ne": ["ne_basic", "ne_mid", "ne_mid_conj", "ne_early"],
    "en": ["en_satpin_sh", "en_p2", "en_p3", "en_p3_no_sh"],
}
NAMES = {"ne": "सीता", "en": "Sita"}


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(q * (len(xs) - 1)))] if xs else 0.0


def cost_usd(r: GenerationResult, prices: dict) -> float | None:
    total = 0.0
    for a in r.attempts:
        p = next((v for k, v in prices.items() if a.usage.model.startswith(k)), None)
        if not p or p.get("input_per_m") is None:
            return None
        out = a.usage.output_tokens + a.usage.thinking_tokens  # thinking billed as output
        total += a.usage.input_tokens / 1e6 * p["input_per_m"] + out / 1e6 * p["output_per_m"]
    return total


def summarize(rows: list[tuple[str, GenerationResult]], prices: dict) -> dict:
    out = {}
    for lang in ("ne", "en"):
        rs = [r for _, r in rows if r.plan.language == lang]
        if not rs:
            continue
        lat = [r.total_latency_ms for r in rs]
        costs = [cost_usd(r, prices) for r in rs]
        outcomes = {o: sum(r.outcome == o for r in rs) for o in ("first_pass", "regenerated", "pruned", "wordlist")}
        out[lang] = {
            "n": len(rs),
            "first_pass_ok_rate": outcomes["first_pass"] / len(rs),
            "first_pass_mean_violations": statistics.mean(r.first_pass_violations for r in rs),
            "final_violation_count_total": sum(r.final_violation_count for r in rs),
            "mean_attempts": statistics.mean(len(r.attempts) for r in rs),
            "fallback_rate": (outcomes["pruned"] + outcomes["wordlist"]) / len(rs),
            "outcomes": outcomes,
            "latency_ms_p50": pct(lat, 0.5),
            "latency_ms_p95": pct(lat, 0.95),
            "tokens_mean": {
                k: statistics.mean(sum(getattr(a.usage, k) for a in r.attempts) for r in rs)
                for k in ("input_tokens", "output_tokens", "thinking_tokens")
            },
            "cost_usd_per_story": statistics.mean(costs) if all(c is not None for c in costs) else None,
            "models": sorted({a.usage.model for r in rs for a in r.attempts}),
        }
    return out


def run_one(job: tuple[str, str, int]) -> tuple[str, GenerationResult | str]:
    """Returns the result, or an error string. 429s are retried with backoff."""
    lang, set_name, i = job
    _, mastery = preset(set_name)
    p = plan(lang, mastery, NAMES[lang], seed=i)  # planner picks a readable theme
    for wait in (10, 30, 60, None):
        try:
            return set_name, generate(p, log=False)
        except Exception as e:  # noqa: BLE001 - recorded, not hidden
            if wait is None or "429" not in str(e):
                return set_name, f"{lang}: {type(e).__name__}: {str(e)[:200]}"
            time.sleep(wait)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3, help="generations per language")
    ap.add_argument("--workers", type=int, default=2, help="Vertex 429s above ~2 concurrent")
    args = ap.parse_args()

    jobs = [(lang, SETS[lang][i % len(SETS[lang])], i) for lang in ("ne", "en") for i in range(args.n)]
    prices = json.loads(PRICES.read_text()) if PRICES.exists() else {}
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RESULTS.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    rows: list[tuple[str, GenerationResult]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(args.workers) as pool, (RESULTS / f"{stamp}.jsonl").open("w", encoding="utf-8") as f:
        for fut in as_completed([pool.submit(run_one, j) for j in jobs]):
            set_name, r = fut.result()
            if isinstance(r, str):
                errors.append(r)
                print(f"ERROR {set_name}: {r}", flush=True)
                continue
            rows.append((set_name, r))
            f.write(json.dumps({"set": set_name, **r.model_dump()}, ensure_ascii=False) + "\n")
            f.flush()
            print(
                f"{r.plan.language} {set_name:<13} {r.outcome:<11} attempts={len(r.attempts)} "
                f"first_pass_violations={r.first_pass_violations:<3} {r.total_latency_ms:>6}ms  {r.title}",
                flush=True,
            )

    shipped_violations = sum(r.final_violation_count for _, r in rows)
    problems = []
    if errors:
        problems.append(f"{len(errors)} job(s) errored")
    if len(rows) + len(errors) != len(jobs):
        problems.append(f"{len(jobs) - len(rows) - len(errors)} job(s) missing")
    if shipped_violations:
        problems.append(f"{shipped_violations} violation(s) shipped: verifier guarantee broken")

    summary = {
        "stamp": stamp,
        "status": "FAILED" if problems else "SUCCESS",
        "problems": problems,
        "jobs": len(jobs),
        "completed": len(rows),
        "n_per_lang": args.n,
        "wall_s": round(time.perf_counter() - t0, 1),
        "errors": errors,
        **summarize(rows, prices),
    }
    (RESULTS / f"{stamp}.summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # Last line is the verdict; exit code matches it.
    print(f"EVAL {summary['status']}: {len(rows)}/{len(jobs)} completed" + (f" — {'; '.join(problems)}" if problems else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
