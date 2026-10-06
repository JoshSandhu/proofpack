# E13 lens 1 - fresh attack - on `941c8e4` (Tuesday 6 October 2026)

**Verdict: FAIL. Six blockers.**

1. One F16 statistic is missing from the committed native file.
2. A hand-edited number in that file passes every test.
3. The shipped F19 report text says the CI namespace was `unshare -rn`. Both CI runs used `sudo unshare -n`.
4. A false sentence says what the F19 socket guard counts.
5. The T12 and printed status "compared by the test suite only" is false for rows this command now compares itself.
6. A false sentence says the F17 comparison "fails on any other difference".

Blockers 3-6 are sentence violations. Blocker 1 is also one.

Scope: a cold lens on lane E build day 13 (`git diff 5154468 941c8e4`) and the builder's note `scratchpad/notes/E13_build.md`. I worked in detached worktrees at `941c8e4` (`tip`, plus `mut` for mutants) and at `5154468` (`base`), all under `scratchpad/lens-E13-r1-fresh-attack/`, all removed at the end. Before trusting any number, I proved every Python process imported from its own worktree's `src`. Nothing was committed. The only ref I pushed was through `workflows/ci_gate.sh`.

## Measured figures (this session, Git Bash, Windows, cp314)

The environment was `PROOFPACK_REQUIRE_DOCX=1 PYTHONIOENCODING=utf-8 PROOFPACK_TR39_FULL=...confusables-18.0.0.txt`, with `PROOFPACK_ASAH_VECTORS` unset.

| | `5154468` | `941c8e4` |
|---|---|---|
| full suite | 2199 passed, 4 skipped, exit 0 | 2269 passed, 4 skipped, exit 0 |
| `-m day13` | - | 70 passed |
| `-m day12` | 196 passed, 3 skipped | 196 passed, 3 skipped |
| `-m day11` | 144 passed | 144 passed |
| `-m day10` | 262 passed | 262 passed |
| `ruff check .` / `ruff format --check .` | - | "All checks passed!" / "332 files already formatted" |
| `proofpack fixtures --offline` | - | exit 0; rows 46: matched 35, not matched 0, no oracle 0, not built 4, suite only 7 |
| `scripts/f16_parity_native.py --check` | - | "885 entries, 0 failures, 382 numeric entries bit-equal" |

The difference between the two trees is exactly the 70 day13 tests, and no earlier marker count moved. These figures agree with the note's.

**CI gate.** I ran `bash workflows/ci_gate.sh <tip> 941c8e4`, and it printed `gate: run 37455062159 ci: success` / `GREEN` within seconds. That is the builder's run, not one my push started (non-blocking 5).

My push did start run **37458152406**. I watched it myself (`gh run watch --exit-status`, exit 0): **7 of 7 jobs succeeded**.
- `pytest + ruff`: "2136 passed, 137 skipped", and day13 "70 passed".
- `offline-namespace`: "namespace command: sudo unshare -n" and "20 passed in 1.78s".
- `docker-smoke`: "compare-dirs ... run platforms ['linux-x86_64-cp312', 'linux-x86_64-cp312']; both on the reference platform: yes; identical under the mask ... yes", on base image `python:3.12-slim@sha256:05cda977…`.

`git ls-remote origin 'refs/heads/ci/*'` printed nothing afterwards.

## Blockers

### B1 - F16: F5's accuracy difference is missing from the parity file, and four sentences say every register value is in it (sentence violation)

**Evidence.**
- `parity._register_entries` skips every register row whose `tolerance_class` is `"register"`. Nine rows with engine functions are skipped: F1/F1b/F1c/F1d/F2/F3/F4/F5/F6/F8 `-register`.
- For eight of them every value appears in another row. **`F5-register.accuracy_diff` does not.** That is `difference_paired(80, 2, 10, 8).est` = -0.08, D1 section 3.2's F5 headline figure.
- I searched all 885 entries of `fixtures/f16_parity_native.json`:
  - for -0.08 within 1e-9;
  - for its Newcombe paired bounds -0.1554 and -0.0102 within 5e-5.

  The search found nothing: `[]`.
- The E10 `compare_versions` block holds the accuracy difference of the F3 pair (est 0.1, n 10), not of F5's table.

