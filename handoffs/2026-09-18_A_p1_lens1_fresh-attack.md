# Lens 1 (fresh attack) - lane A day 6, A-P1 the full mapper

Branch `a-p1-mapper` at `555a5e1` (from `4eb44f3`), probed in a detached worktree under
`scratchpad/lens-a-p1-r1-fresh-attack/wt`; `PYTHONPATH` forced to that worktree's `src` and
`python -c "import proofpack;print(proofpack.__file__)"` printed
`...\lens-a-p1-r1-fresh-attack\wt\src\proofpack\__init__.py` before any number below was taken.
Nothing committed; the main tree was not touched; the worktree is removed at the end.

## Verdict: FAIL (2 blockers, both reachable from `proofpack map` on a real table; both also falsify a shipped sentence)

## Blockers

### B1. `min`/`max` print single-row values that the k=10 floor has just suppressed
`profile_column(["100"]*41 + ["7"]*9).render()` ->
`int; 2 unique; 0.0% missing; min 7 max 100; values: 100 (41), <suppressed> (1 distinct below k=10)`.
The value `7` (count 9, suppressed in the list) is printed as `min 7` on the same line. Three more:
`["40"]*49 + ["97"]` -> `min 40 max 97` (one patient's age, count 1); 50 random 7-digit integers under
`mrn` -> `min 1035333 max 9852152` (two real cells, count 1 each); the committed fixture
`diabetes_130.csv`, column `encounter_id` -> `min 500001 max 500050`, `patient_nbr` -> `min 1000 max 1029`,
and `mimic_iv_demo.csv` `hadm_id` -> `min 20000001` (each a cell with count 1). The 5 MB single-column
file `mrn` printed `min 32 max 999872`. These reach the printed table (`Mapping.table()`), stdout under
`--yes` (CI logs), the `--json-log` payload (`{"mapping": {... "value_summaries": {...}}}` on stdout),
`mapping.json`, and `./pack/mapping.json` written by `proofpack run`.
The shipped sentences it falsifies (blocker on their own under the grading rule):
`src/proofpack/io/profile.py` module docstring, "Suppression is applied before anything is displayed
or written: a value is listed only when its count in the sample is >= SUPPRESSION_K; below that it is
replaced by the literal <suppressed>"; `ColumnSummary` docstring "Aggregates only."; README step 1
"A value is listed only when its count is >= 10 ... below that it prints as `<suppressed>`".
The build note's own open question 3 says min/max "are single-row values by construction" - the code
and the docstring were shipped saying the opposite of each other. `test_two_unique_split_is_suppressed_the_same_way`
asserts the leak (`s.min == "0" and s.max == "1"` on `["0"]*41 + ["1"]*9`) - my mutant L11 (min set to
None) is killed by that test, so the suite defends the leak rather than the floor.
Repro: `PYTHONPATH=<wt>/src python -c "from proofpack.io.profile import profile_column as p; print(p(['100']*41+['7']*9).render())"`.
Note the spec tension honestly: D1 section 5 step 1 lists "min/max" in the summary, and the task's
binding gloss says no row-level value may appear unless it is one of the top-20 aggregated values.
A min or max of a column with 50 distinct values is not one of those. Coarsening numeric min/max to
a band (as dates are coarsened to month), or withholding them when the extreme value's count is
below k, closes it; the choice is the builder's, the docstring must match whichever is chosen.

### B2. A composite case key written with `/`, `:`, `-`, a space or a tab halts H08, not E01
`declare.validate_dict(make_criteria(clustering={"unit": "patient_id / study_id", "declared_by": "t"}))`
-> `H08: declaration invalid at clustering/unit: enum`. Same for `patient_id/study_id`,
`patient_id:study_id`, `patient_id-study_id`, `patient_id study_id`, `patient_id\tstudy_id`.
The DEC-11 halt (E01, "reduce your case key to one column") fires only for `,` `+` `&` `;` `|` and
` and `. The H08 text names no fix; `subject_id/hadm_id` is the ordinary way MIMIC users write that key.
Shipped sentences it falsifies: `src/proofpack/errors.py` comment "a composite case key is a typed
halt whose message ends "reduce your case key to one column", never a traceback"; README step 3
"E01 (DEC-11) ... when `criteria.yaml`'s `clustering.unit` names two or more columns". No traceback
in any of the six shapes (exit 3 through `main()`), so the "never a traceback" half held.
Repro: put `clustering: {unit: "patient_id/study_id", declared_by: x}` in a criteria.yaml and run
`proofpack map --input <any csv> --criteria <that yaml>`; stderr's first line is the H08 enum message.
Also measured while here: `unit: ["patient_id", "patient_id"]` (one column twice) -> E01 "names 2
columns"; `clustering: {unit: case_id, columns: [subject_id, hadm_id]}` and `{unit: case_id, key: [...]}`
pass silently (only the `unit` key is inspected; the schema does not forbid extra keys).

## Non-blocking (reachable, no rule of the task broken, worth a line each)

N1. `proofpack run` with no `--mapping` and no `--yes` writes `./pack/mapping.json` with
`decided_by: proposed`, original headers and the value summaries (with B1's min/max) into the pack
output directory - the directory a customer hands over. Then `proofpack map --yes --out ./pack/mapping.json`
accepts that file (matching hash, all high) and rewrites it as `decided_by: file`: a mapping no human
confirmed becomes a "file" decision. The `--yes` rule as written in D1 section 5 step 3 is satisfied
(prior exists, hash equal, every role high); `decided_by` is never inspected.
Measured: run rc 0 -> `proposed`; map --yes rc 0 -> `file`.
N2. Interactive `map` on a table whose roles are all high asks nothing (0 prompts measured on the
seeded cohort) and still writes `decided_by: interactive`. There is no overall accept prompt, so
`class` -> `y_pred` (synonym) on a UCI-style table where `class` is the truth label is written as a
human decision with no keypress.
N3. Interactive accept/edit leaves `confidence` at medium/low, so a table with any non-high role
(PhysioNet Sepsis, `Gender` 0/1) can never run `--yes` afterwards; a human confirmation has no effect
on CI mode. Mutants L18 and L26 (accept/edit set the confidence to high) both SURVIVE the day-6 suite,
so the behaviour is unobserved either way. This is the build note's D5/needs-from-Josh 1, restated
from the CI side.
N4. Interactive edit accepts a role another column already holds (`gender` edited to `y_true` beside
`y_true`): `map` writes the file and exits 0; `run` then halts H07 "two columns map to the same
canonical role". A one-line check at the prompt would say so immediately.
N5. Ctrl-C at the prompt: `KeyboardInterrupt` propagates out of `main()` (measured by raising it from
`input`); at a console that is a traceback. Not a HaltError, so not item (e) as worded.
N6. A malformed prior under `--yes`: `roles` a string or a list of ints, or `header_set_sha256` an
int, exit 5 "internal error: AttributeError/TypeError ..." rather than H07 (`Mapping.read` catches
OSError/ValueError/KeyError/TypeError only). No header or cell in the message; no traceback.
N7. A date column the sniff does not recognise passes H11: `visit` holding `15-03-2024` -> `string`,
free text, `ignore high`; `visit` holding Excel serials `45000..45029` -> `row_id medium` ("by values
only"); `20240315`-style would be `int`. ISO `2024-03-15` and `2024-03-15T10:00:00` and `15/03/2024`
do halt H11 (measured). The README's wording "date-like ... by values" is defined by `DATE_PATTERNS`,
so no shipped sentence is false; the gap is real for a customer whose export uses dashes.
N8. Non-UTF-8 stdout (measured with `PYTHONIOENCODING=cp1252`, `PYTHONUTF8` unset) and a CJK header
-> `internal error: UnicodeEncodeError ... position 79-80`, exit 5, no table. The message carries no
header text. The subprocess test sets `PYTHONUTF8=1`; a customer piping output on Windows may not.
N9. `subject_id` + `subject_id_v2` -> the `_v2` column is `ignore high` with the note "header resembles
case_id but another header names it"; `hadm_id` beside `subject_id` (MIMIC's real two-column key) is
`row_id medium`, not E01. Both follow the build's D6 reading (E01 on name claims only); noted because
the second is the textbook composite key and only a `clustering.unit` declaration reaches E01 for it.
N10. Lens mutants (28 planted, literal one-line edits, `-m day6` run in a copy with `PYTHONPATH`
forced): 20 killed, 8 SURVIVED - L09 free-text `n_unique > 2` guard -> `> 0`; L13 label
"holds N distinct values" conflict threshold 10 -> 100; L14 two partial tokens for one role need
three; L15 `&` dropped from the DEC-11 separator set; L18/L26 accept/edit set high (N3); L20 full
hash in the H07 detail; L22 `missing_pct` unrounded. L13, L14 and L15 are rules the docstrings state
with no test feeding them. The committed sweep reproduced: 17 planted, 17 killed, 0 survived, 34 s.
N11. Test id `test_no_halt_carries_a_header_or_value` asserts a universal in its name; its docstring
scopes it to "every halt the committed fixtures raise, plus two constructed ones". I could not
construct a reachable halt carrying a header (the only candidate, `apply_mapping`'s `{"role": role}`,
needs a hand-edited prior that ignores a column whose original name is itself a canonical role or an
`attr_*` name), so this is a naming note, not a falsification.
N12. `--quiet` interactive: the table is not printed but the per-role prompts still appear, so the
human confirms roles without the value summary in front of them.

## What could not be broken (what was tried)

- (b) Declarations inferred: grep of the diff for a recoding dictionary or any write of positive
  class / orientation / threshold / reference type / clustering - none; `sex` 1/2 and 0/1 stay the
  strings `1`,`2` / `0`,`1` in the printed table (`values: 1 (200), 2 (200)`), medium with the note;
  `age` -> `age_band` is a role override, not a declaration.
- (f) `case_id` from values: `_value_candidate` has no `case_id` outcome; `patient_nbr` repeating ->
  `case_id low` with "confirm or ignore"; `id`/`ID2` repeating -> ignore; `idx` unique ints -> `row_id
  medium`, repeating -> ignore.
- (g) No M/F guess for 1/2: see (b).
- (h) Floor boundaries in the values list: count 9 -> `<suppressed>`, count 10 -> shown, count 11 ->
  shown, in `top` and in `split`; `n_suppressed_values` counts every distinct value below k, not only
  the inspected 20 (a 9,947-unique column reported 9947). The leak is only through min/max (B1).
- (i) Sample: `column[:10_000]`; a 10,001-row file with `SECRET_ROW_10001` in row 10,001 printed
  `n_sampled` 10000 and the string appeared nowhere in stdout, stderr or the written file.
- (j) Closed stdin: 30 hostile files run as subprocesses with `stdin=DEVNULL`, each halted in 0.3 s
  (the 4.8 MB single-column file in 0.8 s); a pipe on stdin halts before any read.
- (e) Tracebacks: none in 30 hostile files (0 bytes, header only, blank first line, latin-1, 2,560
  bytes of binary, tab-separated, quoted newline in a header, zero-width space in a header, NFD/NFC
  twins, `LABEL`/`label`, `Label `/`Label`, BOM mid-header, ragged row, JSON junk, no extension,
  200 distinct free-text notes, a name repeated 10 times among 190 singletons, Excel serials, three
  date shapes). NFD/NFC twins and `LABEL`/`label` -> H07 with `n_duplicate_headers: 1` and no header
  text; `Label `/`Label` -> S04 in `load_table` (headers are stripped on read).
- (a) Headers/values in halts: every halt message and detail seen carries counts, 12-char hash
  prefixes or canonical names only; `SECRET_ROW_10001`, `SECRETVAL`, `EXTRA_SECRET` never appeared.
  Original headers do appear in the printed table, the prompt, `--json-log` stdout and
  `mapping.json` - the first three are D1 section 5 step 3's table and step 5's file; B1 is the value
  side of the same surfaces.
- (l) `git diff 4eb44f3 555a5e1 -- src/proofpack/stats schema pyproject.toml` is empty.
- Tests not weakened: the diff under `tests/` (excluding fixtures) adds one file and deletes no line;
  no skip/xfail/only added. Full suite in the worktree: `460 passed, 1 skipped, 1 xfailed in 48.01s`;
  `-m day6`: `96 passed, 366 deselected`; `ruff check` and `ruff format --check` clean (58 files).
- Fixtures rigged (k): `scripts/make_mapping_fixtures.py` imports nothing from `proofpack`; the 35
  `expected.json` files assert roles/confidences/notes only; a read of all 35 non-ignore role sets
  against the confidence table found each consistent with the stated rules.
- `_stdin_is_terminal` on a real console handle (the build note's [unverified]): opening `CONIN$` in
  this session's hidden console gave `GetConsoleMode` -> 1 (mode 503), `isatty` True, and
  `_stdin_is_terminal()` True with it as `sys.stdin`; with NUL: `isatty` False, `GetConsoleMode` 0.

## What I could not check

- A human typing at the prompt in a Windows console end to end (the prompt path was driven by
  injected `input`).
- PowerShell 5.1 output parity (Git Bash only in this session).
- The E7 manifest hash of `mapping.json` (E7 is not built).
- Real PhysioNet PSV / UCI files (offline; the fixtures carry only the header sets).

## Sentences I refused to write in this note
"The floor cannot leak through the values list" (I inspected counts 9/10/11 only); "no halt carries a
header" (see N11); "H11 catches date columns" (see N7).
