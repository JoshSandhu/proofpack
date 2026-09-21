# Lens 2 (regression and record) - E7 repair 1, lane E, `02d00c5` on `ab729d3` - 2026-09-21

**Verdict: PASS. No blocker.** Every figure in the repair note re-measures exactly in both
shells: `784 passed, 1 skipped, 1 xfailed`; `-m day7` 135; `-m day6` 285; `-m day5` 54;
`day1`..`day4` 59+1 / 40 / 29+1 / 182; ruff, format and doctor clean; the sweep `--list`
170 ids, 0 duplicates, 34 day5 + 112 day6 + 24 day7; `--marker day7` `24 planted, 24
killed, 0 survived; 110 s`. The four edited test files copied into a worktree at `ab729d3`
give `12 failed, 111 passed`, each of the twelve on the `E` line the note quotes (the three
`OverflowError` spellings, `assert ('not_met' == 'not_assessable'`, `assert ('met' ==
'not_assessable'`, `assert (True is None)`, `assert (False is None)` twice, and the run
test's `AssertionError: {'attainable_at_n': None, ... 'criterion_id': 'F1_pe'`). Lens 1's
two blockers no longer reproduce (below). Five non-blocking items follow, one of them a
sentence the hard rule refuses.

Worktrees `wt-02d00c5`, `wt-ab729d3` and `wt-a0c9abc` under
`scratchpad/lens-E7-r2-regression/`, `PYTHONPATH=<worktree>/src` forced and proved before
the first figure (`python -c "import proofpack;print(proofpack.__file__)"` printed each
worktree's own `src\proofpack\__init__.py`; the unforced form in `wt-02d00c5` printed
`C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py`, the `.pth` trap). All
three removed at the end. The main tree was read only (`git diff`, `git log`, `git
ls-files`, `git status`); `git status --short` was empty before this note was written.
Every figure below is from this session.

---

## Lens 1 blockers, re-run at `02d00c5`

- **B1 (method `none` compared on `point_estimate`).** Hand-built Number `est 0.90, ci
  (None, None), method none, single_class, n 100` under `point_estimate >= 0.95`, `>= 0.5`,
  `ci_lower_bound >= 0.0`, `ci_upper_bound <= 1.0`: all four rows `not_assessable /
  no_interval`, `detail.not_estimable_reason single_class`, `compared_value None`. Through
  `proofpack.cli.main` on the synthetic cohort: `F1_pe` and `MCC_pe` `not_assessable /
  no_interval`, `analytic_ci_unavailable`, the Numbers' `est` `0.6620689655172414` and
  `0.4821183187439812` (the test asserts them at 1e-12 and passes). At `ab729d3` the same
  test file fails on `assert ('not_met' == 'not_assessable'` and `assert ('met' ==
  'not_assessable'`.
- **B2 (`met` beside `attainable_at_n false` on a cluster-bootstrap cell).** The lens-1
  construction (400 rows in 200 two-row cases, S3 = rows 0-29 all negative, score 0.1
  except row 0 at 0.9; `specificity` and `accuracy` `ci_lower_bound >= 0.89` at `{site,
  S3}`) through `tests/assembler.py` and through `run --offline`: both rows `met`,
  `compared_value 0.9`, `n 30`, `method cluster_bootstrap_percentile`, `attainable_at_n
  None`, `max_lower_bound_at_n None`, `detail {attainability_not_computed:
  method_not_wilson}`; the cell `ci (0.9, 1.0)`, `k 29`, `n_cases 15`. Re-derived without
  repo code: case c000000 is drawn m ~ Binomial(15, 1/15) times per resample; P(m >= 4) =
  0.014 < 0.025 < P(m >= 3) = 0.074, so the 2.5th percentile of the resampled proportion is
  27/30 = 0.9, above the k = n Wilson figure 0.886486606826 at n = 30 - the lens's
  arithmetic holds and `(14/15)^15 = 0.3553`. At `ab729d3` the three B2 tests fail on
  `assert (False is None)`.

## Non-blocking

**N1 - a sentence generalises past its measured inputs (sentence; `criteria.py` lines
37-39, README lines 293-295).** "On any other method (`cluster_bootstrap_percentile`,
`none`) both are `null` and `detail.attainability_not_computed` is `method_not_wilson`."
Measured: a hand-built Number `method none, not_estimable_reason zero_denominator, n 0,
est None` under `sensitivity ci_lower_bound >= 0.9` gives `not_assessable / no_interval`,
`detail {'not_estimable_reason': 'zero_denominator'}` - both attainability fields `null`
and **no** `attainability_not_computed` key, because `_row`'s annotation branch is guarded
by `n > 0`. The same Number with `n 5, single_class` carries both keys. The row is right
(a typed reason is present, nothing is omitted - DEC-08 holds); the sentence is not: write
"whose `n` is above 0" or name the `n = 0` case. `zero_denominator` under `ci_lower_bound`
on a proportion is reachable from `run` (lens 1: sensitivity on an all-negative site). No
test feeds it to the annotation branch.

