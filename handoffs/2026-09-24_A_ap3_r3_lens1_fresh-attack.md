# A-P3 repair 3, lens 1 (fresh attack) - build day 9, lane A, `5440295` against `78ae8dc` - 2026-09-24

**Verdict: PASS. No blockers.**

Nine non-blocking findings are recorded below. **N1 is the one Josh should read.** Repair 3 swapped the `--check` exact comparison for a tolerance comparison, and that change lets a hand-edited oracle through. I set `captured.F1d-clopper-pearson.values.cp_hi` to `1.0000009`, a proportion bound above 1:

- `scripts/capture_fixture_oracles.py --check` exits 0 at `5440295` and exits 1 at `78ae8dc`.
- `proofpack fixtures` then reads the row as matched.

Four of the findings are sentence violations (N2 to N5). Five of my own mutants of the repair survive (N6 to N8, N9).

All figures are from this session on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1), unless a line names another platform. Nothing was measured on the reference platform (`python:3.12-slim` linux/amd64) or on ubuntu / Python 3.12.

The work ran in detached worktrees under `scratchpad/lens-AP3-r1-fresh-attack/`, at `5440295` (`new`, `mut`) and at `78ae8dc` (`old`), with `PYTHONPATH` forced to each tree's `src`. Each import was proved: `proofpack.__file__` printed `...\lens-AP3-r1-fresh-attack\new\src\proofpack\__init__.py`, and the matching path for `old` and `mut`.

Nothing was committed, pushed, tagged, downloaded or installed. I ran `gh run view 36005620750` and `gh run list` read-only.

**Why this note has a different file name.** The path I was given, `handoffs/2026-09-24_A_ap3_lens1_fresh-attack.md`, already holds the committed round-1 lens note (from `a09a0ef`, the lens at `1a967d8`). My first write replaced that file in the working tree. I restored it with `git checkout --`, and this note is written to `2026-09-24_A_ap3_r3_lens1_fresh-attack.md` instead.

## Re-run (in `new` at `5440295`, `PYTHONPATH` forced)

