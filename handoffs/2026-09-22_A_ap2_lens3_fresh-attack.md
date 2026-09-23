# A-P2 lens 3 (fresh attack) - egress, telemetry, `--offline`, `/api/telemetry` (build day 8, lane A; repair round 2; 23 September 2026)

Engine `028170e` (branch `a-p2-egress`; pre-sha `0cf9ba5`); site `7e7e460` (main; pre-sha `2b5c7de`).
Cold lens, no prior context. All probing in detached worktrees under the session scratchpad
`dead0240-lens-AP2-r3-fresh-attack/` (`engine-wt` 028170e, `engine-pre` 0cf9ba5, `engine-ref` a0c9abc,
`engine-merge` = 028170e with `git read-tree -u --reset` of the tree `git merge-tree --write-tree 657ef11 028170e`
printed (`2f08301`), `site-wt` 7e7e460, `site-pre` 2b5c7de; both site trees with `node_modules`
junctioned, `PROOFPACK_ENGINE_DIR` at `engine-ref`, the site's `ENGINE_REF`). `PYTHONPATH` forced for
every engine figure and proved: `import proofpack` printed `...\dead0240-lens-AP2-r3-fresh-attack\engine-wt\src\proofpack\__init__.py`;
unforced it printed `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py` (lane E's tree).
The engine's main tree was read (`git diff`, `git status`, `git merge-tree`) and not modified, checked
out, stashed, committed or tested. Nothing was committed or pushed. One network call left this machine:
a GET to `https://proofpack.globalphoenix.co.uk/api/telemetry` (answered `404` in 0.145 s, 10:41 UTC),
to measure the row's date. Every figure below was measured in this session, Git Bash only.

## Verdict: **FAIL** - two blockers, both false sentences on `/legal/dpa` clause 2.1 written in this repair round. No egress byte, socket or exit code defect was found.

## Blockers

### B1 (site, `/legal/dpa` 2.1, sentence): "a later revision of that definition, with the same ten keys and stricter value patterns" - the later revision admits values the published one refuses

Rendered in `dist/legal/dpa/index.html`: *"the sender and the receiver validate against a later revision
of that definition, with the same ten keys and stricter value patterns, which the runner-telemetry row
on /trust names ..."*. `tests/day8-ap2-repair2.test.mjs` line 74 (`AP2R2-N4`) pins that exact string.

Per-property `jsonschema.Draft202012Validator(...).is_valid`, published copy (`src/data/egress_schema.json`,
LF sha256 `c98b85aec4a1de89…`, equal to a0c9abc) against 028170e's `$defs/telemetry`:

```
platform     'macosx-14.0-arm64-cp312'   published a0c9abc: refuse  028170e: admit
platform     'linux-x86_64-cp39'         published a0c9abc: refuse  028170e: admit
platform     'a.b-cp31'                  published a0c9abc: refuse  028170e: admit
licence_id   None                        published a0c9abc: refuse  028170e: admit
halt_code    'E01'                       published a0c9abc: refuse  028170e: admit
halt_code    'S03'                       published a0c9abc: refuse  028170e: admit
run_id       '0F8FAD5B-...-70867728950E' published a0c9abc: admit   028170e: refuse
```

The first row is a genuine record: `proofpack.manifest.platform_tag()` with `sysconfig.get_platform()`
returning `macosx-14.0-arm64` gives `macosx-14.0-arm64-cp314`, which the sender's whitelist and the
Function admit and the published schema refuses. The `licence_id` patterns are disjoint (`^L-…` / `^lic_…`),
so neither is stricter; `licence_id` null (sent on every refused-licence run) is admitted only by the
later revision. The same defect, not on a legal page, is in the runner-telemetry `state_note`
(rendered on `/trust` and on `/docs/egress`): *"which tightens licence_id (lic_ plus up to 60 letters or
digits, or null; …), platform, run_id, …"* - admitting null and admitting `macosx-…` are loosenings.
Repro: `python r3/prop_cmp.py <site>/src/data/egress_schema.json <engine@028170e>/schema/egress_schema.json`.
Repair (one clause each): "a later revision with the same ten keys and different value rules (it
admits a null licence_id, the lic_ ids the site issues, macOS platform tags and the E/S halt codes, and
refuses upper-case run ids)".

