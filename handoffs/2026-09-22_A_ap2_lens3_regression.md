# A-P2 lens 3 (regression and record) - build day 8, lane A, repair round 2 - 23 September 2026

**Verdict: FAIL.** Two blockers, both sentences on `/legal/dpa` 2.1 that this repair wrote and that I measured false; one of them is pinned by the repair's own site test. The code is not the problem: every engine and site figure in the repair note re-measures (two figure slips below), every new test fails at its pre-sha on the line the note quotes, nothing was weakened, and the new deadline holds over HTTPS as well as HTTP.

Engine `a-p2-egress` at `028170e` (repair of `0cf9ba5`, branch from `7b2ca2a`); site `main` at `7e7e460` (repair of `2b5c7de`). Cold lens, no prior context. Every figure below was measured in this session in detached worktrees under `scratchpad/lens-AP2-r3-regression/` (`eng-028170e`, `eng-0cf9ba5`, `eng-a0c9abc`; `site-7e7e460`, `site-2b5c7de` with `node_modules` junctioned and `PROOFPACK_ENGINE_DIR` at `eng-a0c9abc`, the site's `ENGINE_REF`), with `PYTHONPATH` forced and proved in both shells (`import proofpack` printed `...\lens-AP2-r3-regression\eng-028170e\src\proofpack\__init__.py` in Git Bash and in PowerShell 5.1; unforced it printed `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py`, lane E's main tree). The engine's main tree was read (`git diff`, `git log`, `git merge-tree`) and not modified, checked out, stashed, committed or tested. Nothing was committed or pushed. My one outbound request was a GET to the live `/api/telemetry` (404). Every probe that used the real transport ran under a guard that refused any name lookup other than loopback (`LENS GUARD non-loopback lookups: []` on every run).

## Blockers

### B1 (site, `/legal/dpa` 2.1 and the `/trust` runner-telemetry row; `sentence_violation`): "a later revision of that definition, with the same ten keys and stricter value patterns" is false. The later revision admits values the published one refuses, and the receiver stores them

DPA 2.1 (source `src/content/legal/dpa.md`, rendered once in `dist/legal/dpa/index.html`): "the sender and the receiver validate against a later revision of that definition, with the same ten keys and stricter value patterns". The row's `state_note` (rendered once on `dist/trust/index.html`): "the later revision at 028170e ..., which tightens licence_id (lic_ plus up to 60 letters or digits, or null; ...), platform, run_id, timestamp, engine_version, duration_s and manifest_sha256".

The keys and the required list are the same (both 10; measured). The value rules are not stricter: `jsonschema.Draft202012Validator` on each revision's `$defs/telemetry`, one field changed from a record the revision otherwise accepts:

```
licence_id=None: published(a0c9abc) admits=False later(028170e) admits=True
licence_id='lic_abc': published(a0c9abc) admits=False later(028170e) admits=True
licence_id='L-abc': published(a0c9abc) admits=True later(028170e) admits=False
halt_code=E01: published admits=False later admits=True
halt_code=S05: published admits=False later admits=True
platform=macosx-14.0-arm64-cp312: published admits=False later admits=True
platform=freebsd-13.2-release-amd64-cp312: published admits=False later admits=True
```

And the receiver, `handleTelemetry` from `functions/_lib/telemetry.mjs` at `7e7e460` with the harness's `freshEnv()`:

```
licence_id null -> 204
halt_code "E01" -> 204
halt_code "S05" -> 204
licence_id "L-abc" -> 400 {"error":"invalid value for key: licence_id"}
```

So the receiver takes and stores records (a null `licence_id`, six halt codes, dotted platform tags) that the schema published on `/trust` refuses. A DPA reader who takes the published schema as the outer bound of what is accepted is told the wrong thing. `licence_id` changed shape (`^L-...` to `^lic_...` or null), `platform` widened (dots and more segments allowed), `halt_code` grew from 13 values to 19. Only `run_id`, `timestamp`, `engine_version`, `duration_s` and `manifest_sha256` are tightened. The row itself says "lengthens the halt_code list", which contradicts the DPA's "stricter".

