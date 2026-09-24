# ProofPack reporting conventions for the T7 methods appendix

These are ProofPack conventions; no regulator specifies them, and none of them is a
guarantee.

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
disjoint - with a Wald interval. The AUROC difference is refused with `boundary_estimate` (estimate carried, no z, no p) when
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
too narrow and only a "very low precision" or no annotation. ProofPack's decision of 15
September 2026 (DEC-18): a design-effect-adjusted Wilson interval for clustered proportions
is a planned engine item, with its own method name and its own coverage run; until it is
in the engine, this table is the statement of what the interval does, every clustered cell
keeps its tier annotation, and `MIN_UNITS_PER_STRATUM` stays at 2.

The AUROC frozen-share half: every shape the constant renders measured at or above the
bar in the recorded run; the first shape it refuses did in the recorded run and in six of
eight cells over four runs (see the constants paragraph above for the seed-to-seed spread
at the 0.20 and 0.30 rows).

The DEC-08 refusal-below-the-bar is **not implemented on either route** for the
`MIN_UNITS_PER_STRATUM` half: the AUROC route renders the u = 2, m = 0 shape (0.715 /
0.620 in the table above) and the proportion route renders a clustered cell of 10 cases at
p = 0.9 (0.672 above), each with its tier annotation and no refusal. That is the DEC-18
position stated two paragraphs above.

## Calibration (build day 6, `stats.calibration`)

Each convention below is stated in full in the module docstring of `stats.calibration`,
with the test that feeds the input named; this section is the T7 summary of the same
rules.

**Scope.** The block is computed only for a score declared `probability` with
`higher_is_positive`. A `logit` or `other` score gives a `None` block with the typed
reason `score_not_probability`; a `lower_is_positive` probability is refused with
`score_not_positive_class_probability` and never transformed to `1 - p`.

**O:E ratio.** `O = sum(y)` over `E = sum(p)`; interval on the log scale by the delta
method, `ln(O/E) +/- z * sqrt((1 - O/N) / O)`, exponentiated (`log_delta`). `E = 0` is
`zero_denominator`; `O = 0` and `O = N` are `single_class` before any interval is formed.

**Calibration-in-the-large, slope and intercept.** The intercept of
`logit P(y=1) = a + logit(p)` with the slope fixed at 1 (an offset model), and `a`, `b` of
`logit P(y=1) = a + b * logit(p)`, each by the module's own Newton-Raphson / IRLS in numpy
with Wald intervals from the observed information at convergence (`irls_wald`). Oracle:
`statsmodels GLM(Binomial)` with and without an offset on fixture F4
(`fixtures/f4_calibration.csv`, `f4_expected.json`), estimates and standard errors to 1e-6.

**Typed IRLS outcomes.** `complete_separation` when every fitted probability is within
1e-8 of its label; `irls_not_converged` on any of four exits (the budget of 100 iterations
spent; the 30 step-halvings of one Newton step all raise the deviance, at which point
`detail.iterations` is that step's index - 1 on 50 rows all at `p = 1.0` with 12 events;
a singular information matrix; a non-finite parameter or standard error);
`constant_score` when `logit(p)` takes one value; `single_class` when the labels do.
`test_separation_and_non_convergence_are_typed_reasons_never_inf_nan_or_a_traceback` and
`test_irls_not_converged_at_iteration_one_names_the_step_halving_exit_not_the_budget`
feed the separated, one-crossing and all-1.0 inputs and serialise each block without NaN.

**Scores at exactly 0 or 1** are clipped to `[1e-12, 1 - 1e-12]` for the two logit-scale
models only; `n_clipped` is carried in the block and `scores_clipped_for_logit` rides on
the three IRLS Numbers. The O:E, Brier, ECE and decile curve use the raw score.

**Decile curve.** Ten equal-mass bins by score rank, ties by stable sort order
(`numpy.argsort(kind="stable")`, then `numpy.array_split`, so the first `N mod 10` bins
hold one extra row); each bin's observed rate goes through `proportion_ci` (DEC-10) -
Wilson on independent rows, the cluster bootstrap with Wilson refused under a clustered
plan - and a bin that receives no rows is `zero_denominator`, never dropped. Under ties
the `ece_equal_mass_10.edges` array is the minima of the bins plus the last bin's maximum,
not a partition (`decile_tie_rule` states the scheme).

