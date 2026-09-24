# A-P3 lens 1, fresh attack: build day 9, lane A at `1a967d8` (branch `a-p3-release`)

Written 24 September 2026 by a cold fresh-attack lens session. Nothing was committed or pushed. Every figure below was measured in this session on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1), Git Bash, in detached worktrees at `1a967d8` (and one at `e17a510`) under the session scratchpad, with `PYTHONPATH=<worktree>/src` and `proofpack.__file__` printed inside the worktree first. Nothing was measured on the reference platform (`python:3.12-slim` linux/amd64). No image was built or pulled, nothing was installed from an index, no workflow ran.

## Verdict: FAIL

One blocker, graded by the rule in the lens brief (a surviving non-equivalent mutant that reopens a blocker class). The shipped comparison code is correct on every input I fed it; what fails is that no test holds the line for a row whose engine value is missing.

## Blocker

**FA-B1. A mutant that counts a missing engine value as within tolerance survives the full suite, and under it `proofpack fixtures` reports a not-matched row as matched and exits 0.**

- Mutant: in `src/proofpack/fixtures.py::compare_row`, `within = False` (the branch for `engine_value is None or not math.isfinite(...)`) replaced by `within = True`.
- Full suite under the mutant: `1462 passed, 2 skipped, 1 xfailed in 121.88s`. `-m ap3` under the mutant: `57 passed`.
- Under the mutant, the CLI with F8's adapter changed to leave out `half_width_n50`: `rc 0 matched True [('half_width_n100', 0.0595..., True), ('half_width_n300', 0.0341..., True), ('half_width_n50', None, True)]`; summary `matched 30`; the report validates and is written.
- Unmutated, the same input gives `not matched: F8-half-width (outside tolerance: half_width_n50)` and `not matched: F8-register (...)`, `matched 28, not matched 2`.
- Repro: `sed`-replace that line in a scratch copy, then `PYTHONPATH=<copy>/src python -m pytest -q -p no:cacheprovider` (green); the CLI demonstration is `fx._f8 = lambda: {k: v for k, v in orig().items() if k != "half_width_n50"}` then `main(["fixtures","--offline","--out",D])`.
- Repair: a test that feeds a row whose engine function omits one key, and another whose engine returns one NaN, and asserts `not_matched` and exit 6. It must fail against the mutant above. (The NaN case also needs FA-R2 fixed first, or the command exits 5.)

## Non-blocking (record and carry)

**FA-R1. `git_sha` records the customer's repository as the engine's commit.** `git_sha()` goes three parents up from `fixtures.py` and runs `git rev-parse HEAD` there when it finds `.git` and `pyproject.toml`. I installed the wheel with `pip --no-deps --no-index --target vendor` inside a fresh git repository (HEAD `981daf7f1c3f...`, one `pyproject.toml`). `fixtures --offline` wrote `0.1.0.dev1 981daf7f1c3ffdff04e55ed109b4ebb61fda7624 git rev-parse HEAD in the package's checkout (tracked files unmodified)`. T12 prints the same value in its "Git commit" row. The sentence "the package's checkout" is false there. Repro: `git init X; commit X/pyproject.toml; pip install --target X/vendor <wheel>; PYTHONNOUSERSITE=1 PYTHONPATH=X/vendor;<deps> python -m proofpack.cli fixtures --offline --out D`.

**FA-R2. `proofpack fixtures` can raise, the report is not always written, and a not-matched row's deviation can read as smaller than it is.**
- If an engine value is NaN (F8 `ci_lo` at n=50 planted NaN), the command prints `internal error: ValueError: Out of range float values are not JSON compliant: nan`, exits 5 and writes no `fixtures_report.json`.
- If one oracle entry is deleted (`captured.F1-wilson` removed from `oracles_v1.json`), it prints `internal error: KeyError: 'F1-wilson'` and exits 5.
- If `f4_expected.json` is removed, it prints `internal error: FileNotFoundError: packaged resource 'f4_expected.json' not found` and exits 5.
- None of these counts as matched: the exit is non-zero and no report is written.
- Three sentences are false: `compare_row`'s "Never raises", the comment "a row reports, never raises", and `render/t12.py`'s "the report itself is always written, D1 section 7".
- The row built in memory has `max_abs_deviation` 1.11e-16, the largest over the values that did compare. T12's "Largest deviation" cell prints `1.11e-16` beside "not matched", so the caption "deviations are the largest absolute difference between engine and oracle values in the row" is false for that row.