The repair's test pins the false wording: `tests/day8-ap2-repair2.test.mjs` AP2R2-N4 (the DPA test) asserts `assert.match(dpa, /the sender and the receiver validate against a later revision of that definition, with the same ten keys and stricter value patterns/)`.

Repro: `scratchpad/lens-AP2-r3-regression/schemacmp.py` (validator, both revisions) and `fn_probe.mjs` (the Function); both kept.

Repair (one clause each): DPA 2.1 "... a later revision of that definition with the same ten keys, whose value rules differ (the runner-telemetry row on /trust lists how)"; the row: "changes licence_id (...; it now admits null and the lic_ ids the site issues, and refuses the published ^L- form), widens platform, tightens run_id, timestamp, engine_version, duration_s and manifest_sha256, and adds six halt codes"; move the AP2R2-N4 pin with it.

### B2 (both repos; `/legal/dpa` 2.1, the `/trust` row `limits`, `/docs/egress`; `sentence_violation`): "in the engine's tests for a 500, a timeout, a refused connection, a 3xx and an unreadable schema resource the run's exit code and run.json are the same as with --offline". The tests do not assert that about run.json

Here is what each engine test inspects (`tests/test_telemetry.py` at `028170e`, read):
- 500 / timeout / refused: `test_a_failed_send_prints_one_w16_line_and_leaves_exit_code_and_documents` hashes `run.json`, `ingest_report.json` and `pseudonyms.json` inside the transport and again after the run, and asserts they are equal. That is before-and-after equality, not a comparison with an `--offline` run.
- 3xx: `test_a_302_through_the_cli_prints_w16_and_the_location_host_receives_nothing` asserts `rc == EXIT_OK`, the W16 line and the two listeners. It never reads `run.json`.
- Unreadable schema: `test_a_run_with_the_schema_resource_unreadable_prints_w16_and_exits_as_the_run` asserts `rc == EXIT_OK`, that `run.json` and `pseudonyms.json` **exist**, 0 transport calls, and the W16 line.
- No test in the suite compares `run.json` with an `--offline` run's `run.json`. The only offline comparison, `test_the_exit_code_with_a_failed_send_equals_the_exit_code_offline`, compares exit codes, on a 503.

Counter-example, constructed and run in `eng-028170e`. In `cmd_run`, straight after `run_telemetry`:

```text
if sent is not None and (sent.reason_code == "schema_unavailable" or (sent.status or 0) // 100 == 3):
    _p = Path(args.out) / "run.json"
    _p.write_bytes(_p.read_bytes() + b"\n")
```

It fired in both tests (recorded to a scratch file: `http_error 302 b'\n\n'` and `schema_unavailable None b'\n\n'`). Both tests passed, and so did the whole suite: **`876 passed, 1 skipped, 1 xfailed in 76.47s`**, `-m ap2` **`88 passed`**. I restored the file (`git checkout`) and `git status --short` was empty.

The behaviour holds in the code: lens 1's `attack_socket.py` section C, re-run at `028170e`, prints `run.json(normalised)==offline:True` for 301, 302, 303, 307 and 308. But that is a lens script, not "the engine's tests". The exit-code half is true as the tests stand: each of the five asserts `rc == EXIT_OK`, and the fixture's offline rc is `EXIT_OK`. The same attribution is in `errors.py` (`WARN_CODES` comment: "the line's own words are the measured ones (... the W16 tests named in FLAG_ONLY_CODES)"). The W16 line's own words ("run.json and the exit code are unchanged") are exactly what the 3xx and schema-unreadable tests do not read.

Repro: the mutant above, then `python -m pytest -q -p no:cacheprovider -m ap2`. Repair: either add the missing assertion (hash `run.json` inside the transport and after the run in the 3xx and schema-unreadable tests, the way the 500/timeout/refused test does; the mutant above must fail them) and reword to "run.json is byte-identical before and after the send", or reword all three copies and the `errors.py` comment to name what each test reads.

## Non-blocking findings

