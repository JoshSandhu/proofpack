# Lens 3 (regression and record) - A-P1 repair 2, branch `a-p1-mapper` at `ea526e3` (pre `e92989b`)

**Verdict: FAIL - one blocker, a shipped sentence.** Every figure in the repair-2 note re-measures exactly in both shells (528 passed / 1 skipped / 1 xfailed; 164 day6; ruff clean on 60 files; doctor exit 0; 38 mutants planted and 38 killed; the sepsis table 3485 bytes and byte-identical across shells), the 19 pre-fix failures fail on the assertions the note quotes, lane E's files are untouched, nothing in `tests/` is weakened, every lens-2 blocker and non-blocking item the note says it closed is closed on re-run, and the carried list matches measurement. The blocker is one sentence added to `Mapping.read`'s rewritten docstring - "A non-mapping file or a non-list ``roles`` raises AttributeError/TypeError on its own and is caught the same way" - which a run counter-example falsifies: a prior whose `roles` is `{}` or `""` passes `Mapping.read` with an empty role list, and `map --yes` then exits 0 and rewrites the file. It is the same docstring, and the same defect class, as lens-2 B1; the note records no counter-example for it.

Worktrees: `scratchpad/lens-a-p1-r3-regression/wt` (detached at `ea526e363474bd1c96de3b893667457a5a766df0`) and `.../tip` (detached at `e92989b926dee377c1ae269f3aea162a94f5979b`), both removed at the end. The main tree (`a5a5ed8`, lane E) was read once with `git worktree list` and never checked out, stashed or committed in. Nothing committed anywhere; `git status --short` in `wt` was empty after every probe.

`PYTHONPATH` proof, run before any figure in each shell:

| shell | worktree | `python -c "import proofpack;print(proofpack.__file__)"` |
|---|---|---|
| Git Bash, no `PYTHONPATH` (the trap, measured) | wt | `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py` - lane E's tree |
| Git Bash | wt | `...\lens-a-p1-r3-regression\wt\src\proofpack\__init__.py` |
| Git Bash | tip | `...\lens-a-p1-r3-regression\tip\src\proofpack\__init__.py` |
| PowerShell 5.1 | wt | `...\lens-a-p1-r3-regression\wt\src\proofpack\__init__.py` |

## Blockers

### B1. `Mapping.read`'s new docstring says a non-list `roles` raises on its own; `roles: {}` and `roles: ""` read as an empty role list and `map --yes` accepts the file

