# Lens 3 (regression and record) - build day 6 repair round 2, lane E, `7eb617f` - 2026-09-18

**Verdict: PASS.** No blocker. Every figure in the repair-2 note re-measures in the
`7eb617f` worktree with `PYTHONPATH` forced (`429 passed, 1 skipped, 1 xfailed`; `-m day6`
65; `-m day5` 54; `day1`..`day4` 59+1 / 40 / 29+1 / 182; ruff and format clean; doctor
clean; the sweep `34 planted, 34 killed, 0 survived` in both shells; both coverage seeds
equal T7's 24 clustered and 12 i.i.d. cells to the digit) and in PowerShell 5.1 from the
main tree; the four tests the note says fail at `a5a5ed8` fail there on the assertion the
note quotes (`4 failed, 57 passed`); the six sweep mutants the note names die on the named
test alone with the quoted `E` lines; every one of the eighteen falsified phrases is
absent at `7eb617f` and present at its named sha; lens 2's two sentence findings and its
recorded output change are closed on lens 2's own inputs; lens 1's four blockers stay
closed on lens 1's one-liners. The prevalence rule the round changed agrees with an
exhaustive enumeration of every possible draw on 6,917 random case shapes (0
mismatches). What remains is non-blocking: two T7 measurements and the F4 IPA interval
that no test asserts, one docstring phrase that is loosely true on its own named input,
and one sentence in the note that generalises past the shapes it measured.

Worktrees: `7eb617f` (twice - one for figures, one for mutant planting) and `a5a5ed8`
under `scratchpad/lens-E6-r3-regression/`, `PYTHONPATH=<worktree>/src` forced and proved
by `python -c "import proofpack;print(proofpack.__file__)"` printing each worktree's own
`src/proofpack/__init__.py` before every figure below. All three removed at the end. The
main tree was used read-only (the note's commands in PowerShell; `git diff`; the sweep and
the seed-2026 coverage run, which copy elsewhere) and `git status --short` was empty
before this note was written.

## Blockers

None.

## Non-blocking

### N1 - three figures the note and T7 quote are measured, reproduce here, and are asserted by no test

- T7's "Which annotations each calibration cell carries" table (60 one-row cases, 3 events,
  `p = 0.08`, B = 200, seed 5): re-measured `iid oe ['very_low_precision']`, clustered oe
  `['log_delta_refused_clustered']`, Brier / IPA `[]` on both routes. No test feeds that
  cohort (`grep -n "0.08" tests/test_calibration.py` is empty). The note's RG-N3 row says
  "none (prose)" for the test, so this is disclosed, not hidden; recorded because Josh's
  needs-2 decision rests on it and a change to `_Ctx.tier` would leave T7 stale unnoticed.
- T7's and the note's F4 IPA `0.3385 (-0.0290, 0.6148)` with `['very_low_precision',
  'imprecise']`: re-measured to the digit, and my own outcome-stratified row bootstrap from
  the cell's generator (`policy.rng(["calibration", "ipa"])`, 12 positives then 8
  negatives, m from m each) reproduces the bounds to 4.9e-17 / 0.0. The suite asserts the
  F4 IPA estimate at 1e-9 and `ci_lo is not None` elsewhere; no test asserts the F4 IPA
  bounds or its flags.

### N2 - one docstring phrase is loosely true on its own named input (sentence precision)

`calibration.py` module docstring (FA-N2 rewrite): "the ``MAX_STEP_HALVINGS`` halvings of
one Newton step all raise the deviance ... 1 on 50 rows all at ``p = 1.0`` with 12
events". Re-run on that input: `dev0 = 2099.95`, the Newton step is `-7.6e11`, and of the
31 candidates the loop tries (the full step plus 30 halvings) 30 have an **infinite**
deviance and the last (scale `2**-30`) a finite `16322.67`. Every candidate is above
`dev0`, so "raise" is not false, but the exit fires on the code's `isfinite and <= dev`
test, and the mechanism on the named input is non-finiteness, which the sentence does not
name; "the 30 halvings" also omits the full step. The test
(`test_irls_not_converged_at_iteration_one_...`) asserts `iterations == 1`, the reason
and the docstring phrase, not the candidate deviances. Wording, not behaviour.

### N3 - one sentence in the note generalises past the shapes it measured (hard rule)

