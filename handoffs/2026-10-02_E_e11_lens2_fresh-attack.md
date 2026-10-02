# E11 (build day 11, lane E) at `0fa9391`: cold fresh-attack lens 2 (2 October 2026)

**Verdict: FAIL. Two blockers.**

**B1.** Lens 1's FA-B1 is marked "fixed, one cause" in the repair note, but it still reproduces. The repaired route prints `wilson_deff` with no tier annotation on clustered cells of 30 to 60 cases whose coverage I measured at 0.78 to 0.85. The shapes are inside the route's bounds (no case above a fifth of the rows, at most 50 rows per case). The process is the one that sets the threshold: TAU2 = 0.5, truth 0.9. I measured this twice: once with the engine's own `proportion_ci`, once with an implementation that shares no repository code. Four of lens 1's own B1 rows also still print unannotated below the bar (0.806 to 0.893). The committed grid itself records 26 such rows, plus 0.882 at truth 0.9.

**B2.** The `Guidance status.` item on T1, T2 and T8 (HTML and DOCX) names the AI-DSF draft without the literal `draft guidance (January 2025), not for implementation`. Its month is typed in `scope.py` rather than read from `guidance_map_v1.csv`. With the map row moved to February 2025, the T1 `<h1>` reads "February 2025" and the same page's `Guidance status.` item still reads "January 2025". This is pre-existing since `ad66073`, and lens 1 left it under could-not-check. Graded by attack 1's rule.

Everything else I attacked held. That covers:
- the ledger repair (RG-B1);
- the McNemar Se/Sp figures;
- DEFF and Wilson by hand;
- Newcombe;
- item 0;
- the header following the map row;
- the coverage JSON regenerating.

Read the blockers, not the counts.

Target: `0fa9391` on `main` (one commit over `2adfaaa`, unpushed). I used detached worktrees under `scratchpad/lens-E11-r2-fresh-attack/`:
- `wt` (`0fa9391`): probes and planted mutants, each restored;
- `wt2` (`0fa9391`): the clean suite, the sweep and the coverage re-run;
- `old` (`2adfaaa`): the regression tests.

`PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed a path inside each worktree before I trusted any figure. `PROOFPACK_REQUIRE_DOCX=1` and `PYTHONIOENCODING=utf-8` were set throughout. Every CLI run was in-process through `proofpack.cli.main(..., registry=ephemeral_registry())` with `--offline`. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1, Git Bash. I committed, pushed and downloaded nothing. This note is the only file I wrote in the repository.

## Blockers

### B1. `wilson_deff` prints with no tier annotation below the DEC-08 bar on in-route shapes of 30 or more cases, at the threshold-setting process; FA-B1 is marked fixed and still reproduces

The repair added two bounds to the route (`deff_wilson_route`): the largest case holds at most 0.20 of the rows, and the mean case size is at most 50. The grid it measured has one dominant case, equal sizes, or one mixed cycle. It has no shape with **several** mid-sized dominant cases beside many one-row cases, which is the shape of a test set where a few patients contribute many images. Those shapes pass both bounds. At 30 cases or more `precision_flags` returns `[]`, so they print with `wilson_refused_clustered` alone (plus `imprecise` on some draws, which is not an R2 tier).

The engine's own `proportion_ci` in `wt2` uses `plan_clustering("case_id", ...)`. The process is the coverage script's: latent `b_i + e_ij`, Var(b) = TAU2, case sizes fixed, truth p. R = 2000 per row; `methods` was `{'wilson_deff': 2000}` on every row. My own simulation shares no repository code. It uses the ratio-estimator DEFF floored at 1, `sum m_i^2 / n` at the boundary, and Wilson on `n / DEFF` with z = 1.959964.

| shape (cases x rows) | K | n | largest share | TAU2 | p | engine coverage | own coverage | cluster bootstrap, same driver (R 1000) |
|---|---|---|---|---|---|---|---|---|
| 4 x 19 + 26 x 1 | 30 | 102 | 0.186 | 0.5 | 0.9 | **0.8285** | 0.8195 | 0.836 |
| 4 x 19 + 26 x 1 | 30 | 102 | 0.186 | 0.5 | 0.5 | **0.8460** | 0.8525 | 0.894 |
| 5 x 40 + 25 x 1 | 30 | 225 | 0.178 | 0.5 | 0.9 | **0.7760** | 0.7935 | 0.794 |
| 5 x 50 + 35 x 1 | 40 | 285 | 0.175 | 0.5 | 0.9 | **0.7800** | 0.7695 | 0.792 |
| 7 x 50 + 23 x 2 | 30 | 396 | 0.126 | 0.5 | 0.9 | **0.8105** | 0.8045 | 0.811 |
| 10 x 50 + 50 x 1 | 60 | 550 | 0.091 | 0.5 | 0.9 | **0.8530** | 0.8475 | 0.833 |
| heavy tail 30,20,15,12,10,8,7,6,5,5,4,4,3,3,3,2x5,1x20 | 40 | 165 | 0.182 | 0.5 | 0.9 | - | 0.8905 | - |
| heavy tail 40,30,25,20,15,12,10,8,8,6,6,5,5,4x3,3x4,2x10,1x30 | 60 | 264 | 0.152 | 0.5 | 0.9 | - | 0.8755 | - |

Lens 1's B1 rows at the tip, with the same driver (R 2000, `wilson_deff` on every draw, flag `wilson_refused_clustered` only, or plus `imprecise`):

| shape | p | TAU2 | coverage |
|---|---|---|---|
| 30 x 20 | 0.98 | 0.5 | **0.8930** |
| 30 x 20 | 0.98 | 0.8 | **0.8060** |
| 30 x 8 | 0.95 | 0.8 | **0.8520** |
| mixed cycle x 3 | 0.95 | 0.8 | **0.8535** |

Only lens 1's two one-dominant-case rows (skew40, skew30) moved to the bootstrap.

My simulation also reproduces the committed grid within Monte-Carlo error:

| grid row | own | committed |
|---|---|---|
| mixed 30, p 0.9, TAU2 0.5 | 0.9055 | 0.90675 |
| 30 x 50, p 0.98, TAU2 0.8 | 0.76425 | 0.7635 |
| 60 + 9 x 1, p 0.5, TAU2 0.8 | 0.13975 | 0.13725 |
| 5 x 50, p 0.9, TAU2 0.5 | 0.7915 | 0.80825 |

So the engine and my code agree; the route is what fails.

Why this blocks:
- **The brief's Accept line fails.** It reads "no rendered clustered cell below the bar without its tier annotation". DEC-08 reads "refused with a typed reason below it".
- **The bootstrap is not a fallback here.** On these shapes the cluster bootstrap (the `ad66073` route) is no better: 0.79 to 0.89. So this is not a regression against `ad66073`, but the bootstrap does not supply a fallback.
- **The note's verdict is false.** Its sentence is "Both blockers are repaired", with FA-B1 "fixed, one cause". FA-B1 rows 3 to 6 still reproduce. The note's own carried row E11r1-1 (26 of 162 recorded rows, and need 49) is the same class, from the committed JSON.
- **A grid sentence does not close it.** The repair's statement "at the process that sets the threshold, every printed row of 30 cases or more covered at or above the bar" is true of grid rows only. The route prints shapes the grid never held, at that same process, below the bar.

Repro: `PYTHONPATH=<wt>/src PYTHONHASHSEED=0 python scratchpad/lens-E11-r2-fresh-attack/probe/cov_engine.py 2000`. It prints, for example, `5x40+25x1: K 30 n 225 p 0.9 tau2 0.5 reps 2000 seed 701336: coverage 0.7760; methods {'wilson_deff': 2000}; flags {('wilson_refused_clustered',): 1224, ('imprecise', 'wilson_refused_clustered'): 776}`. Own code: `probe/cov_own.py 2000`. Bootstrap: `probe/cov_engine_boot.py 1000`.

What a repair has to decide is not mine to choose. Josh's need 49 already asks it for TAU2 0.8 and truth 0.95 / 0.98; these shapes add TAU2 0.5 and truth 0.9. There are three candidates:
- an observable condition on the size distribution (for example the effective number of cases `(sum m_i)^2 / sum m_i^2`, which is 6.7 to 13 on these shapes against K = 30 to 60) that keeps or refuses the cell;
- the tier annotation on every clustered proportion that is not on a measured shape;
- a refusal under DEC-08.

### B2. `Guidance status.` names the AI-DSF draft without the literal qualifier and with a month typed in code, not read from the map row

My own scanner (`probe/scan.py`) found the item in T1, T2 and T8 HTML and in T1 and T8 DOCX. It checks each innermost HTML block element and each `w:p`. The item reads `... the FDA draft guidance "Artificial Intelligence-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations" (January 2025), it is a draft, not for implementation, and section numbering may change on finalisation`. It is built at `src/proofpack/scope.py:55-59`, with "January 2025" as a literal.

To check whether it follows the map, I set `version_date` of `FDA_AIDSF_PERF_VALIDATION` and `FDA_AIDSF_SUBGROUP_PERF` to `2025-02-03` in `wt`'s `design/guidance_map_v1.csv` and re-ran `build_sample_pack.py --compare`:
- T1 `<h1>`: `T1 · FDA AI-DSF performance evidence attachment set, per draft guidance (February 2025), not for implementation`.
- The same page's `Guidance status.` item: still "(January 2025)".
- `January 2025` count minus the literal-qualifier count is 1 on each of T1, T2 and T8: that item.

Every other mention passed the scan:
- Every `FDA_AIDSF_*` anchor row carries the literal qualifier in its own `<tr>`; my check printed no row lacking it.
- The T7 hits are `href` attributes only.
- The PCCP title is the final guidance and correctly unqualified.

It is unchanged since `ad66073`; lens 1 recorded it as could-not-check. I grade it a blocker because attack 1's rule is literal ("any mention without `draft guidance (January 2025), not for implementation` in the same line/element") and the binding rule says the label is read from the map row. Josh may rule the item qualified under DEC-71 (a)'s wording ("draft, January 2025, not for implementation"). The hard-coded month, which gives one page two dates, stands either way.

Repro: `PYTHONPATH=<wt>/src python scripts/build_sample_pack.py --out P --compare && python scratchpad/lens-E11-r2-fresh-attack/probe/scan.py P/T1.html` (the `li Guidance status.` line).

## Non-blocking (record and carry)

**N1 (sentence). Test name `test_e11_deff_wilson.py::test_the_committed_threshold_leaves_no_unannotated_cell_below_the_bar_at_its_process`.** It inspects the committed grid rows only. The name asserts that no unannotated cell below the bar is left at its process. Counter-example: shape 4 x 19 + 26 x 1 at TAU2 0.5 and p 0.9, which is its process, printed unannotated at 0.8285 (B1). Name what it inspects: "every committed grid row at its process ...".

**N2 (sentence). Test name `test_e11_repair1.py::test_a_compare_whose_first_writer_raises_writes_nothing_and_is_not_counted`.** With `write_t2` and `write_t7` raising, the compare exits 5 and writes `compare_ingest_report.json`, `ingest_report.json`, `pseudonyms.json` and `run.json`. The test inspects only `T*.html`. "writes no document" is what it shows.

**N3 (sentence). `cli.py` module docstring: "(DEC-47 counts HTML and DOCX documents; E11 decision 1)".** DEC-47's row ("counts every run with a `criteria` list that wrote a document") names no format. The HTML/DOCX reading is E11 decision 1's, not DEC-47's.

**N4 (sentence, on the page). T7 `METHOD_DESCRIPTIONS["wilson_deff"]`: "(any other clustered proportion prints the cluster bootstrap)".** A one-case cell prints no interval: method `none`, `insufficient_clusters`, route `not_estimable` (measured: 7 rows, 3 successes, one case). It prints the bootstrap's refusal, not a bootstrap interval.

**N5. Surviving non-equivalent mutant L6.** I swapped the order of the case-share and rows-per-case checks in `deff_wilson_route`. It survived the full non-slow suite: `1959 passed, 2 skipped, 4 deselected, 1 xfailed`. It changes `detail.design_effect.route` only on a cell that exceeds both bounds; the interval is the same. No test feeds such a cell.

**N6. Partial-write reporting.** First, a run or compare that exits 5 after a partial write prints no summary, so a W15 from the `finally` commit is computed and never printed (the note's open question 2). Second, when the **first** writer raises, `run.json` carries `manifest.ledger_count` 1 while `ledger.json` stays absent. Measured on `run --templates T1,T7` with `write_t1` raising: rc 5, files `ingest_report.json, pseudonyms.json, run.json`, ledger `{}`. The same holds for compare, whose `comparison.ledger.prior_acceptance_runs` is 0. No document carries the figure, so the miscount is in JSON only.

**N7. `doctor --offline` prints `Next step: proofpack declare --out criteria.yaml, ...`.** This engine's subcommands are `doctor, map, run, compare, fixtures, licence`; there is no `declare`. The line is in handoffs since 22 September, and `cli.py` does not contain it at `ad66073`, `2adfaaa` or `0fa9391`, so it comes from another module. Not E11's; recorded.

**N8. Newcombe: need 46 stands.** My own method-10 code matches all 35 compared fixture limits (worst 4.876e-05). It gives F5 `(80, 2, 10, 8)` as (-0.155356, -0.010249). The excluded `1 97 1 1` value is unchanged in the fixture with its reason.

**N9. Mutation sweep.** `scripts/mutation_sweep.py --marker day11` in `wt2` printed `50 planted, 50 killed, 0 survived; 759 s`. I planted 16 mutants of my own on the repair lines (`probe/mut.py`, output `mut.txt`). Two survived the targeted files:
- L6, above.
- R1: the T2.docx note branch forced for every template. It is equivalent today, because every id in `TEMPLATE_IDS` (`T1, T2, T7, T8`) has an HTML writer.

Fourteen were killed:
- L1 / L2: share and rows `>` changed to `>=`.
- L3: smallest case in place of largest.
- L4 / L5: constants changed.
- L7: the five-case check moved to four.
- L8: the route in the bootstrap detail forced.
- L9: the tier taken from a floor of 10.
- C1: the partial write not counted.
- C2: `write_documents` copies the caller's list.
- C3: a compare counted on `run.json` alone.
- C4: a json-only run counted.
- V1 / V2: the threshold filters dropped.

## What I could not break (tried, with figures)

- **Suite and lint (`wt2`, `0fa9391`).**
  - Full suite: `1963 passed, 2 skipped, 1 xfailed in 237.88s`. The second skip is the TR39-full file, because `PROOFPACK_TR39_FULL` was unset. The total equals the note's `1964 passed, 1 skipped`.
  - Markers: `day11` 110, `day10` 262, `day9` 337, `day8` 470 + 1 skipped (the same TR39 file), `ap3` 176, `ap2` 91, `ap4` 195. These equal the note's figures.
  - `ruff check`: `All checks passed!`. `ruff format --check`: `287 files already formatted`.
  - `fixtures --offline`: `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`, rc 0.
  - `doctor --offline`: `All essential checks passed.`
  - `capture_fixture_oracles.py --check`: `72 identical, 0 differ within their tolerance, 0 differ outside it`.
  - `build_sample_pack.py --compare` sizes: T1 142,983, T7 48,056, T8 35,178, compare.json 329,347, T2 69,922, run.json 236,843, as in the note.
- **Regression tests at `2adfaaa`.** In `old`, `test_e11_repair1.py` gave `9 failed, 1 passed`. The one that passes is the disclosed M19 pin. The tip's `test_e11_merge_blockers.py` failed its 4 unlicensed cases. Together: `13 failed, 20 passed`, as the note says.
- **The ledger (RG-B1 and DEC-47 / DEC-70 (b)), F5, limit 3.**
  - Two runs and one compare count `{key: 3}`, and the compare's `prior_acceptance_runs` is 2.
  - A compare with no licence: rc 4, no document, ledger `{}`.
  - A licence without `compare`: rc 4, no document, `{}`.
  - `run --format json` after one run: rc 0, files `ingest_report.json, pseudonyms.json, run.json`, ledger stays 1, `ledger_count` 1.
  - Five runs carry `ledger_count` 1 to 5, with W14 in `run.json` and on stdout on runs 4 and 5 only (count > 3, as README and D1's `warn_after` say).
  - Partial writes count: the read-only `T8.html` and the raising T8 / T2 writers, through the repair tests and my mutants C1 / C2, which those tests kill.
  - `lxml` hidden: `run --format json,html,docx --templates T1,T7` gave rc 5, files `T1.html, ingest_report.json, pseudonyms.json, run.json`, counted `{key: 1}`. That is exactly the `_docx_extra_missing` docstring's measured sentence.
- **McNemar Se / Sp (by hand, scipy only).**
  - F5's CSVs at `>= 0.5`: Se `e 40, new-only 1, prior-only 5, h 4`; Sp the same; accuracy `80 / 2 / 10 / 8`. Exact p 0.21875 / 0.21875 / 0.03857421875.
  - Four constructed pairs through `compare` gave `b` = prior-only-correct and `c` = new-only-correct, as T2-3's header defines them. The p-values were equal to my hand figures (largest difference 1.7e-18):
    - Se 4 / 20 (24, exact 0.0015439) with Sp 20 / 5 (25, continuity-corrected 0.0051103).
    - Se 13 / 12 (25, cc 1.0) with Sp 20 / 4 (24, exact 0.0015439).
    - Se 0 / 0 with Sp 1 / 0 (both `1.000 (exact)`).
    - Sp 0 / 7 with the new version all correct (exact 0.015625).
  - The accuracy row is the sum of the two (for example 24 / 25 and 33 / 16).
  - The sample pack's T2-3 gave Se 6 / 8, `0.791 (exact)`, which by hand is 2 x 6476 / 16384. Sp gave 8 / 21, `0.026 (continuity-corrected chi-square)`, where (13 - 1)^2 / 29 = 4.9655.
- **DEFF and Wilson by hand (exact fractions, `probe/deff_hand.py`).** Each matches the engine to at most 2.2e-16:
  - 6 x 4 rows, successes 4,4,0,1,3,0: DEFF 3.6, (0.197688, 0.802312).
  - Ten cases of 3 to 5 rows: DEFF 4.068851, `very_low_precision`.
  - 12 singletons: DEFF 1, the plain Wilson.
  - p = 0 on 5 x 3: DEFF 3, (0, 0.434482).
  - p = 1 on 5 x 3: (0.565518, 1).
  - Negative correlation (6 x 2, one success each): estimate 0.000000, `deff_floored_at_one`.
  - Sizes 1,2,5,4,3: share 0.333, so `case_share_above_grid` and the bootstrap.
  - 5 x 60: `rows_per_case_above_grid`.
  - One case: `insufficient_clusters`, `not_estimable`.
- **The coverage table reproduces.** `coverage_bar.py --deff-wilson --json` re-run in `wt2` gave `identical True`, threshold 30, 95 s. The figures quoted in `bootstrap.py`, `conventions_T7.md` and the test all match the JSON as I re-read it:
  - 0.90675;
  - 12 below at 5 to 20 cases;
  - 26 of 162;
  - 0.7635;
  - 408 share rows, minimum 0.13725;
  - 18 of 30 one-dominant constant-setting rows of 30 cases or more below the bar, minimum 0.582.
- **The AI-DSF header follows the map row.** The T1 `<h1>` and the DOCX title paragraph read the row (February after my edit). The T1 HTML and DOCX criterion rows for the paired `C2` both read `not assessable` / `requires_compare`. The T1 docstring's claim about the `ad66073` golden is true: line 135 is the only line carrying `AI-DSF`, and its `<title>` is `T1 · ProofPack v0.1.0.dev1 · run test-onl`.
- **Item 0 and the Next-step lines.**
  - `compare --format json,html,docx` with `docx` and `docxtpl` hidden: rc 7, the one-line error ending `nothing was written`, an empty `--out`, no ledger.
  - `run --templates T2`:
    - With no licence, and with a licence without `compare`, it names `licence install ... then proofpack compare`. The compare that follows wrote no `T2.html` (rc 4).
    - With `compare` in the licence it names `proofpack compare`, and that compare wrote `T2.html` (rc 0).
  - `compare --format json,html,docx --templates T2,T7` prints `T2.docx not written: T2 has no DOCX writer in this engine version (it is written as T2.html under --format html)` after writing `T2.html`, `T7.html` and `T7.docx`.
- **Rows 132 / 149.** `no_score_column` and `metric_not_compared` are in `schema/output_schema_v1.json`'s enums (4 occurrences). The criterion text for `metric_not_compared` is in `criteria.py:134`. The repair did not touch them.

## What I could not check

- **The `no_score_column` branch on a rendered page.** As in lens 1, a prior table with no score halts H07 first, so I saw no rendered annotation for it.
- **The day-10 sweep (`37 / 37`, about 23 min).** I did not re-run it. The day-10 marker passed 262 / 262.
- **PowerShell 5.1.** All my figures are from Git Bash and in-process Python.
- **The worst shape.** I did not search for it. B1's rows are the shapes I tried, at R = 2000 (Monte-Carlo error about 0.007) and, for the bootstrap, R = 1000. I did not test whether an effective-cases condition closes B1.
- **Rao and Scott 1992.** Not fetched; it is still `[unverified]` on the page, correctly.

## Sentences I refused to write

- "The repaired route prints only where coverage clears the bar". B1 refutes it.
- "The ledger counts every run that wrote a document". I tested the cases listed above, not every writer failure.
- "B2 is unqualified". The item carries "draft" and "not for implementation"; what fails is the literal and the source of its month.

Repro scripts and raw outputs are in `scratchpad/lens-E11-r2-fresh-attack/`:
- `probe/`: `cov_own.py`, `cov_engine.py`, `cov_engine_boot.py`, `deff_hand.py`, `scan.py`, `mut.py`, `cov_engine_tip.txt`, `cov_engine_boot.txt`;
- `zz/`: the CLI and McNemar probe tests;
- `suite.txt`, `markers.txt`, `mut.txt`, `mut_full.txt`, `sweep11.txt`, `cov_rerun.txt`.
