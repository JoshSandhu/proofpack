# Lane E - build day 11 (E11) - lens 1, regression-and-record, at `2adfaaa` (base `ad66073`; Friday 2 October 2026)

**FAIL. Two blockers.** **B1:** item 2 moved the ledger increment after the write, and a writer that raises part-way now leaves documents on disk that were never counted: with a read-only `T8.html` in `--out`, `run --templates T1,T7,T8` exits 5 with `T1.html` and `T7.html` freshly written and `run.json` saying `ledger_count 2`, and `ledger.json` stays at `1`. At `ad66073` the same probe leaves `ledger.json` at `2`. DEC-47 counts "every run with a criteria list that wrote a document". **B2:** item 5's route rule (`wilson_deff` at five cases or more) renders intervals whose coverage I measured far below the DEC-08 bar when case sizes are unequal. The engine's own `proportion_ci` gives coverage `0.364` on one 40-row case plus nine one-row cases at p = 0.5, against `0.917` from the cluster bootstrap at `ad66073` on the same draws. The shipped T7 page sentence says the interval is "printed for a cell of at least five cases, where its measured coverage is at or above the 0.90 bar". That is a statistical gate, and no counter-example to the sentence was run before it shipped.

Everything else I re-measured reproduces the note exactly, in both shells:
- Full suite `1953 passed, 1 skipped, 1 xfailed` (Git Bash 232.16 s, PowerShell 237.14 s).
- Markers: `-m day11` `99`, `day10` `262`, `day9` `337`, `day8` `471`, `ap3` `176`, `ap2` `91`, `ap4` `194` (the note quotes no ap4 figure).
- `ruff` clean, `284 files already formatted`.
- The day-11 sweep: `43 planted, 43 killed, 0 survived` (Git Bash 657 s, PowerShell 658 s).
- The day-10 sweep: `37 / 37` (Git Bash 1383 s).
- Sample-pack sizes and F17: identical to the note's.
- Fixtures line, capture check, `tr39`, `doctor`: identical to the note's.
- The coverage run regenerates `design/coverage_deff_wilson.json` identically, `True`, in both shells.
- The five goldens regenerate byte-identically (LF).
- Every "At ad66073" figure the note quotes reproduces.
- The Newcombe fetch record matches what the three URLs return now: 302, 403, and a 139,150-byte PDF with the recorded SHA-256. My own method-10 code matches all 35 compared limits.
- Each of the 19 day-6 observers fails alone on its own named mutant.

The non-blocking records follow. Two are sentence violations: a docstring makes a false claim about `ad66073`, and N2 covers further copy of the B2 class. The others are a DOCX test that no CI job runs, incomplete cross-lane and carried lists, and the item-5 tests failing only at import at `ad66073`.

Setup: detached worktrees `scratchpad/lens-E11-r1-regression/tip` (`2adfaaa`), `base` (`ad66073`) and `mut` (`2adfaaa`, for planted mutants and probes, reverted after each). `PYTHONPATH=<wt>/src` was set on every call and checked: `proofpack.__file__` printed the worktree's own `src\proofpack\__init__.py` in both shells. `PROOFPACK_REQUIRE_DOCX=1` was set on every suite run. Nothing was committed, and the main tree carries only this note. All figures below are mine, measured on 2 October 2026; sweeps ran beside other jobs, so timings are contended.

## Blockers

### B1 - A run that wrote documents and then hit a writer error is not counted (DEC-47); its documents carry a count the ledger never recorded

**Repro (one line):** copy `scratchpad/lens-E11-r1-regression/probes/test_lens_probe_ledger2.py` into `tests/` of a `2adfaaa` worktree, then run `PYTHONPATH=<wt>/src python -m pytest -rA tests/test_lens_probe_ledger2.py`. The probe does the following:
1. Uses `_home`, `_inputs`, `_run` from `test_e11_ledger.py` / `test_e10_compare_cli.py`.
2. Runs once (ledger `{key: 1}`).
3. Pre-creates `r2/T8.html` with `os.chmod(S_IREAD)`.
4. Runs `run --templates T1,T7,T8 --offline` into `r2`.

**Evidence at `2adfaaa`:**
- `rc 5 files ['T1.html', 'T7.html', 'T8.html', 'ingest_report.json', 'pseudonyms.json', 'run.json']` (T8.html is the pre-existing read-only file).
- `ledger [1] run.json ledger_count 2`.
- stderr `internal error: PermissionError: [Errno 13] Permission denied: '...\r2\T8.html'`.

