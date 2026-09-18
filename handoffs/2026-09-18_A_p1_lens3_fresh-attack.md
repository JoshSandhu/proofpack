# Lens 3 (fresh attack) - lane A day 6, A-P1 the full mapper, after repair 2

Branch `a-p1-mapper` at `ea526e363474bd1c96de3b893667457a5a766df0` (repair 2, on `e92989b`), probed
in a detached worktree `scratchpad/lens-a-p1-r3-fresh-attack/wt`; a second detached worktree
`.../tip` at `e92989b926dee377c1ae269f3aea162a94f5979b` for the pre-fix run. `PYTHONPATH` forced
to the worktree's `src` on every run; `python -c "import proofpack;print(proofpack.__file__)"`
printed `...\lens-a-p1-r3-fresh-attack\wt\src\proofpack\__init__.py` (Git Bash and PowerShell
5.1) and `...\tip\src\proofpack\__init__.py` before any figure below was taken; without
`PYTHONPATH` it printed `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py` (lane
E's tree - the trap, measured). Nothing committed; the main tree (`a5a5ed8`, lane E) was read
once with `git worktree list` and never touched; both worktrees removed at the end.

## Verdict: FAIL (4 blockers: two reachable from `proofpack map` on a real table, of which one also falsifies three shipped sentences; two are sentence-only with a one-line fix each)

## Blockers

### B1. Enter (an empty answer) at the all-high prompt is an accept; README step 4, the `_confirm_interactive` docstring and a test id say "anything else re-prompts"

Measured (`_confirm_interactive(m, ask=lambda p: "", say=print)` on the seeded cohort, every role
high): no refusal line, `m.decided_by == "interactive"`. Also accepted without a refusal:
`"accept"`, `"  a  "`, `"A"`; `"quit"` and `"abort"` abort. At the per-role prompt (`gender` 1/2,
sex medium) an empty answer is likewise an accept (`notes` gain `accepted interactively`, no
refusal line). The `""` arm has been in the per-role accept since `555a5e1`; repair 2 copied it
into the new all-high loop and then documented the loop as the opposite.

Shipped sentences falsified (each checked against the code at `ea526e3`):
- `README.md` line 103: "or once for the whole mapping when every role is high (`a` or `q`;
  anything else re-prompts)".
- `src/proofpack/cli.py` line 144 (`_confirm_interactive` docstring): "(accept / abort; any
  other answer re-prompts ...)".
- `tests/test_mapping_repair2.py::test_all_high_prompt_reprompts_on_anything_but_a_or_q` - the
  id asserts a universal; the test feeds `n no e x a` and asserts 4 refusals.

Why it blocks beyond the sentences: the prompt text `every role is high (N columns): [a]ccept /
[q]uit?` announces no default, so a stray Enter writes `mapping.json` with `decided_by:
interactive` - recorded as a human acceptance - and `--yes` then accepts that file in CI. D1
section 5 step 3's "user accepts/edits" is met by a keypress the user did not make.

Repro: `PYTHONPATH=<wt>/src python -c "import sys;sys.path.insert(0,'tests');from conftest
import make_cohort;from proofpack.io.mapping import map_headers;from proofpack.cli import
_confirm_interactive as c;k=make_cohort();m=map_headers(list(k),k);c(m,ask=lambda p:'',
say=print);print(m.decided_by)"` -> prints `interactive`, no `answer a or q` line.

Fix (either): make `""` re-prompt at both prompts (and the per-role README line gains nothing),
or keep Enter as accept and say so in the prompt text, the README, the docstring and the test
id. Regression test: feed `""` and `"accept"` at the all-high prompt and at a per-role prompt
and assert whichever rule is chosen.

### B2. `score` holding 0/1 beside `prob`: the prompt says "choose one", the human sets `score` to `ignore`, and `proofpack run --mapping` halts H07 "two columns map to the same canonical role"

