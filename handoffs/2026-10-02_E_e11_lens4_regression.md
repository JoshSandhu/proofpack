# Lane E - build day 11 (E11) - lens 4, regression-and-record, at `ba26d88` (repair 3 `6e19574` + the rewritten handoff; base `45e6761`; Friday 2 October 2026)

**PASS. No blockers.**

Lens 3's two blockers no longer reproduce at `ba26d88`. Each has a regression test that fails at `45e6761` on an assertion, not an import abort.
- **FA-B2: McNemar printed on clustered pairs.** I checked 7 clustered compares: 5 of my own shapes, which the repair-3 tests do not use, and the repairer's 2. Every McNemar entry in them reads `p null, method none, not_computed_reason mcnemar_assumes_independent_pairs`. On my 5, T2 prints `n.e. (mcnemar_assumes_independent_pairs)` in all three McNemar cells. None of their 12 or 13 claim paragraphs names McNemar, and every `PAIRED_DIFF` sentence says "paired rows" (7 per page, 0 "paired cases").
- **FA-B1: clustered differences printed with no tier and no `ᵈ`.** My own walker looks for any Number with an interval that lacks the mark, lacks a case-count tier below 30 cases, or has fewer than five cases. It found none: 0 of 1,123 intervals in 11 clustered documents of shapes the repair-3 tests do not use, two of them with a fairness block and criteria.

Every count, size and figure the note quotes reproduces exactly: the suite, the seven markers, ruff, every command in its table, the walk counts, the McNemar type I error figures, the coverage probe and the fails-at-base list. The suite, the markers, ruff and the table's commands ran in both shells, except the sweeps: day-11 in Git Bash, day-10 in PowerShell. The probes and re-run scripts ran in Git Bash only. The times differ because my runs were contended. Example: the day-11 sweep took 1222 s against the note's 1109 s.

There are eight non-blocking records. Read N1 first. Repair 3 made a measured figure that T7 prints false. The T7 table "Which annotations each calibration cell carries" says the clustered O:E on its stated input carries `['log_delta_refused_clustered']`. On that input it now carries `['log_delta_refused_clustered', 'clustered_coverage_not_established']`.

This is the regression half of DEC-12 (i)'s owed rounds. It does not discharge the fresh-attack lens, which re-derives coverage.

Setup. Detached worktrees under `scratchpad/lens-E11-r4-regression/`:
- `wt1` (`ba26d88`): the suite, markers, commands and probes;
- `wt0` (`45e6761`): the new and changed tests, copied in;
- `wt2` (`ba26d88`): the two mutation sweeps;
- `wt3` (`ba26d88`): my own planted mutants, each restored with `git checkout`.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`, in Git Bash and in PowerShell 5.1. Every suite run had `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8` and `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1. The two sweeps ran side by side with my probes, so every time here is contended. I committed, pushed, downloaded and paid for nothing. This note is the only file I wrote outside the scratchpad.

## Blockers

None.