Note, paragraph 2: "on the inputs where the two rules differ the reference Brier moves
from ``boundary_estimate`` (no interval) to ``fixed_by_outcome_stratification`` (no
interval) with the same estimate; no cell gains an interval and no refusal is loosened."
The note measured that on shapes A, D and RG-N1 (the eleven-shape test's three
`calibration_block` runs). The general claim rests on the derivation (the round-1
condition - identical counts within a stratum - implies the new one, so the rule can
only move `False -> True`, and on a `True` input every draw's reference Brier is
identical). I did not falsify it: `probe/prev_exhaustive.py` enumerates every
m-from-m multiset draw per stratum on 6,917 random shapes of 2-6 cases of 1-3 rows
(two seeds; strata of at most 5 units) and the new rule equals "one distinct prevalence
over all draws" on every one (2,030 of them `True`). The sentence should name the three
shapes and the derivation rather than "the inputs where the two rules differ". The
note's own "Sentences refused" list already declines the stronger form; this is the
weaker one that slipped through. Not shipped text (the note is in the scratchpad).

### N4 - the note's "four sites" is five

"Sentences refused": "they are the four sites in ``irls_logistic`` that return that
reason". `grep -n '"irls_not_converged"' src/proofpack/stats/calibration.py` prints five
return lines (368, 380, 391, 394, 396): singular information at a step and singular at
convergence are two sites. The shipped docstring says "four exits" and folds those two
into "a singular information matrix at a step or at convergence", which is right; only
the note's count is off.

### N5 - seven of lens 2's planted mutants still survive `-m day6`, as the note carries

Re-planted at `7eb617f` through the sweep's own `make_copy` / `plant` / `restore`
(`probe/lens2_survivors.py`; baseline `65 passed`): L2-3 killed (`1 failed, 23 passed`);
L2-4, L2-5, L2-6, L2-7, L2-8, L2-9, L2-10 each `65 passed, 366 deselected`. L2-1 and L2-2
are in the committed sweep and die there. The note's carried table names all seven with
the one assertion each needs; nothing to add.

## Could not break

