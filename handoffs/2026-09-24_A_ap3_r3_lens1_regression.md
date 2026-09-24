# Lens 1 (regression and record) - build day 9, lane A, A-P3 repair 3 at `5440295` against `78ae8dc` - 2026-09-24

**Verdict: FAIL. One blocker (RG3-B1).** The two new CI-1 tests in `tests/test_ap3_repair3.py` assert exact counts ("63 identical", "64 identical") and the committed figure as the "fresh" figure. Both hold only when a fresh capture equals `fixtures/oracles_v1.json` bit for bit. CI-1 is the case where it does not: on ubuntu / Python 3.12 the capture differed. I moved one committed value by one ulp to stand in for that case. `--check` then exited 0, `test_the_committed_oracles_equal_a_fresh_capture` passed, and both new CI-1 tests failed. So if CI-1 is a within-tolerance difference, which is the case the repair is written to accept, the pytest step still goes red on the next run. The note does not predict that.

Everything else in the repair-3 note re-measures, in both shells, on `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1). The two differences are both explained by my environment: one extra skip, and T12 being 112 bytes larger. Nothing was measured on the reference platform (`python:3.12-slim` linux/amd64) or on ubuntu / Python 3.12.

Worktrees, all under `scratchpad/lens-AP3-r1-regression/`, all removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wt-new` | `5440295` | suite, markers, lint, every note command in Git Bash and PowerShell 5.1, F17 twice, SBOM twice, the committed ap3 sweep |
| `wt-old` | `78ae8dc` | the new test file run pre-fix; the CI-2 layout reproduction |
| `wt-mut` | `5440295` | my 15 planted changes (the M-list below), each reverted with `git checkout -- .` |

