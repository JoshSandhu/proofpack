# E13 lens 3 - fresh attack - on `ec989ed` (Tuesday 6 October 2026)

**Verdict: FAIL. Three blockers: two sentence violations and one wrong count on the T12 page.**

1. The renamed test `test_every_register_class_value_has_its_key_in_the_file` and the new `parity.py` sentence "asks the committed file for the key of the entry it finds" say each value's own key is looked up. 19 of the 67 values equal more than one entry. With `F2-exact.sensitivity` deleted from the committed file, the renamed test still gives **1 passed**.
2. The new F13 status cell and the new `fixtures.py` sentence say this command recomputes each deviation from the recorded values. I planted a 17th recorded pair in `fixtures/r/f13_engine_comparison.json` (engine 0.1, R 0.9, `within: false`). `proofpack fixtures --offline` then **exits 0**. F13 stays `suite_only`, its reason still says "recorded 16 values" and "max abs deviation 2.7755575615628914e-17", and its cell still says "deviations recomputed by this command from the recorded values".
3. T12's F13 row prints **Values 0**. The same row prints a largest deviation of 2.78e-17, and repair 2's new status cell says this command recomputed the deviations. `fixtures_report.json` has `n_values_compared: 0` for F13, while `fixtures._deviations_read` counts 16 for the same row.

No statistic in the engine is wrong:
- the F16 file regenerates key for key;
- my own DeLong (11 F3 values) and Wilson/Clopper-Pearson (16 F1-family values) agree with the file to within 2.2e-15;
- the 16 recorded F13 deviations agree with my recomputation;
- every repair-2 mutant I ran is killed;
- I found no leak in the egress bytes.

Lens 2's three blockers (FA-B1, FA-B2, FA-B3) no longer reproduce in the form lens 2 raised them. B1 and B2 above are new sentences that the repair wrote.

Scope: a cold lens on `git diff bcb1dac ec989ed` (E13 repair 2 and the two lens-2 notes) and on the note `scratchpad/notes/E13_repair2.md`. I worked in three detached worktrees under `scratchpad/lens-E13-r3-fresh-attack/`, all removed at the end:
- `tip` at `ec989ed`, for suites and the gate;
- `mut` at `ec989ed`, for plants and mutants; each was restored with `git checkout` and `git status --short` was empty after each;
- `base` at `bcb1dac`.

Every Python process ran with `PYTHONPATH=<worktree>/src`, and printed `...\lens-E13-r3-fresh-attack\<worktree>\src\proofpack\__init__.py` before I used its numbers. Nothing was committed. The only push was the gate's throwaway `ci/ec989ed`.

## Measured figures (this session, Git Bash, Windows 11, win-amd64-cp314, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1)

Environment: `PROOFPACK_REQUIRE_DOCX=1 PYTHONIOENCODING=utf-8 PROOFPACK_TR39_FULL=...confusables-18.0.0.txt`, with `PROOFPACK_ASAH_VECTORS` unset.

| | `ec989ed` (this lens) | note's figure |
|---|---|---|
| full suite | 2299 passed, 4 skipped in 306.04 s, exit 0 | the same |
| skips | `[3] test_day12_r_captures.py:156` r_vectors_not_committed_dec77; `[1] test_doctor_cli.py:57` | the same |
| `-m day13` | 99 passed, 2204 deselected | 99 |
| `-m day12` | 196 passed, 3 skipped | the same |
| `-m day11` | 144 passed | 144 |
| `-m day10` | 262 passed | 262 |
| `ruff check .` / `ruff format --check .` | "All checks passed!" / "336 files already formatted" (at `bcb1dac`, the same command printed 334) | the same; the note "did not find the cause" (N2 below) |
| `fixtures --offline` | exit 0; "rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 7" | the same |
| `scripts/f16_parity_native.py --check` | "894 entries, 0 failures, 386 numeric entries bit-equal; committed at fa4929dd… on win-amd64-cp314", exit 0 | the same |
| the three changed test files, copied into `bcb1dac` | **4 failed, 57 passed**: two `FALSE_AT_BCB1DAC` parameters on `parity.py`, `test_the_f13_status_cell_follows_a_drift_planted_in_the_recorded_comparison` and `test_the_suite_only_status_cell_names_who_checked_the_row` | 4 failed, 57 passed |

The earlier markers match lens 2's figures at `bcb1dac`: day12 196/3, day11 144 and day10 262. day13 rises from 93 to 99, the six new test ids the note lists.

## Blockers

