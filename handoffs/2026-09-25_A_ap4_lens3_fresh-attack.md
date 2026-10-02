# A-P4 lens 3, fresh attack: build day 10, lane A at `fd9488f` (branch `a-p4-docx`)

**Verdict: FAIL.** One blocker (FA3-B1). The engine numbers drawn in the F2/F3 and F4 PNG legends are read by no test. Three mutants that print those numbers rounded differently from the HTML each survive all 190 ap4 tests. FA2-B1 was closed for the F5 value texts and the F5 criterion legend only. The shipped code prints the right strings today. Three sentence violations and five record-and-carry findings follow.

Lens round 3 ran on **Friday 2 October 2026** (day 10 is still open; the file keeps its 2026-09-25 name). This was a cold fresh-attack lens with no prior context. I committed, pushed, tagged, installed and downloaded nothing. Platform for every figure: Windows 11, `win-amd64-cp314` (CPython 3.14), docxtpl 0.20.2, python-docx 1.2.0 and matplotlib 3.11.2 from the pip user site (as `doctor --offline` prints them), Git Bash. I used four detached worktrees under `scratchpad/lens-AP4-r3-fresh-attack/`: `wt` (`fd9488f`), `wt-old` (`e2c98df`), `wt-mut` (`fd9488f`, my mutants) and `wt-81f` (`81f1102`, HTML and wheel baseline). Before each worktree's first figure, `python -c "import proofpack;print(proofpack.__file__)"` printed a path inside it. One probe started in a Git Bash `;`-separated `PYTHONPATH` printed the main tree instead. I discarded it, and every later probe used `C:/` paths and printed the worktree path. Every `proofpack run` carried `--offline`, with `socket.socket`, `socket.create_connection` and `socket.getaddrinfo` replaced by a raiser: 0 calls across 53 CLI runs. I worked read-only in `wt-ap4` and the main tree. This note is the only file I wrote outside my worktrees. All four worktrees are removed.

## Suite, markers, lint, sweep (`wt` at `fd9488f`, `PYTHONUTF8=1`)

