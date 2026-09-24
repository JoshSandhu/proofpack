"""DEC-12(ii): the mutation sweep as a committed script.

Plants a declared list of mutants - each ``(id, file, regex, replacement, expected count)``
- one at a time into a *copy* of the working tree, runs the named pytest marker there,
and prints killed / survived per mutant. A mutant is **killed** when the marker's tests
fail against it and **survived** when they all pass. A surviving mutant that is not
equivalent (i.e. it changes behaviour) is a coverage gap: close it with a test, or carry
it in the handoff note with the reason.

Why a copy and not a worktree: the sweep must run against the *working tree* (the code
being handed off, committed or not), and a git worktree can only check out a commit. The
copy holds ``src``, ``tests``, ``schema``, ``fixtures``, ``design``, ``scripts`` (the
day-6 sentences test reads ``scripts/coverage_calibration.py``), ``pyproject.toml`` and
``README.md`` (repair 4.2 of A-P1: ``tests/test_mapping_repair4_2.py`` reads it);
``PYTHONPATH`` is forced to the copy's ``src`` for every subprocess.
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
    python scripts/mutation_sweep.py --marker day6            # both day-6 lists (E and A)
    python scripts/mutation_sweep.py --marker day7            # the day-7 list (E7)
    python scripts/mutation_sweep.py --marker day8            # the day-8 list (E8)
    python scripts/mutation_sweep.py --marker day9            # the day-9 list (E9)
    python scripts/mutation_sweep.py --marker day5 --only ref_largest_to_smallest
    python scripts/mutation_sweep.py --list
    python scripts/mutation_sweep.py --marker day5 --fail-on-survivor   # exit 1 if any survive

    python scripts/mutation_sweep.py --marker ap2             # the A-P2 egress list (day 8 A)
    python scripts/mutation_sweep.py --marker ap3             # the A-P3 release list (day 9 A)

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
#: README.md joined the copy in repair 4.2 of A-P1: tests/test_mapping_repair4_2.py reads
#: it (a test that cannot open it would fail against every mutant and count each killed);
#: scripts joined it on day 6 E (the sentences test reads scripts/coverage_calibration.py).
#: A-P3 (build day 9) added the Dockerfile, .dockerignore, .github (the workflow files its
#: tests read and its mutants change) and uv.lock (tests/test_sbom.py reads it).
COPIED = (
    "src",
    "tests",
    "schema",
    "fixtures",
    "design",
    "scripts",
    "pyproject.toml",
    "README.md",
    "Dockerfile",
    ".dockerignore",
    ".github",
    "uv.lock",
)
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
    marker: str = ""  # a non-day marker the mutant is run under (A-P2: ``ap2``); "" = dayN

    @property
    def label(self) -> str:
        return self.marker or f"day{self.day}"


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
    # ---- day-6 repair round 1: lens 1's blockers and the sites its tests now observe
    Mutant(
        "clustered_oe_statistic_uses_the_full_cohort_o",
        CALIBRATION,
        r"            num = float\(ctx\.y\[idx\]\.sum\(\)\)",
        "            num = float(ctx.y.sum())",
        what="the clustered O:E resample holds O at the cohort's value (lens 1 FA-B1 / M2)",
        day=6,
    ),
    Mutant(
        "clustered_oe_single_class_draw_is_a_ratio_not_nan",
        CALIBRATION,
        r"            if den <= 0\.0 or num == 0\.0 or num == idx\.shape\[0\]:",
        "            if den <= 0.0:",
        what="a single-class case draw yields O:E = 0 instead of nan (degenerate_resamples)",
        day=6,
    ),
    Mutant(
        "clustered_route_class_units_guard_dropped",
        CALIBRATION,
        r"    if guard\.deficient_class is not None:",
        "    if guard.deficient_class is not None and False:",
        what="one case holding 180 of 200 rows renders the O:E and the fits (lens 1 property)",
        day=6,
    ),
    Mutant(
        "prevalence_invariant_is_the_b93e050_label_rule",
        CALIBRATION,
        r"    per_unit: list\[tuple\[int, int\]\] = \[\]\n",
        '    return all(s.label != "mixed" and s.matrix is not None for s in resampler.strata)\n'
        "    per_unit: list[tuple[int, int]] = []\n",
        what="two-row mixed cases make the reference Brier boundary_estimate (lens 1 FA-B3, RG-B3)",
        day=6,
    ),
    Mutant(
        "prevalence_invariant_always_true",
        CALIBRATION,
        r"    per_unit: list\[tuple\[int, int\]\] = \[\]\n",
        "    return True\n    per_unit: list[tuple[int, int]] = []\n",
        what="the reference Brier is never bootstrapped (cases of one and three rows)",
        day=6,
    ),
    # ---- day-6 repair round 2: lens 2's FA-N1 / RG-N1 (the prevalence rule) and FA-N5 L2-2
    Mutant(
        "prevalence_invariant_is_the_round1_identical_counts_rule",
        CALIBRATION,
        r"    per_unit: list\[tuple\[int, int\]\] = \[\]\n",
        "    return all(\n        len(set(counts)) <= 1\n"
        "        for stratum in resampler.strata\n"
        "        for counts in stratum.class_unit_rows.values()\n    )\n"
        "    per_unit: list[tuple[int, int]] = []\n",
        what="30 mixed cases of (1, 1) beside 30 of (2, 2): boundary_estimate (lens 2 FA-N1)",
        day=6,
    ),
    Mutant(
        "prevalence_invariant_reads_positive_counts_only",
        CALIBRATION,
        r"        if len\(\{r_total \* k - p_total \* r for k, r in units\}\) > 1:",
        "        if len({k for k, r in units}) > 1:",
        what="mixed (1, 1) beside (1, 2): the prevalence varies but reads fixed (lens 2 L2-1)",
        day=6,
    ),
    Mutant(
        "prevalence_invariant_reads_row_counts_only",
        CALIBRATION,
        r"        if len\(\{r_total \* k - p_total \* r for k, r in units\}\) > 1:",
        "        if len({r for k, r in units}) > 1:",
        what="mixed (1, 1) beside (2, 2): the prevalence is fixed but is bootstrapped to no width",
        day=6,
    ),
    Mutant(
        "decile_bin_ids_are_a_prefix_not_the_bins_rows",
        CALIBRATION,
        r"            cluster_ids=None if ctx\.ids is None else ctx\.ids\[rows\],",
        "            cluster_ids=None if ctx.ids is None else ctx.ids[: rows.shape[0]],",
        what="each decile bin's cluster bootstrap groups the wrong cases (lens 2 FA-N5 L2-2)",
        day=6,
    ),
    Mutant(
        "mass_edges_read_the_empty_last_bin",
        CALIBRATION,
        r"        \[float\(p\[filled\[-1\]\]\.max\(\)\)\] if filled else \[\]",
        "        [float(p[mass_bins[-1]].max())] if n else []",
        what="N = 1..9 raises numpy's zero-size reduction (lens 1 FA-B2 / RG-B1)",
        day=6,
    ),
    Mutant(
        "oe_below_200_200_is_not_computed",
        CALIBRATION,
        r"    est = o / e\n    if o == 0\.0 or o == n:",
        "    est = o / e\n    if o < 200 or n - o < 200:\n"
        '        return _unavailable(ctx, key, "not_computed_this_run", est=est)\n'
        "    if o == 0.0 or o == n:",
        what="the 200/200 annotation suppresses the O:E interval (lens 1 RG-N3)",
        day=6,
    ),
    Mutant(
        "curve_flag_rides_on_the_companion_not_the_number",
        CALIBRATION,
        r"            cell = replace\(cell, number=number\)",
        "            cell = replace(cell, analytic=number)",
        what="the 200/200 flag lands on the analytic Number under clustering (lens 1 FA-N2 M18)",
        day=6,
    ),
    Mutant(
        "difference_frozen_sides_at_the_default_level",
        SUBGROUPS,
        r'    frozen = _frozen_sides\(\{"a": values_a, "b": values_b\}, level\)',
        '    frozen = _frozen_sides({"a": values_a, "b": values_b}, DEFAULT_LEVEL)',
        what="the frozen-side rule reads 0.95 whatever level was asked (item 17, lens 1 RG-N1)",
        day=6,
    ),
    Mutant(
        "difference_bounds_at_the_default_level",
        SUBGROUPS,
        r'    frozen = _frozen_sides\(\{"a": values_a, "b": values_b\}, level\)\n'
        r"    lo, hi = percentile_bounds\(usable, level\)",
        '    frozen = _frozen_sides({"a": values_a, "b": values_b}, level)\n'
        "    lo, hi = percentile_bounds(usable, DEFAULT_LEVEL)",
        what="a difference at 0.90 renders its 0.95 bounds (day-5 item 17, lens 1 RG-N1)",
        day=6,
    ),
)

MAPPING = "src/proofpack/io/mapping.py"
SCHEMA_IO = "src/proofpack/io/schema.py"
PROFILE = "src/proofpack/io/profile.py"
DECLARE = "src/proofpack/io/declare.py"
CLI = "src/proofpack/cli.py"

#: Day 6 A (the full mapper). Run with ``--marker day6``.
MUTANTS_DAY6_A: tuple[Mutant, ...] = (
    Mutant(
        "synonym_label_to_y_pred",
        MAPPING,
        r'^    "label": "y_true",$',
        '    "label": "y_pred",',
        count=2,  # the synonym table and the partial-token table both carry the row
        day=6,
        what="synonym lookup: 'label' resolves to y_pred",
    ),
    Mutant(
        "unit_interval_upper_bound_100",
        PROFILE,
        r"lo >= 0\.0 and hi <= 1\.0",
        "lo >= 0.0 and hi <= 100.0",
        day=6,
        what="the [0, 1] score rule accepts values up to 100",
    ),
    Mutant(
        "suppression_k_nine",
        PROFILE,
        r"^SUPPRESSION_K = 10$",
        "SUPPRESSION_K = 9",
        day=6,
        what="the suppression floor drops to 9 (a count of 9 is shown)",
    ),
    Mutant(
        "sample_rows_10001",
        PROFILE,
        r"^SAMPLE_ROWS = 10_000$",
        "SAMPLE_ROWS = 10_001",
        day=6,
        what="the type-inference sample reads row 10,001",
    ),
    Mutant(
        "every_role_high_becomes_any",
        MAPPING,
        r'return all\(r\.confidence == "high" for r in self\.roles if r\.role is not None\)',
        'return any(r.confidence == "high" for r in self.roles if r.role is not None)',
        day=6,
        what="the every-role-high rule passes when any role is high",
    ),
    Mutant(
        "hash_comparison_always_true",
        MAPPING,
        r"if prior is not None and prior\.header_set_sha256 == current:",
        "if prior is not None:",
        day=6,
        what="a prior mapping.json is accepted whatever its header-set hash",
    ),
    Mutant(
        "composite_key_needs_three",
        MAPPING,
        r"if len\(case_claims\) >= 2:",
        "if len(case_claims) >= 3:",
        day=6,
        what="two headers resolving to case_id no longer halt E01",
    ),
    Mutant(
        "composite_declaration_needs_three",
        DECLARE,
        r"    if n >= 2:\n        raise HaltError\(",
        "    if n >= 3:\n        raise HaltError(",
        day=6,
        what="a two-column clustering.unit no longer halts E01",
    ),
    Mutant(
        "tty_check_always_true",
        CLI,
        r"            if not tty:\n                raise HaltError\(",
        "            if False:\n                raise HaltError(",
        day=6,
        what="a non-terminal stdin is prompted instead of halting H07",
    ),
    Mutant(
        "binary_set_yes_no_removed",
        MAPPING,
        r'^    frozenset\(\{"yes", "no"\}\),$',
        "",
        day=6,
        what="yes/no columns are no longer y_true candidates",
    ),
    Mutant(
        "free_text_threshold_never",
        PROFILE,
        r"^FREE_TEXT_UNIQUE_SHARE = 0\.5$",
        "FREE_TEXT_UNIQUE_SHARE = 5.0",
        day=6,
        what="a free-text column lists its values",
    ),
    Mutant(
        "date_values_not_event_date",
        MAPPING,
        r'    if sig\.get\("date"\):\n        return "event_date"',
        '    if sig.get("date"):\n        return None',
        day=6,
        what="a date-valued column is no longer an event_date candidate",
    ),
    Mutant(
        "sex_12_is_high",
        MAPPING,
        r'return RoleMapping\(h, role, "medium", c\.source, notes\)',
        'return RoleMapping(h, role, "high", c.source, notes)',
        day=6,
        what="sex coded 1/2 or 0/1 is high instead of medium",
    ),
    Mutant(
        "e01_message_truncated",
        MAPPING,
        r'columns resolve to case_id; reduce your case key to one column"',
        'columns resolve to case_id; reduce your case key"',
        day=6,
        what="the DEC-11 message no longer ends with the mandated sentence",
    ),
    Mutant(
        "label_with_floats_stays_high",
        MAPPING,
        r's\.n_unique > 2:\n            return \(\n                "conflict",',
        's.n_unique > 2:\n            return (\n                "consistent",',
        day=6,
        what="a label column holding continuous scores keeps high confidence",
    ),
    Mutant(
        "duplicate_fold_check_removed",
        MAPPING,
        r"if len\(set\(folded\)\) != len\(folded\):",
        "if False:",
        day=6,
        what="two headers identical after case-folding no longer halt H07",
    ),
    Mutant(
        "binary_rule_case_sensitive",
        MAPPING,
        r"if len\(lowered\) == 2 and any\(lowered == b for b in BINARY_LABEL_SETS\):",
        "if s.n_unique == 2 and any(lowered == b for b in BINARY_LABEL_SETS):",
        day=6,
        what="the two-valued label rule becomes case-sensitive",
    ),
    # Day 6 A repair 1: the lens's eight survivors are observed by tests/test_mapping_repair1.py
    # (pins); the ten below change the repair's own gates.
    Mutant(
        "min_max_floor_removed",
        PROFILE,
        r"return _fmt_num\(x\) if rows >= SUPPRESSION_K else SUPPRESSED",
        "return _fmt_num(x)",
        day=6,
        what="a numeric min/max held by fewer than k rows is printed (FA-B1)",
    ),
    Mutant(
        "min_max_floor_off_by_one",
        PROFILE,
        r"if rows >= SUPPRESSION_K else SUPPRESSED",
        "if rows >= SUPPRESSION_K - 1 else SUPPRESSED",
        day=6,
        what="a min/max held by 9 rows is printed",
    ),
    Mutant(
        "proposed_prior_accepted_by_yes",
        MAPPING,
        r'CONFIRMED_DECIDED_BY = frozenset\(\{"interactive", "file"\}\)',
        'CONFIRMED_DECIDED_BY = frozenset({"interactive", "file", "proposed"})',
        day=6,
        what="--yes accepts a mapping.json that proofpack run wrote unconfirmed (FA-N1)",
    ),
    Mutant(
        "slash_no_longer_splits_the_case_key",
        DECLARE,
        r'\[\^A-Za-z0-9_\]\+"\)',
        '[^A-Za-z0-9_/]+")',
        day=6,
        what="subject_id/hadm_id falls through to the schema's H08 enum halt (FA-B2)",
    ),
    Mutant(
        "clustering_list_keys_need_three",
        DECLARE,
        r"if isinstance\(value, \(list, tuple\)\) and len\(value\) >= 2:",
        "if isinstance(value, (list, tuple)) and len(value) >= 3:",
        day=6,
        what="clustering.columns: [a, b] passes silently",
    ),
    Mutant(
        "all_high_prompt_removed",
        CLI,
        r"^    if not pending:$",
        "    if not pending and False:",
        day=6,
        what="an all-high table is written as interactive with no keypress (FA-N2)",
    ),
    Mutant(
        "held_role_edit_accepted",
        CLI,
        r"holder = held_by\(r, new_role\)\n                if holder is not None:",
        "holder = held_by(r, new_role)\n                if holder is not None and False:",
        day=6,
        what="an edit to a role another column holds is written (FA-N4)",
    ),
    Mutant(
        "dash_date_shape_removed",
        PROFILE,
        r'^    re\.compile\(r"\^\\d\{1,2\}-\\d\{1,2\}-\\d\{4\}\$"\),\n',
        "",
        day=6,
        what="15-03-2024 values are free text again and pass H11 (FA-N7)",
    ),
    Mutant(
        "console_not_tolerant",
        CLI,
        r'stream\.reconfigure\(errors="backslashreplace"\)',
        "pass",
        day=6,
        what="a CJK header on a cp1252 stdout is exit 5 again (FA-N8)",
    ),
    Mutant(
        "quiet_hides_the_table_at_a_terminal",
        CLI,
        r"if not args\.json_log and \(not args\.quiet or tty\):",
        "if not args.json_log and not args.quiet:",
        day=6,
        what="--quiet at a terminal prompts with no table (FA-N12)",
    ),
    # repair 2 (the lens-2 findings; tests/test_mapping_repair2.py)
    Mutant(
        "apply_two_case_id_columns_h07_not_e01",
        MAPPING,
        r"if n_case >= 2:",
        "if n_case >= 3:",
        day=6,
        what="patient_nbr + mrn_local through run is H07, not the DEC-11 E01 (FA-B1)",
    ),
    Mutant(
        "partial_case_id_tokens_counted_by_map_headers_e01",
        MAPPING,
        r'if c and c\.role == "case_id" and c\.source != "partial"',
        'if c and c.role == "case_id"',
        day=6,
        what="patient_weight + patient_height halt E01 in map_headers (lens-2 M05)",
    ),
    Mutant(
        "accept_of_a_held_role_taken",
        CLI,
        r"holder = held_by\(r, r\.role\) if r\.role is not None else None",
        "holder = None",
        day=6,
        what="'a' at both case_id prompts writes two holders (FA-B1)",
    ),
    Mutant(
        "all_high_prompt_takes_any_answer",
        CLI,
        r'say\("  answer a or q"\)',
        "break",
        day=6,
        what="'n' at the all-high prompt is an accept (RG-N1)",
    ),
    Mutant(
        "attr_twins_not_single_holder",
        MAPPING,
        r'return role in SINGLE_HOLDER_ROLES or role\.startswith\(\("attr_", "rater_"\)\)',
        "return role in SINGLE_HOLDER_ROLES",
        day=6,
        what="'Attr Site' beside attr_site are both high (FA-N7)",
    ),
    Mutant(
        "prior_role_type_unchecked",
        MAPPING,
        r"if role is not None and not isinstance\(role, str\):",
        "if False:",
        day=6,
        what="a prior with role 123 reaches run --yes as exit 5 (RG-B1)",
    ),
    Mutant(
        "list_key_string_not_split",
        DECLARE,
        # anchored to the clustering check's indentation: repair 5 of day 8 added a second
        # ``if isinstance(value, str):`` (the control-character walk), and the unanchored
        # pattern matched twice from eda8a35 (found and fixed on day 9)
        r"^        if isinstance\(value, str\):$",
        "        if False:",
        day=6,
        what="clustering.columns: 'subject_id, hadm_id' passes silently (FA-N8)",
    ),
    Mutant(
        "and_separator_lower_case_only",
        DECLARE,
        r"\[Aa\]\[Nn\]\[Dd\]",
        "and",
        day=6,
        what="'a AND b' counts three tokens (RG-N3)",
    ),
    Mutant(
        "dotted_date_shape_removed",
        PROFILE,
        r'^    re\.compile\(r"\^\\d\{1,2\}\\\.\\d\{1,2\}\\\.\\d\{4\}\$"\),\n',
        "",
        day=6,
        what="15.03.2024 values are categorical again and pass H11 (FA-N2)",
    ),
    Mutant(
        "out_dir_check_off",
        CLI,
        r"if not out_dir\.is_dir\(\):",
        "if False:",
        day=6,
        what="--out into a missing directory is exit 5 after the prompts (FA-N6)",
    ),
    Mutant(
        "hash_is_the_column_count",
        SCHEMA_IO,
        r'joined = "\\n"\.join\(sorted\(h\.strip\(\) for h in headers\)\)',
        "joined = str(len(headers))",
        day=6,
        what="a header renamed at the same width keeps the hash (lens-2 M24)",
    ),
    # repair 3: the four lens-3 survivors (L08, L11, L13, L14; L20 was a dead clause and
    # is deleted) and one observer per new gate.
    Mutant(
        "date_type_on_any_value",
        PROFILE,
        r"if all\(any\(p\.match\(v\) for p in DATE_PATTERNS\) for v in values\):",
        "if any(any(p.match(v) for p in DATE_PATTERNS) for v in values):",
        day=6,
        what="one date among sixty cells types the column date (lens-3 L08)",
    ),
    Mutant(
        "affix_case_id_claims_not_counted",
        MAPPING,
        r'if c and c\.role == "case_id" and c\.source != "partial"',
        'if c and c.role == "case_id" and c.source in ("canonical", "synonym")',
        day=6,
        what="patient_id + pt_subject_id is not E01 in map_headers (lens-3 L11)",
    ),
    Mutant(
        "fold_header_without_strip",
        MAPPING,
        r'header\.replace\("\\ufeff", ""\)\)\.strip\(\)\.casefold\(\)',
        'header.replace("\\\\ufeff", "")).casefold()',  # a re.sub template: \\ is one \
        day=6,
        what="' Label ' and 'label' are two headers after folding (lens-3 L13)",
    ),
    Mutant(
        "apply_e01_counts_non_high_case_id_only",
        MAPPING,
        r'if mapping\.role_of\(original\) == "case_id"\)',
        'if mapping.role_of(original) == "case_id"\n'
        '        and mapping.entry(original).confidence != "high")',
        day=6,
        what="two high case_id columns pass apply_mapping (lens-3 L14)",
    ),
    Mutant(
        "empty_answer_accepts",
        CLI,
        r'^ACCEPT_ANSWERS = \("a", "accept"\)$',
        'ACCEPT_ANSWERS = ("a", "accept", "")',
        day=6,
        what="Enter alone accepts at both prompts (lens-3 FA-B1)",
    ),
    Mutant(
        "ignore_collision_unchecked_on_a_prior",
        MAPPING,
        r"pair = ignore_collision\(prior\.roles\)",
        "pair = None",
        day=6,
        what="a prior ignoring 'score' beside prob -> score reaches apply_mapping (DEC-31)",
    ),
    Mutant(
        "accept_does_not_record_confirmed",
        CLI,
        r"^                r\.confirmed = True$",
        "                r.confirmed = False",
        day=6,
        what="'a' leaves confirmed False so --yes refuses the file (DEC-28)",
    ),
    Mutant(
        "date_month_floor_removed",
        PROFILE,
        r"shown_lo = keys\[0\] if months\[keys\[0\]\] >= SUPPRESSION_K else SUPPRESSED",
        "shown_lo = keys[0]",
        day=6,
        what="a month held by one row prints as min (DEC-39)",
    ),
    Mutant(
        "yes_role_difference_unchecked",
        MAPPING,
        r"^        if p\.role == f\.role:$",
        "        if True:",
        day=6,
        what="a prior 'age' on a column now holding bands passes --yes (carried 7)",
    ),
    Mutant(
        "roles_list_check_removed",
        MAPPING,
        r'if not isinstance\(data\["roles"\], list\):',
        "if False:",
        day=6,
        what="roles: {} reads as an empty list again (lens-3 RG-B1)",
    ),
    Mutant(
        "originals_not_checked_against_the_table",
        MAPPING,
        r"unknown = sum\(1 for r in prior\.roles if r\.original not in header_set\)",
        "unknown = 0",
        day=6,
        what="original: NOT_A_HEADER passes --yes (DEC-29)",
    ),
    Mutant(
        "out_is_dir_check_off",
        CLI,
        r"if out_path\.is_dir\(\):",
        "if False:",
        day=6,
        what="--out naming a directory reaches the prompt (carried 6)",
    ),
    Mutant(
        "recursion_error_not_caught",
        MAPPING,
        r"except \(ValueError, RecursionError\) as exc:",
        "except ValueError as exc:",
        day=6,
        what="100,000 nested '[' is exit 5 again (lens-3 FA-B4)",
    ),
    # repair 3.2: one observer per new check, plus the five lens-1 survivors (M03, M05,
    # M11, M15, M20 of the repair-3 fresh-attack note) now that a test feeds each input.
    Mutant(
        "ignored_role_name_kept_at_apply",
        MAPPING,
        r"role = IGNORED_PREFIX \+ original if read_as_a_role_by_validate\(original\) else \w+",
        "role = original",
        day=6,
        what="an ignored 'sex' column reaches validate as the sex attribute (lens-1 FA-B1)",
    ),
    Mutant(
        "yes_confirmed_values_unchecked",
        MAPPING,
        r"^    if changed:$",
        "    if False:",
        day=6,
        what="a confirmed column whose values changed passes --yes (lens-1 FA-B2)",
    ),
    Mutant(
        "yes_split_counts_compared",
        MAPPING,
        r"values = frozenset\(str\(item\[0\]\) for item in split",
        "values = frozenset(str(item) for item in split",
        day=6,
        what="the same two values in other proportions halt --yes (FA-B2's control)",
    ),
    Mutant(
        "bom_prior_not_decoded",
        MAPPING,
        r'raw\.decode\("utf-8-sig"\)',
        'raw.decode("utf-8")',
        day=6,
        what="a prior with a UTF-8 BOM is H07 could not be decoded (lens-1 FA-N5)",
    ),
    Mutant(
        "proposed_prior_relabelled_file",
        MAPPING,
        r"        return prior\n\n    if non_interactive:\n        if prior is None:",
        '        prior.decided_by = "file"\n        return prior\n\n'
        "    if non_interactive:\n        if prior is None:",
        day=6,
        # re-anchored in repair 4.2: the conditional rewrite it flipped is gone
        what="every matching prior is relabelled file on the way out (lens-1 RG-N5 of repair 3)",
    ),
    Mutant(
        "write_oserror_not_caught",
        CLI,
        r"    except OSError:\n        # at b0f60a6 a read-only --out",
        "    except MemoryError:\n        # at b0f60a6 a read-only --out",
        day=6,
        what="a read-only --out is exit 5 PermissionError with the path (lens-1 FA-N1)",
    ),
    Mutant(
        "us_shaped_slash_date_month_fifteen",
        PROFILE,
        r"month = int\(m\.group\(1\)\) if month_first else int\(m\.group\(2\)\)",
        "month = int(m.group(2))",
        day=6,
        what="03/15/2024 keys to 2024-15 (lens-1 FA-N4)",
    ),
    Mutant(
        "yes_role_difference_skipped_for_ignore",
        MAPPING,
        r"^        if p\.role == f\.role:$",
        "        if p.role is None or p.role == f.role:",
        day=6,
        what="a file prior ignoring a high column passes --yes (lens-1 M03)",
    ),
    Mutant(
        "duplicate_entry_check_removed",
        MAPPING,
        r"^    if duplicated:$",
        "    if False:",
        day=6,
        what="the site entry appended a second time unchanged passes --yes (lens-1 RG-N2)",
    ),
    Mutant(
        "one_missing_entry_tolerated",
        MAPPING,
        r"    if missing:\n",
        "    if missing > 1:\n",
        day=6,
        what="a prior missing one entry passes the entry-set check (lens-1 M05)",
    ),
    Mutant(
        "accept_arm_collision_unchecked",
        CLI,
        r"                line = collision_line\(r, r\.role\)\n",
        "                line = None\n",
        day=6,
        what="'a' on prob -> score beside an ignored 'score' is taken (lens-1 M11)",
    ),
    Mutant(
        "date_min_month_floor_at_nine",
        PROFILE,
        r"shown_lo = keys\[0\] if months\[keys\[0\]\] >= SUPPRESSION_K else SUPPRESSED",
        "shown_lo = keys[0] if months[keys[0]] >= SUPPRESSION_K - 1 else SUPPRESSED",
        day=6,
        what="a min month held by nine rows prints (lens-1 M15)",
    ),
    Mutant(
        "fresh_non_high_confirmed_anywhere",
        MAPPING,
        r"if not by_original\[f\.original\]\.confirmed\]",
        "if not any(p.confirmed for p in prior.roles)]",
        day=6,
        what="confirmed on any prior entry covers every fresh non-high role (lens-1 M20)",
    ),
    # repair 4 of A-P1 (lens-2 round 2 on 4fbbf35; DEC-42)
    Mutant(
        "date_order_decided_per_value",
        PROFILE,
        r"_date_key\(v, month_first=month_first\)",
        "_date_key(v, month_first=_month_first([v]))",
        day=6,
        what="the day/month order decided per value: nine March rows print (lens-2 FA-B1)",
    ),
    Mutant(
        "month_first_never",
        PROFILE,
        r"return second_above and not first_above",
        "return False",
        day=6,
        what="every two-field date read day-first: 03/15/2024 keys to 2024-15",
    ),
    Mutant(
        "second_field_boundary_thirteen",
        PROFILE,
        r"second_above = second_above or int\(m\.group\(2\)\) > 12",
        "second_above = second_above or int(m.group(2)) > 13",
        day=6,
        what="03/13/2024 x60 keys to 2024-13 (lens-2 M09)",
    ),
    Mutant(
        "first_field_boundary_twelve",
        PROFILE,
        r"first_above = first_above or int\(m\.group\(1\)\) > 12",
        "first_above = first_above or int(m.group(1)) >= 12",
        day=6,
        what="12/15/2024 x60 keys to 2024-15 (lens-2 M21)",
    ),
    Mutant(
        "period_ignored_halt_removed",
        MAPPING,
        r'raise HaltError\("S03", PERIOD_IGNORED, \{"period_column_ignored": True\}\)',
        "return period",
        day=6,
        what="an ignored column named by period.column is the period axis (lens-2 FA-B2)",
    ),
    Mutant(
        "period_translation_removed",
        MAPPING,
        r'return \{\*\*period, "column": entry\.role\}',
        "return period",
        day=6,
        what="period.column naming a header mapped to event_date is S03 not present (lens-2 N4)",
    ),
    Mutant(
        "period_prompt_refusal_removed",
        CLI,
        r"if new_role == IGNORE and period_column is not None and r\.original == period_column:",
        "if False:",
        day=6,
        what="e ignore on the period column is taken at the prompt and halts after the answers",
    ),
    Mutant(
        "edit_does_not_record_confirmed",
        CLI,
        r"r\.confirmed = True  # DEC-42.*$",
        "r.confirmed = False",
        day=6,
        what="an edit leaves confirmed False so the edited file never passes --yes (DEC-42)",
    ),
    Mutant(
        "yes_confirmed_role_difference_without_a_summary",
        MAPPING,
        r'and f\.confidence != "high"\n            and _summaries_agree\(prior, fresh, '
        r"f\.original\) is not None\n        \):",
        'and f.confidence != "high"\n        ):',
        day=6,
        # re-anchored in repair 4.2 (the condition gained two clauses)
        what="an interactive prior's edited Gender with its stored summary deleted passes --yes",
    ),
    # repair 4.2 of A-P1 (lens-1 round 1 on 9cfbdd5; DEC-42 narrowed)
    Mutant(
        "interactive_prior_relabelled_file",
        MAPPING,
        r"        return prior\n\n    if non_interactive:\n        if prior is None:",
        '        if prior.decided_by == "interactive":\n            prior.decided_by = "file"\n'
        "        return prior\n\n    if non_interactive:\n        if prior is None:",
        day=6,
        what="an interactive prior is written back file, so a second --yes on an edit is H07",
    ),
    Mutant(
        "yes_exemption_reads_file_as_interactive",
        MAPPING,
        r'prior\.decided_by == "interactive"\n            and p\.confirmed',
        "prior.decided_by in CONFIRMED_DECIDED_BY\n            and p.confirmed",
        day=6,
        what="a file prior confirmed on Gender -> attr_gender_code passes --yes (lens-1 B1)",
    ),
    Mutant(
        "yes_exemption_reads_the_stored_confidence",
        MAPPING,
        r'and f\.confidence != "high"\n            and _summaries_agree',
        'and p.confidence != "high"\n            and _summaries_agree',
        day=6,
        what="confidence: medium typed on age beside interactive and confirmed passes --yes",
    ),
    Mutant(
        "yes_exemption_ignores_the_confidence",
        MAPPING,
        r'and f\.confidence != "high"\n            and _summaries_agree',
        "and _summaries_agree",
        day=6,
        what="decided_by: interactive typed beside confirmed on age (high) passes --yes",
    ),
    Mutant(
        "yes_missing_summary_compared",
        MAPPING,
        r"if original not in prior\.value_summaries or original not in fresh\.value_summaries:",
        "if original not in prior.value_summaries and original not in fresh.value_summaries:",
        day=6,
        what="a confirmed prior without a summary for the column is exit 5 KeyError (lens-2 M06)",
    ),
)

CRITERIA = "src/proofpack/criteria.py"
ATTAINABILITY = "src/proofpack/stats/attainability.py"
LEDGER = "src/proofpack/io/ledger.py"
MANIFEST = "src/proofpack/manifest.py"
LICENCE_VERIFY = "src/proofpack/licence/verify.py"
RUN = "src/proofpack/run.py"
DESCRIPTIVE = "src/proofpack/stats/descriptive.py"
BOOTSTRAP = "src/proofpack/stats/bootstrap.py"

#: The day-7 list (E7: criteria engine, attainability, ledger, manifest, licence verify,
#: the DEC-26 gate in run, the three carried items). ``--marker day7``.
MUTANTS_DAY7: tuple[Mutant, ...] = (
    Mutant(
        "comparator_ge_to_gt",
        CRITERIA,
        r"return statistic_value >= value",
        "return statistic_value > value",
        day=7,
        what="the >= comparator reads as >",
    ),
    Mutant(
        "ci_lower_bound_reads_upper",
        CRITERIA,
        r'return number\.get\("ci_lo"\)',
        'return number.get("ci_hi")',
        day=7,
        what="ci_lower_bound reads ci_hi (the ci index)",
    ),
    Mutant(
        "point_estimate_reads_lower",
        CRITERIA,
        r'return number\.get\("est"\)',
        'return number.get("ci_lo")',
        day=7,
        what="point_estimate reads ci_lo",
    ),
    Mutant(
        "fairness_bound_none_still_evaluated",
        CRITERIA,
        r'if f is None or f\.get\("bound"\) is None:',
        "if f is None:",
        day=7,
        what="a fairness block without a bound is evaluated (float(None))",
    ),
    Mutant(
        "attainability_upper_bound",
        ATTAINABILITY,
        r"return wilson_bounds\(n, n, level\)\[0\]",
        "return wilson_bounds(n, n, level)[1]",
        day=7,
        what="the k = n Wilson UPPER bound (1.0) instead of the lower",
    ),
    Mutant(
        "attainable_ge_to_gt",
        ATTAINABILITY,
        r"return bound >= value",
        "return bound > value",
        day=7,
        what="attainable_at_n for >= uses a strict comparison",
    ),
    Mutant(
        "ledger_increment_by_two",
        LEDGER,
        r"counts\[key\] = counts\.get\(key, 0\) \+ 1",
        "counts[key] = counts.get(key, 0) + 2",
        day=7,
        what="the ledger increment counts two per run",
    ),
    Mutant(
        "ledger_warn_at_limit",
        LEDGER,
        r"and count > limit:",
        "and count >= limit:",
        day=7,
        what="the warning fires at the limit instead of above it",
    ),
    Mutant(
        "manifest_criteria_hash_of_input",
        MANIFEST,
        r'"criteria_sha256": sha256_file\(criteria_path\),',
        '"criteria_sha256": sha256_file(input_path),',
        day=7,
        what="criteria_sha256 hashes the input file",
    ),
    Mutant(
        "canonical_json_unsorted",
        MANIFEST,
        r"doc, sort_keys=True, indent=1,",
        "doc, sort_keys=False, indent=1,",
        day=7,
        what="canonical JSON without sorted keys",
    ),
    Mutant(
        "signature_over_payload_bytes",
        LICENCE_VERIFY,
        r'\.verify\(signature, segment\.encode\("ascii"\)\)',
        ".verify(signature, payload_bytes)",
        day=7,
        what="the signature is checked over the decoded payload, not the segment",
    ),
    Mutant(
        "expires_compared_to_grace_end",
        LICENCE_VERIFY,
        r"if now <= expiry_with_skew:",
        "if now <= grace_with_skew:",
        day=7,
        what="ok until the end of grace (the expires comparison)",
    ),
    Mutant(
        "skew_sign_flipped",
        LICENCE_VERIFY,
        r"if now <= expiry_with_skew:",
        "if now <= effective - CLOCK_SKEW:",
        day=7,
        what="the 24 h clock-skew tolerance subtracted instead of added",
    ),
    Mutant(
        "unknown_key_id_falls_back",
        LICENCE_VERIFY,
        r"public_key = registry\.lookup\(key_id\)$",
        "public_key = registry.lookup(key_id) or next(iter(registry.keys.values()))",
        day=7,
        what="an unknown key_id falls back to the registry's first key",
    ),
    Mutant(
        "trial_takes_the_later_expiry",
        LICENCE_VERIFY,
        r"effective = min\(expires, issued \+ timedelta\(days=TRIAL_DAYS\)\)",
        "effective = max(expires, issued + timedelta(days=TRIAL_DAYS))",
        day=7,
        what="a trial's 30-day rule takes the later of the two dates",
    ),
    Mutant(
        "run_h07_gate_dropped",
        RUN,
        r"    p = default_mapping_path\(input_path\)\n    if not p\.exists\(\):",
        "    p = default_mapping_path(input_path)\n    if False:",
        day=7,
        what="run without a mapping falls through to ingest (no 'run proofpack map first')",
    ),
    Mutant(
        "refused_licence_no_watermark",
        RUN,
        # E9 moved the rule into run.watermark_for (DEC-48); the mutant is the same: the
        # manifest takes the licence's own (null) watermark on a refused licence
        r"watermark = watermark_for\(licence\)",
        "watermark = licence.watermark",
        day=7,
        what="a refused licence leaves the watermark null",
    ),
    Mutant(
        "licence_exit_code_ok",
        RUN,
        r"if not self\.licence\.usable:\n            return EXIT_LICENCE",
        "if not self.licence.usable:\n            return EXIT_OK",
        day=7,
        what="an unusable licence exits 0",
    ),
    Mutant(
        "blank_case_id_needs_four",
        SCHEMA_IO,
        r"        if blank:\n            raise HaltError\(",
        "        if blank > 3:\n            raise HaltError(",
        day=7,
        what="S05 fires only above three blank ids (carried 26)",
    ),
    Mutant(
        "dev_rows_counts_test",
        DESCRIPTIVE,
        r'int\(sum\(1 for v in table\.dataset\.tolist\(\) if v == "dev"\)\)',
        'int(sum(1 for v in table.dataset.tolist() if v == "test"))',
        day=7,
        what="flow.dev_rows counts the test rows (carried 27)",
    ),
    Mutant(
        "resample_sd_inf_kept",
        BOOTSTRAP,
        r"return None, RESAMPLE_SD_NOT_FINITE",
        "return sd, RESAMPLE_SD_NOT_FINITE",
        day=7,
        what="a non-finite resample sd is written as inf (carried 25)",
    ),
    # repair 1 of 21 September (lens 1 B1, B2, FA-N3)
    Mutant(
        "method_none_point_estimate_compared",
        CRITERIA,
        r'if reason is not None or method == "none":',
        "if False:",
        day=7,
        what="a Number with method none is compared on est under point_estimate (B1)",
    ),
    Mutant(
        "attainability_on_any_method",
        CRITERIA,
        r"if method == ATTAINABILITY_METHOD and isinstance\(n, int\) and n > 0:",
        "if isinstance(n, int) and n > 0:",
        day=7,
        what="attainable_at_n filled on a cluster-bootstrap cell (B2)",
    ),
    # repair 2 of 21 September (lens 2 FA-N1 / RG-N1)
    Mutant(
        "attainability_annotation_needs_positive_n",
        CRITERIA,
        r"elif method != ATTAINABILITY_METHOD:",
        "elif method != ATTAINABILITY_METHOD and isinstance(n, int) and n > 0:",
        day=7,
        what="the 02d00c5 guard: no method_not_wilson annotation at n 0 or n null",
    ),
    Mutant(
        "grace_overflow_raises",
        LICENCE_VERIFY,
        r'except OverflowError:\n        return _out_of_range\("grace_days", key_id\)',
        'except ZeroDivisionError:\n        return _out_of_range("grace_days", key_id)',
        day=7,
        what="grace_days 3_000_000 raises OverflowError out of verify (FA-N3)",
    ),
)

#: The day-8 list (E8: the overall block on a clustered plan, the claims generator, the
#: claim-binding checker, the number formatting, the anchors, the renderer and T8).
#: ``--marker day8``.
FORMAT = "src/proofpack/render/format.py"
GATES = "src/proofpack/gates.py"
IO_SCHEMA = "src/proofpack/io/schema.py"
CHECKER = "src/proofpack/narrate/checker.py"
CLAIMS = "src/proofpack/narrate/claims.py"
ANCHORS = "src/proofpack/render/anchors.py"
HTML = "src/proofpack/render/html.py"
T8_TEMPLATE = "src/proofpack/templates/T8.html"
BASE_TEMPLATE = "src/proofpack/templates/base.html"
MUTANTS_DAY8: tuple[Mutant, ...] = (
    Mutant(
        "format_percent_rounding_place",
        FORMAT,
        r"def percent\(x: float, places: int = 1\) -> str:",
        "def percent(x: float, places: int = 2) -> str:",
        day=8,
        what="a percentage prints two decimals instead of D4 section 1.2's one",
    ),
    Mutant(
        "format_suppressed_prints_the_count",
        FORMAT,
        r'    if num\.get\("suppressed"\):\n        return SUPPRESSED_MARK',
        '    if num.get("suppressed"):\n        return f"{SUPPRESSED_MARK} {num.get(\'n\')}"',
        day=8,
        what="a suppressed cell prints its n beside the marker (a digit from the cell)",
    ),
    Mutant(
        "checker_status_equality_skipped",
        CHECKER,
        r'        if status != row\.get\("status"\):',
        '        if status is None and status != row.get("status"):',
        day=8,
        what="a claim's status is no longer compared with criteria_results[index].status",
    ),
    Mutant(
        "checker_value_ref_unresolved_accepted",
        CHECKER,
        r'            return reject\("value_ref_unresolved", value_ref=ref\)',
        "            pass",
        day=8,
        what="an unresolved value_ref is not rejected",
    ),
    Mutant(
        "checker_digit_regex_decimal_only",
        CHECKER,
        r'        if ch\.isnumeric\(\) or unicodedata\.category\(ch\) in \("Nd", "Nl", "No"\):',
        "        if ch.isdecimal():",
        day=8,
        what="only decimal digits count as digits (a Roman numeral or a superscript passes)",
    ),
    Mutant(
        "checker_section_sign_unchecked",
        CHECKER,
        r'    if "§" in norm:',
        "    if False:",
        day=8,
        what="the section sign is no longer a forbidden token",
    ),
    Mutant(
        "checker_guidance_ref_unchecked",
        CHECKER,
        r"        if not isinstance\(gref, str\) or gref not in guidance:",
        "        if False:",
        day=8,
        what="a guidance_ref outside the map is accepted",
    ),
    Mutant(
        "checker_criterion_index_missing_tolerated",
        CHECKER,
        r'        if index is None:\n            return reject\("criterion_index_missing"',
        '        if index is None and claim["criterion_id"] is None:\n'
        '            return reject("criterion_index_missing"',
        day=8,
        what="a criterion addressed by id with no position is not rejected as index-missing",
    ),
    Mutant(
        "claims_relation_above_on_upper_bound",
        CLAIMS,
        r'    if lo > 0:\n        return "above"',
        '    if hi > 0:\n        return "above"',
        day=8,
        what="a difference whose interval spans zero is read as above",
    ),
    Mutant(
        "anchors_draft_label_lookup_skipped",
        ANCHORS,
        r"        if DRAFT_QUALIFIER not in status\.lower\(\):",
        "        if False:",
        day=8,
        what="a draft map row without the not-for-implementation qualifier is rendered",
    ),
    Mutant(
        "html_autoescape_off",
        HTML,
        r"        autoescape=True,",
        "        autoescape=False,",
        day=8,
        what="customer text is rendered unescaped",
    ),
    Mutant(
        "html_criteria_rows_keyed_by_id",
        HTML,
        r'    for i, row in enumerate\(document\.get\("criteria_results"\) or \[\]\):',
        "    for i, row in enumerate(\n"
        '        {r["criterion_id"]: r for r in document.get("criteria_results") or []}.values()\n'
        "    ):",
        day=8,
        what="the criteria table is keyed by id, so rows sharing an id collapse to one",
    ),
    Mutant(
        "html_claims_generated_off_by_one",
        HTML,
        r'        "claims_generated": len\(document\.get\("claims"\) or \[\]\),',
        '        "claims_generated": len(document.get("claims") or []) + 1,',
        day=8,
        what="section 7's claims count is off by one",
    ),
    Mutant(
        "t8_footer_dropped_from_page_two",
        T8_TEMPLATE,
        r'\{\{ page_footer\(\) \}\}\n</section>\n<section class="page" id="page-3">',
        '</section>\n<section class="page" id="page-3">',
        day=8,
        what="the second page section has no footer",
    ),
    Mutant(
        "run_clustered_overall_uses_the_analytic_route",
        RUN,
        r"        if not clustered:\n"
        r"            block = \{k: v\.as_dict\(\) for k, v in metrics\.items\(\)\}",
        "        if True:\n            block = {k: v.as_dict() for k, v in metrics.items()}",
        day=8,
        what="the overall block takes two_by_two_metrics (Wilson) on a clustered plan",
    ),
    # --- repair 1 of day 8 (23 September): one mutant per rule the lenses found missing
    Mutant(
        "checker_metric_binding_skipped",
        CHECKER,
        r"            if f\.metric is not None and f\.metric not in allowed:",
        "            if False:",
        day=8,
        what="a value_ref naming a sibling metric is accepted (FA-B1)",
    ),
    Mutant(
        "checker_operating_point_binding_skipped",
        CHECKER,
        r"        return reject\(\"operating_point_mismatch\", value_ref=ref, "
        r"operating_point=op\)",
        "        continue",
        day=8,
        what="a value_ref naming another operating point is accepted (FA-B1)",
    ),
    Mutant(
        "checker_relation_fallthrough_accepts_estimate",
        CHECKER,
        r'        expected = "not_assessable"$',
        '        expected = claim["relation"]',
        day=8,
        what="a claim binding no Number may state relation estimate (FA-B1: the tp count)",
    ),
    Mutant(
        "checker_duplicate_claim_ids_tolerated",
        CHECKER,
        r"    repeated = \{i for i in ids if isinstance\(i, str\) and ids\.count\(i\) > 1\}",
        "    repeated = set()",
        day=8,
        what="two claims with one claim_id are both accepted (FA-N4)",
    ),
    Mutant(
        "checker_confusables_unmapped",
        CHECKER,
        r"        ch = confusables\.get\(ch, ch\)",
        "        ch = ch",
        day=8,
        what="a Cyrillic a in pass is not mapped to a (FA-B2)",
    ),
    # checker_format_characters_kept (repair 1, FA-B2) was withdrawn at 7fa690b; lens RG-B3
    # of round 3 fed com­pass (real code: accepted; mutant: rejected). It is restored
    # in the repair-3 block below with the test that feeds that literal.
    Mutant(
        "checker_join_window_short",
        CHECKER,
        r"^_JOIN_RUN = 14$",
        "_JOIN_RUN = 12",
        day=8,
        what="the thirteen spaced letters of a longest listed word are not joined (FA-B4)",
    ),
    Mutant(
        "checker_hyphen_parts_not_split",
        CHECKER,
        r'        out\.update\(token\.split\("-"\)\)',
        "        pass",
        day=8,
        what="un-biased and pass- are matched as whole tokens only (FA-B2)",
    ),
    Mutant(
        "gates_h02_skips_y_pred",
        GATES,
        r'    for column, values in \(\("y_true", table\.y_true\), \("y_pred", table\.y_pred\)\):',
        '    for column, values in (("y_true", table.y_true),):',
        day=8,
        what="a y_pred column outside the declared classes passes H02 (FA-B3)",
    ),
    Mutant(
        "format_declared_rounds_to_three",
        FORMAT,
        r'    return format\(Decimal\(repr\(float\(x\)\)\), "f"\)\.replace\("-", MINUS\)',
        "    return _plain(float(x), 3)",
        day=8,
        what="a declared 0.4275 prints 0.427 (FA-B4)",
    ),
    Mutant(
        "t8_prior_version_read_under_strict_undefined",
        T8_TEMPLATE,
        r"\{% if model\.prior_version is not none %\}",
        "{% if document.declarations.model.prior_version %}",
        day=8,
        what="a criteria.yaml without model.prior_version fails the render (FA-B5)",
    ),
    Mutant(
        "html_declaration_index_ignored",
        HTML,
        r'    index = row\.get\("declaration_index"\)',
        "    index = 0",
        day=8,
        what="every criteria row prints the first entry's author and justification (FA-N1)",
    ),
    Mutant(
        "criteria_declaration_index_dropped",
        CRITERIA,
        r"                    declaration_index=k,",
        "                    declaration_index=None,",
        day=8,
        what="criteria rows carry no declaration index (FA-N1)",
    ),
    Mutant(
        "run_prevalence_wrong_key",
        RUN,
        r"        prevalence = clustered_proportion\(all_rows, pos, "
        r'_overall_cell_key\("prevalence"\)\)',
        "        prevalence = clustered_proportion(all_rows, ~pos, "
        '_overall_cell_key("prevalence"))',
        day=8,
        what="the clustered overall prevalence is the negative share (lens FA-N2's survivor)",
    ),
    # --- repair 2 of day 8 (23 September): one mutant per rule the lens-2 pair found missing
    Mutant(
        "schema_blank_y_pred_analysed",
        IO_SCHEMA,
        r"        sc_missing = np\.array\(\[v is None for v in table\.y_pred\.tolist\(\)\], "
        r"dtype=bool\)",
        "        sc_missing = np.zeros(n, dtype=bool)",
        day=8,
        what="a blank y_pred on a table without a score column is analysed as a negative "
        "prediction (FA-B1 / RG-B1)",
    ),
    Mutant(
        "schema_indeterminate_y_pred_ignored",
        IO_SCHEMA,
        r"    if table\.y_pred is not None:\n        indet \|= np\.array\(",
        "    if False:\n        indet |= np.array(",
        day=8,
        what="a y_pred equal to a declared indeterminate value is analysed as a negative "
        "prediction (FA-B1)",
    ),
    Mutant(
        "gates_h02_skips_y_pred_beside_a_score",
        GATES,
        r"        if values is None:\n            continue\n        observed",
        '        if values is None or (column == "y_pred" and table.score is not None):\n'
        "            continue\n        observed",
        day=8,
        what="H02 does not read y_pred when a score column exists (RG-N2, FA-N4's survivor)",
    ),
    Mutant(
        "checker_offshape_pointer_bound_by_nothing",
        CHECKER,
        r'        if f is None:\n            return reject\("value_ref_unbound", value_ref=ref, '
        r'reason="path off the pointer shapes"\)',
        "        if f is None:\n            continue",
        day=8,
        what="a Number off the eight pointer shapes is accepted unbound (FA-B2)",
    ),
    Mutant(
        "checker_unbound_template_binds_a_number",
        CHECKER,
        r"    if numbers and template_id not in BOUND_TEMPLATES:",
        "    if False:",
        day=8,
        what="a template outside the bound set binds a Number (FA-B2: 20 templates)",
    ),
    Mutant(
        "checker_scalar_under_estimate_template_accepted",
        CHECKER,
        r"    if template_id in ESTIMATE_TEMPLATES and len\(numbers\) != len\(refs\):",
        "    if False:",
        day=8,
        what="OVERALL_ESTIMATE over /flow/analysed alone is accepted (FA-B2)",
    ),
    Mutant(
        "checker_null_metric_binds_any_number",
        CHECKER,
        r"    if numbers and metric_id is None:",
        "    if False:",
        day=8,
        what="a claim with metric_id null binds any Number (FA-B2)",
    ),
    Mutant(
        "checker_operating_point_null_ignored",
        CHECKER,
        r"        if f\.operating_point == op:\n            continue",
        "        if f.operating_point == op or f.operating_point is None:\n            continue",
        day=8,
        what="AUROC_ESTIMATE with operating_point op1 is accepted (FA-B2)",
    ),
    Mutant(
        "checker_reference_null_on_difference_accepted",
        CHECKER,
        r'        if reference is None and block_read == "diff_vs_reference" '
        r"and ref_level is not None:",
        "        if False:",
        day=8,
        what="a diff_vs_reference claim with reference null is accepted (FA-B2)",
    ),
    Mutant(
        "checker_swapped_difference_slots_accepted",
        CHECKER,
        r"        if len\(blocks\) != 2 or blocks\[0\] is not None "
        r"or blocks\[1\] not in DIFFERENCE_BLOCKS:",
        "        if len(blocks) != 2:",
        day=8,
        what="the estimate and difference pointers swapped are accepted (FA-B2)",
    ),
    Mutant(
        "checker_token_runs_not_joined",
        CHECKER,
        r"            joined \+= parts\[j\]\n            out\.add\(joined\)",
        "            joined += parts[j]",
        day=8,
        what="p a s s and pa-ss are matched as separate tokens only (FA-B4 / RG-B2)",
    ),
    Mutant(
        "checker_small_capitals_unmapped",
        CHECKER,
        r'    "ᴘ": "p",',
        '    "ᴘ": "ᴘ",',
        day=8,
        what="the small capital P is not mapped to p (RG-B2)",
    ),
    Mutant(
        "html_has_criteria_from_declarations_only",
        HTML,
        r'        "has_criteria": bool\(document\.get\("criteria_results"\)\)\n        or bool\(',
        '        "has_criteria": False\n        or bool(',
        day=8,
        what="a fairness bound without a criteria list prints no criteria table (FA-B3)",
    ),
    # --- repair 3 of day 8 (23 September): the lens-3 pair's findings at 7fa690b
    Mutant(
        "checker_format_characters_kept",
        CHECKER,
        r'        if unicodedata\.category\(ch\) in \("Mn", "Cf"\):',
        "        if False:",
        day=8,
        what="a soft hyphen or zero-width joiner is kept: com\\u00adpass reads com + pass (RG-B3)",
    ),
    Mutant(
        "checker_well_calibrated_substring_dropped",
        CHECKER,
        r'    if any\("wellcalibrated" in _LETTERS_ONLY\.sub\("", r\) for r in readings\):',
        "    if False:",
        day=8,
        what="well-calibratedness is accepted (RG-B1)",
    ),
    Mutant(
        "checker_well_calibrated_hyphen_only",
        CHECKER,
        r'    if any\("wellcalibrated" in _LETTERS_ONLY\.sub\("", r\) for r in readings\):',
        '    if any("wellcalibrated" in r.replace("-", "") for r in readings):',
        day=8,
        what="well calibratedness (a space, then letters) is accepted (lens-4 FA-B4 / RG-N2)",
    ),
    Mutant(
        "checker_earlier_readings_dropped",
        CHECKER,
        r"_READING_MAPS: tuple\[dict\[str, str\], \.\.\.\] = \(\n    _CONFUSABLES_R1,\n"
        r"    \{\*\*_CONFUSABLES_R1, \*\*_SMALL_CAPITALS\},\n\)",
        "_READING_MAPS: tuple[dict[str, str], ...] = ()",
        day=8,
        what="pass + small capital A reads passa only and is accepted (RG-B1)",
    ),
    Mutant(
        "checker_capital_i_reading_dropped",
        CHECKER,
        r'    capital_i = normalise_free_text\(raw\.replace\("I", "l"\)\)',
        "    capital_i = full",
        day=8,
        what="faiI is accepted (FA-B2)",
    ),
    Mutant(
        "checker_rn_reading_dropped",
        CHECKER,
        r'    rn = full\.replace\("rn", "m"\)',
        "    rn = full",
        day=8,
        what="rneets is accepted (FA-B2)",
    ),
    Mutant(
        "checker_latin_alpha_unmapped",
        CHECKER,
        r'    "ɑ": "a",  # Latin alpha, U\+0251',
        '    "ɑ": "ɑ",  # Latin alpha, U+0251',
        day=8,
        what="p + Latin alpha U+0251 + ss is accepted (FA-B2)",
    ),
    Mutant(
        "checker_f_with_hook_unmapped",
        CHECKER,
        r'    "ƒ": "f",',
        '    "ƒ": "ƒ",',
        day=8,
        what="U+0192 f with hook + ail is accepted (FA-B2)",
    ),
    Mutant(
        "checker_dental_click_unmapped",
        CHECKER,
        r'    "ǀ": "l",',
        '    "ǀ": "ǀ",',
        day=8,
        what="fai + U+01C0 dental click is accepted (FA-B2)",
    ),
    Mutant(
        "checker_armenian_oh_unmapped",
        CHECKER,
        r'    "օ": "o",',
        '    "օ": "օ",',
        day=8,
        what="g + two Armenian oh U+0585 + d is accepted (FA-B2)",
    ),
    Mutant(
        "checker_cherokee_p_unmapped",
        CHECKER,
        r'    "Ꮲ": "p",',
        '    "Ꮲ": "Ꮲ",',
        day=8,
        what="Cherokee U+13E2 + ass is accepted (FA-B2)",
    ),
    Mutant(
        "checker_lunate_sigma_read_after_nfkc",
        CHECKER,
        r'_BEFORE_NFKC: dict\[str, str\] = \{"ϲ": "c", "Ϲ": "c"\}',
        "_BEFORE_NFKC: dict[str, str] = {}",
        day=8,
        what="Greek lunate sigma U+03F2 + onsistent is accepted (FA-B2)",
    ),
    Mutant(
        "checker_not_met_record_on_any_row",
        CHECKER,
        r'        if template_id == "CRITERION_NOT_MET_RECORD" and row\.get\("status"\) '
        r'!= "not_met":',
        "        if False:",
        day=8,
        what="CRITERION_NOT_MET_RECORD is accepted on a met row (RG-B2 / FA-B1)",
    ),
    Mutant(
        "checker_attainability_note_on_any_row",
        CHECKER,
        r'        if template_id == "ATTAINABILITY_NOTE" and not isinstance\('
        r'row\.get\("attainable_at_n"\), bool\):',
        "        if False:",
        day=8,
        what="ATTAINABILITY_NOTE is accepted on a row without attainable_at_n (RG-B2)",
    ),
    Mutant(
        "checker_template_shapes_unchecked",
        CHECKER,
        r"        if shapes is not None and f\.shape not in shapes:",
        "        if False:",
        day=8,
        what="the overall sensitivity is accepted as AUROC_ESTIMATE (RG-B2 / FA-B1)",
    ),
    Mutant(
        "checker_auroc_template_metric_unchecked",
        CHECKER,
        r"    if template_metrics is not None and metric_id not in template_metrics:",
        "    if False:",
        day=8,
        what="AUROC_ESTIMATE over the threshold-free prevalence is accepted (FA-B1)",
    ),
    Mutant(
        "checker_slot_order_unchecked",
        CHECKER,
        r"        if -1 in slot_positions or slot_positions != sorted\(set\(slot_positions\)\):",
        "        if -1 in slot_positions:",
        day=8,
        what="FAIRNESS_GAP with tpr_gap and fpr_gap swapped is accepted (FA-B1)",
    ),
    Mutant(
        "checker_scalar_slots_unchecked",
        CHECKER,
        r"        if -1 in scalar_positions or scalar_positions != "
        r"sorted\(set\(scalar_positions\)\):",
        "        if False:",
        day=8,
        what="SITE_COUNT over /flow/rows_read is accepted (FA-B1)",
    ),
    Mutant(
        "checker_scalar_slot_order_unchecked",
        CHECKER,
        r"        if -1 in scalar_positions or scalar_positions != "
        r"sorted\(set\(scalar_positions\)\):",
        "        if -1 in scalar_positions:",
        day=8,
        what="FLOW_COUNTS with its seven counts reversed is accepted (FA-B1)",
    ),
    Mutant(
        "checker_count_template_scope_unchecked",
        CHECKER,
        r"    if template_id in SCALAR_SLOTS and any\(",
        "    if False and any(",
        day=8,
        what="FLOW_COUNTS carrying sensitivity, op1 and sex = F is accepted (FA-B1)",
    ),
    Mutant(
        "checker_calib_na_beside_calibration",
        CHECKER,
        r'    if template_id == "CALIB_NA" and isinstance\(doc\.get\("calibration"\), dict\):',
        "    if False:",
        day=8,
        what="CALIB_NA is accepted on a document with a calibration block (FA-B1)",
    ),
    Mutant(
        "declare_reserved_operating_point_ids_accepted",
        DECLARE,
        r"    reserved = \[i for i in op_ids if i in RESERVED_OPERATING_POINT_IDS\]",
        "    reserved = []",
        day=8,
        what="an operating point declared threshold_free loses its block (FA-B3)",
    ),
    Mutant(
        "declare_reserved_ids_threshold_free_only",
        DECLARE,
        r'frozenset\(\{"threshold_free", "auroc", "brier"\}\)',
        'frozenset({"threshold_free"})',
        day=8,
        what="an operating point declared auroc drops its subgroup cells (repair 3)",
    ),
    # repair 4 (lens round 4 at 23f3d9f)
    Mutant(
        "checker_tr39_map_empty",
        CHECKER,
        r"    for k, v in tr39_mod\.CONFUSABLES\.items\(\)",
        "    for k, v in {}.items()",
        day=8,
        what="the vendored TR39 data is not read: Lisu PA + ass is accepted (FA-B4, DEC-60)",
    ),
    Mutant(
        "checker_tr39_reading_dropped",
        CHECKER,
        r'    tr39 = normalise_free_text\(tr\)\.replace\("rn", "m"\)',
        "    tr39 = full",
        day=8,
        what="Lisu PA + assIng is accepted (FA-B4)",
    ),
    Mutant(
        "checker_tr39_capital_i_reading_dropped",
        CHECKER,
        r'    tr39_i = normalise_free_text\(tr\.replace\("I", "l"\)\)\.replace\("rn", "m"\)',
        "    tr39_i = full",
        day=8,
        what="Lisu TSA + aiI is accepted (FA-B4)",
    ),
    Mutant(
        "claims_metric_ref_split_again",
        CLAIMS,
        r"        ref = row_refs\[i\]",
        '        ref = _dotted_to_pointer(row.get("metric_ref"))',
        day=8,
        what="the criterion claim for operating point [0] binds operating point 0's Number (FA-B1)",
    ),
    Mutant(
        "html_metric_ref_split_again",
        HTML,
        r"        ref = row_refs\[i\]",
        '        ref = claims_mod._dotted_to_pointer(row.get("metric_ref"))',
        day=8,
        what="T8 prints operating point 0's Number on the [0] row (FA-B1)",
    ),
    Mutant(
        "checker_metric_ref_split_again",
        CHECKER,
        r"        row_ref = row_refs\[index\] if index < len\(row_refs\) else None",
        '        row_ref = claims_mod._dotted_to_pointer(row.get("metric_ref"))',
        day=8,
        what="the engine's criterion claim on operating point [0] is rejected (FA-B1)",
    ),
    Mutant(
        "gates_dec61_y_pred_operating_points_unchecked",
        GATES,
        r"    if table\.score is not None or len\(decl\.operating_points\) <= 1:",
        "    if True:",
        day=8,
        what="a y_pred-only table with two operating points runs (FA-B2, DEC-61)",
    ),
    Mutant(
        "run_dec61_gate_not_called_in_overall_block",
        RUN,
        r"    gate_h08_y_pred_operating_points\(table, decl\)  # DEC-61",
        "    pass  # DEC-61",
        day=8,
        what="overall_block prints one y_pred two-by-two under two thresholds (FA-B2)",
    ),
    Mutant(
        "claims_calib_na_on_any_reason",
        CLAIMS,
        r"        if calibration_suppression\(doc\) != CALIB_NA_REASON:",
        "        if False:",
        day=8,
        what="a y_pred-only document carries CALIB_NA (FA-B3)",
    ),
    Mutant(
        "checker_calib_na_reason_unchecked",
        CHECKER,
        r"        and claims_mod\.calibration_suppression\(doc\) != claims_mod\.CALIB_NA_REASON",
        "        and False",
        day=8,
        what="CALIB_NA on a no_score_column document is accepted (FA-B3)",
    ),
    Mutant(
        "html_header_model_not_customer_text",
        BASE_TEMPLATE,
        r'<header class="page-header"><span class="customer-text">',
        '<header class="page-header"><span>',
        day=8,
        what="the model name and version in the page header are engine text (DEC-62)",
    ),
    Mutant(
        "t8_operating_point_cell_not_customer_text",
        # E9: T8's criteria table is the one macro T1 shares (templates/_criteria.html)
        "src/proofpack/templates/_criteria.html",
        r'<td\{% if r\.operating_point_is_customer_text %\} class="customer-text"\{% endif %\}>',
        "<td>",
        day=8,
        what="the criteria table's operating-point id is engine text (DEC-62)",
    ),
    # repair 5 of build day 8 (lens-5 FA5-B4, DEC-65): the control-character gate
    Mutant(
        "declare_dec65_check_not_called",
        DECLARE,
        r"^    _check_control_characters\(data\)$",
        "    pass",
        day=8,
        what="a NUL in the model name reaches T8.html raw (FA5-B4, DEC-65)",
    ),
    Mutant(
        "declare_dec65_multiline_everywhere",
        DECLARE,
        r"rx = _CONTROL_MULTILINE if key in MULTILINE_FIELDS else _CONTROL",
        "rx = _CONTROL_MULTILINE",
        day=8,
        what="a tab or line feed in the model name passes (DEC-65)",
    ),
    Mutant(
        "declare_dec65_multiline_nowhere",
        DECLARE,
        r"rx = _CONTROL_MULTILINE if key in MULTILINE_FIELDS else _CONTROL",
        "rx = _CONTROL",
        day=8,
        what="a line feed in a justification is H08 (DEC-65's recorded choice)",
    ),
    Mutant(
        "declare_dec65_c1_and_del_dropped",
        DECLARE,
        r'(^_CONTROL = re\.compile\("\[\\x00-\\x1f)\\x7f-\\x9f\]',
        r"\1]",
        day=8,
        what="DEL and C1 controls (U+007F, U+0085, U+009F) in the model name pass (DEC-65)",
    ),
    Mutant(
        "declare_dec65_keys_unchecked",
        DECLARE,
        r"            if isinstance\(k, str\) and _CONTROL\.search\(k\):",
        "            if False:",
        day=8,
        what="a key holding U+0001 passes (DEC-65)",
    ),
    Mutant(
        "mapping_dec65_check_not_called",
        MAPPING,
        r"^        _check_control_characters\(m\)$",
        "        pass",
        day=8,
        what="a control character in mapping.json notes or timestamp passes (DEC-65)",
    ),
    Mutant(
        "mapping_dec65_role_not_read",
        MAPPING,
        r'\{"role": r\.role, "notes": list\(r\.notes\)\}',
        '{"notes": list(r.notes)}',
        day=8,
        what="the mapping role attr_colour plus a line feed halts H07, not H08 (DEC-65)",
    ),
    # repair 6 of build day 8 (lens-6 FA-B1 / DEC-66, RG-B1, FA-N4)
    Mutant(
        "schema_dec66_check_not_called",
        IO_SCHEMA,
        r"^    check_control_characters\(raw, period\)$",
        "    pass",
        day=8,
        what="race levels re\\x01d / bl\\x1bue reach T8.html raw with exit 0 (DEC-66)",
    ),
    Mutant(
        "schema_dec66_c1_dropped",
        IO_SCHEMA,
        r'(^_CONTROL_CELL = re\.compile\("\[\\x00-\\x1f)\\x7f-\\x9f\]',
        r"\1]",
        day=8,
        what="attr_colour levels re\\x85d / bl\\x9fue (C1) pass ingest (DEC-66)",
    ),
    Mutant(
        "declare_self_reference_check_dropped",
        DECLARE,
        r"^    cycle = self_reference_at\(data\)$",
        "    cycle = None",
        day=8,
        what="zz_extra: &a [*a] is not the self-reference H08 (lens-6 RG-B1)",
    ),
    Mutant(
        "declare_walk_enters_shared_objects_again",
        DECLARE,
        r"elif isinstance\(v, \(dict, list, tuple\)\) and id\(v\) not in entered:",
        "elif isinstance(v, (dict, list, tuple)):",
        day=8,
        what="an alias chain 24 deep is walked leaf by leaf (lens-6 FA-N4)",
    ),
)

#: The day-9 list (E9: the template library's facet bindings, the sentence renderer, T1,
#: T7, the D5 furniture, the figures, the --templates dispatch and the sample pack).
#: ``--marker day9``.
TEMPLATES_LIB = "src/proofpack/narrate/templates.py"
SENTENCES = "src/proofpack/render/sentences.py"
T1_RENDER = "src/proofpack/render/t1.py"
T7_RENDER = "src/proofpack/render/t7.py"
FIGURES = "src/proofpack/render/figures.py"
RUN = "src/proofpack/run.py"
SAMPLE_PACK = "scripts/build_sample_pack.py"
MUTANTS_DAY9: tuple[Mutant, ...] = (
    Mutant(
        "facet_est_swapped_for_ci_lo",
        TEMPLATES_LIB,
        r'("OVERALL_ESTIMATE": \{\n        "k": \(f"\{_V\}\.k",\),\n'
        r'        "n": \(f"\{_V\}\.n",\),\n'
        r'        "est": \(f"\{_V\}\.)est(",\),)',
        r"\1ci_lo\2",
        day=9,
        what="OVERALL_ESTIMATE's {est} slot takes the Number's ci_lo facet",
    ),
    Mutant(
        "facet_family_slot_bound_to_another_pointer",
        TEMPLATES_LIB,
        r'^        "slope": \("slope\.est",\),$',
        '        "slope": ("intercept.est",),',
        day=9,
        what="CALIB_HIERARCHY's slope slot prints the intercept (binding not by facet)",
    ),
    Mutant(
        "status_word_printed_as_fixed_text",
        SENTENCES,
        r'parts\.append\(Part\(lib\.STATUS_WORDS\[str\(text\[slot\]\)\], "status"\)\)',
        'parts.append(Part(lib.STATUS_WORDS[str(text[slot])], "fixed"))',
        day=9,
        what="a criterion sentence's status word leaves .status (the verdict grep's scope)",
    ),
    Mutant(
        "t1_section_anchor_id_swapped",
        T1_RENDER,
        r'^    "s8": \("FDA_AIDSF_CALIBRATION",\),$',
        '    "s8": ("PP_METHODS",),',
        day=9,
        what="T1 section 8 cites the wrong guidance anchor",
    ),
    Mutant(
        "t1_draft_label_lookup_ignores_the_map_given",
        T1_RENDER,
        r"^    refs = anchors\.resolve\(ids, guidance_map\)$",
        "    refs = anchors.resolve(ids)",
        day=9,
        what="T1 labels anchors from the packaged map, not the one it was given",
    ),
    Mutant(
        "t1_placeholder_branch_never_taken",
        T1_RENDER,
        r'"filled": text is not None,',
        '"filled": True,',
        day=9,
        what="an unfilled customer-text slot prints no placeholder box",
    ),
    Mutant(
        "t7_methods_from_a_static_list",
        T7_RENDER,
        r'return Counter\(str\(n\.get\("method"\)\) for n in number_objects\(document\)\)',
        "return Counter(METHOD_DESCRIPTIONS)",
        day=9,
        what="T7 lists every method ProofPack knows instead of those the run used",
    ),
    Mutant(
        "f4_omission_condition_dropped",
        FIGURES,
        r"^    if isinstance\(cal, dict\):\n        return None$",
        "    if True:\n        return None",
        day=9,
        what="a null calibration omits F4 without printing the reason",
    ),
    Mutant(
        "f5_criterion_line_for_any_statistic",
        FIGURES,
        r'and row\.get\("statistic"\) == "ci_lower_bound"',
        "and True",
        day=9,
        what="F5 draws a criterion line for a point-estimate criterion",
    ),
    Mutant(
        "svg_map_y_axis_not_inverted",
        FIGURES,
        r"return self\.y0 \+ self\.h - \(float\(v\) - self\.ymin\) / \(self\.ymax - self\.ymin\) "
        r"\* self\.h",
        "return self.y0 + (float(v) - self.ymin) / (self.ymax - self.ymin) * self.h",
        day=9,
        what="the documented linear map draws y upside down",
    ),
    Mutant(
        "furniture_licence_mark_retyped",
        HTML,
        r'out\.append\(\{"kind": "licence", "text": str\(manifest\["watermark"\]\)\}\)',
        'out.append({"kind": "licence", "text": "LICENCE EXPIRED - not for submission"})',
        day=9,
        what="the cover stamp prints one retyped mark whatever the manifest carries",
    ),
    Mutant(
        "templates_dispatch_drops_t1",
        RUN,
        r'return \{"T1": write_t1, "T7": write_t7, "T8": write_t8\}',
        'return {"T7": write_t7, "T8": write_t8}',
        day=9,
        what="--templates T1 writes nothing",
    ),
    Mutant(
        "dec48_no_licence_mark_dropped",
        RUN,
        r'return WATERMARK_NO_LICENCE if licence\.reason_code == "no_file" else WATERMARK_EXPIRED',
        "return WATERMARK_EXPIRED",
        day=9,
        what="a run with no licence file carries the expired mark (DEC-48 undone)",
    ),
    Mutant(
        "theme_block_escaped_again",
        BASE_TEMPLATE,
        r"^\{\{ css \| safe \}\}$",
        "{{ css }}",
        day=9,
        what="the font stacks reach <style> as &#34; and every page falls back to serif",
    ),
    Mutant(
        "sample_pack_unmarked",
        SAMPLE_PACK,
        r"data_marking=SYNTHETIC_MARK",
        "data_marking=None",
        day=9,
        what="the sample pack's pages carry no SYNTHETIC mark",
    ),
)

MUTANTS = MUTANTS + MUTANTS_DAY6_A + MUTANTS_DAY7 + MUTANTS_DAY8 + MUTANTS_DAY9


def make_copy() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="proofpack-mutants-"))
    for item in COPIED:
        src = REPO / item
        if src.is_dir():
            shutil.copytree(src, tmp / item, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, tmp / item)
    return tmp


EGRESS_SUPPRESS = "src/proofpack/egress/suppress.py"
EGRESS_PSEUDONYMISE = "src/proofpack/egress/pseudonymise.py"
EGRESS_WHITELIST = "src/proofpack/egress/whitelist.py"
EGRESS_BUILD = "src/proofpack/egress/build.py"
EGRESS_TELEMETRY = "src/proofpack/egress/telemetry.py"
CLI = "src/proofpack/cli.py"

#: A-P2 (build day 8, lane A): the egress rules, the telemetry send and --offline. Run
#: with ``--marker ap2`` (the tests carry ``day8`` and ``ap2``).
AP2_MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "ap2_min_n_default_5",
        EGRESS_SUPPRESS,
        r"DEFAULT_MIN_N = 10",
        "DEFAULT_MIN_N = 5",
        what="k-suppression floor on n: 5 rows instead of 10",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_min_events_default_1",
        EGRESS_SUPPRESS,
        r"DEFAULT_MIN_EVENTS = 5",
        "DEFAULT_MIN_EVENTS = 1",
        what="k-suppression floor on events: 1 instead of 5",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_min_nonevents_default_1",
        EGRESS_SUPPRESS,
        r"DEFAULT_MIN_NONEVENTS = 5",
        "DEFAULT_MIN_NONEVENTS = 1",
        what="k-suppression floor on non-events: 1 instead of 5",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_looser_value_accepted",
        EGRESS_SUPPRESS,
        r"if declared < default:",
        "if declared > default:",
        what="a looser egress.suppression value is accepted and a stricter one refused",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_unknown_n_not_suppressed",
        EGRESS_SUPPRESS,
        r"if n is None or n < thresholds\.min_n:",
        "if n is not None and n < thresholds.min_n:",
        what="a cell whose n is unknown passes unsuppressed",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_pseudonym_order_reversed",
        EGRESS_PSEUDONYMISE,
        r"chosen = originals\n",
        "chosen = list(reversed(originals))\n",
        what="pseudonym order: last code point first",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_unknown_row_pseudonymised",
        EGRESS_PSEUDONYMISE,
        r"    if level == UNKNOWN_LEVEL:\n        return level\n",
        "    if False:\n        return level\n",
        what="the Unknown/missing row loses its pass-through",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_whitelist_keeps_unknown_keys",
        EGRESS_WHITELIST,
        r"        # every key of ``value`` that is not in ``props`` is dropped here\n"
        r"        return out",
        "        for key in value:\n            out.setdefault(key, value[key])\n"
        "        return out",
        what="whitelist projection passes keys the schema does not name",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_bucket_boundary_moved",
        EGRESS_BUILD,
        r'\("<1k", 0, 1_000\),\n    \("1k-10k", 1_000, 10_000\),',
        '("<1k", 0, 10_000),\n    ("1k-10k", 10_000, 10_000),',
        what="row bucket boundary: <1k swallows 1k-10k",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_manifest_sha256_over_wrapped",
        EGRESS_BUILD,
        r"return hashlib\.sha256\(canonical_json\(dict\(manifest\)\)\)\.hexdigest\(\)",
        'return hashlib.sha256(canonical_json({"m": dict(manifest)})).hexdigest()',
        what="manifest_sha256 hashes something other than the manifest block's bytes",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_licence_id_sent_when_refused",
        EGRESS_BUILD,
        r"verified = licence_status in VERIFIED_LICENCE_STATUSES",
        "verified = True",
        what="a refused licence's id is sent as if verified",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_timeout_50s",
        EGRESS_TELEMETRY,
        r"TIMEOUT_S = 5\.0",
        "TIMEOUT_S = 50.0",
        what="the one attempt waits 50 s instead of 5",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_offline_short_circuit_removed",
        EGRESS_TELEMETRY,
        r"if offline or not telemetry_enabled\(",
        "if not telemetry_enabled(",
        what="--offline no longer skips the send",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_telemetry_false_ignored",
        EGRESS_TELEMETRY,
        r'return egress\.get\("telemetry", True\) is not False',
        "return True",
        what="egress.telemetry: false no longer skips the send",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_non_2xx_counted_as_sent",
        EGRESS_TELEMETRY,
        r"if 200 <= status < 300:",
        "if 200 <= status < 600:",
        what="a 500 is reported as sent",
        day=8,
        marker="ap2",
    ),
    Mutant(
        "ap2_exit_code_changed_by_send",
        CLI,
        r"    return outcome\.exit_code\n",
        "    return EXIT_WARNINGS if sent is not None and not sent.sent else outcome.exit_code\n",
        what="a failed send turns the run's exit code into 2",
        day=8,
        marker="ap2",
    ),
)
MUTANTS = MUTANTS + AP2_MUTANTS

FIXTURES = "src/proofpack/fixtures.py"
T12 = "src/proofpack/render/t12.py"
F17_SCRIPT = "scripts/f17_determinism.py"
SBOM_SCRIPT = "scripts/sbom.py"
RELEASE_YML = ".github/workflows/release.yml"

#: A-P3 (build day 9, lane A): proofpack fixtures, F17, T12, the Dockerfile, the SBOM and
#: the workflow files. Run with ``--marker ap3`` (the tests carry ``day9`` and ``ap3``).
AP3_MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "ap3_closed_form_tolerance_1e_8",
        FIXTURES,
        r'^    "closed_form": 1e-9,$',
        '    "closed_form": 1e-8,',
        what="the closed-form tolerance class loosened from 1e-9 to 1e-8",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_matched_at_ten_times_the_tolerance",
        FIXTURES,
        r"within = dev <= tol\[name\]",
        "within = dev <= 10 * tol[name]",
        what="a value counts as within at ten times its tolerance",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_no_oracle_row_counted_matched",
        FIXTURES,
        r"    if row\.engine is None or row\.oracle is None:\n        return out\n",
        '    if row.engine is None or row.oracle is None:\n        out["matched"] = True\n'
        "        return out\n",
        what="a row with no oracle (not built, suite only, no oracle recorded) is matched",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_exit_code_ignores_not_matched",
        FIXTURES,
        r"    return EXIT_FIXTURES_NOT_MATCHED if any\(.*\) else EXIT_OK",
        "    return EXIT_OK",
        what="proofpack fixtures exits 0 with a row not matched",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_missing_dependency_counted_matched",
        FIXTURES,
        r'out\.update\(status="not_matched", reason=f"optional_dependency_missing',
        'out.update(status="matched", matched=True, reason=f"optional_dependency_missing',
        what="a comparison that could not run for want of scipy is reported matched",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_f17_mask_drops_duration_s",
        F17_SCRIPT,
        r'^MASKED_KEYS = \("run_id", "started", "duration_s"\)$',
        'MASKED_KEYS = ("run_id", "started")',
        what="F17's mask leaves duration_s unmasked",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_t12_not_matched_printed_matched",
        T12,
        r'^    "not_matched": "not matched",$',
        '    "not_matched": "matched",',
        what="T12 prints a not-matched row as matched",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_dockerfile_base_python_3_slim",
        "Dockerfile",
        r"^FROM --platform=linux/amd64 python:3\.12-slim$",
        "FROM --platform=linux/amd64 python:3-slim",
        what="the Dockerfile's base image loses its 3.12 pin",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_dockerfile_user_root",
        "Dockerfile",
        r"^USER proofpack$",
        "USER root",
        what="the image runs as root",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_release_fixtures_without_offline",
        RELEASE_YML,
        r"run: uv run proofpack fixtures --offline --out release",
        "run: uv run proofpack fixtures --out release",
        what="the release workflow runs proofpack fixtures without --offline",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_release_names_a_publishing_secret",
        RELEASE_YML,
        r"          repository-url: https://test\.pypi\.org/legacy/\n",
        "          repository-url: https://test.pypi.org/legacy/\n"
        "          password: ${{ secrets.TEST_PYPI_TOKEN }}\n",
        what="the TestPyPI step names a token secret instead of trusted publishing",
        day=9,
        marker="ap3",
    ),
    Mutant(
        "ap3_sbom_drops_dev_packages",
        SBOM_SCRIPT,
        r"        if pkg is project:\n            continue\n",
        "        if pkg is project or (name not in runtime and name not in stats):\n"
        "            continue\n",
        what="the SBOM leaves out the locked packages outside the runtime closure",
        day=9,
        marker="ap3",
    ),
)
MUTANTS = MUTANTS + AP3_MUTANTS


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
    # UTF-8 both ways (repair 3 of day 8): a failing day-8 test prints its non-ASCII
    # literals, and a cp1252 read of that output left proc.stdout None and ended the sweep
    # with a TypeError at checker_capital_i_reading_dropped
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "-m", marker],
        cwd=copy,
        env={**env_for(copy), "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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
    # --only picks by id within the day (a day-6 id needs --marker day6 beside it)
    chosen = [
        m
        for m in MUTANTS
        if (not args.only or m.id in args.only)
        and (m.day == day if day is not None else m.label == args.marker)
    ]
    if args.list:
        for m in MUTANTS:
            print(f"{m.id:<40} {m.label} {m.file:<36} {m.what}")
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
