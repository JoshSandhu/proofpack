# Lens 2 (fresh attack) - build day 9, lane E, at `dd94874` - 2026-09-23

**Verdict: FAIL.** One blocker:

- **B1.** On a run with two operating points, T1 prints 92 claim sentences that are bound to one operating point and do not name it. The same subgroup and metric then appear twice on the page with different numbers. Example: "For age = 0-40, sensitivity was 30/38 ..." and "For age = 0-40, sensitivity was 36/38 ...". A reader cannot tell which figure belongs to which operating point.

B1 was already in the build at `71b00d2`; repair 1 did not introduce it. Lens 1 recorded that it made no run with two operating points. No E9 test feeds one: `op2` appears in none of `test_render_t1.py`, `test_e9_*.py`, `test_render_figures.py` or `test_sample_pack.py`.

Every blocker lens 1 raised (FA-B1, FA-B2, FA-B3, RG-B1, RG-B2) is closed. I reproduced each lens-1 repro at `dd94874` and none reproduces. The figures are in "What I could not break".

Repair 1 also left the following, each graded record-and-carry:

- three new false sentences (N1, N2, N3);
- a module docstring that one of its own tests contradicts (N4);
- seven surviving mutants of mine, five of them non-equivalent (N5).

**Worktrees.** All under `scratchpad/lens-E9-r2-fresh-attack/`, all now removed:

- `wt` at `dd94874`: suite, markers, lint, probes, day-9 sweep;
- `wt0` at `71b00d2`: pre-fix runs and the run.json comparison;
- `wtmut` at `dd94874`: my mutants.

In each worktree `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` before I used any figure from it.

Every run outside pytest carried `--offline`, or ran with `socket.socket` / `create_connection` replaced by a function that raises. I committed nothing. The only file I wrote in the main tree is this note.

## Blockers

### B1 - a two-operating-point T1 prints sentences that do not name their operating point, with different numbers under the same words

**The input.** I ran `proofpack run --offline --templates T1,T7,T8` (exit 0) on `cohort_with_a_thirty_row_site()` with `CRITERIA` + `FAIRNESS`, and appended a second operating point `{"id": "op2", "threshold": 0.3, "rule": ">=", "provenance": "prespecified_sap"}`. The script is `scratchpad/lens-E9-r2-fresh-attack/twoop_cli.py`.

**What T1 prints.** Section 9 prints its narrative after both operating points' tables. Verbatim from the CLI's `T1.html`:

```
For age = 0-40, sensitivity was 30/38 (78.9%ᶜ) [63.7, 88.9], a difference of +0.6 percentage points [−17.8, +19.1] versus 40-65.
For age = 0-40, sensitivity was 36/38 (94.7%) [82.7, 98.5], a difference of +2.8 percentage points [−10.3, +16.6] versus 40-65.
```

Section 10 does the same for the fairness gaps:

```
For F versus M: TPR gap +7.0 [−7.9, +21.7], FPR gap −4.8 [−14.8, +5.4], PPV gap +8.9 [−6.2, +23.3], AUROC gap +0.079 [−0.002, +0.160].
For F versus M: TPR gap +6.4 [−1.7, +15.8], FPR gap −1.3 [−13.0, +10.4], PPV gap +4.2 [−7.7, +15.8], AUROC gap +0.079 [−0.002, +0.160].
```

