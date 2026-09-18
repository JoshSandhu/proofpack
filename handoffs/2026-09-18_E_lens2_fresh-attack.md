# Lens 2 (fresh attack, DEC-12(i)) - build day 6 repair round 1, lane E, `a5a5ed8` - 2026-09-18

**Verdict: PASS. No blockers.** Every number I could re-derive without repo code agrees
with the engine: the i.i.d. statistics to 4.4e-16 on F4 and 150 random cohorts, the
clustered O:E, slope and every decile bin bit for bit against my own case bootstrap from
each cell's generator, the i.i.d. Brier and IPA bit for bit against my own
outcome-stratified row bootstrap; statsmodels `method="newton"`, `Logit` and sklearn agree
to 4.4e-16. The seven lens-1 blockers are closed and each stays closed under the
constructions I added; the recorded seed-2026 coverage table reproduces in all 24 cells;
on a process the repairer did not use - a case effect the score does *not* carry, 30
cases x 10 rows - the repaired clustered route covers the truth 0.949-0.970 where the
i.i.d. analytic covers 0.645-0.715, which is the property a cluster bootstrap exists for.
What I found is six non-blocking items, three of them shipped sentences a constructed
input falsifies (N1, N2, N6), and nine of my ten planted mutants surviving the full
suite with a demonstrated behaviour change each (N5).

Worktrees: `a5a5ed8` and `b93e050` under `scratchpad/lens-E6-r2-fresh-attack/`,
`PYTHONPATH=<worktree>/src` forced and proved by `python -c "import proofpack;
print(proofpack.__file__)"` printing each worktree's own `src/proofpack/__init__.py`
before every figure below (the prior lenses' `lens-a-p1-r2` and `lens-S6-r1` worktrees
were left alone). Both of mine removed at the end. The main tree was read only; it is
clean at `a5a5ed8` apart from this note. Git Bash throughout.

## Blockers

None.

## Non-blocking

### N1 - `_prevalence_invariant`'s "exactly when" is an "if", not an "iff" (sentence violation)

`calibration.py` module docstring: "The resampled prevalence is the same in every draw
**exactly when**, within every stratum of the resampler, every unit carries the same
number of positive rows and the same number of negative rows"; `_prevalence_invariant`'s
docstring: "Whether every resample keeps the prevalence"; the repair note's FA-B3 row:
"invariant exactly when every stratum's units carry identical (positive, negative) row
counts". The "if" direction holds. The "only if" does not: mixed cases whose class counts
are *proportional* hold the prevalence fixed while the rule reads them as varying.
Constructed and run (declared plan, B = 200, seed 3; my own 500 draws of the module's
`clustered_by_case` resampler counted the distinct prevalences):

| input | `_prevalence_invariant` | distinct prevalences in 500 draws | `brier_ref` rendered |
|---|---|---|---|
| 30 mixed cases (1 event, 1 non-event) + 30 mixed cases (2, 2) | False | **1** | `method: none`, `boundary_estimate`, no CI |
| 10 pure-positive + 10 pure-negative one-row cases + 20 mixed (1, 1) + 20 mixed (2, 2) | False | **1** | `boundary_estimate` |
| 30 mixed (1, 2) + 30 mixed (2, 4) | False | **1** | `boundary_estimate` |
| control: 10 pure-positive + 12 pure-negative + the same mixed cases | False | 16 | `cluster_bootstrap_percentile` (0.24994, 0.24996) |

So on those inputs the reference Brier carries `boundary_estimate` - the label the note's
FA-B3 row says the rule avoids - with the right estimate and a valid enum reason, and the
IPA keeps its interval. Not a blocker under the grading rule (no wrong number, no
missing reason, no suppression); a sentence the code does not honour, on a shape a
multi-lesion dataset can produce. The exact rule is "the drawn class totals are fixed"
(the current test) **or** "every stratum's units share one (positive : negative) ratio and
the pure strata balance" - or say "when" and drop "exactly".

