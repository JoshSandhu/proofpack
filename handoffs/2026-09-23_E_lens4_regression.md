# Lens 4 (regression and record) - build day 8, lane E, repair 3 at `fe35332` - 2026-09-23

**Verdict: PASS.** No blockers. Each of the five lens-3 blockers (RG-B1, RG-B2 / FA-B1,
RG-B3, FA-B2, FA-B3) no longer reproduces on its literal inputs, and every figure in the
repair-3 note that I re-ran matched. The one figure whose baseline the note leaves unstated
is N4. Full suite: `1122 passed, 1 skipped, 1 xfailed`, in Git Bash and in PowerShell 5.1. Markers:
`day8` 334, `day7` 139, `day6` 285, `day5` 54, `day4` 182, `day3` 29 + 1 xfailed, `day2` 40,
`day1` 59 + 1 skipped. `--collect-only` gives 60 / 40 / 30 / 182 / 54 / 285 / 139, the
`7b2ca2a` counts. The day-8 sweep gives `79 planted, 79 killed, 0 survived; 914 s`, exit 0.
With the new and changed test files copied into `0f553c9`, the run gives
`22 failed, 154 passed`, and each first `E` line is an assertion.
Seven non-blocking items follow. N1 is a repair-3 sentence that is false on a `dev` row.
N2 is an open spelling class that the carried list does not name. N5 is two non-equivalent
mutants of mine that survive `-m day8`.

Worktrees under `scratchpad/lens-E8-r4-regression/`: `head` at `fe35332`, `base` at `0f553c9`,
`mut` at `fe35332` for my mutations. I forced `PYTHONPATH=<worktree>/src` and, before each figure,
checked that `python -c "import proofpack;print(proofpack.__file__)"` printed that
worktree's own `src\proofpack\__init__.py`. The probe scripts that follow import
`proofpack` and assert or print the path. All three worktrees are removed. In the main tree
I wrote only this note and committed nothing.

## Blockers

None.

## Non-blocking

**N1 - The repair-3 sentences about blank `y_pred` rows are false on a `dev` row (sentence
violation, the same class as lens-3 FA-N3).** README: "counted under
`flow.excluded_missing_score` when the row's `y_true` is present (a row whose `y_true` is also
blank counts under `flow.excluded_missing_label` ...)". `schema_v1.json` `y_pred` and
`output_schema_v1.json` `excluded_missing_score` say the same, and so does the `analysis_mask`
docstring: "A row whose `y_true` is present and whose prediction input is missing counts under
`excluded_missing_score`". The code is `excl_sc = ~dev & ~yt_missing & sc_missing`. So a `dev`
row counts under `dev_rows` whatever its `y_true` and `y_pred`. Counter-example, measured at
`fe35332`: 120 rows, no score column, `dataset` = `dev` on rows 0-19, `y_pred` blank on rows
0, 10, ..., 110, `y_true` blank on rows 0, 20, ..., 100. Result:
`{rows_read 120, dev_rows 20, excluded_missing_label 5, excluded_missing_score 5,
indeterminate 0, analysed 90}`. Row 10 (`y_true` present, `y_pred` blank) and row 0 (both
blank) are counted under `dev_rows`. The note records no run with a `dataset` column.
Repro (from `tests/`): the table above through `assemble(cols, make_criteria(criteria=[], fairness=None))["flow"]`.

