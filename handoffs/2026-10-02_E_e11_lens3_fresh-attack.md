# E11 (build day 11, lane E) at `3302d59`: cold fresh-attack lens 3 (2 October 2026)

**Verdict: FAIL. Two blockers.**

**B1.** Clustered *difference* cells print below the DEC-08 bar with no tier annotation and no `ᵈ`. The T2-3 paired difference (Sensitivity, Specificity, Accuracy) carries no case-count tier at any case count: a 6-case Sensitivity difference prints `−8.0 [−37.1, +4.0]` bare, beside version cells marked `ᵃᶜᵈ`. Measured with the engine's own cell function, the paired Sensitivity difference covered **0.8638** on five cases of 50 rows beside 25 one-row cases (30 cases), and **0.8799** on ten cases of ten rows. The T1 subgroup difference covered **0.8864** (engine) and **0.8835 / 0.8460** (my own code) on the same 30-case shape. Repair 2 carried this class as E11r2-1, saying "nothing measured today says whether they need it". It is now measured, and the brief's Accept line ("no rendered clustered cell below the bar without its tier annotation") fails on it. Pre-existing since E5 / E10; not introduced by repair 2.

**B2.** T2-3 prints McNemar p-values on clustered pairs as if the pairs were independent. That includes the Sensitivity and Specificity McNemar that E11 item 3 added (DEC-70 (d), a statistical gate). There is no typed reason and no flag, and the same row refuses the Newcombe interval on the same pairs (`newcombe_refused_clustered`). With the null true (equal marginal accuracy) on the 30-case shape, the printed test rejects at p < 0.05 in **0.5380** of 2000 tables. On 30 cases of ten rows it rejects in **0.2630**. The unclustered control gives **0.0300**. That p-value is a wrong number on the page.

Everything else I attacked held:
- repair 2's `ᵈ` rule, on every clustered proportion I could render (HTML and DOCX);
- the AI-DSF qualifier, on every element of T1, T2, T7 and T8 (HTML and DOCX), following the map row;
- the ledger;
- the McNemar arithmetic and the method switch at 25;
- Newcombe, re-read from the PDF on disk;
- DEFF-Wilson by hand on 13 tables;
- the coverage JSON regenerating identically;
- item 0;
- rows 132 / 149.

Read the blockers, not the counts.

Target: `3302d59` on `main` (one commit over `0fa9391`, unpushed). Detached worktrees under `scratchpad/lens-E11-r3-fresh-attack/`:
- `wt` (`3302d59`): the suite, then my planted mutants, each restored with `git checkout`;
- `wt2` (`3302d59`): clean probes and the day-11 sweep;
- `wt0` (`0fa9391`): the regression run.

`PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed a path inside each worktree before I trusted any figure there. `PROOFPACK_REQUIRE_DOCX=1` and `PYTHONIOENCODING=utf-8` were set on every suite run. Every CLI run was in-process through `proofpack.cli.main(..., registry=ephemeral_registry())` with `--offline`. Platform: Windows 11, CPython 3.14 (win-amd64), Git Bash. I committed, pushed and downloaded nothing. The Newcombe PDF I read is the builder's copy on disk (`scratchpad/e11/newcombe1998_uottawa.pdf`, SHA-256 `90a3a049...5e0d0f87`, 139,150 bytes, as recorded). This note is the only file I wrote outside the scratchpad. All three worktrees were clean (`git status --short` empty) and were removed with `git worktree remove --force` at the end.

## Blockers

### B1. Clustered difference cells (T2-3 paired differences, T1 subgroup differences) print below the bar with no tier annotation and no `ᵈ`

What the code does:
- `stats/comparison.py::_paired_proportion_cell`, the T2-3 Sensitivity / Specificity / Accuracy difference under a clustered plan, builds its Number with `flags=["newcombe_refused_clustered"]`. It never calls `precision_flags`, so the cell carries no case-count tier at **any** case count.
- `stats/subgroups.py::_proportion_difference` adds `precision_flags(n_cases)`, which is `[]` at 30 cases or more.
- Neither goes through `proportion_ci`, so neither carries repair 2's `clustered_coverage_not_established` / `ᵈ`.

Repair 2's note carries this as E11r2-1: "Clustered cells that do not go through `proportion_ci` (subgroup differences, AUROC, O:E, calibration slope and intercept, T2 differences) carry their case-count tier only; their coverage on several-large-case shapes at 30 cases or more is not measured". For T2-3 the first half of that is false (they carry no tier at all). The second half I measured.

**Coverage, engine code.** `probe/p2_diff_cov.py` calls the engine's own `_paired_proportion_cell` (what `compare` calls) and `subgroups._bootstrap_difference` with `clustered_flat` (what the subgroup cell calls). The process is the coverage script's: latent `b_i + e_ij`, Var(b) = TAU2 = 0.5, success when the latent is below `Phi^-1(p)`. For the paired cell, one latent per row is read by both versions at their own thresholds. R = 2000, B = 1000.

| cell | shape (cases x rows) | K | truth | coverage | flags on every printed cell |
|---|---|---|---|---|---|
| T2-3 paired Se difference | 5 x 50 + 25 x 1 | 30 | 0.90 - 0.85 | **0.8638** (1997 / 2000 printed) | `newcombe_refused_clustered` |
| T2-3 paired Se difference | 10 x 10 | 10 | 0.90 - 0.85 | **0.8799** (1974 / 2000) | `newcombe_refused_clustered` (no `ᵇ`: `precision_flags(10)` is `very_low_precision`) |
| T2-3 paired Se difference | 10 x 5 | 10 | 0.90 - 0.80 | 0.9412 | the same |
| T2-3 paired Se difference | 5 x 10 | 5 | 0.90 - 0.85 | 0.9648 (1759 / 2000) | the same (no `ᵃ`) |
| T1 subgroup Se difference, two groups of | 5 x 50 + 25 x 1 | 30 | 0.9 - 0.9 | 0.9025 | `newcombe_refused_clustered` |
| T1 subgroup Se difference, two groups of | 5 x 50 + 25 x 1 | 30 | 0.9 - 0.8 | **0.8864** (1999 / 2000) | `newcombe_refused_clustered` |
| T1 subgroup Se difference, two groups of | 10 x 10 | 10 | 0.90 - 0.85 | 0.9030 | `+ very_low_precision` |

**Coverage, own code (no repository import).** Cases are resampled with replacement and the rows of the drawn cases pooled; percentile 2.5 / 97.5 (`probe/p5_own.py`, `probe/p11_sub_own.py`):
- paired Se difference, 5 x 50 + 25 x 1, 0.90 - 0.85: **0.8680**;
- subgroup difference, the same shape each side: 0.9 - 0.8 **0.8835**, 0.9 - 0.9 0.9150, 0.95 - 0.85 **0.8460**.

**On the page.** I ran `compare --format json,html,docx --templates T2,T7` on F5 with a `case_id` of ten cases of ten rows and `clustering.unit: case_id` (`probe/p1_clustered_cli.py`, output `o1few/`). The T2-3 Sensitivity row reads:

`45/50 (90.0%) [54.7, 98.5]ᵃᶜᵈ   41/50 (82.0%) [47.0, 95.9]ᵃᶜᵈ   −8.0 [−37.1, +4.0]   cluster_bootstrap_percentile   5 / 1   0.219 (exact)`

`run.json` `comparison.differences.op1.sensitivity.number` has `n_cases 6, flags ['newcombe_refused_clustered']`. The version cells carry their tiers and `ᵈ`; the difference beside them carries nothing. On the 45-case run (`o1/`) the Accuracy difference is `n 100, n_cases 45, flags ['newcombe_refused_clustered']`.

**Why it blocks:**
- The lens rule: "a clustered cell below 0.90 rendered without its tier annotation is a blocker".
- The brief's Accept line: "no rendered clustered cell below the bar without its tier annotation".
- DEC-18 (c): "every clustered cell keeps its tier annotation". The T2-3 difference keeps none, even at 6 cases.

This is not a repair-2 regression: `0fa9391` and `ad66073` print these cells the same way. Repair 2's choice of a mark on proportions only leaves this class open, and its carried row understates it.

Repro: `PYTHONPATH=<wt>/src python scratchpad/lens-E11-r3-fresh-attack/probe/p2_diff_cov.py 2000 1000` (add `P2_FEW=1` for the 10- and 5-case rows); own: `probe/p5_own.py 2000 1000`, `probe/p11_sub_own.py 2000 1000`; page: `WT=<wt> probe/p1_clustered_cli.py OUT 10,10,10,10,10,10,10,10,10,10`.

### B2. McNemar is printed on clustered pairs with no refusal; its type I error there is 0.54 at a nominal 0.05

`comparison._mcnemar_by_op` and E11 item 3's `_mcnemar_by_metric` count `b` / `c` over rows and call `mcnemar(b, c)` whatever the clustering plan. Nothing in `compare_versions` (lines 785-786) checks `plan.clustered`. The schema, T7 (`exact_mcnemar`: "Exact McNemar test on the discordant pairs") and the T2-3 caption say nothing about independence. On the clustered F5 compare (45 cases, `Clustering route: declared`), T2-3 prints `5 / 1  0.219 (exact)` on Sensitivity and Specificity and `10 / 2  0.039 (exact)` on Accuracy. On the same rows the paired interval is refused with `newcombe_refused_clustered`. The sentence under the table reads "10 cases were correct under the prior version only and 2 under the new version only (McNemar exact, p = 0.039)".

**Type I error, measured** (`probe/p5_own.py`, R = 2000). The null is true: each version's correctness is `latent < Phi^-1(p)`, with its own case effect (Var 0.5) and row noise, so the two versions have equal marginal accuracy and `P(b) = P(c)`. Rejection rate at p < 0.05, with the engine's rule (exact below 25 discordant, continuity-corrected chi-square otherwise):

| shape | K | n | p | own formula | engine `mcnemar()` |
|---|---|---|---|---|---|
| 5 x 50 + 25 x 1 | 30 | 275 | 0.90 | **0.5380** | **0.5380** |
| 30 x 10 | 30 | 300 | 0.85 | **0.2630** | **0.2630** |
| 275 x 1 (control, unclustered) | 275 | 275 | 0.90 | 0.0300 | 0.0300 |

So the printed p-value is the right arithmetic for the wrong test. The arithmetic itself is right: b+c = 24 / 25 / 0 / 1 / 7 / 40, `(20,4)`, `(20,5)`, `(13,12)`, `(0,0)`, `(1,0)`, `(0,7)`, `(30,10)`, all equal to scipy's `binomtest` / `chi2.sf` to 2e-18. The engine's own X2 convention refuses the analytic method under clustering everywhere else (Wilson, Newcombe, DeLong, log-delta, IRLS Wald). Here it prints a p-value that rejects a true null ten times as often as it says. This is graded a blocker as a wrong number on the page, and because DEC-70 (d) made the Se / Sp rows a statistical gate with their own DEC-12 (i) lens. The Accuracy-row half is pre-existing (E10). The Se / Sp half is E11 item 3's.

The repair is not mine to choose. Options: a typed refusal under a clustered plan, as Wilson / Newcombe / DeLong have; a cluster-adjusted McNemar (the clustered-McNemar literature, not fetched here, so `[unverified]`); or a printed annotation. That is a decision for Josh.

Repro: `PYTHONPATH=<wt>/src python scratchpad/lens-E11-r3-fresh-attack/probe/p5_own.py 2000 1000` (the `(b)` lines); page: `o1/cmp/T2.html` from `probe/p1_clustered_cli.py OUT lens`.

## Non-blocking (record and carry)

**N1 (sentence, the repair-2 note).** "At `0fa9391` ... `15 failed, 10 passed`". Measured in `wt0` with the tip's `test_e11_repair2.py` and `test_e11_deff_wilson.py`: 26 collected, `15 failed, 11 passed`. The 11 passes are the control test and ten `test_e11_deff_wilson.py` tests. The failing list and first lines match the note.

**N2 (sentence, docstring the repair edited).** `scope.py` line 1: "Scope and disclaimer strings, verbatim from D4 section 7 (design draft)". Repair 2 rewrote the Guidance status item. D4 section 7 item 5 reads `... the FDA draft guidance "..." (January 2025), it is a draft, not for implementation, ...`. The module now ships `... the FDA guidance "...", it is {aidsf_draft}, ...`. Item 7 already lacked D4's Clopper-Pearson clause before this commit. The rewrite is right for the page; the word "verbatim" is no longer true.

**N3 (sentence, on the T7 page and in `conventions_T7.md`).** "The engine reads a cell's case sizes but not its within-case correlation or the truth". The engine estimates the design effect from the rows, which is a reading of the within-case correlation. On my 6 x 5 table it printed DEFF 4.72, which implies an intraclass correlation near 0.93 under `1 + (m - 1) rho`. What it cannot read is the true correlation of the process. The legend row's wording ("coverage not established for this cell's case sizes and within-case correlation") is fine.

**N4. `ᵈ` is printed on T2 and T8 with no legend.** The clustered compare's T2 prints 13 cells with `ᵈ`. The clustered run's T8 prints the decile cell `41/50 (82.0%) [35.1, 93.3]ᵇᶜᵈ`. Neither page has a tier legend; only T1 and T7 do. This is pre-existing for `ᵃᵇᶜ`; `ᵈ` is new.

**N5. `ᵈ` on a cell that is the plain Wilson interval.** A clustered plan whose cases are all single rows routes to `wilson_deff` with DEFF 1 (`deff_one_row_per_case`). 13 / 20 printed `[0.4329, 0.8188]`, the unclustered Wilson interval exactly, with `clustered_coverage_not_established`. It is over-annotation and harmless; recorded in case Josh's need 49 picks option (b).

**N6 (sentence, on a page; pre-existing E10).** In a clustered compare, T2's sentences read "on 100 paired cases" and "10 cases were correct under the prior version only". `run.json` for the same cell has `n 100, n_cases 45`: the 100 are rows, and on a clustered page "cases" is the clustering unit.

**N7. Printed line points `compare` at the `run` docs.** With the docx modules hidden, `compare --format json,html,docx` prints `error: --format docx needs the [docx] extra ... (docs: /docs/run); nothing was written`. What it says about writing is true (rc 7, `--out` absent, no ledger).

**N8. Mutants on the repair-2 lines.** See "Mutation" below. Survivors are recorded there; none reopens a blocker class.

**N9 (sentence, pre-existing A-P4, touched by repair 2's constant).** `scripts/make_docx_templates.py`, beside `_T1_LITERALS = (COVER_NOTE, PUBLIC_SUMMARY_NOTE, MODEL_CARD_NOTE, LONG_FORM_TITLE)`, says "The three literals the T1 template repeats ... (checked here so a change to the constants fails the regeneration test rather than drifting)". There are four, and `grep _T1_LITERALS` finds no use, so nothing is checked. Repair 2 turned `MODEL_CARD_NOTE` into a template with `{aidsf_draft}`. The DOCX template reads `{{ model_card_note }}` from the context, so the page is right.

## What I could not break (tried, with figures)

- **Suite and lint (`wt`, `3302d59`, Git Bash).**
  - Full suite: `1978 passed, 2 skipped, 1 xfailed in 299.88s`. The second skip is `test_e8_repair4.py:405`: a worktree has no `workflows/data/confusables-18.0.0.txt` beside it. The total of 1981 equals the note's `1979 passed, 1 skipped, 1 xfailed`.
  - Markers (`--collect-only`; every one of them passed inside the full run): `day11` 125, `day10` 262, `day9` 337, `day8` 471, `ap3` 176, `ap2` 91, `ap4` 197. The note's figures exactly; the note's "before" was day11 110 and ap4 195, the rest unchanged.
  - `ruff check .`: `All checks passed!`. `ruff format --check .`: `290 files already formatted`.
- **Regression tests at `0fa9391`.** The tip's two test files in `wt0` gave `15 failed, 11 passed` (N1). All 14 non-control `test_e11_repair2.py` tests failed, plus `test_t7_prints_the_committed_table`.
- **Repair 2's mark on every clustered proportion with an interval.**
  - Clustered `run --templates T1,T7,T8` and `compare --templates T2,T7` on F5 with a `case_id`, in two shapes: 5 x 12 + 40 x 1 (45 cases) and 10 x 10. I walked every Number in `run.json` with `k`, `n` and an interval whose method is `wilson_deff` or `cluster_bootstrap_percentile`: 0 lacked the flag (run: 10 `wilson_deff` + 17 bootstrap; compare: 16 + 25).
  - T1.html data-ref facets: every flagged `cell` / `est` facet printed `ᵈ` (15 + 10); no unflagged cell printed it. All 36 prose `k/n (x%)` estimates carried it.
  - Proportion cells `k/n (x%) [lo, hi]` with `ᵈ`: T1.html 20 / 20, T1.docx 16 / 16, T2.html 13 / 13, T8 (HTML and DOCX) 1 / 1.
  - The `ᵈ` legend row is on T1 and T7, HTML and DOCX.
  - The HTML / DOCX difference in `ᵈ` counts (52 / 44) is the forest-plot labels and value table, which are text in HTML and drawn into the PNG in DOCX (`figures_png` uses the same labels).
  - A one-case cell (7 rows, 3 successes): `none`, `insufficient_clusters`, flags `['wilson_refused_clustered', 'not_evaluable_shown_for_transparency']`, no `ᵈ`. That matches T7's new sentence.
  - Two cases (3 / 3 and 0 / 3): bootstrap `[0.0, 1.0]` with `ᵃᶜᵈ`, matching "two or more cases ... prints the cluster bootstrap".
- **AI-DSF qualifier (attack 1).** My own element scanner (`probe/p3_scan.py`) checks each element's own text plus its inline children, and each `w:p` in document, headers and footers. It finds every element naming `AI-DSF`, "Lifecycle Management and Marketing Submission" or "draft guidance" that lacks `draft guidance (January 2025), not for implementation`. Mentions / without the literal:
  - sample pack: T1.html 52 / 0, T2.html 12 / 0, T7.html 7 / 0, T8.html 12 / 0, T1.docx 51 / 0, T7.docx 6 / 0, T8.docx 11 / 0;
  - clustered run / compare: T1.html 46 / 0, T1.docx 45 / 0, T8.docx 11 / 0, T2.html 12 / 0, T7 6-7 / 0.
  - Map row moved: I set only `FDA_AIDSF_PERF_VALIDATION`'s `version_date` to 2025-03-14 in `wt2`'s map. The T1 `<h1>` and the Guidance status item read "March 2025" (T1.html: 18 "March 2025", T2 9, T8 8). The model-card note and every other anchor row stayed "January 2025", each read from its own row (the scanner, run with the March literal, lists those 34 T1 elements and each carries its own row's January qualifier). Restored with `git checkout`.
- **Ledger (attack 2), F5, limit 3, fresh home per case (`probe/p6_ledger.py`).**
  - run, run, compare: ledger 1, 2, 3; `run.json` `ledger_count` 1, 2, 3; no W14.
  - Fourth run: 4, rc 2, W14 in `run.json` and on stdout. W14 fires when the count exceeds the limit, not at it, as README and D1's `warn_after` read.
  - Five runs: W14 on runs 4 and 5 only.
  - compare with no licence: rc 4, `run.json` + reports only, `ledger.json` absent.
  - Licence without `compare`: rc 4, the same, and `Next step: proofpack licence install FILE, then compare again for T2.html`.
  - `run --format json` and `compare --format json`: rc 0, no document, ledger absent, `ledger_count` 0.
  - `compare --format json,docx --templates T2`: rc 0, no document (T2 has no DOCX writer, said so), ledger absent.
  - A second run against a limit-1 criteria file: count 2, W14.
  - Lens 1 RG-B1 (read-only `T8.html`): rc 5, `T1.html` and `T7.html` written, ledger 2, `ledger_count` 2. Closed.
- **McNemar Se / Sp (attack 3), by hand from F5's raw CSVs at `>= 0.5`.**
  - Sensitivity: both correct 40, b 5, c 1, neither 4, exact p 0.21875.
  - Specificity: the same.
  - Accuracy: 80 / 10 / 2 / 8, exact p 0.03857421875, corrected chi-square 4.0833.
  - `run.json` `mcnemar_by_metric.op1` and `mcnemar.op1` are equal to these. The method strings are `exact_mcnemar` / `cc_mcnemar`, and the switch is at b + c = 25 (24 exact, 25 corrected).
  - A row with one version all correct, `(0, 7)`: 0.015625.
  - The arithmetic holds; B2 is about the test's validity under clustering.
- **Newcombe (attack 4).** The mark came off in `8c302a1`. The commit and fixture name the URL (`eiti.uottawa.ca/~nat/Courses/csi5388/Newcombe.1998.pdf`) and Table III, method 10. I extracted pages 7-8 of the PDF on disk with pypdf and transcribed the 18 method-10 rows myself. My own method 10 (Wilson limits; phi numerator `max(eh - fg - n/2, 0)` when `eh > fg`; phi 0 on a zero margin) matched 35 of 36 printed limits to four decimals. The one that did not is `(1, 97, 1, 1)` lower: printed 0.8736, mine 0.873672, which is the note's disclosed exclusion. F5 `(80, 2, 10, 8)` gives (-0.155356, -0.010249).
- **DEFF-Wilson by hand (attack 5, `probe/p7_deff.py`, fractions).** Engine against hand, largest difference 4.44e-16:
  - equal 6 x 5 (DEFF 4.72);
  - equal 10 x 3 (2.7407);
  - unequal 5,5,4,4,3,3,2,2,1,1 (3.6243);
  - all singletons (DEFF 1, the plain Wilson);
  - p = 0 and p = 1 on 5 x 4 (DEFF 4, `[0, 0.43448]` / `[0.56552, 1]`);
  - negative ICC, 6 x 2 one success each (estimate 0, `deff_floored_at_one`, typed in `detail.design_effect.reason`);
  - share exactly 0.20 (`wilson_deff`) and mean exactly 50 rows (`wilson_deff`).
  - Off the route: shares 0.267 and 51/251, both `case_share_above_grid`; one case, `insufficient_clusters`.
- **The coverage table reproduces.** `coverage_bar.py --deff-wilson --json` in `wt` gave `identical True` against `design/coverage_deff_wilson.json`, threshold 30, 115 s. From the JSON:
  - printed rows of 30 cases or more: 216, of which 162 are recorded rows, 26 of them below the bar, lowest 0.7635 (equal 30 x 50, TAU2 0.8, truth 0.98), printed `0.763` by the engine's float formatting, as everywhere else;
  - constant-setting rows of 30 cases or more: minimum 0.90675;
  - 12 constant-setting rows of 5-20 cases below the bar, lowest 0.80825;
  - all rows 0.13725 to 1.0, as T7 says.
  - T7 section 6's figures are all true of the JSON.
- **Item 0 (attack 7).**
  - With `docx`, `docxtpl` and `lxml` hidden: `compare --format json,html,docx --templates T2,T7`, `compare --format json,docx --templates T7`, `run --format json,html,docx --templates T1,T7,T8` and `run --format json,docx --templates T1` each gave rc 7, `--out` absent, no ledger, and the one line ending `nothing was written`.
  - With the extra, `run` printed `Next step: open the documents beside run.json (T1.html, T1.docx, T7.html, T7.docx, T8.html, T8.docx)`, exactly the files written.
  - `compare --templates T2,T7,T8 --format json,html,docx` wrote `T2.html, T7.*, T8.*` and printed the T2.docx line.
  - Paired criterion C2 on T1: the HTML row and the DOCX row are cell for cell identical (`not assessable`, `requires_compare`).
- **Rows 132 / 149 (attack 6).** `no_score_column` and `metric_not_compared` are in `output_schema_v1.json` (lines 497, 543, 860, 1554). A compare with C2 on `ppv` gave `not_assessable`, and T2 prints `not assessable metric_not_compared` and the sentence `(metric_not_compared)`.
- **Doctor.** `Next step: write criteria.yaml (...), then proofpack map --input test.csv --criteria criteria.yaml`. `map --help` lists `--input` and `--criteria`.

## Mutation (attack 4)

The repo's sweep: `scripts/mutation_sweep.py --marker day11` in `wt2` printed `56 planted, 56 killed, 0 survived; 1048 s`, the note's figure. It ran beside my mutant run, so the time is contended.

My own 14 mutants on repair-2 lines (`probe/p10_mut.py`) were each run against `-m day11 -x`. If a mutant survived that, it was run against nine render / stats files (`test_render_t1/t7/t8`, `test_e10_t2`, `test_bootstrap_carried`, `test_calibration`, `test_doctor_cli`, `test_e9_templates`, `test_bootstrap`). Each file was restored with `git checkout` afterwards; `git status` in `wt` was clean at the end.

| id | mutant | outcome |
|---|---|---|
| L1 | T7 legend row `ᵈ` dropped | killed (`test_a_run_on_the_lens_shape_...`) |
| L2 | T1 legend row `ᵈ` dropped | killed (the same) |
| L3 | `ᵈ` superscript mapped to "" | killed (`test_the_lens_in_route_shape_prints_the_mark`) |
| L4 | `MODEL_CARD_ANCHOR = "FDA_AIDSF_PERF_VALIDATION"` | **survived** (385 passed, 1 skipped) |
| L5 | `AIDSF_STATUS_ANCHOR = "FDA_AIDSF_MODEL_CARD"` | **survived** (385 passed, 1 skipped) |
| L6 | T8 prints `LONG_FORM_ITEMS` raw (the `{aidsf_draft}` slot) | killed (`test_e11_aidsf_header.py::test_no_docx_paragraph_..._qualifier[T8]`) |
| L7 | T2 prints `LONG_FORM_ITEMS` raw | killed (`test_a_moved_map_row_moves_every_month_on_t2`) |
| L8 | mark only below 30 cases | killed |
| L9 | mark first, not last | killed (`test_the_route_switches_at_five_cases_...`) |
| L10 | flag removed from the schema enum | killed outside day11 only (`test_calibration.py::test_the_assembled_document_validates_against_the_output_schema`) |
| L11 | doctor's next step `then proofpack licence install criteria.yaml` | **survived** |
| L12 | mark only on the `wilson_deff` route | killed |
| L13 | T7 description drops the `ᵈ` sentence | killed |
| L14 | the mark stripped from a calibration decile bin when the curve flag is added | **survived** (385 passed, 1 skipped) |

What the survivors mean:
- **L4 / L5** are equivalent on the committed map, where every AI-DSF row has one date. They are not equivalent on a map whose rows differ: the moved-map tests move every `FDA_AIDSF_*` row together, so neither anchor is pinned to its own row.
- **L11.** `test_doctor_names_only_commands_the_parser_has` inspects only that each `proofpack <word>` is a subcommand. A wrong subcommand passes it.
- **L14.** The repair note says "calibration decile bins call `proportion_ci`, so clustered bins carry it too". That is true at the tip (T8's decile cell printed `ᵇᶜᵈ`), but no test inspects it. A clustered decile bin printed without `ᵈ` would pass the suite.

All four are record-and-carry: the code at the tip prints correctly in each case.

## What I could not check

- **The `no_score_column` branch on a rendered page.** A prior table with no score halts H07 first, as lenses 1 and 2 found.
- **The day-10 sweep (37 mutants, about 23 minutes).** Not re-run; `-m day10` passed 262 / 262 inside the full run.
- **PowerShell 5.1.** All my figures are Git Bash and in-process Python.
- **The clustered AUROC difference, Brier, slope and O:E coverage.** Not measured. B1's table is proportion differences only.
- **The worst shape for B1 and B2.** I did not search for it.
- **The clustered-McNemar literature and Rao and Scott 1992.** Not fetched. Rao-Scott stays `[unverified]` on the page, correctly.

## Sentences I refused to write

- "Every clustered cell now carries its tier annotation." B1 refutes it for differences.
- "The McNemar p-values are correct." The arithmetic is; under clustering the test is not (B2).
- "Repair 2 closed lens 2's blockers." What I measured: every clustered proportion I rendered carries `ᵈ`, and every AI-DSF element I scanned carries the literal and follows its row. The Accept line still fails on differences.

Repro scripts and raw outputs are in `scratchpad/lens-E11-r3-fresh-attack/`:
- `probe/`: `p1_clustered_cli.py`, `p2_diff_cov.py`, `p3_scan.py`, `p5_own.py`, `p6_ledger.py`, `p7_deff.py`, `p8_item0.py`, `p10_mut.py`, `p11_sub_own.py`;
- outputs: `suite.txt`, `p2_out.txt`, `p2few_out.txt`, `p5_out.txt`, `p11_out.txt`, `p10_out.txt`, `sweep11.txt`, `cov_out.txt`.
