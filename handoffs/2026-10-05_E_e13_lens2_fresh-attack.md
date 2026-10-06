# E13 lens 2 - fresh attack - on `bcb1dac` (Tuesday 6 October 2026)

**Verdict: FAIL. Three blockers, all sentence violations.**

1. The new `parity.py` docstring says a test "looks up each of the 67 values ... among the file's values ... by exact equality". Since the gate repair `bcb1dac` it looks them up in a fresh compute instead. A value moved inside tolerance in the file passes all 17 F16 tests.
2. The new `suite_only` status text prints "checked by the test suite or a CI job, not by this command" on F13. A drift planted in F13's recorded comparison makes `proofpack fixtures --offline` exit 6 with no pytest involved. That is the counter-example lens 1 used against FA-B5.
3. The repair note (`notes/E13_repair1.md`) quotes the image report as "... suite only (...) 7". The image job printed `suite only (...) 5` in the note's own run 37464523986, and again in mine. The number was typed, not read from the run.

No number in the engine is wrong. I found no leak. The F16 file regenerates byte for byte. My own CI run on the tip is green on 7 of 7 jobs. Each of the six lens 1 blockers no longer reproduces, apart from the two places above where the repair wrote new sentences.

Scope: a cold lens on `git diff 941c8e4 bcb1dac` (E13 repair 1 and its gate repair) and the repair note `scratchpad/notes/E13_repair1.md`. I worked in three detached worktrees under `scratchpad/lens-E13-r2-fresh-attack/`, all removed at the end:
- `tip` at `bcb1dac`;
- `mut` at `bcb1dac`, for mutants and plants, each restored by `git checkout`;
- `base` at `941c8e4`.

Every Python process ran with `PYTHONPATH=<worktree>/src`, and printed `...\lens-E13-r2-fresh-attack\<worktree>\src\proofpack\__init__.py` before I used any number. Nothing was committed. The only ref I pushed went through `workflows/ci_gate.sh`.

## Measured figures (this session, Git Bash, Windows, win-amd64-cp314)

Environment: `PROOFPACK_REQUIRE_DOCX=1 PYTHONIOENCODING=utf-8 PROOFPACK_TR39_FULL=...confusables-18.0.0.txt`, with `PROOFPACK_ASAH_VECTORS` unset.

| | `bcb1dac` (this lens) | note's figure |
|---|---|---|
| full suite | 2293 passed, 4 skipped in 305.63 s, exit 0 | the same |
| skips | `[3] test_day12_r_captures.py:156` r_vectors_not_committed_dec77; `[1] test_doctor_cli.py:57` | the same |
| `-m day13` | 93 passed | 93 |
| `-m day12` | 196 passed, 3 skipped | the same |
| `-m day11` | 144 passed | 144 |
| `-m day10` | 262 passed | 262 |
| `ruff check .` / `ruff format --check .` | "All checks passed!" / "334 files already formatted" | the same |
| `doctor --offline` | exit 0, 17 `[ok` lines | the same |
| `fixtures --offline` | exit 0; "rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 7" | the same |
| `scripts/f16_parity_native.py --check` | "894 entries, 0 failures, 386 numeric entries bit-equal" | the same |

The earlier markers match lens 1's `941c8e4` figures (day12 196/3, day11 144, day10 262). The full suite grows by 24 tests, from 2269 to 2293, and day13 by 23, from 70 to 93.

**CI.** I ran `bash workflows/ci_gate.sh <tip> HEAD` at 12:52 UTC. It printed `gate: run 37464523986 ci: success` / `gate: GREEN bcb1dac` / exit 0. That is the builder's run from 12:36:53Z, not mine. My push started run **37466442454** (created 12:52:21Z, head `bcb1daca804a…`). I watched it myself with `gh run watch --exit-status` (exit 0), and **7 of 7 jobs concluded success**:
- `pytest + ruff` (job 112278552332): "2160 passed, 137 skipped"; `-m day13` "93 passed, 2204 deselected".
- `offline-namespace` (job 112278552237): "namespace command: sudo unshare -n", then "22 passed in 3.16s".
- `docker-smoke` (job 112278551908):
  - the image report line is "rows 46: matched 33, not matched 0, no oracle recorded 4, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 5";
  - both F17 steps print "other_files: equal e3b0c44298fc1c14";
  - "F17 (run) 5000 rows on linux-x86_64-cp312 (reference platform: yes); run exit codes [4, 4]; identical under the mask ['run_id', 'started', 'duration_s']: yes".
