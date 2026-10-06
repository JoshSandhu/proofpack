# Lane E - build day 13 (E13, validation by code) - lens 2, cold regression-and-record, at `bcb1dac` (pre `941c8e4`; Tuesday 6 October 2026)

**FAIL. 1 blocker, a sentence (the hard rule).**

Every count, hash and command result in the repair note that I re-ran reproduces in Git Bash, except one CI figure the note misquotes (N1). Each regression test the note lists fails at `941c8e4` on the assertion the note quotes. The six lens-1 blockers FA-B1..B6 and the three RG-B1..B3 are closed by what the code and the shipped text now say. What fails:

- **B1.** The `parity.py` module docstring says `test_every_register_class_value_is_in_the_file` "looks up each of the 67 values ... among the file's values of the same fixture, by exact equality". Since the gate repair `bcb1dac`, the test looks them up among a fresh `parity.compute()`'s values and asks only for the key in the file. I moved the committed F3 value `0.0593464387919201` by 1e-12: the test file still gave **17 passed** and `--check` "0 failures".

## Setup

Detached worktrees under `scratchpad/lens-E13-r2-regression/`:
- `tip` at `bcb1dac`: suites, CLI and script commands.
- `pre` at `941c8e4`: the six changed test files copied in, run, then restored with `git checkout -- tests`. Afterwards the same worktree was moved to `bcb1dac` (`git checkout --detach`) and used for plants and mutants. Each plant was applied alone and restored with `git checkout`; `git status --short` was empty after each.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Environment: `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8`, `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, `PROOFPACK_ASAH_VECTORS` unset. Windows 11, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1.

## Blockers

### B1 - `parity.py` says the register-class test looks values up "among the file's values ... by exact equality"; since `bcb1dac` it does not (sentence)

Verbatim, `src/proofpack/parity.py` lines 18-20 at `bcb1dac`:

> ``tests/test_f16_parity_native.py::test_every_register_class_value_is_in_the_file`` looks up each of the 67 values of the ``register``-class rows (F1-F6 and F8) among the file's values of the same fixture, by exact equality.

The test body at `bcb1dac` (`tests/test_f16_parity_native.py:533-541` of the diff): `block = fresh["fixtures"][row.fixture]`, then `keys = [k for k, e in block.items() if float(value) in _numbers(e.get("value"))]`, then `assert any(k in committed["fixtures"][row.fixture] for k in keys)`. The exact lookup is in the fresh compute. The committed file is asked for the key only. The gate repair changed the test and its own docstring, but not this sentence, which describes the `923a018`/`a894fee` version.

Counter-example (run, in the `bcb1dac` plant tree):
- `fixtures/f16_parity_native.json` line 339, F3 entry `"value": 0.0593464387919201` changed to `0.0593464387929201` (+1e-12, inside the closed tolerance 1e-9). This is the `F3-register.paired_p` value that RED run 37463363415 named.
- `pytest tests/test_f16_parity_native.py`: **17 passed in 1.39s**.
- `python scripts/f16_parity_native.py --check`: `F16 native check: 894 entries, 0 failures, 385 numeric entries bit-equal`.

If the sentence were true, the test would have failed: the file no longer holds the computed value exactly.

The same gap reaches two other sentences:
- The test's name, `test_every_register_class_value_is_in_the_file`. With the plant, that exact value is not in the file, and the test passes. What it checks is "a key whose fresh value equals each register-class value is in the file".
- The note's refused-sentence line: "an exactly equal value for each of the 67 `register`-class values (test above)". On this machine the file does hold all 67 exactly. My own script, which reads the committed file and no repository test, printed `register-class values 67 not exactly in the committed file 0`. But the cited test no longer measures that, and on the Linux runner one of the 67 is not bit-equal (run 37463363415).

Repro: `sed` the line-339 value as above in a scratch worktree at `bcb1dac`, then `PYTHONPATH=<wt>/src python -m pytest -q tests/test_f16_parity_native.py`, which gives 17 passed.

Repair (wording only): say what the test does. For example: "looks up each of the 67 values among a fresh `compute()`'s values of the same fixture by exact equality, and requires that entry's key in the committed file, whose values `compare` holds to the fresh run under the labelled tolerances". The test name could become `..._has_its_key_in_the_file`. Add the parity.py sentence to `FALSE_AT_941C8E4`, or to a second list for sentences found false at `bcb1dac`.

## Non-blocking

**N1 - the note misquotes the docker-smoke image report.** The note says: "`docker-smoke`: the image report reads `rows 46: matched 33, ... no oracle recorded 4, ... not built 4, suite only (...) 7`". Those figures add up to 48. The job log of run 37464523986 (job 112272095844, 12:37:21Z) reads `rows 46: matched 33, not matched 0, no oracle recorded 4, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 5`. My own run 37466777729 (job 112279691478) prints the same line. The figure is 5, not 7. Correct the note before it becomes the handoff.

**N2 - `ci_gate.sh` reported GREEN without watching its own push's run (FA-N4 / RG-N1, carried; reproduced).** My gate started at 12:54:56Z. It printed:
- `gate: run 37466442454 ci: success`: another session's push of the same sha at 12:52:21Z;
- `gate: run 37464523986 ci: success`: the builder's run;
- `gate: GREEN bcb1dac`, exit 0, at 13:01:40Z.

It never watched run **37466777729**, the run its own push started at 12:55:03Z, which was still `in_progress`. It deleted `ci/bcb1dac` at 13:01:40Z, while that run, and possibly the other session's gate, were still in flight. I watched 37466777729 myself (`gh run watch --exit-status`, exit 0): **success, 7 of 7 jobs**, finished 13:02:48Z. This is outside the E13 diff (`workflows/`). It is recorded because two lenses on one sha now race each other's branch.

**N3 - an open item from lens 1 that the note's carried list omits.** Fresh-attack non-blocking 10 is not carried under any FA-N id: D1 F14's `diff_vs_complement` case and the F2-against-(85, 15, 25, 175) case are not in the `F14-newcombe` register row, so they are not in F16 either. The note's FA-N1..N7 map to lens-1 items 1-9 only.

**N4 - F17's new `other_files` check has compared zero files on every run measured.** Each run directory held only the three known files, so the hash `e3b0c44298fc1c14…` is the SHA-256 of zero bytes. This held for:
- both CI steps in runs 37464523986 and 37466777729: `other_files: equal e3b0c44298fc1c14`;
- the local `proofpack fixtures --offline` F17 item: `sha256_run1 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- my 400-row probe: files `['ingest_report.json', 'pseudonyms.json', 'run.json']`.

