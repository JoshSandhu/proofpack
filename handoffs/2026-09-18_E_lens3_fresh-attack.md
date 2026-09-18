# Lens 3 (fresh attack, DEC-12(i)) - build day 6 repair round 2, lane E, `7eb617f` - 2026-09-18

**Verdict: PASS. No blockers.** Every number I re-derived without repo code agrees with
the engine: F4 to 3.6e-15, 150 random i.i.d. cohorts at n = 30 / 200 / 2,000 to 1.2e-14
(joint intercept; every other statistic at or below 8.0e-15, most exactly 0), statsmodels
GLM with and without offset and sklearn to 4.4e-16; the clustered O:E and Brier bit for bit
and the clustered intercept-in-the-large and slope to 1.1e-16 from my own case bootstrap
off each cell's generator on 80 shuffled cases of 1-5 rows. The repaired prevalence rule
(`_prevalence_invariant`, the one statistical gate this round touched) agrees with an
**exhaustive enumeration of every possible draw** on 2,567 random case shapes (717 of them
invariant) and with 500 draws on 2,000 larger shapes, zero mismatches. Every lens-1 and
lens-2 blocker stays closed; all 18 phrases the sentences test greps were present at their
named sha and are gone at HEAD. What I found is six non-blocking items: two shipped
sentences a measurement falsifies (N1, N2), one minor sentence (N5), an `inf` reachable
in the O:E cell's `resample_sd` on a score column below 1e-154 (N3, not reachable through
`cmd_run` today), nine of my eighteen planted mutants surviving the full suite (N4, five
of them new), and one pre-existing precedence between two typed reasons (N6).

