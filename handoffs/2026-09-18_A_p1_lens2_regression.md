# Lens 2 (regression and record) - A-P1 repair 1, branch `a-p1-mapper` at `e92989b` (pre `555a5e1`)

**Verdict: FAIL - one blocker.** Every suite figure re-measured in both shells is one *higher* than the note's (506 passed, not 505; 142 day6, not 141), the 30 pre-fix failures fail on exactly the assertions the note quotes, lane E's files are untouched, nothing in `tests/` is weakened, and every lens-1 blocker and repro is closed. The blocker is a shipped sentence in the new `Mapping.read` docstring - "any shape or I/O failure is H07 `could not be read`" - that a run counter-example falsifies: a prior whose `role` is `123` passes `Mapping.read`, is accepted and rewritten by `map --yes` (exit 0), and then gives `run --yes --mapping` exit 5 `internal error: AttributeError`. FA-N6 ("malformed prior -> exit 5") is therefore closed for the shapes the test feeds and open for `role`.

Worktrees: `scratchpad/lens-a-p1-r2-regression/wt` (detached at `e92989b926dee377c1ae269f3aea162a94f5979b`) and `.../tip` (detached at `555a5e111afdfc245f7a5bfb8111d03bd854e478`), both removed at the end. The main tree (`b93e050`, lane E: `calibration.py`, `descriptive.py`, `number.py`, `test_calibration.py`, `f4_expected.json` modified in its working tree) was read once with `git status` and `git worktree list`, never checked out, stashed or committed in. Nothing committed anywhere.

`PYTHONPATH` proof, run before any figure in each shell:

| shell | worktree | `python -c "import proofpack;print(proofpack.__file__)"` |
|---|---|---|
| Git Bash | wt | `...\lens-a-p1-r2-regression\wt\src\proofpack\__init__.py` |
| Git Bash | tip | `...\lens-a-p1-r2-regression\tip\src\proofpack\__init__.py` |
| PowerShell 5.1 | wt | `...\lens-a-p1-r2-regression\wt\src\proofpack\__init__.py` |
| Git Bash, no `PYTHONPATH` (the trap, measured) | wt | `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py` - lane E's tree |

## Blockers

### B1. `Mapping.read`'s docstring claims "any shape or I/O failure is H07"; a `role` that is not a string is accepted by `map --yes` and is exit 5 under `run --yes`

Repro (worktree at `e92989b`, `PYTHONPATH` forced, `tests/` on `sys.path` for `conftest`): write a confirmed prior for `make_cohort()` (`decided_by: file`, matching hash), set `roles[0]["role"] = 123`, then
`proofpack run --input t.csv --criteria c.yaml --mapping m.json --out p --yes` -> **exit 5**, first stderr line `internal error: AttributeError: 'int' object has no attribute 'startswith'`. With `roles[0]["role"] = ["a"]` -> **exit 5**, `internal error: TypeError: cannot use 'list' as a dict key (unhashable type: 'list')`. The same two files through `proofpack map --input t.csv --out m.json --yes` -> **exit 0**, the file rewritten with `decided_by: file` and the int/list role kept. No traceback, no header or cell in either message.

Why it blocks: `src/proofpack/io/mapping.py` line 259 (added in this diff) reads "Read a prior `mapping.json`; any shape or I/O failure is H07 `could not be read`." The next sentence lists what is checked (`header_set_sha256` a string; each `roles` entry a mapping whose `original` and `confidence` are strings), and `role` is not in that list, so the first sentence generalises past the check - the day's hard rule, with the counter-example above run and *not* failing. The note's section 5 refuses "A malformed mapping.json is always H07" and says the docstring "lists the shapes it checks" - the committed docstring says "any shape" first. The code half: lens-1 N6 was "malformed prior under `--yes` -> exit 5"; the repair closes it for `roles: "x"`, `roles: [1, 2]`, `header_set_sha256: 123`, `original: 1`, `confidence: null`, `value_summaries: null` and `[]` (all seven re-run here, exit 3 `HALT H07: mapping.json could not be read`) and leaves it open for `role`. Fix is one line in `Mapping.read` (`role` must be a string or null) plus the sentence narrowed to what is inspected, plus a test feeding `role: 123` and `role: ["a"]` through `run --yes` asserting exit 3.

