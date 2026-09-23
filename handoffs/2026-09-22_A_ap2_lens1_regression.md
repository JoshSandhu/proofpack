# A-P2 lens 1 (regression and record) - build day 8, lane A - 23 September 2026

**Verdict: FAIL.** Three blockers. Engine `a-p2-egress` at `4d61b6e` (from `7b2ca2a`); site `main` at `b8242c1` (from `994f460`, not pushed: `main...origin/main [ahead 1]`). Cold lens, no prior context; every figure below was measured in this session in detached worktrees under the scratchpad with `PYTHONPATH` forced (proved: `import proofpack` resolves to `.../lens-AP2-r1-regression/eng-4d61b6e/src/proofpack/__init__.py`; unforced it resolves to the engine's main tree). The engine's main tree was not touched; nothing was committed; the worktrees and junctions were removed at the end.

## Blockers

### B1 - the site gate chain is red at `b8242c1`: `test:unit` 651 pass / 1 fail, not the note's 652 / 0

`npm run test:unit` in a detached worktree at `b8242c1` (node_modules junctioned, `PROOFPACK_ENGINE_DIR` at a detached engine worktree at `a0c9abc`): `ℹ tests 653 / pass 651 / fail 1 / skipped 1`, exit 1. The failure:

```
✖ FA-B4: every page under src/pages declares a dateModified equal to the latest git date of the page and its data imports
  + 'src/pages/trust/index.astro: declares 2026-09-21, last changed 2026-09-23 (src/pages/trust/index.astro, src/data/egress_channels.json)'
  - []
```
`tests/day7-unlensed-repair2.test.mjs:141`; the date comes from `git log -1 --format=%as -- <file>` (line 92), which reads committed history only. `b8242c1` was committed at `2026-09-23T01:01:36+01:00`; `src/pages/trust/index.astro` still has `const DATE = '2026-09-21'` (line 31). The orchestrator addendum's `653 / 652 pass / 0 fail / 1 skipped` was measured on the staged tree before the commit, when the file's last committed date was still 21 September, and is not true at the sha. `npm test` runs `test:unit` before `check:legal`, and `deploy.yml` runs the gates first, so a push of `b8242c1` deploys nothing.

Repro: `cd <site worktree at b8242c1> && npm run test:unit` (after `npm run build`).

### B2 - `/trust` states that a CI job "runs" a check that has never run; the note says the page carries the fact that it had not

The new FAQ answer on `/trust` (`src/pages/trust/index.astro` line 192, rendered in `dist/trust/index.html`):

> "...its CI job runs the whole run inside a network namespace with no network (unshare -rn), with and without the flag; the release-image network capture does not exist yet, and the validation page says so."

The `offline-namespace` job exists only on branch `a-p2-egress` and, by the note's own item 13, "the job has not run" (`[unverified]`). The note's "Sentences refused" says the old sentence was "Rewritten on `/trust` and `/docs/egress`, with the fact that the job had not yet run". `/docs/egress` carries it (`grep -c "not yet run" dist/docs/egress/index.html` = 1); `/trust` does not (`grep -c "not yet run\|had not yet run" dist/trust/index.html` = 0). A published customer-facing sentence asserts a check that was never executed; that is the hard rule's defect.

Repro: `grep -o "[^.]*unshare[^.]*\." dist/trust/index.html`.

### B3 - a test id asserts the sentence the builder measured false

`tests/test_egress.py::test_f19_the_n7_cell_is_suppressed_and_no_digit_of_its_estimates_is_in_the_bytes` (line 216). The note's first refused sentence is "no digit of its estimate appears in the payload bytes ... measured false: the suppressed row's `npv` estimate `0.8333333333333334` (5/6) recurs legitimately in another cell (30/36), and `0.5` is the operating-point threshold". The test body asserts only the row's Wilson bounds (`len(repr(v)) >= 10`, at least 6 of them; comment at lines 225-227 says why) and the name still asserts the refused sentence. Test names are shipped text under the hard rule; here the counter-example was run and showed the sentence false, and the name was kept.

Repro: `grep -n "no_digit_of_its_estimates" tests/test_egress.py`.

## Non-blocking findings

- **N1 (sentence)** `src/proofpack/egress/telemetry.py` line 8: "there is no environment variable that redirects the send, so nothing can quietly point the runner at another host". `send(payload, url=...)` (line 127) and `run_telemetry(..., url=...)` (line 161) both take a `url`; `cmd_run` passes none. The CLI has no redirect; the API has a parameter. The sentence generalises past what was measured.
- **N2 (sentence)** `telemetry.py` lines 13-14 and 132: `send` "never raises to the caller" / "never raises". It catches `Exception` (line 141). `tests/conftest.py` relies on the opposite: `NetworkAttempted(BaseException)` is chosen precisely because `send` cannot swallow it (conftest lines 293-296). Measured in probe P2 below: an `AssertionError` (an `Exception`) raised by the socket stub was swallowed into `[W16] telemetry not sent (transport_error)`; a `BaseException` would not be. "never raises an `Exception`" is the measured sentence.
- **N3 (sentence)** `schema/egress_schema.json` descriptions, published verbatim on `/trust` once the pin moves: "so a key or a string the schema does not name cannot pass" (line 5); `identifier`: "an original header never matches because it is never looked at" (line 55); `manifest_sha256`: "it reveals nothing about the table" (line 28). The whitelist test feeds one unknown key (`original_header: "Patient ID"`), one unconstrained-string schema and one out-of-pattern `platform`; the sentences generalise over every key and every string.
- **N4 (sentence)** `/trust` FAQ: "every socket call is made to raise". `tests/test_offline.py` patches three names (`socket.socket`, `socket.getaddrinfo`, `socket.create_connection`). Probe P3 measured which of them `urllib` reaches first: `create_connection` (and `getaddrinfo` when `create_connection` is left unpatched). "three socket entry points" is the measured sentence.
- **N5 (missing test)** The task text says `egress.telemetry: false` is "honoured identically" to `--offline` and that `--offline` is tested with sockets refused. No test runs `egress.telemetry: false` with the socket entry points refused and the real transport; `test_telemetry_false_never_calls_the_transport` checks a recording transport only. Probe P4 (below) passed: 0 socket calls, `rc 0`, the skip line printed. The regression test is one fixture away.
- **N6 (ordering, not a defect at the sha)** `src/data/egress_channels.json` row `runner-telemetry` is `live` and its `limits` say "stored in the `runs` table ... answered 204"; `/legal/privacy` says "Our database (the `runs` table)". The note records that the table does not exist in the Supabase project until `db/migrations/2026-09-22_runs.sql` is applied and that a deployed `POST /api/telemetry` answers 500 `not stored` until then. `deploy.yml` deploys on push. The migration must be applied before the push, and the note's needs-from-Josh 1 says so; the pages carry no marker for the interval.
- **N7 (sentence)** `/docs/egress`: "stores the ten fields with a receipt time in a `runs` table for 24 months". `/trust`'s retention row adds "The purge that enforces the 24 months is not built yet"; the docs page and `/legal/dpa` 2.1 do not.
- **N8 (record)** "Fails pre-build" for the engine is by collection error, not by assertion: all three new files fail at `from conftest import NETWORK_ATTEMPTS` in the `7b2ca2a` worktree (3 errors during collection). The one changed existing test, `test_doctor_cli.py::test_egress_telemetry_skeleton_rejects_row_level_fields` with the `lic_1` fixture id, fails at `7b2ca2a` (1 failed) and passes at `4d61b6e`, so it pins the new `licence_id` pattern. The evidence that the assertions bite is the mutation sweep (16 / 16 killed, below).
- **N9 (record)** `check:egress` reads the row's `state` as a page-versus-manifest equality only. With the JSON reverted to `not_built` and no rebuild: `FAIL row "runner-telemetry": state is "live", manifest says "not_built"`. After a rebuild: `egress check: 0 error(s)`, `dist/trust/index.html` renders "Not built yet" twice. The gate does not inspect whether `functions/api/telemetry.js` exists; `live` versus `not_built` is the author's word.
- **N10 (carried nit, reproduced)** `main(["licence","verify",FILE,"--offline"])` → `SystemExit 2` (`unrecognized arguments: --offline`); `["--offline","licence","verify",FILE]` → rc 4 (refused, `unknown_key_id` on the shipped registry, as expected for the ephemeral-key file). `doctor` accepts the flag before and after.
- **N11 (record)** In CI the site's `tests/day8-telemetry.test.mjs` comparison of `functions/_lib/telemetry-schema.mjs` with its source skips (the engine checkout is at `ENGINE_REF`), so the Function's schema copy is compared by no CI job until the pin moves. Measured here: engine at `a0c9abc` → 19 pass / 1 skipped; engine at `4d61b6e` → 20 pass / 0 skipped.

## Suites and figures, re-measured

Engine, worktree at `4d61b6e`, `PYTHONPATH` forced (Git Bash | PowerShell 5.1):

| Command | Git Bash | PowerShell 5.1 | Note says |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `862 passed, 1 skipped, 1 xfailed in 80.73s` | `862 passed, 1 skipped, 1 xfailed in 87.68s` | 862 / 1 / 1 |
| `-m ap2` | `74 passed, 790 deselected` | `74 passed, 790 deselected` | 74 |
| `-m day8` | `74 passed, 790 deselected` | not repeated | 74 |
| `-m day7` | `139 passed, 725 deselected` | `139 passed, 725 deselected` | 139 |
| `ruff check .` | `All checks passed!` | same | same |
| `ruff format --check .` | `121 files already formatted` | same | same |
| `doctor --offline` | `All essential checks passed.`, exit 0 | same, exit 0 | same |
| `scripts/mutation_sweep.py --marker ap2` | `16 planted, 16 killed, 0 survived; 81 s` | not repeated | 16 / 16, 75 s |
| `--list \| grep -c " ap2 "` / lines / duplicate ids | 16 / 187 / 0 | not repeated | 16 / 187 / 0 |
| `git diff --name-status 7b2ca2a 4d61b6e -- src/proofpack/stats src/proofpack/narrate src/proofpack/render` | 0 lines | | empty |
| F19 smoke, fresh empty `PROOFPACK_HOME`, `--offline` | the note's six lines, exit 4, `ingest_report.json pseudonyms.json run.json` | identical, exit 4, same three files | same |
| the same with `--json-log` | `{'exit_code': 4, 'licence_status': 'refused', 'telemetry': {'skipped': '--offline'}, 'warnings': []}` | identical (re-parsed with `utf-8-sig`; the PowerShell pipe adds a BOM) | same |

The skip is `tests/test_doctor_cli.py:57` (write access cannot be revoked for this user); the xfail is F13 pending the R capture. One discrepancy that is the environment, not the code: the note's `smoke/home_empty` now holds a `ledger.json` written by the builder's runs, so re-using it prints a seventh line `[W14] the declared limit on acceptance runs against this test set is exceeded` and `warnings: ['W14']`; a fresh directory reproduces the note exactly.

Files the branch touches outside `src/proofpack/egress/`: `.github/workflows/ci.yml`, `pyproject.toml` (one marker line), `schema/egress_schema.json`, `scripts/ci_namespace_run.py` (new), `scripts/mutation_sweep.py`, `src/proofpack/cli.py`, `doctor.py`, `errors.py`, `run.py`, `tests/conftest.py`, `tests/test_doctor_cli.py`, `tests/test_egress.py`, `tests/test_offline.py`, `tests/test_telemetry.py`. `cli.py`: one call site in `cmd_run` plus the summary lines, `TELEMETRY_SENTENCE` and the `transport=` hook on `main`; `run.py`: `write_run` writes `pseudonyms.json`; `errors.py`: W16 in `WARN_CODES` and `FLAG_ONLY_CODES`. `narrate/`, `render/`, `templates/`, `claims_schema.json`, `output_schema_v1.json`: untouched.

Site, worktree at `b8242c1`, Git Bash, `PROOFPACK_ENGINE_DIR` at the `a0c9abc` worktree:

| Command | Measured | Note says |
|---|---|---|
| `check:bytes` | `275 text file(s)`, OK | same |
| `build` | wheel `152257 bytes, sha256 9b7d6986cd96…` from `a0c9abc`; `30 page(s) built` | same |
| `check:links` | `30 page(s), 1241 internal link(s), 1 distinct external URL(s)`, OK | same |
| `check:schema` | OK | same |
| `check:pricing` | `30 page(s), 37 currency figure(s), 0 error(s)` | same |
| `check:egress` | `vendored schema sha256_lf=c98b85aec4a1de89… canonical=1c914910cae38b8c…`; `claim scan: 36 built file(s), 523 attribute value(s), 2 sent document(s)`; `0 error(s)` | same |
| `check:validation` | `40 check(s): 0 pass, 0 fail, 40 pending, 4 [unverified]`, OK | same |
| `check:seo` | `0 error(s)`, OK (3 WARN lines shown; the note says 5) | 5 warnings |
| `check:keys` | `key_id=pp-2026-09 status=live`, 0 errors | same |
| `check:legal` | red by design: `2 of 2 gated page(s) failing` | same |
| `test:unit` | **653 / 651 pass / 1 fail / 1 skipped** (B1) | 653 / 652 / 0 / 1 |
| `test:e2e` | `9 passed (39.4s)` | 9 passed |
| `node --test tests/day8-telemetry.test.mjs` | 20 / 19 pass / 1 skipped at `a0c9abc`; 20 / 20 / 0 at `4d61b6e` | same |

## What I tried to break and could not

- **The F19 forbidden bytes.** Re-ran the F19 fixture through `cli.main` with a recording transport: `roc` has 401 points, 400 thresholds, 400 distinct (E7 RG-N8's figure); the `St Mary's` row is `n 7, events 2`; the site levels are `Königsberg`, `Royal Free`, `Site A`, `St Mary's`; the captured payload is 374 bytes with exactly the ten keys, `platform win-amd64-cp314`, `row_count_bucket <1k`, `halt_code None`, `licence_id lic_test0000000000000000000000000001`. The test's fourteen needles, four labels and 400 thresholds are asserted absent from two serialisations; the sweep's `ap2_whitelist_keeps_unknown_keys` and `ap2_pseudonym_order_reversed` are killed.
- **The socket guard (probes P1-P4, an untracked file in the `4d61b6e` worktree, deleted afterwards).** P1: with the fixture's three patches in place, `socket.socket()`, `socket.getaddrinfo(...)` and `socket.create_connection(...)` each raise and the calls list reads `['socket', 'getaddrinfo', 'create_connection']`. P2: `proofpack.egress.run_telemetry` replaced by one that ignores `offline`, the real `urllib_transport` handed to `main`, `--offline` set: the assertion `no_sockets.calls == []` fails with `RC=0 CALLS=['create_connection'] W16=['[W16] telemetry not sent (transport_error); run.json and the exit code are unchanged']` - the guard catches the reach, and `send` swallows the stub's `AssertionError` into W16 (N2). P3, one patch removed at a time: `socket` unpatched → `CALLS=['create_connection']`; `getaddrinfo` unpatched → `CALLS=['create_connection']`; `create_connection` unpatched → `CALLS=['getaddrinfo']`. Each remaining patch still records the reach, so no single removal lets the run proceed silently. P4: `egress.telemetry: false`, all three patched, real transport: `rc 0`, `CALLS=[]`, the skip line printed.
- **The schema.** An independent walk of `schema/egress_schema.json`: 12 object nodes; every one with `type: object` or `properties` that defines keys carries `additionalProperties: false`; the six `if`/`then` nodes (`number`, `two_by_two_cell`, `calibration_bin`) have no `type` and narrow their closed parent; 14 string properties, every one with `enum`, `const` or `pattern`, every `pattern` with `maxLength`. The engine's own walk (`test_every_string_property_in_the_schema_is_constrained_and_every_object_is_closed`) agrees.
- **The migration.** `db/migrations/2026-09-22_runs.sql`: 4 statements, each `create table if not exists` / `create unique index if not exists` / `create index if not exists`; the `create table ... runs (...)` block is byte-equal to `db/schema.sql`'s, and the three index statements equal `db/schema.sql` lines 199-201. `tests/day8-telemetry.test.mjs` parses both files to `['id', ...ten keys..., 'received_at']`.
- **The Function.** Reads `request.headers.get('content-type')` and `('content-length')` and no other header (read the code; the test's regex `request\.headers\.get\((?!'content-(type|length)')` agrees); the same `freshEnv()` from `tests/harness.mjs` that `day2-checkout`, `day3-quote` and the `day4-repair*` tests use; the entry file's `onRequestPost` / `onRequest` pair is the pattern `functions/api/checkout.js` uses. The twelve bad values → 400 naming the schema key only; the unknown key → `{"error":"unknown key"}`; a duplicate `run_id` → 204 at the read and at the unique-index throw.
- **The DEC-43 gate, measured.** `PROOFPACK_ENGINE_REQUIRED=1 npm run check:egress` with the engine at `a0c9abc`: `engine copy compared`, 0 errors. With the engine at `4d61b6e`: `FAIL the vendored egress schema has DRIFTED from the engine repository. engine canonical sha256 1541b3b8f1eb5f59… vendored 1c914910cae38b8c…`, exit 1. So: at the branch merge into engine `main` the pin stays `a0c9abc` and both `check:egress` and the `egress-drift` job stay green; at the pin move (S4) the drift job goes red until `src/data/egress_schema.json` is re-copied from the engine and `egress_schema.provenance.json` updated, exactly as decision 8 says. The Function's own copy names `4d61b6e9d19f5db179e4654ae7cfc8eb42d037ba` and canonical `1541b3b8…`, the engine's figure.
- **Nothing weakened.** `git diff --name-status` on `tests/` in both repositories: engine `M conftest.py, M test_doctor_cli.py, A test_egress.py, A test_offline.py, A test_telemetry.py`; site `M day4-repair4, M day7-unlensed-repair1, A day8-telemetry`; no deletions. Added-line greps: engine - one `pytest.skip` (`test_offline.py:156`, the sweep's copy has no `.github`; the real tree runs it) and no `xfail` / `.only`; site - one `t.skip` (`day8-telemetry.test.mjs:316`, the schema comparison when no checkout at the sha is reachable) and no `.only` / `.todo`; no marker line removed. `day4-repair4` S4R4-NB2 pins `endpoints.length === 6` and derives the number word; `day7-unlensed-repair1` FA-B1/RG-B2 pins "six dynamic endpoints". All three changed or new site tests fail at `994f460` against its own build (`day8-telemetry`: module not found; S4R4-NB2 and FA-B1/RG-B2: one failure each).
- **The YAML.** `.github/workflows/ci.yml` at `4d61b6e` parses (`yaml.safe_load`): jobs `test, offline-namespace, audit, wheel, import-without-scipy`; `offline-namespace` on `ubuntu-latest`, 5 steps; the `run` block contains `unshare -rn`, the `sudo unshare -n` fallback, the name-lookup refusal, and the four `grep -q` lines the note quotes.

## What I could not check

- The `offline-namespace` job itself: no Linux with Python is reachable here (the note says the same). Its YAML parses and its script ran natively on Windows in the builder's session; whether `ubuntu-latest` allows `unshare -rn`, and whether `sudo unshare -n` leaves `.venv/bin/python` usable as root, is decided by the first CI run. Open question 4 stands.
- The `SupabaseDb` insert path against a real PostgREST (`"schema"` and `"timestamp"` as column names; the `timestamptz` cast of the `...Z` string): no database credentials here; the tests exercise `MemoryDb` only.
- The live endpoint: not deployed (`b8242c1` unpushed).

## Sentences I refused to write

- "the three engine test files fail pre-build on their assertions" - they fail at collection (N8).
- "check:egress inspects the state change" - it inspects page-versus-manifest equality (N9).
- "removing any one socket patch makes the offline test pass" - measured false; another patch records the reach (P3).
- "the site gate chain is green" - `test:unit` is red at the sha (B1).

## Worktrees

Created and removed: engine `eng-4d61b6e`, `eng-7b2ca2a`, `eng-a0c9abc`; site `site-b8242c1`, `site-994f460` (node_modules junctions removed as links first). The builder's `wt-a-p2` and `wt-engine-a0c9abc` were not touched.