**Brier, reference Brier, IPA.** The Brier score is `mean((p - y)**2)` with a percentile
bootstrap through the same resampler as `stats.subgroups._brier_cell` (rows within outcome
class; cases within outcome class under a clustered plan), so the overall Brier equals the
subgroup module's value on the whole cohort bit for bit. The reference Brier is
`pi (1 - pi)` at the observed prevalence and `IPA = 1 - Brier / Brier_ref`. When
`_prevalence_invariant` returns `True` - within every stratum of the resampler,
`R * pos_u - P * rows_u` takes one value over the units (`P`, `R` the cohort's positive
and total row counts) - the reference Brier carries the typed reason
`fixed_by_outcome_stratification` instead of the `boundary_estimate` a zero-width draw
would produce; otherwise it is bootstrapped. On the eleven case shapes
`test_the_prevalence_rule_agrees_with_the_resamplers_own_draws_on_eleven_shapes` feeds,
the function returns `True` on exactly the shapes whose 500 draws of the module's own
resampler give one prevalence.

**ECE** under two stated schemes - ten right-closed equal-width bins on `arange(11) / 10`
(the first bin closed at 0; the rule that reproduces R2's F4 figures 0.1255 at five bins
and 0.1955 at ten) and the ten equal-mass bins - each labelled `supplementary`, and **no
interval for either**: `not_computed_this_run` with the reason string beside it (no
coverage run of a bootstrap interval for a binned absolute deviation has been made
against the DEC-08 bar of 0.90).

**The 200/200 annotation** (after Van Calster 2019): fewer than 200 events **or** fewer
than 200 non-events in the analysed rows puts `below_200_events_or_nonevents` on every
decile bin's rendered Number and the counts in `curve_flag`; strict on both sides (199 is
flagged, 200 is not); an annotation, never a suppression (DEC-08) - the O:E, slope,
intercept and every bin stay reported. On i.i.d. rows the flag rides on the rendered
Number only; the Wilson companion under `analytic` does not carry it (recorded from repair
round 1, lens 2 RG-N2 of 2026-09-18).