- `pip-audit`, the wheel, ap4 with the docx extra, and import with scipy uninstalled: success.

A third run on `ci/bcb1dac`, **37466777729** (created 12:55:03Z), was pushed by another session. It also concluded success. Afterwards, `git ls-remote origin 'refs/heads/ci/*'` printed nothing.

## Blockers

### B1 - `parity.py`: the docstring names a lookup in the file that the gate repair removed (sentence violation)

Verbatim, `src/proofpack/parity.py` lines 18-20 at `bcb1dac`:

> ``tests/test_f16_parity_native.py::test_every_register_class_value_is_in_the_file`` looks up each of the 67 values of the ``register``-class rows (F1-F6 and F8) among the file's values of the same fixture, by exact equality.

At `bcb1dac`, the test looks each value up among a **fresh `parity.compute()`'s** values by exact equality. It then requires only that the matching entry's **key** is in the committed file; it reads none of the file's values. The commit message of `bcb1dac` and the test's own docstring say so. The module docstring was not updated with it.

**Counter-example (run in `mut`).**
- I moved `F3-delong.paired_p` in `fixtures/f16_parity_native.json` from `0.0593464387919201` to `0.0593464392919201`. That is +5e-10, inside the closed 1e-9.
- `python -m pytest tests/test_f16_parity_native.py` gives **17 passed**.
- `F3-register`'s `paired_p` computes to `0.0593464387919201`. "Exactly in file F3 values: False".

So the 67 values are not looked up among the file's values. The builder's own RED run 37463363415 is a second counter-example: on Linux the register value is `0.05934643879192011`, and the file holds `0.0593464387919201`.

The same false claim is in the repair note, under "Sentences refused": "It holds every value of the non-`register`-class rows and an exactly equal value for each of the 67 `register`-class values (test above)". On the Linux runner the file does not hold an exactly equal value for `F3-register.paired_p`. That is the measured cause of RED run 37463363415. The test above does not check that property any more.

**Repro:** in a scratch copy, add 5e-10 to `F3-delong.paired_p` in the file, then `PYTHONPATH=<copy>/src python -m pytest tests/test_f16_parity_native.py` → 17 passed.

### B2 - F13's status cell reads "not by this command"; this command re-checks F13's recorded figures and exits 6 on a drift (sentence violation)

**The new text.** Repair 1 added `render/t12.py:54`, `STATUS_TEXT["suite_only"] = "checked by the test suite or a CI job, not by this command"`. It prints on F13, F18 and F20 (the note: "Any other `suite_only` row prints ... (F13, F18, F20)"). The T12 golden carries it on F13 at line 271. The same row's reason says "each within 1e-6 as recomputed here from the recorded engine and R numbers".

**What the check does.** `fixtures.f13_recorded_outcome` checks the following, and returns `not_matched` on any failure:
- the comparison file's hashes against `proc_asah.json`;
- the run id;
- each name's R value and tolerance;
- `abs(engine - r)`, which it recomputes.

**Counter-example (run in `mut`).**
- In `fixtures/r/f13_engine_comparison.json`, I raised `values["ndka auc"].engine` by 1e-3, from `0.6119579945799458`.
- `python -m proofpack.cli fixtures --offline --out <dir>` then exited **6**, with "rows 46: matched 35, not matched 1, ... suite only (...) 6".
- F13's status became `not_matched`, with reason "r_capture_recorded_not_matched: fixtures/r/f13_engine_comparison.json (GitHub run 37332685741, engine commit 9d285d98…): outside tolerance: ndka auc".

No pytest was involved. This is the same shape as lens 1's FA-B5 counter-example on F16, for which the repair introduced `SUITE_ONLY_MEASURED_TEXT` on F12, F16, F17 and F19 only. F13 does not set `evidence.measured_by_this_command`, so `status_text` gives it the "not by this command" text.

The R comparison itself was run inside the r-captures job, and the reason says so accurately. The status cell denies the re-check that this command makes.

**Repro:** add 1e-3 to any `engine` value in a scratch copy of `fixtures/r/f13_engine_comparison.json`, then `PYTHONPATH=<copy>/src python -m proofpack.cli fixtures --offline --out <dir>; echo $?` → 6.

### B3 - the repair note types the image report's suite-only count as 7; the runs print 5 (sentence violation, note only)

Verbatim, from the note, under the GREEN gate:

> the image report reads `rows 46: matched 33, ... no oracle recorded 4, ... not built 4, suite only (...) 7`

The note's own run 37464523986, job `Docker image smoke` (112272095844), printed "rows 46: matched 33, not matched 0, no oracle recorded 4, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 5". My run 37466442454 printed the same line.

33 + 4 + 4 + 7 = 48, not 46. The 7 is the Windows figure, carried over by hand.

**Repro:** `gh run view -R JoshSandhu/proofpack --job 112272095844 --log | grep "rows 46"`.

## Lens 1 blockers re-checked at `bcb1dac`

| lens 1 | at `bcb1dac` |
|---|---|
| **FA-B1** (F5 accuracy difference missing) | **Closed.** 894 entries; `F5-register.accuracy_diff.est` -0.08. My Newcombe (1998) method-10 paired interval, from the published formula with scipy's z and my own Wilson bounds, is [-0.15535638110228397, -0.010249291949335146]. The file holds [-0.1553563811022839, -0.010249291949335215], so the largest difference is 7e-17. Every one of the 204 numeric values the register's engine functions compute (F13 and F13b excluded) is in the file within 1e-9 relative. The new F16 `what` text holds. The parity docstring sentence about the test does not (B1). |
| **FA-B2** (label read from one side) | **Closed.** Plants through `parity.compare`, each one failure: method relabelled `closed`; `n` 100 → 100.0; `n` → `True`; est → None with a reason; est -1e-3. A key deleted from the file, an extra key and a missing fixture each fail. A +5e-10 move inside closed passes, as the tolerance allows. |
| **FA-B3 / RG-B2** (`unshare -rn` text) | **Closed.** All three cited jobs print "unprivileged user namespaces are unavailable on this runner; using sudo unshare -n" then "namespace command: sudo unshare -n": 112240530133 (run 37455062159), 112250748567 (37458152406) and 112251845081 (37458488364). All three runs are at head `941c8e4`. `ci.yml:159` writes `echo "$NS" > namespace.txt`. |
| **FA-B4 / RG-B1** (guard sentence) | **Closed.** The new text names the three attributes, and the limit test pins the two routes it does not see. |
| **FA-B5** (status text) | **Closed for F12, F16, F17 and F19. Reopened on F13 (B2).** |
| **FA-B6** (F17 other files) | **Closed.** See the F17 plants below. |
| **RG-B3** (F12 "no file written") | **Closed.** The text names the fixture's directory, its PROOFPACK_HOME and `--out`. |

I copied the six repaired test files into `base` (`941c8e4`) and ran the five other than `test_f17_determinism.py`: **64 passed, 23 failed**, the note's figure.
- Every new test fails there, except the F19 limit test. The note states that one pins unchanged behaviour.
- That includes all three `test_compare_fails_when_the_two_labels_differ` cases, `test_compare_reads_the_bytes_of_every_other_file`, `test_the_suite_only_status_cell_names_who_checked_the_row`, `test_every_register_class_value_is_in_the_file` and `test_f5_accuracy_difference_is_in_the_file_with_its_interval`.

## Non-blocking (record and carry)

1. **Mutants.** I ran 20 mutants of the new code against the seven E13/T12 test files (112 tests; baseline 112 passed). 17 were killed.
   - **M13 survives:** `status_text` returns the measured text for any row with `measured_by_this_command`, whatever its status. A `not_matched` F16 row would then print "checked by this command, against no independent oracle" instead of "not matched". No test renders a measured row that has failed.
   - **M19 survives:** `halt_fixtures.check`'s `ok` ignores `out_exists`. This is the same class as lens 1's M2 (FA-N1, carried).
   - **M10** (`other_files` hashes the bytes but not the path) survives. Under `identical` it is equivalent, because `file_names` catches a rename.
   - **Killed:** label check removed (M1), tol only (M2), class only (M3); F5 block removed (M4) or its arguments swapped (M5); `other_files` dropped (M6), names only (M7), basename exclusion (M8), `.json` exclusion (M9); status text ignoring measured (M11) or giving the measured text for every `suite_only` row (M12); `evidence_rows` reverted (M14); the summary label (M15); the F12, F19 and F17 reasons and the F16 `what` text reverted (M16, M17, M18, M20).
