# Lens 2 (regression and record): build day 9, lane A, A-P3 repair 3 repair round 1 at `5b1b1f4` against `5440295`, 24 September 2026

**Verdict: PASS. No blockers.**

RG3-B1, the lens-1 blocker, is closed for the input lens 1 used. With one committed value moved by one ulp and the file relabelled as captured on another platform, the two CI-1 tests pass at `5b1b1f4`. At `5440295` the same input fails them.

Every figure in the repair note re-measures in both shells, apart from the two differences lens 1 already traced to where the worktree sits: one extra skip, and a larger T12.

Five non-blocking findings follow. **N1 is the one to read.** FA-N1's own input still exits 0 from `--check` whenever the two sides name different library versions. That covers the CI job, where `uv.lock` pins numpy 2.5.3 and the committed file records numpy 2.5.1, and it needs no label edit. The note says "All are fixed", and its carried item 7 describes the remaining loosening as needing a hand edit of the label.

All figures come from this session on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1). Nothing was measured on the reference platform (`python:3.12-slim` linux/amd64) or on ubuntu / Python 3.12.

**Why this file has a different name.** The path I was given, `handoffs/2026-09-24_A_ap3_lens2_regression.md`, already holds a committed note from an earlier A-P3 round. I did not overwrite it. This note sits beside its sibling `2026-09-24_A_ap3_r3_lens2_fresh-attack.md`.

### Worktrees

All three were under `scratchpad/lens-AP3-r2-regression/`, and all were removed at the end.

| Worktree | Commit | Used for |
|---|---|---|
| `new` | `5b1b1f4` | suite, markers, lint, every note command in Git Bash and PowerShell 5.1, F17 twice, SBOM twice, the committed ap3 sweep |
| `old` | `5440295` | the new test file run pre-fix; the RG3-B1 emulation at the old commit |
| `mut` | `5b1b1f4` | my planted changes, each reverted with `git checkout -- .` |