**False sentences** (counter-example: the F5-register row above):
- `src/proofpack/parity.py` docstring line 8: "for every value the fixture register computes (each register row with an engine function, F1-F11 and F14 ...)".
- `src/proofpack/fixtures.py:2201`, the F16 row description rendered in T12: "every register value F1-F11 and F14".
- The test name `tests/test_f16_parity_native.py::test_every_register_row_with_an_engine_is_in_the_file_except_f13_and_f13b`. Its body skips `tolerance_class == "register"`.
- The note: "Every value of every register row with an engine function: F1-F11 (there is no F7 row) and F14".

**Repro:** `python -c "import json;f=json.load(open('fixtures/f16_parity_native.json'));print([k for v in f['fixtures'].values() for k,e in v.items() if isinstance(e.get('value'),float) and abs(e['value']+0.08)<1e-9])"` prints `[]`.

### B2 - F16: a hand-edited number with a hand-widened `tol` label passes every test and `--check`

**Cause.** `parity.compare_entry` reads `tol` from the first argument, which is the committed file. It never compares that label with the fresh run's label.

**The plant** (in `mut`):
- `F1-wilson.wilson_lo`: `"tol": "closed"` → `"bootstrap"`.
- Value `0.2552885198782742` → `0.2553185198782742`. That is +3.0e-5, 30,000 times the closed tolerance.

**Results**
- `pytest tests/test_f16_parity_native.py tests/test_e13_report_rows.py`: **22 passed**.
- `python scripts/f16_parity_native.py --check`: "885 entries, 0 failures, 381 numeric entries bit-equal".

The site's Pyodide test is to read the same file's labels, so the widened label would loosen it too.

**Repro:** apply the two-field edit above, then run the two commands.

### B3 - F19: shipped report text says the CI namespace is `unshare -rn`; both runs used `sudo unshare -n` (sentence violation)

**Evidence.** The job falls back when unprivileged user namespaces are refused. Run 37455062159 logged "unprivileged user namespaces are unavailable on this runner; using sudo unshare -n" and "namespace command: sudo unshare -n". Run 37458152406 logged "namespace command: sudo unshare -n". The builder refused "F19 runs inside unshare -rn in CI" in the note, but the report row ships it.

**False sentences:**
- `fixtures.py:1857`, the F19 reason, also in the T12 golden line 278 and in `fixtures_report.json`: "The --offline run inside unshare -rn is Linux only: the CI job offline-namespace".
- `fixtures.py:1896`, artefact `where`: "proofpack run --offline inside unshare -rn, then the F19 test file inside the same namespace".
- `f19.py:40` docstring.
- `tests/test_f19_egress_bytes.py:7`: "runs this file inside unshare -rn".
- `tests/test_f19_egress_bytes.py:175`: "failed inside unshare -rn with socket_calls 0". The RED run was in `sudo unshare -n`.

`tests/test_e13_report_rows.py:70` (`assert "unshare -rn" in ...["reason"]`) pins the false wording.

**Repro:** `gh run view -R JoshSandhu/proofpack 37458152406 --log --job 112250748567 | grep "namespace command:"`.

### B4 - F19: "a transport that bypassed the recorder would be counted, not sent" is false (sentence violation)

**The guard.** It replaces three attributes of the `socket` module: `socket`, `getaddrinfo` and `create_connection`.

**Counter-example (constructed, `tip`).** A `telemetry.send` that calls `_socket.socket()` and then sends through the given transport. Result: 1 socket created, `socket_calls 0`, `telemetry_sends 1`, `f19.check(r) == []`.

A second counter-example is the builder's own RED run 37453449607: the real urllib path inside the namespace counted 0. A client holding its own reference to `create_connection` taken before the guard was counted (`socket_calls 1`), so that path is covered.

**False sentences:**
- `f19.py:15-17` "so a transport that bypassed the recorder would be counted, not sent".
- `fixtures.py:1853` "with sockets refused" (in the F19 reason and on T12).
- `fixtures.py:1868` "(sockets refused)".

The accurate sentence names the three attributes the guard replaces.

