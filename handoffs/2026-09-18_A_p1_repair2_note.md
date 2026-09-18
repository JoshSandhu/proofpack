# Day 6 A - repair 2 for A-P1 the full mapper (18 September 2026)

Branch `a-p1-mapper`, one commit `ea526e363474bd1c96de3b893667457a5a766df0` on top of `e92989b`
(repair 1, on `555a5e1`, from `4eb44f3`). Not pushed, not merged. The main tree (`a5a5ed8`,
lane E) was read once with `git worktree list` and never checked out, stashed or committed in.

Worktrees: `scratchpad/a-p1-r2/wt` (the branch) and `scratchpad/a-p1-r2/tip` (detached at
`e92989b926dee377c1ae269f3aea162a94f5979b`, for the pre-fix failures). Both removed at the end;
the branch is the deliverable. `PYTHONPATH=<worktree>/src` on every run;
`python -c "import proofpack;print(proofpack.__file__)"` printed
`...\scratchpad\a-p1-r2\wt\src\proofpack\__init__.py` in Git Bash and in PowerShell 5.1 before
any figure below was taken (and `...\a-p1-r2\tip\src\proofpack\__init__.py` before the pre-fix
run).

## 0. Figures

| | Git Bash | PowerShell 5.1 |
|---|---|---|
| Suite at `e92989b` in the worktree before any edit | **506 passed, 1 skipped, 1 xfailed in 44.68s** | - |
| Suite at `ea526e3` | **528 passed, 1 skipped, 1 xfailed in 40.40s** | **528 passed, 1 skipped, 1 xfailed in 40.39s** |
| `-m day6` at `ea526e3` | **164 passed, 366 deselected in 2.47s** | **164 passed, 366 deselected in 2.42s** |
| `python -m ruff check .` / `ruff format --check .` | All checks passed! / 60 files already formatted | same |
| `python -m proofpack.cli doctor --offline` | All essential checks passed. (exit 0) | not repeated |
| `python scripts/mutation_sweep.py --marker day6` | **38 planted, 38 killed, 0 survived; 98 s** (was 27/27/0) | - |
| New tests against `e92989b` (file copied into the tip worktree, Ctrl-C test deselected) | **19 failed, 2 passed, 1 deselected in 0.66s**; the deselected one (`test_ctrl_c_during_load_is_h07_not_a_traceback`) run alone interrupts pytest itself: `!!! KeyboardInterrupt !!!` at `test_mapping_repair2.py:301`, `no tests ran in 0.48s` | - |

528 = 506 + 22: `tests/test_mapping_repair2.py` collects **22** items from **13** test functions
(13 - 2 parametrised + 5 + 6), measured with `--collect-only` and `grep -c '^def test_'`. 164 =
142 + 22. The two items that pass at `e92989b` are the two whose docstring begins "Pins" (the
lens-2 survivors M05 and M24).

Nothing weakened, measured: `git diff --name-status e92989b ea526e3 -- tests/` = 1 `M`
(`test_mapping_repair1.py`, its module docstring only), 1 `A`, **0 `D`**; added lines under
`tests/` matching `mark.skip|skipif|xfail|.only|pytest.skip|importorskip`: **0**; no marker
removed. `src/proofpack/stats/`, `schema/output_schema_v1.json`, `pyproject.toml`: **0 diff
lines**. `cli.py`: nine hunks inside `_confirm_interactive` and one inside `cmd_map`
(`git diff -U0` hunk headers all name those two functions); the `map` subparser, `main()`,
`cmd_run` and `cmd_compare` are unchanged.

Line endings: every tracked file I edited is `i/lf w/crlf` before and after (edits went
through `scratchpad/a-p1-r2/edit.py`, which normalises to LF, replaces exactly once, and writes
CRLF back). The new test file is `i/lf w/lf`. One heredoc collapsed backslashes in an edit
script (the known trap); that script was rewritten with the Write tool and re-run, the target
file untouched by the failed attempt (the helper exits before writing when the match count is
not 1).

The CLI on the sepsis fixture (`PYTHONUTF8=1`, stdin from `/dev/null`): exit 3, the same 3485
bytes lens 2 measured, `'Age' -> age high float; 50 unique; 0.0% missing; min <suppressed> max
<suppressed>; values: <suppressed> (50 distinct below k=10)`.

