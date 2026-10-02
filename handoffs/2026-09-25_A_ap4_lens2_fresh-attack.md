# A-P4 lens 2, fresh attack: build day 10, lane A at `e2c98df` (branch `a-p4-docx`)

**Verdict: FAIL.** One blocker: a non-equivalent mutant that prints a differently rounded number in the DOCX survives every ap4 test (FA2-B1). The shipped code prints the right numbers - every number I traced matches, and no footer, injection, figure-coordinate, lock, network or import check failed - but nothing tests the numbers drawn inside the F5 PNGs. Eight sentence violations in shipped text follow, two of them pinned as "present" by `tests/test_ap4_sentences.py`, then ten record-and-carry findings.

Lens round 2 ran on **Friday 2 October 2026** (day 10 is still open; the file keeps its 2026-09-25 name). Cold fresh-attack lens session; no prior context. I committed nothing, pushed nothing, installed nothing, downloaded nothing, made no tag. Every figure below was measured in this session on Windows 11, `win-amd64-cp314` (CPython 3.14.6; docxtpl 0.20.2, python-docx 1.2.0, matplotlib 3.11.2 from the pip user site, as `doctor --offline` prints them), in Git Bash. I worked in four detached worktrees under `scratchpad/lens-AP4-r2-fresh-attack/`: `wt-e2c` (`e2c98df`: suite, markers, lint, sweep, probes), `wt-487` (`4879ac5`), `wt-81f` (`81f1102`: HTML and wheel comparison) and `wt-mut` (`e2c98df`: my mutants). In each, `PYTHONPATH` was forced to that worktree's `src` (plus its `tests` for the probes), and `python -c "import proofpack;print(proofpack.__file__)"` printed a path inside it before I trusted any number. Every `proofpack run` carried `--offline`. With `socket.socket`, `socket.create_connection` and `socket.getaddrinfo` replaced by a function that raises, `run --format json,html,docx --templates T1,T7,T8` gave exit 0 and six documents. I worked read-only in `wt-ap4` and the main tree. The only file I created outside my worktrees is this note. All four worktrees are removed.

## Suite, markers, lint, sweep (`wt-e2c`, `PYTHONUTF8=1`, `PROOFPACK_REQUIRE_DOCX=1`)

| command | result |
|---|---|
| `python -m pytest -q -p no:cacheprovider -rs` | `1740 passed, 2 skipped, 1 xfailed in 204.14s`. The skips are `test_doctor_cli.py:57` (write access) and `test_e8_repair4.py:405` (the confusables file looked up relative to my scratch path; environmental, RG1-N10). The builder's `1741 passed, 1 skipped` is the same 1,743 collected. |
| `-m ap4` / `-m day10` | `154 passed, 1589 deselected` / `154 passed, 1589 deselected` |
| `-m ap3` / `-m day9` / `-m day8` / `-m ap2` | `172 passed` / `331 passed` / `469 passed, 1 skipped` (the same environmental skip) / `90 passed` |
| `python -m ruff check .` / `ruff format --check .` | `All checks passed!` / `248 files already formatted` |
| `python scripts/mutation_sweep.py --marker ap4` | `14 planted, 14 killed, 0 survived; 342 s` (`ap4_f5_rows_flipped` `1 failed, 85 passed`) |
| `python scripts/make_docx_templates.py --out DIR` | `T1.docx` 52,840, `T7.docx` 40,587, `T8.docx` 42,510 bytes; `cmp` byte-equal to the committed three |
| `tests/test_ap4_repair1.py` copied into `wt-487` | `21 failed, 3 passed in 3.25s` (as the repair note says; the three are FA2-N11 below) |
| `python -m uv lock --check --offline` | `Resolved 72 packages`, exit 0 |

## Blockers

### FA2-B1. The numbers drawn in the F5 PNGs are not tested: a mutant that rounds them differently survives all 154 ap4 tests

