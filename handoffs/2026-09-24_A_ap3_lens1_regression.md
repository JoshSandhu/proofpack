# Lens 1 (regression and record): build day 9, lane A (A-P3) at `1a967d8`, 24 September 2026

**Verdict: FAIL.** There are two blockers. Both are sentences in shipped text that a run contradicts. Every suite figure, command and measured number in the build note re-measured, in Git Bash and in PowerShell 5.1.

- **RG-B1.** T12's failure-mode table says a W16 run ends with "exit 2 unless another code sets it". The engine's own test asserts exit 0 with W16 printed. T12's "exit 0" row also says "no warning".
- **RG-B2.** The header of `release.yml` says `tests/test_workflows.py` "asserts it on every line that runs the engine". I planted an engine run with no `--offline` and all ten tests in that file passed. The build note refused this same sentence ("Every engine run in the workflows is offline"), yet the workflow file carries it.

All figures below are my own. They were measured on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1). None comes from the reference platform: nothing was built, pulled or pushed. Worktrees were under `scratchpad/lens-AP3-r1-regression/`:

- `wt-new` at `1a967d8`;
- `wt-old` at `e17a510`;
- `wt-mut` at `1a967d8`, for mutations;
- `wt-merge` at `f72a9af`, for a trial merge.

`PYTHONPATH` was forced in each worktree. `python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` in both shells. All four worktrees are removed.

## Blockers

### RG-B1: T12 states the wrong exit behaviour for W16, in the regulator-facing failure-mode table

The golden `tests/fixtures/golden/T12.html` line 176, verbatim:

```
<tr data-code="W16"><td class="mono">W16</td><td>telemetry not sent; run.json and the exit code are unchanged</td><td>warning: the run completes; exit 2 unless another code sets it</td>...
```

The row contradicts itself. Its second cell comes from `errors.WARN_CODES` and says the exit code is unchanged. Its third cell is `render/t12.py`'s blanket `WARN_CODES` text and says exit 2.

The engine's own test sides with the second cell. `tests/test_telemetry.py::test_a_302_through_the_cli_prints_w16_and_the_location_host_receives_nothing` asserts `rc == EXIT_OK` with a `[W16]` line printed; `errors.py`'s `FLAG_ONLY_CODES` comment says the same. At `1a967d8` that test passed (1 passed, 1.79 s).

T12's exit-code rows state that exit 0 means "no HALT, no warning, a usable licence", which is also false for a W16 run.

`tests/test_t12.py::test_the_failure_mode_table_lists_every_engine_code` checks that the codes are present. It does not inspect the "Engine action" column. This column is a statement about engine behaviour on the page the RA lead signs against.

Repro: `PYTHONPATH=<wt>/src python -c "from proofpack.render import t12; print([r['does'] for r in t12.failure_mode_rows() if r['code']=='W16'])"`, then `pytest "tests/test_telemetry.py::test_a_302_through_the_cli_prints_w16_and_the_location_host_receives_nothing"`.

Suggested fix: take each code's action from `FLAG_ONLY_CODES` or a per-code table, not from its dict of origin. Add a test that fails on the old W16 row.

### RG-B2: `release.yml`'s header says the workflow test covers "every line that runs the engine"; it does not

`.github/workflows/release.yml` lines 4-5, verbatim:

```
# ... Every engine command below carries --offline
# (tests/test_workflows.py asserts it on every line that runs the engine).
```

The test inspects only the lines its `ENGINE_CALL` regex matches: `proofpack[:ci] <sub>` and `proofpack.cli <sub>`. In `wt-mut` I added this step to `release.yml`'s `build` job:

```
run: uv run python -c "from proofpack.cli import main; main(['run', '--input', 'a.csv', '--criteria', 'c.yaml', '--out', 'o'])"
```

The file still parsed. `python -m pytest tests/test_workflows.py` gave `10 passed in 0.31s`.

The committed file already has engine-running lines that the regex does not inspect:

- `uv run python scripts/build_sample_pack.py --out release/sample` runs `assemble_run`;
- the two `f17_determinism.py` calls run `proofpack.cli run`.