The F17 reason prints "...the file lists and every other file's bytes: 6 of 6 equal". That is true, but it does not say there were none. The note says so for CI ("neither run directory held a file beyond the three"); the report row does not. It is not a false sentence. A row that named the count (0) would not read as if documents had been compared.

**N5 - test gaps the repair left, re-measured here.** F17 mutants M16 (the `pseudonyms_json_masked` hash replaced by a constant) and M17 (the same for `ingest_report_json`) still survive. Each gave `57 passed` over `test_f17_reference_image.py`, `test_f17_determinism.py`, `test_e13_report_rows.py` and `test_fixtures_cmd.py`. The note carries them as "not re-run after this repair"; they are now measured as surviving.

**N6 - the pre-build method has two soft spots, neither a gap in what is pinned.**
- `test_t12.py::test_every_report_row_appears_in_t12` fails at `941c8e4` with `AttributeError: module 'proofpack.render.t12' has no attribute 'status_text'`, not on an assertion. FA-B5 is still pinned on an assertion by `test_the_suite_only_status_cell_names_who_checked_the_row` (`assert 'compared by...t suite only' not in '<!DOCTYPE h...`).
- Three of the 13 `FALSE_AT_941C8E4` parameters target test files: `test_f19_egress_bytes.py` twice and `test_f16_parity_native.py` once. With the new test files copied into `941c8e4` they pass, so only the 10 that target `src/` fail there. They pin text in test files, which is not behaviour.

**N7 - note wording.** "The test at `test_e13_report_rows.py:70` that pinned the old wording is deleted." No test function was deleted. One `assert` line was removed from `test_no_row_says_verified_and_ci_artefacts_are_marked_unseen`, and its subject moved into the new `test_the_f19_row_names_the_namespace_fallback_and_the_three_socket_attributes`.

**N8 - the note's re-run commands fail in PowerShell 5.1.** The note labels them "Git Bash", and in Git Bash all of them work.
- `cd ... && PYTHONPATH=... python scripts/f16_parity_native.py --check`: `The token '&&' is not a valid statement separator in this version.`
- `bash <...>/suite.sh mytag` and `bash .../ci_gate.sh ...`: in PowerShell, `bash` resolves to `C:\Windows\system32\bash.exe` (WSL), which prints `execvpe(/bin/bash) failed: No such file or directory` and exits 1.
- `git -C ... log --oneline -1  # bcb1dac` works in both shells.

## Re-measured