Also measured, not part of the blocker (no exit 5, no traceback): `value_summaries: "SECRET_STR"` (a string) passes `data.get("value_summaries") or {}` and is written back by `map --yes`; `notes: "x"` reads as `['x']`; `notes: 5` is H07 `could not be read`; `decided_by: {"a": 1}` / `["interactive"]` are the confirmed-mapping H07 (the `str()` cast makes them a non-confirmed string). Under `map --yes` a prior with an unknown role string, a duplicated `original`, two entries on one role, an empty `roles` list, or an `original` absent from the header set is accepted and rewritten (exit 0) - the hash and `all_high` are the only checks (day-6 build behaviour, not new in the repair); `run --yes` halts H07 on the duplicated role and proceeds (exit 0) on the others.

## Measured against the note (both shells, `PYTHONPATH` forced to the worktree's `src`)

| command | note says | Git Bash (measured) | PowerShell 5.1 (measured) |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | 505 passed, 1 skipped, 1 xfailed | **506 passed, 1 skipped, 1 xfailed in 47.36s** | **506 passed, 1 skipped, 1 xfailed in 45.15s** |
| `... -m day6` | 141 passed, 366 deselected | **142 passed, 366 deselected in 2.90s** | **142 passed, 366 deselected in 2.40s** |
| `python -m ruff check .` | All checks passed! | same | same |
| `python -m ruff format --check .` | 59 files already formatted | `59 files already formatted` | same |
| `python -m proofpack.cli doctor --offline` | All essential checks passed. | not run in Bash | same, exit 0 |
| `python scripts/mutation_sweep.py --marker day6` | 27 planted, 27 killed, 0 survived; 62 s | `27 planted, 27 killed, 0 survived; 59 s` | not repeated |
| new tests at `555a5e1` (file copied into the tip worktree, Ctrl-C test deselected) | 30 failed, 15 passed, 1 deselected | `30 failed, 15 passed, 1 deselected in 1.18s` | - |
| the Ctrl-C test alone at `555a5e1` | `!!! KeyboardInterrupt !!!`, no tests ran | `!!! KeyboardInterrupt !!!` at `test_mapping_repair1.py:307`, `no tests ran in 0.52s`, rc 2 | - |
| `map --input tests/fixtures/mapping/sepsis_2019.csv --out ../m.json < NUL` (`PYTHONUTF8=1`) | exit 3; `'Age' -> age high float; 50 unique; ... min <suppressed> max <suppressed>` | exit 3, 27 lines, no file written; the `Age` line as quoted; `ICULOS` `min 1 max 5`, `SepsisLabel` `min 0 max 1` (34/16), `Gender` `min 0 max 1` (28/22) | exit 3; captured bytes identical to Git Bash's (3485 bytes each, `cmd /c ... < NUL > file 2>&1`) |
| the eight lens-1 mutants (L09 L13 L14 L15 L18 L26 L20 L22) planted in a copy of `src` + `schema`, `-m day6 -x` | 8 planted, 8 killed | 8 killed, each by the test the note names; e.g. L09 `1 failed, 136 passed` (note: 135), L15 `1 failed, 105 passed`, L18/L26 `1 failed, 121 passed`, L22 `1 failed, 140 passed` (note: 139) | - |
| `scripts/make_mapping_fixtures.py` re-run in the checkout | 0 files listed by `git status` | `git status --short` lists 0 fixture files; `git diff --ignore-cr-at-eol --name-only` empty; 71 fixture files `i/lf w/crlf` before and after | - |
| `_stdin_is_terminal` on a real console (`Start-Process python`, minimised) | `isatty=True terminal=True` | - | `isatty=True terminal=True`, from the worktree's `cli.py` |

Collected: 508 items = 506 + 1 skip (`test_doctor_cli.py:57`, write access) + 1 xfail (`test_f13_matches_proc_on_the_asah_dataset`). `tests/test_mapping_repair1.py` collects **46** items from **23** test functions (23 - 3 parametrised + 13 + 6 + 7); `test_mapping_full.py` 96. 96 + 46 = 142, and 460 + 46 = 506. The note's "141 = 96 + 46 - 1" and "505 = 460 + 46 - 1" subtract an item that exists; its "27 test functions" is 23. Every count in the note's mutant table is one below the measured one for the same reason. The direction is one more test, not one fewer, so this is a record defect, not a weakening (non-blocking 3).

