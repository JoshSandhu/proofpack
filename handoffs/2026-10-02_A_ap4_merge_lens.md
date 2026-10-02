# A-P4 repair 3 and the A-P4/E10 merge: cold lens (2 October 2026)

**Verdict: FAIL. Three blockers.** Two of them come from the merge. Since the merge, `compare` accepts `--format docx` (the two sides now share `FORMATS`), but `cmd_compare` never runs A-P4's extra check (B1). The DOCX also drops E10's type note in the T1-11 cell (B2). The third is a false `Next step` line for `run --templates T2`. The HTML form of that line was already false on E10's side (`c779678`), and the merge carries it to `.docx` (B3). Repair 3 does what its commit says. The legend test kills every number mutant I planted, `$...$` strings no longer crash the PNG path through any of the four routes, and both sweeps kill every mutant. The suite, the markers, ruff and the lock pass in both shells. Read the blockers, not the counts.

Targets: `ec9699c` (A-P4 repair 3, branch `a-p4-docx`) and `a13931b` (its merge into `main`; parents `c779678` and `ec9699c`). Both are unpushed (`origin/main` = `c779678`). I used detached worktrees under `scratchpad/ap4-merge-lens/` at `a13931b`, `fd9488f`, `c779678` and `ec9699c`, plus `w-mut` (`a13931b`, my mutants, restored after each) and `w-fdt` (`fd9488f` with the repair-3 test copied in). Before the first figure in each worktree, `python -c "import proofpack;print(proofpack.__file__)"` printed a path inside that worktree. I set `PROOFPACK_REQUIRE_DOCX=1` throughout. Every CLI run was in-process through `proofpack.cli.main(..., registry=ephemeral_registry())` with `--offline`. `socket.socket`, `socket.create_connection` and `socket.getaddrinfo` were replaced by a raiser, and none of 120+ runs made a call. Platform: Windows 11, CPython 3.14.6, matplotlib 3.11.2, docxtpl 0.20.2, python-docx 1.2.0. I committed, pushed and downloaded nothing. This note is the only file I wrote outside the scratchpad.

## Blockers

### B1. `compare --format ...docx` without the `[docx]` extra writes `run.json` and the HTML, then exits 7 saying "nothing was written"

Since the merge, `compare` accepts `docx`, because `run.FORMATS` is shared. A-P4's pre-statistics check (`require_extra()`, exit 7 before `assemble_run`) sits in `cmd_run` only, and `cmd_compare` has no counterpart. With docx, docxtpl and matplotlib hidden (`sys.modules[...] = None` for `docx`, `docxtpl`, `matplotlib`, `lxml`, `PIL`), on the F5 pair under a valid licence:

```
=== h1 lic=ok cmd=compare --format json,html,docx --templates T2,T7
rc 7 socket calls 0
files ['T2.html', 'T7.html', 'compare_ingest_report.json', 'ingest_report.json', 'pseudonyms.json', 'run.json']
--- stderr
error: --format docx needs the [docx] extra (docxtpl, python-docx, matplotlib), which is not installed: pip install "proofpack[docx]" (docs: /docs/run); nothing was written
```

Six files are written, and the one printed line says nothing was. The statistics ran, the compare ledger counted the run, and the summary (`compare written: ...`, licence line, criteria counts) is never printed. The README's DOCX bullet ("without it `--format docx` exits 7 with one typed line and writes nothing") and `cli.py`'s exit-code docstring ("one typed line before any statistics run; nothing written") are both false for `compare`. At `c779678` the same command exits 5 with `unknown --format token 'docx'` before anything is written. At `ec9699c`, `compare` has no `--format`. So the merge introduced this. No test runs `compare` with `docx`: `grep` finds no test file with both. The `compare --format` help still reads "comma list of json, html".

Repro: `LENS_HIDE=1 python drive.py <wt> <work> h1 ok compare --format json,html,docx --templates T2,T7` (scratch driver; the same applies to any `main(["compare", ..., "--format", "json,html,docx", "--offline"])` with the three modules hidden and a usable licence).