**FA-R3. T12's doctor table prints "Condition held: yes" for conditions that are not held.** The report's `ok: true` is relabelled "Condition held". On this machine the rendered page reads:
- `reference platform yes no windows-amd64-cp314 (reference is linux-x86_64-cp312; ...)`
- `network yes no skipped (--offline)`
- `docx extra yes no not installed - HTML/JSON only`

The caption says `0 with the condition not held`. Repro: `python scripts/build_t12.py --report <a report from this machine> --out D` and read `<table class="doctor">`.

**FA-R4. T12 says "Each code below is raised by the engine itself (`proofpack/errors.py`)" and lists H10, which nothing raises.** `gates.gate_h10` emits `W10`. No `.py` file under `src/proofpack` outside `errors.py` names `"H10"`. It is the only code in the four tables with no user (checked by a regex over `src/proofpack/**/*.py`, render excluded).

**FA-R5. `release.yml`'s header sentence is false: "tests/test_workflows.py asserts it on every line that runs the engine".** I added each of these lines as one extra `run:` step to the parsed `release.yml` and called `offline_violations`. It missed all seven. Every one of them runs the engine without `--offline`:
- `echo start && proofpack run --input a --criteria b` (the test skips any line beginning with `echo `);
- `proofpack run --input a && proofpack fixtures --offline --out x`;
- `proofpack run --input a; echo --offline`;
- `docker run --rm "${IMAGE}:${GITHUB_REF_NAME}" run --input a`;
- `docker run --rm proofpack:latest run --input a`;
- `PP=proofpack; $PP run --input a`;
- a `uses: docker://ghcr.io/x/proofpack:ci` step with `with: args: run --input a`.

The same header states "TestPyPI is reached by trusted publishing" as a fact about a job that has never run. I read every line of the current `ci.yml` and `release.yml` by hand, and every engine command there carries `--offline`: the brief's blocker is not present in the files as written.

**FA-R6. `tests/test_dockerfile.py` passes four planted lines that it does not inspect.** The current Dockerfile contains none of them (read line by line):
- `RUN python -c "import urllib.request as u; u.urlretrieve('https://example.org/x', '/tmp/x')"`;
- `RUN python -m pip install requests` (unhashed, from an index);
- `ENV PROOFPACK_SIGNING_SEED=deadbeef`;
- `COPY signing.txt /tmp/`.

A fifth, `ADD --chmod=644 https://...`, was caught.

**FA-R7. Tolerance sentences cite D1 section 9 for classes it does not state.**
- The `reported_rounding` rule reads "(D1 section 9, bootstrap intervals and published tables)". D1 section 9 states reported rounding for "bootstrap CIs" only, and F14's Newcombe table carries that citation.
- The Clopper-Pearson rows read "absolute deviation at most 1e-6 (D1 section 9, iterative)". D1 section 9's iterative list is "IRLS slope/intercept, DeLong via placements".
- `tolerance_policy.source` is "D1 section 9" beside the `register` class, which comes from D1 section 3.2.

**FA-R8. The report schema, and so `scripts/build_t12.py`, accepts reports that contradict themselves.** All four of these validated. T12 renders from the file as given:
- a row with `status: matched`, `matched: true` and one value with `within: false`, `abs_deviation: 1.0` (T12 would print "matched");
- `summary.matched` 43 against rows that say otherwise;
- `exit_code` 0 with a `not_matched` row;
- F14's `unverified` set false and `marking` null.

The engine never writes such a file. Only a hand-edited report reaches this path.

