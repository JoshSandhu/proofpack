# Lens 1 (regression and record) - build day 9, lane E, at `71b00d2` - 2026-09-23

**Verdict: FAIL.** There are two blockers. Both break the binding rules on rendered pages. No test fails on either of them.

- **RG-B1.** A number is typed into a template. F4's note in `_figures.html` prints the literal `200/200 convention: fewer than 200 events or non-events`. It does not read `run.json`'s `calibration.curve_flag` `minimum` or `note`. With `minimum` planted as 150, the SVG still prints 200 and the page contradicts itself.
- **RG-B2.** The forbidden word `verdict` appears 4 times on the rendered T7. T1's own verdict grep, applied to T7, fails with those 4 hits. T7 has no verdict grep: `test_no_status_word_on_t7_...` looks only for `criterion met` and `not assessable`.

These figures in the E9 build note matched what I re-ran, in Git Bash and in PowerShell 5.1:

- **Suite.** `1387 passed, 1 skipped, 1 xfailed` in both shells (129.12 s / 127.33 s).
- **Markers.** In both shells:
  - `day9` 131, `day8` 468, `day7` 139, `day6` 285, `day5` 54, `ap2` 88;
  - `day4` 182, `day3` 29 + 1 xfailed, `day2` 40, `day1` 59 + 1 skipped.
- **Counts at `eda8a35`.** `--collect-only` gives day5 54, day6 285, day7 139, day8 468, ap2 88, and day9 `no tests collected`.
- **Lint.** `All checks passed!` / `185 files already formatted`.
- **Sweeps.**
  - day-9 sweep: `15 planted, 15 killed, 0 survived`, exit 0, in both shells (120 s / 135 s).
  - day-8 sweep: `103 planted, 103 killed, 0 survived` in Git Bash (1460 s). I did not run it in PowerShell.
- **`--list`.** 289 lines: 34 day5, 112 day6, 25 day7, 87 day8, 15 day9, 16 ap2.
- **Sample pack.** 236,843 / 140,030 / 48,126 / 35,227 bytes. The Git Bash build, a second Git Bash build and the PowerShell build are equal once `run_id`, `run_id[:8]`, `started` and `duration_s` are masked.
- **Stats and gates.** `git diff --name-status eda8a35 71b00d2 -- src/proofpack/stats/ src/proofpack/gates.py` prints nothing.

Worktrees, all under `scratchpad/lens-E9-r1-regression/`:

| Worktree | Commit | Used for |
|---|---|---|
| `wt71` | `71b00d2` | suite, markers, lint, timing, PowerShell sweep |
| `wteda` | `eda8a35` | pre-build runs and marker counts |
| `wtmid` | moved `8c5dbfd`, `0d65c03`, `5078a03`, then `71b00d2` | pre-fix runs, footer, anchor and SVG mutants, Git Bash sweeps |
| `wtmut` | `71b00d2` | probes, rerun block, wheel, row-23 mutant |

In each worktree I forced `PYTHONPATH=<worktree>/src` and printed `proofpack.__file__` before trusting any figure. Every printed path was inside that worktree. The wheel check imported from the unpacked wheel under `python -S`, and the printed path was `...\whlx\proofpack\__init__.py`.

I committed nothing. The only file I wrote in the main tree is this note.

## Blockers

**RG-B1 - F4 prints a typed `200` that does not come from the run.** The rule (CLAUDE.md, and the computed task: "no number typed into a template") and D4 section 14 ("every numeric token in the rendered pack maps to a JSON Number; zero orphan numbers") are both broken. `src/proofpack/templates/_figures.html` line 56, verbatim:

```
{% if f.flag %}<text class="fig-text fig-note" x="90" y="58">200/200 convention: fewer than 200 events or non-events</text>{% endif %}
```

`figures.f4_calibration` builds `f.flag` from `curve_flag.note` and uses it only as a truth value. The page prints the typed text instead.

On the sample pack (128 events), T1 carries that SVG line. I planted `curve_flag.minimum = 150` and a note reading `fewer than 150 events ... (planted by the lens)`, then rendered T1. The F4 SVG still printed `['200/200 convention: fewer than 200 events or non-events']`, while the planted note printed elsewhere on the same page (`planted by the lens` present: True). No test fails.

Repro: in a worktree, `python -c "import json;from proofpack.render import t1;d=json.load(open('<sample>/run.json',encoding='utf-8'));d['calibration']['curve_flag']['minimum']=150;d['calibration']['curve_flag']['note']='fewer than 150 events';print('200/200 convention' in t1.render_t1(d))"` prints `True`.

**RG-B2 - T7 prints the forbidden word `verdict` four times, and no test reads T7 for it.** The rule: "the verdict words ... appear in ... no rendered page except where a criteria table prints the three status words".

