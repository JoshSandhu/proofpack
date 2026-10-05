# Lane E - build day 12 (E12, the R captures) - lens 4, cold fresh attack, at `614edd2` (E12 repair 3, DEC-77; pre `e6ad3c8`; Monday 5 October 2026)

**FAIL. 4 blockers.**

Two blockers are tests that cannot fail on the repair's new recorded-comparison gate (DEC-12 (i) territory). Two are false sentences, each falsified by a run.

- **B1.** Lens 3 B2's class is reopened for the file the orchestrator named, `f13_engine_comparison.json`. A mutant survives the whole suite. Under it, a corrupt committed comparison file makes row F13 `no_oracle_recorded`, with the reason "are not both committed". `proofpack fixtures` then exits 0, where the committed code exits 6.
- **B2.** The maximum deviation that the F13 `suite_only` row prints is pinned by no test. A mutant that reports `0.0` in place of `8.999999999703689e-07` passes the whole suite.
- **B3.** The `scripts/r_upload_guard.py` docstring says it prints "never a line of the vectors". I planted a file whose name is a vectors data line, and the guard printed that line.
- **B4.** `fixtures.py`, the handoff and R3-3 say the loader reads the vectors "never from `fixtures/r/`". With `PROOFPACK_ASAH_VECTORS=fixtures/r/asah_vectors.csv`, it read all 113 rows from there and `r_f13_compare.py` exited 0.

The rest held. The statistics are right: I re-derived DeLong (1988 structural components) and the recalibration fits myself, numpy only. The worst deviation from the engine was `1.998e-15` for F13 and `2.220e-16` for F13b. I tried to get the aSAH rows into an artefact, a log line, a cache or a commit through the code as committed, and they did not get there, except by B3's planted file name. Lens 3's B1 and B2 are closed: their mutants and four new variants of mine each fail a test. Every count in the repair note reproduces.