They happen to carry no telemetry today: the first has no telemetry path, and the second passes `--offline` internally (`test_the_f17_script_runs_the_engine_offline`). The sentence nonetheless states a guarantee over a class of lines. The build note lists it among its refused sentences, but it shipped in the workflow file.

Repro: add the step above to `release.yml` in a scratch tree, then `PYTHONPATH=<wt>/src python -m pytest -q tests/test_workflows.py` → 10 passed.

Suggested wording: "each line that `tests/test_workflows.py`'s `ENGINE_CALL` regex matches carries `--offline` (five in ci.yml, six here)".

## What re-measured (both shells unless noted)

| Check | Note | Lens, Git Bash | Lens, PowerShell 5.1 |
|---|---|---|---|
| Full suite at `1a967d8` | `1463 passed, 1 skipped, 1 xfailed` in `wt-ap3` | `1462 passed, 2 skipped, 1 xfailed in 168.95s` | `1462 passed, 2 skipped, 1 xfailed in 163.50s` |
| Full suite at `e17a510` | `1406 passed, 1 skipped, 1 xfailed` | `1405 passed, 2 skipped, 1 xfailed in 123.85s` | not run |
| `-m ap3` | 57 passed | `57 passed, 1408 deselected` | `57 passed` (clean re-run; see the self-inflicted note below) |
| `-m ap2` | 89 | 89 passed | 89 passed |
| `-m day8` | 469 | `468 passed, 1 skipped` | `468 passed, 1 skipped` |
| `-m day9` | 207 | 207 passed | 207 passed |
| ruff check / format | `All checks passed!` / `205 files already formatted` | the same | the same |
| `doctor --offline` | exit 0 | exit 0 | exit 0 |
| `fixtures --offline --out DIR --r-captures` | 43 rows: 30 / 0 / 2 / 6 / 5, exit 0 | same line, exit 0, 1.31 s (`time`) | same line, exit 0, 1.18 s (`Measure-Command`) |
| Report `rows` equal between shells | n/a | only `generated` and `duration_s` differ | the same |
| Report against `schema/fixtures_report_schema.json` | valid | `jsonschema.validate` passed | n/a |
| Largest deviation per class | 1.78e-15 F2-exact; 2.19e-9 F4-irls; 5.77e-5 F3-register; 3.21e-5 F14-newcombe | 1.7764e-15 F2-exact; 2.1908e-9 F4-irls; 5.7749e-5 F3-register; 3.2128e-5 F14-newcombe | n/a |
| Planted `captured.F1-wilson.wilson_lo` +2e-9 (file edited, CLI run) | not matched, exit 6 | exit 6; `not matched: F1-wilson (outside tolerance: wilson_lo)`; deviation 1.99999999895e-9 | n/a |
| Same cell, +5e-10 | matched, exit 0 | matched, deviation 4.99999986e-10, exit 0 | n/a |
| F17, `--n 5000` | four `equal`, exit codes [4, 4], 593,303 bytes, ledger [0, 0], egress sha different | two runs: four `equal` (0c4b77b7…, a8394939…, ca4e145e…, d306a3aa…), [4, 4], 593,303 bytes, ledger [0, 0], egress sha different, raw bytes different, exit 0, 3.19 s and 3.18 s | the same four hash prefixes, exit 0, 3.04 s |
| SBOM twice, then compare | 62 components (13 / 1 / 48); identical | identical (`cmp`) | identical; the PowerShell file equals the Git Bash file |
| SBOM vs `uv.lock` | every package | 62 locked (project excluded) = 62 in the SBOM; none missing, none extra; each purl is `pkg:pypi/<name>@<version>` | n/a |
| `capture_fixture_oracles.py --check` | exit 0 | exit 0 | exit 0 |
| T12 golden, `PROOFPACK_REGEN_GOLDEN=1 … -k golden` | regenerates | 1 passed; `cmp` against `HEAD:tests/fixtures/golden/T12.html` is silent (the `git status` M was CRLF only) | n/a |
| `mutation_sweep.py --marker ap3` | `12 planted, 12 killed, 0 survived; 127 s` | `12 planted, 12 killed, 0 survived; 155 s` (a trial-merge suite was running at the same time) | not run |
| Trial merge onto `f72a9af` | "Auto-merging scripts/mutation_sweep.py", `1467 passed, 2 skipped, 1 xfailed` | the same message; `1467 passed, 2 skipped, 1 xfailed in 152.32s` | n/a |

