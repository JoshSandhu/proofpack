# Lane E - build day 12 (E12, the R captures) - lens 3, cold regression-and-record, at `adcbcc3` (E12 repair 2; pre `6928511`; Monday 5 October 2026)

**PASS. 0 blockers.**

Every count and command in the repair-2 note reproduces in Git Bash and in PowerShell 5.1. The new file `tests/test_e12_repair2.py` gives `8 failed, 16 passed` at `6928511`, as the note says. Every failure there is an assertion, and the 16 passes are the controls and pins the note names. The seven lens-2 blockers (FA-B1 to FA-B5, RG-B1, RG-B2) no longer reproduce. Four records are non-blocking. One is a new surviving mutant on the changed status rule. One is a sentence that the note backs with no counter-example; I built one, and it holds. One is a docstring that describes `PINNED_USES` too narrowly. One is a crash on a directory, which predates this repair.

`capture.R` and the r-captures workflow have still never run. Gate 2 of section 10 is not met by measurement. F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]`. I re-measured that in both shells.

Setup. Detached worktrees under `scratchpad/lens-E12-r3-regression/`:
- `new` (`adcbcc3`): the suite in Git Bash;
- `newps` (`adcbcc3`): the suite in PowerShell 5.1;
- `mut` (`adcbcc3`): mutants and probes, each restored with `git checkout`;
- `old` (`6928511`): the new tests copied in;
- `old23` (`2328e86`): the repair-1 docstring count;
- `old45` (`45e6761`): the N4 count.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Suite runs used `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8` and `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1. I committed, pushed, downloaded and installed nothing, and I did not install R. This note is the only file I wrote outside the scratchpad.

## Blockers

None.