**N2 - the attainability level is `evaluate()`'s argument, not the Number's `ci_level`
(not reachable from `run` today).** `_row` computes `max_lower_bound_at_n(n, level)` with
`level` = `evaluate(..., level=0.95)`'s default while comparing the Number's own `ci_lo`.
Hand-built Wilson Number at `ci_level 0.80`, `k = n = 30`, `ci_lo 0.948096` (Wilson at
0.80), criterion `specificity ci_lower_bound >= 0.9`: `met` with `attainable_at_n False`
and `max_lower_bound_at_n 0.8864866068260313` - the B2 contradiction on a `wilson` row.
With `evaluate(level=0.80)` the same row is `met` / `True` / `0.9480957277857291`. Not
reachable: `criteria_schema.json` has no level key, `run.py` calls `evaluate(decl, doc)`
with the default, and every Number in the three assembled documents scanned (406 / 384 /
390 Numbers) carries `ci_level 0.95`. Carry: read `number["ci_level"]` in `_row` (or
refuse with a typed detail when it differs from `level`), with this hand-built Number as
the test.

**N3 - `detail.attainability_not_computed` and its value `method_not_wilson` are pinned
by no schema enum** (`criterionResult.detail` is `{"type": "object"}`); the same shape as
lens 1's RG-N9 (`resample_sd_reason`). The schema also states neither of the two rules
this repair added (`method none` -> `status not_assessable`; a filled attainability field
-> `method wilson`); only `tests/test_criteria.py::assert_no_met_row_is_marked_unattainable`
and the B1 tests inspect them. A `criterionResult` `allOf` (`if method == "none" then
status == "not_assessable"`) would make `jsonschema.validate` in the run test a second
observer. Own item.