- **N1 (engine, `sentence_violation`; `telemetry.py` module docstring and `urllib_transport` docstring).** "so an ``--offline`` process never imports a network module" (rewritten in this repair) and the new "Every network module is imported here so that a process that never sends never imports one" are false as general statements. An in-process `main(["run", ..., "--offline"])` on the smoke table left `['_socket', 'socket']` in `sys.modules` (none before). The first importer was `platform._node` (`import socket`, for `gethostname`), reached from `numpy/testing/_private/utils.py:90` `platform.machine()`. No socket object was created: lens 1's trap on `socket.socket.__init__` recorded `sockets=[]` for every command. What is true, and what `test_the_default_transport_is_urllib_and_no_network_module_is_imported_at_module_level` inspects, is that no module under `src/proofpack` imports one at module level. Reword to that.
- **N2 (figure, engine code and the note).** "the 45-byte 204 answer" (`telemetry.py:20`, `tests/test_telemetry.py:319`, `:357`, the note's table) is 46 bytes: `len(b"HTTP/1.1 204 No Content\r\nContent-Length: 0\r\n\r\n")` = 46. The 13.5 s pre-sha figure is 45 gaps × 0.3 s.
- **N3 (site, `sentence_violation`, same root as B1).** `/docs/egress`: "The receiver ... validates the record against the same definition". Nothing earlier on that page is a definition the word "same" can refer to. The page opens by saying its table is held to "the schema", which is the published `a0c9abc` copy. The Function validates against `028170e`'s, which differs (B1). The repair changed "schema" to "definition" and kept "same".
- **N4 (figure).** `check:seo` in both site worktrees: `0 error(s), 5 warning(s)` (index 275, trust 271, trust/validation 204, pricing 217, how-it-works 234 chars). The note says 2 WARN lines. The site main tree is clean (`git status --short` empty) at the same sha.
- **N5 (carried RG-L2R-N8, reproduced).** In `eng-028170e`, with the fixture patching only two of `socket`, `getaddrinfo` and `create_connection` (each pair in turn), `-m ap2` over `test_offline.py test_telemetry.py test_egress.py` gave `88 passed` all three times. Removing the `--offline` short-circuit (`if offline or not telemetry_enabled(` → `if not telemetry_enabled(`) failed 4: `test_run_offline_opens_no_socket_and_calls_no_transport`, `test_offline_never_calls_the_transport`, `test_json_log_carries_the_telemetry_result_and_the_skip_reason`, `test_f19_the_telemetry_payload_validates_and_carries_only_the_schema_keys`. Removing the `telemetry: false` short-circuit failed 2: `test_telemetry_false_with_the_real_transport_and_sockets_refused_opens_no_socket`, `test_telemetry_false_never_calls_the_transport`. The patches detect; the code's two short-circuits are what is pinned. No site sentence claims more: `/trust` and `/docs/egress` say the three entry points "are made to raise".
- **N6 (carried RG-L2R-N7, reproduced).** With `runner-telemetry.state` set to `not_built` and no rebuild: `FAIL row "runner-telemetry": state is "live", manifest says "not_built"`. After `npm run build`: `egress check: 0 error(s)`, and `Not built yet` appears 3 times on `dist/trust/index.html` (2 when restored). The gate checks that the page matches the manifest; it does not check the state change against the code.
- **N7 (carried FA-L2-N1, re-measured; the note says it was not).** `egress: {Telemetry: false}` → `rc=0 transport calls=1`, `telemetry sent (http 204)`. `egress: {telemetry: false}` → `transport calls=0`, skipped.
- **N8 (environment).** `test:unit` in the detached worktree: `664 / 662 / 0 / skipped 2`. With `GPS_AUTOMATION_DIR=C:/Users/joshs/GPS/ProofPack/gps-automation`: `664 / 663 / 0 / 1`, the note's figure. The one remaining skip is `the vendored copy equals the engine schema at its commit ... # no engine checkout at 028170e reachable`.
- **N9 (housekeeping).** Worktrees named `dead0240-lens-AP2-r3-regression/*` (engine: `eng-028170e`, `eng-0cf9ba5`, `eng-a0c9abc`; site: `site-2b5c7de`, `site-7e7e460`) were registered before I started, apparently from an earlier run of this lens. I did not touch them or the `dead0240-lens-AP2-r3-fresh-attack/*` set. The orchestrator should remove them.

## Suites and figures, re-measured

Engine, `eng-028170e`, `PYTHONPATH` forced (Git Bash | PowerShell 5.1 | note):

| Command | Git Bash | PowerShell 5.1 | Note |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `876 passed, 1 skipped, 1 xfailed in 79.35s` | not repeated | 876 / 1 / 1 |
| `-m ap2` | `88 passed, 790 deselected in 15.61s` | `88 passed, 790 deselected in 14.34s` | 88 |
| `-m day8` | `88 passed, 790 deselected in 14.50s` | not repeated | 88 |
| `-m day7` | `139 passed, 739 deselected in 8.17s` | `139 passed, 739 deselected in 7.46s` | 139 |
| `python -m ruff check .` | `All checks passed!` | `All checks passed!` | same |
| `python -m ruff format --check .` | `125 files already formatted` | `125 files already formatted` | 125 after the notes commit |
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.` | same, `exit=0` | same |
| `scripts/mutation_sweep.py --marker ap2` | `16 planted, 16 killed, 0 survived; 74 s` | not repeated | 16/16/0; 71 s |
| F19 smoke, fresh empty `PROOFPACK_HOME`, `scratchpad/smoke/test.csv` + `criteria.yaml`, `--offline` | the telemetry line, the sentence on its own line, `Next step` back to E7's text, `exit=4`, `ingest_report.json pseudonyms.json run.json` | identical, `exit=4`, same three files | same |
| the same with `--json-log` | `{'exit_code': 4, 'licence_status': 'refused', 'telemetry': {'skipped': '--offline'}, 'warnings': []}` | identical | same |
| `git diff --numstat 7b2ca2a 028170e` | `cli.py 20 3`, `errors.py 11 1`, `run.py 12 1`, `pyproject.toml 1 0`; `cli.py` hunks `-449,6 +449,17`, `-462,6 +473,7`, `-474,6 +486,7`, `-562,14 +575,18` (`main`) | | same |
| `git merge-tree --write-tree 657ef11 028170e` | exit 0, no conflict (at `0cf9ba5`: `CONFLICT (content)` in `scripts/mutation_sweep.py` and `src/proofpack/cli.py`) | | same |
| `git merge-tree --write-tree 7fa690b 028170e` (lane E committed `7fa690b`, "day-8 repair 2", while I worked) | exit 0, no conflict | | not in the note (later commit) |

Before `7fa690b` landed I also applied lane E's then-uncommitted working-tree diff (12 files, read with `git diff` from the main tree) with `git apply --check` onto a scratch checkout of the `657ef11 x 028170e` merged tree. It applied cleanly.

Site, `site-7e7e460`, Git Bash, `PROOFPACK_ENGINE_DIR` at `eng-a0c9abc`:

| Command | Measured | Note |
|---|---|---|
| `check:bytes` | `277 text file(s)`, OK | same |
| `build` | wheel `152257 bytes, sha256 9b7d6986cd96…` from `a0c9abc`; `30 page(s) built` | same |
| `check:links` | `30 page(s), 1243 internal link(s)`, OK | same |
| `check:schema` | OK | same |
| `check:pricing` | `37 currency figure(s), 0 error(s)` | same |
| `check:egress` | `engine copy compared: ../eng-a0c9abc/...`; `claim scan: 36 built file(s), 523 attribute value(s), 2 sent document(s)`; `0 error(s)` | same |
| `check:validation` | `40 check(s): 0 pass, 0 fail, 40 pending, 4 [unverified]`, OK | same |
| `check:seo` | `0 error(s), 5 warning(s)` | **2 WARN** (N4) |
| `check:keys` | `key_id=pp-2026-09 status=live`, 0 errors | same |
| `test:unit` | `664 / 662 / 0 / 2`; with `GPS_AUTOMATION_DIR` `664 / 663 / 0 / 1` (N8) | 664 / 663 / 0 / 1 |
| `test:e2e` | `9 passed (37.4s)`, first run | 9 passed (38.5s) |
| `check:legal` | red by design: `2 of 2 gated page(s) failing`, rc 1 | same |
| the three day-8 files with `PROOFPACK_ENGINE_DIR=eng-028170e` | `31 / 31 / 0 / 0` | same |
| `PROOFPACK_ENGINE_REQUIRED=1 check:egress`, engine at `a0c9abc` / at `028170e` | `0 error(s)`, rc 0 / `FAIL the vendored egress schema has DRIFTED`, rc 1 | same |
| `node scripts/vendor-telemetry-schema.mjs` against `eng-028170e` | wrote `functions/_lib/telemetry-schema.mjs`, sha256 `70812ae1…` before and after (byte-identical), canonical `35bfb91f6c9caf14…` | same |
| `curl -o /dev/null -w %{http_code}` GET `https://proofpack.globalphoenix.co.uk/api/telemetry` | `404` (origin/main is `994f460`; `b8242c1` is not on it) | 404 |

## Fails pre-build

- **Engine.** I copied `tests/test_telemetry.py` from `028170e` into `eng-0cf9ba5` and ran it with `PYTHONPATH=eng-0cf9ba5/src` (proved). The four selected ids gave `4 failed, 36 deselected in 15.43s`: the drip test (`AssertionError: 13.53526250005234`, `sent: True != False`); the `send` schema test (`OSError: egress_schema.json unreadable`); the CLI schema test (`assert 5 == 0`); the next-step test (`ImportError: cannot import name 'TELEMETRY_SENTENCE' from 'proofpack.egress.telemetry'`). The whole file gave `4 failed, 36 passed`. Each matches the note's quoted line. Restored with `git checkout -- tests`.
- **Site.** I copied `tests/day8-ap2-repair2.test.mjs` and the modified `day8-ap2-repair1.test.mjs` into the built `site-2b5c7de`. The new file gave `6 / 0 pass / 6 fail`, each on the note's quoted line: `/One HTTP request with a 5 s timeout/` (not-match); `/the schema the engine validates its own\s+outbound payload against/`; `/published verbatim on \[\/trust\]\(\/trust\) at the engine commit the site builds from/`; `/was repaired on 23 September 2026 \(engine commits \`47d1aeb\` and \`466ab15\`\)/`; `/one attempt|one urllib attempt/`; `/as of 22 September 2026/`. The modified repair-1 file gave `5 / 4 / 1 fail` (AP2R1-N1, the moved DPA regex). Restored.

## Nothing weakened

- `git diff --name-status`, tests only: engine repair `M tests/test_telemetry.py`; engine branch-wide `M conftest.py, M test_doctor_cli.py, A test_egress.py, A test_offline.py, A test_telemetry.py`; site repair `M day8-ap2-repair1.test.mjs, A day8-ap2-repair2.test.mjs`. No deletion in either repository.
- Added lines grepped for `skip|xfail|.only|todo`. The engine's four hits are `_skip_reason` and the `skipped` strings in `telemetry.py`, not test skips. The site has none.
- Removed test lines: the engine's six are the module docstring and the old `from proofpack.cli import TELEMETRY_SENTENCE, main`; the site's one is the repair-1 DPA regex the note says moved. No `pytestmark` or `pytest.mark` line was removed; `test_telemetry.py` still carries `pytestmark = [pytest.mark.day8, pytest.mark.ap2]`.
- The repair-1 regex moved with its sentence, and its pin (the redirect clause) is still in it.

## What I tried to break and could not (with the bytes and figures)

- **The deadline over HTTPS, the real endpoint's scheme (not measured by the repair).** I set up a trusted self-signed certificate (`SSL_CERT_FILE`), a TLS server on 127.0.0.1 and a TCP relay, then called `send(..., transport=urllib_transport, timeout=1.0)`:
  - Control, one record, no drip: `sent=True, 204` in 0.42 s.
  - One TLS record per byte, 0.3 s apart: **`timeout` in 1.01 s** at `028170e`, `sent=True, 204` after **13.93 s** at `0cf9ba5`.
  - One TLS record whose TCP bytes the relay drips 0.3 s apart: `timeout` in 1.01 s at `028170e` (1.03 s at `0cf9ba5`).
  - Side measurement: with `https://localhost:<port>` the lookup returned `::1` first, and the run gave `timeout` at 1.03 s, not a hang. Each connect attempt gets the time left, and the read then found none left.
  - Script: `tls_drip.py`, kept.
- **The HTTP drip test.** `--durations`: `1.00s call`, which matches the note's 1.00 s.
- **Lens 1's scripts at `028170e`, under the loopback guard.**
  - `attack_socket.py` section A: `run`, `compare`, `map --yes` (H07, rc 3), `doctor`, `licence show` (both flag positions), `--offline licence verify` and `--offline licence install` (rc 5 `SameFileError`, pre-existing) gave `sockets=[]`. `licence verify FILE --offline` and `fixtures --offline` exited through argparse (2), pre-existing.
  - Section B: `egress.telemetry: false` with the default transport gave `sockets=[]` and the skip line.
  - Section C: 204 → sent. 500 and 413 → W16 `http_error`. 301, 302, 303, 307, 308 → W16 `http_error, http NNN`, `other_host_got=[]`, `main_got=1`. Hang → `timeout` 5.07 s (`send()` alone 5.00 s). Closed port → `connection_refused` 2.10 s. `run.json(normalised)==offline:True` and `rc=0` in every case. A self-signed certificate (untrusted) → `transport_error`, 0 bodies.
  - `attack_payload.py`: 424 needles. The telemetry bytes' only hit is the send's own date; the aggregates' only hits are the canonical names `sex`, `age`, `site`. All 400 ROC thresholds are absent (E7 RG-N8). The `St Mary's` cells: 7, all null. The type and length refusals are as lens 2 lists them.
  - The script's one `!!` line (`St Mary's op1 npv est 0.8333333333333334 appears in aggregates bytes`, also in lens 2's re-run) I traced: the hit is cell 62, `site Site A npv op1`, `n 36 k 30` = 5/6. Another level's own estimate happens to be the same number; nothing leaked.
