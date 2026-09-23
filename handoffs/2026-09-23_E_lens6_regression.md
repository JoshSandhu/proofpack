# Lens 6 (regression and record) - build day 8, lane E, repair 5 at `ea2f743` - 2026-09-23

**Verdict: FAIL.** One blocker. Repair 5 added a recursive walk, `control_character_at`, with no
guard against a self-referential YAML alias. A `criteria.yaml` whose first line is
`zz_extra: &a [*a]` halted `H08 declaration invalid at <root>: additionalProperties` (exit 3) at
`2a9a6e2`. At `ea2f743` it is `internal error: RecursionError: maximum recursion depth exceeded`
(exit 5). The same happens when the model name also holds `"Tri\0age"`. That document is a
counter-example to the new comment "... are H08 naming the field" and to the note's "each halts
there". Lens 3 graded the same shape (exit 5 `RecursionError` on a customer file, FA-B4) as a
blocker, so I grade this one the same way. Josh may downgrade it. The class is older than this
repair: the same alias under `model:` or `criteria[0]` is exit 5 at both commits (below).

Apart from that, each figure and command in the repair-5 note matched in Git Bash and in
PowerShell 5.1. Suite: `1214 passed, 1 skipped, 1 xfailed`. Markers: `day8` 426, `day7` 139, `day6`
285, `day5` 54. The new test file at `2a9a6e2` gives `64 failed, 4 passed` in both shells, and each
failure is an assertion (none is an import error). The day-8 sweep gives `99 planted, 99 killed, 0
survived`, exit 0, and the tree is clean afterwards. FA5-B4's literal no longer reproduces: through
the CLI it now gives exit 3, no directory, `H08 ... model/name: control character U+0000`.

Seven non-blocking items follow. N1 is a sentence violation in `declare.py` that a test in the same
commit falsifies. N2 is three of my mutants that survive `-m day8` and are not equivalent. N3 is a
false sentence in `design/tokens.json` about D5's contrast figures; it has been there since the E8
build, and lenses 1-5 did not raise it.

Worktrees under `scratchpad/lens-E8-r6-regression/`: `new` at `ea2f743`, `old` at `2a9a6e2`, `probe`
at `ea2f743` (probes and mutants), `sweep` at `ea2f743`, and `base` at `23f3d9f` (the RG-N6 check).
In each I forced `PYTHONPATH=<worktree>/src`, and `python -c "import proofpack;print(proofpack.__file__)"`
printed that worktree's `src\proofpack\__init__.py` before I trusted any figure. Every probe script
prints the path first. All five worktrees are removed. In the main tree I ran only read-only
commands, wrote only this note and committed nothing.

## Blockers

### B1 - `control_character_at` recurses without a guard: a self-referential alias that halted H08 at `2a9a6e2` is exit 5 `RecursionError` at `ea2f743`

`src/proofpack/io/declare.py::control_character_at` walks each dict and list with no record of what
it has already visited. PyYAML `safe_load` turns `&a [*a]` into a list that contains itself.
`validate_dict` now calls the walk (`_check_control_characters(data)`) before the jsonschema step.
At `2a9a6e2` that step reported the unknown root key as H08 first.

Measured (the `_prepare` CSV and mapping from `tests/test_run_cli.py`, 200 rows, `make_criteria()`,
licence home, `--offline`, run through `python -m proofpack.cli run`):

| `criteria.yaml` | `2a9a6e2` | `ea2f743` |
|---|---|---|
| first line `zz_extra: &a [*a]` | `HALT H08: declaration invalid at <root>: additionalProperties`, exit 3, no directory | `internal error: RecursionError: maximum recursion depth exceeded`, exit 5, no directory |
| the same, plus `name: "Tri\0age"` under `model` | exit 3, the same H08 | exit 5, the same `RecursionError` |
| the same without the alias line | exit 4 (licence `unknown_key_id` in that home; run.json written) | `HALT H08: declaration invalid at model/name: control character U+0000; remove it`, exit 3 |
| `extra: &a [*a]` under `model:` | exit 5 `internal error: ValueError: Circular reference detected` | exit 5 `RecursionError` |
| `extra: &a [*a]` in `criteria[0]` | exit 5 `ValueError: Circular reference detected` | exit 5 `RecursionError` |

Git Bash and PowerShell 5.1 give the same result for the first row. Nothing is written in any
row that ends in exit 5, so no data leaves. The defect is a typed halt that became an untyped crash
on a customer file, in the gate this repair added. The last two rows show the class was already
there at `2a9a6e2`, in other positions.

