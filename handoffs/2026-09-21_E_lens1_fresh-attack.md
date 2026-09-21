# Lens 1 (fresh attack, DEC-12(i)) - build day 7 E7, lane E, `ab729d3` - 2026-09-21

**Verdict: FAIL. Two blockers.** B1: a `point_estimate` criterion on a Number that has no
interval (method `none`, a typed `not_estimable_reason`) is `met` or `not_met`, not
`not_assessable` - the F1 overall Number (`analytic_ci_unavailable`, est 0.662) and a
clustered PPV cell at a boundary (`boundary_estimate`, est 0.0) both produced `not_met` from
`proofpack run`; the E6 handoff's binding item 5, the criteria.py docstring and the README
all say "never `not_met`". B2: under clustering a cluster-bootstrap lower bound can exceed
the Wilson bound at k = n, so a `ci_lower_bound` criterion is `met` in the same row that
carries `attainable_at_n: false` - 29 of 30 negatives correct in 15 two-row cases gives
`ci_lo 0.9` against `max_lower_bound_at_n 0.8865`; the attainability docstring's "cannot be
met by any outcome at that n, whatever the model does" and "`attainable_at_n: false` is
exact" are falsified by that run. Everything else I re-derived agrees: the Wilson k = n
bound to 0 (own formula, n = 1..500, levels 0.80 / 0.90 / 0.95 / 0.99), the manifest
hashes to `hashlib`, every day-4/5/6 figure of six assembled documents byte-identical
between `a0c9abc` and `ab729d3` apart from the four documented additions, the 57-plus-3
construction and nine neighbours finite through the full run, 21 / 21 committed mutants and
22 / 24 of my own killed, zero sockets with and without `--offline`, 61 licence attacks
refused or accepted as D1 says except the OverflowError family (N3). Eight non-blocking
items follow.

Worktrees: `ab729d3` and `a0c9abc` under `scratchpad/lens-E7-r1-fresh-attack/`,
`PYTHONPATH=<worktree>/src` forced and proved (`python -c "import proofpack;
print(proofpack.__file__)"` printed each worktree's own `src\proofpack\__init__.py`; the
unforced form printed `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py`,
the `.pth` trap). Both removed at the end. The main tree was read only and is clean at
`ab729d3` apart from this note. Git Bash throughout. Every figure below was measured in
this session in the `ab729d3` worktree unless the sha says otherwise.

## Blockers

### B1 - a criterion on a Number with no interval is `met` / `not_met` when the statistic is `point_estimate` (wrong status; sentence violation)

The engine reads `est` for `point_estimate` and compares it whatever the Number's method
(`criteria.py::_row`: `compared = _statistic_of(number, statistic)`; only a `None` result
routes to `no_interval`). A Number with a typed reason still carries `est` (F1, MCC,
`boundary_estimate`), so it is compared.

Repro 1 (i.i.d., the synthetic cohort with S3 = 30 rows, `criteria` = one `f1`
`point_estimate >= 0.70` at `op1` overall, one `mcc` `point_estimate >= 0.40`, no
fairness; `proofpack run` with a valid ephemeral-signed licence):

```
{'criterion_id': 'F1_pe',  'statistic': 'point_estimate', 'compared_value': 0.6620689655172414, 'method': 'none', 'status': 'not_met', 'reason_code': 'statistic_compared', 'detail': {}}
{'criterion_id': 'MCC_pe', 'statistic': 'point_estimate', 'compared_value': 0.4821183187439812, 'method': 'none', 'status': 'met',     'reason_code': 'statistic_compared', 'detail': {}}
```

The F1 Number in `overall.op1.f1` of that run.json: `est 0.662, ci_lo None, ci_hi None,
method none, not_estimable_reason analytic_ci_unavailable, flags [ci_pending_bootstrap]`.

