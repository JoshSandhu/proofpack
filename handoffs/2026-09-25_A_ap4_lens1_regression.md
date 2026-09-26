# A-P4 lens 1 (regression and record) at `4879ac5` - build day 10, lane A

This round ran on Saturday 26 September 2026 (day 10 continued; the file keeps its
2026-09-25 name). Cold lens, no prior context. Every figure below was measured in this
session on win-amd64-cp314 (Windows 11, CPython 3.14.6, docxtpl 0.20.2, python-docx 1.2.0,
matplotlib 3.11.2 from the pip user site), in detached worktrees at `4879ac5` and `81f1102`
under the scratchpad, with `PYTHONPATH=<worktree>/src` forced and proved
(`proofpack.__file__` printed inside each worktree before any figure was trusted). Both
worktrees were removed after the note was written.

**Verdict: PASS, no blocker.** The note `AP4_build.md` at `4879ac5` is true where it is
measurable here: the full suite, the five marker counts, ruff, doctor, the template
regeneration, the unlicensed CLI run and the mutation sweep re-measure to the note's
figures (one environment skip aside); every new test file fails at `81f1102`; no test was
deleted, no xfail was added, no marker removed; the lock diff adds nine packages and
moves nothing; the diff under `src/proofpack/stats/`, `gates.py` and `criteria.py` is
empty. Eleven non-blocking findings follow, four of them sentence violations. Read them,
not the flag.

## Blockers

None.

## Non-blocking findings