| Command | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1554 passed, 2 skipped, 1 xfailed in 147.20s` |
| `-m ap3` / `-m ap2` / `-m day8` | `140 passed` / `89 passed` / `468 passed, 1 skipped` |
| `python -m ruff check .` / `python -m ruff format --check .` | `All checks passed!` / `225 files already formatted` |
| `python scripts/mutation_sweep.py --marker ap3` | `29 planted, 29 killed, 0 survived; 363 s` |
| `tests/test_ap3_repair3.py`, copied into `old` (`78ae8dc`) | `11 failed in 2.47s` (all 11) |

The suite has one skip more than the repair note's figure (`1555 passed, 1 skipped`). That skip is `tests/test_e8_repair4.py:405`, "full confusables.txt not present at ...\lens-AP3-r1-fresh-attack\workflows\data\confusables-18.0.0.txt". The test looks for that file relative to the tree's parent directory, so the extra skip comes from where my worktree sits, not from the code. The `day8` figure of `468 + 1 skipped` has the same cause.

## Blockers

None.

## Non-blocking (record and carry)

**N1. `--check` now accepts a hand-edited oracle that `78ae8dc` rejected, and `proofpack fixtures` reads it as matched.**

`compare()` checks every captured value against D1 section 9's cross-platform tolerance (1e-9 / 1e-6). It does this even when the fresh capture comes from the same platform and library versions as the committed file. On this machine that is `win-amd64 cp314` on both sides, and all 65 values come out identical.

Evidence, from a copy of `fixtures/oracles_v1.json` with `F1d-clopper-pearson.cp_hi` changed from `1.0` to `1.0000009`:

- At `5440295`: `captured.F1d-clopper-pearson.values.cp_hi: committed 1.0000009 fresh 1.0 abs difference 9.000e-07 iterative tolerance 1e-06 within`, `exit(5440295)=0`.
- The same value at `78ae8dc`: `exit(78ae8dc, same doctored value)=1`.
- `fx.run_fixtures` with that file gives `F1d-clopper-pearson matched [('cp_hi', 1.0000009, 1.0, True), ...]`, summary `not_matched: 0`, `exit_code 0`.

A second input moved all 18 iterative values by +9.9e-7 at once, which included `F1c cp_lo` 0.0 → 9.9e-07 and `F1d cp_hi` 1.0 → 1.00000099. The result was `ok=True`, `47 identical, 18 differ within their tolerance, 0 differ outside it`.

`tests/test_fixtures_cmd.py::test_the_committed_oracles_equal_a_fresh_capture` passes with either file. This is not the blocker class "a not-matched fixture counted as matched": the row is within tolerance of the oracle it was given. What changed is that the check guarding that oracle file is looser.

- **Repro:** set `cp_hi` of `F1d-clopper-pearson` to `1.0000009` in a copy, then run `PYTHONPATH=<wt>/src python scripts/capture_fixture_oracles.py --check --committed <copy>` and read the exit code: 0.
- **Suggested repair:** compare exactly when `captured_on_platform` and `library_versions` equal the fresh capture's, and apply the tolerance only when they differ.

**N2 (sentence violation). The test name `test_the_committed_oracles_equal_a_fresh_capture` is now false.**

The test body is unchanged, but through `--check` it now passes when values differ. N1 shows it passing with 1 value changed and with 18 changed. The name should say what the test inspects, for example "within the D1 section 9 tolerance of a fresh capture".

- **Repro:** as in N1. The test passes on a file that is not equal to a fresh capture.

**N3 (sentence violation). The new `tests/test_wheel_fixtures.py` docstring says: "The test is skipped only when the interpreter running pytest cannot import one of RUNTIME_MODULES itself, and the skip names it."**

This is false. `_build_wheel` (from `tests/test_render_theme.py:188`) skips with "no wheel builder available in this environment" before `dependency_paths()` is ever reached.

Counter-example, which I ran:

- Setup: `PYTHONUSERBASE=<empty dir, no uv.exe>`, `PIP_NO_INDEX=1`, `PATH=/usr/bin:/c/Windows/System32`, and `PYTHONPATH=<new>\src;<real user site>`.
- Command: `pytest tests/test_wheel_fixtures.py -rs`.
- Output: `ERROR: No matching distribution found for hatchling ... 1 skipped in 1.70s`.

Every one of the 14 `RUNTIME_MODULES` imported in that environment.

- **Repro:** the command above.

**N4 (sentence violation). Three shipped sentences say `docker build` has never run. It ran in run 36005620750.**

Evidence from `gh run view 36005620750`: `✓ Run docker build --platform linux/amd64 -t proofpack:ci .`. The log shows `#11 naming to docker.io/library/proofpack:ci done` and pip `Successfully installed attrs-26.1.0 ... numpy-2.5.3 ...`.

The three sentences:

- `Dockerfile:14`: "docker build has never run with it". Repair 3 rewrote lines 5-7 of the same comment block to cite run 36005620750 and left this line in place.
- `.dockerignore:2`: "docker build has never run".
- `.github/workflows/ci.yml:122` (`docker-smoke` header): "Written on 24 September 2026; it has not run anywhere yet." The checkout, wheel, export and build steps ran in 36005620750.

- **Repro:** `grep -n "never run\|not run anywhere" Dockerfile .dockerignore .github/workflows/ci.yml`, then `gh run view 36005620750`.

**N5 (sentence violation, minor). `.github/dependabot.yml` still carries "[unverified] the "uv" ecosystem (it reads and rewrites uv.lock) was not read ..." and "Dependabot reads it once the file is on the default branch".**

After the push, Dependabot opened branches `dependabot/uv/ruff-0.16.8`, `dependabot/uv/hypothesis-6.168.0` and `dependabot/uv/scikit-learn-1.9.1`, visible in `gh run list`. The behaviour is now observed rather than unverified. This is not changed by the diff. I record it because the sentence now misdescribes what has been seen.

**N6 (surviving mutants: `compare()` in `scripts/capture_fixture_oracles.py`).** Three non-equivalent mutants survive `-m ap3` (`140 passed` each):

