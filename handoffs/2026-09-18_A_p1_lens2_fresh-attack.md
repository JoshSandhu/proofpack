# Lens 2 (fresh attack) - lane A day 6, A-P1 the full mapper, after repair 1

Branch `a-p1-mapper` at `e92989b` (repair 1, on `555a5e1`, from `4eb44f3`), probed in a detached
worktree `scratchpad/lens-a-p1-r2-fresh-attack/e92989b` (a second detached worktree at `4eb44f3`
was added and not needed). `PYTHONPATH` forced to that worktree's `src`;
`python -c "import proofpack;print(proofpack.__file__)"` printed
`...\lens-a-p1-r2-fresh-attack\e92989b\src\proofpack\__init__.py` before any figure below was
taken. Git Bash only. Nothing committed; the main tree (`b93e050`, lane E) was read once with
`git worktree list` and never touched; both worktrees are removed at the end.

## Verdict: FAIL (1 blocker, reachable from `proofpack run` and from `proofpack map` at a terminal; it also falsifies a shipped sentence)

## Blockers

### B1. Two headers the mapper itself resolves to `case_id` (by partial token) halt H07, not the DEC-11 E01

Table `row_id,label,prob,patient_nbr,mrn_local` (60 rows; `patient_nbr` repeats every three rows,
`mrn_local` every two). `proofpack map` prints

```
'patient_nbr' -> case_id  low   ...  note: header resembles a case identifier; confirm or ignore
'mrn_local'   -> case_id  low   ...  note: header resembles a case identifier; confirm or ignore
```

- `proofpack run --input two_partials.csv --criteria crit.yaml --out pack` (no prior, no `--yes`):
  exit 3, `HALT H07: two columns map to the same canonical role`, `detail: {"role": "case_id"}`.
  Not E01, and the message does not end `reduce your case key to one column`.
- `proofpack map` at a terminal, answer `a` to both prompts: exit 0, `mapping.json` written with
  two `case_id` holders (`decided_by: interactive`); `proofpack run --mapping` on it: the same H07.
- Neither prompt says a second header carries the token: the `case_id` branch in `map_headers`
  returns before the `"{n} headers carry a token for {role}; choose one"` note is added (the
  note the `age` pair gets in `test_two_partial_tokens_for_one_role_are_both_low_with_the_note`).
- The accept path of `_confirm_interactive` has no held-role check (repair 1 added one to the
  edit path only), so a human can confirm two columns into one single-holder role.

Shipped sentence falsified: `src/proofpack/io/mapping.py` line 36, "Two headers resolving to
``case_id`` halt with E01 (DEC-11), not ``low``." - the two headers above resolve to `case_id`
and are both `low`. (`errors.py` line 47 and README step 3 say "by name", which the code's
comment at line 573 defines as excluding partial tokens; line 36 carries no such qualifier.)

Mutant M05 (E01 counts partial-token `case_id` claims too, i.e. the `and c.source != "partial"`
clause removed) SURVIVED `-m day6` (142 passed): no test pins the exclusion either way, so the
repair is free of test conflicts. The build's D6 reading ("E01 on name claims only") was taken to
keep MIMIC's `subject_id` + `hadm_id` out of E01; two partial tokens are a different pair.

Repro: `PYTHONPATH=<wt>/src python -m proofpack.cli run --input <the csv above> --criteria <any
valid criteria.yaml with clustering.unit: case_id> --out pack < NUL` -> exit 3, first stderr line
`HALT H07: two columns map to the same canonical role`.

## Non-blocking

N1. **`header_set_sha256` reduced to the column count survives the full suite.** Mutant M24
(`joined = str(len(headers))` in `io/schema.py`) -> `496 passed, 1 xfailed` with
`tests/test_doctor_cli.py` ignored (it inspects the package location, not the hash). The two
hash-mismatch tests (`test_yes_with_a_prior_whose_hash_differs_halts_h07`,
`test_halt_gates.py::test_h07_rejects_yes_when_headers_change`) both add an `extra` column; no
test renames one header at the same width and asserts the hash changes or that `--yes` refuses
the prior. The code is right (measured: renaming `label` to `Label2` changes the hash); the
`--yes` rule of D1 step 3 rests on this function and nothing pins it. Not reachable as a defect.