### B2 (both, `/legal/dpa` 2.1, `/trust` row, `/docs/egress`, sentence): "in the engine's tests for a 500, a timeout, a refused connection, a 3xx and an unreadable schema resource the run's exit code and run.json are the same as with --offline" - no engine test compares run.json with an `--offline` run

What each named test inspects at 028170e (`tests/test_telemetry.py`):

- 500 / timeout / refused - `test_a_failed_send_prints_one_w16_line_and_leaves_exit_code_and_documents`:
  fake transports (`500`, `TimeoutError`, `ConnectionRefusedError`); asserts `rc == EXIT_OK`, the three
  documents' hashes equal before and after the send, one W16 line. No `--offline` run.
- 3xx - `test_a_302_through_the_cli_prints_w16_and_the_location_host_receives_nothing`: asserts
  `rc == EXIT_OK`, the W16 line, the two listeners. `run.json` is not read.
- unreadable schema - `test_a_run_with_the_schema_resource_unreadable_prints_w16_and_exits_as_the_run`:
  asserts `rc == EXIT_OK` and `(out / "run.json").exists()`. `run.json`'s content is not read.
- the one test that runs `--offline` beside a failed send
  (`test_the_exit_code_with_a_failed_send_equals_the_exit_code_offline`) feeds a **503** and compares
  the exit code only.

The world-fact holds on measurement (lens 1's `attack_socket.py` re-run at 028170e: normalised `run.json`
equal to the offline run's and `rc=0` for 204, 500, 413, 301, 302, 303, 307, 308, hang, closed port;
mine for the unreadable schema: `normalised run.json equal: True`, `rc offline 0 rc unreadable 0`,
`transport calls 0`). The sentence is about what the tests establish, which is the recurring
defect the hard rule names, and it is on a `/legal/*` page. Repro: read the four tests above;
`grep -n "offline" tests/test_telemetry.py` finds one `--offline` beside a failure (line 467, the 503).
Repair: "in the engine's tests a 500, a timeout and a refused connection leave the exit code 0 and the
three documents' hashes unchanged, and a 302 and an unreadable schema resource leave the exit code 0",
citing the test ids.

## Non-blocking findings (ordered by weight)

### N1 (engine, test coverage): the new HTTPS path has no test; a mutant that turns certificate verification off survives all 88 `ap2` tests

Hand mutants of `src/proofpack/egress/telemetry.py` at 028170e, each run with `-m ap2 -x`
(`r3/mutants_r3.py`; the file restored after each, `git status --short` empty afterwards):

```
R1_https_no_deadline_wrap                SURVIVED 88 passed
R2_https_verification_off                SURVIVED 88 passed   (https_open: context=ssl._create_unverified_context())
R3_https_handler_dropped                 SURVIVED 88 passed   (build_opener without _DeadlineHTTPSHandler)
R4_run_telemetry_catch_all_removed       KILLED   ::test_a_run_with_the_schema_resource_unreadable_prints_w16_and_exits_as_the_run
R5_send_catch_narrowed_to_OSError        SURVIVED 88 passed
R6_makefile_bypasses_wrapper             KILLED   ::test_a_receiver_that_answers_one_byte_at_a_time_is_cut_off_at_the_deadline
R7_connect_timeout_60s                   SURVIVED 88 passed
R8_per_op_timeout_again                  KILLED   (the drip test)
R9_summary_drops_sentence                KILLED   ::test_the_next_step_hint_and_doctor_say_what_is_sent_and_how_to_turn_it_off
R10_log_entry_always_offline             SURVIVED 88 passed   (--json-log reports "--offline" for egress.telemetry: false)
R11_schema_unavailable_mislabelled       KILLED   ::test_send_with_the_schema_resource_unreadable_is_schema_unavailable
```

What R2 means, measured (`r3/r2_demo.py`, a self-signed loopback TLS server): 028170e as committed
→ `SendResult(sent=False, reason_code='transport_error')`, bodies received 0; R2 → `SendResult(sent=True,
status=204)`, bodies received 1. The production URL is `https://`; the only deadline test is `http://`.
Repair 2 replaced the default `HTTPSHandler` with a subclass, which is exactly where R1-R3 live. A
loopback TLS test (a self-signed server receives nothing; a trusted-CA server that drips its answer is
cut off) would kill R1-R3. The committed code is correct on every case I fed (see "could not break").

