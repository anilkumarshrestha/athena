"""CLI: python scripts/generate.py ne_basic --name Sita [--theme ...] [--seed 1]"""

import argparse

from athena.agents.planner import plan
from athena.generate import generate, summary
from athena.presets import PRESETS, preset

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", choices=sorted(PRESETS))
    ap.add_argument("--name", default="Sita")
    ap.add_argument("--theme")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    language, mastery = preset(args.preset)
    p = plan(language, mastery, args.name, theme=args.theme, seed=args.seed)
    print(summary(generate(p)))