Fix: run the same `require_extra()` check in `cmd_compare` before `assemble_compare`, with a test under the hidden-extra plugin. Or refuse `docx` for `compare` and say so in the help.

### B2. T1.docx drops E10's "(difference against the prior version)" from the T1-11 criterion cell, so the DOCX cell differs from the HTML cell

E10 added `type_note` to `render/t1.py` `subgroup_blocks` and printed it in `templates/T1.html`'s subgroup-difference table (`{{ c.status_word }}{{ c.type_note }}`). The merge's integration fix brought the criteria table's Type column and caption into the DOCX, but left this cell out. `scripts/make_docx_templates.py` line 1494-1496 still builds `{{ c.status_word }}` then `; max LB ...` with no `type_note`, and `grep -rn type_note` finds it only in `t1.py` and `T1.html`. On the synthetic cohort (`f17_determinism.py --n 400 --inputs-only`), I declared `Cpd` (sensitivity, `paired_difference_vs_prior`, op1, `sex = F`, ci_lower_bound >= -0.05) and `Cpt` (the same scope, a point bound 0.4). The licensed run, `--format json,html,docx --templates T1,T8`, gave exit 0:

```
HTML cell: Cpd (row 1) → not assessable (difference against the prior version); max LB — at n = —, attainable: —
DOCX cell: Cpd (row 1) → not assessable; max LB — at n = —, attainable: —
HTML phrase count: 1    DOCX phrase count: 0     ("(difference against the prior version)")
```

The cell exists so that a margin on the new-minus-prior difference is not read as a bound on the subgroup's own statistic (E9 row 121). The DOCX loses that in the one place the HTML prints it. No test caught it, because `test_ap4_roundtrip` compares the T8 criteria cells and the T7 tables, and its fixture has no paired subgroup criterion. Repro: `LENS_SYN=<syn3> python drive.py <wt> <work> s3 ok runsyn --format json,html,docx --templates T1,T8`, then search `word/document.xml` text for `difference against the prior version` (0) and `T1.html` (1, plus 1 in the criterion sentence both media carry).

Fix: add `{{ c.type_note }}` after the status run in `make_docx_templates.py`, regenerate T1.docx, and add a round-trip assertion on a document with a paired subgroup criterion.

### B3. `run --templates T2` with `docx` prints a `Next step` naming a file no command writes

```
=== r1 lic=ok  run --templates T2 --format docx            rc 0
  T2 not written: T2 is the version comparison report, written by proofpack compare (docs: /docs/compare)
Next step: run again with --format json,html for T2.docx (docs: /docs/run)
=== r2 lic=ok  run --templates T2 --format json,html,docx  rc 0
Next step: run again with --format json,html for T2.html, T2.docx (docs: /docs/run)
=== r3 lic=none run --templates T2 --format docx           rc 4
Next step: proofpack licence install FILE, then run again for T2.docx (docs: /docs/run)
```

`run` never writes T2. `--format json,html` writes no `.docx`. Neither `run` nor `compare` writes `T2.docx` (`DOCX_FILES` is T1, T7, T8; `compare --templates T2 --format docx` prints `T2.docx not written: template T2 is not built in this engine version`). The `T2 not written` note says T2 is "written by proofpack compare", which is true for the HTML only when only `docx` was asked. The HTML form is E10's own: at `c779678`, `run --templates T2` licensed prints `Next step: run again with --format json,html for T2.html`, also false, and unlicensed prints `then run again for T2.html`. That part predates the merge. The merge's `document_names()` extends it to `.docx`. Fix: drop T2 from the names in `cmd_run`'s Next-step lines, or give `run --templates T2` its own line pointing at `compare`, and test the printed line.

## Non-blocking