**Same probe at `ad66073`:** `rc 5 ...`, `ledger [2] run.json ledger_count 2`.

The note's own planted case shows the same thing. `tests/test_e11_ledger.py::test_the_count_is_recorded_after_the_write` patches `write_t8` to raise, and under the default templates `T1.html` and `T7.html` are written first. With the patch reproduced (`test_lens_probe_ledger.py`), the output is `rc 5 files ['T1.html', 'T7.html', 'ingest_report.json', 'pseudonyms.json', 'run.json']`, `ledger after r2 {key: 1}`, `run.json manifest.ledger_count 2 ledger.acceptance_runs 2`. The test asserts only that `T8.html` is absent and that the ledger is unchanged. It never looks at the two documents that were written.

**Why it blocks:**
- DEC-47 counts every run with criteria "that wrote a document". This run wrote two.
- The miss undercounts, which is the direction that suppresses `W14`.
- Two packs now carry the same `ledger_count` (the next run prints 2 again).
- The trigger is ordinary on Windows: a read-only file, or a `T8.docx` held open in Word.
- `cmd_run` and `cmd_compare` reach `record_ledger(outcome, documents)` only when `write_documents` returns, so the same holds for `compare`.

Decision 1 of the note ("A raise in a writer leaves the ledger unchanged") states the behaviour but treats it as the intended reading of "recorded after the write". DEC-47's sentence has both halves, and the partial write satisfies the first.

