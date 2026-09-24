# Lens 2 (regression and record): build day 9, lane A (A-P3) repair 1 at `a09a0ef`, 24 September 2026

**Verdict: PASS.** No blocker. The three lens-1 blockers (FA-B1, RG-B1, RG-B2) are closed on the inputs I fed. Every suite figure, command and measured number in the repair note (`workflows/notes-day9/AP3_repair1.md`) re-measured in Git Bash, and every one except the mutation sweep also in PowerShell 5.1. One sentence violation is open (RG2-S1, below, graded non-blocking). Under the repair rule it is fixed before the round counts as closed. Four non-blocking findings are recorded.

- **RG2-S1 (sentence violation, not a blocker).** The comment on `IMAGE_CALL` in `tests/test_workflows.py` says the pattern matches "an image ... named by a word containing `proofpack` ... followed by an engine subcommand". The repair note's RG-B2 row says the same ("an image word containing proofpack ... followed by a subcommand"). A digest-pinned image is such a word, and the pattern does not match it: `docker run --rm ghcr.io/globalphoenix/proofpack@sha256:0123 run --input a` planted in `release.yml` without `--offline` left `tests/test_workflows.py tests/test_ap3_repair1.py tests/test_offline.py` at `53 passed`.

All figures below are mine. They were measured on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1). None comes from the reference platform (`python:3.12-slim` linux/amd64). Nothing was built into an image, pulled, pushed or tagged, and nothing was installed from an index. Worktrees were under `scratchpad/lens-AP3-r2-regression/`:

- `wt-a09` at `a09a0ef`;
- `wt-1a9` at `1a967d8`, with the repaired test files copied in;
- `wt-mut` at `a09a0ef`, for mutations (each reverted; `git status` clean after each);
- `wt-merge` at `9806d3d` (main) with `git merge --no-commit --no-ff a09a0ef`, for a trial merge. Nothing was committed.

`PYTHONPATH` was forced in each. `python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` in both shells. All four worktrees are removed.

## Blockers

None.

## Sentence violation (non-blocking, to be fixed)

### RG2-S1: the `IMAGE_CALL` comment, and the note's RG-B2 row, describe a class of inputs the pattern does not match

`tests/test_workflows.py` at `a09a0ef`, verbatim:

```
#: An image or program named by a word containing ``proofpack`` (``proofpack:latest``,
#: ``ghcr.io/x/proofpack:ci``) or by a shell variable (``$PP``, ``"${IMAGE}:${TAG}"``),
#: followed by an engine subcommand.
```

The repair note, RG-B2 row: "adds `IMAGE_CALL` (an image word containing `proofpack`, or a shell variable, followed by a subcommand)". The commit message of `58c1b2e` says the test "matches images, shell variables and inline main([...])".

The character class after the image word is `[\w.:/${}-]`, with no `@`. I added each line below as one `run:` step to the parsed `release.yml` and called the repaired `offline_violations`:

| Command (no `--offline`) | Result |
|---|---|
| `docker run --rm ghcr.io/globalphoenix/proofpack@sha256:abc run --input a` | MISSED |
| `docker run --rm proofpack:latest run --input a` (the comment's own form) | caught |

Planted in the file itself (a `planted` step after the `fixtures` step, `yaml.safe_load` parses it): `tests/test_workflows.py tests/test_ap3_repair1.py tests/test_offline.py` gave `53 passed in 3.09s`. The Dockerfile's own comment plans a digest pin for the base image, so a digest reference is a form the workflows may take.

- Repro: `PYTHONPATH=<wt>/src python -c` importing `tests/test_workflows.py`, append `{"run": "docker run --rm ghcr.io/globalphoenix/proofpack@sha256:abc run --input a"}` to `jobs.build.steps`, call `offline_violations`: `[]`.
- Fix: add `@` to the class, with the digest line in `LENS_COUNTER_EXAMPLES`; or narrow the comment and the note to the forms the tests feed.

The release.yml header is not affected. It says the test "asserts --offline on each command its ENGINE_CALL, IMAGE_CALL and MAIN_CALL patterns match: six here", which is what it inspects.

## Non-blocking (record and carry)

**RG2-N1. Three mutants of the repair survive `-m ap3` and the full suite; the code is correct on each input unmutated.** Each mutant was planted in `wt-mut` and reverted. None makes a not-matched row read as matched or exit 0: M5 records the wrong commit, M12 exits 5 with no report on a non-dict engine result, M14 changes only the reason text. So none reopens a blocker class (FA-B1 was a not-matched row reported as matched).

| Mutant in `src/proofpack/fixtures.py` | `-m ap3` | Full suite | Unmutated, on the input that tells them apart |
|---|---|---|---|
| M5: `_is_proofpack_checkout` returns `True` after the path check (the `pyproject.toml` name test dropped) | `91 passed` | `1497 passed, 1 skipped, 1 xfailed` | `<X>/src/proofpack/fixtures.py` with `<X>/pyproject.toml` naming `customer` and `<X>/.git`: `(None, NOT_THE_PROOFPACK_CHECKOUT)`, 0 git calls |
| M12: `if not isinstance(got, dict):` made `if False:` | `91 passed` | `1497 passed, 1 skipped, 1 xfailed` | a row whose engine returns `[1.0]`: `not_matched`, `engine_error: returned list` |
| M14: the `oracle value ...` reason dropped (`if oracle_value is None:` made `if False:`) | `91 passed` | `1497 passed, 1 skipped, 1 xfailed` | a row whose oracle value is `None`: `not_matched`, `oracle value missing: a`, `max_abs_deviation` `None` |

M5 is the FA-R1 class. Both parameters of `test_git_sha_is_null_for_a_wheel_vendored_inside_another_git_repository` put the package at `vendor/proofpack`, so the path check decides them and the name check never does. `fixtures.py`'s module docstring cites that test for the whole "otherwise it is null" clause. The note's FA-B1 row says "A non-dict engine result gives `engine_error: returned <type>`"; no test feeds one, and the note does not record a run. I ran it (above) and the sentence holds. Next: a `src/proofpack` layout under a `customer` pyproject as a third parameter; a non-dict and a null-oracle row beside `test_a_planted_row_with_one_value_missing_and_one_nan_is_not_matched`.

**RG2-N2. The workflow test misses engine runs whose form its patterns do not name.** None of these contradicts a sentence (the header names the three patterns), but each runs the engine without `--offline` and is reported as no violation:

| Command | Result |
|---|---|
| `proofpack --quiet run --input a --criteria b` (a common option before the subcommand; D1 section 7 names the `proofpack --offline doctor` order) | MISSED |
| `docker run --rm -e X=1 proofpack:ci --quiet run --input a` | MISSED |
| `proofpack run --input a --criteria b  # --offline` (a trailing comment) | MISSED |
| `proofpack run --input a --out ./--offline-dir` (substring) | MISSED |
| `python -c "import subprocess; subprocess.run(['proofpack','run','--input','a'])"` | MISSED |
| `python -c "from proofpack.cli import main; main(argv=['run','--input','a'])"` | MISSED |
| `$(which proofpack) run --input a` | MISSED |
| `python -m proofpack run`, `uv run proofpack run`, `exec proofpack run`, a tab separator, `timeout 60 proofpack run ... & wait`, `(proofpack run ...)` | caught (6) |

`grep` of the committed `ci.yml` and `release.yml` for `--quiet`, `# --offline`, `--offline-`, `subprocess`, `main(argv`, `$(which` and `@sha256` on a `proofpack` line: no hit.

**RG2-N3. A truncated oracle file still exits 5 with no report.** `fixtures/oracles_v1.json` replaced by `{"captured": ` in `wt-a09`: `internal error: JSONDecodeError: Expecting value: line 2 column 1 (char 14)`, exit 5, no `fixtures_report.json`. `load_oracles` catches `FileNotFoundError` only. The note's decision 1 treats an absent oracle file as an install defect reported as `not_matched`, exit 6; a truncated one is the same defect and takes the old path. No sentence claims otherwise: the note refuses "never raises" and "always written". The exit is non-zero and nothing reads as matched.

**RG2-N4. Record items in the repair note.**
- *Merge notes.* "Shared files. These are touched on both sides since `e17a510`: `cli.py`, `scripts/mutation_sweep.py`, `tests/test_offline.py`". Measured: `git diff --name-only e17a510 main` (main `9806d3d`) touches `scripts/mutation_sweep.py` and not `cli.py` or `tests/test_offline.py`. The note's next bullet says the same ("The only file changed on both sides since `e17a510` is `scripts/mutation_sweep.py`"), so the first bullet contradicts it. The list of files is complete: `comm -12` of the two name lists gives `scripts/mutation_sweep.py` only.
- *L13.* The FA-R1 row says the dirty-state test "also kills the lens's L13 dirty-state mutant", and the carried FA-R9 row says "I did not plant L13 itself". I planted it (`state = "tracked files unmodified"`): `-m ap3` gave `1 failed, 90 passed`, the failing case `[ M src/proofpack/fixtures.py\n-0-tracked files modified]`. The sentence holds by my run, not by the note's.
- *Fails pre-fix, the dirty-state test.* The note gives no first failing line for `test_git_sha_in_a_proofpack_checkout_records_the_tracked_file_state`. At `1a967d8` its three cases fail on `AttributeError: module 'proofpack.fixtures' has no attribute 'GIT_SHA_SOURCE'` (line 216), a missing name, not the behaviour. The L13 plant above shows it pins the behaviour at `a09a0ef`.
- *Commands.* The note's re-run table is Git Bash only and says nothing was run in PowerShell. I ran each in both (below).

## Regression checks (what I ran, and what I got)

### Suite, markers, lint at `a09a0ef`

| Command | Note (Git Bash) | Git Bash (mine) | PowerShell 5.1 (mine) |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1497 passed, 1 skipped, 1 xfailed in 113.96s` | `1496 passed, 2 skipped, 1 xfailed in 134.27s`; the extra skip is `tests/test_e8_repair4.py:405` (the full `confusables.txt` is looked for beside the tree, and a scratch worktree has none); with `PROOFPACK_TR39_FULL` set, that test gives `1 passed` | `1497 passed, 1 skipped, 1 xfailed in 122.37s` (with `PROOFPACK_TR39_FULL` set) |
| `-m ap3` | `91 passed` | `91 passed, 1408 deselected` | `91 passed, 1408 deselected` |
| `-m ap2` | `89 passed` | `89 passed, 1410 deselected` | `89 passed, 1410 deselected` |
| `-m day8` | `469 passed` | `468 passed, 1 skipped` (the same TR39 skip) | `468 passed, 1 skipped` (same) |
| `-m day9` | `241 passed` | `241 passed, 1258 deselected` | `241 passed, 1258 deselected` |
| `-m "ap3 and not day9"` | n/a | `no tests collected (1499 deselected)` | n/a |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `208 files already formatted` | same | same |

The one skip left in both shells is `tests/test_doctor_cli.py:57` (write access cannot be revoked for this user). My first PowerShell full run gave `1 failed` (`test_fixtures_offline_opens_no_socket`, `oracle_file_missing: oracles_v1.json`): I had moved `oracles_v1.json` out of the same worktree for RG2-N3 during that run. The clean re-run is the figure above.

`ap3` is declared in `pyproject.toml`. `ci.yml` has no literal `ap3`: its marker step reads `dayN` names from `pyproject.toml` and runs `-m day9`, and no `ap3` test lacks `day9` (row above). The `pytest (all markers)` step runs the whole suite.

### Fails pre-build (`1a967d8` with the repaired test files copied in)

`tests/test_ap3_repair1.py` and `tests/test_workflows.py` copied, the 34 new tests run: `25 failed, 9 passed`.

- Failed (25): every test in `test_ap3_repair1.py` except `test_the_sentences_the_lenses_found_false_are_gone[tests/test_workflows.py]`, plus `test_the_release_header_names_what_the_test_inspects_and_no_more`. The first failing lines are the note's: `assert 1.1102230246251565e-16 is None` (line 78); `assert (5 == 6)` at lines 102, 120, 137 after `internal error: ValueError: Out of range float values are not JSON compliant: nan`, `KeyError: 'F1-wilson'` and `FileNotFoundError: f4_expected.json`; `assert 0.0 is None` (158); `assert ('aaaa...' is None)` (196); `assert 'exit 2' not in 'warning: th...code sets it'` (225); `AssertionError: H10` (248); `'Condition held' not in` (255); `'bootstrap i...ished tables' not in` (272); and nine sentence cases, for example `('src/proofpack/fixtures.py', 'Never raises')` and `('Dockerfile', 'No key material enters')`.
- Passed (9): `test_the_sentences_the_lenses_found_false_are_gone[tests/test_workflows.py]` (the repaired file was the one copied in), the seven `test_the_lens_counter_examples_are_caught` cases and `test_a_docker_uses_step_with_engine_args_is_caught`. These eight test the detector defined in the test file itself, so a copied file carries the repair with it. I appended `1a967d8`'s `ENGINE_CALL`, `shell_lines` and `offline_violations` to a copy of the repaired file (so the old detector is the one called): the eight gave `8 failed`. They pin the detector.

The FA-R11 figures re-measured: `Dockerfile` and `.github/dependabot.yml` deleted in `wt-1a9`; `1a967d8`'s `test_dockerfile.py` and `test_workflows.py` gave `10 passed, 12 skipped`; the repaired files gave `2 failed, 18 passed, 11 errors`. Both equal the note.

### Nothing weakened

- `git diff --name-status 1a967d8 a09a0ef -- tests/`: `M` for `tests/fixtures/golden/T12.html`, `test_dockerfile.py`, `test_fixtures_cmd.py`, `test_offline.py`, `test_workflows.py`; `A` for `test_ap3_repair1.py`. No `D`.
- The diff adds no `skip`, `xfail`, `importorskip` or `.only` call. The four added lines that contain "skip" remove skips (two comments, one assertion message and one string in the `REFUSED` table). No marker line is removed.
- `git diff --name-status 1a967d8 a09a0ef -- src/proofpack/stats/`: empty.

### Commands and figures in the note, both shells

| Command (in my `a09a0ef` worktree) | Git Bash | PowerShell 5.1 |
|---|---|---|
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.`, exit 0 | same, exit 0 |
| `python -m proofpack.cli fixtures --offline --out DIR --r-captures` | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0, 1.13 s | same line, exit 0, 1.17 s |
| the report | `git_sha` `a09a0ef05d7a…`, source `git rev-parse HEAD in the proofpack source checkout the package was imported from (src/proofpack; pyproject.toml names proofpack); tracked files unmodified`; largest deviation per class: closed form 1.78e-15 (F2-exact), iterative 2.19e-9 (F4-irls), register 5.77e-5 (F3-register), reported rounding 3.21e-5 (F14-newcombe) | the two reports are equal once `generated` and `duration_s` are removed |
| `python scripts/build_t12.py --report DIR/fixtures_report.json --out T` | 49,479 bytes; `(0 flagged by doctor)`; reference-platform row `no`, `no`, `windows-amd64-cp314 (reference is linux-x86_64-cp312; tolerances per T7 apply)`; 0 hits for "Condition held" | 49,479 bytes, `(0 flagged by doctor)` |
| `python scripts/f17_determinism.py --out DIR --n 5000`, twice | four `equal` (`0c4b77b7789a0c64`, `a839493ed99f3925`, `ca4e145eb123633e`, `d306a3aa6600d4a4`), exit codes [4, 4], identical under the mask: yes, exit 0; 2.84 s and 2.85 s | the same four prefixes, exit 0, 2.89 s |
| `python scripts/sbom.py --out X`, twice | `62 components: 13 required, 1 optional, 48 excluded`; `cmp` identical | the same line; hashes equal; Git Bash and PowerShell files byte-identical |
| `python scripts/capture_fixture_oracles.py --check` | exit 0 | exit 0 |
| `python scripts/mutation_sweep.py --marker ap3` | `15 planted, 15 killed, 0 survived; 154 s` (the trial-merge suite ran at the same time) | not run |
| `git merge-tree --write-tree main a09a0ef` | exit 0 against main `9806d3d` | n/a |

The T12 size differs from the note's 49,367 by 112 bytes. T12 prints the package path, and my worktree path is 112 characters longer than `C:\Users\joshs\GPS\ProofPack\wt-ap3`.

F17's unmasked `egress_manifest_sha256_unmasked` pair differs between my Git Bash and PowerShell runs (it carries `run_id`); `f17_result.json` records `raw_bytes_equal: false`. The masked hashes are identical across both shells and all three runs. This is a same-platform repeat on `win-amd64-cp314`, not the reference platform.

### Package-specific checks

- **`fixtures_report.json` against the committed schema.** `jsonschema.Draft202012Validator(schema).validate(report)` passes on both shells' reports. The report names 25 fixtures: F1, F1b, F1c, F1d, F2 to F21 and F13b. `grep -ohE "\bF[0-9]{1,2}[b-d]?\b"` over D1 and R3 gives the same 25. The report text contains none of "passed validation", "validated", "certified", "compliant".
- **Planted mismatches through the CLI**, each in `wt-a09`'s `fixtures/oracles_v1.json`, reverted after each:

| Plant on `captured.F1-wilson.values.wilson_lo` | Exit | Report | Row |
|---|---|---|---|
| +2e-9 | 6 | written | `outside tolerance: wilson_lo` |
| +5e-10 | 0 | written | matched |
| NaN | 6 | written | `oracle value not finite (nan): wilson_lo` |
| `null` | 6 | written | `oracle value missing: wilson_lo` |
| `"abc"` | 6 | written | `oracle value not a number (str): wilson_lo` |
| `values` emptied | 6 | written | `no value compared` |
| whole file absent | 6 | written | `matched 4, not matched 26` |
| `f4_expected.json` replaced by `[1,2]` | 6 | written | the three F4 rows `oracle_error: TypeError` |
| file truncated (RG2-N3) | 5 | not written | `JSONDecodeError` |

- **FA-R1 end to end.** `python -m uv build --wheel --offline` in `wt-a09`, installed with `pip install --no-deps --no-index --target X/vendor` into a fresh `git init X` whose `pyproject.toml` names `customer`. With `PYTHONNOUSERSITE=1` and `PYTHONPATH=X/vendor;<user site>`, `proofpack.__file__` was `...\X\vendor\proofpack\__init__.py`. `fixtures --offline`: `rows 43: matched 29, not matched 0, no oracle recorded 3, not built 6, compared by the test suite only 5`, exit 0, `git_sha` `None`, source `not a proofpack source checkout (...); the enclosing git repository is not read`. The same result with the working directory inside `X`. (`python -m pip wheel . --no-deps --no-build-isolation` failed here: `Cannot import 'hatchling.build'`; hatchling is not installed, and I installed nothing.)
- **T12 golden.** `PROOFPACK_REGEN_GOLDEN=1 python -m pytest tests/test_t12.py -k golden`, then `cmp` with the committed blob: byte-identical (the file is LF in index and working copy).
- **T12 wording.** The rendered page carries "CSA-structured", "This record supports, does not replace, the manufacturer's own validation", "draft guidance (January 2025), not for implementation" and "hash identity is claimed on the reference platform only (D1 section 9)". Its `[unverified ...]` spans are printed. It has no "compliant", "certified", "validated" or "approved"; "endorsed" appears only in the footer's "no regulator has endorsed this tool". The W16 row reads "flag only: one line printed after run.json is written, not in the document; the exit code is the run's own (exit 0 with the W16 line in tests/test_telemetry.py::test_a_302_...)". That test asserts `rc == EXIT_OK` and the one `[W16]` line. The W14 row keeps the exit-2 action, and `tests/test_run_cli.py::test_the_ledger_warning_w14_is_exit_2_and_in_the_document` asserts `EXIT_WARNINGS`. H10's row reads "not raised in this version: gates.gate_h10 emits W10"; `gates.py` line 203 is `"W10"` in `gate_h10`. Every other code in the table is quoted at a `HaltError(...)` or `Finding(...)` call site outside `errors.py` and `render/` (listed by file and line).
- **Workflows.** `yaml.safe_load` parses `ci.yml`, `release.yml` and `dependabot.yml`. `--offline` removed from `release.yml`'s `uv run proofpack fixtures --offline --out release`: `10 failed, 9 passed` in `tests/test_workflows.py`: `test_every_engine_run_in_a_workflow_carries_offline[release.yml]`, `test_a_planted_line_without_offline_is_caught`, the seven `test_the_lens_counter_examples_are_caught` cases and `test_a_docker_uses_step_with_engine_args_is_caught` (the last nine each add a line to the parsed release file and assert exactly one violation, so the extra one fails them). `--offline` removed from `ci.yml`'s `proofpack:ci doctor --offline`: `2 failed` (the ci offline test and `test_ci_builds_the_image_without_pushing`).
- **Dockerfile.** `FROM --platform=linux/amd64 python:3.12`: `1 failed, 11 passed`, the failure `test_the_base_image_is_python_3_12_slim_amd64_by_digest_or_marked_unverified`.
- **SBOM against `uv.lock`.** 63 packages in the lock, 62 components; the one not in `components` is `proofpack 0.1.0.dev1`, which is `metadata.component`. Every component has a `purl`. The SBOM text contains no "signing", "seed", "private" or "secret".
- **The cited CI run.** `gh run view 35911876338`: `2026-09-23T19:49:28Z`, conclusion `success`, head `eda8a357…`, job "proofpack run inside unshare -rn (no network)" `success`. The `tests/test_offline.py` docstring's figures match.
- **Trial merge.** `wt-merge` (main `9806d3d`, `git merge --no-commit --no-ff a09a0ef`, one auto-merge in `scripts/mutation_sweep.py`), full suite with `PROOFPACK_TR39_FULL`: `1506 passed, 1 skipped, 1 xfailed in 129.49s` (Git Bash).

## Lens 1's blockers: closed on what I fed

- **FA-B1.** The sweep's `ap3_missing_engine_value_counted_within` is killed (`15 planted, 15 killed`). An engine value left out, or NaN, gives `not_matched`, exit 6 and a written report (tests at lines 78 and 102 fail at `1a967d8` and pass here).
- **RG-B1.** T12's W16 row no longer prints "exit 2" (the test, and the sweep mutant `ap3_t12_w16_given_the_exit_2_action`, killed).
- **RG-B2.** The release.yml header now names the test, its three patterns and "six here". The eight lens lines are caught by the repaired detector and missed by the old one (8 failed with the old one restored). RG2-S1 above is a gap in the new comment, not in the header.

## Cut, carried and never-run lists against what I measured

- The carried rows (FA-R6, R8, R9, R10, R12, RG-N2, N3 second half, N6, N7, N8) account for every lens-1 finding not fixed. `grep` of both lens-1 notes gives FA-B1, FA-R1 to R13, RG-B1, RG-B2 and RG-N1 to N10; RG-N10 (brief items) needs nothing.
- FA-R9's list (L1, L2, L5, L6, L8, L14 still surviving) I did not re-plant. L13 I did (RG2-N4).
- Written, never run: `ci.yml` `docker-smoke`; `release.yml` `build`, `image`, `testpypi`, `install-from-testpypi`, `github-release`, `zap-baseline`; `dependabot.yml`. These match what I measured: `git ls-remote --heads origin a-p3-release` and `git ls-remote --tags origin` return nothing, and `git tag` lists none. The orchestrator's second `offline-namespace` run (35992801938) is not in the note; I did not read it.
- Open and not in the note: RG2-S1, RG2-N1, RG2-N2, RG2-N3.

## What I could not break (what I tried)

- **The mismatch path.** +2e-9 on a 1e-9 cell: exit 6, row named. +5e-10: matched, exit 0. NaN, null, a string and an emptied `values` in the oracle: each `not_matched`, exit 6, report written.
- **The absent-file path.** `oracles_v1.json` absent, and `f4_expected.json` replaced by a list: report written, exit 6.
- **`git_sha` in a vendored wheel.** A wheel installed under `X/vendor` in a customer repository: `null`, no git call, from both working directories I tried.
- **The golden, F17 and the SBOM.** Byte-identical golden; identical masked F17 hashes across three runs and two shells; SBOM byte-identical across two runs and two shells.
- **The offline and Dockerfile checks.** `--offline` removed from one `release.yml` line and one `ci.yml` line: caught. `python:3.12` in the Dockerfile: caught.
- **The detector tests.** They fail with `1a967d8`'s detector restored (8 of 8).
- **Scope.** No change under `stats/`. No test deleted, no skip or xfail added.
- **The merge.** Trial merge with main `9806d3d`: clean, and its suite passes.

## What I could not check

- **Everything that runs only in GitHub Actions**: `docker-smoke` and the six `release.yml` jobs, Dependabot, Trivy, ZAP. Written, never run.
- **The base image digest.** No pull was allowed.
- **The CycloneDX 1.5 JSON schema.** Not fetched; the SBOM was checked structurally.
- **The reference platform.** Every figure is from `win-amd64-cp314`.
- **The sweep in PowerShell.** Not run.
- **The second CI run 35992801938.** Not read.

## Sentences refused

- "RG2-S1 is the only gap in the workflow test." RG2-N2 lists seven more forms it misses, and I tried only those.
- "The repair closes FA-B1 for every oracle defect." A truncated file still exits 5 (RG2-N3).
- "M5, M12 and M14 are harmless." The code is right on the one input I fed each; I did not feed more.
