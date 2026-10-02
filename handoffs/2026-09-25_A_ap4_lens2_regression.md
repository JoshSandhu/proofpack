# A-P4 lens 2 (regression and record) at `e2c98df` - build day 10, lane A

Lens round 2 onward ran on **Friday 2 October 2026** (day 10 was still open: the 26 September
session stopped at the usage limit and no work ran 27 September - 1 October; the file keeps
its 2026-09-25 name). Cold lens, no prior context. Inputs: `git diff 4879ac5 e2c98df`, the
repair note `workflows/notes-day10/AP4_repair1.md`, the two lens-1 notes, the A-P3 handoffs,
the brief, D4, D5, DECISIONS. Every figure below was measured in this session on
win-amd64-cp314 (Windows 11, CPython 3.14.6, docxtpl 0.20.2, python-docx 1.2.0, matplotlib
3.11.2 from the pip user site, `python -m uv` 0.12.13), in detached worktrees at `e2c98df`
and `4879ac5` under `scratchpad/lens-AP4-r2-regression/`, with `PYTHONPATH` forced to each
worktree's `src` and proved (`python -c "import proofpack;print(proofpack.__file__)"` printed
`...\lens-AP4-r2-regression\eng-e2c98df\src\proofpack\__init__.py`, and the `eng-4879ac5`
equivalent, before any figure was read, in Git Bash and in PowerShell 5.1). Every
`proofpack run` carried `--offline`. Nothing was downloaded, committed or pushed; the only
file written outside the worktrees is this note. Both worktrees are removed.

**Verdict: FAIL, one blocker (RG2-B1).** The repair's replacement for FA-S3 in
`src/proofpack/render/docx.py` says a newline or a tab in a declaration halts at H08, "so the
line-break rewrite is reachable through the Python API only". A CLI run refutes it: H08
lets a line feed and a tab through under `description`, `source` and `justification`
(DEC-65, `io/declare.py` `MULTILINE_FIELDS`), and both reach the DOCX as `<w:br/>` and
`<w:tab/>`. FA-S3 is therefore not closed. Everything else in the note re-measures: the full suite, the five marker counts, lint, the
sweep (14 planted, 14 killed, the same 14 killing tests the note names), the template
regeneration (byte-equal), doctor, `uv lock --check`, the unlicensed run, and `21 failed, 3
passed` for the new file at `4879ac5` with the note's quoted assertion. Six non-blocking
findings follow. Read the blocker, not the counts.

## Blockers

### RG2-B1 (sentence; FA-S3 not closed). `render/docx.py` asserts what H08 prevents, and a CLI run refutes it

Verbatim (`src/proofpack/render/docx.py`, module docstring, added by `e2c98df`): "a newline
or a tab in a declaration halts at H08 (``control character U+000A`` / ``U+0009``, exit 3,
nothing written), so the line-break rewrite is reachable through the Python API only." The
note repeats it in the FA-S3 row ("so the line-break rewrite is reachable through the Python
API only") and in Decision 2 ("the CLI can reach only the four sequences (H08 halts a newline
or tab)").

The repairer measured `model.name` only. `io/declare.py` lines 46-55 (DEC-65):
`MULTILINE_FIELDS = frozenset({"justification", "description", "source"})` and
`_CONTROL_MULTILINE` is "the same set less tab (U+0009) and line feed (U+000A)". Counter-example,
run through `proofpack.cli.main` under the tests' ephemeral licence (`conftest.write_licence`,
`ephemeral_registry()`), sockets replaced by a raiser, on the f17 inputs with
`reference_standard.description: "QQa\nbZZ"` and `operating_points[0].source: "TTa\tbUU"`
(written by `yaml.safe_dump`), `--format json,html,docx --templates T1,T7,T8 --offline`:

- exit 0, all nine files written (`T1.docx`, `T1.html`, `T7.docx`, `T7.html`, `T8.docx`,
  `T8.html`, `ingest_report.json`, `pseudonyms.json`, `run.json`); `run.json` holds
  `'QQa\nbZZ'` and `'TTa\tbUU'`;
- `word/document.xml` matches `QQa</w:t>\s*<w:br/>\s*<w:t[^>]*>bZZ` twice in `T1.docx`
  and once in `T8.docx`;
- the tab arrives as its own run: `op1: threshold 0.5 rule &gt;=, other (TTa</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t xml:space="preserve">bUU)` in `T1.docx` and `T8.docx`.

The `model.name` measurements the sentence rests on do re-measure: `model.name: "m{_{ 7*7 }_}n"`
exit 4 with `run.json` written, `"a\nb"` -> `HALT H08: declaration invalid at model/name:
control character U+000A; remove it`, exit 3, no out directory; `"a\tb"` -> `U+0009`, exit 3.
So the sentence holds for `model.name` and is false as written for the declaration as a whole.

Not a numbers defect. A multi-line justification printing as a line break may be what a
customer wants, and the HTML prints the same string as whitespace. The defect is the
sentence. It asserts what a check prevents, the repairer ran no counter-example for it, and
it is the repair's own replacement for a lens finding the note lists as closed. The pinned
phrase (`test_the_corrected_sentence_is_present[...-no customer string is evaluated as a\ntemplate]`)
covers only the first clause, so no test fails when the false clause is corrected.

Repro (Git Bash, `PYTHONPATH` forced, a licence in `PROOFPACK_HOME`): set
`reference_standard.description` in the f17 `criteria.yaml` to `"QQa\nbZZ"`, run
`python -m proofpack.cli run ... --format docx --templates T8 --offline`, then
`unzip -p OUT/T8.docx word/document.xml | grep -c "QQa</w:t><w:br/>"` prints `1`.

Repair: name the fields. H08 halts U+000A and U+0009 under `model.name` and every key other
than `justification`, `description` and `source`. Under those three, a CLI run reaches
`<w:br/>` and `<w:tab/>`. Add a phrase test that fails on the old sentence. Optionally
add a behaviour test that feeds `"QQa\nbZZ"` through `reference_standard.description` on the
CLI and reads the break back. Correct the note's FA-S3 row and Decision 2 the same way.
This is not a statistical gate, so DEC-12's fresh-attack lens is not required. A cold check of the one paragraph is.

## Non-blocking findings

