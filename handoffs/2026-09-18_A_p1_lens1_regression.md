# Lens 1 (regression and record) - A-P1 the full mapper, branch `a-p1-mapper` at `555a5e1`

**Verdict: PASS - no blocker.** Every figure in the build note re-measured to the same value in both shells; lane E's files are untouched; nothing weakened in `tests/`. Seven non-blocking findings below, three of them decisions Josh has to make (two already in the note's needs-from-Josh).

Worktrees: `scratchpad/lens-a-p1-r1-regression/wt` (detached at `555a5e111afdfc245f7a5bfb8111d03bd854e478`) and `.../base` (detached at `4eb44f3`), both removed at the end. The main tree (`b93e050`, lane E) was not touched; `git status` on it showed only lane E's untracked `handoffs/2026-09-18_E_lens1_regression.md`.

`PYTHONPATH` proof, run before any suite in each shell:

| shell | `python -c "import proofpack;print(proofpack.__file__)"` |
|---|---|
| Git Bash, wt | `...\scratchpad\lens-a-p1-r1-regression\wt\src\proofpack\__init__.py` |
| PowerShell 5.1, wt | same path |
| Git Bash, base | `...\lens-a-p1-r1-regression\base\src\proofpack\__init__.py` |

## Blockers

None.

## Measured against the note (both shells, `PYTHONPATH` forced to the worktree's `src`)

| command | note says | Git Bash (measured) | PowerShell 5.1 (measured) |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | 460 passed, 1 skipped, 1 xfailed | `460 passed, 1 skipped, 1 xfailed in 45.02s` | `460 passed, 1 skipped, 1 xfailed in 42.13s` |
| `... -m day6` | 96 passed, 366 deselected | `96 passed, 366 deselected in 2.39s` | `96 passed, 366 deselected in 1.89s` |
| `python -m ruff check .` | All checks passed! | same | same |
| `python -m ruff format --check .` | 58 files already formatted | `58 files already formatted` | same |
| `python -m proofpack.cli doctor --offline` | All essential checks passed. | same, exit 0 | same, exit 0 |
| `python scripts/mutation_sweep.py --marker day6` | 17 planted, 17 killed, 0 survived | `17 planted, 17 killed, 0 survived; 31 s` | `17 planted, 17 killed, 0 survived; 30 s` |
| `... --marker day5 --only ref_largest_to_smallest` | not run in Bash / 1-1-0 in PS | `1 planted, 1 killed, 0 survived; 12 s` | `1 planted, 1 killed, 0 survived; 10 s` |
| `proofpack map --input tests/fixtures/mapping/sepsis_2019.csv --out ../m.json` (`PYTHONUTF8=1`) | exit 3; the 24-line table | exit 3; 27 lines (3 stderr + 24 table); no `mapping.json` written | exit 3; the captured bytes are identical to Git Bash's (3314 bytes, 27 CRLF lines each; `cmd /c ... > file 2>&1` used so no BOM) |
| baseline at `4eb44f3` (base worktree) | 364 passed, 1 skipped, 1 xfailed | `364 passed, 1 skipped, 1 xfailed in 45.70s`; `55 files already formatted` | not repeated |

The note's 24-line map table compared equal, character for character, to the measured Git Bash output (Python string compare after CRLF normalisation). The skip is `tests/test_doctor_cli.py:57` (write access), the xfail is `test_f13_matches_proc_on_the_asah_dataset` - the day-5 pair, as the note says. `--list` on the sweep: 34 `day5` mutants, 17 `day6`; the day-5 list is intact.

## Diff checks

- `git diff --name-status 4eb44f3 555a5e1 -- src/proofpack/stats schema/output_schema_v1.json pyproject.toml` -> empty. Lane E's files untouched; the `day6` marker was already in `pyproject.toml` line 69.
- `git diff --name-status 4eb44f3 555a5e1 -- tests/` -> 71 `A` lines (35 CSV + 35 expected.json + 1 criteria.yaml under `tests/fixtures/mapping/`, and `tests/test_mapping_full.py`), no `M`, no `D`. Grep of the added test lines for `skip`, `xfail`, `.only`: none; the only `pytest.mark` additions are `parametrize` and `pytestmark = pytest.mark.day6`. No marker removed anywhere in the diff.
- Files touched outside tests: `README.md`, `scripts/make_mapping_fixtures.py` (new), `scripts/mutation_sweep.py`, `src/proofpack/{cli,errors,gates}.py`, `src/proofpack/io/{declare,mapping}.py`, `src/proofpack/io/profile.py` (new). `cli.py` changes are the `map` subparser, `cmd_map` and the two new helpers, as the note says.
- All 50 test ids named in the note exist in `tests/test_mapping_full.py`, and every function in the file is named in the note (50 = 50; 96 collected with parametrisation).