### N2 (engine, merge risk - measured): the evening merge is conflict-free and fails one `ap2` test

`git merge-tree --write-tree 657ef11 028170e` → exit 0 (no conflict). That tree in a worktree,
`PYTHONPATH` forced: `1 failed, 1075 passed, 1 skipped, 1 xfailed in 93.16s`; `-m ap2` `1 failed, 87
passed`; `-m day8` `1 failed, 287 passed`; `-m day7` `139 passed`. The failure:
`tests/test_egress.py::test_f19_pseudonyms_json_holds_the_map_beside_run_json_and_is_not_inside_any_payload`
- `assert … ['T8.html', '...', 'run.json'] == ['ingest_repo...', 'run.json']` (line 307): E8 writes
`T8.html` into the pack. In the merged tree the telemetry call sits after `write_documents` (T8 is
written before the send). The repair note's merge sentence measured only `merge-tree`; it does not say
the merged suite is green, so this is not a false sentence. Engine `main` moved to `7fa690b` (E8
repair 2) during this session; `git merge-tree --write-tree 7fa690b 028170e` also exits 0; the merged
suite was not re-run at `7fa690b`. Files outside the task's list still on the
branch: `handoffs/` (four lens notes), `scripts/ci_namespace_run.py`, `src/proofpack/doctor.py` (+8 −1),
`tests/conftest.py` (+37), `tests/test_doctor_cli.py` (+3 −1); `cli.py` is +20 −3 in four hunks and
`run.py` +12 −1, more than one call site each. E8's committed diff touches none of the four
out-of-list code files.

### N3 (engine, sentence): "an `--offline` process never imports a network module" / "a process that never sends never imports one"

`telemetry.py` lines 12-14 (rewritten in 466ab15) and 130-131 (new). An import hook in a fresh process,
`PYTHONPATH` forced: `--offline run` on the smoke fixture → `IMPORT socket <- platform.py:710 <
platform.py:1007 < platform.py:1127 < numpy\testing\_private\utils.py:90`, `rc 4 socket loaded: True`;
`--offline doctor` → `IMPORT socket <- platform.py:710 < … < proofpack\doctor.py:34 < doctor.py:136 <
cli.py:113`, `rc 0 socket loaded: True`; `--offline licence show` and `--version` → none. No socket is
opened (every command under the socket trap: `sockets=[]`); the module is loaded. The
existing test scans module-level imports under `src/proofpack` only. Repro: `r3/who_imports_socket.py`.

### N4 (engine, sentence): the test id `test_send_never_raises_and_classifies_the_failure` ships the sentence repair 2 refused, and the file's docstring says every CLI run uses a recording transport

Repair 2's note refused "send never raises" (a `BaseException` passes through). The test id at
`tests/test_telemetry.py:85` still says it. Counter-example: a transport raising `KeyboardInterrupt` →
`send` raised `KeyboardInterrupt` (by design). The module docstring (context of the 466ab15 hunk) says
"every CLI run in this file uses a recording transport, and the suite-wide guard in `conftest` would
turn any reach for the real one into a test failure"; `test_a_302_through_the_cli_prints_w16_…` runs
`cli.main` with `REAL_TRANSPORT` (via `to_loopback`) and passes.
`test_no_ap2_test_id_carries_a_sentence_the_build_note_refused` does not list "never_raises".

### N5 (both, sentence as a reader takes it): with `HTTPS_PROXY` set, a proxy that drips its CONNECT answer holds `send()` for 20.6 s

A loopback proxy answering `HTTP/1.1 200 Connection established\r\n\r\n` one byte per 0.4 s, then
tunnelling to a trusted loopback TLS server: `SendResult(sent=False, reason_code='timeout') in 20.62s`,
the proxy saw `CONNECT 127.0.0.1:<port> HTTP/1.1`, 0 bodies at the server. `http.client` reads the
CONNECT answer inside `connect()` on the raw socket (5 s per read), before `_DeadlineSocket` wraps it.
On the code's own terms the tunnel is part of "the connect", so the DPA's and `/docs/egress`'s
"a 5 s socket timeout on the connect" holds per operation; the `/trust` row's "a 5 s deadline, counted
from the start of the request, on every read and write" is false for these reads. A corporate proxy
is the ordinary case for this buyer. Not a leak (the body is inside TLS; the proxy saw only the host).

