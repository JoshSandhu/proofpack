# Lane E - build day 12 (E12, the R captures) - lens 3, cold fresh attack, at `adcbcc3` (repair 2; pre `6928511`; Monday 5 October 2026)

**FAIL. 2 blockers.**

Both blockers are lens 2 B1's class reproduced with a new input: a present but unreadable `fixtures/r/asah_vectors.csv`. The committed code handles that file correctly today. Unmutated, the F13 row reads `not_matched | oracle_file_unreadable: fixtures/r/asah_vectors.csv (ValueError)` and the three F13 comparisons FAIL. But no test feeds an unreadable vectors file anywhere. Two mutants survive the whole `day12 or fixture or ap3` selection:
- one in the test gate (repair 2's code);
- one in the `src` loader (build item 3).

Under either mutant the F13 comparisons skip, with a reason that calls the file absent. The day-12 module docstring sentence that repair 2 added, "neither gate skips when a file it needs is unreadable", is false of the test it describes.

Everything else lens 2 raised is closed by execution (figures below). The statistics are right. I re-derived DeLong from the 1988 structural components and the recalibration by my own Newton fit, numpy only. Worst deviation from the engine: 2.66e-15 on nine data sets for F13, and 2.22e-16 on F4 for F13b.

`capture.R` and the r-captures workflow have still never run, here or on GitHub. Gate 2 of section 10 is not met. Today F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]` (re-measured below).

Setup. Detached worktrees under `scratchpad/lens-E12-r3-fresh-attack/`:
- `new` (`adcbcc3`): the suite, lint, markers and the CLI;
- `pw` (`adcbcc3`): probes and mutants, each restored with `git checkout`, captures deleted after each probe;
- `old` (`6928511`): `tests/test_e12_repair2.py` copied in;
- `o2` (`2328e86`): `tests/test_e12_repair1.py` from `adcbcc3` copied in.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Suite runs used `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8` and `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`. Platform: Windows 11, Git Bash, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1. I committed, pushed, downloaded and installed nothing, and I did not install R. I fetched no web page this round. This note is the only file I wrote outside the scratchpad.

## Blockers

| # | Blocker | Verbatim evidence | One-line repro |
|---|---|---|---|
| B1 | **Lens 2 B1 reproduces for the third needed file. The rule "an unreadable file does not skip" has no test that fails when it is reversed for `asah_vectors.csv`, and the sentence repair 2 added about that test is false.** The `tests/test_day12_r_captures.py` module docstring says `test_the_skip_reasons_are_the_typed_strings` asserts "that neither gate skips when a file it needs is unreadable (E12 repair 2)". `F13_NEEDS` is `(proc_asah.json, asah_vectors.csv)`. The test makes only `proc_asah.json` and `rms_val_prob_f4.json` unreadable; it never makes the vectors file unreadable. The repair's `GATE_MUTANTS` test pins M1 and RG-N1's deletion only by their text: G1 (`if bad & set(needs[:1]):`) and G2 (`if bad & set(fx.R_CAPTURE_FILES):`) each "fail" only because `assert source.count(old) == 1` in `test_fa_b1_each_lens_mutant_of_gate_fails_the_skip_reason_test[RG-N1 ...]` no longer finds its anchor line. | Mutant G3 keeps every anchor: in `_gate`, `bad = {f for f, _ in caps.unreadable}` became `bad = {f for f, _ in caps.unreadable if f != fx.R_VECTORS_FILE}`. `-m "day12 or fixture or ap3"` gave `329 passed, 8 skipped, 1751 deselected`, the same as unmutated (`329 passed, 8 skipped, 1751 deselected in 53.68s`). The behaviour, with the synthetic capture in `pw/fixtures/r/` and `81,Good,2,0.5,9.5` appended to `asah_vectors.csv` (y = 2, so the loader raises `ValueError`): unmutated, the three F13 comparisons gave `3 failed, 32 deselected`. Under G3: `SKIPPED [3] tests\test_day12_r_captures.py:129: r_captures_not_captured: F13 (absent: fixtures/r/asah_vectors.csv)`, `3 skipped, 32 deselected`. The reason says "absent"; the file is present and unreadable. CI's main job does not fail on a skip. | in `tests/test_day12_r_captures.py` `_gate`, `bad = {f for f, _ in caps.unreadable}` -> `... if f != fx.R_VECTORS_FILE}`; `python -m pytest -q -m "day12 or fixture or ap3"` |
| B2 | **The loader's "vectors file unreadable" branch is pinned by no test. Reversed, a present but corrupt `asah_vectors.csv` makes row F13 `no_oracle_recorded`, with the reason "are not both committed".** This is lens 1 FA-B2's class: the report calls an unreadable file not captured. `load_r_captures`'s docstring says "a file that does not parse is ``None`` and named in ``unreadable``". That holds in the code, but no test feeds the vectors file a parse error. | Mutant L1, in `src/proofpack/fixtures.py` `load_r_captures`: `unreadable.append((R_VECTORS_FILE, type(exc).__name__))` became `pass`. `-m "day12 or fixture or ap3"` gave `329 passed, 8 skipped, 1751 deselected`. The same corrupt-vectors capture, unmutated: `r-captures: partial_see_rows_f13_f13b - read: fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json; unreadable: fixtures/r/asah_vectors.csv; absent: none; row F13 not_matched, row F13b matched` and `F13 row: not_matched \| oracle_file_unreadable: fixtures/r/asah_vectors.csv (ValueError)`. Under L1: `... unreadable: none; absent: fixtures/r/asah_vectors.csv; row F13 no_oracle_recorded, row F13b matched`, `F13 row: no_oracle_recorded \| [unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and its input (fixtures/r/asah_vectors.csv) are not both committed; ... (absent: fixtures/r/asah_vectors.csv)`, and `3 skipped`. | in `load_r_captures`, the vectors `except (ValueError, KeyError)` branch's `unreadable.append(...)` -> `pass`; `python -m pytest -q -m "day12 or fixture or ap3"` |

One repair closes both. Add a test that:
- writes the synthetic capture with a present but unreadable `asah_vectors.csv` (for example `81,Good,2,0.5,9.5` appended);
- asserts `caps.unreadable` names it, row F13 reads `oracle_file_unreadable: fixtures/r/asah_vectors.csv (ValueError)`, and `_gate(dir, F13_NEEDS)[1] == []`;
- calls `_f13_or_skip` through `_no_skip`.

G3 and L1 must then fail. Alternatively, cut the module docstring to the two files the test feeds. That fixes the sentence but not the mutants. B1 touches the comparison gate, so under DEC-12 (i) its repair gets a fresh lens.

## Non-blocking (record and carry)

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **Repair 2's new status rule has an unpinned case: a row whose values are all numeric and all outside tolerance.** Mutant S1 (`_deviations_read` counts `v["within"]` instead of `v["abs_deviation"] is not None`) survives. The rule as committed gives the documented token. With every F13b value moved by +1e-3 it printed `present_compared_in_rows_f13_f13b \| ... row F13 matched, row F13b not_matched`; under S1 that would be `partial`. The rule decides the printed `--r-captures` line only (`cli.py:743`), not the rows or the exit code. | S1: `-m "day12 or fixture or ap3"` `329 passed, 8 skipped`. S2 (`>= 0`; 5 failed), S3 (`is None`; 3 failed) and S4 (`> 1`; 1 failed) were each killed. |
| N2 | **The `GATE_MUTANTS` test kills any edit of the line `if bad & set(needs):`, equivalent refactors included,** because it asserts that its anchor text occurs once. G1 and G2 died that way, not by behaviour (B1). | as B1 |
| N3 | **Lens 2's N7 / FA-N5 stands: some capture fields are compared nowhere.** Moving each by +2e-6 or -2e-6, or deleting it, failed none of the eight comparisons: `s100b ci_delong_mid`, `ndka ci_delong_mid`, `val.prob Dxy`, `glm joint (Intercept) se`, `glm joint logit_p se` and `glm offset (Intercept) se`. Also, deleting `roc.test conf.int lo` / `hi` failed nothing: they are `F13_OPTIONAL_NAMES`, by design. | `sweep.py` |
| N4 | **The pytest comparisons do not read the capture's header; only the report row does.** With `proc_asah.json`'s `fixture` set to `F13b`, the F13 comparison test passed, and `test_the_fixtures_report_row_f13_is_matched` failed. The compare job runs both, so a wrong header still fails there. | `sweep.py` case "proc fixture id F13b" |
| N5 | **A value written as a JSON string number reads `matched` in the report row; the pytest fails it.** `val.prob Slope` as `"1.19..."`: `test_f13b_engine_slope...` and `test_f13b_every...` FAILED, and `row13b` passed. This is lens 1 RG-N6's carry. `capture.R` writes strings only for values that are not finite. | `sweep.py` case "val.prob Slope as a JSON string" |
| N6 | **Carried, unchanged and confirmed open:** FA-N1 (M10, the not-captured line), FA-N2 (the `present` / `rows` keys, `GIT_WRITE`'s `push`), FA-N3 (the token with `proc_asah.json` alone, or from an installed package), FA-N4 (`R_CAPTURES_NOT_READ`'s opening words), FA-N6 (provenance not checked), FA-N7 (skip reasons are a prefix plus detail, not exactly `R_CAPTURES_NOT_CAPTURED`), RG-N2 (`@v9999` passes `PINNED_USES`), and Josh's question 3 (actions and the container pinned by tag, not sha: `actions/checkout@v4`, `actions/upload-artifact@v4`, `actions/download-artifact@v4`, `astral-sh/setup-uv@v6`, `rocker/r-ver:4.5.1`). The attack list calls an unpinned action a blocker. Three earlier lenses carried the tag pin to Josh as a decision, and I keep that grading. | - |

## What I could not break (re-measured, with figures)

**Suite and lint, `adcbcc3`** (`new`, clean run). Each figure matches the repair note:

| Run | Result |
|---|---|
| full suite | `2079 passed, 9 skipped in 306.15s` |
| skip lines | `SKIPPED [3] tests\test_day12_r_captures.py:129: r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv)`; `SKIPPED [5] tests\test_day12_r_captures.py:138: r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)`; `SKIPPED [1] tests\test_doctor_cli.py:57: write access cannot be revoked for this user` |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `306 files already formatted` |
| `-m day12` | `82 passed, 8 skipped, 1998 deselected` |
| `-m day11` | `144 passed, 1944 deselected` |
| `-m day10` | `262 passed, 1826 deselected` |
| `-m ap3` | `176 passed, 1912 deselected` |
| `-m fixture` | `71 passed, 2017 deselected` |

day11, day10, ap3 and fixture equal lens 2's `6928511` figures, so I found no damage outside day 12.

**Lens 2's blockers, re-tried:**
- **FA-B1 (M1) and RG-N1's deletion.** Pinned. `tests/test_e12_repair2.py` copied into `old` (`6928511`) gave `8 failed, 16 passed in 4.71s`. Both `test_fa_b1_each_lens_mutant...` cases fail with `AssertionError: assert 'skipped' == 'failed'`. The 16 that pass at both commits are each named `..._control_...`, `..._pass_this_check`, `..._fail_this_check` or `..._fails_the_comparisons_it_feeds`, as the module docstring says. Reopened for the vectors file: B1.
- **FA-B2 / RG-B1.** The README sentence now lists what the test inspects. I read it against the test body: top level `== {"contents": "read"}`; job `permissions` a dict whose values are within `{read, none}`; `"secrets." not in text`; `PINNED_USES.match` on each step's `uses`; `GIT_WRITE.search` on each step's `run`. W8-W11 pass the test and M7/M8 fail it, in the suite.
- **FA-B3 / RG-B2.** The new name and docstring match the body. Each line below was appended alone to a copy of `capture.R`, and the test FAILED on each: `require(ggplot2)` (`{'ggplot2'}`) and `system("curl https://example.invalid")` (`[('system2', '"sha256sum",'), ('system', '"curl https:')]`).
- **FA-B4.** Closed by the code: `values` `{}` gives `partial`, and all-`"NaN"` gives `partial` (tests pass). S2, S3 and S4 were killed (N1).
- **FA-B5.** `tests/test_e12_repair1.py` from `adcbcc3`, copied into `o2` (`2328e86`): `18 failed, 2 passed in 3.35s`. The two passes are `test_fa_b3_control_the_committed_workflow_copied_passes` and `test_rg_b2_control_the_committed_capture_r_copied_passes`, as the docstring now says.

**The statistics, re-derived without repository code** (`derive.py`: numpy and `math` only):
- DeLong from the 1988 placements: psi = 1, 0.5 or 0, V10 and V01 by direct O(mn) sums, S10/(m-1) and S01/(n-1), var = S10/m + S01/n.
- Paired: the 2x2 covariances, var_d = S11 + S22 - 2 S12, z = (A1 - A2)/sqrt(var_d), p = erfc(\|z\|/sqrt 2), d +/- 1.959963984540054 sqrt(var_d).
- Wald interval truncated to [0, 1].
- Nine data sets with ties: N/cases 113/41, 30/9, 57/20, 200/71, 14/6, 80/30, 41/26 and 60/15, plus an 18/6 set with AUROC 0.986111 whose upper bound truncates to 1.000000 in both mine and the engine's.
- Every `F13_NAMES` value and both `conf.int` bounds against `fx.f13_engine_values(..., with_conf_int=True)`: worst `2.6645352591003757e-15` (`roc.test statistic`). The signs of z and the conf.int are roc1 minus roc2, s100b first, as `roc.test(roc_s100b, roc_ndka)`.

**Recalibration on `fixtures/f4_calibration.csv`**, by my own Newton fit:
- joint intercept `0.49977163424518545`, slope `1.1945124796435689`, SEs `0.5950556263256326` / `0.5617458146727721`;
- offset intercept `0.45623046546120943`, SE `0.5536866258585561`;
- Brier `0.158755`; C `0.8541666666666666`; n 20, events 12.

Every one of the 13 `F13B_NAMES` engine values is within 2.22e-16 of mine. Like is compared with like: `val.prob Intercept`, `glm joint (Intercept)` and `glm joint tight (Intercept)` go with the engine's joint `intercept`; `glm offset (Intercept)` and `glm offset tight (Intercept)` go with `intercept_large`.

**Perturbation sweep** (`sweep.py`). The setup: the synthetic capture plus my own `roc.test conf.int` bounds, in `pw/fixtures/r/`. The eight comparison test functions were called in-process; a skip, a failure and an error are each classified. That is 37 fields, each +2e-6, -2e-6, +5e-7, -5e-7 and deleted (185 cases). The results:
- Every compared field failed one or more tests at +/-2e-6 and when deleted. None skipped.
- At +/-5e-7 every field passed except `var_delong` (relative 1e-6) and the four counts (exact), which are stricter by design.
- The exceptions are N3's fields.
- `f4 sha256 = "f"*64`: `test_f13b_capture_recorded_the_sha256...` and the F13b row FAILED.
- vectors `sha256 = "0"*64`: the vectors-sha test and the F13 row FAILED.
- A vectors row's s100b moved by +0.5 with the recorded sha unchanged: the F13 comparison, the vectors-sha test and the F13 row FAILED.
- The vectors file rewritten as CRLF passed (the same LF bytes).
- `s100b auc = "NaN"`: FAILED.
- A sign-flipped `conf.int lo`: FAILED.
- The `values` key removed from `rms_val_prob_f4.json`: three F13b tests `KeyError` (an error, not a skip), and the F13b row FAILED.
- All files absent: all eight skip, with `r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv)` or `r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)`.

**The compare job's state** (the synthetic capture in `pw/fixtures/r/`): `-m day12` `90 passed, 1998 deselected`, 0 skipped. `fixtures --offline --r-captures` printed `r-captures: present_compared_in_rows_f13_f13b - read: fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json, fixtures/r/asah_vectors.csv; unreadable: none; absent: none; row F13 matched, row F13b matched`.

**Absent (today), in `new`:**
- `python -m proofpack.cli fixtures --offline --out DIR --r-captures` exited 0 and printed `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`.
- It also printed `r-captures: r_captures_not_captured - no R capture is committed (fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json); F13 and F13b stay 'no oracle recorded' until fixtures/r/capture.R's output is committed`.
- `unverified` appears 37 times in `fixtures_report.json`. F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]`.
- `r_capture_drift.py --committed fixtures/r --fresh fixtures/r` exited 0 with `no capture is committed; nothing to compare`.
- `capture_fixture_oracles.py --check` exited 0 with `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`.
- `git grep -i "verified against R\|matches pROC\|validated against R\|agrees with R\|confirmed against R" adcbcc3 -- . ':!handoffs'` found nothing.

**`capture.R`, read line by line** (unchanged since `2328e86`):
- `roc()` sets `levels = LEVELS, direction = DIRECTION` and `stopifnot`s both. `ci.auc`, `var` and `roc.test` take a roc object, so nothing re-detects direction.
- `ci.auc(method = "delong", conf.level = 0.95)`; `var` is pROC's own, from its namespace, with `method = "delong"`.
- `roc.test(..., method = "delong", paired = TRUE)`.
- `val.prob(p, y, pl = FALSE)` is given the probabilities `p`, not `logit_p`.
- Every number goes through `json_number`'s `sprintf("%.17g")`, and the vectors through `sprintf("%.17g")`. `jsonlite::toJSON` writes strings only.
- The F4 sha256 is taken on a temp copy written by `writeBin(f4_raw)`, the same `readBin` bytes that `rawToChar` parses.

**The workflow** (unchanged since `05c2671`):
- top-level `permissions: contents: read`, and no job-level permissions;
- triggers `workflow_dispatch` and `push` with paths, with no `pull_request_target`;
- no `secrets` in any form, and no step that commits or pushes;
- `set -euo pipefail` before `pytest | tee`, so a pytest failure fails the step before the `SKIPPED` grep.

**Mutants killed** (each run against `day12 or fixture or ap3`): S2, S3 and S4 (N1); M1 and RG-N1's deletion (the repair's tests, in the suite).

## What I could not check

- Whether `capture.R` runs. R is not installed here, and nothing was downloaded. That leaves unchecked:
  - whether `rocker/r-ver:4.5.1` installs rms from its snapshot;
  - whether `tools::sha256sum` exists in R 4.5.1;
  - whether pROC's paired DeLong `roc.test` returns `conf.int`;
  - whether `lrm.fit` and `glm` at their default convergence agree with the engine to 1e-6;
  - which pROC and rms versions the snapshot installs.
- I fetched no source this round. The pROC and rms definitions I matched against are the ones lens 2 read on `master`. My derivation is from the published formulae.
- Any workflow run on GitHub: `adcbcc3` is not pushed.
- PowerShell 5.1 figures: every figure here was taken in Git Bash.

## Sentences I refused to write

- "The engine matches pROC and rms." Nothing has been compared with R.
- "Gate 2 is met."
- "An unreadable capture never skips": B1 and B2.
- "Lens 2's blockers are all closed." B1 reopens its B1 for a third file.