## Non-blocking

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **A measured figure on the T7 page is false since repair 3.** The section "Which annotations each calibration cell carries (R2 section 3.3)" comes from `design/conventions_T7.md` lines 386-393 and is printed on every T7 (golden `T7.html` line 222). Its input is "60 one-row cases with 3 events (`p = 0.08` on every row ...) ... under a declared plan". For the clustered O:E / intercept-in-the-large row it prints "measured `['log_delta_refused_clustered']`". Repair 3 puts the mark on both cells, and the table was not re-measured. The Brier row's `[]` is still true: on this input the Brier has no interval (`boundary_estimate`). The repair note does not mention the table. | Same input through `assemble`, `case_id` one per row, `clustering.unit: case_id`. At `ba26d88`: `oe ['log_delta_refused_clustered', 'clustered_coverage_not_established']`, `intercept_large ['irls_wald_refused_clustered', 'clustered_coverage_not_established']`. At `45e6761`: `oe ['log_delta_refused_clustered']`. Repro: `PYTHONPATH=wt1/src python -c` with `make_cohort(n=60)`, `y_true` 3 ones, `score` 0.08, then print `doc["calibration"][k]["number"]["flags"]` |
| N2 | **The note says it refused a sentence that ships three times.** Its "Sentences refused" list has "No clustered cell of fewer than five cases can print an interval", with the scoped wording "written instead". The same sentence ships unscoped in three places: on the T7 page (`conventions_T7.md` line 255: "prints no interval on any route, the cluster bootstrap included"), in the schema (`notEstimableReason` description: "prints no interval on any route"), and in `number.py` ("on every clustered route"). Its counter-examples did run: the four `test_dec75c_*` inputs fail at `45e6761`. I could not break it (0 of 1,123 intervals below five cases; see below). So the sentence holds on everything tried. The record and the shipped text disagree; the note should either scope the text (the builders `clustered_number` is applied at) or drop the refusal. The handoff has the same kind of gap: it refuses "repair 3 closes lens 3", yet its carried table heads rows 1 and 2 "Closed by repair 3 (`6e19574`)". Those rows' "Why carried" cells still read "Round cap (3 lens rounds); needs a rule (need 51)" and "Round cap; refuse, adjust or annotate is need 50", both of which DEC-75 answered. | `grep -n "on any route" design/conventions_T7.md schema/output_schema_v1.json`; `grep -n "every clustered route" src/proofpack/stats/number.py`; the handoff's carried table rows 1-2 |
| N3 | **Two "Rule as shipped" cells in the handoff's decision table are false at `ba26d88`.** "Route ... below 5 cases the bootstrap with its tier": two to four cases are now refused. "The `ᵈ` mark ... every clustered proportion Number ... `bootstrap._with_clustered_coverage_mark`": the mark is now on every clustered interval, and that function was removed in `6e19574`. The DEC-75 row below them is right; the two earlier rows were not updated. Need 47 is still worded as a question, but the paragraph above the needs says DEC-75 answered it. | `git show ba26d88:handoffs/2026-10-02_E.md`, section "The decisions taken today"; `git grep _with_clustered_coverage_mark ba26d88 -- src` finds nothing |
| N4 | **The calibration `analytic_status` change is pinned by no test and missing from the DEC-43 list.** At `ba26d88`, `_clustered_cell` sets a refused calibration cell's status to `unavailable`; it was `refused_clustered`. On a 120-row run of four cases, all seven calibration cells read `('unavailable', 'fewer_than_five_cases')`. My mutant D (status always `refused_clustered`) survived `-m day11` (`144 passed`) and then `-m "day10 or day9 or day8 or day6 or day5 or ap4"` (`1410 passed`). This is a `run.json` value another lane could read. The note's summary and open question 4 name it, but neither "Changes another lane must know" list does. | `wt3`: `calibration.py:553` -> `status = "refused_clustered"`, then the two marker runs |
| N5 | **The paired AUROC difference's class-units tier is pinned by no test.** My mutant H drops `*auroc_precision_flags(n_cases, resampler.class_units.values())` from `comparison._paired_auroc_cell`, leaving `clustered_number` to add `precision_flags(n_cases)`. It survived `-m day11` (`144 passed`) and the five-marker run (`1410 passed`). It is not equivalent: `auroc_precision_flags(40, [3, 37])` is `['very_low_precision']` and `precision_flags(40)` is `[]`. A 40-case paired AUROC difference with three positive cases would then print `ᵈ` with no `ᵇ`. The walk test's tier rule (none needed at 30 cases or more) cannot see this. | `wt3`: `comparison.py:513` -> empty, then the two marker runs |
| N6 | **Lens 3's mutant L14 is now killed, so carried row 14 / E11r3-3 can drop L14.** L14 strips `ᵈ` from a decile bin when the curve flag is added. Re-planted at `ba26d88`, it fails `test_e11_repair3.py::test_dec75b_every_clustered_interval_carries_the_mark_and_its_case_count_tier[cmp10]` (`1 failed, 127 passed`). L4, L5 and L11 I did not re-run. | `wt3`: `calibration.py:827` (lens 3's `p10_mut.py` text), `-m day11 -x` |
| N7 | **Carried row E11r3-6 describes the refused cells' status inexactly.** It says `analytic_status` "stays `refused_clustered` on a proportion, AUROC, difference or comparison cell the rule refuses". The T2-3 paired Brier and slope differences say `used` whether or not they carry an interval. On F5 at four cases of 25 rows, `differences.brier` and `differences.slope` read `analytic_status used, method none, insufficient_clusters` (the bootstrap's own refusal, before the five-case rule). This was so before repair 3. | four-case compare (`_f5_clustered(..., [25] * 4)`), read `comparison.differences.brier` |
| N8 | **Masking: F17's mask is three keys; the T2 golden's is eleven.** F17 masks exactly `('run_id', 'started', 'duration_s')` (`scripts/f17_determinism.py:58`, printed by the run). The T2 golden's `MASKED_MANIFEST` (`tests/test_e10_t2.py:73-85`) replaces eleven manifest keys: those three plus `mapping_sha256`, `numpy`, `scipy`, `python`, `platform`, `reference_platform`, `input_sha256` and `prior_input_sha256`. It has been so since E10 and repair 3 does not touch it. Recorded because this lens's brief asks for "masking touches only run_id, started and duration_s", which is true of F17 only. | `sed -n 73,85p tests/test_e10_t2.py` |

