# Lens 2 (regression and record) - build day 6 repair round 1, lane E, `a5a5ed8` - 2026-09-18

**Verdict: PASS.** No blocker. Every figure in the repairer's note re-measures exactly in
both shells; every one of the sixteen tests the note says fails at `b93e050` fails there on
the assertion the note quotes; the four "mutant-measured" claims reproduce on the named
test alone with the quoted `E` lines; the committed sweep reads `30 planted, 30 killed, 0
survived` in Git Bash (139 s) and PowerShell (136 s); the twenty-four coverage cells at
both seeds reproduce to the digit and the two shells' outputs are identical bar the
elapsed line; F4 regenerates byte-identical from its recipe and every statsmodels /
sklearn / hand value in `f4_expected.json`, including the two rewritten notes' figures,
re-runs to 0.0; lens 1's four blockers close on lens 1's own one-liners and its
could-not-break constructions still hold. What remains is non-blocking: one module
docstring sentence written as an "if and only if" that a constructed input falsifies
(the prevalence rule; the typed reason the input then gets is `boundary_estimate`), one
unrecorded output change on the i.i.d. route (the decile-bin companion's flags), the
DEC-18 (c) coverage table not yet in T7, and four smaller sentences.

Worktrees: `a5a5ed8` and `b93e050` under `scratchpad/lens-E6-r2-regression/`,
`PYTHONPATH=<worktree>/src` forced and proved by
`python -c "import proofpack;print(proofpack.__file__)"` printing each worktree's own
`src/proofpack/__init__.py` before every figure below. Both removed at the end; the main
tree was used read-only (the note's commands, both shells) and is clean at `a5a5ed8`
apart from this note.

## Blockers

None.

## Non-blocking

### N1 - the prevalence rule's "exactly when" is an "if", not an "if and only if" (sentence violation)

`calibration.py` module docstring: "The resampled prevalence is the same in every draw
exactly when, within every stratum of the resampler, every unit carries the same number
of positive rows and the same number of negative rows". The note's "Sentences refused"
says the same: "it is exact for the per-stratum m-from-m draw". The condition is
sufficient, not necessary. Constructed and run (declared clustering, 138 rows, 54 cases):
10 one-row positive cases, 20 one-row negative cases (pure prevalence 1/3), 12 mixed
cases of (1 event, 2 non-events) and 12 of (2, 4). Over 1,000 draws of the module's own
`clustered_by_case` resampler the prevalence takes **one** value (0.3333...), yet
`_prevalence_invariant` returns `False` (the mixed stratum's per-unit counts are
`{positive: [1, 2], negative: [2, 4]}`), the reference Brier is bootstrapped, all 200
draws are usable and identical, and the rendered Number is `method: none`,
`not_estimable_reason: boundary_estimate`, no interval - the reason FA-B3 said this cell
avoids, on a shape that needs every mixed case's own prevalence to equal the pure strata's.
The IPA renders with an interval. Contrived, typed, no wrong number: non-blocking. The
sentence should read "when"; the docstring of `_prevalence_invariant` itself ("the rows of
one class it contributes are fixed exactly when every one of its units carries the same
number of rows of that class") is per stratum per class and holds.

Repro: `python probe/attack_prev.py <wt>` (scratchpad) - prints `distinct prevalences
over 1000 by-class draws: {0.3333333333333333} | _prevalence_invariant: False` and
`brier_ref rendered: none boundary_estimate None None usable 200`.

### N2 - an unrecorded output change on the i.i.d. route: the decile-bin companion loses the 200/200 flag

At `b93e050` `_decile_curve` appended `curve_flag` to `cell.number.flags` in place; on
i.i.d. rows `number` and `analytic` were the same object, so the flag sat on both. At
`a5a5ed8` `replace()` puts it on the rendered Number only. Measured on ten cohorts (n =
10, 25, 60, 250, 1,000; i.i.d. and two-row declared) with the block serialised at both
shas and every leaf compared: on the i.i.d. route below 200/200 the only differences are
the two ECE reason strings and, in each of the ten bins,
`observed/analytic/flags` losing `below_200_events_or_nonevents` (n = 1,000 differs in the
ECE strings only). The clustered route differs where the note says (O:E and the three
fits' `number` and `bootstrap`, `brier_ref` where the rule changed, the ECE strings). The
note's FA-N7 / M18 row describes the clustered case and does not say the i.i.d. companion
changes; no test pins which flags the i.i.d. `analytic` carries (the census assertion is
clustered-only). Consistent with the M18 rule, and the renderer reads `number`; recorded
because the note's "None is a widening: each either refuses more or changes which draws
an interval is the percentile of" does not cover a flag leaving a serialised companion.

### N3 - DEC-18 (c): the calibration coverage table is in the module docstring and the script, not in T7

`design/conventions_T7.md` carries the day-5 coverage-bar section (`coverage_bar.py`)
and nothing for `coverage_calibration.py`; `git diff b93e050 a5a5ed8 --stat` touches no
`design/` file. DEC-18 (c) says T7 carries the measured coverage table while every
clustered cell keeps its tier annotation. The note does not list T7 under "Carried".

### N4 - one cell of twenty-four below the bar, escalated and not decided

Re-measured: intercept-in-the-large, 60 x 3, seed 2026 reads **0.897** (seed 7: 0.930;
Monte-Carlo SE about 0.017; the i.i.d. Wald on the same cohorts 0.913). The note renders
it with the tier annotation and puts the decision to Josh (needs 1). DEC-08's sentence is
"refused with a typed reason below it"; DEC-18 (c) is the precedent the note cites for
rendering meanwhile. Recorded as open, not as a defect of the round.

### N5 - four smaller sentences, each with a run counter-example

- `calibration.py`, "so the event count ``O`` varies from draw to draw" (the flat
  resampler paragraph): 100 declared two-row cases each carrying one event and one
  non-event, 500 flat draws: `distinct O = {100}`. The O:E still renders
  `cluster_bootstrap_percentile (0.9555, 1.1111)`, 200 usable, from the variation of `E`
  alone - which is the design's own variability, so the number is not wrong; the sentence
  generalises.
- `calibration.py`, the b93e050 description "holds ``O`` at the same integer in every
  draw whenever every case is pure": all cases pure, positive cases of sizes 1 and 2,
  500 `clustered_by_case` draws: 13 distinct values of `O`.
- `number.py`, the comment "cases within outcome class when, e.g., every mixed case
  carries one event": mixed cases of (1, 1) and (1, 2) beside one-row pure cases - every
  mixed case carries one event - render `brier_ref` `cluster_bootstrap_percentile` with
  an interval, not `fixed_by_outcome_stratification`; the "e.g." names a condition the
  rule does not use.
- `descriptive.py`, "No row id, row index or numeric row value is a key or a value
  here": a `site` column reading `"1000"`..`"1029"` on 30 rows makes those thirty strings
  the `table1.test.site` keys (`n: 1` each). They are attribute level labels, which the
  same paragraph says do leave; the sentence's "numeric row value" reads as if they could
  not.

### N6 - four of the seventeen new tests pass at `b93e050`; the note says so for each

`test_the_equal_width_edges_are_arange_over_ten_and_not_linspace`,
`test_table1_and_missingness_keys_are_column_names_and_level_labels_and_nothing_per_row`,
`test_item17b_...` and the renamed 200/200 test pass at `b93e050`: the first two observe a
sentence the engine already satisfied, the last two are mutant-measured (the kills below
reproduce). The literal "48 mixed cases" in `test_brier_ref_is_fixed_when_...`'s docstring
is not asserted (the test asserts `>= 1`); I measured 48 at `default_rng(1)`.

## Could not break

- **Suite, worktree `a5a5ed8`, Git Bash:** `425 passed, 1 skipped, 1 xfailed in 54.58s`;
  `-m day6` `61 passed, 366 deselected`; `-m day5` `54 passed, 373 deselected`; `-m day1`
  `59 passed, 1 skipped`; `day2` `40`; `day3` `29, 1 xfailed`; `day4` `182` (the day-1..4
  counts equal the day-5 handoff's); `ruff check` `All checks passed!`; `ruff format
  --check` `64 files already formatted`; `doctor --offline` `All essential checks
  passed.`; the named acceptance test `1 passed`. **Main tree, PowerShell 5.1:** `425
  passed, 1 skipped, 1 xfailed in 44.86s`; `61`; `54`; `1 passed`; ruff both clean; doctor
  clean; `day1`..`day4` `59+1 / 40 / 29+1 / 182`. The day-5 handoff's three named sets in
  Git Bash: `27 passed`, `7 passed`, `7 passed`. Every command in the note's table ran in
  both shells and no command failed in either.
- **Fails pre-fix.** The three test files copied into the `b93e050` worktree: `16 failed,
  45 passed in 7.93s` (note: `16 failed, 45 passed in 7.57s`). First `E` line per test:
  census x2 `AssertionError: oe` / `assert {'positive': ...egative': 131} == {'all':
  200}`; slope oracle `assert {'positive': ...negative': 78} == {'all': 120}`; O:E test
  `assert (1.0885384107...) == (1.0510290021...)`; degenerate `assert 200 == 171`; 180-of-200
  `assert ({'positive': ...8, 'mixed': 1} == {'all': 21}`; prevalence `assert
  'boundary_estimate' == 'fixed_by_out...tratification'`; N = 1..9 (eight) `ValueError:
  zero-size array to reduction operation maximum which has no identity`; sentences
  `('calibration.py', 'overstates it in every resample')`. Every one is the assertion the
  note quotes, none an import abort.
- **Mutant-measured claims, named test only, worktree** (mutant planted from the sweep's
  own pattern, file restored, `git status` clean after): `oe_below_200_200_is_not_computed`
  on the renamed 200/200 test `3 failed, 2 passed`, `E AssertionError: assert ('none' ==
  'log_delta'`; `curve_flag_rides_on_the_companion_not_the_number` on the census test `2
  failed`, `assert 'boundary_estimate' == 'clustered_da...ic_ci_invalid'`;
  `clustered_route_class_units_guard_dropped` on the 180-of-200 test `1 failed`, `E
  AssertionError: oe` / `assert None == 'insufficient_clusters'` (so with the guard gone
  the O:E renders on that input - the `_clustered_cell` docstring's counter-example);
  `difference_frozen_sides_at_the_default_level` `1 failed, 3 passed`, `assert () ==
  ('a',)`; `difference_bounds_at_the_default_level` `1 failed, 3 passed`, `assert
  (0.7089624999...) == (0.7164249999...)`.
- **Sweep:** `python scripts/mutation_sweep.py --marker day6`: `30 planted, 30 killed, 0
  survived; 139 s` (Git Bash) / `136 s` (PowerShell), worktree.
- **Coverage:** `coverage_calibration.py --full` at seed 2026 and `--seed 7`, worktree, Git
  Bash: all twenty-four clustered cells equal the note's table (seed 2026: O:E 0.920 /
  0.943 / 0.903, intercept-in-the-large 0.920 / 0.943 / 0.897, slope 0.940 / 0.943 /
  0.933, joint intercept 0.903 / 0.927 / 0.917; seed 7: 0.937 / 0.960 / 0.937, 0.927 /
  0.957 / 0.930, 0.937 / 0.940 / 0.920, 0.923 / 0.953 / 0.940); the i.i.d. cells equal lens
  1's figures (O:E 0.960 / 0.967 / 0.940, intercept-in-the-large 0.930 / 0.953 / 0.913,
  slope 0.950 / 0.953 / 0.960); elapsed 154 s / 154 s. The seed-2026 run repeated in
  PowerShell: identical output bar the elapsed line (151 s).
- **F4 and the fixture.** CSV body regenerated from the header's recipe: byte-identical.
  `f4_expected.json` re-run (statsmodels 0.15.0, scikit-learn 1.9.0, numpy 2.5.1): offset
  `fit(tol=1e-10)` estimate / SE / deviance 0.0 / 0.0 / 0.0, 4 iterations; default fit 0.0
  / 0.0, 4 iterations, SEs 0.0 apart; joint tight 0.0 on all five, 6 iterations; default 0.0
  on all four, 5 iterations; tight-vs-default SEs 9.13e-6 / 1.99e-5 apart; sklearn Brier
  0.0; hand O:E, log-delta SE, bounds, Brier, reference, IPA, ECE (10, 5, mass) all 0.0.
  Engine: intercept-in-the-large SE 2.19e-9 from the tight fit; joint SEs 3.30e-10 /
  7.21e-10 from the tight fit and 1.11e-16 / 1.11e-16 from `fit(method='newton',
  tol=1e-12)`, 7 iterations - every figure in the two rewritten notes.
- **Independent flat case bootstrap on a fresh cohort** (70 three-row cases, mixed,
  `default_rng(11)`, B = 150, seed 3; every case drawn with equal probability from the
  cell's own generator, all rows kept): O:E bounds 0.0 / 0.0 from the rendered, 37
  distinct values of `O`; intercept-in-the-large 1.1e-16 / 2.8e-17 against statsmodels
  `newton` refits; slope 0.0 / 0.0; joint intercept 1.1e-16 / 0.0; Brier bounds 0.0 / 0.0
  against the module's within-class resampler (`units_per_stratum {positive: 7,
  negative: 17, mixed: 46}`).
- **Single-class draws are `nan` on every route:** 40 one-row cases, 2 events, `p ~ U(0.05,
  0.3)`, B = 200: O:E `usable 171` = draws holding an event case (171),
  intercept-in-the-large `164 = 164`, slope `175` and joint intercept `176` against 176 /
  180 draws with an event (the shortfall is non-converged joint fits on one-event draws,
  the docstring's second `nan` case); all four `degenerate_resamples`.
- **Prevalence rule on other shapes:** positive cases of size 2, negative of size 1, mixed
  (1, 2) only -> `fixed_by_outcome_stratification`; pure positive cases of sizes 1 and 2
  -> bootstrapped with `lo < hi`; mixed (1, 1) beside (1, 2) -> bootstrapped, IPA with an
  interval.
- **Lens 1's blockers, its own one-liners at `a5a5ed8`:** B1 prints `1.0096 1.3674 1.0275
  1.328 cluster_bootstrap_percentile` (was `1.0911 1.2709`); B2 N = 0..14 every one a
  block, JSON without NaN; B3 `brier_ref` `fixed_by_outcome_stratification`; B4 the ECE
  reason string is the new one. Lens 1's constructions: all scores 0.5 -> `constant_score`,
  intercept-in-the-large with an interval, Brier `boundary_estimate`, ECE 0; `y == (p >
  0.5)` -> `complete_separation`, offset `irls_wald`; single class both ways ->
  `single_class` on all seven; one case holding 72 of 80 rows -> `insufficient_clusters` on
  all six; declared clustering without ids raises; NaN / inf / 1.2 / -0.2 raise
  `ValueError`; 0 / 1 / 5e-324 clipped (3); 200/199 and 199/200 flagged, 200/200 not; the
  95-row tie cohort bins `[10 x 5, 9 x 5]`.
- **Nothing weakened.** `git diff --name-status b93e050 a5a5ed8 -- tests/`: three `M`, no
  `D`; against `4eb44f3`: four `A`. No `skip` / `xfail` / `.only` / `TODO` / `FIXME` added, no
  `pytest.mark` removed. `git diff b93e050 a5a5ed8 -- bootstrap.py subgroups.py cli.py
  io/ schema/ pyproject.toml`: 0 bytes; `git diff 4eb44f3 a5a5ed8 -- bootstrap.py cli.py
  io/mapping.py`: 0 bytes, so `MIN_UNITS_PER_STRATUM 2`, `MAX_FROZEN_VARIANCE_SHARE
  0.20`, `LOW/VERY_LOW_PRECISION_UNITS 10/30`, `FEW_EVENTS 5`, `MIN_USABLE_FRACTION 0.90`,
  `DEFAULT_B 2000` are as they were; `cli.py` imports nothing from `proofpack.stats`;
  `number.py` is a comment change only, so no enum moved and the enum-agreement test's
  scope is unchanged. The schema is untouched; the ten dumped blocks (with
  `class_units_guard` under `bootstrap.resampling`) validate against `calibrationBlock`
  with 0 errors.
- **scipy-free import:** with `scipy` and `scipy.stats` set to `None` in `sys.modules`,
  `import proofpack, proofpack.stats, proofpack.stats.calibration,
  proofpack.stats.descriptive` succeeds and no `scipy` module is loaded afterwards.
- **In-place flag appends:** the only `self.flags.append` in `src/` is
  `Number.with_precision_flags` (`number.py:245-250`); `calibration.py` has none.
- **Line endings:** `git ls-files --eol` in the main tree: `i/lf w/lf` on all ten files
  the note lists (the note's claim); the worktree checkouts are `w/crlf` and the fixture
  reader tolerated it (the F4 tests pass there).
- **Commit:** `fix E: ...`, ends `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`;
  not pushed (`a5a5ed8 [main]`, no upstream mark).

## Could not check

- The R `rms::val.prob` capture (`[pending]`, day 9) and the Debray 2017 attribution
  (`[unverified]`); not fetched.
- Coverage of the clustered decile-bin intervals (DEC-18 (a), not built) and of the Brier
  / IPA cells under the clustered plan (the script measures neither; the note says so).
- The seed-7 coverage run in PowerShell (seed 2026 only was repeated there).
- The note's 152 s "byte-identical bar the elapsed line" re-run after the guard landed -
  its earlier output is not on disk; what I compared is Git Bash against PowerShell now.

## Sentences I refused to write

- "The prevalence rule is exact" - N1 is the counter-example; stated as sufficient.
- "The clustered calibration intervals meet DEC-08" - twenty-three of twenty-four measured
  cells at or above 0.90 and one at 0.897, on one process, three shapes, two seeds.
- "The i.i.d. route is unchanged" - N2: the companion's flags changed in every bin below
  200/200 on the ten cohorts compared.
- "Every new test pins the repair" - four pass at `b93e050`; two of those are pinned by
  mutants I re-planted, two observe sentences.
- "The flat resampler makes ``O`` vary" - N5's first bullet.

Worktrees removed at the end (`git worktree list` shows none under
`lens-E6-r2-regression`). Probe scripts stay in
`scratchpad/lens-E6-r2-regression/probe/` (`f4_oracle.py`, `plant.py`,
`attack_clustered.py`, `attack_prev.py`, `dump_blocks.py`, `lens1_recheck.py`, the two
block dumps and the coverage JSON / text outputs).