**N2 - `well-calibrated` with a separator other than a hyphen *and* letters attached is
accepted, and the carried list does not name this.** At `fe35332` these give `None` inside "The model was {} here.":
`well calibratedness`, `well.calibratedly`, `well_calibrateds`, `well/calibratedness`.
`wellcalibratedness` and `well–calibratedness` (en dash) are rejected. The same four are
accepted at `0f553c9`. They would also pass `657ef11`'s substring rule, which reads
`well-calibrated` with a hyphen only. So this is not a regression, and RG-B1 is closed on
its class. The repair's rule is scoped to "a reading that contains `wellcalibrated` once its
hyphens are removed", and that sentence is accurate. `_words` joins tokens across any
separator for an exact match only, so `well calibrated` alone is rejected, while `well` +
`calibratedness` joins to `wellcalibratedness`, which is not in the word set. Carried item 2
names "look-alike spellings" only. No engine claim carries `free_text`, so nothing reaches a
page today. Lenses 1 and 2 graded accepted spellings of a listed word as blockers. I grade
this one non-blocking because every commit since `657ef11` accepted it and the gate's scope
is Josh's open decision. If the orchestrator applies the earlier grading, this is a blocker.
Repro: `python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('well calibratedness'))"` prints `None`.

**N3 - Rule 8b accepts a subset of a family template's pointers, and the carried list does not name this.**
`CL-0060` (`CALIB_HIERARCHY`, `refs (4, 6)`) with `value_refs` = its last five pointers
(`slope`, `intercept`, `brier`, `brier_ref`, `ipa`; `oe` omitted) is accepted. So is
`FLOW_COUNTS` over `/flow/n_sites` alone. The rule-8b docstring discloses this ("a subset of a
family's pointers leaves the other slots without a pointer"), and so does the note's refused
sentence "Rule 8b fixes slot filling". Carried items 1-6 do not list it. E9 must fill slots
by pointer facet, not by position, or `{oe}` would take the slope. `FAIRNESS_GAP` is
`refs (4, 4)`, and its subsets give `value_refs_count`.

**N4 - The note's "newly rejected: 0" does not name its baseline.** I re-ran lens 3's
`probe/fz.py` in `head`. It gives 18,752 texts, and the result is equal to the repairer's
`fz_fix.json`. Rejected at `657ef11` and accepted now: 0. Rejected at `7fa690b` and accepted
now: 0. Code changed from `7fa690b`: 0. Newly rejected against `7fa690b` alone: **180**, the
RG-B1 spellings, which is the fix. Accepted at both earlier commits and rejected now: 0,
which is the note's 0.

**N5 - My own mutants (`probe/my_mutants.py`, `-m day8`, `mut` worktree, tree clean after).**
One of the seven was killed and six survived:
- `second_earlier_reading_dropped` (`_READING_MAPS` keeps `_CONFUSABLES_R1` only):
  **non-equivalent**. `ᴘassɑ` and `ᴄonsistentɑ` are rejected at `0f553c9` (7fa690b's rule,
  checker diff empty) and at `fe35332`, and accepted with the mutant, while
  `334 passed`. Only the 7fa690b reading rejects these two spellings, and no test feeds
  either. The sweep's `checker_earlier_readings_dropped` drops both readings and is killed
  through the first. The RG-B1 kind of loss (a repair silently dropping an earlier
  rejection) can therefore reopen through the second reading with every test green. Fix:
  add `ᴘassɑ` to the literal list in
  `test_every_spelling_rejected_at_657ef11_or_7fa690b_is_still_rejected`.
- `rn_first_only` (`full.replace("rn", "m", 1)`): **non-equivalent**. `turn rneets` is
  rejected at `fe35332`, accepted at `0f553c9`, and accepted with the mutant, while
  `334 passed`. The test feeds `rneets` alone.
- `reserved_gate_case_sensitive_to_lower` (the gate compares `i.lower()`): survives. It makes
  `Threshold_Free` halt. No test feeds a case-variant id that must still run, and I measured
  that such ids run correctly (see below).
- `attainability_is_none_only` and `calib_na_not_none`: equivalent on engine documents,
  because `attainable_at_n` is a bool or `None` and `calibration` is a dict or `None`.
- `subgroup_estimate_takes_diff_shape` (`SUBGROUP_ESTIMATE` shapes `{2, 3, 4}`): equivalent
  on my probe. A `SUBGROUP_ESTIMATE` over `/subgroups/0/diff_vs_reference/op1/sensitivity/number`
  is `value_ref_unbound` at `0f553c9` too.
- `first_earlier_reading_dropped`: killed (`1 failed`).

**N6 - Three new tests pass at `0f553c9`, and each docstring says so.**
`test_a_format_character_inside_an_unlisted_word_is_dropped_not_a_boundary` is the pin for the
restored mutant, and the sweep kills `checker_format_characters_kept`.
`test_the_ids_the_lens_ran_clean_still_run` is a guard, and
`test_a_blank_y_pred_on_a_blank_label_row_counts_under_missing_label` is a record. None of the
three shows a behaviour change. The first earns its place through the sweep.

**N7 - Records.**
- `_readings` names lens FA-B2, but no D1 section 4.4 line and no oracle (the lens-3 N4 class).
- H08 now also covers a reserved operating-point id. The D1 section 5 / `errors.py` H08 text reads
  "mandatory declaration missing or criterion lacking author/date/justification". The CLI
  prints the specific message, and the non-unique-id check is the existing precedent.
- The golden's mask is `manifest.numpy` only (lens-3 N7, carried in the note's item 5).
  `run_id`, `started` and `duration_s` are assembler constants, not masks.