## What I could not break (re-measured)

**Suite and lint at `ba26d88` (`wt1`).**

| Run | Git Bash | PowerShell 5.1 | Note |
|---|---|---|---|
| Full suite | `1998 passed, 1 skipped, 1 xfailed in 248.85s` | `1998 passed, 1 skipped, 1 xfailed in 252.08s` | the same counts. The skip is `test_doctor_cli.py:57` (`day1`); the xfail is F13 (`day3`) |
| Markers (`--collect-only`; none of them holds the skip or the xfail, and all passed inside the full run) | `day11` 144, `day10` 262, `day9` 337, `day8` 471, `ap4` 198, `ap3` 176, `ap2` 91 | the same seven | the same seven |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `294 files already formatted` | the same | the same |

**Fails pre-build.** `tests/test_e11_repair3.py`, copied into `wt0`: `19 failed, 1 passed in 5.02s`. The pass is `test_control_an_unclustered_compare_keeps_the_mcnemar_p_value`, as the note says. No failure was an import abort. The first `E` line of each matches the note's quotes, for example:
- `assert {'b': 10, 'c'...ant': 12, ...} == {'b': 10, 'c'...c': None, ...}`;
- `assert ['0.219 (exac....039 (exact)'] == ['n.e. (mcnem...ndent_pairs)']`;
- `assert 'mcnemarEntry' in {...}`;
- `assert ['newcombe_refused_clustered'] == ['newcombe_re..._established']`;
- `assert None == 5`;
- `assert (None, 4) == ('fewer_than_five_cases', 4)`;
- `AssertionError: 35 of its 36`.

The four `dec75b` parameters list 30, 10, 26 and 130 extra items, each with the first extra item the note quotes.

I also copied the seven changed test files into `wt0`: `10 failed, 149 passed`. Each changed assertion fails there, on the figure the note says the rule changed:
- the McNemar entry key;
- the clustered paired flags;
- the four `n.e.`;
- the four-case route;
- the Accept count;
- the T1 legend string;
- the a0c9abc bin;
- three `PAIRED_DIFF` sentences.

**Nothing weakened.**
- `git diff --name-status 45e6761 ba26d88`: 36 `M`, 1 `A` (`tests/test_e11_repair3.py`), 0 `D`.
- No skip, xfail or `only` was added. The only marker lines added are `pytestmark = pytest.mark.day11`, one `parametrize` and one `@pytest.mark.ap4`. No marker was removed.
- Five `assert` lines were removed (`git diff 45e6761 ba26d88 -- tests | grep "^-\s*assert"`), the five the note names. Each was replaced by the assertion of the new figure.
- One parameter was removed: the 2-4-case case of `test_every_clustered_route_that_prints_an_interval_carries_the_mark`. Its new behaviour is `test_dec75c_*`.
- The `test_bootstrap_carried.py` loosening is scoped. It asserts that the snapshot's bin had fewer than five cases, the bootstrap method and the same estimate, and that `refused == 1`.

**Statistical-gate hunks.** `git diff --name-status 45e6761 ba26d88 -- src/proofpack/stats/` lists `bootstrap.py`, `calibration.py`, `comparison.py`, `number.py` and `subgroups.py`. Every hunk is one of these:
- `clustered_number` and its constants;
- a call to it at a cell builder (`auroc_ci`, both `proportion_ci` routes, `_clustered_cell`, `_brier_cells`, `_proportion_difference`, `_auroc_difference`, `_brier_cell`, `_paired_proportion_cell`, `_paired_auroc_cell`, `_paired_calibration_cells`);
- `mcnemar_entry` and the `clustered` keyword;
- the tier at creation in the two paired cells;
- one reason and one flag comment in `number.py`;
- comment text.