**FA-R9. Surviving mutants beyond FA-B1.** Each was run against the full suite, with the result recorded as `1462 passed, 2 skipped, 1 xfailed` unless stated:
- L1 `out["matched"] = all_in` (a row with an empty oracle `values` dict is matched). Demonstrated: `matched True exit 0`. Not graded blocker: an emptied oracle in a checkout fails `test_the_committed_oracles_equal_a_fresh_capture` (I measured `capture_fixture_oracles.py --check` exit 1 on a register edit).
- L2: exit code ignores `not_matched` rows of class `register`. Demonstrated with register `F8.half_width_n50` +1e-3: row not matched, exit 0. Equivalent under the current register: every register value is also compared in a captured row with a tighter tolerance, so a register-only mismatch would need the register itself to move.
- L5: F17 `identical` compares `run.json` only (a `pseudonyms.json` or `ingest_report.json` difference passes).
- L6: `f17_determinism.py` `main` returns 0 when the runs differ. The `docker-smoke` step relies on this exit code.
- L8: the SBOM drops the sdist hashes.
- L14: `release.yml`'s fixtures step `|| true`. The step name says "exit 0 only when no row with an oracle is not matched".
- L13, run against `-m ap3` only (`57 passed`): `git_sha` reports "tracked files unmodified" for a dirty tree.

**FA-R10. Supply chain in `release.yml`, [unverified] where marked.**
- `pypa/gh-action-pypi-publish@release/v1` is a branch.
- `actions/*@v4`, `astral-sh/setup-uv@v6` and `aquasecurity/trivy-action@0.28.0` (already [unverified]) are movable tags. `ghcr.io/zaproxy/zaproxy:stable` is unpinned (marked).
- `install-from-testpypi` uses `--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/`. A same-named package on either index at a higher or equal version (numpy, jsonschema, or `proofpack` itself) is eligible for install and runs in that job. [unverified] whether any of these names is held by someone else on TestPyPI or PyPI: I did not fetch either index. The job has `contents: read` and no secret.

**FA-R11. Deleting `.github/dependabot.yml` leaves the full suite green: `1461 passed, 3 skipped, 1 xfailed`.** The skip reasons in `tests/test_workflows.py` ("no release.yml here (the mutation sweep's copy)") and `tests/test_dockerfile.py` describe a copy that no longer lacks those files. `COPIED` now includes `.github` and `Dockerfile`. Deleting the Dockerfile as well is caught, but only by `tests/test_sweep_day9.py::test_every_declared_mutant_of_every_day_still_matches_its_file` (the ap3 Dockerfile mutants stop matching). The Dockerfile tests themselves skip.

**FA-R12. [unverified, predicted from the code] `tests/test_wheel_fixtures.py` will skip in GitHub Actions.** It puts the runtime dependencies on `PYTHONPATH` from `site.getusersitepackages()` and skips on "No module named". Under `uv sync` in CI, that directory holds no numpy. So the clean-venv install-then-run has no CI check except the never-run `install-from-testpypi` job.

**FA-R13. Two docstrings and the build note contain sentences I found false.**
- `tests/test_fixtures_cmd.py` says `clopper_pearson_bounds` returning None "makes the three interior Clopper-Pearson rows not matched". There are two interior cases (F1, F1b), and the test asserts four rows.
- `fixtures.py` says "The command imports no network module". After `fixtures --offline --html`, `socket` and `urllib.parse` are in `sys.modules` (via `numpy.testing` -> `platform.uname`; no connection was attempted).
- The build note says "A-P2's `offline-namespace` has not run either". The orchestrator records run 35911876338 green on 23 September. I did not read that run.

## What I could not break (what I tried)

- **Sockets.** I ran `fixtures` (`--offline`, no flag, `--offline --html --r-captures`) under a `sys.addaudithook` that raises on every `socket.*` event. I did the same for F17 (both child runs inherit the hook) and `build_sample_pack.py`, and for `fixtures` from the wheel in a fresh venv outside the tree. The hook logged no connect, getaddrinfo or socket creation. The one event was `socket.gethostname` from `numpy.testing` -> `platform.uname`, which is local. Its value is not in the report (grep 0).
- **Tolerance edges on `F1-wilson.wilson_lo`.** My Wilson (1927) formula equals the engine and the oracle to 0.0.
  - Oracle moved by 1 ulp: dev 5.55e-17, matched, exit 0.
  - Oracle moved by +1e-9: dev 1.0000000272e-9, not matched, exit 6.
  - Oracle moved by +2e-9 and by -2e-9: dev 1.9999999989e-9, not matched, exit 6.
  - The report's `max_abs_deviation` equals my computed deviation in every case.
