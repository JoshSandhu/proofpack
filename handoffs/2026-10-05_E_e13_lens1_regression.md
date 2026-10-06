# Lane E - build day 13 (E13, validation by code) - lens 1, cold regression-and-record, at `941c8e4` (pre `5154468`; Tuesday 6 October 2026)

**FAIL. 3 blockers, all of them sentences (the hard rule).**

Every count, hash and command result in the build note that I could re-run reproduces, in Git Bash and in PowerShell 5.1. The code does what the note says it measures. What fails is shipped text that says more than the checks inspect, or says something the gate's own logs contradict:

- **B1.** `src/proofpack/f19.py` says a transport that bypassed the recorder "would be counted, not sent". I built one that was neither counted nor stopped: 158 bytes reached a listener on 127.0.0.1 with `socket_calls` 0. A second version, which also called the recorder, passed every F19 check (`f19.check(r) == []`).
- **B2.** Five pieces of shipped text say F19 ran, or runs in CI, inside `unshare -rn`. These are the F19 report reason (pinned by a test), the evidence `where`, two docstrings in the test file and the `f19.py` docstring. Both gate runs used `sudo unshare -n`. The build note's own refused-sentence list includes "F19 runs inside unshare -rn in CI".
- **B3.** Row F12's description on the page reads "no file written". `halt_fixtures.check` inspects only the fixture directory and `--out`. A planted HALT that wrote a file outside those two places scored `ok True`.

One process finding is not a defect of E13. My own run of `workflows/ci_gate.sh` printed **`gate: RED 941c8e4`** and exited 1. The workflow run my push started, **37458488364**, concluded **success** on all 7 jobs. The script never watched that run (details under N1).

## Setup

Detached worktrees under `scratchpad/lens-E13-r1-regression/`:
- `tip` at `941c8e4`: both suites, the CLI and script commands, probes, and mutants. Each mutant was applied alone and then restored; `git status --short` was empty afterwards.
- `pre` at `5154468`: the new and modified test files copied in, and in a second stage the new modules too.
- `wip` at `6669316`: the note's "before" figures.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`.

