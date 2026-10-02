# Lane E - build day 11 (E11) - lens 2, regression-and-record, at `0fa9391` (repair 1; base `2adfaaa`; Friday 2 October 2026)

**FAIL. One blocker.** **B1:** the repair note marks FA-B1 and RG-B2 "fixed", and both still reproduce. `wilson_deff` still prints with no tier annotation on clustered cells of 30 or more cases whose coverage I measured well below the DEC-08 bar. That includes shapes at the process the repair uses to set its threshold (TAU2 0.5, truth 0.9). Five cases of 50 rows beside 25 one-row cases (30 cases, n 275, largest share 0.182, inside every bound of `deff_wilson_route`) gave `wilson_deff` on 2000 of 2000 draws and coverage **0.7615**. 1203 of those cells carried no flag beyond `wilson_refused_clustered`. The same shape at 60 cases (6 x 50 + 54 x 1) gave **0.7885**. The committed v2 grid holds the second half of the class: 26 of its 162 printed rows at 30 cases or more fall below the bar, and FA-B1's own row (30 x 20, TAU2 0.8, truth 0.98) gave 0.8125 at the tip, again `wilson_deff` with no tier. The brief's Accept line reads "no rendered clustered cell below the bar without its tier annotation", and it fails on the engine's own committed simulation. The note's carried row E11r1-1 and need 49 frame the residual as "only at TAU2 0.8 or truth 0.95 / 0.98", which "the engine cannot see". The shapes above are at TAU2 0.5 and truth 0.9, and their case sizes are observable.

Everything else I re-measured reproduces the note exactly:
- Full suite, `PROOFPACK_REQUIRE_DOCX=1`: PowerShell `1964 passed, 1 skipped, 1 xfailed in 259.00s`. Git Bash gave `1963 passed, 2 skipped, 1 xfailed in 237.61s`. The extra skip is `test_e8_repair4.py:405` (the full `confusables.txt` is looked for beside the repository, and a worktree has none). With `PROOFPACK_TR39_FULL` set, that file gives `18 passed`.
- Markers, both shells: `day11` 110, `day10` 262, `day9` 337, `day8` 471 (Git Bash 470 + the same 1 skip), `ap3` 176, `ap2` 91, `ap4` 195.
- `ruff`: clean, `287 files already formatted`.
- The new tests fail at `2adfaaa` as the note quotes: `9 failed, 1 passed` for `test_e11_repair1.py`, the 4 unlicensed `merge_blockers` cases, and the `deff_wilson` import abort.
- The day-11 sweep: `50 planted, 50 killed, 0 survived`.
- Every CLI and script figure in the note's table, in both shells.
- The coverage JSON regenerates byte-identically.
- The five goldens regenerate identically.
- The Newcombe URLs return 302 / 403 / 200 with 139,150 bytes.
- Item 0's tests fail at `ad66073`.