**Where each sentence comes from.** The first sentence of each pair comes from `/subgroups/0/metrics/op1/...` (CL-0028) and `/fairness/gaps/0/operating_points/op1/...` (CL-0119). The second comes from `.../op2/...` (CL-0028's op2 twin, and CL-0120).

**How many.** On that page I counted the claim sentences whose claim carries an `operating_point` that the sentence text does not contain: `SUBGROUP_ESTIMATE_WITH_DIFF` 60, `SUBGROUP_ESTIMATE` 30, `FAIRNESS_GAP` 2. `OVERALL_ESTIMATE` names its operating point in the sentence and is unaffected.

**Why it is a blocker.** The page states two different sensitivities, and two different TPR gaps, for one described population. The fairness criterion `fairness:tpr_gap` is assessed at `op1`, and the sentence that prints the `op2` gap reads identically to it. A number reaches the page under a label that does not identify it. The tables do label it (T1-10 captions "at operating point op1" / "op2"; the T1-13 `Op.` column; T1-18 "sensitivity (op1)"). The sentences do not.

**What E9 inherits and what it adds.** The skeletons are D4 section 8 verbatim: `SUBGROUP_ESTIMATE_WITH_DIFF` and `FAIRNESS_GAP` have no `{op_id}` slot. The placement is E9's: `T1.html` puts every attribute's sentences for all operating points after the last operating point's tables. At `71b00d2` the same page carries the same two pairs: the `F versus` sentence occurs 2 times in both `docs0/two_T1.html` and `docs/two_T1.html`.

**Repro:** `PYTHONPATH=<wt>/src python twoop_cli.py <dir>` prints `rc 0` and the four sentences above. Equivalently, in `tests/`: `assemble(cohort_with_a_thirty_row_site(), crit)` with `crit["operating_points"].append({... "id": "op2" ...})`, then `render_t1`. Grep `<p class="claim"` for `For <span class="customer-text inline">F</span> versus`: it gives 2 matches with different TPR gaps.

## Non-blocking (record-and-carry)

- **N1 (sentence_violation, new in repair 1) - T7 prints "z and the two-sided p are printed as detail, and no status is read from them".** This is from `design/conventions_T7.md`, reworded by repair 1 from "are detail, never a verdict".
  - The AUROC-difference `z` and `p_value` sit in `run.json` at `subgroups[i].diff_vs_reference.auroc.detail`. On the i.i.d. document that holds 15 of them.
  - I searched T1, T7 and T8 for each value at 3 dp. There were 12 value hits. Each is a coincidental match: a decile mean, an interval bound or an AUROC cell. None sits beside a `z` or `p`.
  - T1's only printed `p =` values are the `chi2_homogeneity` p-values in the heterogeneity footnote.
  - So the sentence is true only if "printed" means "written to `run.json`".

  Repro: `grep -c "two-sided" T1.html T8.html` gives 0 and 0; `grep -o "z and the two-sided p are printed" T7.html` gives 1.
- **N2 (sentence_violation, rewritten by repair 1) - T7 section 5 prints "No target is compared to and no word describes the calibration."**
  - The criteria schema's `metric_id` enum admits `calibration_slope`, `oe`, `brier`, `ipa` and `ece`.
  - I declared `_criterion(id="C_slope", metric="calibration_slope", operating_point=None, value=0.8)`. T1 section 12 then prints `C_slope ... 1.349 [1.056, 1.642] ... criterion met`, and the claim reads "Criterion C_slope (calibration slope, overall, CI lower bound >= 0.8; A, 2026-01-01): observed 1.349 [1.056, 1.642] - criterion met.".
  - T7 of the same document prints the sentence (`True`). A target is compared to the calibration slope in the same pack.
  - `C_oe` (`ci_upper_bound` <= 1.3) and `C_brier` (`point_estimate` <= 0.3) are also `met` / `statistic_compared`.

  The sentence is true of `stats.calibration` alone. As printed, it is not true of the pack.
- **N3 (sentence_violation) - the test name `test_t7_iid_and_clustered_carry_no_forbidden_word_and_no_internal_decision_text`.** It asserts only that `Josh`, `open decision` and the old intro sentence are absent.
  - The i.i.d. T7 it renders still prints `DEC-08`, `DEC-09`, `DEC-10`, `DEC-18`, `DEC-34` and `DEC-35` (11 occurrences; 14 on the clustered T7). It also prints "repair round 1 of build day 6" (2), "Lens 2" / "lens 1" / "lens 2" (5), three pytest ids and `scripts/coverage_calibration.py`.
  - The note carries this as FA-N1 residue. The test name claims more than the test inspects.
- **N4 (sentence_violation; graded record-and-carry, see below) - the `tests/test_e9_repair1.py` module docstring says "each fails at `71b00d2`".**
  - I copied the six new or edited test files into `wt0` at `71b00d2` with `PYTHONPATH` forced. Result: `14 failed, 131 passed`. Ten of the eleven `test_e9_repair1.py` tests fail.
  - `test_the_footer_helper_counts_per_page_and_refuses_the_lens_mutant` **passes at `71b00d2`**. It tests the new helper on a hand-built mutant, and RG-N3 was a test weakness with no code defect to fail against. The repairer's own pre-fix evidence for RG-N3 (the mutant planted in `71b00d2`'s `T1.html`) is sound.
  - The attacks block's literal rule makes "a test that passes at 71b00d2" a blocker. I did not apply it here because no product code at `71b00d2` is defective in this respect. Josh may overrule that grading.