Environment: `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8`, `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, `PROOFPACK_ASAH_VECTORS` unset. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1.

Three things to discount:
- My first Git Bash suite launch had `PYTHONPATH` still pointing at `wt-e13\src`, because a heredoc collapsed the backslashes. I killed it within a minute and used none of its output.
- My first mutant batch ran while the Git Bash suite was on its `-m day12`/`day11`/`day10` runs. I re-ran all four markers afterwards with nothing else touching the tree (figures below). They are identical.
- A fresh-attack lens ran its gate on the same sha at 11:42 UTC (run 37458152406) and wrote `handoffs/2026-10-05_E_e13_lens1_fresh-attack.md` into `wt-e13`, untracked.

## Blockers

### B1 - `f19.py` says a bypassing transport "would be counted, not sent"; it was neither counted nor stopped (sentence)

Verbatim, `src/proofpack/f19.py` lines 15-17:

> While the run lasts, `socket.socket`, `socket.getaddrinfo` and `socket.create_connection` refuse and count every call (`_no_sockets`), so a transport that bypassed the recorder would be counted, not sent.

The test name `test_f19_a_send_that_bypasses_the_recorder_is_counted_and_refused` makes the same general claim. That test plants one bypass only: one that looks up `socket.getaddrinfo` and `socket.create_connection` on the module at call time.

The build note lists "The F19 socket guard catches every network path" under sentences refused, and open question 4 raises the gap. The docstring still asserts it.

The counter-example is `scratchpad/lens-E13-r1-regression/counter/test_lens_f19_counter.py`. It is not committed.
- The client module does `from socket import socket as _EarlySocket` at import time. This is ordinary import style, and the reference is taken before the guard is installed.
- `telemetry.send` is monkeypatched to connect with that class to a listener on 127.0.0.1. The listener runs in a child process, so the guard does not affect it.
- Result:
  - plant A (the send skips the recorder): `socket_calls 0 telemetry_sends 0 received 158 b"PLANTED-EGRESS ['duration_s', 'engine_version', 'halt_code',"`, and `check` = `['planted: telemetry_sends', 'planted: telemetry_valid']`. The bytes left, and the guard did not count them.
  - plant B (the same send, then the real `send` with the recorder): `socket_calls 0 telemetry_sends 1 received 158 check []`. Every F19 check passes while bytes leave over a real socket.

Things I tried that the guard does catch:
- A `create_connection` reference taken early: `socket_calls 1`, because `socket.create_connection` calls the patched module-level `getaddrinfo`.
- Mutant M2 (the guard patches `socket.socket` only): the test suite catches it (KILLED).

Repro: `PYTHONPATH=<tip>/src python -m pytest -q -s scratchpad/lens-E13-r1-regression/counter/test_lens_f19_counter.py`. Copy the file into `tests/` first, because it imports `proofpack` from the worktree. Expected result: 2 passed, and the A and B lines above.

Repair (wording only): say what the guard patches. For example: "the three module attributes `socket.socket`, `socket.getaddrinfo` and `socket.create_connection` refuse and count calls made through them; a client holding its own reference to `socket.socket` is not seen (lens counter-example)". Rename the test after what it plants.

### B2 - shipped text says F19 ran, or runs in CI, inside `unshare -rn`; both gate runs used `sudo unshare -n` (sentence and record)

The text, verbatim:
- `src/proofpack/fixtures.py` line 1855-1857, the F19 report reason, which is page text for `/trust/validation`: "The --offline run inside unshare -rn is Linux only: the CI job offline-namespace (artefact f19-offline-namespace)". `tests/test_e13_report_rows.py:70` pins it: `assert "unshare -rn" in _row(report, "F19")["reason"]`. It is also in the T12 golden, row F19.
- `src/proofpack/fixtures.py` line 1896, evidence `where`: "proofpack run --offline inside unshare -rn, then the F19 test file inside the same namespace".
- `tests/test_f19_egress_bytes.py` line 7: "The CI job ``offline-namespace`` runs this file inside ``unshare -rn``".
- `tests/test_f19_egress_bytes.py` lines 172-176, the gate-repair docstring: "failed inside ``unshare -rn`` with ``socket_calls`` 0".
- `src/proofpack/f19.py` line 40: "The network half of gate 8 (``--offline`` inside ``unshare -rn``) is Linux only: the CI job ``offline-namespace`` ... runs it".

What the logs show (`gh run view --log --job`):
- GREEN run 37455062159, job 112240530133: `unprivileged user namespaces are unavailable on this runner; using sudo unshare -n`, then `namespace command: sudo unshare -n`, then `20 passed in 2.80s`.
- RED run 37453449607, job 112235248644: the same two lines (`namespace command: sudo unshare -n`), then `E assert (0 >= 1)` and `1 failed, 18 passed in 1.96s`.

The build note itself refuses "F19 runs inside unshare -rn in CI." ("Not so on that runner: it used the sudo unshare -n fallback"), and asks Josh whether `sudo unshare -n` satisfies gate 8. Until he answers, the page must not say `-rn`.

Repro: `gh run view 37455062159 --log --job 112240530133 | grep "namespace command:"` gives `namespace command: sudo unshare -n`; then `grep -n "unshare -rn" src/proofpack/fixtures.py tests/test_f19_egress_bytes.py src/proofpack/f19.py`.

Repair: name the namespace the job used. The job records it in `namespace.txt` inside the artefact, or the text can say "the job's namespace (`unshare -rn` where the runner allows it, otherwise `sudo unshare -n`; on the gate runs it was `sudo unshare -n`)". Change the test at line 70 to pin the new wording.

### B3 - the F12 row says "no file written"; the check inspects two places only (sentence, page copy)

Verbatim:
- `src/proofpack/fixtures.py` line 2173-2175, the F12 description shown in T12 and on the trust page: "the HALT fixtures of proofpack.halt_fixtures run through proofpack run or compare with --offline: exit 3, the fixture's own code on the first stderr line, no file written".
- `halt_fixtures.check` snapshots only `work` (the fixture's inputs and its `PROOFPACK_HOME`) and tests whether `--out` exists. The build note describes this exactly ("no file added, removed or changed under the fixture directory, and `--out` absent"). The page row does not.

Counter-example (run): `hf.check(hf.FIXTURES[0], <tmp>/w, writes_elsewhere)`. The invoke function writes `leaked_run.json` into a different temporary directory, then returns exit 3 with the right HALT line and the no-document line. Output: `ok True files_changed [] outside file exists True`.

Repro: `PYTHONPATH=<tip>/src python scratchpad/lens-E13-r1-regression/counter/f12_write_elsewhere.py` prints `ok True files_changed [] outside file exists True`. It is the same shape as `writes_a_document` in `tests/test_f12_halt_cli.py::test_f12_check_reports_a_halt_that_leaves_a_file_or_an_out_directory`, but it writes outside `work`.

Repair: "no file added, removed or changed under the fixture's directory or its PROOFPACK_HOME, and --out absent". Then update the T12 golden.

## Non-blocking

**N1 - `ci_gate.sh` reported RED although the run my push started is green.** This is not an E13 defect.
- `gate.txt`:
  - `gate: run 37458152406 ci: ` (empty conclusion)
  - `gate: run 37455062159 ci: success`
  - `gate: RED 941c8e4`, exit 1, at 11:51:22 UTC
- The script selects runs by `--commit <sha>` and `headBranch == ci/<short>`. So it picked up:
  - the builder's earlier gate run 37455062159 (same branch name);
  - another session's concurrent gate run 37458152406, pushed at 11:42:07;
  - not my own run 37458488364, which was created at 11:45:08 and concluded **success** on 7 of 7 jobs at 11:52:45.
- `gh run watch` on 37458152406 returned while its `pytest + ruff` job was still in progress. I did not establish why. That run later concluded `success`.
- My gate deleted `ci/941c8e4` at 11:51:22, while my run and the other session's run were still in progress.

Two gates on one sha share one branch name, and an earlier gate's runs satisfy a later gate's query. The gate needs a per-push identifier, for example the run's `head_sha` plus a creation time after the push, or a unique branch suffix.

**N2 - check branches no test pins.** I applied each mutant alone and ran the test files named:

| mutant | tests | result |
|---|---|---|
| M6 `structural_violations` skips calibration bins | `test_f19_egress_bytes.py` | SURVIVED, 20 passed |
| M13 `structural_violations` skips two-by-two tables | `test_f19` + `test_e13_report_rows` | SURVIVED, 30 passed |
| M17 a suppressed cell carrying a value is not reported | same | SURVIVED, 30 passed |
| M14 Numbers that are small on their own counts are not marked small-only | same | SURVIVED, 30 passed |
| M7 the fairness-gap rule in `small_only_values` dropped | `test_f19` | SURVIVED, 20 passed |
| M11 `_small_row` reduced to `n < 10` (events and non-events ignored) | `test_f19` | SURVIVED, 20 passed |
| M16 `sites_pseudonymised` not in `check` | `test_f19` + `test_e13_report_rows` | SURVIVED, 30 passed |
| M8 the scanner's `percent_decoded` view dropped | `test_f19` | SURVIVED, 20 passed |
| M1 `check` drops `hits` | `test_f19` | KILLED, `test_f19_small_cell_values_with_their_counts_nulled_are_caught` |
| M2 guard patches `socket` only | `test_f19` | KILLED, `test_f19_a_send_that_bypasses_the_recorder_is_counted_and_refused` |
| M15 long small-only values not searched in bytes | `test_f19` + rows | KILLED, `test_f19_the_small_cells_are_the_two_planted_sites_...` |
| M10 `f19_behaviour` ignores failures | rows + `test_f19` | KILLED, `test_f19_one_failing_cohort_is_not_matched` |
| M3 `halt_fixtures.check` ignores changed files | `test_f12_halt_cli.py` | KILLED, `test_f12_check_reports_a_halt_that_leaves_a_file_or_an_out_directory` |
| M4 `f17.mask` accepts a duplicate | `test_f17_*` | KILLED, `test_compare_dirs_refuses_a_masked_key_that_occurs_twice` |
| M9 `ingest_report.json` not compared | `test_f17_*` + rows | KILLED, `test_f17_cli_twice_same_platform_repeat_...` |
| M5 closed tolerance 1e-6 | `test_f16_parity_native.py` | KILLED, `test_compare_catches_a_planted_numeric_drift_beyond_the_tolerance[closed-2e-09-False]` |

Neither cohort has a small calibration bin, a small two-by-two table, or a site row with n >= 10 and fewer than 5 events. The leaky plant changes cells only. So the bins and two-by-two branches, and the events part of this module's own copy of the 10/5/5 rule, never fail anywhere.

The note does not claim they were planted: its "Plants" list names only the checks that did fail. This is a test gap, not a false sentence. Each surviving mutant needs one plant.

**N3 - the re-run commands in the note fail as written, in both shells.**
- `bash <scratchpad>/e13/suite.sh final`: Git Bash prints `bash: line 1: scratchpad: No such file or directory`. PowerShell 5.1: `powershell -File <scratchpad>\e13\suite_final.ps1` is a parse error (the `<` operator is reserved). These are placeholders. The real paths are `C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/e7ef1e65-84a2-4100-bf4b-f3dd52cd1f7f/scratchpad/e13/`.
- `python scripts/f16_parity_native.py --check` without `PYTHONPATH` forced imports the main tree in both shells (`C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py`) and exits 1 with `ImportError: cannot import name 'parity' from 'proofpack'`. With `PYTHONPATH=<tree>/src` it prints the note's line exactly. The note's Suite section says `PYTHONPATH` was forced; the re-run block does not repeat it.

**N4 - the five new test files pin by import only at `5154468`.**
- Copied alone into `pre`: each aborts at collection with `ImportError: cannot import name 'f17' | 'halt_fixtures' | 'parity' | 'f19' from 'proofpack'`.
- With the new modules also copied in (`f17.py`, `f19.py`, `parity.py`, `halt_fixtures.py`, `egress/scan.py`, the two scripts and the F16 JSON), these fail at `5154468`, each on an assertion:
  - `test_e13_report_rows.py`: 9 failed, 1 passed;
  - `test_f12_halt_cli.py`: 3 failed, 16 passed (the three report-row tests);
  - `test_f16_parity_native.py`: 1 failed, 11 passed (ancestor check);
  - `test_f17_reference_image.py`: 1 failed, 8 passed (the `ci.yml` step);
  - `test_f19_egress_bytes.py`: 1 failed, 19 passed (the `ci.yml` step).

The rest test the new modules themselves. Their evidence is the mutant table above (N2), not the pre-build run.

The three modified files fail at `5154468` on assertions, not on imports:
- `test_fixtures_cmd.py`: 5 failed (summaries `{'not_built': 5} != {'not_built': 4}`, the status lists, `KeyError: 'F16'`);
- `test_workflows.py`: 1 failed (`{'ci': 6} != {'ci': 7}`);
- `test_halt_gates.py`: the strengthened `test_gate_exits_3_and_writes_nothing` passes at `5154468`, 36 passed. It strengthens a test and pins no engine change, which the note does not claim.

The note's claim about the old test reproduces. At `5154468` the old scenarios without a mapping print `HALT H07: run proofpack map first: no confirmed mapping.json was given` for H01-H07 and H11, and `HALT H08` / `HALT H09` for those two, all with exit 3.

**N5 - "the four fixtures green in CI on the release image" (the brief).** Only F17's two-container comparison runs on the image. In the image, `proofpack fixtures` reports `rows 46: matched 33, not matched 0, no oracle recorded 4, ..., not built 4, compared by the test suite only 5` (run 37455062159, docker-smoke), and F16 reads `no_oracle_recorded` there. F12 and F19 run in the CI venv jobs, not on the image. The note says this in parts; its cut list does not say it in one line.

**N6 - the note says "scipy 1.18.1" for the F16 file.** The committed file records `scipy_available: true` and no scipy version. The 1.18.1 is the machine's (`fixtures --offline` prints it). Minor.

## Re-measured (all match the note unless stated)

| | note | Git Bash (lens) | PowerShell 5.1 (lens) |
|---|---|---|---|
| full | 2269 passed, 4 skipped, exit 0 | 2269 passed, 4 skipped in 384.23s, exit 0 | 2269 passed, 4 skipped in 418.21s, exit 0 |
| skips | `[3] r_vectors_not_committed_dec77`, `[1] test_doctor_cli.py:57` | same | same |
| -m day13 | 70 passed | 70 passed (26.80s; clean re-run 22.10s) | 70 passed |
| -m day12 | 196 passed, 3 skipped | same (clean re-run 38.28s) | same |
| -m day11 | 144 passed | 144 passed | 144 passed |
| -m day10 | 262 passed | 262 passed | 262 passed |
| ruff check / format --check | All checks passed! / 332 files already formatted | same | same |
| doctor --offline | exit 0, 17 `[ok` | exit 0, 17 | exit 0, 17 |
| fixtures --offline | rows 46: matched 35, not matched 0, no oracle 0, no independent oracle 0, not built 4, suite only 7 | same, exit 0 | same, exit 0 |
| `f16_parity_native.py --check` | 885 entries, 0 failures, 382 bit-equal | same (forced PYTHONPATH), exit 0 | same, exit 0 |
| before suite at 6669316 | 3 failed, 2232 passed, 4 skipped; day13 1 failed, 35 passed | 3 failed, 2232 passed, 4 skipped in 323.42s (the F19 suppression plant, `test_invariants` hard-coded marker, `test_telemetry` module-level import); day13 1 failed, 35 passed | not run |

**F19 figures** (`f19.run_all()` in `tip`). Every one matches the note's table:
- synthetic: telemetry 340 bytes, 1 send, valid; aggregates 22,829 bytes, valid; cells 83; small rows 0; small-only floats 7 (2 shared); needles 8; hits 0; socket calls 0; exit 4.
- small_cell_real_site_names: telemetry 340; aggregates 25,577; cells 97; small rows Addenbrooke's 9/4 and St Mary's 7/2; small cells 14 (0 unsuppressed); structural violations 0; small-only 113 (8 shared); needles 117; hits 0.

**F17 in CI** (docker-smoke logs, both gate runs):
- The compare-dirs step printed `run_json_masked: equal d57c6d40ed526901`, `manifest_masked a8729e4184c8d5ed`, `pseudonyms_json_masked ca4e145eb123633e`, `ingest_report_json d306a3aa6600d4a4` and `file_names 7fe1d0490f327ef2`.
- Both runs: platforms `['linux-x86_64-cp312', 'linux-x86_64-cp312']`, exit codes 4 and 4.
- Artefact 11409741246 (GREEN) and 11408216255 (RED run).
- Base image `python:3.12-slim@sha256:ddb0207a` in run 37453449607 and `@sha256:05cda977` in 37455062159, as the note says.

**F17 locally:**
- Two CLI runs of 400 rows (exit 4 and 4) compared equal (exit 0).
- `--require-reference-platform`: exit 1.
- One digit of one `est` changed (`0.1691318580586025` to `...021`): exit 1, `identical ... no`.
- `started` and `duration_s` edited only: exit 0.
- `started` duplicated: exit 1, `refused: started occurs 2 times; expected exactly once`.

**CI pytest job** (run 37455062159, job 112240530044): `2136 passed, 137 skipped`, then `day markers declared: day1 ... day13`, and `-m day13`: `70 passed, 2203 deselected`. `offline-namespace`: `20 passed in 2.80s`, artefact 11409111479.

**Nothing weakened.** `git diff --name-status 5154468 941c8e4` shows 22 files, all `M` or `A`, no `D`. There are no added skip, xfail, `only` or `todo` markers. The two removed `assert` lines were replaced by stronger ones: `assert not out.exists()` plus the printed-code check, and the CI count 6 to 7. `day13` is in `pyproject.toml`, and CI reads its markers from there (`day markers declared: ... day13`).

## What I could not break

- **The scanner** (`egress/scan.find`). I ran 3,000 random plants: the six real-looking names inside standard and url-safe base64 at random offsets (with and without padding), `quote`, `quote_plus`, JSON `ensure_ascii`, and upper case, wrapped in non-JSON prefixes and suffixes. 0 missed.
- **F17's mask.** A changed estimate digit, a duplicated `started` and a manifest from the wrong platform each fail. Volatile-only edits pass. All three files in a run directory (`ingest_report.json`, `pseudonyms.json`, `run.json`) are compared.
- **F16 `compare`.** The tolerance mutant is caught. `--check` reproduces 885/0/382 in both shells.
- **F12 `check`** catches a wrong printed code, a file under `work`, a ledger write, `--out` present and a silent halt (tests plus M3). It does not catch a write outside `work` (B3).

## What I could not check

- The urllib plant's `socket_calls 0` inside `sudo unshare -n` (RED run). No Linux namespace is available here, so it stays not diagnosed [unverified], as the note says.
- The reference image locally. Docker was not used on this machine.
- The Pyodide half of F16. It is lane S's.

## Sentences I refused to write

- "The F19 socket guard stops a bypassing send." B1 shows it does not.
- "The gate is GREEN on my run." The script printed RED. Only the run object 37458488364 is green, and the script did not watch it.
- "F12 shows a HALT writes nothing." It shows nothing changed under the fixture directory and `--out` is absent.

## Cleanup

Worktrees `tip`, `pre` and `wip` removed with `git worktree remove --force`. No node_modules junction existed. Nothing was committed or pushed except the throwaway `ci/941c8e4` branch that `ci_gate.sh` pushed and deleted.