Repro (worktree at `ea526e3`, `PYTHONPATH` forced, `tests/` on `sys.path` for `conftest`): write a confirmed prior for `make_cohort()` (`decided_by: file`, matching hash), set `"roles": {}`, then
`proofpack map --input t.csv --out m.json --yes` -> **exit 0**, no stderr, the file rewritten with `roles: []` and `decided_by: file`; `proofpack run --input t.csv --criteria c.yaml --mapping m.json --out p --yes` -> **exit 0** (the cohort's headers are already canonical, so an empty mapping renames nothing). `"roles": ""` behaves the same. Direct: `Mapping.read` on `{}` -> `roles=[]`, `all_high=True`; on `""` -> the same; on `()` (not JSON) the same. The shapes that do raise and are caught: `5`, `0`, `false`, `null`, `"x"`, `{"a": 1}`, `[[]]`, `["x"]`, `[null]`; a non-mapping file `[]`, `"x"`, `5`, `null`, `true`, `[1]`, `{"a": 1}` -> H07 `could not be read` (all measured).

Why it blocks: `src/proofpack/io/mapping.py`, the `Mapping.read` docstring rewritten in this diff (added lines), reads "``roles`` iterates and each entry is a mapping with ..." (true - a dict and a string iterate) and then "A non-mapping file or a non-list ``roles`` raises AttributeError/TypeError on its own and is caught the same way." The second sentence generalises over the class "non-list `roles`"; two members of the class (`{}`, `""`) raise nothing, pass the check, and reach `--yes`. The hard rule of the day: a sentence asserting what a check guarantees must have a run counter-example recorded; the note's section 1 records the `role` and `value_summaries` counter-examples and none for this sentence, and lens 2's B1 was this docstring's previous generalising sentence. The code consequence is the carried FA-N4 shape (`roles: []` -> "every role is high" vacuously true; hand-edited files only, reachable=false), so the code half is not new; the sentence half is. Fix: either narrow the sentence to the shapes measured (`5`, `"x"`, `{"a": 1}` raise; `{}` and `""` iterate as empty), or add `if not isinstance(data["roles"], list): raise TypeError("roles")` (one line, H07 through the existing `except`) with a test feeding `{}` and `""` through `map --yes` asserting exit 3 and the bytes unchanged - and record the counter-example either way.

## Measured against the note (both shells, `PYTHONPATH` forced to the worktree's `src`)

| command | note says | Git Bash (measured) | PowerShell 5.1 (measured) |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | 528 passed, 1 skipped, 1 xfailed in 40.40s / 40.39s | **528 passed, 1 skipped, 1 xfailed in 48.51s** | **528 passed, 1 skipped, 1 xfailed in 44.07s** |
| `... -m day6` | 164 passed, 366 deselected | **164 passed, 366 deselected in 2.65s** | **164 passed, 366 deselected in 3.17s** |
| `python -m ruff check .` | All checks passed! | same | same |
| `python -m ruff format --check .` | 60 files already formatted | same | same |
| `python -m proofpack.cli doctor --offline` | All essential checks passed. (exit 0) | same, `rc=0` | same, `rc=0` |
| `python scripts/mutation_sweep.py --marker day6` | 38 planted, 38 killed, 0 survived; 98 s | **38 planted, 38 killed, 0 survived; 100 s** | **38 planted, 38 killed, 0 survived; 96 s** (the note did not run it in PowerShell) |
| new tests at `e92989b` (file copied into the tip worktree, Ctrl-C test deselected) | 19 failed, 2 passed, 1 deselected in 0.66s | **19 failed, 2 passed, 1 deselected in 0.78s** | - |
| the Ctrl-C test alone at `e92989b` | `!!! KeyboardInterrupt !!!` at `:301`, no tests ran in 0.48s | `!!! KeyboardInterrupt !!!` at `test_mapping_repair2.py:301`, `no tests ran in 0.51s`, rc 2 | - |
| `map --input tests/fixtures/mapping/sepsis_2019.csv --out ../m.json < /dev/null` (`PYTHONUTF8=1`) | exit 3; 3485 bytes; the `'Age'` line | exit 3, 3485 bytes, no file written; line 15 `'Age' -> age high float; 50 unique; 0.0% missing; min <suppressed> max <suppressed>; values: <suppressed> (50 distinct below k=10)` | exit 3, 3485 bytes, `Get-FileHash` equal to the Git Bash capture, no file |

Collected: `tests/test_mapping_repair2.py` = **22** items from **13** `def test_` (13 - 2 parametrised + 5 + 6); `test_mapping_repair1.py` = 46 items from 23 functions; `"""Pins` occurs 7 times in repair1 and 2 in repair2. 528 = 506 + 22 and 164 = 142 + 22, as the note says. The two items that pass at `e92989b` are `test_two_partial_case_id_tokens_are_not_counted_by_map_headers_e01` and `test_header_rename_at_the_same_width_changes_the_hash_and_yes_refuses_the_prior` - the two "Pins".

## Pre-fix failures (the tip worktree, first `E` line per test, all matching the note verbatim)

`AssertionError: patient_nbr` / `assert ['header rese...rm or ignore'] == ['header rese...; choose one']` (FA-B1 apply); `assert [] == ['  case_id i...another role']` (FA-B1 prompt); `AssertionError: Attr Site` / `assert ('attr_site', 'high', []) == ('attr_site',... choose one'])` (FA-N7); `AssertionError: assert (1 == 5)` (RG-N1); `assert (0 == 3)` (FA-N5); `assert (5 == 3)` (FA-N6); `AssertionError: ['run', ...] assert 5 == 3` x5 (RG-B1); `assert (0 == 3)` (value_summaries); `Failed: DID NOT RAISE HaltError` x6 (FA-N8); `AssertionError: 15.03.2024` / `assert ('categorical' == 'date'` (FA-N2). None aborts on an import or attribute error.

## Diff checks

- `git diff --name-status e92989b ea526e3 -- tests/` -> `M tests/test_mapping_repair1.py`, `A tests/test_mapping_repair2.py`; **0 `D`**. Deleted lines under `tests/`: the two module-docstring lines the note names ("three tests marked "pins" ..."). Added test lines matching `mark.skip|skipif|xfail|.only|pytest.skip|importorskip`: **0**. `pytest.mark` / `pytestmark` lines removed anywhere in the diff: **0**.
- `git diff --name-status e92989b ea526e3 -- src/proofpack/stats schema/output_schema_v1.json pyproject.toml` -> **empty**.
- `cli.py`: `git diff -U0` hunk headers - nine name `_confirm_interactive`, one names `cmd_map`; none names the `map` subparser, `main()`, `cmd_run` or `cmd_compare`.
- Nine files, +758/-78, as the note says. All nine `i/lf w/crlf` in this fresh checkout (the note's "new test file is `i/lf w/lf`" describes the builder's worktree; the index is LF, which is what merges).

## Lens-2 blockers and findings: closed or not (measured at `ea526e3`)

| lens-2 item | status |
|---|---|
| B1 (FA-B1) two partial `case_id` headers H07 not E01; accept takes both | **closed**: `run` on `row_id,label,prob,patient_nbr,mrn_local` x60 with `clustering.unit: case_id` -> exit 3, `HALT E01: 2 columns are mapped to case_id (proofpack map: keep one, set the others to ignore); reduce your case key to one column`; no `H07`, no `Traceback`, neither header in stderr, no pack directory; a prior holding both -> the same E01; `map --yes` on that prior -> H07 "requires every mapped role at high"; the non-tty table carries `note: 2 headers carry a token for case_id; choose one` on both rows; `--json-log` on the E01 path: 0 stdout lines. Prompt: `a a e ignore` -> one refusal, `holders("case_id") == ["patient_nbr"]`; three `y_true` claims `a a a` -> two refusals, one holder; `e y_pred` on the first then `e y_pred` on the second -> refused ("already held by 'label'"), and `apply_mapping` passes after `e ignore a` |
| RG-B1 `role: 123` / `["a"]` exit 5 under `run --yes` | **closed** for `123`, `["a"]`, `{"x": 1}`, `1.5`, `true`: `run --yes` and `map --yes` exit 3 `HALT H07: mapping.json could not be read`, bytes unchanged, no `internal error`; `role: null` still reads (an ignore); `role: ""` reads (harmless: `role_of` returns `""`, falsy, the original name is kept). `value_summaries: "SECRET_STR"` -> H07 under both, the string absent from stdout and stderr |
| N1 hash pin | closed (`5fbb6eb2369b` / `4916f8a0beca`; mutant `hash_is_the_column_count` killed, 1 failed / 163 passed) |
| N2 dotted / month-name dates | closed for the six shapes: `15.03.2024`, `17 Mar 2024`, `17 Sept 2024`, `17 sept 2024`, `17  Mar  2024` -> `date`, month min/max, values not shown. Outside them, as the README now says: `3/17/24`, `17-Mar-2024`, `1st Mar 2024`, `Mar 17 2024`, `2024.03.17`, `17 Marc 2024`, `17 Ma 2024` -> `categorical`, the value listed at count 20 |
| N5 `attr_` / `attr_x y` | closed (three refusals, `attr_x_y` and `rater_b2` written, `Attr_X` -> `attr_x`) |
| N6 `--out` into a missing directory | closed for a missing parent and a missing chain (`a/b/m.json`) and a parent that is a file: H07 before any prompt, no path in the message. See non-blocking 2 for the sibling |
| N7 `Attr Site` + `attr_site` | closed (both `low` with the note; mutant killed) |
| N8 / RG-N3 list-key strings; `AND` | closed: `columns: "a AND b"`, `"a and"`, `"case_id<NBSP>hadm"` -> E01 names 2; `unit: "a\tAND\tb"` -> 2; `"a and b and c"` -> 3; `"aANDb"` -> H08 enum (one token) |
| N10 Ctrl-C outside a prompt (`map`) | closed for the span the README names: raised from `load_table`, `map_headers`, `check_h11`, `Mapping.table` -> H07 `mapping interrupted; nothing written`; raised from `Mapping.write` (after the `try`) -> propagates out of `main()`, which the README's "between the table load and the last prompt" excludes |
| N3, N4, N9, N10 (`run` half), N11 | carried, and each re-measured as the note says (section below) |
| RG-N1 all-high prompt | closed: `n no e x` -> four `answer a or q`, then `a`; `n q` -> H07 with `decided_by` still `proposed` |
| RG-N2 figures / "three tests marked pins" | closed (docstring says seven; 7 measured) |

Lens-1 blocker repros, re-run: B1 `["100"]*41+["7"]*9` -> `min <suppressed> max 100`; `["40"]*49+["97"]` -> `min 40 max <suppressed>`; `["7"]*41+["100"]*9` -> `max <suppressed>`; `*40 + *10` -> `min 7`; `"1"x5+"1.0"x4` both suppressed, `x5+x5` `min 1`; `A x9` suppressed, `x10` shown; 50 random 7-digit ids -> both suppressed and no id in `render()` or `to_dict()`. B2: `/`, ` / `, `:`, `-`, space, tab, ` and `, ` AND `, a two-item list, the same name twice -> E01 "names 2 columns"; `subject_id`, `a__b` -> H08 enum; `['a']`, `[]` -> H08 type. `sex` 1/2 -> `medium` with `no dictionary declared for 1/2`; 10,001 rows -> `n_sampled` 10000 and the row-10,001 string nowhere.

## Fixtures: twelve read by hand against D1 section 5 step 2 and the note's decisions

No fixture changed in this diff (`git diff --name-status` lists none). Read: `sepsis_pt_prefix` (`pt_Age` age, `pt_Gender` sex, `pt_SepsisLabel` y_true - affix rule), `sepsis_v2_suffix` (`SepsisLabel_v2`, `PredictedProbability_v2`), `sepsis_british` (`Sex`, `centre` site), `diabetes_130` (`gender` sex, `hospital` site, `pred_prob` score, `race`, `age` -> `age_band` by values, `patient_nbr` case_id low, `encounter_id` row_id medium, `readmitted` y_true by dataset row), `mimic_iv_demo` (`subject_id` case_id high, `hadm_id` row_id medium, `gender`, `race`, `label`, `probability`, `admittime`/`dischtime` event_date low), `sepsis_two_labels` (`SepsisLabel` + `outcome` both y_true low with "2 headers claim y_true"), `sepsis_sex_12` (medium, the 1/2 note), `sepsis_label_holds_scores` (y_true low, "continuous"), `sepsis_nfc_nfd_twins` (H07 "unicode normalisation"), `sepsis_two_case_ids` (E01 ending the DEC-11 sentence), `mimic_composite_key` (criteria list of two -> E01), `sepsis_2019` (`Gender` 0/1 -> sex medium). Each agrees with the synonym table (`gender`->sex; `centre`/`hospital`->site; `probability`/`pred_prob`->score; `label`/`outcome`->y_true; `patient_id`/`subject_id`->case_id) and with the build's decisions on dataset rows. Also `sepsis_visit_dates` / `mimic_visit_dates` (`visit` event_date medium) and `diabetes_sex_01` (sex medium, the 0/1 note) - consistent. 35 fixture bases exist; the brief's "thirty" is a floor.

## Sentence rule (added lines in the diff)

Grepped the added lines for `never|prevent|guarantee|ensure|cannot|always|closed|impossible|protect|no longer|any shape|every|whatever|all|safe|complete`. Each hit, and what I fed it:

- `Mapping.read` "a non-list ``roles`` raises AttributeError/TypeError on its own" - **falsified** (B1: `{}`, `""`).
- `Mapping.read` "A non-mapping file ... raises" - `[]`, `"x"`, `5`, `null`, `true`, `[1]` all H07. Kept.
- `_confirm_interactive` docstring / README step 4 "an accept or an edit that would give a role a second holder among the entries already settled ... is refused; entries still to be asked are not counted" - two holders both orders, three holders, an edit to a role a later pending entry holds then that entry accepted (refused at the second), a high `y_true` beside a values-claimed `flag` (the mapper ignores `flag` at high, so no prompt). Could not break. Kept.
- README step 4 "Ctrl-C between the table load and the last prompt" - four raise points inside the span -> H07; one after it (`write`) propagates, as the sentence allows. Kept.
- `apply_mapping` / `errors.py` / module docstring "two columns on ``case_id`` ... halts E01 there, whatever the source" - fed the partial pair, a hand-written prior holding both, and the name-claim pairs (`case_id`+`patient_id`, `case_id`+`mrn_hash`, `study_id`+`subject_id`, `Patient ID`+`subject id`, `pt_case_id`+`case_id`, `case_id_v2`+`case_id`, `CASE_ID`+`Case-Id`: each E01 in `map_headers` first). Could not break. Kept.
- `_single_holder` "(every role except ``ignore``)" - the roles `_decide_named` sees are canonical, `attr_*` or `rater_*`; each is covered. Kept.
- README step 3 "every sampled value one of the six shapes" - `DATE_PATTERNS` has six entries; a mixed column (`17 Mar 2024` / `18/03/2024`) is `date` because both are shapes. Kept.
- Test name `test_all_high_prompt_reprompts_on_anything_but_a_or_q` - see non-blocking 1: `""`, `accept`, `quit`, `abort` do not re-prompt.

The note's ten refused sentences are absent from the diff.

## Non-blocking

1. **Test name generalises**: `test_all_high_prompt_reprompts_on_anything_but_a_or_q` - measured, the answers that do not re-prompt are `a`, `accept`, `` (Enter), `q`, `quit`, `abort` (and `  A  `, since `_ask` strips and lower-cases). The test body feeds five literal answers and the note's section 1 names the six words; the name says "anything but a or q". A sentence nit under the hard rule, not a code defect: rename to the literal five, or to "...on n_no_e_x".
2. **`--out` naming an existing directory, at a terminal**: exit 5 `internal error: PermissionError: [Errno 13] Permission denied: '<path>'` after the prompt is answered - the FA-N6 sibling (the repair checks `parent.is_dir()`, not that `--out` itself is not a directory). Under `--yes` it is H07 `could not be read`. `--out` naming an existing file overwrites it (expected). The README sentence is "when the directory of `--out` does not exist", so no sentence is falsified; one more `is_dir()` on the target closes it.
3. **The dotted shape checks width, not validity**: `31.02.2024` x20 and `99.99.2024` x20 are `date` with `max 2024-02` / `max 2024-99`. The slash shapes behaved the same before this repair (`\d{1,2}`); no row value is printed and no sentence claims a valid month. Recorded so the shape is on file.
4. **List keys inspect lists and strings only**: `columns: ["a, b"]` (a one-item list whose item holds a comma), `columns: 5`, `columns: {"a": 1, "b": 2}` pass `validate_dict`; README step 3 says "lists two or more or is a string that splits", which is what the code inspects.
5. **Enter at the all-high prompt is an accept** (`""` in the accept tuple), so a stray Enter records `decided_by: interactive` on an all-high table; the per-role prompt has had the same tuple since repair 1. Design, not a rule of the task; noted for Josh.
6. Record nits: the sweep took 100 s here (note: 98 s); the new test file is `w/crlf` in a fresh checkout (index `lf`).

## Cut and carried lists against what I measured

Nothing is described as cut. Carried, each re-measured: FA-N3 `proofpack run` without `--yes` on `sepsis_2019_gender_mf.csv` with `clustering.unit: case_id` -> exit 0, `./pack/mapping.json` written `decided_by: proposed` with the original headers and `patient -> case_id low` (with the default `make_criteria()` it halts H05 first - a different criteria file, same finding); FA-N4 `roles: []` -> `map --yes` and `run --yes` both exit 0; `role: "SECRET_ROLE"` on `row_id` -> exit 0 both (lens 2 mutated a different entry and saw S01; the outcome depends on which role is renamed); FA-N9 `{"columns": {"label": 5}}` -> exit 5 `TypeError: object of type 'int' has no len()`; FA-N10 `run` half: `KeyboardInterrupt` from `load_table` propagates out of `main()`; RG-N4 `["2024-03-15"]*49 + ["1999-01-01"]` -> `min 1999-01`; `clustering.unit: subject_id` -> H08 enum, no fix line; `attr_site` ignored beside `Attr Site` -> `apply_mapping` H07 `{"role": "attr_site"}`; `notes: "x"` reads as `['x']`, `notes: 5` and `notes: null` H07; `confidence: "HIGH"` / `"bogus"` -> H07 "requires every mapped role at high"; `decided_by: ["file"]` -> the confirmed-mapping H07; `timestamp: 5` / `{}` and unknown top-level or entry keys -> accepted (not inspected, as the docstring says). All consistent with the note's section 3.

## What could not be broken (what was tried)

- The E01-at-apply gate: the partial pair through `run` (no prior, a prior holding both, `--json-log`), and seven name-claim pairs through `map_headers`; every halt carried a count and no header.
- The held-role refusal: two holders both orders, three holders, an edit to a role a later entry holds, a high holder beside a values claim.
- `Mapping.read`: 26 prior shapes through `map --yes` and `run --yes` (table above) - no exit 5, no traceback, no `SECRET` string in stdout or stderr; the two that pass unexpectedly are B1.
- The floor and the 10,000-row sample (lens-1 B1 repros, eight edge columns, 50 random ids).
- DEC-11 by declaration: 14 `unit` shapes and 11 list-key shapes.
- Ctrl-C at four points inside `cmd_map`'s span.
- Fifteen date strings against the six shapes.
- Shell parity on the sepsis table: byte-identical (3485 bytes, equal `Get-FileHash`).
- The committed sweep: 38 planted, 38 killed.

## Could not check

- mintty behaviour of `_stdin_is_terminal` (no mintty here; the docstring says so).
- A human at a real console end to end (the prompt path was driven by an injected `input` and a patched `_stdin_is_terminal`, and by subprocesses with `stdin=DEVNULL`).
- The E7 manifest hash of `mapping.json` (E7 not built).
- The merge of `a-p1-mapper` onto lane E's tree - the orchestrator's step.
- Real PhysioNet / UCI / MIMIC exports (offline; the fixtures carry header sets only).

## Sentences I refused to write in this note

"The E01 gate is closed" (one pair through `run`, seven through `map_headers`); "`Mapping.read` now rejects every malformed prior" (B1 is the counter-example, and 26 shapes are not every shape); "the prompt cannot write two holders" (three tables, five answer sequences); "the six date shapes are validated" (`99.99.2024` is `date`); "Ctrl-C is handled in `map`" (`write` is outside the span).