| Id | What was measured | Repro |
|---|---|---|
| RG2-N1 (figures stale at the shipped sha) | The hidden-extra figures in the `ci.yml` `docx-extra` comment, the `tests/ap4_docx.py` docstring and the `AP4_MUTANTS` comment (`29 passed, 101 skipped` / `23 failed, 47 passed, 60 errors`) are `4879ac5`'s 130-test ap4 set. I re-measured them exactly there (`29 passed, 101 skipped, 1589 deselected in 10.88s` / `23 failed, 47 passed, 1589 deselected, 60 errors in 13.26s`). At `e2c98df`, where the text ships, the same plugin gives `50 passed, 104 skipped, 1589 deselected` and `26 failed, 68 passed, 1589 deselected, 60 errors`. The sweep comment's three outcomes re-measure at `e2c98df` (driver that adds the plugin to the sweep's child env): `ap4_footer_emptied_in_render` SURVIVED, `ap4_png_dpi_150` and `ap4_zip_mtime_now` killed at `1 failed, 49 passed, 104 skipped`, and under `PROOFPACK_REQUIRE_DOCX=1` `baseline (no mutant) does not pass -m ap4; refusing to sweep` with `FAILED tests/test_ap4_cli.py::test_the_licence_states_and_which_files_exist[ok-kwargs0-True]`. The text dates its figures but names no sha. A reader who runs the command at the tip gets other counts. Name `4879ac5` beside them. | `-p hide_docx` plugin (`sys.modules[n] = None` for `docx`, `docxtpl`, `matplotlib`), `python -m pytest -q -p no:cacheprovider -p hide_docx -m ap4` at each sha |
| RG2-S2 (sentence, the note) | The note's RG1-N9 row says the wheel test is "skipped only when `python -m uv` is not importable". `tests/test_ap4_templates.py` line 41 is `pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]`, so `test_a_built_wheel_carries_the_three_docx_templates_beside_the_html_ones` also skips when the extra is absent. With the plugin above: `SKIPPED [1] tests\test_ap4_templates.py:213: the [docx] extra ... is not installed`. The main CI `test` job (`uv sync --all-groups --locked`, no extra) will therefore skip it. The helper's own docstring ("skipped only where `uv` is not importable") is accurate for the helper's single `pytest.skip`. This is A-P3's refused "skipped only when ..." sentence class. | the same plugin, `-rs` on that test id |
| RG2-S3 (sentence, generalisation) | `render/docx.py`: "no customer string is evaluated as a template", and the four sequences become `{{` ... "wherever they occur". Both generalise over a class of inputs. I could not break either. The test feeds two literal strings through T8's `model.name`. Lens 1 fed fourteen strings through eight slots. I fed `Zq{_{ 7*7 }_}qZ` and `Yp{_% if 1 %_}pY` through `model.name` into T1, T7 and T8: the rewrite appears in `document.xml` (T1 1, T8 2) and in every header part (T1 9, T7 3, T8 3), `Zq49qZ` and `YppY` appear 0 times, and no other part carries the string. Name the inputs instead of "no customer string" and "wherever". | `probe_rewrite.py` (scratchpad, removed) |
| RG2-N2 (tests that pass at `4879ac5`) | Three of the 24 new tests pass at `4879ac5`; the note says so. `test_f5_png_rows_sit_at_the_svg_row_fractions_top_down` pins behaviour through its mutant: with `ax.set_ylim(-0.5, n_rows - 0.5)` planted at `4879ac5` it fails with `AssertionError: ('F5-age-sensitivity', (np.float64(-0.5), np.float64(3.5)))` while `tests/test_ap4_figures.py` passes (`1 failed, 11 passed`), exactly as the note quotes. `test_docxtpl_rewrites_the_four_escape_sequences_and_a_newline` pins docxtpl's behaviour, which the docstring describes; it would fail on a docxtpl upgrade or on an escape added to the renderer, and no mutant shows that. `test_t7_unverified_runs_are_twenty_in_pp_unverified_and_one_in_the_conventions_paragraph` pins `{PP Unverified: 20, None: 1}`, so a later fix that styles the 21st marking fails it. Record only. | copy `tests/test_ap4_repair1.py` into a `4879ac5` worktree, `-rA` |
| RG2-N3 (note commands) | `cmp` (the regeneration check) is not a PowerShell 5.1 command (`The term 'cmp' is not recognized ...`). `Get-FileHash` gave the same three hashes. The licensed-run figures cite `run_licensed.py`, which is in no repository, and the scratchpad that held it is gone, so they cannot be re-run from the note. The note gives the Git Bash prefix only, no PowerShell form. | `cmp a b` in PowerShell |
| RG2-N4 (merge record) | The merge notes name all eight files both sides changed since `81f1102`. Against main (`dec344b`, E10 landed; re-run at `61cf02c`): `git merge-tree --write-tree --name-only main e2c98df` shows CONFLICT (content) in `src/proofpack/cli.py`, `src/proofpack/run.py`, `tests/test_offline.py`, and auto-merging in `pyproject.toml`, `scripts/mutation_sweep.py`, `tests/test_ap3_r3_repair1.py`, `tests/test_ap3_repair2.py`, `tests/test_render_t8.py`. That is the note's list, measured there against `6c4e253`. `dec344b` adds only E's handoff. Main moved to `61cf02c` (2 Oct 09:49) during this lens: it adds `.github/workflows/pypi.yml` and `tests/test_pypi_workflow.py`, neither touched by the branch, and the merge-tree output is unchanged. FA-R5's decision now also covers the PyPI wheel, which would carry the three `.docx` after the merge. Not in the notes: after the merge, `mutation_sweep.py --marker day10` selects by `m.day == 10`. The 14 ap4 mutants (day 10) therefore join E10's 18 (main declares 18 `day=10,` lines) under `-m day10`, and E10's recorded `18 planted, 18 killed` will no longer be what that command prints. ap3/day9 has the same shape. | `git grep -c "day=10," main -- scripts/mutation_sweep.py` -> 18 |
| RG2-N5 (dates) | "What tomorrow needs" puts day 11 on Mon 28 Sept (DEC-69). None of days 11-14 ran (28 Sept - 1 Oct), so the dates are Josh's to reset. This lens names none. | read the note |

## What was re-measured (note figure -> this session)

| Command (in the `e2c98df` worktree) | Note | Git Bash | PowerShell 5.1 |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider -rs` | `1741 passed, 1 skipped, 1 xfailed in 160.45s` | `1740 passed, 2 skipped, 1 xfailed in 194.95s`; the second skip is `tests/test_e8_repair4.py:405` (confusables path relative to the lens worktree; RG1-N10, environmental) | `1740 passed, 2 skipped, 1 xfailed in 180.87s`, the same two skips |
| `-m ap4` / `-m day10` | `154 passed, 1589 deselected` each | `154 passed, 1589 deselected in 39.16s` / `in 38.30s` | `in 35.17s` / `in 37.84s` |
| `-m ap3` / `-m day9` / `-m day8` | `172` / `331` / `470 passed` | `172 passed` / `331 passed` / `469 passed, 1 skipped` (RG1-N10) | the same three |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `248 files already formatted` | the same | the same |
| `python -m proofpack.cli doctor --offline` | `[ok  ] docx extra  docxtpl 0.20.2, python-docx 1.2.0, matplotlib 3.11.2` | the same, `All essential checks passed.` | the same |
| `python -m uv lock --check --offline` | `Resolved 72 packages`, exit 0 | `Resolved 72 packages in 1ms`, exit 0 | `Resolved 72 packages in 0.84ms`, exit 0 |
| `python scripts/mutation_sweep.py --marker ap4` (`PROOFPACK_REQUIRE_DOCX=1`) | `14 planted, 14 killed, 0 survived; 331 s` | `14 planted, 14 killed, 0 survived; 364 s`; `ap4_f5_rows_flipped` `1 failed, 85 passed`, `ap4_figure_width_100mm` `1 failed, 33 passed` | `14 planted, 14 killed, 0 survived; 342 s` |
| The killing test of each ap4 mutant (the sweep's `make_copy`/`plant`/`-x -m ap4`, plus `-rf`) | the note's list of 14 | all 14 identical to the note's list, `ap4_f5_rows_flipped` -> `test_ap4_repair1::test_f5_png_rows_sit_at_the_svg_row_fractions_top_down`, `ap4_figure_width_100mm` -> `test_ap4_docx::test_inline_images_are_160_mm_wide_...` | - |
| `python scripts/make_docx_templates.py --out DIR` | 52,840 / 40,587 / 42,510 bytes, byte-equal | the same sizes, SHA-256 prefixes `259f6c1ebbf38bc2` / `d6ab2c521a1b6c3c` / `0aef69d154576ed6`, `cmp` equal to the committed files | the same three hashes by `Get-FileHash`, equal |
| the unlicensed run (`PROOFPACK_HOME` empty, f17 `--n 400 --inputs-only`, `--format json,html,docx --templates T1,T7,T8 --offline`) | exit 4; 649 / 370 / 236,797 bytes; the Next-step line naming six files | exit 4, the same three sizes, `HTML and DOCX not written: licence refused (no_file); ...`, `Next step: proofpack licence install FILE, then run again for T1.html, T1.docx, T7.html, T7.docx, T8.html, T8.docx (docs: /docs/run)` | the same |
| the licensed run (own driver: `conftest.write_licence`, `ephemeral_registry()`, sockets replaced by a raiser) | exit 0 in 2.0 s; `run.json` 236,806, `T1.docx` 680,584, `T1.html` 141,950, `T7.docx` 50,438, `T7.html` 47,196, `T8.docx` 46,160, `T8.html` 34,456 | exit 0 in 2.1 s; 236,806 / 680,575 / 141,950 / 50,438 / 47,196 / 46,157 / 34,456 | exit 0 in 2.2 s; 236,806 / 680,563 / 141,950 / 50,436 / 47,196 / 46,150 / 34,456 |
| `--collect-only` per file (RG1-N4) | extra 16, determinism 8, styles 15; repair1 24 | `16`, `8`, `15`, `24` | - |

The DOCX sizes move by a few bytes between runs. Lens 1 measured the cause: the run id and
`started` are in the footer and the core properties. The HTML and `run.json` sizes are equal
across all three runs. The licensed Next-step line continues past the note's quotation: `...
T8.docx); --templates T1,T7,T8 writes all three (docs: /docs/run)`.

## Fails pre-fix (`tests/test_ap4_repair1.py` copied into the `4879ac5` worktree)

`21 failed, 3 passed in 3.95s`. That is the note's count. The first failure is the note's
verbatim line: `E       assert 'tests/test_...te_identical' not in '"""DOCX ren...turn write\n'`.
The three that pass are the ones the note names: `test_docxtpl_rewrites_...`,
`test_f5_png_rows_...` and `test_t7_unverified_runs_...` (RG2-N2). RP1-1: with
`FIGURE_WIDTH_MM = 100` planted at `4879ac5`, `e2c98df`'s `test_inline_images_are_160_mm_wide_...`
fails with `E       assert {3600000} == {5760000}`, and `4879ac5`'s own version of the test
gives `1 passed`. Both are the note's figures.

## Nothing weakened

- `git diff --name-status 4879ac5 e2c98df -- tests/` shows `M ap4_docx.py`,
  `M test_ap4_docx.py`, `A test_ap4_repair1.py`, `M test_ap4_sentences.py` and
  `M test_ap4_templates.py`. There is no `D` line. `81f1102..e2c98df` has only `A`/`M` lines.
- Grepping the diff for `skip`, `xfail`, `.only` and `pytest.mark` finds one added
  `pytest.skip` (`build_wheel_offline`, uv not importable) and the new file's `pytestmark`
  and `parametrize` lines. Every other hit is comment text. No marker line is removed.
- `git diff --name-status 4879ac5 e2c98df` (and `81f1102 e2c98df`) `-- src/proofpack/stats/
  src/proofpack/gates.py src/proofpack/criteria.py` is empty.
- `43aab67^{tree}` = `e2c98df^{tree}` = `aa19c675...`, which matches the note's amend claim.
- `uv.lock` is unchanged by `e2c98df`. Since `81f1102` it adds nine `[[package]]` entries:
  contourpy, cycler, docxtpl, fonttools, kiwisolver, lxml, matplotlib, pillow and
  python-docx. It removes one line (`provides-extras = ["stats"]`). numpy 2.5.3, scipy 1.18.1,
  statsmodels 0.15.0 and scikit-learn 1.9.0 are unmoved.
- `ap4` is declared in `pyproject.toml` (line 102) beside `ap3`. `ci.yml` `docx-extra` runs
  `uv sync --all-groups --locked --extra docx`, then `pytest -m ap4` under
  `PROOFPACK_REQUIRE_DOCX: "1"`. The `test` job syncs without the extra.
- The seven A-P3 CI sentence violations: the six shipped phrases (lens 2 FA N3, N4, N5,
  RG3-S1, FA3-S3, and FA3-S1's `OFFLINE_FLAG`) occur at `e2c98df` only inside
  `tests/test_ap4_sentences.py`'s lists. FA N6 was note-only. `test_ap4_sentences.py` passes
  in both full suites.

## Lens-1 findings: closed or carried (re-checked here)

The closed items are closed as described, except FA-S3 (RG2-B1):

- FA-S1/RG1-N2 and FA-S2: `test_every_test_citation_...` passes, and each citation resolves
  to a `def`.
- RG1-N1 and RG1-N11: the sentences now record measurements. The figures are `4879ac5`'s
  (RG2-N1).
- RG1-N3: the new docstring is in place.
- RG1-N4: the counts were corrected.
- RG1-N5: the merge notes are complete (RG2-N4).
- RG1-N6: the tomorrow section exists (RG2-N5).
- RG1-N9: the ap4 wheel test builds `--offline`. It ran in both full suites.
- FA-R4: reproduced.

The carried list (FA-R1, R2, R3, R5, R6, R7, R9, RG1-N7, RG1-N8, `test_render_theme._build_wheel`,
the pattern-count kills) is what lens 1 left open. Open and not in the note: the
three-key route for newline and tab (RG2-B1); the main CI job skipping the wheel test
(RG2-S2); `--marker day10` absorbing the ap4 mutants after the merge (RG2-N4).
Lens 1's untested `_add_rich` fallback stays untested.

## What I could not break (what I tried)

- **The round-trip covers every DOCX table.** The licensed `T1.docx` has 42 `<w:tbl>`, all
  top level (0 nested; python-docx `d.tables` = 42). T7 has 10 and T8 has 29, also all top
  level. `body_paragraphs` reads every unique cell of every `d.tables`, and the decimal
  scan reads those plus every footer. D4 section 2 names T1-1 to T1-18. The DOCX and the
  HTML both caption the same eleven: T1-1, 2, 3, 5, 6, 7, 8, 9, 10, 11 and 18 (the HTML has
  18 `<table>`, the DOCX adds the margin-note tables). T1-4, 12, 14, 15 and 16 are absent
  from both, as lens 1 recorded in RG1-N8.
- **Import hygiene.** In a fresh process, `import proofpack, proofpack.render.html,
  proofpack.render.docx, proofpack.render.figures, proofpack.run, proofpack.cli` loaded none
  of `docx`, `docxtpl`, `matplotlib`, `PIL`, `lxml`, `fontTools`, `kiwisolver`, `cycler` or
  `contourpy`.
- **The skip text.** With the extra hidden, every ap4 skip at `e2c98df` carries the one
  named reason (`-rs`, a single distinct reason).
- **docxtpl rewrites in headers.** See RG2-S3.

## What I could not check

- The `docx-extra` and `test` CI jobs: the branch has not been pushed.
- Word: no Word was driven.
- Byte identity on another platform: none was claimed.
- Whether `python -m uv build --wheel --offline` opens a socket: uv is a native binary, and
  no socket probe reaches it.
- The hidden-extra measurements in PowerShell: Git Bash only.
- E10's content beyond the merge-tree names, the `day=10` count and `tests/test_sweep_day10.py`.

## Sentences I refused to write

- "FA-S3 is closed." RG2-B1.
- "The ap4 wheel test runs in the main CI job." It skips there without the extra (RG2-S2),
  and no CI has run.
- "The DOCX output is byte-identical across runs." It is not: two runs differ by a few bytes
  through the run id and `started`. The byte test covers two renders of one `run.json`, and I
  did not re-run that test beyond the suite.
- "No customer string can reach the DOCX as anything but text." I could not break it for the
  inputs listed in RG2-S3. That is a list, not a class.
- "The note's figures re-measure exactly." The licensed DOCX sizes cannot (RG2-N3,
  run-dependent), and the hidden-extra figures re-measure only at `4879ac5` (RG2-N1).