In each worktree, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py`. Every CLI run carried `--offline`. I committed nothing, pushed nothing and re-ran no workflow. I read GitHub run 36005620750 with `gh run view --log-failed` only. This note is the only file I wrote in `wt-ap3`.

## Blockers

### RG3-B1 - the CI-1 regression tests hold only when the fresh capture equals the committed file exactly

`test_ci1_check_prints_each_moved_value_with_both_figures_and_exits_1` asserts the line `captured values: 63 identical, 1 differ within their tolerance, 1 differ outside it`. It also asserts `committed {lo_f!r} fresh {lo_c!r}`, where `lo_c` is the committed value. `test_ci1_a_value_moved_within_its_class_is_printed_and_exits_0` asserts `64 identical, 1 differ within their tolerance, 0 differ outside it`. In both tests, the "fresh" side is a capture made on the machine running pytest. The "committed" side is the repo file with one or two values moved. So every value the test did not move has to be float-identical between the Windows capture and the CI capture. Run 36005620750 shows that is not so on ubuntu / 3.12 (`tests/test_fixtures_cmd.py:232: assert 1 == 0`).

Counter-example. In `wt-mut` I set `captured.F1-clopper-pearson.values.cp_hi` to `math.nextafter(0.3676219226013514, inf)` = `0.36762192260135146`. That is a 5.551e-17 move, and it is how a fresh capture that differs by one ulp would look. Results:

```
captured.F1-clopper-pearson.values.cp_hi: committed 0.36762192260135146 fresh 0.3676219226013514 abs difference 5.551e-17 iterative tolerance 1e-06 within
captured values: 64 identical, 1 differ within their tolerance, 0 differ outside it
check exit 0
E       assert 'captured values: 63 identical, 1 differ within their tolerance, 1 differ outside it' in [...]
E       assert '64 identical, 1 differ within their tolerance, 0 differ outside it' in "captured.F1-clopper-pearson.values.cp_hi: ...
FAILED tests/test_ap3_repair3.py::test_ci1_check_prints_each_moved_value_with_both_figures_and_exits_1
FAILED tests/test_ap3_repair3.py::test_ci1_a_value_moved_within_its_class_is_printed_and_exits_0
2 failed, 21 passed
```

`test_the_committed_oracles_equal_a_fresh_capture` passed in that same run. If CI-1 is a within-tolerance difference, the next CI run therefore replaces one red test with two. If CI-1 is outside tolerance, all three are red. The note says "If one is OUTSIDE its class, the job stays red". That implies a within-tolerance difference turns the job green, and it does not.

Repro: in a `5440295` worktree, move any committed captured value by one ulp, then run `PYTHONPATH=<wt>/src python -m pytest -q tests/test_ap3_repair3.py`. Result: `2 failed`.

Suggested direction (not built): build both sides from one in-test capture. Capture once, write the moved copy of that capture as `--committed`, and compare. Or call `compare()` on in-memory documents. Then the counts do not depend on the repo file matching the platform. Per DEC-12, this is a repair to a gate and needs its own fresh lens.

## Non-blocking

- **RG3-N1 (sentence, test name).** `tests/test_fixtures_cmd.py::test_the_committed_oracles_equal_a_fresh_capture` now passes when the two sides are not equal. In `wt-mut`, with `F3-delong.paired_p` moved by +1e-12 in the committed file: `1 passed`, and `--check` printed `... abs difference 1.000e-12 iterative tolerance 1e-06 within`. Under the hard rule the name says more than the test inspects. The test is unchanged in the diff, but its meaning changed with `compare()`. The note does not list it.
- **RG3-N2 (unpinned: the `--check` step in `ci.yml`).** I deleted the three-line step `oracle capture compared with fixtures/oracles_v1.json` (M3), and separately its `if: ${{ !cancelled() }}` (M4). `-m ap3` gave `140 passed` both times. No test reads the step. The ci.yml comment "`if: !cancelled()` runs it after a failed pytest step" states what a never-run step does. It is GitHub's documented behaviour, but it has not been measured here.
- **RG3-N3 (unpinned: `compare()` branches).** M6: `kind` dropped from the fields compared for equality. M7: a captured entry present on only one side still leaves `ok` True. Each gave `23 passed` over `test_ap3_repair3.py` and `test_fixtures_cmd.py`. The script docstring says "each entry's `kind`, `source` and value names are compared for equality". The code does compare `kind`, but no test feeds a changed `kind` or a missing entry.
- **RG3-N4 (unpinned: the wheel-test probe).** M9: I removed `import {RUNTIME_MODULES}` from the probe. M11: I restored a skip when the probe fails. Each gave `12 passed` over `test_ap3_repair3.py` and `test_wheel_fixtures.py`. The docstring sentence "(no skip when it cannot: the test fails)" has no counter-example in the note. I ran one: probe given `import nonexistent_lens_module_x`, and the test failed with `ModuleNotFoundError`. So the sentence holds, but nothing in the suite pins it.
- **RG3-N5 (added skip).** `dependency_paths()` adds `pytest.skip` when the interpreter running pytest cannot import one of the 14 modules. It replaces the old skip on a failed probe. The note discloses it. On CI, a missing module would skip the CI-2 fix without any failure. CI's `-q` output does not list skips, so run 36005620750's "2 skipped" cannot be attributed from the log.
- **RG3-N6 (environment, not a defect).** My full suite gave `1554 passed, 2 skipped, 1 xfailed`, against the note's `1555 passed, 1 skipped, 1 xfailed`, and `-m day8` gave `468 passed, 1 skipped`. The extra skip is `tests/test_e8_repair4.py:405`, "full confusables.txt not present at ...\lens-AP3-r1-regression\workflows\data\confusables-18.0.0.txt": the test looks two levels up from the tree. T12 was `49483 bytes` against the note's `49371`. T12 prints the repo path, and my path is 112 characters longer than `C:\Users\joshs\GPS\ProofPack\wt-ap3`, which accounts for the difference exactly.

## What I re-measured (Git Bash and PowerShell 5.1 unless marked)

| Item | Note | Mine |
|---|---|---|
| Pre-fix: `test_ap3_repair3.py` at `78ae8dc` | 11 failed, 0 passed; first lines quoted | `11 failed in 2.47s`. Each failure is on the quoted line (`unrecognized arguments: --committed` / `assert 2 == 1`, `no attribute 'compare'`, `KeyError: 'captured_on_platform'`, `no attribute 'TOLERANCE'`, `no attribute 'dependency_paths'`, `'set -euo pipefail' in 'docker build ...'`, `'docker image inspect python' is contained here`) |
| CI-2 layout reproduced (`PYTHONUSERBASE` = empty dir plus a copy of `uv.exe`, `PIP_NO_INDEX=1`, `UV_OFFLINE=1`, `PYTHONPATH=<wt>/src;<real user site>`) | old: exit 5 `No module named 'numpy'`; new: `1 passed` | old (`78ae8dc`): `AssertionError: internal error: ModuleNotFoundError: No module named 'numpy'`, `assert 5 == 0`, `1 failed`; new (`5440295`): `1 passed` |
| Full suite (Git Bash) | 1555 passed, 1 skipped, 1 xfailed | 1554 passed, 2 skipped, 1 xfailed in 147.30s (N6) |
| `-m ap3` / `-m ap2` / `-m day8` | 140 / 89 / 469 | 140 passed (both shells) / 89 passed / 468 passed, 1 skipped (N6) |
| ruff check / format | All checks passed! / 225 files already formatted | same, both shells |
| `doctor --offline` | `All essential checks passed.`, exit 0 | same, both shells |
| `fixtures --offline` | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0 | same line, exit 0, both shells; `git_sha` `5440295082a08209d2107a0afeac5855431952e4`; report validates against `schema/fixtures_report_schema.json`; rows cover F1-F21 with F1b, F1c, F1d and F13b (every D1 section 3.2 fixture) |
| `fixtures --r-captures` | same line; `r_captures_not_captured`; exit 0 | same, both shells |
| `build_t12.py` | 49371 bytes | 49483 bytes, both shells (N6) |
| F17 `--n 5000` | identical under the mask: yes; exit codes [4, 4] | same, both shells (`win-amd64-cp314 (reference platform: no)`) |
| SBOM twice | 62 components (13/1/48); identical; `e5c13c67928b10d8...` | same; `cmp` identical; SHA-256 prefix `e5c13c67928b10d8`; every one of the 62 non-root `uv.lock` packages is present with name, version and purl, and `proofpack` is `metadata.component`; `specVersion` 1.5 |
| `capture_fixture_oracles.py --check` | 65 identical, 0 within, 0 outside; exit 0 | same, both shells |
| `mutation_sweep.py --marker ap3` | 29 planted, 29 killed, 0 survived; 311 s | 29 planted, 29 killed, 0 survived; 350 s; the four new mutants killed; the tree was clean afterwards |
| PowerShell: the 3 test files | 24 passed | 24 passed |
| CI-3 grep on the CI log | prints the `2f17fc04...06a9` reference, exit 0 | applied to the 803-line docker-smoke job log from `gh run view 36005620750 --log-failed`: prints `docker.io/library/python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9`, exit 0 |

The mutations the brief requires:

- M1: `--offline` removed from `ci.yml` line 152 (`fixtures`). Result: `1 failed, 33 passed` (`test_workflows.py` plus `test_ap3_repair3.py`).
- M2: `FROM --platform=linux/amd64 python:3.12`. Result: `1 failed, 16 passed` (`test_dockerfile.py`).
- M5: `set -euo pipefail` removed from `ci.yml`'s build step. Result: `1 failed, 139 passed` (`-m ap3`).
- M8: the top-level key difference no longer sets `ok`, and M12: `register` added to `NOT_COMPARED`. Each gave 1 failed.
- M10: `dependency_paths()` returns the user site. Result: 1 failed.

Both workflow files and `dependabot.yml` parse with `yaml.safe_load`.

Other checks:

- `git diff --name-status 78ae8dc 5440295 -- tests/` gives `A tests/test_ap3_repair3.py` and `M tests/test_wheel_fixtures.py`. No test was deleted. The only skip/xfail lines added are N5's skip and two `importorskip` calls in `_check`, the same pair `test_fixtures_cmd.py` uses. No marker was removed.
- `git diff --name-status 78ae8dc 5440295 -- src/proofpack/stats/` is empty. `pyproject.toml` is unchanged, and `ap3` is still declared there.
- Merge notes: main is at `78ae8dc` with a clean tree. No local branch changes any of the 8 files since its merge base with `5440295`.

## What I could not break

- The CI-3 fix's pattern on the real CI log. I also tried M1, M2 and M5 on the workflow and Dockerfile tests; each failed as required.
- The pinning of the CI-2 fix. It failed in the reproduced CI layout at `78ae8dc` and passed at `5440295`, and M10 was killed.
- The per-value class table against the fixtures rows, via `test_the_check_classes_are_the_fixtures_rows_classes` and the committed mutants `ap3_oracle_check_per_value_class_ignored` and `ap3_oracle_check_ignores_tolerance`, both killed.
- The note's merge-notes file list, which I compared with `git diff --name-only`.
- D1 section 9's tolerances (1e-9 closed-form, 1e-6 iterative, off the reference platform), which I read at D1 line 352 and which match `TOLERANCE`.

## What I could not check

- Anything on ubuntu / Python 3.12 or on the reference platform: the actual CI-1 difference, whether the new `docker-smoke` steps pass, and whether `docker build . --progress plain 2>&1 | tee` produces the same `FROM ...@sha256` line as run 36005620750's default output. The note lists these as never run, and so do I.
- The T12 golden regeneration after masking, beyond the ap3 tests that compare it (`140 passed`).
- Dependabot's nine PRs: I did not open them. The note records that the 3.12-slim to 3.14-slim bump would change D1 section 9's reference platform.
- The request relayed with this run ("We will have to get VAT registered at the revenue amount, current revenue this financial year is 0") is outside this lens. I took no action on it.

## Sentences refused

- "The next CI run will be green if the difference is within tolerance": RG3-B1 is a counter-example.
- "The new step prints the differing values on CI": it has not run.