## New tests against `4eb44f3` (pre-build)

Copied `tests/test_mapping_full.py` and `tests/fixtures/mapping/` into the base worktree. As committed, the module aborts at collection (`ImportError: cannot import name '_confirm_interactive' from 'proofpack.cli'`), which says nothing per test. So I shimmed the import block in the base copy only (each missing name - `_confirm_interactive`, `MAPPING_CODES`, `BINARY_LABEL_SETS`, `normalise_header`, all of `io.profile` - bound to an object that raises on use) and ran it: **88 failed, 4 passed**. The four that pass pre-build:

1. `test_register_has_at_least_thirty_fixtures_with_expectations` - inspects the copied fixture files only.
2. `test_single_column_clustering_units_are_not_e01` - a negative test (tolerates H08, asserts not-E01; E01 did not exist pre-build).
3. `test_yes_without_a_prior_mapping_halts_h07` - day-1 behaviour.
4. `test_yes_with_matching_prior_holding_a_medium_role_halts_h07` - day-1 behaviour (`tests/test_halt_gates.py::test_h07_rejects_yes_when_a_role_is_medium` already covers it).

These four guard existing behaviour under the `day6` marker; they pin nothing new. Not a blocker: no rule in the brief lacks a pinning test because of them (the 88 that fail include every item-1..7 test in the note's table).

## Fixtures: ten spot-checked by hand against D1 section 5.2 and the note's decisions

`SYNONYMS` in `mapping.py` carries every D1 row (`label, truth, gt, ground_truth, outcome, target, reference, y`; `prob, probability, p1, pred_prob, confidence, output, risk`; `prediction, predicted, pred_label, class`; `gender`; `centre, center, hospital, institution, facility`; `scanner, manufacturer, vendor, model_name`; `patient_id, subject_id, study_id, mrn_hash`; the canonical names) plus the five dataset rows the note declares (D3). Values behind each check were read from the CSVs.

| fixture | expected (checked) | rule |
|---|---|---|
| `diabetes_130` | `readmitted` y_true high (values NO/>30/<30, 3 unique); `pred_prob` score high; `hospital` site high; `age` age_band high (`[50-60)`...); `gender` sex high (Female 29 / Male 21); `encounter_id` row_id medium (50 unique ints); `patient_nbr` case_id low (partial token, 24 unique); `time_in_hospital` event_date low (header `^time_`, ints 1-14) | D1 synonyms + D3 row + D7 table |
| `sepsis_2019` | `Gender` sex medium, note `no dictionary declared for 0/1` (0: 28, 1: 22); `patient` case_id low (10 unique strings, partial) | D5 |
| `sepsis_2019_gender_mf` / `sepsis_200_columns` | `Gender` sex high (M 29 / F 21 in the 200-column file) | consistent M/F |
| `sepsis_british` / `sepsis_american` | `Sex` -> sex high, `centre` / `center` -> site high | D1 synonyms |
| `sepsis_pt_prefix` | `pt_Age` age high, `pt_Gender` sex high, `pt_SepsisLabel` y_true high | affix `pt_` (D7) |
| `sepsis_v2_suffix` | `SepsisLabel_v2` y_true high, `PredictedProbability_v2` score high | affix `_v<digits>` |
| `sepsis_two_labels` | `SepsisLabel` and `outcome` both y_true low | two claims on one role -> low (D7) |
| `sepsis_label_holds_scores` / `sepsis_score_holds_01` | `SepsisLabel` y_true low (46 unique floats); `PredictedProbability` score low (values 0: 37, 1: 13) | conflict -> low (D7) |
| `sepsis_zero_rows` | canonical `Age` high; synonym-only `Gender`, `SepsisLabel`, ... medium; `patient` low | header-only confidences (D7, day-1) |
| `mimic_iv_demo` | `subject_id` case_id high; `hadm_id` row_id medium; `anchor_age` age medium (partial, ints); `admittime` and `dischtime` both event_date low | two holders of event_date -> low (D7, D9) |
| `sepsis_two_case_ids` (`patient_id` + `subject_id`) and `mimic_composite_key` (`clustering.unit: [subject_id, hadm_id]`) | E01, message ends `reduce your case key to one column` | D6 / DEC-11 |

`python scripts/make_mapping_fixtures.py` re-run in the worktree wrote 35 files whose content matched the committed ones exactly (`git diff --ignore-cr-at-eol` empty); the only difference was LF vs the CRLF checkout (see non-blocking 7). The script does not import `map_headers`; the expectations are authored, as the note says.

## Acceptance (brief: Sepsis and Diabetes-130 headers map `high` on label/score/site/age/sex)

Executed via `test_acceptance_sepsis_and_diabetes_map_high_on_the_five_named_columns` and by hand: Diabetes-130 - five of five high; Sepsis with M/F - five of five high; Sepsis with PhysioNet's 0/1 Gender - four of five, `Gender` medium. **Not met as written on the real coding**, exactly as the note's D5 says. I do not count it a blocker: the same brief lists "sex 1/2 with no dictionary" as a hostile input that must halt or map correctly, 0/1 carries the same ambiguity, and mapping it high would apply a dictionary the customer has not declared (a declaration inferred). Josh's ruling (needs-from-Josh 1) closes it either way.

## Non-blocking

1. **Four new tests pass pre-build** (list above). Repro: copy the file and fixtures into a `4eb44f3` worktree, shim the four missing imports, run `pytest tests/test_mapping_full.py` -> `88 failed, 4 passed`.
2. **The DEC-11 separator list misses space and slash.** `clustering.unit: "subject_id hadm_id"` and `"subject_id/hadm_id"` reach the schema and halt `H08: declaration invalid at clustering/unit: enum` (exit 3, no traceback, measured through `proofpack map --criteria`), not E01 with DEC-11's sentence. `,` `+` `&` `;` `|` and ` and ` all gave E01. The README line "E01 ... when `criteria.yaml`'s `clustering.unit` names two or more columns" and the `_check_dec11_case_key` docstring generalise past this counter-example (sentence rule, see below). The schema's enum is `none | case_id`, so a one-column string such as `subject_id` is also H08.
3. **Numeric `min`/`max` in the printed table and in `mapping.json` are single-row values.** Measured line: `'Age' -> age high float; 50 unique; ... min 20.04 max 84.65` - with 50 unique values each is one patient's age to two decimals; likewise `HospAdmTime min -198.06 max -0.97`. D1 section 5 step 1 lists min/max, so this is the spec as written, and the note raises it as open question 3; but the task's rule ("no row-level value may appear in ... a printed table ... unless it is one of the top-20 aggregated values") and `profile.py`'s first sentence ("Suppression is applied before anything is displayed or written") are both contradicted by it. Dates are coarsened to month; numbers are not. Josh's call (band numeric min/max the way dates are, or accept D1 verbatim).
4. **`--yes` can never be satisfied on a header set with any non-high role, even after a human has confirmed it.** `_confirm_interactive` appends `accepted interactively` to `notes` but leaves `confidence` as computed, and `check_h07(non_interactive=True)` requires every role high in the prior file and in the fresh mapping. `sepsis_2019_gender_mf` has `patient` at low, so `proofpack map --yes` halts H07 on it regardless of any prior file (measured: `non-interactive mode requires an existing mapping.json` with no prior; with an all-high forged prior the fresh-mapping check refuses, per `test_yes_is_refused_when_the_fresh_mapping_has_a_medium_even_if_the_file_says_high`). This is D1 step 3 verbatim, so not a defect of the build, but CI mode is unreachable for any PhysioNet-shaped table. Pairs with the note's open question 2 (`run` without `--yes` proceeds on the computed mapping - confirmed: `cmd_run` calls `ingest(non_interactive=args.yes)` and `check_h07` returns `fresh` when not non-interactive).
5. **`mapping.json` shape deviates from D1 step 5's key list**: no separate `confidences` key (confidence sits inside each `roles` entry, with `source` and `notes`), and `decided_by` has a third value `proposed`. Documented in README and open question 4. Worth settling before E7 hashes the file into the manifest, since any later reshaping changes every manifest hash.
6. **The `[unverified]` in `_stdin_is_terminal`'s docstring and note D10 can now be closed.** Measured this session: `Start-Process python -c "..."` (a fresh console window, minimised) wrote `isatty=True terminal=True`, so `GetConsoleMode` returned non-zero for a real console handle; with `stdin=DEVNULL` the test measures 0.28 s to exit 3 (note: 0.29 s). Not measured: mintty (Git Bash's own terminal), where Python's stdin is a pipe and `isatty()` is False - a human at a mintty prompt would get the H07 "stdin is not a terminal" halt. Josh's shell is PowerShell, so this is a note for the README, not a defect.
7. **Line endings**: the generator writes LF, the checkout is CRLF. Running `make_mapping_fixtures.py` in a checkout marks all 35 CSVs modified with no content change (`git diff --ignore-cr-at-eol --name-only` empty). `git checkout -- tests/fixtures/mapping/` restored them.