- `entry_symdiff_ignored`: `ok = False` removed from the loop over `set(ca) ^ set(cb)`. With this mutant, a captured entry present in only one of the two files passes the check. My probe of the unmutated code, with entry `F2-exact` deleted, gave `ok=False`, `captured.F2-exact: present in the fresh capture only`. No test feeds that input.
- `no_class_passes`: `ok = False` removed in the `cls is None` branch. With this mutant, a captured entry that has no `CAPTURED_CLASS` passes. `test_the_check_classes_are_the_fixtures_rows_classes` only inspects the committed file's entries.
- `toplevel_only_committed_keys`: the top-level loop iterates `set(a)` instead of `set(a) | set(b)`. With this mutant, a top-level key present only in the fresh capture is not reported.

- **Repro:** `python <scratch>/probe/mut.py <wt> entry_symdiff_ignored`. The runner is in the lens scratch directory; the same replacement, made by hand and followed by `pytest -m ap3`, gives the same result.

**N7 (surviving mutants: the CI-1 workflow step).** No test reads the new `ci.yml` step `oracle capture compared with fixtures/oracles_v1.json`:

- `ci_oracle_step_removed`, which deletes the step, survives.
- `ci_oracle_step_no_if`, which drops `if: ${{ !cancelled() }}`, survives.

That step is the whole point of CI-1's diagnosis: the lines it prints are what tells the orchestrator which value moves on ubuntu/3.12.

**N8 (surviving mutant: CI-2, `runtime_modules_drop_numpy`).** Deleting `"numpy"` from `RUNTIME_MODULES` survives here. On this machine all 14 modules live in one directory, so the numpy directory is still on `PYTHONPATH` through scipy. The mutant is equivalent on this layout and not equivalent where numpy is installed apart from the others.

`wheel_probe_no_dep_import` also survives. It drops the 14-module import from the probe. I grade it equivalent in effect: the fixtures run in the same venv would still fail on a missing module, at a later assert.

**N9 (record). Dependabot's scikit-learn 1.9.0 → 1.9.1 PR will fail `--check` because the version appears in the `source` string.**

`captured.F3-auroc.source` is `"scikit-learn 1.9.0 roc_auc_score"`, and `source` is compared for equality. Each statsmodels, scipy or scikit-learn bump therefore needs a recapture. Repair 3's open question (a Windows capture or a reference-platform capture) then decides which machine that recapture is made on.

The `python:3.12-slim` → `3.14-slim` Dependabot bump would change D1 section 9's reference platform, as the repair note says. I also checked the grep in the digest step: it names `python:3\.12-slim` literally and exits 1 on a log without that reference (`rc(empty log)=1`).

## What I could not break (what I tried)

**CI-1 `compare()`.** Each input below is a copy of the committed file compared with a fresh capture on this machine:

| Input | Result |
|---|---|
| unchanged | `True`, `65 identical` |
| `wilson_lo` +1 ulp | `within`, `True` |
| `wilson_lo` +0.999e-9 | `within`, `True` |
| `wilson_lo` +1e-9 | `abs difference 1.000e-09 ... OUTSIDE`, `False` (the float sum lands just above 1e-9) |
| `wilson_lo` +2e-9 | `OUTSIDE`, `False` |
| `paired_p` +1e-6 | `OUTSIDE`, `False` |
| `paired_p` +2e-6 | `OUTSIDE`, `False` |
| `wilson_lo` = NaN | `abs difference nan ... OUTSIDE`, `False` |
| `wilson_lo` as a str | `not a number`, `False` |
| entry `F2-exact` deleted | `False` |
| one `F2-exact` value deleted | `captured.F2-exact.values.dor: present in the fresh capture only`, `False` |
| extra top-level key | `False` |
| `register_decimals` deleted | `False` |
| `F3-delong.kind` changed | `False` |
| `captured_on_platform` and `library_versions` deleted | `True`. They are recorded, not compared. `test_ci1_the_committed_file_names_the_platform_it_was_captured_on` pins the key on the real file. |

