# Lens 3 (fresh attack, DEC-12(i)) - build day 7 E7 repair 2, lane E, `2cd7e16` - 2026-09-21

**Verdict: PASS. No blocker.** Nothing I constructed made `proofpack run` on a table with
a `criteria.yaml` produce a wrong status, a status the engine chose, a wrong attainability
figure, a wrong manifest hash, a licence accepted that D1 section 7 says to refuse (or the
reverse), a socket under `--offline`, a verdict word outside `criteria_results`, a
`NaN` / `Infinity` byte or a row identifier in a written document. 95 `criteria.yaml`
variants, 33 hand-built Numbers, 116 licence constructions (88 against `verify`, 17
through the CLI, 9 date payloads at two commits, 2 base64 spellings on a segment that
actually differs), 19 item-25 constructions, 21 mapping-file variants, 12 ledger
corruptions and 4 two-process races, 8 documents diffed path by path against `a0c9abc`,
115 `run.json` files schema-valid with 115 distinct `run_id`s, the committed sweep 25 / 25,
15 of my own 22 mutants killed. Suite `788 passed, 1 skipped, 1 xfailed`; `-m day7` 139 in
both shells. **Nine non-blocking items follow; none is a sentence a counter-example
falsifies** - one sentence is incomplete (N2) and is recorded as such.

Worktrees under `scratchpad/lens-E7-r3-fresh-attack/`: `wt-2cd7e16`, `wt-02d00c5`,
`wt-a0c9abc`, `wt-ab729d3`; `PYTHONPATH=<worktree>/src` forced and proved by `python -c
"import proofpack;print(proofpack.__file__)"` printing each worktree's own
`src\proofpack\__init__.py` before the first figure (the unforced form printed
`C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py` - the `.pth` trap,
measured first). Every probe is `scratchpad/lens-E7-r3-fresh-attack/probes/p*.py` and
imports through `harness.py`, which asserts the worktree's `proofpack.__file__` on import.
All four worktrees removed at the end. The main tree was read only (`git diff`, `git log`,
`git ls-files --eol`, `git status`); the only file written there is this note. Git Bash
throughout, PowerShell 5.1 for the cross-shell cells named below. Every figure below was
measured in this session.

## Blockers

None.

## Non-blocking

### N1 - a probability column below about 1e-309 gives an O:E `est` of `inf` and exit 5 (pre-existing day-4 route, surfaced by item 25's `allow_nan=False`)

`calibration_block` computes O:E as observed / sum(p); with every score a denormal the sum
underflows and the ratio overflows. Measured through `proofpack run --offline` (60 rows,
20 events, `score` `1e-310` on every row, i.i.d.): `internal error: ValueError: Out of
range float values are not JSON compliant: inf`, exit 5, no `run.json`, ledger file not
written. `5e-324` the same. `1e-300` runs (`est 3.33e299`, finite bounds). Through
`calibration_block` directly: clustered 60 + 0 at `1e-310` -> `oe.number.est inf`,
`analytic.est inf`, `ci (None, None)`, `degenerate_resamples`; i.i.d. 60 + 0 at `1e-320`
-> `est inf`, `ci (inf, inf)`, `method log_delta`, **no typed reason** - a Number that
carries neither an interval nor a reason, which `canonical_json` then refuses so it never
reaches a file. Scores at exactly `0.0` are typed `zero_denominator`. Reach: a table whose
every score is a denormal float; a softmax export underflows to `0.0`, not to a denormal,
so I grade this record-and-carry: guard the O:E denominator with a typed reason
(`expected_below_float_range` or the like) in `calibration.py`. Not E7's change; the
57 + 3 construction and its 18 neighbours (56 + 4, 58 + 2, 59 + 1, 60 + 0 at `1e-160`,
`1e-150`, `1e-155`, `5e-324` with 3 at 0.5, `1e-300`, `B` 2000, seed 1, 3 at 1.0, all 1.0,
all 1 - 1e-16) are finite and serialise; `resample_sd` is `None` with
`resample_sd_not_finite` on the eleven whose draws exceed about 1e154 and a float on the
rest.

Repro: `python probes/p11_inf_run.py` (writes a 60-row CSV with `score` `1e-310`, runs
the CLI).

### N2 - "at ab729d3 the first five of those six raised OverflowError" is incomplete: the sixth raised there too (verify.py module docstring and the test docstring)