`capture.R` and the r-captures workflow have still never run. Gate 2 of section 10 is not met. Today F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]`.

Setup: detached worktrees under `scratchpad/lens-E12-r4-fresh-attack/`:
- `wt614` (`614edd2`): the suite, lint, markers and mutants;
- `wt6ad` (`e6ad3c8`): the before figures, and the new tests copied in;
- `wtjob` (`614edd2`): a simulated job;
- `wtm` (`614edd2`): the gate and loader mutants, and B1's demonstration.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Platform: Windows 11, Git Bash, CPython 3.14.6. I committed, pushed, downloaded and installed nothing, I did not install R, and I fetched no web page. The vectors I wrote are my own synthetic rows, not aSAH. This note is the only file I wrote outside the scratchpad. All four worktrees are removed.

## Blockers

| # | Blocker | Verbatim evidence | One-line repro |
|---|---|---|---|
| B1 | **Outside the job, an unreadable `f13_engine_comparison.json` turning into "absent" is pinned by no test.** This is lens 3 B2's class (and lens 1 FA-B2's), reopened for the file that orchestrator item 3 names. The `f13_oracle` docstring says "an unreadable ``proc_asah.json`` or :data:`R_COMPARISON_FILE` is :class:`OracleFileUnreadable`". The code does that, but the only tests that make the comparison file unreadable read the pytest outcome: `test_outside_the_job_an_unreadable_needed_file_fails_the_recorded_comparison[...]`. That outcome is `failed` under the mutant as well, because `no_oracle_recorded` is not `suite_only`. `proc_asah.json`'s half of the same loop is pinned, by `test_the_loader_names_a_capture_path_that_is_a_directory_unreadable`. | Mutant M20, in `f13_oracle`'s local branch: `for rel in (R_CAPTURE_FILES[0], R_COMPARISON_FILE):` became `for rel in (R_CAPTURE_FILES[0],):`. Results: whole suite less the 4 `slow` tests `2120 passed, 11 skipped, 4 deselected`; `-m day12` `128 passed, 9 skipped`. Setup: the synthetic capture in `fixtures/r/`, with `f13_engine_comparison.json` written as `{"values": `. **Unmutated:** `exit 6`, `rows 46: matched 35, not matched 1, ...`, `F13 \| not_matched \| oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (JSONDecodeError)`. **Under M20:** `exit 0`, `rows 46: matched 35, not matched 0, no oracle recorded 1, ...`, `F13 \| no_oracle_recorded \| [unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and the engine comparison the r-captures job records beside it (fixtures/r/f13_engine_comparison.json) are not both committed; ...`. | apply M20; corrupt `fixtures/r/f13_engine_comparison.json`; `python -m proofpack.cli fixtures --offline --out D --r-captures` -> exit 0 |
| B2 | **The maximum deviation printed in the `suite_only` F13 row (`max_abs_deviation` and the reason) is a number no test pins.** `test_dec77_outside_the_job_f13_is_suite_only_...` asserts `max < 1e-12`, and `0.0` satisfies that. This is the repair's new gate code (`f13_recorded_outcome`), so DEC-12 (i) applies. | Mutant M18 deleted `worst = max(worst, dev)`. Results: whole suite less `slow` `2120 passed, 11 skipped, 4 deselected`; `-m day12` `128 passed, 9 skipped`. Input: the synthetic record with `values["s100b auc"]["engine"] += 9e-7`. Unmutated: `suite_only 8.999999999703689e-07`. Under M18: `suite_only 0.0`. | `probe/m18.py` with and without M18 |
| B3 | **False sentence (DEC-77 log-line route).** The `scripts/r_upload_guard.py` docstring says: "It prints file names and counts, never a line of the vectors." The guard prints every name in `upload/`. When a name is a vectors data line, the guard writes that line to the job log, and on this public repository the log is public. `tests/test_e12_repair3.py::test_dec77_upload_guard_exits_1_on_each_plant` checks only that `"row,outcome"` does not appear outside the header. | `upload/` held the three synthetic JSON files plus an empty file named after the synthetic vectors' fifth data line, with `PROOFPACK_ASAH_VECTORS` naming those vectors. The guard printed: `r-upload-guard: the files are ['5,Good,0,0.13,6.0', 'f13_engine_comparison.json', 'proc_asah.json', 'rms_val_prob_f4.json'], not exactly [...]` and exited 1. | `touch "upload/<a data line>"; python scripts/r_upload_guard.py upload` |
| B4 | **False sentence.** `src/proofpack/fixtures.py` (the comment on `R_VECTORS_ENV`) says ":func:`load_r_captures` reads the vectors from that file only, never from ``fixtures/r/``". The handoff's DEC-77 paragraph and decision R3-3 repeat "never from `fixtures/r/`". The loader reads whatever path the variable names. Unlike `capture.R`, nothing in Python refuses a path inside the checkout. `.gitignore` does keep the file out of `git status`; I measured that. | In `wtjob`, the 113-row synthetic vectors were copied to `fixtures/r/asah_vectors.csv`, with `PROOFPACK_ASAH_VECTORS=fixtures/r/asah_vectors.csv`. Results: `vectors_path fixtures\r\asah_vectors.csv \| present (..., '$PROOFPACK_ASAH_VECTORS (asah_vectors.csv)', ...) \| unreadable () \| <aSAH vectors withheld (DEC-77): 113 rows>`; row F13 `matched`; `r_f13_compare.py` `row F13 matched, ...`, exit 0. | `PROOFPACK_ASAH_VECTORS=fixtures/r/asah_vectors.csv python -c "from proofpack import fixtures as fx; print(fx.load_r_captures().vectors_path)"` |

Repairs:
- **B1:** a test that makes `f13_engine_comparison.json` unreadable (corrupt, and a directory) with the vectors not read, and asserts row F13 `not_matched` and `oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (`. M20 must then fail.
- **B2:** assert the row's `max_abs_deviation` equals the recomputed maximum on an input where it is not 0, for example the 9e-7 edit above.
- **B3 and B4:** sentence fixes are enough. Alternatively, change the code: the guard prints no name that it has not checked against the vectors, and the loader refuses a path under the checkout. B1 and B2 touch the comparison gate, so the repair is lensed again (DEC-12 (i)).

## Non-blocking (record and carry)

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **M15 survives the whole suite:** the loader's `proc_sha = lf_sha256(raw_json)` became a plain `sha256`. That is not equivalent on this machine. `core.autocrlf` is `true`, there is no `.gitattributes`, and `fixtures/newcombe_table2.json` is `w/crlf`. A committed `proc_asah.json` checked out as CRLF would mismatch the LF sha the runner records. The committed code handles it, but no test feeds a CRLF `proc_asah.json`. It would fail loudly (`r_capture_input_mismatch`), not silently. | `2120 passed, 11 skipped, 4 deselected`; `git ls-files --eol` -> `i/lf w/crlf fixtures/newcombe_table2.json` |
| N2 | **M7 survives the whole suite:** `r_f13_compare.py` returns 0 when the row is not matched. The docstring sentence (exit 1) is true: on a stale `proc_asah.json`, the script printed `row F13 not_matched, ... 0 values` and exited 1. No test feeds a not-matched input. In the job, the next step (`pytest -m day12`) still fails. | `2120 passed, 11 skipped, 4 deselected` |
| N3 | **M14 survives the whole suite:** the local branch's `_check_header(caps.proc, "F13")` was deleted. A `proc_asah.json` with a wrong `schema` or `fixture`, plus a record that matches its sha, would still read `suite_only`. | `2120 passed, 11 skipped, 4 deselected` |
| N4 | **M5 survives `-m day12`** (the guard's `*asah*vectors*` / `.csv` name test disabled). It is equivalent in exit code: any such file also breaks the exact-three-names rule. M23 (`__str__ = __repr__` deleted) is equivalent, because `dict` has no `__str__` of its own. M24 (the parse error message carrying the original exception) is not observable: the loader records only the type name. | `128 passed, 9 skipped` each |
| N5 | **The `--r-captures` status token reads `present_compared_in_rows_f13_f13b` outside the job, where row F13 compared nothing** (`n_values_compared` 0, `suite_only`). It comes from `_deviations_read` counting a `suite_only` F13 as 16. The row's own reason is explicit ("compared inside the r-captures job, not by this command"), and it does not call the result a match. | `wtjob` local run: `r-captures: present_compared_in_rows_f13_f13b - ... row F13 suite_only, row F13b matched; ...` |
| N6 | **The all-absent line is kept byte for byte (DEC-43):** "F13 and F13b stay 'no oracle recorded' until fixtures/r/capture.R's output is committed". Under DEC-77 that is no longer enough for F13: committing `capture.R`'s two files without `f13_engine_comparison.json` leaves F13 `no_oracle_recorded`. | `test_the_skip_reasons_are_the_typed_strings`'s "synthetic capture less `f13_engine_comparison.json`" case |
| N7 | **`capture.R`'s check rests on two sentences that were not run (no R here).** Line 59-60: "so that no git command and no upload of the checkout can reach it". The README: "it stops when that variable ... names a file inside the working directory". By reading (not run): the check normalises `dirname()` only. A `PROOFPACK_ASAH_VECTORS` that is a symlink outside the checkout, pointing to a file inside it, passes the check, and `file(path, "wb")` then writes through the link into the checkout. The job creates no such link. | reasoned from `capture.R` lines 65-69, 125-128; not run |
| N8 | **R3-N3 widened:** when HEAD equals the record's engine commit but tracked `src/` files are modified (`git_sha()` reports "tracked files modified"), the F13 reason still says "the engine commit is this checkout's HEAD". | read in `f13_recorded_outcome` / `git_sha` |
| N9 | **Carried unchanged:** the actions and container are pinned by tag, not sha (`actions/checkout@v4`, `astral-sh/setup-uv@v6`, `actions/upload-artifact@v4`, `rocker/r-ver:4.5.1`). The attack list calls that a blocker; earlier lenses carried it to Josh as a decision, and I keep that grading. R3-N5 (the DEC-77 workflow test inspects names only): a planted step `cat "$RUNNER_TEMP"/*/*.csv` names none of `PROOFPACK_ASAH_VECTORS`, `asah_vectors` or `dec77`. I read that from the test's regex; I did not plant it. The F13b report row still takes a string number as `matched` (L3-FA-N5): all 13 `F13B_NAMES` written as strings read `matched` in the row and FAILED the pytest. | - |

## What I could not break (with figures)

**Suite and lint, `614edd2`.** Every figure matches the repair note:

| Run | Result |
|---|---|
| full suite (`PROOFPACK_REQUIRE_DOCX=1`, TR39 file, vectors variable unset) | `2125 passed, 10 skipped in 259.67s` |
| skip lines | `[3] ... r_vectors_not_committed_dec77: F13 needs the aSAH vectors, which exist only inside the r-captures job (PROOFPACK_ASAH_VECTORS is not set)`; `[5] ... r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)`; `[1] ... r_captures_not_captured: F13 recorded (absent: fixtures/r/proc_asah.json, fixtures/r/f13_engine_comparison.json)`; `[1] tests\test_doctor_cli.py:57: write access cannot be revoked for this user` |
| `--collect-only` | `2135 tests collected` |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `312 files already formatted` |
| `-m day12` | `128 passed, 9 skipped, 1998 deselected` |
| `-m day11` | `144 passed, 1991 deselected` |
| `-m day10` | `262 passed, 1873 deselected` |
| `-m "day12 or fixture or ap3"` | `375 passed, 9 skipped, 1751 deselected` |
| `-m day12` at `e6ad3c8` (before) | `82 passed, 8 skipped, 1998 deselected` |
| `fixtures --offline --r-captures` today | `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`; F13 and F13b `no_oracle_recorded`, reasons starting `[unverified until captured]` |

A grep of `.py`, `.md`, `.html`, `.json` and `.yml` outside `handoffs/` for "verified against R", "matches pROC", "matched against R", "agrees with R" and "checked against R" found only the README's "be checked against R by code" (a purpose) and `f4_expected.json`'s "are to be compared against". No damage outside day 12: day11, day10 and the combined marker equal the note's before and after figures.

**The statistics** (`probe/rederive.py`, numpy and `math`; no repository code in the references):
- DeLong 1988: psi = 1, 1/2, 0 by explicit loops; V10 and V01; S10/(m-1) and S01/(n-1); var = S10/m + S01/n.
- Wald interval truncated to [0, 1].
- Paired: the covariance from the placements, z = (A1 - A2)/sqrt(v1 + v2 - 2 cov), p = 2 Phi(-|z|).
- Six data sets with heavy ties (n/cases 113/39, 60/24, 41/12, 200/70, 35/8, 113/40), against `fx.f13_engine_values`. The worst deviations: `roc.test statistic 1.998e-15`, `p.value 6.661e-16`, `var_delong 8.674e-19`, `ci_delong_lo/hi 1.110e-16`, and counts and AUCs `0`.
- F4, my own Newton fit:
  - joint intercept `0.49977163424518545`, slope `1.1945124796435689`;
  - SEs `0.5950556263256326` / `0.5617458146727721`;
  - offset-only intercept `0.4562304654612094`, SE `0.5536866258585561`;
  - Brier `0.158755`, C `0.8541666666666666`.
  - All 13 `F13B_NAMES` engine values are within `2.220e-16`.
- Like is compared with like: `val.prob Intercept`, `glm joint (Intercept)` and `glm joint tight (Intercept)` go with the engine's joint intercept; both `glm offset` intercepts go with `intercept_large`.
- I emulated R's `glm.fit` IRLS at its default `epsilon = 1e-8` (mustart (y+0.5)/2; the relative-deviance stop). It stopped after 5 / 4 iterations. Its distance from the exact MLE: intercept `7.636e-10`, slope `1.828e-09`, offset intercept `3.331e-16`. So the default-convergence `glm` fields should sit well inside 1e-6 [this is an emulation; R has not run].

**The comparison test, perturbed** (`probe/perturb.py`, `probe/perturb_b.py`: the repository's own test functions and report rows, called in-process):
- **Job shape** (the variable set to the synthetic vectors). Each of the 16 `F13_NAMES` in `proc_asah.json` at +2e-6 and -2e-6: the F13 comparison test `failed`, row `not_matched`. At +5e-7: the test passed and the row matched, except `var_delong` (relative 1e-6) and the counts (exact), where the test failed by design. Each name deleted: `failed` / `not_matched`, never a skip.
- **Local shape.** Each name's recorded `engine` at +2e-6: `failed` / `not_matched`. At +5e-7: `passed` / `suite_only`. Each name deleted from the record: `failed` / `not_matched`.
- **F13b.** Each of the 13 names at ±2e-6: `failed` / `not_matched`. At +5e-7: passed / matched. Deleted: `failed` / `not_matched`. F4 `sha256` `0`x64: the sha test FAILED and the row read `not_matched`.

**A simulated job with vectors that are not the tests' synthetic ones.** This is the case the repair note's simulation could not see, because it used the same synthetic file at the variable's path. Setup: 113 rows, 41 cases, s100b and ndka to 2 decimals with ties; `proc_asah.json` from my own DeLong code; `GITHUB_RUN_ID=99`; `GITHUB_SHA=HEAD`. Results:
- `r_f13_compare.py`: `row F13 matched, max abs deviation 4.440892098500626e-15, 16 values`, exit 0.
- `pytest -q -m day12 -rs`: `137 passed, 1998 deselected` (no SKIPPED).
- With the variable then unset: `fixtures --offline --r-captures` gives F13 `suite_only` with "the engine commit is this checkout's HEAD", F13b `matched`, exit 0.

**DEC-77 leak routes I tried**, sentinel s100b `0.42424242` and ndka `42.424242` planted in a vectors row:
- (A) The vectors edited after the capture (sha mismatch): `3 failed, 134 passed`; `r_f13_compare.py` exit 1. Sentinel hits in either output: 0.
- (B) The sha made consistent, the values stale: `3 failed, 134 passed`. Sentinel hits with the workflow's flags: 0. With `-l --tb=long` added: 0, and no `array([` line.
- `capture.R`'s `cat()` lines print paths, the row count and four aggregates.
- No `actions/cache`, and setup-uv has `enable-cache: false`.
- No step writes to the repository. The token is `contents: read`. There is no secret and no `pull_request_target`.
- `.gitignore` hides `fixtures/r/asah_vectors.csv` from `git status`; I measured that in B4's run.
- The guard caught a data line inside a JSON file and the header inside a JSON file (the repair's tests). B3 is the route I found.

**Lens 3's blockers are closed by execution.** Each mutant below was run with `-m "day12 or fixture or ap3"`, from a baseline of `375 passed, 9 skipped`:
- L1 (the loader's vectors `unreadable.append` -> `pass`): `4 failed`;
- G3a (the gate ignores an unreadable comparison file): `6 failed`;
- my G3c (the recorded gate skips on any unreadable file): `6 failed`;
- my R4 (the runner gate skips when the named path is not a file): `6 failed`;
- my R5 (`_f13_rows` skips when the vectors were not read): `4 failed`, the four vectors job-shape cases;
- my R6 (the runner gate skips when `proc_asah.json` is absent): `4 failed`.

**Other mutants killed** (`-m day12`):
- guard: M1 (header not a needle), M2 (no vector lines read), M3 (extra names allowed), M4 (always exit 0);
- `r_f13_compare.py`: M6 (no refusal without the variable), M8 (`--engine-sha` ignored);
- record checks: M9, M10, M11, M12 (the vectors sha, rows, schema and engine-sha checks), M13 (string numbers accepted);
- M16 (`_deviations_read` reverted), M17 (`r` written as the engine value), M19 (problems ignored), M21 (an absent record treated as present), M22 (O1-like: unreadable vectors read as absent in the job shape);
- M25 (a tolerance of up to 1e-3 accepted).

**`capture.R`, read line by line:**
- `levels = LEVELS, direction = DIRECTION` are explicit and `stopifnot`-checked;
- `ci.auc(method = "delong", conf.level = 0.95)`; pROC's own `var(method = "delong")`;
- `roc.test(..., method = "delong", paired = TRUE)`;
- `val.prob(p, y, pl = FALSE)` is given probabilities;
- every number goes through `sprintf("%.17g")`;
- the F4 sha256 is taken on `writeBin(f4_raw)`, the bytes `rawToChar` parses.

None of the attack list's blocker items is present.

## What I could not check

- Any run of `capture.R` or of the r-captures job (no R here; `614edd2` is not pushed). That leaves unchecked:
  - setup-uv and `uv python install` inside `rocker/r-ver:4.5.1` (R3-N4);
  - `tools::sha256sum` in R 4.5.1;
  - `conf.int` on pROC's paired DeLong test;
  - whether `lrm.fit` inside `val.prob` converges to within 1e-6 of the MLE at its default tolerance (I emulated `glm` only);
  - the rms and pROC versions the snapshot installs.
- Real aSAH figures. Under DEC-77 they exist only on the runner, and I used synthetic rows.
- PowerShell 5.1 figures: every figure here was taken in Git Bash.

## Sentences I refused to write

- "The aSAH rows cannot leave the runner." B3 is a route by name. The job has never run.
- "Lens 3's blockers are closed, so the recorded comparison is pinned." B1 reopens the class for the comparison file.
- "F13 matches pROC" and "Gate 2 is met": nothing has been compared with R.