- **`send` with values that break the projection** (`duration_s=object()`, `licence_id=5`, `run_id=b"x"`, an integer key) and `run_telemetry` on a document with an empty `manifest` all gave `payload_invalid`, with 0 transport calls. The widened `except Exception` does not relabel a payload fault as `schema_unavailable` on those inputs.
- **The proxy.** With `HTTPS_PROXY` at a loopback recorder: one connection, first line `CONNECT proofpack.globalphoenix.co.uk:443 HTTP/1.1`, payload bytes at the proxy `False`, `transport_error` in 0.03 s. There was no lookup of the real host.
- **The schema.** Walked at `028170e`:
  - 12 object nodes. Every node typed `object` carries `additionalProperties: false`. The six without it are the `if`/`then` narrowers of `number`, `two_by_two_cell` and `calibration_bin`, which have no `type`.
  - 14 string nodes. None is unconstrained, and each has a `maxLength`, `enum` or `const`.
  - `$defs/telemetry` has 10 keys, all 10 required, `additionalProperties` false.
  - The only change in the repair is the `$defs/level` description. Its token-pattern sentence matches `pattern` in the file.
- **The YAML.** `.github/workflows/ci.yml` at `028170e` parses (`yaml.safe_load`): jobs `test, offline-namespace, audit, wheel, import-without-scipy`. `offline-namespace` runs on `ubuntu-latest` with 5 steps. Its run step tries `unshare -rn true` and falls back to `sudo unshare -n`. It exits 1 if `getaddrinfo('proofpack.globalphoenix.co.uk', 443)` resolves inside the namespace. It then runs `ci_namespace_run.py --offline` and `--online`, grepping `telemetry skipped (--offline); nothing was sent`, `namespace run: --offline exit=0 run.json=written`, `\[W16\] telemetry not sent (` and `namespace run: --online exit=0 run.json=written`.
- **The migration and the Function.** Neither changed since `b8242c1` (`git diff --stat b8242c1 7e7e460 -- db functions/_lib/telemetry.mjs functions/api/telemetry.js` is empty).
  - `db/migrations/2026-09-22_runs.sql`: `create table if not exists runs` and three `create ... index if not exists`, with no other statement. The table block is equal to `db/schema.sql`'s (CR stripped), and the three index lines are in `schema.sql`.
  - The Function reads only `request.headers.get('content-type')` (line 110) and `('content-length')` (line 114). Its only `cookie` is in a comment.
  - `tests/day8-telemetry.test.mjs` builds its env with `freshEnv()` from `tests/harness.mjs`, as `day2-checkout.test.mjs` does. `TELEMETRY_DEF` is unchanged in `7e7e460`: the file's diff is the three header lines.
