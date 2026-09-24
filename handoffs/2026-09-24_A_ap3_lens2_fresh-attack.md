# A-P3 lens 2, fresh attack: build day 9, lane A at `a09a0ef` (branch `a-p3-release`)

Written 24 September 2026 by a cold fresh-attack lens session. I committed nothing, pushed nothing, and made no tag. Every figure below was measured in this session on Windows 11, `win-amd64-cp314` (Python 3.14, Git Bash). I worked in detached worktrees under `scratchpad/lens-AP3-r2-fresh-attack/`:

- `wt-new` and `wt-probe` at `a09a0ef`;
- `wt-mut` at `a09a0ef`, for mutants;
- `wt-old` at `1a967d8`.

`PYTHONPATH` was forced to the worktree's `src`. I proved each import path with `python -c "import proofpack;print(proofpack.__file__)"`, which printed that worktree's `src\proofpack\__init__.py`. One early probe used a `;`-joined PYTHONPATH with `/c/...` paths and imported the main tree: `fixtures` was an "invalid choice" there. I discarded that probe and re-ran it with `C:/...` paths, with the import proved. Nothing was measured on the reference platform (`python:3.12-slim` linux/amd64). No image was built or pulled, nothing was installed from an index, and no workflow ran.

## Verdict: FAIL

There is one blocker, graded by the rule in the lens brief: a not-matched fixture counted as matched. Each lens-1 blocker (FA-B1, RG-B1, RG-B2) is closed, and I re-measured each closure.

## Blocker

**FA2-B1. Delete one value from an oracle entry and `proofpack fixtures` counts the row as matched, compares fewer values and exits 0. An engine value outside tolerance then goes unreported.**

The comparison set comes from the oracle's own keys:
- `fixtures.py:501`: `values = dict(entry["values"])` in `_captured`;
- line 179: `_register`;
- line 625: F14's `examples` loop;
- line 1042: `compare_row` iterates `for name in sorted(expected)`.

No row declares which value names it must compare. Repair 1's decision 1 makes a deleted *entry* `not_matched`, exit 6 (`oracle_error: KeyError`), on the ground that "those files ship in the wheel, so a missing one is a defect in the install". A deleted *value* inside an entry is the same defect, and it reads as matched. Measured results:

- **Installed wheel, one value deleted from each of two entries.** I built the wheel (`python -m uv build --wheel --offline`) and installed it with `pip --no-deps --no-index` into a fresh venv. `proofpack.__file__` was `...\p\v2\Lib\site-packages\proofpack\__init__.py`. I deleted `captured.F1-wilson.values.wilson_lo` and `captured.F2-exact.values.sensitivity` from that install's `_fixtures/oracles_v1.json`. Result: `rows 43: matched 29, not matched 0, no oracle recorded 3, ...`, exit 0. Rows: `('F1-wilson', 'matched', 1)` and `('F2-exact', 'matched', 16)`, where the intact file gives 2 and 17 values.
- **Engine value 1,000 times outside tolerance, oracle value deleted (source checkout, in process).** With `fx._f1_wilson` returning `wilson_lo + 1e-6` for 81/263:
  - with the oracle intact: `not_matched outside tolerance: wilson_lo`, exit 6, summary 29 / 1;
  - with `wilson_lo` deleted from the oracle: `matched 1 0.0 exit 0 summary {'matched': 30, 'not_matched': 0, ...}`.
  - F1-register does not catch it: its tolerance is 1e-4.
- **T12 rendered from that report** (`scripts/build_t12.py`): `F1-wilson | Wilson 95% interval of 81/263 ... | closed form: 1e-09 | 1 | 0 | matched`.
- **The same class elsewhere.** `register.F1.wilson_lo` deleted: `('F1-register', 'matched', 3)`. F14's `examples` cut to one: `('F14-newcombe', 'matched', 4)`. Both exit 0.

Why this is a blocker and not record-and-carry: the shipped engine is correct on every input I fed it, and in a source checkout `test_the_committed_oracles_equal_a_fresh_capture` / `capture_fixture_oracles.py --check` would catch the edited file. An installed wheel runs neither, and `proofpack fixtures` on an install is what the report and T12 are for.

