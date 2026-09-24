# Lens 3 (regression and record): build day 9, lane A (A-P3) repair 2 at `43521dd`, 24 September 2026

**Verdict: PASS.** No blocker. Lens 2's one blocker (FA2-B1) is closed on the inputs I fed, and each lens-2 sentence violation (FA2-R2, R3, R4, R5, R6, R8, RG2-S1) is gone from the file that carried it. Every suite figure, command and measured number in the repair note (`scratchpad/notes/AP3_repair2.md`) re-measured, in Git Bash and in PowerShell 5.1 (the mutation sweep and the trial merge in Git Bash only). One new sentence violation is open (RG3-S1, below, graded non-blocking as lens 2 graded RG2-S1). Under the repair rule it is fixed before the round counts as closed. Three non-blocking findings are recorded.

- **RG3-S1 (sentence violation, not a blocker).** The new test name `tests/test_ap3_repair2.py::test_the_zap_upload_step_runs_after_a_failed_scan` states what a never-run workflow step does. The test reads one YAML key: `assert upload.get("if") == "always()"` (line 357). No scan has failed and no upload has run: `release.yml`'s `zap-baseline` job has never run (the repair note says "The new `if: always()` has not run"). This is the class lens 2 raised as FA2-R6 against the step name. Repro: `grep -n "def test_the_zap_upload_step_runs_after_a_failed_scan" tests/test_ap3_repair2.py`. A name that says what it inspects, such as `test_the_zap_upload_step_carries_if_always`, would fix it; the note's table row cites the old id and would change with it.

All figures below are mine. They were measured on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1). None comes from the reference platform (`python:3.12-slim` linux/amd64). Nothing was built into an image, pulled, pushed or tagged, and nothing was installed from an index. The wheel was built with `python -m uv build --wheel --offline` and installed with `pip --no-deps --no-index`. Worktrees were under `scratchpad/lens-AP3-r3-regression/`:

- `tip` at `43521dd`;
- `pre` at `a09a0ef`, with the repaired test files copied in;
- `probe` at `43521dd`, for planted files (each reverted; `git status` clean after each);
- `merge` at `9806d3d` (main) with `git merge --no-commit --no-ff 43521dd`, for a trial merge. Nothing was committed.

`PYTHONPATH` was forced in each. `python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` in both shells. The venv install printed `...\lens-AP3-r3-regression\v\Lib\site-packages\proofpack\__init__.py` with `PYTHONPATH` unset. All worktrees are removed.

## Blockers

None.

## Sentence violation (non-blocking, to be fixed)

RG3-S1, above.

## Non-blocking (record and carry)

**RG3-N1. An oracle file that is present but cannot be opened still exits 5 with no report.** `fixtures/oracles_v1.json` replaced by an empty directory in `probe`: `internal error: PermissionError: [Errno 13] Permission denied: '...\probe\fixtures\oracles_v1.json'`, exit 5, no `fixtures_report.json`. `load_oracles` catches `FileNotFoundError` and `ValueError` only. This is RG2-N3's class (a damaged install); the exit is non-zero and nothing reads as matched. No sentence claims otherwise: the `OracleFileUnreadable` docstring says "present and does not parse", and the note refuses "`proofpack fixtures` reports every oracle defect as not matched". The same file as invalid UTF-8 (`\xff\xfe{`) is caught: `matched 4, not matched 26`, exit 6.