## 1. Findings -> fix -> test id -> first `E` line at `e92989b`

Every `E` line is the first one pytest printed for that test in the tip worktree, verbatim.
Tests are in `tests/test_mapping_repair2.py::` unless a path is given.

| Finding | Fix (module) | Test id | First `E` line at `e92989b` |
|---|---|---|---|
| FA-B1 (blocker, sentence) two partial-token `case_id` headers halt H07, not E01; the accept prompt takes both; `mapping.py` line 36 false | `io/mapping.py`: `apply_mapping` counts the columns whose role is `case_id` first and halts E01 `N columns are mapped to case_id (proofpack map: keep one, set the others to ignore); reduce your case key to one column`, detail `{"n_case_id_columns": N}` (other roles stay H07); the `case_id` partial branch now also appends `2 headers carry a token for case_id; choose one`. `cli.py` `_confirm_interactive`: an accept whose role is held by a settled entry (high, or answered earlier in the loop; entries still to be asked are not counted) is refused with `<role> is already held by '<original>': edit this one (e) to ignore or another role` and re-prompts; the edit check uses the same settled rule. Line 36 replaced by what `map_headers` and `apply_mapping` inspect, with the literal pairs. `errors.py` comment names `apply_mapping` as the third raiser; README step 3 likewise | `test_two_partial_case_id_headers_reach_e01_at_apply_not_h07` (`row_id,label,prob,patient_nbr,mrn_local` x 60: both low with the two notes; `apply_mapping` E01 with that message; `run` through `main()` with `clustering.unit: case_id` -> exit 3, first stderr line `HALT E01: ...`, no `H07`, no `Traceback`, no header, nothing written; a `--mapping` file holding both -> the same); `test_accept_of_a_second_holder_is_refused_at_the_prompt` (`a a e ignore` -> the one refusal line, 4 prompts, `holders("case_id") == ["patient_nbr"]`; `e ignore a` -> `["mrn_local"]`; `label` + `outcome` (two y_true name claims) the same way) | `AssertionError: patient_nbr` / `assert ['header rese...rm or ignore'] == ['header rese...; choose one']`; `assert [] == ['  case_id i...another role']` |
| FA-B1 mutant M05 unpinned (`c.source != "partial"`) | No behaviour change; pinned | `test_two_partial_case_id_tokens_are_not_counted_by_map_headers_e01` (`patient_weight` + `patient_height`: no halt, both `case_id low partial`; `patient_id` + `subject_id`: E01 `2 columns resolve to case_id; ...`) - **passes at `e92989b`**; kills `partial_case_id_tokens_counted_by_map_headers_e01` | - |
| RG-B1 (blocker, sentence) `Mapping.read` "any shape or I/O failure is H07"; `role: 123` / `["a"]` reach `run --yes` as exit 5 | `Mapping.read`: `role` must be a string or null, `value_summaries` a mapping or null (TypeError -> H07). Docstring replaced by the list of what is inspected and what is not (role names, confidence strings, notes, `decided_by`'s type) | `test_prior_with_a_non_string_role_halts_h07_under_run_yes_and_map_yes[123, ["a"], {"x": 1}, 1.5, True]` (`run --yes` and `map --yes`: exit 3, first line `HALT H07: mapping.json could not be read`, no `internal error`, file bytes unchanged, nothing written); `test_prior_with_a_string_value_summaries_halts_h07` (`"SECRET_STR"`: H07, the string absent from stderr; `null` still reads as `{}`) | `AssertionError: ['run', ...] assert 5 == 3` (all five); `assert (0 == 3)` |
| RG-N1 all-high prompt takes any non-`q` answer as accept | `_confirm_interactive`: the all-high prompt loops; `a`/`accept`/empty accept, `q`/`quit`/`abort` abort, anything else says `answer a or q` | `test_all_high_prompt_reprompts_on_anything_but_a_or_q` (`n no e x a` -> 5 identical prompts, 4 refusals, then `interactive`; `n q` -> H07 with `decided_by` still `proposed`) | `AssertionError: assert (1 == 5)` |
| FA-N5 edit accepts `attr_`, `rater_`, `attr_x y` | `_confirm_interactive`: an `attr_`/`rater_` edit must match `io.schema._IDENT` with a non-empty name after the prefix; the refusal line now ends `, or attr_<name> / rater_<name> in lower-case letters, digits and _` | `test_edit_prompt_refuses_bare_and_non_identifier_attr_names` (`attr_x y`, `attr_`, `rater_` refused, `attr_x_y` written; `Attr_X` is `attr_x` because `_ask` lower-cases; `rater_b2` written) | `assert (0 == 3)` |
| FA-N6 `--out` into a missing directory: exit 5 after the answers | `cmd_map`: `Path(args.out).resolve().parent.is_dir()` checked before the table and the prompts; H07 `the directory for --out does not exist: create it or pass --out inside an existing directory`, detail `{"out_dir_exists": false}` (no path in the message) | `test_out_into_a_missing_directory_halts_h07_before_any_prompt` (0 prompts consumed, stdout empty, that first line, `no_such_dir` absent from stderr; with the directory created the same command writes the file after 1 prompt) | `assert (5 == 3)` |
| FA-N10 Ctrl-C outside a prompt is a traceback | `cmd_map`: the body from `load_table` to the last prompt is inside `try`; `KeyboardInterrupt` -> H07 `mapping interrupted; nothing written`. `main()` untouched (outside today's cli scope), so `run`/`compare` are carried | `test_ctrl_c_during_load_is_h07_not_a_traceback` (`load_table` raising `KeyboardInterrupt`: exit 3, that first line, no `Traceback`, no file) | pytest itself interrupted (`!!! KeyboardInterrupt !!!`, `no tests ran in 0.48s`) |
| FA-N7 `Attr Site` + `attr_site` both high | `io/mapping.py`: `_single_holder(role)` = canonical roles plus any `attr_`/`rater_` prefix; `_decide_named` uses it, so the twins are both `low` with `2 headers claim attr_site; choose one` and reach the prompt | `test_attr_twins_are_low_with_the_note_and_reach_the_prompt` (both low with the note, `non_high` 2, `apply_mapping` H07 `{"role": "attr_site"}` on the unedited pair, `e ignore a` -> one holder and `apply_mapping` keys `["row_id", "y_true", "Attr Site", "attr_site"]`; `rater_a` + `Rater A` likewise; a lone `attr_site` stays high) | `AssertionError: Attr Site` / `assert ('attr_site', 'high', []) == ('attr_site',... choose one'])` |
| FA-N8 / RG-N3 `clustering.columns: "subject_id, hadm_id"` passes; `a AND b` counts 3 | `io/declare.py`: a string under one of the six list keys is split on `_CASE_KEY_SEPARATORS` and >= 2 tokens is E01 `clustering.<key> names N columns; ...`; the ` and ` alternative is `[Aa][Nn][Dd]` | `test_list_key_strings_and_upper_case_and_reach_e01[6 keys]` (the string -> E01 names 2 with `{"n_case_key_columns": 2, "key": <key>}`; a one-token string passes; `a AND b` and `a And b` -> names 2) | `Failed: DID NOT RAISE HaltError` (all six) |
| FA-N2 dotted, month-name dates pass H11 and print | `io/profile.py` `DATE_PATTERNS` gains `D.M.YYYY` and `D <English month name or 3-letter abbreviation> YYYY` (case-insensitive, the twelve names spelled out in `_MONTH_NAME`); `_date_key` reads both. Two-digit years stay `categorical` (carried: the century is a guess). README step 3's "date-like by header or by values" now lists the six shapes and names `3/17/24` as not among them | `test_dotted_and_month_name_dates_are_typed_date` (`15.03.2024/16.03.2024/02.11.2025` x 20 and `17 Mar 2024/18 March 2024/2 NOV 2025` x 20: `date`, `2024-03`..`2025-11`, no value in `to_dict()`, `event_date medium`, H11 `{"date_like_columns": 1}`; `3/17/24`, `17 Foo 2024`, `17 Mayhem 2024` x 60: `categorical` with the value listed at count 60) | `AssertionError: 15.03.2024` / `assert ('categorical' == 'date'` |
| FA-N1 hash reduced to the column count survives | No behaviour change; pinned | `test_header_rename_at_the_same_width_changes_the_hash_and_yes_refuses_the_prior` (`5fbb6eb2369b` vs `4916f8a0beca`; `score` -> `Score` on the seeded cohort: H07 `header-set hash differs ...`) - **passes at `e92989b`**; kills `hash_is_the_column_count` | - |
| FA-N11 / RG-N2 figures one below the tree; "three tests marked pins" | `tests/test_mapping_repair1.py` docstring: seven tests whose docstring begins "Pins"; this note's figures are the measured ones (section 0) | the docstring | - |

Sentences the lenses falsified, and what replaced them: `mapping.py` "Two headers resolving to
``case_id`` halt with E01 (DEC-11), not ``low``" -> the name-claim pair that halts in
`map_headers`, the token pair that is `low` with two notes and halts E01 in `apply_mapping`,
the pair that is the reason token claims are not counted, and the three test ids;
`Mapping.read` "any shape or I/O failure is H07" -> "Inspected, each failure H07 ...: [the
list]. Not inspected: [the list]" with both test ids. Also narrowed on my own: README step 4
"Ctrl-C anywhere in `map`" (my first draft) -> "between the table load and the last prompt (the
test raises it from `load_table` and at two prompts)".