Repro: `python -c "import json,sys;p=sys.argv[1];d=json.load(open(p));del d['captured']['F1-wilson']['values']['wilson_lo'];json.dump(d,open(p,'w'))" <site-packages>/proofpack/_fixtures/oracles_v1.json`, then `proofpack fixtures --offline --out D`. Result: exit 0, and F1-wilson is matched with `n_values_compared` 1.

Suggested repair: each `Row` declares the value names it compares, for example the engine function's keys, fixed in the register. An oracle missing a declared name is `not_matched`, with the reason `oracle value missing: <name>`. The regression test deletes one captured value, one register value and one Newcombe example, and must fail at `a09a0ef`.

## Non-blocking (record and carry)

**FA2-R1. Four surviving non-equivalent mutants in the repair-1 code.** I planted each in `wt-mut` and ran it against `-m "ap3 or day9" -x`:
- `_is_proofpack_checkout` returns `True` after the path check (the pyproject name check dropped): `241 passed`. It is non-equivalent. I installed the wheel with `pip --target X/src` inside `git init X`, whose `pyproject.toml` names `customer`. The shipped code gives `(None, 'not a proofpack source checkout ...')`. The mutant gives `('1d64586b...', 'git rev-parse HEAD in the proofpack source checkout ... (src/proofpack; pyproject.toml names proofpack); tracked files unmodified')`. So the source string would state a false fact, and no test pins the name condition.
- `if not isinstance(got, dict)` removed: `241 passed`. A non-dict engine result then raises, and the command exits 5 with no report. The note's "A non-dict engine result gives `engine_error: returned <type>`" has no test.
- `if oracle_value is None or engine_value is None` narrowed to `engine_value is None`: `241 passed`. An oracle NaN then raises `TypeError` (exit 5). No test feeds an oracle NaN or null, though the schema change (`values[].oracle` nullable) exists for it.
- `max_abs_deviation = worst if values else None` changed to `= worst`: `241 passed`. A row with no values would print a deviation of 0. That contradicts the note's decision 2.
- A fifth, `isinstance(value, bool)` dropped from `_number`, survives too. It is equivalent under the shipped engine, which returns no bools.

**FA2-R2. On an installed wheel, F14 reads `newcombe_table2.json` from outside the package, and its `[unverified]` marking can be replaced.** `resources._CANDIDATES["newcombe_table2.json"]` is `["../../fixtures/newcombe_table2.json"]` only. For a wheel installed with `pip --target X/src`, that path resolves to `X/fixtures/newcombe_table2.json`, a file in the customer's directory. I planted a copy of the repository's file there with `provenance.status` changed to `checked`. Result: `F14-newcombe matched ('fixtures/newcombe_table2.json', False, 'checked')`. The marking `[unverified against the primary PDF]` is gone from that row. `NEWCOMBE_ABSENT`'s sentence "F14 is compared in a source checkout only" (`fixtures.py:154`) is false for this layout. This is FA-R1's class: the package reads its enclosing directory.