## Non-blocking

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **A new surviving mutant on the changed status rule (DEC-12 (i) territory).** Mutant S5: `_deviations_read` counts `v["within"]` instead of `v["abs_deviation"] is not None`. Under `-m "day12 or fixture or ap3"` it gives `329 passed, 8 skipped, 1751 deselected` (survives). No test feeds a row whose values are all read but all outside tolerance. On the committed code, the synthetic capture with every `rms_val_prob_f4.json` value +1.0 gives F13b `not_matched` with 13 deviations read and 0 within. The status is `present_compared_in_rows_f13_f13b`, and the line ends `row F13 matched, row F13b not_matched`. That is what the docstring says. Under S5 the status would be `partial_see_rows_f13_f13b`. The rule as committed matches its sentence; the distinction is unpinned. | in `mut`, `fixtures._deviations_read`: `if v["abs_deviation"] is not None` -> `if v["within"]`; `python -m pytest -q -m "day12 or fixture or ap3"` |
| N2 | **A sentence written without a recorded counter-example, which I then ran: it holds.** `_no_skip`'s docstring says "a skip raised by the gate fails the calling test". The commit body says "(a skip there fails the test)". The repair note records only that `_no_skip`'s conversion is an equivalent mutant under M1 and RG-N1 (G3 below), because `_gate`'s direct assertions fail first. So the note runs no case in which the conversion does the failing. My counter-examples move the skip into the wrapper, where `_gate` is still right. G6: `_f13_or_skip` skips on `if absent or caps.unreadable:`. Result: `3 failed, 326 passed, 8 skipped`, and `::test_the_skip_reasons_are_the_typed_strings` FAILED. G7 is the same in `_f13b_or_skip`, with the same figures. G6 plus G3 (`_no_skip` catching `KeyError`): the skip-reason test alone gives `1 skipped`, with the line `SKIPPED [1] ...:129: r_captures_not_captured: F13 (absent: )`. The selection gives `2 failed, 326 passed, 9 skipped`, caught by `::test_fa_b1_control_...` and `::test_fa_b1_an_unreadable_capture_fails_the_comparisons_it_feeds`. The sentence is true on these inputs. G3 alone still survives (`329 passed, 8 skipped`), as the note records. | in `mut`, `_f13_or_skip`: `if absent:` -> `if absent or caps.unreadable:`; run the selection |
| N3 | **The workflow test's docstring says `PINNED_USES` takes "``v<N>`` or a commit sha". The regex also takes dotted tags.** I planted each ref in a copy of the workflow, in place of the upload step's `uses`. `actions/upload-artifact@v4.1.2` passed. `@v9999` passed (RG-N2, carried). `@main` failed. Repair 1's wording, "a version tag or a commit sha", was the closer one. It is harmless, because a dotted tag is still a tag, but the sentence is narrower than the check. | `r2._workflow_outcome(tmp_path, monkeypatch, r2.UPLOAD_USES, "      - uses: actions/upload-artifact@v4.1.2\n")` -> `passed` |
| N4 | **Pre-existing (build item 3), not the repair: a capture path that is a directory crashes `--r-captures`.** With `fixtures/r/proc_asah.json` made a directory, `proofpack fixtures --offline --out DIR --r-captures` exits 5 with `internal error: PermissionError: [Errno 13] Permission denied: '...\mut\fixtures\r\proc_asah.json'`. `load_r_captures` catches `FileNotFoundError` and `ValueError` only. The failure is loud: in the pytest module run, all eight comparisons read FAILED and none SKIPPED. | `mkdir fixtures/r/proc_asah.json`; `python -m proofpack.cli fixtures --offline --out DIR --r-captures` |
| N5 | **The carried table is one item stale.** It lists FA-N2's M14 (`"rows": {}`) as not pinned. Repair 2 now kills it: `1 failed, 328 passed, 8 skipped`, the failure `tests/test_e12_repair2.py::test_fa_b4_proc_values_all_nan_strings_is_partial`, which asserts `st["rows"]`. These still survive, re-measured: FA-N1's M10 (`elif status == R_CAPTURES_NOT_CAPTURED:`) `329 passed, 8 skipped`; FA-N2's M13 (`"present": list(R_CAPTURE_FILES)`) `329 passed, 8 skipped`; M15 (`push` dropped from `GIT_WRITE`) `329 passed, 8 skipped`. | `"rows": {...}` -> `"rows": {}` in `r_captures_status`; run the selection |
| N6 | Small record items. The drift command prints two last lines: `r-capture drift: no capture is committed; nothing to compare`, then `r-capture drift: 0 difference(s) above 1e-12`. The note quotes the first. The note says it took no PowerShell 5.1 figures; mine are below and match. | - |

## What I could not break (re-measured, with figures)

**Suite and lint at `adcbcc3`.** Each figure matches the note.

