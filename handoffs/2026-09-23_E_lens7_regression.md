# Lens 7 (regression and record) - build day 8, lane E, repair 6 at `d36c767` - 2026-09-23

**Verdict: PASS.** No blockers. Both lens-6 blockers are closed on the inputs lens 6 fed and on more positions I added:

- **FA-B1 (DEC-66).** The six lens-6 table-cell inputs are now exit 3 with `HALT S02: column role '<role>' holds a control character (U+XXXX) in N row(s)`, and nothing is written. At `941f8a7` they were exit 0 with `run.json` written.
- **RG-B1 (row 74).** A self-referential alias is now exit 3 with an H08 naming the path. I tested it in ten positions of `criteria.yaml`. None reached `RecursionError`.

Every figure and command in the repair-6 note that I re-ran matched in Git Bash and in PowerShell 5.1:

- Suite: `1256 passed, 1 skipped, 1 xfailed`.
- Markers: `day8` 468, `day7` 139, `day6` 285, `day5` 54.
- Pre-fix: `42 failed, 13 passed` at `941f8a7`.
- `design/tokens.json`: equal to D5 section 3.1, with the three re-paired figures recomputed independently.
- Sweep: `103 planted, 103 killed, 0 survived`, exit 0.

Eight non-blocking items follow:

- N1 and N2: the S4 list and carried row 85 are incomplete.
- N3: a non-equivalent mutant of the new gate survives the full suite.
- N4: four sentences generalise.
- N5: two pre-fix failures are attribute aborts.
- N6: an alias chain under a schema-typed key still grows exponentially in jsonschema.
- N7 and N8: records.

Worktrees under `scratchpad/lens-E8-r7-regression/`:

- `new` at `d36c767`: suite, markers, lint and note commands;
- `old` at `941f8a7`: pre-fix runs;
- `pw` at `d36c767`: probes, mutants, wheel, footer and anchor;
- `sweep` at `d36c767`: the committed sweep.

In each worktree I forced `PYTHONPATH=<worktree>/src` and printed `proofpack.__file__` inside that worktree before trusting a figure. Every probe script prints it first. All four worktrees are removed. In the main tree I ran only read-only commands and wrote only this note. I committed nothing.

## Blockers

None.

## Non-blocking

**N1 - The S4 list misses one moved halt code and overstates two others, through `run`.**

I measured through `proofpack run`, with a licence, `--offline`, `make_cohort(n=200)` and a mapping confirmed from the clean table. Then I rewrote row 0 of one column with the value plus `\x01`. Results at `941f8a7` / `d36c767`:

- `y_true` `0\x01`: `HALT H02: y_true contains value(s) outside declared classes and indeterminate values` / `HALT S02: column role 'y_true' holds a control character (U+0001) in 1 row(s)`. Both exit 3. **The S4 list does not name this move.**
- `score` `0.196917\x01` and `age` `65\x01`: `HALT H07: non-interactive mode requires every role at high confidence in the mapping computed from this table, ...` at **both** commits. The S4 bullet says a `score` or `age` cell "was S02 with its type message and is now S02 with the control-character message". That holds for `io.schema.validate` called directly (the note's per-column test). Through `run` it is H07 on both sides.
- `row_id` `r000000\x01`: exit 0 / S02. `site` `S2\x01`: exit 2 with `T8.html` holding 1 raw control byte / S02. `case_id` `c\x01`: exit 0 / S02. The note's "new halt" bullet covers these three.

Repro: `pw` probe `test_probe_every_cohort_column`, which is in `scratchpad/lens-E8-r7-regression/probe/test_zz_lens7_probe.py`, copied into `tests/`.

**N2 - Carried row 85 names `sex` only.** The same probe shows that `score` and `age` holding U+0001 also halt H07 before the DEC-66 check, at both commits: exit 3 and nothing written, but the message names confidence, not the column's control character. `sex` stays H07 even when the mapping was confirmed from the clean table and the CSV was edited afterwards (`HALT H07: non-interactive mode requires every role at high confidence in the mapping computed from this table ...`).

**N3 - A non-equivalent mutant of the DEC-66 gate survives the full suite.**

- The mutant `b_period_col_dropped` deletes `or h == pcol` from `columns_read_by_validate`.
- Full suite under the mutant, with `PROOFPACK_TR39_FULL` set: SURVIVED (pytest exit 0 over `tests/`).
- Literal: `schema.validate` on 40 rows of `y_true`, `score`, and `rater_visit` = `2024-03-15\x01`, with `period={"column": "rater_visit", "granularity": "quarter"}`. At `d36c767` that gives `S02 column role 'rater_visit' holds a control character (U+0001) in 40 row(s)`. The mutant accepts it, with period levels `['2024-Q1']`.
- No test feeds a period column that is neither canonical nor `attr_`.
- Reach through the CLI needs an interactive `map` edit. A hand-edited `mapping.json` role is `HALT H07: mapping.json maps a column to rater_visit but the mapping computed from this table gives it event_date`.
- `coarsen_date("2024-03-15\x01", "quarter")` returns `2024-Q1`, so under the mutant the control byte does not reach the page on this input.

Six other mutants I planted were killed by `tests/test_e8_repair6.py` alone:

- `open_ids` never discarded;
- `finished` ignored;
- `continue` -> `break` in the column loop;
- the count in the message forced to 1;
- the `attr_` branch dropped;
- `self_reference_at` result forced to `None`.

**N4 - Sentences that generalise (the hard rule).** In each case I constructed the counter-example and ran it:

- `design/tokens.json` `source`, new in this diff: "Each token's surface is in its `on` key". 10 of the 19 colour entries have no `on` key. `brand-strong` is `role: text` with no `on`. The other nine are the seven surfaces plus `stop-line` and `ok-line`.
- `io/schema.py`, the `_CONTROL_CELL` comment: "... searched for in the table's cells". The search covers only the columns `columns_read_by_validate` lists. The commit's own guard test feeds U+0001 in `rater_1` and `n\x1b[31m` in `notes`, and both are accepted.
- `columns_read_by_validate` docstring: "The column keys `validate` reads cells from". With `period={"column": "period", ...}` and an `event_date` column present, `validate` builds its Table without reading `event_date`. Yet `event_date` is listed and checked: a cell `2024-01-0\x013` there halts `S02 column role 'event_date' ...`. The behaviour is conservative; the sentence is wrong.
- The repair note heading "An ordinary table is unaffected (measured)" is the sentence its own refused list refuses ("The ingest check leaves every ordinary table unaffected"). The body names the 41 files, 82,451 cells and the cohort. The heading should name them too.

**N5 - Two "fails pre-fix" tests fail at `941f8a7` only on an attribute abort. Three guards pass there.**

- `::test_a_shared_but_not_self_referential_alias_is_accepted` fails with `AttributeError: ... no attribute 'self_reference_at'`. Its docstring says so. The behaviour it pins, `validate_dict` accepting the shared alias, also held at `941f8a7`.
- `::test_the_plants_cover_every_column_validate_reads_from_the_table` fails with `AttributeError: ... 'columns_read_by_validate'`.
- The three guards (`::test_a_missing_block_halts_before_the_control_character_walk`, `::test_cells_of_columns_validate_does_not_read_and_edge_whitespace_pass`, `::test_a_trailing_tab_in_a_site_cell_is_stripped_before_the_check`) pass at `941f8a7`, as the note declares.
- None of these five pins the repair. The other 37 new-file failures and the 3 `test_render_theme.py` failures are on the assertion the note quotes.

**N6 - An alias chain under a schema-typed key is still exponential, in jsonschema, not in the walk.**

`validate_dict` with the chain as `criteria[0].value` (H08 `criteria/0/value: type`):

| Depth | `d36c767` | `941f8a7` |
|---|---|---|
| 16 | 0.01 s | 0.04 s |
| 20 | 0.14 s | 0.70 s |
| 22 | 0.55 s | 3.03 s |
| 24 | 2.38 s | not run |

As `model.name` it gives 0.55 s at depth 22 on `d36c767` and 3.78 s on `941f8a7`. At depth 20, cProfile puts 0.144 of 0.146 s inside `jsonschema` `iter_errors`. The committed test feeds `model.extra` only (0.001 s at depth 24). The DEC-65 walk itself no longer expands the chain. This extends carried row 86: the expansion happens in `run.json` and in jsonschema's error path.

**N7 - Docstrings of the new functions that name no D1 / D4 / D5 line or oracle:**

- `self_reference_at`;
- `columns_read_by_validate` (it names `schema_v1.json` but not D1 section 1);
- `_path_text` and `_children`;
- `_string_hit`, which has no docstring.

`check_control_characters` names DEC-66 and D1 lines 257-272 and 274; I checked the line numbers against D1. D1 section 5 step 6 does assign no code to a malformed table value, as the note says: H01-H12 only. S02 is `errors.SCHEMA_CODES` "column value cannot be coerced to its declared type". The choice is recorded for Josh.

**N8 - Records.**

- The golden masking touches `manifest.numpy` only. `run_id`, `started` and `duration_s` are assembler constants (`test-only-assembler`, `2026-09-18T00:00:00Z`, `None`), as lenses 5 and 6 recorded. The orchestrator's check wording ("masking touches only run_id, started and duration_s") describes this case.
- The note's figures need `PROOFPACK_TR39_FULL` (lens-6 N6, carried). I set it for every pytest run.
- The commit trailer is `Claude Opus 5.5`, not the orchestrator's `Claude Fable 5.1`. The note records this as a decision (the harness attribution line). Earlier E8 commits carry the same trailer.

## What I could not break

- **Suite, markers and lint** (`new`, `PROOFPACK_TR39_FULL` set):
  - Full suite, Git Bash: `1256 passed, 1 skipped, 1 xfailed in 144.95s`.
  - Full suite, PowerShell 5.1: the same counts in `139.92s`.
  - `day8` 468 / `day7` 139 / `day6` 285 / `day5` 54 passed in both shells. `day4` 182, `day3` 29 + 1 xfailed, `day2` 40, `day1` 59 + 1 skipped, `ap2` 88 (Git Bash).
  - `--collect-only`: day1 60, day2 40, day3 30, day4 182, day5 54, day6 285, day7 139 (equal to `7b2ca2a`), day8 468 (426 + 42).
  - `ruff check`: `All checks passed!`. `ruff format --check`: `167 files already formatted`. Both shells.
- **Fails pre-build.** `tests/test_e8_repair6.py`, plus the new `test_render_theme.py` copied in as `test_render_theme_new.py`, run at `941f8a7`: `42 failed, 13 passed`. The first `E` lines are the note's:
  - 3 `RecursionError` (alias positions);
  - 2 `AssertionError: internal error: RecursionError` (CLI);
  - `AssertionError: 11.237291499972343` (chain; note 7.68 s; timing);
  - `RecursionError` (5,000-deep);
  - 6 `run written: ...run.json` (the lens-6 CLI inputs);
  - 15 `DID NOT RAISE` plus 3 type-halt detail mismatches (`score`, `indeterminate`, `age`) plus `('S02', {'count': 1})` (`dataset`);
  - the three sentence asserts;
  - the tokens tuple;
  - the sweep list;
  - `assert 6.8 == 6.189...`, `9.11 == 7.8808...`, `10.02 == 8.6520...`.
- **Nothing weakened.**
  - `git diff --name-status 941f8a7 d36c767 -- tests/` shows `A test_e8_repair6.py` and `M test_render_theme.py`, with no deletions.
  - Added `skip` / `xfail` / `.only` / TODO lines: 0. Removed `pytest.mark` / `pytestmark` lines: 0.
  - In `test_render_theme.py`, `D5_ERRATA` is removed. `entry.get("on", bg) == bg` became `entry["on"] == bg`, which is stricter.
  - `day8` is declared in `pyproject.toml`. `ci.yml` runs every declared marker, and installs with `uv sync --all-groups --locked` (3 times). `uv.lock` names `jinja2` 3.1.6.
  - `git diff 941f8a7 d36c767` over `cli.py`, `run.py`, `errors.py`, `criteria.py`, `gates.py`, `pyproject.toml`, `uv.lock`, `schema/`, `stats`, `render`, `narrate`, `templates` and `.github`: 0 lines.
  - `941f8a7` and `ea2f743` differ only in three handoff files.
- **RG-B1 in ten positions** (`probe/selfref.py`, `validate_dict`, `d36c767`). Each gives H08 `the value contains itself`, detail `reason: self_reference`, at the path shown:
  - `--- &r` root with `zz: *r` -> `zz`
  - `prevalence: &p [*p]` -> `prevalence/0`
  - `clustering: &c {unit: *c}` -> `clustering/unit` (passes E01 first)
  - `clustering: {unit: &u [*u]}` -> `clustering/unit/0`
  - `subgroups: &s [*s]` -> `subgroups/0`
  - `criteria: &k [*k]` -> `criteria/0`
  - `model: &m` with `me: *m` -> `model/me`
  - `fairness: &f {x: *f}` -> `fairness/x`
  - `zz: &z {k: [*z]}` -> `zz/k/0`
  - `operating_points: &o [*o]` -> `operating_points/0`

  Through the CLI, lens 5's `alias.py` gives `exit 3`, `No document was written.`, `pack exists: False` in both shells.
- **FA-B1 and DEC-66.** Lens 6's scripts against `new`, in both shells:
  - `p3_fair.py`: `3 {} HALT S02 ... 'race' ... (U+0001) in 400 row(s)`.
  - `p2_star.py`: `race` soh / c1 / nul give rc 3 with U+0001 / U+0085 / U+0000 and counts 400 / 400 / 200. `attr_colour` nul gives rc 3, U+0000, 200. The `html` pair gives rc 0, `<script>` 0 times raw and `{{ 7*7 }}` literal once.
  - `p7_site.py`: `site` U+001B 266 rows; `device` U+0000 200; `sex` H07.

  My additions:
  - `compare` with the prior's `site` cells `S\x011` / `S\x012` / `S\x013`: exit 3, `HALT S02 ... 'site' ... in 200 row(s)`, no directory. At `941f8a7` it was `HALT H09 ... unknown level`.
  - `case_id` `c\x01`: S02.
  - `attr_Colour` (the mapping lower-cases it): S02 `attr_colour`.
  - Unread columns `notes`, `rater_1` and `Site_extra`, holding `re\x01d` / `bl\x1b[31mue` / `x\x85y`: rc 0, with 0 raw and 0 JSON-escaped control characters in `run.json`, `ingest_report.json`, `pseudonyms.json` and `T8.html`, and 0 raw in the printed stream.
  - Edge characters that `strip()` removes pass (`\x1fS9`; `18-64\x85` in `age_band`): rc 0, 0 bytes out. By my own run, `strip()` removes U+0009-U+000D, U+001C-U+001F and U+0085, and keeps U+0001, U+007F and U+009F. The docstring's list is a subset and does not claim to be complete.
- **Ordinary tables** (`measure.py`, run at both commits):
  - `files 41 cells 82451 control hits 0`. The six site copies hash-equal `proofpack-site` `public/demo` at `95e9575`.
  - Synthetic cohort: rc 0, 66 claims, 1 criteria row. `run.json`, with the volatile manifest keys removed, is 483,366 bytes at both commits and byte-identical (`cmp` silent).
  - My own byte scan of the 217 csv / json fixture files under `tests/fixtures/` finds 0 C0 or C1 bytes other than CR and LF.
  - `map` on the `race` `re\x01d` table prints 1 raw 0x01 and 1 raw 0x1b at both commits (row 84, carried).
  - The 20-level chain through `run` gives `run.json` 155,418,186 bytes, rc 0, at both commits (row 86). I deleted those two files afterwards.
- **DEC-67.** My own WCAG 2 sRGB computation, sharing no code with the repository, gives 6.1890 / 8.6520 / 7.8809 against `honesty-bg` / `stop-bg` / `ok-bg`, and 6.8025 / 10.0196 / 9.1109 against `bg`. `tokens.json` now carries `on` = the `-bg` token, D5's `6.2:1` / `8.7:1` / `7.9:1` verbatim, and `6.19:1` / `8.65:1` / `7.88:1` computed.
  - A script parsing D5 section 3.1's table matches all 19 token / hex pairs to `tokens.json` (0 mismatches, 19 entries). Both font stacks, the scale, line heights, tracking, spacing, radii, layout and print values equal D5 section 3.1 / 3.5 by reading.
  - `git grep` for `6.80`, `10.02`, `9.11` and "do not match the formula" outside `handoffs/` finds only the two tests that assert the sentence's absence, plus CSV and lock digits.
- **Every note command, in both shells, byte-equal where printed:**
  - `doctor --offline`: 17 `[ok`, `All essential checks passed.`, exit 0.
  - `tr39_subset.py --check`: `vendored subset matches`, exit 0.
  - `--list`: 274 lines (34 / 112 / 25 / 87 / 16).
  - No-licence run: exit 4, and `runjson.py` gives `253943 bytes 20 keys 70 claims 0 rejections 3 refs [0, 1, 2, 2, 2, 3, 4, 5, None] CRLF 0 BOM False`. The Git Bash and PowerShell `run.json` are equal once `run_id`, `started` and `duration_s` are removed.
  - No mapping: H07, exit 3, `dir=no`.
  - `licence show` / `verify`: `refused (no_file)`, exit 4.
  - `html_run.py`: `T8.html bytes 40375 CRLF False BOM False`.
  - `repros5.py` / `repros6.py` (Git Bash): the note's lines, including the `FileNotFoundError` tail.
  - `offline_and_imports.py`: `rc 0 socket calls 0`.
  - `paths.py`: the three rc-3 lines, `file unchanged True`.
  - Imports with the six optional modules set to `None`: `imports ok; loaded: []`.
  - Verdict grep: `5 passed, 1253 deselected`. E6 schema test: `1 passed`.
- **Wheel.** `python -m uv build --wheel`, installed with `pip --target` into a fresh `--without-pip` venv. Its `site-packages` holds `bin`, `proofpack` and `proofpack-0.1.0.dev1.dist-info` (no `.pth`). `proofpack.__file__` and `_schema\tokens.json` resolve inside the venv, and the shipped file reads `honesty-bg 6.19:1`. With the `"design/tokens.json" = ...` force-include line removed, the wheel test fails: `FileNotFoundError: packaged resource 'tokens.json' not found`. The line was restored and the test passes again.
- **Golden.** An independent render of the assembler document at both commits, with `numpy` set to `x.y.z`, gives 40,030 bytes, sha256 `d941a70786e3619d...`, equal to the committed golden. The tokens change does not reach the page.
- **Footer.** With the `<footer class="page-footer">` line removed from `base.html`, the footer tests fail with `assert 0 == 3`, `0 == 1`, `0 == 2` and `(0 == 3)`.
- **Anchor label.** With the AI-DSF map rows' status set to `final`, the anchor test fails with `assert ([])`.
- **Corpus.** 146 files, each with `rule` and `expected_reason_code`. `tests/test_claims.py` collects 146 ids, and they equal the file stems (`diff` empty).
- **Sweep** (`sweep` worktree, `--marker day8`, committed tree): `103 planted, 103 killed, 0 survived; 1463 s`, exit 0. `git status --short` is empty afterwards. The note gives 1291 s; I read the difference as machine load, since my probes ran alongside. The four new mutants are each killed with `1 failed`:
  - `schema_dec66_check_not_called`: 290 passed;
  - `schema_dec66_c1_dropped`: 294 passed;
  - `declare_self_reference_check_dropped`: 278 passed;
  - `declare_walk_enters_shared_objects_again`: 283 passed, 30.01 s.

  These equal the note's figures.

## What I could not check

- The day-7 clustered run test. It is not in this diff, so there is nothing new to re-run. Lenses 1-5 cover it.
- The interactive `map` route that would let a `rater_` role carry the period column (N3).
- CI on GitHub. Nothing is pushed.
- What a regulator's viewer or a terminal does with the bytes. I counted bytes only.

## Sentences I refused to write

- "DEC-66 refuses every control character in the table." Written instead: the inputs above, the unread columns that pass, the characters `strip()` removes, and N1-N3.
- "The self-reference class is closed." Written instead: the ten positions and the CLI repro.
- "Alias chains are fast now." Written instead: N6's timings under `criteria[0].value`.
- "Repair 6 introduced no regression." Not written. What I measured is above.

## Re-run these

```bash
L=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/a743e7e5-3be8-4d70-9ed0-681f5784a106/scratchpad/lens-E8-r7-regression
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/new d36c767
cd $L/new && export PYTHONPATH=$L/new/src PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt
python -c "import proofpack;print(proofpack.__file__)"          # must print $L/new/src/...
python -m pytest -q -p no:cacheprovider                          # 1256 passed, 1 skipped, 1 xfailed
bash $L/run_note.sh $L/new new                                   # the note's commands (PowerShell: $L/run_note.ps1)
cp $L/probe/test_zz_lens7_probe.py tests/ && python -m pytest -q -s tests/test_zz_lens7_probe.py   # N1, N2, unread columns
WT=$L/new ARGS=tests python $L/probe/mutants.py b_period_col_dropped    # N3: SURVIVED
WT=$L/new python $L/probe/chain_value.py                          # N6 timings
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $L/new
```

## What the next repair needs

1. N1: add `y_true` (H02 -> S02) to the S4 list. Scope the `score` / `age` bullet to `validate` and state that `run` gives H07 on both sides.
2. N2: widen row 85 to `score` and `age`.
3. N3: a test that feeds a period column that is neither canonical nor `attr_` (in-process is enough), and the matching sweep mutant.
4. N4: reword the four sentences to name what is inspected. The fix for the `tokens.json` sentence is "the nine tokens with a stated contrast carry their surface in `on`".
5. N6: record it with row 86 for Josh (a node or size bound on the declaration is a new rule).