2. **F17 does not see empty directories.** An empty `emptydir/` in one run only left `identical` True, because `file_names` lists files only. No run writes directories today.
3. **`ci_gate.sh` reproduced FA-N4.** A re-gate printed the builder's run 37464523986 as GREEN while its own push's run 37466442454 was `in_progress`. A second session pushed the same branch name at 12:55 (run 37466777729), so two gates on one sha share `ci/<short>`, and either one's delete removes the branch under the other. Both runs concluded success. This is outside the E13 diff (`workflows/`).
4. **The `parity.compare` key-set message names sides from the fresh run's view.** A key deleted from the committed file reads "missing [], extra ['F5-register.accuracy_diff.ci_lo']". This predates E13; the failure is still counted.
5. **Constants labelled `bootstrap` accept a hand-edit inside 4 decimals.** These are the 24 `bootstrap` entries, for example `E6.calibration_block.*.bootstrap.thresholds.max_frozen_variance_share`, which are thresholds, not resampled values. This predates repair 1.
6. **The CI job's display name "proofpack run inside unshare -rn (no network)"** is unchanged (the note carries it).

## What I could not break

- **F16 regeneration.** `scripts/f16_parity_native.py --out` at `bcb1dac`, on a clean tree, against the committed file:
  - after LF normalisation, `diff` prints one line, `engine_commit` `fa4929dd…` against `bcb1daca…`;
  - 894 and 894 keys, symmetric difference empty, 0 entries differ.
- **F19, with my own plants on top of `small_cell_cohort`.**
  - Plants: `Harefield Hospital` (4 rows, 1 event), a note column reading "referred from Harefield Hospital" and a `ward` column "Ward 7B Lister".
  - `f19.check` gives `[]`; 21 small cells, 0 unsuppressed. The egress site levels are only `Site A`-`Site F`, and the three small sites (A, C, F) carry `est`/`n`/`k`/`ci_lo` null.
  - I searched the telemetry (340 bytes) and aggregates (26,981 bytes) payloads myself for 12 names and fragments, without `scan.find`. Each was tried as raw, lower-cased, NFD, JSON-escaped (both `ensure_ascii` settings), URL-quoted and `quote_plus`, `'`/`&` forms and underscores. The payloads were searched raw, lower-cased, URL-decoded, JSON round-tripped, and after base64/urlsafe-base64 decoding of every token of 8+ characters. **0 hits.**
  - `two_by_two` is the overall table only (tp 94, fp 68, fn 31, tn 207). The calibration bins are suppressed. No cell with `n` below 10 is shown.
- **F17: real nondeterminism through the mask** (400-row repeat, two runs, `identical` True as built). Each plant was applied to one copy:
  - key order reversed in `ingest_report.json`: caught by `ingest_report_json`;
  - a trailing zero on one float in `run.json`: caught by `run_json_masked`;
  - a temp path added to `pseudonyms.json`: caught by `pseudonyms_json_masked`;
  - a new `"finished"` timestamp: caught by `run_json_masked`;
  - a second `started` key: refused (`ValueError: started occurs 2 times`).

  Masked as documented: `started` changed to 1999-01-01 and `duration_s` to 9e99. The mask is the three documented keys and `run_id` in `pseudonyms.json`, and no wider.
- **F12.** All 11 fixtures exit 3 and print their own code with the expected message. Two examples: H05 "duplicate case_id rows with conflicting y_true while clustering.unit is none", and H12 "paired compare with unmatched row_ids". H10 is the only HALT code without a fixture (`FLAG_ONLY_CODES` = H10, W14, W16).
- **The note's other figures.** The suite table, the 23 failed / 64 passed at `941c8e4`, ap4 "197 passed, 1 skipped", F19 in the namespace "22 passed", and CI `-m day13` "93 passed" all re-measured equal. The 46-line diff of the parity file is +45 −1; the removed line is the old `engine_commit`.

## What I could not check

- **The reference image locally.** Docker is not running on this machine. I relied on the logs of runs 37464523986 and 37466442454.
- **The Pyodide half of F16.** It is lane S's, after a pin move.
- **`unshare -rn` on any runner.** Every job I read fell back to `sudo unshare -n`.
- **Secondary (subtraction) suppression.** FA-N3, carried. I did not re-measure it.
- **A PowerShell 5.1 run of the suite.** I used Git Bash only.

## Sentences I refused to write

- "F16 holds an exactly equal value for every register-class value." B1 is its counter-example on Linux.
- "The gate on `bcb1dac` is green" as a reading of the gate's own output. The gate printed someone else's run. The green I report is run 37466442454, which I watched.
- "F19 leaks nothing." I searched the two payloads' bytes in the forms listed above, for the names I planted.