- **Oracles against published formulae, without repo code.**
  - Wilson for F1-F1d, worst deviation 2.2e-16.
  - Clopper-Pearson via `scipy.stats.beta.ppf`, worst 5.6e-17.
  - DeLong (1988) structural components for F3: SE s1 0.154919..., paired var 0.0072, z 1.885618..., p 0.059346..., logit and Wald bounds. Every deviation is 0 or 4e-17.
  - F6 chi-square 4.632727..., p 0.098632..., deviation 0.
- **F17.** I ran the script myself (5,000 rows, exit codes [4, 4], 3.2 s): a line diff of `run.json` differs in `duration_s`, `run_id` and `started` only, `pseudonyms.json` in `run_id` only, `ingest_report.json` in nothing. The run directory holds exactly those three files. I flipped one byte in the body of `run.json`, one in `pseudonyms.json` and one in `ingest_report.json`: each made `identical` false in the matching check.
- **T12 injection.** I put `<script>alert(1)</script>` + U+202E + U+2066 into the report's doctor info, platform, `git_sha_source`, a row's `reason` and `what_is_compared`, and F14's marking, then rendered with `build_t12.py`. The page had 0 raw `<script>alert`, 7 escaped, 0 U+202E, 0 U+2066 (`&#x202e;`). The intended-use slot has no input path in this version.
- **T12 wording and anchors.**
  - "This record supports, does not replace, the manufacturer's own validation." is present verbatim.
  - No checkbox or tick mark (0 hits for checked/☑/✓/✔).
  - The FDA anchor carries "draft guidance (January 2025), not for implementation" in the margin note and the table.
  - Forbidden-word grep: validated, compliant, certified, approved, meets and pass have 0 hits in page text. "qualified" and "endorsed" appear only in the verbatim D4 footer and cover note. "validation" appears in the supports sentence and the anchor id.
- **SBOM.** 63 `[[package]]` in `uv.lock`, no duplicate names, 0 missing from the SBOM by (name, version). Two runs are byte-identical, and `SOURCE_DATE_EPOCH=0` gives `1970-01-01T00:00:00Z`.
- **Wheel.** Built with `python -m uv build --wheel --offline` from cache (80 entries). It contains the three `_fixtures` files and the schema but no `newcombe_table2.json`, and no entry contains `PRIVATE KEY`, `BEGIN OPENSSH` or `SIGNING_KEY=`. From a fresh venv: `rows 43: matched 29, not matched 0, no oracle recorded 3`, exit 0, `git_sha` null.
- **Regression at `e17a510`.** I copied the nine new or changed test files and `1a967d8`'s `pyproject.toml` onto `e17a510`. Four modules fail to collect and six tests fail. `test_every_engine_run_in_a_workflow_carries_offline[ci.yml]` passes there, legitimately: the older `ci.yml` was already offline. 18 tests skip.
- **Committed sweep.** `python scripts/mutation_sweep.py --marker ap3`: `12 planted, 12 killed, 0 survived; 156 s`.

## Re-run figures (Git Bash, lens worktree at `1a967d8`)

| Command | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1462 passed, 2 skipped, 1 xfailed in 165.26s` (second skip: `test_e8_repair4.py:405`, confusables file located relative to the tree) |
| `-m ap3` / `-m ap2` / `-m day8` / `-m day9` | `57 passed` / `89 passed` / `468 passed, 1 skipped` / `207 passed` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `205 files already formatted` |
| `fixtures --offline --out D` | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0, `duration_s` 1.038 |

## What I could not check

- **The reference platform and every workflow job.** None has run: `docker-smoke`, `build`, `image`, Trivy, `testpypi`, `install-from-testpypi`, `github-release`, `zap-baseline`. I could not check the base image digest, whether the action tags exist, or whether Dependabot accepts the `uv` ecosystem.
- **The CycloneDX 1.5 schema.** It was not fetched.
- **Package names on TestPyPI and PyPI.** I could not check who holds `proofpack` or its dependency names there.
- **CI run 35911876338.**
- **PowerShell.** I did not repeat any figure in PowerShell 5.1.

## Sentences I refused to write

- "Every engine run in the workflows is offline": I read every line of the two files and found none without `--offline`. The test inspects only what its regex matches (FA-R5).
- "No key material can enter the image": the Dockerfile as written copies two inputs, and the test misses planted lines (FA-R6).
- "The fixtures command never makes a network call": I measured seven invocations under the hook and prove nothing beyond them.
