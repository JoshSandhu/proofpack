"""DEC-08 coverage bar: measure the cluster-bootstrap percentile interval's coverage.

Josh, 13 September 2026, DEC-08: *"One bar for both constants: a cell renders with its
tier annotation when the engine's own coverage simulation for that shape is >= 0.90,
and is refused with a typed reason below it. Day 5 E measures MIN_UNITS_PER_STRATUM and
MAX_FROZEN_VARIANCE_SHARE against that bar, sets both, and records the numbers in T7."*

This script is that simulation. It is deterministic (one seed, recorded in the output),
committed, and re-runnable::

    python scripts/coverage_bar.py --quick     # R=100, B=200; 41 s measured 2026-09-15
    python scripts/coverage_bar.py --full      # the recorded run, R=400, B=1000; 743-781 s
    python scripts/coverage_bar.py --full --json out.json

What it measures
----------------
For each *shape* in a grid it draws R cohorts from a known truth, forms the day-4
cluster-bootstrap percentile interval with the engine's own resampler
(:mod:`proofpack.stats.bootstrap` - ``clustered_by_case`` for an AUROC cell,
``clustered_flat`` for a proportion cell, ``percentile_bounds`` for the interval; the
deficient-class refusal is bypassed on purpose so that every shape is *measured*, and
the constants are then set against what was measured), and reports the share of the R
intervals that cover the truth. Nominal level 0.95; the DEC-08 bar is 0.90.

Two families of shapes:

* **AUROC cell.** Negatives: ``N`` pure-negative cases of one row (N in two sizes).
  Positives: ``u`` pure-positive cases of ``w = 3`` rows each (``u`` = 1..5), plus ``m``
  *mixed* cases carrying one positive and one negative row. When ``u = 1`` the pure
  stratum is frozen and the positive class's frozen variance share is
  ``w**2 / (w**2 + m)``; ``m`` is chosen so that share runs over 0.05..0.5. When
  ``u >= 2`` nothing is frozen and ``u`` is the unit count of the stratum that decides
  ``MIN_UNITS_PER_STRATUM`` (``m = 0`` rows, where the pure stratum is the *only* one).
  Scores: a case effect ``b ~ N(0, tau2)`` shared by the case's rows, a row effect
  ``N(0, 1 - tau2)``, plus ``delta`` for a positive row; marginally positives are
  ``N(delta, 1)`` and negatives ``N(0, 1)``. The truth is the expectation of the
  row-weighted Mann-Whitney statistic - the engine's estimand (the point estimate is not
  changed by clustering, D1/day-4 decision) - which is exact for pairs across cases,
  ``Phi(delta / sqrt(2))``, and for the within-case pairs of the mixed cases,
  ``Phi(delta / sqrt(2 (1 - tau2)))``, weighted by the pair counts.
* **Proportion cell.** ``u`` cases of ``w`` rows each (``u`` = 1..5, 10, 20, 40; ``w``
  in {1, 3}), a latent ``b_j + e_ij`` as above and the indicator ``latent > Phi^-1(1 - p)``
  so the truth is exactly ``p`` (two sizes: 0.5 and 0.9). A single stratum: the
  frozen-share dimension collapses to ``u = 1`` (share 1) and the grid is a grid over
  ``u``, which is what ``MIN_UNITS_PER_STRATUM`` decides for this route.

Reading the table
-----------------
The last block prints, for every candidate ``(MIN_UNITS_PER_STRATUM,
MAX_FROZEN_VARIANCE_SHARE)`` pair, whether every shape the rule would *render* has
measured coverage >= 0.90, and the loosest feasible pair. The constants in
``stats.bootstrap`` are set by hand from that block and their docstrings quote this
script's version, seed and the numbers. Nothing here claims the bar *guarantees*
coverage: it was measured on the shapes in this grid, with Monte-Carlo error of about
``sqrt(0.9 * 0.1 / R)`` - 0.03 at R = 100, 0.015 at R = 400 - per cell.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from statistics import NormalDist

import numpy as np

from proofpack.stats.bootstrap import (
    MAX_FROZEN_VARIANCE_SHARE,
    MIN_UNITS_PER_STRATUM,
    clustered_by_case,
    clustered_flat,
    percentile_bounds,
)
from proofpack.stats.discrimination import auroc_mann_whitney

SCRIPT_VERSION = "coverage_bar.py v1 (build day 5, 2026-09-15)"
SEED = 20260915
LEVEL = 0.95
BAR = 0.90
TAU2 = 0.5  # within-case correlation of the latent / score
DELTA = 1.5  # AUROC separation: Phi(1.5 / sqrt 2) = 0.8556
W_POS = 3  # rows per pure-positive case in the AUROC family
SHARES = (0.05, 0.10, 0.20, 0.30, 0.40, 0.50)
UNITS = (1, 2, 3, 4, 5)
NEG_SIZES = (30, 120)
PROP_UNITS = (1, 2, 3, 4, 5, 10, 20, 40)
PROP_W = (1, 3)
PROP_P = (0.5, 0.9)
CANDIDATE_MIN = (1, 2, 3, 4, 5, 6, 8, 10)
CANDIDATE_MAX = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)

_ND = NormalDist()


def mixed_cases_for_share(share: float, w: int) -> int:
    """``m`` such that ``w**2 / (w**2 + m)`` is as close as possible to ``share``."""
    return max(0, round(w * w * (1.0 - share) / share))


def auroc_truth(u: int, w: int, m: int, n_neg: int) -> float:
    n_pos = u * w + m
    n_neg_total = n_neg + m
    pairs = n_pos * n_neg_total
    within = m  # one positive-negative pair per mixed case shares the case effect
    across = pairs - within
    p_across = _ND.cdf(DELTA / math.sqrt(2.0))
    p_within = _ND.cdf(DELTA / math.sqrt(2.0 * (1.0 - TAU2)))
    return (across * p_across + within * p_within) / pairs


def auroc_cohort(rng: np.random.Generator, u: int, w: int, m: int, n_neg: int):
    """Scores, positives, case ids for one AUROC shape."""
    scores, pos, ids = [], [], []
    case = 0
    for _ in range(u):
        b = rng.normal(0.0, math.sqrt(TAU2))
        scores.extend(b + rng.normal(0.0, math.sqrt(1.0 - TAU2), w) + DELTA)
        pos.extend([True] * w)
        ids.extend([case] * w)
        case += 1
    for _ in range(n_neg):
        b = rng.normal(0.0, math.sqrt(TAU2))
        scores.append(b + rng.normal(0.0, math.sqrt(1.0 - TAU2)))
        pos.append(False)
        ids.append(case)
        case += 1
    for _ in range(m):
        b = rng.normal(0.0, math.sqrt(TAU2))
        e = rng.normal(0.0, math.sqrt(1.0 - TAU2), 2)
        scores.extend([b + e[0] + DELTA, b + e[1]])
        pos.extend([True, False])
        ids.extend([case, case])
        case += 1
    return np.asarray(scores), np.asarray(pos, dtype=bool), np.asarray(ids)


def prop_cohort(rng: np.random.Generator, u: int, w: int, p: float):
    thr = _ND.inv_cdf(1.0 - p)
    ind, ids = [], []
    for case in range(u):
        b = rng.normal(0.0, math.sqrt(TAU2))
        latent = b + rng.normal(0.0, math.sqrt(1.0 - TAU2), w)
        ind.extend((latent > thr).tolist())
        ids.extend([case] * w)
    return np.asarray(ind, dtype=bool), np.asarray(ids)


def coverage_auroc(rng, u, w, m, n_neg, reps, b_resamples) -> dict:
    truth = auroc_truth(u, w, m, n_neg)
    covered = 0
    widths = []
    describe = None
    for _ in range(reps):
        scores, pos, ids = auroc_cohort(rng, u, w, m, n_neg)
        resampler = clustered_by_case(pos, ids)
        if describe is None:
            describe = resampler.describe()
        vals = np.empty(b_resamples)
        for k in range(b_resamples):
            idx = resampler.draw(rng)
            got = pos[idx]
            vals[k] = (
                auroc_mann_whitney(scores[idx], got) if got.any() and not got.all() else np.nan
            )
        usable = vals[np.isfinite(vals)]
        lo, hi = percentile_bounds(usable, LEVEL)
        covered += lo <= truth <= hi
        widths.append(hi - lo)
    share = describe["frozen_variance_share"].get("positive", 0.0)
    return {
        "family": "auroc",
        "u_pure_positive_cases": u,
        "rows_per_pure_case": w,
        "mixed_cases": m,
        "n_negative_cases": n_neg,
        "frozen_share_positive": round(share, 4),
        "max_stratum_units_positive": max(describe["class_strata"]["positive"]),
        "truth": round(truth, 4),
        "coverage": covered / reps,
        "mean_width": round(float(np.mean(widths)), 4),
        "reps": reps,
    }


def coverage_prop(rng, u, w, p, reps, b_resamples) -> dict:
    covered = 0
    widths = []
    describe = None
    for _ in range(reps):
        ind, ids = prop_cohort(rng, u, w, p)
        resampler = clustered_flat(ids, n_rows=ind.shape[0])
        if describe is None:
            describe = resampler.describe()
        vals = np.empty(b_resamples)
        for k in range(b_resamples):
            vals[k] = float(ind[resampler.draw(rng)].mean())
        lo, hi = percentile_bounds(vals, LEVEL)
        covered += lo <= p <= hi
        widths.append(hi - lo)
    return {
        "family": "proportion",
        "u_cases": u,
        "rows_per_case": w,
        "truth": p,
        "frozen_share_all": round(describe["frozen_variance_share"]["all"], 4),
        "max_stratum_units_all": max(describe["class_strata"]["all"]),
        "coverage": covered / reps,
        "mean_width": round(float(np.mean(widths)), 4),
        "reps": reps,
    }


def renders(row: dict, min_units: int, max_share: float) -> bool:
    """Would the day-4 rule render this shape under the candidate constants?"""
    if row["family"] == "auroc":
        share, units = row["frozen_share_positive"], row["max_stratum_units_positive"]
    else:
        share, units = row["frozen_share_all"], row["max_stratum_units_all"]
    return not (units < min_units or share >= max_share)


def feasibility(rows: list[dict]) -> tuple[list[dict], tuple[int, float] | None]:
    table = []
    best = None
    for mn in CANDIDATE_MIN:
        for mx in CANDIDATE_MAX:
            rendered = [r for r in rows if renders(r, mn, mx)]
            worst = min((r["coverage"] for r in rendered), default=None)
            ok = worst is not None and worst >= BAR
            table.append(
                {
                    "min_units": mn,
                    "max_share": mx,
                    "rendered": len(rendered),
                    "worst_coverage": worst,
                    "meets_bar": ok,
                }
            )
    # loosest = smallest MIN admitting any MAX, then the largest MAX at that MIN
    for mn in CANDIDATE_MIN:
        feasible = [t["max_share"] for t in table if t["min_units"] == mn and t["meets_bar"]]
        if feasible:
            best = (mn, max(feasible))
            break
    return table, best


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--quick", action="store_true", help="R=100, B=200")
    mode.add_argument("--full", action="store_true", help="R=400, B=1000 (the recorded run)")
    ap.add_argument("--json", help="also write every row and the feasibility table here")
    args = ap.parse_args(argv)
    reps, b = (100, 200) if args.quick else (400, 1000)
    rng = np.random.default_rng(SEED)
    t0 = time.time()
    rows: list[dict] = []
    print(f"{SCRIPT_VERSION}; seed {SEED}; R={reps}, B={b}; nominal {LEVEL}; bar {BAR}")
    print(
        f"current constants: MIN_UNITS_PER_STRATUM={MIN_UNITS_PER_STRATUM}, "
        f"MAX_FROZEN_VARIANCE_SHARE={MAX_FROZEN_VARIANCE_SHARE}"
    )
    print("\nAUROC family (u pure-positive cases x 3 rows, m mixed cases, N negative cases)")
    head = ("u", "m", "N", "share", "maxU", "truth", "cover", "width")
    print(f"{head[0]:>2} {head[1]:>4} {head[2]:>4} " + " ".join(f"{h:>6}" for h in head[3:]))
    for n_neg in NEG_SIZES:
        for u in UNITS:
            ms = (
                [mixed_cases_for_share(s, W_POS) for s in SHARES]
                if u == 1
                else [0, mixed_cases_for_share(0.2, W_POS)]
            )
            for m in ms:
                r = coverage_auroc(rng, u, W_POS, m, n_neg, reps, b)
                rows.append(r)
                print(
                    f"{u:>2} {m:>4} {n_neg:>4} {r['frozen_share_positive']:>6.3f} "
                    f"{r['max_stratum_units_positive']:>6} {r['truth']:>6.4f} "
                    f"{r['coverage']:>6.3f} {r['mean_width']:>6.3f}"
                )
                sys.stdout.flush()
    print("\nProportion family (u cases x w rows, truth p)")
    print(f"{'u':>2} {'w':>2} {'p':>4} {'share':>6} {'maxU':>4} {'cover':>6} {'width':>6}")
    for p in PROP_P:
        for w in PROP_W:
            for u in PROP_UNITS:
                r = coverage_prop(rng, u, w, p, reps, b)
                rows.append(r)
                print(
                    f"{u:>2} {w:>2} {p:>4} {r['frozen_share_all']:>6.3f} "
                    f"{r['max_stratum_units_all']:>4} {r['coverage']:>6.3f} {r['mean_width']:>6.3f}"
                )
                sys.stdout.flush()
    table, best = feasibility(rows)
    print("\nFeasibility: does every shape the rule renders cover >= 0.90?")
    print(f"{'MIN':>4} " + " ".join(f"{mx:>5}" for mx in CANDIDATE_MAX))
    for mn in CANDIDATE_MIN:
        cells = [t for t in table if t["min_units"] == mn]
        print(
            f"{mn:>4} "
            + " ".join(
                (
                    "  ok "
                    if t["meets_bar"]
                    else f"{t['worst_coverage']:.2f} "
                    if t["worst_coverage"] is not None
                    else "  -  "
                )
                for t in cells
            )
        )
    print("\nloosest feasible pair (smallest MIN, then largest MAX):", best)
    print(f"elapsed {time.time() - t0:.0f} s")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "version": SCRIPT_VERSION,
                    "seed": SEED,
                    "reps": reps,
                    "B": b,
                    "rows": rows,
                    "feasibility": table,
                    "loosest": best,
                },
                fh,
                indent=1,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
