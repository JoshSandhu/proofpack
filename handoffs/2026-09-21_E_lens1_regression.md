# Lens 1 (regression and record) - build day 7, lane E, `ab729d3` - 2026-09-21

**Verdict: FAIL.** One blocker. A `point_estimate` criterion on a Number that has no
interval (`method: none`, a typed `not_estimable_reason`) is reported `met` or `not_met`,
not `not_assessable`; it is reachable from the CLI on the synthetic cohort (`f1` and `mcc`
at `op1` carry `analytic_ci_unavailable` on every i.i.d. run, and a `point_estimate >= 0.99`
criterion on either comes back `not_met` with `method: none` in the criteria row), and the
README, the `criteria.py` docstring and the test name
`test_a_number_without_an_interval_is_not_assessable_never_not_met` all say the opposite
of what the code does. Everything else in the build note re-measures exactly: `771 passed,
1 skipped, 1 xfailed` in both shells; `-m day7` 122; `-m day6` 285; `-m day5` 54;
`day1`..`day4` 59+1 / 40 / 29+1 / 182; ruff and format clean; doctor clean; the sweep
`34 day5 + 112 day6 + 21 day7, 0 duplicate ids` and `--marker day7` `21 planted, 21
killed, 0 survived; 89 s`; the item-25 test fails at `a0c9abc` on `E       AssertionError:
inf` / `E       assert inf is None`; the shipped key bytes equal both site key files and
the live `/trust` page; the site's reference verifier and the engine agree on the same
files, and the engine also accepts three licences issued by the site's own
`functions/_lib/licence.mjs` under an ephemeral seed. Fourteen non-blocking items follow,
four of them sentences the hard rule refuses.

Worktrees: `ab729d3` and `a0c9abc` under `scratchpad/lens-E7-r1-regression/`,
`PYTHONPATH=<worktree>/src` forced and proved by `python -c "import
proofpack;print(proofpack.__file__)"` printing each worktree's own
`src/proofpack/__init__.py` before every figure below (once a stale `.pyc` of the same size
and mtime second served a mutated `keys.py` after `git checkout` had restored the source;
`__pycache__` was cleared and the figure re-measured). Both removed at the end. The main
tree was used read-only (`git diff`, `git log`, `git show`); `git status --short` was empty
before this note was written.

---

## Blocker

### B1 - a `point_estimate` criterion on a Number with no interval is `met` / `not_met`, never `not_assessable`

**Rule.** The day's binding text: "a criterion on a Number whose interval is unavailable
(method none, a typed reason) is not_assessable, never not_met". E6 handoff "Tomorrow needs"
5 says the same. D1 section 2 lists "CI not estimable" among the `not_assessable` reasons
with no statistic qualifier. `README.md` (this commit): "A Number with no interval is
`not_assessable`, never `not_met`." `criteria.py` module docstring: "a Number with no
interval (a typed `not_estimable_reason`) or a suppressed one gives `not_assessable` and
carries the reason in `detail` - never `not_met`".

**What the code does** (`criteria._row`, lines 332-341): `compared = _statistic_of(number,
statistic)`; only when that is `None` is the row `no_interval`. For `point_estimate` the
statistic is `est`, which a typed-reason Number carries, so the row is compared and comes
out `met` or `not_met` with `method: none`. The test's second half asserts exactly this
("point_estimate on the same Number: est exists, so it is compared") under a name that says
"never_not_met". The build note's "Decisions taken" does not record this choice; the
"Sentences refused" list does not refuse it.

**Counter-examples run (worktree `ab729d3`).**

1. Hand-built Number `est 0.90, ci (None, None), method none, not_estimable_reason
   single_class`; criterion `sensitivity @ op1, point_estimate >= 0.95` ->
   `status not_met, reason_code statistic_compared, method none, compared_value 0.9`.
   The same Number with `>= 0.5` -> `met`.
2. Through `proofpack.cli.main` on the synthetic 400-row cohort with S3 = 30 (the
   test-file criteria plus two rows): `F1_pt` (`f1 @ op1 point_estimate >= 0.99`) ->
   `status not_met reason statistic_compared method none`, the Number read being
   `overall.op1.f1` with `method none`, `not_estimable_reason analytic_ci_unavailable`,
   `ci (None, None)`, `est 0.6620689655172414`; `MCC_pt` likewise, `est
   0.4821183187439812`. `run.json` written, exit 0, the document validates against the
   schema (the `criterionResult` `allOf` only ties `met`/`not_met` to
   `statistic_compared` and a numeric `compared_value`, which this row has).

