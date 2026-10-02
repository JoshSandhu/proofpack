# A-P4 lens 3 (regression and record) at `fd9488f` - build day 10, lane A

Lens round 3 ran on **Friday 2 October 2026** (day 10 was still open: the 26 September
session stopped at the usage limit and no work ran 27 September - 1 October; the file keeps
its 2026-09-25 name). Cold lens, no prior context. Inputs: `git diff e2c98df fd9488f`, the
repair note `scratchpad/notes/AP4_repair2.md`, the four earlier lens notes, the A-P3
handoffs, the brief, D4, D5, DECISIONS. Every figure below was measured in this session on
win-amd64-cp314 (Windows 11, CPython 3.14.6, docxtpl 0.20.2, python-docx 1.2.0, matplotlib
3.11.2 from the pip user site), in detached worktrees at `fd9488f` and `e2c98df` under
`scratchpad/lens-AP4-r3-regression/`, with `PYTHONPATH` forced to each worktree's `src` and
proved (`python -c "import proofpack;print(proofpack.__file__)"` printed
`...\lens-AP4-r3-regression\eng-fd9\src\proofpack\__init__.py`, and the `eng-e2c`
equivalent, before any figure was read, in Git Bash and in PowerShell 5.1). Every
`proofpack run` carried `--offline`. Nothing was downloaded, committed or pushed; the only
file written outside the worktrees is this note. Both worktrees are removed.

**Verdict: FAIL, one blocker (RG3-B1).** FA2-B1's class is closed for F5 only. The F2 and
F4 PNGs that `T1.docx` embeds draw engine numbers in their legends (`AUROC 0.835 [0.795,
0.876]`; `slope 1.349 [1.056, 1.642]; intercept −0.749 [−1.005, −0.493]`). No test reads
them. A mutant that prints them to two places survives all ap4 tests. Everything else in the
note re-measures: the full suite, the five marker counts, lint, `30 failed, 7 passed` for the
new file at `e2c98df` with the note's quoted first line, each of the three new mutants killed
by the test the note names, the sweep (`17 planted, 17 killed`) in both shells, the template
regeneration, doctor, `uv lock --check`, both runs, the SHA-256 figures for FA2-S8, and the
merge notes. Two sentence violations and six non-blocking findings follow. Read the blocker,
not the counts.

## Blockers

### RG3-B1. The numbers in the F2 and F4 PNG legends are not tested: a mutant that prints them to two places survives all 191 ap4 tests

Lens 2 FA2-B1 ("a wrong or differently rounded number") asked for a test that compares the
F5 `ax.texts` with the SVG "and the legend texts with the SVG legend strings". The repair
added two tests, `test_f5_png_value_texts_equal_the_svg_value_texts_in_every_f5_figure` and
`test_f5_png_criterion_legend_equals_the_svg_criterion_text`. Both read F5 only.
`grep -n "get_legend\|\.legends" tests/test_ap4_*.py` finds one hit, the F5 criterion test.

