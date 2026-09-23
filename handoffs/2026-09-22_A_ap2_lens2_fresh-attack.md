# A-P2 lens 2 (fresh attack) - egress, telemetry, `--offline`, `/api/telemetry` (build day 8, lane A; repair round 1; 23 September 2026)

Engine `0cf9ba5` (branch `a-p2-egress`, from `7b2ca2a`; pre-sha `4d61b6e`); site `2b5c7de` (main; pre-sha
`b8242c1`). Cold lens, no prior context. All probing in detached worktrees under the session
scratchpad (`lens-AP2-r2-fresh-attack/`: `eng-0cf9ba5`, `eng-4d61b6e`, `eng-a0c9abc`, `site-2b5c7de`,
`site-b8242c1`; the two site trees with `node_modules` junctioned, `PROOFPACK_ENGINE_DIR` at
`eng-a0c9abc`, the site's `ENGINE_REF`). `PYTHONPATH` forced to `eng-0cf9ba5/src` for every engine
figure and proved: `import proofpack` printed `...\lens-AP2-r2-fresh-attack\eng-0cf9ba5\src\proofpack\__init__.py`;
unforced, the same command printed lane E's main tree (`C:\Users\joshs\GPS\ProofPack\proofpack\src\...`).
The engine's main tree was read (`git diff`, `git status`, `git merge-tree` against its committed
`29fc04e`) and not modified, checked out, stashed, committed or tested. Nothing was committed or
pushed anywhere. Every figure below was measured in this session.

## Verdict: **PASS** - no finding meets the blocker rule. Nine non-blocking findings, four of them false sentences, one of them the merge conflict the evening will meet.

What I could not break: no telemetry byte carried a name, a header, a threshold, a date other than
the send's own timestamp, a row value, the ledger key, the licence signature or the map; every
command opened zero sockets under `--offline`; the exit code and the normalised `run.json` were the
same across a 204, 500, 413, 301, 302, 303, 307, 308, a hang, a closed port and a bad certificate;
the endpoint reflected nothing, set no cookie and did not look a licence id up. The lens-1 blockers
(the "since 22 September" rows, the `/trust` date, the test id) do not reproduce; the lens-1 fixes
(a 3xx not followed, a trailing newline refused) reproduce as fixed; the six new engine tests and the
five new site tests fail at their pre-shas.

The findings below are graded by the attack block's rule. None is an egress byte that leaves, a
socket under `--offline`, a send that changes the exit code of a sound install, a looser suppression,
an endpoint that reflects or distinguishes, a test green at the pre-sha, or a false sentence on a
`/legal/*` page. Two of them (N1, N4) are the ones a customer or an IT reviewer will meet first.

## Blockers

None.

## Non-blocking findings (ordered by weight)

### N1 (engine, reachable, carried FA-N5 / FA-N4 - re-measured): a mis-cased opt-out key is accepted silently and the record is sent

`criteria.yaml` with `egress: {Telemetry: false, suppression: {...}}` (capital T) through `cli.main`
with a recording transport: `rc=0 transport calls=1`, the summary line reads `telemetry sent
(http 204) to https://proofpack.globalphoenix.co.uk/api/telemetry`. The same run with
`telemetry: false` → `transport calls=0`, `telemetry skipped (egress.telemetry: false); nothing
was sent`. `suppression: {min_n: 10, min_N: 1}` → `rc=0`, sent, `Thresholds(10, 5, 5)`;
`min_n: 1e3` (YAML float `1000.0`) → `rc=0`, sent (JSON Schema `integer` admits `1000.0`;
`thresholds_from_declarations` would raise H08 on it but is not called at run time). YAML 1.1
booleans behave: `telemetry: no` and `telemetry: off` → skipped; `telemetry: n` → `HALT H08`
(string). `egress: null`, `egress: []`, `egress: 'off'`, `suppression: null`, `suppression: []` →
`HALT H08`, exit 3, nothing written, 0 transport calls.