**Repro:** `scratchpad/lens-E13-r1-fresh-attack/probe/p6.py` (CE1). I will describe it here because the worktree is removed: monkeypatch `telemetry.send` to `import _socket; _socket.socket().close(); return real_send(...)`, then `f19.run_cohort("ce1", f19.small_cell_cohort(), tmp)`.

### B5 - "compared by the test suite only" is printed for F12, F16, F17 and F19, which this command now compares itself (sentence violation)

**Evidence.** `render/t12.py:54` maps `suite_only` to "compared by the test suite only". `fixtures.py:2662` prints "compared by the test suite only 7". E13 puts four rows the command measures itself under that status.

**Counter-example.** I raised `F1-wilson.wilson_lo` in the committed file by 1e-3 and ran `python -m proofpack.cli fixtures --offline` (no pytest): **exit 6**, F16 `not_matched`, "884 of 885 agree". The command made the comparison itself.

The builder carried this item knowingly ("Changing the text is a T12 and site change"). The sentence is still on the T12 golden and in the printed summary at `941c8e4`.

**Repro:** perturb one closed entry in `fixtures/f16_parity_native.json`, then run `proofpack fixtures --offline`.

### B6 - F17: "masks exactly those three values ... and nothing else, and fails on any other difference" is false (sentence violation)

**Evidence.** `f17.compare` hashes the contents of `run.json`, `pseudonyms.json` and `ingest_report.json`, plus the list of file names. The content of any other file in the run directory is not read.

**Counter-example.** I copied the two `same_platform_repeat` runs and added `T8.json` with different content to each (`{"run_id": "a"}` and `{"run_id": "b", "x": 1}`). `f17.compare(...)["identical"]` is **True**. A licensed run writes HTML and DOCX documents that this comparison would not read.

**False sentence:** `src/proofpack/f17.py:8`.

**Repro:** as stated.

## Non-blocking (record and carry)

1. **Surviving mutants** (my harness, `mut` worktree, 25 + 4 mutants, each restored by checkout):
   - **F12:** `ok` ignores the no-document line (M1); `ok` ignores an `--out` that exists but holds no file (M2).
   - **F19:**
     - `_is_small` without `min_n` (M5), and without `min_nonevents` (M6). No cohort site is small by n alone or by non-events alone.
     - Structural check skips `two_by_two` (M7) and calibration bins (M8).
     - The free-text needles are removed (M9).
     - `check` ignores `sites_pseudonymised` (M12).
     - The fairness-gap rule is removed (M14). No cohort has a fairness block.
   - **F17:** `pseudonyms.json` is not compared (M16); `ingest_report.json` is not compared (M17). `hashed_set` asserts only the names.
   - **F16:** `parity.compare` ignores an extra fixture in the fresh run (M21).

   Killed: M4, M10, M13, M15, M19, M20, M22-M25, N1 (snapshot emptied). M3 as first written was equivalent (`{} or {...}`), and N1 is its corrected form. The engine-side mutants N2/N3 (the events or non-events rule removed from `egress/suppress.py`) are killed by `test_f19_both_cohorts_pass_every_check` ("cells/66: unsuppressed with n 36, k 33").
