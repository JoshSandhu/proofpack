# Lens 4 (regression and record) - build day 9, lane E, repair 3 at `f72a9af` against `952bddc` - 2026-09-24

**Verdict: PASS. No blockers.** Lens 3's blocker FA-B1 no longer reproduces at `f72a9af`: on lens 3's own input, on the repairer's CLI input and on two documents I built with three operating points and 23 criteria rows, no F5 plot draws a criterion declared on another operating point, and each T1-11 prints exactly the criteria rows declared on its operating point or on none (20 printed, 20 expected, on each document; 48 printed at `952bddc`). The five tests in `tests/test_e9_repair3.py` each fail at `952bddc` on an assertion. The suite, marker and lint figures in the orchestrator's note (`workflows/notes-day9/E9_repair3.md`) are equal to mine in both shells. I raise seven non-blocking items: three are minor sentence violations (N1-N3).

Worktrees, all under `scratchpad/lens-E9-r4-regression/`, all removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wt-f72` | `f72a9af` | suite, markers, lint, timing, `--list`, the Git Bash day-9 sweep, the repro scripts |
| `wt-952` | `952bddc` | the pre-fix runs (new and edited test files copied in), my probe at the old commit, the sample pack at `952bddc` |
| `wtmut` | `f72a9af` | 14 planted mutants, the PowerShell day-9 sweep and timing |
| `wtgold` | `f72a9af` | golden regeneration, sample pack twice, the PowerShell repros |

In each worktree `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` before I used a figure from it. Every CLI or sample-pack run carried `--offline` or ran with `socket.socket` and `socket.create_connection` replaced by a function that raises: `socket calls 0` on every run. I committed nothing. The only file I wrote in the main tree is this note; `git status --short` in the main tree printed nothing before I wrote it, and HEAD was still `f72a9af`.

## Blockers

None.

## Non-blocking

**N1 (sentence_violation, minor) - the new test module's docstring points to E lines the repair note does not carry.** `tests/test_e9_repair3.py` line 4-5: "Every test below was run in a ``952bddc`` worktree with ``PYTHONPATH`` forced and failed there; the first ``E`` line of each is in the repair note." The first half is true (below). The repair note is the orchestrator's (the repairer's session ended first) and carries no `E` line: `grep -cE "^\s*E\s" workflows/notes-day9/E9_repair3.md` prints `0`. The lines exist only in the repairer's scratch file `scratchpad/E9r3/prefix_E.txt`, and my own pre-fix run reproduces each of them (below). Repro: the grep above.

**N2 (sentence_violation, minor) - "a row with no operating point (an ``auroc`` criterion ...)".** The comment in `render/t1.py::subgroup_blocks` and the commit message both describe a criteria row without an operating point as an `auroc` criterion. The class is wider: every threshold-free metric has no operating point under H09 (`io/declare.py` lines 453-469). Counter-example, run: criterion `Ce` (`metric: ece`, `operating_point` absent, scope sex = F, `<= 0.2`) in `probe_ops.py`. `criteria_results` row 14 is `('Ce', 'ece', None, 'not_assessable')`, and the F row of the sex T1-11 prints `Ce (row 14) → not assessable` under op1, op2 and op3. The behaviour is what the rule intends; the sentence names one member of the class as if it were the class. Repro: `python probe_ops.py <wt>` and read the sex F row.

**N3 (sentence_violation, minor) - test name `test_each_t1_11_prints_the_criteria_rows_of_its_own_operating_point_and_c5`.** Its regex reads only the tables with `data-attribute="sex"` and, in them, only the `F` row: 2 of the 6 T1-11 tables on its document (age, sex, site at op1 and op2). "each T1-11" says more than it reads. My probe reads every T1-11 on two documents (below), so the behaviour holds on what I fed; the name is the defect. A name that states what it reads: `..._the_sex_f_row_of_each_operating_points_t1_11_prints_its_own_rows_and_c5`.

**N4 (inherited, table twin of lens-3 FA-N1) - T1-13 still prints the threshold-free AUROC gap in rows labelled with an operating point.** Repair 3 moved the AUROC gap out of the operating-point clause in the `FAIRNESS_GAP` sentence. Table T1-13 on the two-op CLI T1 (`E9r2/twoop_cli.py` at `f72a9af`) prints, as plain text: `F op1 +7.0 [−7.9, +21.7] ... +0.079 [−0.002, +0.160] ...` and `F op2 +6.4 [−1.7, +15.8] ... +0.079 [−0.002, +0.160] ...` under the column heads `Level Op. Δ TPR ... Δ AUROC [95% CI]`. The sentence form also still prints the same gap twice, now labelled `AUROC gap (no operating point)`. Unchanged since `e17a510`; not in the note or in the E9 handoff's carried list. Repro: `python E9r2/twoop_cli.py <wt> <out>`, then read `T1-13` in `<out>/pack/T1.html`.

**N5 - one equivalent survivor of repair 3's F5 filter.** Replacing `and (None if row_op is None else str(row_op)) == op` with `and (row_op is None or str(row_op) == op)` fails only the two sweep-pattern tests (`test_sweep_day9.py`), which fail because the committed pattern no longer matches, not because behaviour changed. It is equivalent on declaration-valid input: H09 gives every threshold metric an operating point and no threshold-free one an operating point, so no threshold-metric row with `None` reaches the op1 plot. Record only.

**N6 - the note names no output change for S4 (DEC-43).** The note says "No stats/, gates, criteria, checker, schema, run.py, CLI or tokens.json change", and each of those is true (below). It names none of the output changes, and the E9 handoff's figures are now stale:
- sample-pack `T7.html` is **47,666** bytes at `f72a9af` (47,830 at `952bddc`); `T1.html` 142,924, `T8.html` 35,178 and `run.json` content are unchanged (run.json 236,842 / 236,843 bytes differ only in the three volatile manifest values);
- every T1 with a fairness declaration prints the new `FAIRNESS_GAP` text; `templates.LIBRARY["FAIRNESS_GAP"].skeleton` changed;
- on a run whose criteria name more than one operating point, T1-11 prints fewer criteria rows and F5 draws fewer lines (48 -> 20 rows and 7 -> 2 lines on my first document);
- `proofpack/_schema/conventions_T7.md` (force-included from `design/conventions_T7.md`, `pyproject.toml` line 60) loses the z/p sentence on every T7;
- `render.figures._criterion_lines` gains an `op` parameter (private).
`proofpack-site` at `02c42b8` greps for none of `FAIRNESS_GAP`, `AUROC gap`, `two-sided p`, `_criterion_lines`, `subgroup_blocks`, `47830`, `142924` or `conventions_T7`; it still pins `a0c9abc` (`ci.yml` line 18, `deploy.yml` line 31).

**N7 - F5 draws no line for a criterion declared on a second operating point, and the page does not say so (carried row 100, more exposed).** Before repair 3 an op2 criterion was drawn on the op1 plot (the blocker). Now it is drawn on no plot: on lens 3's input `F5 C3 line count: 0`, and on my probe `Cb` (op2) and `Cc` (op2) appear on no F5 figure. F5 still draws the first operating point only, and no caption or line states that the op2 forest and its criterion lines are not drawn. This is the carried scope limit (row 100, open question 4), not a repair-3 defect.

## Measured against the note

**Suite** (`PROOFPACK_TR39_FULL` set, `wt-f72`):

| Command | Git Bash | PowerShell 5.1 | Note (Git Bash) |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | `1411 passed, 1 skipped, 1 xfailed in 150.06s` | `1411 passed, 1 skipped, 1 xfailed in 149.33s` | `1411 passed, 1 skipped, 1 xfailed (106 s)` |
| `-m day9` | `155 passed` | `155 passed` | `155 passed` |
| `-m day8` / `day7` / `day6` / `day5` / `ap2` | `468` / `139` / `285` / `54` / `88 passed` | the same five | - |
| `--collect-only -m` the same six | `155` / `468` / `139` / `285` / `54` / `88` of `1413` | the same | - |
| `python -m ruff check .` / `ruff format --check .` | `All checks passed!` / `195 files already formatted` | the same | the same |

Without `PROOFPACK_TR39_FULL` the first Git Bash run gave `1410 passed, 2 skipped, 1 xfailed`; the second skip is `test_e8_repair4.py:405` (full `confusables.txt` not present). The other skip in both runs is `test_doctor_cli.py:57` (write access cannot be revoked for this user).

- `day5` 54, `day6` 285, `day7` 139, `day8` 468 and `ap2` 88 equal the counts collected at `eda8a35`.
- `day9` 155 = lens 3's 150 + the 5 tests of `test_e9_repair3.py`; 1411 = 1406 + 5.
- `day9` is declared in `pyproject.toml`; the CI step "pytest (all markers)" reads the marker list from `pyproject.toml` (`.github/workflows/ci.yml` lines 28-46).

**100,000-row timing** (the day-9 timing test, `-s`): Git Bash `run --templates T1,T7,T8 5.11 s; T1+T7+T8 renders from run.json 0.28 s; T1 3693048 bytes`; PowerShell `4.40 s; 0.26 s; T1 3693048 bytes`. T1's size equals lens 3's and the E9 handoff's.

**Pre-fix.** I copied `tests/test_e9_repair3.py` alone into `wt-952` (with `952bddc`'s own `test_e9_repair2.py` in place): **`5 failed`**, each on an assertion, none on an import or attribute. The first `E` line of each:
- `assert {'F5-sex-sens...01-01): 0.5']} == ...`, differing item `'F5-sex-sensitivity': ['customer criterion C3 (A, 2026-01-01): 0.7', 'customer criterion C4 (A, 2026-01-01): 0.6']`;
- `assert {'op1': [('C3...on not met')]} == {'op1': [('C4...on not met')]}`: at `952bddc` op1 and op2 each print C3, C4, C5 and both `fairness:tpr_gap` rows (4 and 5);
- `assert ['For F versu...02, +0.160].'] == ...`, index 0 `'For F versus M at operating point op1: TPR gap +7.0 ...'`;
- `assert 'written to ...n beside the' not in '<!DOCTYPE h...'`;
- `assert 'state_what_they_inspect' not in '"""Build da...'`.
Each equals the repairer's `scratchpad/E9r3/prefix_E.txt`. With the edited `test_e9_repair2.py` and `test_e9_templates.py` copied in as well: `7 failed, 84 passed` - the four behavioural repair-3 tests, the two edited repair-2 tests and the `[fairness_gap]` skeleton case. (In that run the fifth repair-3 test passes, because it reads the copied-in `test_e9_repair2.py`; run alone it fails, as above.)

**Nothing weakened.**
- `git diff --name-status 952bddc f72a9af -- tests/`: `M` both goldens, `test_e9_repair2.py`, `test_e9_templates.py`; `A` `test_e9_repair3.py`. No `D`.
- The only skip/xfail/`.only`/todo/marker line added or removed in `tests/` and `scripts/` is `+pytestmark = pytest.mark.day9`.
- The edits to existing tests: the two-op test's `FAIRNESS_GAP` expectation moved to the new text; the z/p test now asserts the sentence absent (it asserted it present); one test renamed with its body unchanged; one skeleton expectation. The golden diff is 1 line in T1 (CL-0061) and 1 line in T7 (the conventions paragraph).

**No statistics.** Each printed nothing:
- `git diff --name-status 952bddc f72a9af -- src/proofpack/stats/ src/proofpack/gates.py`;
- `git diff --stat 952bddc f72a9af` over `cli.py`, `run.py`, `schema/`, `criteria.py`, `narrate/checker.py`, `narrate/claims.py`, `egress/`, `io/`, `render/format.py`, `manifest.py`, `licence/`, `design/tokens.json`, `design/guidance_map_v1.csv`, `pyproject.toml`, `uv.lock`, `.github`;
- `git diff --stat eda8a35 f72a9af -- src/proofpack/stats/ src/proofpack/gates.py src/proofpack/criteria.py design/tokens.json`.
Two sample-pack builds, one at each commit, give `run.json` files that differ only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`.

