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
    python scripts/coverage_bar.py --deff-wilson   # build day 11: the wilson_deff family
    python scripts/coverage_bar.py --deff-wilson --json design/coverage_deff_wilson.json

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

The design-effect Wilson family (build day 11, E11 item 5, DEC-18 (a))
-------------------------------------------------------------------
``--deff-wilson`` measures the clustered proportion's ``wilson_deff`` interval
(:func:`proofpack.stats.proportions.design_effect` and
:func:`~proofpack.stats.proportions.proportion_deff`, the engine's own functions) on the
proportion family's process above: ``u`` cases of ``w`` rows, the shared case effect at
``TAU2 = 0.5``, truth ``p``. No resampling, so R is larger (``DEFF_REPS``, 4000;
Monte-Carlo standard error about 0.005 at a coverage of 0.90). The grid is ``u`` in
:data:`DEFF_UNITS`, ``w`` in :data:`DEFF_W` and ``p`` in :data:`PROP_P`; every draw is
counted (a draw whose design effect is not estimable is not covered - there is none on
this grid, since ``u >= 2``). The last line prints the smallest ``u`` at which every grid
shape with at least ``u`` cases covers at or above the bar:
``stats.bootstrap.MIN_CASES_DEFF_WILSON`` is set by hand from it. Equal case sizes only;
mixed case sizes are not on the grid.

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
    MAX_CASE_SHARE_DEFF_WILSON,
    MAX_FROZEN_VARIANCE_SHARE,
    MAX_ROWS_PER_CASE_DEFF_WILSON,
    MIN_UNITS_PER_STRATUM,
    clustered_by_case,
    clustered_flat,
    deff_wilson_route,
    percentile_bounds,
)
from proofpack.stats.discrimination import auroc_mann_whitney
from proofpack.stats.proportions import design_effect, proportion_deff

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
#: build day 11 (E11 item 5): the wilson_deff family; v2 (E11 repair 1) widens the grid
#: to the shapes the two cold lenses on 2adfaaa measured below the bar
DEFF_SCRIPT_VERSION = "coverage_bar.py --deff-wilson v2 (E11 repair 1, 2026-10-02)"
DEFF_SEED = 20261002
DEFF_REPS = 4000
#: equal case sizes: u cases x w rows
DEFF_UNITS = (2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 40, 60)
DEFF_W = (1, 3, 8, 20, 50)
#: one dominant case: one case of B rows beside u - 1 cases of s rows
DEFF_DOM_UNITS = (5, 10, 20, 40, 60)
DEFF_DOM_SMALL = (1, 2, 4)
DEFF_DOM_BIG = (10, 20, 40, 60)
#: mixed case sizes: this cycle of sizes, repeated to u cases
DEFF_MIX_CYCLE = (1, 2, 3, 4, 5, 6, 8, 10, 12, 20)
DEFF_MIX_UNITS = (10, 20, 30, 40, 60)
#: the shared case effect's share of the latent variance: TAU2 (0.5, the process of the
#: build-day-5 and build-day-11 grids) sets the constant; 0.8 is recorded beside it
DEFF_TAU2 = (TAU2, 0.8)
#: truths that set the constant (PROP_P, at TAU2), and truths recorded beside them
DEFF_P_RECORDED = (0.95, 0.98)
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


def deff_shapes() -> list[tuple[str, tuple[int, ...]]]:
    """Every case-size shape of the ``--deff-wilson`` grid, in run order (v2): the equal
    family, the one-dominant-case family and the mixed family."""
    shapes: list[tuple[str, tuple[int, ...]]] = []
    for w in DEFF_W:
        for u in DEFF_UNITS:
            shapes.append(("equal", (w,) * u))
    for u in DEFF_DOM_UNITS:
        for s in DEFF_DOM_SMALL:
            for big in DEFF_DOM_BIG:
                shapes.append(("one_dominant", (big,) + (s,) * (u - 1)))
    for u in DEFF_MIX_UNITS:
        shapes.append(("mixed", tuple(DEFF_MIX_CYCLE[i % len(DEFF_MIX_CYCLE)] for i in range(u))))
    return shapes


def deff_cohort(rng, sizes: tuple[int, ...], p: float, tau2: float):
    """``prop_cohort``'s process with case sizes ``sizes`` and case-effect share ``tau2``:
    every row's marginal success probability is ``p``, so the truth is ``p``."""
    thr = _ND.inv_cdf(1.0 - p)
    k = len(sizes)
    b = rng.normal(0.0, math.sqrt(tau2), k)
    latent = np.repeat(b, sizes) + rng.normal(0.0, math.sqrt(1.0 - tau2), int(sum(sizes)))
    return latent > thr, np.repeat(np.arange(k), sizes)