Repro (worktree, PYTHONPATH forced): `python probe/attack_prev.py` (appendix).

### N2 - `irls_not_converged` is emitted at `iterations: 1` where the docstring says the iteration budget ran out (sentence violation)

Module docstring, "IRLS rules": "``irls_not_converged`` when the iteration budget runs
out". `irls_logistic` also returns it when the 30 step-halvings of one Newton step all
raise the deviance (`MAX_STEP_HALVINGS`, whose own comment says so). Constructed: 50 rows
all at `p = 1.0` with 12 events (every score clipped to `1 - 1e-12`) - `intercept_large`
is `irls_not_converged` with `detail.iterations: 1`, a budget of 100 untouched; a reader
of the detail block sees a budget of 100 exhausted at iteration 1. On that cohort the
offset MLE exists (my bisection of the score equation: a = -28.783723, statsmodels
`method="newton"` -28.7837227, SE 0.331) and the engine refuses it. Same outcome on the
mixed vector `[0, 1, 0, 1, 1e-300, 1 - 1e-16, 5e-324, 0.5, 0.4, 0.6] x 5` (24 iterations,
MLE a = 13.6987 by bisection, statsmodels returns nan) and on scores at `expit(+/-700)`.
Every one of those is a typed reason, never a number, never inf; the value -28.78 is an
artefact of the 1e-12 clip anyway, so refusing is defensible. A realistic mix - a
calibrated score rounded to 0.00 / 1.00 on 5 %, 20 %, 50 %, 80 % of rows - converges in
2-3 iterations and matches statsmodels to 4e-16. The sentence should name both exits.

Repro: `python probe/irls_dbg.py`.

### N3 - the few-events tier is applied to the O:E and the fits on i.i.d. rows and to nothing under a clustered plan

`_Ctx.tier` passes `events=None` when clustered, and `_brier_cells` uses
`precision_flags(resampler.n_units)` on both routes. Constructed: 60 one-row cases, 3
events. i.i.d.: O:E flags `['very_low_precision']`; the same rows under a declared plan:
`['log_delta_refused_clustered']` and nothing else; Brier and IPA carry no tier on either
route, and the decile bins carry `not_evaluable_shown_for_transparency` (their own n).
Within one block the O:E says "very low precision" and the Brier beside it does not, on
the same 60 rows. Day 5's `proportion_ci` and `_brier_cell` made the same choice
(`precision_flags(n_cases)` with no events), and the cross-check test forces the Brier to
match it, so this is inherited, not introduced. DEC-08 is annotate-never-omit; a missing
annotation is not a suppression. Record for T7: state which cells carry the events rule.
My mutant `L2_tier_reads_events_under_clustering` (below) is the observer that does not
exist.

### N4 - a blank `case_id` in one row is a `TypeError` traceback in three entry points, pre-existing, not gated at ingest

