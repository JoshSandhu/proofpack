# ProofPack reporting conventions for the T7 methods appendix

Paragraphs the T7 template (D4 section 10, build day 9) inserts verbatim. Every number here
comes from a committed script's output, named with its version and seed. These are
ProofPack conventions; no regulator specifies them, and none of them is a guarantee.

## Subgroup tables (build day 5, `stats.subgroups`)

**Attributes tabulated.** Every attribute column the mapping recognised is tabulated. An
attribute declared in `criteria.yaml` carries the manufacturer's own `prespecified` flag and
`source`; an attribute present in the table but not declared is tabulated with
`prespecified: false` and `source: exploratory`.

**Age bands.** Half-open, `lo <= age < hi`, labelled `lo-hi`. The declared bands are used
when the `age` declaration carries them. When `age` is not declared the engine uses
`[0,40), [40,65), [65,80), [80,200)` - the bands shown in D1 section 2 - and records
`bands_source: engine_default`. Ages in no band, and missing ages, sit in the Unknown row
and are counted separately (`n_outside_bands`, `n_unknown_missing`).

**The Unknown row.** Rows whose attribute value is missing form an explicit
`Unknown/missing` row. It carries its own metrics and differences, takes part in every
other level's complement, and is never a reference level.

**Reference level.** The declared level, or the largest level by n when the declaration
says `largest` (and for undeclared attributes). Ties go to the first level in the level
order (sorted labels); the attribute block records the rule used (`declared`, `largest`,
`largest_tie_first_in_level_order`).

**Complement.** The complement of a level is every other analysed row of the same
attribute, including the Unknown row. No difference is reported against the overall cohort,
because the subgroup is part of it.

**Differences.** Proportion metrics: Newcombe (1998) method 10 on independent rows. AUROC:
the unpaired DeLong (1988) difference - the two variances add because the samples are
disjoint - with a Wald interval; z and the two-sided p are detail, never a verdict. The
AUROC difference is refused with `boundary_estimate` (estimate carried, no z, no p) when
either side's DeLong variance is zero - a perfectly separated side, whose own AUROC the
engine already refuses for the same reason - because the interval would otherwise be the
other side's alone. Under clustering (declared `case_id`, or repeated case ids detected)
both analytic methods are refused with the typed reason
`clustered_data_analytic_ci_invalid`; the difference is computed by the cluster bootstrap
with each side's cases resampled independently (percentile interval, method
`cluster_bootstrap_percentile`, flag `newcombe_refused_clustered` or
`delong_refused_clustered`), and is refused outright with `cases_span_both_groups` when
any case has rows on both sides. The shared-case test is made on exactly the rows that
enter the difference (for a sensitivity difference, the reference-positive rows of each
side). On that route too a difference is refused with `boundary_estimate` (estimate
carried) when either side is frozen - when the side's own resampled statistic has a
zero-width percentile interval, the rule that refuses a single cell, applied to each side:
a perfectly separated level's AUROC, a level's proportion at 0/n or n/n, a constant-score
level's AUROC. The cell records the frozen side under `bootstrap.resampling.frozen_sides`.
Lens 2 (15 September 2026, FA-B1) measured the interval that was rendered before this
refusal existed - a 10-case level perfectly separated beside a 60-case level - covering
the true AUROC difference in 0.295 of replicates and the true sensitivity difference (a
10-case level at 10/10) in 0.615, at a nominal 0.95.

**AUROC per level** needs at least 10 positives and 10 negatives (R2 section 3.3); below
that it is shown as not evaluable with the reason, never omitted.

**Tiers** are measured in resampling units - cases under clustering, rows otherwise - and
in units carrying the event: fewer than 10 units is "not evaluable, shown for
transparency"; fewer than 30, or fewer than 5 event units, is "very low precision"; a
Wilson half-width above 0.10 is "imprecise". Annotations, never suppression (DEC-08).

**Brier per level** only when the score is declared a probability with
`higher_is_positive`; plain mean squared error, percentile bootstrap interval.

**Heterogeneity footnote.** Per attribute and operating point, a Pearson chi-square test
of homogeneity (no continuity correction) across the evaluable levels, for sensitivity
and for specificity separately; Fisher's exact test instead when there are exactly two
levels and an expected cell is below 5. The Unknown row is not a level for this purpose.
Raw p-values and Holm-adjusted p-values within the attribute family are reported with the
sentence "exploratory; no conclusion about subgroup consistency is drawn from this test".
Nothing beside a p-value is a status. Under clustering (declared `case_id`, or repeated
case ids detected) the tests are not run: they count rows as independent trials, and on
F6 with every patient's row copied three times the chi-square rose from 4.63 (p 0.099) to
13.90 (p 0.001). Every entry then carries the typed reason
`clustered_data_analytic_ci_invalid`, the footnote records the `clustering_route`, and no
p-value is printed. An attribute with fewer than two evaluable levels reports
`insufficient_levels` on every route: there was no comparison to make before the question
of independence arose.

**Fairness** is measured, never mitigated. Gaps against the reference level are the
reference-level differences read as gaps: `tpr_gap` = sensitivity difference; `fpr_gap` =
(1 - specificity) difference; `ppv_gap`, `npv_gap`, `auroc_gap`; plus a selection-rate gap
labelled `descriptive_not_target`. The `criterion_of_interest` and `bound` are the
manufacturer's declaration echoed verbatim. Calibration by group is not computed in this
build (`not_computed_this_run`). The equalised-odds / calibration impossibility result is
cited in R2 section 4 from memory and is marked **[unverified]** there and in the output.

**Declaration boundary.** Clustering is detected from repeated `case_id` values. A
manufacturer who assigns one `case_id` per lesion of a patient will receive independent-row
intervals; the engine cannot see a case column it was not given.