| | note (bcb1dac) | Git Bash (lens, `tip`) | PowerShell 5.1 (lens, `tip`) |
|---|---|---|---|
| full | 2293 passed, 4 skipped, exit 0 | 2293 passed, 4 skipped in 303.24s, exit 0 | 2293 passed, 4 skipped in 287.68s, exit 0 |
| skips | `[3] r_vectors_not_committed_dec77`, `[1] test_doctor_cli.py:57` | same | same |
| -m day13 | 93 passed | 93 passed, 2204 deselected | 93 passed, 2204 deselected |
| -m day12 | 196 passed, 3 skipped | 196 passed, 3 skipped | 196 passed, 3 skipped |
| -m day11 | 144 passed | 144 passed | 144 passed |
| -m day10 | 262 passed | 262 passed | 262 passed |
| ruff check / format --check | All checks passed! / 334 files already formatted | same | same |
| doctor --offline | exit 0, 17 `[ok` | exit 0, 17 | exit 0, 17 |
| fixtures --offline | exit 0; rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only (...) 7 | same, exit 0 | same, exit 0 |
| `f16_parity_native.py --check` | 894 entries, 0 failures, 386 numeric entries bit-equal | same, exit 0, in `tip` and, run exactly as the note writes it, in `wt-e13` | same, exit 0 |

The arithmetic agrees: 2269 at `941c8e4` plus the 24 new test ids (15 in `test_e13_report_rows.py`, 5 in `test_f16_parity_native.py`, 1 in `test_f17_reference_image.py`, 2 in `test_f19_egress_bytes.py`, 1 in `test_t12.py`) gives 2293. CI gives 2160 passed plus 137 skipped, which is 2297, the same as the local 2293 + 4.

**Fails pre-build** (`941c8e4` with the six new test files copied in, `PYTHONPATH` forced to that tree): five files gave **23 failed, 64 passed**, the note's figure. The first failing lines:
- F16:
  - `AssertionError: ('F5-register', 'accuracy_diff', -0.08)` / `assert []`;
  - `KeyError: 'F5-register.accuracy_diff.est'`;
  - three times `AssertionError: []` / `assert (0 == 1)`.
- F17: `assert True is False`.
- E13 rows: `assert 5 == 6`; `assert ('inside unshare -rn' not in '{"id": "F19...`; `'no file written' not in 'the HALT fi...file written'`; ten sentence parameters.
- T12: `assert 'compared by...t suite only' not in '<!DOCTYPE h...`.

I also ran `test_f17_determinism.py` there, which the note did not: **1 failed, 5 passed**, with `Extra items in the right set: 'other_files'`. Both new F19 limit tests pass at `941c8e4`, as the note says: they pin a limit, not a change.

**Nothing weakened.**
- `git diff --name-status 941c8e4 bcb1dac` shows 18 files, all `M` except the two lens notes (`A`), and no `D`.
- The diff adds no skip, xfail, `only` or `todo`. It does not touch `pyproject.toml` or `.github/`.
- Each removed `assert` has a stronger replacement:
  - `== 5` became `== 6`;
  - `"unshare -rn" in runs` became both `NS=` lines plus `echo "$NS" > namespace.txt`;
  - `STATUS_TEXT[...]` became `status_text(row)`;
  - the F19 reason line moved to the new F19 row test.
- The two renamed tests keep their bodies.
- `day13` is in `pyproject.toml:103`. CI printed `day markers declared: day1 ... day13`, then `93 passed, 2204 deselected` for `-m day13` (run 37466777729, job 112279691451).

**F16 file.** At `bcb1dac` I regenerated it from a clean tree (`tree_clean True`, win-amd64-cp314). `fixtures` was equal to the committed file; only `generated.engine_commit` differed (`bcb1dac…` against `fa4929d…`). Against `941c8e4`'s file, 9 keys were added (`F5-register.accuracy_diff.{ci_hi, ci_level, ci_lo, est, flags, method, n, not_estimable_reason, suppressed}`), 0 removed and 0 changed. `git diff --numstat` gives `45 1`; the one removed line is the old `engine_commit`. I re-derived the new interval from Newcombe's method 10 with scipy's normal quantile and Wilson bounds, without repository code. For (80, 2, 10, 8), with phi corrected by N/2, I got -0.15535638110228397 and -0.010249291949335146, against the file's -0.1553563811022839 and -0.010249291949335215. Without the N/2 correction the bounds are -0.1531 and -0.0132, so the engine's method is the corrected one.

**CI.** Run 37464523986, the note's GREEN run (head `bcb1daca…`, created 12:36:53Z, 7 of 7 jobs success). From its logs:
- `pytest + ruff`: `2160 passed, 137 skipped`, `-m day13` `93 passed`.
- `offline-namespace`: `namespace command: sudo unshare -n`, `22 passed in 1.97s`.
- `docker-smoke`: `other_files: equal e3b0c44298fc1c14` twice.
- ap4: `197 passed, 1 skipped`.