Each hunk is named in the note's change list. No interval function, resampler, `design_effect` or constant value changed. The schema diff:
- adds `fewer_than_five_cases` and `$defs.mcnemarEntry`;
- replaces the two inline McNemar entry definitions with a `$ref` that adds the required `not_computed_reason` and lets `p` be `null` only in the refused branch;
- changes two descriptions.

The removal is the inline definition, replaced, and the note and handoff name the new required key. `egress_schema.json`: 0 diff lines. Ten clustered documents validate against `output_schema_v1.json` with 0 errors: nine walk shapes plus a four-case run. So does the four-case F5 compare.

**Goldens.** `PROOFPACK_REGEN_GOLDEN=1 -k golden`: `6 passed`. All five goldens (T1, T2, T7, T8, T12) have the same LF-normalised SHA-256 before and after, and `git diff --stat` was empty; I restored them with `git checkout`. The golden diff `45e6761..ba26d88` holds only:
- the `ᵈ` legend row's text (T1, T7);
- the T2 and T8 legend tables;
- six "paired rows" sentences (T2);
- the T12 register row.

**Every command in the note, both shells, at `ba26d88`.** The note marks most of the PowerShell column "not re-run"; I ran each there.

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| `doctor --offline` | exit 0, 17 `[ok`, `All essential checks passed.`, the note's `Next step:` line | the same |
| `fixtures --offline --out DIR` | exit 0, `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`; `unverified` 37 | the same |
| `capture_fixture_oracles.py --check` | `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`, exit 0 | the same |
| `tr39_subset.py <abs path> --check` | `vendored subset matches`, exit 0 | the same |
| `coverage_bar.py --deff-wilson --json OUT` | `identical True`, threshold 30, 107 s | `identical True`, threshold 30, 91 s |
| `build_sample_pack.py --out DIR --compare` | exit 0; `compare.json` 329,448, `run.json` 236,843, T1 143,196, T2 70,598, T7 48,264, T8 35,179; on T2 `SYNTHETIC - illustrative` 8, `NO LICENCE - not for submission` 7 | the same bytes and counts |
| `f17_determinism.py --n 400 --compare` | `run exit codes [4, 4]; identical under the mask ['run_id', 'started', 'duration_s']: yes`, exit 0 | the same |
| `test_e10_timing.py -s` | `compare --templates T2 25.86 s; T2 render from run.json 0.03 s; T2 74856 bytes`, 1 passed | `30.54 s`, `0.03 s`, `74856 bytes`, 1 passed |
| `mutation_sweep.py --marker day11` | `71 planted, 71 killed, 0 survived; 1222 s`, exit 0; all 15 `e11r3_*` `killed` | - |
| `mutation_sweep.py --marker day10` | - | `37 planted, 37 killed, 0 survived; 1486 s`, exit 0 |
| `git rev-list --count ad66073..6e19574` / `git diff --shortstat 45e6761 6e19574` / tokens | `14` / `36 files changed, 1005 insertions(+), 161 deletions(-)` / 0 lines | - |

The handoff's own figures also hold:
- `rev-list --count ad66073..3302d59` = 12;
- `--shortstat ad66073 3302d59` = 78 files, +40,537 / -294, of which 35,251 lines are `design/coverage_deff_wilson.json`;
- `origin/main` = `c779678`.

On the sample pack, `January 2025` count = literal-qualifier count on T1 63/63, T2 15/15, T7 7/7 and T8 15/15, and `Jan 2025` is 0, as lens 3 RG measured.

**The note's measured figures, re-run.**
- **The repairer's `e11r3/walk.py`**, at the tip and at the base. Its output equals the repairer's `walk_r3.txt` and `walk_base.txt` line for line, apart from the path line. Summed:
  - base: 96 / 26, 90 / 90, 67 / 30, 50 / 10;
  - tip: 96 / 0, 0 / 0, 64 / 0, 49 / 0.

  These are the note's figures.