Repro 2 (clustered: 400 rows in 200 two-row cases, `clustering.unit: case_id`, site S3 =
30 rows all `y_true 0`; criterion `ppv point_estimate >= 0.5` at `{attribute: site,
level: "*"}`): the S3 row is `compared_value 0.0, n 12, method none, status not_met,
reason_code statistic_compared`; the cell's Number is `est 0.0, ci None, method none,
not_estimable_reason boundary_estimate, flags [wilson_refused_clustered,
very_low_precision]`, its `analytic` companion `clustered_data_analytic_ci_invalid`.

Why blocker: a customer with a real table gets a status decided on a point estimate the
document itself refuses to render with an interval (D1 section 4.1: "Nothing without a CI
is rendered except counts"; D1 section 2 lists "CI not estimable" as a `not_assessable`
reason with no statistic qualifier). The E6 handoff's binding item 5 - "a criterion on a
Number with `method: none` and a typed reason is `not_assessable`, never `not_met`" - is
the rule this build was told to implement.

Sentences falsified (sentence_violation): `src/proofpack/criteria.py` lines 25-26 "a
Number with no interval (a typed `not_estimable_reason`) or a suppressed one gives
`not_assessable` and carries the reason in `detail` - never `not_met`"; `README.md`
"A Number with no interval is `not_assessable`, never `not_met`."; the build note's row 2
"a Number with `not_estimable_reason single_class` and value 0.0 is `not_assessable`" is
true only because that test used `ci_lower_bound`. The 12 literal-reading cases in
`tests/test_criteria.py` feed a Number that always has an interval; no test feeds
`point_estimate` to a Number without one.

Repair shape (not prescribed): in `_row`, route on `number.get("not_estimable_reason")
is not None or number.get("method") == "none"` before `_statistic_of`, with the reason in
`detail`; regression test = repro 1's two rows asserted `not_assessable` / `no_interval`
with `detail.not_estimable_reason == "analytic_ci_unavailable"`, measured failing first.
A repair here touches the criteria gate: DEC-12(i) lens again.

### B2 - `attainable_at_n: false` beside `status: met` on a clustered cell (wrong attainability flag; sentence violation)

`max_lower_bound_at_n` is the i.i.d. Wilson bound at k = n (D1's definition, exact - see
"could not break"). On a clustered cell the rendered interval is the cluster-bootstrap
percentile interval, whose lower bound is not bounded by that figure: with one wrong row
in one of 15 two-row cases the case is absent from 35.5 % of resamples (`(14/15)^15`), so
the 2.5th percentile of the resampled proportion sits at 27/30 = 0.9, above n / (n + z^2)
= 0.8865 at n = 30.

Repro (`proofpack run`, 400 rows in 200 two-row cases, `clustering.unit: case_id`, site S3
= 30 rows all `y_true 0`, score 0.1 on 29 of them and 0.9 on row 0 (case c000000, whose
sibling row is right); criteria `specificity ci_lower_bound >= 0.89` and `accuracy
ci_lower_bound >= 0.89` at `{attribute: site, level: S3}`, B 200, seed 20240101):

```
{'criterion_id': 'sp_S3',  'value': 0.89, 'compared_value': 0.9, 'n': 30, 'method': 'cluster_bootstrap_percentile', 'status': 'met', 'attainable_at_n': False, 'max_lower_bound_at_n': 0.8864866068260313}
{'criterion_id': 'acc_S3', 'value': 0.89, 'compared_value': 0.9, 'n': 30, 'method': 'cluster_bootstrap_percentile', 'status': 'met', 'attainable_at_n': False, 'max_lower_bound_at_n': 0.8864866068260313}
```

The S3 specificity cell: `est 0.9667, ci (0.9, 1.0), method cluster_bootstrap_percentile,
n 30, k 29, n_cases 15, flags [wilson_refused_clustered, very_low_precision]`.

Why blocker: the row states the criterion is met and that it cannot be met at this n. The
renderer (E8) prints both words in one T1/T8 row; a reviewer reads a contradiction, and
"a wrong attainability figure" is on the brief's blocker list. Clustered tables (several
images or admissions per patient) are the ordinary case for this product's buyers.

Sentences falsified (sentence_violation): `src/proofpack/stats/attainability.py` lines
22-24 "A `>=` criterion whose `value` exceeds it cannot be met by any outcome at that
`n`, whatever the model does - which is the fact the pack states, and all it states";
lines 26-31 "the figure here is the i.i.d. Wilson bound over the rows, so
`attainable_at_n: false` is exact (not attainable even with independent rows)"; the build
note's decision 4 "Under clustering `n` is the row count, so `false` is exact". The
builder's reasoning (a cluster bootstrap is wider than Wilson, so a Wilson-unattainable
value is bootstrap-unattainable) is the false step: a percentile interval on a small
cluster count is not wider at its lower end.

Repair shape (not prescribed): on a Number whose `method` is not `wilson` the flag is
`null` and the figure carries a typed annotation (`attainability_basis: wilson_iid_rows`
or the like), or the attainability is computed from the cell's own resampler; either way
a status of `met` must never sit beside `attainable_at_n: false` - assert that invariant
over every row in the E7 run test. Regression test = this construction, measured
`met` + `false` first. Touches `stats.attainability` and the criteria row: DEC-12(i).

## Non-blocking

### N1 - the ledger loses updates under concurrent runs (undercount in T8)

`io.ledger.record_run` reads, increments and rewrites `ledger.json` with no lock. Six
`python -m proofpack.cli run --offline` processes started together on the same input and
`PROOFPACK_HOME`, three trials: file count after all six finished **5, 3, 6**; per-run
`ledger.acceptance_runs` `[4, 2, 1, 3, 5, 1]`, `[3, 1, 1, 2, 1, 2]`, `[3, 6, 2, 1, 5, 4]`.
Two runs in a CI pipeline can therefore both report count 1. The docstring "incremented
once per run whose declarations carry a criteria block" is true per process and false
across them. Carry: an `O_EXCL` lock file or `os.replace` on a temp file with a retry, and
a two-process test. Record-and-carry (rare on a laptop; a wrong figure when it happens).

### N2 - a run whose only criterion is the fairness bound is not counted

`has_criteria=bool(decl.criteria)` reads the `criteria` list only. A `criteria.yaml` with
no `criteria` list and `fairness.bound: 0.10` produced one `fairness:tpr_gap` row
(`not_met`) and left the count at 1 (file `{...: 1}` before and after). An acceptance
decision was made and not recorded. Carry: count when `criteria_results` holds any
`met` / `not_met` row.

### N3 - `verify()` raises `OverflowError` on a signed payload with an extreme date or grace (sentence violation, exit 5 not 4)

`src/proofpack/licence/verify.py` line 10 "`verify` **raises nothing on bad input**" and
line 152 "Raises nothing on bad input". Measured (ephemeral key, `now` 2026-09-21T12:00Z):
`grace_days 3_000_000` -> `OverflowError: date value out of range`; `grace_days 10**9` ->
`OverflowError: days=1000000000; must have magnitude <= 999999999`; `grace_days 10**12`
-> `OverflowError: Python int too large to convert to C int`; `expires
9999-12-31T23:59:59Z` -> `OverflowError` (the 24 h skew added to `datetime.max`);
`expires 0001-01-01T00:00:00+05:00` and a trial issued 9999-12-31 likewise. Through
`proofpack run` this is `internal error: OverflowError: ...`, exit 5, no `run.json`
(measured on the NaN path with the same handler). Reach: only a payload signed by the
real key, so the issuer's constants bound it today (GRACE_DAYS 30, `expiresAtMs` from the
plan); a hand-signed `scripts/sign_licence.py` file could hit it. Carry: clamp or refuse
`grace_days > 3650` and years outside 2000-2200 with a typed `missing_field` /
`expires_unparsable`; drop or qualify the two sentences.

### N4 - two of my mutants survive `-m day7` (test gaps)

`L15_wrong_length_sig_ok`: `except ValueError: pass` in `verify` (the wrong-length
signature branch falls through to `ok`) - 122 passed. At `ab729d3` a 63-byte, a 65-byte
and an all-zero 64-byte signature are each `refused signature_invalid` (measured), but no
day-7 test feeds a wrong-length signature with an otherwise valid payload; the "three
truncations never raise" test asserts only that nothing raises.
`L3_unknown_row_included_in_star`: removing the `is_unknown_row` skip in
`_subgroup_rows` - 122 passed; no day-7 test runs a `level: "*"` criterion on a table with
a missing attribute value. Both non-equivalent; the code is right, the tests do not
inspect it. Carry both into the day-7 list with an observer each.

### N5 - `scope` absent from a criterion is read as `overall` (an engine-supplied default)

`criteria_schema.json` does not require `scope`; `_reads_for` and `check_references` use
`c.get("scope", "overall")`. A criterion with no `scope` key ran to `not_met` on
`overall.op1.sensitivity` (exit 0). D1 section 2's example writes `scope: overall`
explicitly and the file's own description says "The engine never supplies defaults".
Carry: add `scope` to `required` (H08 names the field).

### N6 - three declaration gaps that reach a row instead of a halt

(a) `date: "2026-13-40"` passes the `^\d{4}-\d{2}-\d{2}$` pattern and the run proceeds
(exit 0). (b) `value: .nan` / `.inf` in YAML pass `type: number`; the whole run computes
and then `canonical_json` refuses the document: `internal error: ValueError: Out of range
float values are not JSON compliant: nan`, exit 5, nothing written. (c) a criterion on an
age band that does not exist (`level: "41-66"` with bands `[40,65]`) is
`not_assessable / level_absent` rather than H09, because `check_references` skips level
checks on the numeric `age` attribute. Two criteria sharing an `id` produce two rows with
the same `criterion_id` and different values (no uniqueness check; `level: "*"` already
makes the id non-unique, so the renderer must key on the row, not the id).

### N7 - the "no licence" watermark says EXPIRED

With no licence file at all `run.json` is written with `manifest.watermark = "LICENCE
EXPIRED - not for submission"`, `licence_id null`, `tier null` (exit 4, as decided). The
watermark asserts an expiry that never happened. `cli.py`'s docstring and README say this
is by design (D1 "after grace emit JSON only" read as the same state); a second string for
`refused` / `no_file` ("NO LICENCE - not for submission") would keep the manifest true.
Needs Josh (the build note's needs 2 is the same decision).

### N8 - small items, recorded

- `licence install` replaces an installed, valid licence with an `expired` one silently
  (status is not `refused`, so it copies; exit 4 after the copy). Measured: a valid file
  installed, then an expired-past-grace file installed over it, `proofpack.lic` bytes now
  the expired file's.
- A `mapping.json` with no `decided_by` key is read as `file` (lane A's
  `Mapping.read` default, `mapping.py` line 384) and passes DEC-26; measured: the key
  deleted from a confirmed file, run exit 0. Lane A's documented convention, not E7's
  code, but DEC-26's words are "decided_by interactive or file".
- `git diff a0c9abc ab729d3 -- src/proofpack/stats/` touches six files, not only the
  item-25 branch of `bootstrap.py`: `discrimination.py` (ROC origin threshold
  `float("inf")` -> `None`, a day-3 output shape change with its test rewritten),
  `calibration.py` (`no_score_column`, item 28), `descriptive.py` (`dev_rows`, item 27),
  `subgroups.py` / `calibration.py` (`resample_sd_reason` pass-through). The six-document
  diff below shows no figure moved; the ROC change is necessary for `allow_nan=False` and
  is recorded here because the brief's constraint names one file.
- `tests/test_licence.py::test_the_site_reference_verifier_agrees_on_the_same_file`
  carries a new `skipif` (site checkout absent); it ran here (the suite's one skip is the
  day-1 write-access test) and will skip in CI, where the private site repo is not beside
  the engine. The note's "the site's verifier agrees" is a local measurement only.
- `tests/test_mapping_repair3_2.py::test_a_header_spelled_like_the_ignored_key_is_h07_without_the_header`
  loosened its first-line assertion from the ignored-key message to `startswith("HALT
  H07: ")` because the DEC-26 `--yes` rule now halts first; the ignored-key route is no
  longer inspected through `run`.
- `REASON_CODES["no_calibration_block"]` reads "the calibration block is absent (no score
  column)" but a y-pred-only run gives `calibration_suppressed` with reason
  `no_score_column` (measured), so `no_calibration_block` is unreachable from `run` and
  its description names the wrong case.
