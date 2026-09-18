# Lens 1 (fresh attack) - build day 6, lane E, `b93e050` - 2026-09-18

**Verdict: FAIL.** Four blockers. The i.i.d. numbers are right - every statistic re-derived
here from the published formulae without repo code agrees with the engine to 9e-16 on F4
and on 150 random cohorts, and statsmodels `method="newton"` / `Logit` and sklearn agree to
7e-11 / 5.6e-17. What fails is the **clustered route** and three sentences: (B1) under a
declared or detected clustered plan the O:E, intercept-in-the-large and joint-intercept
intervals are the percentile of an *outcome-stratified* case bootstrap, which holds the
event count `O` fixed in every resample, so the rendered interval is 2.2-2.5x too narrow
and covers the truth 61-79 % of the time at a nominal 95 % - below the DEC-08 bar of 0.90
on the ordinary two-rows-per-case design; (B2) any cohort of 1 to 9 analysed rows raises a
numpy `ValueError` from `calibration_block` where the docstring says the empty bin is
`zero_denominator`; (B3) on two-row mixed cases the reference Brier is refused
`boundary_estimate`, the reason decision 11 says it avoids; (B4) the engine string
`ci_not_computed_because`, written into every customer block, asserts "overstates it in
every resample" and 145 of 1000 resamples sit below the point on the first cohort tried.
Eleven of eighteen mutants I planted survive the full suite (409 passed), one of them the
exact mechanism of B1.

Worktrees: `b93e050` (`wt`) and `4eb44f3` (`base`) under
`scratchpad/lens-E6-r1-fresh-attack/`; `PYTHONPATH=<worktree>/src` forced and proved by
`python -c "import proofpack;print(proofpack.__file__)"` printing each worktree's own
`src/proofpack/__init__.py` before any figure below. Both removed at the end. The main
tree was read only and is clean at `b93e050` apart from this note and the regression
lens's. Git Bash only; PowerShell figures are the builder's, not re-measured.

## Blockers

### B1 - the clustered O:E, intercept-in-the-large and joint-intercept intervals cover the truth 61-79 % of the time

`calibration.py:411-414` `_Ctx.resampler` hands `_clustered_cell` (O:E, `:480-498`) and
`_irls_cells` (`:551-566`) the `clustered_by_case` resampler, which draws cases **within
outcome class** (`bootstrap.py:817-841`: pure-positive cases from pure-positive cases,
pure-negative from pure-negative, mixed from mixed). With one row per case, or two rows
per case (every mixed case then carries exactly one event), `O = sum(y)` is the same
integer in every resample. Measured on a 200-row cohort, `ids = arange(200)`, 200 draws:
`distinct O = [91]`; on the same rows as 100 two-row cases: `distinct O = [91]`. The O:E
ratio's sampling variance is `Var(O)/E**2` (the module's own line 29 derivation) and the
calibration intercepts' variance is likewise dominated by `O`; a resampler that freezes
`O` measures only the variability of `E`.

Coverage, my own data-generating process (case effect `N(0, 0.8)`, row noise `N(0, 0.9)`,
calibrated `p`, so the truth is O:E = 1, intercept = 0, slope = 1), 300 replicates each,
`BootstrapPolicy(n_resamples=200)`, the same rows fed to both routes:

| design | quantity | i.i.d. route (analytic) coverage / width | **clustered route coverage / width** |
|---|---|---|---|
| 200 cases x 1 row (declared) | O:E | 0.960 / 0.338 | **0.630 / 0.136** |
| 200 cases x 2 rows (declared) | O:E | 0.967 / 0.239 | **0.670 / 0.109** |
| 60 cases x 3 rows (declared) | O:E | 0.940 / 0.356 | **0.787 / 0.204** |
| 200 x 1 | intercept_large | 0.930 | **0.613** |
| 200 x 2 | intercept_large | 0.953 | **0.673** |
| 60 x 3 | intercept_large | 0.913 | **0.793** |
| 200 x 2 (200 reps) | intercept (joint) | 0.945 | **0.725** |
| 200 x 1 / 200 x 2 / 60 x 3 | slope | 0.950 / 0.953 / 0.960 | 0.947 / 0.940 / 0.907 |