- **Suite, worktree `7eb617f`, Git Bash:** `429 passed, 1 skipped, 1 xfailed in 55.51s`;
  `-m day6` `65 passed, 366 deselected in 8.42s`; `-m day5` `54 passed, 377 deselected`;
  `day1` `59 passed, 1 skipped, 371 deselected`; `day2` `40 passed, 391 deselected`;
  `day3` `29 passed, 401 deselected, 1 xfailed`; `day4` `182 passed, 249 deselected`
  (day-1..5 counts equal the day-5 handoff's; only the deselected counts grew); `ruff
  check` `All checks passed!`; `ruff format --check` `66 files already formatted`;
  `doctor --offline` `All essential checks passed.`; the named acceptance test `1 passed
  in 2.27s`; the day-5 handoff's three named sets `27 passed, 155 deselected` / `7
  passed, 47 deselected` / `7 passed, 47 deselected`. **Main tree, PowerShell 5.1**
  (`proofpack.__file__` printed as the main tree's first): `429 passed, 1 skipped, 1
  xfailed in 49.83s`; `65`; `54`; `1 passed`; ruff both clean; doctor clean;
  `day1`..`day4` `59+1 / 40 / 29+1 / 182`; the three named sets `27 / 7 / 7`. No command
  in the note's table failed in either shell.
- **Fails pre-fix.** The two final test files copied into the `a5a5ed8` worktree: `4
  failed, 57 passed in 6.32s` (note: `6.28s`). First `E` line per test, each the one the
  note quotes: flat-O `AssertionError: assert 'varies from draw to draw' not in
  '``stats.cal...`; eleven shapes `AssertionError: ('mixed (1,1) x 30 + (2,2) x 30',
  {0.5})` / `assert False is True`; iteration-one `AssertionError: assert 'halvings of
  one Newton step all raise the deviance' in ...`; sentences `AssertionError:
  ('calibration.py', 'is the same in every draw exactly when')`. None an import abort.
  The flat-O and iteration-one tests fail at `a5a5ed8` only on their docstring
  assertions - their behaviour assertions (`O == {100}`, `cluster_bootstrap_percentile`,
  `iterations == 1`, `constant_score`, `n_clipped 50`) pass there, which is what the note
  says (shipped code right, sentence wrong). The four tests that pass at `a5a5ed8` (L2-2
  observer, RG-N2 pin, RG-N6 literals, the site column) are the four the note lists.
- **Mutants, named test only, worktree** (`probe/plant.py`, the sweep's own patterns,
  file restored byte for byte, `git status` clean after):
  `decile_bin_ids_are_a_prefix_not_the_bins_rows` on the L2-2 observer `E assert 20 ==
  38`; `prevalence_invariant_is_the_round1_identical_counts_rule`,
  `..._reads_positive_counts_only`, `..._reads_row_counts_only`,
  `..._is_the_b93e050_label_rule` on the eleven-shape test each `E AssertionError:
  ('mixed (1,1) x 30 + (2,2) x 30', {0.5})`; `prevalence_invariant_always_true` `E
  AssertionError: ('pure 10 / 12 one-row + mixed (1,1) x 20 + (2,2) x 20', {0.4918...,
  ...})` - both directions of the rule are observed.
- **Sweep:** `python scripts/mutation_sweep.py --marker day6`: `34 planted, 34 killed, 0
  survived; 170 s` (Git Bash, worktree) / `172 s` (PowerShell, main tree).
- **Coverage:** `coverage_calibration.py --full` (seed 2026) and `--full --seed 7`,
  worktree, Git Bash: all 24 clustered cells and all 12 i.i.d. cells equal T7's table
  (seed 2026 clustered: O:E 0.920 / 0.943 / 0.903, intercept-in-the-large 0.920 / 0.943 /
  **0.897**, slope 0.940 / 0.943 / 0.933, joint intercept 0.903 / 0.927 / 0.917; seed 7:
  0.937 / 0.960 / 0.937, 0.927 / 0.957 / 0.930, 0.937 / 0.940 / 0.920, 0.923 / 0.953 /
  0.940); `elapsed 154 s` / `155 s`. Seed 2026 diffed against lens 2's
  `cov2026_bash.txt`: identical bar the elapsed line and one trailing blank line (the
  note's claim). Seed 2026 repeated in PowerShell from the main tree: identical bar the
  elapsed line (`161 s`) and `Out-File`'s BOM.
- **The prevalence rule, exhaustively.** `probe/prev_exhaustive.py` (above): on 6,917
  random shapes every possible draw enumerated; `_prevalence_invariant` equals "one
  distinct prevalence" on all of them. On the note's own shapes (`probe/recheck.py`): A,
  B, D, RG-N1 `invariant True, 1 distinct prevalence in 500 draws, brier_ref
  fixed_by_outcome_stratification, method none, no interval`; the control `False, 16
  distinct, cluster_bootstrap_percentile (0.24994, 0.24996)`.
- **F4 and the fixture** (`probe/f4_oracle.py`, statsmodels 0.15.0, scikit-learn 1.9.0):
  CSV body regenerated from the header's recipe, byte-identical (the file is `w/crlf`
  in the worktree and the reader tolerated it); offset `fit(tol=1e-10)` estimate / SE /
  deviance 0.0 / 0.0 / 0.0, 4 iterations, default fit 0.0 / 0.0, 4 iterations, SEs 0.0
  apart; joint tight 0.0 on all five, 6 iterations; default 0.0 on all four, 5
  iterations, tight-vs-default SEs 9.13e-6 / 1.99e-5 apart; sklearn Brier 0.0; hand O:E,
  log-delta SE, bounds, Brier, reference, IPA, both ECEs and the 5-bin ECE all 0.0.
  Engine: intercept-in-the-large 2.2e-16 from the tight fit, its `wald_se` 2.19e-9; joint
  estimates 1.7e-16 / 0.0; joint SEs 3.30e-10 / 7.21e-10 from the tight fit and 1.1e-16 /
  1.1e-16 from `fit(method='newton', tol=1e-12)`; engine iterations 7 (joint) / 4
  (offset) - every figure in the two fixture notes. The suite asserts the statsmodels
  values at 1e-6 and the sklearn / hand values at 1e-9 (`tests/test_calibration.py:174-260`).
- **Lens 1's blockers at `7eb617f`, its own one-liners:** B1 prints `1.0096 1.3674 1.0275
  1.328 cluster_bootstrap_percentile`; B2 N = 0..14 each a block, JSON without NaN; B3
  `brier_ref` `fixed_by_outcome_stratification` on the 100 x 2 cohort; B4 neither "every
  resample" nor "overstates" in `ci_not_computed_because`.
- **Lens 2's findings at `7eb617f`:** FA-N2 `all 1.0, 12 events: reason
  irls_not_converged it 1`, block `irls_not_converged` / `iterations 1`, slope
  `constant_score`, `n_clipped 50`; FA-N3 as N1 above; FA-N4 still raises `TypeError: '<'
  not supported between instances of 'str' and 'NoneType'` from
  `calibration_from_table` on a blank `case_id` (carried, pre-existing; `grep calibration
  src/proofpack/cli.py` is empty); RG-N2 bin 1 `number.flags ['very_low_precision',
  'below_200_events_or_nonevents']`, `analytic.flags ['very_low_precision']`, method
  `wilson`; RG-N5 500 flat draws on 100 two-row (1, 1) cases `distinct O = {100}`; pure
  positive cases of 1 and 2 rows (5 each) beside 10 negatives, 500 by-class draws: 11
  distinct `O`.
- **Sentence census, whitespace collapsed, `git show <sha>:<file>`:** lens-1 list 8 / 8
  present at `b93e050`, 0 / 8 at `a5a5ed8` and `7eb617f`; lens-2 list 3 / 10 at
  `b93e050`, 10 / 10 at `a5a5ed8`, 0 / 10 at `7eb617f` - the note's 8 / 10 / 0 of 18.
- **`E = 0`:** all scores 0.0 with 14 events: O:E `zero_denominator`, intercept-in-the-large
  `irls_not_converged`, slope `constant_score`, JSON without NaN (the T7 sentence).
- **Nothing weakened.** `git diff --name-status a5a5ed8 7eb617f -- tests/`: two `M`, no
  `D`; against `4eb44f3`: four `A`. The test diff adds no `skip` / `xfail` / `.only` /
  `TODO` / `FIXME` and removes no `pytest.mark` or `def test_`. `git diff a5a5ed8 7eb617f`
  touches exactly the ten files the note lists; `bootstrap.py`, `subgroups.py`, `cli.py`,
  `io/`, `schema/`, `pyproject.toml` untouched from `a5a5ed8`, and `bootstrap.py`,
  `cli.py`, `io/mapping.py` untouched from `4eb44f3` (0 lines), so `MIN_UNITS_PER_STRATUM
  2`, `MAX_FROZEN_VARIANCE_SHARE 0.20` and the day-4/5 thresholds are as they were;
  `calibration.py`'s diff is docstrings plus `_prevalence_invariant` only, so
  `CURVE_MIN_EVENTS 200`, `CLIP_EPS 1e-12`, `IRLS_TOL 1e-10`, `IRLS_MAX_ITER 100`,
  `SEPARATION_TOL 1e-8`, `MAX_STEP_HALVINGS 30`, `N_BINS 10` stand. `number.py` is
  comment-only; code `METHODS` (18) / `FLAGS` (15) / `NOT_ESTIMABLE_REASONS` (21) equal
  the schema's `$defs/method`, `flag`, `notEstimableReason` enums with no member either
  side. `cli.py` imports nothing from `proofpack.stats`.
- **scipy-free import:** with `scipy`, `scipy.stats`, `statsmodels` and `sklearn` set to
  `None` in `sys.modules`: `proofpack`, `proofpack.stats`, `calibration`, `descriptive`
  import, no `scipy` module is loaded afterwards, and a 120-row block builds.
- **Line endings, main tree:** `git ls-files --eol` `i/lf w/lf` on the nine text files
  the note names and `i/lf w/crlf` on `design/conventions_T7.md` (338 CRLF, 0 bare LF -
  no mixing), as the note says.
- **Commit:** `fix E: day-6 repair round 2 - ...`, ends `Co-Authored-By: Claude Opus 5
  <noreply@anthropic.com>`; `7eb617f [main]`, not pushed.

## Could not check

- The R `rms::val.prob` capture (`[pending]`, day 9) and the Debray 2017 attribution
  (`[unverified]`); not fetched.
- Coverage of the clustered decile-bin intervals (DEC-18 (a), not built) and of the Brier
  / reference Brier / IPA under a clustered plan; lens 2's second-process figures in T7
  (marked there as the lens's own) were not re-run.
- The seed-7 coverage run in PowerShell (seed 2026 only was repeated there; the note ran
  neither in PowerShell).
- The note's process-incident claim that the redo reproduced "this session's own text" -
  what I checked is the diff against `a5a5ed8` and its measurements, not the lost edits.

## Sentences I refused to write

- "The prevalence rule is exact" - it agrees with exhaustive enumeration on 6,917 random
  shapes of at most 6 cases and 5 units per stratum, and with 500 draws on the eleven
  named shapes; stated as that.
- "The clustered calibration intervals meet DEC-08" - 23 of 24 cells at or above 0.90 and
  one at 0.897, one process, three shapes, two seeds.
- "Every new test pins the repair" - two of the four `a5a5ed8`-failing tests fail there on
  a docstring assertion only; four more pass there by design and are mutant- or
  sentence-anchored as the note says.
- "The i.i.d. route is unchanged this round" - `_prevalence_invariant` is reached on the
  row resampler and returns `True` there as before; the F4 block's every figure above
  equals the fixture; stated as those measurements.
- "No shipped sentence generalises" - N2 is loosely true on its named input; N3 is in the
  note, not the code.

Worktrees removed at the end (`git worktree list` shows none under
`lens-E6-r3-regression`). Probe scripts and outputs stay in
`scratchpad/lens-E6-r3-regression/` (`probe/f4_oracle.py`, `prev_exhaustive.py`,
`plant.py`, `recheck.py`, `lens2_survivors.py`; `full_bash.txt`, `day*_bash.txt`,
`sweep_bash.txt`, `sweep_ps.txt`, `cov2026_bash.txt`, `cov7_bash.txt`, `cov2026_ps.txt`).