In `src/proofpack/render/figures_png.py::f5_figures` I replaced the value text beside each row, `row["value"],`, with `f"{row['est']:.2f}" if row["drawn"] else row["value"],`. That is a number formatted outside `render/format.py`, rounded differently from the HTML. The F5 age/sensitivity figure then carries the text artists `['0.78', '0.79', '0.67']`. The SVG and the T1 table print `29/37 (78.4%) [62.8, 88.6]ᶜ` and so on for the same rows. With the mutant planted, `pytest -q -m ap4` (all 154, `PROOFPACK_REQUIRE_DOCX=1`) printed `154 passed, 1589 deselected in 33.52s`. The figure tests compare the artists' x/y coordinates, the y tick labels and the dash styles. None of them reads `ax.texts`. A PNG's text cannot be extracted from the DOCX, so the round-trip tests cannot see it either. The shipped code is right today: I compared every text artist of the eleven figures with the T1 HTML, and the only strings not in the page are the three legend labels `chance (dashed)`, `identity (dashed)` and `overall estimate (dashed)`. This reopens the blocker class "a wrong or differently rounded number". Mutant I (below) is the same gap for the F5 criterion legend's `value_text`.

Repro (in a scratch worktree of `e2c98df`): `sed -i 's/^                    row\["value"\],$/                    f"{row['"'"'est'"'"']:.2f}" if row["drawn"] else row["value"],/' src/proofpack/render/figures_png.py && PYTHONPATH=$PWD/src PROOFPACK_REQUIRE_DOCX=1 python -m pytest -q -m ap4` gives `154 passed`.

Fix: one test that compares each F5 figure's `ax.texts` with the SVG's `fig-value` texts, and the legend texts with the SVG legend strings. Add the mutant to `AP4_MUTANTS`.

## Sentence violations in shipped text (record-and-carry; `sentence_violation`)

### FA2-S1. `Dockerfile` lines 6-8: the grep step "has not yet run with that step". It had run on 24 September.

GitHub Actions run `36020197050` (push of `81f1102`, 24 September 2026 15:26Z, success) ran the job "Docker image smoke (linux/amd64, no push)". Its step "record the base image digest (the Dockerfile pin is [unverified] until this is read)" succeeded. At `2026-09-24T15:26:54.4227792Z` it printed `docker.io/library/python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9`. This branch's `ed5d507` (25 September 23:01) wrote the sentence a day later. `tests/test_ap4_sentences.py:43` pins it as present (`("Dockerfile", "has not yet run with that step")`). The digest the comment waits for is in that log, so the `[unverified]` pin can now be read from a primary record. Repro: `gh run view 36020197050 --log | grep -a "slim@sha256:[0-9a-f]\{64\}" | grep -v "grep -o"`.

### FA2-S2. `.github/workflows/ci.yml` lines 31-33: the oracle step "has not run yet (A-P4, 25 September 2026), so whether those lines appear in a job log is not measured". It had run, and the lines are there.

The same run, job "pytest + ruff", step "oracle capture compared with fixtures/oracles_v1.json", succeeded on 24 September. It printed `captured.F3-delong.values.paired_p: committed 0.0593464387919198 fresh 0.05934643879191981 abs difference 6.939e-18 iterative tolerance 1e-06 within` and `captured values: 64 identical, 1 differ within their tolerance, 0 differ outside it`. `tests/test_ap4_sentences.py:42` pins the phrase `this step has not run yet` as present. Repro: `gh run view 36020197050 --log | grep "oracle capture compared" | grep "committed"`.

### FA2-S3. `ci.yml` (the `docx-extra` comment) and `tests/ap4_docx.py`: "Neither job had run anywhere when this was written (26 September 2026)"

The two jobs named are `docx-extra` and the main `test` job. The main test job ("pytest + ruff") had run on `main` on 24 September (run `36020197050`, success). This branch changes nothing in that job except one comment (`git diff 81f1102 e2c98df -- .github/workflows/ci.yml` has two hunks: the oracle-step comment and the new job). The sentence is true of `docx-extra` and of this branch, not of "neither job". Repro: `gh run list -b main -w ci -L 3`.

### FA2-S4. The "with the modules hidden" figures in `tests/ap4_docx.py`, `ci.yml` and `scripts/mutation_sweep.py` are the 130-test tree's, not the tree they ship in