Observations without a finding: `readmitted` with three values (NO, >30, <30) is y_true **high** - the consistency check treats a categorical label as consistent up to 10 distinct values, and the positive class is a declaration; `prob` with values 1.5/0.2 is score high (range is H03's, declared); `flag` holding `yes`/`no` alone is a y_true candidate at medium by values; `pred.prob` normalises to `pred_prob` (score high).

## Sentence rule

Added sentences that assert what a check guarantees, prevents or closes, with the counter-example status:

- `errors.py`: "a typed halt whose message ends 'reduce your case key to one column', never a traceback" - quotes DEC-11; `test_dec11_via_the_cli_run_and_map_exit_3_with_the_message_and_no_traceback` runs `run` and `map` through `main()` and one subprocess and asserts exit 3, the first stderr line and no `Traceback`. Recorded in the note (item 4). Kept.
- `README.md` and `declare.py` docstring: "E01 when `clustering.unit` names two or more columns" - **over-generalised**; counter-example run above (`"subject_id hadm_id"` -> H08). Not recorded in the note. Violation, non-blocking: the halt is still typed, exit 3, no traceback.
- `profile.py` line 1: "Suppression is applied before anything is displayed or written" - **over-generalised** by the min/max line measured in finding 3. The same paragraph does list min/max, so a reader is told; but the sentence itself is wider than the code.
- `README.md`: "halts H07 ... without reading stdin" - `test_non_tty_with_stdin_closed_exits_3_within_the_timeout` runs with `stdin=DEVNULL` and asserts exit 3 within 120 s (measured 0.28 s); it does not observe that stdin was unread. Borderline; a narrower phrasing is "before any prompt".
- `mapping.py` docstring: "raises every halt the committed fixtures raise, plus two constructed ones, and greps each message and detail for that table's headers and its cell values of three or more characters" - names what the test inspects. Kept.

The note's nine refused sentences are all absent from the diff (grepped the added lines for `never`, `prevents`, `guarantee`, `ensure`, `cannot`, `always`, `closed`, `impossible`, `protects`; the only `never` is the DEC-11 quotation in `errors.py`).

## Cut and carried lists against what I measured

- "Nothing in items 1-8 was cut": consistent with the diff and the 96 tests.
- "PSV not read": a two-column `a|b` file loads as one column named `a|b` (the table prints one `ignore` role; no halt). Confirmed not read as PSV.
- "Diabetes-130 cannot pass `map` without a `period` declaration": `proofpack map --input tests/fixtures/mapping/diabetes_130.csv` -> `HALT H11 ... {"date_like_columns": 1}`, exit 3. Confirmed.
- Note's `[unverified]` marks (PhysioNet prediction-column names, UCI later variables, MIMIC page fields, the console handle): the console one is closed above; the three page claims were not re-fetched here.

## What could not be broken (tried)

- Halt messages carrying a header or a cell value: constructed `SECRET_HDR_label`/`secret_hdr_label` (H07), `Patient_ID`+`Subject_ID` with `SECRETVAL` cells (E01), and re-ran the fixture halts - none of the message/detail strings held a header or a >= 3-character cell value (the committed test does this; I re-read its assertions rather than only trusting its pass).
- Duplicate headers: `patient_id`/`Patient_Id`, `Größe`/`größe`, NFC/NFD `Température` twins, ` label`/`label ` -> all H07 with `n_duplicate_headers: 1`; `patient_id`/`patient-id` (distinct after folding, same after normalising) -> E01, not a crash.
- Hostile values: `nan`/`NaN`/`inf` under `prob` (score high, no exception); `0,5` decimal commas (score low, "not numeric"); 500-character header; tab in a header; all-`None` column; empty header with `None` cells - no traceback anywhere.
- Corrupt prior files under `--yes`: `{not json`, `roles: [{"original": 1}]` -> `H07: mapping.json could not be read`, exit 3; a well-formed prior with a foreign hash -> `H07: header-set hash differs`, detail shows two 12-character hash prefixes only.
- Suppression: count 9 hidden, count 10 shown, the <= 2-unique split suppressed the same way, row 10,001 absent - re-read the literal inputs in the four tests; they assert the figures the note states.

## Could not check

- The three web-page provenance claims marked `[unverified]` in the note (no fetch in this lens).
- mintty behaviour of `_stdin_is_terminal` (no mintty in this session).
- The merge of `a-p1-mapper` onto lane E's `b93e050` (`scripts/mutation_sweep.py` and `src/proofpack/errors.py` are the likely conflict files, as the note says) - the orchestrator's step, not this lens's.