Notes on the table:

- **The one-test gaps.** The full-suite and `day8` figures differ from the note's by one: `tests/test_e8_repair4.py:405` looks for `../workflows/data/confusables-18.0.0.txt` relative to the tree, so it skips in my scratch worktrees and runs in `wt-ap3`. The note records this.
- **The failing PowerShell ap3 run was my doing.** The first PowerShell `-m ap3` gave `1 failed, 56 passed`. During that run I had planted a socket call in `wt-new`'s `cli.py` for a few seconds (below). A clean re-run gave 57 passed.
- **Tolerance and schema checks.** Every row: the D1 section 9 tolerances are 1e-9 and 1e-6. D1 line 160 does state "tolerance 1e-4 on the shown rounding", the basis for the `register` class. The report `exit_code` and `offline: true` are present.
- **Every F-numbered fixture has a row.** The report's fixture set is F1, F1b, F1c, F1d, F2 to F13, F13b and F14 to F21, each with at least one row. `tests/fixtures/` holds `claims_corpus`, `golden`, `item25_oe_block_a0c9abc.json` and `mapping`; there is no F-numbered file there. `fixtures/` holds `f4_calibration.csv`, `f4_expected.json`, `newcombe_table2.json` and `oracles_v1.json`.
- **`[unverified]` markings.** They are on F13 and F13b (reason `[unverified until captured] …`) and F14 (`oracle_source.marking` `[unverified against the primary PDF]`). The golden has no occurrences of `validated`, `certified`, `compliant` or `passed validation`. The report JSON has none either.
- **The day-9 wording in the golden.** The golden carries:
  - "supports, does not replace, the manufacturer's own validation" twice;
  - "claimed on the reference platform only";
  - one FDA anchor (`FDA_AIDSF_PERF_VALIDATION`) with the draft label.

## Pre-build (tests copied into `e17a510`)

Command: `pytest --continue-on-collection-errors` over the nine new or changed test files. Result: `7 failed, 1 passed, 17 skipped, 4 errors`.

- **Errors (4).** `test_f17_determinism.py`, `test_fixtures_cmd.py`, `test_sbom.py` and `test_t12.py` fail at collection, because the scripts and modules are absent.
- **Failed (7).** These are the ones the build should make fail:
  - `test_dockerignore_admits_the_lock_and_the_wheel_only`;
  - the sweep list test;
  - the wheel test;
  - `test_the_f17_script_runs_the_engine_offline`;
  - `test_no_secret_other_than_github_token`;
  - `test_ci_builds_the_image_without_pushing`;
  - `test_fixtures_offline_opens_no_socket`.
- **Passed (1).** `test_every_engine_run_in_a_workflow_carries_offline[ci.yml]`: it pins a property `ci.yml` already had (N2).
- **Skipped (17).** Eleven `test_dockerfile.py` tests skip on "no Dockerfile in this tree". Five `test_workflows.py` tests skip on "no release.yml here (the mutation sweep's copy)". The Dependabot test skips on "no dependabot.yml here". See N1.

## Nothing weakened

- **Tests.** `git diff --name-status e17a510 1a967d8 -- tests/`: nine A, one M (`test_offline.py`), no D. There are no deletions anywhere in the diff.
- **Statistics.** `git diff --name-status e17a510 1a967d8 -- src/proofpack/stats/` is empty.
- **Skips.**
  - No `xfail` and no `.only` were added. No marker was removed.
  - Skip or importorskip lines added: Dockerfile absent, sweep file absent, wheel dependencies not importable, `release.yml` absent, `dependabot.yml` absent, and `importorskip("statsmodels")` / `("sklearn")` in the oracle drift check. See N1.