N2. **Dotted, two-digit-year and month-name dates named `visit` pass H11 and, at >= 10 rows per
date, print.** `visit` holding `15.03.2024` x 60 -> `ignore high; categorical; values:
15.03.2024 (60)` in the table, in `--json-log` stdout and in `mapping.json`; no H11. `visit` of
53 distinct `DD.MM.2024` values -> `values not shown (free text)`, no H11. `3/17/24` and
`17 Mar 2024` likewise. ISO `2024-03-15` and the repair's `15-03-2024` halt H11 (measured). The
value is an aggregate (count 60 >= k), so no rule of the task is broken; README step 3 "H11 when a
column is date-like by header or by values" reads wider than the four `DATE_PATTERNS` to a
customer whose export is German/Swiss. Same class as lens-1 N7; the repair closed one shape.

N3. **`proofpack run` without `--yes` still writes `./pack/mapping.json`** (`decided_by:
proposed`, original headers, value summaries) and proceeds on `low` roles (`patient` ->
`case_id low` on `sepsis_2019_gender_mf.csv`, exit 0). Carried by the repair (outside today's
cli scope); the `--yes` half is closed (`map --yes` on that file: H07 "was not confirmed").

N4. **`--yes` compares only the hash, never the prior's `original` names or `role` strings.**
Priors with a matching hash and `decided_by: file`: `roles: []` -> exit 0 and the file is
rewritten with `roles: []` ("every role is high" is vacuously true); `original: NOT_A_HEADER`
-> exit 0; `role: SECRET_ROLE_NAME` at high -> exit 0; `run --yes` on the last two then halts
`S01 required column role 'y_true' is missing`. Hand-edited files only.

N5. **The edit prompt accepts `attr_`, `rater_` (bare prefix) and `attr_x y`.** `validate()`
later keeps `attr_` (matches `_IDENT`) and drops `attr_x y` into `unused_columns` silently.

N6. **`--out` into a directory that does not exist, after the prompts are answered:** exit 5
`internal error: FileNotFoundError: [Errno 2] No such file or directory: '<path>'`; the answers
are lost. Not a traceback; a customer mistake reported as internal.

N7. **`Attr Site` beside `attr_site`** -> both `attr_site high`, `non_high_roles: 0`, the
all-high prompt, file written; `run` halts H07 `{"role": "attr_site"}`. `attr_*` roles are not in
`SINGLE_HOLDER_ROLES`.

N8. **`clustering.columns: "subject_id, hadm_id"` (a string)** passes `validate_dict` silently
(`_CASE_KEY_LIST_KEYS` read lists only); `unit: ["subject_id/hadm_id"]` -> H08 `type`, not E01.

N9. **JSON loader (day 1):** `{"columns": {"label": 5}}` -> exit 5 `TypeError: object of type
'int' has no len()`; a header written `"lab\udce9el"` -> exit 5 `UnicodeEncodeError ...
'\udce9'` (one character of the header in the message); 100,000 nested `[` -> exit 5
`RecursionError`. Contrived inputs.

N10. **Ctrl-C outside a prompt** (raised from `load_table`) propagates out of `main()` -
`KeyboardInterrupt` is a `BaseException`, the catch-all is `Exception`. A traceback at a console
during a long load; not a halt.

N11. **Figures:** the suite at `e92989b` is `506 passed, 1 skipped, 1 xfailed in 47.22s` and
`-m day6` is `142 passed, 366 deselected`; the repair note says 505 / 141 ("46 - 1" - the
46 items of `test_mapping_repair1.py` all collect). `ruff check` / `format --check`: clean, 59
files. `git diff 4eb44f3 e92989b -- src/proofpack/stats schema pyproject.toml`: 0 lines.
`tests/`: no `D`, no skip/xfail/only added. `cli.py` diff: `import os`, the `map` subparser's
help strings, and the block from `_stdin_is_terminal` to the end of `cmd_map`.

N12. Observation, D1 design: a two-unique column prints `0 (41), <suppressed> (1 distinct below
k=10)` with `n_sampled` 50, so the suppressed value's row count (9) is derivable; the value is not.

## Mutants (24 planted in a copy of `src`, one literal edit each, `-m day6` from the worktree)