| Id | What was measured | Repro (Git Bash, `PYTHONPATH` forced) |
|---|---|---|
| RG1-N1 (sentence) | `tests/ap4_docx.py` (module docstring) and `.github/workflows/ci.yml` (the `docx-extra` comment) say the CI job "installs the extra and sets that variable, so the skip cannot hide there; the main pytest job runs without the extra and the same tests skip with a named reason". Neither job has run (the comment itself says so). The mechanism holds locally: with the three modules hidden (`sys.modules[...] = None` through a `-p` plugin) `-m ap4` gives `29 passed, 101 skipped` without the variable and `23 failed, 47 passed, 60 errors` with `PROOFPACK_REQUIRE_DOCX=1`. The sentence about what the two CI jobs do is the same class as lens 2 FA N3/N4, which this branch's first commit closed. Note line 78 ("the docx job cannot") is the same sentence. | `grep -n "cannot hide" tests/ap4_docx.py .github/workflows/ci.yml` |
| RG1-N2 (sentence: citation) | `src/proofpack/render/docx.py` line 55 cites `tests/test_ap4_roundtrip.py::test_two_renders_of_one_document_are_byte_identical`. That test id lives in `tests/test_ap4_determinism.py`; `test_ap4_roundtrip.py` has no such test. | `git grep -n test_two_renders_of_one_document_are_byte_identical 4879ac5` |
| RG1-N3 (note accuracy) | The note names the seventh A-P3 sentence violation as FA3-S2. The binding list (`handoffs/2026-09-24_A_ci.md`, "Tomorrow needs" and "What did not land") is lens 2 FA N3, N4, N5, N6, FA3-S1, RG3-S1, FA3-S3: the note-only seventh is lens 2 FA N6, not FA3-S2 (a first-round item the same handoff lists separately). The six in shipped files are closed: the twelve `tests/test_ap4_sentences.py` cases and `test_fa3_s1_...` all fail at `81f1102` (`13 failed` with `test_sweep_ap4.py`) and pass at `4879ac5`. | `sed -n '53,64p' handoffs/2026-09-24_A_ci.md` |
| RG1-N4 (note accuracy) | Per-file test counts differ from the note in three files: `test_ap4_extra.py` 16 collected (note 17), `test_ap4_determinism.py` 8 (note 7), `test_ap4_styles.py` 15 (note 14). The ids (13 / 4 / 5) and the ap4 total (130, and `-m day10` = 130) match. | `python -m pytest --collect-only -q tests/test_ap4_extra.py \| grep -c ::` |
| RG1-N5 (merge notes) | `git merge-tree --write-tree 6c4e253 4879ac5` (names only; no E10 content read) conflicts in `src/proofpack/cli.py`, `src/proofpack/run.py` and `tests/test_offline.py`. The merge notes name all three as shared but do not say they conflict. Two files both sides changed are missing from the notes' shared list: `tests/test_ap3_r3_repair1.py` and `tests/test_ap3_repair2.py` (both auto-merge). The other auto-merged shared files (`pyproject.toml`, `scripts/mutation_sweep.py`, `tests/test_render_t8.py`) are named. | `git merge-tree --write-tree --name-only 6c4e253 4879ac5` |
| RG1-N6 (note omission) | The note has no "What tomorrow needs" section, does not name DEC-69's dates (days 11-14 = Mon 28 Sept - Thu 1 Oct) and does not record "T12 has no DOCX today", all three asked for by the task. Day 11 items it does name: T2.docx (item 9, decision 12, open question 3). | read `AP4_build.md` |
| RG1-N7 (carried, lane E, DEC-71 a) | The rendered `T1.docx` body carries one unqualified AI-DSF name, the tag line `T1 · FDA AI-DSF performance evidence attachment set` (the same context string as the HTML header DEC-71(a) assigns to lane E, day 11). All 39 paragraphs and cells naming the map's AI-DSF document carry `draft guidance (January 2025), not for implementation`; the header parts name no guidance. When lane E qualifies the HTML string the DOCX inherits it (one context); the day-11 note should say so. | `lens_inspect.py` (below): `any 'AI-DSF' text without qualifier in body: ['T1 · FDA AI-DSF ...']` |
| RG1-N8 (D4 section 2 coverage, record) | D4 section 2 names eighteen T1 tables (T1-1 to T1-18). The licensed f17 render prints eleven captions in both the HTML and the DOCX (T1-1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 18; T1-13 and T1-17 render when fairness and criteria are declared; the generator names both). T1-4 (overlap), T1-12 (intersectional), T1-14/15/16 (robustness) are in neither document at `81f1102` (the engine has no overlap, intersectional or robustness block). The round-trip's decimal scan reads every cell of every DOCX table (42 tables in `T1.docx`: 15 margin-note tables and the data tables), so it covers every table the DOCX has; it cannot cover tables the engine does not produce. Not an A-P4 defect; the note should record the gap. | `run_licensed_lens.py` (below) |
| RG1-N9 (DEC-72) | `test_a_built_wheel_carries_the_three_docx_templates_beside_the_html_ones` builds through `test_render_theme._build_wheel`, which runs `python -m uv build --wheel` without `--offline` (pre-existing route, first used by an ap4 test here). DEC-72 names `python -m uv build --wheel --offline` as the only wheel-build route from 26 September. Measured: the offline route builds `proofpack-0.1.0.dev1-py3-none-any.whl` (508,972 bytes) with the three `.docx` byte-equal to the committed files and `Provides-Extra: docx` plus the three `Requires-Dist ...; extra == 'docx'` lines. Whether the non-offline route opened a socket was not measured (uv is a native binary). | `python -m uv build --wheel --offline --out-dir DIR` |
| RG1-N10 (environment) | Day-8 marker: `469 passed, 1 skipped` here against the note's `470 passed`; full suite `1716 passed, 2 skipped, 1 xfailed` against `1717 passed, 1 skipped, 1 xfailed`. The one extra skip is `tests/test_e8_repair4.py:405` (confusables file looked up relative to the worktree's parent; RG3-N6 recorded it for lens worktrees). Same 1,719 collected. | run the suite in a scratchpad worktree |
| RG1-N11 (sweep comment) | `scripts/mutation_sweep.py` (the `AP4_MUTANTS` comment) says that without the extra "every mutant would count as survived - the sweep's baseline check does not see a skip". Not measured by the builder or here (the sweep was run with the extra present only). Name what was measured or drop the sentence. | `grep -n "would count as survived" scripts/mutation_sweep.py` |

## What was re-measured (note figure -> this session)