- **Markers.** `ap3` is declared in `pyproject.toml`. `ci.yml` has no literal `ap3`: its day loop reads the markers from `pyproject.toml` and runs `-m day9`, which covers every ap3 test (build note Decision 10). The `pytest (all markers)` step runs the whole suite.

## Mutations I ran (in `wt-new`/`wt-mut`, each reverted)

| Mutation | Result |
|---|---|
| `release.yml` build: `uv run proofpack fixtures --out release` (without `--offline`) | 2 failed: the offline test for `release.yml` and the planted-line test |
| `ci.yml` docker-smoke: `… proofpack:ci doctor` (without `--offline`) | 2 failed: the offline test for `ci.yml` and `test_ci_builds_the_image_without_pushing` |
| `ci.yml` docker-smoke: the `run … --format json` line without `--offline` | 1 failed: the offline test for `ci.yml` |
| Dockerfile `FROM --platform=linux/amd64 python:3.12` | 1 failed: `test_the_base_image_is_python_3_12_slim_amd64_by_digest_or_marked_unverified` |
| `cmd_fixtures` opens `socket.create_connection(("127.0.0.1", 9))` when not `--offline` | `test_fixtures_offline_opens_no_socket` failed at `assert no_sockets.calls == []`. The docstring sentence "Opens no socket, with or without --offline" now has a counter-example that failed; the build note did not record one |
| An engine run through `python -c "…main(['run', …])"` added to `release.yml` without `--offline` | 10 passed (RG-B2) |
| Dockerfile deleted | `11 passed, 12 skipped`, 0 failed (N1) |
| `release.yml` deleted | 1 failed (`test_no_secret_other_than_github_token`, because GITHUB_TOKEN is then named nowhere); 6 skipped |

I parsed all three YAML files with `yaml.safe_load`:

- `ci.yml` jobs `test, offline-namespace, docker-smoke, audit, wheel, import-without-scipy`;
- `release.yml` jobs `build, image, testpypi, install-from-testpypi, github-release, zap-baseline`;
- `dependabot.yml` version 2.

## Non-blocking

- **N1. The suite stays green when a file under test is deleted.** With the Dockerfile deleted, `tests/test_dockerfile.py` (11) and the sweep test skip and nothing fails. With `release.yml` deleted, one test fails, and only because of GITHUB_TOKEN. The skip reason "(the mutation sweep's copy)" is stale: `COPIED` now includes `Dockerfile`, `.dockerignore`, `.github` and `uv.lock`. Replace the skips with failures.
- **N2. The `ci.yml` offline test passes on a tree without A-P3.** `test_every_engine_run_in_a_workflow_carries_offline[ci.yml]` passes at `e17a510`. It does pin the new docker-smoke lines at `1a967d8` (mutations 2 and 3 above).
- **N3. The `offline-namespace` job has run.** The note ("A-P2's `offline-namespace` has not run either") is stale, and so is the `tests/test_offline.py` docstring, which this diff rewrote ("it had not run anywhere … nothing here relies on it"). `gh run view 35911876338`: conclusion `success` at `eda8a35`; job "proofpack run inside unshare -rn (no network)" `success`.
  - A-P2 handoff "Tomorrow needs" item 4 asked that A-P3 read this result. It also said "the Docker image is where [the release-image network capture] would be built". The note does not mention the capture. docker-smoke runs `--network none` and records no capture. This remains open.
- **N4. `socket` is imported during a fixtures run.** The `fixtures.py` module docstring says "The command imports no network module". Measured: `socket` is in `sys.modules` after `run_fixtures(doctor=False)`. It is imported by `platform.uname()` from a library's `utils.py` (`IS_WASM = platform.machine() …`). No connection is opened: the socket mutation above is caught. Suggested wording: "opens no socket (`tests/test_offline.py::test_fixtures_offline_opens_no_socket`)".
- **N5. Two comments go beyond what their tests inspect.**
  - The Dockerfile says "No key material enters the image". The wheel carries `licence/keys.py`'s `SHIPPED_PUBLIC_KEY`, the Ed25519 verify key. The sentence means the signing key; say so.
  - `.dockerignore` says "the build context holds the two inputs … and nothing else (no source tree, no .git, no licence file, no key)". That describes Docker's behaviour, which has never been run here. The test inspects the lines of the file.