- `metric_not_computed` is the reason on `sensitivity` under a comparator reference
  standard (PPA/NPA routing), where "no Number with an interval exists for this metric
  id in v1" is not the reason; a `routed_to_ppa_npa` code would say why.

## Sentences refused

- "the criteria engine never emits a status on a Number without an interval" - B1.
- "attainability is exact under clustering" - B2.
- "the ledger counts every acceptance run" - N1, N2.
- "`verify` raises nothing" - N3.
- "no verdict word can reach the document" - the grep found none in 22 documents (below);
  a grep inspects the documents it was run on.

## Could not break

Each figure is from this session, `ab729d3` worktree, `PYTHONPATH` forced.

- **Suite and markers.** `python -m pytest -q -p no:cacheprovider`: `771 passed, 1
  skipped, 1 xfailed in 92.13s`; `-m day1` 59 passed 1 skipped, `day2` 40, `day3` 29 + 1
  xfailed, `day4` 182, `day5` 54, `day6` 285, `day7` 122; `ruff check` "All checks
  passed!", `ruff format --check` "104 files already formatted"; `day7` declared in
  `pyproject.toml` beside `day6`, and `.github/workflows/ci.yml` reads the marker list
  from `pyproject.toml` (lines 30-47), so it is gated. `doctor --offline` "All essential
  checks passed."; the E6 re-run block's one-off schema test 1 passed; lane A's
  `map --input tests/fixtures/mapping/sepsis_2019.csv < /dev/null` probe exit 3, 3485
  bytes, 27 lines, no output file (equal to the 18 September handoff); the round-5
  long-s probe `categorical None None`.