| Run | Git Bash (`new`) | PowerShell 5.1 (`newps`) |
|---|---|---|
| full suite `-rs` | `2079 passed, 9 skipped in 309.43s`, exit 0 | `2079 passed, 9 skipped in 309.43s`, exit 0 (two separate runs started together; their `[timing]` lines differ, e.g. T2 30.74 s / 29.96 s) |
| skip lines | `SKIPPED [3] tests\test_day12_r_captures.py:129: r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv)`, `SKIPPED [5] ...:138: r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)`, `SKIPPED [1] tests\test_doctor_cli.py:57: write access cannot be revoked for this user` | the same three lines |
| `-m day12` | `82 passed, 8 skipped, 1998 deselected` | the same |
| `-m day11` | `144 passed, 1944 deselected` | the same |
| `-m day10` | `262 passed, 1826 deselected` | the same |
| `test_day12_carried.py test_e12_repair1.py test_e12_repair2.py` | `55 passed` | `55 passed` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `306 files already formatted` | the same |
| `--collect-only` | `2088 tests collected` (the note's 2064 -> 2088) | - |

**The note's commands, in both shells.** No command failed in either shell.
- `python -m proofpack.cli doctor --offline`: exit 0, 17 `[ok` lines.
- `fixtures --offline --out DIR --r-captures`: exit 0 and `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`.
  - The line `r-captures: r_captures_not_captured - no R capture is committed (fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json); F13 and F13b stay 'no oracle recorded' until fixtures/r/capture.R's output is committed` is byte for byte the note's.
  - `unverified` appears 37 times in `fixtures_report.json`.
  - F13: `no_oracle_recorded | [unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and its input (fixtures/r/asah_vectors.csv) are not both committed; ...`.
  - F13b: `no_oracle_recorded | [unverified until captured] the rms::val.prob capture (fixtures/r/rms_val_prob_f4.json) is not committed; ... (f4_expected.json r_rms_val_prob: [pending])`.
  - The two shells' reports differ only in the worktree path, `duration_s` and `generated`.
- `scripts/capture_fixture_oracles.py --check`: exit 0, `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`.
- The YAML jobs: `['capture', 'compare']`.
- `scripts/r_capture_drift.py --committed fixtures/r --fresh fixtures/r`: exit 0 (N6).

**Fails pre-build.** I copied `tests/test_e12_repair2.py` into `old` (`6928511`): `8 failed, 16 passed in 4.67s`. Every failure is an `AssertionError`, and the first lines match the note:
- `assert 'skipped' == 'failed'` (x2, the gate mutants);
- `assert 'test_the_wor...it_write_step' == 'test_the_wor...hes_git_write'`;
- `assert 'test_capture..._and_commands' == 'test_capture..._listed_names'`;
- `assert 'present_comp...rows_f13_f13b' == 'partial_see_rows_f13_f13b'` (x2);
- `assert 'both compared one or more' not in ...`;
- `assert 'and failed there' not in ...`.

The 16 passes are the ones the note names: `..._control_...` (2), `..._fails_the_comparisons_it_feeds` (1), `..._pass_this_check` (4 workflows and 7 capture.R lines) and `..._fail_this_check` (2). The pass-at-both tests pin documentation lists, not changes. The note and the module docstring say so.

**The repair-1 docstring (FA-B5).** `tests/test_e12_repair1.py` copied into `old23` (`2328e86`): `18 failed, 2 passed in 3.42s`. The passes are the two named controls, as the new docstring says.

**Lens 2's blockers, re-run on `adcbcc3`.** Mutants are in `mut`, under `-m "day12 or fixture or ap3"` (baseline `329 passed, 8 skipped, 1751 deselected`).
- **FA-B1 / RG-N1, closed.** M1 (`return caps, list(needs)`) and the RG-N1 deletion give `5 failed, 324 passed, 8 skipped` each, with `::test_the_skip_reasons_are_the_typed_strings` FAILED; these are the note's figures. My own gate mutants are killed too. G4 (`bad & set(needs)` -> `bad >= set(needs)`) gives `4 failed`. G5 (branch deleted, absent excluding unreadable) gives `4 failed`. So are the wrapper mutants G6 and G7 (N2).
- **The unreadable case, fresh inputs.** Each input below went on the synthetic capture, with the day-12 module run in a subprocess through repair 1's redirect plugin. In every case, every comparison fed by the bad file read FAILED, and no test anywhere read SKIPPED.
  - `asah_vectors.csv` = bytes `ff fe 00 garbage` (unreadable `UnicodeDecodeError`): the three F13 comparisons FAILED and the five F13b PASSED.
  - `asah_vectors.csv` = `x\n` (`ValueError`): the same.
  - `proc_asah.json` = `[]` (`ValueError`, not a JSON object): the same.
  - `rms_val_prob_f4.json` re-encoded UTF-16 (`UnicodeDecodeError`): the five F13b comparisons FAILED and the three F13 PASSED.
  - `proc_asah.json` a directory: all eight FAILED (N4).
- **FA-B2 / RG-B1, closed.** The name and the README now list what the test inspects. I read the test body against that list: the triggers; top-level `permissions == {"contents": "read"}`; each job's permissions a mapping with values in `{read, none}`; `"secrets." not in text`; `PINNED_USES`; `GIT_WRITE` on each `run`; the container; the upload step; the capture and drift steps. Each item is asserted. Lens 2's W8-W11 pass the test (pinned), and M7 and M8 fail it (pinned).
- **FA-B3 / RG-B2, closed.** The name and the seven not-matched lines are pinned, at both commits.
- **FA-B4, closed.** The figures:

  | Mutant | Result |
  |---|---|
  | back to `n_values_compared` | `2 failed, 327 passed` |
  | `all` -> `any` | `4 failed, 325 passed` |
  | count every value | `2 failed, 327 passed` |
  | `> 0` -> `>= 0` (mine) | `5 failed` |
  | `> 0` -> `> 1` (mine) | `1 failed`, the control |

  `_number` returns `None` for NaN and infinity, so "all missing or not finite" gives no numeric deviation, as the lane S line says.
- **FA-B5, closed** (above).

**The E11 lens-4 carried sentences.**
- N4: `tests/test_e11_repair3.py` copied into `old45` (`45e6761`) gives `19 failed, 1 passed in 5.21s`, and the pass is `::test_control_an_unclustered_compare_keeps_the_mcnemar_p_value`. That matches its docstring.
- N5: `clustered_number`'s docstring is unchanged since `6928511`, where lens 2 matched its six steps to the code. `git diff 6928511 adcbcc3` touches neither file.

**Nothing weakened.**
- `git diff --name-status 6928511 adcbcc3`: `M fixtures/r/README.md`, `A` two lens-2 handoffs, `M src/proofpack/fixtures.py`, `M tests/test_day12_r_captures.py`, `M tests/test_e12_repair1.py`, `A tests/test_e12_repair2.py`. Nothing deleted.
- The `skip` lines added in the diff are `_no_skip`, which turns a skip into `pytest.fail`, and `_outcome`'s `except pytest.skip.Exception`, which classifies. No `xfail`, `.only` or `todo` was added, and no marker was removed.
- `pytestmark = pytest.mark.day12` is on the new file.
- `pyproject.toml` and `.github/` are unchanged since `6928511`. `day12` is at `pyproject.toml` line 102, and `ci.yml` reads the marker list from `pyproject.toml` (lines 43-59).
- All seven changed files are `i/lf w/lf`.

**The workflow as committed** (`yaml.safe_load`):
- `on` is `workflow_dispatch` and `push` with paths `fixtures/r/**` and `.github/workflows/r-captures.yml`;
- `permissions` is `{'contents': 'read'}`; jobs `capture` and `compare` have no `permissions` key;
- `uses` is `actions/checkout@v4` x2, `actions/upload-artifact@v4`, `actions/download-artifact@v4` and `astral-sh/setup-uv@v6`;
- the container is `rocker/r-ver:4.5.1`;
- the compare step has `if grep -q "SKIPPED" day12.txt; then ...; exit 1; fi`.

These match the README's sentence that the file declares `contents: read` at the top level and no job-level permissions.

**The DEC-12 (i) scope claim.** `r_captures_status` is called once outside `fixtures.py`, at `cli.py:743`, for the printed line. The exit code comes from `exit_code_for(rows)`. That agrees with the note's statement that the rule does not enter the report rows or the exit code.

## What I could not check

- Whether `capture.R` runs, or whether the workflow runs. There is no R here, nothing was downloaded, and `adcbcc3` is not pushed.
- An installed wheel: it would need an install.
- Lane S: the site pins `81f1102`, and I ran nothing in `proofpack-site`.
- The equivalences earlier lenses marked `[unverified]` (`lrm.fit` convergence; which pROC version writes `conf.int`).

## Sentences I refused to write

- "The status rule is pinned": S5 survives (N1).
- "An unreadable capture always fails the comparison": I measured five more inputs plus the repair's one, not every input.
- "The workflow test proves the workflow cannot write or read a secret": W8-W11 pass it, by design and now pinned.
- "The engine matches pROC and rms" / "gate 2 is met": nothing has been compared with R.
