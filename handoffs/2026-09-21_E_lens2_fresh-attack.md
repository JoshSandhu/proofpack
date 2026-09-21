# Lens 2 (fresh attack, DEC-12(i)) - build day 7 E7 repair 1, lane E, `02d00c5` - 2026-09-21

**Verdict: PASS. No blocker.** Both lens-1 blockers are closed on the literal inputs that
raised them and on new constructions: a `point_estimate` criterion on a method-`none` Number
is `not_assessable` / `no_interval` from `proofpack run` (the synthetic F1 and MCC overall
Numbers, a clustered PPV cell at `boundary_estimate`, a zero-positive site's sensitivity, a
30-row site's AUROC at `insufficient_positives`), and no row of 61 `run.json` files written
this session reads `met` beside `attainable_at_n: false` (the clustered S3 cells carry
`null` + `method_not_wilson`; the i.i.d. k = n = 30 cell carries the figure
0.8864866068260313 and `met` / `True` at `>=` the figure, `not_met` / `False` one part in
10^12 above it). Suite 784 / 1 / 1, `-m day7` 135, the committed sweep 24 / 24, 19 of my
own 25 mutants killed (one equivalent, five test gaps), 60 licence constructions refused or
accepted as D1 section 7 says, the Wilson k = n bound at 0.0 from my own formula over
n = 5..500 at four levels, seven documents figure-identical to `a0c9abc`, item 25 finite on
19 constructions, zero sockets with and without `--offline`, 42 documents schema-valid
with no `NaN` / `Infinity` byte and no row identifier. **Nine non-blocking items follow,
four of them shipped sentences a constructed counter-example falsifies** (the hard rule),
and six lens-1 non-blocking items re-verified as still open.

Worktrees under `scratchpad/lens-E7-r2-fresh-attack/`: `wt02d` and `wt02d_b` at `02d00c5`,
`wtab7` at `ab729d3`, `wta0c` at `a0c9abc`; `PYTHONPATH=<worktree>/src` forced and proved
by `python -c "import proofpack;print(proofpack.__file__)"` printing each worktree's own
`src\proofpack\__init__.py` before every figure (the unforced form prints the main tree's,
the `.pth` trap). All four removed at the end. The main tree was read only; the only file
written there is this note. Git Bash throughout; every figure below was measured in this
session.

## Blockers

None.

## Non-blocking

### N1 - "on any other method both are null and `detail.attainability_not_computed` is `method_not_wilson`" is false at n = 0 (sentence violation; four places)

`src/proofpack/criteria.py` lines 35-43, `src/proofpack/stats/attainability.py` lines
26-29 ("leaves both `null` with `detail.attainability_not_computed: method_not_wilson`
otherwise"), `README.md` line 295, `schema/output_schema_v1.json` line 118. The code fills
the annotation only inside `isinstance(n, int)` and `elif n > 0` (`criteria.py` lines
344-349), so a method-`none` proportion Number with `n: 0` or `n: null` gets neither the
figure nor the annotation. Counter-example through `proofpack run` (400 rows, site S3 = 30
rows with every `y_true` set to `0`; criterion `sensitivity ci_lower_bound >= 0.8` at
`{site, S3}`):

```
{'criterion_id': 'se_S3', 'statistic': 'ci_lower_bound', 'n': 0, 'method': 'none', 'attainable_at_n': None, 'max_lower_bound_at_n': None, 'status': 'not_assessable', 'reason_code': 'no_interval', 'detail': {'not_estimable_reason': 'zero_denominator'}}
```

The status is right; the sentence is not. The attainability.py "otherwise" is also false
for a `ci_upper_bound` or `point_estimate` criterion on a Wilson Number (`sp_S3_ub`,
`sp_S3_pe` in the same run: both `null`, `detail: {}`). Write the guard as the code has it:
"a `ci_lower_bound` criterion on a proportion metric whose Number carries an integer
`n > 0`: filled on `method: wilson`, `method_not_wilson` on any other method; otherwise
both `null` and no annotation".

Repro: `python -c "..."` is long; the harness is
`scratchpad/lens-E7-r2-fresh-attack/probes/harness.py` (`setup` + `run`), input as above.

### N2 - "the manifest keys that differed were `run_id`, `started`, `duration_s` ... and `ledger_count`" (sentence violation; three places)

`src/proofpack/manifest.py` lines 5-11 and `schema/output_schema_v1.json` line 17 report
`started` as a key that differed in the F17 test's measurement; `tests/test_manifest.py`
line 154 comments `# run_id and started differ`. The test asserts only `"run_id" in
differ and "ledger_count" in differ`. Six consecutive pairs of `proofpack run` on the same
input at `02d00c5`: keys differing were `['duration_s', 'ledger_count', 'run_id']`,
`['ledger_count', 'run_id']`, `['duration_s', 'ledger_count', 'run_id']`, `['ledger_count',
'run_id']`, `['duration_s', 'ledger_count', 'run_id']`, `['duration_s', 'ledger_count',
'run_id']` - `started` never differed (both runs inside one UTC second) and `duration_s`
twice did not. The sentence should say "may differ" (as the test's own docstring does) or
name run_id and ledger_count as the two the test asserts. Also uncorrected in this repair:
`tests/test_manifest.py` lines 3-7, the module docstring, still reads "byte-identical JSON
except `run_id`, `started` and `duration_s` ... compared after those three keys are
blanked" - the RG-N2 sentence, while the body blanks four manifest keys and
`ledger.acceptance_runs`.

### N3 - `expires_unparsable` "with `detail.field`" and "three truncations" (sentence violation)

`src/proofpack/licence/verify.py` lines 25-26 and `REASON_CODES["expires_unparsable"]`
(line 81): "a date, the trial end or the grace end outside Python's `datetime` range
(`expires_unparsable` with `detail.field`)". Measured (ephemeral key, `now`
2026-10-15T12:00Z): `expires 0001-01-01T00:00:00+05:00` -> `refused expires_unparsable
{}`; `expires 9999-12-31T23:59:59-05:00` -> `refused expires_unparsable {}`; only the
sums carry a field (`9999-12-31T23:59:59Z` -> `{'field': 'expires'}`, a trial `issued
9999-12-31` -> `{'field': 'issued'}`). The repair note's own table says the `+05:00` case
is `{}`. Line 13 "three truncations of a signed file": the test's second of three is
`seg + "." + "A" * len(sig)` - a same-length replacement, not a truncation.

### N4 - the ledger counts a run that wrote no document

`assemble_run` calls `ledger.record_run` before `write_run` serialises. Measured on one
`PROOFPACK_HOME` (counts read from `ledger.json` after each command): a normal run -> 1;
`value: .inf` in `criteria.yaml` (`internal error: ValueError: Out of range float values
are not JSON compliant: inf`, exit 5, no `run.json`) -> 2; no licence (exit 4, document
written) -> 3; `--out` naming an existing file (`internal error: FileExistsError`, exit 5,
nothing written) -> 4. The next successful pack's `manifest.ledger_count` and
`ledger.acceptance_runs` include the two aborted runs. The docstring "incremented once per
`run` whose declarations carry a `criteria` block" is literally true; the T2 banner's
"used in N runs" is what overstates. Carry: record after the write, or say in the
docstring that aborted runs count.

### N5 - `licence install` exits 5 on two reachable inputs; the hint after installing an expired file says "run"

`proofpack licence install <the installed path itself>` -> `internal error: SameFileError:
... are the same file`, exit 5 (`shutil.copyfile` refuses; `cmd_licence` does not catch
it). A read-only `proofpack.lic` in the per-user directory -> `internal error:
PermissionError`, exit 5. Neither is a traceback; both are untyped exit 5 on a customer
command. Installing an expired-past-grace file over a valid one (lens-1 N8, still
reproduces: the target's bytes become the expired file's) prints `status: expired
(expired_past_grace)` and then `Next step: proofpack run --input ...` with exit 4 - the
hint contradicts the exit code (`cmd_licence` picks `run_next` on `status != "refused"`).

### N6 - a validly signed licence at the `datetime` edge is refused because the grace sum is computed before it is needed

`expires 9999-12-30T12:00:00Z`, `grace_days 30`, ephemeral key: `now <= expires + 24 h`
holds, yet `verify` returns `refused expires_unparsable {'field': 'grace_days'}` because
`grace_with_skew` (line 246) is summed before the `ok` branch is reached. `grace_days
2_900_000` on an expired-40-days licence is `grace` (year 9967 fits). Reach: a hand-signed
file only (the issuer's `expiresAtMs` comes from the plan periods). A decision, not a
defect I can grade: refuse-at-the-edge is defensible; the docstring should say it.

### N7 - mutation survivors (test gaps; five non-equivalent)

Committed list: `--marker day7` **24 planted, 24 killed, 0 survived; 111 s**; `--list`
170 lines, 34 day5 + 112 day6 + 24 day7, 0 duplicate ids; worktree clean afterwards. My
own 25 (planted in a copy, `-m day7`, `PYTHONPATH` to the copy and proved per mutant): 19
killed, 6 survived. `M01` (`reason is not None or method == "none"` -> `and`) is
equivalent on engine output: over 1,941 Numbers in this session's documents `(reason set)
xor (method none)` is the empty set. Non-equivalent survivors: `M05` the Unknown row
included under `level: "*"` (lens-1 N4, still open); `M06` the wrong-length-signature
`except ValueError` falling through to `ok` (lens-1 N4 L15, still open: a 63-byte
signature is `signature_invalid` today and no test feeds one against an otherwise valid
payload); `M08` `grace_days < 0` -> `< -1` (a signed `grace_days: -1` accepted; no test
feeds it); `M17` `has_criteria=True` in `run.py` (no test runs `proofpack run` without a
`criteria` list and reads the ledger count back - `test_ledger.py` inspects `record_run`
only); `M26` the fairness bound emitting a row for the Unknown level (no test has a bound
on an attribute with a missing value). The five belong on the day-7 list with an observer
each.

### N8 - a ledger `counts` value of `true` is read as 1

`_read` accepts `isinstance(v, int)`, which a JSON `true` satisfies; a file `{"counts":
{"<key>": true}}` gives `acceptance_runs 2` on the next run rather than W15. Every other
corruption I fed - a BOM, an empty file, `{"counts": []}`, `1e400`, a nested object, a
directory in the file's place - gives `W15` with `counted false`, `acceptance_runs null`,
exit 2, the file left unrewritten.

### N9 - lens-1 items re-verified as still open at `02d00c5` (carried by the repair note, not marked fixed)

N1 ledger races: two `python -m proofpack.cli run` processes on one ledger, four trials:
file count 1 / 1 / 2 / 2, per-run `acceptance_runs` `[1, 1]`, `[1, 1]`, `[1, 2]`, `[2, 1]`.
N2 a fairness-only bound (no `criteria` list, `bound 0.10`) yields `fairness:tpr_gap
not_met` and `acceptance_runs 0`. N5 a criterion without `scope` runs as `overall`
(`met`). N6 `date: "2026-13-40"` runs; two criteria with `id: dup` give two rows (`met`
at 0.5, `not_met` at 0.99). N8 `decided_by` deleted from a confirmed `mapping.json` ->
run exit 0. RG-N14 the CLI summary line prints `criteria rows: 2 met, 2 not met, 5 not
assessable` and `--json-log` emits `criteria_status_counts` with those keys.

## Sentences refused

- "a criterion on a Number without an interval is never `not_met`" - measured on nine such
  rows from `run` (all `not_assessable`); nine rows, not a class.
- "no `met` row carries `attainable_at_n: false`" - 61 documents walked; a walk inspects
  the documents it was run on.
- "`verify` never raises" - 60 constructions and the suite's 300 blobs; N6 shows the
  refusal branches have edges nobody has enumerated.
- "F17 holds" - the differing keys are listed as measured (N2).
- "the ledger counts every acceptance run" - N4, N9.

## Could not break

Every figure from this session, `02d00c5` worktrees, `PYTHONPATH` forced.

- **Suite and markers.** `python -m pytest -q -p no:cacheprovider`: `784 passed, 1
  skipped, 1 xfailed in 76.10s`; `-m day7` 135; `day6` 285; `day5` 54; `day4` 182; `day3`
  29 + 1 xfailed; `day2` 40; `day1` 59 + 1 skipped; `ruff check` "All checks passed!";
  `ruff format --check` "106 files already formatted"; `doctor --offline` "All essential
  checks passed." exit 0; `day7: Day 7` in `pyproject.toml` line 73 and
  `.github/workflows/ci.yml` lines 30-50 reads the marker list from it. `git diff ab729d3
  02d00c5 -- tests/`: 4 `M`, 0 `D`, no `skip` / `xfail` / `.only` added or removed. The
  18 September E block's one-off schema test 1 passed; repair-r7's 27 `27 passed`; day-5
  round-1's seven and round-2's seven `7 passed` each; the A block's `map --input
  tests/fixtures/mapping/sepsis_2019.csv < /dev/null`: exit 3, 3485 bytes, 27 lines, no
  output file; the long-s probe `categorical None None`; the hidden-module import
  (`scipy`, `scipy.stats`, `statsmodels`, `sklearn`, `cryptography` and three submodules
  set to `None`) imports `proofpack`, `.stats`, `.licence`, `.criteria`, `.run`, `.cli`,
  `.manifest`, `verify(b"abc")` -> `not_two_segments`, no scipy module loaded; `METHODS`
  18 / `FLAGS` 15 / `NOT_ESTIMABLE_REASONS` 21.
- **Pre-fix proof.** The four edited test files copied into `wtab7` (`ab729d3`): `12
  failed, 111 passed in 6.62s`, the 12 being B1's three `point_estimate` /
  `ci_lower_bound` params, the two B2 hand / assembled tests, the two `run` tests and the
  five overflow params - the note's list exactly; `ci_upper_bound <= 1.0` passes there.
- **B1 closed.** Lens 1's repro 2 (clustered, S3 all negative, `ppv point_estimate >=
  0.5` at `{site, "*"}`): S3 row `not_assessable / no_interval`, `compared_value null`,
  `method none`, `detail.not_estimable_reason boundary_estimate`; S1 and S2 compared on
  `est` with `cluster_bootstrap_percentile` (`met` 0.5634, `met` 0.6076). `f1` overall
  `ci_lower_bound` -> `no_interval / analytic_ci_unavailable`, `n 400`; a 30-row site's
  AUROC -> `insufficient_positives`, `n null`; a clustered overall -> `overall_not_computed`.
- **B2 closed, and the figure re-derived.** Own Wilson lower bound (R2 section 1.1, `z`
  from `statistics.NormalDist().inv_cdf`) at k = n over n = 5..500: max |engine - own|
  **0.00e+00** at levels 0.80 / 0.90 / 0.95 / 0.99; max |engine - n/(n+z^2)| 1.11e-16;
  30 -> 0.8864866068260313, 50 -> 0.9286524008666414, 200 -> 0.9811546736227335 (the test
  literals 0.886486606826 / 0.928652400867 / 0.981154673623 within 1e-9). `attainable` at
  n = 1, 2, 30, 10^6: value 0 -> `True` / `True` / `None` under `>=` / `>` / `<=`, 1 and
  1.0000001 -> `False` / `False` / `None`. Through `run` on an i.i.d. site of 30 negatives
  all right (`specificity` Wilson `est 1.0`, `ci_lo 0.8864866068260313`, `k 30`):
  `>= 0.8864866068260312` `met` + `True`; `> 0.8864866068260312` `met` + `True` (the
  closed form sits one ulp below the engine's Wilson evaluation); `>= 0.886486606827`
  `not_met` + `False`; `<= 0.5` `not_met` + `None` with the figure filled; `accuracy`
  overall `>= 1.0` and `>= 1.0000001` `not_met` + `False` against 0.9904877056657034 at
  n = 400, `>= 0.0` `met` + `True`; `prevalence >= 0.2` `met` + `True`. The clustered S3
  cells (lens 1's construction) through `run`: `sp_S3` and `acc_S3` `met`,
  `compared_value 0.9`, `n 30`, both fields `null`, `detail {attainability_not_computed:
  method_not_wilson}`. Every `n` in the in-memory document is a Python `int` (366
  Numbers), so the `isinstance(n, int)` guard is not defeated by `numpy.int64` from
  `run` (a hand-built `np.int64(30)` does defeat it: both `null`, no annotation - not
  reachable).
- **Criteria gates.** `comparator: >=` unquoted (YAML folded-scalar trap) -> `HALT H08:
  criteria file could not be read: ScannerError`; a tab-indented file -> the same; empty
  file and a top-level list -> `H08: criteria file must be a YAML mapping`; a BOM +
  CRLF file -> runs, `criteria_sha256` changes, declarations and statuses equal to LF;
  a duplicate top-level `criteria:` key (last wins, `[]`) -> 0 rows; a scope on an
  undeclared attribute (`site` absent from `subgroups`) -> the exploratory row is read,
  `met`; `level: "*"` on `sex` with 16,667 blank values -> one row (`F`), the
  `Unknown/missing` row excluded, and a named `Unknown/missing` level -> one row.
- **Verdict grep.** My own walker over every key and string of four `run.json` files
  (i.i.d. with criteria, without criteria, clustered, y-pred-only), whole tokens and
  substrings, excluding `declarations`: 0 hits on the 43-word `VERDICT_WORDS` plus the
  brief's seven outside `criteria_results`; inside it only `met` / `not_met`; `pass`,
  `fail`, `verdict`, `meets`, `acceptable`, `consistent`, `unbiased` absent as
  substrings from every byte. `grep -rniE` of `src/proofpack` for the seven: only lane A's
  `--yes` hints, `doctor`'s `FAIL` mark and `mapping.py`'s `verdict` / `consistent` locals
  (pre-`a0c9abc`); `ingest_report.json` (in the pack directory) holds counts, hashes and
  role names only.
- **Manifest.** Two runs: differing paths `$.ledger.acceptance_runs`,
  `$.manifest.duration_s`, `$.manifest.ledger_count`, `$.manifest.run_id`,
  `$.manifest.started` (that pair straddled a second); `input_sha256`, `criteria_sha256`,
  `mapping_sha256` each equal `hashlib.sha256(file bytes)`; `mapping.json` re-indented ->
  `mapping_sha256` changes, statuses equal (DEC-27: the bytes are hashed; D1 section 4.2
  asks for the mapping's hash and the file is the mapping); a BOM on the input -> accepted,
  `input_sha256` changes, flow and statuses equal; 61 `run.json` files, 61 distinct
  `run_id`s; `platform win-amd64-cp314`, `reference_platform false`. `canonical_json`:
  `nan`, `inf`, `np.float64(nan)` -> `ValueError`; `np.int64`, `np.bool_`, `np.float32`,
  `datetime`, `Path`, `bytes` -> `TypeError`; `np.float64(2.5)` serialises.
- **Ledger.** Limit 1: first run count 1 no warning, second count 2 `W14 {count 2, limit
  1}` exit 2; no `criteria` list -> `acceptance_runs 0`, file untouched; six corruptions
  -> `W15` (N8 above); the pack directory holds `run.json` and `ingest_report.json` only.
- **Licence.** 60 constructions against `verify` (ephemeral registry, `now`
  2026-10-15T12:00Z): `expires == now` `ok` 0 days; `now - 24 h` exactly `ok` (-1);
  `now - 24 h - 1 s` `grace`; grace 0 expired 25 h `expired`, 23 h `ok`; grace 30 expired
  31 d exactly `grace` (-31), 31 d + 1 s `expired`; grace 2 000 000 `grace`; issued after
  expires `ok`; trial issued 29 / 31 / 62 d ago `ok` + `TRIAL` / `ok` + `TRIAL` (-1) /
  `expired`; `expires` with a space separator, `.5Z`, `-00:00`, `+14:00`, an ISO week
  date -> `ok`; `Z` + offset, `+24:00`, year 10000, an ordinal date -> `expires_unparsable`;
  `grace_days` `True` / `100.0` -> `missing_field`, `10**12` / `10**30` ->
  `expires_unparsable {field: grace_days}`; `tier` list, `key_id` list -> `missing_field`;
  a `licence_id` with a newline, empty, an empty `licensee`, nested extras, a 3 MB
  payload, duplicate `tier` keys (last wins), a `NaN` literal in `models`, CRLF at the
  end -> `ok`; a JSON array / string / UTF-16 payload, signed -> `payload_not_json_object`;
  A's signature on B's segment, a 63-byte and an all-zero 64-byte signature, the right
  `key_id` with the wrong key, the shipped `key_id` on an ephemeral signature against the
  shipped registry -> `signature_invalid`; three segments, a leading or trailing dot, an
  empty signature -> `not_two_segments`; base64url, unpadded, a space inside, a BOM, a
  trailing NUL -> `base64_invalid`; an ephemeral `key_id` against the shipped registry
  and an empty registry -> `unknown_key_id`; a naive `now` accepted. The shipped literal
  equals `proofpack-site/keys/licence_pub.b64` and `licence_pub.json` by string and by
  bytes (`5d82e76854675953...`), `key_id pp-2026-09`; a one-bit change to
  `SHIPPED_PUBLIC_KEY_B64` fails at import (`ImportError: the shipped and published
  licence keys differ`), to both literals fails 2 tests in `test_licence.py`; the site's
  `scripts/verify_licence.py` and the engine agree on a good file (`signature OK` / `ok
  valid`), a signature tamper and a payload tamper (`InvalidSignature` / `refused
  signature_invalid`); `licence show --json-log` and `install` print no signature
  segment; a directory as `verify` / `install` target -> `refused (no_file)` exit 4;
  `PROOFPACK_LICENCE` a directory -> `no_file`. Through `run` with no licence: exit 4,
  `run.json` written, `watermark 'LICENCE EXPIRED - not for submission'`, `licence_id
  null` (lens-1 N7 stands).
- **Sockets.** `socket.socket`, `create_connection`, `getaddrinfo` replaced with raisers:
  `run` with and without `--offline` completes (exit 2 on W14, the ledger at its limit),
  zero calls.
- **Item 25.** `calibration_block` on 19 constructions: 57+3 at 1e-160 (`est 13.33`,
  `ci (4.0, 4.0e159)`, `resample_sd None`, `resample_sd_not_finite`), 56+4, 58+2, 59+1,
  60+0 (`est 3.3e159`, finite bounds), 1e-150 (sd 1.06e149, finite), 1e-155, 1e-300,
  1e-306, 5e-324 (sd 12.48), 1e-100, events 3 and 1 (no interval, typed), B 2000, seed 1,
  40 events, i.i.d. (log-delta, no bootstrap), 30+30, 3+57: no non-finite float in any
  block, `json.dumps(allow_nan=False)` succeeds on all 19. Seven documents assembled with
  each tree's own `tests/assembler.py` at `a0c9abc` and `02d00c5` (i.i.d., clustered,
  comparator, logit, five-site 120-row, prevalence 0.05, lower_is_positive) and diffed
  path by path: **0 values differ**; added keys are `resample_sd_reason` (12 / 89 / 12 /
  0 / 14 / 12 / 0 cells in that order), `dev_rows`, the assembler's manifest keys; the one changed value
  is `overall.threshold_free.roc[0][2]` `inf` -> `null`. `git diff a0c9abc 02d00c5 --
  src/proofpack/stats/` touches six files (lens-1 N8 recorded why); `DEFAULT_B 2000`,
  `DEFAULT_LEVEL 0.95`, `MIN_UNITS_PER_STRATUM 2`, `MAX_FROZEN_VARIANCE_SHARE 0.20`,
  `MIN_USABLE_FRACTION 0.90`, `CLIP_EPS 1e-12` unchanged.
- **DEC-26.** No mapping -> H07 in 0.10 s (400 rows) and 0.20 s (50,000 rows) against
  0.72 s / 2.51 s for the confirmed run - nothing computed first; `decided_by`
  `proposed` / `yes` / `FILE` / `""` -> H07 "this one was not confirmed"; header-set hash
  altered -> H07; `interactive` -> runs; no pack directory on H07; no `mapping.json` in
  any of the 61 pack directories.
- **Schema.** 42 `run.json` files from this session validate against
  `schema/output_schema_v1.json` with 0 errors; no `NaN` / `Infinity` byte; no
  `row_id` / `case_id` literal in any of the 61.
- **DEC-36.** The y-pred-only document carries `calibration: null` beside
  `calibration_suppressed_reason {reason: no_score_column, ...}`, `overall: null`,
  `flow.dev_rows`; the i.i.d. document has 18 top-level keys.

## Could not check

- The reference platform (`linux-x86_64-cp312`) and F17's cross-platform half.
- A licence signed by the production key (none exists off the issuer; the shipped key's
  bytes and the site's own verifier were exercised with an ephemeral pair).
- `licence install` across a symlink (Windows privilege).
- The `/docs/run` and `/docs/licence` anchors the CLI prints (lane S).
- PowerShell 5.1 (Git Bash only).
- The E8 renderer's reading of `criteria_results` and of `manifest.watermark`.