- **N6. Eleven register rows are labelled `"kind": "published_table"`, with `unverified: false`.** They are F1 to F1d, F2, F3 and F3-bootstrap, F4, F6, F8 and F9 `-register`/`-cluster-bootstrap`. D1 line 160 says those values were "computed there [R2 §9] with scipy 1.17.1 / statsmodels 0.15.0 / scikit-learn 1.8.0", and F9 is "hand-derived from F3 [decision]". Neither is a published table. `fixtures_report.json` is a release asset; a kind such as `design_register` would be accurate. F14 (Newcombe) is the only row in that kind with a published source, and it is marked.
- **N7. The release T12 would say "is the reference platform" when it is not** [unverified: never run]. The release `fixtures_report.json` and T12 are generated in the `build` job on `ubuntu-latest` with uv's Python 3.12, not inside `python:3.12-slim`. `platform_tag()` there would be `linux-x86_64-cp312`, which equals `REFERENCE_PLATFORM`. The report would then carry `on_reference_platform: true`, and T12 would print "is the reference platform". Generate the release report inside the image, or make the tag test tighter.
- **N8. The T12 footer describes a customer run.** The D4 7.1 verbatim footer says "from customer-supplied data and customer-declared criteria (author/date in Run Manifest)" and "Narrative sections are machine-drafted". T12 is built from ProofPack's own fixture register, with no customer data, no criteria and no narrative.
- **N9. The TestPyPI install cannot tell which index served `proofpack`** [unverified]. `install-from-testpypi` uses `--extra-index-url https://pypi.org/simple/` for `proofpack[stats]==<version>`. If a package of that name and version exists on PyPI, pip may install it. The `__file__` assertion only proves where the package was installed, not which index it came from.
- **N10. Brief items the note does not list as cut.** The brief names "T9 HTML" among the release assets; the note sends it to S4/E10, which is stated. The brief says "Pinned" base image, and the digest is `[unverified]`, which is stated. Nothing else in the brief is missing from the note.

## Merge notes checked

Against `main` at `f72a9af`, the only file changed on both sides since `e17a510` is `scripts/mutation_sweep.py`. The note names it, along with the files E9 may yet touch. `git merge-tree --write-tree main 1a967d8` exited 0.

## What I could not break (what I tried)

- **The mismatch path.** A planted 2e-9 on a 1e-9 cell gives not matched, exit 6, and the row is named. A planted 5e-10 stays matched.
- **The schema.** It refuses `matched: true` on a row without an oracle (the test does this, and it passed).
- **F17.** Four runs across two shells gave identical masked hashes, and the prefixes are identical between shells.
- **The SBOM.** Its bytes are identical across two runs and both shells, and it covers all 62 locked packages.
- **The T12 golden.** It regenerates byte-identically.
- **The offline and Dockerfile checks.** The removal of `--offline` from the three workflow lines I tried was caught. `python:3.12` in the Dockerfile was caught.
- **The fixtures socket test.** It catches a planted connection.
- **Scope.** No change under `stats/`.
- **The merge.** The trial merge's suite equals the note's figure.

## What I could not check

- **Everything that runs only in GitHub Actions.** That is the `docker-smoke`, `build`, `image`, `testpypi`, `install-from-testpypi`, `github-release` and `zap-baseline` jobs. It also covers Dependabot's `uv` ecosystem, the Trivy tag `0.28.0`, and the ZAP `-I` behaviour. All are written, never run.
- **The base image digest.** No pull was allowed.
- **The CycloneDX 1.5 JSON schema.** Not fetched.
- **The reference platform.** Every figure here is from `win-amd64-cp314`.
- **PowerShell runs of the sweep, the e17a510 suite and the pre-build copy.** Not run.
- **The wheel test.** `tests/test_wheel_fixtures.py` ran inside the suite; I did not repeat its `uv build` by hand.