The three texts say `-m ap4` gave `29 passed, 101 skipped` without `PROOFPACK_REQUIRE_DOCX` and `23 failed, 47 passed, 60 errors` with it. 29 + 101 = 130 is the ap4 count at `4879ac5`. At `e2c98df`, with the same `-p` plugin (`sys.modules[name] = None` for the three), I measured `50 passed, 104 skipped` and `26 failed, 68 passed, 60 errors`. None of the texts names the tree measured. The `mutation_sweep.py` comment's `(29 passed, 101 skipped)` for `ap4_footer_emptied_in_render` has the same problem. Repro: `PYTHONPATH="$PWD/src;<dir with hide_docx.py>" python -m pytest -q -p hide_docx -m ap4`.

### FA2-S5. `src/proofpack/render/docx.py` docstring: "a newline or a tab in a declaration halts at H08 ... so the line-break rewrite is reachable through the Python API only". It is reachable through the CLI.

`criteria.yaml` with `criteria[0].justification: "line one\nline two"`, then `run --format json,html,docx --templates T1,T7,T8 --offline` under a valid ephemeral licence, gave `EXIT 0` and all six documents. `word/document.xml` matches `line one</w:t>\s*<w:br/>` once in `T1.docx` and twice in `T8.docx`. H08 does reject a form feed in the same field (`HALT H08: declaration invalid at criteria/0/justification: control character U+000C; remove it`, exit 3). The sentence generalises from `model.name` to every declaration field. Repro: `probes/cli_just.py justification 'line one\nline two'` (harness: `test_run_cli._criteria`, `conftest.write_licence`, `confirmed_mapping`, `main([... "--offline"])`).

### FA2-S6. `docx.py` docstring: "Two rewrites happen after rendering and are docxtpl's"

docxtpl rewrites more than two things after rendering. In `declarations.model.name` of T8 through `render_docx_bytes`: `"a\x0cb"` turns `w:type="page"` from 0 to 1 and `<w:p>` from 474 to 476, and `"a\x07b"` turns `<w:p>` from 474 to 475. Lens 1 measured the same as FA-R2. A tab also becomes `<w:tab/>`. Only the newline and the four sequences are named. Through the CLI, H08 halts U+000C, so the extra rewrites are API-only today. The undercount stands either way.

### FA2-S7. `docx.py` docstring: "docxtpl, python-docx and matplotlib are imported inside :func:`render_docx` and :func:`proofpack.render.figures_png` only"

`render_docx` imports nothing. The extra's imports in `docx.py` are in `_rich` (`docxtpl.RichText`), `attach_images` (`docx.shared.Mm`, `docxtpl.InlineImage`) and `render_docx_bytes` (`docxtpl.DocxTemplate`). The import-hygiene property holds (FA2 "could not break"). The sentence names the wrong function. Repro: `grep -n "noqa: PLC0415 - the extra" src/proofpack/render/docx.py`.

### FA2-S8. The figure determinism and colour sentences do not hold with a `matplotlibrc` in the working directory

The sentences are in `figures_png.py` ("the colours are the theme's tokens", "two renders of one document give identical bytes on one machine") and `docx.py` ("two renders of one ``run.json`` are byte-identical"). matplotlib reads `./matplotlibrc` from the current directory at import (`matplotlib.matplotlib_fname()` printed `matplotlibrc`), and `figures_png` does not reset `rcParams`. I rendered the same synthetic T1 three ways:

- No rc file: sha256 `11dba1474cc0a8c6...`.
- From a directory holding `axes.grid: True` / `savefig.transparent: True` / `text.color: red` / `legend.labelcolor: red`: sha256 `4a508b640e53cd27...`, legend text colour `{'#ff0000'}`, x gridlines visible.
- From a directory holding `text.usetex: True`, through the CLI: `internal error: RuntimeError: Failed to process string with tex because latex could not be found`, `EXIT 5`, files `T1.html, ingest_report.json, pseudonyms.json, run.json` (no `.docx`, no T7/T8 HTML).