### B1 - the renamed test and the new `parity.py` sentence say "its key" / "the key of the entry it finds"; 19 of the 67 values equal two or three entries, and any one key passes (sentence violation)

Verbatim, `src/proofpack/parity.py` at `ec989ed`:

> looks up each of the 67 values of the ``register``-class rows (F1-F6 and F8) among the values a fresh :func:`compute` gives for the same fixture, by exact equality, and asks the committed file for the key of the entry it finds

The new test name is `test_every_register_class_value_has_its_key_in_the_file`.

`_register_class_lookup` collects **every** fresh key whose value equals the register value. It then accepts the value if `any` of those keys is in the committed file. I ran that lookup over the 67 values (in `mut`): **19 values match more than one key**. Examples:
- `F2-register` `sensitivity` 0.9 and `specificity` 0.9 both match `['F2-exact.sensitivity', 'F2-exact.specificity']`;
- `F1c-register` `wilson_lo` 0.0 and `cp_lo` 0.0 both match `['F1c-clopper-pearson.cp_lo', 'F1c-wilson.wilson_lo']`;
- `F4-register` `brier` 0.158755 matches three keys, `E6.calibration_block.brier.analytic.est`, `E6.calibration_block.brier.number.est` and `F4-closed-form.brier`.

I deleted the first matching key for each of the 19, one at a time, in a copy of the committed file. `_register_class_lookup` reported **no miss for that value in 19 of 19**.

**Counter-example, through pytest** (in `mut`):
- I deleted `F2-exact.sensitivity` from `fixtures/f16_parity_native.json`.
- `pytest "tests/test_f16_parity_native.py::test_every_register_class_value_has_its_key_in_the_file"` gives **1 passed in 1.18s**.

F2-register's sensitivity has lost its key, and the test that says each value "has its key in the file" passes. The deletion does not escape F16: the whole file gives 7 failed and 11 passed, through `compare`'s key-set check. The defect is the sentence and the name, the same class as lens 2's FA-B1, which this repair renamed.

The new limit test's "Deleting the key is a miss" holds for `F3-delong.paired_p` only, because that value matches one key.

**Repro:** in a scratch copy, delete `"F2-exact.sensitivity"` from the committed file's `F2` block, then `PYTHONPATH=<copy>/src python -m pytest -q "tests/test_f16_parity_native.py::test_every_register_class_value_has_its_key_in_the_file"`. It prints 1 passed.

**What would be true:** "asks the committed file for any key among the fresh entries holding an equal value". A test name that says what is looked up, for example `..._equals_a_fresh_entry_whose_key_is_in_the_file`. Alternatively, match each value to its own named entry.

### B2 - F13: a recorded pair outside tolerance is not recomputed, the command exits 0, and the cell says the deviations were recomputed; the reason's "16 values" is a constant, not a count (sentence violation; a typed number)

Verbatim, the new text:
- `render/t12.py` `SUITE_ONLY_RECORDED_TEXT`: "compared inside a CI job; deviations recomputed by this command from the recorded values". The T12 legend carries the same words.
- `fixtures.py` module docstring: "this command recomputes each deviation from the recorded engine and R values".

`f13_recorded_outcome` loops over `F13_NAMES` (16 names) only. A recorded name outside that list is never read. The reason prints `{len(F13_NAMES)} values`, a constant.

**Counter-example (run through the CLI, in `mut`).** I added `"ndka auc (second capture)": {"engine": 0.1, "r": 0.9, "tolerance": 1e-6, "abs_deviation": 0.8, "within": false}` to `values` in `fixtures/r/f13_engine_comparison.json`. Then `python -m proofpack.cli fixtures --offline --out <dir>` printed:
- `rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 7`;
- **exit 0**.

The F13 row in `fixtures_report.json` was:
- status `suite_only`, `max_abs_deviation` 2.7755575615628914e-17;
- reason "compared inside the r-captures job, not by this command: GitHub run 37332685741 **recorded 16 values** of the engine ... max abs deviation 2.775557561562891…";
- `t12.status_text` gave "compared inside a CI job; deviations recomputed by this command from the recorded values".

The file now records 17 pairs. One of them is 0.8 apart and marked `within: false` by the file itself. This command neither recomputes nor reports it. `--r-captures` prints `present_compared_in_rows_f13_f13b ... row F13 suite_only`.

**Reachability:** the CI writer, `scripts/r_f13_compare.py`, writes the F13 row's own values, so today an extra name arrives only by a hand edit or a change to the writer. That is the same route as lens 2's +1e-3 plant, which this repair answered.