2. **F19 does not scan the URL or the headers.** CE2 sent with `url + "?site=St%20Mary%27s"`: `hits []`, `check []`. Today the URL is the constant `TELEMETRY_URL`, so there is no leak. The brief's "every egress byte" is wider than "either payload's bytes", and the shipped text says the latter.
3. **Small-cell counts can be recovered by subtraction from the aggregates bytes.** My cohort had one small site, St Mary's (7 rows, 2 events), plus Guy's and Royal Free. From the aggregates bytes alone, overall minus the shown sites gives St Mary's sensitivity n 2 / k 1 and specificity n 5 / k 5. `f19.check` returns `[]`. The aggregates document is not sent at launch, and D1 section 6 specifies primary suppression only. This is for Josh before any aggregates egress.
4. **F19 needles are the site levels of the engine's own `run.json`**, not the input CSV's values. A site name the engine dropped or rewrote would not be searched.
5. **`ci_gate.sh` re-run on a sha that already has a run on `ci/<short>` reports the old run.** At 12:42:09 it printed "run 37455062159 ci: success / GREEN" while its own push's run 37458152406 was `in_progress`. This is outside the E13 diff (`workflows/`). A re-gate can print GREEN from a stale run.
6. **`scripts/mutation_sweep.py --marker ap3 --only ap3_f17_mask_drops_duration_s,ap3_f17_file_names_not_compared` refuses** with "baseline (no mutant) does not pass -m ap3". The cause is the T12 golden's F13 text ("HEAD was not read") in the sweep's git-less copy. It is the same at `5154468`, so it was not introduced here. So the two retargeted F17 sweep mutants have not been executed by the sweep. In such a copy, `-m day13` gives 2 failed: `test_the_report_carries_the_engine_commit_of_this_checkout` and `test_the_committed_file_names_the_clean_engine_commit_that_produced_it`, which both need git. No day13 sweep mutants are declared.
7. **The note says "Reasons carry no platform tag".** The F16 reason contains "on win-amd64-cp314", which is the committed file's platform. It is a note-only sentence violation; correct it before the note becomes the handoff.
8. **F12's "changed no file" is measured only under the fixture's directory.** That is the docstring's own scope, but the reason text does not say so.
9. **The F12 H01 fixture flips `score.orientation`.** D1's input is swapped labels (AUROC 0.20). Both halt on H01 for the right reason.
10. **D1 F14's `diff_vs_complement` case and the F2-against-(85, 15, 25, 175) case are not in the `F14-newcombe` register row**, so they are not in F16 either. This register gap predates E13.

## What I could not break

**F16 values.** I regenerated the file at `941c8e4` from a clean tree. Of 885 entries, 0 differ; only the `generated` block differs (commit `941c8e4…` against `f5586f0…`).

I also re-derived 54 values with scipy, statsmodels and numpy from the published formulae, without repository code. All agree within their tolerance; the largest deviation is 7.2e-10.
- Wilson and Clopper-Pearson for F1, F1b, F1c and F1d.
- F2: MCC, PPV and NPV at 0.05, and the Wilson bounds.
- F3 DeLong, by placements: AUCs, SEs, paired variance 0.0072, z, p, the Wald interval and the logit interval.
- F4: Brier, the reference Brier, IPA and O/E; the GLM slope, intercept, calibration-in-the-large and their SEs.
- F6: χ² and p.
- F8: the three half-widths.
- F10 and F11.
- F14: Newcombe method 10 on all three cases.

I also re-derived the F5 McNemar figures: exact p 158/4096 = 0.0386, corrected χ² 49/12 = 4.0833.

**F12.** All 11 fixtures print their own code with the right message at `941c8e4`. H07 reads "header-set hash differs from mapping.json in non-interactive mode", and H12 reads "paired compare with unmatched row_ids".

I confirmed the builder's measured sentence at `5154468`. The old `test_halt_gates` procedure printed "HALT H07: run proofpack map first" for H01-H06 and H11, and its own code for H08 and H09.

H10 is the only HALT code with no fixture, and it is flag-only.

**F19 suppression.**
- A site small by events only (Harefield 15/3) and one small by non-events only (Royal Brompton 12/10/2): 14 small cells, 0 unsuppressed, `check []`.
- The spy test shows that suppression happens before `whitelist.project`.
- The telemetry body holds no statistic: 340 bytes, with keys duration_s, engine_version, halt_code, licence_id, manifest_sha256, platform, row_count_bucket, run_id, schema and timestamp.

**F17 mask.** One-occurrence enforcement, the duplicate refusal and the platform requirement all hold. The masked hashes in the fresh CI run equal the builder's (`d57c6d40…`, `a8729e41…`, `ca4e145e…`, `d306a3aa…`, `7fe1d049…`).

**CI.** The gate run 37458152406 (my push) is green on all 7 jobs.

## What I could not check

- **The reference image locally.** Docker is not running on this machine, and I did not start it. I relied on the CI logs above.
- **The Pyodide half of F16.** It is lane S's, after a pin move.
- **`unshare -rn` on any runner.** Both CI runs refused unprivileged user namespaces.
- **Why the urllib path reached no patched function inside `sudo unshare -n`.** I did not diagnose it.
- **A PowerShell 5.1 run of the suite.** I used Git Bash only.