### Counter-examples that FAILED first (the hard rule, applied to my own checks)

1. Before deciding against lens-2's M05 as the fix (E01 on token claims too), I fed
   `label,prob,patient_weight,patient_height` to `map_headers` at `e92989b`: both are
   `case_id low partial` (the `patient_` affix is stripped, `weight` is no synonym, the
   `patient` token remains). M05 would halt that table E01 with no case key in it. The E01
   moved to `apply_mapping` instead, and that table is the M05 pin.
2. `test_edit_prompt_refuses_bare_and_non_identifier_attr_names` first fed `Attr_X` expecting
   a refusal; `_ask` lower-cases every answer, so it was written as `attr_x` and the loop ended
   there (`assert (3 == 4)`). The test now states that rule.
3. My probe `p_b1.py` answered `a` to every prompt and looped forever at the refused second
   holder (killed by PID; the process list showed lane E's two processes untouched). A human
   sees the refusal line and types `e` or `q`; the per-role prompt already loops the same way
   on `x`. Recorded, not changed.
4. `scripts/mutation_sweep.py --marker day6` halted twice on the restructured `cmd_map` /
   `_confirm_interactive`: `tty_check_always_true` matched 0 times (the line is one indent
   deeper inside the `try`) and `held_role_edit_accepted` matched 2 times (`if holder is not
   None:` is now in the accept path too); both patterns now name their line.
5. A first draft of the month-name shape was `[A-Za-z]{3,9}`, which typed `17 Foo 2024` as a
   date with month `00`; the shape now spells out the twelve names, and `17 Foo 2024` /
   `17 Mayhem 2024` are asserted `categorical`.

## 2. Mutants

`scripts/mutation_sweep.py --marker day6` in the repaired tree: **38 planted, 38 killed, 0
survived; 98 s**. The eleven added for this repair (each killed; the sweep prints the failing
count per mutant):

| Mutant | What it changes |
|---|---|
| `apply_two_case_id_columns_h07_not_e01` | `n_case >= 3`: the pair through `run` is H07 again |
| `partial_case_id_tokens_counted_by_map_headers_e01` | lens-2 M05: `patient_weight` + `patient_height` halt E01 in `map_headers` |
| `accept_of_a_held_role_taken` | `a` at both `case_id` prompts writes two holders |
| `all_high_prompt_takes_any_answer` | `n` at the all-high prompt is an accept |
| `attr_twins_not_single_holder` | `Attr Site` + `attr_site` both high |
| `prior_role_type_unchecked` | `role: 123` reaches `run --yes` as exit 5 |
| `list_key_string_not_split` | `columns: "subject_id, hadm_id"` passes |
| `and_separator_lower_case_only` | `a AND b` counts three tokens |
| `dotted_date_shape_removed` | `15.03.2024` is categorical and passes H11 |
| `out_dir_check_off` | `--out` into a missing directory is exit 5 after the prompts |
| `hash_is_the_column_count` | lens-2 M24: a rename at the same width keeps the hash |

## 3. Carried, and why

| Finding | Why carried |
|---|---|
| FA-N3 / RG-N4: `proofpack run` without `--yes` writes `./pack/mapping.json` (`proposed`, original headers) and proceeds on `low` roles | `cmd_run` is outside today's cli scope (the `map` subparser and `cmd_map` only). Repair-1 needs-from-Josh 2. |
| FA-N4: `--yes` compares the hash only; a prior with `roles: []`, an `original` not in the header set, or an unknown role string at high is accepted by `map --yes` (`run --yes` then halts S01 or proceeds) | Hand-edited files only (lens: reachable=false). A header-set equality check in `check_h07` is a two-line addition; left for Josh's ruling on what `--yes` should re-verify beyond the hash (open question 1). |
| FA-N9: JSON loader (day 1) exit 5 on a scalar column, a lone surrogate in a header, 100,000 nested `[` | Day-1 `io/schema.py` loader, contrived inputs (lens: reachable=false); not touched today. |
| FA-N10, `run` / `compare` half: Ctrl-C during their load is still a traceback | Needs a `main()` edit (outside today's cli scope; repair-1 R1-D8). `map` is closed. |
| FA-N2, two-digit years (`3/17/24`) | The century (and D/M vs M/D) is a guess; the column stays `categorical` and, at >= 10 rows per value, lists the value. Pinned in the FA-N2 test so the shape is on file. |
| RG-N4: date `min`/`max` not put through the floor; `clustering.unit: subject_id` -> H08 `enum` with no fix line; `--yes` unreachable after a human accept on a non-high table | Repair-1 open question 1, open question 2 and needs-from-Josh 1; unchanged. |
| Ignored column whose original name equals a role another column holds (`attr_site` ignored beside `Attr Site` -> `attr_site`): `apply_mapping` H07 `{"role": "attr_site"}` | Found while writing the FA-N7 test (the test ignores `Attr Site` instead). Day-1 rename rule ("ignored columns keep their name"); a typed halt, not a traceback. Open question 3. |
| An `ask` that answers `a` at a refused second holder loops | A human reads the refusal and answers `e` or `q`; the same loop exists for `x` at every prompt. |
| mintty behaviour of `_stdin_is_terminal` | Not measured (no mintty); the docstring says so. |

## 4. Decisions taken

| id | Decision |
|---|---|
| R2-D1 | DEC-11 by mapping: two columns on `case_id` reaching `apply_mapping` halt E01 (message ending the DEC-11 sentence, with the `proofpack map` fix in parentheses before it); two columns on any other role stay H07. `map_headers` still counts name claims only, because `patient_weight` + `patient_height` carry the token and no key. |
| R2-D2 | The prompt's held-role check (accept and edit) counts entries already settled: high ones and those answered earlier in the loop. Entries still to be asked are not counted, so the first of two low holders can be accepted and the second must be edited. |
| R2-D3 | `attr_*` / `rater_*` are single-holder roles for the name-claim conflict (`_single_holder`); `SINGLE_HOLDER_ROLES` itself is unchanged. |
| R2-D4 | `Mapping.read` checks types (`role` string or null, `value_summaries` mapping or null) and nothing about role names; the docstring lists both sides. |
| R2-D5 | The all-high prompt takes `a`/`accept`/empty and `q`/`quit`/`abort` only. |
| R2-D6 | An edited `attr_`/`rater_` name must match `_IDENT` with a non-empty name after the prefix (the schema's own rule, so `validate` keeps it). |
| R2-D7 | `--out`'s directory is checked before the table and the prompts; the H07 message carries no path (detail `{"out_dir_exists": false}`). |
| R2-D8 | Ctrl-C inside `cmd_map` (from `load_table` to the last prompt) is H07 `mapping interrupted; nothing written`; `main()` untouched. |
| R2-D9 | A string under a `clustering` list key is split like `unit`; ` and ` matches any case. |
| R2-D10 | Date shapes: `D.M.YYYY` and `D <English month> YYYY` added; two-digit years not. |
| R2-D11 | The eleven repair gates go into the committed sweep (as repair 1 did for its ten). |

## 5. Sentences refused

1. "Two columns on case_id can no longer reach the pack" - not written; `apply_mapping`'s
   docstring names the pair and the test, and `map_headers`'s says token claims are not counted
   and why.
2. "The prompt never writes two holders of one role" - not written; the docstring says which
   entries the check counts (settled ones) and which it does not (still to be asked), and the
   test feeds `a a e ignore` and `e ignore a` on one pair.
3. "Every malformed mapping.json is H07" - not written (the lens-2 blocker was this sentence's
   sibling); `Mapping.read` lists what it inspects and what it does not.
4. "The E01 gate is complete" / "DEC-11 is closed" - not written; three raisers are named in
   `errors.py` with the shapes each inspects.
5. "`map` handles Ctrl-C" - not written; the README names the span (`load_table` to the last
   prompt) and the three raise points the tests feed; `run`/`compare` carried.
6. "The profiler recognises German/Swiss dates" - not written; the six literal shapes are listed
   and `3/17/24` is named as outside them.
7. "The hash is now pinned against any weakening" - not written; the test feeds one rename at
   one width and one reorder.
8. "`--out` errors are handled" - not written; the check is `parent.is_dir()` before the prompts,
   and the test feeds one missing directory.
9. "attr_/rater_ names are validated" - not written; the rule is `_IDENT` plus a non-empty
   suffix, and the test feeds five literal answers.
10. "The all-high prompt is safe against a stray key" - not written; five literal answers.

## 6. Needs from Josh

1. (Repair-1 note 2, again) Should `proofpack run` require a confirmed `mapping.json`, and
   should the file live outside the pack directory? Until then FA-N3 stands.
2. Should `--yes` re-verify the prior beyond the hash and `decided_by` (originals equal the
   header set; role names in the canonical list or `attr_`/`rater_`)? Two lines each; FA-N4.
3. (Repair-1 notes 1, 3, 4 stand: `sex` 0/1 at high; date min/max through the floor; `hadm_id`
   as a `case_id` synonym.)

## 7. Open questions (at most five)

1. FA-N4's header-set check in `check_h07` (above).
2. `clustering.unit: subject_id` (one token, not in the enum) still gives the generic H08 `enum`
   message with no fix line (repair-1 open question 2).
3. An ignored column whose original name equals a role another column holds halts H07 at
   `apply_mapping` (section 3); should ignored columns be renamed on collision, or should the
   prompt refuse that shape?
4. `_tolerant_console()` and the Ctrl-C mapping for `run` and `compare` need a `main()` edit.
5. Two-digit-year dates: leave as `categorical`, or add the shape with a stated century rule?

## 8. Re-run these (both shells, at `ea526e3`, `PYTHONPATH` forced to the worktree's `src`, `PYTHONUTF8=1` for the map demo)

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| `python -c "import proofpack;print(proofpack.__file__)"` | `...\scratchpad\a-p1-r2\wt\src\proofpack\__init__.py` | same |
| `python -m pytest -q -p no:cacheprovider` | `528 passed, 1 skipped, 1 xfailed in 40.40s` | `528 passed, 1 skipped, 1 xfailed in 40.39s` |
| `python -m pytest -q -p no:cacheprovider -m day6` | `164 passed, 366 deselected in 2.47s` | `164 passed, 366 deselected in 2.42s` |
| `python -m ruff check .` / `python -m ruff format --check .` | `All checks passed!` / `60 files already formatted` | same |
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.` (exit 0) | not repeated |
| `python scripts/mutation_sweep.py --marker day6` | `38 planted, 38 killed, 0 survived; 98 s` | not run in PowerShell |
| `python -m proofpack.cli map --input tests/fixtures/mapping/sepsis_2019.csv --out ../m.json < /dev/null` | exit 3; 3485 bytes; the `'Age'` line as in repair 1 | not repeated (repair 1 and lens 2 measured byte parity; nothing in this repair touches the table text) |
| pre-fix: copy `tests/test_mapping_repair2.py` into a worktree at `e92989b`, `pytest -q tests/test_mapping_repair2.py --deselect tests/test_mapping_repair2.py::test_ctrl_c_during_load_is_h07_not_a_traceback` | `19 failed, 2 passed, 1 deselected in 0.66s`; the deselected test alone: `!!! KeyboardInterrupt !!!` | - |
