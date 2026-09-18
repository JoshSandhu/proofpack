# Build day 6, lane A - A-P1 the full mapper

Branch `a-p1-mapper`, tip `555a5e1`, from `4eb44f3`. Worktree
`C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/05205ce1-d2d1-4872-983c-bec2db7cf845/scratchpad/a-p1/wt`
(removed with `git worktree remove --force` after the commit; the branch is kept). Not pushed, not merged. The main tree was not touched; it moved to `b93e050` (lane E) while this ran, so the orchestrator's merge of `a-p1-mapper` (from `4eb44f3`) is a real merge - `scripts/mutation_sweep.py` and `src/proofpack/errors.py` are the two files both lanes are likely to have edited.
Every number below was measured in this session with `PYTHONPATH=<worktree>/src` forced;
`python -c "import proofpack;print(proofpack.__file__)"` printed the worktree's `src\proofpack\__init__.py` in both shells before any suite ran.

## What landed (item -> module/function -> test ids -> fixture)

| # | Item | Module / function | Test ids (`tests/test_mapping_full.py`, marker `day6`) | Checked against |
|---|---|---|---|---|
| 1 | Value-level summaries | `io/profile.py`: `profile_column`, `ColumnSummary` (type, `n_unique`, top <= 20 with counts, min/max, missing %, the <= 2-unique split), `SUPPRESSION_K = 10`, `SAMPLE_ROWS = 10_000`, `FREE_TEXT_UNIQUE_SHARE = 0.5` | `test_free_text_column_with_thirty_distinct_values_shows_none_of_them`, `test_suppression_floor_count_nine_is_suppressed_and_count_ten_is_shown`, `test_two_unique_split_is_suppressed_the_same_way`, `test_sample_boundary_row_10001_does_not_reach_the_summary`, `test_missing_pct_after_missing_token_normalisation`, `test_date_column_lists_no_values_and_coarsens_min_max_to_month`, `test_type_inference_literal_columns`, `test_value_summaries_in_mapping_json_are_the_suppressed_ones` | literal columns in the tests; `sepsis_2019` (patient ids at count 5 each -> `[["<suppressed>", 10]]`) |
| 2 | Heuristics on top of the synonym table | `io/mapping.py`: `normalise_header`, `_name_claim` (canonical / synonym / affix / partial / date-header), `_value_candidate`, `_check_consistency`, the confidence table in the module docstring | `test_two_valued_column_from_each_label_set_is_a_y_true_candidate_at_medium[5 sets]`, `test_two_valued_column_under_a_score_synonym_is_score_at_low_not_y_true`, `test_float_within_unit_interval_is_a_score_candidate_and_outside_is_ignored`, `test_visit_column_holding_dates_is_event_date_at_medium`, `test_unique_integer_column_is_row_id_and_a_repeating_one_is_not_case_id`, `test_case_id_from_a_partial_token_is_low_and_from_a_synonym_is_high`, `test_age_numeric_banded_and_neither`, `test_sex_coding_rules[5 codings x 3 headers]`, `test_site_device_protocol_severity_race_ethnicity_by_synonym_only`, `test_every_other_column_is_ignore_at_high_and_keeps_its_header`, `test_header_only_call_keeps_the_day1_confidences` | literal columns; all 35 fixtures via `test_fixture_roles_and_confidences` |
| 3 | Conflicts and hostile inputs | `_decide_named` (two name claims -> both low), the value-candidate demotion, `fold_header` + the H07 duplicate halt, empty header -> ignore | `test_label_holding_continuous_scores_keeps_the_role_at_low_with_a_note`, `test_two_headers_claiming_y_true_are_both_low_and_yes_is_refused`, `test_value_candidate_yields_to_a_header_that_names_the_role`, `test_two_value_only_candidates_for_one_role_are_both_low`, `test_normalise_header_literal_cases`, `test_bom_in_the_first_header_still_resolves_the_role`, `test_duplicate_headers_after_case_folding_halt_h07_via_the_cli_without_a_traceback`, `test_empty_string_header_is_ignore` | fixtures `sepsis_two_labels`, `sepsis_label_holds_scores`, `sepsis_score_holds_01`, `sepsis_visit_dates`, `sepsis_unicode_headers`, `sepsis_bom_first_header`, `sepsis_whitespace_headers`, `sepsis_dup_after_fold` (H07), `sepsis_nfc_nfd_twins` (H07), `sepsis_empty_header`, `sepsis_200_columns`, `sepsis_one_row`, `sepsis_zero_rows` |
| 4 | DEC-11 composite case key | `errors.py` `MAPPING_CODES = {"E01"}`; `io/declare.py` `_check_dec11_case_key` (list of >= 2, or a string split on `, + & ; |` or ` and `); `map_headers` on two name claims for `case_id` | `test_e01_is_registered_and_constructs`, `test_two_case_id_headers_halt_e01_through_map_headers_and_ingest`, `test_composite_clustering_unit_halts_e01_before_the_schema_check[5 shapes]`, `test_single_column_clustering_units_are_not_e01`, `test_dec11_via_the_cli_run_and_map_exit_3_with_the_message_and_no_traceback` (main() for `run` and `map`, plus one subprocess: exit 3, first stderr line `HALT E01: clustering.unit names 2 columns; reduce your case key to one column`, no `Traceback`) | `sepsis_two_case_ids` (E01), `mimic_composite_key` + its `criteria.yaml` (E01 via the CLI) |
| 5 | Interactive confirm and `--yes` | `cli.py`: `_stdin_is_terminal`, `_confirm_interactive`, `cmd_map`; `mapping.check_h07` (prior hash equal AND every role high in the prior file AND in the fresh mapping); `Mapping.file_sha256`, `decided_by`, UTC timestamp | `test_yes_without_a_prior_mapping_halts_h07`, `test_yes_with_matching_all_high_prior_is_accepted`, `test_yes_with_matching_prior_holding_a_medium_role_halts_h07`, `test_yes_with_a_prior_whose_hash_differs_halts_h07`, `test_yes_is_refused_when_the_fresh_mapping_has_a_medium_even_if_the_file_says_high`, `test_non_tty_without_yes_prints_the_table_then_halts_h07`, `test_non_tty_with_stdin_closed_exits_3_within_the_timeout` (subprocess, `stdin=DEVNULL`, timeout 120 s, measured 0.29 s), `test_tty_prompt_accept_edit_and_abort`, `test_confirm_helper_prompts_once_per_non_high_role_only` | the seeded cohort |
| 6 | Fixtures | `tests/fixtures/mapping/` - 35 CSVs (<= 50 rows, synthetic, seed 20260918) + `*.expected.json` + `mimic_composite_key.criteria.yaml`; generator `scripts/make_mapping_fixtures.py` (expected roles authored in the script, not computed) | `test_register_has_at_least_thirty_fixtures_with_expectations`, `test_fixture_roles_and_confidences[35]`, `test_acceptance_sepsis_and_diabetes_map_high_on_the_five_named_columns` | see the acceptance paragraph |
| 7 | Tests, privacy, H11, CLI table, mutation sweep | `mapping.check_h11(..., mapping=)` (date-like by header or by values; coverage by original header, or by role when it is the sole holder); `Mapping.table()` | `test_mapping_json_round_trip_and_hash_is_order_independent`, `test_no_halt_carries_a_header_or_value` (walks the 3 fixture halts + 2 constructed), `test_h11_fires_on_a_visit_column_holding_dates_and_period_can_cover_it`, `test_h11_two_columns_sharing_the_event_date_role_are_not_covered_by_the_role_name`, `test_cli_map_prints_the_table_for_the_sepsis_fixture_in_a_subprocess`, `test_cli_map_prints_non_ascii_headers_with_pythonutf8` | `sepsis_2019`, `sepsis_visit_dates`, `sepsis_unicode_headers` |
| 8 | Docs | `README.md`: layout lines, a `proofpack map` section, the `mapping.json` shape (one place) | - | - |