The F2 legend (`_curve_figure`, `label=spec["legend"]`) and the F4 legend (`fig.legend`, the
deciles line's `label=spec["legend"]`) carry the engine's figures. In the shipped code they
equal the SVG strings. For the synthetic document I read `'ROC curve (solid); AUROC 0.835
[0.795, 0.876]'` and `'deciles (points, solid bars); slope 1.349 [1.056, 1.642]; intercept
−0.749 [−1.005, −0.493]'`, and both are in the T1 HTML. They are engine numbers in the DOCX,
inside the PNG, with no test.

Mutants, each planted alone through the sweep's own `make_copy`/`assert_imports_from_copy`,
then `pytest -q -m ap4 --ignore=tests/test_sweep_ap4.py -rf` under
`PROOFPACK_REQUIRE_DOCX=1`:

- `f2_legend_two_dp`: `label=_two_dp(spec["legend"])` in `_curve_figure`, where `_two_dp`
  cuts every three-place decimal to two. The F2 legend then reads `AUROC 0.83 [0.79, 0.87]`.
  Result: `190 passed, 1589 deselected in 45.00s`.
- `f4_legend_two_dp`: the same on the F4 deciles label. The legend then reads `slope 1.34
  [1.05, 1.64]; intercept −0.74 [−1.00, −0.49]`. Result: `190 passed, 1589 deselected in
  45.48s`.
- My first, mis-escaped attempt replaced every number in both legends with U+0001
  (`'AUROC \x01 [\x01, \x01]'`). That also gave `190 passed`.

The note's FA2-B1 row describes the two F5 tests accurately. It does not claim F2 or F4. But
the blocker it closes was graded on the class (a differently rounded number reaching the
DOCX through a PNG), and that class is still open for F2 and F4. The shipped code is right
today. No test holds it.

Repro (in a scratch worktree of `fd9488f`, Git Bash):
`sed -i 's/^        label=spec\["legend"\],$/        label=spec["legend"].replace("0.835 [0.795, 0.876]", "0.84 [0.80, 0.88]"),/' src/proofpack/render/figures_png.py && PYTHONPATH=$PWD/src PROOFPACK_REQUIRE_DOCX=1 python -m pytest -q -m ap4`
gives `191 passed, 1589 deselected in 37.75s`.

Repair: one test that compares every legend text of F2, F4 (and F3 with a planted `pr` array,
as `test_f3_planted_pr_array_equals_the_svg_and_is_absent_without_one` already plants) with
the SVG legend strings, less the fixed `(dashed)` reference labels. Add a mutant for each
legend to `AP4_MUTANTS`. This is not a statistical gate, so DEC-12's fresh-attack lens is not
required. A cold check of the new test and its mutants is.

## Sentence violations (record; fix in the repair round or the merge commit)

| Id | Verbatim (where) | What was measured | Repro |
|---|---|---|---|
| RG3-S1 (false as written; new in `fd9488f`) | `src/proofpack/render/figures_png.py` module docstring: "every labelled line has a dash pattern of its own and a text label in the legend" | F4's labelled line `'deciles (points, solid bars); slope 1.349 ...'` has `get_linestyle()` = `'None'` and marker `'o'`, so it has no dash pattern. The cited test excludes it: `styles = [... for ln in labelled if ln.get_marker() in ("None", "")]`. The other six labelled lines (three `--` references with `(0, (6, 4))`, the F2 `-` series) match the sentence. | list `ax.lines` with a label for `all_figures(synthetic_document(), {})` and print `get_linestyle()`, `get_marker()` |
| RG3-S2 (generalisation; contradicts the note's own refused list) | `figures_png.py` `_builtin_rc` docstring: "``rcParamsDefault`` less the backend keys), so a ``matplotlibrc`` read at import does not reach the figure". The note's FA2-S8 row says "`rcParamsDefault` less matplotlib's backend keys". | The note refuses "A matplotlibrc cannot change the figures". The shipped docstring states it about every `matplotlibrc`. matplotlib 3.11.2's `STYLE_BLACKLIST` has 15 keys, and five of them are not backend keys: `date.epoch`, `timezone`, `docstring.hardcopy`, `figure.max_open_warning`, `savefig.directory`. I could not break the behaviour (see below). The sentence is still a class claim. Name the test's seven keys instead, and list the 15 keys or say "less `STYLE_BLACKLIST`". | `python -c "import matplotlib.style.core as c; print(sorted(c.STYLE_BLACKLIST))"` |

The note's other sentences, and the diff's, name inputs and tests. FA2-S1 and FA2-S2's CI
facts re-read: `gh run view 36020197050 --json headSha,conclusion,createdAt` gives
`81f11022...`, `success`, `2026-09-24T15:26:28Z`. `--json jobs` shows the docker job's step
8, `record the base image digest (the Dockerfile pin is [unverified] until this is read)`,
`success` at 15:26:54Z. The log line at `15:26:54.4227792Z` is
`docker.io/library/python:3.12-slim@sha256:2f17fc04...06a9`. The oracle step printed both
quoted lines at `15:28:49.86Z`, byte-equal to the `ci.yml` comment. Byte identity:
`docx.py` now says "gives equal bytes for T1, T7 and T8" and cites the byte test, with zip
mtimes and `core.xml` created/modified set from `manifest.started`. That meets the rule.

## Non-blocking findings

| Id | What was measured | Repro |
|---|---|---|
| RG3-N1 (decorator on `f3_figure` unpinned) | Dropping `@_builtin_rc` from each function alone: `png_bytes`, `f2_figure`, `f4_figure` and `f5_figures` each give `1 failed, 189 passed` (killed by `test_a_matplotlibrc_in_the_working_directory_changes_no_png_byte`). `f3_figure` gives `190 passed`. The rc test renders the synthetic document, whose `f3` is `None`, and `grep -rn '"pr"' src/proofpack` outside `render/` is empty. The engine emits no `pr` array at `fd9488f`, so F3 is drawn only from a planted document (API). | `scratchpad/plant_dec.py` (removed): `re.subn(r"^@_builtin_rc\n(def f3_figure\()", ...)` then `-m ap4` |
| RG3-N2 (citation scope) | The colour sentence ("every line colour and patch face colour of the synthetic document's eleven figures is one of five tokens") cites `test_two_labelled_series_..._in_the_tokens`, which reads `ax.lines` and `ax.patches`, not `ax.patch` or `fig.patch` (lens 2 mutants D, E survive). Measured over the eleven figures: `ax.patch` and `fig.patch` are `#ffffff` (the `bg` token); lines `#16202b` ×76 and `#6b7784` ×11; histogram patches `#d8dfe6` ×10; visible spines `#4a5a6a`. The spines with `#000000` (24) are the hidden top and right ones. Legend texts (11 axes, 2 figure-level) and the one F2 annotation are `#000000`, as the docstring says. The sentence holds as measured; its citation covers part of it. | iterate `fig.patch`, `ax.patch`, `ax.lines`, `ax.patches`, spines and legend texts with `to_hex` |
| RG3-N3 (note: run.json size) | The note says the "HTML and `run.json` sizes equal the lens's" and puts the DOCX size drift down to run id and `started`. My PowerShell licensed run wrote `run.json` 236,805 bytes; Git Bash wrote 236,806. The JSON diff is `manifest/duration_s` `0.701` vs `0.79`, plus `started` and `run_id`. The `run.json` size is run-dependent as well. | diff the two `run.json` files' leaves |
| RG3-N4 (note: merge-tree sha) | The merge notes ran `git merge-tree ... main e2c98df`, not the tip. Re-run against `main` = `c779678` with `fd9488f`: CONFLICT (content) in `src/proofpack/cli.py`, `src/proofpack/run.py` and `tests/test_offline.py`; auto-merging `README.md`, `pyproject.toml`, `scripts/mutation_sweep.py`, `tests/test_ap3_r3_repair1.py`, `tests/test_ap3_repair2.py`, `tests/test_render_t8.py` and `uv.lock`. That is the note's list. `comm` of the two sides' changed files since `81f1102` gives the same ten files. The merged tree's `pyproject.toml` and `uv.lock`, run with `python -m uv lock --check --offline` in a scratch directory, gave `Resolved 72 packages`, exit 0, urllib3 `2.8.0`. `git rev-list --count 81f1102..c779678` = 17, and `git grep -c "day=10,"` = 18 on main, 17 on `fd9488f` (RG2-N4 stands). | `git merge-tree --write-tree --name-only main fd9488f` |
| RG3-N5 (note: carried items omitted) | Repair 1 carried FA-R9 (the T7 conventions pipe table as one monospace block) and RG1-N8 (D4 section 2's T1-4, 12, 14, 15 and 16 in neither document). Neither is named in the repair-2 note's carried list, "What tomorrow needs" or "Needs from Josh". FA-R9 overlaps FA2-N3. Lens 1's untested `_add_rich` fallback is also unnamed. | `grep -n "FA-R9\|RG1-N8" workflows/notes-day10/AP4_repair1.md` |
| RG3-N6 (hidden-extra counts at the tip, record) | The three texts now name `4879ac5`, which is accurate. At `fd9488f`, with a `-p hide_docx` plugin (`sys.modules[n] = None` for `docx`, `docxtpl`, `matplotlib`): `-m ap4` gives `80 passed, 111 skipped, 1589 deselected in 6.43s`, and under `PROOFPACK_REQUIRE_DOCX=1` it gives `32 failed, 99 passed, 1589 deselected, 60 errors in 13.40s`. The main CI `test` job (no extra) would therefore skip 111 ap4 tests. | `PYTHONPATH="<wt>/src;<plugdir>" python -m pytest -q -p no:cacheprovider -p hide_docx -m ap4` |

FA2-N1 (`$...$` in a level) is still open as carried. Through the API, the F5 figures with
every `"level": "S1"` (18 occurrences) replaced by `$\foo$` raise `ValueError` in
`png_bytes` at `fd9488f`.

## What was re-measured (note figure -> this session)

| Command (the `fd9488f` worktree) | Note | Git Bash | PowerShell 5.1 |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider -rs` | `1778 passed, 1 skipped, 1 xfailed in 173.14s` | `1777 passed, 2 skipped, 1 xfailed in 174.16s`. The second skip is `test_e8_repair4.py:405` (confusables path relative to the lens worktree; RG1-N10, environmental). 1,780 collected. | `1777 passed, 2 skipped, 1 xfailed in 185.80s`, the same two skips |
| `-m ap4` / `-m day10` | `191 passed, 1589 deselected` each | `in 43.45s` / `in 40.10s` | `in 39.78s` / `in 41.60s` |
| `-m ap3` / `-m day9` / `-m day8` | `172` / `331` / `470 passed` | `172 passed` / `331 passed` / `469 passed, 1 skipped` (RG1-N10) | the same three |
| `tests/test_ap4_repair2.py` | `37 passed in 7.19s` | `37 passed in 6.46s` | - |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `251 files already formatted` | the same | the same |
| `python -m proofpack.cli doctor --offline` | `[ok  ] docx extra  docxtpl 0.20.2, python-docx 1.2.0, matplotlib 3.11.2` | the same, `All essential checks passed.` | the same |
| `python -m uv lock --check --offline` | `Resolved 72 packages`, exit 0 | `Resolved 72 packages in 0.84ms`, exit 0 | `Resolved 72 packages in 1ms`, exit 0 |
| `python scripts/mutation_sweep.py --marker ap4` (`PROOFPACK_REQUIRE_DOCX=1`) | `17 planted, 17 killed, 0 survived; 467 s`; the three new mutants `1 failed, 117 / 118 / 119 passed` | `17 planted, 17 killed, 0 survived; 424 s`, the three at `1 failed, 117 passed` / `118` / `119` | `17 planted, 17 killed, 0 survived; 445 s` |
| Each new mutant alone, `-m ap4 --ignore=tests/test_sweep_ap4.py -rf` | `1 failed, 189 passed` each, killed by the value-text test, the criterion-legend test and the rc test, with the quoted first lines | identical: `('F5-age-sensitivity', ['0.78', '0.79', '0.67', '0.73'], ['29/37 (78.4%) [62.8, 88.6]ᶜ', ...`, `('F5-sex-sensitivity', ['customer criterion C_sex (Dr A., 2026-03-01): 1e-05'], [...0.00001'])`, `RuntimeError: Failed to process string with tex because latex could not be found` | - |
| `python scripts/make_docx_templates.py --out DIR` | 52,840 / 40,587 / 42,510 bytes, byte-equal | the same sizes, `cmp` equal, SHA-256 `259f6c1ebbf38bc2` / `d6ab2c521a1b6c3c` / `0aef69d154576ed6` | the same three hashes by `Get-FileHash`, equal to the committed files |
| FA2-S8 hashes, no rc file (my script: `all_figures` -> 11 `png_bytes`, `render_docx_bytes(doc, "T1")`) | PNG joint `7d0b59a88ce3ca1f`, `T1.docx` `11dba1474cc0a8c6`, at both shas | at `e2c98df` and at `fd9488f`: SHA-256 of the eleven PNGs' concatenated bytes `7d0b59a88ce3ca1f`, `T1.docx` `11dba1474cc0a8c6` | - |
| the unlicensed run (`PROOFPACK_HOME` empty, f17 `--n 400 --inputs-only`) | exit 4; 649 / 370 / 236,797; the Next-step line naming six files | exit 4, the same three sizes and lines | the same |
| the licensed run (the note's `run_licensed.py`, retyped from the note) | exit 0 in 2.1 s; `run.json` 236,806, `T1.docx` 680,574, `T1.html` 141,950, `T7.docx` 50,441, `T7.html` 47,196, `T8.docx` 46,156, `T8.html` 34,456 | exit 0 in 2.0 s; 236,806 / 680,574 / 141,950 / 50,438 / 47,196 / 46,151 / 34,456 | exit 0 in 2.3 s; 236,805 / 680,575 / 141,950 / 50,437 / 47,196 / 46,154 / 34,456 (RG3-N3) |

The note's driver needs Windows-form paths in Git Bash. With `PYTHONPATH="/c/...;/c/..."`,
`from conftest import ...` raised `ModuleNotFoundError`. With `C:/...;C:/...` it ran. The
note's own prefix is `C:/Users/...`, so that is my invocation, not the note's.

## Fails pre-fix (`tests/test_ap4_repair2.py` copied into the `e2c98df` worktree)

`30 failed, 7 passed in 4.95s`, which is the note's count. The first failure is the note's
verbatim line, `E       assert 'has not yet...th that step' not in '# ProofPack...-offline"]\n'`.
The rc test fails on `assert 1 == 0`, and the mutant-list test on `KeyError:
'ap4_f5_value_text_two_dp'`. The seven that pass at `e2c98df` are the ones the note names:
the import-site inspection, the two F5 tests, the tab/FF/BEL counts, the three-field CLI
test and the two `model.name` halts. The two F5 tests and the rc test each kill their
mutant (table above).

The rc test pins more than `usetex`. I deleted `text.usetex: True` from `HOSTILE_RC` in a copy
of the test and ran it at `e2c98df`. It failed on the hashes (`At index 0 diff:
'a50d7f78...' != 'a4753dd2...'`). At `fd9488f` the same copy gives `1 passed`.

## Nothing weakened

- `git diff --name-status e2c98df fd9488f -- tests/` shows `M ap4_docx.py`,
  `M test_ap4_repair1.py`, `A test_ap4_repair2.py` and `M test_ap4_sentences.py`. There is
  no `D` line, and `81f1102..fd9488f` has only `A`/`M` lines.
- The diff's `skip`/`xfail`/`pytest.mark`/`pytestmark` hits are comment text, the lens notes,
  and the new file's `pytestmark` and `parametrize` lines. No skip or xfail is added, and no
  marker line is removed. The modified `PRESENT` pins in `test_ap4_repair1.py` and
  `test_ap4_sentences.py` move from deleted sentences to their replacements.
- `git diff --name-status e2c98df fd9488f` and `81f1102 fd9488f` `-- src/proofpack/stats/
  src/proofpack/gates.py src/proofpack/criteria.py` (and `render/format.py`) are empty.
- `uv.lock` is unchanged by `fd9488f`. Since `81f1102` it adds nine `[[package]]` entries
  (63 -> 72): contourpy, cycler, docxtpl, fonttools, kiwisolver, lxml, matplotlib, pillow
  and python-docx. The one `-` line is `provides-extras = ["stats"]`. numpy 2.5.3, scipy
  1.18.1, statsmodels 0.15.0 and scikit-learn 1.9.0 are unmoved. docxtpl's dependencies are
  jinja2, lxml and python-docx. matplotlib's are contourpy, cycler, fonttools, kiwisolver,
  numpy, packaging, pillow, pyparsing and python-dateutil. The ones not in the list of nine
  were already in the `81f1102` lock.
- `ap4` is declared in `pyproject.toml` (line 102) beside `ap3`. `ci.yml` `docx-extra` runs
  `uv sync --all-groups --locked --extra docx`, then `uv run pytest -q -p no:cacheprovider -m
  ap4` under `PROOFPACK_REQUIRE_DOCX: "1"`.
- The seven A-P3 CI sentence violations (`handoffs/2026-09-24_A_ci.md`: lens 2 FA N3, N4, N5,
  N6, and FA3-S1, RG3-S1, FA3-S3): at `fd9488f` the old phrases occur only inside
  `tests/test_ap4_sentences.py`'s lists and docstring. FA N6 was note-only. `OFFLINE_FLAG`
  rejects `--out=--offline`, `OPT=--offline proofpack run` and `>--offline.log`. The `& echo
  --offline` case is handled by `SEPARATORS`. The first commit `ed5d507` carries them.

## Lens-2 blockers and findings: closed or carried

- **FA2-B1**: closed for F5 (the two tests, the two mutants killed). The class is open for
  F2 and F4 (RG3-B1).
- **RG2-B1 = FA2-S5**: closed. The docstring names `model.name` (halts) and the three
  `MULTILINE_FIELDS` keys, and `io/declare.py` has that set. The CLI test passes at both
  shas and reads `QQa</w:t><w:br/>`, `JJa</w:t><w:br/>` and the `<w:tab/>` run.
- **FA2-S1, S2, S3, S4, S6, S7, RG2-S3, RP2-1**: each old phrase is absent and each new
  phrase is present (phrase tests fail at `e2c98df`). The CI facts re-read as above.
- **FA2-S8**: closed in code and test. The new docstring has RG3-S1 and RG3-S2.
- **FA2-N1, N2 (other than A, I), N3, N4, N7, N8, RG2-N3, N4, N5**: carried as the note
  says. FA2-N1 reproduces (above).

## What I could not break (what I tried)

- **The rc decorator.** I used a 19-key `matplotlibrc` in the working directory: the seven
  test keys, plus `figure.facecolor: blue`, `axes.facecolor: green`, `font.family:
  monospace`, both antialias keys off, `path.simplify_threshold: 0.9`,
  `axes.unicode_minus: False`, `axes.formatter.use_locale: True`, `savefig.bbox: tight`,
  `figure.dpi: 30`, and the blacklisted `timezone` and `date.epoch`
  (`matplotlib_fname()` printed `matplotlibrc`, `text.usetex` `True`). PNG joint
  `7d0b59a88ce3ca1f` and `T1.docx` `11dba1474cc0a8c6`, unchanged. A licensed CLI run from
  that directory gave exit 0, and the 11 `word/media` parts of `T1.docx` equal a clean run's.
- **The round-trip covers every DOCX table.** In the round-trip fixture run (`cli_run`:
  criteria and fairness declared), `T1.docx` has 44 `<w:tbl>`, all top level (0 nested;
  python-docx 44). T7 has 11 and T8 has 31, also all top level. `paragraph_texts` reads
  every unique cell of every `d.tables`. The captions are equal in both media: T1 shows
  T1-1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 13 and 18; T7 shows T1-2; T8 shows T1-1 and T1-17. Of
  D4 section 2's T1-1 to T1-18, T1-4, 12, 14, 15 and 16 are in neither medium (RG1-N8), and
  T1-17 prints in T8. The header's only decimal-looking tokens are `v0.9` and `v0.1.0.dev1`
  (versions).
- **Import hygiene.** A fresh process importing `proofpack`, `.render.html`, `.render.docx`,
  `.render.figures`, `.run` and `.cli` held none of `docx, docxtpl, matplotlib, PIL, lxml,
  fontTools, kiwisolver, cycler, contourpy`.
- **The three new mutants and the four other decorator drops**: each is killed by the test
  the note names (RG3-N1 is the exception).
- **Citations.** Every `tests/<file>.py::<name>` in the nine changed files resolves to a
  `def`. The exception is `ci.yml`'s `tests/ap4_docx.py::needs_extra`, a module attribute
  that exists.

## What I could not check

- The `docx-extra` and `test` CI jobs: the branch has not been pushed.
- Word: no Word was driven.
- Byte identity on another platform: none is claimed.
- Licences of the extra's closure: not re-read (the note says the same).
- The hidden-extra figures in PowerShell: Git Bash only.
- E10's content beyond the merge-tree names, the merged lock and the `day=10` count.

## Sentences I refused to write

- "FA2-B1 is closed." It is closed for F5. RG3-B1 leaves F2 and F4 open.
- "The PNGs print the engine's numbers, and a test holds it." They print them today. No test
  holds the F2 or F4 legend.
- "A `matplotlibrc` cannot reach the figures." I could not break it with the 19 keys listed.
  That is a list, not a class (RG3-S2).
- "The note's figures re-measure exactly." The licensed DOCX and `run.json` sizes are
  run-dependent (RG3-N3).
- "The branch is ready to merge." It is not while RG3-B1 is open, and no CI has run on it.