The coordinates still match (the artists' data do not change). Fix: draw inside `matplotlib.rc_context(matplotlib.rcParamsDefault)` (or set every rcParam the drawer relies on) and test from a directory with a hostile `matplotlibrc`.

## Record-and-carry findings

### FA2-N1. Customer text with a pair of `$` is parsed as mathtext in the F5 PNG; `$\foo$` crashes the pack after `run.json`

F5 row labels are the raw subgroup levels (`figures.f5_data`: `str(r.get("level"))`). They go to `ax.set_yticklabels`, which parses `$...$` as mathtext. I replaced the CSV `site` value `S1` with `$\foo$` (185 rows) and ran the CLI licensed, with `--offline` and sockets blocked. Result: `internal error: ValueError: \foo ... ParseFatalException: Unknown symbol: \foo`, `EXIT 5`, files `T1.html, ingest_report.json, pseudonyms.json, run.json`. Through the API, `a$b$c`, `$1,000-$2,000` and `$x^{2}$` render without error but are drawn as mathtext, so the PNG label differs from the HTML's. The test compares `get_text()`, the raw string, so it passes. The same applies to the F2 operating-point annotation and the F5 criterion legend (customer strings). Same class as FA-R1, which lens 1 graded record-and-carry, but `$` in a category label is a far likelier input than U+FFFE. Fix: escape `$` (or set `usetex`/`parse_math` off: `Text.set_parse_math(False)`) for every customer string handed to matplotlib. Repro: `probes/cli_level.py '$\foo$' site S1`.

### FA2-N2. Surviving non-equivalent mutants (my list; the committed sweep's 14 are all killed)

Each was planted alone in `wt-mut`, then `pytest -x -q -m ap4 --ignore=tests/test_sweep_ap4.py` was run (`PROOFPACK_REQUIRE_DOCX=1`):

| id | change | result |
|---|---|---|
| A | F5 value text `row["value"]` -> `f"{est:.2f}"` | **SURVIVED** `153 passed` (FA2-B1) |
| I | F5 criterion legend `{crit['value_text']}` -> `{crit['value']}` | SURVIVED `153 passed` (same gap; needs a planted criterion to show) |
| D | `ax.set_facecolor(c["bg"])` -> `"#fff8dc"` (not a token) | SURVIVED `153 passed` |
| E | `fig.set_facecolor(...)` -> `"#ffffff"` (not a token) | SURVIVED `153 passed` |
| F | F4 identity line `linestyle="-"` while its label says "identity (dashed)" | SURVIVED `153 passed` |
| M | `REFERENCE_DASHES = (1, 0)` (drawn solid; `!= "-"` still true) | SURVIVED `153 passed` |
| H | F2 operating-point annotation text `op` -> `""` | SURVIVED `153 passed` |
| G | `props.title = ...` deleted (core title falls back to python-docx's) | SURVIVED `153 passed in 40.37s` (run by hand) |
| N | reference line colour `ink_faint` -> `ink` (still a token) | SURVIVED (near-equivalent) |
| P | strip fill `line` -> `ink` (still a token) | SURVIVED (near-equivalent) |
| B | `started_datetime` drops `.astimezone(UTC)` | SURVIVED. Equivalent for engine output: `manifest.py:68` always writes `...Z`. |
| C | `markdown_blocks` keeps backticks | killed (`test_markdown_blocks_reads_paragraphs_headings_and_a_pipe_table`) |
| O | `savefig(dpi=100)` | killed (`test_png_bytes_are_identical_across_two_renders_and_carry_no_metadata`) |
| Q | F5 y tick labels reversed | killed (`test_f5_rows_reference_line_and_labels_equal_the_svg_for_every_attribute_and_metric`) |

D/E show that the token rule for figure colours is tested on labelled line colours only. F/M show that "colour is never the only encoding" is tested as `linestyle != "-"` and as distinct styles among labelled lines. A dash pattern that draws solid passes both.

### FA2-N3. DOCX table structure differs from the HTML's (numbers identical)

D4 section 5: "Column order fixed so DOCX and HTML are identical", "Total/Overall row last". Comparing every HTML `<table>` of the synthetic T1/T7/T8 with the DOCX tables cell by cell, in order:

- T1-6 (two-by-two) is one table in the HTML and three in the DOCX (`Device positive` in 3 `<w:tbl>`). Each repeats the header and holds one row (`scripts/make_docx_templates.py:1246-1275`, three `b.table` calls).
- Each subgroup table's `Overall` row is a separate table with its own header row in the DOCX (6 tables with `Pre-spec.` against the HTML's 3).
- The difference table for an attribute with no criterion (age) has 4 columns in the HTML and 5 in the DOCX (an empty "Criterion (id) and status" column).
- The criteria table has 189 cells in the HTML and 180 in the DOCX: the justification moves out of the row into a `PP Manufacturer Text` paragraph.

Every number cell of the matched tables is equal. Record, or decide that D4's "identical" means the cell values only.

### FA2-N4. U+FFFE in `criteria[0].justification` is dropped silently in the DOCX; in `model.name` it crashes the render (FA-R1, re-measured)

Through the CLI (`justification: "j￾k"`): `EXIT 0`, six documents. `run.json` holds `'j￾k'`. `T8.docx`'s `document.xml` contains `jk` and no U+FFFE. Through the API, `model.name = "m￾n"` in T8 still raises `XMLSyntaxError: Char 0xFFFE out of allowed range, line 1, column 1317`. The same character crashes the render in one slot and disappears without a word in another. Carry with FA-R1 (lane E's `_CONTROL`).