**N4 - `detail.field` names the term that overflowed, not the extreme value.** Signed
payloads (ephemeral key, `now` 2026-10-15T12:00Z): `expires 9999-12-30T00:00:00Z` with the
default `grace_days 30` -> `refused expires_unparsable, detail {field: grace_days}`
(`expires + 24 h` fits; `+ 30 d + 24 h` does not); a trial with `issued 9999-11-01` and
`expires 9999-12-31T23:59:59Z` -> `{field: grace_days}` likewise. The description
("the grace end lies outside the datetime range (detail.field)") is accurate as written;
a reader of `licence show` is pointed at a field that is 30. Fifteen further payloads
beyond the test's five (`grace_days` 10**12, 10**30, 2**31, 999 999 999; `expires`
`9999-12-31T23:59:59-05:00`, `9999-12-31T23:59:59.999999Z`, `0001-01-01T00:00:00Z`,
`0001-01-02T00:00:00+05:00`; `issued` `0001-01-01T00:00:00+05:00`; trial `issued
0001-01-01`; two trials near year 9999) were fed: none raised, each `refused` /
`expired` / `ok` as the module docstring's rules read. Also recorded: `issued
9999-12-31T23:59:59Z` on an annual licence whose `expires` is 2027 verifies `ok valid,
days_left 320` - `issued > expires` is not inspected anywhere (pre-existing, not this
repair's).

**N5 - counts the notes disagree on, recorded.** Lens 1 regression wrote "`git diff
--name-status a0c9abc ab729d3 -- tests/`: 8 `A`, 13 `M`"; measured at both `ab729d3` and
`02d00c5`: 7 `A`, 13 `M`, 0 `D` (`tests/fixtures/item25_oe_block_a0c9abc.json`,
`test_bootstrap_carried.py`, `test_criteria.py`, `test_ledger.py`, `test_licence.py`,
`test_manifest.py`, `test_run_cli.py`). The repair note's "closed form identical to 12
places (difference 0.00e+00 at each)": at n = 30 the hand Wilson and `n / (n + z^2)`
differ by 1.11e-16 (0.00e+00 at 50 and 200); identical to 12 places, as it says.

## What was measured and could not be broken

**Suite and lint.** Git Bash, `wt-02d00c5`, `PYTHONPATH` forced: `python -m pytest -q -p
no:cacheprovider` `784 passed, 1 skipped, 1 xfailed in 77.55s`; `-m day7` `135 passed,
651 deselected in 8.43s`; `-m day6` `285 passed, 501 deselected in 15.06s`; `-m day5` `54
passed, 732 deselected in 24.10s`; `-m day4` `182 passed`; `-m day3` `29 passed, 1
xfailed`; `-m day2` `40 passed`; `-m day1` `59 passed, 1 skipped`; `ruff check` `All
checks passed!`; `ruff format --check` `106 files already formatted`; `doctor --offline`
`All essential checks passed.`, exit 0. PowerShell 5.1, same worktree, `$env:PYTHONPATH`
set and `proofpack.__file__` printed under the worktree first: full suite `784 passed, 1
skipped, 1 xfailed in 67.42s` (the note left this cell "not repeated"); `-m day7` 135 in
8.76 s; `-m day6` 285 in 12.54 s; `-m day5` 54 in 20.06 s; ruff, format and doctor the same
lines. 784 - 771 = 13 = 135 - 122: the four B1 params less the one replaced test, the B2
hand test, the synthetic invariant, the B2 assembled test, five licence params, the B1 run
test and the B2 run test. `day7: Day 7` is in `pyproject.toml`'s marker list and
`.github/workflows/ci.yml` lines 30-47 loop over every `day\d+` marker read out of it.

**Nothing weakened.** `git diff --name-status ab729d3 02d00c5 -- tests/`: 4 `M`, no `D`;
`a0c9abc..02d00c5`: 7 `A`, 13 `M`, no `D`. The tests diff adds no `skip`, `xfail`,
`.only`, `TODO` and removes no `pytest.mark` line. Three test functions were renamed with
their bodies rewritten (`..._never_not_met` -> the four-param B1 test, dropping the half
that asserted `met` on `point_estimate`; `..._except_the_three_volatile_keys` ->
`..._and_the_ledger_count` with four assertions added; `test_assemble_run_writes_nothing`
-> `..._only_the_ledger_file_under_home`, recursive). Every changed file is `i/lf` in the
index.

**Pre-fix.** The four edited test files copied into `wt-ab729d3` (then restored with `git
checkout`): `12 failed, 111 passed in 7.81s`. Passing there, as the note discloses: the
`ci_upper_bound <= 1.0` param (`ci_hi` is `None` at `ab729d3`), the two invariant
observers over the i.i.d. documents, the renamed RG-N1 and RG-N2 tests, and the RG-N3
literals test (the engine was right; the literal was not). The note's 14 / 109 was
measured before the helper's literal `"wilson"`; 12 / 111 is the committed state.

**Item 25 at `a0c9abc`.** `tests/test_bootstrap_carried.py` and its fixture copied into
`wt-a0c9abc`, `-o markers=day7`: `E       AssertionError: inf` / `E       assert inf is
None` on the item-25 test; `AttributeError: ... no attribute '_resample_sd'` and `KeyError:
'resample_sd_reason'` on the two helpers; the snapshot test passes; `3 failed, 1 passed`.
`git diff a0c9abc 02d00c5 -- src/proofpack/stats/bootstrap.py` is `27e6bbc`'s change
only: `_resample_sd`, `RESAMPLE_SD_NOT_FINITE`, the one `usable.std(ddof=1)` line and the
`sd_reason` / `resample_sd_reason` pass-throughs; `02d00c5` does not touch the file.

**Sweep.** `scripts/mutation_sweep.py --list` in the worktree: 170 lines, 170 unique ids,
34 day5 / 112 day6 / 24 day7; `--marker day7`: `24 planted, 24 killed, 0 survived; 110 s`
(the note: 106 s); the three new mutants (`method_none_point_estimate_compared`,
`attainability_on_any_method`, `grace_overflow_raises`) and the two re-targeted ones are
each `killed`; worktree clean afterwards.

**Wilson at k = n, by hand.** R2's Wilson lower bound at p = 1 with `z =
NormalDist().inv_cdf(0.975)`, no repo code: 0.886486606826 (30), 0.928652400867 (50),
0.981154673623 (200); the engine deviates 1.11e-16, 0.0, 0.0; the old literal 0.928655 is
2.60e-6 from the hand figure (inside the old 5e-6 tolerance, outside the new 1e-9).

**Criteria sweep.** 30 metric ids x 3 statistics x 2 comparators x 3 scopes = 918 criteria
evaluated over the i.i.d. synthetic document (S3 = 30 rows, a `sex` fairness block) and
over the clustered B2 document: 0 rows with `met` / `not_met` on `method none` or with
`compared_value None`; 0 rows `met` beside `attainable_at_n False`; 0 filled attainability
fields off a `wilson` row; 0 `ci_lower_bound` proportion rows with `n > 0` on a non-Wilson
method lacking `attainability_not_computed`. Status counts i.i.d. 171 met / 171 not_met /
576 not_assessable (`no_interval` 12, `metric_not_computed` 84,
`metric_not_computed_for_scope` 420, `gap_requires_fairness_attribute` 60); clustered 105 /
105 / 708 (`no_interval` 60, `overall_not_computed` 96). In those documents (406 / 384 /
390 Numbers) `method none` <=> `not_estimable_reason` set <=> `ci_lo None` with 0
exceptions, so `_row`'s two-condition route and the old `_statistic_of` route agree on
every Number except the `point_estimate` rows the repair changed. On the run route a
proportion Number's method is `wilson`, `cluster_bootstrap_percentile` or `none`
(`bootstrap.proportion_ci`); `wilson_cc` and `clopper_pearson` exist in the day-2 API only.

**Licence.** `SHIPPED_PUBLIC_KEY`, `PUBLISHED_PUBLIC_KEY`, `keys/licence_pub.json`
`public_key` and the one non-comment line of `keys/licence_pub.b64` all decode
(`validate=True`) to `5d82e76854675953ac2e86f04a691ba3fab2dfb6a73b36be691a6e9f39ab3000`,
32 bytes; `key_id pp-2026-09` in the json and `SHIPPED_KEY_ID`. `curl -sL
https://proofpack.globalphoenix.co.uk/trust`: 61,541 bytes,
`XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA=` once, `pp-2026-09` once. Reference
verifier `proofpack-site/scripts/verify_licence.py` and the engine on three files signed
by a key generated in this process and discarded: good -> `signature OK`, rc 0, printed
payload equal to `LicenceResult.payload`, engine `ok valid`; payload re-encoded with a
changed `licensee` -> rc 1 `cryptography.exceptions.InvalidSignature`, engine `refused
signature_invalid`; one bit of the signature flipped -> the same pair. The diff, the
repair note, the two lens-1 notes and the tests carry no `PRIVATE KEY`, `-----BEGIN`,
`LICENCE_SIGNING_KEY`, seed or signature; the only base64 / hex strings of 40+ characters
in the diff are the public key's two spellings; `Ed25519PrivateKey` appears in
`tests/conftest.py` (ephemeral generation) and in the test that asserts its absence from
`src/`; no `.lic` / `.pem` / `.key` is tracked. `import proofpack, proofpack.stats,
proofpack.licence, proofpack.licence.verify, proofpack.criteria, proofpack.manifest,
proofpack.run, proofpack.cli` with `cryptography` (five module names), `scipy`,
`scipy.stats` and `scipy.special` set to `None` in `sys.modules`: imports;
`verify(b"abc")` -> `refused not_two_segments`. `test_offline_opens_no_socket` and
`test_no_oracle_leaks` pass. `REASON_CODES` 14 in both registers; `STATUSES` four.