- **The `/trust` "the build fails" sentence.** I changed the vendored `licence_id` pattern (`+` to `*`) in the worktree: `PROOFPACK_ENGINE_REQUIRED=1 check:egress` at `a0c9abc` gave `5 error(s)`, including `DRIFTED` and `not byte-identical`. `deploy.yml` sets `PROOFPACK_ENGINE_REQUIRED: '1'` (line 155) on its engine-backed step. Restored.
- **The lens-1 and lens-2 items the repair marked fixed** (FA-L2-N2, N3, N4, N10; RG-L2R-N3, N4, N5), from `dist/` at `7e7e460`:
  - `since 22 September 2026`: 0 files.
  - `/trust`: `Last updated 2026-09-23.` 1; `then a 5 s deadline, counted from the start of the request` 1; `a revision marked status: skeleton` 1 (the published copy carries `"status": "skeleton"`, line 63); `no record has been received as of 23 September 2026` 1; `validates its own outbound payload against` 0; `every socket call is made to raise` 0; `had not run anywhere as of 23 September 2026` 2.
  - `/legal/dpa`: `one attempt` 0. `/docs/egress`: `47d1aeb` 2, `466ab15` 2.
  - No test is named `no_digit_of_its_estimates` (lens-1 RG-B3).
  - Commit dates: `4cad727 2026-09-22 14:41`, `47d1aeb 2026-09-23 01:38`, `466ab15 2026-09-23 02:26`, which match `/docs/egress`.
  - FA-L2-N4's specific false sentence ("the schema the engine validates its own outbound payload against") is gone. The replacement is B1.
