"""DEC-08 coverage of the clustered calibration intervals (repair round 1, build day 6).

Josh, 13 September 2026, DEC-08: a cell renders with its tier annotation when the
engine's own coverage simulation for that shape is >= 0.90. Lens 1 of 2026-09-18
(FA-B1) measured the build-day-6 clustered route - cases resampled *within outcome
class* - for the O:E ratio, the intercept-in-the-large and the joint intercept at
0.61-0.79 on 200 x 1, 200 x 2 and 60 x 3 cases (nominal 0.95). The repair resamples
cases in a single stratum for those quantities
(:func:`proofpack.stats.bootstrap.clustered_flat`), and this script is the measurement
DEC-08 asks for. Deterministic, committed, re-runnable::

    python scripts/coverage_calibration.py --quick   # R=100, B=200
    python scripts/coverage_calibration.py --full    # R=300, B=200: the recorded run
    python scripts/coverage_calibration.py --full --json out.json
    python scripts/coverage_calibration.py --full --seed 7   # a second seed

What it measures
----------------
The lens's data-generating process, reproduced here rather than reused: ``n_cases``
cases of ``rows_per_case`` rows; the row's true logit is ``-0.5 + b_case + e_row`` with
``b_case ~ N(0, 0.8)`` shared by the case's rows and ``e_row ~ N(0, 0.9)``; the score
``p`` is the true probability, so the label ``y ~ Bernoulli(p)`` is calibrated to it and
the truths are O:E = 1, intercept-in-the-large = 0, slope = 1, joint intercept = 0. For
each of the three shapes the lens measured (200 x 1, 200 x 2, 60 x 3) it draws R cohorts,
forms the engine's block once under the i.i.d. declarations and once under a declared
clustered plan with the same rows, and reports the share of the R rendered intervals
that cover the truth, with the mean width. Cohorts with fewer than two events or two
non-events are skipped and counted.

Nothing here claims the interval *guarantees* coverage: it is measured on this process
at these three shapes, with Monte-Carlo error of about ``sqrt(0.9 * 0.1 / R)`` - 0.03
at R = 100, 0.017 at R = 300 - per cell. The Brier, reference Brier and IPA are not
measured here: they keep the outcome-stratified resampler ``stats.subgroups._brier_cell``
uses (module docstring of ``stats.calibration``).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from conftest import make_criteria  # noqa: E402
from proofpack.io.declare import validate_dict  # noqa: E402
from proofpack.stats.bootstrap import BootstrapPolicy  # noqa: E402
from proofpack.stats.calibration import calibration_block  # noqa: E402

VERSION = "coverage_calibration.py v1 (build day 6 repair round 1, 2026-09-18)"
SEED = 2026
SHAPES = ((200, 1), (200, 2), (60, 3))
TRUTH = {"oe": 1.0, "intercept_large": 0.0, "slope": 1.0, "intercept": 0.0}


def simulate(n_cases: int, rows_per_case: int, reps: int, n_resamples: int, rng) -> dict:
    decl = validate_dict(make_criteria())
    decl_c = validate_dict(make_criteria(clustering={"unit": "case_id", "declared_by": "t"}))
    ids = np.repeat(np.arange(n_cases), rows_per_case)
    cover = {r: {q: 0 for q in TRUTH} for r in ("iid", "clustered")}
    width = {r: {q: 0.0 for q in TRUTH} for r in ("iid", "clustered")}
    rendered = {r: {q: 0 for q in TRUTH} for r in ("iid", "clustered")}
    refused: dict[str, int] = {}
    skipped = 0
    for rep in range(reps):
        case_eff = rng.normal(0.0, 0.8, n_cases)
        eta = -0.5 + np.repeat(case_eff, rows_per_case) + rng.normal(0.0, 0.9, ids.shape[0])
        p = 1.0 / (1.0 + np.exp(-eta))
        y = rng.uniform(size=p.shape[0]) < p
        if y.sum() < 2 or (~y).sum() < 2:
            skipped += 1
            continue
        pol = BootstrapPolicy(n_resamples=n_resamples, seed=rep + 1)
        blocks = {
            "iid": calibration_block(p, y, decl, policy=pol).block,
            "clustered": calibration_block(p, y, decl_c, cluster_ids=ids, policy=pol).block,
        }
        for route, block in blocks.items():
            for q, truth in TRUTH.items():
                num = block[q]["number"]
                if num["ci_lo"] is None:
                    key = f"{route}:{q}:{num.get('not_estimable_reason')}"
                    refused[key] = refused.get(key, 0) + 1
                    continue
                rendered[route][q] += 1
                cover[route][q] += int(num["ci_lo"] <= truth <= num["ci_hi"])
                width[route][q] += num["ci_hi"] - num["ci_lo"]
    out = {
        "n_cases": n_cases,
        "rows_per_case": rows_per_case,
        "skipped": skipped,
        "refused": refused,
    }
    for route in ("iid", "clustered"):
        out[route] = {
            q: {
                "rendered": rendered[route][q],
                "coverage": (cover[route][q] / rendered[route][q]) if rendered[route][q] else None,
                "mean_width": (
                    (width[route][q] / rendered[route][q]) if rendered[route][q] else None
                ),
            }
            for q in TRUTH
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--quick", action="store_true", help="R=100, B=200")
    mode.add_argument("--full", action="store_true", help="R=300, B=200 (the recorded run)")
    ap.add_argument("--json", help="also write every row here")
    ap.add_argument("--seed", type=int, default=SEED, help=f"generator seed (default {SEED})")
    args = ap.parse_args(argv)
    reps, n_resamples = (100, 200) if args.quick else (300, 200)
    print(f"{VERSION}; seed {args.seed}; R={reps}, B={n_resamples}; nominal 0.95; bar 0.90")
    rng = np.random.default_rng(args.seed)
    t0 = time.time()
    rows = []
    for n_cases, rows_per_case in SHAPES:
        row = simulate(n_cases, rows_per_case, reps, n_resamples, rng)
        rows.append(row)
        print(f"\nshape {n_cases} cases x {rows_per_case} rows (skipped {row['skipped']})")
        print(f"{'quantity':>16} {'iid cov':>8} {'width':>7} {'clustered cov':>14} {'width':>7}")
        for q in TRUTH:
            a, b = row["iid"][q], row["clustered"][q]
            fmt = lambda v: "   -   " if v is None else f"{v:.3f}"  # noqa: E731
            print(
                f"{q:>16} {fmt(a['coverage']):>8} {fmt(a['mean_width']):>7} "
                f"{fmt(b['coverage']):>14} {fmt(b['mean_width']):>7}"
            )
        if row["refused"]:
            print(f"refused: {row['refused']}")
    print(f"\nelapsed {time.time() - t0:.0f} s")
    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {"version": VERSION, "seed": args.seed, "R": reps, "B": n_resamples, "rows": rows},
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