### N6 (both, carried, still reproduces)

- FA-L2-N1: `egress: {Telemetry: false}` → `rc=0 transport calls=1`, `telemetry sent (http 204)`;
  unknown keys in `egress` / `egress.suppression` accepted and sent; `min_n: 10.0` and
  `min_nonevents: 5.0` → `rc=0`, sent, while `thresholds_from_declarations({"suppression":
  {"min_nonevents": 5.0}})` → `HaltError {'field': 'egress.suppression.min_nonevents', 'default': 5}`.
  No looser value was accepted: `min_n 9 / 0 / -1 / '10' / 10.5 / 9.0 / true`, `min_events 4 / 4.0`,
  `min_nonevents 4` → `HALT H08`, exit 3, 0 transport calls.
- FA-L2-N8: upstream `400 {"message":"row too large: 4096 bytes"}` → the Function answers 204, no row.
- FA-L2-N5 / N6 (aggregates, unsent at launch): attributes `clinician_note`, `attr_consultant_name`,
  `manifest_hash` appear in the aggregates bytes (levels pseudonymised to `Level A`).

### N7 (engine, record): `send()` sends a body that is not JSON when `duration_s` is NaN

`telemetry.send({... "duration_s": float("nan") ...}, transport=rec)` → `SendResult(sent=True, 204)`,
body `{"duration_s":NaN,…}` (`jsonschema` admits NaN under `minimum` / `maximum`; `json.dumps`
default `allow_nan=True`). Not reachable from `cmd_run`: `write_run`'s `canonical_json` refuses NaN
first (`ValueError Out of range float values are not JSON compliant: nan`, lens-1 script). The
Function would answer 400 `body is not JSON`.

### N8 (engine, record): the telemetry sentence is printed under a skip or a failure

`--offline` run: `telemetry skipped (--offline); nothing was sent` then `telemetry: after run.json is
written the engine sends one record to …`. The second line describes the default, not the run.

## What I could not break (tried, with the figures)

- **Every egress byte.** F19 through `cli.main` with a recording transport: 374 bytes, the ten keys;
  my own `jsonschema` run against `$defs/telemetry` and the root: 0 errors each. Lens 1's
  `attack_payload.py` at 028170e (exit 0): 424 needles (every header, every site level, `St Mary's`,
  `Königsberg`, `Royal Free`, the ledger key, the licence signature, `mapping.json` bytes, the
  `pseudonyms.json` map, 400 distinct ROC thresholds, every date in `run.json`) → telemetry hits only
  `started` / the date inside the payload's own `timestamp`; the synthetic cohort (5,000 rows): 377
  bytes, 12 needles, none. Site `Site A` / `7` / the licence id → `Site A…E`; `sex` `St Mary's` →
  `Level A`; n 10 / events 5 / non-events 5 → kept; 9/9, 10/4, 10/6 → suppressed; calibration bin
  events 4 or n 9 → null; zero subgroups → 20 cells; `"roc"` absent, `0.5` present only as values
  (key-based strip); licence id 300 chars, `duration -1 / 1e12 / None`, newline in `platform`,
  upper-case `run_id`, `halt_code H99 / W16`, `rows_read -1 / None / 10.0 / True` → `EgressError`;
  `Decimal('1.5')` and `True` as `duration_s` → `payload_invalid`, no transport call.
- **The socket.** Lens 1's `attack_socket.py` at 028170e and again on the merged tree: `run`,
  `compare`, `map --yes`, `doctor`, `licence show` (both orders), `licence verify`, `licence install`
  under `--offline` with `socket.socket.__init__`, `getaddrinfo`, `create_connection` trapped →
  `sockets=[]` in all ten lines (`map --yes` H07 rc 3, `install` `SameFileError` rc 5, argparse rc 2:
  pre-existing). `egress.telemetry: false` without the flag, real transport → `sockets=[]`. Real
  transport on loopback: 204 sent; 500 / 413 / 301 / 302 / 303 / 307 / 308 → W16, `other_host_got=[]`;
  hang 5.07 s (`send()` alone 5.00 s); closed port 2.10 s; self-signed → `transport_error`, 0 bodies;
  `rc=0` and normalised `run.json` equal to offline in every case.