## Diff checks

- `git diff --name-status 555a5e1 e92989b -- tests/` -> `M tests/test_halt_gates.py`, `M tests/test_mapping_full.py`, `A tests/test_mapping_repair1.py`; **0 `D`**. Added test lines matching `mark.skip|skipif|xfail|.only|pytest.skip|importorskip`: **0**. Deleted lines under `tests/`: exactly the five the note lists (`assert s.min == "0" and s.max == "1"`, `assert s.inferred_type == "int" and s.min == "1" and s.max == "4"`, `map_headers(list(cols), cols).write(prior)`, the `def test_no_halt_carries_a_header_or_value():` line and its docstring line), each replaced on the following lines. No `pytest.mark` / `pytestmark` line removed anywhere in the diff.
- `git diff --name-status 555a5e1 e92989b -- src/proofpack/stats schema/output_schema_v1.json pyproject.toml` -> **empty**.
- Files touched: `README.md`, `scripts/make_mapping_fixtures.py`, `scripts/mutation_sweep.py`, `src/proofpack/{cli,errors}.py`, `src/proofpack/io/{declare,mapping,profile}.py` and the three test files (11 files, +892/-75). `cli.py` hunks are the `_stdin_is_terminal` docstring, `_ask`, `_confirm_interactive`, `_tolerant_console` and `cmd_map`; no hunk touches the `map` subparser or `main()`.
- The five pre-existing tests the note says now set `decided_by` first: each diff hunk adds one `decided_by = ...` line (or splits a `write` into three lines to do so) and changes no assertion.
- Line endings: all eleven changed files `i/lf w/crlf` in a fresh checkout.

## Pre-fix failures (the tip worktree, first `E` line per test)

All 30 match the note's table verbatim: `assert ('7', '100') == ('<suppressed>', '100')`; `assert 'H08' == 'E01'` (the eight separator shapes; `&`, `;`, `|`, the doubled list and `a, b, c` pass at the tip); `Failed: DID NOT RAISE HaltError` (six list keys, and the `ingest` test); `assert 'HALT H08: de...ng/unit: enum' == 'HALT E01: cl...to one column'`; `assert 0 == 3` (proposed prior; EOF all-high half; malformed `prior3`/`prior4`); `assert [] == ['every role ...t / [q]uit? ']`; `assert [] == ['  y_true is...oose another']`; `assert 5 == 3` (`prior0`-`prior2`); `assert None == {}` (`prior5`); `assert ('categorical' == 'date'`; the cp1252 `UnicodeEncodeError` tuple; `IndexError: list index out of range`. None aborts on an import or attribute error. The 15 that pass at the tip are the ones the note names as pins or as shapes that already reached E01 (list above in the run log: the date pin, five separator shapes, the H08 single-token test, accept/edit confidence, the `attr_coding` edit, `prior6`, and the five FA-N10 pins).

## Lens-1 blockers and findings: closed or not

| lens-1 item | status at `e92989b` (measured) |
|---|---|
| B1 min/max leak | closed on every repro: `["100"]*41+["7"]*9` -> `min <suppressed> max 100`; `["40"]*49+["97"]` -> `min 40 max <suppressed>`; 50 random 7-digit ids -> both suppressed and no id in `render()` + `to_dict()`; `diabetes_130` `encounter_id`/`patient_nbr` and `mimic_iv_demo` `hadm_id` -> both `<suppressed>` through `map_headers` |
| B2 separators | closed: `/`, ` / `, `:`, `-`, space, tab, `subject_id hadm_id`, `.`, NBSP, newline, `Patient ID`, `('a','b')` -> E01 "names 2 columns"; `columns`/`key`/`columns: ('a','b')` -> E01 "lists 2 columns"; `subject_id`, `a__b`, `''`, `'-'`, `'/'`, `aANDb` -> H08 enum (one token); `['a']`, `[]` -> H08 type |
| N1 `--yes` on a proposed prior | closed by `test_yes_refuses_a_proposed_prior` (run writes `proposed`; `map --yes` exit 3, bytes unchanged); the `run`-writes-into-`./pack` half carried, as the note says |
| N2 all-high asks nothing | closed (one prompt) - but see non-blocking 1 |
| N3 confidence kept | carried and pinned; L18/L26 killed |
| N4 held-role edit | closed; L-mutant R06 killed in the committed sweep |
| N5 Ctrl-C | closed at the per-role, all-high **and** the edit sub-prompt (`e` then `KeyboardInterrupt` from `input` -> H07 `mapping interrupted at the prompt; nothing written`, measured here; the test feeds the first two only) |
| N6 malformed prior exit 5 | **partly closed** - B1 above |
| N7 dash dates | closed (`test_dash_separated_dates_are_typed_date_and_halt_h11`) |
| N8 cp1252 | closed; re-run directly in PowerShell (`PYTHONIOENCODING=cp1252`, `PYTHONUTF8` unset, header `体温`, stdin `NUL`): exit 3, table printed with `'\u4f53\u6e29'`, first stderr line the non-terminal H07 |
| N10 eight survivors | all eight killed (table above) |
| N11 test id | renamed; `mapping.py` docstring cites the new id |
| N12 `--quiet` | closed (`test_quiet_at_a_terminal_prints_the_table_the_prompt_refers_to`) |
| RG-NB-2 / -3 / -7 | closed (B2, B1, fixture regen above) |
| RG-NB-6 `[unverified]` console | closed; docstring records the measurement; re-measured here |
| RG-NB-1 four tests pass at `4eb44f3` | carried; not re-run (no base worktree in this session) |
| RG-NB-4 / -5 | carried to Josh, as the note says |