`make_cohort(30, with_case_id=True)` with `case_id[0]` set to `""`, `None` or `"NA"`:
`schema.validate` keeps the row with `case_id[0] = None` (object column), `gates.ingest`
passes it (exit 2, W10 only), and then `flow_block`, `calibration_from_table` **and**
day 5's `subgroup_analysis` each raise `TypeError: '<' not supported between instances
of 'str' and 'NoneType'` from `numpy.unique` (`_arraysetops_impl.py:385`), with
`clustering.unit` `case_id` or `none`. Same for mixed int / str ids passed directly.
Not reachable today: `cmd_run` stops at ingest ("statistics and templates land on later
build days"), and a CSV case column is all strings, so only the blank matters. E7 wires
the statistics into `cmd_run`; a blank case id needs an S-code halt or a typed treatment
there. Not damage this build introduced (the day-5 path raises identically).

Repro: `python probe/caseid.py`; `python probe/caseid3.py`.

### N5 - nine of ten planted mutants survive the full suite

Each planted in a copy through `scripts/mutation_sweep.py`'s own `make_copy` / `plant`
/ `restore` (`assert_imports_from_copy` passed), `-m day6` run, then the full suite with
`tests/test_invariants.py::test_ci_runs_every_declared_day_marker_without_a_hardcoded_list`
deselected (it reads `.github/`, which the copy does not carry, and fails in every copy
unmutated - an artefact of the copy, not of any mutant; the sweep's `-m day6` never
selects it). Then each survivor was run on a constructed input beside the unmutated copy
to show the behaviour it changes:

| id | mutant | day6 | full | differs on |
|---|---|---|---|---|
| L2-1 | `_prevalence_invariant` reads the positive counts only | survives | survives | mixed (1, 1) x 30 beside mixed (1, 2) x 30: `brier_ref` `fixed_by_outcome_stratification` instead of `cluster_bootstrap_percentile` |
| L2-2 | `_decile_curve` passes `ctx.ids[: rows.shape[0]]` (a prefix of the case column, same length) instead of `ctx.ids[rows]` | survives | survives | 200 two-row cases with rows that differ in score: bin 3's interval (0.0976, 0.3590) over 38 cases becomes (0.1, 0.35) over 20 - **a wrong interval on every bin under any real clustered table**. Unobserved because `clustered_arrays` builds every case by `np.repeat`, so a case's two identical rows are always adjacent in the same bin and the prefix grouping coincides with the true one |
| L2-3 | `_brier_cells` tier from rows, not cases | **killed** | - | `test_one_case_holding_180_of_200_rows...` |
| L2-4 | the DEC-09 companion on the O:E / fits carries `est=None` | survives | survives | `oe.analytic.est` 0.625 -> null |
| L2-5 | a refused clustered draw reports `analytic_status: refused_clustered` instead of `unavailable` | survives | survives | 40 one-row cases, 2 events: O:E `degenerate_resamples` with status `refused_clustered` |
| L2-6 | `scores_clipped_for_logit` dropped from the IRLS Numbers under a clustered plan | survives | survives | 100 two-row cases, 20 rows at 0.0 / 1.0: slope flags lose the clip flag |
| L2-7 | `flow.n_sites` counts `Unknown/missing` (lens 1 M13) | survives | survives | one blank site: `n_sites` 3 -> 4 |
| L2-8 | `calibration_from_table` passes `table.case_id` unsliced by the mask | survives | survives | 40 rows, one missing label, case column: `ValueError: cluster_ids must align row-for-row` instead of a block of 39 |
| L2-9 | `curve_flag.event_cases` counted over the non-event rows | survives | survives | 60 events / 140 non-events: `event_cases` 52 -> 92 |
| L2-10 | `_Ctx.tier` applies the few-events rule under clustering | survives | survives | N3's input: the clustered O:E gains `very_low_precision` |

L2-2 is the one that matters: the shipped code is right (my own case bootstrap of all
ten bins on that cohort, grouping each bin's rows by `ids[rows]` in first-appearance
order and drawing from the cell's generator, reproduces every rendered bound to 1.1e-16),
but no test can tell. The observer is one clustered cohort whose cases' rows differ in
score, with one bin's bounds recomputed. Record-and-carry, all nine; none reopens a
wrong number in the code as committed. The committed sweep: `30 planted, 30 killed, 0
survived; 137 s`, from the worktree.

### N6 - one phrase in the sentences test never matched the b93e050 text (sentence violation)

`test_the_sentences_the_day6_lenses_falsified_are_gone_from_the_shipped_text`: "each
phrase below was asserted in shipped text at b93e050". The FA-B3 entry `"whose cases mix
outcomes the prevalence does vary"` is line-wrapped at b93e050 (`... or whose\ncases mix
outcomes ...`, `calibration.py:87-88`), so `phrase not in text` was already true there:
that assertion observes nothing. The test fails at b93e050 through the other seven
phrases (verified: `16 failed, 45 passed` with the three a5a5ed8 test files copied into
the b93e050 worktree, the note's figure to the digit, this test among them), so the
finding is one vacuous line, not a missing regression. Match on `"mix outcomes the
prevalence does vary"` or collapse whitespace first.