- **N5 - my mutants against the repair code** (`wtmut`, 27 planted over the eight render/CLI test files, `-x`):

  | Result | Mutants |
  |---|---|
  | Killed (18) | `f2_or_instead_of_and`, `f2_npa_always`, `f4_has_interval_dropped`, `f4_not_drawn_clause_dropped`, `f4_flag_short_reads_events`, `f5_ref_check_dropped`, `f4_bar_method_from_all_bins`, `t1_table_methods_no_auroc`, `t1_diff_methods_no_auroc` (golden only), `t7_x1_reference_only`, `cli_next_step_first_template`, `f2_typed_prints_both`, `thresh_phrase_reverted`, `cp_clause_restored`, `x1_methods_dropped` (T7 golden only), `tolerance_f17_restored`, `f4_flag_short_typed_200`, `f2_typed_caption_dropped` |
  | Malformed (2) | `f5_no_ref_caption_dropped` and `f5_no_ref_caption_says_line`: my substitutions were syntax errors (`1 error` at collection), so neither counts; the F5 caption is asserted by `test_f5_draws_no_reference_line_and_f2_no_marker_for_a_typed_reason` in any case |
  | Survived (7) | Listed below; each gave `182 passed` |

  The seven survivors:

  - `f2_sp_check_dropped`: `if not fmt.has_interval(se_num):`. With a typed-reason specificity that carries `est`, the F2 marker is drawn at that `est`. Non-equivalent. The test plants a typed sensitivity only.
  - `ipa_footnote_unconditional`: `{% if true %}The IPA row` inside the outer `ipa_tiers or clustered` guard. On a clustered run whose IPA row has no tier, it prints "The IPA row's tier superscript () ...", which is exactly lens 1's N13. Non-equivalent. The repair's test feeds the i.i.d. document only.
  - `f5_desc_always_dashed`: the SVG `<desc>` says "the dashed line is the overall estimate" when no line is drawn. Non-equivalent.
  - `cli_json_next_step_T8`: the `--format json` next-step line always names `T8.html`. Non-equivalent. Only the exit-4 line is tested.
  - `t1_table_methods_without_overall`: the T1-10 caption omits the Overall row's methods. It is non-equivalent only if the Overall row carries a method that no level row carries. I did not construct such a run.
  - `method_list_default_phrase`: an unmapped method prints as "Wilson score". The note's rule "an id missing from the map prints as the id" is pinned by no test. Equivalent on every engine method I saw.
  - `t7_printed_numbers_includes_analytic`: equivalent. `printed_numbers` yields only `node["number"]`, and an `analytic` Number has no `number` key.
