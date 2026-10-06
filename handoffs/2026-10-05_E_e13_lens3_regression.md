# Lane E - build day 13 (E13, validation by code) - lens 3, cold regression-and-record, at `ec989ed` (pre `bcb1dac`; Tuesday 6 October 2026)

**PASS. 0 blockers.**

Every figure in the repair-2 note (`scratchpad/notes/E13_repair2.md`) that I re-ran reproduces, in Git Bash and in PowerShell 5.1. The four regression tests the note lists fail at `bcb1dac` on the assertions it quotes (4 failed, 57 passed). The two lens-2 blockers (FA-B1 = RG-B1, FA-B2) do not reproduce at `ec989ed`, and the third (FA-B3, the note's typed "7") is corrected in `notes/E13_repair1.md`. No test or gate was deleted or weakened. My own CI run on `ec989ed`, 37472723517, concluded success on 7 of 7 jobs. What remains is non-blocking (below): one imprecise singular in the new `parity.py` sentence, the cause of the ruff 334/336 difference the note could not find, `ci_gate.sh` reporting the builder's run instead of mine again, and a carried list that drops repair 1's carried items.

## Setup

Detached worktrees under `scratchpad/lens-E13-r3-regression/`:
- `tip` at `ec989ed`: the suite, markers, lint, CLI and script commands, in both shells;
- `mut` at `ec989ed`: plants and mutants, each restored with `git checkout` (`git status --short` empty after each);
- `base` at `bcb1dac`: the three changed test files (and, separately, the new golden) copied in and run; then the lens-2 plants reproduced on a restored tree.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Environment: `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8`, `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, `PROOFPACK_ASAH_VECTORS` unset. Windows 11, CPython 3.14. Nothing was committed. The only push was `ci_gate.sh`'s throwaway `ci/ec989ed`.

## Blockers

None.

## Re-measured

| | note (`ec989ed`) | Git Bash (lens, `tip`) | PowerShell 5.1 (lens, `tip`) |
|---|---|---|---|
| full | 2299 passed, 4 skipped in 300.82 s, exit 0 | 2299 passed, 4 skipped in 307.07s, exit 0 | 2299 passed, 4 skipped in 284.78s, exit 0 |
| skips | `[3] test_day12_r_captures.py:156` r_vectors_not_committed_dec77; `[1] test_doctor_cli.py:57` | same | same |
| `-m day13` | 99 passed | 99 passed, 2204 deselected | 99 passed, 2204 deselected |
| `-m day12` | 196 passed, 3 skipped | 196 passed, 3 skipped | 196 passed, 3 skipped |
| `-m day11` | 144 passed | 144 passed | 144 passed |
| `-m day10` | 262 passed | 262 passed | 262 passed |
| ruff check / format --check | All checks passed! / 336 files already formatted | same | same |
| `doctor --offline` | exit 0, 17 `[ok` | exit 0, 17 | exit 0, 17 |
| `fixtures --offline` | exit 0; rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only (...) 7 | same, exit 0 | same, exit 0 |
| `f16_parity_native.py --check` | 894 entries, 0 failures, 386 numeric entries bit-equal; committed at fa4929dd… | same | same, exit 0 |

The note's command forms:
- Git Bash: the `cd` / `export` / `python -c` lines, run literally in `wt-e13` (read-only), printed `C:\Users\joshs\GPS\ProofPack\wt-e13\src\proofpack\__init__.py`. `$TEMP` is `C:\Users\joshs\AppData\Local\Temp`, so `--out "$TEMP/fx"` is a usable path. The pytest and `fixtures` lines I ran in `tip` with my own `--out`.
- PowerShell 5.1: the `$env:` line and `python -m pytest -q -m day13` (in `mut`, same sha) gave `99 passed, 2204 deselected`. The line does not set `PROOFPACK_TR39_FULL`; day13 does not need it. `& 'C:\Program Files\Git\bin\bash.exe' C:/Users/joshs/GPS/ProofPack/workflows/ci_gate.sh` with no arguments printed `usage: ci_gate.sh <repo-dir> [<ref>]`, exit 1: the explicit path reaches Git Bash, where bare `bash` resolves to `C:\Windows\system32\bash.exe` (WSL), as RG-N8 said. I did not push a second time from PowerShell.

The arithmetic: 2293 at `bcb1dac` + 6 new ids = 2299. CI's 2166 passed + 137 skipped = 2303 = 2299 + 4.

**Fails pre-build** (`base` at `bcb1dac`, the three changed test files copied in, `PYTHONPATH` forced to `base`): **4 failed, 57 passed**, the note's figure. First failing lines:
- `AssertionError: ('src/proofpack/parity.py', "file's values of the same fixture, by exact equality")`;
- `AssertionError: ('src/proofpack/parity.py', 'test_every_register_class_value_is_in_the_file')`;
- `test_the_f13_status_cell_follows_a_drift_planted_in_the_recorded_comparison`: `AssertionError: assert 'not by this command' not in 'checked by ...this command'`;
- `test_the_suite_only_status_cell_names_who_checked_the_row`: `AssertionError: F13` / `assert 'checked by t... this command' == 'compared ins...corded values'`.

Each is an assertion, none an import abort. The tests that pass at `bcb1dac`, as the note says or as I expected:
- the third `FALSE_AT_BCB1DAC` parameter (`def test_every_register_class_value_is_in_the_file` in the test file): passes once the new test file is copied in (RG-N6, disclosed);
- `test_a_not_matched_row_prints_not_matched_whatever_its_evidence`: pins correct behaviour that no test covered (disclosed);
- `test_the_register_class_lookup_reads_keys_not_values_of_the_file` and the renamed `..._has_its_key_in_the_file`: they exercise a helper in the test file itself, so they cannot fail on old `src/`. The note lists neither as a regression test with a failing line.

The new golden `tests/fixtures/golden/T12.html`, copied alone into `bcb1dac`: `test_golden_t12_matches_the_committed_render` fails on the legend line (`- ... "compared inside a CI job; deviations recomputed by this command from the recorded values" and ...` against `+ ... oracle" and "checked by the test suite or a CI job, not by this command" ...`).

**Nothing weakened.**
- `git diff --name-status bcb1dac ec989ed`: 10 files, 8 `M` and the two lens-2 notes `A`. No `D`.
- The diff adds no skip, xfail, `only` or `todo`, and touches neither `pyproject.toml` nor `.github/`.
- Two `assert` lines were removed, both in the old `test_every_register_class_value_is_in_the_file`: `assert keys` and `assert any(k in committed ... for k in keys)`. Their replacement records a miss when `not any(k in committed ... for k in keys)`, which is also true when `keys` is empty, and asserts `misses == []`. Same strength.
- `day13` is at `pyproject.toml:103`. CI read it: my run's `pytest + ruff` job printed `day markers declared: day1 ... day13`, then `99 passed, 2204 deselected` for day13.

## Lens-2 blockers re-checked at `ec989ed`

| lens 2 | at `ec989ed` |
|---|---|
| **FA-B1 = RG-B1** (the `parity.py` sentence) | **Closed.** The sentence now says the test looks values up in a fresh `compute()` and asks the file for the key, reading no value of it. I ran the plants it names in `mut`: `F3-delong.paired_p` `0.0593464387919201` -> `0.0593464392919201` (+5e-10) gave `tests/test_f16_parity_native.py` **18 passed** and `--check` `894 entries, 0 failures, 385 numeric entries bit-equal`. The entry is `"tol": "irls"` and `parity.TOLERANCE["irls"]` is 1e-6, so the note's correction of the lens ("irls, not closed") holds. The other side of the sentence ("held to that fresh run by `compare` under the labelled tolerances"): +2e-6 gave **6 failed, 12 passed**, and `--check` named `F3.F3-delong.paired_p`. At `bcb1dac` the lens plant gave 17 passed, the note's figure. |
| **FA-B2** (F13's status cell) | **Closed.** At `ec989ed` the clean report's F13 cell reads "compared inside a CI job; deviations recomputed by this command from the recorded values". With the lens plant (`values["ndka auc"].engine` `0.6119579945799458` + 1e-3) `proofpack fixtures --offline` exited **6**, `rows 46: matched 35, not matched 1, ... suite only (...) 6`, F13 `not_matched`, `max_abs_deviation` 0.0010000000000000009, reason ending `outside tolerance: ndka auc`; `t12.render_t12` of that report gives F13's cell `('not_matched', 'not matched')`. The same plant at `bcb1dac` gave exit 6 and the same summary line, the note's figure. |
| **FA-B3 = RG-N1** (the typed 7) | **Closed in the note.** `notes/E13_repair1.md:11` now quotes `suite only (...) 5`, marked "[corrected in E13 repair 2 ...]". `gh run view --job 112272095844 --log` prints that line. RG-N7 ("is deleted") and the refused-sentence line (`:121`) carry the same marker. |

**Mutants of the new code** (in `mut`, over `test_e13_report_rows.py`, `test_t12.py`, `test_f16_parity_native.py`, `test_fixtures_cmd.py`, `test_day12_r_captures.py`; baseline 111 passed, 3 skipped):
- **M-a**, `f13_recorded_outcome` reads the file's `abs_deviation` instead of `abs(e - r)` (that is, "recomputed by this command" made false): 1 failed, `test_the_f13_status_cell_follows_a_drift_planted_in_the_recorded_comparison`.
- **M-b**, the recorded text for every non-measured `suite_only` row: 2 failed, the golden and the status-cell test. The note's figure.
- **M-c**, lens 2's M13 (measured text checked before status): 1 failed, the not-matched test. The note's figure.
- **M-d**, the recorded text returned for F13 with a deviation before the status is read: 2 failed.

All four killed.

## CI

I ran `bash workflows/ci_gate.sh <tip> HEAD` at 13:40:50Z. It printed `gate: run 37470619342 ci: success` / `gate: GREEN ec989ed`, exit 0, at **13:40:56Z**: six seconds, reading the builder's run from 13:25:03Z. My push's run, **37472723517** (created 13:40:55Z, head `ec989edb2361…`), was `queued` when the gate deleted the branch. I watched it with `gh run watch --exit-status` (exit 0). **7 of 7 jobs success**, finished 13:48:12Z:
- `pytest + ruff` (112300115153): `2166 passed, 137 skipped in 208.14s`; day12 `196 passed, 3 skipped`; day13 `99 passed, 2204 deselected`.
- `proofpack run inside unshare -rn (no network)` (112300115892): `namespace command: sudo unshare -n`, `22 passed in 3.13s`.
- `Docker image smoke` (112300115631): `rows 46: matched 33, not matched 0, no oracle recorded 4, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 5`; `other_files: equal e3b0c44298fc1c14` twice; `F17 (run) 5000 rows on linux-x86_64-cp312 (reference platform: yes); run exit codes [4, 4]; identical under the mask ['run_id', 'started', 'duration_s']: yes`.
- `pytest -m ap4 with the [docx] extra installed` (112300116021): `197 passed, 1 skipped`.
- `wheel artefact`, `import proofpack (scipy uninstalled)`, `pip-audit`: success.

The note's run 37470619342 (created 13:25:03Z, head `ec989edb…`): I read its logs. `pytest + ruff` (112292828945) `2166 passed, 137 skipped in 369.09s`, day13 `99 passed, 2204 deselected`; namespace (112292829016) `sudo unshare -n`, `22 passed in 2.34s`; docker (112292829032) the same `rows 46 ... 5` line and F17 line; ap4 (112292829038) `197 passed, 1 skipped`. Every CI figure the note quotes matches its log. Afterwards `git ls-remote origin 'refs/heads/ci/*'` printed nothing.

## Non-blocking (record and carry)

**N1 - the new `parity.py` sentence says "the key of the entry it finds"; the lookup accepts any of several.** 19 of the 67 register-class values equal more than one entry of the fresh compute (for example F2-register `sensitivity` 0.9 equals `F2-exact.sensitivity` and `F2-exact.specificity`; F4-register `brier` 0.158755 equals 3 entries). `_register_class_lookup` passes when any one of those keys is in the file. Run: deleting `F2-exact.sensitivity` from a copy of the committed file gives `_register_class_lookup` `(67, [])`; `parity.compare` then reports 1 failure. The helper's own docstring is exact ("whose entries' keys are all absent"); the module sentence is singular. Not a false guarantee, since the sentence claims no detection of a deleted key, and `compare` counts the deletion. Wording only: "the key of an entry it finds".

**N2 - the ruff 334/336 difference the note could not explain.** `ruff format --check -v` lists 334 paths at `bcb1dac` and 336 at `ec989ed`. The two extra paths are `handoffs\2026-10-05_E_e13_lens2_fresh-attack.md` and `handoffs\2026-10-05_E_e13_lens2_regression.md`: this ruff formats Markdown under `handoffs/`. `ruff check --show-files` lists 194 files in both trees. So each committed handoff note moves the "files already formatted" figure, and this note will too.

**N3 - `ci_gate.sh` reported GREEN from the builder's run, not mine (FA-N3 / RG-N2, carried; reproduced again).** Above: GREEN in 6 seconds from run 37470619342, branch deleted with my run 37472723517 queued. My run then concluded success, so no wrong verdict resulted today. The note says the race "did not occur here" for its own gate; it occurs on every re-gate of the same sha. Outside lane E's tree (`workflows/`).

**N4 - the repair-2 carried list drops repair 1's carried items.** `notes/E13_repair2.md` "Carried" lists only lens-2 items. Repair 1's (`notes/E13_repair1.md:88-139`) are not repeated or referenced: FA-N3 secondary (subtraction) suppression before any aggregates egress; gate 8's wording against `sudo unshare -n` (my run's namespace job again printed `sudo unshare -n`); question 54, the base image by digest; whether `fixtures/f16_parity_native.json` ships in the wheel. The handoff that merges these notes needs both lists.

**N5 - still open from lens 2, re-measured unchanged.** F17's `other_files` compared zero files again (`other_files: equal e3b0c44298fc1c14`, the SHA-256 of empty input, in both F17 steps of run 37472723517) (RG-N4). The `notes/E13_repair1.md:41` FA-B5 row still says F13 prints "not by this command"; that is a correct description of `bcb1dac`, not of `ec989ed`, and it carries no marker.

## What I could not break

- **The new status rule.** Clean report: F13 alone takes the recorded text; F12, F16, F17, F19 the measured text; F18, F20 "checked by the test suite or a CI job, not by this command" (listed from `fixtures --offline` at `ec989ed`). No other `suite_only` row carries a row-level `max_abs_deviation`: F16's per-fixture deviations sit inside `evidence.items`.
- **"deviations recomputed by this command".** `f13_recorded_outcome` computes `abs(e - r)` and does not read `abs_deviation` or `within`; M-a above shows the drift test fails when it reads the file's field.
- **F16 regeneration.** `scripts/f16_parity_native.py --out <scratch>` at `ec989ed`, tree clean: 894 entries, `fixtures` equal to the committed file; only `generated.engine_commit` differs (`ec989edb…` against `fa4929dd…`).
- **Lens-1 and lens-2 "could not break" items.** The repair-2 diff touches `fixtures.py` and `parity.py` in docstrings only, and `render/t12.py`'s `status_text` and one constant; F12, F17, F19, `egress/` and the statistics are not in it. Their figures re-measured through the CLI: F12 11 of 11 `ok` (exit 3, `files_changed 0`, `out_exists False`); F19 hits 0, socket calls 0, small-cell cohort 14 small cells, 0 unsuppressed; F17 6 of 6 equal, 400 rows; F16 894 of 894.

## What I could not check

- The reference image locally (no Docker on this machine); I relied on the logs of runs 37470619342 and 37472723517.
- The Pyodide half of F16 (lane S, after a pin move).
- `unshare -rn` on any runner: both runs fell back to `sudo unshare -n`.
- Whether a third session gated `ec989ed` while mine ran: `gh run list --commit` showed only 37470619342 and 37472723517 at 13:41Z.

## Sentences I refused to write

- "The gate is GREEN on my push." The script's GREEN came from run 37470619342. Mine is 37472723517, watched by hand, success.
- "The register-class test catches a deleted key." N1 is its counter-example; `compare` catches it.
- "The F13 cell can only read the recorded text when this command recomputed the deviations." The rule reads `max_abs_deviation` on any `suite_only` row; today only F13 sets it (above), which is what I can name.

## Cleanup

Worktrees `tip`, `mut` and `base` removed with `git worktree remove --force`. No node_modules junction existed. Nothing was committed.