The slope is unaffected (its variance does not ride on the class counts). An
*unstratified* case bootstrap of the O:E written here in twelve lines on the same DGP
gives 0.940 / 0.923 / 0.937 (widths 0.294 / 0.205 / 0.309), so the defect is the
stratification, not the bootstrap. On one 200-row / 100-case cohort at B = 2000 the engine
rendered O:E `(1.091, 1.271)` where the analytic gives `(1.010, 1.367)` and the
unstratified case bootstrap `(1.009, 1.330)`.

DEC-08: "a cell renders with its tier annotation when the engine's own coverage
simulation for that shape is >= 0.90, and is refused with a typed reason below it." No
coverage run exists for these three cells (the note's decision 7 refuses the ECE interval
on exactly that ground and then renders these); the shape a paired-reading customer
brings is the 200 x 2 row. Grade: a wrong number a customer obtains on a real clustered
table, method labelled `cluster_bootstrap_percentile` with the tier annotation and no
flag.

Mutant **M2** below (the clustered O:E statistic uses the full-cohort `O` instead of the
resample's) survives `-m day6` and the full suite: the tests never observe `O` varying
because `clustered_arrays` (`tests/test_calibration.py:389`) builds every case by
`np.repeat`, two identical rows per case, so no test has a mixed case or a case whose
rows differ.

Repro (worktree, PYTHONPATH forced): `python probe/oe_coverage.py` (the script is
reproduced in the appendix; 155 s) - or the one-cohort version:
`python -c "import sys,numpy as np;sys.path.insert(0,'tests');from conftest import make_criteria;from proofpack.io.declare import validate_dict as v;from proofpack.stats.calibration import calibration_block as c;from proofpack.stats.bootstrap import BootstrapPolicy as P;r=np.random.default_rng(5);p=1/(1+np.exp(-(-0.5+r.normal(0,1.5,200))));y=r.uniform(size=200)<p;a=c(p,y,v(make_criteria()),policy=P(n_resamples=2000,seed=1)).block['oe']['number'];b=c(p,y,v(make_criteria(clustering={'unit':'case_id','declared_by':'t'})),cluster_ids=np.repeat(np.arange(100),2),policy=P(n_resamples=2000,seed=1)).block['oe']['number'];print(a['ci_lo'],a['ci_hi'],b['ci_lo'],b['ci_hi'],b['method'])"`
prints `1.0096 1.3674 1.0911 1.2709 cluster_bootstrap_percentile`.

### B2 - `calibration_block` raises for 1 <= N <= 9

`calibration.py:820-822` `mass_edges` takes `.max()` of the last equal-mass bin, which
`numpy.array_split` leaves empty below ten rows; the guard is `if n` only. Measured: N =
1, 2, 3, 5, 9 each raise `ValueError: zero-size array to reduction operation maximum
which has no identity`; N = 0 and N = 10, 11, 25 return a block. Reached through
`calibration_from_table` on a nine-row `make_cohort` table validated by `io.schema`
(no gate refuses it). Line 75: "A bin that receives no rows (``N < 10``) is
``zero_denominator``, never dropped." - false; it is a traceback. The regression lens
found this too; recorded here because I hit it independently before reading its note.

Repro: `python -c "import sys,numpy as np;sys.path.insert(0,'tests');from conftest import make_criteria;from proofpack.io.declare import validate_dict;from proofpack.stats.calibration import calibration_block;p=np.random.default_rng(0).uniform(0.1,0.9,9);calibration_block(p,np.arange(9)%2==0,validate_dict(make_criteria()))"`

### B3 - two-row mixed cases: reference Brier refused as `boundary_estimate`, docstring false

`_prevalence_invariant` (`:589-592`) returns `False` when a `mixed` stratum exists, so
`brier_ref` is bootstrapped; but every two-row mixed case carries exactly one event, the
resampled prevalence never moves, and `bootstrap_percentile` returns `boundary_estimate`.
Measured on 100,000 rows as 50,000 two-row cases (declared): `brier_ref` rendered
`method: none`, `not_estimable_reason: boundary_estimate`, no interval. Lines 87-89
"under a clustered plan whose case sizes differ or whose cases mix outcomes the
prevalence does vary" is false on that input; the note's decision 11 says the
`boundary_estimate` label is the one it avoids. Mutant **M1** (drop the `mixed` half of
`_prevalence_invariant`) survives the full suite. Same finding as the regression lens's
B3, reached from a different input.

Repro: as B1's one-liner but read `['brier_ref']['number']` - prints
`not_estimable_reason == 'boundary_estimate'` on the 100-case x 2-row cohort.

### B4 - an engine string in the output JSON asserts a false statistical fact

`_ECE_CI_WHY` (`:206-210`), serialised as `ece_equal_width_10.ci_not_computed_because`
and `ece_equal_mass_10.ci_not_computed_because` in every present block, and the module
docstring line 100-101: "the percentile bootstrap of a binned absolute deviation
overstates it in every resample". My own outcome-stratified row resampler and my own ECE
(neither from the repo), 1000 draws: `n = 300` point 0.0626, **145 / 1000 resamples
below the point**, bootstrap mean 0.0813; `n = 2000` point 0.0296, **290 / 1000 below**,
mean 0.0341. The upward bias of the *mean* is real; "in every resample" is not. The
decision (no ECE interval, `not_computed_this_run`) is sound; the sentence a regulator
reads beside it is not. Graded a blocker because it leaves the engine as customer-facing
text; sentence violation.

Repro: `python probe/sentences.py` (appendix) - the S2 lines.

## Non-blocking

### N1 - the statsmodels `tol=1e-10` sentence is F4-only (sentence violation)

`fixtures/f4_expected.json` `default_fit_note` and the note's decision 12: "at
`tol=1e-10` (and with method='newton') its SE equals the observed information at the
MLE". Over 150 random cohorts (50 each of n = 30, 200, 2000, my DGP): max |engine SE -
statsmodels IRLS `fit(tol=1e-10)` SE| = **1.03e-5** (slope) / 7.1e-6 (intercept), on an
n = 30 cohort with SE 2.739; on that cohort statsmodels `fit(method="newton", tol=1e-12)`
equals the engine bit for bit (2.7389851771687166) and `Logit(...).fit()` to 2.7e-15, and
my own observed information at statsmodels' own IRLS parameters is 3.9e-11 from the
engine. So the engine is right and the oracle sentence generalises from F4: statsmodels'
IRLS reports the SE from the penultimate weights at *any* deviance tolerance. Estimates,
deviances and Brier over the same 150 cohorts: 7.0e-11 / 4.5e-13 / 5.6e-17.

### N2 - eleven of eighteen planted mutants survive the full suite

Each mutant planted in the worktree, `-m day6` run, then the full suite on survivors,
file restored after each (`git status` clean at the end). The committed sweep: `20
planted, 20 killed, 0 survived; 92 s`. Mine:

| id | mutant | `-m day6` | full suite | equivalent? |
|---|---|---|---|---|
| M1 | `_prevalence_invariant` drops the `mixed` half | 45 passed | 409 passed | no (B3 mechanism) |
| M2 | clustered O:E statistic uses the full-cohort `O` | 45 passed | 409 passed | no (B1 mechanism; differs whenever a resample's `O` varies) |
| M3 | `_decile_curve` passes `plan=None` | 45 passed | 409 passed | no (a bin whose ids do not repeat renders Wilson, route `none`, under a declared plan) |
| M4 | O:E Number `k = int(e)` | killed | - | - |
| M5 | `n_clipped` always 0 | killed | - | - |
| M6 | `_Ctx.tier` drops the few-events rule on i.i.d. rows | 45 passed | 409 passed | no (n >= 30 with < 5 events loses `very_low_precision`) |
| M7 | IPA resample uses the full-cohort Brier | 45 passed | 409 passed | no (i.i.d. IPA collapses to `boundary_estimate`; no test asserts the i.i.d. IPA has an interval) |
| M8 | `IRLS_TOL = 1e-3` | 45 passed | 409 passed | no: F4 moves 1.2e-7 / 4.7e-8 (inside the 1e-6 gate); over 300 random cohorts the worst move is **5.5e-6** |
| M9 | `_clustered_cell` drops the tier flags | 45 passed | 409 passed | no (a clustered cohort under 30 cases loses `very_low_precision` on seven Numbers) |
| M10 | ECE weights equal per bin | killed | - | - |
| M11 | 200/200 counted on cases under clustering | 45 passed | 409 passed | no (the note's open question 1; the code's choice is not pinned) |
| M12 | `oe_log_delta_bounds` ignores `level` | 45 passed | 409 passed | equivalent today (no level but 0.95 is declarable; carried item 17's class) |
| M13 | `flow.n_sites` counts `Unknown/missing` as a site | 45 passed | 409 passed | no |
| M14 | `table1.dev` tabulated over `~mask` | 45 passed | 409 passed | no (differs when excluded non-dev rows exist beside dev rows) |
| M15 | missingness ignores indeterminate `-1` | killed | - | - |
| M16 | `SEPARATION_TOL = 1e-2` | 45 passed | 409 passed | equivalent for correctness (a crossing pair forbids all `|mu - y| < 0.5`; only the iteration at which separation is declared moves) |
| M17 | equal-mass ECE fed the width bins | killed | - | - |
| M18 | curve flag appended to `cell.analytic` instead of `cell.number` | 45 passed | 409 passed | no under clustering (on i.i.d. rows `number` and `analytic` are the same object, so the test cannot tell) |

Record-and-carry, except M2 and M1, which are the observers B1 and B3 need.

### N3 - "no row value, header or id leaves this module" is false (sentence violation)

`descriptive.py:37`. Constructed: `sex` with one row `"PATIENT-NAME-JOSH"`, an extra
attribute column `ethnicity` with one row `"ID-77812"`: `table1.test.sex` keys `['F',
'M', 'PATIENT-NAME-JOSH']`, `table1.test.ethnicity` keys `['A', 'ID-77812']`,
`missingness.columns` keys include `ethnicity`. Attribute level labels are row values and
the column names are headers; both leave, as they do from `stats.subgroups` (day 5) and
must for a Table 1. The sentence should say what is aggregated, not that nothing leaves.

### N4 - the sklearn binning sentence is false on computed floats (sentence violation)

`calibration.py:94-97`: the right-closed rule "reproduces ... `sklearn.calibration.calibration_curve`'s
binning". On F4's decimal literals the two agree (20/20 bin ids). On `0.1 * 3 =
0.30000000000000004`, `0.1 * 6`, `0.1 * 7` sklearn (edges `linspace(0, 1, 11)`, whose
third edge is `0.30000000000000004`) gives bins `[2, 5, 6]` and the engine (edges
`arange(11) / 10`) gives `[3, 6, 7]`. The engine's rule is the better one for a score
parsed from text; the sentence names a function it does not reproduce.

### N5 - the flow table does not reconcile when the table carries `dev` rows

60 rows, 10 `dataset = dev` (one with a missing label), one test row with a missing label:
`flow = {rows_read: 60, excluded_missing_label: 1, excluded_missing_score: 0,
indeterminate: 0, analysed: 49}` - sums to 50; the ten dev rows appear only as
`table1.n_dev` and the dev row's missing label is counted nowhere. D1 section 4.2's flow
keys have no dev entry, so this is a spec gap surfacing, but an R1 flowchart that does
not add up is what a reviewer checks first. One key (`dev_rows`) closes it.

### N6 - `calibration_from_table` raises on a `y_pred`-only table

`score.type: probability` declared, no `score` column (allowed by S01): `ValueError:
calibration needs a score column`. Not reachable today (E7 wires the call); when it is,
this needs to be a typed suppression, not a raise, or a gate.

### N7 - a pre-existing sentence the build made false

`number.py` module docstring: "``flags`` is the one field still appended to in place, by
:meth:`Number.with_precision_flags`". `calibration._decile_curve:688-689` now appends
`curve_flag` in place too (after construction, so past `__post_init__`'s flag check -
harmless today because the flag is in `FLAGS`).

### N8 - small things

- `zero_cell_log_undefined` is named for `O = 0` in the O:E paragraph (`:34-36`) and is
  unreachable from `_oe_cell`: `O = 0` is `single_class` first.
- `ece_equal_mass_10.edges` under ties are bin minima plus the last maximum, not a
  partition: on 95 rows with ten tied values the list is `[0.1, 0.2, 0.3, 0.4, 0.5, 0.5,
  0.6, 0.7, 0.8, 0.9, 0.9]` while bins 6-9 span `(0.5, 0.6)`, `(0.6, 0.7)`, ... The rule
  is stated correctly in `decile_tie_rule`; the `edges` key just is not edges there.
- The clustered `curve_flag` under a case holding 90 % of the rows reports `event_cases:
  13, nonevent_cases: 9` beside `events: 98, nonevents: 102` - correct counts, and the
  rows decide the flag (M11 shows no test pins which).

## Could not break

- **Suite, worktree, PYTHONPATH proved:** `409 passed, 1 skipped, 1 xfailed in 56.31s`;
  `-m day1` `59 passed, 1 skipped`; `day2` `40`; `day3` `29, 1 xfailed`; `day4` `182`;
  `day5` `54`; `day6` `45` - the day-1..5 counts equal the day-5 handoff's. `ruff check`
  `All checks passed!`; `ruff format --check` `61 files already formatted`; `doctor
  --offline` `All essential checks passed.` The day-5 handoff's three named sets: `27
  passed`, `7 passed`, `7 passed`. `git diff 4eb44f3 b93e050 -- bootstrap.py
  subgroups.py cli.py io/` is empty; `MIN_UNITS_PER_STRATUM 2`, `MAX_FROZEN_VARIANCE_SHARE
  0.20`, `LOW/VERY_LOW_PRECISION_UNITS 10/30`, `FEW_EVENTS 5`, `MIN_USABLE_FRACTION 0.90`,
  `DEFAULT_B 2000` unchanged.
- **Re-derivation without repo code** (my own Newton-Raphson on the log-likelihood, two
  parameters and the offset model with slope 1; observed-information Wald SEs; O:E and its
  log-delta bounds; Brier / reference / IPA; ECE under both schemes; stable-rank decile
  bins with `divmod` splitting; hand Wilson per bin). Max |engine - mine|: F4: slope 0,
  intercept 5.6e-17, SEs 0 / 0, intercept_large 0, its SE 1.1e-16, O:E and bounds 0,
  Brier / ref / IPA 0, both ECEs 0, bin means 0, bin Wilson 1.1e-16. 50 cohorts each at
  n = 30 / 200 / 2000: slope <= 4.4e-16, intercept <= 2.2e-16, SEs <= 4.4e-16, Wald bounds
  <= 8.9e-16, intercept_large <= 1.5e-16, O:E, bounds, Brier, ref, IPA, both ECEs and bin
  means exactly 0, bin Wilson <= 2.2e-16; every bin's `n` and `events` equal mine.
- **Oracles** (statsmodels 0.15.0, scikit-learn 1.9.0): 150 cohorts, GLM `fit(tol=1e-10)`
  estimates 7.0e-11 / 4.9e-11, offset intercept 3.4e-13, deviances 4.5e-13, offset SE
  1.1e-7, sklearn Brier 5.6e-17; SEs vs `method="newton"` bit for bit (N1).
- **i.i.d. coverage** on my DGP: O:E 0.940-0.967, intercept_large 0.913-0.953, slope
  0.950-0.960, joint intercept 0.945; Brier 0.940 / 0.907 and IPA 0.937 / 0.930 at n =
  200 / 1000 (B = 200, 300 reps, truths from a 2e6-row draw).
- **Constructions that behaved:** all scores equal (0.5 balanced, 0.3 with 12 events):
  slope and intercept `constant_score`, intercept_large fitted with an interval (0.0 and
  -1.2e-16), Brier / IPA `boundary_estimate` (every stratified resample identical), ECE
  equal-width 0; scores exactly 0 and 1 consistent and contradicted with their labels:
  `n_clipped` 6, finite fits, O:E and Brier on the raw score; `1e-300`, `1 - 1e-16` and
  the denormal `5e-324`: clipped (counts 2, 3), finite, JSON clean; `y == (p > 0.5)` and
  its complement: slope / intercept `complete_separation`, intercept_large fitted, IPA
  0.663 / -1.340 with intervals; a genuine one-crossing near-separation: slope 1.288
  (-0.305, 2.882), 13 iterations; logits at +/-700 and +/-800 into `irls_logistic`:
  `complete_separation`, no overflow; single class both ways: `single_class` on all seven
  with estimates carried where defined (O:E 1.93 / 0.0, Brier, ref 0.0), IPA `None`, ten
  bins still tabulated; N = 0 with and without a declared plan: every cell
  `zero_denominator`, JSON clean; N = 10, 11, 25: bins of 1-3 rows each Wilson with
  `not_evaluable_shown_for_transparency`; NaN, inf, 1.2 and -0.2 in the score: `ValueError
  ... must lie in [0, 1]` (and `gate_h03` / S02 halt them before any table reaches here);
  `logit`, `other`: block `None`, `score_not_probability`; `lower_is_positive`
  probability: `score_not_positive_class_probability`, not transformed; a supplied plan
  contradicting the ids raises; declared clustering without ids raises.
- **Clustered shapes:** one case holding 180 of 200 rows: all seven quantities
  `insufficient_clusters` with `very_low_precision`, the companion
  `clustered_data_analytic_ci_invalid`, every bin `cluster_bootstrap_percentile` with the
  tier and the 200/200 flag; cases all of size 1 (declared): route `declared`, every
  analytic refused, Brier ref `fixed_by_outcome_stratification` (the intervals are B1's);
  the mixed-case census: 17 companions refused, no `wilson` / `log_delta` / `irls_wald` /
  `bootstrap_percentile` method anywhere under a plan.
- **200/200:** 200 / 199, 199 / 200 flagged with the counts; 200 / 200 not.
- **Ties:** 95 rows over nine tied values plus five at 0.5: bins `[10 x 5, 9 x 5]`, every
  bin's rows in stable order, always ten bins, none empty at N >= 10.
- **100,000 rows:** i.i.d. at B = 2000, 2.5 s, slope 1.0029 in 6 iterations; 50,000
  two-row cases at B = 200, 26.2 s (B = 2000 would be about 260 s).
- **Walk of every block above:** every dict with `est`/`method`/`ci_level` re-validates
  through `Number(**d)`, none lacks both an interval and a typed reason, no method outside
  `METHODS`, no `wilson` under a plan, no verdict token (`calibrated`, `miscalibrated`,
  `pass`, `fail`, `verdict`, `met`, `consistent`, `acceptable`, `unbiased`) in any key or
  string of the serialised JSON.
- **Descriptive:** site all missing -> `n_sites 0` and one `Unknown/missing` level at
  1.0; every row's label missing -> `analysed 0`, empty level tables, no division by zero;
  a literal `Unknown/missing` token beside a real blank: counted together (2), as the
  day-5 tables do; `y_pred` `""` counted missing and the indeterminate token not;
  `dataset` `None` counted missing; `calibration_from_table` on a table with dev rows and
  case ids: `n 60`, route `none`; with repeating ids and `clustering.unit: none`: route
  `detected`, `n_cases 40`.

## Could not check

- Coverage of the clustered **decile-bin** intervals against the DEC-08 bar: DEC-18 (a)
  is not built and the note says so; not measured here.
- The R `rms::val.prob` capture (`[pending]`, day 9) and the Debray 2017 attribution
  (`[unverified]` in the diff; not fetched).
- PowerShell 5.1: every figure here is Git Bash from the worktree.
- The scipy-hidden import beyond the suite's own test (`test_calibration_imports_and_runs_with_scipy_hidden`
  passed inside the 409; I did not re-run it by hand).
- Whether the joint-intercept coverage at 60 x 3 and 200 x 1 is also below the bar - only
  200 x 2 was measured (0.725); the mechanism is the same.

## Sentences I refused to write

- "The clustered route is right for the slope" - measured 0.907-0.947 on three shapes,
  stated as those figures only.
- "The i.i.d. numbers are correct" as a class - stated as the deviation figures on F4 and
  150 cohorts above.
- "An unstratified case bootstrap fixes B1" - measured 0.923-0.940 on my DGP at B = 200,
  three shapes; the repair needs its own coverage run against the DEC-08 bar.
- "The tests never exercise mixed cases" - one does (`test_brier_ref_..._varies_when_case_sizes_differ`,
  cases of 1 and 3 identical rows, so still no case whose rows differ); stated as M1 / M2
  surviving.

## Appendix - the probe scripts (scratchpad, not committed)

`probe/rederive.py` (own Newton-Raphson, O:E, Brier, ECE, bins, Wilson; F4 + 150
cohorts), `probe/oracle_sm.py` / `oracle_sm2.py` (statsmodels, sklearn), `probe/attack1.py`
/ `attack2.py` (constructions), `probe/oe_coverage.py` (B1 coverage), `probe/oe_mech.py`
(fixed `O`), `probe/oe_unstrat.py` (unstratified alternative), `probe/int_cov.py` (joint
intercept), `probe/brier_coverage.py`, `probe/attack_desc.py`, `probe/sentences.py`
(S2, S12, S28), `probe/my_mutants.py` (the eighteen mutants), `probe/m8.py`. All under
`scratchpad/lens-E6-r1-fresh-attack/probe/`; the worktrees are removed, the scripts
stay for the repairer.