Repro (from a worktree at `ea2f743`, with a confirmed mapping beside `test.csv`): put
`zz_extra: &a [*a]` as line 1 of `criteria.yaml`, then run
`python -m proofpack.cli run --input test.csv --criteria criteria.yaml --out pack --offline`.
It prints `internal error: RecursionError ...` and exits 5. At `2a9a6e2` the same command gives H08 and exit 3.

## Non-blocking

**N1 - Sentence violations in `declare.py` (the hard rule).**
- Module docstring (line 6): "... is also H08, and so is a string holding a control character
  (DEC-65, `control_character_at`)". The commit's own test contradicts this.
  `tests/test_e8_repair5.py::test_tab_and_line_feed_are_accepted_in_the_three_free_text_fields`
  feeds `"line one\n\tline two\n"` as a justification, and `validate_dict` accepts it.
- The `MULTILINE_FIELDS` comment: "C0 controls ..., DEL ... and C1 controls ... in a string of
  `criteria.yaml`, key or value, are H08 naming the field." The note records no counter-example run
  against this sentence. I ran three, all with `"Tri\0age"` as the model name:
  - with the `prevalence` block removed: `H08 'mandatory declaration block(s) missing: prevalence'`,
    which names no field;
  - with `clustering.unit: "a b"`: `E01 'clustering.unit names 2 columns; ...'`. The note's
    decision 3 records this order, but the comment does not;
  - with a leading `zz_extra: &a [*a]`: exit 5 (B1).
- `control_character_at` docstring: "... ; `None` if none does." On a self-referential input the
  function raises `RecursionError` (B1).
- The note's "Because the assembler, `run`, `compare` and `map --criteria` all read the document
  through `validate_dict`, each halts there" is false on the B1 document.

**N2 - Three of my mutants survive `-m day8` (`probe` worktree; `425 passed, 1 skipped` each; tree
restored after each).** None is equivalent. I ran each with the inputs below, and each changes an outcome:
- `M8`: `_check_control_characters(data)` moved from above the authored-field loop to just above the
  jsonschema step. With criterion id `"C\x1b[31m"` and an empty author, `ea2f743` gives
  `H08 declaration invalid at criteria/0/id: control character U+001B`. The mutant gives
  `H08 'criterion C\x1b[31m lacks author'`, which puts a raw ESC in the printed message, as `2a9a6e2`
  does. The `validate_dict` comment says the gate runs "before any message below that prints a
  criterion id". The code does this, but no test pins it.
- `M5`: `"decided_by"` dropped from the mapping walk. With `decided_by: "file\x01\x1b[31m"`,
  `ea2f743` gives exit 3 `H08 mapping.json invalid at decided_by: control character U+0001`. The
  mutant gives exit 3 `H07 ... not confirmed`, whose detail escapes the value as JSON
  (`"file\u0001\u001b[31m"`); I counted 0 raw control bytes printed. The docstring names
  `decided_by` as read, but no test feeds it.
- `M2`: keys checked with `_CONTROL_MULTILINE` instead of `_CONTROL`. With the key `"a\tb"` inside
  `model`, `ea2f743` gives `H08 model (key): control character U+0009`. The mutant accepts the
  document, as `2a9a6e2` does.

**N3 - `design/tokens.json` `source` asserts a mismatch that does not exist (it has been there
since the E8 build; lenses 1-5 did not raise it).** The sentence is "Three of D5's stated ratios do
not match the formula and are kept as stated: honesty 6.2 (computed 6.80), stop 8.7 (computed
10.02), ok 7.9 (computed 9.11)". I recomputed with the WCAG 2 sRGB formula, sharing no code with
the repository. Each token against its own `-bg` surface gives D5's figure: `#8a4b00` on `#fdf3e3`
**6.19**, `#7f1d1d` on `#fdeaea` **8.65**, `#14532d` on `#e4f2e8` **7.88**. D5's figures match the
formula. The difference is that `tokens.json` pairs these three tokens with `on: "bg"`. Every hex
value in `tokens.json` equals D5 section 3.1 row by row: 19 colours, both font stacks, the type
scale, line heights, spacing, radii, focus, measure and wrap. The section 3.5 print values
(A4, `20mm 18mm 26mm`, 0.72rem) are equal too. The other computed ratios match mine to 2 dp:
16.46, 7.09, 4.57, 1.34, 9.97, 11.69. All the text pairs pass 4.5:1 either way.