- **Wilson at k = n.** Own implementation of Newcombe method 3 with `p = k / n`, `z` from
  `statistics.NormalDist().inv_cdf`: max |engine - own| over n = 1..500 **0** at 0.95,
  0.90, 0.99, 0.80; max |engine - n/(n+z^2)| 1.1e-16; the docstring's 0.8865 / 0.9287 /
  0.9812 reproduced; `attainable` at n = 1, 2, 30, 10^6 with value 0 (True), 1 (False),
  1.0000001 (False), `<=` (None); n = 0 / -1 `ValueError`; `>=` and `>` differ only at
  value == bound. The F8 row from the full run: `C_n30` `not_met`, `n 30`,
  `attainable_at_n False`, `max_lower_bound_at_n 0.8864866068260313`, `metric_ref
  subgroups[8].metrics.op1.accuracy.number`, `compared_value == cell.number.ci_lo`.
- **Criteria gates.** 26 malformed files: no `value` -> H08 `criteria/0: required`;
  `value: null`, `"0.85"`, `true` -> H08 `value: type`; `=>` and `≥` -> H08
  `comparator: enum`; `ci_lower_bounds` -> H08 `statistic: enum`; `level S9` -> H09
  unknown level; attribute `region` -> H09 unknown attribute; scope without `level` ->
  H08 `scope: oneOf`; `author ""` and `"   "` -> H08 lacks author; `op9` -> H09 unknown
  operating point; `sensitivty` -> H09 unknown metric; `id: 7` -> H08 `id: type`; a YAML
  date (unquoted `2026-03-01`) -> H08 `date: type`; `auroc` at `op1` and `sensitivity`
  without an operating point -> H09; a fairness bound without `statistic` -> H08. None
  wrote a document. `<=` and `<` on `ci_lower_bound` compare `ci_lo` literally
  (`sp_S3_le`: `ci_lo 0.4333 <= 0.99` met). Typed-reason Numbers under `ci_lower_bound`:
  `zero_denominator` (sensitivity on an all-negative site) -> `not_assessable /
  no_interval` with the reason in `detail`; `insufficient_positives` (AUROC on that site)
  likewise; a clustered overall -> `overall_not_computed`; a logit score -> brier / oe
  `calibration_suppressed` with `score_not_probability` in `detail`; `ece` ->
  `metric_not_computed`; `paired_difference_vs_prior` -> `requires_compare`.