96 tests carry `day6`; the whole suite is 460 passed, 1 skipped, 1 xfailed (364 + 96; the skip and the xfail are the day-5 ones).

**Acceptance (brief: Sepsis and Diabetes-130 headers map `high` on label / score / site / age / sex).** Read literally and measured:

- `diabetes_130`: `readmitted` -> y_true high, `pred_prob` -> score high, `hospital` -> site high, `age` -> age_band high (banded `[70-80)` strings), `gender` -> sex high (Male/Female). Met.
- `sepsis_2019_gender_mf`: `SepsisLabel` -> y_true high, `PredictedProbability` -> score high, `hospital` -> site high, `Age` -> age high, `Gender` (M/F) -> sex high. Met.
- `sepsis_2019` (PhysioNet's real coding, fetched: "Gender: Female (0) or Male (1)"): four of the five high; `Gender` -> sex **medium** with the note `no dictionary declared for 0/1`. **Not met as written**, by decision D5 below. Josh's call whether 0/1-coded sex should be high.

## What was cut and why

Nothing in items 1-8 was cut. Two things are recorded as not done rather than cut:

- The PSV (pipe-delimited) format of the PhysioNet files is not read by `load_table` (D1 section 1 says CSV); the Sepsis fixtures are CSV with the PSV header set.
- The Diabetes-130 header set cannot pass `proofpack map`/`run` without a `period` declaration because `time_in_hospital` matches H11's header regex (`^time_`) although it holds integers 1-14. H11 was left as it is (header-conservative; a value-based exemption would weaken a privacy gate: an integer column under a date-like header can be an epoch or serial date). The fixture test drives `map_headers` directly; open question 1.

## Decisions taken

| id | Decision |
|---|---|
| D1 | **Suppression floor k = 10** (`profile.SUPPRESSION_K`): D1 section 5 states no floor, so the egress cell rule `n < 10` of D1 section 6 is reused. A value with count 9 prints as `<suppressed>`; count 10 prints. The suppressed count is over every distinct value below the floor, not only the inspected top 20. Free-text rule: type categorical/string, `n_unique > 2` and `n_unique > 0.5 x` non-missing sample -> no values listed (the `<= 2` exemption keeps the label split visible). |
| D2 | **Sample rule**: the first 10,000 rows after the header, a prefix, no seed (`profile.SAMPLE_ROWS`). Row 10,001 does not reach the summary (`test_sample_boundary_row_10001_does_not_reach_the_summary`). |
| D3 | **Site for Sepsis**: a column `hospital` with values A/B (the two public hospital systems, R3); the per-file patient id arrives as a column `patient`. The prediction columns are `PredictedProbability`/`PredictedLabel` [unverified: the fetched page says only "the risk of sepsis (a real number) and a binary sepsis prediction (0 or 1)"]. Diabetes-130 has no site or model output in the public file: `hospital` (H01-H05) and `pred_prob` are appended [decision]. Dataset-specific synonym rows added: `sepsis_label`, `readmitted`, `predicted_probability`, `predicted_label`, `hospital_system`. |
| D4 | **Duplicate-header code = H07** with the message `two headers are identical after case-folding, whitespace trimming and unicode normalisation; rename one of them` (detail `n_duplicate_headers`). D1 names no code; `load_table`'s exact-duplicate halt is S04 and stays. The identity compared is `fold_header` (BOM stripped, NFC, trimmed, case-folded), not the camel-split key, so `SepsisLabel`/`sepsislabel` and NFC/NFD twins halt while `Sepsis Label`/`sepsis_label` are two claims on one role (both low). |
| D5 | **Sex coded 0/1 is medium**, like 1/2, with the note `no dictionary declared for 0/1`. The brief names only 1/2; treating 0/1 differently from 1/2 could not be justified, and the note is what makes the human confirm the coding. This is the one place the acceptance is not met on the real-coded Sepsis fixture. |
| D6 | **DEC-11 code = `E01`** in a new `errors.MAPPING_CODES` table (the letter DEC-11 names; a separate table so the H-code table stays exact, as `errors.py`'s comment on `SCHEMA_CODES` asks). Both paths end `reduce your case key to one column`: `clustering.unit` as a list of >= 2 or a string with a separator (`,` `+` `&` `;` `|` or ` and ` with spaces - `random_id` is one column), checked in `declare.validate_dict` before the jsonschema step; and two headers resolving to `case_id` by name (canonical/synonym/affix). A partial token (`patient_nbr`, `patient_name`) is not a resolved key: two partials are both low, not E01. |
| D7 | **Confidence table** (module docstring): canonical/synonym/affix + consistent values -> high; synonym/affix with no values -> medium (day-1 behaviour, kept so `test_h07_rejects_yes_when_a_role_is_medium` still holds); conflict -> low + note; partial token -> medium/low; heuristic alone -> medium; two claims on one role -> low for both; unmatched -> ignore at high. `--yes` now checks every role high in the prior file **and** in the fresh mapping (a hand-edited all-high file does not pass a table whose computed mapping has a medium). |
| D8 | **`ignore` is stored as the string `ignore` in mapping.json and as `None` in memory**, so `apply_mapping` and `gates.report()` are unchanged; `Mapping.read` accepts both. `decided_by` is `proposed` for an unconfirmed mapping (`interactive` / `file` are the two `map` writes). `cmd_run` still writes the computed mapping with `decided_by: proposed` when no prior exists (untouched; cli edits were kept to the `map` subparser, `cmd_map` and its two helpers). |
| D9 | **H11 by values**: `check_h11(..., mapping=)` adds columns whose summary type is `date`; a column is covered by `period.column` equal to its header, or to its role when it is the sole holder of that role (two `event_date` holders still halt: `test_h11_two_columns_sharing_the_event_date_role_are_not_covered_by_the_role_name`). `gates.ingest` now maps with values and passes the mapping to H11. |
| D10 | **Windows stdin**: with `stdin=DEVNULL`, `sys.stdin.isatty()` returned True and `input()` raised EOFError (exit 5) - measured in `test_non_tty_with_stdin_closed_exits_3_within_the_timeout` before the fix. `_stdin_is_terminal` adds `GetConsoleMode` on Windows (returned 0 for NUL); `_confirm_interactive` also maps EOFError to H07. A real console handle was not measured in this session [unverified]. |
| D11 | **Mutation sweep**: `Mutant.marker` (default `day5`); `--marker` selects its own list, `--only` picks by id across lists. Without it the 34 day-5 mutants print as survivors under `--marker day6` (they touch code no day-6 test observes) - seen in the first run, `51 planted, 17 killed, 34 survived`. |
| D12 | **Empty-string header -> ignore at high** with the note `empty header` (a pandas index export); its unique integers are not proposed as `row_id`. |

## Sentences refused

1. "No HaltError raised here carries an original header or a cell value" (mapping.py docstring, first draft) - replaced by what the test inspects: it raises the 3 fixture halts plus 2 constructed ones and greps message + detail for that table's headers and cell values of >= 3 characters.
2. "Declarations are never inferred here" (mapping.py, README) - replaced by "reads no declaration and writes none; `io.declare` reads them from `criteria.yaml`".
3. "The engine never guesses which code is which" (mapping.py) - replaced by "no dictionary is applied to the codes, so the levels stay the strings 1 and 2".
4. "Original headers never leave the machine" (mapping.py, README) - replaced by "written to mapping.json and nowhere else by this module" / "the one file this command writes original headers to".
5. "`GetConsoleMode` succeeds only for a real console handle" (cli.py) - not measured for a console; replaced by the measured NUL result and an [unverified] mark.
6. "Never case_id / never a categorical attribute" (`_value_candidate` docstring) - replaced by "not among this function's outcomes".
7. "…_is_never_case_id" (test name) - renamed `_is_not_case_id`.
8. "Suppression before display prevents a row-level value from appearing" - not written; the note says which literal counts print and which do not.
9. "The non-TTY path never hangs" - not written; the test states `stdin=DEVNULL`, timeout 120 s, measured 0.29 s.

## Re-run these (both shells, at `555a5e1`, `PYTHONPATH` forced to the worktree's `src`, `PYTHONUTF8=1` for the map demo)

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| `python -c "import proofpack;print(proofpack.__file__)"` | `...\scratchpad\a-p1\wt\src\proofpack\__init__.py` | same |
| `python -m pytest -q -p no:cacheprovider` | `460 passed, 1 skipped, 1 xfailed in 40.72s` | `460 passed, 1 skipped, 1 xfailed in 47.01s` |
| `python -m pytest -q -p no:cacheprovider -m day6` | `96 passed, 366 deselected in 1.92s` | `96 passed, 366 deselected in 2.13s` |
| `python -m ruff check .` | `All checks passed!` | `All checks passed!` |
| `python -m ruff format --check .` | `58 files already formatted` (main at `4eb44f3` reported `55 files already formatted`; the three new files account for the difference; no file I did not touch was reformatted) | `58 files already formatted` |
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.` | `All essential checks passed.` (exit 0) |
| `python scripts/mutation_sweep.py --marker day6` | `17 planted, 17 killed, 0 survived; 30 s` | `17 planted, 17 killed, 0 survived; 31 s` |
| `python scripts/mutation_sweep.py --marker day5 --only ref_largest_to_smallest` | not run in Bash | `1 planted, 1 killed, 0 survived; 11 s` (the day-5 list still runs under its marker) |
| `python -m proofpack.cli map --input tests/fixtures/mapping/sepsis_2019.csv --out ../m.json` | exit 3; output below | exit 3; the 24 stdout lines diffed byte-identical to Git Bash's (CR/LF and the BOM `Out-File` adds stripped) |

Baseline before any change, in the worktree at `4eb44f3`: `364 passed, 1 skipped, 1 xfailed in 42.87s`.

Map demo output (Git Bash; the three stderr lines came first in both tools' captured output, which merge the streams; the order in a console was not measured):

```
HALT H07: stdin is not a terminal: run interactively or pass --yes with a prior mapping.json
  detail: {"non_high_roles": 2}
  No document was written.
  original header                  -> role           conf    value summary
  'patient'                        -> case_id        low     categorical; 10 unique; 0.0% missing; values: <suppressed> (10 distinct below k=10)
                                      note: header resembles a case identifier; confirm or ignore
  'HR'                             -> ignore         high    int; 38 unique; 2.0% missing; min 55 max 124; values: <suppressed> (38 distinct below k=10)
  'O2Sat'                          -> ignore         high    int; 13 unique; 8.0% missing; min 88 max 100; values: <suppressed> (13 distinct below k=10)
  'Temp'                           -> ignore         high    float; 20 unique; 42.0% missing; min 35.4 max 38.9; values: <suppressed> (20 distinct below k=10)
  'SBP'                            -> ignore         high    int; 33 unique; 0.0% missing; min 94 max 159; values: <suppressed> (33 distinct below k=10)
  'MAP'                            -> ignore         high    int; 34 unique; 0.0% missing; min 60 max 109; values: <suppressed> (34 distinct below k=10)
  'DBP'                            -> ignore         high    int; 29 unique; 0.0% missing; min 50 max 94; values: <suppressed> (29 distinct below k=10)
  'Resp'                           -> ignore         high    int; 20 unique; 0.0% missing; min 10 max 29; values: <suppressed> (20 distinct below k=10)
  'EtCO2'                          -> ignore         high    empty; 0 unique; 100.0% missing
  'Age'                            -> age            high    float; 50 unique; 0.0% missing; min 20.04 max 84.65; values: <suppressed> (50 distinct below k=10)
  'Gender'                         -> sex            medium  int; 2 unique; 0.0% missing; min 0 max 1; values: 0 (28), 1 (22)
                                      note: no dictionary declared for 0/1
  'Unit1'                          -> ignore         high    int; 2 unique; 14.0% missing; min 0 max 1; values: 1 (24), 0 (19)
                                      note: two-valued but y_true is claimed by name; ignored
  'Unit2'                          -> ignore         high    int; 2 unique; 18.0% missing; min 0 max 1; values: 0 (24), 1 (17)
                                      note: two-valued but y_true is claimed by name; ignored
  'HospAdmTime'                    -> ignore         high    float; 50 unique; 0.0% missing; min -198.06 max -0.97; values: <suppressed> (50 distinct below k=10)
  'ICULOS'                         -> ignore         high    int; 5 unique; 0.0% missing; min 1 max 5; values: 1 (10), 2 (10), 3 (10), 4 (10), 5 (10)
  'SepsisLabel'                    -> y_true         high    int; 2 unique; 0.0% missing; min 0 max 1; values: 0 (34), 1 (16)
  'PredictedProbability'           -> score          high    float; 46 unique; 0.0% missing; min 0.001 max 0.9002; values: <suppressed> (46 distinct below k=10)
  'PredictedLabel'                 -> y_pred         high    int; 2 unique; 0.0% missing; min 0 max 1; values: 0 (37), 1 (13)
  'hospital'                       -> site           high    categorical; 2 unique; 0.0% missing; values: B (26), A (24)
```

Header provenance fetched in the Claude in-app browser (18 September): PhysioNet 2019 page (the 41 columns, `Gender: Female (0) or Male (1)`, `Age` years with 100 for >= 90, one file per subject `p00101.psv`); UCI 296 page (first 10 variables: `encounter_id`, `patient_nbr`, `race`, `gender` male/female/unknown-invalid, `age` `[0, 10)`..`[90, 100)`, `weight`, `admission_type_id`, `discharge_disposition_id`, `admission_source_id`, `time_in_hospital`; `readmitted` and the later variables are [unverified] - the table's later pages were not opened); MIMIC-IV demo page (`subject_id`, `anchor_year_group` named; `hadm_id`, `gender`, `anchor_age`, `race`, `admittime`, `dischtime` [unverified] on that page). All three are recorded in `scripts/make_mapping_fixtures.py`'s docstring.

## Needs from Josh

1. D5: should a sex column coded 0/1 (PhysioNet's coding) be `high` rather than `medium`? As built, `--yes` is refused on the real-coded Sepsis header set until a human has confirmed the coding once.
2. D6: the DEC-11 code is `E01` in `errors.MAPPING_CODES`. If the E family should be named differently (or should be H13), say so before another lane depends on the string.

## Open questions (at most five)

1. H11 halts the real Diabetes-130 header set on `time_in_hospital` (integers 1-14) with no way past except a `period` declaration on a non-date column. Options: (a) leave it (a halt the customer can explain), (b) allow an interactively confirmed `ignore` role in `mapping.json` to exempt a header-date-like column from H11 - a privacy-gate change that needs its own fresh-attack lens (CLAUDE.md, DEC-12 i).
2. `cmd_run` without a prior `mapping.json` and without `--yes` proceeds on the computed mapping (day-1 behaviour, out of today's cli scope). Should `run` insist on a confirmed `mapping.json` (H07) the way `map` now does?
3. The value-summary `min`/`max` of a numeric column are single-row values by construction (D1 section 5 lists them). Keep, or coarsen numeric min/max to a band as dates are coarsened to month?
4. Should `mapping.json` be written with the D1 key names `roles` + `confidences` as two maps, or is the day-1 list-of-entries shape (now with `source` and `notes`) what E7's manifest should hash? README documents the shape as built.
5. `sepsis_2019`'s `patient` column is `case_id` at low (partial token). A user who concatenates PSV files would more likely name it `patient_id` or `subject`; is `patient` worth a synonym row (which would make it high on values that repeat)?