**CLI in both shells** (`scratchpad/e2e_shell/test.csv` + `criteria.yaml` +
`test.csv.mapping.json`, an empty `PROOFPACK_HOME` per shell, `--offline`): the five
lines the note quotes, identical apart from `run_id` (`a5262257-...` Git Bash,
`5364d4e2-...` PowerShell), `exit=4`; rows `C_met` met `wilson` `True`
`0.9708630437264916` on `0.6684443704768314`, `C_n30` not_met `wilson` `False`
`0.8864866068260313` on `0.5212421254128505`, `C_auroc` met `delong_wald` nulls,
`fairness:tpr_gap` not_met `newcombe10` nulls on `0.217046664854876`, three `C_f1_site`
`metric_not_computed_for_scope`, `C_ece` `metric_not_computed`, `C_prior`
`requires_compare`; `manifest.watermark 'LICENCE EXPIRED - not for submission'`,
`ledger_count 1`. The two `run.json` files are 216,303 bytes each, no CRLF, no BOM; the
manifest keys that differ are `duration_s`, `run_id`, `started`; with those blanked no
top-level block differs; the three SHA-256 fields are equal; the two
`ingest_report.json` are byte-identical. `licence show` with no file: `licence: none
found` / `status: refused (no_file)` / `Next step: proofpack licence install FILE (docs:
/docs/licence)`, `exit=4` (PowerShell). The E6 block's schema test `1 passed in 2.10s`;
the round-5 probe `profile_column(['17 \u017fep 2024'] * 60)` -> `inferred_type
'categorical', min None, max None` (printing needs `PYTHONIOENCODING=utf-8` in Git Bash;
the value is the same).