A fresh `--check` at `5440295` gave `65 identical, 0 differ within their tolerance, 0 differ outside it`. That supports the note's statement that the recapture changed no value.

**CI-2.** I re-created CI's layout, with the dependencies reachable only through `PYTHONPATH` and not through the user site:

- Setup: `PYTHONUSERBASE=<scratch userbase holding only uv.exe>`, `PIP_NO_INDEX=1`, `UV_OFFLINE=1`, `PYTHONPATH=<new>\src;C:\Users\joshs\AppData\Roaming\Python\Python314\site-packages`.
- In that shell, `site.getusersitepackages()` printed the scratch directory and numpy imported from the real user site.
- `pytest tests/test_wheel_fixtures.py`: `1 passed in 4.84s`.

**CI-3.** I ran the step's own command, `grep -o -m1 -E 'docker\.io/library/python:3\.12-slim@sha256:[0-9a-f]{64}'`:

- On the saved `--log-failed` text of run 36005620750, it printed `docker.io/library/python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9`, rc 0.
- On a one-line log without that reference, it gave rc 1.
- `.dockerignore` (`*` plus two admits) keeps `docker-build.log`, which `tee` writes into the build context, out of the COPY inputs.

**Egress.** A `sitecustomize.py` replaced `socket.socket`, `socket.create_connection` and `socket.getaddrinfo` with a function that prints `LENS: socket attempt` and raises. I counted `LENS` lines from these runs:

| Run | `LENS` lines | Exit / result |
|---|---|---|
| `proofpack fixtures --offline` | 0 | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0 |
| `proofpack fixtures` without `--offline` | 0 | exit 0 |
| `capture_fixture_oracles.py --check` | 0 | not recorded |
| `scripts/f17_determinism.py --n 1000` | none printed | `identical under the mask ['run_id', 'started', 'duration_s']: yes`, exit codes `[4, 4]` |

The new ci.yml step runs `capture_fixture_oracles.py`, which imports no `proofpack` and makes no `proofpack run` call.

**F17.** Flipping one byte of `run2/ingest_report.json` turned `compare()` from `True` to `{'identical': False}`.

**SBOM.** Two runs of `scripts/sbom.py` were byte-identical (`cmp`), with SHA-256 prefix `e5c13c67928b10d8`. The SBOM lists 62 components, and uv.lock has 62 packages excluding proofpack. No package is missing or extra by (name, version), and every purl starts `pkg:pypi/`.

**T12, built from the report above:**

- It contains "This record supports, does not replace, the manufacturer's own validation."
- It contains 6 × "not for implementation".
- Grep counts in the report: `validated`, `compliant`, `certified`, `approved`, `CSA-compliant` and `passed validation` are all 0.
- `qualified` occurs 4 times, all in "the manufacturer's qualified statistician".
- The markings `[unverified against the primary PDF]` and `[unverified until captured]` (×2) are present.
- In a report I edited:
  - `<script>` in `platform` and in a row's `reason` rendered as `&lt;script&gt;` (0 raw `<script>`).
  - U+202E rendered as `&#x202e;`, the design `render/html.py:29-35` documents.
  - A row forced to `not_matched` rendered `data-status="not_matched">not matched`.

**Workflows.** Repair 3 adds no secret, `pull_request_target`, permission or action pin. `ci.yml` remains `permissions: contents: read`.

## What I could not check

- **Whether the three fixes pass on GitHub Actions** (ubuntu, Python 3.12, numpy 2.5.3). The next CI run is the first place any of them executes, and this lens did not push or re-run anything.
- **Which captured value moves on ubuntu/3.12, and whether it is within its class.**
- **Whether `docker-smoke` passes its later steps** (doctor, fixtures, run exit 4, F17 at 5,000 rows in the image). They have never run.
- **Anything on the reference platform.** No image was pulled.

## Sentences refused

- "`--check` catches a hand-edited oracle": refused, because N1 is a counter-example.
- "The wheel test now passes on CI": refused, because it has not run there. What was measured is a Windows emulation of CI's layout.
- "The digest step prints the base digest": refused. The grep was run on the saved log text, not inside a job.
