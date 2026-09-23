# A-P2 lens 1 (fresh attack) — egress, telemetry, `--offline`, `/api/telemetry` (build day 8, lane A; 23 September 2026)

Engine `4d61b6e` (branch `a-p2-egress`, from `7b2ca2a`); site `b8242c1` (main, from `994f460`).
All probing in detached worktrees under the session scratchpad (`lens-AP2-r1-fresh-attack/`:
`eng-4d61b6e`, `eng-7b2ca2a`, `eng-a0c9abc`, `site-b8242c1`, `site-994f460`), `PYTHONPATH`
forced and proved (`import proofpack` printed `...\lens-AP2-r1-fresh-attack\eng-4d61b6e\src\proofpack\__init__.py`
in Git Bash and in PowerShell 5.1; without it the same command prints lane E's main tree).
The engine's main tree was not touched. Nothing was committed. Every figure below was
measured in this session.

## Verdict: **FAIL** — one blocker (a false legal sentence on `/legal/sub-processors`), one deploy-red unit failure the note's figures did not see, and one sentence about the sender ("one attempt", "at most one outbound call") that a 301/302/303 answer falsifies.

The egress core held under every counter-example I could construct: no name, header, threshold,
date, row value, ledger key, signature or map byte reached the captured telemetry bytes; every
`--offline` command opened zero sockets under a trap on `socket.socket.__init__`,
`socket.getaddrinfo` and `socket.create_connection`; the exit code and `run.json` were identical
across a 204, 500, 413, 307, 308, a hanging port (5.07 s), a closed port and a self-signed TLS
host. The blockers are on the site's legal text and the deploy, not in the bytes that leave.

## Blockers

### B1 (site, blocker, `/legal/sub-processors`): two "since 22 September 2026" sentences describe processing that has not begun and a table that does not exist

`src/content/legal/sub-processors.md` at `b8242c1` (lines 16–17):

> Cloudflare | Hosting of this site … and the six server endpoints (Functions): … **and since 22 September 2026 the runner telemetry receiver (`POST /api/telemetry`)**
> Supabase | Postgres database (…, **and since 22 September 2026 the runner telemetry records, table `runs`**) …

Measured today: `git -C proofpack-site status -sb` → `## main...origin/main [ahead 1]` (b8242c1 is
not pushed); `curl -s -o /dev/null -w "%{http_code}" https://proofpack.globalphoenix.co.uk/api/telemetry`
→ `404`; the live `/legal/sub-processors` still reads "five server endpoints". The `runs` table:
the builder's note says the migration was "Not applied by this session (no database credentials
are held here)" and lists it under needs-from-Josh; nothing in the repository applies it. So
Cloudflare does not run the receiver and Supabase holds no `runs` table, and the page dates both
to a day that has passed. As the ICO would read it, the Supabase row states a processing activity
(runner telemetry records in Supabase) that is not occurring and names infrastructure that is not
there. When B2 is fixed and the commit deploys, the Cloudflare sentence becomes true from the
deploy date (not from 22 September); the Supabase sentence stays false until the migration is
applied, and the page cannot know that date in advance.

