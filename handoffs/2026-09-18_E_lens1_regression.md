# Lens 1 (regression and record) - build day 6, lane E, `b93e050` - 2026-09-18

**Verdict: FAIL.** Three blockers. The suite figures, the oracle values, the fixture, the
mutation sweep and the untouched files all check out exactly as the note records them;
what fails is three sentences the diff ships or the note asserts, each falsified here by a
constructed input that was run: (B1) `calibration_block` raises a numpy traceback for any
cohort of 1 to 9 analysed rows, where the module docstring says an empty bin "is
`zero_denominator`, never dropped"; (B2) the engine string `ci_not_computed_because`,
written into the customer's output JSON, says the bootstrap ECE "overstates it in every
resample" and 371 of 1000 outcome-stratified resamples on `make_cohort(300)` sit below the
point estimate; (B3) on a clustered cohort of two rows per case with mixed-outcome cases
the reference Brier is refused as `boundary_estimate` - the reason the note's decision 11
says it avoids - and the docstring's "whose cases mix outcomes the prevalence does vary"
is false on that input.

Worktrees: `b93e050` and `4eb44f3` under
`scratchpad/lens-E6-r1-regression/`, `PYTHONPATH=<worktree>/src` proved by
`python -c "import proofpack;print(proofpack.__file__)"` printing each worktree's own
`src/proofpack/__init__.py` before any figure below. Both removed at the end. The main
tree was read only; it is clean at `b93e050`.

## Blockers

### B1 - `calibration_block` raises for 1 <= N <= 9; the docstring says the empty bin is typed

`src/proofpack/stats/calibration.py:820`:

```
mass_edges = [float(p[b].min()) for b in mass_bins if b.shape[0]] + (
    [float(p[mass_bins[-1]].max())] if n else []
)
```

guards `n == 0` only. With 1 to 9 rows `numpy.array_split` leaves the last equal-mass bin
empty and `.max()` on it raises `ValueError: zero-size array to reduction operation maximum
which has no identity` before `_decile_curve` runs. Line 75 of the same file:
"A bin that receives no rows (``N < 10``) is ``zero_denominator``, never dropped."

Repro (worktree, PYTHONPATH forced):
`python -c "import sys,numpy as np;sys.path.insert(0,'tests');from conftest import make_criteria;from proofpack.io.declare import validate_dict;from proofpack.stats.calibration import calibration_block;p=np.random.default_rng(9).uniform(0.1,0.9,9);calibration_block(p,np.arange(9)%2==0,validate_dict(make_criteria()))"`

Measured: N = 1..9 each raise; N = 10..14 return a block. Ingestion has no minimum-row HALT
beyond "no rows" (`io/schema.py` S04), so `calibration_from_table` reaches this on any
analysed cohort below ten rows. No day-6 test feeds N < 10 (the smallest is
`cohort_arrays(n=25)`); a 400-cohort fuzz (N drawn from 1..39, five score shapes) hit it 95
times and nothing else. A regression test at N = 9 (ten bins, the last with `n: 0` and
`zero_denominator`) fails at `b93e050` on this traceback.

### B2 - a shipped engine string asserts a statistical fact that is false

`calibration.py:206-210`, `_ECE_CI_WHY`, serialised into every present block as
`ece_equal_width_10.ci_not_computed_because` and `ece_equal_mass_10.ci_not_computed_because`:
"the percentile bootstrap of a binned absolute deviation overstates it in every resample".
The same sentence is in the module docstring (line 116) and the note's decision 7.

Counter-example run: the ECE recomputed on 1000 draws of the module's own
`stratified_by_outcome` resampler (seed 0), with the module's `ece` and binning:

| input | scheme | point | resamples below the point | bootstrap mean |
|---|---|---|---|---|
| `make_cohort(300)` | equal-width | 0.1519 | **371 / 1000** | 0.1576 |
| `make_cohort(300)` | equal-mass | 0.1372 | 252 / 1000 | 0.1469 |
| F4 | equal-width | 0.1955 | 175 / 1000 | 0.2473 |
| F4 | equal-mass | 0.1955 | 149 / 1000 | 0.2537 |