### FA2-N5. Three repair-1 tests pass at `4879ac5`

They are `test_docxtpl_rewrites_the_four_escape_sequences_and_a_newline`, `test_f5_png_rows_sit_at_the_svg_row_fractions_top_down` and `test_t7_unverified_runs_are_twenty_in_pp_unverified_and_one_in_the_conventions_paragraph`. The repair note declares them as pins, and no `src/` code changed for their items. Each repaired item also has a test that does fail at `4879ac5`: the phrase tests for FA-S3 and FA-S4's note. For FA-R4, I planted `ap4_f5_rows_flipped` at `e2c98df`, and the only failure was `test_f5_png_rows_sit_at_the_svg_row_fractions_top_down` (`1 failed, 152 passed`). I did not grade this a blocker because no repaired defect lacks a test that fails against the old state. Recorded so the grading can be checked.

### FA2-N6 (the repair note, not shipped). "At the tip: `25 passed` (the 22 plus the re-run inline-image test)"

The same note says `tests/test_ap4_repair1.py` collects 24, and 24 + 1 = 25. "the 22" is the miscount the note says was amended out of the commit message.

### FA2-N7. Still open from lens 1, re-measured here

- RG1-N7: the T1 tag line `T1 · FDA AI-DSF performance evidence attachment set` is still the only body paragraph naming the AI-DSF guidance without `draft guidance (January 2025), not for implementation`. I checked at row level: the other unlabelled hits are the scope item that states draft status in its own words and the PCCP guidance's own title. Lane E, DEC-71(a).
- FA-R5: the wheel built by `python -m uv build --wheel --offline` is 509,420 bytes with 85 entries at `e2c98df`, against 381,262 bytes with 80 entries at `81f1102`: +128,158 bytes. The three `.docx` are inside it, and `METADATA` carries `Provides-Extra: docx` plus three `Requires-Dist ...; extra == 'docx'` lines. How the extra stays out of the Pyodide path: the three packages are only `extra == 'docx'` requirements and are imported only inside `render/docx.py` and `render/figures_png.py`. A fresh process importing `proofpack`, `.cli`, `.run`, `.render.html`, `.render.figures` and `.render.docx` holds none of `docx, docxtpl, matplotlib, PIL, lxml, fontTools, kiwisolver, contourpy, cycler`. The site pins `81f1102` (DEC-43), so the demo's wheel is unchanged until the pin moves. Josh's decision, as the repair note asks.
- FA-R6: `PP Mono` / `PP Unverified` name `Cascadia Mono` in all three templates' `styles.xml`.
- FA-R7: `app.xml` still says `Microsoft Macintosh Word` / `Normal.dotm`, and `core.xml` `generated by python-docx`.

### FA2-N8. `test_render_theme._build_wheel` (lane E) still has the non-offline route; not re-measured

Carried by the repair note to day 11. Not re-run here.

## What I could not break (what I tried)