### N7 - small things

- The `imprecise` flag (R2 section 3.3: Wilson half-width > 0.10, a proportion tier)
  rides on the IPA - a quantity on (-inf, 1] - and on the Brier, through
  `_number_from_draw(...).with_precision_flags()`: F4's IPA (-0.029, 0.615) carries it;
  so does every IPA in my constructions with a half-width over 0.10. Day 5's
  `_brier_cell` does the same on the Brier; the IPA is new. An annotation, not a
  verdict; T7 should say what "imprecise" means off the proportion scale, or the IPA
  should not carry it.
- The committed coverage process (`scripts/coverage_calibration.py`, the lens-1 DGP)
  puts the case effect *inside* the score, so given the scores the rows are independent
  Bernoulli draws and the i.i.d. analytic interval is valid on it (its own i.i.d. column
  reads 0.913-0.967). The table therefore measures the single-stratum bootstrap's
  small-sample behaviour, not its handling of within-case correlation. The script says
  what it does and claims nothing more; the process that exercises the route is the one
  below ("could not break"), and it belongs in the script as a second DGP.
- Under quasi-complete separation (four rows at logit 0 with both labels, the rest
  separated) the joint fit runs the full 100 iterations to `irls_not_converged` (finite
  deviance, no inf); the MLE does not exist there, and the module docstring names only
  `complete_separation` for that. Typed either way.
- `ece_equal_mass_10.edges` under ties is still bin minima plus the last maximum (lens 1
  N8, carried): 95 rows over nine tied values give `[0.1, ..., 0.5, 0.5, 0.6, ..., 0.9,
  0.9]`; 100 identical scores give eleven `0.5`s and an equal-mass ECE of 0.08 beside an
  equal-width ECE of 0 (the ten bins split identical scores by row order; the scheme is
  stated).
- The repair note's "a5a5ed8 ... `64 files already formatted`" and every count in its
  "Re-run these" table reproduce from the worktree (below).

## Could not break