`src/proofpack/licence/verify.py` lines 19-21: "at `ab729d3` the first five of those six
raised `OverflowError` out of the date arithmetic (lens 1 of 21 September, N3; the sixth
was added by repair 2 to pin the empty `detail` below)";
`tests/test_licence.py::test_extreme_dates_and_grace_days_are_refused_expires_unparsable`
docstring: "at ab729d3 the first five of these signed payloads raised OverflowError".
Measured in `wt-ab729d3` (ephemeral key, `now` 2026-10-15T12:00Z): all six raise -
`expires 9999-12-31T23:59:59-05:00` -> `OverflowError: date value out of range`, the same
line as the `+05:00` payload. The sentence does not say the sixth did not raise, so no
counter-example falsifies it; it reads as if the sixth were different in kind, and it is
not. Write "all six raised at ab729d3; the sixth was added by repair 2". Not a
sentence violation by the rule; recorded as a precision item.

### N3 - hand-built Numbers only (not reachable from `run`; the guard as written)

* `method wilson`, `n True`: `isinstance(True, int) and True > 0` holds, so the
  attainability fields are filled at n = 1 (`max_lower_bound_at_n 0.2065493143772375`,
  `attainable_at_n False` against 0.9). The docstring's "an `int` above 0" is literally
  what the guard tests; a `bool` satisfies it. Every `n` the engine builds is a Python
  `int` (`proportion(k, n)`, `proportion_ci`).
* a `None` where a Number should be (`overall.op1.sensitivity: null`): `_resolve_overall`
  returns `_Read(None, "overall.op1.sensitivity")` with no reason, and the row is
  `not_assessable` with `reason_code None` - outside the schema's enum. `overall_block`
  and `two_by_two_metrics` never place `None` there (a 2 x 2 with no predicted positives
  gives `ppv` `method none`, `zero_denominator`, `n 0`, and the row is annotated).
* `method wilson` beside a `not_estimable_reason` (`single_class`, `insufficient_clusters`)
  or beside `suppressed: true`: `not_assessable` with the attainability fields filled.
  `not_estimable()` always writes `method none`, and nothing is suppressed locally
  (DEC-08), so neither shape is built.
* `method wilson`, `ci_lo 0.9`, `n 30` (a Wilson interval that cannot exist: the k = n
  bound is 0.8865): `met` beside `attainable_at_n False`. On the engine's own Numbers
  `proportion(k, n).ci_lo` at k = n equals `max_lower_bound_at_n(n)` exactly for n in
  {1, 2, 5, 30, 128, 1000} and is below it at k = n - 1, so the pair cannot arise from
  `run` at `ci_level 0.95`; lens 2's RG-N2 (`ci_level 0.80`) stands as carried.

### N4 - seven of my 22 mutants survive `-m day7` (test gaps; four new)

Planted in a copy of `wt-2cd7e16` with `PYTHONPATH` to the copy and proved per mutant
(`probes/p14_mutants.py`). Killed (15): a suppressed Number compared; the reference-level
gap row reading `level_absent`; `compared_value` rounded to six places (`assert (0.886487
== 0.8864866068260313)`); `<=` read as `<`; `<` read as `<=`; an empty segment falling
through; `days_left` from `expires` rather than the trial's effective date; `ok` strictly
before `expires + 24 h`; a `bool` accepted for `grace_days`; the ledger key without its
NUL separator; the ledger counting runs without criteria; `input_sha256` hashing the
mapping; the analytic overall block on clustered rows; S05 reading `""` only (`assert 5 ==
3`); W14's count off by one. Survived (7):

* **`L3-M03`** a named `level` matched case-insensitively (`str(r.get("level")).lower()`):
  no day-7 test has two levels that differ in case only. Non-equivalent.
* **`L3-M08`** a `prevalence` criterion reading the `auroc` Number (`tf.get("auroc")`):
  no day-7 test feeds a `prevalence` criterion. Non-equivalent; measured right through
  `run` (`prevalence ci_lower_bound >= 0.2` -> `met`, `compared_value 0.2761841236239046`,
  `n 400`, `wilson`, `attainable_at_n True`).
* **`L3-M18`** the ledger key over every row rather than the analysed rows
  (`table.y_true` without `mask`): no day-7 test runs a table with excluded rows and reads
  the key. Non-equivalent; measured right through `run` (two tables differing only in
  the scores of two rows whose labels are blank: same `test_set_sha256`, different
  `input_sha256`).
