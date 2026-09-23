# Lens 2 (regression and record) - build day 9, lane E, repair 1 at `dd94874` - 2026-09-23

**Verdict: PASS. No blockers.** Every figure in the repair note that I re-ran matched. Every lens-1 blocker repro now gives the fixed result. Each new test fails at `71b00d2` on the assertion the note quotes, with one exception: the footer-helper test passes there (N1). Five non-blocking items follow. One is a sentence violation in a test docstring (N1). Two are untested branches I found with my own mutants (N2).

Worktrees, all under `scratchpad/lens-E9-r2-regression/`, all removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wtdd` | `dd94874` | suite, markers, lint and the rerun block, in both shells |
| `wt71` | `71b00d2` | the new and edited test files copied in (pre-fix) |
| `wtmut` | `dd94874` | mutants, probes, goldens, sample pack, wheel |

In each worktree I forced `PYTHONPATH=<wt>/src` and printed `proofpack.__file__` before trusting a number. Every path printed was inside that worktree. Every run outside pytest carried `--offline`. I committed nothing. The only file I wrote in the main tree is this note.

## Blockers

None.

## Non-blocking

**N1 (sentence_violation, minor) - a test docstring says each test fails at `71b00d2`; one passes there.** The docstring of `tests/test_e9_repair1.py` says: "each fails at ``71b00d2`` (the pre-fix line is in the repair note)".

I copied `test_e9_repair1.py` and the five edited test files into `wt71`. `test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant` **passed** there (`PASSED tests/test_e9_repair1.py::test_the_footer_helper_...`). It builds its mutant inside the test and checks a test helper (`footers_per_page`), so it cannot fail against the old source.

The repair note itself is accurate on this point. Its RG-N3 row shows a different pre-fix check (the lens's mutant planted in `71b00d2`'s `T1.html`: the old test passed, the new one failed), and its "13 failed, 96 passed" count includes this test among the passes.

I checked the helper does real work in the source, not only in the test: with the footer moved from page 9 to page 1 in `templates/T1.html`, it gives `4 failed, 159 passed`. The failures are the golden, `test_the_footer_is_on_every_page_and_once_in_print`, the sample-pack marks test and this test.

Repro: copy `tests/test_e9_repair1.py` and `tests/test_render_t8.py` from `dd94874` into a `71b00d2` worktree, then run `PYTHONPATH=<wt>/src python -m pytest -q tests/test_e9_repair1.py -k footer_helper`. Result: `1 passed`.

**N2 - two repair branches have no test that fails when they are mutated.** I planted 16 mutants of the repaired code in `wtmut` and ran them against `-m day9` (timing test deselected).

- **Killed: 10.** The F5 reference-line gate; F4's on-plot line with `200` retyped; T1-10 methods without AUROC; T1-11 methods without AUROC; X1 from `diff_vs_reference` only; `method_list` taking the first id only; the IPA footnote always printed; the exit-4 line naming the first template only; F4's "not drawn" clause dropped; the THRESH_PROVENANCE phrase reverted.
- **Survived, and the behaviour can change (non-equivalent):**
  - `f2_gate_se_only`: F2 checks only sensitivity/PPA for an interval. No test plants a typed reason on specificity/NPA. I probed the real code by hand: specificity set to `boundary_estimate` → `marker drawn: False`, and the caption reads `op1 (specificity n.e. (boundary_estimate))`. The code is right; nothing pins it.
  - `cli_json_branch_T8`: the `--format json` next-step line is untested. The real code, which I ran with a test licence and `--offline`, prints `Next step: run again with --format json,html for T1.html, T7.html (docs: /docs/run)` for `--templates T1,T7`, and `... for T8.html` by default. So the note's S4 line is true, but no test holds it.
- **Survived, but no fed input can tell the difference (equivalent):**
  - `t10_methods_no_overall`: leaving the overall row out of T1-10's method list changes nothing on the fed documents, because the overall row's methods are already among the subgroup rows' methods.
  - `method_list_default_wilson`: an unknown method id falls back to the Wilson phrase. On every engine input this cannot happen. Every `method` in the three `run.json` files I made, and every method in the output schema's enums, has a `METHOD_PHRASES` entry (the gap lists were `[]`).
  - Two more of my own mutants (`f4_no_interval_gate` as I wrote it, `x1_includes_analytic`) were equivalent as written, so I discarded them. Reverting F4 to its `71b00d2` behaviour is killed, as the pre-fix run already shows.

**N3 - one more place types `200` (the RG-B1 kind of defect), this time in an engine string the repair edited.** `scope.LONG_FORM_ITEMS[6]` keeps "the 200/200 calibration-curve convention" (D4 7.2 verbatim). It prints on T1 page 2 and T8 section 1.

With `curve_flag.minimum = 150` planted in the sample `run.json`, T1's F4 plot now reads `150/150 convention ...` (once), but page 2 still prints the 200/200 sentence.

This cannot happen on a real run. `minimum` is `stats.calibration.CURVE_MIN_EVENTS`, and the criteria schema gives the customer no way to set it. It is the engine constant written into text.

Repro: `python -c "import json,re;from proofpack.render import t1;d=json.load(open('<sample>/run.json',encoding='utf-8'));d['calibration']['curve_flag']['minimum']=150;print(re.findall(r'the 200/200 [a-z-]+ convention', t1.render_t1(d)))"`

**N4 - the S4 list does not name the template-context keys this repair adds.**

- `figures.f4_calibration` gains `flag_short`.
- T1's per-operating-point context gains `table_methods` and `diff_methods`.
- `t7_context` gains `x1_methods`.
- F5's `desc` text now depends on whether a reference line is drawn.

These are internal render inputs. `proofpack-site` names none of them: my grep for `proofpack.render`, `X1_SENTENCE`, `TOLERANCE_POLICY`, `LONG_FORM_ITEMS`, `css_root_block`, `method_list`, `cell_methods` and `difference_methods` found no match. For CLI flags, defaults, output paths and `run.json` keys the list is complete: `git diff --stat 71b00d2 dd94874 -- src/proofpack/run.py schema/ src/proofpack/manifest.py pyproject.toml uv.lock .github/ scripts/` prints nothing, and `cli.py` changes only the two next-step strings.

**N5 - the page grep's word list is narrower than the checker's.** `tests/test_render_t8.py::FORBIDDEN_ON_PAGE` is missing seven words from `narrate/checker.py`:

- from `VERDICT_WORDS`: `noninferior`, `unresolvable`;
- from `CERTIFICATION_WORDS`: `approval`, `certification`, `clearance`, `endorsed`, `endorsement`.

I ran the checker's full lists over 18 pages: T1, T7 and T8 of six documents (i.i.d. with criteria, logit score, `y_pred` only, comparator, clustered with `case_id = c{i//3}`, derived threshold). Outside `.status`, `.disclaimer` and `.customer-text` there is exactly one hit per page: `endorsed`, in `.cover-note`, in the disclaimer sentence "no regulator has endorsed this tool". It is a negation, and E8's T8 already printed it. It is not an endorsement claim, but it sits outside the exempt scopes. Record only.

## Measured against the note

**Suite.** `1399 passed, 1 skipped, 1 xfailed` in both shells, equal to the note. Git Bash took 112.53 s and PowerShell 5.1 108.59 s.

**Markers.** Equal to the note in both shells:

| Marker | Count |
|---|---|
| `day9` | 143 |
| `day8` | 468 |
| `day7` | 139 |
| `day6` | 285 |
| `day5` | 54 |
| `ap2` | 88 |

`--collect-only` gives the same figures. They equal the counts collected at `eda8a35` (day5 54, day6 285, day7 139, day8 468, ap2 88). `day9` is 143 = 131 at `71b00d2`, plus 11 in `test_e9_repair1.py`, plus 1 theme test.

**Lint.** `All checks passed!` / `188 files already formatted` in both shells.

**Pre-fix run.** This is the note's own file set: `test_e9_repair1.py`, the new theme test, `test_e9_templates.py`, `test_render_t1.py` and `test_sample_pack.py`, copied into `wt71`. Result: **`13 failed, 96 passed`**, equal to the note. With `test_render_furniture.py` and `test_render_t8.py` added in full: `14 failed, 135 passed`. The fourteenth is the edited theme-block test, which fails on its new message match.

Each failure's first `E` line equals the line the note quotes:

- `assert [(['verdict']...erdict word')] == []`
- `AssertionError: T7.html`
- `assert [(['biased'],...ally biased')] == []`
- `'Interval methods in this table: cluster bootstrap, percentile interval;' in '...Wilson score for proportions, DeLong for AUROC; tiers ...'`
- `'data-role="...data-bin="1"' not in ...`
- `'data-role="reference"' not in ...`
- `['200/200 con...r non-events'] == ['150/150 con...r non-events']`
- `'identical manifest hash' not in ...`
- `'then run again for T1.html, T7.html (docs: /docs/run)' in '...'`
- `'the refused characters < > { } ; \\:' in "token --pp-x carries a character a <style> block cannot hold: 'a<b'"`
- `[('THRESH_PRO..., ['biased'])] == []`
- `'Operating po...cally biased.' == 'Operating po...estimated on.'`

None aborts on import or attribute.

**Nothing weakened.**

- `git diff --name-status 71b00d2 dd94874 -- tests/` shows 1 A and 8 M, no D.
- The only marker line added is `pytestmark = pytest.mark.day9`. No skip, xfail, `.only` or todo was added to code or tests.
- The one assertion removed is the grep's `biased` exemption.
- `match="cannot hold"` was replaced by the new message match.
- The footer total-count assertions were replaced by the per-page `[1] * sections` check.

**No statistics.** Both commands print nothing:

- `git diff --name-status 71b00d2 dd94874 -- src/proofpack/stats/ src/proofpack/gates.py src/proofpack/criteria.py src/proofpack/egress/ src/proofpack/narrate/checker.py src/proofpack/narrate/claims.py`;
- the same for `eda8a35..dd94874` over `stats/` and `gates.py`.

`design/tokens.json`, `guidance_map_v1.csv` and `citations.yaml` are unchanged. `format.py` changed a comment only.

**Rerun block.** I ran the builder's `rerun.sh` in Git Bash and `rerun_r1.ps1` in PowerShell, both from `wtdd`, with `H` pointed at my scratch folder and the tr39 path made absolute. Every line equals the builder's `E9r1/rerun_bash.txt`, apart from paths, `run_id` and times. That includes repros6's trailing `FileNotFoundError ... pp-b4-...\pack\T8.html`, which the builder's output also carries.

| Command | Result (both shells unless noted) |
|---|---|
| doctor | exit 0, 17 `[ok` lines (PowerShell: `essential=1`) |
| tr39 `--check` | `vendored subset matches`, exit 0 |
| `--list` | 289 lines: 16 ap2, 34 day5, 112 day6, 25 day7, 87 day8, 15 day9 |
| no-licence `run` | exit 4, and `253938 bytes 20 keys 70 claims 0 rejections 3 refs [0, 1, 2, 2, 2, 3, 4, 5, None] CRLF 0 BOM False`. PowerShell shows `exit=-1` from the script's `Select-Object -First 3`; run on its own with `--templates T1,T7` it gives `exit=4` and `... then run again for T1.html, T7.html (docs: /docs/run)` |
| nomap | exit 3 H07, `dir=no` / `dir=False` |
| `licence show` | exit 4 (PowerShell `-1`, the same `Select-Object` cause) |
| `html_run` | `T8.html bytes 43961` |
| repros5 / repros6 | as r6 |
| p3 / p2 / p7 (Git Bash) / alias / offline / paths / imports | as the note, including `socket calls 0` and `imports ok; loaded: []` |
| verdict grep | `5 passed` |
| E6 schema | `1 passed` |
| k1 | `engine claims rejected: 0` and the same 15 `free_text accepted` texts; the PowerShell line is cut at 90 characters by the script |

**Day-9 sweep** (Git Bash, `wtmut`): `15 planted, 15 killed, 0 survived; 128 s`, equal to the note.

**Sample pack.** `scripts/build_sample_pack.py --out` gives run.json 236,843 / T1 139,999 / T7 47,808 / T8 35,178 bytes, equal to the note.

**100,000-row timing** (`make_criteria()`, B = 200):

| Where | Whole run | Three renders |
|---|---|---|
| Inside the Git Bash full suite | 4.04 s | 0.34 s |
| Alone, Git Bash | 4.53 s | 0.26 s |
| Alone, PowerShell | 4.54 s | 0.27 s |

T1 is 3,690,123 bytes in all three runs.

**Clustered CLI repro.** I ran the builder's `cli_clustered.py` (`--offline --templates T1,T7,T8`). Exit 0. Results:

- `Wilson score for proportions, DeLong for AUROC` appears 0 times;
- `bar interval: cluster bootstrap, percentile interval`;
- no bin-1 decile point;
- T1-10 `cluster bootstrap, percentile interval`; T1-11 `no interval method`;
- the X1 paragraph ends `no interval method (none, 105).`;
- T7 `verdict` 0, `effective` 0, `Josh` 0.

All equal to the note.

## Could not break

- **Lens-1 blockers, re-run on `dd94874`:**
  - RG-B1: the lens's own repro now prints `False` (the page has `150/150 convention` once).
  - RG-B2: `verdict` on the sample T7: `0`.
  - FA-B2: `Wilson score for proportions, DeLong for AUROC` and `Newcombe method 10 for proportions` on the clustered CLI T1: `0` and `0`.
  - FA-B3: the clustered bin-1 decile point: `[]`.
  - FA-B1 (T1 half): 0 page-grep hits on a derived-threshold T1.
- **Forbidden words across inputs:** E8's `FORBIDDEN_ON_PAGE` gives **0 hits** outside the exempt scopes on all 18 pages of N5 (6 documents × T1/T7/T8). On the same 18 pages, `Josh`, `open decision`, `Clopper-Pearson alongside` and `identical manifest hash` each occur 0 times.
- **Captions against their cells** (my own script resolving every `data-ref` in each table). On the clustered CLI T1:
  - each T1-10 caption names only `cluster bootstrap, percentile interval`, and its cells are `cluster_bootstrap_percentile` (15 / 9 / 12);
  - each T1-11 caption names `no interval method`, and its cells are `none` (9 / 3 / 6).

  The DEC-34 footnote says every interval in the calibration table is cluster-bootstrap. That table's cells are 6 `cluster_bootstrap_percentile` and 3 `none` (no interval), so the footnote is true.
- **Cells, with my own formatter.** It works from `Decimal(repr(x))` with half-even rounding and never imports `proofpack`. Matches: 114 of 114 compared cells on the sample T1 and 119 of 119 on the clustered T1, once U+2212 is used for negative three-decimal values (my first pass used an ASCII hyphen; those were the only 2 differences per page). Skipped: 22 and 17 (count and typed-reason cells).
- **Goldens.** `PROOFPACK_REGEN_GOLDEN=1` on the T1, T7 and T8 golden tests gave `3 passed`; `git diff --stat` then printed nothing (the files differ in line endings only).
- **Determinism.** Two sample-pack builds differ in `run.json` at exactly `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`. T1, T7 and T8 are identical after masking those three values and `run_id[:8]`. Masked occurrences: T1 `started` 10 and `rid8` 10; T7 4 and 4; T8 `run_id` 2, `started` 5, `duration_s` 1, `rid8` 4.
- **Footer mutants** (`templates/T1.html`):
  - page 9's footer removed: `5 failed` (golden, footer test, furniture, sample pack, helper test);
  - moved to page 1: `4 failed`.
- **Anchor-label mutants:**
  - the `FDA_AIDSF_SUBGROUP_PERF` row's status set to `final`: `9 failed`, including `test_every_fda_draft_anchor_is_labelled_in_every_margin_note` and the T8 anchor test;
  - `label_for` returning the title only: `9 failed`, including the same two and `test_a_map_row_without_the_qualifier_makes_t1_refuse`.
- **SVG-map mutants:**
  - `PlotMap.y` +1 unit: `4 failed` (F2, F3, F4 inversions and the golden);
  - `PlotMap.x` +1: `6 failed`;
  - `X0` 70→71, a consistent change: killed by the golden only, `1 failed` (RG-N4, carried).
- **Library against D4 section 8.** D4's `template_id` column has 55 ids; the library has 56. None is missing. The one extra is `SUBGROUP_ESTIMATE`, as lens 1 found. `all_skeletons()` returns 83 texts.
- **Wheel.** `python -m uv build --wheel --offline` ships `proofpack/_schema/conventions_T7.md` with the new text: `verdict` False, `Josh` False, `open decision` False, `DEC-18` True. Rendering the sample `run.json` from the unpacked wheel under `python -S`, with `PYTHONPATH` unset, printed `...whl/x\proofpack\__init__.py`. T1, T7 and T8 came out at 139,999 / 47,808 / 35,178 bytes, equal to the source-tree pages.
- **Conventions text against the decisions.** The new DEC-18, DEC-34 and DEC-35 sentences in `design/conventions_T7.md` match the decision rows:
  - DEC-18 (a) and (c): the constant stays at 2, the tier annotation stays;
  - DEC-34: no case-count floor;
  - DEC-35: the few-events tier stays on O:E and the fits, i.i.d. only.

  "No status is read from" z and p: `criteria.py` has no `p_value` or `z` read. `_figures.html` has no digit in any text node.
- **CI.** `pyproject.toml` declares `day9` (line 86). The CI step "pytest every declared day marker" reads the marker list from `pyproject.toml`.
- **Build-note corrections.** `notes/E9_build.md` line 3 now reads "Ten commits ... (corrected by repair 1, lens RG-N1)", and `git rev-list --count eda8a35..71b00d2` = 10. The last three commits each end with the `Co-Authored-By: Claude Opus 5.5` line.

## Could not check

- The day-8 sweep: not re-run, for time (about 25 minutes per shell).
- A wheel installed into a fresh venv: I used the unpacked wheel under `python -S` instead.
- Browser rendering of the changed SVG captions and footnotes.
- Whether the PowerShell k1 line matches past 90 characters: the builder's script cuts it there.
- A run with two operating points, or with `report_both_ways`: not made. F2 and F5 with several operating points were read in code only.

## Sentences I refused to write

- "Every repaired branch is pinned by a test." N2 lists two branches no test pins.
- "No page carries a certification word." The one hit on each page is `endorsed` inside the negated disclaimer sentence (N5).
- "The typed 200 is gone from the pack." It is gone from `_figures.html`, but still in `scope.LONG_FORM_ITEMS[6]` (N3).