- **Suite, worktree, PYTHONPATH proved:** `425 passed, 1 skipped, 1 xfailed in 56.89s`;
  `-m day1` `59 passed, 1 skipped, 367 deselected`; `day2` `40 passed`; `day3` `29 passed,
  1 xfailed`; `day4` `182 passed`; `day5` `54 passed`; `day6` `61 passed, 366 deselected`
  - the day-1..5 counts equal the day-5 handoff's and the repair note's. `ruff check`
  `All checks passed!`; `ruff format --check` `64 files already formatted`; `doctor
  --offline` `All essential checks passed.` The day-5 handoff's three named sets: `27
  passed, 155 deselected`, `7 passed, 47 deselected`, `7 passed, 47 deselected`.
  `git diff 4eb44f3 a5a5ed8 -- bootstrap.py subgroups.py cli.py io/ test_bootstrap.py
  test_subgroups.py test_discrimination.py test_proportions.py test_number.py` is empty;
  `MIN_UNITS_PER_STRATUM 2`, `MAX_FROZEN_VARIANCE_SHARE 0.2`, `LOW/VERY_LOW 10/30`,
  `FEW_EVENTS 5`, `MIN_USABLE_FRACTION 0.9`, `DEFAULT_B 2000`, `DEFAULT_SEED 20240101`,
  `CURVE_MIN_EVENTS 200`, `CLIP_EPS 1e-12`, `IRLS_TOL 1e-10`, `IRLS_MAX_ITER 100`,
  `SEPARATION_TOL 1e-8`, `MAX_STEP_HALVINGS 30`, `N_BINS 10`. `git diff --name-status
  b93e050 a5a5ed8 -- tests/`: three `M`, no `D`; no `skip` / `xfail` / `.only` added, no
  `pytest.mark` removed. Every touched file is `i/lf w/lf` in the main tree, as the note
  says.
- **Re-derivation without repo code** (my own Newton-Raphson on the log-likelihood with
  step-halving, two parameters and the offset model; observed-information Wald SEs; O:E
  and log-delta bounds; Brier / reference / IPA; both ECEs; stable-sort deciles with
  `divmod` splitting; hand Wilson per bin). Max |engine - mine| on F4: every quantity 0,
  bin Wilson 1.1e-16. 50 cohorts each at n = 30 / 200 / 2000 (my DGP, seed 2026):
  slope <= 4.4e-16, intercept <= 2.2e-16, SEs <= 1.1e-16, Wald bounds <= 2.2e-16,
  intercept-in-the-large <= 2.2e-16, O:E, its bounds, Brier, ref, IPA, both ECEs and
  every bin mean exactly 0, bin Wilson <= 2.2e-16; every bin's `n` and `events` equal
  mine. `probe/rederive.py`.
- **Oracles** (statsmodels, sklearn; 150 cohorts, seed 99): GLM `method="newton",
  tol=1e-12` offset intercept 1.7e-16, its SE 5.6e-17, joint intercept / slope 4.4e-16,
  SEs 2.2e-16 / 3.3e-16, deviances 4.6e-13; `Logit` slope 4.4e-16, SE 3.3e-16; sklearn
  Brier 5.6e-17. `probe/oracle.py`. The fixture's new notes reproduce: offset default
  and `tol=1e-10` both 4 iterations, SEs 0.0 apart, engine 2.19e-9 from them; joint 5 /
  6 iterations, 9.13e-6 / 1.99e-5 apart, engine 7 iterations, 3.30e-10 / 7.21e-10 from
  the tight fit and 1.1e-16 from `newton`. `probe/f4_notes.py`.
- **Lens-1 blockers, re-attacked.** FA-B1: the clustered O:E and slope on 80 cases of
  1-5 rows with the rows *shuffled* (cases not contiguous): my own single-stratum case
  bootstrap from the cell keys reproduces the O:E bounds to 1.1e-16 and the slope bounds
  (statsmodels refits) to 2.7e-13, 150 of 150 usable both. FA-B2: N = 1, 2, 5, 9 with and
  without a declared plan return a block (the suite's test; my N = 5 declared two-row
  cases: every quantity `insufficient_clusters`, bins 6-10 `zero_denominator`, schema
  valid). FA-B3: two-row mixed cases are `fixed_by_outcome_stratification` (100,000
  rows as 50,000 two-row cases: `fixed_by_outcome_stratification`, 29.8 s at B = 200).
  FA-B4: no "every resample" / "overstates" in `ci_not_computed_because`; "no coverage
  run" and "0.90" present. RG-N1: item 17b's two `subgroups.py` sites are in the
  committed sweep and die there.
- **Coverage, the repairer's process:** `scripts/coverage_calibration.py --full` from
  the worktree reproduces the recorded seed-2026 table in all 24 cells (O:E 0.920 /
  0.943 / 0.903; intercept-in-the-large 0.920 / 0.943 / 0.897; slope 0.940 / 0.943 /
  0.933; joint intercept 0.903 / 0.927 / 0.917; i.i.d. column 0.913-0.967), `elapsed
  154 s`.
- **Coverage, a process with within-case correlation the score does not carry** (true
  logit `-0.5 + b_case + e_row`, `b_case ~ N(0, 2.0)`, `e_row ~ N(0, 0.7)`, score
  `expit(-0.5 + e_row)`; truths from a 2e6-row draw: O:E 1.0958, intercept-in-the-large
  0.1712, slope 0.616, intercept -0.0009; R = 200, B = 200, seed 777, MC SE 0.02):

  | shape | quantity | i.i.d. analytic | clustered (repaired) | refused |
  |---|---|---|---|---|
  | 30 x 10 | O:E | 0.655 (w 0.287) | **0.970** (w 0.568) | 2 `insufficient_clusters` |
  | 30 x 10 | intercept-in-the-large | 0.645 | **0.955** | 2 |
  | 30 x 10 | slope | 0.965 | 0.914 | 2 |
  | 30 x 10 | joint intercept | 0.715 | **0.949** | 2 |
  | 50 x 8 | O:E | 0.740 | **0.930** | 0 |
  | 50 x 8 | intercept-in-the-large | 0.710 | **0.935** | 0 |
  | 50 x 8 | slope | 0.950 | 0.950 | 0 |
  | 50 x 8 | joint intercept | 0.755 | **0.945** | 0 |

  With a milder case effect (`N(0, 1.0)`, 100 x 2, 60 x 3, 100 cases of 1-5 rows) both
  routes cover 0.905-0.960. My own DGP with the case effect inside the score (100 cases
  of 1-5 rows; 150 x 2 with `N(0, 2.0)`; 60 geometric cases): clustered route
  0.900-0.925 on every cell, none below the bar. `probe/cov_resid_harsh.py`,
  `probe/cov_resid.py`, `probe/cov_clustered.py`.
- **Constructions that behaved** (`probe/attack1.py`, `attack2.py`): all scores 0.5 /
  0.3 / 1.0 / 0.0 (typed on every cell, JSON clean); the boundary vector with 0, 1,
  1e-300, 1 - 1e-16 and 5e-324 (`n_clipped` 35, bin 1 `score_min` 0.0); `y == (p >
  0.5)` and its complement (`complete_separation` on slope and intercept, O:E and
  intercept-in-the-large with intervals, IPA 0.650 / -1.294); single class both ways,
  i.i.d. and declared (`single_class` on all seven, IPA `None`, Brier ref 0.0); n = 5,
  10, 25 i.i.d. and as two-row declared cases (n = 5 declared: `insufficient_clusters`
  everywhere; n = 10 declared: the joint intercept `degenerate_resamples`, the rest
  rendered); NaN, inf, 1.2, -0.2 into `calibration_block`: `ValueError ... must lie in
  [0, 1]`, and through `gates.ingest` NaN is excluded by the mask (29 of 30 included)
  while inf / -inf / 1e400 halt S02 and 1.2 / -0.2 halt H03, so calibration never sees
  them; `logit` / `other` / `lower_is_positive` refused with their reasons and a `None`
  block; one case holding 180 / 100 / 40 of 200 rows: all `insufficient_clusters`
  (`class_units_guard` deficient) while 200 one-row declared cases render; ties: 95
  rows over nine tied values `[10 x 5, 9 x 5]`, always ten bins; 200 / 199, 199 / 200
  flagged with the counts, 200 / 200 not; one crossing pair: slope 44.49 (-129, 218) in
  18 iterations, finite; 100,000 i.i.d. rows at B = 2000 in 1.6 s; a level of 0.90 is
  carried on every Number, ECE included, and its O:E / slope / Brier intervals sit inside
  the 0.95 ones. Schema (`calibrationBlock`): the all-1.0, all-events, N = 0 (both
  routes), 180-of-200, n = 5 declared and quasi-separated blocks validate with no errors.
- **Walk of every block above and an assembled document with dev rows, a missing label
  and a blank site** (the repo's `walk_keys_and_strings` and `VERDICT_WORDS`): every
  dict with `est` / `method` / `ci_level` re-validates through `Number(**d)`, none lacks
  both an interval and a typed reason, no method outside `METHODS`, no interval under
  `method: none`, no flag outside `FLAGS`, no verdict token in any key or string, no
  `wilson` / `log_delta` / `irls_wald` / `bootstrap_percentile` under a plan.
- **scipy hidden** (`sys.modules['scipy'] = None`, statsmodels and sklearn likewise):
  `proofpack`, `proofpack.stats`, `calibration`, `descriptive` import and a block builds.
- **Descriptive** (`probe/attack_desc.py`): blank / `None` / `NA` sites count as one
  `Unknown/missing` level and `n_sites` 3; all sites missing -> `n_sites 0`; age `None`
  / `NA` / -5 / 150 -> two missing, `Unknown/missing` band present, shares sum to 1;
  every label missing -> `analysed 0`, empty level tables; `"None"` and
  `"Unknown/missing"` spelt as data -> the Unknown level; `dataset` spelt `DEV` / `Dev`
  / ` dev ` -> `S02` halt; a `y_pred`-only table -> the three descriptive blocks build
  and `calibration_from_table` raises (lens 1 N6, carried); the flow sums to
  `rows_read` on every table without dev rows and is short by the dev count with them
  (lens 1 N5, carried).

## Could not check

- Coverage of the clustered decile-bin intervals against the DEC-08 bar (DEC-18 (a) not
  built; not measured here).
- The R `rms::val.prob` capture (`[pending]`) and the Debray 2017 attribution
  (`[unverified]`); not fetched.
- The note's "the i.i.d. route on the same cohorts reproduces the lens's own figures to
  the digit" - the i.i.d. column of the script's output equals lens 1's table, which is
  the same claim from the other side; lens 1's script itself was not re-run.
- PowerShell 5.1: every figure here is Git Bash from the worktree.
- Whether `boundary_estimate` on N1's shapes is reached through `calibration_from_table`
  from a CSV - it is the same array path, but I built the arrays directly.

## Sentences I refused to write

- "The clustered route now covers at 0.95" - measured 0.914-0.970 on two shapes of one
  process and 0.900-0.960 on six shapes of two others; stated as those figures.
- "The repair fixed the clustered intervals" as a class - the O:E and slope were
  reproduced bit for bit on two cohorts and the coverage measured on the shapes above.
- "`_prevalence_invariant` is wrong" - it is right in the direction that matters for
  the typed reason it protects (fixed totals -> `fixed_by_outcome_stratification`) and
  wrong only in the sentence's converse (N1).
- "No customer can obtain a traceback" - a blank `case_id` is one, on a path E7 has not
  wired yet (N4).
- "The mutation sweep is adequate" - 30 of 30 committed mutants die; 9 of my 10 do not
  (N5).
- "The i.i.d. numbers are correct" as a class - stated as the deviation figures on F4
  and 150 cohorts.
- "`cmd_run` never reaches calibration" as a guarantee - it does not call it today
  (`grep calibration cli.py` is empty); E7 changes that.

## Appendix - the probe scripts (scratchpad, not committed)

Under `scratchpad/lens-E6-r2-fresh-attack/probe/`: `rederive.py` (own Newton, O:E,
Brier, ECE, bins, Wilson; F4 + 150 cohorts), `oracle.py` (statsmodels newton / Logit,
sklearn), `attack_prev.py` (N1), `irls_dbg.py` (N2), `attack1.py` / `attack2.py`
(constructions, schema, timing, level 0.90), `attack_desc.py`, `caseid.py` /
`caseid3.py` (N4), `my_mutants.py` / `my_mutants_full.py` / `survivor_probe*.py` (N5),
`bin_oracle.py` (every decile bin), `oe_var_oracle.py` (O:E and slope on shuffled
variable-size cases), `brier_oracle.py`, `cov_clustered.py` / `cov_resid.py` /
`cov_resid_harsh.py` (coverage), `verdict_walk.py`, `f4_notes.py`. Outputs beside them
(`cov_*.txt`, `sweep_day6.txt`, `suite_run.txt`). Both worktrees removed; the scripts
stay for the repairer.