**Verdict grep.** Own walker over every key and string of the Git Bash `run.json` (statuses
`met`, `not_met`, `not_assessable` all present): 0 hits on the 40 `VERDICT_WORDS` plus the
brief's seven outside `criteria_results` / `declarations`; inside, the whole tokens `met`
and `not_met` only; the substrings `pass`, `fail`, `verdict`, `meets`, `acceptable`,
`consistent`, `unbiased` absent from every non-`declarations` key and string.

**Schema.** `git diff ab729d3 02d00c5 -- schema/`: two `description` strings; 0 changed
`required` / `enum` / `type` / `additionalProperties` lines. `criterionResult.reason_code`
enum equals `criteria.REASON_CODES` (test read and passing).

**Sentences in the diff.** Each added sentence that names a behaviour was checked against
a run: "est is not compared on a Number that carries no interval, whatever the statistic
named" - the three statistics are the whole `STATISTICS` enum and the B1 test feeds all
three; "the one file it writes is `<PROOFPACK_HOME>/ledger.json`" - the recursive walk
asserts `after - before == {"home/ledger.json"}`; the F17 sentence names the four keys and
the ledger body key that were measured to differ, and my cross-shell comparison differed
in three (one home each); "no new status, no new acceptance" (the note's DEC-12 paragraph)
- of my fifteen extra licence payloads none that would have raised at `ab729d3` is now
`ok` or `grace`. The one sentence found false is N1.

**Lens 1's "could not break", re-verified where this round reaches it:** the key bytes,
the reference verifier, the imports with `cryptography` and `scipy` hidden, the socket
test, the verdict grep, the F8 row, the item-25 `E` line, the F17 keys, DEC-26's
`mapping.json` absence from both pack directories - all as they wrote.

## Could not check

- The reference platform (`linux-x86_64-cp312`): `reference_platform false` here.
- A licence signed by the production key: none exists off the issuer; the shipped key's
  bytes and id and an ephemeral-key file are what was exercised.
- The mutation sweep in PowerShell (Git Bash only, as the note's table marks it).
- E8's rendering of `detail.attainability_not_computed` and of the B1 `not_assessable`
  rows (no renderer yet).
- DEC-12(i)'s fresh-attack half on this repair: the parallel fresh-attack lens's job; this
  note is the regression lens.

## Cut and carried, checked against the note

The note's carried table (FA-N1, N2, N4-N8; RG-N4, N8-N14) matches what the tree shows:
no lock in `io/ledger.py`, `has_criteria=bool(decl.criteria)` in `run.py`, `c.get("scope",
"overall")` in `criteria.py`, `run.py`'s one watermark string, the `skipif` in
`test_licence.py`, and the CLI summary line `criteria rows: 2 met, 2 not met, 5 not
assessable` reproduced in both shells. Open and not in the note: N1-N4 above.

## Sentences this lens refused to write

- "No `met` row can carry `attainable_at_n: false` now" - a hand-built Wilson Number at
  `ci_level 0.80` produces one (N2); the sentence written is the 918-row sweep's count.
- "`verify` never raises" - twenty inputs (the test's five and my fifteen) were fed; the
  docstring's list is the claim.
- "The schema pins the two new rules" - it does not (N3); the tests do.
- "On any other method the detail says why" - false at `n = 0` (N1).