**FA2-R3. The workflow test still misses engine runs without `--offline`.** The committed `ci.yml` and `release.yml` contain none of these lines: I read every line, and the engine-call counts are ci 5, release 6. I appended each as one extra step to `release.yml`'s `build` job and called `offline_violations`. It returned MISSED for all eight:
- `docker run --rm ghcr.io/x/proofpack@sha256:0123abcd run --input a --criteria b` (a digest-pinned image; `@` is outside `IMAGE_CALL`'s character class);
- `proofpack run --input a --criteria b  # --offline is added later` (the check is a substring test);
- `proofpack run --input a --criteria b --out out--offline`;
- `python -c "import subprocess; subprocess.run(['proofpack','run','--input','a'])"`;
- `python -c "from proofpack.cli import main; a=['run','--input','a']; main(a)"`;
- `echo run --input a --criteria b | xargs proofpack`;
- `CMD=run; proofpack $CMD --input a`;
- `uses: docker://python:3.12-slim` with `entrypoint: proofpack`, `args: run --input a`.

The `release.yml` header and the test docstring scope themselves to what the three patterns match, and those sentences hold. The test *name* `test_every_engine_run_in_a_workflow_carries_offline` (`tests/test_workflows.py:106`) states more than the test inspects (sentence violation).

**FA2-R4. `TOLERANCE_RULES["closed_form"]` lists the rows D1 section 9 does not name, and leaves some out** (sentence violation, repair-1 text at `fixtures.py:73-77`). D1 section 9 names "Wilson, 2×2, Brier, O/E, PSI". The rule adds F3-auroc, F4's ECE / reference Brier / IPA and F6's chi-square. `F6-closed-form` also compares `holm_1`..`holm_3` (Holm-adjusted p-values) and `se_site1`..`se_site3` at 1e-9. The rule does not list them, and D1 section 9 does not name them. The test name `test_the_tolerance_rules_cite_d1_section_9_only_for_what_it_names` repeats the claim.

**FA2-R5. A stale sentence in `tests/test_offline.py:196`, and a skip.** The comment reads "the mutation sweep's copy holds src/tests/schema/scripts only (its COPIED tuple)". Since `1a967d8`, `COPIED` includes `.github`, `Dockerfile`, `.dockerignore`, `uv.lock` and more (`scripts/mutation_sweep.py:63-76`). With `ci.yml` removed, `test_the_ci_namespace_job_and_its_script_exist_and_assert_both_invocations` gives `SKIPPED ... (the mutation sweep's copy)`. `test_workflows._load` would fail in the same tree, so the file's absence is still caught. Repair 1's FA-R11 changed the other skips but not this one (sentence violation).

**FA2-R6. `release.yml:180` states behaviour of a job that has never run** (sentence violation): "passive baseline scan; the report is an artefact, the job does not fail on findings". The upload step has no `if: always()`, so if the `docker run` exits non-zero, no artefact is uploaded. Whether `-I` keeps the exit at 0 on every finding level is [unverified]: I did not read ZAP's documentation. Job names such as "publish to TestPyPI (trusted publishing)" (`:104`) name what the job is written to do. The header says "Written, never run", so I did not count them.

**FA2-R7. `test_dockerfile` passes `COPY --from=ghcr.io/x/y:latest /k /k`** (`12 passed`). That line copies a file from an unpinned remote image. `python:3.12-slim-bookworm` also passes as the base. The committed Dockerfile has neither. This extends FA-R6, which is still carried: the test name `test_no_add_from_a_url_and_no_download_in_run` states more than the test inspects.

**FA2-R8. A wrong reason text for a bool engine value.** An engine value of `True` gives the reason `engine value not finite (1.0): half_width_n50`. It is not reachable from the shipped engine, which returns floats.

**FA2-R9. F17 does not compare the run directories' file sets.** Adding `T8.html` to one run gives `identical True`. The script names its hashed set (`hashed_set`: three files), and each run wrote exactly those three files here, so this is a gap rather than a false sentence.

**Carried from lens 1 / repair 1, re-read and still open:** FA-R6, FA-R8, FA-R9 (L2, L5, L6, L8, L14), FA-R10, FA-R12, RG-N2, RG-N3, RG-N6, RG-N7, RG-N8.

Also: the `image` job runs `aquasecurity/trivy-action@0.28.0` (a movable tag) while it holds `packages: write`. `echo "${{ secrets.GITHUB_TOKEN }}" | docker login ... --password-stdin` stores the token in the runner's `~/.docker/config.json` for the rest of the job. Both are the FA-R10 supply-chain class. Neither has run.

## Lens-1 blockers: closed (re-measured)

- **FA-B1.** F8 `half_width_n50` set to `inf` gives `not_matched engine value not finite (inf): half_width_n50`, `max_abs_deviation` `None`, exit 6, and the report validates. T12 prints "—", "not matched" and the reason. Left out: `not_matched`, exit 6. Engine returns `[1,2]`: `engine_error: returned list`, exit 6. Engine returns `{}`: three `engine value missing` reasons, exit 6. `ap3_missing_engine_value_counted_within` is killed in the committed sweep.
- **RG-B1.** The golden's exit-0 row reads "no HALT, no warning other than W16, a usable licence". I checked the claim against the engine: `FLAG_ONLY_CODES` is `{H10, W14, W16}`, but `ledger.record_run`'s W14 is appended to `warnings` (`run.py:516-517`), and `test_run_cli.py:451` asserts `EXIT_WARNINGS` for it. So W16 is the only warning with exit 0, and T12's W14 row ("exit 2") is right. Mutant `exit0_row_old_text` is killed.
- **RG-B2.** The header now names the test, its three patterns and "six here". I counted 6 engine calls in `release.yml` and 5 in `ci.yml`, each listed and each carrying `--offline`.
- **Regression tests.** I copied `tests/test_ap3_repair1.py` into `wt-old` (`1a967d8`), with the import proved: `25 failed`. None passes at the old commit.

## What I could not break (what I tried)

- **Tolerance edges on `F1-wilson.wilson_lo`, compared through the CLI with the file edited.** My Wilson formula (z = 1.959963984540054) equals the engine and the oracle: 0.2552885198782742.
  - Oracle +1 ulp: deviation 5.55e-17, matched, exit 0.
  - The largest float with deviation ≤ 1e-9 (9.999999717e-10): matched, exit 0. One ulp beyond (1.0000000272e-9): not matched, exit 6.
  - Engine ±1e-9 as oracle: deviation 1.0000000272e-9, not matched, exit 6.
  - +2e-9: deviation 1.9999999989e-9, not matched, exit 6.
  - The report's `max_abs_deviation` equals my deviation each time.
  - An emptied `values` dict gives `not_matched` "no value compared", exit 6.
- **Sockets.** I installed a `sitecustomize` audit hook, inherited by child processes, that raises on every `socket.*` event except `gethostname`. I proved it by refusing a `create_connection`. Under it I ran:
  - `fixtures` without `--offline` (exit 0);
  - `fixtures --offline --html --r-captures` (exit 0);
  - `build_sample_pack.py`, `f17_determinism.py --n 400`, `build_t12.py` and `sbom.py` (each exit 0).

  The log holds 5 `socket.gethostname` events and no connect, getaddrinfo or socket creation. The one getaddrinfo in the log is my own proof call.
- **F17.** I ran it twice with `--n 5000` (2.73 s; exit codes [4, 4]; `identical ... yes`) and diffed all 3 files of all 4 runs under my own regex mask of the three keys. They are identical. Unmasked, only `/manifest/started`, `/manifest/duration_s` and `/manifest/run_id` differ.

  Byte flips against run1:
  - a digit in the body of `run.json`: `run_json_masked` False;
  - a digit in the manifest `seed`: `run_json_masked` and `manifest_masked` False;
  - "Site C" → "Site D" in `pseudonyms.json`: `identical` False;
  - a digit in `ingest_report.json`: False.

  My first `pseudonyms.json` flip landed inside the masked `run_id`, and `identical` stayed True, as the mask says it should.
- **T12 injection.** I put `<script>alert(1)</script>` + U+202E + U+2066 + `<img onerror>` into `platform`, `git_sha_source`, every row's `what_is_compared`, `reason`, `oracle_source.detail` and value names, and every doctor `name` and `info`. The rendered page had 0 raw `<script>alert`, 0 raw `<img`, 110 escaped, 0 U+202E and 0 U+2066 (110 `&#x202e;`). I also put the same text into the intended-use slot through `t12_context`: 0 raw and 1 escaped. The slot has no input path in this version.
- **T12 wording.** In the page text:
  - validated, compliant, certified, approved, CSA-compliant, meets, pass and passed have 0 hits;
  - "qualified" appears only in D4's footer ("the manufacturer's qualified statistician"), and "endorsed" only in "No regulator has endorsed this tool";
  - "This record supports, does not replace, the manufacturer's own validation." is present verbatim;
  - every FDA anchor carries "draft guidance (January 2025), not for implementation";
  - "hash identity is claimed on the reference platform only (D1 section 9)" is present;
  - the IQ/OQ table has empty "Performed by / Date / Signature" cells and no tick mark.
- **The SBOM against `uv.lock`, with my own parse.** The lock holds 63 packages, 62 of them non-project. Every package is in the SBOM, with 0 missing and 0 extra. All 62 purls are `pkg:pypi/<name>@<version>`, and each sdist SHA-256 equals the lock's. Two runs are byte-identical (`cmp`). A whitespace-only lock change alters `serialNumber` only, as the docstring says. The docstring says the CycloneDX schema was not fetched, and claims nothing more.
- **Dockerfile planted lines caught** (`tests/test_dockerfile.py`): `USER root` as the last `USER`, `USER 0`, `curl | sh`, `ADD https://`, a secret mount copied into the image, `ENV ..._SIGNING_KEY`, `--require-hashes` dropped and `--no-index` dropped. Removing the `[unverified]` digest comment is also caught. Read by hand, the Dockerfile has one `FROM` (tag only, marked `[unverified]`), `COPY` of `requirements.lock` and `dist/`, no `ADD`, no download in a `RUN`, and `USER proofpack` last.
- **The wheel** (80 entries). It contains `_fixtures/oracles_v1.json`, `f4_expected.json`, `f4_calibration.csv` and the report schema. It does not contain `newcombe_table2.json`. No entry contains `PRIVATE KEY`, `BEGIN OPENSSH`, `SIGNING_KEY=` or `SIGNING_SEED`. From the fresh venv: `matched 29, not matched 0, no oracle recorded 3`, exit 0, `git_sha` null.
- **`git_sha` with the wheel under a customer repository's `src/`.** It returns null with the new reason (the shipped code holds; FA2-R1 is about the test).
- **Sentences re-read and found true:**
  - `cmd_fixtures`'s docstring: the test runs with and without `--offline`;
  - `t12.py`'s licence sentence: the cited test asserts no T12 and a report without a licence;
  - `NOT_RAISED`: `gates.py:203` builds `W10`, and no `.py` outside `errors.py`/`render/` quotes `"H10"`;
  - the doctor docstring;
  - the Dockerfile's "This file COPYs two inputs" and `SHIPPED_PUBLIC_KEY`;
  - `test_offline.py`'s "first run is GitHub Actions run 35911876338". I read it with `gh run list`: ci.yml at `7b2ca2a` (run 35624276759) has no `offline-namespace`, and `eda8a35` has it.
- **Damage elsewhere.** The diff touches no file under `stats/`, and not `gates.py`, `errors.py` or `TOLERANCES`. Day markers: day5 54, day6 285, day7 139, day8 468 + 1 skipped, day9 241, ap2 89, ap3 91. All pass.
- **Committed sweep.** `python scripts/mutation_sweep.py --marker ap3`: `15 planted, 15 killed, 0 survived; 149 s`.
- **My own mutants killed:**
  - `git status` failure read as clean;
  - an oracle error given `no_oracle_recorded`;
  - the doctor flag inverted;
  - the old exit-0 row text;
  - `docker://` args dropped from the test;
  - the register tolerance changed to 1e-3.

## Re-run figures (Git Bash, `wt-new` at `a09a0ef`, PYTHONPATH forced and proved)

| Command | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1496 passed, 2 skipped, 1 xfailed in 128.82s`. The skips are `test_doctor_cli.py:57`, and `test_e8_repair4.py:405` because the confusables file is looked up relative to the tree, which is why this differs from the note's 1497 / 1 in `wt-ap3`. |
| `-m ap3` / `-m ap2` / `-m day8` / `-m day9` | `91 passed` / `89 passed` / `468 passed, 1 skipped` / `241 passed` |
| `-m day7` / `-m day6` / `-m day5` | `139` / `285` / `54 passed` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `208 files already formatted` |
| `fixtures --out D` (no flag, hook on) | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0 |
| `f17_determinism.py --n 5000` | `identical ... yes`, [4, 4], exit 0, 2.73 s |
| `sbom.py` twice | `62 components: 13 required, 1 optional, 48 excluded`, identical |

## What I could not check

- **Every workflow job and the reference platform.** Nothing has run: `docker-smoke`, `build`, `image`, Trivy, `testpypi`, `install-from-testpypi`, `github-release` and `zap-baseline`. That includes the base image digest, the action tags, Dependabot's `uv` ecosystem, and ZAP's exit behaviour under `-I`.
- **RG-N7** (whether the release `build` job's report says "reference platform: yes" off the image). I cannot change the interpreter's version here.
- **The CycloneDX 1.5 schema.** It was not fetched.
- **PowerShell 5.1.** I repeated no figure there.

## Sentences I refused to write

- "Deleting an oracle is always reported as not matched": FA2-B1.
- "The workflow test catches every engine run without --offline": FA2-R3 lists eight lines it misses.
- "`proofpack fixtures` makes no network call": I measured the invocations listed above under one audit hook, and nothing beyond them.
- "The F14 `[unverified]` marking always reaches the page": FA2-R2.