- **The repairer's `mcnemar_t1.py`** (it imports numpy, scipy and the standard library only): 0.5380 / 0.2750 / 0.0365, the note's figures.
- **My own McNemar simulation** (`probe/mc_own.py`, no repository import, my own seeds, R 4000, the R2 section 6 rule written from the formula): 5 x 50 + 25 x 1 at p 0.9 **0.5495**; 30 x 10 at p 0.85 **0.2615**; 275 one-row cases **0.0362**. A true null is rejected far above the nominal 0.05 on both clustered shapes. That is DEC-75 (a)'s ground.
- **Lens 3's `p2_diff_cov.py`** at the tip, R 1000, B 500: identical, line for line, to the repairer's `p2_tip.txt` / `p2few_tip.txt`:
  - paired Se difference, 30 cases: 0.8849;
  - paired Se difference, 10 cases: 0.8850, 0.9208 (truth 0.9 - 0.8);
  - paired Se difference, 5 cases: 0.9635;
  - four cases of three rows: 0 printed (the probe's division by zero).

  The flag tuples the probe prints mix printed and unprinted cells. The tuples without the mark (`()`, `('very_low_precision',)`) come from the unprinted cells: the analytic Newcombe refusal returned before the bootstrap. My walker (below) is what checks printed cells.
- **Newcombe's 36th limit, with my own method 10** (Wilson limits; `phi` from the raw `eh - fg` when it is not positive): `(1, 97, 1, 1)` gives lower **0.873672**, upper 0.985026. The register row's 0.873672 matches, and the fixture's `excluded` entry is asserted by `test_dec75d_*`.

**The two blockers, on shapes the tests do not use.** My walker (`probe/walk.py`, my own code; it imports only the test helpers that build documents) checks every Number with an interval. It flags a Number that lacks `clustered_coverage_not_established`, has `n_cases` missing or below 5, has no tier at 5-29 cases, or has no `ᵃ` below 10.

| document | intervals | flagged | refused `fewer_than_five_cases` |
|---|---|---|---|
| compare, F5, 10 cases of 7 + 15 of 2 | 76 | 0 | 0 |
| compare, F5, one case of 6 + 94 one-row cases | 86 | 0 | 0 |
| compare, F5, 5 cases of 20 | 32 | 0 | 36 |
| compare, F5, 50 cases of 2 | 78 | 0 | 0 |
| compare, F5, 6 of 15 + 1 of 10 | 65 | 0 | 6 |
| run, 200 rows, 40 cases of 5 | 97 | 0 | 0 |
| run, 300 rows, 3 cases of 60 + 120 one-row | 97 | 0 | 0 |
| run, 100 rows, 5 cases of 20 | 84 | 0 | 9 |
| run, 300 rows, 6 cases of 50 | 97 | 0 | 0 |
| run, 300 rows, 150 two-row cases nested in sex/age/site, CRITERIA + FAIRNESS | 207 (6 under `/fairness`) | 0 | - |
| the same, 50 six-row cases | 204 (6 under `/fairness`) | 0 | - |

Every one of the five compares has McNemar `p null`, `method none` and the reason, on `mcnemar` and on both `mcnemar_by_metric` entries. The near-unclustered compare (94 one-row cases) is refused as well, as DEC-75 (a) words it.

On the pages:
- **T2.** On the five compares, every `[lo, hi]` table cell carries `ᵈ`: 0 cells without it of 50, 25, 46, 50 and 50. The legend table is present, and the three McNemar cells read `n.e. (mcnemar_assumes_independent_pairs)`.
- **T1.** The 11 bracket cells per document without `ᵈ` are the separate `data-facet="ci"` cells of Tables T1-7 and T1-18. The `est` cell beside each carries the mark, for example `84.2ᵃᵈ | [77.5, 90.4]`.
- **T8.** T8 prints marks only in the criteria table, and the legend follows it. A run with no criteria prints neither marks nor legend.
- **Fairness-and-criteria runs.** T1 HTML 247 / 245 `ᵈ` and T1 DOCX 190 / 190, each with the legend row; T8 HTML 5 and T8 DOCX 5, with the legend. `fairness:tpr_gap` is `met` on its own interval, which carries the mark.

**DEC-75 (c) through the criteria.** On a 120-row run of four cases of 30 rows, criterion `C1` (sensitivity `ci_lower_bound >= 0.8`) reads `not_assessable / no_interval`, `detail.not_estimable_reason fewer_than_five_cases`, as the note says.

On the four-case F5 compare:
- T1, T2 and T8 print no interval (`fewer_than_five_cases` 61 / 33 / 4 times);
- T1, T7 and T8 DOCX render (265,571 / 50,022 / 47,833 bytes);
- the document validates.

**Mutants.** The sweep's 15 `e11r3_*` were all killed (table above). Of mine, on repair-3 lines the sweep list does not cover (`probe/mut.py`, `-m day11 -x`, restored by `git checkout`; `git status` clean after), seven of nine were killed:

| id | mutant | outcome |
|---|---|---|
| A | `_mcnemar_by_metric(..., clustered=False)` | killed (`test_dec75a_no_mcnemar_p_value_...`) |
| B | subgroup AUROC difference without `clustered_number` | killed (`test_dec75b_...[run_nested]`) |
| C | subgroup Brier `if arrays.clustered:` -> `if False:` | killed (`test_dec75b_...[cmp10]`) |
| D | calibration status always `refused_clustered` | **survived** (N4) |
| E | `imprecise` kept on a refused Number | killed (`test_dec75c_four_cases_...`) |
| F | the T2-3 caption clause never printed | killed (`test_dec75a_t2_prints_...`) |
| G | the T1 IPA footnote filter dropped | killed (`test_the_t1_ipa_footnote_...`) |
| H | the paired AUROC class-units tier dropped | **survived** (N5) |
| K | `n_cases <= MIN_CLUSTERED_CASES` (five cases refused) | killed (`test_e11_deff_wilson.py::test_the_route_switches_at_five_cases_...`) |
| L14 (lens 3) | decile bin loses `ᵈ` with the curve flag | killed (N6) |

**Lens 3's could-not-break list, re-checked where repair 3 touched it.**
- The unclustered McNemar arithmetic: the control test passes, `p 0.03857421875`.
- The AI-DSF qualifier counts on the sample pack (above).
- Newcombe `matched 34`.
- The DEFF-Wilson coverage JSON, `identical True` in both shells.
- The ledger and item 0, through the full suite.
- The one-case cell: `insufficient_clusters` (`test_e11_repair2.py`, passing).

**DEC-43 coverage.** Both new reason codes are in the note's and the handoff's lists: `fewer_than_five_cases` and `mcnemar_assumes_independent_pairs`. So are these:
- the new required key `not_computed_reason`;
- every page string I found new in the golden diff and the templates: the T2 legend caption, the T2-3 caption clause, the legend row, T8's legend, the T1 footnote, the T7 descriptions and section 6, `PAIRED_DIFF`, and the T12 row.

The gap is N4. The site (read only, `ce04e93`) has no reference to `not_computed_reason`, `fewer_than_five_cases` or `clustered_coverage_not_established` outside its handoffs. Its `src/data/egress_schema.json` is unaffected (`egress_schema.json` is unchanged).

## What I could not check

- CI. Nothing is pushed, so neither the day loop nor the `docx-extra` job has run on `ba26d88`.
- Linux and macOS. Every figure here is win-amd64-cp314.
- Coverage of the families DEC-75 (b) marks without a coverage run: AUROC difference, Brier, IPA, slope difference. That is the fresh-attack lens's work.
- The clustered `detected` route. My F5 shape halted at H05: the shared case ids carry conflicting `y_true` under `clustering.unit: none`.
- Lens 3's mutants L4, L5 and L11. Not re-run; repair 3 does not touch their lines.
- Need 52 (the per-class five-case floor) is Josh's to answer.

## Sentences I refused to write

- "Repair 3 closes lens 3's blockers." Written instead: what reproduces and what does not, on the inputs named.
- "No clustered interval prints without `ᵈ`." Written instead: 0 of 1,123 on the eleven documents listed.
- "The regression tests pin every repair-3 rule." Mutants D and H survive.

Probes and raw outputs are in `scratchpad/lens-E11-r4-regression/`:
- `probe/`: `walk.py`, `pages.py`, `t1cells.py`, `fair.py`, `val.py`, `four.py`, `mc_own.py`, `mut.py`, `mut2.py`;
- outputs: `suite_bash.txt`, `suite_ps.txt`, `prebuild.txt`, `walk_r3_tip.txt`, `walk_r3_base.txt`, `mut_out.txt`, `sweep11.txt`, `sweep10_ps.txt`, `cov_bash.log`, `p2.txt`, `p2few.txt`.

All four worktrees were removed with `git worktree remove --force` at the end.