- **Line endings.** Every touched site file is `i/lf w/lf`; every touched engine file is `i/lf w/crlf`.
- **Voice.** The site repair's added lines have no marketing adjective, no exclamation mark outside `<!--`, and no rhetorical question.

## Sentences I refused to write

- "The later revision is stricter". Measured false (B1).
- "The engine's tests show run.json unchanged on a 3xx". No engine test reads it there (B2). The lens script shows it; I say so.
- "An --offline process imports no network module". `socket` is imported (N1); no socket object is created.
- "Removing one socket patch fails a test". `88 passed` three times (N5).
- "The gate checks the telemetry row's state against the code". It checks the page against the manifest (N6).
- "The evening merge is clean". Measured only as `merge-tree 7fa690b x 028170e` exit 0 at the time I ran it. Whatever lane E commits later is not in it.
- "The deadline holds on a dripped TLS handshake". Not measured (my relay passed the first 0.3 s through).

## What I could not check

- The `offline-namespace` job: Windows, no `unshare`. The YAML parses and its commands are as above. It has not run anywhere (the branch is unpushed).
- A receiver that drips the TLS handshake. A hostname with several addresses other than `localhost`. Linux and macOS.
- Postgres: whether `db/migrations/2026-09-22_runs.sql` has been applied (no credentials), the `409` text, `timestamptz`. The live deploy of `b8242c1`..`7e7e460` (unpushed; the path answers 404).
- The full engine suite in PowerShell 5.1. The note did not repeat it either. `-m ap2`, `-m day7`, `ruff`, `format`, `doctor`, the smoke and `--json-log` were repeated there and match.

## Worktrees

Created and removed: engine `eng-028170e`, `eng-0cf9ba5`, `eng-a0c9abc`, and `eng-merge` (a scratch checkout of the merged tree, never committed); site `site-7e7e460`, `site-2b5c7de`. I deleted the two `node_modules` junctions as links first; the site main tree's `node_modules` still holds 499 entries. The scratch scripts (`schemacmp.py`, `fn_probe.mjs`, `tls_drip.py`, `offline_mut.py`, `n1_probe.py`, `proxy_probe.py`, `guarded.py`) and outputs stay in `scratchpad/lens-AP2-r3-regression/`.
