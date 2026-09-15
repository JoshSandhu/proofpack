# Verify (build day 5, round 1) — 2026-09-15 — Lane E — **REGRESSION-AND-RECORD LENS**

Repo `proofpack`. Commit under review `d1fd20a` ("E5: stats.subgroups - per-level metrics,
differences, fairness gaps, heterogeneity footnote"); pre-build `3ea2bfd`. Builder's note:
scratchpad `notes/E5_build.md`. Everything below was executed in detached worktrees at
`d1fd20a` and `3ea2bfd` with `PYTHONPATH=<worktree>/src` forced and proved
(`proofpack.__file__` resolved inside each worktree before any number was trusted).

**Verdict: FAIL — 1 blocker, 9 non-blocking.**

Every figure in the note is true: the suite (352 / 1 / 1), the day markers (42; 59 / 40 / 29 /
182), lint, doctor, the mutation sweep (21 / 21 / 0), the `--quick` timing and — re-run in
full, 781 s, in both shells — every one of the 60 coverage cells in `design/conventions_T7.md`
byte-for-byte. Every frozen fixture value (F6, F8, F14 ×3, the frozen `diff_vs_complement`
case) re-derives from the published formula without repo code to the stated precision. The
F18 injection counts (49 / 19 / 43 of 50) re-measure exactly. Nothing was skipped, xfailed
or deleted.

The blocker is what the tests do **not** pin. I planted fifteen behavioural mutants of my own
beside the builder's twenty-one; **thirteen survived the `day5` marker**, and three of
them — PPV, NPV and accuracy each computed as `1 - x` — survive the **entire suite at once**
(`352 passed`). Three of the six proportion metrics in every subgroup row of a
regulator-facing table have no value test. The sweep's "21 killed, 0 survived" is true of
the builder's list and is not evidence about these.

---

## Blocker

### B1 — PPV, NPV and accuracy per level are unpinned: inverting all three leaves the whole suite green

**Evidence.** In the `d1fd20a` worktree I edited `_conditioned` in
`src/proofpack/stats/subgroups.py` so that `ppv` uses `ind = ~pos[sel]`, `npv` uses
`ind = pos[sel]` and `accuracy` uses `ind = pos != pred`, then ran the full suite:

```
352 passed, 1 skipped, 1 xfailed in 53.07s
```

Each alone also survives `-m day5` (my sweep below: `L_ppv_inverted`, `L_npv_inverted`,
`L_accuracy_inverted`, all `SURVIVED`). The values are **right today** — I checked the F and
M rows of a 400-row `make_cohort` against numpy on the raw columns and every deviation was
`0.0` — so this is a pinning gap, not a wrong number. But `test_two_by_two_counts_per_level_sum_to_the_level_and_selection_rate_is_the_called_share`
checks only `selection_rate`; `test_fairness_gaps_are_the_reference_differences...` checks
`ppv_gap == d["ppv"]` (an identity, not a value); nothing compares a per-level PPV, NPV or
accuracy to an oracle. The note's item 1 says "complement est checked by hand against numpy
on the raw columns" — that is the sensitivity difference only.

**Repro (one line, from the worktree root with `PYTHONPATH=src`):**
`python -c "import re,pathlib;p=pathlib.Path('src/proofpack/stats/subgroups.py');p.write_text(p.read_text().replace('ind = pos == pred','ind = pos != pred'))" && python -m pytest -q -p no:cacheprovider -m day5`
→ `42 passed`.

**What closes it.** A test that computes PPV, NPV and accuracy per level from the raw columns
with numpy (as the sensitivity check already does) and compares `est`, `k` and `n`; and the
three mutants added to `scripts/mutation_sweep.py` so the DEC-12(ii) sweep inspects them.
The other ten survivors below (N1) should be closed or carried by name in the same repair.

---

## Non-blocking

### N1 — Ten further behavioural mutants survive `-m day5`

My sweep (`probe/extra_mutants.py`, driven through the builder's own
`scripts/mutation_sweep.py` machinery so the copy-and-`PYTHONPATH` discipline is the same):
16 planted (one a no-op control), 3 killed, 13 survived, 247 s. Beyond B1's three:

| mutant | what it changes | note's own claim it contradicts |
|---|---|---|
| `L_unknown_in_homogeneity` | the Unknown row enters the chi-square / Fisher family | decision 12: "the Unknown row is left out of the homogeneity test" |
| `L_brier_single_class_not_refused` | a single-class level's Brier is bootstrapped instead of refused `single_class` | decision 9 |
| `L_clustered_auroc_diff_sign` | clustered AUROC difference computed as other minus level | no sign pin on the clustered route (the i.i.d. sign is pinned by F18) |
| `L_clustered_prop_diff_no_tier` | clustered proportion difference loses its tier flags | "tiers ... in resampling units" |
| `L_event_units_are_rows` | `event_units` counted in rows, not cases, under clustering | `test_tiers_count_resampling_units_not_rows_under_clustering` pins `n_units` only |
| `L_orientation_ignored` | `lower_is_positive` scores not negated for AUROC | the module docstring's "oriented so higher = positive" |
| `L_brier_clustered_uses_iid_resampler` | Brier under clustering resamples rows | "the plain mean squared error with a percentile bootstrap interval through the day-4 resampler (stratified by outcome, or clustered)" |
| `L_n_cases_max` | `n_cases` on a clustered difference is the larger side | — |
| `L_two_sided_bootstrap_same_draw` | side b of the two-sided bootstrap drawn from `default_rng(b)`, not the cell's generator | see N2 |

I verified by direct numpy / inspection that decisions 9 and 12, the orientation handling
and the clustered Brier resampler are **correct today** (single-class Brier → `single_class`
with `est` carried; clustered Brier → `cluster_bootstrap_percentile` with
`resampling.kind == "clustered"`; `lower_is_positive` AUROC deviation from
`roc_auc_score` on the negated score `0.0`). They are unpinned, not wrong. Killed: the
selection-rate inversion, the H09 halt on a declared Unknown reference, and
`prespecified` forced true.

### N2 — A test name asserts a property the test does not inspect (hard rule)

`test_the_two_sided_bootstrap_draws_each_side_independently_and_is_seeded_by_the_cell_key`
inspects determinism (two runs equal) and seed sensitivity (seed 99 moves the bounds, not
the estimate). It does not inspect independence of the two sides: with side b drawn from
`np.random.default_rng(b)` inside the loop (`L_two_sided_bootstrap_same_draw`) it still
passes. Rename to what it inspects, or add an assertion that a side-b-only change moves
the interval.

### N3 — DEC-08's refusal rule is not implemented, and "Nothing was cut" is not accurate

DEC-08: a cell "is refused with a typed reason below [0.90]". The builder measured, found
no value of `MIN_UNITS_PER_STRATUM` on the grid satisfies it, kept 2, and escalated
(needs-from-Josh 1). That escalation is honest and the T7 paragraph carries the table.
But a shape the builder's own run puts at **0.672** coverage renders today: I built a
clustered sensitivity cell of 10 cases × 1 row at 9/10 and got
`0.9 (0.7, 1.0) cluster_bootstrap_percentile ['wilson_refused_clustered',
'very_low_precision', 'imprecise']` — rendered, annotated, not refused. The note's first
headline, "Every item in the brief landed (1–7). Nothing was cut", should say that DEC-08's
refusal-below-the-bar is not implemented pending Josh's decision. Recorded here so the
open item is visible in the ledger, not only in the needs-from-Josh list.

### N4 — The `MAX_FROZEN_VARIANCE_SHARE = 0.20` margin is one Monte-Carlo standard error

Full run, N = 120, share 0.20: **0.915** (bar 0.90, MC error ≈ 0.015). The `--quick` run
(R = 100, MC error ≈ 0.03) puts the same shape at **0.870**. Both are consistent with a
true coverage near 0.90. The docstring's "every measured shape this constant lets through
covers at or above the bar" is true of the R = 400 point estimates and says "measurement,
not a guarantee"; the margin should be stated in `conventions_T7.md` beside the 0.915.

### N5 — The no-verdict grep does not cover the brief's phrase "well calibrated"

`VERDICT_WORDS` in `tests/test_subgroups.py` contains neither `well` nor `calibrated`
(nor `passes`). Counter-example run: the test's own tokeniser on the strings
`"well calibrated"` and `"model is well-calibrated"` → `flagged=False`. Nothing in
today's output carries the phrase; the pin the brief asks for is partial.

### N6 — Hard-rule sentence in `scripts/mutation_sweep.py` without a recorded counter-example

Docstring: "the script asserts that `proofpack` resolves there before any mutant runs, so
an editable install of the real tree **cannot** be what the tests import." The check
inspects one `python -c "import proofpack"` subprocess in the copy. I tried to defeat it
(PYTHONPATH pre-set to the main tree's `src`; cwd set to the main tree) and both still
resolved to the copy — the sentence held, but the note records no such attempt. Name what
the check inspects.

### N7 — The note's "cannot reach Wilson by a forgotten argument" — counter-examples run, none broke it

I tried: (i) clustering declared with no `case_id` column →
`ValueError: clustering.unit is 'case_id' but no case_id column was supplied`;
(ii) a `ClusterPlan(clustered=False)` supplied over a repeating case column →
`ValueError ... contradicts` (pinned by `test_a_supplied_plan_that_contradicts_the_case_column_is_refused`);
(iii) `cluster_ids` omitted with a repeating column under `clustering.unit: none` → route
`detected`, every proportion `cluster_bootstrap_percentile`. The sentence stands; the
note should record which attempts were made.

### N8 — Documentation inconsistencies

- `scripts/coverage_bar.py` docstring: `--quick  # ~2-5 minutes`. Measured: **38.7 s** in
  PowerShell, 39 s in Git Bash; the note and `conventions_T7.md` say ≈ 40 s.
- Statistic-bearing helpers `_brier_cell`, `_auroc_cell`, `_level_row`,
  `_attribute_block` have no docstring; the formula and oracle for Brier live only in the
  module docstring and the test. `unpaired_delong`, `holm`, `_homogeneity_test` and
  `band_ages` do name their oracle or formula.
- Commit subject `E5: ...` departs from the repo's `day4 E: ...` / `day3 E: ...` style.

### N9 — `test_no_module_level_scipy_import_in_subgroups` is a source grep

With a stub `subgroups.py` planted at `3ea2bfd` it passed (the stub had no scipy line);
against the real `3ea2bfd` it errors on a missing file. It pins the file's text, not
behaviour; the behavioural pin is `test_the_module_imports_and_the_footnote_degrades_with_scipy_hidden`,
which I also ran outside pytest with scipy blocked before any import: `import proofpack`,
`import proofpack.stats`, `import proofpack.stats.subgroups` all succeed and
`_homogeneity_test` returns `scipy_unavailable`. Keep both; know which is which.

---

## What I could not break

**Suite and commands, both shells.** Git Bash and PowerShell 5.1, worktree at `d1fd20a`:

```
python -m pytest -q -p no:cacheprovider           352 passed, 1 skipped, 1 xfailed   (40.88 s bash / 43.37 s ps)
python -m pytest -q -p no:cacheprovider -m day5   42 passed, 312 deselected           (15.10 s / 15.26 s)
-m day1 / day2 / day3 / day4                      59+1 skipped / 40 / 29+1 xfailed / 182   (both shells; = repair-r7)
python -m ruff check .                            All checks passed!
python -m ruff format --check .                   48 files already formatted
python -m proofpack.cli doctor --offline          All essential checks passed.
python scripts/mutation_sweep.py --marker day5    21 planted, 21 killed, 0 survived; 210 s  (note: 194 s; CPU shared)
python scripts/coverage_bar.py --quick            39 s bash / 38.7 s ps; table shape reproduced
python scripts/coverage_bar.py --full             781 s in each shell; the two outputs byte-identical
```

At `3ea2bfd`: `310 passed, 1 skipped, 1 xfailed`, `All checks passed!`, `43 files already
formatted` — exactly the note's pre-build figures. 352 − 310 = 42 = the day-5 tests.

**Fails pre-build.** `tests/test_subgroups.py` copied into the `3ea2bfd` worktree: one
collection error (`ImportError: cannot import name 'subgroups'`). With a stub module
planted so collection succeeds: 35 failed, 1 passed (N9), 6 errors (the module-scoped
`reports` fixture). The tests that do not need the module fail on their own assertion:
`FISHER_EXPECTED_BELOW == 5.0` (line 237), `DEFAULT_AGE_BANDS == (...)` (695),
`AUROC_EVALUABLE_CLASS == 10` (800), and
`{"cases_span_both_groups", "insufficient_levels"} <= NOT_ESTIMABLE_REASONS` (1227).
This is a build round, so import-abort failures are acceptable; recorded for the record.

**Nothing weakened.** `git diff --name-status 3ea2bfd d1fd20a -- tests/` → `A tests/test_subgroups.py`
only. The diff adds no `skip`, `xfail`, `.only`, `TODO` and removes no `pytest.mark` line;
the only `only` hit is the sweep's `--only` flag. `pyproject.toml`, `conftest.py` and CI are
untouched; `slow` is not deselected anywhere, so F18 runs in CI. `fixture` and `slow` are
declared markers.

**Frozen values, re-derived without repo code** (`probe/rederive.py`, formulae written out):

| fixture | my derivation | note / fixture | test and precision |
|---|---|---|---|
| F6 Pearson χ² on [[45,5],[38,12],[27,3]], p = e^(−χ²/2) | 4.6327, 0.0986 | 4.6327, 0.0986 | `test_f6_chi_square_...`, `approx4` (5e-5), also vs `chi2_contingency` |
| F6 Fisher [[45,5],[38,12]] (hypergeometric sum) | 0.1084 | 0.1084 | `test_f6_fisher_exact_...`, 5e-5, also vs `fisher_exact` |
| F6 Holm [0.012, 0.04, 0.30] | [0.036, 0.08, 0.30] | same | `test_f6_holm_...`, 5e-5, plus 100 random sets vs statsmodels at 1e-12 |
| F14 Table II 56/70 vs 48/80 | (0.0524, 0.3339) | (0.0524, 0.3339) | dev 3.2e-5 / 2.7e-5; test asserts 5e-5 |
| F14 Table II 9/10 vs 3/10 | (0.1705, 0.8090) | (0.1705, 0.809) | dev 2.3e-5 / 1.8e-5 |
| F14 Table II 10/10 vs 0/20 | (0.6791, 1.0000) | (0.6791, 1.0) | dev 1.4e-5 / 0 |
| F14 frozen complement 30/40 vs 100/120 | −0.0833 (−0.2453, 0.0493) | same | `F14_COMPLEMENT_FROZEN`, 5e-5 |
| F8 Wilson half-width p=0.9, n=50/100/300 | 0.0851 / 0.0596 / 0.0341 | same | `test_f8_...`, 5e-5 |

The F14 test's docstring carries the fixture's `[unverified against the primary PDF]`
verbatim and the helper asserts the fixture's `provenance.status` string is unchanged.

**Unpaired DeLong.** My own placement-value implementation (DeLong 1988 `V10`/`V01`
components, `S10/m + S01/n`) on 20 random cohorts with ties injected by rounding: max
absolute deviation from `unpaired_delong` across est, variance, both bounds and p =
**2.1e-15**; AUCs equal `roc_auc_score` to 1e-12.

**F18 re-measured** (seeds 20260915–20260964, n = 5,000, B = 200): B excludes 0 in
**49/50**, A and C cover 0 in **19/50** each and cover their true +0.0292 in **49/50**, B
covers −0.06 in **43/50** — the note's figures exactly.

**Coverage bar.** Full run reproduces all 60 cells of `conventions_T7.md` and the
constants' docstrings (`MIN_UNITS_PER_STRATUM = 2`, `MAX_FROZEN_VARIANCE_SHARE = 0.20`
in `bootstrap.py` equal the values the conventions file records). Quick-run deviations
from the full run on the share row (N=30 / N=120): +0.048/−0.058, −0.083/−0.005,
−0.032/−0.045, −0.013/+0.007, −0.007/+0.007, −0.013/+0.010 — within 3 MC standard errors
of a R=100 run; the feasibility block ends `None` in both, as the note says.

**Schema.** Lines removed from `output_schema_v1.json` are only the loose placeholders
(`subgroups: array of object`, `fairness: object|null`) and the enum lists that were
re-emitted longer; `additionalProperties: false` and `required` were added, none removed.
`test_the_enums_added_today_agree_between_code_and_schema` pins the enums to the code's
frozensets; the plant-a-`status` and plant-a-`diff_vs_overall` tests reject as claimed.

**Number invariant.** Every serialised Number in the three report shapes re-validates
through `Number(**d)` and carries a CI or a reason in `NOT_ESTIMABLE_REASONS`
(`test_every_number_in_the_output_has_a_ci_or_a_typed_reason`); difference Numbers carry
`n = min(n1, n2)` on both routes, consistent with `difference_unpaired`.

## What I could not check

- pROC `roc.test(paired = FALSE)` for the unpaired DeLong difference — no R capture exists;
  the builder marks it `[unverified]` and so do I.
- Newcombe 1998 Table II against the primary PDF — `[unverified]` stands.
- The `--full` timing of 743 s: mine was 781 s with two runs sharing the CPU; the numbers,
  not the seconds, are what the table records.
- Whether Josh accepts option (a), (b) or (c) for DEC-08 — a decision, not a check.

## Sentences I refused to write

- "The day-5 suite pins the subgroup table" — it does not pin PPV, NPV or accuracy (B1).
- "The mutation sweep shows the tests have teeth" — it shows the 21 declared mutants die.
- "The DEC-08 bar is met by 0.20" — 0.915 at one MC standard error above it (N4).
- "The scipy-hidden test proves the package imports without scipy" — it proves
  `subgroups.py` does; the rest of the package was already in `sys.modules`. My separate
  cold run with scipy blocked before any import is the evidence for the package.

Worktrees `lens-E5-r1-regression/new` and `/old` removed after this note was written; the
main tree was left clean apart from this file.