- **Verdict grep.** My own walker over every key and string of 22 `run.json` files and
  their `ingest_report.json` (i.i.d., clustered, y-pred-only, indeterminates both ways,
  comparator reference, dev rows, logit, lower_is_positive, period, prevalence 0.05,
  unicode levels, missing sex, no criteria, the 57-plus-3 family): outside
  `criteria_results` zero hits on the 43-word `VERDICT_WORDS` set plus the brief's seven;
  inside it only `met` / `not_met` (as whole tokens; `not_assessable` splits to `not`,
  `assessable`); substrings `pass`, `fail`, `verdict`, `meets`, `acceptable`,
  `consistent`, `unbiased` absent from every non-declarations byte. Engine strings: the
  only `pass` / `fail` / `verdict` in `src/` are lane A's `--yes` hints, `doctor`'s own
  `FAIL` mark and a `verdict` local in `mapping.py`, all pre-`a0c9abc`.
- **Manifest.** Two runs in one process: byte diff of `run.json` = `run_id`,
  `duration_s` (0.767 -> 0.052), `ledger_count` 1 -> 2, `ledger.acceptance_runs` 1 -> 2,
  nothing else (`started` equal to the second); `input_sha256`, `criteria_sha256`,
  `mapping_sha256` equal; `run_id` distinct across the 72 runs. `mapping.json` re-indented ->
  `mapping_sha256` changes and equals `hashlib.sha256(file bytes)` (DEC-27: the bytes);
  the run leaves the mapping file's bytes untouched. `criteria.yaml` CRLF -> LF:
  `criteria_sha256` changes, `declarations` echo and every status equal. An input with a
  UTF-8 BOM: accepted, `input_sha256` changes, flow and statuses equal. `canonical_json`:
  `nan`, `inf`, `-inf`, `np.float64(nan)` raise `ValueError`; `np.int64`, `np.bool_`,
  `datetime`, `Path`, `set` raise `TypeError` (nothing written); `np.float64(2.5)`
  serialises; the documented bytes for `{"b": 1, "a": {"y": [1.5, None], "x": "é"}}`
  reproduced. `platform win-amd64-cp314`, `reference_platform false`.