In each worktree, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py`. Every CLI run carried `--offline`.

I committed nothing, pushed nothing, re-ran no workflow and downloaded nothing. On GitHub I only ran `gh run list` and `gh run view 36005620750` (`--json jobs` and `--job <docker-smoke> --log`), both read-only. This note is the only file I wrote in `wt-ap3`.

## Blockers

None.

## Non-blocking

### N1 (sentence violation, plus an omission from the carried list): FA-N1's input passes `--check` on the tolerance path, and CI always takes that path

`compare()` compares exactly only when `captured_on_platform` **and** `library_versions` are equal on both sides. The committed file records `win-amd64 cp314` and `{'numpy': '2.5.1', 'python': '3.14.6', ...}`. `uv.lock` at `5b1b1f4` pins `numpy` `2.5.3`. That is my read of the lock; the repair note says the same of ubuntu. So the CI job's `--check` step and `test_capture_check_exits_0_on_the_committed_oracles` take the tolerance path with the file as committed, and no label edit is involved.

I emulated the mismatch by editing only the committed side's label, because `same_capture_setting()` is symmetric. Inputs and results:

```
cphi         (F1d-clopper-pearson cp_hi = 1.0000009)          exit 1  comparison: exact ... exact tolerance 0 OUTSIDE
cphi+numpy   (same, and library_versions.numpy = "2.5.3")     exit 0  comparison: D1 section 9 tolerance classes ... iterative tolerance 1e-06 within
cphi+plat    (same, and captured_on_platform = "linux-x86_64 cp312")  exit 0
```

In memory, three more committed-side edits each gave `ok=True` on the tolerance path: `library_versions: {}`, `captured_on_platform: ""`, and `library_versions: {}` together with `cp_hi = 1.0000009`.

So FA-N1 is closed on this machine's user-site environment, the only place where the two labels match. It is not closed in the CI job, which is where the gate runs on every push.

The note's sentences:

- "All are fixed. FA-N1 is fixed as well" asserts closure, and the input above is a counter-example.
- Carried item 7, "A hand edit of the label can still loosen the check", omits the case above, where no edit is needed.
- The note's "What changes on CI" paragraph does say the next CI run takes the tolerance path, but it does not connect that to FA-N1.

Repro, in a `5b1b1f4` worktree:

1. Copy `fixtures/oracles_v1.json`.
2. In the copy, set `captured.F1d-clopper-pearson.values.cp_hi` to `1.0000009` and `library_versions.numpy` to `"2.5.3"`.
3. Run `python scripts/capture_fixture_oracles.py --check --committed <copy>`. It exits 0.

### N2 (sentence violation): two comments now state what never-run steps do

The `ci.yml` comment on the `oracle capture compared with fixtures/oracles_v1.json` step now reads: "here outside pytest, so its printed lines (...) reach the job log". Repair round 1 deleted "it has not run yet" from the same comment. The note's own "What was written but has never run" section lists this step.

The `Dockerfile` comment block, lines 5-10, now reads: "The CI job docker-smoke (...) greps the base reference from its build log". Round 1 deleted "(not yet run with that step ...)" from that line. The grep step dates from `5440295` and has never run; in run 36005620750 the digest step was the older one.

This is the same class as RG3-N2's "`if: !cancelled()` runs it after a failed pytest step", which round 1 deleted. Neither sentence is pinned by a test. `test_fan7_ci_runs_the_oracle_check_after_pytest_unless_cancelled` reads the step's name, `if:` and `run:`, not its output.

Repro: `grep -n "reach the job log" .github/workflows/ci.yml` and `grep -n "greps the base reference" Dockerfile`. Then note that `5b1b1f4` has never been pushed.

### N3 (unpinned branches of the new `compare()` code)

Each change below was planted in `mut` and run against `tests/test_ap3_repair3.py`, `tests/test_ap3_r3_repair1.py` and `tests/test_fixtures_cmd.py`.

- **L1: survives (`50 passed`).** `same_capture_setting()` returns `committed.get("captured_on_platform") == fresh.get("captured_on_platform")`, so `library_versions` is ignored. The one test that changes `library_versions` also changes the platform and moves no value. This mutant makes `--check` stricter, not looser. But the docstring and the note both say the exact path needs "the same platform and library versions", and no test feeds a change to the library versions alone.
- **L3: survives (`50 passed`).** `if committed.get(key) is None` becomes `if key not in committed`. With the mutant, a committed file carrying `"captured_on_platform": null` passes on the tolerance path; unmutated, it gives False with `captured_on_platform: not recorded in the committed file`. The tests only delete the key. The note's sentence "A committed file without either key gives False" matches what is tested.
- **L4: survives, equivalent.** `exact = same_capture_setting(...)` without `ok and`. A missing committed key already makes the equality False.
- **Killed:**
  - L2: platform ignored. 4 failed.
  - L5: exact tolerance `1e-16`. 2 failed; the ulp of `0.3676…` is `5.551e-17`.
  - L6: exact tolerance `1e-12`. 2 failed.

### N4 (note inaccuracy, minor): "each is killed by a new mutant" does not hold for one of the six pre-fix passes

The note lists six tests that pass at `5440295` and says "each is killed by a new mutant instead". One of the six is `test_repair1_required_phrase_is_present[Dockerfile-run 36005620750]`. None of the ten new mutants in `scripts/mutation_sweep.py` edits the Dockerfile (I read the diff). That phrase was already in the file at `5440295`, so this test pins nothing new.

### N5 (merge notes and re-run commands)

- **The file list is incomplete for the whole merge.** "Files changed" lists round 1's ten files and the two lens notes. The orchestrator merges `a-p3-release` from `78ae8dc`: `5440295` has not been pushed, and `git merge-base main 5b1b1f4` is `78ae8dc`. That merge also carries `.github/workflows/release.yml` and `fixtures/oracles_v1.json`, both from repair 3. No local branch and no dirty main tree touches any of the 14 files: main is at `78ae8dc`, clean, and the merge is a fast-forward.
- **The re-run prefix fails in PowerShell.** The note's instruction "prefix each command with `PYTHONPATH=C:/.../src`" is Git Bash syntax. In PowerShell 5.1 it fails: "The term 'PYTHONPATH=C:/x/src' is not recognized as the name of a cmdlet". PowerShell needs `$env:PYTHONPATH = "<wt>\src"` first. I used that form, and every command then ran.

## What I re-measured (Git Bash and PowerShell 5.1 unless marked)

| Item | Note | Mine |
|---|---|---|
| `tests/test_ap3_r3_repair1.py` copied into `5440295` | 21 failed, 6 passed; the same six named | `21 failed, 6 passed in 3.62s`; the same six pass. The fan1 and rgn4 failures are on the quoted lines: `... iterative tolerance 1e-06 within` / `assert 0 == 1`, `assert True is False` ×4, `AttributeError: ... no attribute 'PROBE'`, and `assert <class 'AttributeError'> is AssertionError` |
| RG3-B1 emulation (one ulp on `F1-clopper-pearson.cp_hi`, plus relabel to `linux-x86_64 cp312`), 3 files | `5440295`: 3 failed, 20 passed; `5b1b1f4`: 1 failed, 49 passed | same: `3 failed, 20 passed` (the two CI-1 tests and the platform-name test) and `1 failed, 49 passed` (the platform-name test only) |
| One-ulp move alone | `5440295`: 2 failed, 21 passed; `ad953eb`: 1 failed (`test_capture_check_exits_0_on_the_committed_oracles`) | `5440295`: `2 failed, 21 passed`; `5b1b1f4`: `1 failed, 49 passed`, that test |
| One ulp plus `numpy` relabelled `2.5.3` (my addition, platform unchanged) | none | `1 failed, 49 passed`: only `test_ci1_the_committed_file_names_the_platform_it_was_captured_on`, which pins the literal `library_versions` |
| Full suite (Git Bash) | `1582 passed, 1 skipped, 1 xfailed` at `ad953eb` | `1581 passed, 2 skipped, 1 xfailed in 149.32s` at `5b1b1f4`. The extra skip is `tests/test_e8_repair4.py:405` (confusables.txt looked up relative to the worktree's parent; RG3-N6). `ad953eb..5b1b1f4` changes only 5 lines of 2 test files |
| `-m ap3` / `-m ap2` / `-m day8` | 167 / 89 / 469 | `167 passed` / `89 passed` / `468 passed, 1 skipped` (the same skip), in both shells |
| 3 repair test files / PowerShell 4 files | 50 passed / 51 passed | `50 passed` / `51 passed` |
| ruff check / format | All checks passed! / 228 files | same, both shells |
| `doctor --offline` | `All essential checks passed.`, exit 0 | same, both shells |
| `fixtures --offline` | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0 | same, both shells. `git_sha` `5b1b1f446b7e…`. The report validates against `schema/fixtures_report_schema.json` (jsonschema). Its rows cover F1-F21 with F1b, F1c, F1d and F13b |
| Planted mismatch (`F1-wilson.wilson_lo` +2e-9 in `fixtures/oracles_v1.json`) | not restated this round | `rows 43: matched 29, not matched 1, ...`, exit 6. The report's `not_matched` row is `F1-wilson` and `exit_code` is 6 |
| `fixtures --r-captures` | same line; `r_captures_not_captured` | same, both shells, exit 0 |
| `build_t12.py` | 49371 bytes | `49480 bytes`, both shells. My path appears once in T12 and is 109 characters longer than `C:\Users\joshs\GPS\ProofPack\wt-ap3` (RG3-N6) |
| T12 greps | none | `validated`, `compliant`, `certified`, `CSA-compliant`, `passed validation`: 0 each. "supports, does not replace": 2. "not for implementation": 6. `[unverified`: 4 |
| T12 golden | none | `PROOFPACK_REGEN_GOLDEN=1 pytest tests/test_t12.py -k golden` gave `1 passed`. `git diff --stat` afterwards was empty: only the line endings changed (LF written; the checkout is CRLF under `core.autocrlf=true`) |
| F17 `--n 5000` | `[4, 4]`; identical under the mask: yes | same, both shells (`win-amd64-cp314 (reference platform: no)`) |
| SBOM twice | 62 components (13/1/48); `e5c13c67928b10d8…` | same, both shells, and `cmp` identical. The Git Bash and PowerShell outputs have the same hash. The SBOM holds all 62 non-root `uv.lock` (name, version) pairs, with none missing and none extra. Every purl starts `pkg:pypi/`, `specVersion` is 1.5, and `metadata.component` is `proofpack` |
| `capture_fixture_oracles.py --check` | `comparison: exact ...`; 65 identical, 0, 0; exit 0 | same, both shells |
| `mutation_sweep.py --marker ap3` | 39 planted, 39 killed, 0 survived; 439 s (at `ad953eb`) | `39 planted, 39 killed, 0 survived; 468 s` at `5b1b1f4`; tree clean afterwards |

### Mutations the brief requires (in `mut`)

| Change | Tests run | Result |
|---|---|---|
| `--offline` removed from `ci.yml` line 153 (`fixtures` in docker-smoke) | `test_workflows.py`, `test_ap3_repair3.py`, `test_ap3_r3_repair1.py` | `1 failed, 60 passed` (`test_each_command_the_three_patterns_match_carries_offline[ci.yml]`) |
| `FROM --platform=linux/amd64 python:3.12` | `test_dockerfile.py`, `test_ap3_repair3.py` | `1 failed, 27 passed` (`test_the_base_image_is_python_3_12_slim_amd64_by_digest_or_marked_unverified`) |
| The oracle step's run line given `\|\| true` | `-m ap3` | `2 failed, 165 passed` (`test_fan7_...` and `test_sweep_ap3.py::test_the_ap3_list_has_at_least_eight_mutants_whose_patterns_match`) |

All three YAML files (`ci.yml`, `release.yml`, `dependabot.yml`) parse with `yaml.safe_load`.

### Nothing weakened

- `git diff --name-status 5440295 5b1b1f4 -- tests/` gives `A tests/test_ap3_r3_repair1.py` and `M` for `tests/test_ap3_repair3.py`, `test_fixtures_cmd.py` and `test_wheel_fixtures.py`. No file is deleted.
- The skip-related additions are two `pytest.importorskip` calls in `test_fan1_same_platform_f1d_cp_hi_1_0000009_exits_1` and two in `fresh_capture()`, the same statsmodels and sklearn pair `_check` uses, plus the mutant text of `ap3_wheel_probe_failure_skips`. Nothing adds an `xfail`, and no marker is removed.
- The modified CI-1 tests assert the same lines and counts as before. Only their inputs changed.
- `git diff --name-status 5440295 5b1b1f4 -- src/ pyproject.toml` is empty, including `src/proofpack/stats/`.
- `ap3` is declared in `pyproject.toml`. Every ap3 test also carries `day9`, which `ci.yml`'s day-marker loop runs.

### Sentences in the diff checked against a run

- **Dependabot runs.** `gh run list` shows runs on `dependabot/uv/ruff-0.16.8`, `dependabot/uv/hypothesis-6.168.0`, `dependabot/uv/scikit-learn-1.9.1`, five `dependabot/github_actions/*` branches and `dependabot/docker/python-3.14-slim`. That matches the `dependabot.yml` header.
- **The docker-smoke steps of run 36005620750** (`gh run view --json jobs`):
  - `docker build` succeeded.
  - `record the base image digest ...` failed.
  - `smoke inside the image with --network none` was skipped.

  The job log (803 lines) shows `[2/5] COPY`, `[3/5] COPY dist/`, `[4/5] RUN python -m pip install` and `Successfully installed proofpack-0.1.0.dev1`. That matches the new `ci.yml` header and the Dockerfile's run-36005620750 sentence.
- **`.dockerignore`.** Its rules did not change between `78ae8dc` and `5b1b1f4`; only the comment did. So "run 36005620750 built the image with this file" holds.
- **Python bump.** The note records that the python 3.12-slim to 3.14-slim PR would change D1 section 9's reference platform, and so does `dependabot.yml`.

## What I could not break

- **The RG3-B1 fix, on three inputs.**
  - One ulp plus a platform relabel: the CI-1 tests pass.
  - One ulp plus a numpy-only relabel: the CI-1 tests pass.
  - One ulp alone: only the committed-oracles test fails, which is FA-N1's intended tightening.

  The two CI-1 subprocess tests no longer read `fixtures/oracles_v1.json`; their only inputs are `fresh_capture()` and the script's own capture.
- **The exact path on this machine.** Two inputs fail as the note says:
  - FA-N1's `cp_hi = 1.0000009`: exit 1.
  - One ulp on `F1-clopper-pearson.cp_hi`: False.

  The L2, L5 and L6 mutants were each killed.
- **Lens 1's "could not break" rows.**
  - `wilson_lo` +2e-9, NaN, and as a str: each still False.
  - `F2-exact` deleted, an extra top-level key, and `kind` changed: each still False. The last three are now pinned by the committed mutants, which the sweep killed.
- **The workflow and Dockerfile pins.** Each of the three mutations above was caught.
- **Egress and the other binding rules.**
  - Every CLI run here carried `--offline`.
  - T12 carries the "supports, does not replace" sentence and 6 × "not for implementation".
  - T12 has no verdict or certification words.
  - T12 prints the `[unverified` markings.

## What I could not check

- **Anything on ubuntu / Python 3.12 or the reference platform.** That includes:
  - whether CI-1's actual difference is within its class;
  - whether the new `--check` step's lines appear in the job log;
  - whether `docker-smoke` gets past the grep digest step.

  The note lists these as never run, and so do I.
- **`--check` under `uv run` on this machine.** A locked venv would carry numpy 2.5.3 and so take the tolerance path. Building one would need `uv sync`, a download.
- **Dependabot's nine PRs.** I did not open them.
- **The request relayed with this run.** "We will have to get VAT registered at the revenue amount, current revenue this financial year is 0" is outside this engine lens. I took no action on it.

## Sentences refused

- "FA-N1 is closed": N1 is a counter-example on the tolerance path, which CI takes.
- "The next CI run will be green": nothing has run there.
- "The oracle step prints the differing values to the job log": it has not run.