* **`L3-M19`** `prevalence` dropped from `PROPORTION_METRICS`: as M08.
* `L3-M07` the fairness bound emitting an Unknown-level row - lens 2's M26, still open.
* `L3-M09` `grace_days < -1` - lens 2's M08, still open.
* `L3-M22` the attainability level hard-coded 0.95 in `_row` - equivalent on the run
  route (`evaluate` is only ever called with the default); the level test inspects
  `max_lower_bound_at_n` directly.

Committed sweep in the worktree: `--marker day7` **25 planted, 25 killed, 0 survived;
112 s**; `--list` 171 lines, 0 duplicate ids, 34 day5 + 112 day6 + 25 day7; worktree
clean afterwards.

### N5 - a `y_pred`-only table: an overall-scoped criterion is `not_assessable` while the subgroup rows carry the same metric

`overall` is `null` for a `y_pred`-only table (`overall_block` returns `None` when
`table.score is None`), so `sensitivity ci_lower_bound >= 0.5` at `scope: overall` is
`not_assessable / overall_not_computed`; the same table's `subgroups[0].metrics.op1.
sensitivity.number` is a Wilson Number (`est 0.789`, `ci_lo 0.637`, `k 30`, `n 38`), so a
site-scoped criterion on the same metric would be compared. The build note's item 12
discloses the overall half as E8's ("the operating-point metrics from `y_pred` are
E8's with the clustered overall"); recorded here so E8 sees the asymmetry a customer
would see in T8. The document validates; `calibration null` beside
`calibration_suppressed_reason {reason: no_score_column, ...}` (DEC-36).

### N6 - two schema shapes

* The `ledger` block is not in the output schema's top-level `required` set (a document
  without it validates); every run writes it. The five keys the E6 handoff named
  (`calibration`, `calibration_suppressed_reason`, `missingness`, `table1`, `flow`) and
  `criteria_results` / `manifest` are required (measured by deleting each).
* `ledger.warn_after_acceptance_runs: 2.0` passes `type: integer` (JSON Schema's
  integer semantics) and the document carries `warn_limit: 2.0`; `0`, `-1`, `"3"`,
  `true` and `{}` are H08 naming the field.

### N7 - `doctor` marks a refused licence `[ok  ]`

`python -m proofpack.cli doctor --offline` with `PROOFPACK_LICENCE` pointing at a file
signed by an unknown key prints `[ok  ] licence  <path>: refused (unknown_key_id)` - the
check's own status (non-essential, "ran") beside the word `refused`. Cosmetic; the run
route is unaffected (exit 4, watermark).

### N8 - carried items re-verified as still open at `2cd7e16`

Ledger race: two `python -m proofpack.cli run` processes on one ledger, four trials -
file count 2 / 1 / 2 / 2, per-run `acceptance_runs` `[1, 2]`, `[1, 1]`, `[2, 1]`, `[2, 1]`
(lens-1 N1). A ledger value of JSON `true` read as 1 -> next run `acceptance_runs 2`, no
W15 (lens-2 FA-N8); the other eleven corruptions I fed (`-1`, `1.5`, `"2"`, `1e400`, a
nested object, an empty file, a BOM, `[]`, a trailing NUL, trailing garbage, and
`PROOFPACK_HOME` naming a file) give `W15` with `counted false`, exit 2 (or 4 with no
licence), the file left as it was; a 23-digit integer is read as the count and W14 carries
it. A fairness-only bound: one `not_met` row, count unchanged (lens-1 N2). `date:
"2026-13-40"` runs; two criteria with `id: X` give two rows, `met` at 0.5 and `not_met` at
0.99 (lens-1 N6). `decided_by` deleted from a confirmed `mapping.json` -> run exit 0
(lens-1 N8). `licence install` on the installed path -> `internal error: SameFileError`
exit 5; on a read-only target -> `internal error: PermissionError` exit 5; an
expired-past-grace file installed over a valid one -> the bytes replaced, `status:
expired (expired_past_grace)`, then `Next step: proofpack run ...`, exit 4 (lens-2 FA-N5).
`expires 9999-12-30T12:00:00Z` with `grace_days 30` -> `refused expires_unparsable
{field: grace_days}`; with `grace_days 0` -> `ok` (lens-2 FA-N6). `issued` after
`expires` -> `ok` (lens-2 RG-N4). `models 0` / `-1` / `"1"`, `features null`, `licence_id`
empty or with a newline, `licensee` empty -> `ok` (lens-1 N11). No licence at all ->
`run.json` written with `watermark 'LICENCE EXPIRED - not for submission'`, `tier null`,
exit 4 (lens-1 N7). The CLI summary line `criteria rows: 2 met, 2 not met, 5 not
assessable` and `--json-log`'s `criteria_status_counts` keys (lens-1 RG-N14). A criterion
without `scope` runs as `overall` (lens-1 N5). `value: .nan` / `.inf` / `1e309` -> exit 5
after the whole run (lens-1 RG-N5), and the run is counted: `value: .nan` on a fresh
`PROOFPACK_HOME` -> `ledger.json` absent before, `{<key>: 1}` after, no `run.json`
(lens-2 FA-N4; `record_run` runs before `write_run`). N1's route left no ledger file
only because that criteria file had no `criteria` list.

### N9 - small items

* `proofpack run` with `--out` naming the input's own directory leaves
  `<input>.mapping.json` (original headers and value summaries) beside `run.json`. The
  file is the customer's, written by `map`; `run` wrote nothing named `mapping.json` into
  any of the 115 pack directories. Recorded because DEC-26's rationale is the hand-over.
* A `grace` licence with no other warning exits 0 with the watermark (`run.py`'s "exit 0
  / 2" reads as "0, or 2 when a warning exists"; measured: `rc 0`, `warnings []`,
  `watermark 'LICENCE EXPIRED - not for submission'`).
* `expires` spellings Python's `fromisoformat` accepts beyond the issuer's `isoUtc`:
  `2027-09-01 00:00:00Z` (space), `20270901T000000Z` (basic), `.123Z`, `+00:00` -> `ok`;
  lower-case `z`, a naive timestamp, a date only, an epoch string -> `expires_unparsable`;
  an epoch integer -> `missing_field`.

## Sentences refused

- "the criteria engine emits the right status on every input" - 95 criteria files and 33
  hand-built Numbers were fed; the hand-built shapes in N3 show the routing depends on
  invariants of the Number builders, not of `_row`.
- "`verify` accepts exactly what D1 section 7 says" - 116 constructions; `issued` after
  `expires`, `models 0` and a 31-day trial (`issued + 30 d + 24 h skew`) are accepted and
  D1 does not speak to them.
- "no non-finite float can reach a run" - N1.
- "the attainability figure is exact" - exact against my own Wilson formula for n = 1..500
  at four levels (0.0); it is the figure at `evaluate`'s level, not the Number's
  (RG-N2, hand-built).
- "the ledger counts every acceptance run" - the race and the aborted runs (N8).
- "the sixth payload was new" - it raised at `ab729d3` too (N2).
- "no `met` row carries `attainable_at_n: false`" - true of the 115 documents walked and
  of every Number `proportion` builds at 0.95; one hand-built Number produces it.

## Could not break

Every figure from this session, `wt-2cd7e16`, `PYTHONPATH` forced, unless another sha is
named.

- **Suite, markers, lint.** `python -m pytest -q -p no:cacheprovider`: `788 passed, 1
  skipped, 1 xfailed in 64.53s`; `-m day7` 139; `day6` 285; `day5` 54; `day4` 182; `day3`
  29 + 1 xfailed; `day2` 40; `day1` 59 + 1 skipped; `ruff check` `All checks passed!`;
  `ruff format --check` `108 files already formatted`; `doctor --offline` exit 0.
  PowerShell 5.1, `$env:PYTHONPATH` set and `proofpack.__file__` printed under the
  worktree first: `-m day7` `139 passed, 651 deselected in 7.67s`, ruff and doctor the
  same lines, `licence show` with no file `refused (no_file)`, exit 4. `day7: Day 7` is in
  `pyproject.toml` line 73 and `.github/workflows/ci.yml` lines 28-46 read the marker list
  from it. `git diff --name-status 02d00c5 2cd7e16 -- tests/`: 4 `M`, 0 `D`; the tests
  diff adds one `@pytest.mark.parametrize` and no `skip` / `xfail` / `.only`; every changed
  file `i/lf` in the index. The E6 handoff's block: the schema test `1 passed in 2.01s`;
  repair-r7's 27 `27 passed`; day-5 round-1's seven and round-2's seven `7 passed` each;
  `map --input tests/fixtures/mapping/sepsis_2019.csv < /dev/null` exit 3, 3485 bytes, 27
  lines, no output file; the long-s probe `categorical None None`; the hidden-module
  import (`scipy` x3, `statsmodels`, `sklearn`, `cryptography` x6 set to `None`) imports
  `proofpack`, `.stats`, `.licence`, `.licence.verify`, `.criteria`, `.run`, `.cli`,
  `.manifest`, `verify(b"abc")` -> `refused not_two_segments`, no scipy module loaded.
  `DEFAULT_B 2000`, `DEFAULT_SEED 20240101`, `DEFAULT_LEVEL 0.95`, `MIN_UNITS_PER_STRATUM
  2`, `MAX_FROZEN_VARIANCE_SHARE 0.2`, `MIN_USABLE_FRACTION 0.90` unchanged; `git diff
  a0c9abc 2cd7e16 -- src/proofpack/stats/` changes no constant (the lens-1 N8 six-file
  list; `2cd7e16` itself touches `attainability.py`'s docstring only).
- **Pre-fix proof.** The four edited test files copied into `wt-02d00c5`: `3 failed, 124
  passed in 6.96s` - the two params of
  `test_a_method_none_number_at_n_zero_or_n_null_is_annotated_method_not_wilson` and
  `test_a_zero_denominator_site_row_is_annotated_method_not_wilson_through_run`, each on
  `E       AssertionError: assert {'not_estimab..._denominator'} == {'not_estimab...d_not_wilson'}`
  / `Right contains 1 more item: {'attainability_not_computed': 'method_not_wilson'}` -
  the note's three, on the note's lines. Worktree restored with `git checkout`.
- **The gates (95 `criteria.yaml` files through `run --offline`).** H08 from the schema:
  `value` absent / `null` / `"0.85"` / `true`; `comparator` `=>` / `≥`; `statistic`
  `ci_lower_bounds`; `id` `7` / `""`; `scope: all`; `fairness.bound "0.1"`; a bound
  without `statistic`; `criterion_of_interest` absent; `ledger.warn_after_acceptance_runs`
  `0` / `-1` / `"3"` / `true` / `{}`; `operating_point: null` typed on a threshold-free
  metric. H08 from `declare`: `author` `""` and `"   "`, `date` absent, `justification`
  `" \t"`. H09: `level S9`, `attribute hospital`, `level 3` (int), `level 1.0`,
  `Unknown/missing` on a table with no missing `sex`, `op9`, `sensitivity` without an
  operating point, `auroc` with one, metric `sensitivty`. Rows: the statistic named is
  the one compared (`ci_lower_bound <` `met` on 0.668 < 0.7 with the figure filled and
  `attainable_at_n null`; `ci_upper_bound <=` on 0.817; `specificity >` 0.5 `met`,
  `attainable True`); `value -1` `met` / `True`, `1` and `1.0000001` `not_met` / `False`
  at n = 128; `age` `level: "*"` four rows (`0-40` n 38 ... `80-200` n 26), `40-65` one
  row, `41-66` `not_assessable / level_absent`; `site *` three rows with S3 `n 13`
  `attainable False` against `0.7719046276458018`; `sex *` with 60 blank values -> `F` and
  `M` only, `Unknown/missing` named -> one row `n 22`; `tpr_gap` at `F` `met` (0.217 <=
  0.3), at the reference `M` `level_is_reference`, at `site` `no_fairness_block` without
  a block and `gap_requires_fairness_attribute` with one on `sex`; `auroc_gap` overall
  `gap_requires_fairness_attribute`; `f1` `point_estimate` overall `not_assessable /
  no_interval / analytic_ci_unavailable` `n 400`; `oe` `point_estimate <= 1.2` `met` on
  0.71 (`log_delta`), `oe ci_lower_bound >= 0.8` `not_met` on 0.615, `calibration_slope`
  `met` on 1.056 (`irls_wald`), `calibration_intercept` `<= 0.5` `met` on -0.493, `ipa`
  `<= 0.9` `met` on 0.28 (`bootstrap_percentile`), `ipa` at a site
  `metric_not_computed_for_scope`, `brier` at S1 `met` on 0.151, `kappa` / `psi`
  `metric_not_computed`; a comparator reference standard: `sensitivity`
  `metric_not_computed`, `ppa` `met` on 0.668, `ppa` at S3 `not_met` on 0.355 `n 13`,
  `ppv` `met`; two operating points: `se2` at `op2` on 0.9015, the fairness bound one row
  per op (`op1` 0.217 `not_met`, `op2` 0.158 `not_met`), `gap2` at `op2` `met`;
  `lower_is_positive` with rule `<=` on the mirrored scores: the same 2 x 2 (`tp 96, fn 32,
  fp 66, tn 206`) and `auroc 0.8353`; `report_both_ways` with 20 indeterminate labels:
  `analysed 380`, `n 120`; the fairness bound on `age` (three non-reference bands) and on
  `site`; `bound 0` and `-0.1` `not_met`; `calibration_by_group` `not_estimable_this_run`;
  `auroc_gap` as the criterion of interest `not_met` on 0.16; `criteria: []` and no
  `criteria` key -> no rows, count unchanged.
- **The row, by hand (33 Numbers).** `method none` with `zero_denominator` `n 0`,
  `boundary_estimate`, `insufficient_clusters`, `single_class`, `n None`: `not_assessable
  / no_interval`, both attainability fields `null`, `attainability_not_computed:
  method_not_wilson` under `ci_lower_bound`; no attainability key under `ci_upper_bound`
  and `point_estimate`. `cluster_bootstrap_percentile` with an interval under `<=`: `met`
  with the annotation and no figure. `wilson_cc`, `clopper_pearson`, `WILSON`, a missing
  `method` key: annotated. `wilson` with `n 30.0`, `n -5`, `n np.int64(30)`, `n` absent:
  both `null`, no annotation (the guard as written). `balanced_accuracy` on `wilson`:
  `met`, no figure, no key. `ci_lo None` without a reason: `no_interval`. `overall null`:
  `overall_not_computed`. `evaluate(level=0.80)` on a Number at `ci_level 0.80` `k = n =
  30`: `met`, `attainable True`, figure `0.9480957277857291`.
- **Attainability re-derived.** R2 section 1.1's Wilson lower bound at p = 1, `z` from
  `statistics.NormalDist().inv_cdf`, no repo code, n = 1..500 at 0.80 / 0.90 / 0.95 /
  0.99: max |engine - own| **0.0**; max |engine - n / (n + z^2)| 1.11e-16. Figures
  0.8864866068260313 (30), 0.9286524008666414 (50), 0.9811546736227335 (200),
  0.2065493143772375 (1), 0.3423802275066532 (2), 0.999996158555936 (10^6).
  `proportion(n, n).ci_lo == max_lower_bound_at_n(n)` for n in {1, 2, 5, 30, 128, 1000}
  and `proportion(n - 1, n).ci_lo` below it. Through `run`: `C_n30` `not_met`, `n 30`,
  `False`, `0.8864866068260313` on `0.5212421254128505`; `sensitivity` `n 128` = tp + fn.
- **Verdict grep.** My own walker (whole words after splitting on non-letters, the 40
  `VERDICT_WORDS` plus the brief's seven; substrings of the seven as a second pass) over
  every key and string of 53 `run.json` files (with and without criteria, clustered,
  comparator, y-pred-only, every gate variant that ran) outside `declarations`: 0 hits
  outside `criteria_results`; inside it only `met`, `not_met`, `not_assessable` as whole
  tokens and none of `pass`, `fail`, `verdict`, `meets`, `acceptable`, `consistent`,
  `unbiased` as a substring; `assessable` appears outside the block in 0 strings.
  `ingest_report.json`: counts, hashes, role names; 0 hits; no `row_id`.
- **Manifest.** Two runs in one process: differing paths `$.ledger.acceptance_runs`,
  `$.manifest.duration_s`, `$.manifest.ledger_count`, `$.manifest.run_id` (one pair),
  plus `$.manifest.started` (a second pair straddled a second); `input_sha256`,
  `criteria_sha256`, `mapping_sha256` each equal `hashlib.sha256(file bytes)` and equal
  across the pair. `mapping.json` re-indented -> `mapping_sha256` changes, no other block
  moves (DEC-27: the bytes are hashed - and the file is the mapping, so a reformatted file
  is a different artefact; D1 section 4.2 asks for the mapping's hash and does not say
  canonical). `criteria.yaml` LF instead of the CRLF `write_text` produced, a BOM on it, a
  BOM on the input, CRLF on the input: each run completes, the one hash changes,
  statuses and every other block equal. `canonical_json`: `nan`, `inf`, `np.float64(nan)`
  -> `ValueError`; `np.int64`, `np.bool_`, `np.float32`, `datetime`, `Path`, `bytes`,
  `set`, `ndarray` -> `TypeError`; `np.float64(2.5)`, a tuple, `10**30`, `-0.0`, `1e-400`
  (`0.0`) serialise; a lone surrogate -> `UnicodeEncodeError` (the CSV is read strict
  UTF-8, so none is built). 115 `run.json` files this session: 115 distinct `run_id`s, 0
  schema errors, no `NaN` / `Infinity` / BOM / CRLF byte, no `mapping.json` in any pack
  directory. `platform win-amd64-cp314`, `reference_platform false`; `started`
  whole-second `Z`, `duration_s` a float.
- **Ledger.** Limit 1: run 1 count 1 no warning, run 2 `W14 {count 2, limit 1}` exit 2;
  no `ledger` block -> `warn_limit null`, never W14; no `criteria` -> count unchanged, the
  history count reported. Same labels and scores with different attribute columns, or
  different scores on excluded rows -> the same key (the analysed `y_true` + `score`
  bytes, as the docstring says). The ledger file lives under `PROOFPACK_HOME`, never under
  `--out`. Twelve corruptions -> N8.
- **Licence (`verify`, ephemeral registry, `now` 2026-10-15T12:00Z).** `expires` 1 h /
  23 h / 24 h past -> `ok` (`days_left -1`); 24 h + 1 s and 25 h -> `grace`; 30 d and 31 d
  -> `grace` (-30, -31); 31 d + 1 s and 32 d -> `expired`; 1 s future `ok` (0); `grace_days
  0` 23 h `ok`, 25 h `expired`; a swapped issued/expires re-signed -> `expired`; trial
  issued 29 d / 31 d ago `ok` + `TRIAL` (1 / -1), 31 d + 1 h `grace`, 62 d `expired`,
  issued in the future `ok` + `TRIAL`, `expires` in 5 d `TRIAL` (5). Refused: three
  segments (two ways), an empty signature, an empty payload, `.` alone, no dot
  (`not_two_segments`); the signature over another licensee's payload, A's signature on
  the wrong key, all-zero / 63-byte / 65-byte / one-bit-flipped signatures
  (`signature_invalid`); a segment with one character changed (`missing_field`
  `licence_id` - the decoded JSON changed shape); `key_id` wrong / `""` / the shipped id on
  an ephemeral signature (`unknown_key_id`, the id echoed to 32 chars), `key_id` absent /
  `null` / `7` (`missing_field`); base64url and unpadded signature, unpadded segment, a
  base64url segment on a payload whose canonical spelling holds `+` (`probes/p7b.py`), a
  newline inside the signature, extra padding, a BOM, UTF-16 (`base64_invalid`); an
  array, a JSON string, random bytes (`payload_not_json_object`); `tier` `lifetime` /
  `Trial` (`unknown_tier`), `null` (`missing_field`); `grace_days` -1 / 1.0 / `true` /
  `"30"` (`missing_field`), 10**9 (`expires_unparsable {field: grace_days}`); `expires`
  naive / date-only / `""` / lower-case `z` / an epoch string (`expires_unparsable`,
  `detail {}`), `null` / an epoch int (`missing_field`); `issued` `null` / `yesterday`
  on an annual licence. Accepted: leading newline and spaces with a CRLF tail, a 3 MB
  `features` list, duplicate `tier` keys (last wins: `trial` -> `grace`), non-ASCII
  licensee, `company_no null` (what the issuer writes when none is given). The nine date
  payloads at `2cd7e16`: `+05:00` and `-05:00` -> `{}`; `9999-12-31Z` -> `{field:
  expires}`; trial `issued 9999` -> `{field: issued}`; `grace_days` 3 000 000 and 10**9 ->
  `{field: grace_days}`; `9999-12-31T22:00:00Z` with `grace_days 0` -> `{field: expires}`.
  A naive `now`, `now` in year 9999 (`expired`, -2911834) and year 1 (`ok`, 740223) do not
  raise. The signature segment never appears in `repr(result)`, `as_dict()`, `licence
  show`, `verify`, `install` or `--json-log` output (checked by substring on 17 CLI
  calls). An ephemeral-key file against the shipped registry -> `unknown_key_id`;
  `SHIPPED_PUBLIC_KEY` hex `5d82e76854675953ac2e86f04a691ba3fab2dfb6a73b36be691a6e9f39ab3000`,
  32 bytes, equal to `keys/licence_pub.b64` and `licence_pub.json` (`pp-2026-09`); one bit
  changed in `SHIPPED_PUBLIC_KEY_B64` alone -> `ImportError: the shipped and published
  licence keys differ; rotate both together` at import; both literals changed together
  (stale `__pycache__` removed first - a same-size, same-second rewrite was served from
  bytecode until it was) -> 2 tests fail in `tests/test_licence.py`
  (`..._by_bytes_and_the_published_copy_is_the_same`, the canonical-spelling param).
  The site's `scripts/verify_licence.py` and the engine agree on a good file (`signature
  OK` / `ok valid`), a payload re-encoded with another licensee (`InvalidSignature` /
  `refused signature_invalid`) and a signature with one bit flipped (the same pair). The
  CLI: `verify` / `show` / `install` on good, expired, grace, trial, tampered, missing and
  a directory: statuses and exit codes as the docstring (0 on `ok` / `grace`, 4 else); a
  refused file is not installed; `--json-log` on `show` and `verify` carries the
  `as_dict()` fields and the path only.
- **Sockets.** `socket.socket`, `create_connection`, `getaddrinfo` and
  `urllib.request.urlopen` replaced with raisers: `run` with `--offline` (exit 0, licence
  from `PROOFPACK_LICENCE`) and without it (exit 0): 0 calls. Licence states through
  `run`: valid -> `licence_id` and `tier annual`, `watermark null`, exit 0; expired past
  grace -> exit 4, `run.json` written, the one-line fix printed; none -> exit 4, `tier
  null`; trial -> `TRIAL`; grace -> the expired watermark, exit 0 with no other warning.
- **Item 25 and the day-4/5/6 figures.** 19 constructions -> N1 (finite on 18; the
  overflow is the O:E numerator, not the sd). Eight documents assembled with each
  tree's own `tests/assembler.py` at `a0c9abc` and `2cd7e16` (i.i.d., clustered,
  comparator, logit, prevalence 0.05 x 600, lower-is-positive, five-site 120-row,
  y-pred-only) and diffed path by path: **0 values differ** on the seven `a0c9abc` can
  build; the one changed value is `overall.threshold_free.roc[0][2]` `inf` -> `null`;
  added keys `dev_rows`, `resample_sd_reason`, `guidance_refs`, `suppression_log`; the
  y-pred-only document raises `ValueError: calibration needs a score column` at
  `a0c9abc` and builds at `2cd7e16` (item 28).
- **DEC-26.** No mapping -> `HALT H07: run proofpack map first: no confirmed mapping.json
  was given (--mapping FILE) and none exists beside the input as <input>.mapping.json` in
  0.01 s (400 rows) and 0.10 s (50 000 rows) against 0.71 s / 1.96 s for the confirmed run;
  `decided_by` `proposed` / `yes` -> `this one was not confirmed`; `interactive` -> runs;
  the header-set hash altered -> H07; absent -> `could not be read`; a medium role
  unconfirmed -> H07, `confirmed: true` on it -> runs (DEC-28); a role renamed, an
  `original` outside the headers, `roles: []`, a role missing, a duplicate `y_true` ->
  lane A's H07 lines; a list, an empty file, `{{{` -> H07; `--mapping` elsewhere ->
  `mapping_sha256` of that file; `--mapping` missing -> H07; `--yes` accepted; no pack
  directory on any H07. Item 26: `""`, `NA`, `null`, `nan`, `NaN`, `N/A`, `None`, `na`, a
  space -> `HALT S05: case_id is blank in 1 row(s); fill every case id or drop the
  column`, exit 3, nothing written; `-` and `#N/A` are ids (not in the schema's
  `missing_tokens`). Item 27: 50 `dev` rows -> `dev_rows 50`, `analysed 350`, the flow
  sums to `rows_read`. Item 28 -> N5. Item 30 -> N6.

## Could not check

- The reference platform (`linux-x86_64-cp312`) and F17's cross-platform half.
- A licence signed by the production key (none exists off the issuer).
- `licence install` across a symlink (`os.symlink` refused: Windows privilege).
- The `/docs/run` and `/docs/licence` anchors the CLI prints (lane S).
- PowerShell 5.1 for the full suite and the sweep (Git Bash; `-m day7`, ruff, doctor and
  `licence show` in PowerShell only).
- The day-6 sweep (`--marker day6`): not re-run; `2cd7e16` touches no file it plants in.
- E8's rendering of `criteria_results`, `detail.attainability_not_computed` and
  `manifest.watermark`.