| command | result |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1777 passed, 2 skipped, 1 xfailed in 175.82s`. The skips are `test_doctor_cli.py:57` (write access) and `test_e8_repair4.py:405` (confusables path relative to the lens worktree, environmental). This is the note's 1,780 collected. |
| `-m ap4` / `-m day10` (`PROOFPACK_REQUIRE_DOCX=1`) | `191 passed, 1589 deselected` / `191 passed, 1589 deselected` |
| `-m ap3` / `day9` / `day8` / `ap2` / `day7` / `day6` / `day5` | `172 passed` / `331 passed` / `469 passed, 1 skipped` (the environmental skip) / `90 passed` / `139 passed` / `285 passed` / `54 passed` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `251 files already formatted` |
| `PROOFPACK_REQUIRE_DOCX=1 python scripts/mutation_sweep.py --marker ap4` | `17 planted, 17 killed, 0 survived; 443 s`; the three new mutants `1 failed, 117/118/119 passed` |
| `tests/test_ap4_repair2.py` copied into `wt-old` (`e2c98df`) | `30 failed, 7 passed in 5.79s`. The 7 that pass are the note's 7 pins, by name. At `e2c98df` the rc test fails with `RuntimeError: Failed to process string with tex because latex could not be found`, `assert 1 == 0`. |
| `make_docx_templates.py --out DIR` | `T1.docx` 52,840 / `T7.docx` 40,587 / `T8.docx` 42,510 bytes, `cmp` equal to the committed three |
| `python -m uv lock --check --offline` / `doctor --offline` | `Resolved 72 packages`, exit 0 / `[ok  ] docx extra  docxtpl 0.20.2, python-docx 1.2.0, matplotlib 3.11.2`, `All essential checks passed.` |

## Blockers

### FA3-B1. The F2/F3 and F4 PNG legends carry engine numbers that no test reads; three differently-rounding mutants survive all 190 ap4 tests

The F2 legend is `ROC curve (solid); AUROC 0.835 [0.795, 0.876]`. The F4 legend is `deciles (points, solid bars); slope 1.349 [1.056, 1.642]; intercept −0.749 [−1.005, −0.493]`. These are Numbers formatted by `render/format.py` and drawn into PNGs inside `T1.docx`, where python-docx text extraction cannot reach them. No test outside `tests/test_ap4_repair2.py` reads a legend text, and that file reads only the F5 criterion legend (`grep -n "legend\|get_texts\|\.texts" tests/test_ap4_*.py` gives no hit in any other ap4 file). Lens 2's fix for FA2-B1 asked for "the legend texts with the SVG legend strings"; the repair compared the F5 ones only.

I planted three mutants in `wt-mut`, each alone, and ran `PROOFPACK_REQUIRE_DOCX=1 pytest -x -q -m ap4 --ignore=tests/test_sweep_ap4.py`:

| id | change in `figures_png.py` | drawn text (read from the artists) | result |
|---|---|---|---|
| L3-n | `_curve_figure`: `label=spec["legend"]` -> `re.sub(r"(\d\.\d\d)\d", r"\1", spec["legend"])` | F2 legend `ROC curve (solid); AUROC 0.83 [0.79, 0.87]` | **SURVIVED** `190 passed, 1589 deselected in 42.12s` |
| L3-o | `f4_figure`: the same rewrite on the decile line's `label` | F4 legend `...; slope 1.34 [1.05, 1.64]; intercept −0.74 [−1.00, −0.49]` | **SURVIVED** `190 passed in 39.88s` |
| L3-j | `f4_figure`: the same rewrite applied to `fig.legend(...).get_texts()` after the legend is built | as L3-o | **SURVIVED** `190 passed in 44.24s` |

The T1 HTML prints `AUROC 0.835 [0.795, 0.876]` and `slope 1.349 [1.056, 1.642]; intercept −0.749 [−1.005, −0.493]` once each, in the SVG. A real defect of this shape would put a second rounding of the same Number into the DOCX, and nothing would fail. This is the blocker class "a wrong or differently rounded number", reopened as FA2-B1 was. The shipped code is right: unmutated, the PNG legend strings equal the SVG `fig-text` strings above.

Repro (scratch worktree of `fd9488f`, Git Bash): in `src/proofpack/render/figures_png.py` replace `        label=spec["legend"],` (the one followed by `gid="series"`) with `        label=__import__("re").sub(r"(\d\.\d\d)\d", r"\1", spec["legend"]),`, then `PYTHONPATH=$PWD/src PROOFPACK_REQUIRE_DOCX=1 python -m pytest -q -m ap4` gives `191 passed`. Use the Edit tool for the replacement: heredoc backslashes collapse here.

Fix: one test that, after `fig.canvas.draw()`, compares every visible `Text` of each of the eleven figures (legend texts, `ax.texts`, F2 annotations, F4 `flag_short`, tick labels) with the SVG's text nodes for that figure. Add L3-n and L3-o (or L3-j) to `AP4_MUTANTS`. One test of that shape also closes FA3-N1 and FA3-N2's first item.

## Sentence violations in shipped text (record-and-carry; `sentence_violation`)

### FA3-S1. `src/proofpack/render/docx.py`: "What reaches those rewrites through the CLI (``proofpack run`` with a licence, ...). ``criteria.yaml`` ``model.name: m{_{ 7*7 }_}n`` ran to exit 4 with ``run.json`` written"

With a licence, that run does not exit 4. Measured: `model.name: "m{_{ 7*7 }_}n"`, `run --format json,html,docx --templates T8 --offline` with an ephemeral licence gave `rc=0`, files `T8.docx, T8.html, ingest_report.json, pseudonyms.json, run.json`, and `T8.docx`'s `document.xml` holds `m{{ 7*7 }}n` twice and `m49n` zero times. Exit 4 is the outcome with no licence (measured: `rc=4`, `HTML and DOCX not written: licence refused (no_file)`). That run writes no DOCX, so the measurement cited under "What reaches those rewrites" does not show the rewrite being reached. The sentence predates this repair, but repair 2 placed it under the new "with a licence" heading. Repro: `cli.py`-style driver (`test_run_cli._criteria`, `conftest.write_licence`, `ephemeral_registry()`) with `crit["model"]["name"] = "m{_{ 7*7 }_}n"`.

### FA3-S2. `src/proofpack/render/figures_png.py`: "every labelled line has a dash pattern of its own and a text label in the legend"

Measured on the synthetic document: F4's labelled line `decile:1` (label `deciles (points, solid bars); ...`) has `get_linestyle() == 'None'` and marker `'o'`, so it has no dash pattern. F2's labelled `series` is `'-'`. The test it rests on, `test_two_labelled_series_at_most_each_with_its_own_dash_pattern_in_the_tokens`, leaves marker lines out of the style check, and lens 2's mutants F and M (solid reference line) still survive (carried). Name what the test inspects instead: distinct line styles among labelled lines with no marker.

### FA3-S3. `tests/test_ap4_repair2.py` module docstring: "Each sentence below is closed by a phrase test that fails at ``e2c98df``"

The first bullet below it, FA2-B1, is closed by `test_f5_png_value_texts_equal_the_svg_value_texts_in_every_f5_figure` and `test_f5_png_criterion_legend_equals_the_svg_criterion_text`. Both pass at `e2c98df` (measured, `-rA`), and neither is a phrase test. Their bite is shown by mutants, as the note says. Only the docstring overstates it.

## Record-and-carry findings

### FA3-N1. Figure tick labels are read by no test (axis constants, not engine Numbers)

L3-f (F5: `ax.set_xticks([0.0, 0.5, 1.0], ["0", "0.5", "1"])`; the SVG prints `0.0 0.5 1.0`) SURVIVED with `190 passed`. L3-g2 (F2/F3 and F4: the label `0.6` at position 0.5) SURVIVED with `190 passed in 41.63s`. Unmutated, every F5 x tick label equals the SVG's (`0.0`, `0.5`, `1.0`; my comparison after `canvas.draw()`). I graded this below blocker because the tick values are constants typed in both drawers, not engine output. The FA3-B1 test closes it.

### FA3-N2. More surviving mutants

| id | change | result |
|---|---|---|
| L3-i | F4 `flag_short` text not drawn (`200/200 convention: fewer than 200 events or non-events` is in the synthetic SVG) | SURVIVED `190 passed in 40.05s` |
| L3-h | F5 criterion legend drops `[unverified] ` from the label | SURVIVED `190 passed`. The test's author is `Dr A.`, so the mutant is equivalent on that input. With author `[unverified] Dr B.` the shipped legend reads `customer criterion C_a ([unverified] Dr B., 2026-03-01): 0.4275 (heavy dashed)`. |
| L3-k | `props.title = ...` dropped (lens 2 G) | SURVIVED `190 passed in 43.12s` (still open, carried) |

Killed (for the record): L3-a `style.context("classic")`, L3-b `png_bytes` unwrapped, L3-c `f4_figure` unwrapped, L3-d2 `rc_context({"text.usetex": False})`, L3-d3 `rc_context(rcParamsOrig)`. Each was killed by `test_a_matplotlibrc_in_the_working_directory_changes_no_png_byte`. L3-e (tier superscripts stripped from F5 value texts) was killed by `test_f5_png_value_texts_equal_the_svg_value_texts_in_every_f5_figure`. L3-l (`PP Status` dropped) was killed by `test_no_forbidden_word_outside_customer_text_and_status_words_only_in_pp_status[T1]`. L3-m (customer inline style dropped) was killed by `test_customer_text_is_in_the_manufacturer_styles_and_labelled`.

### FA3-N3. FA2-N1 (mathtext) reaches the pack through `criteria.yaml` as well as the CSV

Lens 2 could not check this route. With `criteria[0].scope = {attribute: sex, level: "*"}` (`ci_lower_bound`, sensitivity, op1) and `author: "$\foo$"`, the licensed CLI gave `rc=5`, files `T1.html, ingest_report.json, pseudonyms.json, run.json`, and `internal error: ValueError: \foo ... ParseFatalException: Unknown symbol: \foo`. Author `$x^2$` and operating-point id `$x$` both gave `rc=0`, with the F5 legend and the F2 annotation drawn as mathtext. The CSV route still reproduces at `fd9488f`: site level `$\foo$` gives `rc=5` with the same four files. The carried fix (`text.parse_math: False` in `_builtin_rc`, or `set_parse_math(False)`) needs CLI tests for a level, an author and an operating-point id. `$\foo$` must be built with `chr(92)` or the Edit tool: a Git Bash heredoc turned my first `\\f` into U+000C, which S02 halted.

### FA3-N4. A criterion value outside [0, 1] is clipped out of the PNG while the legend states it

`value: 1.2` on sex/sensitivity/op1: the PNG `axvline` at x = 1.2 lies outside `xlim (0, 1)` and is not visible. The legend still reads `...: 1.2 (heavy dashed)`. The SVG path sits at px 466, right of the plot's right edge at 420, in the value-text column. `value: -0.1` is the mirror case. Both drawers agree in data coordinates (my parity check passed). Whether a criterion line off the axis prints is a renderer question for lanes E and A, not a number defect.

### FA3-N5. Still open from lenses 1 and 2, re-measured here

- RG1-N7: `T1 · FDA AI-DSF performance evidence attachment set` is still the one body paragraph of 50 in `T1.docx` that names the AI-DSF guidance without `not for implementation` (T7 0 of 6, T8 0 of 11). Lane E, DEC-71(a).
- FA-R5: `python -m uv build --wheel --offline` gives 510,533 bytes and 85 entries at `fd9488f`, against 381,262 and 80 at `81f1102` (+129,271). The three `.docx` are inside, and `METADATA` has `Provides-Extra: docx` with three `extra == 'docx'` requirements. The site pins `81f1102` (DEC-43), so the demo's wheel is unchanged until the pin moves. Josh's call.
- FA-R6: the 23 `PP` styles name `Cascadia Mono`. `styles.xml` also names `Courier` outside the PP styles, from python-docx's default template.
- FA2-N1: reproduced (FA3-N3).

## What I could not break (what I tried)

- **Numbers.** I wrote my own formatter: exact-binary `Decimal`, half-even, U+2212, signed points. I traced 48 strings from the synthetic document's JSON, and every one is in both the T1 DOCX text and the T1 HTML. They are the overall PPV/NPV/accuracy sentences (`96/162 (59.3%), 95% CI 51.6% to 66.5%`) and youden/LR+/LR−/DOR/balanced-accuracy (`was 9.364, 95% CI 5.755 to 15.235`). They include every subgroup level's Se and Sp `k/n (%) [CI]` with tiers (`18/27 (66.7%) [47.8, 81.4]ᵇᶜ`), every level's AUROC, and the Se differences (`−9.9 [−37.8, +14.5]`). Then, with my own lxml reader of every `w:t`/`w:tab`/`w:br` in document, header and footer parts: of the 2,877 digit tokens in T1/T7/T8 (1,964 / 515 / 398; 485 / 141 / 77 distinct), none is missing from the HTML's visible text. Every table cell holding a digit (371 / 27 / 100, the anchor margin notes aside) equals an HTML `<td>`/`<th>` text. The one apparent exception is the T1 criteria cell whose two lines the HTML joins with `<br>`. There are 0 `txbxContent` parts.
- **Footers and watermark.** 15 renders: T1/T7/T8 × valid, `TRIAL`, `LICENCE EXPIRED - not for submission`, `NO LICENCE - not for submission`, `SYNTHETIC DATA - not for submission`. Sections and footer parts are 9/3/3, and every `sectPr` has a `default` footer reference. No `titlePg`, no `evenAndOddHeaders`. Every referenced footer holds `not for implementation`, a `PAGE` field and `html.footer_marks(document)`. A grace-state licensed CLI run (expiry 5 days ago) wrote 9/3/3 footers, each with the disclaimer and `PAGE`.
- **Injection.** Through the CLI: 12 payloads (`<w:p>INJX</w:p>`, `</w:t></w:r></w:p><w:p><w:r><w:t>INJC`, `&lt;w:br/&gt;`, `{{ 7*7 }}J{% raw %}R{% endraw %}`, `m{_{ 7*7 }_}n`, U+202E, U+2028, U+0085, `$x^{2}$`, `$\foo$`, U+0007, U+000C) × 3 slots (a CSV `site` level, `criteria[0].justification`, `criteria[0].author`). Every XML part of every written DOCX parsed with lxml. There is no raw `<w:p>INJX`, no unescaped `INJC` and no `49J` / `m49n`. U+0085, U+0007 and U+000C halted at S02 / H08 (exit 3, nothing written). The only crash is FA3-N3.
- **Figures.** From my own SVG parse through each `data-map`, against the artists: 894 coordinates on the synthetic document (F2 series and operating point, all nine F5: estimates, interval ends, reference, labels, value texts), worst `|d| = 2.22e-16`. The same parity held for two criteria (`0.4275`, `0.1 + 0.2`, which prints `0.30000000000000004`), for `1.2`, `−0.1`, a level-scoped criterion and a `point_estimate` criterion. With a planted `suppressed` row and a `not_estimable_reason` row, the PNG texts are `‡` and `n.e. (planted_reason)`, equal to the SVG. Colours over the eleven figures (`findobj`): patch faces are `bg` ×23 and `line` ×10. Lines are `ink` ×147 and `ink-faint` ×22. Texts are `ink` ×111 and `#000000` ×14, the legend texts and F2 annotation the docstring names. `T1.docx` media: 11 PNGs with chunks `IHDR, pHYs, IDAT, IEND` only, and every `wp:extent cx="5760000"`.
- **The rc fix (FA2-S8).** PNG joint hash prefix `7d0b59a88ce3ca1f` and `T1.docx` `11dba1474cc0a8c6` (the note's figures) were unchanged under each of: a clean directory; `./matplotlibrc` with 18 keys the test does not feed (`figure.facecolor`, `savefig.bbox: tight`, `font.family: serif`, `path.sketch`, `text.antialiased: False`, `axes.unicode_minus: False`, `axes.formatter.use_locale`, `mathtext.fontset`, `legend.frameon`, and others); the same file through `MATPLOTLIBRC`; through `MPLCONFIGDIR`; `MPLCONFIGDIR/stylelib/default.mplstyle`; and `rcParams` set in-process before the render.
- **The extra.** With a meta-path finder hiding `docx, docxtpl, matplotlib, lxml, PIL` and `find_spec` returning `None`, `-m ap4` gave `80 passed, 111 skipped`, so the main CI job is not broken. CLI `json,html` gave `rc=0` with three HTML files. `json,html,docx` and `docx` gave `rc=7`, the one `EXTRA_LINE`, and no out directory. No extra module was loaded. A plain process importing `proofpack`, `.cli`, `.run`, `.render.html`, `.render.t1`, `.render.t7`, `.render.figures` and `.render.docx` loads none of the nine closure modules.
- **Lock.** `git diff 81f1102 fd9488f -- uv.lock` adds exactly nine packages (contourpy 1.4.0, cycler 0.12.1, docxtpl 0.20.2, fonttools 4.66.0, kiwisolver 1.5.1, lxml 6.1.3, matplotlib 3.11.2, pillow 12.3.0, python-docx 1.2.0) and changes one line (`provides-extras`). numpy 2.5.3, scipy 1.18.1, statsmodels 0.15.0 and scikit-learn 1.9.0 are unchanged.
- **HTML unchanged.** On the same assembled document at `81f1102` and `fd9488f`, the T1/T7/T8 HTML sha256 prefixes are `8ed8a806b8b7`, `df115ca9d9ba`, `d32233e3b375` and, with `TRIAL`, `7e0ca94d8d57`, `c0d834d93527`, `06481232c7bd`. `git diff 81f1102 fd9488f` touches nothing under `stats/` and no golden or fixture file.
- **Determinism.** With `manifest.started = 2026-10-02T09:41:07.987654+01:00`, under `PYTHONHASHSEED=1` and `=2` with `TZ=America/New_York`, T1/T7/T8 were identical across processes (`9a6404355469`, `9e1ff84842b4`, `8db4a2036384`). Every zip mtime is `(2026, 10, 2, 8, 41, 6)`, and `core.xml` created and modified are `2026-10-02T08:41:07Z`.
- **Wiring.** Expired past grace: `rc=4`, `HTML and DOCX not written: licence expired (expired_past_grace)`. No licence: `rc=4`, `licence refused (no_file)`. Neither writes a `.docx`. `--templates T12`, `T1,T12` and `T2` with docx: `error: unknown --templates id 'T12'; choose from T1, T7, T8` (or `'T2'`), `rc=5`, no out directory.
- **Shipped sentences confirmed.** In run 36020197050 (`gh run view`: `81f1102...`, `2026-09-24T15:26:28Z`, success), the step "record the base image digest" succeeded and printed `docker.io/library/python:3.12-slim@sha256:2f17...06a9` at `15:26:54.4227792Z`. The oracle step printed both quoted lines at `15:28:49Z`. `git ls-remote origin` lists no `a-p4-docx`. The 4879ac5 hidden-extra counts are lens 2 regression's re-measurement (RG2-N1). The `docx.py` import, core-property and `fixed_zip` sentences match the code.

## What I could not check

- Word: no copy was driven (pagination, fields, the Cascadia Mono substitution).
- The `docx-extra` CI job: the branch is unpushed.
- Byte identity on another platform. I also could not check the rc test on a machine where LaTeX is installed: there the `e2c98df` failure would be a hash difference, not the `RuntimeError`.
- FA2-N3 (table structure) was not re-measured beyond the cell-value comparison above.

## Sentences I refused to write

- "The figures print the engine's numbers, and the tests hold it." They print them today; no test holds the F2/F4 legends (FA3-B1).
- "No matplotlibrc can change the figures." I fed four routes and 25 keys, not every file.
- "No customer string can break the DOCX render." `$\foo$` in an author or a level does (FA3-N3).
- "CI has run the ap4 tests." The branch is unpushed.

## For the repair

1. FA3-B1 (blocks PASS): compare every visible `Text` of the eleven figures with the SVG text nodes after `canvas.draw()`, and add L3-n and L3-o to `AP4_MUTANTS`. That also closes FA3-N1, L3-i and, with a `[unverified]` author fed, L3-h.
2. FA3-S1/S2/S3: reword to the measured outcomes above.
3. FA3-N3 with FA2-N1: mathtext off for customer strings, with CLI tests for a level, an author and an operating-point id.

This repair touches no statistical gate; a cold check of the new test is enough.