The RED run 37463363415 has head `a894fee…`, `pytest + ruff` failure and the other 6 success. My own run 37466777729 (above) shows the same figures, with `pytest + ruff` at `2160 passed, 137 skipped in 211.11s`, `22 passed in 3.08s` in the namespace, and base image `python:3.12-slim@sha256:05cda977…`. `git ls-remote origin 'refs/heads/ci/*'` printed nothing afterwards.

**`f19.py`'s cited namespace runs.** `gh run view --log --job` on 37455062159/112240530133, 37458152406/112250748567 and 37458488364/112251845081 each printed `namespace command: sudo unshare -n`, all at head `941c8e4`. The job writes `echo "$NS" > namespace.txt` and uploads `namespace.txt` in `f19-offline-namespace` (`ci.yml:159`, `:175`). The next step read it back with `NS="$(cat namespace.txt)"` and ran 22 tests.

## What I could not break

Each lens-1 blocker, tried again at `bcb1dac`:
- **FA-B1:** -0.08 is now in F5 (`F5-register.accuracy_diff.est`). A mutant removing the F5 line from `parity.BLOCKS` gives 7 failed, 10 passed.
- **FA-B2:** the lens's plant (`F1-wilson.wilson_lo` label `bootstrap`, value +3.0e-5), through `--check --out <copy>`, exits 1 with `894 entries, 1 failures` and the entry named. Mutants:
  - the label rule removed: 3 failed;
  - the class half of the rule removed: 1 failed;
  - closed tolerance 1e-6: 1 failed.
- **FA-B3 / RG-B2:** in `f19.py` and `fixtures.py`, no text says the job ran inside `unshare -rn` except as the conditional "where the runner allows it". The sentence parameters fail at `941c8e4`.
- **FA-B4 / RG-B1:** the docstring now names the three attributes and the two routes it does not see. The limit test passes in both variants.
- **FA-B5:** I moved `F1-wilson.wilson_lo` in the committed file by 1e-3 (`0.2552885…` to `0.2562885…`) and ran `proofpack fixtures --offline` with no pytest. Result: **exit 6**, F16 `not_matched`, summary `not matched 1 ... suite only (...) 6`. So the `t12.py` comment's cited run reproduces. A mutant making every `suite_only` row print the measured text gives 2 failed in `test_t12.py`.
- **FA-B6:** on two 400-row runs (exit 4, 4; `identical True`; 6 checks):
  - the T8.json plant: `(False, ['other_files'])`;
  - one digit of one `est` (`0.1691318580586025` to `…021`): `(False, ['run_json_masked'])`;
  - `started` and `duration_s` edited only: `(True, [])`;
  - `started` duplicated: `refused: started occurs 2 times; expected exactly once`.

  Two more mutants each give 1 failed: `KNOWN_FILES` matched by base name, and `other_files` hashing names only.
- **RG-B3:** the F12 row ends "no file added, removed or changed under the fixture's directory (its inputs and its PROOFPACK_HOME), and no --out". `halt_fixtures` says a file written elsewhere is not seen. Locally, all 11 HALT items are `ok`, with `files_changed 0` and `out_exists False`.

What lens 1 could not break, still holding:
- the 885 old F16 entries are unchanged;
- F19 local figures: synthetic cells 83, needles 8, small-only 7; small-cell cohort cells 97, small rows 2, small cells 14 (0 unsuppressed), needles 117, small-only 113; hits 0, socket calls 0;
- the F17 mask behaviour above;
- `egress/scan.py` is not in the diff.

## What I could not check

- The reference image locally: Docker was not used on this machine. I relied on the two CI runs' logs.
- The Pyodide half of F16: lane S's, after a pin move.
- The contents of the `f19-offline-namespace` artefact: I did not download it. That `namespace.txt` existed is shown by the next step reading it.
- Why the urllib plant counted 0 sockets inside `sudo unshare -n` (lens 1, [unverified]).

## Sentences I refused to write

- "The gate is GREEN on my push." The script printed GREEN from two runs it did not start. Only run 37466777729, watched by hand, is my push's, and it is green.
- "`other_files` shows the documents are byte-identical." No document was in either run directory.
- "The register-class test holds the file's values to the engine exactly." It holds a fresh compute to the engine exactly, and the file to the fresh compute under tolerance (B1).

## Cleanup

Worktrees `tip` and `pre` removed with `git worktree remove --force`. No node_modules junction existed. Nothing was committed. The only push was `ci_gate.sh`'s throwaway `ci/bcb1dac`, which it deleted.