22 killed, 2 SURVIVED (M05 -> B1; M24 -> N1, also against the full suite). Killed, with the
first failing test: M01 min/max floor `>= K-1` (`test_two_unique_split_is_suppressed_the_same_way`);
M02 top-list floor `>` (`test_suppression_floor_count_nine_is_suppressed_and_count_ten_is_shown`);
M03 sample 10,001 (`test_sample_boundary_row_10001_does_not_reach_the_summary`); M04 E01 at
three claims (`[sepsis_two_case_ids]`); M06 `decided_by` check off (`test_yes_refuses_a_proposed_prior`);
M07 fresh all-high check off (`test_yes_is_refused_when_the_fresh_mapping_has_a_medium_...`);
M08 `GetConsoleMode` ignored (`test_cp1252_stdout_prints_the_table_with_escapes`); M09 dash date
shape removed (`test_dash_separated_dates_...`); M10 sex 1/2 consistent (`[sepsis_sex_12]`);
M11 repeating int column -> `case_id` by values (`[diabetes_130]`); M12 free-text guard off
(`test_free_text_column_with_thirty_distinct_values_shows_none_of_them`); M13 separators reverted
to five (`test_separators_the_lens_listed_reach_e01[patient_id/study_id-2]`); M14 all-high prompt
removed (`test_all_high_table_asks_once_before_interactive`); M15 hash-type check removed
(`test_malformed_prior_under_yes_halts_h07_not_exit_5[prior2]`); M16 `fold_header` without NFC
(`[sepsis_nfc_nfd_twins]`); M17 `n_suppressed` counts `<= K` (the count-nine/ten test); M18 label
conflict at 11 (`test_label_with_ten_distinct_values_...`); M19 file written before the `--yes`
check (`test_yes_without_a_prior_mapping_halts_h07`); M20 `_tolerant_console` removed (the cp1252
test); M21 date min/max not coarsened (`test_date_column_lists_no_values_and_coarsens_min_max_to_month`);
M22 `--yes` without a prior accepted (`test_yes_without_a_prior_mapping_halts_h07`); M23 accept
leaves `decided_by: proposed` (`test_tty_prompt_accept_edit_and_abort`).

## What could not be broken (what was tried)

- (a) **Row-level values in a printed line, a halt, a log.** 57 hostile files through
  `proofpack map` as subprocesses with `stdin=DEVNULL` (NFC/NFD `Température` twins -> H07
  `n_duplicate_headers`; `la<ZWSP>bel` beside `label` -> ignore high with the note, alone ->
  `y_true medium` by values; a leading BOM and a mid-header BOM; `Label ` beside `Label` -> S04
  duplicate; `LABEL`/`label` -> H07; `pred-prob`/`pred.prob` -> both `score low`; `score` of 0/1
  -> low "only 0/1"; `label` of floats -> low "continuous (60 unique floats)"; `patient_nbr` +
  `encounter_id` -> `case_id low` + `row_id medium`; `subject_id` + `hadm_id` -> high + `row_id
  medium`; 10,001 rows with `SECRET_ROW_10001_MRN` in row 10,001 -> `n_sampled` 10000, the string
  nowhere; 200 free-text notes -> `values not shown`; `visit` ISO -> H11; Excel serials -> `int`,
  ignore with the row_id note; 0-row, header-only-no-EOL, 0-byte (S04), blank first line (S04),
  one 5 MB cell (S04 `Error`), 700,000-row single column (0.76 s, `9992 unique`, extremes
  suppressed); latin-1 and UTF-16 (S04 `UnicodeDecodeError`); tab- and pipe-separated; a quoted
  newline in a header; a ragged row; a NUL byte; six JSON shapes; a directory and a missing file
  as `--input`; `٣٤` (Arabic-Indic digits, `int`, `min 34`); `1e400` (`min inf`); `-0`; sex
  1/2, 0/1 and mixed `1/2/M`; a 5,000-character header; 2,002 columns; all-`NA`; blank-only rows;
  CR-only and LF-only endings; an empty header name beside a second empty name -> S04). Every
  stderr line carried counts, 12-character hash prefixes or canonical names only; no
  `Traceback`; every run ended within 0.8 s. The three stdout hits of `SECRET` were a header (the
  table prints headers by design) and two cells held by 60 rows.