**What does hold.** I moved each of the 16 named engine values in turn:
- by +1e-3: **16 of 16** `not_matched`, exit 6;
- by -1e-3: 16 of 16 `not_matched`;
- by +2e-6: 16 of 16 `not_matched`;
- by +9e-7: 16 of 16 `suite_only`, inside 1e-6.

Each of the following gives `not_matched`, exit 6:
- an engine value of NaN, `"0.5"`, `true`, `null` or `inf`;
- a tolerance widened to 1e-3 with a move of 5e-4;
- a name deleted.

So the sentence holds for the 16 named pairs. It does not hold for "the recorded values" as a whole.

**Repro:** add any extra key to `values` in a scratch copy of `fixtures/r/f13_engine_comparison.json`, then `PYTHONPATH=<copy>/src python -m proofpack.cli fixtures --offline --out <dir>; echo $?`. It prints 0, and the reason says "recorded 16 values".

**What would be true:** either refuse a name outside `F13_NAMES` (`not_matched`, naming it), or say "the 16 named deviations recomputed by this command". The reason should count the names it read, not `len(F13_NAMES)`.

### B3 - T12's F13 row prints "Values 0" beside a largest deviation and a status that says this command recomputed the deviations (a wrong number on the page)

At `ec989ed`, `fixtures --offline` and `t12.render_t12` on the report it wrote give this F13 row, verbatim (cells abridged):

> `<td class="num">0</td><td class="num mono">2.78e-17</td><td class="fixture-status" data-status="suite_only">compared inside a CI job; deviations recomputed by this command from the recorded values</td>`

The values behind it:
- `fixtures_report.json`'s F13 has `n_values_compared: 0`, `values: []` and `max_abs_deviation: 2.7755575615628914e-17`.
- The table caption defines the largest deviation as "the largest absolute difference between engine and oracle values in the row". So the page prints a largest deviation over 0 values.
- `fixtures._deviations_read` counts **16** for the same row, which is what the `--r-captures` line uses.
- The row's reason says "recorded 16 values". The new status says this command recomputed them.

The 0 was already printed at `bcb1dac`, beside "checked by the test suite or a CI job, not by this command". Repair 2 changed the status to one that the count contradicts. No test reads F13's Values cell: the golden masks the report, and its F13 row also prints 0.

**Repro:** `PYTHONPATH=<tip>/src python -m proofpack.cli fixtures --offline --out <dir>`, then render the report with `proofpack.render.t12.render_t12`. The F13 row's Values cell reads 0, and the cell after it reads 2.78e-17.

**What would be true:** the number of pairs recomputed (16), or "—" with the note naming why. `n_values_compared` is a key in `fixtures_report.json`, so a change there goes in changes_for_other_lanes (DEC-43). A render-only change does not.

## Lens 2 blockers re-checked at `ec989ed`