**Sweep.** `python scripts/mutation_sweep.py --list`: 291 lines in both shells, `ap2` 16, `day5` 34, `day6` 112, `day7` 25, `day8` 87, `day9` **17**, as the commit message says; the two new rows are `f5_criterion_line_for_any_operating_point` and `t1_11_criteria_for_any_operating_point`. `--marker day9`: Git Bash `17 planted, 17 killed, 0 survived; 194 s`, exit 0; PowerShell the same line, exit 0. The two new mutants are killed with `1 failed, 18 passed` and `1 failed, 19 passed`.

## What I could not break

- **Lens-3 FA-B1 (the blocker), four inputs, both shells.**
  - Lens 3's input (`scratchpad/E9handoff/b1_repro.py`): `criteria_results [('C3', {... 'F'}, 'op2', 'met')]`, `F5 C3 line count: 0`, `T1-11 plain 'C3 (row 1)': 1 ['C3 (row 1) → criterion met']` (op2's table only), `F5 caption op: op1`. The E9 handoff records the same script at `e17a510` printing a line count of 1 and 2 T1-11 hits; I did not re-run it there.
  - The repairer's CLI input (`E9r3/fab1_cli.py`, C3 on op2 with `level: "*"`, `--offline`, sockets refused): `rc 0 socket calls 0`, `F5 criterion labels: []`, `T1-11 op1 [fairness:tpr_gap row 3]`, `T1-11 op2 [C3 row 1, fairness:tpr_gap row 4]`. Byte-identical (after the first line) to the repairer's `fab1_main.txt`, and PowerShell equals Git Bash.
  - My own probe (`probe_ops.py`, reads `run.json`'s `criteria_results` and does not call render code other than `render_t1`): `CRITERIA` + `FAIRNESS` + nine criteria on op1, op2, op3 and none (`Ca`-`Ci`: sensitivity, specificity, auroc, ece, point-estimate, scope `sex = F`, `sex = *`, `site = *`, `age = 0-40`), 23 criteria rows. For every T1-11 row it compares the printed `(id, row, status)` set with the rows whose scope is that attribute and level and whose `operating_point` is the table's `data-op` or null; for every F5 figure it compares the drawn criterion ids with the `ci_lower_bound` rows on that attribute and metric at the plotted operating point (null for AUROC). Declaration order op1, op2, op3: `T1-11 printed 20 expected 20 F5 lines 2 defects 0`. Order op3, op1, op2 (F5 then plots op3): `printed 20 expected 20 F5 lines 3 defects 0`. At `952bddc`: `printed 48 expected 20 F5 lines 7 defects 48` and `defects 46`.
  - Every status printed equals `criteria_results[row - 1].status` (the probe checks the id at that position too).
- **My mutants of repair 3's code** (`wtmut`, each against `-m "day9 and not slow"`, restored after each):

  | Mutant | Result |
  |---|---|
  | F5 op filter line deleted | `3 failed` (`test_an_op2_criterion_draws_no_line_on_the_op1_f5_plot` + the two sweep-pattern tests) |
  | F5 AUROC plot bound to `overall_op` | `1 failed` (the same F5 test: C5 undrawn) |
  | F5 filter rewritten to `row_op is None or ...` | 2 failed, sweep-pattern tests only (N5, equivalent) |
  | T1-11 op filter line deleted | `3 failed` (`test_each_t1_11_...` + the two sweep-pattern tests) |
  | T1-11 rows without an operating point dropped | `3 failed` (the same) |
  | T1-11 bound to the first operating point | `3 failed` (the same) |
  | `FAIRNESS_GAP` reverted to repair 2's text | `4 failed` (two-op test, repair-3 gap test, skeleton case, T1 golden) |
  | `(no operating point)` label dropped | `3 failed` |
  | T7 z/p sentence restored in `conventions_T7.md` | `3 failed` (repair-2 and repair-3 T7 tests, T7 golden) |
  | lens-3 FA-N4 survivor `f5_caption_last_op` | **killed now**, `1 failed` (`test_an_op2_criterion_draws_no_line_on_the_op1_f5_plot`); it survived at `e17a510` (`616 passed`) |

- **Footer, anchor and SVG mutants** (`wtmut`):
  - the last `{{ page_footer() }}` removed from `templates/T1.html`: `5 failed` - `test_the_footer_is_on_every_page_and_once_in_print`, `test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant`, `test_each_furniture_element_is_on_t1_and_t8`, the T1 golden, `test_every_page_of_every_document_is_marked_synthetic`;
  - the `FDA_AIDSF_SUBGROUP_PERF` row's status `draft - not for implementation` set to `final` in `guidance_map_v1.csv`: `4 failed` - `test_every_fda_draft_anchor_is_labelled_in_every_margin_note`, `test_every_caption_repeats_n_the_interval_method_and_the_anchor`, both goldens;
  - `PlotMap.y` + 1 unit: `6 failed` (the F2, F3 and F4 inversion tests, the T1 golden, the two sweep-pattern tests);
  - `PlotMap.x` + 1 unit: `6 failed` (F2, F3, F4 inversion, both F5 tests, the T1 golden).
- **Goldens.** `PROOFPACK_REGEN_GOLDEN=1` on the three golden tests in `wtgold`: `3 passed`; `git diff --stat` printed nothing, and the LF-normalised md5 of each regenerated file equals the committed one (T1 `cf3081f2...`, T7 `2dfdb6c8...`, T8 `ddfc6250...`). I restored the working files.
- **Sample pack and masking** (`scripts/build_sample_pack.py --out`, sockets refused, `exit 0`, `socket calls 0`, twice at `f72a9af`). `run.json` differs only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`. Masking exactly those (the full `run_id`, its first 8 characters, `started`, and T8's `Duration (s)` cell) makes T1, T7 and T8 identical. Occurrences masked: T1 `run_id` 1, `rid8` 10, `started` 10; T7 4 and 4; T8 `run_id` 2, `rid8` 4, `started` 5, `Duration (s)` 1. Each page carries `SYNTHETIC - illustrative` and `NO LICENCE - not for submission` (T1 12 and 11, T7 5 and 5, T8 7 and 7) and one footer per page (9 / 3 / 3); T7 carries 18 `[unverified]` beside 18 `pending verification`.
- **Lens-3 sentence items at `f72a9af`.**
  - FA-N1: on the two-op CLI T1 both `FAIRNESS_GAP` sentences read `...; AUROC gap (no operating point) +0.079 [−0.002, +0.160].` (both shells); on a `y_pred`-only run with `FAIRNESS` it reads `AUROC gap (no operating point) n.e. (not_computed_this_run) [no interval]`, and on the clustered run each gap prints `n.e. (cases_span_both_groups) [no interval]`.
  - FA-N3: `z and the two-sided p` and `beside the difference` occur 0 times on the i.i.d., clustered, `y_pred`-only and sample-pack T7s. The only remaining z/p text in `src` and `design` is in `stats/discrimination.py` docstrings.
  - FA-N2 = RG-N1: `state_what_they_inspect` occurs 0 times in `tests/test_e9_repair2.py`.
- **Library against D4 section 8.** Parsing the section-8 table of `D4_pack_templates.md` gives 55 ids; `templates.LIBRARY` has 56; missing from the library: none; extra: `SUBGROUP_ESTIMATE` (the recorded engine addition). `all_skeletons()` returns 83 texts. `test_claims.py` lines 317 and 325 compare the schema enum to `list(templates.LIBRARY)` and to the id set of `all_skeletons()`.
- **Forbidden words and anchors** on T1, T7 and T8 of the two-op CLI pack and the sample pack, outside `.status`, `.disclaimer` and `.customer-text` (`FORBIDDEN_ON_PAGE` ∪ the checker's `VERDICT_WORDS` and `CERTIFICATION_WORDS` ∪ the brief's words, 51 in all): the only hits are `endorsed` 1 per page (the cover-note negation, carried row 116) and `guarantee` 2 on T7 ("not a guarantee"). `FDA_AIDSF_*` anchors carrying "draft guidance (January 2025), not for implementation": T1 27/27, T7 3/3, T8 6/6 on both packs. The two-op T1 keeps its one `[unverified]` (impossibility statement) and the two-op T7 its 21.

## What I could not check

- The day-8 sweep (about 25 minutes per shell). Repair 3 touches no day-8 code path (`git diff --stat 952bddc f72a9af` over `checker.py`, `claims.py`, `egress/`, `run.py`, `cli.py` is 0 lines), so the carried row 106 stays open as it was.
- A wheel installed into a fresh venv at `f72a9af`. I read that `design/conventions_T7.md` is force-included as `proofpack/_schema/conventions_T7.md` (`pyproject.toml` line 60), so the wheel carries the edited file; I did not build it.
- Browser rendering of the longer `FAIRNESS_GAP` sentence.
- Whether the repairer measured anything its note does not record: the scratch folder `E9r3/` carries `rerun_bash.txt`, `rerun_ps.txt`, `sweep_day9.txt` and `mutants_out.txt`, which I read but did not re-derive line by line; my own runs above replace them.

## Cut and carried, against what I measured

The note carries nothing (it is the orchestrator's). Against the E9 handoff's carried rows at `952bddc`:
- **Closed by repair 3:** row 93 (FA-B1), row 94 (FA-N1, sentence form; see N4 for the table form), row 95 (FA-N2 = RG-N1), row 96 (FA-N3 = RG-N3), row 97 (FA-N4: `f5_caption_last_op` now killed).
- **Partly closed:** row 105 (DEC-12 (ii)): the day-9 list is 17 with two repair-3 mutants; repairs 1 and 2 still have none.
- **Still open, measured or unchanged:** rows 98, 99, 101, 102, 106, 108-120; row 100 more exposed (N7); row 110 (T1-11 skips the reference level's criterion row): on the repairer's CLI input `C3` on `sex = M` (row 2, the reference level) is printed in no T1-11.
- **Open and not listed anywhere:** N4 (T1-13's Δ AUROC in rows labelled op1 / op2; the sentence prints the gap twice) and N6 (the S4 list and the stale T7 size).

## Sentences I refused to write

- "Every criterion is now attached to the right operating point." Written instead: on four named inputs, each T1-11 prints the rows my probe expects (20 of 20) and no F5 figure draws a row from another operating point.
- "Every test in the repair fails before the fix." Written instead: the five tests of `test_e9_repair3.py`, run alone at `952bddc`, give `5 failed`; the edited repair-2 test that is only renamed passes there.
- "S4 has nothing to move." N6 lists what changed on the page.
- "The F5 filter has no surviving mutant." N5 survives; I call it equivalent on declaration-valid input for the reason given, not because a test reads it.