- `run.json` size on the E7 block depends on the digits of `duration_s`: 253,942 bytes
  (`0.92`) and 253,943 (`1.018`, and the repairer's `0.766`). Walking the whole document,
  mine and the repairer's differ only in `run_id`, `started` and `duration_s`.
- The worktree `scratchpad/repair-E8-r2/base` (`657ef11`) is still registered from repair 2.
  It is not repair 3's; orchestrator housekeeping.

## What I could not break

- **FA-B3, the reserved-id gate (DEC-12(i)).** I fed 27 ids through `validate_dict`, then
  `assemble` on 200 rows, `build_claims` and `check`. `threshold_free`, `auroc` and `brier`
  each give H08 with `{field: operating_points, reserved: [id]}`. `Threshold_Free`,
  `THRESHOLD_FREE`, `AUROC`, `Brier`, `threshold_free ` (trailing space), ` auroc`,
  `threshold-free`, `thresholdfree`, `threshold\u200bfree`, Cyrillic `аuroc`, `prevalence`,
  `roc`, `two_by_two`, `0`, `tpr_gap`, `auroc_gap`, `calibration`, `metrics`, `sensitivity`
  and `op1` each run with their own `overall` key beside `threshold_free`. Each keeps its
  sensitivity and its subgroup op block, and each gives 60 claims with 0 rejected. `a/b`,
  `op~1`, `threshold_free/auroc` and `~0` each give 58 of 60 rejected
  `operating_point_mismatch`, which is lens-3 FA non-blocking 5, carried. The engine keys
  every op-keyed dict by the exact string: `overall`, subgroup `metrics`, the difference
  blocks, fairness `operating_points` and `_attribute_block`. `grep` finds no `lower()` or
  `casefold` on an op id, and `validate_dict` is the only constructor of `Declarations`.
  Same data, different id: the `overall` op block, `threshold_free` and all nine subgroup
  rows under `Threshold_Free`, `AUROC` and `two_by_two` are byte-equal (JSON, sorted keys) to
  `op1`'s. I re-derived the `Threshold_Free` block with my own numpy count and statsmodels
  `proportion_confint(method="wilson")`. Two-by-two `{tp 57, fn 12, fp 35, tn 96}` is equal.
  Sensitivity 57/69, specificity 96/131, PPV 57/92 and NPV 96/108 deviate by at most
  `1.11e-16`. A criterion on `Threshold_Free` or `AUROC` gives `met`, 61 claims and 0
  rejected. A criterion naming `threshold_free`, `auroc` or `Op1` while the op is `op1` gives
  H09. At `0f553c9`: `threshold_free` leaves `overall` holding only the threshold-free block,
  with 47 claims and 45 rejected; `auroc` and `brier` each give 15 claims and lose the
  subgroup op block, which confirms the note's 15. Plain CLI with op `brier` on the E7 fixture:
  `HALT H08 ... reserved: ["brier"]`, "No document was written.", exit 3, no directory, in
  Git Bash and PowerShell. `git diff 0f553c9 fe35332 -- src/proofpack/stats src/proofpack/run.py
  src/proofpack/cli.py src/proofpack/criteria.py` is empty.
- **RG-B1 and FA-B2, differential fuzz.** Generator `probe/fz4.py`: the 48 listed words plus
  `well-calibrated`, `guidance` and `cfr`; single-letter substitutions drawn from 10 Unicode
  letter blocks (Latin-1 to Latin Extended, IPA, Greek, Cyrillic, Armenian, Cherokee,
  phonetic extensions, Latin Extended-C/D, Cherokee supplement), with a seeded 8% sample;
  13 affixes; `rn` for `m`, `I` for `l`, upper case. That is 107,776 texts, each bare and in
  a sentence. Rejected at `0f553c9` and accepted at `fe35332`: **0**. Code changed: 0.
  Newly rejected: 400. Lens 3's `fz.py` (18,752): see N4, 0 lost against either earlier commit.
- **RG-B2 / FA-B1.** Lens 2's `b_checker.py`, unchanged, against `head`: the output is
  byte-equal to the repairer's `b_checker_fix.txt` after the path line.
  `mutations: 8988 accepted: 11`, broken down as CALIB_HIERARCHY `metric_id` 4, FAIRNESS_GAP
  `metric_id` 3, and CRITERION_STATUS `template_id` 4 (`CL-0062`->ATTAINABILITY_NOTE,
  `CL-0063`->both, `CL-0070`->CRITERION_NOT_MET_RECORD). `C_n30` and `fairness:tpr_gap` are
  `not_met`, and `ATTAINABILITY_NOTE` prints either phrase. B5: `swaps: 42849 accepted: 0`.
  Lens 3's `b2_checker.py`: 4 accepted, namely `‮ssap`, `unsafe`, `ssɐd` and
  CRITERION_STATUS->ATTAINABILITY_NOTE, exactly the note's list. I ran engine claims through
  the checker on six documents: synthetic 70, two operating points 130, clustered 60,
  y_pred-only 60, 60 rows at 10% prevalence 60, and 400 rows 60. Each has 0 rejected at both
  `0f553c9` and `fe35332`, so rule 8b refuses none of the engine's own claims on these six.
  Rule-8b edge cases: a duplicated gap pointer gives `value_ref_duplicate`; gap subsets and
  calibration pointer counts of 1-3 give `value_refs_count`; `SITE_COUNT` over
  `/flow/n_cases` gives `value_ref_unbound`.
- **RG-B3.** `checker_format_characters_kept` is in the day-8 list and killed. The
  "became equivalent" sentence is gone from `scripts/mutation_sweep.py`.
- **The sweep.** `--list` gives 250 lines in both shells: 34 day5, 112 day6, 25 day7,
  63 day8, 16 ap2, with no duplicate id. The 22 repair-3 mutants are each `killed`, and
  `--marker day8` gives `79 planted, 79 killed, 0 survived; 914 s`, exit 0. The `head` tree
  was clean after.
- **Fails pre-build.** The 14 changed test paths (11 A, 3 M) were copied into `base` and run
  with `test_e8_repair3.py`, `test_claims.py` and `test_e8_repair2.py`:
  `22 failed, 154 passed in 6.25s`, the note's figure. The first `E` lines are
  `assert [...] == []` with `720 more items`, the sweep-listing set assertion,
  `AssertionError: 'p\u0251ss'`, `('CRITERION_NOT_MET_RECORD', ['/overall/op1/sensitivity'])`,
  `[('CL-0001', ...TIMATE'), ...] == [('C_met', ...`, `Failed: DID NOT RAISE HaltError` (x3),
  the refused-sentence assertion, and corpus `131`-`140` accepted. They equal the note's
  quotes, and none is an import or attribute abort.
- **Nothing weakened.** `git diff --name-status 0f553c9 fe35332 -- tests/` gives 11 `A` and
  3 `M`, with no `D`. Grepping the diff for skip / xfail / `.only` / todo / `pytest.mark`
  finds only `pytestmark = pytest.mark.day8` and one `parametrize`. The two changed
  expectations are the counts 44 / 140 and the N6 claim, each with a comment. The old
  `test_run_cli.py` from `7b2ca2a` against `fe35332` gives `4 failed, 19 passed`, including
  the clustered test, as lens 3 N9 measured.
- **The corpus.** There are 140 files, all `.json`. Each has a `rule` and an
  `expected_reason_code` that is in `REASON_CODES` (44 codes).
  `CORPUS_FILES = sorted(CORPUS.glob("*.json"))`, and the parametrised test collects
  `140/155`.
- **Suite in both shells**, as in the verdict. `ruff check` gives `All checks passed!` and
  `ruff format --check` gives `153 files already formatted`, in both shells. `ap2`: 88
  passed. `day8` is declared at `pyproject.toml` line 82. `ci.yml` reads the marker list and
  runs `uv sync --all-groups --locked` (lines 25, 84). `uv.lock` has `name = "jinja2"`
  (line 497), and `python -m uv lock --check --offline` gives `Resolved 63 packages`, rc 0.
- **The note's commands.** `python -m proofpack.cli doctor --offline`: 17 `[ok` lines,
  `All essential checks passed.` and exit 0 in both shells (`python -m proofpack` has no
  `__main__`, lens-3 N8). E7 block, no licence, e2e fixture: `analysed 400 of 400 rows;
  criteria rows: 2 met, 2 not met, 5 not assessable`, exit 4, JSON only, 20 keys, 70
  claims, 0 rejections, 3 guidance refs, `declaration_index [0, 1, 2, 2, 2, 3, 4, 5, None]`,
  no CRLF and no BOM, in both shells. Without the mapping file: H07, exit 3, no directory.
  `licence show` and `licence verify <absent>` exit 4. `net_and_imports.py`: `--offline` and
  no flag each exit 4 with 0 socket calls, in both shells. `hidden.py`: 13 modules hidden,
  11 import, none loaded, and `environment()` raises `RendererUnavailable`, in both shells.
  `html_run.py`: exit 0, four files, `T8.html bytes 40145 CRLF False BOM False`, in both
  shells. `repros.py`: the threshold_free line raises the H08 above.
- **tokens.json against D5 section 3.1.** My parser reads the nine table rows: 19 names,
  19 hex values, 0 differ. My WCAG recomputation equals every `contrast_computed`. The file
  is unchanged since `a2246c1`.
- **The wheel.** `python -m uv build --wheel` holds the three templates and all seven
  `_schema` files, including `tokens.json`. I installed it into `python -m venv
  --without-pip`. Its `Lib/site-packages` holds `bin`, `proofpack` and
  `proofpack-0.1.0.dev1.dist-info`, with 0 `.pth` files in the venv. With `PYTHONPATH` unset
  and `PYTHONNOUSERSITE=1`, `proofpack.__file__` and `resource_path("tokens.json")` both
  resolve inside the venv, and `site.ENABLE_USER_SITE False`. The committed test passes
  (`1 passed`). I then removed `"design/tokens.json" = "proofpack/_schema/tokens.json"`
  from `pyproject.toml` in `mut`: the test fails with
  `FileNotFoundError(f"packaged resource {name!r} not found")`.
- **The golden.** Rendered in `head` with `numpy` masked: 39,800 bytes, equal to the committed
  LF bytes. Unmasked, the render differs from the golden in one line (`x.y.z` against `2.5.1`).
- **The footer removed** (line 7 `<footer ...>` of `base.html` emptied in `mut`): `4 failed`,
  on `assert 0 == 3`, `assert 0 == 1`, `assert 0 == 2` and `assert (0 == 3)`.
- **The draft label removed** (`label_for` returns `document` for a draft row):
  `test_every_fda_aidsf_anchor_carries_the_draft_label_in_data_and_on_the_page` fails with
  `assert ('draft guidance (January 2025), not for implementation' in 'FDA draft guidance, ...`.
- **DEC-60.** In shipped text, `TR39` appears twice, both in the `checker.py` comment, and
  that comment marks the coverage "[unverified]". The commit message has "TR39 data not
  fetched: [unverified]". The note marks the TR39 coverage [unverified] where it states it
  (lines 13, 69 and 81). Its heading and its description of the decision (lines 8-9) name
  TR39 without stating any coverage.
- **The S4 list.** `cli.py`, `run.py`, `errors.py` and `criteria.py` are unchanged since
  `0f553c9`. The schema changes are the three the note lists: the `template_mismatch` enum
  entry, the `excluded_missing_score` description and the `y_pred` description. The new
  H08 is named with its detail. I found no omission.

## What I could not check

- The sweep in PowerShell: I ran it in Git Bash, the shell the note used. `--list` ran in both.
- CI on ubuntu / Python 3.12: the engine is not pushed.
- A real-licence plain-CLI HTML run: there is no signing key on this machine. The HTML path
  ran through `main(..., registry=ephemeral_registry())`.
- TR39 coverage of the nine letters and `rn`: not fetched (DEC-60), [unverified], as the note says.
- Whether the `free_text` gate should cover N2's separator-plus-suffix spellings: that is
  Josh's scope decision, the same as for the look-alikes.

## Sentences I refused to write

- "Rule 8b binds every template to its pointers." Written instead: 3,850 relabels with 4
  accepted, 8,988 mutations with 11 accepted, and the subset in N3.
- "The reserved-id gate cannot be bypassed." Written instead: the 27 ids fed and what each gave.
- "free_text keeps every rejection an earlier commit made." Written instead: 0 lost on
  107,776 and 18,752 generated texts, and N5, where `ᴘassɑ` is lost under a mutant with every
  test green.
- "The blank-y_pred sentences are now correct." Refused: N1.

## Re-run these

```bash
S=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/a743e7e5-3be8-4d70-9ed0-681f5784a106/scratchpad
L=$S/lens-E8-r4-regression
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/head fe35332
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/base 0f553c9
cd $L/head && PYTHONPATH=$L/head/src python -c "import proofpack;print(proofpack.__file__)"
PYTHONPATH=$L/head/src python -m pytest -q -p no:cacheprovider              # 1122 passed, 1 skipped, 1 xfailed
PYTHONPATH=$L/head/src python -m pytest -q -p no:cacheprovider -m day8      # 334 passed
PYTHONPATH=$L/head/src python scripts/mutation_sweep.py --marker day8       # 79 planted, 79 killed, 0 survived
LENS_WT=$L/head PYTHONPATH=$L/head/src PYTHONIOENCODING=utf-8 python $L/probe/opid.py      # FA-B3: 3 H08, 24 run
LENS_WT=$L/head PYTHONPATH=$L/head/src python $L/probe/fz4.py $L/probe/fz4_head.json       # then the same in base; 0 lost
LENS_WT=$L/mut python $L/probe/my_mutants.py second_earlier_reading_dropped   # N5: SURVIVED, 334 passed (needs the mut worktree)
# N2: prints None
PYTHONPATH=$L/head/src python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('well calibratedness'))"
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $L/head
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $L/base
```

## What the next repair (or E9) needs

N1: scope the four sentences to non-`dev` rows, or name `dev_rows`. N5: add `ᴘassɑ` and
`turn rneets` to the repair-3 literal tests, so that the 7fa690b reading and the all-`rn`
replacement are each pinned. N2 and N3 go to the E9 note as open items: the gate's scope is
Josh's decision, and E9's sentence renderer must fill slots by pointer facet.