- **N6 (sentence_violation, minor) - the next-step line under `--format json` without a licence.** For `--templates T7 --format json` it prints "Next step: proofpack licence install FILE, then run again for T7.html". The same flags after an install still write no HTML: my `jsononly` run with a licence exits 0 with no HTML file. The line omits `--format json,html`.
- **N7 (sentence, minor) - F4's caption when every bin has a typed reason** reads "bar interval: no Number printed; not drawn, no interval: bin 1 n.e. (boundary_estimate), ...". Numbers are printed: the n.e. lines in the same caption, and the decile table. `method_list`'s empty value is the source.
- **N8 - a `sensitivity` that is null** (constructed: `overall.op1.sensitivity = None` on a `reference_standard` run). F2's caption then prints "op1 (ppa n.e.)", because the key choice falls through to `ppa`. I found no engine path that writes a null overall sensitivity.
- **N9 - a day-7 test depends on another workflow's working tree.** My first `-m day7` run gave `1 failed, 138 passed`. The failure was `test_licence.py::test_the_shipped_key_is_the_site_s_live_key_by_bytes_and_the_published_copy_is_the_same`: `proofpack-site/keys/licence_pub.json` then held `public_key` `eS5b0/73atQaGdJoHTrlAPWOpXimdSd4BD98dr7LCkY=`.
  - A read a few minutes later showed the committed `XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA=`, and the re-run gave `139 passed`.
  - Lane S's lens (untracked `handoffs/2026-09-23_S_lens2_*.md` there) was working in that tree at the time.
  - The engine suite's result depends on the site repo's uncommitted state.
- **Carried from lens 1 and re-measured unchanged:**
  - FA-N5, exact-half rounding: the clustered T1 prints "For sex = F, PPV was 51/80 (63.7%)".
  - FA-N7: T1-11 skips the reference-level row of a `level: "*"` criterion. With three `C1` rows it prints rows 4 and 5, not row 3.
  - FA-N8: U+2028 / U+200B are carried raw, 32 times on T1 in my injection probe.
  - FA-N9: T1's `<h1>` has no draft label.

## What I could not break (with figures)

**Suite and lint** (in `wt`, `PROOFPACK_TR39_FULL` set):

- Full suite: Git Bash `1399 passed, 1 skipped, 1 xfailed in 112.05s`; PowerShell 5.1 `1399 passed, 1 skipped, 1 xfailed in 105.32s`. Both equal the note's count.
- Markers:
  - `day9` 143 in both shells;
  - `day8` 468; `day7` 139 (on the re-run, N9); `day6` 285; `day5` 54; `ap2` 88;
  - `day4` 182; `day3` 29 + 1 xfailed; `day2` 40; `day1` 59 + 1 skipped.
- `ruff check`: `All checks passed!`; `ruff format --check`: `188 files already formatted`.
- `doctor --offline`: exit 0, 17 `[ok` lines.
- tr39 `--check`: `vendored subset matches`.
- `mutation_sweep.py --list`: 289 lines.
- `--marker day9` sweep: `15 planted, 15 killed, 0 survived; 133 s`.

**No statistics changed.** `git diff --stat 71b00d2 dd94874` over `stats/`, `gates.py`, `criteria.py`, `egress/`, `narrate/checker.py`, `narrate/claims.py`, `io/`, `schema/` and `design/tokens.json` is empty; from `eda8a35` over `stats/`, `gates.py`, `criteria.py`, `egress/`, `checker.py` and `tokens.json` it is also empty. I generated `run.json` at `71b00d2` and at `dd94874` from five inputs (i.i.d., clustered 400 rows, comparator, logit, two operating points). The five pairs are byte-identical.

**Lens-1 blockers, re-run at `dd94874`:**