## Non-blocking

1. **The all-high prompt accepts any answer that is not `q`/`quit`/`abort`.** `_confirm_interactive` on the seeded cohort with `ask=lambda p: "n"` (also `no`, `N`, `e`, `edit`, `x`) -> `decided_by = "interactive"`, no re-prompt; the per-role prompt re-prompts with `answer a, e or q` on the same inputs. A human who types `no` at `every role is high (N columns): [a]ccept / [q]uit?` gets a `mapping.json` recorded as a human acceptance. No shipped sentence claims otherwise (the docstring says "accept / abort"), so not a sentence violation; one line (mirror the per-role fallthrough) closes it.
2. **`clustering.columns: "a, b"`** (a string under one of the six list keys) passes `validate_dict` silently; `unit: "a AND b"` halts E01 "names **3** columns" (upper-case `AND` is a token, only lower-case ` and ` is a separator); `unit: "x and"` halts E01 "names 2 columns". Each is a typed halt or a documented non-inspection (README step 3 says "lists two or more"); noted so the shapes are on record.
3. **The note's figures are each one below the committed tree**: 505/141/27 vs 506/142/23 functions (46 items), and every "passed" count in its mutant table. The arithmetic "505 = 460 + 46 - 1 ... one item is the Ctrl-C test counted once" subtracts an item that exists; the figures read as derived, not measured at `e92989b`. `tests/test_mapping_repair1.py` line 5 says "the three tests marked 'pins' passed there" - seven tests carry "Pins" in their docstring and 15 items pass at the tip.
4. **Carried from the note, confirmed by measurement**: date `min`/`max` are not put through the floor (`["2024-03-15"]*49 + ["1999-01-01"]` renders `date; 2 unique; 0.0% missing; min 1999-01 max 2024-03; values not shown (dates)` - one row's month, measured; the note's open question 1); `proofpack run` without `--yes` writes `mapping.json` (`proposed`, original headers) into `./pack`; `clustering.unit: subject_id` halts H08 `enum` with no fix line; `--yes` unreachable on any table with a non-high role after a human accept (FA-N3, pinned).
5. **Numeric floor edge cases, all consistent with R1-D1 (rows holding the number, summed over strings)**: `["100"]*5+["1e2"]*5+["7"]*9` -> `min <suppressed> max 100` while `values:` lists all three distinct as suppressed (the max is held by 10 rows across two spellings); `["07"]*9+["7"]` -> `min 7 max 7`; `["nan"]*20+["5"]*3` -> both suppressed, `nan (20)` listed; `["-0"]*5+["0"]*5+["9"]` -> `min 0`; `["inf"]*10+["3"]` -> `max inf`; nine rows only -> both suppressed. `signals` (the true extremes) is absent from `to_dict()`.

## Sentence rule

Added sentences in the diff that assert what a check guarantees, prevents or closes:

- `mapping.py` `Mapping.read`: "any shape or I/O failure is H07" - **falsified** (B1). No counter-example in the note.
- README step 4: "Ctrl-C or a closed stdin at a prompt is H07 (`nothing written`)" - the tests feed both exceptions at two of the three prompts; I fed `KeyboardInterrupt` at the third (the edit sub-prompt) and could not break it. Kept.
- `cli.py` `_ask`: "a closed stdin or Ctrl-C at it is the H07 abort, not a traceback" - the eight-line function's two `except` arms; test cited. Kept.
- `profile.py` module docstring and README step 1: the min/max rule stated with the literal column and the test id; edge cases in non-blocking 5 did not break it. Kept.
- `declare.py` comment: names the character class, the two-token `patient-id`, and the test ids. Kept.
- `errors.py`: names the two raisers and what the CLI test asserts. Kept.
- The note's ten refused sentences: absent from the diff (grepped added lines for `never`, `prevents`, `guarantee`, `ensure`, `cannot`, `always`, `closed`, `impossible`, `protects`, `no longer`, `any shape`, `every way` - the hits are the three descriptive sentences above and the H07 message strings).

## Cut and carried lists against what I measured

The note's section 3 (carried) matches: each carried item re-measured above behaves as the note says. Nothing in the note is described as cut; the diff carries every fix its section 1 lists, with the one partial closure (FA-N6, B1). The fixture set is unchanged by the repair (no fixture in the diff); twelve `expected.json` files read by hand against the CSV headers, D1 section 5 step 2's synonym table and the note's decisions: `diabetes_130` (`pred_prob` score, `hospital` site, `gender` sex, `race`, `readmitted` y_true via the declared dataset row, `age` -> `age_band` by values, `patient_nbr` case_id low, `encounter_id` row_id medium), `sepsis_2019` (`Gender` 0/1 sex medium, `SepsisLabel`/`PredictedProbability`/`PredictedLabel` dataset rows), `sepsis_british` (`Sex`, `centre`), `sepsis_american` (`center`), `sepsis_pt_prefix`, `sepsis_v2_suffix`, `mimic_iv_demo` (`subject_id` case_id, `label`, `probability`, `gender`, `race`; `hadm_id` row_id medium; `anchor_age` age medium; `admittime`/`dischtime` both event_date low), `sepsis_two_case_ids` (E01), `mimic_composite_key` (list of two in `criteria.yaml` -> E01), `sepsis_two_labels` (`SepsisLabel` + `outcome` both y_true low), `sepsis_label_holds_scores` (y_true low). All consistent.

## What could not be broken (what was tried)

- The floor on numeric min/max: the five lens-1 columns, three fixture columns, 50 random ids, and the eight edge cases in non-blocking 5 - no value held by fewer than 10 rows reached `render()`, `to_dict()`, the printed table or the written file.
- DEC-11 through `validate_dict`: 28 `unit` shapes and 6 `clustering` key shapes - every multi-token string and every list of two or more is E01 with the DEC-11 sentence; every single token outside the enum is H08 `enum`; no traceback.
- Prompts: `KeyboardInterrupt` and `EOFError` at all three prompts -> H07; the held-role refusal on `y_true`.
- Malformed priors: 15 shapes through `map --yes` - no traceback, no exit 5, no `SECRET` string in stdout or stderr; 8 shapes through `run --yes` - the two exit 5s are B1, the rest exit 0 or H07.
- cp1252 stdout with a CJK header, directly in PowerShell (above).
- Shell parity on the sepsis table: byte-identical.
- Fixture regeneration: nothing modified.
- The committed sweep and the eight lens mutants: 35 planted, 35 killed.

## Could not check

- mintty behaviour of `_stdin_is_terminal` (no mintty in this session; the docstring says so).
- The four day-6 tests that pass at `4eb44f3` (lens-1 RG-NB-1): not re-run, no base worktree made here.
- The mutation sweep in PowerShell (Git Bash only, 59 s).
- The merge of `a-p1-mapper` onto lane E's tree - the orchestrator's step.
- A human at a real console end to end (the prompt path was driven by injected `input` and `ask`).

## Sentences I refused to write in this note

"Malformed priors are now H07" (B1 is the counter-example); "the floor cannot leak through min/max" (I fed thirteen columns); "every composite key reaches E01" (I fed 34 shapes; `columns: "a, b"` does not); "the prompts are safe against Ctrl-C" (three prompts, two exceptions).