- **Ledger.** Sequential: counts 1, 2, 3 then W14 `{count 4, limit 3}` at the fourth
  (exit 2); no `criteria` list and no fairness bound -> count read, not moved; `criteria:
  []` -> not moved; no `ledger` block -> five runs, count 5, `warn_limit null`, no
  warning; same `y_true` / `score` with a different `sex` column -> same key (D1's key);
  a different threshold -> same key; reversed rows -> different key (documented);
  `warn_after_acceptance_runs` 0 / -1 / `"3"` -> H08 (minimum / type), absent key -> H08
  required, `1.0` -> accepted as 1; `not json`, a negative count, a float count, a
  directory in the file's place -> W15 `counted false` exit 2, no traceback; a
  `10**30` count -> W14; the pack directory holds `run.json` and `ingest_report.json`
  only; `ledger.json` is under `PROOFPACK_HOME`.
- **Licence.** 61 constructions against `verify()` (ephemeral registry; `now`
  2026-09-21T12:00Z): valid annual `ok` 344 days; three segments, empty signature, empty
  payload, one segment -> `not_two_segments`; two fields swapped, keys reordered, a
  one-bit signature flip, a 63 / 65 / all-zero-byte signature, the shipped `key_id` on an
  ephemeral signature, the right `key_id` with another key -> `signature_invalid`;
  base64url / unpadded signature, unpadded payload, a BOM, a space inside a segment ->
  `base64_invalid`; trailing-bit spellings of the signature and of the payload that decode
  to the same bytes -> `base64_not_canonical`; expired 1 h and 23 h -> `ok`, 25 h ->
  `grace` with the watermark, 30 d and 31 d -> `grace`, 31.99 d and 32 d -> `expired`;
  expires without zone / epoch / date-only / lowercase z / leading space / 2027-02-30 ->
  `expires_unparsable` (epoch int -> `missing_field`); `+01:00` and `.000Z` accepted;
  `key_id` wrong / `""` / 10 000 chars -> `unknown_key_id` (detail truncated to 32);
  `key_id` missing, `licence_id 5`, `licensee null`, `grace_days 30.0` / `-1` ->
  `missing_field`; `tier lifetime` / `Annual` -> `unknown_tier`; trial 31 d after issue
  `ok` + `TRIAL`, 32 d `grace`, 60 d `grace`, 62 d `expired`; a 3 MB payload, `models 0`,
  `features []`, a unicode licensee, CRLF at end -> `ok`. Through `run`: expired past
  grace exit 4 with `run.json`, watermark and every statistic computed; grace exit 0 +
  watermark; trial `TRIAL`; no file exit 4 + `run.json`. The shipped literal equals
  `proofpack-site/keys/licence_pub.b64` and `licence_pub.json` (`pp-2026-09`, hex
  `5d82e768...ab3000`); a one-bit change to `SHIPPED_PUBLIC_KEY_B64` fails at import
  (collection error), a change to both literals fails 1 test; no `PRIVATE KEY`,
  `Ed25519PrivateKey`, `-----BEGIN`, `importSigningKey` in `src/`. `licence show` /
  `verify` / `install` print no signature byte and no payload segment (`--json-log`
  before the subcommand works; after `show` argparse rejects it, exit 2 usage).
- **Sockets.** `socket.socket`, `socket.create_connection`, `socket.getaddrinfo` replaced
  with raisers: `run` with `--offline` and without both exit 0 with zero calls.
- **Item 25.** `calibration_block` on 57+3, 56+4, 58+2, 59+1, 60+0 at 1e-160 and 57+3 at
  1e-150, 1e-155, 1e-170, 1e-300, 5e-324, 1e-100, events 20 / 3 / 1: every block finite,
  `json.dumps(allow_nan=False)` succeeds; `resample_sd` `None` + `resample_sd_not_finite`
  where the draws exceed ~1e154 (1e-155 and below), a finite float at 1e-150
  (1.06e149) and 1e-100, `0.0`-width cells typed. Through `proofpack run` (positives
  arranged so H01 passes): 57+3 clustered and i.i.d., 56+4, 58+2, 5e-324, 1e-155, 1e-300 -
  no non-finite float in any document, no `Infinity` / `NaN` byte, `oe` rows compared or
  `no_interval`. Six documents (i.i.d., clustered, comparator, y-pred, logit, 120-row
  five-site) assembled with `tests/assembler.py` in both worktrees and diffed key by key:
  only `resample_sd_reason` added (89 / 12 / 12 / 0 / 14 cells), `dev_rows` 0 added, the
  ROC origin threshold `inf` -> `None`, the assembler's own `suppression_log` /
  `guidance_refs`, and the y-pred document now assembling where `a0c9abc` raised
  `calibration needs a score column`; **no other value differs**. `MIN_UNITS_PER_STRATUM
  2`, `MAX_FROZEN_VARIANCE_SHARE 0.20`, `CLIP_EPS 1e-12`, `DEFAULT_LEVEL 0.95` unchanged.
- **DEC-26.** No mapping -> H07 "run proofpack map first" in 0.01 s (a confirmed run takes
  0.71 s, so nothing was computed); `--mapping` missing path -> H07; `proposed`, `yes`,
  `FILE` -> H07 "this one was not confirmed"; header set differs -> H07; a medium role
  unconfirmed -> H07, confirmed (`file` or `interactive`) -> run; swapped roles, a role
  moved to `y_pred`, a dropped entry, not-JSON, empty, a directory -> H07 with lane A's
  messages; `--yes` accepted and inert; no `mapping.json` beside any of the 72
  `run.json` files this session wrote.
- **Item 26 / 27 / 28.** Three `""` and one `NA` case id in a clustered table ->
  `HALT S05: case_id is blank in 4 row(s); fill every case id or drop the column`, exit
  3, no pack directory; `dataset` with 40 `dev` rows ->
  `flow.dev_rows 40`, `rows_read 400 = 40 + 0 + 0 + 0 + 360`; y-pred-only ->
  `calibration null`, `calibration_suppressed_reason.reason no_score_column`, `overall
  null`, subgroup PPV rows compared, document validates.
- **Mutation sweep.** Committed day-7 list: `21 planted, 21 killed, 0 survived; 79 s`.
  My own 24 (not on the list): 22 killed, 2 survived (N4). Committed day-6 list (`--marker day6`):
  `112 planted, 112 killed, 0 survived; 960 s`.
- **Schema.** Every one of the 22 run documents validates against
  `schema/output_schema_v1.json` with zero errors.

## Could not check

- The reference platform (`linux-x86_64-cp312`): this machine is `win-amd64-cp314`, so
  F17's cross-platform half and the hash identity claim were not exercised.
- The real signing key's output: no live-issued `.lic` was available; agreement with the
  issuer rests on the site's `verify_licence.py` (same signature input, canonical base64
  via `btoa`) and the key bytes, both read, not on a file the Cloudflare function signed.
- `licence install` across a symlink (Windows symlinks need a privilege this shell does
  not hold).
- The E8 renderer's reading of `criteria_results` (B2's contradiction is a document fact
  today; how it prints is tomorrow's).
- PowerShell 5.1 was not used; every figure is Git Bash.