Table `row_id,label,score,prob` (60 rows; `score` 0/1, `prob` floats in [0, 1]) - the brief's own
hostile shape ("score holding 0/1"). Fresh mapping: `score` -> `score low` (`2 headers claim
score; choose one` + `header names a score but the values are only 0/1`), `prob` -> `score low`
(`2 headers claim score; choose one`). `proofpack map` at a terminal, answers `e`, `ignore`, `a`
(3 prompts): exit 0, `mapping.json` = `score -> ignore`, `prob -> score`. Then `proofpack run
--input sp.csv --criteria c.yaml --mapping sp.json --out p` -> **exit 3, `HALT H07: two columns
map to the same canonical role`, `detail: {"role": "score"}`**. `apply_mapping` keeps an ignored
column under its original name (`role = mapping.role_of(original) or original`), so the ignored
column named `score` collides with the column mapped to `score`. The customer did what the
prompt said and has no way past except renaming the column in the source export; the message
describes a mapping that is not the one they wrote. The same shape with `Attr Site` + `attr_site`
(ignore `attr_site`, accept `Attr Site`) is repair 2's own open question 3, and there the H07
detail string `attr_site` is a normalised customer header (attr_ names are attribute names that
reach the pack by design, so I do not count that as a rule-(a) leak).

Repro: write the table above, `proofpack map --input sp.csv --out sp.json` answering
`e` / `ignore` / `a`, then `proofpack run ... --mapping sp.json` -> exit 3, first stderr line
`HALT H07: two columns map to the same canonical role`.

No shipped sentence is false ("Ignored columns keep their name" is literally true). Graded
blocker under the task's rule (reachable on a real table) and because the mapper's own prompt
leads there. Fix: in `apply_mapping`, do not let an ignored column claim a canonical name
(drop ignored columns, or key them as `ignored:<original>`; `validate` already parks them in
`unused_columns`), with a test that feeds this table through `map` (answers `e ignore a`) and
`run` and asserts exit 0.

### B3. (sentence only) `profile.py` line 60: "the column stays `categorical`" - sixty distinct two-digit-year dates are typed `string`