**Fix shape (the repairer's call):** commit when any document reached disk (for example, `write_documents` returns what it wrote before the raise, and the CLI commits in a `finally`). Add a regression test that fails at `2adfaaa` on `ledger [1]`.

### B2 - `wilson_deff` renders on five cases or more whatever the case sizes; on unequal case sizes its coverage is far below the bar, and the page says the opposite

The route (`bootstrap.proportion_ci`, `de.n_cases >= MIN_CASES_DEFF_WILSON`) depends on the case count only. The coverage grid that set the constant has equal case sizes only (`coverage_bar.py` docstring; `conventions_T7.md`; the note's carried E11-5).

**Literal measurement 1, the engine's own `proportion_ci`.** R = 1000 draws per shape, seed 11, the coverage script's process (`prop_cohort`'s latent model, TAU2 = 0.5, threshold at `1 - p`), run once against each worktree:

| shape (rows per case) | p | `ad66073` (`cluster_bootstrap_percentile`; a refusal counts as not covered) | `2adfaaa` (`wilson_deff` on all 1000) |
|---|---|---|---|
| 40, 1 x 9 (10 cases) | 0.5 | 0.917 | **0.364** |
| 40, 1 x 9 | 0.9 | 0.728 (143 refused) | 0.833 |
| 16, 1, 1, 1, 1 (5 cases) | 0.5 | 0.932 | **0.651** |
| 16, 1, 1, 1, 1 | 0.9 | 0.552 (316 refused) | 0.861 |
| 30, 2, 2, 2, 2 (5 cases) | 0.5 | 0.860 | **0.561** |
| 30, 2, 2, 2, 2 | 0.9 | 0.652 (214 refused) | 0.842 |

**Literal measurement 2, a separate run.** `design_effect` + `proportion_deff` directly, R = 4000, seed 20261003:

| shape | p = 0.5 | p = 0.9 |
|---|---|---|
| 16, 1, 1, 1, 1 | 0.650 | 0.866 |
| 8, 8, 1, 1, 1 | 0.811 | 0.952 |
| 30, 2, 2, 2, 2 | 0.570 | 0.847 |
| 20, 1 x 5 | 0.546 | 0.854 |
| 40, 1 x 9 | 0.367 | 0.839 |

**One literal draw.** A 40-row case with 20 of 40 successes, plus nine one-row cases all successes, renders as:
- `wilson_deff 0.5918 [0.4275, 0.7379]`, n 49, n_cases 10.
- Flags `wilson_refused_clustered, very_low_precision, imprecise`.
- `detail.design_effect` `deff 1.4075, n_eff 34.81, reason deff_estimated, route wilson_deff`.

On this shape the row proportion is dominated by the one big case, and the ratio estimator's residual for that case is near zero by construction.

**Sentences that assert what the route delivers, each refuted by the runs above:**
- `src/proofpack/render/t7.py` `METHOD_DESCRIPTIONS["wilson_deff"]`, printed on every T7 that has a `wilson_deff` cell: "printed for a cell of at least five cases, where its measured coverage is at or above the 0.90 bar (section 6)". Section 6 itself carries "equal case sizes only ... not a guarantee"; this sentence does not.
- `src/proofpack/stats/proportions.py` module docstring: "routes it, from the measured case count at which its coverage clears the DEC-08 bar".

The note's own refused list contains the unqualified form of this sentence ("covers at 0.90 or above" without "on the grid's shapes (equal case sizes, ...)"). It shipped in page copy anyway.

DEC-08: a cell "renders with its tier annotation when the engine's own coverage simulation for that shape is >= 0.90, and is refused with a typed reason below it". These shapes were never simulated, and they render. Item 5 is already owed its DEC-12 (i) lens. This is its first input.

## Non-blocking records

| # | Record | Evidence |
|---|---|---|
| N1 | **Sentence (false record), `src/proofpack/render/t1.py::template_name` docstring:** "at ad66073 the header, the `<title>` and the cover's `<h1>` printed the name with no qualifier". At `ad66073` the `<title>` reads `T1 · ProofPack v0.1.0.dev1 · run test-onl`, and every `page-header` reads `synthetic-classifier v1.3 · T1 · ProofPack v0.1.0.dev1 · run test-onl`. Neither names AI-DSF. Only the `<h1>` did, at golden line 135. The note itself says so ("the HTML page header line and `<title>` ... no name at either commit"). Write: "at ad66073 the cover's `<h1>` printed the name with no qualifier". | `grep -o "<title>[^<]*</title>"` and `grep -n "ProofPack v0.1.0" ` on both goldens |
| N2 | **The B2 class in page copy.** Two further places carry it: `METHOD_PHRASES["wilson_deff"]` ("Wilson score on the design-effect sample size n / DEFF") and the `conventions_T7.md` table paragraph "Every shape with five or more cases covered at or above the bar (lowest 0.906)". Both are qualified later in the same paragraph by "equal case sizes only" and "a measurement on the grid's shapes, not a guarantee". Recorded so the B2 repair reads them together. | `git diff ad66073 2adfaaa -- design/conventions_T7.md` |
| N3 | **The new DOCX qualifier scan runs in no CI job.** `tests/test_e11_aidsf_header.py:149` uses a bare `@pytest.mark.skipif(not extra_available(), ...)`. That ignores `PROOFPACK_REQUIRE_DOCX`. Every other DOCX test uses `ap4_docx.needs_extra`, which refuses the skip under the variable; `grep "extra_available()" tests/` shows this line as the only bare use. The tests carry `day11` only. CI's main job is "written without the extra" (`ci.yml`), so they skip there. The `docx-extra` job runs `-m ap4` only, so they are not selected there. Measured with `docx`, `docxtpl` and `matplotlib` set to `None` in `sys.modules` and `PROOFPACK_REQUIRE_DOCX=1`: `7 passed, 3 skipped` (`SKIPPED [3] ... the [docx] extra is not installed`). `--collect-only -m ap4 tests/test_e11_aidsf_header.py` gives `no tests collected (10 deselected)`. **Mitigation, measured:** a DOCX-only mutant (`ctx["template_name"] = T1_TITLE` in `render/docx.py::docx_context`) is killed by `-m ap4` (`2 failed, 192 passed`; `test_ap4_docx.py::test_the_docx_context_is_the_html_context_with_readings_added_beside_html_only_keys`). So the T1 title loss is caught in CI, but the T7/T8 DOCX scans are not run there. Fix: `needs_extra` plus the `ap4` mark. | `scratchpad/lens-E11-r1-regression/hide_docx.py` |
| N4 | **`changes_for_other_lanes` (DEC-43) is incomplete** against `cli.py`, `run.py` and the schemas. Not listed: (a) **`schema/egress_schema.json` changed** (method enum gains `wilson_deff`). The site vendors that file (`proofpack-site/src/data/egress_schema.json`) and its CI requires the egress table to equal the engine's, so the pin move must re-vendor it. (b) `ledger.json`'s compare entries change key (no `compare:` prefix; old entries ignored). (c) `comparison.ledger.prior_acceptance_runs` changes meaning (prior comparisons -> stored runs, compares included). (d) `manifest.ledger_count` / `ledger.acceptance_runs` of a run that wrote no document is now the stored count. (e) A new printed summary line `[W15] ...` when the ledger cannot be written after the documents. (f) `proofpack fixtures` summary now `matched 34 ... no independent oracle 0`, and the T12 row F5-newcombe-paired changes status. (g) T2 cells gain `data-mcnemar` / `data-facet` attributes. | `git diff ad66073 2adfaaa -- schema/ src/proofpack/cli.py src/proofpack/run.py src/proofpack/io/ledger.py`; Grep of `proofpack-site/src` (read only) |
| N5 | **The note's "Nothing was cut" omits E10's Tomorrow-needs item 6** (`handoffs/2026-09-25_E.md` line 177): "the day-8 and day-9 sweeps in both shells (row 106); a wheel in a fresh venv ...; rows 123-125's tests". The E11 note neither lands nor carries row 106, nor rows 123-125. Rows 123-125 are three non-equivalent surviving mutants with no test (`2026-09-24_E9_r3.md` lines 42-44). The note also does not carry E10's "no browser or print check of T2" (`2026-09-25_E.md` line 36). The wheel half is covered: `test_wheel_fixtures` builds a wheel into a fresh venv in the suite and asserts `matched == 33`; it passed in both of my full runs. | the two handoffs, by line |
| N6 | **Item 5's tests cannot fail on an assertion at `ad66073`.** `tests/test_e11_deff_wilson.py` aborts at collection there (`ImportError: cannot import name 'MIN_CASES_DEFF_WILSON'`), and the note's row 5 quotes no `ad66073` figure. Measured stand-in: at `2adfaaa` with the route switched off (`de.n_cases >= 10**9`, so every clustered proportion takes the bootstrap as at `ad66073`), `3 failed, 7 passed`. The three are `::test_deff_one_reproduces_the_plain_wilson_interval_exactly`, `::test_the_route_switches_at_the_measured_case_count` and `::test_accept_no_rendered_clustered_proportion_below_the_bar_without_its_tier`; the other seven test the new functions directly. No test feeds unequal case sizes to the route (B2). Likewise `tests/test_sweep_day11.py` fails at `ad66073` (`2 failed`) only because the list does not exist. | `scratchpad/lens-E11-r1-regression/base_*.txt` |
| N7 | **Tests that pass at `ad66073` (pin nothing by commit).** Measured, all as the note says: `test_e11_aidsf_header` 7 of 10 (the T2/T7/T8/T12 goldens, the T7/T8 DOCX, the scanner self-test); `test_e11_day6_observers` 19 of 20 (only item 1 fails); `test_e11_mcnemar` 6 of 12 (the hand counts, the three statsmodels oracles, the two row-147 placement tests); `test_e11_merge_blockers` 4 of 23 (`json_html_..._still_writes_t2`, `t2_t8_names_t8_only[True-json,docx-...]`, two `compare_next_step_never_names_t2_docx` cases). Each observer is pinned by mutant instead. I planted each `e11_obsNN` mutant and ran only `test_itemNN_*` alone: all 19 gave `1 failed` (rc 1), so every observer kills its own mutant and not just the marker. | `scratchpad/lens-E11-r1-regression/obs_check.py` |
| N8 | **Newcombe: the marks came off on 35 of 36 printed limits, against DEC-70 (a)'s "only on a match".** The note discloses this (decision 7, need 46), and `citations.yaml` / the fixture say `verified` on that basis. My reading of the same PDF agrees: page 5 prints method 10 with only "if eh > fg", and page 7 prints `0)8737` (method 8) and `0)8736` (method 10) on `1 97 1 1`. My own implementation (written here, not the repo's) gives `0.873672` there and matches all 35 compared limits at four decimals. A symmetric correction (`min(eh - fg + n/2, 0)` when `eh < fg`) gives `0.881410`, so it is not the paper's either. Josh's call, as need 46 asks. | `scratchpad/lens-E11-r1-regression/p5.txt`, `p78.txt` |
| N9 | **DEC-08 below five cases (need 47).** Cells of two to four cases still render the cluster bootstrap with `not_evaluable_shown_for_transparency`, where DEC-08's letter refuses below the bar once DEC-18 (c)'s "until it lands" has passed. The brief's Accept line ("no rendered clustered cell below the bar without its tier annotation") permits it. Disclosed; recorded so the B2 repair decides both together. | `design/coverage_deff_wilson.json` (u = 2: 0.793; u = 3: 0.845; u = 4: 0.867 / 0.878) |

## What I could not break (re-measured)

**Suite, markers, lint.** All in worktree `tip`, `PROOFPACK_REQUIRE_DOCX=1`:
- Full suite: Git Bash `1953 passed, 1 skipped, 1 xfailed in 232.16s`; PowerShell `1953 passed, 1 skipped, 1 xfailed in 237.14s`. The skip is `test_doctor_cli.py:57`; the xfail is F13 pROC.
- Markers, Git Bash then PowerShell:
  - `-m day11` `99 passed, 1856 deselected` (27.18 s / 24.16 s)
  - `day10` `262`
  - `day9` `337`
  - `day8` `471`
  - `ap3` `176`
  - `ap2` `91`
  - `ap4` `194`
- `ruff check .` `All checks passed!`; `ruff format --check .` `284 files already formatted`. Both shells.
- `day11` is in `pyproject.toml` beside `day10`. CI's day-marker loop reads every `day\d+` from there, so `day11` is gated without a CI edit.

**Nothing weakened.**
- `git diff --name-status ad66073 2adfaaa`: 0 `D`.
- Test functions renamed (not removed):
  - `..._twenty_in_pp_unverified...` -> `..._21_...`
  - `..._cluster_bootstrap_groups_...` -> `..._clustered_interval_groups_...`
  - `..._through_the_cluster_bootstrap` -> `..._through_the_clustered_route`
  - `test_assemble_run_writes_only_the_ledger_file_under_home` -> `..._writes_nothing_and_the_ledger_after_the_documents`
- Suite growth 1854 -> 1953 = 99 = the `day11` count.
- Added marks: nine `pytestmark = pytest.mark.day11`, one `@pytest.mark.day11` and one `skipif` (N3).
- Removed: no marker, no `skip` and no `xfail`.
- The B2 churn of `test_criteria` / `test_run_cli` changes the S3 bound 0.89 -> 0.80. The end-to-end cell's `ci_lo` (0.8299) is now below `max_lower_bound_at_n(30)` (`0.8864866`), so those two tests no longer build the met-yet-unattainable contradiction. That case is still built by `tests/test_criteria.py::test_a_cluster_bootstrap_cell_gets_no_attainability_flag` (hand Number `ci_lo 0.9`, n 30), unchanged.

**"Fails pre-build"** (new test files copied into `base`):

| file | failed | passed | errors | note's figure |
|---|---|---|---|---|
| `aidsf_header` | 3 | 7 | | 3 FAILED |
| `day6_observers` | 1 | 19 | | 18 + item 1 + the count test |
| `ledger` | 12 | | | 12 FAILED |
| `mcnemar` | 6 | 6 | | 6 of 12 |
| `merge_blockers` | 19 | 4 | | 19 of 23 |
| `newcombe` | 2 | | 3 | 2 FAILED, 3 errors |
| `reason_codes` | 4 | | | 4 FAILED |

Each matches the note's figure. Item 0's three:
- B1: the four hidden-module `compare --format docx` cases fail, and the help test fails.
- B2: `test_ap4_roundtrip.py::test_t1_criteria_cells_with_a_paired_subgroup_criterion_equal_the_html_in_the_docx` fails on `assert missing == []` (`C_pd_sub (row 9) → not assessable (difference against the prior version); ...`).
- B3: fourteen next-step cases fail.

**The note's commands, both shells, at `2adfaaa`:**
- `doctor --offline`: exit 0, 17 `[ok`, `All essential checks passed.`
- `fixtures --offline`: exit 0, `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`; `unverified` 37 in the report.
- `capture_fixture_oracles.py --check`: `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`, exit 0.
- `tr39_subset.py ../workflows/data/confusables-18.0.0.txt --check` (from the main tree, read only) and with the absolute path in both shells: `vendored subset matches`, exit 0.
- `mutation_sweep.py --list`: 411 lines.
- `build_sample_pack.py --compare`: exit 0; sizes `236,843 / 142,983 / 48,056 / 35,178 / 329,347 / 69,922`; `SYNTHETIC - illustrative` 8 and `NO LICENCE - not for submission` 7 on T2.
- The same pack at `ad66073`: `236,843 / 142,924 / 47,666 / 35,178 / 328,965 / 69,017`. The deltas are +0 / +59 / +390 / +0 / +382 / +905, which is the note's line.
- F17 `--n 400 --compare`: `run exit codes [4, 4]; identical under the mask ['run_id', 'started', 'duration_s']: yes`, exit 0. `MASKED_KEYS` is exactly those three, and `scripts/f17_determinism.py` is unchanged since `ad66073`.
- `coverage_bar.py --deff-wilson --json`: threshold 5 in 10 s (Git Bash) and 9 s (PowerShell); the JSON equals the committed file as a whole (`True` both).
- Timing test: `23.29 s; 0.03 s; T2 74188 bytes` (Git Bash), `25.74 s; 0.03 s; 74188 bytes` (PowerShell).
- The one command that failed was mine: a mistyped relative path to `confusables`, in both shells. The note's command is correct.

**Goldens.** With `PROOFPACK_REGEN_GOLDEN=1 -k golden` in `mut`, `git diff --stat` is empty and `cmp` against `HEAD` (LF) is identical for T1, T2, T7, T8 and T12. The golden changes in the diff, read word by word, are exactly the following:
- The T1 h1 qualifier.
- T12's F5-newcombe-paired row and counts (33 -> 34, 1 -> 0).
- T2's Se/Sp cells `5 / 1`, `0.219 (exact)`, the caption and the ledger sentences.
- T7's `rao_scott_1992` open item and section-6 heading.

**Schema.** The diff adds `wilson_deff` (both method enums), `no_score_column`, `metric_not_compared` and `comparisonBlock.mcnemar_by_metric` (newly required), and rewrites two descriptions. It removes nothing. The new required key is the one non-additive change for an old `compare.json`; the note names it.

**Statistical-gate hunks** (`git diff --name-status ad66073 2adfaaa -- src/proofpack/stats/`: `bootstrap.py`, `comparison.py`, `number.py`, `proportions.py`):
- `bootstrap.py`: the `wilson_deff` route.
- `proportions.py`: `design_effect`, `wilson_effective_bounds`, `proportion_deff`.
- `comparison.py`: `_mcnemar_by_metric` and `no_score_column`.
- `number.py`: two enum values.

The note and commits `83ceec0` / `efacffe` name items 3 and 5 as statistical-gate changes owed DEC-12 (i), and every hunk falls under items 3, 5 or 8.

**Arithmetic re-derived without repo code:**
- The literal design-effect table:
  - Cases of 3 rows with 2, 1, 3, 0 successes give `sum (y_i - p m_i)^2 = 5`.
  - `v = 4/3 * 5/144 = 5/108`, against `p(1-p)/n = 1/48`.
  - So DEFF `20/9` and n_eff `5.4`, the note's figures.
- McNemar, Se/Sp `b 5 c 1`: exact p `2 * 7/64 = 0.21875`.
- McNemar, accuracy `10 / 2`: `2 * 79/4096 = 0.0386`, printed `0.039`.
- Newcombe method 10 on `(80, 2, 10, 8)`: `[-0.155356, -0.010249]`, the frozen `[-0.1554, -0.0102]`.

**Sweeps, at `2adfaaa`:**
- Day-11 sweep, Git Bash: `43 planted, 43 killed, 0 survived; 657 s`, exit 0.
- Day-11 sweep, PowerShell: `43 planted, 43 killed, 0 survived; 658 s`, exit 0.
- Day-10 sweep, Git Bash: `37 planted, 37 killed, 0 survived; 1383 s`, exit 0. Its last line is `killed ap4_extra_missing_branch_raises`, re-pointed at `cli._docx_extra_missing`.

All three reproduce the note. Commit `2adfaaa`'s message reports the earlier full run at `108ce34` (42) plus the two boundary mutants alone; the note's 43-run at `2adfaaa` is the figure I reproduced. No mutant in the list feeds unequal case sizes (B2).

## What I could not check

- The note's PowerShell day-10 sweep figure (`37 / 37; 1304 s`): not re-run in PowerShell (about 23 minutes per shell). The Git Bash run above reproduces the count.
- Whether a human reading of Newcombe's page 7 agrees with the machine extraction (I also read it by `pypdf`, not by eye).
- The engine's cluster-bootstrap coverage on unequal case sizes beyond the three shapes above, and `wilson_deff` coverage at TAU2 other than 0.5. Those belong to the DEC-12 (i) lens.
- Site-side effects of N4 (a): I read the site's vendored schema and CI comment only. I did not run the site's checks (lane S's tree today).