1. **The new legend test reads `get_text()`, not what is drawn.** Two mutants survive all 192 ap4 tests (excluding `test_sweep_ap4.py`): the F4 figure legend's texts set invisible (`[t.set_visible(False) for t in fig.legend(...).get_texts()]`) and the F2 axes legend hidden (`ax.legend(...).set_visible(False)`). With either one, `T1.docx`'s PNG carries no AUROC, slope or intercept, and nothing fails. Lens 3 asked for visible texts after `canvas.draw()`. The mutants are not realistic edits, so I record this rather than block on it.
2. **No CLI test for the level and operating-point routes of `$...$`.** The repair tests the author route through the API only. I ran the four routes through the CLI (table below), so the behaviour holds. The mechanism is pinned through the decorator and rc tests.
3. **`test_e10_criterion.py`'s comment and the merge commit say `ax.text(0.03, 0.93, ...)` is "in axes ... fractions".** It is in data coordinates. Measured: the text's transform `is ax.transData`, and it equals axes fractions only because `xlim` and `ylim` are `(0.0, 1.0)`. `fig.legend`'s `bbox_to_anchor` is in `transFigure`, as said.
4. **`compare --format` help** reads "comma list of json, html", but `docx` is accepted and writes T7.docx and T8.docx (c3 below). The `cli.py` module docstring's exit-7 sentence is scoped to `run` (see B1).
5. **README Status** (E10's paragraph) says `run` writes "the HTML documents named by `--templates`" and `compare` writes `T2.html`. It does not mention DOCX, though the README's DOCX bullet further down does. This is incomplete, not false.
6. **`compare --templates T2,T7,T8 --format json,html,docx` licensed** prints "`--templates T2,T7,T8 writes all three`" after `T2.docx not written`. That is true of the HTML only.
7. **`_builtin_rc`'s docstring cites `matplotlib.style.core.STYLE_BLACKLIST`.** matplotlib 3.11.2 warns that `matplotlib.style.core` is deprecated and will be removed in 3.13. The code does not import it. The statement is true today: `style.use("default")` filters `_STYLE_BLACKLIST`, which equals `style.core.STYLE_BLACKLIST`. `pyproject.toml` has `matplotlib>=3.9` with no upper bound.
8. **T1's criteria-table DOCX cells are compared with the HTML by no test.** The roundtrip test reads T8. With `ec9699c`'s T1.docx and T8.docx dropped into the merge tree, three tests fail (`test_every_t8_criteria_cell_and_every_t7_table_cell_is_in_the_docx_as_the_html_shows_it` and the two regeneration tests). An old T1.docx alone would be caught only by the regeneration test. My own cell-by-cell reader found no mismatch (below).

## What I tried and could not break

**Suite, markers, lint, lock (`a13931b` worktree).**

| | Git Bash | PowerShell 5.1 |
|---|---|---|
| full suite | `1853 passed, 2 skipped, 1 xfailed in 218.70s` | `1853 passed, 2 skipped, 1 xfailed in 241.30s` |
| `-m ap4` | `193 passed, 1663 deselected` | `193 passed` |
| `-m day10` | `261 passed, 1595 deselected` | `261 passed` |
| `python -m ruff check .` / `format --check .` | `All checks passed!` / `273 files already formatted` | the same |
| `python -m uv lock --check --offline` | `Resolved 72 packages` | - |

The second skip is `test_e8_repair4.py:405` (the confusables path is relative to the lens worktree; environmental, as in every lens). That accounts for the orchestrator's `1854 passed, 1 skipped`.

**Sweeps** (`a13931b` worktree, `PYTHONPATH` forced, `PROOFPACK_REQUIRE_DOCX=1`). `--marker ap4`: `19 planted, 19 killed, 0 survived; 571 s`, which includes `ap4_png_mathtext_parsed` and `ap4_curve_legend_two_dp`. `--marker day10`: `37 planted, 37 killed, 0 survived; 1343 s`. That is E10's 18 plus A-P4's 19, all `day=10`. The baseline passed in each copy.

**Merge correctness, file by file.** Against `c779678`, `cli.py`, `run.py`, `test_offline.py`, `mutation_sweep.py`, `pyproject.toml`, `uv.lock`, `ci.yml`, `README.md` and `test_render_t8.py` show only A-P4's additions. Against `ec9699c` they show only E10's. Nothing either side had is missing. Specifically:
- `test_offline.py` keeps `test_compare_with_t2_offline_opens_no_socket` and `test_run_offline_with_format_docx_opens_no_socket`.
- The sweep keeps all `AP4_MUTANTS`, and E10's `count=2` and re-pointed patterns.
- `pyproject.toml` has E10's `day10` text, A-P4's `ap4` marker and the `docx` extra.
- The lock has urllib3 2.8.0 and the nine extra packages.
- `ci.yml` has the `docx-extra` job and A-P3's comment.
- `test_render_t8.py` has the `pdf` change and E10's edits.

**CLI behaviour** (F5 pair; `--offline`; exit code; files; notes):

| case | rc | written | notes printed (true?) |
|---|---|---|---|
| c1 compare `--templates T2 --format json,html,docx`, licence ok | 0 | T2.html + 4 JSON | `T2.docx not written: template T2 is not built in this engine version` (true) |
| c2 the same, licence without `compare` | 4 | 4 JSON | `HTML and DOCX not written: the licence (lic_test...) does not carry the 'compare' feature; run.json only` (true; the merge's change) |
| c3 compare `T2,T7,T8` json,html,docx | 0 | T2.html, T7.html, T7.docx, T8.html, T8.docx | true (N6 aside) |
| c4 compare, no licence | 4 | 4 JSON | `HTML and DOCX not written: licence refused (no_file)` (true) |
| c5 compare `--format json,docx --templates T2` | 0 | 4 JSON | `T2.docx not written...`; `Next step: compare again with --format json,html for T2.html` (true) |
| r4 run `--format docx --templates T1,T7,T8`, licensed | 0 | T1/T7/T8.docx | Next step names the three `.docx` (true) |
| r5 the same, unlicensed | 4 | 3 JSON | `DOCX not written: licence refused (no_file)`; `then run again for T1.docx, T7.docx, T8.docx` (true) |
| r6 grace (expired 5 days ago) json,html,docx T1,T7,T8 | 0 | 6 documents | `licence grace (expired_within_grace); watermark: LICENCE EXPIRED - not for submission` (true) |
| r7 expired past grace json,docx | 4 | 3 JSON | `DOCX not written: licence expired (expired_past_grace)` (true) |
| r8 run under a licence without `compare` | 0 | T8.html, T8.docx | the `run` path ignores the feature (true: `compare_licensed` is `True` for `run`) |
| r9 run `--templates T2,T8 --format json,docx` | 0 | T8.docx | the T2 line, then `Next step: open the documents ... (T8.docx)` (true) |
| h3 run with the extra hidden | 7 | no out dir | the one line (true for `run`) |
| h2 compare `--format docx --templates T2`, extra hidden | 0 | 4 JSON | no crash: T2 has no DOCX writer |

**The Type column (merge integration).** I wrote my own lxml reader of `w:tc` text and compared it with the HTML `tr.criterion-row` cells. I covered T1 and T8 for an F5 `run` (C1 point, C2 paired), T8 for an F5 `compare`, T8 for an unpaired `compare` (`--allow-unpaired`, prior minus one row, rc 2), and the synthetic cohort with three criteria: a `level: *` point bound with an `[unverified] Dr B.` author, an overall paired one, and an explicit `type: point`. The header is 19 = 19 in every case and the cells are equal: 38, 38, 38, 38 and 76 + 76 compared, 0 mismatches. The Type cells read `point` / `paired difference vs prior version`. The DOCX caption sentence equals the HTML caption's Type sentence word for word; the HTML wraps `type` and `proofpack compare` in `<code>`. The synthetic cohort with no criteria prints no criteria table and no caption in either medium. The T7 unpaired method descriptions (`Newcombe 1998 method 10 ...`, `DeLong Wald interval for the difference ...`, `not like-for-like` ×2) print in both T7.html and T7.docx. Restoring `ec9699c`'s T1.docx and T8.docx makes the round-trip T8 test fail, which confirms the integration fix is pinned for T8.

**Repair 3.**
- `test_ap4_repair3.py` copied into `fd9488f`: `1 failed, 1 passed`. The mathtext test fails with `ParseFatalException: Unknown symbol: \foo`. The legend test passes there, which is expected because the code was right.
- Legend mutants in `w-mut`, each alone, `-m ap4 -x`. Each of these was killed by `test_f2_f3_f4_png_legends_equal_the_svg_legend_text` (`1 failed, 124 passed`):
  - F2/F3 legend 3 dp to 2 dp (lens 3's L3-n)
  - F4 decile label 3 dp to 2 dp (L3-o)
  - F2/F3 CI dropped
  - F4 CIs dropped
  - F4 slope and intercept swapped
  - F2 reference label `chance`
- The two visibility mutants survived (N1).
- `$...$` through the licensed CLI on the synthetic cohort (`--format json,html,docx --templates T1,T8`). The strings were `\foo$`, `$\foo$`, `$x^2$`, `\$`, `$$`, a lone `$` and `$\alpha$`, each in four routes: criterion author, CSV `site` level, `model.name` and operating-point id.
  - At `a13931b` all 28 runs exit 0 and write T1/T8 HTML and DOCX.
  - At `fd9488f`, `$\foo$` (author, level, op id) and `$$` (author, level) exit 5 with `T1.html` and `run.json` written and no DOCX. The other 23 exit 0.
- Drawn as written, at `a13931b`, after `png_bytes` on all 11 figures:
  - The author `$\foo$` is in the F5 criterion legend `customer criterion S1 ($\foo$, 2026-03-01): 0.4275 (heavy dashed)`.
  - The level is in the F5 level labels (`$\foo$ (ref)ᶜ`).
  - The op id is the F2 annotation `$\foo$`.
  - Every Text holding the string has `get_parse_math() == False`, so 0 are parsed.
  - DOCX/HTML occurrence counts are author 6/7 and level 21/24, where the HTML's extra occurrences are SVG texts.
- Sentences:
  - The `figures_png.py` dash-pattern rule holds. The F2 and F3 series are `-`, the references `(0, (6, 4))`, and the F5 criterion line `(0, (10, 4))` at width 2.5 beside the reference `(0, (6, 4))` at width 1.0. F4's labelled decile series has line style `None` and marker `o`.
  - `_builtin_rc`'s blacklist sentence holds for 3.11.2.
  - `docx.py`'s `m{_{ 7*7 }_}n` sentence holds: licensed exit 0, and T8.docx has `m{{ 7*7 }}n` ×2 while the HTML has `m{_{ 7*7 }_}n`, the documented docxtpl rewrite. Unlicensed: exit 4, `HTML and DOCX not written`.
  - "The engine writes no precision-recall array" holds: no `"pr"` key outside `render/`, and `threshold_free` keys are `auprc, auroc, auroc_wald, prevalence, roc`.

**AI-DSF.** `git diff fd9488f ec9699c` and `git diff ec9699c a13931b` (src, scripts, tests, README) add no line naming AI-DSF. The new DOCX caption and cell text add none. The one pre-existing case is still open (lens 1 RG1-N7, lane E, DEC-71(a)), measured on the merged r6 run. One paragraph in T1.docx names AI-DSF, `T1 · FDA AI-DSF performance evidence attachment set`, and it lacks `not for implementation`. T7.docx and T8.docx have no such paragraph.

## What I could not check

- Word itself, so pagination, fields and how the PNG legend looks were not checked. I read artist state, not pixels.
- CI: nothing is pushed, so neither the `docx-extra` job nor the `test` job has run on `a13931b`.
- B1 with the extra genuinely uninstalled. I hid it with `sys.modules[...] = None` in-process, the same method as the earlier lenses.
- Byte identity on another platform.

## Sentences I refused to write

- "The merge lost nothing from either side." The T1-11 type note is lost in the DOCX (B2).
- "`--format docx` without the extra writes nothing." That holds for `run` only (B1).
- "The PNG legends are tested." Their strings are. Whether they are drawn is not (N1).