Worktrees: `7eb617f` and `a5a5ed8` under `scratchpad/lens-E6-r3-fresh-attack/`,
`PYTHONPATH=<worktree>/src` forced and proved (`python -c "import proofpack;
print(proofpack.__file__)"` printed each worktree's own `src/proofpack/__init__.py`; the
unforced form printed the main tree's, the trap the brief names). Both removed at the end.
The main tree was read only and is clean at `7eb617f` apart from this note (and the regression lens's untracked note beside it). Git Bash
throughout; PowerShell 5.1 not used.

## Blockers

None.

## Non-blocking

### N1 - the eleven-shape test's docstring miscounts its own shapes (sentence violation)

`tests/test_calibration.py::test_the_prevalence_rule_agrees_with_the_resamplers_own_draws_on_eleven_shapes`
docstring: "the count of distinct prevalences is 1 on the **five** shapes marked ``True``
and 16, 11, 13, 92 on four of the ``False`` ones". `PREVALENCE_SHAPES` marks **seven**
shapes `True` (A, B, D, RG-N1, "mixed (1,1) x 20 + 10 one-row pos + 15 one-row neg",
"mixed (1,2) and (2,3) beside 2 one-row pos", "100 one-row cases, 30 positive") and four
`False` (`python -c "from test_calibration import PREVALENCE_SHAPES; ..."` prints `True: 7
False: 4`). The assertions are right (each shape's flag is checked against its own 500
draws); only the count in the sentence is wrong. Repro: `cd <wt>; PYTHONPATH=<wt>/src
python -c "import sys; sys.path.insert(0,'tests'); from test_calibration import
PREVALENCE_SHAPES as S; print(sum(e for *_, e in S))"` -> `7`.

### N2 - T7's annotation table names an input on which two of its four cells read differently (sentence violation)

`design/conventions_T7.md`, "Which annotations each calibration cell carries": "Measured on
60 one-row cases with 3 events (`p = 0.08` on every row, B = 200, seed 5) ... | O:E,
intercept-in-the-large, slope, intercept | ... measured `['very_low_precision']` |". On
that literal input the score is constant, so the slope and the joint intercept are
`constant_score` with `flags: []` on both routes; only the O:E and the
intercept-in-the-large read `['very_low_precision']` (i.i.d.) and
`['log_delta_refused_clustered']` / `['irls_wald_refused_clustered']` (clustered). The
Brier row's "measured `[]`" is true but for a different reason than the row implies: on
that input the Brier and IPA are `boundary_estimate` and the reference Brier
`fixed_by_outcome_stratification`, so the flags are the tier list on a refusal. The rule
the table states (`_Ctx.tier` passes `events=None` under a plan; `_brier_cells` uses
`precision_flags(n_units)`) is what the code does; the measurement column is not what that
input produces. Repro: `PYTHONPATH=<wt>/src python probe/t7_check.py` (prints every cell's
flags and reason on that input, both routes).

### N3 - `oe.bootstrap.resample_sd` is `inf` when a draw's O:E exceeds about 1e154

`bootstrap_percentile` (day 4) takes `usable.std(ddof=1)` of the draws; numpy squares
them, and values above about 1.3e154 overflow to `inf` while the percentile bounds stay
finite. The O:E is the first bootstrapped statistic in the engine with an unbounded
scale, so build day 6 made the path reachable. Constructed (declared plan, 30 two-row
cases, 20 events, B = 200): every score at `1e-154` gives `resample_sd 4.1e152`; at
`1e-155` it is `inf`; 57 rows at `1e-160` beside 3 at `0.5` give `est 13.33` with
`resample_sd inf`. `json.dumps(block, allow_nan=False)` raises; `cli.py` uses the default
`json.dumps`, which would write the non-JSON token `Infinity`. The schema does not catch
it (a Python `inf` satisfies `"type": "number"`). Not a blocker today: `cmd_run` does not
call calibration (`grep calibration src/proofpack/cli.py` is empty), and a probability
column whose bulk sits below 1e-154 is not one a real model produces. It must be closed
before E7 wires the block: `sd = None` (or the typed `boundary_estimate` route) when the
standard deviation is not finite, in `bootstrap_percentile`, with the 57-plus-3 input as
the regression test. Repro: `PYTHONPATH=<wt>/src python probe/inf_thresh.py`.

### N4 - nine of eighteen planted mutants survive the full suite; five are new

Each planted in a copy through `scripts/mutation_sweep.py`'s own `make_copy` / `plant` /
`restore` (`assert_imports_from_copy` passed), `-m day6` first, then the full suite with
`test_ci_runs_every_declared_day_marker_without_a_hardcoded_list` deselected (it reads
`.github/`, absent from the copy). Every survivor was then run beside the unmutated copy
on a constructed input (`probe/survivor_demo.py`):

| id | mutant | outcome | differs on |
|---|---|---|---|
| L3-1 | `_prevalence_invariant` slices `per_unit[start : start + n_units - 1]` (each stratum's last unit is never inspected) | **survives** | 4 positive cases (three one-row, one two-row, the two-row case last) beside 10 one-row negatives: draws take 5 distinct prevalences and the code renders `brier_ref` `cluster_bootstrap_percentile (0.2041, 0.2422)`; the mutant renders `fixed_by_outcome_stratification`, no interval. The eleven shapes all place their differing units earlier in the stratum, so the test cannot tell. **The shipped rule is right** (the exhaustive enumeration below), the observer is missing. |
| L3-2 | `_irls_cells` uses `z_for(DEFAULT_LEVEL)` instead of `z_for(ctx.level)` | **survives** | F4 at `level=0.90`: intercept-in-the-large `(-0.4545, 1.3670)` rendered with `ci_level: 0.9` becomes `(-0.6290, 1.5414)` under the same label - the day-5 item-17 defect class (a level-blind interval), on the Wald cells. My hand value at 0.90: 0.45623 +/- 1.644854 x 0.553687 = (-0.4545, 1.3670), so the shipped code is right; no test feeds a non-default level to the three IRLS cells. |
| L3-3 | `mean_pred` is the bin's median | **survives** | F4's bins are evenly spaced, so mean = median there and the fixture observes nothing; on any random cohort the two differ (my re-derivation compared `mean_pred` to the bin mean on 150 cohorts: 0 deviation, so the shipped value is the mean). |
| L3-4 | `SEPARATION_TOL = 1e-4` | survives | `p in {1e-5, 1 - 1e-5}` x 30, `y = p > 0.5`: `intercept_large` converges at iteration 1 to `-2.3e-12 (-80.02, 80.02)` (`irls_wald`; SE 40.8 is `1 / sqrt(60 x 1e-5)`); the mutant types it `complete_separation`. Both typed; a constant with no observer at its own value. |
| L3-5 | `change <= tol * 1e4` (IRLS converges at 1e-6) | survives | estimates move by at most 9.8e-13 over 50 cohorts of n = 200 and F4 loses one iteration per fit; below every acceptance criterion, so equivalent at the output. Recorded, not carried. |
| L3-6..9 | lens 2's L2-6 (clip flag under clustering), L2-8 (`case_id` unsliced), L2-9 (`event_cases` over non-events), L2-10 (few-events tier under clustering) | survive, as lens 2 measured | the repair note carries them; unchanged. |

Killed by `-m day6`: swapped weights in the prevalence rule, "two distinct values read
as fixed", the last stratum skipped, `_unavailable` dropping `est`, deciles by an unstable
sort, the O:E `k = E`, three step-halvings, the plan-contradiction check removed, and
`brier_ref` deferring to the guard (N6's alternative). L3-1 and L3-2 each need one
assertion: a shape whose differing unit is last in its stratum; F4 at `level=0.90` with
the three Wald bounds asserted. The committed sweep from the worktree: `34 planted, 34
killed, 0 survived; 172 s`.

### N5 - one T7 sentence names an input no block is built from (sentence violation, minor)

`design/conventions_T7.md`, "Typed IRLS outcomes":
"`test_separation_and_non_convergence_are_typed_reasons_never_inf_nan_or_a_traceback` and
`test_irls_not_converged_at_iteration_one_names_the_step_halving_exit_not_the_budget`
feed the separated, one-crossing and all-1.0 inputs and serialise each block without
NaN." The one-crossing input (`y2[30]` flipped) goes to `irls_logistic` directly
(`tests/test_calibration.py:983-988`); no block is built from it and nothing is
serialised. The separated and the all-1.0 blocks are serialised. Say "the two blocks".

### N6 - `brier_ref` reads `fixed_by_outcome_stratification` on a resampler the class-units guard refuses (pre-existing since round 1)

`_brier_cells` evaluates `_prevalence_invariant` before `bootstrap_percentile` applies
`deficient_class`. One case holding 180 of 200 rows beside twenty one-row cases (declared
plan): `brier` and `ipa` are `insufficient_clusters`, `brier_ref` is
`fixed_by_outcome_stratification` with `est 0.2499` and `['very_low_precision']`; the same
on n = 5 and n = 10 declared two-row cases. Identical at `a5a5ed8` (measured in that
worktree); at `b93e050` the label rule read the mixed stratum as varying and the cell was
`insufficient_clusters`. Both reasons are true of the cell and the estimate is the plain
`pi (1 - pi)`, so no wrong number; the 180/200 test's key list omits `brier_ref`, so the
builder chose this and no note records the choice. Record in T7 which reason wins.

## Could not break

- **Suite, worktree, PYTHONPATH proved:** `429 passed, 1 skipped, 1 xfailed in 54.39s`;
  `-m day6` `65 passed, 366 deselected`; `-m day5` `54 passed, 377 deselected`; `-m day1`
  `59 passed, 1 skipped, 371 deselected`; `day2` `40 passed`; `day3` `29 passed, 1
  xfailed`; `day4` `182 passed` - the day-1..5 counts equal the day-5 handoff's and the
  repair note's. `ruff check` `All checks passed!`; `ruff format --check` `66 files already
  formatted`; `doctor --offline` `All essential checks passed.` The day-5 handoff's three
  named sets: `27 passed, 155 deselected`, `7 passed, 47 deselected`, `7 passed, 47
  deselected`. `git diff a5a5ed8 7eb617f -- bootstrap.py subgroups.py cli.py io/ schema/
  pyproject.toml schema` is empty; every day-4/5 constant reads as the lens-2 note lists
  them (`MIN_UNITS_PER_STRATUM 2`, `MAX_FROZEN_VARIANCE_SHARE 0.20`, `LOW/VERY_LOW 10/30`,
  `FEW_EVENTS 5`, `MIN_USABLE_FRACTION 0.90`, `DEFAULT_B 2000`, `DEFAULT_SEED 20240101`,
  `CURVE_MIN_EVENTS 200`, `CLIP_EPS 1e-12`, `IRLS_TOL 1e-10`, `IRLS_MAX_ITER 100`,
  `SEPARATION_TOL 1e-8`, `MAX_STEP_HALVINGS 30`, `N_BINS 10`). `git diff --name-status
  a5a5ed8 7eb617f -- tests/`: two `M`, no `D`; zero added lines containing `skip`, `xfail`
  or `.only`. Every touched file `i/lf w/lf` except `conventions_T7.md` (`w/crlf`), as the
  note says. The two final test files copied into the `a5a5ed8` worktree and run with
  `-m day6`: `4 failed, 61 passed` - exactly the four tests the note names (the note's
  `57 passed` is the two files alone; the four failures are the same). `import proofpack`,
  `proofpack.stats`, `calibration`, `descriptive` with `scipy`, `statsmodels` and
  `sklearn` set to `None` in `sys.modules`: import and run.
- **Re-derivation without repo code** (`probe/rederive.py`: my own Newton-Raphson on the
  Bernoulli log-likelihood with step-halving, two parameters and the offset model;
  observed-information Wald SEs; O:E and log-delta bounds; Brier / reference / IPA; both
  ECEs; stable-sort deciles with `divmod` sizes; hand Wilson per bin). F4: max
  |engine - mine| 3.6e-15 over every quantity. 150 cohorts (50 each at n = 30 / 200 /
  2,000, seed 2026-09-18): joint intercept 1.2e-14, its SE 1.8e-15, slope 8.0e-15, its SE
  1.3e-15, slope bound 4.0e-15, intercept-in-the-large 2.2e-16, its SE 5.6e-17, its
  bounds 4.4e-16, deviances 9.1e-13 (offset 4.5e-13), O:E 0, its bounds 2.2e-16, Brier,
  reference, IPA, both ECEs, every bin's `n`, `events`, `mean_pred` and observed rate
  exactly 0, bin Wilson 2.2e-16; every rendered i.i.d. method label is what I computed
  (`log_delta`, `irls_wald`, `wilson`, `bootstrap_percentile`). Oracles (60 cohorts, seed
  99): statsmodels GLM `method="newton", tol=1e-12` offset intercept 2.2e-16, its SE
  5.6e-17, joint intercept 2.2e-16, slope 4.4e-16, its SE 1.1e-16, deviance 4.5e-13;
  sklearn Brier 0.
- **The prevalence rule, exhaustively** (`probe/prev_fuzz.py`): 3,000 random shapes of 1-7
  cases of 1-4 rows (random labels, 40 % forced pure), keeping those with at most five
  units per stratum; for each, every possible draw enumerated (`m^m` per stratum, product
  over strata, prevalences as exact `Fraction`s) and "one prevalence over all draws"
  compared with `_prevalence_invariant(clustered_by_case(y, ids))`: 2,567 shapes checked,
  717 invariant, **0 mismatches** in either direction. 2,000 larger shapes (5-59 cases of
  1-5 rows) with 500 draws each: 0 mismatches. The docstring's derivation (necessity by
  moving a stratum's whole draw between two units; sufficiency because any draw sums to
  the identity draw's `R P - P R = 0`) is what the enumeration confirms.
- **Clustered route, method labels** (`probe/clustered_oracle.py`): 80 cases of 1-5 rows,
  rows shuffled, declared plan, B = 300, seed 11. My own single-stratum case bootstrap in
  first-appearance order from `policy.rng(cell_key)`: O:E bounds `(0.8913016702459742,
  1.1394371138915673)` bit for bit, 300 usable both; intercept-in-the-large and slope
  bounds to 1.1e-16 (my Newton per draw); Brier from my own three-stratum draw
  (positive, negative, mixed in that order from one generator) bit for bit
  (`{'positive': 14, 'negative': 17, 'mixed': 49}`). Every label
  `cluster_bootstrap_percentile`; every companion `clustered_data_analytic_ci_invalid`.
- **Lens-1 and lens-2 blockers, re-attacked.** FA-B1: seed-2026 coverage re-run from the
  worktree reproduces all 24 clustered cells and the 12 i.i.d. cells of T7's table (O:E
  0.920 / 0.943 / 0.903, intercept-in-the-large 0.920 / 0.943 / 0.897, slope 0.940 / 0.943
  / 0.933, joint intercept 0.903 / 0.927 / 0.917; `elapsed 159 s`); seed 7 reproduces T7's twelve clustered cells (O:E 0.937 / 0.960 / 0.937, intercept-in-the-large 0.927 / 0.957 / 0.930, slope 0.937 / 0.940 / 0.920, joint intercept 0.923 / 0.953 / 0.940; `elapsed 154 s`). Twenty-three of the twenty-four clustered cells at or above 0.90, the one at 0.897, as T7 says.
  FA-B2: N = 1..9 with and without a plan return a block with ten bins (bins 6-10
  `zero_denominator` at N = 5). FA-B3: 30 mixed (1,1) beside 30 (2,2) renders
  `fixed_by_outcome_stratification`. FA-B4: `_ECE_CI_WHY` carries neither "every
  resample" nor "overstates". Lens 2's FA-N1 / RG-N1 (the "exactly when"), FA-N2 (the
  budget sentence), FA-N6 (the wrapped phrase), RG-N5 (four sentences): all 18 phrases in
  the sentences test were grepped by me at their named sha with whitespace collapsed
  (8 of 8 present at `b93e050`, 10 of 10 at `a5a5ed8`) and are absent at `7eb617f`. L2-2
  (the prefix mutant) is in the committed sweep and dies there.
- **Constructions that behaved** (`probe/attack.py`, every block walked: every Number
  re-validates through `Number(**d)`, none lacks both an interval and a typed reason, no
  method outside `METHODS`, no interval under `method: none`, no flag outside `FLAGS`,
  no verdict word and no "calibrated" in any key or string, no `wilson` / `log_delta` /
  `irls_wald` / `bootstrap_percentile` under a plan, every companion refused under a
  plan; eight odd blocks also validate against `calibrationBlock` with zero errors): one
  case holding 180 of 200 rows (the four single-stratum quantities, the Brier and the IPA
  `insufficient_clusters`; N6 for `brier_ref`); 200 declared one-row cases equal the
  i.i.d. estimates with `cluster_bootstrap_percentile` labels; all scores 0.5 / 0.0 / 1.0
  / 1e-300 / 1 - 1e-16, i.i.d. and clustered (typed on every cell; the 1e-300 clustered
  case is N3); the boundary vector `[0, 1, 1e-300, 1 - 1e-16, 5e-324, ...]` (`n_clipped`
  40, all three fits converge); `y == (p > 0.5)` and its complement (`complete_separation`
  on slope and intercept, the rest with intervals); single class both ways, both routes
  (`single_class` on all seven, `brier_ref` est 0.0, IPA `None`, `curve_flag` 0 / 50);
  n = 1, 2, 5, 10, 25 i.i.d. and as two-row declared cases (n = 10 i.i.d. with one event:
  Brier `insufficient_positives`; n = 25 clustered: all `insufficient_clusters`); NaN,
  inf, -inf, 1.2, -0.2 in the score: `ValueError ... must lie in [0, 1]` before any cell;
  `logit` / `other` / `lower_is_positive`: `None` block with `score_not_probability` /
  `score_not_positive_class_probability`; an absent `score.type`: `H08` at validation;
  a declared plan with no ids: `ValueError` from `plan_clustering`; ties on 95 / 100 / 37
  / 1,000 rows over 9 / 1 / 3 / 7 distinct values: always ten bins, never empty, sizes
  `[10 x 5, 9 x 5]` / `[10] x 10` / `[4 x 7, 3 x 3]` / `[100] x 10`, edges as the
  tie rule states; 200 / 199, 199 / 200 and 199 / 199 flagged with the counts on the
  rendered bin Numbers and not on the companions, 200 / 200 not; the detected route on
  300 shuffled rows over 111 cases; `level` 0.90 and 0.99 carried on every Number
  including the ECE with the O:E bounds inside the 0.95 ones; 100,000 i.i.d. rows at
  B = 2,000 in 2.4 s and 50,000 two-row declared cases at B = 200 in 27.4 s (all seven
  rendered); quasi-separation (four rows at 0.5 with both labels): slope and intercept
  `irls_not_converged` at 100 iterations, finite deviance; scores at `expit(+/-700)`:
  intercept-in-the-large 24.45 (22.45, 26.45) with the clip flag, slope and intercept
  `irls_not_converged`; two events among 20 declared two-row cases: `insufficient_clusters`.
- **Descriptive** (`probe/desc.py`, the test's cohort): every value under a level is one
  `int` and one `float`; no score value coincides with any `pct`; the thirty numeric
  `site` labels are keys with `n: 1`; `n_sites` equals the distinct site count.

## Could not check

- Coverage of the clustered decile-bin intervals and of the Brier / reference Brier / IPA
  under a clustered plan against the DEC-08 bar (DEC-18 (a) not built; T7 says nobody
  has measured them; I did not either).
- Lens 2's second-process coverage figures (case effect the score does not carry): T7
  carries them as the lens's own; not re-run.
- The R `rms::val.prob` capture (`[pending]`) and the Debray 2017 attribution
  (`[unverified]`): not fetched.
- The `--marker day5` sweep and `coverage_bar.py`: `bootstrap.py` and `subgroups.py` are
  unchanged since `a5a5ed8`, so not re-run.
- PowerShell 5.1: every figure here is Git Bash from the worktree.

## Sentences I refused to write

- "The prevalence rule is correct" as a class - it agrees with exhaustive enumeration on
  2,567 shapes of at most five units per stratum and with 500 draws on 2,000 larger ones;
  stated as those counts.
- "The clustered intervals are right" - two cohorts reproduced bit for bit from the cell
  generators; coverage measured on one process at three shapes and two seeds.
- "No inf can reach the output" - N3 is one, on a score column below 1e-154.
- "The i.i.d. numbers are correct" - stated as the deviation figures on F4 and 150
  cohorts.
- "The mutation sweep is adequate" - 34 of 34 committed mutants die; 9 of my 18 do not.
- "`cmd_run` never reaches calibration" - it does not call it at `7eb617f`; E7 changes
  that.
- "T7 is now complete" - it carries the conventions listed; N2 and N5 are in it.

## Appendix - the probe scripts (scratchpad, not committed)

Under `scratchpad/lens-E6-r3-fresh-attack/probe/`: `rederive.py` (own Newton, O:E,
Brier, ECE, bins, Wilson; F4 + 150 cohorts + oracles), `prev_fuzz.py` (exhaustive draw
enumeration), `clustered_oracle.py`, `attack.py` (constructions; output in
`attack_out.txt`), `inf_thresh.py` (N3), `guard_order.py` (N6, both shas), `t7_check.py`
(N2), `schema_odd.py`, `desc.py`, `my_mutants.py` / `survivor_demo.py` (N4; output in
`my_mutants_out.txt`). Suite outputs `suite_*.txt`, `ruff.txt`, `sweep_day6.txt`,
`cov2026.txt`, `cov7.txt` beside them. Both worktrees removed.