- **The new deadline.** Trusted-CA loopback TLS (the lens CA added through
  `ssl._create_default_https_context`; `verify_mode 2`, `check_hostname True`): leaf for 127.0.0.1 →
  sent 204 (control); leaf for `example.org` only → `transport_error`, 0 bodies. A relay dripping the
  TLS server's handshake 100 B per 1.0 s → `timeout` in 5.02 s (CPython bounds the whole handshake by
  the socket timeout); a TLS server dripping its 45-byte answer 1 byte per 0.3 s → `timeout` 1.01 s
  (`timeout=1.0`) and 5.00 s (default). HTTP: `100 Continue` every 0.5 s forever → `timeout` 2.00 s
  (`timeout=2.0`); status line then a header every 0.2 s → 2.00 s; status `abc` → `transport_error`;
  a 200 with a 100,000-byte body dripped → sent in 0.00 s (the body is not read).
- **The catch-all.** `build.egress_schema` raising `RecursionError`, `KeyError`, `MemoryError`,
  `UnicodeDecodeError` → `schema_unavailable`, 0 transport calls. Through the CLI with `OSError`:
  rc 0, one W16 line.
- **Ordering.** A transport that lists the pack at send time: `['ingest_report.json',
  'pseudonyms.json', 'run.json']`, `run.json` hashed there; deleting or truncating `run.json` from
  inside the transport → `rc=0`. `--out` an existing file → `rc=5`, 0 transport calls; HALT paths
  (H08, H06) → rc 3, 0 calls. `--json-log`: `{'sent': True, 'status': 204, …}`, `{'sent': False,
  'status': 500, 'reason_code': 'http_error'}`, `{'skipped': '--offline'}`, `exit_code 0` in each.
- **The endpoint** (lens 1's and lens 2's scripts in `site-wt` against the captured bytes, memory
  adapter and a loopback PostgREST stand-in): captured bytes → 204, one row of the ten keys plus
  `id`; again → 204, still one row; GET / HEAD / OPTIONS / PUT / DELETE / PATCH → 405 `allow: POST`;
  4,097 bytes (declared, streamed, or under a lying length) → 413; array / string / null / number →
  400; 100-deep object → 400 `unknown key`; newline in `run_id`, SQL in `licence_id` → 400; extra
  `ip` / `__proto__` / `constructor` → 400, `Object.prototype` not polluted; `text/plain`, no
  content-type → 415; duplicate `run_id` → 204, no second row; two in one second → 204 each. No
  `set-cookie`, no `access-control-*`, no echoed input in any response. Timing (300 each): unknown
  licence 0.036 ms, known 0.046 ms, duplicate 0.044 ms (medians). Upstream: `GET
  /rest/v1/runs?run_id=eq.<uuid>&limit=1` then `POST /rest/v1/runs`, body the ten keys; no client
  header reached upstream.