**Why it matters.** A pack row saying "criterion not met" over a quantity the engine
itself says it cannot put an interval on is the vendor-set-verdict class of defect: the
customer's own `point_estimate` criterion is read, but D1 and the binding rule say the
answer on such a Number is `not_assessable` with the reason, and three shipped sentences
promise exactly that. Whether `point_estimate` should ever be compared on a
`method: none` Number is Josh's to decide (it is a reasonable question); until he does, the
rule as written is the rule, and the shipped text must not say one thing while the code
does another.

**Repro (one line, from the `ab729d3` worktree with `PYTHONPATH=<wt>/src`, `tests` on
`sys.path`):**
```
python -c "import sys;sys.path.insert(0,'tests');from conftest import make_criteria;from proofpack import criteria as c;from proofpack.io.declare import validate_dict;d=validate_dict(make_criteria(criteria=[{'id':'P','metric':'sensitivity','operating_point':'op1','scope':'overall','statistic':'point_estimate','comparator':'>=','value':0.95,'author':'A','date':'2026-01-01','justification':'j'}],fairness=None));n={'est':0.9,'ci_lo':None,'ci_hi':None,'ci_level':0.95,'method':'none','n':100,'flags':[],'suppressed':False,'not_estimable_reason':'single_class'};print(c.evaluate(d,{'overall':{'op1':{'sensitivity':n},'threshold_free':{}},'subgroups':[],'fairness':None,'calibration':None,'calibration_suppressed_reason':None})[0]['status'])"
```
prints `not_met`.

**Repair shape (for the repairer, not a decision):** in `_row`, when
`number.get("not_estimable_reason") is not None` (or `method == "none"`), return
`not_assessable` / `no_interval` with the reason in `detail` for every statistic; keep
`attainable_at_n` filled; regression test on the two literal inputs above (the hand-built
Number and the `f1`/`mcc` rows of the synthetic run) failing on `assert status ==
'not_assessable'` with `E       AssertionError: assert 'not_met' == 'not_assessable'` at
`ab729d3`; rename the test; correct the README, the docstring and the test's comment. If
Josh instead rules that `point_estimate` is comparable on such Numbers, the README, the
docstring, D1 section 2 and the binding text change, and the test name changes - the code
stays. Either way `criteria.py` is not a statistical gate, so DEC-12(i) does not attach
to this repair; the `bootstrap.py` change of `27e6bbc` does (below, N12).

---

## Non-blocking

**N1 - `assemble_run` "writes nothing" is false (sentence; run.py line 178, the note's
item 7, `test_assemble_run_writes_nothing`).** `assemble_run` calls `ledger.record_run`,
which writes `<PROOFPACK_HOME>/ledger.json`. Measured: with `PROOFPACK_HOME` a fresh
`home/` under a temporary directory, `sorted(rglob) after - before` of one `assemble_run`
call is `['home\\ledger.json']`. The test inspects only the top-level names of `tmp_path`
(`home` already exists, so the list is unchanged); it does not inspect what the docstring
claims. Write "writes nothing under `--out`; the ledger file is written" and make the test
walk recursively.

**N2 - "the only ones that differ" is false in two shipped strings (sentence).**
`schema/output_schema_v1.json` `manifest.description`: "run_id, started and duration_s are
the only ones that differ between two runs of the same inputs on one platform (F17)";
`manifest.py` module docstring lines 5-7 say the same; the F17 test is named
`..._except_the_three_volatile_keys` while its body blanks four manifest keys and
`ledger.acceptance_runs`. Measured (two `main([...run...])` calls in one process, same
inputs): manifest keys differing `['duration_s', 'ledger_count', 'run_id', 'started']`,
top-level blocks differing `['ledger', 'manifest']`, `ledger.acceptance_runs` 1 then 2;
every SHA-256 equal. The build note says this correctly (decision 14, `HISTORY_KEYS`); the
schema, the docstring and the test name do not.