T7 renders `design/conventions_T7.md` (E6's file) into the page. These are the rendered text nodes on the sample pack's T7, verbatim:

- `... z and the two-sided p are detail, never a verdict.` (conventions_T7.md line 35)
- `Nothing here is a verdict: no target is compared to and no word describes the calibration;` (line 183)
- `test_no_verdict_word_appears_in_any_key_or_engine_string_of_the_day6_output` (line 184; a pytest id, printed to a regulator-facing page)
- `... walks every key and string of the assembled day-6 documents for the verdict words the brief names` (line 185)

`tests/test_render_t1.py::test_status_words_only_in_status_elements_and_no_forbidden_word_outside_exempt_text` has the same exemptions (disclaimer, customer-text). I applied its loop to `render_t7(document)` on the T7 golden's document and it failed: `HIT (['verdict'], ...)` × 4. `tests/test_render_t7.py::test_no_status_word_on_t7_and_the_page_has_no_external_reference` looks only for `criterion met` and `not assessable`.

The E9 note says the forbidden grep found "0 hits over 82 texts", but that is the library only. The brief's test line is "forbidden grep = 0". (D4 section 14 names T1/T2/T3 for its grep; the task's rule names every rendered page.)

Repro: `python -c "import json,re;from proofpack.render import t7;print(len(re.findall(r'verdict', t7.render_t7(json.load(open('<sample>/run.json',encoding='utf-8'))))))"` prints `4`. With `\bverdict\b` it prints `3`, because the pytest id's `_verdict_` has no word boundary.

## Non-blocking

**N1 - Record: the note says "Eleven commits"; there are ten.** `git rev-list --count eda8a35..71b00d2` = `10`, and the note's own table lists ten.

**N2 - A false sentence in the note.** The furniture row says marks are "imported from `licence.verify` / `scope`, never typed in a test or template". The templates part holds: the furniture grep finds none. The tests part does not:

- `tests/test_render_t1.py:371` types `"INCOMPLETE - customer sections outstanding: 11"`;
- `:383` types the same with `10`;
- `:374` types `f"[CUSTOMER TEXT REQUIRED - {s['title']}; ProofPack does not draft this]"`;
- `tests/test_render_t8.py:210, 213, 604` (E8) type `LICENCE EXPIRED - not for submission`.

Typing a literal in a test is a fair independent oracle. The sentence is what is wrong.

**N3 - The footer tests count footers; they do not check each page.** I built a mutant of `T1.html` with two `page_footer()` calls on page 1 and none on page 9. Across `test_render_t1/t7/t8/furniture/sample_pack/e9_templates` it gave `1 failed, 142 passed`, and the one failure was the golden. `test_the_footer_is_on_every_page_and_once_in_print` passed.

Its name says "on every page". What it inspects is `count('class="page-footer"') == count('<section class="page')`. The same count is in `test_each_furniture_element_is_on_t1_and_t8` and `test_every_page_of_every_document_is_marked_synthetic`. Removing page 9's footer alone is killed (`4 failed, 60 passed`: the golden, the footer test, furniture, sample pack).

**N4 - Most SVG-map changes are killed only by the golden (by design, recorded).**

Killed by the figure tests:

- **`PlotMap.y` +1 unit, `data-map` unchanged.** Failures: F2, F3, F4 and the golden. The F5 tests pass: F5's y is row position.
- **`PlotMap.x` +1 unit.** Failures: F2, F3, F4, both F5 tests and the golden.

Killed only by the T1 golden (`1 failed, 21 passed`):

- F4 strip map `ymax` = `n_max + 1`;
- F5 forest map `w` = `FOREST_W + 1`.

The test inverts through the `data-map` that the same code writes, so a consistent change of a map constant is invisible to it.

**N5 - The S4 list is complete for CLI flags, printed lines and JSON keys, but omits Python API changes.** Omitted:

- `proofpack.run.LICENCE_FIX` is removed and replaced by `run.licence_fix(watermark)`;
- new `run.watermark_for` and `run.document_writers`;
- new keywords `assemble_run(data_marking=)` and `manifest.build_manifest(data_marking=)`;
- new export `proofpack.licence.WATERMARK_NO_LICENCE`.

`proofpack-site` at `48430ab` imports none of these. I grepped for `LICENCE_FIX`, `write_documents`, `assemble_run`, `build_manifest` and `data_marking`, so this breaks nothing measured.

**N6 - The timing figure omits its condition.** The timing test uses `make_criteria()`, whose `bootstrap.B` is 200. The engine default is `B 2000` (`schema/criteria_schema.json`). Mine at B = 200:

- Git Bash alone: 6.09 s whole, 0.45 s renders.
- PowerShell: 5.62 s / 0.45 s.
- Inside the full suite: 6.33 s / 0.48 s.