- **FA-B1 / RG-B2.** I grepped with `checker.VERDICT_WORDS | FORBIDDEN_ON_PAGE | CERTIFICATION_WORDS` plus `robust reliable equitable demonstrates validated clinically bias guarantee ensures well valid`, and the phrases `model is`, `performs well`, `no evidence of bias`, `well calibrated`, over T1 / T7 / T8 of six documents (i.i.d., clustered, comparator, logit, two-op, y_pred-only) and the sample pack. Outside `.status` / `.disclaimer` / `.customer-text` the only hits are:
  - `endorsed` in the D4 1.5 cover note "No regulator has endorsed this tool";
  - `guarantee` in "none of them is a guarantee" / "not a guarantee";
  - `valid` in "valid clinical association" (T8, E8's D4 7.2 text) and in a T7 conventions sentence on i.i.d. intervals;
  - `well` in "as well as".

  None is a verdict about the model. `verdict`, `effective` and `biased` give 0 hits on every page, including the derived-threshold T1 and the two-op T1 (whose `op2` is derived). In `title` / `aria-label` / `alt` / `data-*` attribute values, the only forbidden-word hit is T8's `data-count="criteria_met"` (E8), a key name.
- **FA-B2.** On all six documents I resolved every `data-ref` in every T1-10 and T1-11 table to its Number and built the expected caption from `METHOD_PHRASES`. Mismatches: 0.
  - T7's methods table equals my walk of every Number in `run.json`. i.i.d.: `wilson` 135, `newcombe10` 192, `delong_wald` 45, `delong_logit` 7, `irls_wald` 6, `log_delta` 5, `bootstrap_percentile` 11, `none` 17. Clustered: `cluster_bootstrap_percentile` 95, `none` 310.
  - T7's X1 counts equal a walk of `diff_vs_reference` / `diff_vs_complement` without `analytic`: i.i.d. `delong_wald` 15, `newcombe10` 90; clustered `none` 105; y_pred `newcombe10` 90, `none` 15; logit 13 / 90 / 2; two-op 15 / 180.
- **FA-B3.** Each constructed typed Number was named and not plotted:
  - F4 bin 3 typed: no point and no bar; the caption names "bin 3 n.e. (boundary_estimate)".
  - All bins typed: 0 points.
  - Two-op doc with `op1.sensitivity` typed: F2 draws only `op2`, and the caption names "op1 (sensitivity n.e. (boundary_estimate))".
  - F5 with the overall sensitivity typed: no reference line, and the caption reads "no reference line: the overall estimate is n.e. (boundary_estimate)". The typed level row prints `n.e. (boundary_estimate)ᶜ` and is not drawn.
- **RG-B1.** `minimum` 150 prints "150/150 convention ..."; `minimum` True prints no line.

**Table cells.** My own D4 1.2 formatter works from `Decimal(repr(x))`, half-even, U+2212, the tier map and the `n.e.` rule, and never imports `render.format`. It compared **902** `data-ref` cells on T1 and T8 of six documents. The only mismatches are the 6 intended `/overall/threshold_free/auprc` "not computed in this run (v1.1)" cells, one per document. Among the 902 are signed differences at 0 (`0.000 [−0.122, +0.123]`), negative differences and typed-reason cells.

**Anchors.** Every `<a href="#FDA_AIDSF_*">` carries "draft guidance (January 2025), not for implementation": T1 27/27, T7 3/3, and T8 6/6 (5/5 on y_pred) on every document. The guidance-table rows carry it too.

**Injection** through the repaired paths. I planted `<script>…</script><img src=x onerror=1>{{ 7*7 }}{% raw %}` + U+202E U+2028 U+200B + 10,000 `A` as:

- a typed reason on the overall sensitivity and AUROC;
- a subgroup AUROC `method`;
- a difference `method`;
- a decile `method` and a decile reason;
- the `curve_flag.note`.

Result: T1 and T7 have 0 raw `<script`, 0 raw `<img`, and no `on*` attribute (via `html.parser`). `{{ 7*7 }}` stays literal (T1 32, T7 4). U+202E appears only as `&#x202e;`. The 10k string is kept (32 / 4). `[unverified] planted-customer` / `planted-source` survive on T1 (2 / 2). T7 carries 21 `[unverified]` beside 21 "citation pending verification" (i.i.d.).

**Watermarks and footers** (CLI, `--offline`, sockets refused, 0 socket calls):

| Licence state | Result |
|---|---|
| ok | exit 0; T1 9 pages, T7 3, T8 3; one `page-footer` in every page |
| grace | `LICENCE EXPIRED - not for submission` on every page of all three |
| trial | `TRIAL` on every page |
| expired past grace | exit 4, `run.json` only |
| no licence | exit 4, `NO LICENCE - not for submission` |
| refused file | exit 4, `LICENCE EXPIRED - not for submission` |

`--templates T9` gives `error: unknown --templates id 'T9'; choose from T1, T7, T8`, exit 5, no traceback. `--templates ''` writes T8.

**Sample pack.** I built it twice with sockets refused (0 calls each). `run.json` differs only at `/manifest/run_id`, `/manifest/started` and `/manifest/duration_s`. T7 and T8 are identical after masking; T1's only differing lines carry the run id or the `started` timestamp. Sizes: 236,843 / 139,999 / 47,808 / 35,178 bytes. Every page of T1 (9), T7 (3) and T8 (3) carries both `SYNTHETIC - illustrative` and `NO LICENCE - not for submission`, and the forbidden grep finds 0 hits.

**F17.** Two CLI runs in one `PROOFPACK_HOME` differ at `run_id`, `started`, `duration_s`, and at `ledger.acceptance_runs` / `manifest.ledger_count` (1 against 2: the acceptance ledger, by design). T1 and T7 are identical after masking.

**Other checks:**

- **Colours and fonts.** No hex colour outside `tokens.json`, and only `var(--pp-type-text)` / `var(--pp-type-mono)`, on any page or template. `@import`, `url(`, `<link` and `<script` occur only in template comments. The only `http:` is the SVG namespace, and T7's `http(s):` occurrences are citation text.
- **jinja2 hidden.** `import proofpack, proofpack.stats, cli, run, narrate.templates, synthetic, render.sentences, render.figures, render.format` all succeed with `jinja2` and `markupsafe` refused (`render.t1` needs `markupsafe`; it is inside `render/`).
- **Timing** (inside the Git Bash suite): `100,000 rows: run --templates T1,T7,T8 4.13 s; T1+T7+T8 renders from run.json 0.33 s; T1 3690123 bytes`.
- **Pre-fix.** The repair tests at `71b00d2` give 14 failed (N4 names the one that passes).
- **Criterion rows by position.** Three criteria all with id `C1` (one of them `level: "*"`) give rows 1-5 in `criteria_results` order, with statuses met / not met / not met ×3 equal to `run.json`.
- **conventions_T7.md versus the decisions file.** The DEC-18, DEC-34 and DEC-35 sentences agree with the decision rows as recorded in `spec/DECISIONS_2026-09-13_Josh.md`.

## What I could not check

- The r6 handoff's scripted re-run block (`e2e_shell`, `repros5/6`, `k1_checker`), whose scripts live in another session's scratchpad. I re-ran the markers, doctor, tr39 and the sweep list instead.
- The day-8 sweep (about 25 minutes).
- A wheel install into a fresh venv.
- Browser rendering of the SVG and the print CSS.
- A suppressed Number in a sentence slot. Lens 1 found no real path, and I found none either.
- Whether `t1_table_methods_without_overall` is reachable on engine output: I did not build a run whose Overall row carries a method no level row carries.

## Sentences I refused to write

- "T1 is correct for several operating points": B1 refutes it.
- "The captions name the methods of every run": measured on six documents only.
- "The F17 property holds": two runs in one home differ at the ledger count, so this holds only for separate homes, and I ran one home.
- "No page prints a verdict word": only the 13 T1/T7/T8 pages and the sample pack I rendered were read.