Repro: read the two rows; `git -C C:/Users/joshs/GPS/ProofPack/proofpack-site status -sb`; the GET above.
Repair: word both rows on what exists (the receiver's code, the migration file) and add the date
the migration was applied when it is; or apply the migration and push in one move and date the
rows to that day. `sentence_violation: true`.

### B2 (site, deploy-red, record as blocker for the push, not for the bytes): `tests/day7-unlensed-repair2.test.mjs` FA-B4 fails at `b8242c1`, and `deploy.yml` runs `test:unit` before Publish

`npm run test:unit` in the `b8242c1` worktree: `tests 653 / pass 651 / fail 1 / skipped 1`. The
failure, verbatim:

```
✖ FA-B4: every page under src/pages declares a dateModified equal to the latest git date of the page and its data imports
  actual: [ 'src/pages/trust/index.astro: declares 2026-09-21, last changed 2026-09-23 (src/pages/trust/index.astro, src/data/egress_channels.json)' ]
```

`git log -1 --format=%ci b8242c1` → `2026-09-23 01:01:36 +0100`; `src/pages/trust/index.astro`
line 31 still reads `const DATE = '2026-09-21'`. The note's `653 / 652 pass` was measured by the
orchestrator "after two orchestrator edits" and before the commit, when `git log` for the page
still said 21 September. `.github/workflows/deploy.yml` checks out with `fetch-depth: 0` (line 67)
and runs `npm run test:unit` (line 182) before `Publish`, so the push of `b8242c1` does not
publish. The built `/trust` footer also reads `Last updated 2026-09-21.` for a page changed on
the 23rd. The second FA-B4 test pins `'2026-09-21'` for `dist/trust/index.html`; both move
together with `DATE`.

Repro: `cd <site worktree>; npm run test:unit 2>&1 | grep -A6 "not ok"`.
Grade: not one of the byte-level blockers in the attack block, but it stops the deploy that B1's
sentences assume; I list it here so it is not read as "carry". `blocker: false` in the structured
result; fix it before the push.

## Non-blocking findings (record-and-carry, ordered by weight)

### N1 (engine, reachable, sentence_violation): the transport follows a 301/302/303 to another host and reports "sent"

`urllib.request.urlopen` in `urllib_transport` uses the default opener, whose
`HTTPRedirectHandler` turns a POST answered 301/302/303 into a GET of the `Location` and follows
it. Measured with the real transport against a loopback `ThreadingHTTPServer` answering each
status with `Location: http://127.0.0.1:<second listener>/elsewhere`, a fresh `PROOFPACK_HOME`
per run, through `cli.main` (the wrapper hands `urllib_transport` the loopback URL and the CLI's
own body):

| answer | run exit | line printed | second listener received |
|---|---|---|---|
| 301 | 0 | `telemetry sent (http 204) to https://proofpack.globalphoenix.co.uk/api/telemetry` | `GET /elsewhere`, `User-Agent: proofpack-telemetry/1` |
| 302 | 0 | same | same |
| 303 | 0 | same | same |
| 307 | 0 | `[W16] telemetry not sent (http_error, http 307); …` | nothing |
| 308 | 0 | `[W16] telemetry not sent (http_error, http 308); …` | nothing |

The 204 the line reports came from the second listener; the body was not re-sent (a GET carries
none), so no record leaves, but a second HTTP request goes to whatever host the `Location` names,
with the engine's user agent and the customer's address, and the console says the record reached
`proofpack.globalphoenix.co.uk`. The realistic trigger is a TLS-intercepting proxy or captive
portal inside a hospital network (trusted by the OS store, so verification passes) answering 302
to a block or login page: the runner then reports `telemetry sent (http 200)`.

False sentences: `telemetry.py` module docstring "makes **one attempt**" and "nothing can quietly
point the runner at another host"; `/docs/egress` "At launch the runner makes at most one
outbound call"; `egress_channels.json` `limits` "One attempt with a 5 s timeout"; `/legal/dpa`
2.1 "one attempt after `run.json` is written". Repair: build an opener whose redirect handler
raises (or treat every 3xx as `http_error`), and a test with a loopback 302 to a second listener
asserting the listener saw nothing and the line reads W16. Repro: `attack_socket.py` section C
in the scratchpad.

### N2 (engine, not reachable at launch, sentence_violation): a customer's short strings reach the aggregates `level` field verbatim

`pseudonymise.TOKEN` (`^[A-Za-z0-9][A-Za-z0-9_.+-]{0,15}$`) lets any level of an attribute
outside `site`/`device`/`protocol`/`attr_*` pass unpseudonymised, and `io/schema.py`
`_to_attr` passes CSV values through raw, so the `sex` column's values are the levels. Through
the CLI (F19 cohort, `sex` rewritten to `1987-03-04` × 30, `NHS4857773456` × 30,
`Jane.Doe-1961` × 6, mapping forced confirmed, `--offline`, exit 0) and `build_aggregates` on
the written `run.json`: `sex levels in aggregates bytes: ['1987-03-04', 'F', 'Jane.Doe-1961', 'M', 'NHS4857773456']`;
the six-row `Jane.Doe-1961` cell is suppressed by value (`suppressed: true`) and keeps its label.
A raw date, an identifier and a name-shaped token are in an egress document's bytes.
`pseudonyms.json` holds `site` only. No code path sends the aggregates document (grep for
`build_aggregates` under `src/proofpack`: the definition and its docstring only), which is why
this is not a blocker. False sentences: `pseudonymise.py` "so no free string of the customer's
reaches the `level` field whatever column it came from"; `x-proofpack.never_serialised`
"raw dates". Repair when the aggregates path is wired: pseudonymise every non-engine level
(only `Unknown/missing` and the engine's own age bands are the engine's words), or an allow-list
of engine-made labels.

### N3 (site, deploy state): `src/content/legal/sub-processors.md` and `privacy.md` are dated ahead of the deploy — see B1; `privacy.md` itself is careful ("no record has been received as of that date") and its "Our database (the `runs` table)" describes a destination, not a fact about today.

### N4 (engine, whitelist): a trailing newline passes `licence_id` and `platform`

Python's `re.search("^…$", s)` matches before a trailing `\n`, and `jsonschema` uses the same
engine. Measured: `{**good, "licence_id": "lic_abc\n"}` → `whitelist.project` passes, `jsonschema`
0 errors, `telemetry.send` → `SendResult(sent=True, status=204)` against a recorder; the same
for `platform: "win-amd64-cp314\n"`. `manifest_sha256`, `timestamp` and `run_id` are caught by
`maxLength`. The site's JS `RegExp` (`$` does not match before a newline) answers 400. Not a leak;
the sentence "a string must match its `enum`/`const`/`pattern`" is weaker than stated. A hand-signed
licence is the only source of such an id. Repair: `\Z`, or strip and refuse control characters.

### N5 (engine, declarations): `min_n: 10.0` runs; the belt and the braces disagree

`criteria.yaml` `egress.suppression.min_n: 10.0` → `validate_dict` accepts it (JSON Schema's
`integer` admits `10.0`), the run proceeds and sends (exit 0); `thresholds_from_declarations`
on the same declarations raises `H08` (`not isinstance(declared, int)`). Not reached at run time
today (only tests call the function). `"10"`, `10.5`, `true`, `9`, `0`, `-1` → `HALT H08`, exit 3,
nothing written, 0 transport calls (measured, all seven).

### N6 (engine, `criteria_schema.json` — lane E's file): unknown keys under `egress` and `egress.suppression` are accepted silently

`{"suppression": {"min_n": 10, "min_rows": 1}}` and `{"telemetry": true, "share_everything": true}`
→ exit 0, `Thresholds(10, 5, 5)`. The root has `additionalProperties: false`; these two objects
do not. A misspelt `min_nonevent: 20` is silently the default 5. Record for E.

### N7 (engine, merge risk with E8): files outside the brief's list

`git diff 7b2ca2a 4d61b6e --stat`: `src/proofpack/doctor.py` (+9, the `network` line text),
`tests/conftest.py` (+33: an autouse fixture and a module-level `from proofpack.egress import
telemetry`, so collection of any test at a tree without `egress/` fails — measured against
`7b2ca2a`'s `src`: `ModuleNotFoundError: No module named 'proofpack.egress'` at conftest import),
`tests/test_doctor_cli.py` (+2), `scripts/ci_namespace_run.py` (new). `cli.py` +47 is more than
"one call site" (the `TELEMETRY_SENTENCE` constant, the summary line, the `--json-log` block and
the `transport` hook), `run.py` +13 writes `pseudonyms.json` inside `write_run`. `narrate/`,
`render/`, `templates/`, `claims_schema.json`, `output_schema_v1.json`: untouched (0 lines).

### N8 (site, `/trust` FAQ, sentence_violation): a job that has never run is described in the present tense

`src/pages/trust/index.astro` line 94: "its CI job runs the whole run inside a network namespace
with no network (unshare -rn), with and without the flag". The note marks the job `[unverified]
— the job has not run`; `/docs/egress` carries that caveat, the FAQ does not. Also "In the
engine's tests every socket call is made to raise" — three functions are patched
(`socket.socket`, `getaddrinfo`, `create_connection`), not every call.

### N9 (site, endpoint nits): three things the Function does that its comment does not say

- The content-type test is a substring: `multipart/form-data; boundary=application/json` → 204.
- `looksLikeDuplicate` is `/duplicate|unique|23505|409/i` on the error message: a non-duplicate
  insert failure whose message carries `409` or `unique` is answered 204 and the row is lost
  silently. Could not exercise against Postgres.
- `timestamp: "2026-99-99T99:99:99Z"` passes the pattern (204 on the memory adapter); Postgres
  `timestamptz` will refuse it → 500 `not stored`. The engine never produces it.

### N10 (engine, pre-existing at `7b2ca2a`): `--offline licence install <the installed path>` → exit 5 `internal error: SameFileError`; `licence verify FILE --offline` → argparse exit 2. Both measured at `7b2ca2a` too (E7 item 26b; the note carries the second).

### N11 (engine schema description, sentence_violation, not reachable): `$defs/identifier` says "an original header never matches because it is never looked at". For `attr_*` columns the original header is the attribute name (`io/schema.py` line 366) and it is serialised: a subgroup row with `attribute: attr_consultant_name` projects with that string in the aggregates bytes (measured; `manifest_hash` and `clinician_note` as attribute names pass the pattern too, `Patient ID` is refused).

### N12 (site, `/trust` egress table): "Exists today? Yes" for a channel whose sender is on an unmerged branch and whose receiver is undeployed. True under the manifest's own definition ("This channel exists in code today") and the `state_note` says so; premature to a reader. Nit.

### N13 (D1 design, not code): a 2x2 with `tp 4, fn 1, fp 1, tn 4` passes (n 10, events 5, non-events 5) and carries counts of 1 in the aggregates document. The rule is D1's; noting it for the day the aggregates path is wired.

## Sentences I refused to write

- "the send changes the exit code" — my first section-C run showed `rc=2` on every online case against `rc=0` offline; that was W14 (the ledger limit, one `PROOFPACK_HOME` for eleven runs), not the send. Re-run with a fresh home per run: `rc=0` in all ten cases and normalised `run.json` equal to the offline one.
- "the claims text leaked" — `'4711'` from a claim string was found in the aggregates bytes; it is inside `"ci_hi": 0.805219947113366` of an unrelated cell and is there without any claim.
- "the `started` timestamp leaked" — `manifest.started` equalled the payload `timestamp` to the second on a 0.05 s run; the payload's value is `utc_now_iso()` at the send.
- "the endpoint distinguishes a known licence" — measured only on the memory adapter (0.1 ms either way); Postgres timing was not measured.

## What I could not break (with the bytes and figures)

- **Every egress byte.** Synthetic cohort (5,000 rows) and F19 through `cli.main` with a
  recording transport: payload = exactly the ten keys, 377 / 363 bytes, validates against the root
  `oneOf` and `$defs/telemetry` with `jsonschema.Draft202012Validator`. 424 needles grepped
  against the F19 telemetry bytes and the aggregates bytes: `St Mary's`, `Königsberg`,
  `K\u00f6nigsberg`, `Royal Free`, `clinician_note`, `seen in clinic on Tuesday`, every header,
  the ledger key, the licence signature and its base64 payload, the first 40 bytes of
  `mapping.json`, the serialised `pseudonyms.json` map, every `YYYY-MM-DD` string in `run.json`,
  the model name, the criterion date and all 400 distinct ROC thresholds — the only telemetry hits
  were today's date inside the payload's own `timestamp`; the only aggregates hits were the
  canonical attribute names `sex`, `age`, `site`. The `St Mary's` row (`n 7, events 2`) is 7
  null cells; its eight Wilson bounds are absent.
- **Constructed documents.** `site` levels `Site A`, `7`, the licence id → `Site A…E`, literal
  absent; `sex` `St Mary's` → `Level A`; `Unknown/missing` kept. Row `n=10/events=5/non-events=5`
  → not suppressed; `n=9,events=9`, `n=10,events=4`, `n=10,events=6` → suppressed. Bin `events 4`
  or `n 9` → `n, events, mean_pred` null. 2x2 `fp+tn = 4` → all four null. Zero subgroups → 20
  overall cells. `"roc"` key absent. `build_payload`: licence id of 300 chars, `St Mary`,
  `duration -1`, `1e12`, `None`, `engine_version St Mary`, upper-case `run_id`, `halt_code H99`
  / `W16`, `rows_read -1 / None / 10.0 / True` → `EgressError`; `halt_code H08/E01/S05` build;
  `licence_status` `refused`/`missing`/`OK`/`""` → `licence_id null`, `ok`/`grace`/`expired` →
  the id; buckets `0, 999 → <1k`, `1000 → 1k-10k`, `1e9 → >100k`.
- **The socket.** `run`, `compare`, `map --yes`, `doctor`, `licence show`, `--offline licence
  verify`, `--offline licence install` under a trap on `socket.socket.__init__`,
  `socket.getaddrinfo`, `socket.create_connection` (stronger than the suite's, which does not
  patch `__init__`): `sockets=[]` in every case. Without `--offline`, `egress.telemetry: false`,
  the default `urllib_transport` left in place: `sockets=[]`, "telemetry skipped
  (egress.telemetry: false); nothing was sent". Real transport against loopback: 204 sent; 500
  and 413 → W16 `http_error`; hang → W16 `timeout` at 5.07 s (`send()` alone 5.02 s); closed port
  → `connection_refused` (2.13 s); self-signed certificate (CN and SAN for 127.0.0.1) →
  `transport_error`, **0 bodies received**; `run.json` deleted from inside the transport → the
  run still prints `run written:` and exits 0. Exit code 0 and normalised `run.json` equal to the
  offline run in all ten cases. A HALT (H08 looser `min_n`, H06 single-class `y_true`) → exit 3,
  0 transport calls.
- **The customer's block.** `min_n 9, 0, -1, "10", 10.5, true`, `telemetry "false", 0, null` →
  `HALT H08`, exit 3, no pack, 0 transport calls; `min_n 1000000` → `Thresholds(1000000, 5, 5)`;
  `telemetry` absent and the block absent → sent (opt-out, as D1 says).
- **The endpoint** (`functions/_lib/telemetry.mjs` via `handleTelemetry`, memory adapter):
  GET/HEAD/OPTIONS/PUT/DELETE/PATCH → 405 `allow: POST`; 4,097 bytes by declared length, by
  stream without a length, and with a lying `content-length: 10` → 413; exactly 4,096 → 204;
  a JSON array, string, null, number → 400 `body must be a JSON object`; 100-deep object → 400
  `unknown key`; `run_id` with `\n` (end and middle), licence id with SQL, 61 chars, `H99`,
  `"7"`, `proofpack-telemetry/2`, `St Mary's laptop`, 72-char platform, `duration_s "1.5"` /
  `1e12`, missing `timestamp` → 400 naming only the schema key; extra `ip`, `__proto__`,
  `constructor`, `hasOwnProperty` → 400 `unknown key`; duplicate `run_id` (same and different
  licence) → 204; unknown licence → 204; two in one second → 204, 204; db at `127.0.0.1:9` → 500
  `not stored`. No `Set-Cookie`, no `Access-Control-*`, `cache-control: no-store` and the five
  security headers on every response; no needle (`St Mary's`, `drop table`, `lic_x`, `1.2.3.4`,
  `H99`) in any body. `onRequest()` → 405.
- **The gates.** Engine worktree: `862 passed, 1 skipped, 1 xfailed in 79.83s`; `-m ap2` 74,
  `-m day8` 74, `-m day7` 139, `-m day6` 285, `-m day5` 54, `-m day4` 182, `-m day3` 29 + 1
  xfailed, `-m day2` 40, `-m day1` 59 + 1 skipped; `ruff check` clean, `ruff format --check`
  121 files; `doctor --offline` exit 0 (both shells); `mutation_sweep.py --marker ap2` **16
  planted, 16 killed, 0 survived; 80 s**; `--list` 16 ap2 + 34 day5 + 112 day6 + 25 day7;
  `--marker day7` **25 planted, 25 killed, 0 survived; 112 s**. Pre-sha: the three ap2 test files against `7b2ca2a`'s `src`
  fail at collection (`ModuleNotFoundError: proofpack.egress`); `day8-telemetry.test.mjs` at
  `994f460` → 1 test, 0 pass, 1 fail. Site worktree, `PROOFPACK_ENGINE_DIR` at `a0c9abc`:
  `check:bytes` 275 files OK; build 30 pages; `check:links` 1241 links OK; `check:schema` OK;
  `check:pricing` 37 figures 0 errors; `check:egress` 7 channels, 0 errors; `check:validation`
  OK; `check:seo` 0 errors 5 warnings; `test:e2e` 9 passed (43.0 s); `check:legal` red by design
  (2 of 2 placeholder pages); `check:keys` `pp-2026-09 live`; `day8-telemetry.test.mjs` 19 + 1
  skipped at `a0c9abc`, 20/20 with the engine dir at `4d61b6e`.
- **The drift gate.** `src/data/egress_schema.json` equals the engine's schema at `a0c9abc`
  byte-for-byte after CRLF→LF (the worktree is CRLF), and differs from `4d61b6e`'s;
  `functions/_lib/telemetry-schema.mjs` names `4d61b6e` and its `$defs/telemetry` is what the
  20/20 test compares. `check:egress` with `PROOFPACK_ENGINE_DIR` at `4d61b6e` → red ("/trust
  would publish a schema the engine does not use. Re-copy schema/egress_schema.json into
  src/data/…"): that is what the pin move looks like without the copy, and the note's
  decision 8 names the copy. At merge of the engine branch nothing on the site changes (the
  gate compares against `ENGINE_REF`, still `a0c9abc`).

## What I could not check

- The `offline-namespace` CI job (`unshare -rn`, then `sudo unshare -n`) has never run; no Linux
  with Python is reachable here (WSL holds `docker-desktop` only). `[unverified]`, as the note says.
- Cloudflare Pages routing when a module exports both `onRequest` and `onRequestPost`: no
  `wrangler` in the site's `node_modules`. Wrangler's file-path router sorts method-specific
  routes before the catch-all, so POST reaches `onRequestPost` and everything else 405; not
  measured against the real runtime.
- Postgres behaviour of the insert (the unique index race, the `409`/`unique` message match, the
  `timestamptz` refusal, timing of a duplicate vs a new row): the memory adapter only.
- The live deploy of `b8242c1` (not pushed; it would fail at FA-B4, B2).

## Worktrees

Removed at the end of this session (`git worktree remove --force` on the five paths, the two
`node_modules` junctions deleted as links first). The attack scripts (`attack_socket.py`,
`attack_payload.py`, `attack_endpoint.mjs`) stay in the scratchpad for the repair lens.
