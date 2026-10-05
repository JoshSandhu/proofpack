# Lane E - build day 12 (E12, the R captures) - lens 5, cold fresh attack, at `174ed35` (E12 repair 4; pre `614edd2`; Monday 5 October 2026)

**FAIL. 4 blockers.**

Two blockers are mutants that survive the whole suite:
- **B1** is in the recorded-comparison gate that repair 3 added. DEC-12 (i) applies to it.
- **B2** is in the upload guard's new label, the line that repair 4 added.

Two blockers are shipped sentences that assert more than was run:
- **B3** is the guard's new docstring list of what it prints.
- **B4** is the header of `capture.R`. It still states the guarantee that repair 4 refused to write ten lines below.

Lens 4's four blockers are closed: I ran the mutants myself. The statistics are right: I re-derived DeLong and the recalibration fits with numpy only. With vectors of my own, a simulated job put no data line into any output. Every count in the repair note reproduces.

`capture.R` and the r-captures workflow have still never run. Gate 2 of section 10 is not met. F13 and F13b are `no_oracle_recorded` today, and both reasons start `[unverified until captured]`.

**Setup.** Three detached worktrees under `scratchpad/lens-E12-r5-fresh-attack/`:
- `wt174` (`174ed35`): the suite, lint, markers, the CLI, the perturbation probe and the simulated job;
- `wt614` (`614edd2`): `tests/test_e12_repair4.py` copied in;
- `wtm` (`174ed35`): the mutants, each applied alone and restored, with `git status --short` clean after every batch.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`.

Platform: Windows 11, Git Bash, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1. Every figure here was taken in Git Bash.

I committed, pushed, downloaded and installed nothing. I did not install R, and I fetched no web page. Every vectors file I wrote is my own synthetic data, not aSAH. This note is the only file I wrote outside the scratchpad. All three worktrees are removed.

## Blockers

| # | Blocker | Verbatim evidence | One-line repro |
|---|---|---|---|
| B1 | **The recorded-comparison gate checks the 16 F13 names one by one, but no test needs every name checked.** Mutant K11 changes `f13_recorded_outcome`'s loop `for name in F13_NAMES:` to `for name in F13_NAMES[:-1]:`, which skips `roc.test estimate 2`. It survives. The repository's record tests perturb only three names: `s100b auc` +2e-6, one name removed, and one R value changed. Under K11 the F13 row reads `suite_only`, and its reason says "recorded 16 values ... each within 1e-6" when one value is 1e-3 out. That is attack (2)'s case, a comparison that passes with a perturbed field, reachable under a one-line mutant that no test notices. It is lens 4 B2's class: an output of the gate that no test pins. | K11 survives `-m day12` (`148 passed, 9 skipped, 1998 deselected`, the same as unmutated) and the whole suite less `slow` (`2140 passed, 11 skipped, 4 deselected in 237.64s`, the same as unmutated). Input: the synthetic capture, with the record's `roc.test estimate 2` `engine` +1e-3 and the variable unset. **Unmutated:** `not_matched 6 0.0010000000000000009`, reason `r_capture_recorded_not_matched: ... outside tolerance: roc.test estimate 2`. **Under K11:** `suite_only`, `max_abs_deviation 5.551115123125783e-17`, reason `compared inside the r-captures job, not by this command: GitHub run 20261005 recorded 16 values of the engine at commit eeee... against pROC (proc_asah.json), max abs deviation 5.551115123125783e-17, each within 1e-6 as recomputed here ...`. Two narrower mutants are killed by the three cases that exist: K11b skips the `roc.test` names (`1 failed`) and K11c skips the `ndka` names (`1 failed`). | in `f13_recorded_outcome`, `F13_NAMES` -> `F13_NAMES[:-1]`; `python -m pytest -q -m "not slow"` |
| B2 | **The FA-B3 tests can tell only whether a whole vectors line appears in the guard's output, so a guard that prints most of a row passes them.** Mutant G11 is on the line repair 4 added: `label()` returns `"an entry not among the three names " + p.stem` for an entry outside the three names. It survives. The planted directory's problem line then puts the row number, outcome, y, the full s100b value and the integer part of ndka into the job log, which is public on this repository. That reopens FA-B3's class, a vectors row in the log. `test_fa_b3_the_upload_guard_prints_no_entry_name_outside_the_three` asserts `[ln for ln in lines if ln in out] == []`, which is whole lines only. | G11 survives `-m day12` (`148 passed, 9 skipped`) and the whole suite less `slow` (`2140 passed, 11 skipped, 4 deselected in 196.76s`). G12 (the name with commas as spaces) survives `-m day12` (`148 passed, 9 skipped`). Run on `up/`, holding the three JSON files and a directory named after my vectors' 8th data row (`8,Good,0,0.42424242000000001,42.424242`) with `a.json` inside. **Committed guard:** `r-upload-guard: an entry not among the three names: not a regular file`. **G11:** `r-upload-guard: an entry not among the three names 8,Good,0,0.42424242000000001,42: not a regular file`. Both exit 1. Repair 4's own G1 (the label prints the path) is killed: `2 failed`. | in `label()`, append `+ p.stem`; `python -m pytest -q -m day12` |
| B3 | **False sentence: the guard docstring's list of what it prints.** The docstring reads: "What it prints (E12 repair 4, lens 4 FA-B3): the three names above, those of the three it did not find, the error type of a file it could not read, and counts." The guard also prints the directory argument, in `r-upload-guard: N problem(s) in {directory}` and in `{directory} is not a directory`. A directory argument named after a data line puts that line on stdout, and the guard exits 0. The workflow passes the literal `upload`, so the job cannot reach this. The sentence is still false as written, the same standard lens 4 applied in B3. | Run on a directory named `8,Good,0,0.42424242000000001,42.424242` holding the three JSON files, with `PROOFPACK_ASAH_VECTORS` naming my vectors. Output: `r-upload-guard: 0 problem(s) in 8,Good,0,0.42424242000000001,42.424242`, exit 0. With `<that name>/x`: `r-upload-guard: 8,Good,0,0.42424242000000001,42.424242\x is not a directory`, exit 2. | `python scripts/r_upload_guard.py "<a data line>"` |
| B4 | **False sentence (hard rule): `capture.R`'s header, lines 7-10.** It says: "The script stops unless the environment variable PROOFPACK_ASAH_VECTORS names a file outside the working directory". The check was never run (no R). Repair 4's comment at lines 59-65 of the same file says the check "does not resolve a symbolic link at the file itself". The repair note refuses the sentence "`capture.R` keeps the vectors outside the checkout". Repair 4 rewrote the README twin of this claim (L4-FA-N7) and the line-59 twin (RG-B2 (b)), but left this one. I transcribed the check into Python, which is an emulation and not R: `normalizePath(dirname(path))` as `os.path.realpath(os.path.dirname(path))`, compared with the normalised `getwd()`. Then I gave it a hard link in the runner-temp stand-in pointing at an empty file inside the checkout stand-in. The check passed, and a `"wb"` write through the path landed in the checkout. A symbolic link would be the cleaner case, but `os.symlink` is refused on this machine (`WinError 1314`). | Emulation output: `check stops: False`, then `bytes at the checkout path: b'row,outcome,y,s100b,ndka\n1,Good,0,0.13,6.0\n'`. Under the hard rule the sentence fails regardless of the emulation: it asserts what an unrun check guarantees. | `sed -n 7,10p fixtures/r/capture.R` beside `sed -n 59,65p fixtures/r/capture.R` |

Repairs, each small:
- **B1:** parametrise the record perturbation (+2e-6 on `engine`) over all 16 `F13_NAMES`. K11 must then fail. Under DEC-12 (i) this repair is lensed again.
- **B2:** for each plant, assert the guard's per-entry and count lines equal exact expected strings, or that no field value of the planted row (for example `0.42424242`) appears. G11 and G12 must then fail.
- **B3:** add the directory argument to the list, or stop printing it.
- **B4:** rewrite lines 7-10 to name what the check inspects, as lines 59-65 already do.

## Non-blocking (record and carry)

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **K14 survives the whole suite.** `worst if not problems else None` became `worst`, in `f13_recorded_outcome`'s `not_matched` return. A `not_matched` row with a problem then prints the maximum over the names that passed instead of `None`. The status and the exit code are unchanged. This is lens 4 B2's class on the failing branch. I record it rather than block on it, because the row still fails. | `2140 passed, 11 skipped, 4 deselected`. Input: `roc.test p.value` `engine` `"0.5"` and `s100b auc` +4e-7. Unmutated: `not_matched None`. K14: `not_matched 4.0000000001150227e-07`. |
| N2 | **K9 survives the whole suite.** `_json_number` accepts a JSON `true` as `1.0`. That needs an R value of exactly 1.0 to pass, for example an AUC of 1. | `2140 passed, 11 skipped, 4 deselected` |
| N3 | **C2 survives `-m day12`.** `r_f13_compare.py` stops refusing an unreadable vectors file by name. It then prints `proc_asah.json is absent` and exits 1. The exit is equivalent; the message is wrong. | `148 passed, 9 skipped` |
| N4 | **Carried survivors, re-measured at `174ed35`, `-m day12`, each `148 passed, 9 skipped`:** M14 (the local `_check_header` deleted; L4-FA-N3); M7 (`r_f13_compare.py` exits 0; L4-FA-N2). These are equivalent in exit code: G7 (`.csv` names allowed: any extra name breaks the three-name rule), G9 (no `strip()`: R writes LF) and K5 (bool in the record checks: `str(True)` matches no expected value). | - |
| N5 | **README "Committing a capture" step 4 under-counts the tests the commit must change.** It cites lens 1's 8. I copied my capture-shaped three JSON files into `fixtures/r/`, left the variable unset and ran the suite less `slow`: `11 failed, 2136 passed, 4 skipped, 4 deselected`. One of the eleven crashes rather than asserts: `test_ap3_repair3.py::test_the_check_classes_are_the_fixtures_rows_classes` calls `row.oracle(...)` and catches only `OracleAbsent`, and F13 now raises `ComparedInRunner`. `test_t12.py::test_unverified_markings_survive_to_the_page` is among them: it asserts F13's `[unverified until captured]` span. The other nine: `test_ap3_repair2.py` (2), `test_fixtures_cmd.py` (6), `test_t12.py::test_golden_t12_matches_the_committed_render`. In `src/`, only `compare_row` calls `row.oracle`, and it catches `ComparedInRunner`. | three JSON files in `fixtures/r/`; `python -m pytest -q -m "not slow"` |
| N6 | **In the job's shape, row F13 reads `matched` where the pytest fails.** With `var_delong`, `n_cases` or `n_controls` +5e-7, the row reads `matched` under its single absolute 1e-6. The pytest fails, by design: variance is also relative 1e-6 and counts are exact. The job still fails at the pytest step. | `perturb.py`: `('failed', 'passed', 'matched')` for each of the six |
| N7 | **Carried unchanged:** tag pins (need 54); the F13b row taking string numbers (L3-FA-N5); `present_compared_in_rows_f13_f13b` with F13 `suite_only` (L4-FA-N5); the HEAD sentence with modified `src/` (L4-FA-N8); and the DEC-77 workflow test's name-only inspection (L4-FA-N9). | - |

## What I could not break (with figures)

**Suite and lint at `174ed35`.** Each figure equals the repair note's:

| Run | Result |
|---|---|
| full suite `-rs` (`PROOFPACK_REQUIRE_DOCX=1`, TR39 file, variable unset) | `2145 passed, 10 skipped in 272.26s`, exit 0 |
| skip lines | the same four as the note: `[3] r_vectors_not_committed_dec77 ...`, `[5] r_captures_not_captured: F13b ...`, `[1] r_captures_not_captured: F13 recorded (absent: fixtures/r/proc_asah.json, fixtures/r/f13_engine_comparison.json)`, and `[1] test_doctor_cli.py:57` |
| `--collect-only` | `2155 tests collected` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `315 files already formatted` |
| `-m day12` / `-m day11` / `-m day10` | `148 passed, 9 skipped, 1998 deselected` / `144 passed, 2011 deselected` / `262 passed, 1893 deselected` |
| `-m "day12 or fixture or ap3"` | `395 passed, 9 skipped, 1751 deselected` |
| the five day-12 test files | `120 passed` |
| `tests/test_e12_repair4.py` copied into `614edd2` | `10 failed, 10 passed in 1.90s`, the note's figure |
| `fixtures --offline --r-captures` | exit 0; `rows 46: matched 34, not matched 0, no oracle recorded 2, ...`; the all-absent line unchanged; `unverified` 37 times; F13 and F13b `no_oracle_recorded`, both reasons starting `[unverified until captured]` |
| other commands | `capture_fixture_oracles.py --check` exit 0; `r_capture_drift.py` `0 difference(s) above 1e-12`; `doctor --offline` ends `Next step: write criteria.yaml` |

A `git grep` outside `handoffs/` for "verified against R", "matches pROC", "agrees with R", "checked against R" and similar found only the README's "be checked against R by code", which states a purpose.

**Lens 4's blockers are closed by execution** (`-m day12`):
- B1: M20 `2 failed`, both `test_fa_b1_...[f13_engine_comparison.json ...]`.
- B2: M18 `1 failed`, `test_fa_b2_the_suite_only_row_reports_the_largest_recorded_deviation`.
- B3: G1 (label = path) `2 failed`. The committed guard no longer prints a planted name.
- B4: the sentence is gone; `test_fa_b4_...` reads 80 rows.

Other mutants killed:
- the record checks: K1 (R value not checked against `proc_asah.json`), K2 (the tolerance field), K3 (10x tolerance), K4 (the HEAD sentence), K6 (the `engine_sha` hex check), K7 (the record's schema), K12 (missing numbers tolerated), K17 (`suite_only` -> `matched`, `8 failed`);
- the job shape and the loader: K8 (the vectors sha not compared), K13 (the job-shape `_check_header`), K15 (the vectors sha without CRLF folding), K16 (the y in {0,1} check, `5 failed`);
- the guard: G5 (extra entries allowed), G6 (`missing` never computed), G8 (the header not a needle), G10 (always exit 0, `12 failed`).

**The statistics** (`probe/rederive.py`: numpy and `math` only; the engine is only called to be compared):
- **DeLong 1988 structural components.** psi = 1, 1/2 or 0 by explicit loops; V10 and V01; S10/(m-1) and S01/(n-1); var = S10/m + S01/n. The Wald interval is truncated to [0, 1].
- **The paired test.** The covariance comes from the placements: z = (A1-A2)/sqrt(v1+v2-2cov), p = 2 Phi(-|z|). The difference interval is not truncated.
- **Data.** Seven tied data sets (n/cases 113/41, 60/24, 41/12, 200/70, 35/8, 113/72 with ndka negated to give an AUC below 0.5, and 25/5), against `fx.f13_engine_values(..., with_conf_int=True)`.
- **Worst deviations.** `roc.test statistic 1.998e-15`, `p.value 2.706e-16`, `var_delong 1.735e-18`, `ci_delong 1.110e-16`, `conf.int 1.665e-16`; counts and AUCs `0`. An AUC below 0.5 is reported as it is, never flipped, which is what pROC does with `direction = "<"` given explicitly.
- **F4, my own Newton fit.** Joint intercept `0.49977163424518545`, slope `1.1945124796435689`; SEs `0.5950556263256326` / `0.5617458146727721`; offset-only intercept `0.45623046546120943`, SE `0.5536866258585561`; Brier `0.158755`; C `0.8541666666666666`. All 13 `F13B_NAMES` engine values are within `2.220e-16`.
- **Like with like.** `val.prob Intercept` and both `glm joint` intercepts go with the engine's joint intercept. Both `glm offset` intercepts go with `intercept_large`. The SEs are compared only with the `epsilon 1e-14` fits.

**The comparison, perturbed** (`probe/perturb.py`: the repository's own test functions and report rows, called in process on the synthetic capture copied into `fixtures/r/`):
- **The job shape** (variable set to vectors outside the capture directory). Each of the 16 names in `proc_asah.json` at +2e-6 and at -2e-6: the comparison test `failed` and the row `not_matched`. At +5e-7: the test passed and the row matched, except `var_delong` and the counts, where the test fails (N6). Each name deleted: `failed` / `not_matched`, never a skip. `vectors_sha256` set to 64 zeros: row `not_matched`.
- **The local shape.** Each name's recorded `engine` at ±2e-6: `failed` / `not_matched`. At +5e-7: `passed` / `suite_only`. Each name deleted: `failed` / `not_matched`.
- **F13b.** Each of the 13 names at ±2e-6: `failed` / `not_matched`. At +5e-7: passed / matched. Each deleted: `failed` / `not_matched`. F4 `sha256` set to 64 zeros: the sha test `failed` and the row `not_matched`.
- **Absent.** Every comparison skips with the typed reasons above, and the report says `no_oracle_recorded` with `[unverified until captured]`.

**A simulated job with my own vectors** (`probe/mkjob.py`). The data: 113 rows, 41 cases, scores to 2 decimals with ties, and row 8 carrying the sentinels `0.42424242` / `42.424242`. `proc_asah.json` and `rms_val_prob_f4.json` came from my code. `GITHUB_SHA` was HEAD and `GITHUB_RUN_ID` was `4242`. In order:
- drift: exit 0;
- `r_f13_compare.py`: `row F13 matched, max abs deviation 1.1102230246251565e-16, 16 values`, exit 0;
- `pytest -m day12 -rs`: `157 passed, 1998 deselected`, 0 `SKIPPED`;
- `fixtures --offline --r-captures`: `matched 36`, F13 and F13b `matched`;
- guard: `0 problem(s) in upload`, exit 0.

A `grep` for the two sentinels over the job log, the pytest output, the report directory, `upload/` and `fixtures/r/` found 0 files. With the variable then unset: F13 `suite_only 1.1102230246251565e-16`, "the engine commit is this checkout's HEAD"; `day12` `154 passed, 3 skipped`.

**`capture.R`, read line by line against my reading of pROC and rms** (no manual fetched):
- `levels = LEVELS, direction = DIRECTION` are explicit and `stopifnot`-checked;
- `ci.auc(method = "delong", conf.level = 0.95)` is unpacked as (lo, mid, hi);
- `var` is pROC's own generic, `method = "delong"`;
- `roc.test(..., method = "delong", paired = TRUE)`;
- `val.prob(p, y, pl = FALSE)` is given probabilities, and the `glm` fits take `qlogis(p)`;
- every number goes through `sprintf("%.17g")`;
- `to_json` stops on any vector longer than 1, so no column can be written into a JSON file;
- the F4 sha256 is taken on `writeBin(f4_raw)`, the same bytes `rawToChar(f4_raw)` parses.

**The workflow:**
- `permissions: contents: read`;
- no `secrets.`, no `pull_request_target`, no `actions/cache`;
- `enable-cache: false`;
- no `run` line with `git add`, `git commit` or `git push`;
- the upload path is `upload/` only, after the guard.

## What I could not check

- **Any run of `capture.R` or the r-captures job.** There is no R here, and `174ed35` is not pushed. That leaves these unchecked:
  - whether rms's `lrm.fit` inside `val.prob` converges to within 1e-6 of the MLE at the snapshot's version and default tolerance. Older rms stopped on a -2LL change below 0.025, which could leave the intercept about 1e-5 off. That would fail loudly, not silently;
  - pROC's DeLong `ci.auc` truncation and `roc.test` `conf.int`;
  - `tools::sha256sum` in R 4.5.1;
  - git `safe.directory` inside the container;
  - setup-uv inside `rocker/r-ver:4.5.1`.
- **A symbolic link.** `os.symlink` is refused here (`WinError 1314`), so B4 uses a hard link, and only in a Python emulation of the R check.
- **Real aSAH figures.** Under DEC-77 they exist only on the runner.
- **PowerShell 5.1 figures.** I took none.

## Sentences I refused to write

- "The guard prints no part of a vectors row": B2 and B3.
- "Every F13 name is pinned in the recorded comparison": B1.
- "`capture.R` stops on any path inside the checkout": B4; never run.
- "The aSAH rows cannot leave the runner", "F13 matches pROC", "Gate 2 is met", "E12 passed".