The same test at B = 2000 (a lens copy, removed): 8.93 s whole, 0.31 s renders, T1 3,690,190 bytes. All figures are under 60 s.

**N7 - The PowerShell k1 row cannot come from the builder's `rerun.ps1` as written.** The script sets `$env:LENS_WT=(Get-Location).Path`, which uses backslashes. The harness (`lens-E8-r7-fresh-attack/prev/prev3/harness.py`) asserts that the `proofpack.__file__` path, rewritten with forward slashes, starts with `LENS_WT`. So in PowerShell `k1_checker.py` exits 1 with an `AssertionError` and prints no `free_text accepted` line. I reproduced this in the main tree read-only, and in my worktree.

With a forward-slash `LENS_WT` the PowerShell output equals Git Bash: `engine claims rejected: 0` and the same 15 texts. The note's "identical" for PowerShell may be true, but not from that script.

**N8 - T1's `<h1>` names the draft guidance with no qualifier.** It reads `T1 · FDA AI-DSF performance evidence attachment set`. The label `draft guidance (January 2025), not for implementation` first appears lower on the cover, in the "Guidance versions referenced" row.

This is the only one of T1's 74 guidance mentions without the label within 250 / 400 characters of it (my scan of the sample pack). T7 has 7 mentions and T8 has 22, all labelled. It is a heading, not an anchor. D4 section 2 names T1 this way.

**N9 - An unrecorded D4 deviation.** D4 section 2 row 12 says "only rendered if `criteria` block present". T1 always renders section 12. With no criteria it prints `No acceptance criteria were declared; estimates and intervals only.`, and `test_the_fifteen_sections_are_present_in_d4_order` requires it. This is defensible under DEC-08 (annotate, never omit), but the note's Decisions list does not name it.

**N10 - The theme guard refuses exactly the six characters it names.** `css_root_block()` accepted a token value `a /* b` (a comment opener) and an unbalanced `"unbalanced` (my probe). Its error text, "a character a <style> block cannot hold", generalises beyond what it inspects. The token file is repo-controlled.

**N11 - A sentence generalises.** The `render/sentences.py` docstring says a subset of `CALIB_HIERARCHY`'s pointers "never shifts a number into another slot". The evidence is one reversal test plus the sweep mutant `facet_family_slot_bound_to_another_pointer` (killed), and the note carries row 51 un-re-measured. It should name the inputs fed.