- **Suites and gates** (`PYTHONPATH` forced). Engine at 028170e: `876 passed, 1 skipped, 1 xfailed
  in 79.02s`; `ap2` 88; `day8` 88; `day7` 139; `day6` 285; `day5` 54; `day4` 182; `day3` 29 + 1
  xfailed; `day2` 40; `day1` 59 + 1 skipped; `ruff check` `All checks passed!`; `ruff format
  --check` `125 files already formatted`; `mutation_sweep.py --marker ap2` **16 planted, 16 killed,
  0 survived; 77 s**; `--marker day7` **25 planted, 25 killed, 0 survived; 124 s**; `--list` 187
  lines (34 day5, 112 day6, 25 day7, 16 ap2). E7's "Re-run these": `doctor --offline` `All essential
  checks passed.` exit 0; the e2e fixture `--offline` → `2 met, 2 not met, 5 not assessable`, exit 4,
  pack `ingest_report.json pseudonyms.json run.json` (E7's two plus A-P2's map); without the mapping
  → `HALT H07 …`, exit 3, nothing written; `licence show` → `refused (no_file)`, exit 4. Pre-sha:
  028170e's `tests/test_telemetry.py` against 0cf9ba5's `src` → `4 failed, 36 passed` (the drip test
  `AssertionError: 13.522247700020671`; `OSError: egress_schema.json unreadable`; the CLI test at the
  `rc == EXIT_OK` line; `ImportError: cannot import name 'TELEMETRY_SENTENCE'`). Site at 7e7e460
  (`PROOFPACK_ENGINE_DIR` = a0c9abc): `check:bytes` 277 files OK; build 30 pages; `check:links` 1243
  links OK; `check:schema` OK; `check:pricing` 37 figures 0 errors; `check:egress` 0 errors
  (`engine copy compared`); `check:validation` OK; `check:seo` 0 errors 5 warnings; `test:unit` 664 /
  662 / 0 / 2 skipped (the gps-automation branch and the telemetry-schema comparison, both absent
  from this worktree's neighbourhood); `test:e2e` 9 passed (40.7 s); `check:legal` red by design (2 of
  2); `check:keys` `pp-2026-09 live`. With `PROOFPACK_ENGINE_DIR` at 028170e the three day-8 site files
  → 31 / 31 / 0 skipped. Pre-sha: `day8-ap2-repair2.test.mjs` in the built `2b5c7de` tree → 0 pass /
  6 fail.
- **The drift gate.** `PROOFPACK_ENGINE_REQUIRED=1 npm run check:egress`: engine at a0c9abc → `0
  error(s)`; at 028170e → `FAIL the vendored egress schema has DRIFTED`, exit 1; no engine dir →
  `FAIL no checkout …`. So the branch merge into engine `main` leaves the site gate green (it compares
  with `ENGINE_REF`), and the pin move (S4) turns it red until the copy is re-made, as the note says.
- **Earlier lenses' blockers.** Lens 1's four stay closed: no `since 22 September 2026` in `dist`;
  `/trust` `Last updated 2026-09-23.`; the unshare sentence says "had not run anywhere as of 23
  September 2026"; the test-id scan passes. Lens 2 had no blocker; its N2, N3 and N10 reproduce as
  fixed; its N4 was reworded into B1; N1, N5, N6, N8 are carried (N6 above). Provenance
  `source_file_last_changed_commit 8e98728` equals `git log -1 a0c9abc -- schema/egress_schema.json`;
  `47d1aeb` and `466ab15` are dated 23 September as `/docs/egress` says. Live GET today → 404.

## What I could not check

- The `offline-namespace` job (`unshare -rn`): no Linux here and the branch is unpushed. Read only:
  it greps `telemetry skipped (--offline); nothing was sent` and `[W16] telemetry not sent (`, and
  fails if the namespace still resolves names.
- A hostname resolving to several unreachable addresses (each connect attempt gets `time_left()`);
  needs a resolver I do not control.
- Linux and macOS behaviour of `_DeadlineSocket` (`SocketIO`, `_io_refs`); Windows only.
- Postgres behaviour behind the Function, and whether the `runs` migration has been applied (no
  credentials).
- PowerShell 5.1 figures: not repeated; every figure above is Git Bash.

## Sentences I refused to write

- "a dripped TLS handshake outlives the deadline": measured 5.02 s; CPython's handshake uses the
  socket timeout as a whole-handshake bound.
- "hostname checking is off in the new HTTPS handler": my first positive control failed because two
  leaf files shared a name (`id()` reuse in my script); fixed, the control sends and the
  `example.org` leaf is refused. `SSL_CERT_FILE` did not add a CA on this Windows Python; I patched
  `ssl._create_default_https_context` instead.
- "a tighter suppression value is ignored": my first call passed the whole declarations to
  `thresholds_from_declarations` (which takes the `egress` block) and printed `Thresholds(10, 5, 5)`
  for `{min_events: 6, min_nonevents: 6}`; with the block it is `Thresholds(10, 6, 6)`.
- "the evening merge conflicts": `merge-tree` exits 0; what fails is one test (N2).
- "the send changes the exit code or a document": not on any case fed (above).
- "the endpoint distinguishes a known licence": medians 0.036 / 0.046 / 0.044 ms on the memory adapter.

## Worktrees

Removed at the end of this session (`engine-wt`, `engine-pre`, `engine-ref`, `engine-merge`,
`site-wt`, `site-pre`; the two `node_modules` junctions deleted as links first). Scripts and outputs
stay in `scratchpad/dead0240-lens-AP2-r3-fresh-attack/r3/` (`attack_r3.py`, `mutants_r3.py`,
`prop_cmp.py`, `r2_demo.py`, `who_imports_socket.py`, `unreadable_vs_offline.py`, `misc_r3.py` and
their `.txt` outputs).