`profile_column([f"{i % 28 + 1}/{i % 12 + 1}/24" for i in range(60)])` (60 distinct values) ->
`inferred_type == "string"`, `values not shown (free text)`. The sentence "Two-digit years
(`3/17/24`) are not among them: the century is a guess, and the column stays `categorical`"
generalises over two-digit years; the test feeds `["3/17/24"] * 60` only. The claim that
matters (not typed `date`, H11 not raised) holds for both. Fix: "is not typed `date`" in place
of "stays `categorical`" (README step 3's wording, "two-digit years such as `3/17/24` are not
among them", is already correct).

### B4. (sentence only) `Mapping.read` docstring line 310: "Inspected, each failure H07 `could not be read`: the bytes decode as UTF-8 JSON; ..." - a prior of 100,000 nested `[` is exit 5

`--out m7.json` holding `"[" * 100000 + "]" * 100000`, `proofpack map --input t.csv --out
m7.json --yes` -> **exit 5, `internal error: RecursionError: Stack overflow (used 2912 kB)
while decoding a JSON array from a unicode string`**. `json.loads` raises `RecursionError`
(not a `ValueError`) and the `except (OSError, ValueError, KeyError, TypeError,
AttributeError)` arm does not see it. A BOM-prefixed prior, a directory at `--out` and
`role: 123` through `run --yes` are H07 (fed by hand here); the seven repair-1 shapes and the
five repair-2 shapes are H07 in the suite run above.
Not reachable from a real table (a hand-crafted file); a false sentence in shipped text under
the hard rule. Fix: add `RecursionError` to the arm, or narrow the sentence to "a
`JSONDecodeError` or `UnicodeDecodeError`".

## Non-blocking (reachable, no rule of the task broken, worth a line each)

N1. **`--out` naming an existing directory** (`proofpack map --input t.csv --out ./pack`, the
`run` default directory) at a terminal: the prompt is answered, then exit 5 `internal error:
PermissionError: [Errno 13] Permission denied: '<full local path>'`. The sibling of FA-N6
(missing directory -> H07 before the prompt, closed and re-measured here: 0 prompts, exit 3).
Under `--yes` the same path is H07 `mapping.json could not be read` (the directory is read as
the prior). README step 4's sentence is literal ("does not exist") and stays true.

N2. **`--yes` never compares the prior's roles with the fresh mapping's.** Prior from a cohort
whose `age` is numeric (`age high`, `decided_by: interactive`); the same header set with `age`
now holding `[70-80)` / `[60-70)` -> fresh `age_band high`, all high; `map --yes` exit 0 and
the file is rewritten with `role: age`. `run` would then halt S02 on the non-numeric column - a
typed halt, but the `--yes` rule as written (hash + every role high) is satisfied by a mapping
the table contradicts. Lens-2 N4's class (hand-edited priors) reached by values alone.

N3. **Date shapes outside the six**, each `visit` x 60 through `proofpack map`: `15-Mar-2024`,
`15-mar-2024`, `Mar 15, 2024`, `15/03/2024 10:30`, `2024/03/15 10:30`, `3/17/24` ->
`categorical`, the value printed at count 60, no H11; `20240315` and `45000` -> `int` with `min`
= the value (count 60); `45000.5` -> `float`. `2024-03-15` x 59 + one cell `SECRETV_notadate`
-> `categorical; values: 2024-03-15 (59), <suppressed>` and no H11 (one stray non-missing cell
turns a date column off the `date` type). All aggregates; README step 3 lists the six literal
shapes and "every sampled value", so no sentence is false. `DD-MON-YYYY` is the Oracle/SAS
default export shape.

N4. **`clustering` extra keys**: `case_key: [subject_id, hadm_id]`, `by: "subject_id, hadm_id"`,
`composite: [a, b]` pass `validate_dict` silently (the schema's `clustering` has no
`additionalProperties: false`; README names the six aliases literally). `columns:
"identifiant_séjour"` and `columns: "n°patient"` -> E01 `names 2 columns` (`é` and `°` split
on `[^A-Za-z0-9_]`), a false count on a single accented name; `unit: {a: 1, b: 2}` and `unit:
["subject_id/hadm_id"]` -> H08 `type`; `unit: "case_id "` (trailing space) -> H08 `enum` with no
fix line.

N5. **Underscore-stripped synonym lookup**: `g_t`, `la bel`, `y`, `Y_`, `out_come` -> `y_true
high synonym` (0/1 values); `p_1`, `r_i_s_k`, `output` -> `score` (low on 0/1 values). The
module docstring states the rule ("also matched with underscores removed"); `la bel` and `g_t`
at high read as a stretch.

N6. **Lens mutants: 20 planted (one literal edit each in a copy of the tree, `-m day6 -x`,
`PYTHONPATH` to the copy), 15 killed, 5 SURVIVED (164 passed each):**
L08 `_infer_type` date on `any` value matching instead of `all` (no test feeds a mixed
date/non-date column and asserts it is not `date`; the code is right - N3's last row); L11
`map_headers`'s E01 counts canonical + synonym claims only, not affix (`patient_id` +
`pt_subject_id` measured E01 through the CLI here, but no test feeds an affix pair; README and
`mapping.py` say "affix"); L13 `fold_header` without `.strip()` (the CSV loader strips headers,
so only in-memory callers see it); L14 `apply_mapping`'s E01 counts non-high `case_id` columns
only (two high `case_id` columns reach `apply_mapping` only through a hand-edited prior); L20
`_name_claim`'s `or original in canon` removed (dead: every canonical original normalises to
itself). Killed, with the first failing test: L01 `held_by` counts undecided entries
(`test_accept_of_a_second_holder_is_refused_at_the_prompt`); L02 `held_by` looks at pending only
(`test_edit_to_a_role_another_column_holds_is_refused_at_the_prompt`); L03 `rater_` dropped from
`_single_holder` (`test_attr_twins_...`); L04 month-name shape case-sensitive and L05 month key
`00` (`test_dotted_and_month_name_dates_are_typed_date`); L06 extreme floor `>` and L07
extreme matched on the formatted string (`test_numeric_min_max_below_the_floor_...`); L09 score
candidate at 2 unique (`test_float_within_unit_interval_...`); L10 H11 cover on `h in holders`
(`test_h11_two_columns_sharing_the_event_date_role_...`); L12 name conflict at 3
(`[sepsis_two_labels]`); L15 `Mapping.read` rejects list roles only (`...[123]`); L16 fresh
all-high check skipped on an empty prior summary (`test_yes_is_refused_when_the_fresh_mapping_has_a_medium_...`);
L17 `n_suppressed` at `K-1` (`test_suppression_floor_count_nine_...`); L18 sex 0/1 arm off
(`[diabetes_sex_01]`); L19 accept's held-role check removed (`test_accept_of_a_second_holder_...`).
The committed sweep: **38 planted, 38 killed, 0 survived; 102 s** (note says 98 s).