**RG3-N2. `n_values_compared` counts values that were not compared.** With `captured.F1-wilson.values.wilson_lo` deleted, F1-wilson has `n_values_compared` 2 and one value compared (the test asserts `n_values == 2`; the note's wheel row gives `('F2-exact', 'not_matched', 17)` with `sensitivity` missing). T12 prints the figure under the column "Values", which is neutral. The field name dates from repair 1 (an engine value left out was counted the same way). No row reads as matched.

**RG3-N3. The workflow test's `COMMENT` pattern strips from any whitespace-led `#`, inside quotes as well.** `proofpack run --input a --criteria 'x#y' --offline` gives 0 violations (the `#` is not whitespace-led), but `proofpack run --input a --criteria "a #b" --offline` gives 1 (measured with `43521dd`'s `offline_violations` on a one-step job). The second is a false report, in the reporting direction; no committed line contains `#` inside an engine command. The comment on `COMMENT` ("A shell comment") names the case it was written for. Recorded only.

**Carried, re-read and still open** (the note's list, which I checked against lens 2's two notes): RG2-N2's remaining forms and FA2-R3's rest (the eight forms the note lists; none in the committed `ci.yml` or `release.yml`: my own count of lines the three patterns match is ci 5, release 6), RG2-N4, FA-R8, FA-R9 (L1, L2, L5, L6, L8, L14), FA-R10 / RG-N9, FA-R12, lens-1 RG-N2, RG-N3 second half, RG-N6, RG-N7, RG-N8, and lens 2's supply-chain aside (Trivy by movable tag under `packages: write`; the `docker login` token in `~/.docker/config.json`). The note omits none of lens 2's open items that I could find.

## Regression checks (what I ran, and what I got)

### Suite, markers, lint at `43521dd`

| Command | Git Bash (`tip`) | PowerShell 5.1 (`tip`) | Note |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1534 passed, 2 skipped, 1 xfailed in 128.32s`; the second skip is `test_e8_repair4.py:405` (the full `confusables.txt` is looked for beside the tree). That test with `PROOFPACK_TR39_FULL` set: `1 passed` | `1535 passed, 1 skipped, 1 xfailed in 136.12s` (with `PROOFPACK_TR39_FULL`) | `1535 passed, 1 skipped, 1 xfailed` |
| `-m ap3` | `129 passed, 1408 deselected` | `129 passed, 1408 deselected in 17.94s` | `129 passed` |
| `-m ap2` | `89 passed` | `89 passed` | `89 passed` |
| `-m day8` | `468 passed, 1 skipped` (the TR39 skip) | `469 passed` (with `PROOFPACK_TR39_FULL`) | `469 passed` |
| `-m day9` | `279 passed` | `279 passed` | `279 passed` |
| `-m "ap3 and not day9"` | `1537 deselected` (every ap3 test carries day9, which `ci.yml`'s marker loop runs) | | |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `211 files already formatted` | the same | the same |

The skip left in both shells is `tests/test_doctor_cli.py:57` (write access cannot be revoked for this user). `ap3` is declared in `pyproject.toml` (line 95). `ci.yml` names no marker by hand: it runs the whole suite, then each declared `dayN` marker read from `pyproject.toml`.

### Fails pre-build (`a09a0ef` with the repaired test files copied in)

- `tests/test_ap3_repair2.py` alone in `pre`: **`23 failed, 6 passed`**, equal to the note. The six that pass are the ones the note names: `test_git_sha_is_null_for_src_proofpack_under_a_pyproject_naming_customer`, `test_a_non_dict_engine_result_is_not_matched`, `test_a_null_or_nan_oracle_value_is_not_matched[None]` and `[nan]`, `test_a_row_with_no_value_has_no_largest_deviation`, and `test_each_tolerance_rule_lists_its_rows[reported_rounding]`. The first five pin behaviour that was already right; the sweep row below shows each corresponding mutant killed, so each pins something.
- Each failing line equals the note's quote: line 115 `assert 0 == 6` (three cases, each printing `rows 43: matched 30, not matched 0`); 141 `'matched' == 'not_matched'`; 153 `'Row' object has no attribute 'compares'`; 158 `no attribute 'NEWCOMBE_FILE'`; 206 `('matched' == 'no_oracle_recorded'` (both cases); 214 `no attribute 'source_checkout_root'`; 230 `assert (5 == 6)`; the truncated-Newcombe test `JSONDecodeError: Expecting value: line 1 column 7 (char 6)`; 268 `'engine value...nite (1.0): a' == 'engine value...ber (bool): a'`; 253 `unexpected keyword argument 'compares'`; 321 (two cases); 346 `assert (True is False)`; 357 `assert None == 'always()'`; 392, six sentence cases, each quoting the sentence the note names.
- The other five changed test files copied into `pre`: `3 failed, 77 passed` (`test_the_release_header_names_what_the_test_inspects_and_no_more`, `test_f17_two_runs_are_identical_under_the_three_key_mask`, `test_the_tolerance_rules_drop_the_three_citations_lens_1_found_false`). The new workflow and Dockerfile cases pass there because the detectors live in the test files themselves, so I fed the lens lines to each file's functions directly (below).
- **Detectors, old and new.** `a09a0ef`'s `test_workflows.offline_violations`, fed the four lens-2 lines as one extra step in `release.yml`'s `build` job, reported `0` violations each; `43521dd`'s reported `1` each. That equals the note. `a09a0ef`'s `test_dockerfile` functions, fed `ENV PROOFPACK_SIGNING_SEED=x`, `COPY --from=ghcr.io/x/y:latest /k /k`, `COPY signing.txt /tmp/` and `RUN python -m pip install cryptography` before `USER proofpack`: none caught. `43521dd`'s: the first caught by `test_no_secret_looking_env_or_arg_and_no_key_material`, the other three by `test_the_copies_and_the_run_are_the_ones_written`.

### Nothing weakened

- `git diff --name-status a09a0ef 43521dd -- tests/`: `M` T12 golden, `M test_ap3_repair1.py`, `A test_ap3_repair2.py`, `M test_dockerfile.py`, `M test_f17_determinism.py`, `M test_offline.py`, `M test_workflows.py`. No deletion.
- No `skip`, `xfail`, `importorskip` or `.only` added. One `pytest.skip` removed (`test_offline.py`, replaced by `assert workflow.exists()`). No marker line removed.
- `test_ap3_repair1.py`'s tolerance test lost two assertions on the repair-1 wording; that wording was the FA2-R4 sentence violation, and `test_each_tolerance_rule_lists_its_rows` now pins the rule text against `register()`.
- `git diff --name-status a09a0ef 43521dd -- src/proofpack/stats/ src/proofpack/gates.py src/proofpack/errors.py`: empty. `TOLERANCES` is not in the diff.

### Commands and figures in the note, both shells

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.`, exit 0 | the same, exit 0 |
| `python -m proofpack.cli fixtures --offline --out D --r-captures` | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, `r-captures: r_captures_not_captured`, exit 0; `git_sha` `43521ddd…`, source ends `tracked files unmodified` | the same line with and without `--r-captures`, exit 0 each |
| `python scripts/build_t12.py --report D/fixtures_report.json --out T` | 49,480 bytes, exit 0 | 49,480 bytes, exit 0 |
| `python scripts/f17_determinism.py --out D --n 5000` | twice: five `equal` (`0c4b77b7789a0c64`, `a839493ed99f3925`, `ca4e145eb123633e`, `d306a3aa6600d4a4`, `file_names` `7fe1d0490f327ef2`), exit codes [4, 4], `identical ... yes`, exit 0 | the same five prefixes, exit 0 |
| `python scripts/sbom.py --out X` | twice, `62 components: 13 required, 1 optional, 48 excluded`, `cmp` identical | the same line; SHA-256 `E5C13C67…F538D1`, equal to the Git Bash file's |
| `python scripts/capture_fixture_oracles.py --check` | exit 0 | exit 0 |
| `python scripts/mutation_sweep.py --marker ap3` | `25 planted, 25 killed, 0 survived; 251 s` (each of the ten new mutants killed by one test) | not run |
| `git merge-tree --write-tree main 43521dd` | exit 0 (main `9806d3d`) | |

T12's size differs from the note's 49,371 by exactly 109 bytes. The page prints doctor's write-access directory, and my tree's path is 109 characters longer than `C:\Users\joshs\GPS\ProofPack\wt-ap3` (measured with `len()`). The golden is masked and does not carry it.

### Package-specific checks

- **`fixtures_report.json` against the committed schema.** `jsonschema.validate` passes on the Git Bash report; the planted-deletion reports are validated inside the tests (`fx.validate_report`). The report names 25 fixtures: F1, F1b, F1c, F1d, F2 to F21 and F13b. `ls fixtures` gives the four oracle files (`f4_calibration.csv`, `f4_expected.json`, `newcombe_table2.json`, `oracles_v1.json`); D1 line 312 names F1–F21.
- **Planted defects through the CLI** (`probe`, each reverted):
  - `captured.F1-wilson.values.wilson_lo` and `captured.F2-exact.values.sensitivity` deleted: `matched 28, not matched 2`, `F1-wilson (oracle value missing: wilson_lo)`, `F2-exact (oracle value missing: sensitivity)`, exit 6;
  - `wilson_lo` +2e-9: `not matched 1`, `F1-wilson (outside tolerance: wilson_lo)`, exit 6; +5e-10: `matched 30`, exit 0;
  - `f4_expected.json` as `[]`: the three F4 rows `oracle_error: TypeError`, exit 6; truncated to `{"hand": `: the three F4 rows `oracle_file_unreadable: f4_expected.json (JSONDecodeError)`, exit 6.
- **The installed wheel** (80 entries; `_fixtures/` holds `f4_calibration.csv`, `f4_expected.json`, `oracles_v1.json`; no `newcombe` entry). Intact: `matched 29, not matched 0, no oracle recorded 3`, exit 0. `register.F1.wilson_lo` deleted in the install: `matched 28, not matched 1`, `F1-register (oracle value missing: wilson_lo)`, exit 6. `_fixtures/oracles_v1.json` replaced by `{"captured": `: `matched 3, not matched 26, no oracle recorded 3`, exit 6, report written (equal to the note). File restored.
- **FA2-R2 end to end.** The wheel installed with `pip --no-deps --no-index --target X/src`, with `X/fixtures/newcombe_table2.json` (status `checked`) and `X/fixtures/r/proc_asah.json` planted; `proofpack.__file__` was `...\X\src\proofpack\__init__.py`. No `pyproject.toml`: F14 `no_oracle_recorded`, `oracle_source` null, `r_captures_not_captured`, `matched 29`. `X/pyproject.toml` naming `customer`: the same. Naming `proofpack`: F14 `matched` with marking `checked`, `r-captures: present_not_compared`, `matched 30`. That third case is the note's decision 5 as written, and the note refuses "The Newcombe `[unverified]` marking always reaches the page".
- **F17** on my own two Git Bash runs and one PowerShell run: the five prefixes above, equal across all three. A same-platform repeat on `win-amd64-cp314`, not the reference platform. `--n 400`: exit 0.
- **T12 golden.** `PROOFPACK_REGEN_GOLDEN=1 python -m pytest tests/test_t12.py -k golden` in `probe`, then `cmp` with `git show HEAD:tests/fixtures/golden/T12.html`: byte-identical. `tests/test_t12.py`: `10 passed`.
- **T12 wording** (rendered from my report): "CSA-structured" once, no "CSA-compliant"; "supports, does not replace, the manufacturer's own validation." twice; "draft guidance (January 2025), not for implementation" on each anchor I grepped; "reference platform only (D1 section 9)"; 4 lines carrying `[unverified` (`grep -c`).
- **Workflows.** `yaml.safe_load` parses `ci.yml`, `release.yml` and `dependabot.yml`. `--offline` removed from `release.yml:147` (the `install-from-testpypi` run): `14 failed, 9 passed` in `tests/test_workflows.py`, among them `test_each_command_the_three_patterns_match_carries_offline[release.yml]` (the lens-line cases fail too, because each asserts exactly one violation). The same line with `--offline` turned into ` # --offline`: `14 failed`. `--offline` removed from `ci.yml:133` (`proofpack:ci fixtures`): `1 failed`, `...carries_offline[ci.yml]`.
- **Dockerfile.** `FROM python:3.12`: `1 failed, 16 passed`, the failure `test_the_base_image_is_python_3_12_slim_amd64_by_digest_or_marked_unverified`. `FROM --platform=linux/amd64 python:3.12-slim-bookworm`: the same test fails (the note's "did not reproduce" row holds).
- **SBOM against `uv.lock`** (my own parse): 63 packages in the lock; 62 components, 0 extra; the one not in `components` is `proofpack 0.1.0.dev1`, which is `metadata.component`. Every component purl begins `pkg:pypi/`; `specVersion` 1.5, `bomFormat` CycloneDX.
- **Merge notes.** `comm -12` of `git diff --name-only e17a510 main` and `e17a510 43521dd`: `scripts/mutation_sweep.py` only, as the note says. The branch does not touch `cli.py`, `templates/base.html` or `pyproject.toml` in this round. Trial merge in `merge` (one auto-merge in `scripts/mutation_sweep.py`), full suite with `PROOFPACK_TR39_FULL`: `1544 passed, 1 skipped, 1 xfailed in 145.30s`; ruff `All checks passed!` / `221 files already formatted` (Git Bash). The note's `1543 passed, 2 skipped` at `c3bb893` without the TR39 file is the same count.
- **Line endings.** In `wt-ap3`, every committed file is `i/lf`; `scripts/mutation_sweep.py` is `w/crlf` in the working copy, as the note says.

## Lens 2's blocker and sentence violations: closed on what I fed

- **FA2-B1.** A value deleted from a captured entry, a register entry, and an installed wheel's file each gives `not_matched`, `oracle value missing: <name>`, exit 6 (measured above, in `probe` and in the venv). `test_every_compared_row_declares_the_names_its_engine_and_oracle_carry` passes at `43521dd`; mutant `ap3_compared_set_is_the_oracle_keys` is killed.
- **FA2-R2.** Measured end to end above; mutant `ap3_newcombe_read_beside_any_install` killed.
- **FA2-R3 / RG2-S1.** The four lens lines are caught by the new detector and missed by the old one. The test name is now `test_each_command_the_three_patterns_match_carries_offline`, and the `IMAGE_CALL` comment lists the six words the tests feed.
- **FA2-R4.** Each rule lists its rows; `test_each_tolerance_rule_lists_its_rows` compares the listed ids with `register()` per class. I read D1 section 9 (line 352): "1e-9 closed-form (Wilson, 2×2, Brier, O/E, PSI), 1e-6 iterative (IRLS slope/intercept, DeLong via placements), bootstrap CIs to reported rounding". The rule texts quote that and no more.
- **FA2-R5, R6, R8.** The skip is an assertion; the step name is `passive baseline scan (zap-baseline.py -I)` with `if: always()` on the upload (written, never run; see RG3-S1 for the test name); a bool gives `not a number (bool)`.

## What I could not break (what I tried)

- **The compared set.** Three deletions through the CLI, one register deletion in the installed wheel, the lens's in-process +1e-6 case (in the suite), and `f4_expected.json` as a list and truncated. Each gave `not_matched`, exit 6, report written.
- **The unreadable-file path.** Truncated JSON and invalid UTF-8 in `oracles_v1.json`, and truncated `f4_expected.json`: each `not_matched`, exit 6. (A directory in place of the file is RG3-N1.)
- **The Newcombe read.** A planted `checked` file beside a `pip --target` install under no pyproject and under one naming `customer`: not read, `[unverified]` reason kept.
- **The `--offline` word check.** My own lines: `--offline=0` is reported as no violation, and `proofpack fixtures --offline=0` exits 2 with `argument --offline: ignored explicit argument '0'` (the engine does not run). `"--offline"` in quotes: no violation, correctly. `--offlin` (an argparse abbreviation) and `\t#--offline`: reported.
- **The golden, F17 and the SBOM.** Byte-identical golden; identical masked F17 prefixes across three runs and two shells; SBOM byte-identical across three runs and two shells.
- **The sweep.** All 25 ap3 mutants killed at `43521dd`.
- **Scope and merge.** No change under `stats/`; no test deleted; no skip or xfail added; the trial merge is clean and its suite passes.

## What I could not check

- **Everything that runs only in GitHub Actions**: `docker-smoke` in `ci.yml`; `build`, `image`, `testpypi`, `install-from-testpypi`, `github-release` and `zap-baseline` in `release.yml`; Dependabot; Trivy; ZAP's exit under `-I`; whether `if: always()` uploads after a failed scan. Written, never run. `offline-namespace`'s runs 35911876338 and 35992801938 I did not read.
- **The base image digest.** No pull was allowed.
- **The CycloneDX 1.5 JSON schema.** Not fetched; the SBOM was checked structurally.
- **The reference platform.** Every figure is from `win-amd64-cp314`.
- **The sweep and the trial merge in PowerShell.** Not run.
- **Full-suite figures inside `wt-ap3` itself.** I kept to read-only commands there; my `tip` worktree is the same commit.

## Sentences refused

- "`proofpack fixtures` writes a report for every damaged oracle file": RG3-N1 (a directory in place of `oracles_v1.json` exits 5 with no report).
- "The ZAP artefact is uploaded after a failed scan": the job has never run (RG3-S1).
- "The workflow test catches every engine run without `--offline`": RG2-N2's forms are still missed.
- "F17 proves hash identity": it compares five named checks on one platform, and the reference platform was not measured.