**N3 - the note's attainability figure at n = 50 is mis-rounded.** Note and test comment:
"0.928655 (50)". Re-derived by hand from R2's Wilson formula with `z =
NormalDist().inv_cdf(0.975)` (no repo code) and from the closed form `n / (n + z^2)`:
`0.928652400867` (both; the engine's `max_lower_bound_at_n(50)` deviates 0.0 from each).
`0.886486606826` at 30 and `0.981154673623` at 200 round to the note's figures; 0.928652
does not round to 0.928655. The test's `abs=5e-6` tolerance (2.6e-6 away) is what lets it
pass; tighten to the true six-place figure and 1e-9.

**N4 - `map`'s default output and `run`'s default input disagree (DEC-26 wording).**
`map --out` defaults to `mapping.json` in the working directory; `run` looks for
`<input>.mapping.json` beside the input. A customer who follows `HALT H07: run proofpack
map first` literally (`proofpack map --input test.csv`, then `proofpack run --input
test.csv ...` with no `--mapping`) reaches the same H07 a second time (measured: `map`
non-interactive halts here because stdin is not a terminal, so the second leg was measured
with no file present: `HALT H07: run proofpack map first: no confirmed mapping.json was
given (--mapping FILE) and none exists beside the input as <input>.mapping.json`, exit 3).
DEC-26 says "written beside the pack directory"; the build put the default beside the
input. One default for both commands, or `run`'s H07 line naming `map --out
<input>.mapping.json`, closes it. Needs-from-Josh candidate.

**N5 - `value: .nan` / `.inf` in `criteria.yaml` ends in exit 5, not H08.** YAML's `.nan`
and `.inf` load as Python floats, `criteria_schema.json` `type: number` admits them, and
the run computes to the end and dies at `canonical_json`: `internal error: ValueError: Out
of range float values are not JSON compliant: nan` (and `: inf`), exit 5, no directory
written, no traceback. Typed and nothing wrong reaches a file, but a customer-authored
value should be refused at `io.declare` as H08 naming the field.

**N6 - a new `skipif` on a hard-coded absolute path.**
`test_the_site_reference_verifier_agrees_on_the_same_file` skips unless
`C:/Users/joshs/GPS/ProofPack/proofpack-site/scripts/verify_licence.py` exists, so on CI
(Linux) it is a skip and the note's "the site's verify_licence.py agrees" is measured only
on this machine. The file has no other skip; nothing was xfailed or `.only`-ed; no marker
was removed (grep of the tests diff: 0 removed `pytest.mark` lines). Vendor the ten-line
verifier into `tests/` or read the path from an environment variable with a clear reason.

**N7 - one lane-A CLI-route assertion weakened.**
`tests/test_mapping_repair3_2.py::test_a_header_spelled_like_the_ignored_key_is_h07_without_the_header`
asserted `err.splitlines()[0].startswith("HALT H07: a column's header equals the ignored:
key")` through `run`; it now asserts `startswith("HALT H07: ")` because the hand-built
prior's `prob -> y_pred` (low, unconfirmed) is refused by the `--yes` rule first. The direct
`apply_mapping` assertion of the exact message and detail is unchanged, so the message is
still pinned; the CLI route of it is not. Setting `confirmed: True` on that entry would
have kept the original assertion.

**N8 - `overall.threshold_free.roc` carries every distinct score value into `run.json`.**
Measured on the 400-row synthetic run: the first row's score string occurs once in the
document, at `.overall.threshold_free.roc[333][2]`; 401 ROC points, 400 distinct scores.
Permitted (D1 section 4 puts `roc` in the document; the local pack is exempt from the
aggregates rule) but it is the score column in sorted order, and A-P2's egress
suppression must strip it; the note does not say so.

**N9 - `resample_sd_reason` / `resample_sd_not_finite` are pinned by no schema enum.** The
Cell's `bootstrap` block is `{"type": ["object", "null"]}` (open since day 4), so the new
key and its one value are asserted only by `tests/test_bootstrap_carried.py`. `W14` / `W15`
are in `WARN_CODES` (closed, `Finding` validates against it) and asserted registered; the
schema's `warnings[].code` is a free string (pre-existing). `no_score_column` is in the
`calibrationSuppressedReason` enum (diffed).

**N10 - new public functions without a docstring:** `manifest.platform_tag`,
`sha256_file`, `scipy_version`, `utc_now_iso`; `licence.install_location`;
`ledger.ledger_path`; `criteria.needs_operating_point`;
`declare.metric_needs_operating_point`. The module docstrings carry the formula / D1 line
for each; the functions themselves do not.

**N11 - the engine's `REQUIRED_FIELDS` omit `company_no`, `models` and `features`,** which
D1 section 7 lists in the payload and the issuer always writes. A payload lacking `models`
verifies `ok`. Not a security property (the signature covers whatever is there); a shape
choice the note does not record.

**N12 - DEC-12(i) attaches to `27e6bbc`.** `bootstrap.py` is a statistical gate; the diff
touches only `_resample_sd` (new), the one line in `bootstrap_percentile` that called
`usable.std(ddof=1)`, the `sd_reason` field and the eight `CellCI` pass-throughs (3 in
`bootstrap.py`, 3 in `subgroups.py`, 2 in `calibration.py`; counted in the diff). No
statistic changed: the item-25 snapshot test passes at `ab729d3` with only the two sd keys
stripped. The fresh-attack lens still has to attack it; this note is the regression lens.

**N13 - the five new feature test files fail at `a0c9abc` at collection**
(`ModuleNotFoundError: No module named 'proofpack.licence'` from `test_run_cli.py:39`;
`test_criteria.py`, `test_ledger.py`, `test_licence.py`, `test_manifest.py` likewise), not
on an assertion. Expected for tests of new modules; recorded so nobody reads "fails
pre-build" as pinning a behaviour. The item-25 test is the one that fails on the quoted
assertion (below).

**N14 - the CLI summary prints `met` / `not met` / `not assessable` counts** ("criteria
rows: 2 met, 2 not met, 5 not assessable"). Not in the document, so no grep test sees it;
the status vocabulary and nothing else. Recorded because the E6 rule says the criteria
block is the one place the words appear, and stdout is a second place.

---

## What was measured and could not be broken

Every figure below was measured in this session in the `ab729d3` worktree unless it says
`a0c9abc`.

**Suite and lint** (Git Bash, `PYTHONPATH` forced): `771 passed, 1 skipped, 1 xfailed in
89.29s`; `-m day7` `122 passed, 651 deselected`; `-m day6` `285 passed, 488 deselected`;
`-m day5` `54 passed, 719 deselected`; `-m day1` `59 passed, 1 skipped`; `-m day2` `40
passed`; `-m day3` `29 passed, 1 xfailed`; `-m day4` `182 passed`; `ruff check` `All checks
passed!`; `ruff format --check` `104 files already formatted`. PowerShell 5.1: full suite
`771 passed, 1 skipped, 1 xfailed in 59.12s`; `-m day7` 122; `-m day6` 285; `-m day5` 54;
ruff and format the same lines. Difference from `a0c9abc`'s 649 / 1 / 1 is 122 = the day-7
marker count. `git diff --name-status a0c9abc ab729d3 -- tests/`: 8 `A`, 13 `M`, no `D`.
`day7: Day 7` is declared in `pyproject.toml` beside `day6`; `.github/workflows/ci.yml`
reads the marker list out of `pyproject.toml` (lines 30-50), so it runs `-m day7` without
an edit. `uv.lock` `146 +++`, nothing removed; `cryptography>=42` added to
`[project.dependencies]`.

**Item 25 at `a0c9abc`** (test file and fixture copied into the `a0c9abc` worktree,
`proofpack.__file__` printed under `wt_base/src` first, `-o markers=day7`):
`test_item25_resample_sd_is_none_with_the_reason_and_the_block_serialises` fails on
`E       AssertionError: inf` / `E       assert inf is None`; the helper test on
`AttributeError: module 'proofpack.stats.bootstrap' has no attribute '_resample_sd'`; the
finite-cell test on `KeyError: 'resample_sd_reason'`; the snapshot test passes; `3 failed,
1 passed`. Re-derived at `a0c9abc` without the test: `sd inf`, `ci_hi
3.999999999999999e+159`, `json.dumps(..., allow_nan=False)` raises `Out of range float
values are not JSON compliant: inf`. At `ab729d3`: `est 13.333333333333334`, `ci (4.0,
3.999999999999999e+159)`, `method cluster_bootstrap_percentile`, `resample_sd None`,
`resample_sd_reason resample_sd_not_finite`, `usable_resamples 200`, `json.dumps` with
`allow_nan=False` succeeds. The `bootstrap.py` diff was read line by line: only the
non-finite branch and the pass-throughs (N12).

**Attainability against a hand oracle** (Wilson lower bound from R2's formula with `z`
from `statistics.NormalDist().inv_cdf(0.975)`; the closed form `n / (n + z^2)`; no repo
code): n = 30 `0.886486606826`, 50 `0.928652400867`, 200 `0.981154673623`, 7
`0.645669564933`, 1000 `0.996173241514`; the engine deviates 0.0 from the hand Wilson at
every n and at most 1.11e-16 from the closed form; level 0.90 at n = 30 `0.9172756918749008`
both ways. F8 on the synthetic run: `C_n30` `not_met`, `n 30`, `attainable_at_n False`,
`max_lower_bound_at_n 0.8864866068260313`, `compared_value 0.5212421254128505`, `method
wilson`. The `>=` / `>` boundary observer and the `<=` / `<` `None` are asserted in
`test_criteria.py` on literal inputs (read).

**F17** re-derived (N2): the differing keys are exactly `run_id`, `started`, `duration_s`,
`ledger_count` and `ledger.acceptance_runs`; `input_sha256`, `criteria_sha256`,
`mapping_sha256` equal across the two runs and equal `hashlib.sha256(file bytes)` (the test
asserts this; read). Across shells: the Git Bash and PowerShell `run.json` on the same
fixture differ only in `run_id`, `started`, `duration_s` and are byte-identical after those
three are blanked (each shell had its own empty `PROOFPACK_HOME`, so `ledger_count` is 1 in
both); no CRLF, no BOM, `watermark 'LICENCE EXPIRED - not for submission'`.

**F20.** All eight parametrised cases read in `test_licence.py` with the literal inputs
and figures the note lists (valid annual / quarterly `ok valid`; trial `ok valid TRIAL`;
expired 10 d `grace expired_within_grace` + watermark; 40 d `expired expired_past_grace` +
watermark; tampered payload `signature_invalid`; ephemeral-signed with the shipped key id
against the shipped registry `signature_invalid`; ephemeral key id against the shipped
registry `unknown_key_id`); skew 23 h / 25 h (`days_left -2`); trial 32 d / 31 d / 29 d; 300
random blobs and three truncations refused without raising. Beyond the note: three
licences issued by the site's own `functions/_lib/licence.mjs` `issueLicence` under an
ephemeral WebCrypto seed generated in Node (v24.18.0) and discarded: annual -> `ok valid`,
`days_left 364`, watermark `None`; trial with a 400-day payload expiry -> `ok valid TRIAL`,
`days_left 29` (the 30-day rule applied); quarterly expired 10 days -> `grace
expired_within_grace`, `days_left -11`, the expired watermark; all three carry the ten
payload keys the issuer writes; the annual one against the shipped registry -> `refused
unknown_key_id`. A signature-only tamper (last signature characters altered) is refused
`signature_invalid` by the engine and `InvalidSignature` by the site verifier (the suite
asserts only `refused` for that class).

**Keys.** `keys/licence_pub.b64` (one non-comment line) and `keys/licence_pub.json`
`public_key` both decode (`validate=True`) to
`5d82e76854675953ac2e86f04a691ba3fab2dfb6a73b36be691a6e9f39ab3000`, 32 bytes, `key_id
pp-2026-09`, `status live`; `SHIPPED_PUBLIC_KEY` and `PUBLISHED_PUBLIC_KEY` equal those
bytes and `SHIPPED_KEY_ID` equals the json's. `curl -sL
https://proofpack.globalphoenix.co.uk/trust` (61,541 bytes) contains
`XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA=` once, under "Key id pp-2026-09 Status live
Public key (base64, raw 32 bytes)". Mutating the `PUBLISHED_PUBLIC_KEY_B64` literal by one
character: `ImportError: the shipped and published licence keys differ; rotate both
together` (source then restored; `__pycache__` cleared - see the worktree paragraph).

**Reference verifier.** `scripts/verify_licence.py` in a subprocess with the ephemeral
public key file: good file `signature OK`, rc 0, printed payload equal to the engine's
`payload`; tampered payload rc 1 `cryptography.exceptions.InvalidSignature` beside the
engine's `refused signature_invalid`.

**No private key.** The diff, the build note and the tests carry no `PRIVATE KEY`,
`-----BEGIN`, `LICENCE_SIGNING_KEY=` value, seed or signature; `Ed25519PrivateKey` appears
only in `tests/conftest.py`'s ephemeral generation; no `.lic`, `.pem` or `.key` file is
tracked at `ab729d3`; the 64-hex strings in the diff are `uv.lock` hashes. Nothing printed
by `licence show` / `verify` / `run` in either shell contains a signature segment.

**Imports and sockets.** `import proofpack, proofpack.stats, proofpack.licence,
proofpack.cli, proofpack.run, proofpack.criteria, proofpack.manifest` with `cryptography`,
`cryptography.hazmat`, `cryptography.hazmat.primitives`, `cryptography.exceptions`, `scipy`
and `scipy.stats` all set to `None` in `sys.modules`: imports; `verify(b'abc')` -> `refused
not_two_segments`. `grep` of `src/proofpack` for `socket`, `urllib`, `http`, `requests`: 0
lines; `test_offline_opens_no_socket` (both `socket.socket` and `create_connection`
raising) passes in the suite.

**`cmd_map` untouched.** AST-level comparison of every top-level function in `cli.py`
between `a0c9abc` and `ab729d3`: changed `_build_parser`, `cmd_run`, `main`; new
`cmd_licence`; unchanged `_emit`, `cmd_doctor`, `_stdin_is_terminal`, `_ask`,
`_confirm_interactive`, `_tolerant_console`, `cmd_map`, `cmd_compare`.
`src/proofpack/io/mapping.py` is not in the diff.

**DEC-26 through `run`.** A `file`-confirmed mapping computed for a CSV with one extra
column, passed as `--mapping` for the other CSV: exit 3, no `--out` directory. No mapping
file, a missing `--mapping`, a `proposed` file beside the input: H07 with the lines the
note quotes (test read and passing). No `mapping.json` under `--out` in any run made here.

**Verdict grep.** On the no-licence `run.json` (statuses `met`, `not_assessable`,
`not_met` all present): 0 `VERDICT_WORDS` hits in any key or string outside
`declarations` / `criteria_results`; 0 `pass` / `fail` / `verdict` hits anywhere including
`declarations`. `REASON_CODES` (14) equals the schema's `reason_code` enum; `STATUSES`,
`STATISTICS`, `COMPARATORS` equal their enums (test read). `criteria_results`,
`suppression_log`, `guidance_refs` tightened from nullable to arrays; the top-level
`required` grew from 6 to 17; `manifest` is `additionalProperties: false` with 18
required; `flow.required` grew to 6. One loosening, deliberate and documented: the ROC
origin threshold `number` -> `["number", "null"]` (the `inf` that canonical JSON refuses).

**CLI in both shells** (`<scratchpad>/e2e`, `PROOFPACK_HOME` an empty directory,
`PROOFPACK_LICENCE` unset, `--offline`): the five `run` lines and `exit=4`, `licence show`
three lines and `exit=4`, `licence verify <absent>` `status: refused (no_file)` `exit=4`,
`doctor --offline` `[ok  ] licence  no licence file found - doctor/map/fixtures always
work; run/compare need one` / `All essential checks passed.` `exit=0`, identical in Git
Bash and PowerShell apart from `run_id`. The orchestrator's round-5 probe
(`profile_column(['17 \u017fep 2024'] * 60)`) prints `categorical None None` in
PowerShell.

**Mutation sweep** (worktree, `PYTHONPATH` exported so the child pytest inherits it):
`--list` 167 lines, 167 unique ids, 34 day5 / 112 day6 / 21 day7; `--marker day7` `21
planted, 21 killed, 0 survived; 89 s`, worktree clean afterwards.

---

## What could not be checked

- The CI run on the reference platform (`linux-x86_64-cp312`): `reference_platform` is
  `false` here; F17's cross-platform half and N6's skip on Linux are unmeasured.
- The interactive `proofpack map` leg of N4 (stdin is not a terminal in this session).
- The bootstrap change under attack (DEC-12(i)): the fresh-attack lens's job.
- The renderer's use of `manifest.watermark` (E8/E9 do not exist).
- A licence signed by the production key: no such file exists off the issuer, and the
  engine's registry was exercised with ephemeral keys only (plus the shipped key's bytes
  and id, which are what the production path needs).

## Cut and carried, checked against the note

The note's four cuts (clustered `overall` null; `cmd_compare` untouched - AST-identical;
gap criteria on a non-fairness attribute `gap_requires_fairness_attribute`; carried 16 /
15 / 9-13 not started) hold as measured. Open and not in the note: B1's decision, N1, N2,
N4 (the two defaults), N5, N6 (the CI skip), N8 (ROC thresholds and egress), N11.

## Sentences this lens refused to write

- "The criteria engine never reports `not_met` on a Number without an interval" - it does,
  on `point_estimate` (B1).
- "F17 holds: byte-identical except three keys" - four manifest keys and one ledger key
  differ; the figures are stated as measured (N2).
- "The engine verifies production licences" - only ephemeral-key files and the shipped
  key's bytes were measured; the sentence written is the one under F20 above.
- "The suite proves `--offline` opens no socket" - one test makes two `socket` names
  raise on one command; a grep finds no network import; that is what was inspected.
- "`run` writes nothing outside `--out`" - it writes `<home>/ledger.json` (N1).