N7. **Ctrl-C during `Mapping.write`** (raised from `write` with `input` answering `a`):
`KeyboardInterrupt` propagates out of `main()` - a traceback at a console. Outside the span
README step 4 states ("between the table load and the last prompt"), so the sentence holds;
the window is the write itself.

N8. **Carried, re-measured**: `proofpack run` without `--yes` writes `./pack/mapping.json`
with `decided_by: proposed`, the original headers and the value summaries into the pack
directory (`['row_id', 'y_true', 'score', 'sex']` read back from the file); JSON loader exit 5
on `{"columns": {"label": 5}}` and `{"label": null}` (`TypeError`), a lone surrogate in a
header (`UnicodeEncodeError ... '\udce9'` - one character of the header in the message) and
100,000 nested `[` (`RecursionError`); a closed stdout pipe (`| head -1`) -> exit 5
`BrokenPipeError`, no traceback.

N9. **`--yes` on hand-edited priors** (lens-2 N4, carried): `roles: []` -> exit 0; `original:
NOT_A_HEADER` -> exit 0; `confidence: "HIGH"` -> H07; `decided_by: "file "` -> H07; `source: 5`
+ `notes: "abc"` -> read, then H07 on the fresh medium.

N10. **Figures against the repair-2 note** (both shells, `PYTHONPATH` forced): full suite
**528 passed, 1 skipped, 1 xfailed** (Git Bash 47.24 s, PowerShell 44.12 s); `-m day6` **164
passed, 366 deselected**; `ruff check` / `ruff format --check`: `All checks passed!` / `60 files
already formatted`; the sepsis fixture demo (`< NUL` / `< /dev/null`, `PYTHONUTF8=1`): exit 3,
**3485 bytes, byte-identical** across the two shells, the `'Age'` line as the note quotes it;
the new test file copied into the `e92989b` worktree (Ctrl-C test deselected): **19 failed, 2
passed, 1 deselected in 0.72s** - the note's figures. `git diff --name-status e92989b ea526e3 --
tests/`: 1 `M` (the repair-1 module docstring: its two deleted lines are the "three tests" ->
"seven tests" wording), 1 `A`, 0 `D`; added test lines matching skip/xfail/only: 0;
`src/proofpack/stats`, `schema/output_schema_v1.json`, `pyproject.toml`: 0 diff lines; `cli.py`
hunks all inside `_confirm_interactive` and `cmd_map`; changed files `i/lf w/crlf`.

## Lens-2 blockers and findings: closed or not (measured at `ea526e3`)

| lens-2 item | status |
|---|---|
| FA-B1 two partial `case_id` headers H07 not E01 | closed: `row_id,label,prob,patient_nbr,mrn_local` -> both `case_id low` with both notes; `proofpack run` with `clustering.unit: case_id` -> exit 3 `HALT E01: 2 columns are mapped to case_id (proofpack map: keep one, set the others to ignore); reduce your case key to one column`, nothing written; the accept prompt refuses the second holder (`a a e ignore` -> one refusal line) |
| RG-B1 `role: 123` exit 5 under `run --yes` | closed: `run --yes --mapping m123.json` -> exit 3 `HALT H07: mapping.json could not be read`; the sentence replaced by the inspected/not-inspected list (B4 above is the one decode failure the list still overstates) |
| RG-N1 all-high prompt takes `n` | closed for `n no e x` (4 refusals measured) - and reopened as B1 for `""` and `accept` |
| FA-N5 `attr_x y` | closed: `attr_x y`, `attr_`, `rater_` refused; `attr_x_y` written |
| FA-N6 `--out` missing directory | closed (0 prompts, H07); N1 is the sibling |
| FA-N7 attr twins | closed: both `low` with the note, `non_high` 2 |
| FA-N8 / RG-N3 `columns: "a, b"`, `a AND b` | closed: E01 names 2 for the six keys; `a AND b` / `a And b` -> 2 |
| FA-N2 dotted / month-name dates | closed for `15.03.2024`, `17 Mar 2024`, `17 Sept 2024` (H11); N3 lists the shapes still outside |
| FA-N10 Ctrl-C from `load_table` | closed (in the suite; N7 is the write window) |
| FA-N1 / M24, M05 | pinned (both tests pass at `e92989b` as the note says; my L11 shows the affix half of the E01 sentence is still unpinned) |
| FA-N3 / N4 / N9 / RG-N4 | carried as the note says; re-measured in N8, N9, N2 |

## What could not be broken (what was tried)

- (a) **Row-level values or headers in a halt, a log, an error message.** 69 hostile files
  through `proofpack map` as subprocesses with `stdin=DEVNULL`, every cell held by fewer than 10
  rows marked `SECRETV_*`, every probed header `SECRETH_*`: NFC/NFD `Température` twins (H07
  `n_duplicate_headers`), `la<ZWSP>bel` beside `label` (ignore high, "claimed by name") and alone
  (`y_true medium` by values), a mid-header BOM (`'\ufeffprob' -> score high`), a BOM-only header
  (empty header, ignore), `Label ` + `Label` (S04), `LABEL` + `label` (H07), `score` of 0/1
  (low, "only 0/1"), `label` of 60 floats (low, "continuous"), `patient_nbr` + `encounter_id`
  (`case_id low` + ignore, the free-text `encounter_id` with one `SECRETV_` cell listed nowhere),
  `subject_id` + `hadm_id` (high + `row_id medium`, both extremes suppressed), 10,001 rows with
  `SECRETV_ROW10001` in row 10,001 (`n_sampled` 10000, `SITE_A (10000)`), a value held by rows
  9,992-10,001 (10 rows, 9 sampled -> `<suppressed>`) versus rows 9,991-10,000 (`AGG_TEN (10)`),
  200 free-text notes (`values not shown`), 200 values x 10 rows (the top 20 listed at 10 each),
  fifteen `visit` shapes (N3), 0-row, header-only-no-EOL, 0-byte (S04), one 5 MB cell (S04
  `Error`), 600,000-row `mrn` (0.71 s, `10000 unique`, free text), latin-1 and UTF-16 (S04
  `UnicodeDecodeError`), ragged (S04 with counts), NUL byte, a quoted newline in a header, a
  5,000-character `SECRETH_` header (printed in the table by design, nowhere else), 2,002
  columns, `٣٤`, `1e400` (`max inf`), `1_0` (float 10, suppressed at 9 rows), `nan` x 59 (a
  missing token: `98.3% missing`), all-`NA`, sex `1/2`, `0/1`, `M/F`, `1/2/9`, `M/F/U`, a
  repeating int with no name signal (ignore), seven JSON shapes, a directory and a missing file
  as `--input`. Every stderr line carried counts, hash prefixes or canonical names; no
  `Traceback`; every run under 0.8 s. The four exit 5s are N8's day-1 loader shapes.
- (h) **The floor at 9 and 10**: `A` x9 / x10, `7` x9 / x10 as the min, `"1"` x5 + `"1.0"` x4
  (9 rows, suppressed) / x5 + x5 (`min 1`), `a` x5 + `A` x5 (both suppressed - exact strings),
  the `r10000_nine` / `r10000_ten` / `r10001_tenspan` files above, the committed sepsis `Age`
  column. No value below the floor reached `render()`, `to_dict()`, stdout or the written file.
- (b)/(g) **Declarations inferred; sex guessed**: `cmd_map` reads `period` only; `sex` 1/2 and
  0/1 -> `medium` with the note, levels unchanged; no positive class, orientation, threshold or
  clustering appears in the diff or in `mapping.json`.
- (c) **`--yes`**: no prior -> H07; `proposed` -> H07; hash differs (one-letter rename) -> H07;
  `confidence: HIGH` -> H07; `decided_by: "file "` -> H07; fresh medium with a high prior ->
  H07 (both `map --yes` and `run --yes`); `--out` a directory -> H07. L16 killed.
- (d) **Composite key by declaration**: `subject_id, hadm_id` under the six keys, `a AND b`,
  `[a, b]`, plus N4's shapes; by header: `patient_id` + `subject_id`, `Case ID` + `case_id`,
  `patient_id` + `pt_subject_id` -> E01 `2 columns resolve to case_id; ...`; two partial tokens
  -> E01 at apply through `run`.
- (e)/(j) **Tracebacks; closed stdin**: `0<&-` -> H07 in 0.25 s; an empty pipe -> H07; a pipe
  carrying `a\n` -> H07 (not a terminal; nothing written); `stdin=DEVNULL` on all 69 files.
- (f) `_value_candidate` has no `case_id` outcome (read); `grp` of repeating ints -> ignore.
- (i) `column[:10_000]` and the three boundary files above.
- (k) `make_mapping_fixtures.py` imports `csv`, `json`, `unicodedata`, `numpy` and nothing from
  `proofpack`; five `expected.json` files read by hand against their CSV headers and D1 5.2
  (`sepsis_score_holds_01`: `PredictedProbability` low; `mimic_visit_dates`: `visit` ISO with a
  time -> `event_date medium`, `TimeInHospital`-style camel-case headers do not match the H11
  header regex; `sepsis_dup_after_fold` H07; `sepsis_empty_header`; `diabetes_camel_case`
  `PatientNbr` low / `EncounterId` medium) - consistent with what the mapper does.
- (l) `src/proofpack/stats`, `schema/output_schema_v1.json`, `pyproject.toml`: 0 diff lines.
- Prompt: edit to a role a high entry holds (refused), two lows edited to the same `attr_z`
  (second refused), `gender` edited to `age` then `patient_nbr` to `age` (second refused).

## What I could not check

- mintty behaviour of `_stdin_is_terminal` (none here); a human at a real console end to end
  (the prompt path was driven by an injected `input` and a patched `_stdin_is_terminal`).
- The E7 manifest hash of `mapping.json` (E7 not built).
- Real PhysioNet / UCI / MIMIC exports (offline; the fixtures carry header sets only).
- The merge of `a-p1-mapper` onto lane E's tree.
- The mutation sweep in PowerShell (Git Bash only, 102 s).

## Sentences I refused to write in this note

"The floor cannot leak" (nine columns and three boundary files were inspected); "no halt carries
a value" (69 files, the tokens listed); "Enter always accepts" (measured at the two prompt kinds
on one cohort each); "every date export outside the six shapes prints its dates" (six literal
shapes were fed at count 60; at 60 distinct values the column is free text and lists nothing);
"`--yes` is safe" / "`--yes` is unsafe" (nine priors were fed; N2 and N9 name them); "DEC-11 is
closed" (three header pairs and thirteen declaration shapes were fed).