**N4 - A lone surrogate in customer text is exit 5 at both commits (not DEC-65's range; record and
carry).** With `name: "Tri\ud800age"` (a YAML escape), `run` gives
`internal error: UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' ... surrogates
not allowed`, exit 5, and no directory, at both `2a9a6e2` and `ea2f743`. `validate_dict` accepts the
document. `U+2028`, `U+200B` and `U+FEFF` in the model name are accepted too, which the note carries
as format characters.

**N5 - The S4 list omits one precedence change.** The DEC-65 H08 now precedes the authored-field H08
and the H09 references. At `2a9a6e2`, criterion id `C\x1b[31m` with an empty author gave
`criterion C\x1b[31m lacks author`, and op id `op\x001` gave H09. Both are now control-character
H08s. The exit code (3) is unchanged, and no flag, default, path or JSON key changed.
`git diff 2a9a6e2 ea2f743` is empty for `cli.py`, `run.py`, `errors.py`, `pyproject.toml`, `uv.lock`
and `schema/`, as the note says. B1's exit-code change is not in the list.

**N6 - Figures that need the TR39 file.** In a worktree without `PROOFPACK_TR39_FULL`, the suite is
`1213 passed, 2 skipped, 1 xfailed` and `-m day8` is `425 passed, 1 skipped`. With the variable
pointing at `workflows/data/confusables-18.0.0.txt`, they are `1214 passed, 1 skipped, 1 xfailed` and
`426 passed`, which are the note's figures. This carries lens-5 N4.