| lens 2 | at `ec989ed` |
|---|---|
| **FA-B1 = RG-B1** (`parity.py` "among the file's values") | **The old sentence is gone.** The two `FALSE_AT_BCB1DAC` parameters on `parity.py` fail at `bcb1dac` and pass at the tip. The limit test feeds +5e-10 on `F3-delong.paired_p`, labelled `irls` as the repairer measured (the file's `tol` is `irls`, not `closed`). It gives `(67, [])` and no `compare` failure. **The replacement sentence and the new test name are B1 above.** |
| **FA-B2** (F13 cell "not by this command") | **Closed for the 16 named pairs:** the cell now names the recomputation, and the +1e-3 plant gives `not_matched`, exit 6 and "not matched" through the CLI (`rows 46: matched 35, not matched 1, ... suite only (...) 6`; `max_abs_deviation` 0.0010000000000000009). **The new sentence over-reaches on an extra recorded name (B2), and the page's count contradicts it (B3).** |
| **FA-B3 = RG-N1** (the note's "7") | **Closed in the note.** The repair-2 note quotes the docker-smoke line with 5. I read run 37470619342, job 112292829032 myself: `rows 46: matched 33, not matched 0, no oracle recorded 4, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 5`. |
| **FA-N1 M13** (measured before status) | **Killed.** My mutant M4 below (1 failed). |

## Non-blocking (record and carry)

1. **Mutants of repair 2's `status_text`** (against `test_e13_report_rows.py`, `test_t12.py` and `test_fixtures_cmd.py`, with `-x`). Each of the six is killed:
   - M1, `max_abs_deviation` tested for truthiness: 1 failed (the masked golden sets it to 0.0);
   - M2, the recorded branch removed: 1 failed;
   - M3, the recorded text for rows with `max_abs_deviation` None: 1 failed;
   - M4, the measured check before the status check (lens 2 M13): 1 failed;
   - M5, the recorded check before the status check: 1 failed;
   - M6, the recorded text shortened to "compared inside a CI job": 1 failed.
2. **`ci_gate.sh` reproduced FA-N3 / RG-N2 a third time.**
   - My gate started at 13:41:58Z. It printed `gate: run 37472723517 ci: success`, `gate: run 37470619342 ci: success` and `gate: GREEN ec989ed`, then exited 0 at 13:48:21Z.
   - Neither run is mine. 37472723517 was created at 13:40:55Z, by another session's push of the same sha. 37470619342 is the repairer's.
   - My push's run is **37472872644** (created 13:42:03Z). It was `in_progress` when the gate deleted `ci/ec989ed`. I watched it by hand (section "CI").
   - This is outside lane E's tree (`workflows/`).
3. **The ruff count, 334 → 336, has a cause.** ruff 0.16.6 includes Markdown files. `ruff format --check -v` logs `Included path via include: ...\handoffs\2026-09-10_E_verify_safety.md`, among others. `ec989ed` adds the two lens-2 notes. A clean `bcb1dac` worktree prints 334. The `ec989ed` worktree prints 336 with no untracked file, and `git ls-files '*.py'` gives 193 in both.
4. **Secondary (subtraction) suppression: lens 1 FA-N3, carried, now measured.** I built a cohort with one small site (3 rows: 1 event, 2 non-events), the other 397 rows at one site. The primary rule held: 7 small cells, 0 unsuppressed. But the aggregates document gives:
   - overall sensitivity `n 127, k 95` against Site B `n 126, k 95`;
   - overall specificity `n 273, k 206` against `n 271, k 205`.

   Subtraction recovers the small site's 1 event, 0 detected, 2 non-events and 1 true negative. `f19.py` names primary suppression only and asserts nothing about subtraction. The aggregates document is not sent by any code path at launch (the telemetry body, 340 bytes, holds no cell). It is recorded because a later lane that sends the aggregates document inherits this.
5. **RG-N6, carried.** The third `FALSE_AT_BCB1DAC` parameter targets a test file. It passes when the new test file is copied into `bcb1dac`.
6. **`test_a_not_matched_row_prints_not_matched_whatever_its_evidence` passes at `bcb1dac`.** The note says so: it pins behaviour that was unpinned, not a change.

## What I could not break

- **F16 regeneration.** In a clean `mut` at `ec989ed`, `scripts/f16_parity_native.py --out` wrote 894 entries (`tree_clean True`). Against the committed file, after LF normalisation, `diff` shows one line: `engine_commit` `fa4929dd…` against `ec989edb…`. Both files have 894 keys, the symmetric difference is 0 and 0 values differ. `--check` exits 0.
- **Statistics re-derived without repository code:**
  - **F3, DeLong (1988).** I computed the structural components, the covariance of the two AUCs, the paired z and its two-sided p, the Wald and the logit intervals, on `F3_Y`/`F3_S1`/`F3_S2`. All 11 file values agree within 2.22e-15: `paired_p` mine 0.05934643879191981 against the file's 0.0593464387919201, and `paired_z` 1.8856180831641274 against 1.8856180831641252.
  - **F1, F1b, F1c and F1d.** Wilson score and Clopper-Pearson (beta quantiles) on (81, 263), (490, 500), (0, 20) and (20, 20). All 16 values agree within 1.11e-16.
  - **F13.** I recomputed `abs(engine - r)` for the 16 recorded pairs: maximum 2.7755575615628914e-17, 0 pairs whose `abs_deviation` field disagrees, 0 R values unequal to `proc_asah.json`. The `proc_asah.json` sha256 (CRLF read as LF) equals the recorded one. The run id is 37332685741 on both sides.
- **F19, my own plants on the synthetic cohort.**
  - Plants: sites `Llandough Univ Hospital` (3 rows, 1 event), `Whiston-Prescot` (11 rows), `Ørsted Klinik` (6 rows) and `Ysbyty Gwynedd` (the rest), plus a free-text column `referral_note` reading "seen at Llandough Univ Hospital ward C7".
  - Run result: exit 4, 0 socket calls, 1 telemetry send of 340 bytes, an aggregates document of 23,602 bytes, both schema-valid. There were 21 small cells, 0 unsuppressed, 0 structural violations.
  - My own search, without `scan.find`: 13 needles in 75 forms (raw, lower, upper, NFD, both JSON escapings, `quote`, `quote_plus`, underscores, hex, and a base64 prefix). The payloads were searched raw, lower-cased, URL-decoded and base64/urlsafe-decoded per token of 8 or more characters. **0 hits.**
  - The site levels in egress are `Site A`-`Site D` only. Every number of the three small sites is null.
- **F17.** Two runs of 200 rows gave `identical True`. Each plant was applied to a copy of run 2:
  - `, "seed": 12345` after `duration_s`: `run_json_masked`;
  - a temp path in `ingest_report.json`: `ingest_report_json`;
  - one pseudonym changed: `pseudonyms_json_masked`;
  - an extra `T8.docx`: `file_names` and `other_files`;
  - CRLF in `run.json`: `run_json_masked`;
  - `run.json` re-serialised with sorted keys: `run_json_masked`;
  - one float cut from 17 to 16 significant digits: `run_json_masked`;
  - fractional seconds in `started`: refused, `started occurs 0 times`;
  - `duration_s` as a string: refused.

  Only the documented volatile values passed: `duration_s` rewritten as `1E+5`, and `run_id` in `pseudonyms.json`. The mask is `('run_id', 'started', 'duration_s')` plus `run_id` in `pseudonyms.json`, no wider.
- **F12.** Each of the 11 fixtures, run through `halt_fixtures.check` with `--offline`, exited 3 and printed its own code first. Examples: `HALT H05: duplicate case_id rows with conflicting y_true while clustering.unit is none` and `HALT H12: paired compare with unmatched row_ids`. That is the unmatched path, not the `gates.py:219` missing-row_id path that also raises H12. Each fixture changed no file and wrote no `--out`. `HALT_CODES` minus the fixture codes is `['H10']`, which is flag-only. No E13 test file carries a skip or xfail marker. `tests/test_f12_halt_cli.py` gives 19 passed.
- **The note's other figures:**
  - the suite table and the 4 failed / 57 passed at `bcb1dac`;
  - `--check` 894/0/386;
  - run 37470619342: 7 of 7 jobs success, head `ec989edb…`; in its `pytest + ruff` log, day12 "196 passed, 3 skipped" and day13 "99 passed, 2204 deselected"; in docker-smoke, the F17 line "identical under the mask ['run_id', 'started', 'duration_s']: yes" and `other_files: equal e3b0c44298fc1c14` twice.

## CI

`bash workflows/ci_gate.sh <tip> HEAD` exited 0, but on runs that were not mine (non-blocking 2). My push's run is **37472872644**, head `ec989edb2361e9a1d1304adbe57ff4ab633769c5`, and I watched it by hand. `gh run watch --exit-status` exited 0. The run concluded **success, 7 of 7 jobs**, at 13:52:47Z:
- `pytest + ruff` (112300635515): "2166 passed, 137 skipped in 305.04s". 2166 + 137 = 2303, the local 2299 + 4. The last day-marker lines are "196 passed, 3 skipped" and "99 passed, 2204 deselected".
- `proofpack run inside unshare -rn (no network)` (112300635783): "namespace command: sudo unshare -n", then "22 passed in 2.51s".
- `Docker image smoke` (112300635792): "rows 46: matched 33, not matched 0, no oracle recorded 4, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 5".
- `pip-audit`, `wheel artefact`, `pytest -m ap4 with the [docx] extra installed` and `import proofpack (scipy uninstalled)`: success.

Afterwards, `git ls-remote origin 'refs/heads/ci/*'` printed nothing. No CI job is red. None of the three blockers is a CI failure.

## What I could not check

- **The reference image locally.** Docker is not running on this machine. I relied on the docker-smoke logs of runs 37470619342 and 37472872644.
- **The Pyodide half of F16.** It is lane S's, after a pin move.
- **`unshare -rn` on any runner.** The jobs I read fall back to `sudo unshare -n`.
- **A PowerShell 5.1 run of the suite.** I used Git Bash only.

## Sentences I refused to write

- "The gate is green on my push." The gate printed two runs it did not start. The green I report is run 37472872644, watched by hand.
- "F13's recorded comparison is fully re-checked by this command." B2 is the counter-example.
- "F19 leaks nothing." I searched the two payloads' bytes for the 13 needles in the forms listed. Subtraction recovers a small site's counts from the aggregates document (non-blocking 4).
- "Every register-class value has its own key in the file." B1 is the counter-example.

## Cleanup

The worktrees `tip`, `mut` and `base` were removed with `git worktree remove --force`. No node_modules junction existed. Nothing was committed.