- (h) **Floor boundaries, both extremes and the list.** `["100"]*41+["7"]*9` -> `min
  <suppressed> max 100`; `*40 + *10` -> `min 7`; `["7"]*41+["100"]*9` -> `max <suppressed>`;
  `"1"x5 + "1.0"x4` (9 parse-equal rows) -> suppressed, `x5 + x5` -> `min 1`; `"007"x9 + "7"x1`
  -> `min 7` (10 rows hold the number 7 - the documented row-count rule); `"A"x9` -> suppressed,
  `x10` -> shown; three values of 9 -> `<suppressed> (3 distinct below k=10)`; one value x9 vs
  x10; the committed fixtures `diabetes_130.encounter_id`/`patient_nbr`, `mimic_iv_demo.hadm_id`,
  `sepsis_2019.Age`/`HospAdmTime` all `min <suppressed> max <suppressed>` (lens-1 B1 closed).
  Egress: a site held by 9 rows absent from the interactive `mapping.json`, `--json-log` stdout,
  `./pack/mapping.json` and `ingest_report.json`; held by 10 rows present in the first three.
- (b)/(g) **Declarations inferred; sex 1/2 guessed.** `sex` 1/2 -> `medium`, note `no
  dictionary declared for 1/2`, values stay `1`/`2`; 0/1 the same; `1/2/M` -> `medium`, "confirm
  the coding". `cmd_map` reads `criteria.yaml` for `period` only; no write of positive class,
  orientation, threshold, reference type or clustering in the diff. M10 killed.
- (c) **`--yes`.** `run` writes `proposed`; `map --yes` on it -> H07 "was not confirmed"
  (lens-1 N1's `--yes` half closed). `decided_by` `INTERACTIVE`, `Interactive`, `interactive `,
  `5`, `["interactive"]` -> H07; `file` and absent -> accepted. A prior at high with the fresh
  mapping `low` -> H07 "computed from this table". M06, M07, M19, M22 killed.
- (d) **Composite key by declaration.** Fourteen `clustering.unit` shapes (` / `, `/`, `:`,
  `-`, space, tab, ` and `, `, `, `+`, `&`, `;`, `|`, a two-item list, the same name twice) ->
  E01 ending `reduce your case key to one column`; `subject_id/hadm_id` through `map` and `run`
  via `main()`: exit 3, that first line, no traceback (lens-1 B2 closed). M04, M13 killed. The
  gap is B1 (by header, not by declaration).
- (e)/(j) **Tracebacks; closed stdin.** None of the 57 files; EOF and Ctrl-C at the two prompt
  kinds are the committed tests (run in the suite); a pipe on stdin halts before any read
  (`_stdin_is_terminal` false).
- (f) `_value_candidate` has no `case_id` outcome (read); M11 (repeating int -> `case_id`)
  killed by `[diabetes_130]`.
- (i) `column[:10_000]`; M03 killed; 10,001-row files measured `n_sampled 10000`.
- (k) The fixture test asserts `_roles(m) == spec["roles"]` exactly plus note fragments;
  `make_mapping_fixtures.py` imports `csv`, `json`, `unicodedata`, `numpy` and nothing from
  `proofpack`; `sepsis_sex_12` expects `medium` + the 1/2 note, `sepsis_two_case_ids` and
  `mimic_composite_key` expect E01 ending with the sentence. M04, M10, M11, M16 each killed by a
  fixture row.
- (l) `src/proofpack/stats`, `schema/output_schema_v1.json`, `pyproject.toml`: 0 diff lines.
- Lens-1 N5-N8 closures: the repair-1 tests for them pass in this run; N8 re-measured as a
  subprocess (`PYTHONIOENCODING=cp1252`, `PYTHONUTF8` unset, header `体温`: exit 3, table
  printed, no `UnicodeEncodeError`); N7's dash shape halts H11 (M09 killed).

## What I could not check

- PowerShell 5.1 parity (Git Bash only this session) and a human at a real console; the prompt
  path was driven by an injected `input` and a patched `_stdin_is_terminal`.
- mintty behaviour of `_stdin_is_terminal` (none here).
- The E7 manifest hash of `mapping.json` (E7 not built).
- Real PhysioNet / UCI / MIMIC exports (offline; the fixtures carry header sets only).

## Sentences refused in this note

"E01 now fires for every composite key" (only the fourteen declaration shapes and one header
pair were fed); "the floor cannot leak" (nine literal columns and one egress table were
inspected); "no halt carries a value" (57 files, the tokens listed); "H11 misses non-ISO dates"
(four literal shapes were fed, two halt); "the hash is untested" (two tests feed a width change;
none feeds a rename).