- **Numbers.** I wrote my own formatter (exact-binary `Decimal` half-even rounding, U+2212, signed pp, `k/n (x.x%) [lo, hi]`, three-dp intervals) and traced 52 strings from the synthetic document's JSON: overall op1 Se/Sp/PPV/NPV/accuracy as `k/n`, `%` and `[lo, hi]`; AUROC; calibration slope/intercept/O:E; every subgroup level's Se/Sp `k/n (%) [CI]` and AUROC; the Se differences versus reference. Examples: `96/128`, `75.0`, `[66.8, 81.7]`, `1.349 [1.056, 1.642]`, `−0.749 [−1.005, −0.493]`, `0.710 [0.615, 0.819]`, `30/38 (78.9%) [63.7, 88.9]`, `0.805 [0.597, 0.920]`, `−9.9 [−37.8, +14.5]`. All 52 are in both the DOCX text (python-docx, paragraphs and every table cell) and the HTML text. Wherever an HTML table and a DOCX table hold the same rows (FA2-N3 aside), every cell is equal, in order. A planted `suppressed: true` prints `‡`, and a planted `not_estimable_reason` prints `n.e. (planted_reason)`. The F5 data for those rows is `drawn: False` with `est: None`, so no marker discloses the estimate. The figure's `‡` lives in the PNG. The HTML's extra `‡`/`81.4` counts are the SVG's text nodes.
- **Footers and watermark.** 15 renders (T1/T7/T8 x valid, `TRIAL`, `LICENCE EXPIRED - not for submission`, `NO LICENCE - not for submission`, `SYNTHETIC DATA - not for submission`): sections 9/3/3, footer parts 9/3/3, all referenced. Every `sectPr` has exactly one `footerReference w:type="default"`. There is no `titlePg` and no `evenAndOddHeaders`. Every referenced footer has `not for implementation`, a `PAGE` field and the watermark string from `html.footer_marks`, and none has a stray `not for submission` in the valid state.
- **Injection.** 13 slots: `model.name/version/prior_version`, `operating_points[0].source`, `reference_standard.description`, `clustering.declared_by`, `prevalence[0].label/source`, `subgroups[0].source`, every criterion's `justification/author/date`, and a subgroup level. Each took 7 payloads: `<w:p>...INJ1...`, `</w:t></w:r></w:p><w:p>...INJ2`, `&lt;w:br/&gt;&amp;lt;`, `{{ 7*7 }}|{% raw %}R{% endraw %}|{%p if 1 %}P{%p endif %}|{{r x }}`, `a‮b c d﻿e`, 10,000 `L`, `]]><![CDATA[x`. Rendered in T1/T7/T8, every XML part parsed with lxml, and no `<w:p>`/`<w:tbl>`/`<w:sectPr>`/field count moved. The two `<w:br` moves are T8's YAML echo, 138 -> 139 and 138 -> 144, from the longer YAML. Each payload is found in the extracted text, and the Jinja payload sits only inside `<w:t>` text nodes. The customer parts of claim sentences pass through docxtpl `RichText.add`, which calls `escape(text)`.
- **Figures.** I parsed the SVG myself through each `data-map` and compared it with the artists: F2's 401 vertices, the reference and `op1`; F4's 10 deciles and 10 intervals; the 10 histogram rects through the strip's own map `70.0 372.0 480.0 40.0 0.0 1.0 0.0 40.0`. That is 908 coordinates, worst `|d| = 1.11e-16`. Filled patches: none outside `hist:*`. F2 PNG: identical across two renders (93,623 bytes), chunks `IDAT, IEND, IHDR, pHYs`, no text or time chunk. DejaVu Sans has `ᵃ ᵇ ᶜ ‡ − Δ → ≥`, and drawing every figure raised no warning.
- **Styles.** Every `w:color`/`w:fill` in every `PP` style of the three committed templates is one of `design/tokens.json`'s 18 hex values (0 unknown). No hex literal or `RGBColor(` literal in `docx.py`, `figures_png.py` or the generator (every `RGBColor.from_string(_hex(...))` reads a token). The only typed digits in the templates outside Jinja tags are labels (`95% CI`, section and table numbers).
- **The extra.** I hid `docx, docxtpl, matplotlib, lxml, PIL` (a meta-path finder plus `find_spec` returning `None`) and ran the CLI. `--format json,html` gave exit 0 and three HTML files, with none of the five loaded. `--format json,html,docx` and `--format docx` gave the one `EXTRA_LINE`, `EXIT 7`, and no out directory. The lock moved no oracle library: numpy 2.5.3, scipy 1.18.1, statsmodels 0.15.0 and scikit-learn 1.9.0 are unchanged from `81f1102`. Exactly nine packages were added, and the one `-` line is `provides-extras = ["stats"]`.
- **HTML unchanged.** T1/T7/T8 HTML from the same assembled document, rendered at `81f1102` and at `e2c98df`, have the same sha256 prefixes: `8ed8a806b8b7`, `df115ca9d9ba`, `d32233e3b375` unwatermarked, and `7e0ca94d8d57`, `c0d834d93527`, `06481232c7bd` with `TRIAL`. `git diff 81f1102 e2c98df` touches no file under `stats/`, nor `gates.py`, `criteria.py` or `render/format.py`.
- **Determinism.** I set `manifest.started = 2026-10-02T09:41:07.123456+01:00` and ran under `PYTHONHASHSEED=1` and `=2` with `TZ=America/New_York`. T1/T7/T8 were identical across both processes (`d7ef9cf65f87`, `4ee20d6194be`, `fcc5ab6ac593`). `core.xml` created/modified were `2026-10-02T08:41:07Z`, and every zip mtime was `(2026, 10, 2, 8, 41, 6)`. FA2-S8 is the exception.
- **Wiring.** `--templates T12 --format json,html,docx` printed `error: unknown --templates id 'T12'; choose from T1, T7, T8`, `EXIT 5`, and wrote no out directory. The licence states (`ok`, `grace`, `expired`, none) are asserted by `tests/test_ap4_cli.py::test_the_licence_states_and_which_files_exist`, which passed in my suite. With sockets raising, a docx run gave exit 0.
- **Lens 1's closed items.** FA-S1 and FA-S2: `test_every_test_citation_in_the_module_docstring_names_a_def_in_that_file` passes, and the two ids exist. FA-R4: the sweep's `ap4_f5_rows_flipped` is killed by the new test alone. RP1-1: `ap4_figure_width_100mm` killed (`1 failed, 33 passed`).