The bootstrap mean is above the point estimate on all four (the upward bias the sentence
is reaching for is real); "in every resample" is not. This text leaves the engine in the
output JSON, so it is the kind of sentence the hard rule exists for. The decision itself
(no ECE interval, `not_computed_this_run`, reason stated) is sound; the reason's wording is
what must change - state what was inspected (no coverage run exists) and, if the bias is
named, name it as a bias of the mean, with the figures above or none.

### B3 - the reference Brier under two-row mixed cases is refused with the reason the note says it avoids

`_prevalence_invariant` (`calibration.py:589-592`) returns `False` whenever a `mixed`
stratum exists, so the reference Brier is bootstrapped. But `clustered_by_case` resamples
within strata, and when every case has two rows every mixed case contributes exactly one
event and one non-event: the prevalence is identical in every draw, the percentile
interval has zero width, and the rendered Number is `boundary_estimate` with no interval.
Decision 11 in the note: "carries the typed reason `fixed_by_outcome_stratification`
rather than a `boundary_estimate` that would misdescribe the cause; under a clustered plan
whose case sizes differ or whose cases mix outcomes it is bootstrapped
(`_prevalence_invariant` decides, exactly)". Module docstring line 87-89: "under a
clustered plan whose case sizes differ or whose cases mix outcomes the prevalence does
vary and the reference Brier is bootstrapped with everything else."

Measured (declared clustering, 100 cases, `BootstrapPolicy(n_resamples=100, seed=2)`):

| rows per case | seed | mixed cases | `_prevalence_invariant` | distinct prevalences in 100 draws | `brier_ref` rendered |
|---|---|---|---|---|---|
| 2 | 1 | 48 | False | **1** | `none`, `boundary_estimate`, no CI |
| 2 | 7 | 44 | False | **1** | `none`, `boundary_estimate`, no CI |
| 3 | 1 | 72 | False | 20 | `cluster_bootstrap_percentile`, (0.2487, 0.2500) |

Two rows per case is the ordinary paired-reading design, so this is the common clustered
shape, not a corner. The typed reason is a valid enum value (no silent fallback), but it
is the wrong one by the note's own account. The right test of invariance is whether every
unit within each stratum carries the same per-class row counts - the resampler already
exposes `class_unit_rows` - not "no mixed stratum". A mutant that drops the `mixed` half of
`_prevalence_invariant` (`all(s.matrix is not None ...)`) survives `-m day6` (45 passed),
so the branch the sentence describes is not observed by any test either.

## Non-blocking

### N1 - carried item 17 is not closed as the day-5 note defined it