Setup: detached worktrees under `scratchpad/lens-E11-r2-regression/`: `tip` (`0fa9391`), `base` (`2adfaaa`), `mut` (`0fa9391`, for probes, restored after each) and `ad` (`ad66073`). Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`, in Git Bash and in PowerShell. `PROOFPACK_REQUIRE_DOCX=1` and `PYTHONIOENCODING=utf-8` were set on every suite run. I committed and pushed nothing. This note is the only file I wrote outside the scratchpad. Every figure below is mine, measured on 2 October 2026, with other jobs running on the machine, so timings are contended.

## Blocker

### B1 - The FA-B1 / RG-B2 class still prints `wilson_deff` with no tier annotation below the bar at 30 cases or more, including at the threshold-setting process. The note calls both blockers fixed

**Repro (one line):** `PYTHONPATH=<tip>/src python scratchpad/lens-E11-r2-regression/probe/cov_bound.py 2000`. The probe calls the engine's own `plan_clustering` + `proportion_ci`, as lens-1 FA's `cov_engine.py` did. Its process is a latent `b_i + e_ij` with Var(b) = TAU2, case sizes fixed, truth p, success when the latent is below `Phi^-1(p)`.

**Evidence at `0fa9391`.** Each shape below is inside the new bounds: at least 5 cases, largest share at or below 0.20, at most 50 rows per case on average. TAU2 is 0.5 throughout except the last row. Every row printed `wilson_deff` on every draw, with `route wilson_deff`.

| shape (rows per case) | K | n | largest share | truth | R | coverage | cells with no flag but `wilson_refused_clustered` |
|---|---|---|---|---|---|---|---|
| 50 x 5, 1 x 25 | 30 | 275 | 0.182 | 0.9 | 2000 | **0.7615** | 1203 |
| the same, second seed | 30 | 275 | 0.182 | 0.9 | 4000 | **0.7710** | 2405 |
| 50 x 5, 1 x 25 | 30 | 275 | 0.182 | 0.5 | 2000 | 0.8640 | 72 |
| 40 x 6, 1 x 24 | 30 | 264 | 0.152 | 0.9 | 2000 | **0.7800** | 1233 |
| 50 x 5, 1 x 35 | 40 | 285 | 0.175 | 0.9 | 2000 | **0.7670** | 1228 |
| 50 x 5, 2 x 25 | 30 | 300 | 0.167 | 0.9 | 2000 | **0.7865** | 1285 |
| 20 x 10, 1 x 20 | 30 | 220 | 0.091 | 0.9 | 2000 | 0.8655 | 1394 |
| 50 x 6, 1 x 54 | 60 | 354 | 0.141 | 0.9 | 2000 | **0.7885** | 1342 |
| 50 x 8, 2 x 52 | 60 | 504 | 0.099 | 0.9 | 2000 | 0.8535 | 1531 |
| 20 x 30 (FA-B1's row), TAU2 0.8 | 30 | 600 | 0.033 | 0.98 | 2000 | **0.8125** | 2000 |

The remaining cells carry `imprecise`. That flag is the half-width test in `stats/number.py:266` (`hw > 0.10`), not an R2 tier. No cell carried `very_low_precision` or `not_evaluable_shown_for_transparency`, because `precision_flags` returns `[]` at 30 cases or more.

**Independent re-derivation.** `probe/indep.py` uses no repo code: the ratio-estimator design effect `K/(K-1) * sum (y_i - p m_i)^2 / n^2` over `p(1-p)/n`, floored at 1, with `sum m_i^2 / n` at p = 0 or 1, then Wilson on `n / DEFF`. On the same seeds and draws it gave `0.7615`, `0.8640` and `0.7865`, the engine's figures to four decimals.

**Reached through a run.** I assembled a run with `tests/assembler.assemble` from `make_cohort(n=275, with_case_id=True)`, with `case_id` set to the 50 x 5 + 1 x 25 shape and the clustering unit `case_id`. Its overall cells print as follows:
- `accuracy`: `wilson_deff 0.8291 [0.7724, 0.874]`, n 275, 30 cases, flags `['wilson_refused_clustered']`.
- `prevalence`: the same method and flags.

**At `ad66073`** the cluster bootstrap on the 50 x 5 + 1 x 25 shape gave 0.772 (truth 0.9) and 0.890 (truth 0.5), R = 1000 (`probe/cov_boot_ad.txt`). It too had no tier at 30 cases. So the remedy is not "revert". The cell needs the refusal or annotation that DEC-08 names, which is a decision.

**What the note and diff say:**
- The note says "**Both blockers are repaired**". Its table row reads "FA-B1 + RG-B2 (blockers, sentence) ... **fixed, one cause**".
- FA-B1's own rows 3-6 (30 x 20 at truth 0.98; 30 x 8 at 0.95, TAU2 0.8; mixed sizes at 0.95, TAU2 0.8) are the rows the note then carries as E11r1-1. FA-B1 graded them a blocker under "a clustered cell below 0.90 rendered without its tier annotation". The repair did not change them: 0.8125 measured here on the 30 x 20 row.
- RG-B2's headline reads "on unequal case sizes its coverage is far below the bar". The repair closed it only for **one** dominant case, which is the one family it added to the grid. Several large cases, each under a fifth of the rows, were never on the grid. The constant comment calls the 0.20 bound "Chosen, not measured", and the shapes above show it lets the class through.
- Carried row E11r1-1 / need 49 reads: "No observable gate measured here fixes it"; "The engine cannot see truth or TAU2". The rows above are at TAU2 0.5 and truth 0.9, the process that sets the threshold, and they differ from the grid only in case sizes, which the engine reads. So need 49 as written is not the whole residual.

**Why it blocks:**
- The day's Accept line fails. So does DEC-08 ("refused with a typed reason below it"), on the engine's own committed simulation (26 rows) and on in-bound shapes off it.
- The note's "fixed" disposition of two blockers is false.
- The gate is statistical, so DEC-12 (i) applies to whatever repair follows.

What the shipped sentences say is true as far as it is scoped, because each names "grid rows". Examples: T7 section 6, "At the process that sets the threshold, every printed row of 30 cases or more covered at or above the bar", and the constant comment. A reader of T7 is told the 26 recorded rows exist, but not that untested in-bound shapes at the process itself measure 0.76-0.79.

**Fix shape (not mine to choose):** Josh's need 49 widened to this evidence. Options are a refusal or a tier annotation for every clustered `wilson_deff` cell whose shape the grid did not measure, or a bound measured on several-large-case shapes (the grid needs a k-dominant family). Either way, the note's dispositions should read "partly fixed / carried", not "fixed".

## Non-blocking

| # | Record | Evidence |
|---|---|---|
| N1 | **One grid row prints as two different numbers on the same T7 page.** Row 932 (equal, 30 x 50, TAU2 0.8, truth 0.98, coverage `0.7635`) prints `0.763 (12)` in section 6's table and "lowest **0.764**" in the prose 11 lines below (`conventions_T7.md` lines 235 and 246). The same 0.764 appears in the `bootstrap.py` comment (line 284) and the note. The table is formatted from the JSON by `f"{:.3f}"` (0.7635 is stored as 0.76349999...). The prose figure was typed by hand. `test_t7_prints_the_committed_table` asserts the literal `"0.764"` is present, so the inconsistency is pinned rather than caught. | rendered T7 of `_clustered_run_cohort()`: `<td>30</td><td>0.907 (12)</td><td>0.882 (12)</td><td>0.848 (12)</td><td>0.763 (12)</td>` and the string `0.764` both present |
| N2 | **`pyproject.toml`'s `ap4` marker description is now false.** It reads "every ap4 test also carries day10". `tests/test_e11_repair1.py::test_compare_docx_note_for_t2_names_the_missing_docx_writer` carries `ap4` and `day11` only. `--collect-only -m "ap4 and not day10"` gives `1/1966 tests collected`. That is why `ap4` rose 194 -> 195 while `day10` stayed 262. Either add `day10` or reword the description. | the collect command, in `mut` |
| N3 | **E11r1-1 and need 49 omit the observable residual** (B1). Both should name the several-large-case shapes and the figures above, so that Josh's choice is made on the whole residual. | B1 table |
| N4 | **The note's `tr39` command depends on the working directory.** `python scripts/tr39_subset.py ../workflows/data/confusables-18.0.0.txt --check` exits 1 with `FileNotFoundError` when run from any worktree (measured in Git Bash from `tip`). From the main tree it prints `vendored subset matches` in both shells, and so does the absolute path. The note does not say which directory. | Git Bash, `tip` |
| N5 | **Carried E11r1-8 confirmed.** `tests/test_e11_deff_wilson.py` stops at collection at `2adfaaa` (`ImportError: cannot import name 'MAX_CASE_SHARE_DEFF_WILSON'`). The route regression is carried by `test_e11_repair1.py`, whose two route tests fail there on `assert 'wilson_deff' == 'cluster_bootstrap_percentile'`. | `base` run |

## What I could not break (re-measured)

**"Fails pre-build."** I copied the tip's `test_e11_repair1.py`, `test_e11_merge_blockers.py` and `test_e11_deff_wilson.py` into `base` (`2adfaaa`):
- `deff_wilson` aborts at collection (N5).
- `repair1` + `merge_blockers` give `13 failed, 20 passed`. The 9 `repair1` failures and the 4 `merge_blockers[*-False]` failures are the ones the note names.
- The first assertion lines are the note's, verbatim:
  - `{...: 1} == {...: 2}` (twice);
  - `{} == {...: 1}`;
  - `'wilson_deff' == 'cluster_bootstrap_percentile'` (twice);
  - `'where its m... at or above' not in ...`;
  - the Next-step list diff.
- The one `repair1` pass is the M19 pin, as the note says. The sweep's `e11r1_compare_ledger_before_the_write` mutant (M19's shape) was `killed`.
- No failure was an import abort apart from `deff_wilson`.

**Nothing weakened.**
- `git diff --name-status 2adfaaa 0fa9391`: 0 `D`.
- The only `skip`, `xfail`, `only`, `todo` or `pytest.mark` lines added are one `pytestmark = pytest.mark.day11`, one `parametrize` and one `ap4` mark.
- No marker was removed.
- `day11` is in `pyproject.toml` beside `day10`. CI's day loop reads every `day\d+` from that file (`ci.yml` lines 43-66), so no CI edit was needed.
- Test churn is as the note says: four tests rewritten and one added in `test_e11_deff_wilson.py`, one expectation in `test_e11_merge_blockers.py`. The eight test files the note says it restored with `git checkout` are absent from the diff.

**Statistical-gate hunks.** `git diff --name-status 2adfaaa 0fa9391 -- src/proofpack/stats/` lists `bootstrap.py` and `proportions.py`:
- `bootstrap.py` changes the route only: `deff_wilson_route`, two constants, two `DEFF_ROUTES` values, and the call in `proportion_ci`. The interval functions are untouched.
- `proportions.py` changes its docstring only.
- The commit message and the note both name this a statistical gate owed DEC-12 (i).
- The schema is unchanged in this diff (`git diff --stat 2adfaaa 0fa9391 -- schema/` is empty).

**RG-B1 (ledger), probed beyond the tests.** With `lxml` hidden (`sys.modules["lxml"] = None`), `run --format json,html,docx --templates T1,T7` printed `rc 5`, files `T1.html, ingest_report.json, pseudonyms.json, run.json`, and ledger `{key: 1}`. That is the `_docx_extra_missing` docstring's measured sentence, reproduced. All three writers (`write_t7`, `write_t8`, `write_t2`) and the DOCX writer render to bytes first and call `write_bytes` last. So a document reaches the list only after its writer returns, and I found no writer that leaves a finished document on disk and then raises.

**The note's commands, both shells, at `0fa9391`:**
- `doctor --offline`: exit 0, 17 `[ok`, `All essential checks passed.`
- `fixtures --offline`: exit 0, `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`.
- `capture_fixture_oracles.py --check`: `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`, exit 0.
- `tr39_subset.py --check`: `vendored subset matches` (see N4 on the working directory).
- `mutation_sweep.py --list`: 418 lines.
- `build_sample_pack.py --compare`: exit 0; `run.json` 236,843 / `T1` 142,983 / `T7` 48,056 / `T8` 35,178 / `compare.json` 329,347 / `T2` 69,922; on T2, `SYNTHETIC - illustrative` 8 and `NO LICENCE - not for submission` 7. Identical in both shells and to the note.
- `f17_determinism.py --n 400 --compare`: `run exit codes [4, 4]; identical under the mask ['run_id', 'started', 'duration_s']: yes`, exit 0. `MASKED_KEYS = ("run_id", "started", "duration_s")` (`scripts/f17_determinism.py:58`), and the file is not in this diff.
- `tests/test_e10_timing.py -s`: `compare --templates T2 23.07 s; T2 render 0.03 s; T2 74188 bytes` (Git Bash), `28.20 s; 0.04 s; 74188 bytes` (PowerShell), `1 passed`.
- `coverage_bar.py --deff-wilson --json OUT`: threshold 30. OUT equals `design/coverage_deff_wilson.json` (`identical True` in both shells; byte-identical after LF-normalising in Git Bash). 84 s in Git Bash, 124 s in PowerShell.
- `mutation_sweep.py --marker day11` (Git Bash): `50 planted, 50 killed, 0 survived; 717 s`, exit 0. All seven `e11r1_*` mutants were `killed`.
- `mutation_sweep.py --marker day11` (PowerShell): `50 planted, 50 killed, 0 survived; 836 s`, exit 0.
- `mutation_sweep.py --marker day10` (Git Bash): `37 planted, 37 killed, 0 survived; 1619 s`, exit 0. All three sweeps ran side by side, so their timings are contended.

**Committed coverage JSON, every figure the note and test quote.** I recomputed each from the file:
- 1000 rows: `wilson_deff` 472, `case_share_above_grid` 408, `below_coverage_bar` 120 (no row is `rows_per_case_above_grid`).
- Threshold-setting printed rows at 30 cases or more: lowest `0.90675`.
- Twelve below the bar, the largest case count 20, the lowest `0.80825`.
- Recorded printed rows at 30 cases or more: `162`, of which `26` are below the bar; lowest `0.7635`.
- Case-share rows: `408`, lowest `0.13725`.
- Case-share threshold-setting rows at 30 cases or more: 18 of 30 below the bar, lowest `0.582`.
- The one recorded row at truth 0.9 below the bar: mixed sizes, 30 cases, `0.88175`.

**Goldens.** `PROOFPACK_REGEN_GOLDEN=1 -k golden` in `mut` gave `6 passed`. Compared with `HEAD` after LF-normalising, T1, T2, T7, T8 and T12 are `same`; `git diff --stat` is empty (the `M` status is line endings only). The goldens carry no clustered cell, so the new T7 section 6 is not in them. I rendered it from `_clustered_run_cohort()` instead:
- It carries `26 of the 162`, `0.137`, `case_share_above_grid`, `Twelve printed rows` and the new method sentence.
- It does not carry `where its measured coverage is at or above`.

**Lens-1 records re-checked at the tip:**
- RG-N1: the `<title>` of the `ad66073` golden is `T1 · ProofPack v0.1.0.dev1 · run test-onl`, and `AI-DSF` occurs on its line 135 only, as the new `t1.template_name` docstring says.
- FA-N1: the new Next-step line is pinned by `test_run_templates_t2_without_a_compare_licence_names_the_licence_first[*]`, which fail at `2adfaaa`.
- FA-N4: the new T2.docx note is pinned by `test_compare_docx_note_for_t2_names_the_missing_docx_writer`, which fails at `2adfaaa`.

**Item 0 at `ad66073`.** I copied the tip's `test_e11_merge_blockers.py` and `test_ap4_roundtrip.py` into `ad`:
- B1: the four hidden-module `compare --format docx` cases and `test_compare_help_names_docx` fail.
- B2: `test_t1_criteria_cells_with_a_paired_subgroup_criterion_equal_the_html_in_the_docx` fails.
- B3: the Next-step cases fail.
- Totals: `20 failed, 4 passed`.

**Newcombe fetch record.** I sent HEAD requests only, so no body was transferred:
- `doi.org/...` gives `HTTP/1.1 302 Found`, location `onlinelibrary.wiley.com/doi/...`.
- That Wiley URL gives `403 Forbidden`.
- `www.eiti.uottawa.ca/~nat/Courses/csi5388/Newcombe.1998.pdf` gives `200 OK`, `Content-Length: 139150`, `application/pdf`, `Last-Modified: Mon, 22 Dec 2003`.

All three match `fixtures/newcombe1998_paired.json`. The two copies already on disk (the builder's `scratchpad/e11/newcombe1998_uottawa.pdf` and lens 1's `newcombe_lens.pdf`) both hash to `90a3a049...0d0f87`, the recorded SHA-256.

**`changes_for_other_lanes`, against `cli.py`, `run.py` and the schemas for this diff:**
- `cli.py`: the T2 Next-step line, and the ledger `finally`, which counts an exit 5 after a document.
- `run.py`: `write_documents(..., written=)` and the T2.docx note.
- The schemas are unchanged.

Each item is in the note's list. A Grep of `proofpack-site/src` (read only) for `writes T2.html`, `not built in this engine version`, `wilson_deff`, `case_share_above_grid` and `below_coverage_bar` found nothing.

## What I could not check

- **The SHA-256 of what the uottawa URL serves today.** I sent HEAD requests and did not download the body. The size and the two on-disk copies match the record.
- **The day-10 sweep in PowerShell.** About 27 minutes per shell; the Git Bash run reproduces the note's `37 / 37`.
- **The worst in-bound shape, and coverage on shapes beyond B1's ten rows.** Each row is one simulation (Monte-Carlo error about 0.009 at R = 2000), and I did not search further.
- **Whether a W15 from `record_ledger` inside the new `finally` is lost when a writer has raised.** The exception propagates, and the return value is not printed. I did not construct the case of an unwritable ledger plus a raising writer.
- **Whether DEC-08's refusal, or a tier annotation, is the right answer for B1's cells.** That is Josh's call: need 49, widened.
