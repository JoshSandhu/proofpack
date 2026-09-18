"""DEC-12(ii): the mutation sweep as a committed script.

Plants a declared list of mutants - each ``(id, file, regex, replacement, expected count)``
- one at a time into a *copy* of the working tree, runs the named pytest marker there,
and prints killed / survived per mutant. A mutant is **killed** when the marker's tests
fail against it and **survived** when they all pass. A surviving mutant that is not
equivalent (i.e. it changes behaviour) is a coverage gap: close it with a test, or carry
it in the handoff note with the reason.

Why a copy and not a worktree: the sweep must run against the *working tree* (the code
being handed off, committed or not), and a git worktree can only check out a commit. The
copy holds ``src``, ``tests``, ``schema``, ``fixtures``, ``design`` and
``pyproject.toml``; ``PYTHONPATH`` is forced to the copy's ``src`` for every subprocess.
What is inspected before any mutant runs: one ``python -c "import proofpack"``
subprocess with that environment and the copy as its working directory, whose
``proofpack.__file__`` must resolve under the copy's ``src`` or the sweep exits. That is
a check on one import in one subprocess with the same environment the pytest
subprocesses receive; it is not a check inside pytest. Attempts to defeat it recorded by
the day-5 regression lens (2026-09-15, RG-N6): ``PYTHONPATH`` pre-set to the main tree's
``src`` and the working directory set to the main tree - both resolved to the copy,
because ``env_for`` overwrites ``PYTHONPATH`` and ``cwd`` is the copy.

Usage::

    python scripts/mutation_sweep.py --marker day5            # the day-5 list against -m day5
    python scripts/mutation_sweep.py --marker day6            # the day-6 list against -m day6
    python scripts/mutation_sweep.py --marker day5 --only ref_largest_to_smallest
    python scripts/mutation_sweep.py --list
    python scripts/mutation_sweep.py --marker day5 --fail-on-survivor   # exit 1 if any survive

The round-7 repair of build day 4 ran this by hand as a scratch file; it found that the
two changes that round's commit narrated most prominently were unobservable, which is
why it is a script now (DEC-12, Josh, 13 September 2026).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COPIED = ("src", "tests", "schema", "fixtures", "design", "pyproject.toml")
SUBGROUPS = "src/proofpack/stats/subgroups.py"
DISCRIMINATION = "src/proofpack/stats/discrimination.py"
CALIBRATION = "src/proofpack/stats/calibration.py"
OUTPUT_SCHEMA = "schema/output_schema_v1.json"


@dataclass(frozen=True)
class Mutant:
    id: str
    file: str
    pattern: str
    replacement: str
    count: int = 1  # how many matches the pattern must have (all are replaced)
    what: str = ""  # the behaviour it changes, for the report
    day: int = 5  # the build day whose marker the mutant is meant to be killed by


#: The day-5 list, then the day-6 list. Every one changes behaviour; none is intended to
#: be equivalent. ``--marker dayN`` runs the mutants declared for day N.
MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "ref_largest_to_smallest",
        SUBGROUPS,
        r"largest = max\(lv\.n for lv in candidates\)",
        "largest = min(lv.n for lv in candidates)",
        what="reference-level choice: 'largest' picks the smallest level",
    ),
    Mutant(
        "ref_tie_last_in_order",
        SUBGROUPS,
        r"return tied\[0\]\.label,",
        "return tied[-1].label,",
        what="reference tie rule: last in level order instead of first",
    ),
    Mutant(
        "unknown_row_can_be_reference",
        SUBGROUPS,
        r"candidates = \[lv for lv in levels if not lv\.is_unknown\]",
        "candidates = list(levels)",
        what="the Unknown row becomes a candidate reference level",
    ),
    Mutant(
        "complement_excludes_unknown",
        SUBGROUPS,
        r"np\.concatenate\(\[lv\.rows for lv in attr\.levels\]\)\n            if attr\.levels",
        "np.concatenate([lv.rows for lv in attr.levels if not lv.is_unknown])\n"
        "            if attr.levels",
        what="complement definition: the Unknown row is left out of every complement",
    ),
    Mutant(
        "unknown_row_not_marked",
        SUBGROUPS,
        r"levels\.append\(_Level\(attribute, UNKNOWN_LEVEL, unknown_rows, True\)\)",
        "levels.append(_Level(attribute, UNKNOWN_LEVEL, unknown_rows, False))",
        what="Unknown row membership: missing rows form a level not marked is_unknown_row",
    ),
    Mutant(
        "tier_counts_rows_not_units",
        SUBGROUPS,
        r"tier_flags = precision_flags\(n_units, event_units\)",
        "tier_flags = precision_flags(n, events)",
        what="tier thresholds measured in rows instead of resampling units",
    ),
    Mutant(
        "evaluability_ten_to_five",
        SUBGROUPS,
        r"^AUROC_EVALUABLE_CLASS = 10$",
        "AUROC_EVALUABLE_CLASS = 5",
        what="the 10/10 AUROC evaluability rule loosened to 5",
    ),
    Mutant(
        "evaluability_off_by_one",
        SUBGROUPS,
        r"if n_pos < AUROC_EVALUABLE_CLASS:",
        "if n_pos <= AUROC_EVALUABLE_CLASS:",
        what="the 10/10 rule refuses a level with exactly ten positives",
    ),
    Mutant(
        "difference_sign_flipped",
        SUBGROUPS,
        r"number = difference_unpaired\(k1, n1, k2, n2, level\)",
        "number = difference_unpaired(k2, n2, k1, n1, level)",
        what="the sign of a proportion difference (other minus level)",
    ),
    Mutant(
        "holm_no_running_maximum",
        SUBGROUPS,
        r"running = max\(running, min\(1\.0, pvalues\[i\] \* \(m - rank\)\)\)",
        "running = min(1.0, pvalues[i] * (m - rank))",
        what="Holm ordering: the step-down monotonicity is dropped",
    ),
    Mutant(
        "holm_unsorted",
        SUBGROUPS,
        r"order = sorted\(range\(m\), key=lambda i: pvalues\[i\]\)",
        "order = list(range(m))",
        what="Holm ordering: p-values are not sorted before the step-down",
    ),
    Mutant(
        "fpr_gap_sign",
        SUBGROUPS,
        r'"fpr_gap": _mirror_cell\(d\[arrays\.sp_key\]\),',
        '"fpr_gap": d[arrays.sp_key],',
        what="fpr_gap emitted as the specificity difference instead of its mirror",
    ),
    Mutant(
        "clustered_span_refusal_off",
        SUBGROUPS,
        r"if _shared_cases\(ids_a, ids_b\):",
        "if False and _shared_cases(ids_a, ids_b):",
        count=2,
        what="the clustered refusal: cases spanning both sides no longer refuse",
    ),
    Mutant(
        "proportion_cells_lose_cluster_ids",
        SUBGROUPS,
        r"cluster_ids=arrays\.ids_for\(rows\),(\n        level=arrays\.level,\n    \)"
        r"\n\n\ndef _proportion_difference)",
        r"cluster_ids=None,\1",
        what="DEC-10 / X2: proportion cells reach Wilson on clustered rows",
    ),
    Mutant(
        "fisher_branch_removed",
        SUBGROUPS,
        r"if n_levels == 2 and min_expected < fisher_below:",
        "if False:",
        what="Fisher exact never replaces the chi-square",
    ),
    Mutant(
        "selection_rate_label",
        SUBGROUPS,
        r'^SELECTION_RATE_LABEL = "descriptive_not_target"$',
        'SELECTION_RATE_LABEL = "target"',
        what="the selection-rate gap loses its R2 section 4 label",
    ),
    Mutant(
        "undeclared_not_exploratory",
        SUBGROUPS,
        r"if spec is not None else EXPLORATORY\)",
        'if spec is not None else "declared")',
        what="an undeclared attribute is no longer labelled exploratory",
    ),
    Mutant(
        "default_age_bands_changed",
        SUBGROUPS,
        r"\(\(0, 40\), \(40, 65\), \(65, 80\), \(80, 200\)\)",
        "((0, 18), (18, 40), (40, 65), (65, 80), (80, 200))",
        what="the engine-default age bands drift from D1's",
    ),
    Mutant(
        "age_bands_closed_on_the_right",
        SUBGROUPS,
        r"\(a < float\(hi\)\)",
        "(a <= float(hi))",
        what="age banding becomes [lo, hi] instead of [lo, hi)",
    ),
    # ---- day-5 repair round 1: the lens's survivors that this round's tests observe
    Mutant(
        "ppv_indicator_inverted",
        SUBGROUPS,
        r"sel = pred\n        ind = pos\[sel\]",
        "sel = pred\n        ind = ~pos[sel]",
        what="per-level PPV becomes 1 - PPV (regression lens RG-B1)",
    ),
    Mutant(
        "npv_indicator_inverted",
        SUBGROUPS,
        r"sel = ~pred\n        ind = ~pos\[sel\]",
        "sel = ~pred\n        ind = pos[sel]",
        what="per-level NPV becomes 1 - NPV (regression lens RG-B1)",
    ),
    Mutant(
        "accuracy_inverted",
        SUBGROUPS,
        r"ind = pos == pred",
        "ind = pos != pred",
        what="per-level accuracy becomes 1 - accuracy (regression lens RG-B1)",
    ),
    Mutant(
        "ppv_conditioned_on_positives",
        SUBGROUPS,
        r'elif metric == "ppv":\n        sel = pred',
        'elif metric == "ppv":\n        sel = pos',
        what="per-level PPV computed on the reference-positive rows (fresh-attack lens N4)",
    ),
    Mutant(
        "heterogeneity_ignores_the_plan",
        SUBGROUPS,
        r"heterogeneity_footnote\(per_op, clustering_route=arrays\.plan\.route\)",
        'heterogeneity_footnote(per_op, clustering_route="none")',
        what="the chi-square runs on the rows of a clustered table (fresh-attack lens B1)",
    ),
    Mutant(
        "unpaired_delong_renders_with_a_frozen_arm",
        DISCRIMINATION,
        r"if var_a <= 0\.0 or var_b <= 0\.0:",
        "if var_a <= 0.0 and var_b <= 0.0:",
        what="delong_wald rendered when one arm's DeLong variance is zero (fresh-attack lens B2)",
    ),
    Mutant(
        "two_sided_bootstrap_side_b_from_a_fixed_generator",
        SUBGROUPS,
        r"values_b\[b\] = stat_b\(res_b\.draw\(rng\)\)",
        "values_b[b] = stat_b(res_b.draw(np.random.default_rng(b)))",
        what="side b of the two-sided bootstrap is not drawn from the cell's generator (RG-N2)",
    ),
    Mutant(
        "h09_message_names_observed_levels",
        SUBGROUPS,
        r'"subgroup reference_level is not a level of the analysed rows"',
        '"subgroup reference_level is not an observed level"',
        what="the H09 halt on an excluded reference level says it was not observed (FA-N7)",
    ),
    # ---- day-5 repair round 2: lens 2's blocker and the survivors this round's tests observe
    Mutant(
        "two_sided_bootstrap_frozen_side_check_removed",
        SUBGROUPS,
        r"if frozen or lo == hi:",
        "if lo == hi:",
        what="a difference with one side frozen renders the other side's interval (lens 2 FA-B1)",
    ),
    Mutant(
        "two_sided_bootstrap_frozen_check_side_a_only",
        SUBGROUPS,
        r'frozen = _frozen_sides\(\{"a": values_a, "b": values_b\}, level\)',
        'frozen = _frozen_sides({"a": values_a}, level)',
        what="the frozen-side check inspects side a only (lens 2 FA-B1, side b)",
    ),
    Mutant(
        "two_sided_bootstrap_side_b_drawn_before_side_a",
        SUBGROUPS,
        r"values_a\[b\] = stat_a\(res_a\.draw\(rng\)\)\n"
        r"        values_b\[b\] = stat_b\(res_b\.draw\(rng\)\)",
        "values_b[b] = stat_b(res_b.draw(rng))\n        values_a[b] = stat_a(res_a.draw(rng))",
        what="side b consumes the cell's generator before side a (lens 2 FA-N4)",
    ),
    Mutant(
        "clustered_proportion_difference_sign",
        SUBGROUPS,
        r"    d = k1 / n1 - k2 / n2\n    if not arrays\.clustered:",
        "    d = k2 / n2 - k1 / n1\n    if not arrays.clustered:",
        what="the clustered proportion difference estimate is other minus level (lens 2 FA-N6)",
    ),
    Mutant(
        "heterogeneity_clustered_refusal_before_the_level_count",
        SUBGROUPS,
        r"if clustered and len\(counts\) >= 2",
        "if clustered",
        what="fewer than two levels under clustering reports the clustered reason (lens 2 FA-N8)",
    ),
    Mutant(
        "schema_extension_missing_reason",
        OUTPUT_SCHEMA,
        r'"cases_span_both_groups", "insufficient_levels"',
        '"cases_span_both_groups"',
        what="the output schema no longer accepts one of the day-5 typed reasons",
    ),
    Mutant(
        "schema_extension_missing_flag",
        OUTPUT_SCHEMA,
        r'"wilson_refused_clustered", "newcombe_refused_clustered",',
        '"wilson_refused_clustered",',
        what="the output schema no longer accepts the day-5 flag",
    ),
    # ------------------------------------------------------------- build day 6
    Mutant(
        "oe_denominator_is_n_not_expected",
        CALIBRATION,
        r"    e = float\(ctx\.p\.sum\(\)\)\n    n = ctx\.n",
        "    e = float(ctx.n)\n    n = ctx.n",
        what="O:E denominator becomes N instead of the sum of predicted probabilities",
        day=6,
    ),
    Mutant(
        "oe_log_variance_drops_the_finite_factor",
        CALIBRATION,
        r"se = math\.sqrt\(\(1\.0 - o / n\) / o\)",
        "se = math.sqrt(1.0 / o)",
        what="log-scale delta variance (1 - O/N)/O becomes the Poisson 1/O",
        day=6,
    ),
    Mutant(
        "offset_model_frees_the_slope",
        CALIBRATION,
        r"return irls_logistic\(y, np\.ones\(\(y\.shape\[0\], 1\)\), offset=logit_p\)",
        "return irls_logistic(y, np.column_stack([np.ones(y.shape[0]), logit_p]))",
        what="calibration-in-the-large no longer fixes the slope at 1 (offset dropped)",
        day=6,
    ),
    Mutant(
        "wald_se_is_the_variance",
        CALIBRATION,
        r"se = np\.sqrt\(np\.diag\(cov\)\)",
        "se = np.diag(cov)",
        what="the Wald SE is reported as the variance",
        day=6,
    ),
    Mutant(
        "decile_tie_rule_reversed",
        CALIBRATION,
        r'order = np\.argsort\(np\.asarray\(score, dtype=np\.float64\), kind="stable"\)',
        'order = np.argsort(-np.asarray(score, dtype=np.float64), kind="stable")[::-1]',
        what="ties in the decile bins are placed in reverse row order",
        day=6,
    ),
    Mutant(
        "ece_equal_width_edges_left_closed",
        CALIBRATION,
        r'np\.asarray\(score, dtype=np\.float64\), side="left"\) - 1',
        'np.asarray(score, dtype=np.float64), side="right") - 1',
        what="equal-width ECE bins become left-closed [lo, hi)",
        day=6,
    ),
    Mutant(
        "curve_threshold_199",
        CALIBRATION,
        r"^CURVE_MIN_EVENTS = 200$",
        "CURVE_MIN_EVENTS = 199",
        what="the 200/200 convention moved to 199",
        day=6,
    ),
    Mutant(
        "curve_inequality_inclusive",
        CALIBRATION,
        r"below = events < CURVE_MIN_EVENTS or nonevents < CURVE_MIN_EVENTS",
        "below = events <= CURVE_MIN_EVENTS or nonevents <= CURVE_MIN_EVENTS",
        what="exactly 200 events is flagged",
        day=6,
    ),
    Mutant(
        "curve_inequality_and_not_or",
        CALIBRATION,
        r"below = events < CURVE_MIN_EVENTS or nonevents < CURVE_MIN_EVENTS",
        "below = events < CURVE_MIN_EVENTS and nonevents < CURVE_MIN_EVENTS",
        what="the flag needs both classes below 200 instead of either",
        day=6,
    ),
    Mutant(
        "suppression_ignores_score_type",
        CALIBRATION,
        r'    if decl\.score_type != "probability":\n        return "score_not_probability"',
        '    if decl.score_type == "unused":\n        return "score_not_probability"',
        what="a logit or other score is calibrated as if it were a probability",
        day=6,
    ),
    Mutant(
        "suppression_ignores_orientation",
        CALIBRATION,
        r'    if decl\.orientation != "higher_is_positive":',
        '    if decl.orientation == "unused":',
        what="a lower_is_positive probability is calibrated as the positive-class probability",
        day=6,
    ),
    Mutant(
        "oe_clustered_refusal_dropped",
        CALIBRATION,
        r'        return _unavailable\(ctx, key, "single_class", est=est\)\n    if ctx\.clustered:',
        '        return _unavailable(ctx, key, "single_class", est=est)\n    if False:',
        what="the log-delta O:E interval is rendered on clustered rows (X2 / DEC-09)",
        day=6,
    ),
    Mutant(
        "irls_clustered_refusal_dropped",
        CALIBRATION,
        r"# type: ignore\[index\]\n        if ctx\.clustered:",
        "# type: ignore[index]\n        if False:",
        what="the IRLS Wald intervals are rendered on clustered rows (X2 / DEC-09)",
        day=6,
    ),
    Mutant(
        "ipa_sign_flipped",
        CALIBRATION,
        r"ipa = 1\.0 - brier / ref if brier is not None and ref else None",
        "ipa = brier / ref - 1.0 if brier is not None and ref else None",
        what="IPA reported as Brier/Brier_ref - 1",
        day=6,
    ),
    Mutant(
        "brier_reference_is_prevalence",
        CALIBRATION,
        r"ref = pi \* \(1\.0 - pi\) if pi is not None else None",
        "ref = pi if pi is not None else None",
        what="the reference Brier becomes the prevalence itself",
        day=6,
    ),
    Mutant(
        "clip_epsilon_loosened",
        CALIBRATION,
        r"^CLIP_EPS = 1e-12$",
        "CLIP_EPS = 1e-6",
        what="boundary scores clipped at 1e-6 instead of 1e-12",
        day=6,
    ),
    Mutant(
        "separation_not_typed",
        CALIBRATION,
        r"        if np\.all\(np\.abs\(mu - y\) < SEPARATION_TOL\):",
        "        if False:",
        what="complete separation is no longer detected (runs to the iteration budget)",
        day=6,
    ),
    Mutant(
        "brier_ref_bootstrapped_under_stratification",
        CALIBRATION,
        r"    if _prevalence_invariant\(resampler\):",
        "    if False:",
        what="the reference Brier is bootstrapped where the resampler holds it fixed",
        day=6,
    ),
    Mutant(
        "schema_extension_missing_day6_reason",
        OUTPUT_SCHEMA,
        r'"irls_not_converged", "complete_separation", "constant_score",',
        '"irls_not_converged", "constant_score",',
        what="the output schema no longer accepts a day-6 typed reason",
        day=6,
    ),
    Mutant(
        "schema_extension_missing_day6_flag",
        OUTPUT_SCHEMA,
        r'"below_200_events_or_nonevents", "scores_clipped_for_logit",',
        '"below_200_events_or_nonevents",',
        what="the output schema no longer accepts a day-6 flag",
        day=6,
    ),
)


def make_copy() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="proofpack-mutants-"))
    for item in COPIED:
        src = REPO / item
        if src.is_dir():
            shutil.copytree(src, tmp / item, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, tmp / item)
    return tmp


def env_for(copy: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(copy / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def assert_imports_from_copy(copy: Path) -> None:
    out = subprocess.run(
        [sys.executable, "-c", "import proofpack, sys; print(proofpack.__file__)"],
        cwd=copy,
        env=env_for(copy),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if Path(out).resolve().parent.parent != (copy / "src").resolve():
        raise SystemExit(f"proofpack resolves to {out}, not the copy under {copy / 'src'}")


def plant(copy: Path, mutant: Mutant) -> None:
    target = copy / mutant.file
    original = (REPO / mutant.file).read_text(encoding="utf-8")
    mutated, n = re.subn(mutant.pattern, mutant.replacement, original, flags=re.M)
    if n != mutant.count:
        raise SystemExit(
            f"mutant {mutant.id}: pattern matched {n} time(s) in {mutant.file}, expected "
            f"{mutant.count} - the code moved; update the mutant list"
        )
    target.write_text(mutated, encoding="utf-8")


def restore(copy: Path, mutant: Mutant) -> None:
    shutil.copy2(REPO / mutant.file, copy / mutant.file)


def run_marker(copy: Path, marker: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "-m", marker],
        cwd=copy,
        env=env_for(copy),
        capture_output=True,
        text=True,
    )
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-3:])
    return proc.returncode, tail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="plant declared mutants and run a pytest marker")
    ap.add_argument("--marker", default="day5")
    ap.add_argument(
        "--day",
        type=int,
        default=None,
        help="run only the mutants declared for this build day (default: the marker's day)",
    )
    ap.add_argument("--only", action="append", help="mutant id(s) to run")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fail-on-survivor", action="store_true")
    args = ap.parse_args(argv)
    day = args.day
    if day is None and args.marker.startswith("day") and args.marker[3:].isdigit():
        day = int(args.marker[3:])
    chosen = [
        m for m in MUTANTS if (not args.only or m.id in args.only) and (day is None or m.day == day)
    ]
    if args.list:
        for m in MUTANTS:
            print(f"{m.id:<40} day{m.day} {m.file:<36} {m.what}")
        return 0
    copy = make_copy()
    try:
        assert_imports_from_copy(copy)
        rc, tail = run_marker(copy, args.marker)
        if rc != 0:
            print(f"baseline (no mutant) does not pass -m {args.marker}; refusing to sweep\n{tail}")
            return 2
        print(f"baseline: -m {args.marker} passes in the copy at {copy}\n")
        survivors = []
        t0 = time.time()
        for m in chosen:
            plant(copy, m)
            rc, tail = run_marker(copy, args.marker)
            restore(copy, m)
            status = "killed" if rc != 0 else "SURVIVED"
            if rc == 0:
                survivors.append(m)
            print(f"{status:<9} {m.id:<40} {m.what}")
            if rc != 0:
                print(f"          {tail.splitlines()[-1][:110]}")
        killed = len(chosen) - len(survivors)
        print(
            f"\n{len(chosen)} planted, {killed} killed, {len(survivors)} survived; "
            f"{time.time() - t0:.0f} s"
        )
        for m in survivors:
            print(f"  survivor: {m.id} - {m.what}")
        return 1 if survivors and args.fail_on_survivor else 0
    finally:
        shutil.rmtree(copy, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