**Under a clustered plan** (declared or detected) every analytic interval - the log-delta
O:E, the three Wald intervals, Wilson per bin - is refused with
`clustered_data_analytic_ci_invalid` on the companion Number (DEC-09) and a cluster
bootstrap takes its place: cases in a **single stratum** (`clustered_flat`) for the O:E
and the three IRLS quantities, cases **within outcome class** (`clustered_by_case`) for
the Brier cells. A drawn case set with one outcome class, or a resample on which the
IRLS does not converge, is `nan` to the resampler and counted against the 90 % usable
floor (`degenerate_resamples`). Before any draw the day-4 class-units rule over the
cases within outcome class is applied and refuses the four single-stratum quantities as
`insufficient_clusters`; both resamplers' quantities are carried under
`bootstrap.resampling` (the guard's under `class_units_guard`). Every quantity is
serialised in the day-4 cell shape `{number, analytic, analytic_status,
clustering_route, bootstrap[, detail]}`.

### Which annotations each calibration cell carries (R2 section 3.3)

Measured on 60 one-row cases with 3 events (`p = 0.08` on every row, B = 200, seed 5),
i.i.d. and under a declared plan; lens 2 of 2026-09-18, FA-N3 / FA-N7:

| cell | i.i.d. rows | clustered plan |
|---|---|---|
| O:E, intercept-in-the-large, slope, intercept | `precision_flags(n, events)`: the units tiers **and** the few-events tier (`very_low_precision` below 5 events) - measured `['very_low_precision']` | `precision_flags(n_cases)`: the units tiers only, no few-events tier - measured `['log_delta_refused_clustered']` |
| Brier, reference Brier, IPA | `precision_flags(n_units)`: units tiers only, no few-events tier - measured `[]` | the same - measured `[]` |
| each decile bin | `proportion_ci`'s own annotations (units tiers, few events, `imprecise`) | the same, on the bin's cases - bin 1 measured `['wilson_refused_clustered', 'not_evaluable_shown_for_transparency', 'imprecise', ...]` |

So on those rows the O:E says `very_low_precision` and the Brier beside it carries no
tier. The Brier's choice is day 5's (`_brier_cell` uses `precision_flags(n_cases)` with no
events) and the cross-check test forces the calibration Brier to match it; the clustered
O:E and fits inherit `_Ctx.tier`'s `events=None` under a plan. ProofPack's decision
DEC-35 keeps this as measured: the few-events tier rides on the O:E and the three fits on
i.i.d. rows only, and is not extended to the Brier, reference Brier, IPA or the clustered
cells.

`imprecise` means "the interval's half-width exceeds 0.10" (R2 section 3.3, written for a
proportion). `Number.with_precision_flags` applies that arithmetic to whatever interval
the Number carries, so it rides on the Brier (range `[0, 1]`) and on the IPA (range
`(-inf, 1]`) as well as on proportions: on F4 (B = 200, seed 20240101) the IPA renders 0.3385
(-0.0290, 0.6148) with `['very_low_precision', 'imprecise']`. On the IPA the flag states the half-width on the
IPA's own scale and nothing about a proportion.

### Clustered calibration intervals: coverage (DEC-08, DEC-18 (c); repair round 1 of build day 6)

`scripts/coverage_calibration.py` v1, R = 300 cohorts per shape, B = 200, nominal 0.95,
bar 0.90; Monte-Carlo standard error about 0.017 per cell. Process (the lens-1 DGP of
2026-09-18, reproduced in the script): `n_cases` cases of `rows_per_case` rows, true
logit `-0.5 + b_case + e_row` with `b_case ~ N(0, 0.8)` shared by a case's rows and
`e_row ~ N(0, 0.9)`; the score is the true probability and `y ~ Bernoulli(p)`, so the
truths are O:E = 1, intercept-in-the-large 0, slope 1, joint intercept 0. Re-run with
`python scripts/coverage_calibration.py --full` (151 s measured on 18 September 2026) or
`--full --seed 7`. The clustered route is the single-stratum case bootstrap above; the
i.i.d. column is the analytic interval on the same cohorts.

| quantity | shape | i.i.d. analytic, seed 2026 | clustered, seed 2026 | clustered, seed 7 |
|---|---|---|---|---|
| O:E | 200 x 1 / 200 x 2 / 60 x 3 | 0.960 / 0.967 / 0.940 | 0.920 / 0.943 / 0.903 | 0.937 / 0.960 / 0.937 |
| intercept-in-the-large | 200 x 1 / 200 x 2 / 60 x 3 | 0.930 / 0.953 / 0.913 | 0.920 / 0.943 / **0.897** | 0.927 / 0.957 / 0.930 |
| slope | 200 x 1 / 200 x 2 / 60 x 3 | 0.950 / 0.953 / 0.960 | 0.940 / 0.943 / 0.933 | 0.937 / 0.940 / 0.920 |
| joint intercept | 200 x 1 / 200 x 2 / 60 x 3 | 0.927 / 0.943 / 0.923 | 0.903 / 0.927 / 0.917 | 0.923 / 0.953 / 0.940 |

Before the round-1 repair (build day 6 drew these cases within outcome class) the same
process measured the O:E at 0.630 / 0.670 / 0.787 and the intercept-in-the-large at
0.613 / 0.673 / 0.793 on the three shapes (lens 1 of 2026-09-18, FA-B1).

**What the table says.** Twenty-three of the twenty-four clustered cells are at or above
0.90 and one - the intercept-in-the-large on 60 cases x 3 rows at seed 2026 - reads
0.897, under the bar by less than one Monte-Carlo standard error (0.930 at seed 7; the
analytic interval on the same cohorts 0.913). That cell is rendered with its tier
annotation, and no case-count floor is added to the calibration route (ProofPack's
decision DEC-34, under DEC-18 (c)). These are
measurements on this process at these three shapes and two seeds, not a guarantee.

**What the table does not measure.** In this process the case effect `b_case` is inside
the score, so given the scores the rows are independent Bernoulli draws and the i.i.d.
analytic interval is valid on them (its column reads 0.913-0.967): the table measures the
single-stratum case bootstrap's behaviour with 60-200 cases, not its handling of
within-case correlation the score does not carry. Lens 2 of 2026-09-18 measured a second
process (true logit `-0.5 + b_case + e_row` with `b_case ~ N(0, 2.0)`, the score
`expit(-0.5 + e_row)` carrying no case effect; R = 200, B = 200, seed 777, Monte-Carlo
standard error about 0.02) on 30 x 10 and 50 x 8 cases: the i.i.d. analytic interval
covered the O:E in 0.655 / 0.740 and the intercept-in-the-large in 0.645 / 0.710 of
replicates, the clustered route 0.970 / 0.930 and 0.955 / 0.935 (its note, "could not
break"). Those are the lens's figures from its own script, not re-run here; a second DGP
in the committed script is a carried item. Not measured by anyone: the clustered
decile-bin intervals (DEC-18 (a)) and the Brier, reference Brier and IPA under a
clustered plan.
