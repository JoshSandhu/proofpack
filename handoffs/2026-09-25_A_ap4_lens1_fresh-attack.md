# A-P4 lens 1, fresh attack: build day 10, lane A at `4879ac5` (branch `a-p4-docx`)

**Verdict: PASS.** No blocker. Every number I traced from `run.json` into the DOCX prints as the HTML prints it; every section of every rendered DOCX carries its own footer part with the short disclaimer, the watermark slot and the PAGE / NUMPAGES fields; no Jinja tag or XML string I fed through a customer slot reached `document.xml` as anything but text; 1,025 figure coordinates agree with the SVG to 2.2e-16; the lock moved no oracle library; the HTML path imports none of the extra. Three sentence violations in shipped text (FA-S1..S3, small), one in the builder's note, and nine record-and-carry findings follow.

This round ran on **Saturday 26 September 2026** (the file keeps the day-10 date). Written by a cold fresh-attack lens session. I committed nothing, pushed nothing, installed nothing and made no tag. Every figure below was measured in this session on Windows 11, `win-amd64-cp314` (Python 3.14.6, numpy 2.5.3, scipy 1.18.1, docxtpl 0.20.2, python-docx 1.2.0, matplotlib 3.11.2 from the pip user site), in Git Bash. I worked in two detached worktrees under `scratchpad/lens-AP4-r1-fresh-attack/`: `eng-4879ac5` (suite, markers, lint, sweep, every probe) and `eng-81f1102` (the branch's tests copied in, then the worktree removed). `PYTHONPATH` was forced to each worktree's `src`; `python -c "import proofpack;print(proofpack.__file__)"` printed `...\eng-4879ac5\src\proofpack\__init__.py` and `...\eng-81f1102\src\proofpack\__init__.py` respectively before any number was read. Every `proofpack run` carried `--offline`. Both worktrees are removed. Read-only in `wt-ap4` and the main tree; the only file I created outside my worktrees is this note.

## Suite, markers, lint, sweep (eng-4879ac5, `PYTHONPATH` forced, `PYTHONUTF8=1`, `PROOFPACK_REQUIRE_DOCX=1`)

| command | result |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1716 passed, 2 skipped, 1 xfailed in 185.43s` (the builder's `1717 passed, 1 skipped`: the second skip here is `test_e8_repair4.py:405`, the confusables file resolved relative to my scratch path; environmental) |
| `--collect-only -m ap4` / `-m day10` | `130/1719` each |
| `-m ap3` / `-m ap2` | `172/1719` / `90/1719` |
| `-m day9` / `-m day8` / `-m day7` / `-m day6` / `-m day5` | `331` / `470` / `139` / `285` / `54` of 1719 |
| `python -m ruff check .` / `ruff format --check .` | `All checks passed!` / `245 files already formatted` |
| `python scripts/mutation_sweep.py --marker ap4` | `13 planted, 13 killed, 0 survived; 374 s` |
| `python scripts/make_docx_templates.py --out <scratch>/regen` | `T1.docx 52840`, `T7.docx 40587`, `T8.docx 42510` bytes; `cmp` against the committed files: byte-identical, all three |

The branch's tests at `81f1102` (copied into `eng-81f1102`): the eight files that import `proofpack.render.docx` error at collection (the module does not exist there); of the rest, every new test fails there: `test_ap4_sentences.py` (13 failed), `test_offline.py::test_run_offline_with_format_docx_opens_no_socket`, `test_workflows.py::test_the_counts_of_engine_lines_are_the_ones_written`, `test_sweep_ap4.py::test_the_ap4_list_has_at_least_eight_mutants...`. No new test passes at `81f1102`. The five FA3-S1 lines (`--out=--offline`, `OPT=--offline ...`, `>--offline.log`, `> --offline.log`, `& echo --offline`) each gave `0` violations from `81f1102`'s `offline_violations` and `1` from the branch's.

## Blockers

None.

## Sentence violations (shipped text; to be fixed, non-blocking)

### FA-S1. `src/proofpack/render/docx.py` lines 54-55 cite a test that is in another file

Verbatim: "``tests/test_ap4_roundtrip.py:: test_two_renders_of_one_document_are_byte_identical``". `grep -n "def test_two_renders" tests/test_ap4_*.py` finds it once, in `tests/test_ap4_determinism.py:45`. `tests/test_ap4_roundtrip.py` has no test of that name. Repro: `grep -c test_two_renders_of_one_document_are_byte_identical tests/test_ap4_roundtrip.py` prints `0`.

### FA-S2. `src/proofpack/render/figures_png.py` lines 26-27 cite a truncated test id

Verbatim: "``tests/test_ap4_figures.py ::test_png_bytes_are_identical_across_two_renders``". The test is `test_png_bytes_are_identical_across_two_renders_and_carry_no_metadata` (`tests/test_ap4_figures.py:308`); no test of the shorter name exists. Repro: `grep -n "def test_png_bytes" tests/test_ap4_figures.py`.

### FA-S3. `src/proofpack/render/docx.py` lines 40-41: "a customer string is written as it is" - not for every string

Counter-examples constructed and run through `render_docx_bytes` with the string planted in `declarations.model.name`, `criteria[0].justification`, `criteria[0].author`, `reference_standard.description`, `operating_points[0].source`, `prevalence[0].label`, `subgroups[0].source` and `subgroups[0].level` (T1, T7, T8):

| planted | in the DOCX text (python-docx) | why |
|---|---|---|
| `{_{ 7*7 }_}` | `{{ 7*7 }}` | docxtpl rewrites `{_{`/`}_}`/`{_%`/`%_}` after rendering (`template.py::render_xml_part`); not evaluated, but not "as it is" |
| `a\r\nb` | `a` + break + `b`, the `\r` gone | docxtpl turns `\n` into `<w:br/>`; the XML parser normalises `\r` |
| `a\tb` | `a\tb` (round-trips) | `<w:tab/>`, read back as a tab |

The `{_{` case is reachable through `criteria.yaml` (`model.name: "m{_{ 7*7 }_}n"` ran to exit 0 with six documents; the DOCX prints `m{{ 7*7 }}n`, the HTML prints the string as written). The sentence should name the two rewrites, or the renderer should escape them. Record-and-carry.

### FA-S4 (the note, not shipped). AP4_build.md, item 6: T7's `[unverified]` markings are "in `PP Unverified`"

20 of the 21 `[unverified]` runs of the synthetic T7 are in `PP Unverified`; one is a plain `PP Body` run: the conventions paragraph beginning "Fairness is measured, never mitigated. Gaps against the reference level are..." (from `conventions_T7.md` through `markdown_blocks`, one run per paragraph). The test `test_unverified_markings_survive_extraction_in_the_html_count` asserts only `any(t == "[unverified]" and r == "PP Unverified" ...)`, so the test is right and the note's sentence overstates. Counts match (21 = 21) and the marking survives as text. Record-and-carry.

## Record-and-carry findings

### FA-R1. U+FFFE / U+FFFF in a declaration string crash the DOCX render after `run.json` and `T1.html` are written

`declare.py`'s H08 rejects `[\x00-\x1f\x7f-\x9f]` only. `criteria.yaml` with `model: {name: "m￾n"}` (PyYAML writes it as an escape), `run --format json,html,docx --templates T1,T7,T8 --offline` under a valid ephemeral licence: exit 5, stderr `internal error: XMLSyntaxError: Char 0xFFFE out of allowed range, line 1, column 1317 (<string>, line 1)`, files written `T1.html, ingest_report.json, pseudonyms.json, run.json` - no `.docx`, no `T7.html`, no `T8.html`. The same string renders through the HTML path. U+FFFF behaves the same. A typed line, not a traceback, but a half-written pack; H08 could reject the XML-1.0 non-characters (U+FFFE, U+FFFF) the way it rejects the C0/C1 range. Repro (Python API): `d["declarations"]["model"]["name"] = "m￾n"; render_docx_bytes(d, "T8")`.

### FA-R2. Form feed and BEL in a customer string are XML injected by docxtpl - not reachable through the CLI

Through `render_docx_bytes` directly, with `"a\fb"` in the slots of FA-S3: `word/document.xml` gains 11 `<w:br w:type="page"/>` elements and 22 paragraphs in T1 (6 / 12 in T8) - docxtpl's `resolve_listing` turns `\f` into a page break and `\a` (BEL) into a paragraph break (11 new `<w:p>` in T1), and the string does not round-trip. Through the CLI this is unreachable: `criteria.yaml` with `\f`, `\a` or `\x00` in `model.name` halts `HALT H08: declaration invalid at model/name: control character U+000C; remove it` (exit 3, nothing written), `mapping.py` rejects the same range, and `schema.py` has `_CONTROL_CELL` for table cells (see "could not check" for the cell path). Recorded so the next hand that adds a string source to the document knows the renderer relies on ingest for this.

### FA-R3. A missing dependency of the extra (not one of the three) is an exit-5 internal error after `run.json` and `T8.html`

`require_extra` asks `find_spec` for `docx`, `docxtpl`, `matplotlib` only. In a child process with a meta-path finder hiding one module: `lxml` hidden -> `exit= 5`, `internal error: ImportError: blocked lxml`, files `T8.html, ingest_report.json, pseudonyms.json, run.json`; `docx.shared` hidden -> the same with `blocked docx.shared`; `docxtpl.richtext` hidden -> the same. `matplotlib` hidden entirely -> exit 7, the typed EXTRA_LINE, no out directory (correct). `PIL` and `matplotlib.backends.backend_agg` hidden -> exit 0 with T8.docx (matplotlib had already loaded them under other names). The `cli.py` comment "a missing package is one typed line (exit 7) and never a traceback after run.json was written" holds for the three; a broken install of their closure gives exit 5 after `run.json`.

### FA-R4. My mutant `f5_rows_flipped` survives all 130 ap4 tests

`src/proofpack/render/figures_png.py`: `ax.set_ylim(n_rows - 0.5, -0.5)` -> `ax.set_ylim(-0.5, n_rows - 0.5)` (the first row at the bottom, the reverse of the SVG and of every table). `pytest -x -m ap4` in a copy with `PYTHONPATH` forced to the copy: `130 passed`. The parity test reads x from the artists; nothing asserts the vertical order of F5 rows in the PNG. My other seven mutants: `f4_strip_align_center` killed (`test_f4_deciles_intervals_and_strip_equal_the_svg_through_both_maps`), `header_customer_style_dropped` killed (`test_every_section_has_its_own_footer_with_the_slots_and_a_page_field[T1]`), `status_style_dropped` killed (`test_no_forbidden_word_outside_customer_text_and_status_words_only_in_pp_status[T1]`), `t8_yaml_echo_swapped` (prints `mapping_sha256` where the YAML echo goes) killed (`test_the_licence_states_and_which_files_exist[ok-...]`), `core_created_now` killed (`test_two_renders_of_one_document_are_byte_identical[T1]`), `compresslevel_9` survived (equivalent for every claim made: nothing asserts the compression level), `watermark_guard_dropped` not run (my edit broke the generator's indentation).

### FA-R5. The wheel grows by 127,710 bytes for the browser too

`python -m uv build --offline --wheel` from each worktree: `81f1102` -> `proofpack-0.1.0.dev1-py3-none-any.whl` 381,262 bytes, 80 entries; `4879ac5` -> 508,972 bytes, 85 entries. The five new entries are `proofpack/templates/T1.docx` (52,840), `T7.docx` (40,587), `T8.docx` (42,510) - each byte-equal to the committed file - and `render/docx.py`, `render/figures_png.py`. `METADATA` carries `Provides-Extra: docx` with the three `Requires-Dist ...; extra == 'docx'` lines. The Pyodide demo loads the whole wheel, so every visitor would fetch the three templates the browser never renders. The site pins `81f1102` today (DEC-43), so the wheel the demo loads is unaffected until the pin moves; when it moves, either accept +33% on the wheel or exclude `templates/*.docx` from the browser build. How the extra is excluded from the Pyodide path: its three packages are never `Requires-Dist` without the marker and are imported only inside `render/docx.py` and `render/figures_png.py`; a subprocess `import proofpack, proofpack.render.html, proofpack.render.figures, proofpack.run, proofpack.cli, proofpack.render.docx` plus `render_t8` and `render_t1` left `sys.modules` with none of `docx`, `docxtpl`, `matplotlib`, `PIL`, `lxml`, `fontTools`, `kiwisolver`, `cycler`, `contourpy`, `pyparsing` (`{"hits": [], "n_modules": 1155}`).

### FA-R6. `PP Mono` and `PP Unverified` name "Cascadia Mono", not a Word default

`word/styles.xml` of `T1.docx`: `<w:rFonts w:ascii="Cascadia Mono" w:hAnsi="Cascadia Mono"/>` on the two mono styles; every other PP style inherits the theme's `minorHAnsi` (Calibri) - Word's default. `_mono_face()` takes the first concrete family of `tokens.json` `type.mono` (`ui-monospace, "Cascadia Mono", Consolas, Menlo, monospace`). Cascadia Mono ships with Windows 11 and Windows Terminal, not with Word; Word on a machine without it substitutes. D4 section 9 says "Fonts: Word defaults". Consolas (next in the stack) or Courier New would be a Word default. No number depends on this.

### FA-R7. Stale python-docx defaults in the package properties

Rendered `T1.docx`, `docProps/app.xml`: `<Template>Normal.dotm</Template>`, `<Application>Microsoft Macintosh Word</Application>` (python-docx's default template); `docProps/core.xml`: `<dc:description>generated by python-docx</dc:description>`. The renderer sets title, creator, lastModifiedBy, revision, created and modified (all measured as the manifest's `started`, `2026-09-26T12:44:47Z`, for the CLI run below) but not description or the app part. A reviewer opening File > Properties reads "Microsoft Macintosh Word". Cosmetic; deterministic.

### FA-R8. The zip stamp is two seconds coarser than `manifest.started`

`manifest.started = 2026-09-26T12:44:47Z`; every zip entry's mtime `(2026, 9, 26, 12, 44, 46)`; `core.xml` created/modified `2026-09-26T12:44:47Z`. The docstring says so ("to the zip format's two-second resolution"). Recorded only so nobody reads the one-second gap as a determinism defect.

### FA-R9. The T7 conventions pipe table is a monospace block, the HTML a `<table>`

37 of T7's 104 HTML table cells are not a DOCX cell or paragraph; all 37 are substrings of the mono block (`markdown_blocks`). The builder's note says so. Recorded because a Word reader cannot sort or select the column; the numbers are the same tokens (see parity below).

## What I could not break (what I tried)

- **Numbers.** On one licensed CLI run (`pack_a_base`: `run --format json,html,docx --templates T1,T7,T8 --offline`, exit 0, `T1.docx` 680,584 / `T7.docx` 50,441 / `T8.docx` 46,154 bytes): every one of T1's 510 HTML `<td>/<th>` texts is a DOCX cell or paragraph (0 missing); T8's 130 likewise (0 missing); T7 as FA-R9. Thirty-five cells traced from `run.json` by my own re-implementation of D4 section 1.2 (`format(x*100,".1f")`, `".3f"`, U+2212, `+`, `k/n (xx.x%) [lo, hi]`, tier glyphs): 21 whole-cell strings found in both documents, e.g. `96/128 (75.0%) [66.8, 81.7]`, `0.835 [0.795, 0.876]`, `−0.749 [−1.005, −0.493]`, `9/40 (22.5%) [12.3, 37.5]ᶜ`, `+4.8 [−5.4, +14.8]`, `−0.021 [−0.129, +0.088]`, `n.e. (analytic_ci_unavailable)`; the overall-table facets (`96/162` / `59.3` / `[51.6, 66.5]` / `wilson` for PPV; `3.091` / `2.450, 3.900` for LR+; and so on for NPV, accuracy, LR-, DOR, Youden, balanced accuracy) equal in the DOCX row and the HTML `data-facet` cells. A planted `suppressed: true` prints `‡` with no digit of `est` or `n`; a planted `not_estimable_reason: planted_reason` with `est = 0.123456` prints `n.e. (planted_reason)` and no `12.3%`.
- **Footers and watermark.** 15 files (T1/T7/T8 x valid, synthetic, trial, no licence, expired): `sectPr` 9/3/3 = footer parts 9/3/3 = header parts 9/3/3; every `sectPr` has exactly one `footerReference w:type="default"` and one `headerReference`, no `titlePg`, no `evenAndOddHeaders`; every `footerN.xml` carries the D4 section 7.1 short disclaimer (1,290 characters, equal to the HTML's `<footer>` text), ` PAGE ` and ` NUMPAGES ` `instrText`, and in the four marked states the watermark paragraph (`TRIAL - not for submission`, `SYNTHETIC DATA - not for submission`, `NO LICENCE - not for submission`, `LICENCE EXPIRED - not for submission`) in `PP Watermark`; none in the valid state (2 paragraphs) versus 3 in the marked states. The CLI grace run (`expires` 5 days ago): exit 0, six documents, `LICENCE EXPIRED - not for submission` in all three T7 footers.
- **Markings.** Body counts HTML = DOCX: T1 `[unverified]` 1 = 1, `ᵃ` 1, `ᵇ` 11, `ᶜ` 42, `n.e. (` 6; T7 `[unverified]` 21 = 21, `citation pending verification` 21 = 21. T1's `[unverified]` run is `PP Unverified`. The one label-count difference (T1 51 vs 50, T7 4 vs 3, "draft guidance (January 2025), not for implementation") is the HTML body's own copy of the footer text; the DOCX carries it in every footer part instead. Every DOCX paragraph or footer that names an AI-DSF anchor id carries the qualifier (the two "without" hits were the long-form scope item 5, which states it in D4's words, and the PCCP guidance's own title).
- **Injection.** `{{ 7*7 }}`, `{% raw %}X{% endraw %}`, `{%p if 1 %}Y{%p endif %}`, `<w:p><w:r><w:t>INJECT</w:t></w:r></w:p>`, `</w:t></w:r></w:p>`, `&lt;w:br/&gt;`, `&amp;lt;`, `]]><![CDATA[`, U+202E, U+2028, U+2029, U+FEFF, an emoji, `'"&<>` and a 10,000-character string in the eight slots of FA-S3: every part of every zip parses, paragraph / page-break / tab counts equal the baseline, no `<w:p><w:r><w:t>INJECT`, `{{ 7*7 }}`, `{% raw %}` or `{%p if 1 %}` outside text nodes, and each string round-trips through python-docx (the U+202E and U+2028 cases too). `{{ 7*7 }}` is text, never `49`.
- **Forbidden words.** `test_render_t8.FORBIDDEN_ON_PAGE` over every run outside the three manufacturer styles, plus headers and footers, in all 15 files: 0 hits; `PP Status` runs are exactly `{'criterion met', 'criterion not met', 'not assessable'}`; 0 runs outside `PP Status` carry `met` / `assessable`.
- **Figures.** SVG points parsed from the T1 HTML and put through the inverse of each figure's `data-map`, against `Line2D.get_xydata()` and the histogram `Rectangle` patches: F2 401 series vertices + 2 reference + 1 operating point; F4 10 deciles, 10 intervals, 10 strip bars (left, width, top, bottom through the strip's own map); all nine F5 figures: every estimate x, interval x pair, row order (SVG `cy` -> `(cy-20)/26-0.5` = matplotlib y), reference x, y-tick labels = SVG row labels, value texts = SVG value texts. 1,025 coordinates, worst `|d| = 2.22e-16`. No filled patch outside the strip, no collection, every legend frame off; F2 legend `['chance (dashed)', 'ROC curve (solid); AUROC 0.835 [0.795, 0.876]']`; F4 `['identity (dashed)', 'deciles (points, solid bars); slope 1.349 [1.056, 1.642]; intercept −0.749 [−1.005, −0.493]']`. F2 PNG identical across two renders (93,623 bytes), chunks `IHDR, pHYs, IDAT, IDAT, IEND` - no `tEXt`/`iTXt`/`zTXt`/`tIME`; IHDR 1889 x 1196, 8-bit RGBA. `calibration: null` -> no F4 figure; `score.type = logit` with `calibration` kept -> both drawers still draw (the engine, not the renderer, nulls calibration). No criteria -> 0 criterion artists; a planted `ci_lower_bound` criterion on `sex` at 0.65 -> SVG x `0.65`, PNG x `0.65`, `(0, (10, 4))` dashes; the same rows as `point_estimate` -> 0 lines in both.
- **Styles.** Every `w:color` / `w:fill` literal in every `PP` style of `T1.docx` is a `tokens.json` colour (0 unknown). The header's customer run is `PPManufacturerTextInline`, the engine part unstyled.
- **Determinism.** From one `run.json`, T1/T7/T8 rendered in two separate processes: byte-identical (sha256 `0b356447...`, `70e4bed3...`, `ac2c17f8...`), and byte-identical with the file the CLI wrote in a third process. All 45 entries one mtime, `compress_type` 8, one `external_attr`. Two CLI runs on the same inputs differ (run_id and `started` differ), as they must.
- **The extra and the lock.** `uv.lock`: exactly nine `[[package]]` entries added (contourpy 1.4.0, cycler 0.12.1, docxtpl 0.20.2, fonttools 4.66.0, kiwisolver 1.5.1, lxml 6.1.3, matplotlib 3.11.2, pillow 12.3.0, python-docx 1.2.0), one line changed (`provides-extras`); numpy 2.5.3, scipy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.0 unmoved at both shas (63 -> 72 packages). With `find_spec` returning None for the three and imports blocked: `-m ap4` on two files skips 25 with the named reason; under `PROOFPACK_REQUIRE_DOCX=1` the same run gives `8 failed, 2 passed, 15 errors` - the skip is refused.
- **Wiring.** `--templates T12 --format json,html,docx` and `--templates T1,T12 --format docx`: exit 5, `error: unknown --templates id 'T12'; choose from T1, T7, T8`, no out directory. `--format docx,pdf`: exit 5, `error: unknown --format token 'pdf'; choose from json, html, docx`. `--format DOCX` and `json, docx` accepted. No licence, `--format docx`: exit 4, `run.json` only, `DOCX not written: licence refused (no_file); run.json only (D1 section 7: after grace, JSON only)`, `Next step: proofpack licence install FILE, then run again for T8.docx (docs: /docs/run)`; with `json,html,docx` and three templates the line names all six files; expired past grace: exit 4, `HTML and DOCX not written: licence expired (expired_past_grace)`. `socket.socket`, `getaddrinfo` and `create_connection` replaced by a raiser during a full T1/T7/T8 `json,html,docx --offline` run: exit 0, six documents. `--format html,docx` still writes `run.json`; `--format docx --templates T1` writes `T1.docx` alone.

## Sentences I refused to write

- "The DOCX is safe against injected customer text." docxtpl rewrites four two-character sequences and turns `\f` / `\a` into page and paragraph breaks (FA-S3, FA-R2); the CLI's ingest is what keeps the latter out.
- "Every string the DOCX prints is checked by H08." U+FFFE is not (FA-R1).
- "The ap4 tests would catch a wrong F5 row order in the PNG." My mutant survived (FA-R4).
- "The wheel the demo loads is unchanged." It is unchanged only while the site pins `81f1102` (FA-R5).
- "The DOCX opens and paginates in Word." No Word was driven; the fields carry the cached `1`.
- "The CSV cell path rejects U+FFFE." Not measured (below).

## What I could not check

- **Word.** No copy of Word was driven; `Page 1 of 1` is the cached field value until Word recalculates; the Cascadia Mono substitution (FA-R6) is inferred from the font table, not seen.
- **The CSV level-cell path for U+FFFE and `\f`.** A modified table needs an interactive mapping confirmation (`map --yes` on the edited CSV: `HALT H07: non-interactive mode requires every role at high confidence ...`, with and without the prior `mapping.json` copied in), so the DOCX was never reached from a CSV cell in this session; `schema.py::_CONTROL_CELL` covers `\f`, nothing covers U+FFFE.
- **The `docx-extra` CI job.** The branch has not reached CI; I read the job, ran its `pytest -m ap4` and its smoke run's assertions by hand (exit 4, `run.json` only, the Next-step line names `T1.docx, T7.html, T7.docx, T8.html, T8.docx`), and did not run GitHub.
- **Byte identity across platforms.** One machine.
- **The `_add_rich` fallback** (`s.get("html", "")` when a sentence's claim id is absent from `claims`): I could not construct a document where a sentence exists without its claim, so whether the fallback would print a `Markup` unescaped is untested; it reads as dead code.
- **docxtpl's LGPL-2.1-only licence** for a public repository: a question for Josh, not a measurement.

## For the repair

FA-S1, FA-S2, FA-S3 are one-line edits (two test ids, one qualified sentence). FA-R1 is one regex widening in `declare.py` (and `mapping.py`, `schema.py`) with a test that feeds `"m￾n"` and asserts H08; FA-R4 is one assertion on `ax.get_ylim()` or the y of `estimate:j` against the SVG `cy`; FA-R6 is `_mono_face()` preferring a Word default; FA-R7 two property lines. None touches a statistical gate.