## Cluster-bootstrap coverage bar (DEC-08; build day 5)

`scripts/coverage_bar.py` v1, seed 20260915, R = 400 cohorts per shape, B = 1000 resamples,
nominal level 0.95, bar 0.90. The cluster-bootstrap percentile interval was formed with the
engine's own resampler and its coverage of a known truth measured; the deficient-class
refusal was bypassed so that every shape was measured. Monte-Carlo error per cell is about
0.015 (0.03 at `--quick`). Re-run with `python scripts/coverage_bar.py --full` (about 13
minutes) or `--quick` (R = 100, B = 200, 41 seconds measured on 15 September 2026).

**Constants after this measurement:** `MAX_FROZEN_VARIANCE_SHARE = 0.20` (kept). The
refusal rule is `frozen share >= 0.20`, so the shapes this constant renders are the 0.05
and 0.10 rows below (0.912 / 0.958 and 0.943 / 0.935) and the 0.20 row is the first shape
it refuses. That refused shape has been measured eight times (N = 30 / N = 120): 0.932 /
0.915 in the recorded run (R = 400, Monte-Carlo error 0.015); 0.900 / 0.870 at `--quick`
(R = 100, error 0.03); and at seed 20260916 (R = 200, B = 500, error 0.021) 0.925 / 0.915
with a fresh generator per cell and 0.880 / 0.915 with one generator shared across the
cells in share order. Two of the eight cells are below the bar: the shape sits near the
bar, not above it. The 0.30 row straddles the bar across seeds too (0.863 / 0.873
recorded; 0.930 / 0.915 at the lens's seed 7; 0.910 / 0.890 at seed 20260916). The
constant was therefore neither loosened to 0.30 nor moved: at this boundary it refuses a
shape whose measurements fall on both sides of the bar, which is the conservative side of
a measurement whose seed-to-seed spread is about two and a half Monte-Carlo standard
errors.
`MIN_UNITS_PER_STRATUM = 2` (kept, **but it does not meet the bar** - see below).

### AUROC cell: one frozen pure-positive case of 3 rows beside m mixed cases

| frozen share | m | N = 30 negatives: coverage | width | N = 120: coverage | width |
|---|---|---|---|---|---|
| 0.05 | 171 | 0.912 | 0.061 | 0.958 | 0.059 |
| 0.10 | 81 | 0.943 | 0.087 | 0.935 | 0.082 |
| 0.20 | 36 | 0.932 | 0.120 | 0.915 | 0.114 |
| 0.30 | 21 | 0.863 | 0.145 | 0.873 | 0.137 |
| 0.41 | 13 | 0.877 | 0.174 | 0.823 | 0.157 |
| 0.50 | 9 | 0.843 | 0.181 | 0.770 | 0.165 |

### AUROC cell: u pure-positive cases of 3 rows, no frozen stratum

| u | m = 0 (pure stratum alone), N = 30 | N = 120 | m = 36 mixed beside it, N = 30 | N = 120 |
|---|---|---|---|---|
| 2 | 0.715 | 0.620 | 0.910 | 0.927 |
| 3 | 0.787 | 0.715 | 0.930 | 0.907 |
| 4 | 0.815 | 0.810 | 0.912 | 0.912 |
| 5 | 0.870 | 0.795 | 0.935 | 0.900 |

### Proportion cell: u cases of w rows

| u | w = 1, p = 0.5 | w = 3, p = 0.5 | w = 1, p = 0.9 | w = 3, p = 0.9 |
|---|---|---|---|---|
| 1 | refused (share 1) | refused | refused | refused |
| 2 | 0.505 | 0.502 | 0.190 | 0.343 |
| 3 | 0.762 | 0.723 | 0.237 | 0.522 |
| 4 | 0.870 | 0.868 | 0.347 | 0.618 |
| 5 | 0.940 | 0.830 | 0.407 | 0.667 |
| 10 | 0.975 | 0.950 | 0.672 | 0.920 |
| 20 | 0.938 | 0.940 | 0.850 | 0.902 |
| 40 | 0.953 | 0.943 | 0.922 | 0.953 |

### What the table says

On this grid no value of `MIN_UNITS_PER_STRATUM` renders only shapes at or above the bar.
The shortfall is the percentile bootstrap's own behaviour with few resampling units and,
for a proportion, near a boundary: at p = 0.9 with one row per case it reaches 0.90 only at
40 cases. A floor high enough to clear that would refuse fixture F3 (five positives, R2
section 9), which pins the resampling algorithm, and most of R2 section 1.3's small-class
route. Every shape below the bar carries the R2 section 3.3 tier annotation ("not evaluable,
shown for transparency" below 10 units, "very low precision" below 30), so a reader sees the
shortage; but a cell of 10 to 40 cases at a high proportion renders with an interval that is
too narrow and only a "very low precision" or no annotation. That is an open decision for
Josh (day-5 note): a design-effect-adjusted Wilson interval for clustered proportions, an
effective-units floor per cell, or T7 carrying this table as the statement of what the
interval does. Until it is taken, this paragraph is the honest one and T7 should carry it.

The AUROC frozen-share half: every shape the constant renders measured at or above the
bar in the recorded run; the first shape it refuses did in the recorded run and in six of
eight cells over four runs (see the constants paragraph above for the seed-to-seed spread
at the 0.20 and 0.30 rows).

The DEC-08 refusal-below-the-bar is **not implemented on either route** for the
`MIN_UNITS_PER_STRATUM` half: the AUROC route renders the u = 2, m = 0 shape (0.715 /
0.620 in the table above) and the proportion route renders a clustered cell of 10 cases at
p = 0.9 (0.672 above), each with its tier annotation and no refusal. That is the open
decision named in the previous paragraph, not an omission of this file.