The console does say `telemetry sent`, so this is not silent to a reader of the console; it is
silent to the file the customer authored. The typed refusal exists for a wrong *value* and not for
a wrong *key*. The repair carried it to lane E as `criteria_schema.json`'s `additionalProperties:
false` under `egress` and `egress.suppression` (one line each, plus a test feeding `Telemetry:
false`). I would land it before the merge rather than after: it is the one line here a customer
will actually write. Repro: section 8 of `attack_r2_engine.py` in the scratchpad.

### N2 (engine, reachable, `sentence_violation`): "a 5 s timeout" is a per-read socket timeout; a receiver that drips bytes held `send()` for 27.0 s and the send counted as delivered

A loopback `http.server` whose `do_POST` writes `HTTP/1.1 204 No Content\r\nContent-Length:
0\r\n\r\n` one byte at a time with `time.sleep(0.6)` between bytes (45 bytes):
`telemetry.send(payload, url=..., transport=urllib_transport)` → `SendResult(sent=True, status=204,
reason_code=None)` after **27.0 s**, `TIMEOUT_S = 5.0`. Each `recv` completes inside 5 s, so the
socket timeout never fires. The tests feed a server that never answers (`[hang] 5.07 s`, lens 1;
`send()` alone 5.03 s today) and none that answers slowly.

Sentences this falsifies as a reader takes them: `telemetry.py` "makes one HTTP request with a 5 s
timeout"; `egress_channels.json` `limits` / `/trust` "One HTTP request with a 5 s timeout";
`/docs/egress` "a 5 s timeout"; `/legal/dpa` 2.1 "a 5 s timeout". Each is true of the parameter
and false as a bound on how long a run waits. Not a leak: the record is the same ten keys; the
effect is that a hostile or broken receiver (a captive portal that streams its login page slowly
qualifies) can hold `proofpack run` open for as long as it drips. Repair: a wall-clock deadline on
the whole request (read the response under a total deadline, or reword every copy to "a 5 s socket
timeout on each read; a slow receiver can hold the run longer" and cite the drip test).
Repro: section 2 of `attack_r2_engine.py`.

### N3 (engine, not reachable in a sound install, `sentence_violation`): `send()` raises, and the run's exit turns into 5 after `run.json` is written, when the schema resource cannot be loaded

`proofpack.egress.build.egress_schema` replaced by a function raising `OSError("egress_schema.json
unreadable")`, then through `cli.main` (F19 cohort, telemetry on, recording transport):
`rc=5`, `run.json exists=True`, `transport calls=0`, stderr `internal error: OSError:
egress_schema.json unreadable`. Direct: `telemetry.send(payload, transport=Rec(204))` → `RAISED
OSError`. Cause: `send()`'s first `try` catches `(EgressError, WhitelistError)` only, and
`run_telemetry` catches `EgressError` around `build_payload` only; `egress_schema()` (and
`jsonschema.Draft202012Validator(sub)`, and `_resolve`'s `KeyError` on a dangling `$ref`) are
outside both. Reach: a corrupt or missing `egress_schema.json` in the installed package - a broken
wheel, not a customer input; `doctor` reports that file loads. The sentences it falsifies are
unconditional: `telemetry.py` "``send`` never raises an ``Exception`` to the caller" and "the exit
code is the run's"; `cli.py` "the result changes nothing below - not the exit code, not the files";
`errors.py` W16 "never a change of exit code". A transport that returns `'abc'`, `None`, `204.9`,
`True`, `299`, `199` is classified (`transport_error` / `transport_error` / sent 204 / `http_error`
status 1 / sent 299 / `http_error` 199) and does not raise; `KeyboardInterrupt` passes through by
design. Repair: widen the first `except` to `Exception` → `payload_invalid` (a typed reason,
`schema_unavailable`, would be better than borrowing `payload_invalid`), and the same around
`build_payload` in `run_telemetry`; a test that monkeypatches `egress_schema` to raise `OSError`
and asserts `rc == EXIT_OK` and one `[W16]` line. Repro: section 3 of `attack_r2_engine.py`.

### N4 (site, reachable, `sentence_violation`, carried RG-N10 / RG-N11 / decision 8 - the specific facts were not stated): `/trust` publishes the a0c9abc **skeleton** as "the schema the engine validates its own outbound payload against"; its `licence_id` pattern rejects every id the site issues

`dist/trust/index.html` at `2b5c7de` carries, in the published schema JSON, `"status": "skeleton"`
(1 occurrence) and `licence_id` pattern `^L-[A-Za-z0-9-]+$`; the runner-telemetry row says
`Exists today? Yes`; the FAQ says "The exhaustive list of what may leave is that table, and it is
generated from the schema the engine validates its own outbound payload against." The only sender
that exists (`0cf9ba5`) validates against a `$defs/telemetry` in which, descriptions stripped,
**eight of the ten properties differ** from the published copy: `licence_id` `^lic_[A-Za-z0-9]{1,60}$`
+ null (published: string only, `^L-...`); `halt_code` enum of 19 with `E01`, `S01`-`S05`
(published: 13); `platform` `^[a-z][a-z0-9_.-]{0,62}-cp3[0-9]{1,2}$` (published:
`^[a-z0-9_]+-[a-z0-9_]+-cp3[0-9]{2}$`, which `macosx-14.0-arm64-cp312` fails); `run_id` and
`timestamp` by pattern + maxLength (published: `format`, which `jsonschema` does not enforce by
default); `engine_version` pattern (published: unconstrained); `duration_s` maximum;
`manifest_sha256` maxLength. `required` is identical in both (the ten keys), so the *field list*
the row renders is right; the *schema* the page prints is not the one the payload is validated
against, and a reader who validates a genuine record (`licence_id: lic_test0000…`) against the
published schema gets a failure on `licence_id`.

`/legal/dpa` 2.1 reads "the schema is published verbatim on /trust … and the receiver …
validates the record against the same schema". Each clause holds on its own reading (a0c9abc's
copy is published verbatim; the receiver's copy at `0cf9ba5` equals the sender's); together they
tell an ICO reader that `/trust` shows the receiver's schema, and it does not. I grade this
non-blocking: the field list, the only thing the DPA enumerates, is the same in both copies; the
`state_note` beside the row says the two copies exist; the repair's DEC-43 section says they
become one at the pin move (S4, day 10). Until then the FAQ sentence is false. One-clause repair
on `/trust` ("generated from the schema vendored at the engine commit the site pins, whose ten
keys are the ten the sender validates against; the patterns the sender applies are the stricter
ones in `functions/_lib/telemetry-schema.mjs` until the pin moves") and the same qualifier in
DPA 2.1. Repro: `grep -o '"status": "skeleton"' dist/trust/index.html; grep -o '\^L-' dist/trust/index.html`;
the property diff is in the scratchpad transcript.

### N5 (engine, not reachable at launch - no code path sends the aggregates document): a fairness gap stays unsuppressed when the *reference* level is the small cell, and it carries the small cell's estimate by subtraction

F19 document (`fairness.attribute sex`, `reference_level M`, `reference_rule declared`, one gap
row for `F`). The `M` subgroup row edited to `n 7, events 2` and `build_aggregates` run: `M`'s
own cells are all `suppressed: true`; the five gap cells for `F` are **not**:
`('auroc_gap', 'F', suppressed False, n 400, est 0.0868787379478082)`, `('tpr_gap', 'F', False,
63, 0.0825892857142857)`, `('fpr_gap', 'F', False, 134, -0.04976913991195109)`, `('ppv_gap', 'F',
False, 80, 0.08871951219512186)`, `('npv_gap', 'F', False, 118, 0.039830508474576254)`. `F`'s own
`sensitivity` cell is unsuppressed, so `TPR_M = TPR_F - tpr_gap` to full float precision - the
suppressed cell's estimate leaves in two unsuppressed bytes. Mechanism: `build_aggregates` decides
a gap row by the *level's* row (`rows_by_level.get((f_attr, level))`), and the engine's gap Number
carries `n` (the two arms summed, 63) with `k`, `n_pos`, `n_neg` all `None`, so
`suppress.number_counts` cannot see the small arm. The reference is declared by the customer
(`reference_rule: declared`), so a small flagship site as reference is an ordinary declaration.
D1 section 6 lists "fairness gap rows" as a cell; the rule as written does not say which row's
counts decide a gap. Repair when the aggregates path is wired (a rule change to D1, its own lens):
a gap is suppressed when either its level's row or the reference's row is suppressed. Repro:
section 5 of `attack_r2_engine.py`. `x-proofpack.suppression_cells` and `suppress.py`'s cell
list are not false as written; they are silent on this case.

### N6 (engine, not reachable at launch, carried FA-N11 - sharpened): an `attr_*` header that is itself an identifier is serialised

CSV column `attr_nhs4857773456` (values `ward1` / `ward2`) through `cli.main` with a confirmed
mapping: `rc 0`; `run.json` subgroup attributes `['age', 'attr_nhs4857773456', 'sex', 'site']`;
`build_aggregates` bytes contain `attr_nhs4857773456` (levels pseudonymised to `Level A`,
`Level B`); the telemetry bytes do not contain `nhs4857773456`. `io/schema.py` line 366 makes the
`attr_*` header its own canonical name. D1 section 6's "original headers never serialised" is
false for this class by construction; the schema's `identifier` description now says so (the
repair); the design rule and the code still disagree. Record for the day the aggregates path is
wired.

### N7 (both, merge risk with E8 - measured): the evening merge conflicts in two files, and the main working tree touches two more the branch touches

`git merge-tree --write-tree 29fc04e 0cf9ba5` (run from my worktree; the main tree untouched):
`CONFLICT (content): Merge conflict in scripts/mutation_sweep.py` and `CONFLICT (content): Merge
conflict in src/proofpack/cli.py`, exit 1; `ci.yml`, `pyproject.toml`, `run.py` auto-merge.
E8's working-tree diff against `7b2ca2a` (read only) has `cli.py` hunks at `@@ -442,11 @@`
(after `cmd_map`), `@@ -465,7 @@` and `@@ -477,6 @@` (inside `cmd_run`); the branch's are
`@@ -441,12 @@`, `@@ -456,16 @@`, `@@ -477,6 @@` - the same lines. `git status` in the main tree
also shows ` M src/proofpack/errors.py` and ` M scripts/mutation_sweep.py` uncommitted (E8's
`errors.py` hunk is at line 17, `EXIT_INTERNAL`; the branch's are at 61 and 77, so that file
should merge). Files the branch touches outside the task's list: `src/proofpack/doctor.py` (+9),
`tests/conftest.py` (+37, the `ImportError` guard now lets a tree without `egress/` collect),
`tests/test_doctor_cli.py` (+4), `scripts/ci_namespace_run.py` (new), `handoffs/` (the two lens-1
notes); `cli.py` is +47 not one call site (the `TELEMETRY_SENTENCE` constant, the summary line,
the `--json-log` block, `main(transport=)`). Whoever merges should expect to resolve `cmd_run` and
the sweep's mutant list by hand.

### N8 (site, reachable once deployed, carried FA-N8 / lens-1 N9 - now exercised): `looksLikeDuplicate` answers 204 and stores nothing when an upstream error message merely contains `409`

A loopback PostgREST stand-in (`SUPABASE_URL` pointed at it, `SUPABASE_SERVICE_KEY` set) answering
the insert with `400 {"code":"PGRST102","message":"row too large: 4096 bytes"}` →
`handleTelemetry` → **204**, no row (the message matches `/409/` inside `4096`). The same stand-in
answering a real duplicate (`409`, `23505`) → 204 (correct); `500` with the timestamp value in its
message → `500 {"error":"not stored"}`, the value not echoed; unreachable upstream (port 9) → 500
`not stored`. Also measured on the ok path: upstream traffic is exactly `GET
/rest/v1/runs?run_id=eq.<uuid>&limit=1` then `POST /rest/v1/runs` with a body of the ten keys
in schema order; of the client headers I sent (`cf-connecting-ip`, `x-forwarded-for`, `cookie`,
`x-customer-header`, `user-agent proofpack-telemetry/1`) none reached upstream (the one string hit,
`proofpack-telemetry/1`, is the body's `schema` value, not the user-agent). Repair: match the
status the adapter puts in its own message (`supabase POST /runs: 409`) or the PostgREST `code`
field, not a bare `/409/`. Repro: section 5 of `attack_r2_endpoint.mjs`.

### N9 (site, deploy ordering, carried RG-N6 / lens-1 N12): the pages disagree about the `runs` table, and the deploy will publish before the table exists unless Josh applies the migration first

`/legal/sub-processors` (rendered): "as of 2026-09-23 it had not been applied, the table did not
exist and no telemetry record was held". `/trust` runner-telemetry row (rendered): "stored in the
`runs` table as the ten fields plus a receipt time … and answered 204", `Exists today? Yes`.
`deploy.yml` runs `check:bytes`, `check:keys`, `build`, `check:links`, `check:schema`,
`check:pricing`, `check:egress`, `check:validation`, `check:seo`, `test:unit`, then `Publish`
(`wrangler pages deploy dist`); it does not run `check:legal` (the CI `legal-gate` job does), so
`2b5c7de` deploys on push. Live today: `GET https://proofpack.globalphoenix.co.uk/api/telemetry`
→ 404; `POST` → 405 (see "one thing I did" below). After the push and before the migration, a
genuine record meets PostgREST's 404 for the missing relation → the Function answers 500 `not
stored` → the runner prints `[W16] telemetry not sent (http_error, http 500)`. Needs-from-Josh 1
in the repair note stands. The sub-processors sentence "the table did not exist" is asserted by a
builder who says it held no credentials; nobody in either repository measured it (see "could not
check").

### N10 (site nit, `sentence_violation`): `/docs/egress` dates the redirect rule to 22 September

"The sender landed on 22 September 2026 (engine branch `a-p2-egress`, `src/proofpack/egress`):
one HTTP request after `run.json` is written, a 5 s timeout, a redirect answer (3xx) not
followed, …". `git log -- src/proofpack/egress/telemetry.py` on the branch: the no-redirect
opener is `47d1aeb 2026-09-23 01:38:30 +0100`; at `4cad727` (22 September 14:41) the opener
followed a 301/302/303 (lens 1 measured it). The DPA's HTML comment says "repaired 2026-09-23";
the public sentence does not. One clause.

### N11 (engine, record): the proxy variables, the FreeBSD platform tag, and the sender's request headers

- `HTTPS_PROXY=http://127.0.0.1:<recorder>` with the real URL and the real transport:
  the recorder receives one connection whose first line is `CONNECT proofpack.globalphoenix.co.uk:443
  HTTP/1.1` and no payload bytes; `send` → `transport_error` (the recorder answers 502).
  `https_proxy` the same. Under `--offline` with the variable set: `rc=0`, 0 connections,
  `telemetry skipped (--offline)`. So `urllib` does read an environment variable that decides
  which host the TCP connection goes to (the proxy learns that a ProofPack runner exists and the
  endpoint's hostname; the body stays inside the TLS tunnel). The docstring's "reads no
  environment variable for one [a url]" is true as worded; "one HTTP request" is one request
  through a CONNECT tunnel. Record for the trust page's IT reader: corporate proxies apply.
- `platform: freebsd-13.2-RELEASE-amd64-cp312` (what `sysconfig.get_platform()` yields on FreeBSD:
  the release is not lower-cased) → the site answers `400 invalid value for key: platform`, and
  the engine's own whitelist would refuse it first (`payload_invalid`, never sent). Not a leak; a
  platform whose telemetry silently never arrives. `engine_version 1.0.0+local` the same.
- The full request the sender emits (raw loopback recorder): `POST /api/telemetry HTTP/1.1`,
  `Accept-Encoding: identity`, `Content-Length: 374`, `Host`, `Content-Type: application/json`,
  `User-Agent: proofpack-telemetry/1`, `Connection: close`, then the 374-byte body. No other
  header. `grep -rn "environ\|getenv" src/proofpack`: `PROOFPACK_HOME`, `LOCALAPPDATA`,
  `PROOFPACK_LICENCE` only.

### N12 (site, environment - record): `test:e2e` failed on its first run in the worktree and passed on the second; `test:unit` skips two, not one

First `npm run test:e2e` in `site-2b5c7de` (straight after `npm run build`): `6 failed`
(`demo-degrade` CDN-reachable, `demo-har`, `demo-screen2`, both `parity` tests,
`validation-unverified`), `3 passed (18.9s)`, exit 1 - my `tail -12` cut the reasons and I did
not recover them. Second run, unchanged tree: `9 passed (35.5s)`, exit 0. Every failing test is
a demo/Pyodide test, none touches A-P2; I record it as a flake I could not characterise.
`test:unit`: `658 / 656 pass / 0 fail / 2 skipped`; the skips are the gps-automation vendored
copy (`GPS_AUTOMATION_DIR` not set here) and the `telemetry-schema.mjs` comparison (no checkout
at `0cf9ba5` reachable from the site worktree) - both environment; with `PROOFPACK_ENGINE_DIR` at
`eng-0cf9ba5`, `tests/day8-telemetry.test.mjs` is `20 / 20 / 0 skipped`.

## One thing I did that the reader should know

During the proxy probe (N11) I set `HTTP_PROXY` (not `HTTPS_PROXY`) and called `send` with the
real transport and the real URL; `urllib` does not route an `https://` URL through `HTTP_PROXY`,
so that one call went to the live site: `SendResult(sent=False, status=405, reason_code='http_error')`
in 0.12 s. The body was the F19 fixture's record (`licence_id lic_test0000000000000000000000000001`,
fixture run_id, no customer data); Cloudflare Pages answered 405 for a POST to a path with no
Function, and nothing was stored (no Function is deployed). I did not repeat it. It is also the
measurement behind "POST → 405" in N9.

## Sentences I refused to write

- "the send changes the exit code" - true only with the schema loader made to raise (N3); on
  every sound run measured (204, 500, 413, five 3xx codes, hang, closed port, bad certificate,
  drip) `rc` equalled the offline run's and the normalised `run.json` was equal.
- "the endpoint distinguishes a known licence" - it never reads `licence_id` except to validate
  it; 300 requests each: unknown-id median 0.047 ms, same-id 0.056 ms, duplicate run_id 0.051 ms
  (memory adapter; Postgres not measured).
- "a client header reached Supabase" - the one needle hit upstream, `proofpack-telemetry/1`, is
  the body's `schema` value; the request's `user-agent` upstream is node's.
- "a 4,097-byte body without a length passed" - my first construction was 4,095 bytes (my
  arithmetic); redone at exactly 4,097 → 413 with and without `content-length: abc`; 4,096
  bytes of valid JSON → 400 `unknown key`.
- "a UTF-16 body was accepted" - my first case sent UTF-8 bytes under a `charset=utf-16` label
  (204: the parameter is ignored); a real UTF-16LE body → 400 `body is not JSON`.
- "the two-arms rule leaks FN below 5" - measured the reverse: `sensitivity n 50 k 48` (FN 2),
  `specificity n 60 k 58`, `accuracy n 110 k 108` → suppressed; `n-k = 5` → kept.
- "the gap sentence in `suppress.py` is false" - it lists the cell; it does not say which row
  decides it (N5 is a rule gap, not a false sentence).
- "the site gate chain is red" - `test:e2e` was red once and green once (N12); I report both.

## What I could not break (with the bytes and figures)

- **Every egress byte.** F19 through `cli.main` with a recording transport: 374 bytes, exactly
  the ten keys, 0 errors under `jsonschema.Draft202012Validator` against `$defs/telemetry` and
  against the root `oneOf`; the lens-1 `attack_payload.py` re-run at `0cf9ba5`: 424 needles
  (every header, every site level, `St Mary's`, `Königsberg` both spellings, `Royal Free`, the
  note header and value, the ledger key, the licence signature and its base64 payload, 40 bytes
  of `mapping.json`, the serialised `pseudonyms.json` map, the criterion date, `started`, the
  model name, all 400 distinct ROC thresholds, every `YYYY-MM-DD` in `run.json`) - telemetry
  hits: today's date inside the payload's own `timestamp` only; aggregates hits: the canonical
  names `sex`, `age`, `site` only. The 7-row `St Mary's` cell: 7 cells all null. Synthetic cohort
  (5,000 rows): 377 bytes, 12 needles, no hit. The captured bytes fed verbatim to the site's
  `handleTelemetry`: 204, one row of `schema,licence_id,run_id,engine_version,platform,
  manifest_sha256,duration_s,halt_code,row_count_bucket,timestamp,id`; posted again: 204, still
  one row. `validateTelemetry` behind a `Proxy`: it reads exactly the ten properties.
- **Constructed documents (lens-1 set re-run, plus mine).** `site` levels `Site A`, `7`, the
  licence id → `Site A…E`, literals absent; `sex` `St Mary's` → `Level A`; the three token-shaped
  values (`2026-01-05`, `NHS1234567890`, `7`) pass verbatim as the repair records; `Unknown/missing`
  kept. Row `n 10 / events 5 / non-events 5` → not suppressed; `9/9`, `10/4`, `10/6` →
  suppressed; bin `events 4` or `n 9` → null; 2x2 `fp+tn = 4` → null; zero subgroups → 20
  overall cells; `"roc"` absent. Leaves: `number.est = {'roc': …}` / `[0.5]` → refused
  (object / array not admitted); `method 'wilson; St Mary's'`, `metric_id "St Mary's"` → enum
  refused; `level 'Site A '`, `'Level ZZZZ'` → pattern refused; `number.n = 9` and `k = -1`
  unsuppressed pass the whitelist and fail `jsonschema` (`minimum`); `two_by_two tp = 4`
  unsuppressed passes both (the schema has no rule for the arms - D1 N13); `est nan` / `inf`
  pass both (a `duration_s nan` is refused earlier by `canonical_json` in `write_run`, so it
  cannot reach the payload). `build_payload`: licence id of 300 chars, `lic_abc\n`, `St Mary`,
  `duration -1 / 1e12 / None`, `platform` with `\n`, `engine_version St Mary`, upper-case
  `run_id` → `EgressError`; `halt_code H99 / W16` refused, `H08 / E01 / S05` built; `rows_read
  -1 / None / 10.0 / True` refused; `licence_status refused / missing / OK / ""` → `licence_id
  null`; buckets `0, 999 → <1k`, `1000 → 1k-10k`, `1e9 → >100k`.
- **The socket.** `run`, `compare`, `map --yes`, `doctor`, `licence show`, `--offline licence
  verify`, `--offline licence install` under a trap on `socket.socket.__init__`, `getaddrinfo`,
  `create_connection` with a transport that raises: `sockets=[]` in every case (`map --yes`
  H07 exit 3 and `licence install <installed path>` `SameFileError` exit 5 are pre-existing at
  `7b2ca2a`; `licence verify FILE --offline` and `fixtures --offline` argparse exit 2, likewise).
  `egress.telemetry: false`, no flag, the real transport left in place: `sockets=[]`, the skip
  line. The E7 fixture (`e2e_shell`, `egress.telemetry: false` in its criteria) with
  `socket.socket`, `getaddrinfo`, `create_connection` raising and no flag: `rc 4`, `socket calls
  []`, the skip line; with `--offline --json-log`: `{"exit_code": 4, "licence_status": "refused",
  "warnings": [], "telemetry": {"skipped": "--offline"}}`, the pack holding `ingest_report.json
  pseudonyms.json run.json`. Real transport against loopback (fresh `PROOFPACK_HOME` per run):
  204 → `telemetry sent (http 204)`; 500, 413 → W16 `http_error`; **301, 302, 303, 307, 308 →
  W16 `http_error, http NNN`, `main_got=1`, `other_host_got=[]`** (the lens-1 blocker, closed);
  hang → W16 `timeout` at 5.07 s; closed port → `connection_refused` 2.10 s; self-signed
  certificate → `transport_error`, 0 bodies received; `run.json` deleted from inside the
  transport → the run still prints `run written:` and exits 0. `rc=0` and normalised `run.json`
  equal to the offline run in all cases.
- **The customer's block.** `min_n 9, 0, -1, "10", 10.5, true`, `telemetry "false", 0, null`,
  `egress null / [] / 'off'`, `suppression null / []` → `HALT H08`, exit 3, no pack, 0 transport
  calls; `min_n 1000000` → `Thresholds(1000000, 5, 5)`; `telemetry no / off` → skipped.
- **The endpoint.** `GET/HEAD/OPTIONS/PUT/DELETE/PATCH` → 405 `allow: POST` with `cache-control:
  no-store` and the five security headers; `post` / `Post` (the `Request` constructor
  normalises) → 204; `TRACE` / `CONNECT` are refused by the runtime's `Request`; `onRequest()`
  → 405. Bodies: BOM + JSON → 204 (the decoder strips it); real UTF-16LE → 400; duplicate
  `licence_id` key (bogus first, real last) → 204, last wins; 2,000-deep array → 400 `body must
  be a JSON object`; 600-deep object → 400 `unknown key`; declared `content-length: 4097` with 20
  bytes → 413; `content-length: -5` → 204; empty / `null` / `"string"` → 400; `text/plain` and no
  content-type → 415; `application/json-patch+json` and `multipart/form-data;
  boundary=application/json` → 204 (FA-N8, carried). Values: `lic_` + 60 letters → 204, 61 →
  400; SQL in `licence_id`, `St Mary's`, upper-case / newline `run_id`, nil uuid (204),
  `1.0.0+local` (400), `platform` 63+6 chars (204) / 64+6 (400), upper-case hex (400),
  `duration_s -0` (204) / `604800` (204) / `604800.5`, `"1.5"`, `1e308` (400), `halt_code H10`
  (204, stored) / `W16` / `h08` (400), `>100k ` (400), lower-case `t`/`z` (400),
  `2026-99-99T99:99:99Z` (204 on memory; carried), `+01:00` (400), `proofpack-telemetry/2` and
  `proofpack-aggregates/1` (400); extra `ip`, `received_at`, `id`, `__proto__` → 400 `unknown
  key`, `Object.prototype` not polluted; 9 rows stored, none with a key outside the ten plus `id`.
  Every 400 names a schema key only; no response echoed any input string; no `set-cookie`; no
  `access-control-*`.
- **The gates.** Engine worktree at `0cf9ba5`, `PYTHONPATH` forced: `873 passed, 1 skipped, 1
  xfailed in 75.40s`; `-m ap2` 85, `-m day8` 85, `-m day7` 139, `-m day6` 285, `-m day5` 54,
  `-m day4` 182, `-m day3` 29 + 1 xfailed, `-m day2` 40, `-m day1` 59 + 1 skipped; `ruff check`
  clean; `ruff format --check` `123 files already formatted` (the note says 121; the worktree is
  clean, `git status --short` empty, and I did not find the two); `doctor --offline` exit 0;
  `mutation_sweep.py --marker ap2` **16 planted, 16 killed, 0 survived; 68 s**. Pre-sha: the
  `0cf9ba5` test files against `eng-4d61b6e/src` → **6 failed, 79 passed** (the whitelist newline
  test, `send` newline test, the redirect test at 301/302/303, the CLI 302 test); against
  `eng-a0c9abc/src` → 3 collection errors (no `egress/`). Site worktree at `2b5c7de`,
  `PROOFPACK_ENGINE_DIR` at `a0c9abc`: `check:bytes` 276 files OK; build 30 pages; `check:links`
  1242 links OK; `check:schema` OK; `check:pricing` 37 figures 0 errors; `check:egress` 0 errors
  (`vendored canonical=1c914910cae38b8c…`, `engine copy compared`); `check:validation` OK;
  `check:seo` 0 errors 5 warnings; `check:keys` `pp-2026-09 live`; `test:unit` 658 / 656 / 0 / 2;
  `test:e2e` see N12; `check:legal` red by design (2 of 2). Pre-sha: `tests/day8-ap2-repair1.test.mjs`
  in the built `b8242c1` worktree → **5 / 0 pass / 5 fail**; FA-B4 there → 1 fail (`declares
  2026-09-21, last changed 2026-09-23`). Line endings: every touched site file `i/lf w/lf`; every
  new engine file `i/lf w/crlf`.
- **The drift gate.** `src/data/egress_schema.json` LF-normalised equals the engine's file at
  `a0c9abc` (`sha256_lf c98b85aec4a1de89…`) and differs from `0cf9ba5` (`58fdad367c2f6b34…`) and
  `4d61b6e` (`49225b6011a75e19…`). `PROOFPACK_ENGINE_REQUIRED=1 npm run check:egress` at `a0c9abc`
  → `0 error(s)`; at `0cf9ba5` → `FAIL the vendored egress schema has DRIFTED`, exit 1. So at the
  branch merge into engine `main` the site's gate and `egress-drift` job stay green (they compare
  against `ENGINE_REF`), and at the pin move they go red until the copy is re-made - as the note
  says. `functions/_lib/telemetry-schema.mjs` regenerated from `eng-0cf9ba5` by
  `scripts/vendor-telemetry-schema.mjs` equals the committed file byte for byte (sha
  `0cf9ba5fb603…`, canonical `f323709c97c59f77…`).
- **The lens-1 blockers.** FA-B1: no row reads "since 22 September 2026" (`AP2R1-B1` ×2 pass).
  FA-B2 / RG-B1: `DATE = '2026-09-23'`, FA-B4 green, the footer reads `Last updated 2026-09-23.`.
  RG-B2: the FAQ names the three entry points and "had not run anywhere as of 23 September
  2026" (its date for `test_offline.py`, 22 September, is the file's first commit `4cad727
  2026-09-22 14:41:47`). RG-B3: no `def test_` line carries the refused phrases. The branch is
  not on any remote (`refs/remotes/origin/{HEAD,main,a-p1-mapper}` only), so "had not run
  anywhere" is consistent with what this machine can see.

## What I could not check

- The `offline-namespace` job (`unshare -rn`): no Linux with Python here; the branch is unpushed,
  so it has not run. `[unverified]`, as every copy of the sentence now says.
- Postgres: the `409` / `23505` text, the `timestamptz` refusal of `2026-99-99`, the unique-index
  race and timing - measured against a loopback stand-in and the memory adapter only.
- Whether the `runs` migration has been applied to the Supabase project: no credentials here;
  the sub-processors row asserts it had not been as of 2026-09-23 and nobody measured it.
- Cloudflare's routing of a module exporting both `onRequest` and `onRequestPost`: no `wrangler`
  in `node_modules`; `functions/api/checkout.js` uses the same pair and is live.
- The reasons for the first `test:e2e` failure (N12): my own `tail` discarded them.
- The live deploy of `2b5c7de` (unpushed; today the path answers 404/405).

## Worktrees

Removed at the end of this session (`git worktree remove --force` on the six paths; the two
`node_modules` junctions deleted as links first). The attack scripts (`attack_r2_engine.py`,
`attack_r2_endpoint.mjs`) and their outputs stay in `scratchpad/lens-AP2-r2-fresh-attack/`; the
lens-1 scripts were re-run from `scratchpad/lens-AP2-r1-fresh-attack/` and their outputs are
`rerun_attack_socket.txt` and `rerun_attack_payload.txt` beside mine. The temporary run
directories under `%TEMP%\lens2_eng_*` and `%TEMP%\lens_*` hold fixture data only.
