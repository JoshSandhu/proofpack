# Lens 3 (regression and record) - E7 repair 2, lane E, `2cd7e16` on `02d00c5` - 2026-09-21

**Verdict: PASS. No blocker.** Every figure in the repair-2 note re-measures exactly in both
shells: `788 passed, 1 skipped, 1 xfailed` (Git Bash 109.86 s under a concurrent lens,
PowerShell 61.53 s); `-m day7` 139; `-m day6` 285; `-m day5` 54; `day1`..`day4` 59+1 / 40 /
29+1 / 182; ruff, format (108 files) and doctor clean; the sweep `--list` 171 ids, 0
duplicates, 34 day5 + 112 day6 + 25 day7; `--marker day7` `25 planted, 25 killed, 0
survived` (106 s Git Bash, 110 s PowerShell - the note's table left PowerShell blank).
The four edited test files copied into a worktree at `02d00c5` give `3 failed, 124 passed
in 6.83s`, each of the three on the `E` line the note quotes (`assert {'not_estimab...
_denominator'} == {'not_estimab...d_not_wilson'}` / `Right contains 1 more item:` /
`{'attainability_not_computed': 'method_not_wilson'}`; the `insufficient_positives` param
on the same three lines with `...nt_positives'}` on the left). The two tests the note
discloses as sentence repairs (`-05:00` param, F17) pass at `02d00c5`: `7 passed`. Lens 2's
three sentence items (FA-N1 = RG-N1, FA-N2, FA-N3) are closed on the literal inputs that
raised them. Five non-blocking items follow, three of them sentence-precision items; none
is a defect a customer's run reaches.

Worktrees `wt2cd` (`2cd7e16`), `wt02d` (`02d00c5`), `wta0c` (`a0c9abc`) and `wtab7`
(`ab729d3`) under `scratchpad/lens-E7-r3-regression/`, `PYTHONPATH=<worktree>/src`
forced and proved before the first figure (`python -c "import proofpack;
print(proofpack.__file__)"` printed each worktree's own `src\proofpack\__init__.py`; the
unforced form in `wt2cd` printed `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\
__init__.py`, the `.pth` trap). All four removed at the end. The main tree was read only
(`git diff`, `git log`, `git ls-files`, `git show`, `git status`); `git status --short`
was empty before this note was written. Every figure below is from this session.

---

## Lens 2's items, re-run at `2cd7e16`

- **FA-N1 = RG-N1 (annotation at n 0 / null).** Hand-built `method none` Numbers under
  `sensitivity ci_lower_bound >= 0.9`: `n 0 / zero_denominator`, `n None /
  insufficient_positives`, `n 5 / single_class` -> each `not_assessable / no_interval`,
  both fields `None`, `detail {attainability_not_computed: method_not_wilson,
  not_estimable_reason: <reason>}`. Through `proofpack.cli.main --offline` on the lens-2
  literal input (400 rows, the 30 S3 rows' `y_true` `"0"`, `sensitivity ci_lower_bound >=
  0.8` at `{site, S3}`): the committed run test passes in the `2cd7e16` worktree and fails
  at `02d00c5` on the same three `E` lines. A 135-row grid (n in `0, 1, 30, -3, None, 30.0,
  np.int64(30), True, False` x method in `wilson, cluster_bootstrap_percentile, none,
  wilson_cc, None` x the three statistics), evaluated with each tree's own `criteria.py`:
  **0 rows differ in status, reason code, `attainable_at_n` or `max_lower_bound_at_n`**
  between `02d00c5` and `2cd7e16`; 24 rows gain the annotation, every one a
  `ci_lower_bound` row on a non-`wilson` method at n `0, -3, None, 30.0, np.int64(30),
  False`. The fill set at `2cd7e16` is `wilson` at n `1`, `30`, `True` (N4 below).
- **FA-N2 (F17 sentences).** `manifest.py`, the schema's `manifest.description` and
  `tests/test_manifest.py` lines 3-11 / 157 now say what the test body asserts (read:
  `differ <= VOLATILE_KEYS | HISTORY_KEYS`, `"run_id" in differ and "ledger_count" in
  differ`, `ledger_count (1, 2)`, `acceptance_runs (1, 2)`, the three SHA-256 equalities,
  `a == b` after blanking). My own two CLI runs in one home each (Git Bash, PowerShell):
  manifest keys differing `duration_s`, `run_id`, `started`; 0 top-level blocks differ
  after those three are blanked; the three SHA-256 fields equal; `ledger_count 1` both.
- **FA-N3 (`expires_unparsable` sentences).** Six payloads signed with a key generated in
  this process (`now` 2026-10-15T12:00Z): `+05:00` -> `{}`; `-05:00` -> `{}`;
  `9999-12-31T23:59:59Z` -> `{field: expires}`; trial `issued 9999-12-31` -> `{field:
  issued}`; `grace_days 3_000_000` and `10**9` -> `{field: grace_days}`; the
  `test_random_and_hostile_bytes_never_raise` inputs are `sig[:-8]`, `"A" * len(sig)`,
  `seg[:-4]` as the docstring now names them. See N1 for the `ab729d3` half of that
  sentence.

## Non-blocking

**N1 - "at `ab729d3` the first five of those six raised `OverflowError`" implies a sixth
that did not (record accuracy; `verify.py` line 20, `tests/test_licence.py` line
257).** Measured in `wtab7` (`ab729d3`, `PYTHONPATH` forced): `expires
9999-12-31T23:59:59-05:00` -> `OverflowError: date value out of range`, the same as the
`+05:00` payload. All six raised there; the sixth was simply not in the test until repair
2. The sentence as written is true of the five and silent on the sixth; a reader takes
the contrast as a fact. Write "all six raised `OverflowError` at `ab729d3`; the sixth
joined the test in repair 2".

**N2 - a citation covers a clause its test does not inspect (sentence; `stats/
attainability.py` lines 33-35, `criteria.py` lines 36-38).** "Under a `ci_upper_bound`
or `point_estimate` criterion, **or on a metric outside the set**, both are `null` and
`detail` has no attainability key (the same test, a Wilson Number under each)". The cited
`test_a_method_none_number_at_n_zero_or_n_null_is_annotated_method_not_wilson` feeds a
Wilson Number under `ci_upper_bound` and `point_estimate` only; no test feeds a metric
outside `PROPORTION_METRICS` and asserts `detail` carries no attainability key
(`test_attainability_fields_are_filled_for_a_lower_bound_proportion_criterion_only`
feeds `f1` and asserts the two fields `None`, not `detail`). Measured here: `f1` `wilson`
n 30 -> `met`, both `None`, `detail {}`; `f1` `none` -> `not_assessable`, `detail
{not_estimable_reason: analytic_ci_unavailable}` only; `auroc` `delong_wald` -> `met`,
`detail {}`. The behaviour holds on those three; the sentence should cite the LB-only
test and that test should assert the key's absence, or the clause should drop "the same
test".

**N3 - the note's DEC-12 paragraph generalises without a recorded run (sentence; the
repair note only).** "`attainable_at_n` / `max_lower_bound_at_n` are filled on exactly
the inputs they were filled on at `02d00c5`" is a claim over every input, supported in
the note by reading the two guards and one killed mutant. The 135-row grid above measures
it: 0 differences in the two fill fields. Recorded so the sentence has a run behind it;
the code is as the note says.

**N4 - two hand-built shapes the guard admits (not reachable from `run`).** (a) `n: True`
on a `wilson` Number: `isinstance(True, int) and True > 0` holds, so
`max_lower_bound_at_n` reads `0.2065493143772375` (the k = n bound at n = 1) and
`attainable_at_n` `False` against 0.9. (b) A `wilson` Number with `suppressed: true`, `n
3`: the annotation branch runs before the `suppressed` return, so the row reads
`not_assessable / suppressed` beside `attainable_at_n False`, `max_lower_bound_at_n
0.4385029682449546`. `assert_no_met_row_is_marked_unattainable` does not see (b) (the
status is not `met`). Neither is built by the engine: `n` on the run route is a Python
`int` count (lens 2 counted 366 of 366), and no engine route sets `suppressed=True`
(`grep -rn suppressed src/proofpack`: the `Number` field, its validator, and
`subgroups.py`'s pass-through; k-suppression is egress, A-P2's). Own item if E8 or A-P2
starts building suppressed Numbers: move the annotation branch below the `suppressed`
return, and use `type(n) is int` or refuse `bool`.

**N5 - F20's tampered-signature case pins `refused`, not the reason (pre-existing; not
this repair's).** `test_random_and_hostile_bytes_never_raise` asserts `status ==
"refused"` on `"A" * len(sig)` and the two cuts; no test flips a bit of an otherwise valid
signature and asserts `signature_invalid`. Measured: one bit flipped in byte 0 of the
signature -> engine `refused signature_invalid`, the site verifier `rc 1
cryptography.exceptions.InvalidSignature`; the same-length `A` replacement is
`signature_invalid` too. D1's F20 row lists tampered payload, not tampered signature, so
the test set matches D1; the task's fuller list is what this observes.

## What was measured and could not be broken

**Suite and lint.** Git Bash, `wt2cd`, `PYTHONPATH` forced: `python -m pytest -q -p
no:cacheprovider` `788 passed, 1 skipped, 1 xfailed in 109.86s`; `-m day7` `139 passed,
651 deselected in 8.34s`; `-m day6` `285 passed, 505 deselected in 11.63s`; `-m day5` `54
passed, 736 deselected in 18.28s`; `-m day4` `182 passed`; `-m day3` `29 passed, 1
xfailed`; `-m day2` `40 passed`; `-m day1` `59 passed, 1 skipped`; `ruff check` `All
checks passed!`; `ruff format --check` `108 files already formatted`; `doctor --offline`
`All essential checks passed.`, exit 0, 17 `[ok  ]` lines. PowerShell 5.1, same
worktree, `$env:PYTHONPATH` set and `proofpack.__file__` printed under the worktree
first: full suite `788 passed, 1 skipped, 1 xfailed in 61.53s`; `-m day7` `139 passed,
651 deselected in 8.02s`; ruff, format and doctor the same lines. 788 - 784 = 4 = 139 -
135: the two params of the hand test, the run test, the `-05:00` param. `day7: Day 7` is
`pyproject.toml` line 73; `.github/workflows/ci.yml` lines 30-53 read every `day\d+`
marker out of it.

**Nothing weakened.** `git diff --name-status 02d00c5 2cd7e16 -- tests/`: 4 `M`, 0 `D`;
`a0c9abc..2cd7e16`: 7 `A`, 13 `M`, 0 `D`. The tests diff's only added line matching
`skip|xfail|\.only|todo|pytest\.mark` is the new `@pytest.mark.parametrize`; no removed
line matches. No test renamed or deleted; the `-05:00` param's `field` column changed
from `"expires"` to `None` because the engine returns `{}` for it (measured at `02d00c5`
and `2cd7e16`, identical), so the earlier row asserted a `detail` the engine never
produced only because the old branch keyed on the `+05:00` string; the new branch keys
on `field is None` and the assertion is stricter, not looser. Every changed file is
`i/lf`. The diff adds no `def` outside the two tests; `cli.py` is untouched (`git diff
--stat` names no file under `src/` beyond `criteria.py`, `licence/verify.py`,
`manifest.py`, `stats/attainability.py`); `git diff -- src/proofpack/stats/` is
`attainability.py` alone, docstring lines only.

**Pre-fix.** Above: `3 failed, 124 passed in 6.83s` at `02d00c5`, then `git checkout --
tests/` and `git status --short` empty.

**Item 25 at `a0c9abc`.** `tests/test_bootstrap_carried.py` and its fixture copied into
`wta0c`, `-o markers=day7`: `E       AssertionError: inf` / `E       assert inf is None`
on the item-25 test; `AttributeError: module 'proofpack.stats.bootstrap' has no attribute
'_resample_sd'` and `KeyError: 'resample_sd_reason'` on the two helpers; the snapshot
test passes; `3 failed, 1 passed`. `git diff a0c9abc 2cd7e16 -- src/proofpack/stats/
bootstrap.py`: 37 insertions, 1 deletion, all of them `_resample_sd`,
`RESAMPLE_SD_NOT_FINITE`, the one `usable.std(ddof=1)` line and the `sd_reason` /
`resample_sd_reason` pass-throughs (`27e6bbc`); `02d00c5` and `2cd7e16` do not touch it.

**Sweep.** `--list` 171 lines, 171 unique ids, 34 day5 / 112 day6 / 25 day7 in both
shells; `--marker day7` `25 planted, 25 killed, 0 survived; 106 s` (Git Bash) and `110 s`
(PowerShell); the re-targeted `attainability_on_any_method` and the new
`attainability_annotation_needs_positive_n` each `killed` (`1 failed, 34 passed` / `1
failed, 38 passed`); worktree clean afterwards in both.

**Schema.** `git diff 02d00c5 2cd7e16 -- schema/`: two `description` strings; 0 changed
`required` / `enum` / `type` / `additionalProperties` / `const` lines. Registers at
`2cd7e16`: `METHODS` 18, `FLAGS` 15, `NOT_ESTIMABLE_REASONS` 21, licence `REASON_CODES`
14, `STATUSES` 4 - unchanged from lens 2; this diff adds no entry to any of them.

**Licence.** `SHIPPED_PUBLIC_KEY_B64`, `PUBLISHED_PUBLIC_KEY_B64`, `keys/licence_pub.json`
`public_key` and the one non-comment line of `keys/licence_pub.b64` all decode
(`validate=True`) to `5d82e76854675953ac2e86f04a691ba3fab2dfb6a73b36be691a6e9f39ab3000`,
32 bytes, equal to `SHIPPED_PUBLIC_KEY`; `SHIPPED_KEY_ID pp-2026-09` equals the json's.
`curl -sL https://proofpack.globalphoenix.co.uk/trust`: 61,541 bytes,
`XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA=` once, `pp-2026-09` once. Reference
verifier `proofpack-site/scripts/verify_licence.py` and the engine on three files signed
by a key generated in this process and discarded: good -> `signature OK`, rc 0, printed
payload equal to `LicenceResult.payload`, engine `ok valid`; `licensee` changed in the
payload -> rc 1 `InvalidSignature`, engine `refused signature_invalid`; one bit of the
signature flipped -> the same pair; the good file against the shipped registry ->
`refused unknown_key_id`. F20 rows on that key: valid `ok valid`; expired 10 d `grace
expired_within_grace` + the EXPIRED watermark; expired 40 d `expired expired_past_grace`
+ watermark; `key_id pp-2026-09` on the ephemeral registry `refused unknown_key_id`;
trial 10 d old `ok valid` + `TRIAL`. `expires 9999-12-30T12:00:00Z` with `grace_days 30`
-> `refused expires_unparsable {field: grace_days}` (FA-N6, carried as the note says).
Seven `expires` spellings: naive `2027-09-01T00:00:00` and `2027-09-01` -> `refused
expires_unparsable {}` (so the new `REASON_CODES` text "with an offset" is accurate); a
space separator, `+00:00`, `Z`, basic format `20270901T000000Z` and an ISO week date ->
`ok`. The diff, the repair note, the two lens-2 notes and the tests carry no `PRIVATE
KEY`, `-----BEGIN`, `LICENCE_SIGNING_KEY` or `Ed25519PrivateKey` outside
`tests/conftest.py`'s ephemeral generation and the test that asserts its absence from
`src/`; the only base64 / hex strings of 40+ characters in the diff are the public key's
two spellings (in the lens-2 notes); no `.lic` / `.pem` / `.key` is tracked. `import
proofpack, proofpack.stats, proofpack.licence, proofpack.criteria, proofpack.manifest,
proofpack.run, proofpack.cli` and `proofpack.licence.verify` with `cryptography` (six
module names), `scipy`, `scipy.stats`, `scipy.special`, `statsmodels` and `sklearn` set
to `None` in `sys.modules`: imports; `verify(b"abc")` -> `refused not_two_segments`; a
well-formed two-segment file -> `refused missing_field` before the signature is reached;
no `scipy` module loaded.

**Sockets.** `socket.socket`, `create_connection`, `getaddrinfo` replaced with raisers,
`proofpack.cli.main` `run` with and without `--offline` on the e2e fixture: both complete
(exit 4, no licence), 0 calls.

**CLI in both shells** (`scratchpad/e2e_shell/test.csv` + `criteria.yaml` +
`test.csv.mapping.json`, an empty `PROOFPACK_HOME` per shell, `--offline`): the five
lines the note quotes, identical apart from `run_id` (`fa7ba355-...` Git Bash,
`fb6dbc50-...` PowerShell), `exit=4`; rows `C_met` met `wilson` `True`
`0.9708630437264916` on `0.6684443704768314`, `C_n30` not_met `wilson` `False`
`0.8864866068260313` on `0.5212421254128505`, `C_auroc` met `delong_wald` nulls on
`0.7948394595133246`, `fairness:tpr_gap` not_met `newcombe10` nulls on
`0.217046664854876`, three `C_f1_site` `metric_not_computed_for_scope`, `C_ece`
`metric_not_computed`, `C_prior` `requires_compare`, every `detail {}`; `run.json`
216,303 bytes, no CRLF, no BOM; `ingest_report.json` byte-identical to the builder's
`pack_repair2`; against `pack_repair2/run.json` with `run_id`, `started`, `duration_s`
blanked: 0 top-level blocks differ. `licence show` with no file: `licence: none found` /
`status: refused (no_file)` / `Next step: proofpack licence install FILE (docs:
/docs/licence)`, `exit=4` in both shells. The pack directory holds `run.json` and
`ingest_report.json` only; the home holds `ledger.json` only (DEC-26).

**Verdict grep.** Own walker over every key and string of the Git Bash `run.json`
(statuses `met`, `not_met`, `not_assessable` all present): 0 hits on the 40
`VERDICT_WORDS` plus the brief's seven outside `criteria_results` / `declarations`;
inside, the whole tokens `met` and `not_met` only; `pass`, `fail`, `verdict`, `meets`,
`acceptable`, `consistent`, `unbiased` absent as substrings from every byte of the file.

**The E6 block.** `test_the_assembled_document_validates_against_the_output_schema` `1
passed in 2.00s`; repair-r7's 27 `27 passed, 155 deselected in 0.68s`; day-5 round-1's
seven `7 passed, 47 deselected in 1.72s`; round-2's seven `7 passed, 47 deselected in
2.88s`; the long-s probe `profile_column(['17 \u017fep 2024'] * 60)` (`proofpack.io.
profile`, `PYTHONIOENCODING=utf-8`) -> `categorical None None`.

**Carried items, spot-checked as honest carries.** FA-N4: on one home, a normal run ->
count 1; `value: .inf` in `criteria.yaml` -> `internal error: ValueError: Out of range
float values are not JSON compliant: inf`, no pack directory, count 2. FA-N8: the count
edited to JSON `true` -> the next run's `ledger.acceptance_runs 2`, no W15. FA-N6: above.
Each reproduces at `2cd7e16` as the note's table says it would.

**Sentences in the diff.** Each added sentence naming a behaviour was checked against a
run: "whatever `n` (0 and `null` included)" - the 135-row grid; "a `wilson` Number whose
`n` is not an `int` above 0 leaves both `null` with no annotation" - `n` `0`, `None`,
`30.0`, `np.int64(30)`, `-3` on `wilson`, all `None` / `None` / `{}`; "`started` (whole
seconds) and `duration_s` may or may not differ" - the test body asserts neither; "the
two offset payloads above" carry empty `detail` - measured; "a `grace_days` of 30 is
named when `expires` is 9999-12-30" - measured; "signature segment cut by eight ...
payload segment cut by four ... `A` repeated to the same length" - the test's three
literals. The sentences found imprecise are N1 and N2.

## Could not check

- The reference platform (`linux-x86_64-cp312`): `reference_platform false` here.
- A licence signed by the production key: none exists off the issuer.
- E8's rendering of `detail.attainability_not_computed` (no renderer yet).
- DEC-12(i)'s fresh-attack half on this repair: the parallel fresh-attack lens's job.

## Cut and carried, checked against the note

The note's carried table (FA-N4..N9, RG-N2..N5) matches the tree and the three items I
re-ran. Open and not in the note: N1-N5 above.

## Sentences this lens refused to write

- "The annotation is now complete" - a `wilson` Number with a non-int `n` is unannotated
  by the guard as written (measured on five such `n`); the grid's 24 rows are what
  changed.
- "No suppressed row carries an attainability figure" - N4(b) is one, hand-built.
- "`verify` never raises" - six date payloads and seven spellings were fed; the module
  docstring's list is the claim.
- "F17 holds" - the differing keys of my two runs are listed as measured.
- "All six raised at `ab729d3`" as a property of a class - six literal payloads were fed
  in `wtab7`; two are what N1 reports.