## What I could not check

- Word: no copy was driven, so field values, pagination, the landscape section and the Cascadia Mono substitution are unseen.
- The `docx-extra` CI job: the branch has not reached CI.
- Byte identity on another platform.
- Where docxtpl or lxml drops U+FFFE in the justification path (FA2-N4): measured, not traced.
- Whether `$` can reach the F2 annotation or the F5 criterion legend through the CLI. Operating-point ids and criterion labels go through H08 and the schema; I did not try them.

## Sentences I refused to write

- "The F5 PNG prints the engine's numbers, and a test holds it." It prints them today; no test holds it (FA2-B1).
- "The figures are a pure function of `run.json`." A `matplotlibrc` in the working directory changes them (FA2-S8).
- "The line-break rewrite is unreachable through the CLI." It is reachable through `justification` (FA2-S5).
- "No customer string can break the DOCX render." `$\foo$` in a CSV level does (FA2-N1).
- "The DOCX tables are the HTML tables." Their values are equal; their structure is not (FA2-N3).
- "CI has run the ap4 tests." It has not; the branch is unpushed.

## For the repair

1. FA2-B1: a test that reads F5 `ax.texts` and the legend texts against the SVG, plus mutants A and I in `AP4_MUTANTS`. This blocks PASS.
2. FA2-S1/S2: rewrite the two sentences to cite run `36020197050`, and change the `test_ap4_sentences.py` pins.
3. FA2-S3/S4/S5/S6/S7: rewrite each to name what was measured, on which tree.
4. FA2-S8 and FA2-N1: draw inside `rc_context(rcParamsDefault)` and turn mathtext off for customer strings, with tests run from a directory holding a hostile `matplotlibrc` and with a `$\foo$` level.

None of these touches a statistical gate.