The day-5 handoff, table item 17, named two survivors: `percentile_bounds(usable,
DEFAULT_LEVEL)` in day-4 `bootstrap_percentile`, and `_frozen_sides(..., DEFAULT_LEVEL)`.
`tests/test_subgroups_carried.py:15` says item 17 "kills `percentile_bounds(usable,
DEFAULT_LEVEL)`" and the note's row 8 counts item 17 as closed. Planted at `b93e050`, run
`tests/test_subgroups_carried.py`:

| mutant | site | result |
|---|---|---|
| `percentile_bounds(usable, DEFAULT_LEVEL)` | `bootstrap.py:941` (`bootstrap_percentile`) | killed - `test_item17` fails on `('0-40', 'sensitivity')` width assertion |
| `percentile_bounds(usable, DEFAULT_LEVEL)` | `subgroups.py:524` (`_bootstrap_difference`) | **survives** (3 passed) |
| `_frozen_sides({...}, DEFAULT_LEVEL)` | `subgroups.py:523` | **survives** (3 passed) |
| `percentile_bounds(finite, 0.5)` | `subgroups.py:464` | killed - `test_item19` |
| `values_a - values_b.mean()` | `subgroups.py:517` | killed - `test_item16` |
| `values_a.mean() - values_b` | `subgroups.py:517` | killed - `test_item16` |

`test_item17`'s difference check asserts `d95.ci_lo <= d90.ci_lo and d90.ci_hi <= d95.ci_hi`
(not strict) and reads `ci_level` from the field, which is set from the argument, so a
difference rendered at 0.95 and labelled 0.9 passes it. Unreachable today (no declarable
level), as the day-5 note said. Items 16, 18 and 19 are closed as claimed.

### N2 - the three carried-item tests pass at `4eb44f3`

Expected for observer tests (they pin mutants, not the diff), and the note says so; recorded
because the task asks. `test_calibration.py` and `test_descriptive.py` fail at `4eb44f3` on
`ModuleNotFoundError` at import (a build round, not a repair round - acceptable).

### N3 - `test_the_200_200_annotation_is_strict_on_both_sides_and_never_suppresses` does not itself observe an interval suppression

Mutant: in `_oe_cell`, return `_unavailable(ctx, key, "not_computed_this_run", est=est)` when
events or non-events are below 200. The named test passes (it checks `est is not None` and
ten bins); the mutant is killed elsewhere (`test_f4_oe_...` on `KeyError: 'k'`,
`test_an_n25_cohort_...` on the missing tier flag) - `2 failed, 43 passed`. "Never suppresses"
in a test name generalises past what the test inspects.

### N4 - fixture note in the wrong object

`fixtures/f4_expected.json` puts `default_fit_note` ("stops one IRLS iteration earlier and
reports the Wald SE from the penultimate iteration's weights") under
`statsmodels_glm_binomial_offset`, where the default and `tol=1e-10` fits are identical to
the last digit (`default_fit_se == se == 0.5536866236677364`). The sentence is true of the
joint fit (default 5 iterations, tight 6; SE 1.99e-5 / 9.13e-6 apart, as the note says).

### N5 - private helpers without docstrings

`_oe_cell`, `_decile_curve`, `_ece_entry`, `_expit`, `_deviance`, `_fit_offset`, `_fit_joint`,
`_cell_key`, `_unavailable`, `_cell_dict`, `_equal_width_rows` (calibration) and
`_attribute_labels`, `_missing_mask` (descriptive) carry none. Every public function and
the module docstrings name their oracle or formula.

### N6 - one docstring sentence with no test, held on my construction

"A resample on which the IRLS does not converge is `nan` to the resampler and counted
against `MIN_USABLE_FRACTION`": no test observes it (`test_the_clustered_slope_interval...`
asserts `usable_resamples == 60`). On 40 two-row cases, `p = linspace(0.02, 0.98)`, labels
`p > 0.5` with two crossing cases, B = 200: slope `usable 172` -> `degenerate_resamples`,
intercept `usable 182` with an interval, offset intercept `usable 200`; `json.dumps(...,
allow_nan=False)` clean. Holds; untested.

### N7 - schema: `calibration` and `calibration_suppressed_reason` are not top-level `required`

A document that omits both validates. Pre-existing for `calibration`; the assembled-document
test asserts presence, so it is observed there. Not a loosening: the diff only tightens
(`table1`, `calibration`, `missingness` from bare object/null to `oneOf` fragments with
`additionalProperties: false`).

## Could not break

- **Suite counts, both shells.** Worktree Git Bash: `409 passed, 1 skipped, 1 xfailed`;
  `-m day6` `45 passed, 366 deselected`; `-m day5` `54 passed, 357 deselected`; `-m day1`
  `59 passed, 1 skipped`; `-m day2` `40`; `-m day3` `29, 1 xfailed`; `-m day4` `182` (the four
  day-1..4 counts equal the day-5 handoff's). Main tree PowerShell 5.1: `409 passed, 1
  skipped, 1 xfailed in 60.14s`; `-m day6` `45 passed`; `-m day5` `54 passed`; the named
  acceptance test `1 passed`; `ruff check` `All checks passed!`; `ruff format --check` `61
  files already formatted`; `doctor --offline` `All essential checks passed.` Collected:
  `test_calibration.py` 34, `test_descriptive.py` 8, `test_subgroups_carried.py` 3.
- **Nothing weakened.** `git diff --name-status 4eb44f3 b93e050 -- tests/`: four `A`, no
  `D`/`M`. The diff adds no `skip`, `xfail`, `.only`, `TODO`/`FIXME` (the one grep hit is the
  sweep's `args.only` variable) and removes no `pytest.mark`.
- **Untouched files.** `git diff 4eb44f3 b93e050 -- src/proofpack/stats/bootstrap.py
  src/proofpack/cli.py src/proofpack/io/mapping.py`: 0 bytes, so the two DEC-08 constants
  and every day-4/5 threshold are as they were and `cmd_run`/`cmd_map` are lane A's.
  `number.py` is additions only (+6 reasons, +4 flags). `subgroups.py` not in the diff.
- **F4 fixture.** CSV body regenerated from the recipe in its header comment (`y` list, `p =
  i/100 for i in 5..95 step 5, then 0.99`) is byte-identical to the committed body; R2
  section 9 line 205 quotes the same vectors and figures. `git ls-files --eol`: `i/lf
  w/crlf` on all ten new/changed files.
- **Every recorded oracle value, re-run here** (statsmodels 0.15.0, scikit-learn 1.9.0, numpy
  2.5.1): offset GLM `tol=1e-10` est/SE/deviance deviation `0.0/0.0/0.0`; joint GLM
  `tol=1e-10` intercept/slope/SE_int/SE_slope/deviance `0.0` each; default fits `0.0` each
  against the recorded `default_fit_*`; sklearn Brier `0.0`; hand O:E `0.0`, log-delta SE
  `0.0`, bounds `0.0 / 2.2e-16`; reference Brier and IPA `0.0`; ECE equal-width 10 / 5 and
  equal-mass 10 `0.0`; left-closed edges give 0.2405 / 0.1645 as the note says. Every R2
  4-dp figure within 5e-5 of its recorded value (largest: O:E, 4.7e-5).
- **Engine against those oracles.** Intercept-in-the-large `2.2e-16`, its SE `2.19e-9`, 4
  iterations; slope `0.0`, intercept `1.7e-16`, SEs `7.21e-10 / 3.30e-10`, 7 iterations;
  Brier `0.0`; IPA `0.33852083333333327` with (`-0.0290`, `0.6148`) at B = 200; ECE 0.1955
  / 0.1955 - the note's figures to the digit. Hand Wilson on the ten decile bins of
  `make_cohort(300)`: largest deviation `1.1e-16`.
- **Mutation sweep.** `--marker day6`: `20 planted, 20 killed, 0 survived` in Git Bash (91 s)
  and PowerShell (95 s), from the worktree. `--marker day5`: see the line below.
- **scipy-free import.** With `scipy` and `scipy.stats` set to `None` in `sys.modules`,
  `import proofpack, proofpack.stats, proofpack.stats.calibration` succeeds; the only
  `scipy` token in `calibration.py`/`descriptive.py` is docstring line 134.
- **Schema diff** is a pure tightening (above). Assembled documents (i.i.d., declared,
  detected, logit-suppressed) validate with 0 errors inside the suite.
- **Verdict grep.** `VERDICT_WORDS` contains `calibrated` and `miscalibrated`; the day-6 twin
  walks every key and engine string of the four documents.

Day-5 mutation sweep, Git Bash, worktree: `34 planted, 34 killed, 0 survived; 483 s`
(run concurrently with other work; the note's 440 s is a timing, not compared).

## Could not check

- The R `rms::val.prob` capture (`r_rms_val_prob: [pending]`) - day 9, no R here.
- The Debray 2017 attribution - marked `[unverified]` in the diff; not fetched.
- Coverage of the clustered decile-bin intervals against the DEC-08 bar - DEC-18 (a) is
  not built and the note says so.
- Timing figures (46 s / 81 s / 440 s) are not reproducible byte-for-byte and were not
  compared.

## Sentences I refused to write

- "The day-6 tests cover N < 10" - they do not (B1).
- "The ECE bootstrap is biased upward on every input" - measured on two inputs, two
  schemes; stated as those four figures only.
- "Item 17 is closed" - one of its two named survivors survives (N1).