**N7 - Records.**
- `control_character_at`'s docstring names no D1 / D4 / D5 line. The comment above it cites D1
  section 6 (line 296: "Free-text declaration fields (`justification`, `description`, `source`)
  never leave the machine"). That section is D1's egress schema, not a field definition. D1 has no
  other list of free-text or multi-line fields, so the choice is defensible. It rests on an egress
  sentence.
- `mapping._check_control_characters` names DEC-65 and a test id, and no D-document line.
- The sweep's wall time was 1191 s against the note's 1131 s, on the same 99 mutants. I read this
  as machine load. It is not a finding.

## What I could not break

- **The note's figures, re-run.**
  - Full suite `1214 passed, 1 skipped, 1 xfailed`: Git Bash 91.40 s, PowerShell 89.16 s.
  - Markers, same in both shells: `day8` 426; `day7` 139; `day6` 285; `day5` 54; `ap2` 88;
    `day4` 182; `day3` 29 + 1 xfailed; `day2` 40; `day1` 59 + 1 skipped.
  - `--collect-only` counts: day1 60, day2 40, day3 30, day4 182, day5 54, day6 285, day7 139.
    These equal the `7b2ca2a` counts. `day8` collects 426 (358 at lens 5, plus the 68 new tests).
  - `ruff check`: `All checks passed!`. `ruff format --check`: `163 files already formatted` at
    `ea2f743` and `162` at a clean `2a9a6e2`.
- **Fails pre-build.** Copying `tests/test_e8_repair5.py` into `2a9a6e2` gives `64 failed, 4 passed`
  in both shells. The four that pass are the ones the note names, and their docstrings say "guard" or
  describe `clustering/unit`'s E01. First `E` lines:
  - 37 are `Failed: DID NOT RAISE HaltError`: 22 of the 43-field cases, 13 of the 14 literals,
    the key test and the assembler test;
  - 17 of the 43-field cases fail on the halt detail, because the schema's
    `{'path':..., 'validator': 'enum'|'pattern'|'oneOf'}` is not `{'field':..., 'codepoint': 'U+0001'}`;
  - 3 of the 43-field cases are H09 (`unknown metric` once, `unknown operating point` twice);
  - the `op\x001` literal gives `assert ('H09', ...) == ('H08', ...)`;
  - `run written: ...run.json` for the CLI test;
  - `('notes', 'run written: ...` for the mapping test;
  - the three RG-N6 docstrings, each without the sentence;
  - the sweep list, `{'declare_dec..._called', ...} <= {...}`.

  Each equals the note's quote. No test aborts on an import error.
- **RG-N6 at `23f3d9f`.** With the current `test_e8_repair4.py` copied in, the three guards give
  `2 failed, 3 passed`. The failures are `no_score_column` and `score_not_positive_class_probability`,
  as the note says.
- **The 43-field probe** (`probe_fields.py`):
  - at `2a9a6e2`: 43 fields; 16 reach `run.json` and 11 reach `T8.html`; `model/name` appears 4
    times on the page; rc 0 ×2, 2 ×14, 3 ×27.
  - at `ea2f743`: all 43 give exit 3, 42 of them H08 and `clustering/unit` E01. This matches the
    note.
- **Every command in the note, in both shells, byte-equal where printed:**
  - `doctor --offline`: 17 `[ok` lines, `All essential checks passed.`, exit 0.
  - `tr39_subset.py --check`: `vendored subset matches`, exit 0.
  - The no-licence run: exit 4, and `runjson.py` gives
    `253943 bytes 20 keys 70 claims 0 rejections 3 refs [0, 1, 2, 2, 2, 3, 4, 5, None] CRLF 0 BOM False`.
  - The no-mapping run: `HALT H07: run proofpack map first ...`, exit 3, no directory.
  - `licence show`: `refused (no_file)`, exit 4.
  - `html_run.py`: `T8.html bytes 40375`.
  - `repros5.py`: B1 to B4 equal to the note.
  - `repros6.py`: B1 `[None x5]`, B2 and B3 as carried, and B4 the H08 line with
    `No document was written.`
  - `offline_and_imports.py`: `rc 0 socket calls 0`.
  - `paths.py`: `map --criteria` (3, H08 model/name U+0000); `compare` (3, the same, dir False);
    `map --yes` (3, `mapping.json invalid at roles/0/notes/0 ... U+0001`), file unchanged True.
- **The sweep** (`--marker day8`, committed tree): `99 planted, 99 killed, 0 survived; 1191 s`, exit 0,
  and `git status --short` is empty afterwards. Each of the seven `dec65` mutants is killed with
  `1 failed`. `--list` gives 270 lines: 34 day5, 112 day6, 25 day7, 83 day8, 16 ap2.
- **Mapping text the repair does not read.** I fed each of the following with `\x01` and `\x1b[31m`:
  - every entry's `source`: exit 0;
  - `confidence: "high\x01"`: exit 3, H07 (not high);
  - `value_summaries` strings and an `examples` list: exit 0;
  - an extra key `extra\x01: "x\x00"` in a role entry: exit 0;
  - `decided_by` as a list: exit 3, H07.

  Across `run.json`, `ingest_report.json`, `pseudonyms.json`, `T8.html` and the printed stream I
  counted 0 raw C0 bytes, 0 C1 and 0 JSON-escaped, at both commits.
- **The carried table-cell row.** With the `site` cells prefixed `\x01` or `\x1b[31m`,
  `make_criteria()`, a licence and 200 rows: exit 0; `run.json` 38 escaped; `pseudonyms.json` 3;
  `T8.html` 0 raw and 0 escaped. `T8.html` holds no site level (`S1`/`S2`/`S3` 0 times). A `\x85`
  prefix leaves 0 everywhere. This equals the note's carried row.
- **Declaration edges.**
  - `\x85` and `\x1c` in the model name give H08.
  - An int key `1` holding `"a\x01"` gives H08 `model/1`.
  - `!!binary` bytes in the name, justification or version give H08 `type`.
  - A CRLF `criteria.yaml` (78 CR bytes) with a literal-block justification loads as
    `'line one\nline two\n'` and is accepted.
  - `a: "x\ry"` loads as `'x y'`.
  - `_IDENT` matches `attr_x\n`: `True`.
  - Mapping `notes` nested 400, 800 and 950 deep: exit 0 at both commits.
  - A YAML list 100 and 300 deep: exit 3 at both commits.
  - The three demo and fixture criteria YAMLs (the site's `public/` and `dist/` copies, and
    `mimic_composite_key.criteria.yaml`) give no hit.
- **Nothing weakened.**
  - `git diff --name-status 2a9a6e2 ea2f743 -- tests/` shows `M test_e8_repair4.py`,
    `A test_e8_repair5.py` and no deletions.
  - The diff adds no skip, xfail, `.only` or TODO, and removes no `pytestmark` or `mark.day`.
  - The changed `test_e8_repair4.py` lines are docstrings only.
  - CI runs every marker declared in `pyproject.toml` (`day8` is declared). `uv.lock` names
    `jinja2`. CI installs with `uv sync --all-groups --locked`.
- **Imports.** With `jinja2`, `markupsafe`, `scipy`, `cryptography`, `statsmodels` and `sklearn` set
  to `None`, these import: `proofpack`, `.stats`, `.io.declare`, `.io.mapping`, `.narrate.checker`
  and `.gates`. Loaded: `[]`.
- **Corpus.** 146 files, each with `rule` and `expected_reason_code`. The parametrised test collects
  146 ids, and they equal the file stems (`diff` empty). `146 passed`.
- **Golden.** An independent render of the assembler document, with `numpy` masked to `x.y.z`,
  is 40,030 bytes, sha256 `d941a70786e3619d...`, and equals the committed golden at both commits.
  The mask touches `manifest.numpy` only. `run_id`, `started` and `duration_s` are assembler
  constants (`test-only-assembler`, `2026-09-18T00:00:00Z`, `None`), as lens-5 N7 records.
- **Footer.** With `<footer class="page-footer">...</footer>` removed from `base.html`, the footer
  tests fail with `assert 0 == 3`, `0 == 1` and `0 == 2`.
- **Anchor label.** With the `FDA_AIDSF_PERF_VALIDATION` status set to `final`, the test fails
  (`assert False is True`). With the status empty, rendering raises `AnchorError ... has an empty
  document or status`.
- **Wheel.** I installed the built wheel into a fresh `--without-pip` venv. Its `site-packages`
  holds `bin`, `proofpack` and `proofpack-0.1.0.dev1.dist-info` (no `.pth`), and
  `proofpack.__file__` and `tokens.json` resolve inside the venv. With the `design/tokens.json`
  force-include line removed, the wheel test fails:
  `FileNotFoundError: packaged resource 'tokens.json' not found`.
- **FA5-N1, FA5-N2, RG-N1.** The r4 handoff at `2a9a6e2` carries rows 58 and 67 and the S4 line.
  `git grep "outside TR39|52.694|21.948|159 files"` over `src tests scripts README.md` at `ea2f743`
  finds 0 lines.

## What I could not check

- The day-7 clustered run test. It is not in this diff (`tests/` changes are the two files above),
  so I did not re-run its old form. Lenses 1-5 cover it.
- CI on GitHub. Nothing is pushed.
- What a NUL, ESC or surrogate does in a regulator's viewer, a PDF printer or a terminal. I counted
  bytes only.
- Whether Josh reads B1 as a blocker. It follows lens 3's FA-B4 grading. The crash class it belongs
  to already existed at `2a9a6e2` in the `model` and `criteria` positions.

## Sentences I refused to write

- "The DEC-65 gate refuses every control character in `criteria.yaml`." Tab and line feed pass in
  three fields, and B1's document crashes before the gate reports.
- "Repair 5 introduced no regression." B1.
- "The mapping text is fully covered." `source`, `confidence`, `value_summaries` and extra keys are
  not walked. I measured 0 control bytes reaching any output from them, on the inputs listed above.
- "Self-referential documents are a new defect." At `2a9a6e2` two of the five positions were
  already exit 5.

## Re-run these

```bash
L=C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/a743e7e5-3be8-4d70-9ed0-681f5784a106/scratchpad/lens-E8-r6-regression
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree add --detach $L/new ea2f743
cd $L/new && export PYTHONPATH=$L/new/src && python -c "import proofpack;print(proofpack.__file__)"
PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt python -m pytest -q -p no:cacheprovider   # 1214 passed, 1 skipped, 1 xfailed
# B1: after the suite, build a pack directory with tests/test_run_cli.py::_prepare, write zz_extra: &a [*a] as line 1 of its criteria.yaml, then
python -m proofpack.cli run --input <dir>/test.csv --criteria <dir>/criteria.yaml --out <dir>/pack --offline   # exit 5 RecursionError (2a9a6e2: exit 3 H08)
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force $L/new
```

## What the next repair needs

1. B1: a visited-set (or `id()` set) or a depth bound in `control_character_at` that ends in a typed
   H08 naming the path. A regression test should feed the root alias and must fail at `ea2f743` with
   exit 5. The `model:` and `criteria[0]` aliases, exit 5 at both commits, could go in the same test.
2. N1: correct the module docstring and the `MULTILINE_FIELDS` comment. Name the inputs the tests
   feed and the precedence (missing block, E01) instead of generalising.
3. N2: tests for the gate's position (an id holding ESC beside an empty author), for `decided_by`,
   and for a key holding a tab. Add the three matching sweep mutants.
4. N3: correct the `tokens.json` sentence, or re-pair the three tokens with their `-bg` surfaces.
   This is Josh's or the design day's call, since D5 names no pair explicitly.
