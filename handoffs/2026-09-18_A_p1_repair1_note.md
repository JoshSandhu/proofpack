# Day 6 A - repair 1 for A-P1 the full mapper (18 September 2026)

Branch `a-p1-mapper`, one commit `e92989b` on top of `555a5e1` (from `4eb44f3`). Not pushed, not
merged. The main tree (`b93e050`, lane E, `calibration.py` modified in its working tree) was not
touched: read once with `git status`, never checked out, stashed or committed in.

Worktrees: `scratchpad/a-p1-r1/wt` (the branch) and `scratchpad/a-p1-r1/tip` (detached at
`555a5e111afdfc245f7a5bfb8111d03bd854e478`, for the pre-fix failures). Both removed at the end;
the branch is the deliverable. `PYTHONPATH=<worktree>/src` on every run;
`python -c "import proofpack;print(proofpack.__file__)"` printed the worktree's
`src\proofpack\__init__.py` in Git Bash and in PowerShell 5.1 before any number below was taken
(and the tip worktree's own path before the pre-fix run).

## 0. Figures

| | Git Bash | PowerShell 5.1 |
|---|---|---|
| Suite at `555a5e1` in the worktree before any edit | **460 passed, 1 skipped, 1 xfailed in 48.01s** | - |
| Suite at `e92989b` | **505 passed, 1 skipped, 1 xfailed in 44.72s** | **505 passed, 1 skipped, 1 xfailed in 43.42s** |
| `-m day6` at `e92989b` | **141 passed, 366 deselected in 2.50s** | **141 passed, 366 deselected in 2.54s** |
| `python -m ruff check .` / `ruff format --check .` | All checks passed! / 59 files already formatted | same |
| `python -m proofpack.cli doctor --offline` | All essential checks passed. | same, exit 0 |
| `python scripts/mutation_sweep.py --marker day6` | **27 planted, 27 killed, 0 survived; 62 s** (was 17/17/0) | - |
| New tests against `555a5e1` (file copied into the tip worktree) | **30 failed, 15 passed, 1 deselected**; the deselected one (`test_ctrl_c_at_the_prompt_is_h07`) run alone interrupts pytest itself: `!!! KeyboardInterrupt !!!`, `no tests ran` | - |
| Lens mutants L09, L13, L14, L15, L18, L26, L20, L22 planted in the repaired tree (`scratchpad/a-p1-r1/mutants.py`, copies `src` + `schema`, `-m day6 -x`) | **8 planted, 8 killed**; each by the test named for it in section 2 | - |

141 = 96 + 46 - 1: `tests/test_mapping_repair1.py` has 27 test functions, 46 items (three
parametrised); one item is the Ctrl-C test counted once. 505 = 460 + 46 - 1.

Nothing weakened, measured: `git diff --name-status 555a5e1 e92989b -- tests/` = 2 `M`, 1 `A`,
**0 `D`**; added lines matching `mark.skip|skipif|xfail|.only|pytest.skip|importorskip`: **0**; no
marker removed. Five lines were deleted from `tests/`, each replaced on the next line (section
1 lists them). `src/proofpack/stats/`, `schema/output_schema_v1.json`, `pyproject.toml`: **no
diff**. `cli.py` edits are inside `_stdin_is_terminal`'s docstring, `_confirm_interactive`, two
new helpers (`_ask`, `_tolerant_console`) and `cmd_map`; the `map` subparser is unchanged.

Line endings: every tracked file I edited is `i/lf w/crlf` before and after (edits went through a
helper that normalises to LF, replaces, and writes CRLF back; one `sed -i` pass turned four files
LF and they were converted back before the commit). The new test file is `i/lf w/lf` (written
once; git normalises it on checkout). One heredoc edit collapsed backslashes (the known trap) and
was reverted with `git checkout --` before being redone from a script file.

The CLI on the sepsis fixture, both shells (`PYTHONUTF8=1`, stdin from NUL): exit 3, the three
stderr lines, then the 24-line table in which every numeric column with fewer than 10 rows at an
extreme now reads `min <suppressed> max <suppressed>` (`'Age'`, `'HospAdmTime'`, `'HR'`,
`'PredictedProbability'`, ...) and `'ICULOS'` keeps `min 1 max 5` (each value held by 10 rows),
`'SepsisLabel'` keeps `min 0 max 1` (34 and 16 rows), `'Gender'` keeps `min 0 max 1` (28 and 22).

## 1. Findings -> fix -> test id -> first `E` line at `555a5e1`

Every `E` line is the first one pytest printed for that test in the tip worktree, verbatim (long
ones cut at pytest's own ellipsis). Tests are in `tests/test_mapping_repair1.py::` unless a path
is given.

| Finding | Fix (module) | Test id | First `E` line at `555a5e1` |
|---|---|---|---|
| FA-B1 / RG-NB-3 `min`/`max` print a value the floor suppressed | `io/profile.py`: `_extreme_or_suppressed(x, counts)` - a numeric extreme is printed only when the sampled rows holding that number (summed over strings that parse to it, `"1"` + `"1.0"`) are >= `SUPPRESSION_K`, else the field holds `<suppressed>`; per extreme, so `["100"]*41+["7"]*9` prints `min <suppressed> max 100`. `signals["min"/"max"]` (the mapper's, not serialised) keep the true extremes. Date min/max unchanged (`YYYY-MM`, not put through the floor - section 6, question 1). Module docstring rewritten to name the three fields the floor filters; `ColumnSummary` docstring names what each field holds; README step 1 states the rule with the literal column | `test_numeric_min_max_below_the_floor_print_as_suppressed` (five literal columns, the 10/9-row boundary, the `"1"`/`"1.0"` sum, the sepsis fixture's `Age` through `map_headers`, `table()` and `write()`: `20.04`, `84.65`, `-198.06` absent) | `AssertionError: assert ('7', '100') == ('<suppressed>', '100')` |
| | the two existing assertions that pinned the leak | `tests/test_mapping_full.py::test_two_unique_split_is_suppressed_the_same_way` (`s.max == "1"` -> `s.max == SUPPRESSED`, comment says what the line pinned before); `::test_missing_pct_after_missing_token_normalisation` (`min "1" max "4"` -> both `SUPPRESSED`, plus `signals["min"] == 1.0 and signals["max"] == 4.0`) | (modified expectations; both shells) |
| FA-B2 / RG-NB-2 `/` `:` `-` space tab reach H08 enum, not E01 | `io/declare.py`: `_CASE_KEY_SEPARATORS = r"\s+and\s+|[^A-Za-z0-9_]+"`; `_CASE_KEY_LIST_KEYS` (`columns`, `column`, `key`, `keys`, `units`, `fields`) with a list of >= 2 -> E01 `clustering.<key> lists N columns; reduce your case key to one column`. `errors.py` comment names the two raisers and the CLI test; README step 3 names the character class and the shapes, including that `patient-id` counts two | `test_separators_the_lens_listed_reach_e01[13 shapes]` (the seven lens shapes, `&` `;` `\|`, `patient-id`, `["patient_id","patient_id"]`, `"a, b, c"` -> 3); `test_clustering_list_keys_of_two_halt_e01_and_of_one_do_not[6 keys]`; `test_one_column_units_outside_the_enum_stay_h08` (`subject_id`, `random_id` -> H08 at `clustering/unit`; `case_id`, `none` pass); `test_slash_composite_unit_via_the_cli_is_e01_not_h08` (`subject_id/hadm_id` in a criteria.yaml through `map` and `run` via `main()`: exit 3, first stderr line `HALT E01: clustering.unit names 2 columns; reduce your case key to one column`, no `H08`, no `Traceback`, nothing written) | `AssertionError: assert 'H08' == 'E01'` (eight of the thirteen; the `&` `;` `\|` list and `a, b, c` cases passed at the tip); `Failed: DID NOT RAISE HaltError` (all six keys); `AssertionError: assert 'HALT H08: de...ng/unit: enum' == 'HALT E01: cl...to one column'` |
| FA-N1 `run` writes `decided_by: proposed`; `map --yes` accepts it | `io/mapping.py`: `CONFIRMED_DECIDED_BY = {"interactive", "file"}`; `check_h07` in non-interactive mode halts H07 `non-interactive mode requires a confirmed mapping.json (decided_by interactive or file); this one was not confirmed: run proofpack map interactively once`, detail `{"decided_by": <first 16 chars>}`, before the all-high checks. A day-1 file with no `decided_by` key reads as `file` (unchanged). Three tests that wrote unconfirmed priors now set `decided_by` first: `test_mapping_full.py::test_two_headers_claiming_y_true_are_both_low_and_yes_is_refused`, `::test_yes_with_matching_all_high_prior_is_accepted`, `::test_yes_with_matching_prior_holding_a_medium_role_halts_h07`, `::test_yes_is_refused_when_the_fresh_mapping_has_a_medium_even_if_the_file_says_high`, and `test_halt_gates.py::test_h07_accepts_yes_with_matching_high_mapping` (their assertions are unchanged) | `test_yes_refuses_a_proposed_prior` (`run` writes `proposed`; `map --yes` exit 3 with that first line, the file's bytes unchanged; the same file set to `interactive` is then accepted and rewritten `file`; the key deleted reads as `file` and is accepted); `test_ingest_still_accepts_a_confirmed_prior_and_the_day1_medium_refusal_holds` | `assert 0 == 3`; `Failed: DID NOT RAISE HaltError` |
| FA-N2 all-high table asks nothing, records `interactive` | `cli.py` `_confirm_interactive`: when `m.non_high` is empty, one prompt `every role is high (N columns): [a]ccept / [q]uit? `; `q` -> H07 abort | `test_all_high_table_asks_once_before_interactive` (the seeded cohort: exactly that one prompt string; `q` through `main()` leaves no file; `a` writes `interactive`) | `AssertionError: assert [] == ['every role ...t / [q]uit? ']` |
| FA-N3 / RG-NB-4 accept/edit keep confidence (L18/L26 survived) | No behaviour change (needs Josh, section 6); pinned | `test_accept_and_edit_keep_the_computed_confidence` (`gender` 1/2: accept keeps `medium`, `all_high` False; edit to `ignore` keeps `medium`, role None) - **passes at `555a5e1`**; kills L18 and L26 | - |
| FA-N4 edit to a held role is written; `run` halts later | `_confirm_interactive`: an edit naming a role another entry already holds (`ignore` excepted) says `<role> is already held by '<original>': choose another` and re-prompts | `test_edit_to_a_role_another_column_holds_is_refused_at_the_prompt` (`e`, `y_true` refused; `e`, `sex` accepted; `holders("y_true") == ["y_true"]`); `test_second_edit_to_an_unheld_attr_role_is_accepted` (`attr_coding`) - the second passes at the tip | `assert [] == ['  y_true is...oose another']` |
| FA-N5 Ctrl-C at the prompt is a traceback | `_ask(ask, prompt)` maps `EOFError` -> H07 `stdin closed at the prompt: ...` and `KeyboardInterrupt` -> H07 `mapping interrupted at the prompt; nothing written`; used by every prompt | `test_ctrl_c_at_the_prompt_is_h07` (`input` raising `KeyboardInterrupt` at the `gender` prompt and at the all-high prompt: exit 3, that first stderr line, no `Traceback`, no file); `test_eof_at_the_prompt_is_h07` (the same two prompts with `EOFError`) | pytest itself interrupted (`!!! KeyboardInterrupt !!!`, `no tests ran in 0.52s`); `assert 0 == 3` (the all-high half; the per-role half held at the tip) |
| FA-N6 malformed prior -> exit 5 | `Mapping.read`: `header_set_sha256` must be a string, each `roles` entry a mapping with string `original` and `confidence`, `value_summaries` null -> `{}`; `AttributeError` joins the caught set (a non-mapping file or a non-list `roles` raise on their own - the first draft's explicit check was an equivalent mutant, section 2) | `test_malformed_prior_under_yes_halts_h07_not_exit_5[7 files]` (`roles: "SECRET_HDR"`, `roles: [1, 2]`, hash `123`, `original: 1`, `confidence: null`, `value_summaries: null`, `[]`): exit 3, first line `HALT H07: mapping.json could not be read`, no `internal error`, no `SECRET_HDR` | `assert 5 == 3` (three); `assert 0 == 3` (two - the tip accepted them); `AssertionError: assert None == {}`; the `[]` file passed at the tip |
| FA-N7 `15-03-2024` passes H11 | `io/profile.py` `DATE_PATTERNS` gains `^\d{1,2}-\d{1,2}-\d{4}$`; `_date_key` reads the dash shape as D-M-YYYY like the slash one | `test_dash_separated_dates_are_typed_date_and_halt_h11` (`visit` of three dash dates x 10: type `date`, `2024-03`..`2025-11`, `event_date medium`, H11 fires with `{"date_like_columns": 1}`, a `period` on `visit` covers it; `45000..45029` stays `int`, `row_id medium`, no H11) | `AssertionError: assert ('categorical' == 'date'` |
| FA-N8 cp1252 stdout + CJK header -> exit 5 | `cmd_map` calls `_tolerant_console()`: `sys.stdout`/`stderr.reconfigure(errors="backslashreplace")` in a try | `test_cp1252_stdout_prints_the_table_with_escapes` (subprocess, `PYTHONIOENCODING=cp1252`, `PYTHONUTF8` unset, header `体温`: exit 3, `original header` and `体温` in stdout, first stderr line the non-terminal H07, no `UnicodeEncodeError`) | `AssertionError: ('', "internal error: UnicodeEncodeError: 'charmap' codec can't encode characters in position 79-80: character maps to <undefined>\r` |
| FA-N12 `--quiet` prompts without the table | `cmd_map`: the table is printed when not `--json-log` and (not `--quiet` or stdin is a terminal); not a terminal + `--quiet` still prints nothing and halts | `test_quiet_at_a_terminal_prints_the_table_the_prompt_refers_to` (terminal: first stdout line is the table header, `'gender'` present, `mapping written` absent; non-terminal: stdout and stderr empty, exit 3) | `IndexError: list index out of range` |
| FA-N10 eight mutants survive | Pins with literal inputs | `test_free_text_guard_two_unique_column_of_singletons_is_not_free_text` (L09: `["a","b"]` not free text, `top == [[<suppressed>, 2]]`; `["a","b","c"]` free text); `test_label_with_ten_distinct_values_is_consistent_and_eleven_is_a_conflict` (L13); `test_two_partial_tokens_for_one_role_are_both_low_with_the_note` (L14: `anchor_age` + `age_years`); the `&` case of the separators test (L15); `test_hash_mismatch_detail_carries_twelve_character_prefixes` (L20); `test_missing_pct_is_rounded_to_two_decimals` (L22: 1 of 3 -> 33.33, 1 of 7 -> 14.29); L18/L26 above - all **pass at `555a5e1`** and each kills its mutant (section 2). `scripts/mutation_sweep.py` day-6 list: `tty_check_always_true` pattern updated to the moved line; ten repair mutants added | - |
| FA-N11 universal in a test id | Renamed `test_fixture_halts_and_two_constructed_ones_carry_no_header_or_value`; `mapping.py` docstring cites the new id | the rename (the body is unchanged) | - |
| RG-NB-7 `[unverified]` console; generator writes LF | `_stdin_is_terminal` docstring records this session's measurement (a fresh console window via `Start-Process python`: `isatty=True terminal=True`, from the worktree's `cli.py`; mintty not measured); `scripts/make_mapping_fixtures.py` writes the CSV with the line ending the existing file has (`\r\n` if present, else `\n`). Measured before: regenerating listed **35** fixtures in `git status --short`, `git diff --ignore-cr-at-eol` empty; after: **0** listed, `git ls-files --eol` still `i/lf w/crlf` | - | - |

Sentences the lenses falsified, and what replaced them: `profile.py` "Suppression is applied
before anything is displayed or written ..." -> the three fields the floor filters, the literal
column that leaked at `555a5e1`, and the test id; `ColumnSummary` "Aggregates only." -> what each
field holds; README step 1 -> the min/max rule with `["100"] * 41 + ["7"] * 9`; `errors.py`
"a composite case key is a typed halt whose message ends ..., never a traceback" -> the two
functions that raise E01 and what the CLI test asserts; README step 3 "names two or more columns"
-> the separator character class, the list keys, and `patient-id`; `_check_dec11_case_key`
docstring likewise; README step 4 "without reading stdin" -> "before any prompt".

### Counter-examples that FAILED first (the hard rule, applied to my own checks)

1. `test_edit_to_a_role_another_column_holds_is_refused_at_the_prompt` failed on my first
   answer sequence (`e y_true e attr_x e sex`): the second edit is accepted and ends the loop,
   so the third was never read and the role was `attr_x`. The sequence is now `e y_true e sex`
   and the `attr_x` case is its own test.
2. My first `mutants.py` reported 19 "killed" that were 19 collection errors (the copy lacked
   `schema/`); `-q -q` had hidden the summary. Re-run with `schema` copied and `-rf`: 18 killed
   by a named test, 1 survived (R11) - the survivor was an equivalent mutant (the explicit
   `roles`-is-a-list check is subsumed by the per-entry check), so that line was removed.
3. `scripts/mutation_sweep.py --marker day6` halted on `tty_check_always_true: pattern matched
   0 time(s)` after the `cmd_map` restructure - the pattern now names the moved line.
4. The `_ask` docstring claimed EOFError at the prompt is H07 with no test feeding EOFError
   at a prompt (the day-6 subprocess test feeds `stdin=DEVNULL`, which halts before any prompt);
   `test_eof_at_the_prompt_is_h07` was added and cited.

## 2. Mutants

`scratchpad/a-p1-r1/mutants.py` (copies `src` and `schema`, one literal edit, `-m day6 -x -rf`
from the worktree), in the repaired tree:

| Mutant | Result | Killed by |
|---|---|---|
| L09 free-text `n_unique > 2` -> `> 0` | 1 failed, 135 passed | `test_free_text_guard_two_unique_column_of_singletons_is_not_free_text` |
| L13 label conflict `> 10` -> `> 100` | 1 failed, 136 passed | `test_label_with_ten_distinct_values_is_consistent_and_eleven_is_a_conflict` |
| L14 two partials `>= 2` -> `>= 3` | 1 failed, 137 passed | `test_two_partial_tokens_for_one_role_are_both_low_with_the_note` |
| L15 `&` dropped from the separators | 1 failed, 105 passed | `test_separators_the_lens_listed_reach_e01[patient_id & study_id-2]` |
| L18 edit sets high | 1 failed, 121 passed | `test_accept_and_edit_keep_the_computed_confidence` |
| L26 accept sets high | 1 failed, 121 passed | the same |
| L20 full hashes in the H07 detail | 1 failed, 138 passed | `test_hash_mismatch_detail_carries_twelve_character_prefixes` |
| L22 `missing_pct` unrounded | 1 failed, 139 passed | `test_missing_pct_is_rounded_to_two_decimals` |
| R01 min/max floor removed | 1 failed, 39 passed | `test_mapping_full.py::test_two_unique_split_is_suppressed_the_same_way` |
| R02 floor `>= K` -> `>= K - 1` | 1 failed, 39 passed | the same |
| R03 `proposed` added to `CONFIRMED_DECIDED_BY` | 1 failed, 119 passed | `test_yes_refuses_a_proposed_prior` |
| R04 list keys need three | 1 failed, 111 passed | `test_clustering_list_keys_of_two_halt_e01_and_of_one_do_not[columns]` |
| R05 all-high prompt removed | 1 failed, 120 passed | `test_all_high_table_asks_once_before_interactive` |
| R06 held-role check off | 1 failed, 122 passed | `test_edit_to_a_role_another_column_holds_is_refused_at_the_prompt` |
| R07 `KeyboardInterrupt` not mapped | pytest interrupted after 124 passed | the interrupt inside `test_ctrl_c_at_the_prompt_is_h07` |
| R08 dash date shape removed | 1 failed, 132 passed | `test_dash_separated_dates_are_typed_date_and_halt_h11` |
| R09 console not reconfigured | 1 failed, 133 passed | `test_cp1252_stdout_prints_the_table_with_escapes` |
| R10 `--quiet` hides the table at a terminal | 1 failed, 134 passed | `test_quiet_at_a_terminal_prints_the_table_the_prompt_refers_to` |
| R11 explicit `roles`-is-a-list check removed | 141 passed (SURVIVED) | equivalent: the per-entry `isinstance(r, dict)` check raises the same `TypeError`; the line was deleted |

The committed `scripts/mutation_sweep.py --marker day6` now carries R01-R06 and R08-R10 (ten
including `min_max_floor_off_by_one`): 27 planted, 27 killed, 62 s.

## 3. Carried, and why

| Finding | Why carried |
|---|---|
| FA-N1, first half: `proofpack run` writes `./pack/mapping.json` (original headers, value summaries) into the pack output directory, and without `--yes` proceeds on the computed mapping | `cmd_run` is outside today's cli scope (the `map` subparser and `cmd_map` only, so lane E's merge stays clean). The `--yes` half is fixed. Build note open question 2; Josh's call (section 6). |
| FA-N3 / RG-NB-4: a human accept leaves `confidence` as computed, so `--yes` is unreachable on any table with a non-high role | D1 section 5 step 3 verbatim and the build note's needs-from-Josh 1; pinned by `test_accept_and_edit_keep_the_computed_confidence` so the rule is observed either way. |
| FA-N9: `hadm_id` beside `subject_id` -> `row_id medium`, not E01; `subject_id_v2` -> ignore | Follows the build's D6 (E01 on name claims only). Adding `hadm_id` as a `case_id` synonym would make every MIMIC export halt E01 unless renamed - Josh's call (section 6). |
| FA-N7, second half: Excel serials (`45000..`) and `20240315` are `int` | Pinned as `int` in the dash-date test; a value rule would type every five-digit integer column as a date. |
| RG-NB-1: four day-6 tests pass at `4eb44f3` | They guard day-1 behaviour under the `day6` marker; left as they are. Likewise 15 of the 46 new items pass at `555a5e1` by design (pins for FA-N10 and FA-N3, and the separator shapes that already reached E01). |
| RG-NB-5: `mapping.json` shape vs D1 step 5's key list | Josh's (build note open question 4); the repair adds no key. |
| RG-NB-6: Sepsis `Gender` 0/1 maps `sex` at medium | Josh's (needs-from-Josh 1). |
| Date `min`/`max` (`YYYY-MM`) are not put through the floor | D1 section 1's coarsening as built; a month held by one row is still a month. Open question 1. |
| `clustering.unit: subject_id` (one token, not in the enum) halts H08 `declaration invalid at clustering/unit: enum`, which names no fix | The generic schema-error path (`_h08_from_schema_error`) is day-1 code shared by every declaration; a special case for this path was not added today. `test_one_column_units_outside_the_enum_stay_h08` pins it. |
| mintty (Git Bash's own terminal) behaviour of `_stdin_is_terminal` | Not measured (no mintty in this session); the docstring says so. |
| FA-B2 side note: `patient-id` (a hyphenated single name) halts E01 "names 2 columns" | Chosen over leaving `-` out (the lens listed `patient_id-study_id`); stated in README step 3, the separator comment and the test's parameter list. The customer's fix (declare `unit: case_id`, map the column) is the same one H08 would need. |

## 4. Decisions taken

| id | Decision |
|---|---|
| R1-D1 | Numeric min/max follow the floor by **withholding** (the `<suppressed>` literal, per extreme), not by banding: D1 gives no band rule and a band of one row is still one row. The rule counts rows holding the number, not the string. |
| R1-D2 | DEC-11 string separators = `' and '` plus any run outside `[A-Za-z0-9_]`; the E01 message keeps the shape `clustering.unit names N columns; reduce your case key to one column`. |
| R1-D3 | `clustering.columns` / `column` / `key` / `keys` / `units` / `fields` with >= 2 entries is E01 `clustering.<key> lists N columns; ...`; one entry is not inspected further (the schema does not forbid extra keys - unchanged). |
| R1-D4 | `--yes` requires the prior's `decided_by` in `{interactive, file}`; absent -> `file` (day-1 files). The check reads the string only: a hand-edited `interactive` passes (stated in `check_h07`'s docstring). |
| R1-D5 | An all-high table gets one whole-mapping prompt; `q` aborts. Per-role prompts unchanged. |
| R1-D6 | An edit to a role another entry holds is refused at the prompt (`ignore` may be held by many). |
| R1-D7 | Ctrl-C and EOF at any prompt are H07 with distinct messages; `main()` is unchanged. |
| R1-D8 | `_tolerant_console()` runs in `cmd_map` only (`main()` is outside today's cli scope); `run`/`compare` still print with the interpreter's error handler. |
| R1-D9 | `--quiet` at a terminal prints the table (the prompts refer to it); `--json-log` never prints it. |
| R1-D10 | The fixture generator matches the existing file's line ending; `expected.json` / `criteria.yaml` are written in text mode as before. |
| R1-D11 | The eight lens survivors are pinned by tests rather than by adding them to the committed sweep (they are the lens's, kept in `scratchpad/a-p1-r1/mutants.py`); the ten repair gates are in the committed sweep. |

## 5. Sentences refused

1. "min/max can no longer leak a row-level value" - not written; `profile.py` names the three
   fields the floor filters, the literal column that leaked, and the test id.
2. "E01 now catches every way of writing a composite key" - not written; the separator rule is
   a character class, `patient-id` is named as the two-token single name, and the test lists
   the thirteen literal strings.
3. "`--yes` now requires a human decision" - not written; `check_h07` says it reads the
   `decided_by` string and that `proposed` is what `run` writes.
4. "A prompt can never end in a traceback" - not written; the two tests raise
   `KeyboardInterrupt` and `EOFError` from `input` at two named prompts.
5. "A malformed mapping.json is always H07" - not written; `Mapping.read` lists the shapes it
   checks and the test lists the seven literal files.
6. "The profiler recognises date columns" - not written; the `DATE_PATTERNS` comment lists four
   shapes and names Excel serials as `int`.
7. "Non-UTF-8 consoles are handled" - not written; the test names `PYTHONIOENCODING=cp1252`,
   `PYTHONUTF8` unset and one CJK header.
8. "Nothing sensitive can reach the H07 message" (FA-N6) - not written; the test asserts
   `SECRET_HDR` absent for that literal file.
9. "The suite now defends the floor" - not written; the comment on the changed assertion says
   what that line pinned at `555a5e1`.
10. "`_stdin_is_terminal` is correct on Windows consoles" - not written; the docstring records
    the one console window measured and names mintty as unmeasured.

## 6. Needs from Josh

1. (Build note 1) Should `sex` coded 0/1 be `high`? Until then `--yes` is refused on the
   PhysioNet-coded Sepsis header set even after a human accepts it (FA-N3, pinned).
2. (Build note 2, sharpened by FA-N1) `proofpack run` without `--yes` proceeds on the computed
   mapping and writes `mapping.json` (original headers, value summaries) into `./pack`. Should
   `run` require a confirmed `mapping.json`, and should the file live outside the pack directory?
3. Numeric min/max now withhold below the floor; date min/max stay `YYYY-MM` regardless of
   how many rows hold that month. Same rule for dates, or keep D1 section 1's coarsening alone?
4. `hadm_id`: a `case_id` synonym (MIMIC's admission key, so `subject_id` + `hadm_id` halts E01
   by name) or leave it to the `clustering.unit` declaration (as built)?

## 7. Open questions (at most five)

1. Date `min`/`max` through the floor (above).
2. `clustering.unit: subject_id` (one column, not in the enum) gives the generic H08 `enum`
   message with no fix line; worth a one-line special case in `_h08_from_schema_error`?
3. `_tolerant_console()` for `run` and `compare` needs a `main()` edit (outside today's scope).
4. The all-high prompt makes `map` always ask at least once at a terminal; is a `--accept-all`
   for a human at a console wanted, or is `--yes` with a prior file the only CI path (as D1 says)?
5. `patient-id` counting two tokens: acceptable, or should a lone hyphen between two tokens with
   no underscore be read as one name?

## 8. Re-run these (both shells, at `e92989b`, `PYTHONPATH` forced to the worktree's `src`, `PYTHONUTF8=1` for the map demo)

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| `python -c "import proofpack;print(proofpack.__file__)"` | `...\scratchpad\a-p1-r1\wt\src\proofpack\__init__.py` | same |
| `python -m pytest -q -p no:cacheprovider` | `505 passed, 1 skipped, 1 xfailed in 44.72s` | `505 passed, 1 skipped, 1 xfailed in 43.42s` |
| `python -m pytest -q -p no:cacheprovider -m day6` | `141 passed, 366 deselected in 2.50s` | `141 passed, 366 deselected in 2.54s` |
| `python -m ruff check .` / `python -m ruff format --check .` | `All checks passed!` / `59 files already formatted` | same |
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.` | same, exit 0 |
| `python scripts/mutation_sweep.py --marker day6` | `27 planted, 27 killed, 0 survived; 62 s` | not run in PowerShell |
| `python -m proofpack.cli map --input tests/fixtures/mapping/sepsis_2019.csv --out ../m.json < NUL` | exit 3; `'Age' -> age high float; 50 unique; 0.0% missing; min <suppressed> max <suppressed>; values: <suppressed> (50 distinct below k=10)` | not repeated (the day-6 regression lens measured byte parity of this table in both shells; the change here is the `min`/`max` text only) |
| pre-fix: copy `tests/test_mapping_repair1.py` into a worktree at `555a5e1`, `pytest -q tests/test_mapping_repair1.py --deselect tests/test_mapping_repair1.py::test_ctrl_c_at_the_prompt_is_h07` | `30 failed, 15 passed, 1 deselected in 1.06s`; the deselected test alone: `!!! KeyboardInterrupt !!!` | - |