def coverage_deff(seed_index: int, family: str, sizes, p, tau2, reps) -> dict:
    """The wilson_deff interval's coverage on one shape (E11 item 5; v2: any case sizes,
    any ``tau2``; a generator of its own per row, ``default_rng([DEFF_SEED, seed_index])``,
    so a row re-runs alone)."""
    rng = np.random.default_rng([DEFF_SEED, seed_index])
    n = int(sum(sizes))
    covered = 0
    widths = []
    reasons: dict[str, int] = {}
    for _ in range(reps):
        ind, ids = deff_cohort(rng, sizes, p, tau2)
        de = design_effect(ind, ids)
        reasons[de.reason] = reasons.get(de.reason, 0) + 1
        if de.deff is None:
            continue
        num = proportion_deff(int(ind.sum()), n, de, level=LEVEL)
        covered += num.ci_lo <= p <= num.ci_hi
        widths.append(num.ci_hi - num.ci_lo)
    return {
        "family": family,
        "u_cases": len(sizes),
        "n_rows": n,
        "largest_case_rows": int(max(sizes)),
        "rows_per_case": round(n / len(sizes), 4),
        "case_sizes": list(sizes) if family != "equal" else None,
        "truth": p,
        "tau2": tau2,
        "sets_constant": p in PROP_P and tau2 == TAU2,
        "route": deff_wilson_route(n, len(sizes), int(max(sizes)), True),
        "coverage": covered / reps,
        "mean_width": round(float(np.mean(widths)), 4) if widths else None,
        "deff_reasons": dict(sorted(reasons.items())),
        "reps": reps,
    }


def deff_threshold(rows: list[dict]) -> int | None:
    """The smallest grid ``u`` at which every shape that sets the constant
    (``sets_constant``: truth in :data:`PROP_P` at :data:`TAU2`), has at least ``u`` cases
    and lies inside
    the case-share and rows-per-case bounds of
    :func:`proofpack.stats.bootstrap.deff_wilson_route` covers at or above :data:`BAR`;
    ``None`` when no ``u`` does."""
    inside = [
        r
        for r in rows
        if r["sets_constant"]
        and r["largest_case_rows"] <= MAX_CASE_SHARE_DEFF_WILSON * r["n_rows"]
        and r["n_rows"] <= MAX_ROWS_PER_CASE_DEFF_WILSON * r["u_cases"]
    ]
    for u in sorted({r["u_cases"] for r in inside}):
        if all(r["coverage"] >= BAR for r in inside if r["u_cases"] >= u):
            return u
    return None


def deff_rows(reps: int, only: set[int] | None = None) -> list[dict]:
    """Every grid row, in run order (``only``: just these row indices, for the test that
    re-runs a sample of the committed rows)."""
    rows = []
    i = 0
    for tau2 in DEFF_TAU2:
        for p in PROP_P + DEFF_P_RECORDED:
            for family, sizes in deff_shapes():
                if only is None or i in only:
                    r = coverage_deff(i, family, sizes, p, tau2, reps)
                    r["index"] = i
                    rows.append(r)
                i += 1
    return rows


def main_deff(json_path: str | None, reps: int) -> int:
    t0 = time.time()
    print(f"{DEFF_SCRIPT_VERSION}; seed {DEFF_SEED}; R={reps}; nominal {LEVEL}; bar {BAR}")
    print(
        "wilson_deff family: equal, one-dominant-case and mixed case sizes; TAU2 "
        f"{', '.join(map(str, DEFF_TAU2))}; truth {', '.join(map(str, PROP_P))} at TAU2 "
        f"{TAU2} set the threshold, every other row is recorded"
    )
    rows = deff_rows(reps)
    print(f"{'family':>12} {'u':>3} {'n':>4} {'big':>3} {'tau2':>4} {'p':>4} {'cover':>6}  route")
    for r in rows:
        print(
            f"{r['family']:>12} {r['u_cases']:>3} {r['n_rows']:>4} {r['largest_case_rows']:>3} "
            f"{r['tau2']:>4} {r['truth']:>4} {r['coverage']:>6.3f}  {r['route']}"
        )
    threshold = deff_threshold(rows)
    print(
        f"\nsmallest u with every constant-setting shape at u or more cases, inside the "
        f"case-share ({MAX_CASE_SHARE_DEFF_WILSON}) and rows-per-case "
        f"({MAX_ROWS_PER_CASE_DEFF_WILSON}) bounds, >= {BAR}: {threshold}"
    )
    print(f"elapsed {time.time() - t0:.0f} s")
    if json_path:
        with open(json_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(
                {
                    "version": DEFF_SCRIPT_VERSION,
                    "seed": DEFF_SEED,
                    "reps": reps,
                    "level": LEVEL,
                    "bar": BAR,
                    "tau2": list(DEFF_TAU2),
                    "tau2_setting_the_constant": TAU2,
                    "truths_setting_the_constant": list(PROP_P),
                    "truths_recorded": list(DEFF_P_RECORDED),
                    "max_case_share": MAX_CASE_SHARE_DEFF_WILSON,
                    "max_rows_per_case": MAX_ROWS_PER_CASE_DEFF_WILSON,
                    "rows": rows,
                    "min_cases_meeting_bar": threshold,
                },
                fh,
                indent=1,
            )
            fh.write("\n")
    return 0


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
    mode.add_argument(
        "--deff-wilson",
        action="store_true",
        help=f"the wilson_deff family (build day 11), R={DEFF_REPS}",
    )
    ap.add_argument("--json", help="also write every row and the feasibility table here")
    ap.add_argument("--reps", type=int, default=None, help="--deff-wilson only: override R")
    args = ap.parse_args(argv)
    if args.deff_wilson:
        return main_deff(args.json, args.reps or DEFF_REPS)
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