**N12 - The goldens fix four fields, not three.** The assembler fixes `run_id`, `started` and `duration_s`, and the T1/T7/T8 golden tests also set `manifest.numpy = "x.y.z"` (E8's practice, stated in each test docstring). Also, the goldens render the assembler's document, not a `proofpack run --offline` output. The CLI path is pinned separately by `test_run_templates_t1_writes_t1_html_beside_run_json` and the T7 CLI tests.

**N13 - The pack contradicts itself about Clopper-Pearson (recorded by the note, needs 2).** T1 page 2 and T8 section 1 print `Clopper-Pearson alongside at k = 0 or k = n, and bootstrap settings are ProofPack conventions, stated in T7 with citations`. T7 prints `Clopper-Pearson is not printed beside it at k = 0 or k = n in this build`. E9 adds T1 as a second page that carries the untrue sentence.

**Open items the note omits:** RG-B1, RG-B2, N8 and N9. Nothing else found: every other cut and carried item I checked (F3 no-data, F5 first operating point only, row 49, both-ways tables, the ten library-only templates, rows 51/67/71/87/81) is in the note.

## Could not break

- **Pre-build (build items).** I copied the eight new test files and the two goldens into `wteda`:
  - seven files abort at collection with `ImportError` (no `render.t1`, `t7`, `figures`, `sentences`, and no `WATERMARK_NO_LICENCE`);
  - `test_sweep_day9.py` gives `3 failed`.
  - The three edited test files also fail at `eda8a35`:
    - `test_templates_t1_prints_the_typed_line...` on the assertion (`'not written' is contained here: T1 not written: template T1 is not built in E8`);
    - `test_claims...enums_agree` on `AttributeError: ... 'FACET_BINDINGS'`;
    - `test_run_cli.py` at collection, on `ImportError: cannot import name 'WATERMARK_NO_LICENCE'`.

  For build items an import abort is the expected pre-build failure.
- **Pre-fix (repairs), each failing on its assertion:**
  - `71b00d2` comparator test at `8c5dbfd` fails on `assert ('Sensitivity k/n' not in ...)`.
  - `8c5dbfd`'s `test_every_declared_mutant_of_every_day_still_matches_its_file` at `0d65c03` gives `1 failed, 2 passed`, first extra `('list_key_string_not_split', 'day6', 2, 1)`, 4 items.
  - The theme test at `5078a03` fails on `assert ('&#34;' not in ...)` with `onospace, &#34;Cascadia Mono&#34;`.
  - Row 23 (`951cd08`): the note records no pre-fix run. I restored the ungated loop (`{% if true %}`) and `test_the_pages_are_pure_functions_of_run_json_and_no_criterion_is_authored` failed (`1 failed, 57 passed`).
- **Nothing weakened.** `git diff --name-status eda8a35 71b00d2 -- tests/` shows only A and M rows, no D. The only marker lines added are eight `pytestmark` day9 lines (one with `slow`). No skip, xfail, `.only` or todo was added. The replaced `test_render_t8` assertion now asserts that T1 and T7 are written.
- **Anchor label.** Each of these kills `test_every_fda_draft_anchor_is_labelled_in_every_margin_note`, among 5-7 failures:
  - the `FDA_AIDSF_SUBGROUP_PERF` map row status set to `final`;
  - its `version_date` blanked;
  - the margin note printing the document title only.
- **Library against D4 section 8.** D4 has 55 ids (the four-id last row split) and the library has 56. None is missing. The one extra, `SUBGROUP_ESTIMATE`, is present at `eda8a35`. `all_skeletons()` returns 83 texts: 56 base, 6 variants, 21 phrase texts. The enum test compares `{tid for tid, _, _ in all_skeletons()}` with the claims-schema enum by equality.
- **Goldens.** `PROOFPACK_REGEN_GOLDEN=1` on the three golden tests (`3 passed`) and then `git diff --stat` printed nothing: T1, T7 and T8 regenerate identically (LF-normalised).
- **Cell re-derivation.** I wrote my own formatter from D4 section 1.2:
  - 1-dp percent, 3 dp;
  - signed pp with U+2212;
  - tiers ᵃᵇᶜ;
  - `n.e. (reason)`.

  The sample T1 has 124 `data-ref` cells. I compared 114 and skipped 10 (k/n or CI facets of n.e. Numbers, `three_dp` k/n): **0 mismatches**.
- **Sample-pack marks.** Each page's footers, and the stamps on each cover:
  - T1: 9/9 footers carry both `SYNTHETIC - illustrative` and `NO LICENCE - not for submission`; stamps licence/data/`INCOMPLETE - ...: 11`; 11 CT placeholders.
  - T7: 3/3 footers; stamps licence and data.
  - T8: 3/3 footers; stamps on the cover and again in section 11.

  No status word appears on any of the three, and `approved` / `endorsed` appear only in the disclaimer text.
- **Sockets.** Under a `socket.socket` / `create_connection` guard, the sample-pack script exited 0 with `socket calls 0`.
- **Injection.** A `sex` level label `</text><script>alert(1)</script><text>` and a model name `<img src=x onerror=1>` gave 0 raw `<script` and 0 raw `<img` on T1, T7 and T8. T1 printed `&lt;script&gt;` 5 times.
- **Wheel.** `python -m uv build --wheel` contains all 16 new E9 paths I listed:
  - the two `_schema` files;
  - six templates;
  - five render modules;
  - `synthetic.py`.

  Rendering the sample `run.json` from the unpacked wheel under `python -S` (no `.pth` processed) gives T1/T7/T8 byte-equal to the source-tree pages (140,030 / 48,126 / 35,227).
- **Rerun block, both shells.** Doctor exit 0 with 17 `[ok` lines; tr39 `vendored subset matches`.
  - No-licence run: exit 4 and `watermark: NO LICENCE - not for submission`. PowerShell prints exit 4 when run without `Select-Object`.
  - `253938 bytes 20 keys 70 claims 0 rejections 3 refs`. The note's 253,937 differs by the `duration_s` digits: mine is 0.765, the builder's 0.92.
  - nomap exit 3 H07, `licence show` exit 4.
  - `html_run` `T8.html bytes 44010`.
  - `repros5` / `repros6` lines as r6.
  - p3/p2/p7/alias/offline (`socket calls 0`)/paths/imports (`imports ok; loaded: []`) as r6.
  - Verdict grep `5 passed`; E6 schema `1 passed`.
- **CI.** `.github/workflows/ci.yml` step "pytest every declared day marker" reads the markers from `pyproject.toml`, which declares `day9`. No `slow` deselection exists in CI.
- **Day-8 sweep (Git Bash, at `71b00d2`).** `103 planted, 103 killed, 0 survived; 1460 s`, exit 0. The builder measured this at `8c5dbfd`.

## Could not check

- The day-8 sweep in PowerShell: I did not run it, for time (28 minutes a shell).
- The browser claim that E8's pages rendered in the serif default. I checked the entity-escaping mechanism in bytes; I did not open a browser.
- The note's "130 data-ref cells" on its CLI run. I re-derived the sample pack's 124 instead.
- The note's statement that each of the three T8 golden regenerations was diff-checked.