| Command (in the `4879ac5` worktree) | Note | Git Bash | PowerShell 5.1 |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1717 passed, 1 skipped, 1 xfailed in 181.99s` | `1716 passed, 2 skipped, 1 xfailed in 183.33s` (RG1-N10) | not run (3 min) |
| `-m ap4` | `130 passed, 1589 deselected in 45.16s` / `42.95s` | `130 passed, 1589 deselected in 39.42s` | `130 passed, 1589 deselected in 36.10s` |
| `-m ap3` | `172 passed, 1547 deselected` | `172 passed, 1547 deselected in 24.97s` | - |
| `-m day9` | `331 passed, 1388 deselected` | `331 passed, 1388 deselected in 38.34s` | - |
| `-m day8` | `470 passed, 1249 deselected` | `469 passed, 1 skipped, 1249 deselected in 35.75s` (RG1-N10) | - |
| `-m day10` | `130 passed` | `130 passed, 1589 deselected in 32.43s` | - |
| `python -m ruff check .` / `ruff format --check .` | `All checks passed!` / `245 files already formatted` | the same | the same |
| `python -m proofpack.cli doctor --offline` | `[ok  ] docx extra  docxtpl 0.20.2, python-docx 1.2.0, matplotlib 3.11.2` | the same, `All essential checks passed.` | the same |
| `python scripts/make_docx_templates.py --out DIR` | three files, part-equal | `T1.docx` 52,840 / `T7.docx` 40,587 / `T8.docx` 42,510 bytes, SHA-256 prefixes `259f6c1ebbf38bc2` / `d6ab2c521a1b6c3c` / `0aef69d154576ed6`, **byte-equal** to the committed files (not only part-equal) | the same three hashes |
| `python scripts/mutation_sweep.py --marker ap4` (`PROOFPACK_REQUIRE_DOCX=1`) | `13 planted, 13 killed, 0 survived; 373 s` | `13 planted, 13 killed, 0 survived; 329 s` (all thirteen listed ids killed; the baseline copy passed `-m ap4` first) | - |
| `python -m uv lock --check --offline` | (not in the note) | `Resolved 72 packages`, exit 0 | - |
| the unlicensed run (`f17_determinism.py --n 400 --inputs-only`, `PROOFPACK_HOME` empty, `--format json,html,docx --templates T1,T7,T8 --offline`) | exit 4; `ingest_report.json` 649, `pseudonyms.json` 370, `run.json` 236,797; the Next-step line naming the six files | the same lines, exit 4, the same three sizes | the same lines, exit 4, the same three sizes |
| the licensed run (`conftest.write_licence`, `ephemeral_registry()`, the same inputs) | exit 0 in 1.9 s; `run.json` 236,806, `T1.docx` 680,574, `T1.html` 141,950, `T7.docx` 50,437, `T7.html` 47,196, `T8.docx` 46,151, `T8.html` 34,456 | exit 0 in 1.9 s; 236,806 / 680,574 / 141,950 / **50,440** / 47,196 / **46,155** / 34,456 (T7/T8 DOCX sizes move by a few bytes with the run's `started` and run id, which the footer and core properties carry) | - |

The uv.lock diff (`git diff 81f1102 4879ac5 -- uv.lock`): one `-` line (`provides-extras = ["stats"]`), nine new `[[package]]` entries - contourpy 1.4.0, cycler 0.12.1, docxtpl 0.20.2, fonttools 4.66.0, kiwisolver 1.5.1, lxml 6.1.3, matplotlib 3.11.2, pillow 12.3.0, python-docx 1.2.0 - and the project's `docx = [...]` block. numpy, scipy, statsmodels and scikit-learn are untouched. Licences read from the installed metadata: docxtpl LGPL-2.1-only, python-docx MIT, matplotlib its own PSF-based licence, contourpy BSD-3-Clause, cycler BSD (the file text), fonttools MIT, kiwisolver BSD (the file text), lxml BSD-3-Clause, pillow MIT-CMU - as the note's table has them.

## Fails pre-build (new tests copied into the `81f1102` worktree)

- `tests/test_ap4_sentences.py` + `tests/test_sweep_ap4.py`: `13 failed` (every case; the phrases are present / the corrected ones absent / no ap4 mutants / FA3-S1's four forms pass `offline_violations`).
- `test_ap4_cli.py`, `_determinism.py`, `_docx.py`, `_extra.py`, `_figures.py`, `_roundtrip.py`, `_styles.py`, `_templates.py`: each `1 error during collection`, `ModuleNotFoundError: No module named 'proofpack.render.docx'`.
- Modified files, new versions at `81f1102`: `test_sbom.py` 2 failed (71 vs 62; the nine scopes), `test_workflows.py::test_the_counts_of_engine_lines_are_the_ones_written` failed (ci 6 vs 5), `test_offline.py::test_run_offline_with_format_docx_opens_no_socket` failed; `test_render_furniture.py`, `test_render_t8.py` (`pdf` token) and `test_render_t1.py` (`LISTED_CELLS`) pass at both shas - adjustments, not pins, as expected.

## Nothing weakened

`git diff --name-status 81f1102 4879ac5 -- tests/` has no `D` line. Added skips: only the declared `needs_extra` skipif and the same named `pytest.skip(SKIP_REASON)` in `test_offline.py`; no `xfail`, no `.only`, no `pytest.mark` line removed. Three tests renamed (item 0). `git diff --name-status 81f1102 4879ac5 -- src/proofpack/stats/ src/proofpack/gates.py src/proofpack/criteria.py` is empty. `ap4` is declared in `pyproject.toml` and `ci.yml`'s `docx-extra` job runs `uv sync --all-groups --locked --extra docx` then `pytest -q -p no:cacheprovider -m ap4` under `PROOFPACK_REQUIRE_DOCX: "1"`; its grep string `T1.docx, T7.html, T7.docx, T8.html, T8.docx` is a substring of the Next-step line measured above.

## What I could not break (what I tried)

- **Byte identity for one `run.json`.** `render_docx_bytes` twice from `lic_pack1/run.json` in Git Bash and again in PowerShell: T1 (680,574 bytes, 45 parts, 11 media), T7 (50,440), T8 (46,155) identical to each other and to the files the CLI wrote, SHA-256 prefixes `1ddb15e510a4fb17` / `aad89d962b2fa4a8` / `d0589eac9c7f6b18` in both shells. Two separate *runs* differ (run id, `started`) - that is the claim's stated scope, not a counter-example.
- **The exit-7 path.** With `docx`, `docxtpl` and `matplotlib` set to `None` in `sys.modules`, `main(["run", ..., "--format", "json,html,docx", "--offline"])` printed the one `error: --format docx needs the [docx] extra ...; nothing was written` line, returned 7, and the `--out` directory does not exist.
- **Import hygiene.** In a fresh process: `import proofpack, proofpack.render.html, proofpack.render.docx, proofpack.render.figures, proofpack.run, proofpack.cli` leaves no module of `docx`, `docxtpl`, `matplotlib`, `PIL` or `lxml` in `sys.modules`.
- **Furniture in the rendered files.** T1 9 sections / T7 3 / T8 3, each footer part starting with the short disclaimer and carrying the draft label; no watermark under the valid licence; `[unverified]` 18 in `T7.docx` = 18 in `T7.html`; `n.e.` 6 times and 44 tier glyphs in `T1.docx`; every one of the 23 D5 section 3.5 style names present, `PP Body` colour `16202B` = `tokens.json` ink `#16202b`.
- **Templates.** Regenerated in both shells: byte-equal to the committed files.

## What I could not check

- The CI jobs (`docx-extra`, the main `test` job's skips) on GitHub Actions: the branch has not been pushed. RG1-N1 stands until a run shows the skip lines and the extra job's counts.
- Whether `uv build --wheel` (the test's route) opens a socket (RG1-N9).
- The DOCX in Word (field codes, page breaks, landscape section): no Word was driven; Josh's review hour.
- Byte identity on another platform (not claimed by the note).
- E10's content on main: only path names were read (`git diff --name-only`, `git merge-tree --name-only`), per the task.

## Scripts used (scratchpad, removed with the worktrees)

`run_licensed_lens.py` (two licensed CLI runs, sizes, table/section/footer counts, mark counts), `render_twice.py` (byte identity from one `run.json`), `lens_inspect.py` (licences, styles, header line, AI-DSF qualifier scan), `hide/hide_docx.py` (the `-p` plugin hiding the extra).
