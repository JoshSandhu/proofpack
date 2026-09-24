# Lens 3 (fresh attack) - build day 9, lane E, at `e17a510` - 2026-09-24

**Verdict: FAIL.** One blocker:

- **B1.** On a run that declares two operating points, T1 prints a customer criterion's status and draws its line against the other operating point's estimates. `_criterion_lines` in `render/figures.py` (F5) and the criteria column of Table T1-11 in `render/t1.py` match criteria rows by attribute, level and metric, and never compare the row's `operating_point`. An op2 criterion is drawn on the F5 plot captioned "at operating point op1" and printed as "criterion met" in op1's T1-11. Every op1 criterion is printed again in op2's T1-11.

B1 was already in the build: it reproduces through the CLI at `dd94874`, byte for byte. Neither lens-2 note mentions it; their two-operating-point probe checked sentences only. Lens 2's FA-B1 (sentences that do not name their operating point) is closed at `e17a510`, and so is every lens-1 blocker. The figures are under "What I could not break".

Also recorded, each record-and-carry:

- three sentence violations: N1 and N2 are new in repair 2, and N3 is carried T7 text that is false on clustered and `y_pred` runs;
- one surviving non-equivalent mutant of repair 2's code (N4);
- five inherited defects this lens found by constructing inputs (N5 to N9).

**Worktrees**, all under `scratchpad/lens-E9-r3-fresh-attack/`, all removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wt` | `e17a510` | suite, markers, lint, probes, day-9 sweep, CLI probes |
| `wt-dd` | `dd94874` | pre-fix runs, run.json comparison, the B1 repro at the old commit |
| `wtmut` | `e17a510` | my mutants |

In each worktree `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` before I trusted a figure from it. Every CLI run carried `--offline` and ran with `socket.socket` and `socket.create_connection` replaced by a function that raises: 0 calls on every run. I committed nothing. The only file I wrote in the main tree is this note.

## Blockers

### B1 - T1 attaches criteria to the wrong operating point: F5 criterion lines and the T1-11 criteria column

**The input.** `make_criteria(criteria=[_criterion(id="C3", operating_point="op2", scope={"attribute": "sex", "level": "F"}, value=0.70)], fairness=None)`, with `op2` appended (threshold 0.3, rule `>=`, `prespecified_sap`), on `cohort_with_a_thirty_row_site()`.

**What run.json says.** `criteria_results[0]` is `C3`, scope `sex = F`, `operating_point` `op2`, status `met`. The sex = F sensitivity is `51/65` (0.7846, CI 0.6703 to 0.8671) at op1 and `64/65` (0.9846, CI 0.9179 to 0.9973) at op2. C3 is `met` because 0.918 >= 0.70, at op2.

**What T1 prints.**

- F5 "Sensitivity by sex" has the caption "Sensitivity by sex at operating point op1". It plots F at `51/65 (78.5%) [67.0, 86.7]` and draws the dashed criterion line "customer criterion C3 (A, 2026-01-01): 0.7" at x = 0.70. The op1 interval crosses that line.
- The T1-11 table that follows op1's T1-10 ("performance by sex at operating point op1") prints `F +7.0 [−7.9, +21.7] ... C3 (row 1) → criterion met ; max LB 0.944 at n = 65`. That is op2's status and op2's maximum lower bound, printed beside op1's differences. Op2's T1-11 prints the same cell again.
- On a document with `C1` at op1 and `C3` at op2 (`probe/crit.py`), op2's age T1-11 prints `C1 (row 1) → criterion met`, `C1 (row 6)` and `C1 (row 3) → criterion not met`. Op1's sex T1-11 prints `C3 (row 8) → criterion met`. F5 "Sensitivity by sex" (op1) draws C3's line at 0.2. The T1-11 captions do not name an operating point. The only link to the right one is the row number into T1-17, whose `Op.` column is correct.

**Why it is a blocker.** A status and a declared value reach the page under a label that names a different operating point. Anyone reading op1's plot and op1's differences table sees an interval with a lower bound of 67.0 against a 70 line, next to "criterion met". It is the lens-2 B1 kind of defect (a figure under a label that does not identify it), in its stronger form: here the label names the wrong operating point. No test feeds a criterion on a second operating point.

**Where.** `render/figures.py::_criterion_lines` filters on `scope.attribute`, `metric`, `statistic == "ci_lower_bound"` and a numeric `value`, but not `operating_point`. F5 always plots the first operating point (`overall_op`). `render/t1.py::subgroup_blocks` builds each operating point's `crits` from every `crit_rows` row whose scope matches attribute and level.

**Repro (one line):** in `tests/`, `assemble(cohort_with_a_thirty_row_site(), crit)` with the criteria above, then `render_t1`. The F5 "Sensitivity by sex" figure carries `customer criterion C3 (A, 2026-01-01): 0.7`, and both sex T1-11 tables carry `C3 (row 1) → criterion met`.

I also ran it through the CLI (`main(["run", ..., "--offline", "--templates", "T1"])`, licensed, sockets refused), with C3 at `op2`, `level: "*"`, value 0.2. At `e17a510` and at `dd94874` alike it printed:

- `rc 0 socket calls 0`;
- `criteria_results [('C3', {'attribute': 'sex', 'level': 'F'}, 'op2', 'met'), ('C3', {... 'M'}, 'op2', 'met')]`;
- `F5 criterion label: ['customer criterion C3 (A, 2026-01-01): 0.2']` under `F5 caption: F5 - Sensitivity by sex. Sensitivity by sex at operating point op1`.

## Non-blocking (record-and-carry)

- **N1 (sentence_violation, new in repair 2) - `FAIRNESS_GAP` now places the threshold-free AUROC gap "at operating point op1".** The sentence reads "For F versus M at operating point op1: TPR gap +7.0 [...], FPR gap −4.8 [...], PPV gap +8.9 [...], AUROC gap +0.079 [−0.002, +0.160]." The AUROC gap is `/fairness/gaps/0/auroc_gap/number`, which has no operating point; the checker has a special exemption for it at `checker.py` line 901. On the two-operating-point document, the op2 sentence prints the same `+0.079` under "at operating point op2".
  - Before repair 2 the sentence did not scope the gap to an operating point. The repair's own note raises this as open question 1. A sentence on the page is still false while the question is open.
  - Repro: render T1 of the lens-2 two-op document and grep `at operating point <span class="customer-text inline">op2</span>: TPR gap`. That sentence ends `AUROC gap +0.079 [−0.002, +0.160]`.
- **N2 (sentence_violation, minor, new in repair 2) - the test name `test_the_repair_1_test_name_and_docstring_state_what_they_inspect`.** It asserts three literal strings present or absent in `tests/test_e9_repair1.py`. It cannot establish that the name and docstring "state what they inspect". This is the FA-N3 kind (a test name that claims more than the test inspects), one level up.
- **N3 (sentence_violation, carried T7 text, reworded by repair 2) - "z and the two-sided p are written to run.json beside the difference (`diff_vs_reference.auroc.detail` and `diff_vs_complement.auroc.detail`)".**
  - True on the i.i.d. documents: 6 + 9 AUROC difference cells carry `detail` with `z` and `p_value`.
  - The same sentence prints on the clustered T7 and the `y_pred`-only T7, whose run.json has `detail: None` in all 15 AUROC difference cells.
  - The paragraph goes on to say that under clustering the analytic methods are refused, so a careful reader can recover the scope. The sentence itself is unconditional.
  - Repro: `probe/docs.py`, then count `detail` per cell (my table: `clu` and `ypred` rows `'None'`); T7 of `clu` contains the sentence (`find` gives 14249).
- **N4 - surviving mutants of repair 2's code** (`wtmut`, run against `-m "(day9 or day8) and not slow"` with `-x`). See the table in "Mutation". The survivors:
  - `f5_caption_last_op` is non-equivalent. The F5 caption names the last operating point while the plot draws the first: a wrong label on a two-op run. No test renders F5 on a two-op document.
  - The others are listed with their grade in the table.
- **N5 - an operating-point id containing `/` or `~` loses every engine claim at that operating point.** `op/1~x` is accepted by the declaration schema (minLength only). `narrate/checker.py` then rejects all 60 engine claims at that operating point with `operating_point_mismatch`: 30 `SUBGROUP_ESTIMATE_WITH_DIFF`, 15 `SUBGROUP_ESTIMATE`, 13 `OVERALL_ESTIMATE`, 1 `FAIRNESS_GAP` and the `CRITERION_STATUS` of `fairness:tpr_gap` row 9. None is substituted.
  - The pointer segment is `op~11~0x`, and `pointer_facets` compares it to the claim's `op/1~x` without unescaping.
  - T1 prints no sentence for that operating point, and T8 lists the 60 rejections.
  - The same happens at `dd94874`. The checker is E8's and unchanged since `eda8a35`.
  - Repro: `probe/opids.py` prints `'op/1~x' ... rejections 60 ['operating_point_mismatch', ...]`.
- **N6 - operating-point ids that differ only by white space read as one.** `op1` and `op1 ` are both accepted. T1 then prints "For age = 0-40 at operating point op1, sensitivity was 30/38 ..." and "For age = 0-40 at operating point op1 , sensitivity was 36/38 ...". This is repair 2's disambiguation defeated by the customer's own ids. It is a declaration check, not a render fix: an H08-like refusal, or TR39 skeleton equality, over the ids.
- **N7 - F5 draws the first operating point only, and the page does not say so.** On the two-op document, the nine F5 plots are captioned "at operating point op1" (AUROC: no op). No plot or line states that op2's forest is not drawn.
- **N8 - the F5 AUROC caption joins method phrases that contain commas with ", "**: "interval: DeLong, Wald interval, DeLong, logit-transformed interval" (i.i.d. age and site). F4's `method_list` joins with "; ".
- **N9 - a suppressed Number with `k`/`n` in a sentence slot prints the counts** (constructed only). Given `{"est": 0.75, ..., "n": 4, "k": 3, "suppressed": True}`, `SUBGROUP_ESTIMATE_WITH_DIFF` prints `3/4 (‡) [no interval]`. The table cell prints `‡` alone, as `format.py`'s docstring says ("no digit from the cell, no count"). The egress null shape (`k: None`) prints `—/— (‡)`. No run.json carries `suppressed: true`: 0 in each of my seven documents. The carried "a k/n slot from a suppressed cell" case therefore stays constructed-only.
- **Carried from lenses 1 and 2, re-measured unchanged at `e17a510`:**
  - FA-N5, exact-half rounding: new instance `/overall/op2/accuracy` est 0.6225 prints `62.3` (a half-even Decimal gives 62.2), against 51/80 printing 63.7 (lens 1). `format.py` documents the rule (the binary double's decimal, `x * 100` once).
  - FA-N8: U+2028 and U+200B are carried raw (134 of each on the op-id injection T1).
  - FA-N9: T1's title "FDA AI-DSF performance evidence attachment set" is the one AI-DSF mention without the draft label on each T1 (1 per page file).
  - RG-N5: `endorsed` in the cover-note negation, 1 per page.
  - N1 residue of lens 2: T7 still prints DEC ids, "Lens 2", "lens 1 of 2026-09-18", "(its note, \"could not break\")", "the page returned 403 in the research session", "(cited from memory)".
  - The `op2` T1-11 caption, like op1's, names no operating point (see B1).

## Mutation

The committed day-9 sweep (`python scripts/mutation_sweep.py --marker day9`, Git Bash, `wt`): `15 planted, 15 killed, 0 survived; 168 s`, exit 0.

My mutants (`probe/mutants.py`, `wtmut`, each against `-m "(day9 or day8) and not slow" -x`):

| Mutant | Result |
|---|---|
| `sent_op_first_op` (every sentence names the first operating point) | killed, `test_a_two_operating_point_t1_names_...` |
| `sent_op_upper` (op id upper-cased) | killed, the same test |
| `tpl_sub_ne_no_op`, `tpl_diff_ne_no_op` (op clause dropped from a variant) | killed, `test_each_skeleton_renders_...[subgroup_not_estimable]` / `[subgroup_diff_not_estimable]` |
| `tpl_fair_no_op` | killed, the two-op test |
| `tpl_fair_ci_swap` (TPR and FPR `ci` bindings swapped) | killed, `[fairness_gap]` |
| `cli_json_inverted`, `cli_json_clause_html_only` | killed, `test_the_exit_4_next_step_...` / `test_the_no_licence_json_next_step_...` |
| `f4_no_bar_when_any_not_drawn`, `f4_no_bar_dropped` | killed, `test_a_clustered_t1_and_t7_name_the_methods_...` / `test_f4_with_every_bin_typed_...` |
| `f5_caption_no_op` | killed by the T1 golden only |
| `t1_sub_sentences_first_op_only` (op2's subgroup sentences dropped) | killed, the two-op test |
| `fmt_signed_zero_plus` (`+0.0`) | killed, `test_differences_in_percentage_points_...` |
| **`f5_caption_last_op`** (the caption names the last operating point, the plot draws the first) | **survived**, `616 passed`: non-equivalent on a two-op run (N4) |
| `sent_kn_suppressed` (a suppressed Number's k/n not printed) | survived, `616 passed`: equivalent on engine output, which never carries `suppressed: true` (N9) |

15 planted: 13 killed, 2 survived, 1 of the survivors non-equivalent.

## What I could not break (with figures)

**Suite and lint** (`wt`, `PROOFPACK_TR39_FULL` set):

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| full suite | `1406 passed, 1 skipped, 1 xfailed in 133.42s` | `1406 passed, 1 skipped, 1 xfailed in 132.07s` |
| `-m day9` / `day8` / `day7` / `day6` | `150` / `468` / `139` / `285 passed` | `150` / `468` / `139` / `285 passed` |
| `-m day5` | `54 passed` | - |
| `ruff check` / `ruff format --check` | `All checks passed!` / `191 files already formatted` | the same |
| 100,000-row timing (inside the suite) | `run --templates T1,T7,T8 4.29 s; T1+T7+T8 renders from run.json 0.25 s; T1 3693048 bytes` | - |

The counts equal the repair note's. The suite is 1399 at `dd94874` plus the 7 tests of `test_e9_repair2.py`.

**Pre-fix.** I copied `test_e9_repair2.py`, `test_e9_templates.py` and `test_claims.py` into `wt-dd`. Result: `11 failed, 236 passed`, equal to the note. The failures are the 5 new non-pin tests, the 5 edited skeleton cases and the D4 transcription test. The two pins pass there, as their docstring says.

**No statistics changed.** `git diff --stat dd94874 e17a510` over `stats/`, `gates.py`, `criteria.py`, `egress/`, `narrate/checker.py`, `narrate/claims.py`, `io/`, `schema/`, `render/format.py`, `run.py`, `pyproject.toml`, `uv.lock`, `design/tokens.json` and `design/guidance_map_v1.csv` prints nothing. So does `eda8a35..e17a510` over `stats/`, `gates.py`, `criteria.py`, `egress/` and `tokens.json`.

I built six documents at both commits: i.i.d. with `CRITERIA` + `FAIRNESS`, two operating points, clustered with fairness, `y_pred` only, logit score, and comparator. All six pairs are byte-identical.

**Lens-2 FA-B1 closed.** On all six documents, every claim printed on T1 with an `operating_point` contains its id in its sentence: 0 unnamed of 70 / 130 / 62 / 59 / 70 / 70 claims. None is left unprinted.

**Lens-1 blockers closed.**

- "Wilson score for proportions, DeLong for AUROC" and "Newcombe method 10 for proportions" occur 0 times on the clustered T1.
- The clustered F4 draws bins 2-10. Bin 1 is `boundary_estimate` and is not drawn.
- `verdict` occurs 0 times on every T7 I rendered (11 pages).

**Slot bindings.** For every template and variant under `lookup` (884 bindings, over metric `None` / `sensitivity` / `auroc` / `oe` / `accuracy` and status `None` / `not_assessable`):

- every `ci`, `ci_lo`, `ci_hi`, `k`, `n` and `method` facet reads the selector of the estimate before it;
- every slot's binding count equals its occurrences in the skeleton.

Rendering from literal Numbers (est 0.7512, CI 0.6123 to 0.8456, k/n 151/201) gives `151/201 (75.1%) [61.2, 84.6]`. Differences at −0.0321, 0.0, −0.00004 and a typed diff print `−3.2`, `0.0`, `0.0` and `n.e. (boundary_estimate)`. A typed value prints `n.e. (boundary_estimate)` in place of its estimate.

**Cells, my own formatter** (`probe/cells.py`: `Decimal(repr(x))`, half-even, U+2212, the tier map, never importing `render.format`). It compared **926** `data-ref` cells on T1/T8/T7 of the six documents. The 28 mismatches are all of one of three kinds:

- 20 `ci` cells of a typed Number print `no interval`, where I expected the reason; the `est` cell beside each prints the reason;
- 6 `auroc` cells print "not computed in this run (v1.1)" as intended;
- 2 are FA-N5's half (`62.3`).

A slash op document adds 260 more cells, with mismatches of the same three kinds only.

**Digits traced.** Outside `<style>` and `<svg>`, every digit run on T1 of the six documents traces to a value in run.json (0 to 3 dp, ×100, counts, strings) or to static citation text: `2007-03-13`, `2024/1368`, `807.92`, `510(k)`, `D4 section 5.10`, the version string. Every T7 digit run outside run.json is conventions or citation text (years, DOIs, the coverage table).

**T7 methods table against run.json.** It equals my walk of every Number on 7 documents. i.i.d.: `wilson` 135, `newcombe10` 192, `delong_wald` 45, `delong_logit` 7, `irls_wald` 6, `log_delta` 5, `bootstrap_percentile` 11, `none` 17. Two-op: `wilson` 249, `newcombe10` 384. Clustered: `cluster_bootstrap_percentile` 95, `none` 322. `y_pred`: 115 / 182 / 3 / 36.

**Figures** (`probe/figs.py`: inverting `data-map` from the SVG alone). The F2 polyline and operating-point markers, the F4 points, bars and histogram strip (x extent and n), and the F5 points, intervals and reference line match run.json on all six documents plus the slash-op document. That is 2,333 coordinates, max deviation `2.22e-16`.

- No `fill` other than `none` outside the histogram strip; no `<polygon>`; no `<rect>` outside the strip.
- F4 is omitted with its reason on logit (`calibration is null (score_not_probability)`) and on `y_pred` (`no_score_column`).
- F2 on `y_pred` prints "F2 (ROC) is not drawn: the run document carries no ROC array".
- 40 site levels give 40 F5 rows and 40 points (viewBox height 1120).
- A `point_estimate` criterion draws no line. A `ci_lower_bound` one draws a labelled line (B1 aside).

**Anchors.** Every `<a href="#FDA_AIDSF_*">` carries "draft guidance (January 2025), not for implementation" (T1 27, T7 3, T8 6 or 5 on `y_pred`). So does every raw `FDA_AIDSF_*` id in text (12 per T1, 3-4 per T8) and every figcaption (9-11 per T1).

**Forbidden words.** I grepped `FORBIDDEN_ON_PAGE` ∪ the checker's `VERDICT_WORDS` and `CERTIFICATION_WORDS` ∪ robust, reliable, fair, equitable, demonstrates, validated, meets, passes, clinically, pass, fail, verdict, acceptable, consistent, unbiased, safe, effective, biased, guarantee, ensures, good, adequate, sufficient, superior, inferior, noninferior, equivalent. I also searched for the phrases "model is", "performs well", "no evidence of bias" and "well calibrated". The scope was T1/T7/T8 of six documents, outside `.status` / `.disclaimer` / `.customer-text`. The only hits are:

- `endorsed` in the cover note (RG-N5);
- `guarantee` in "none of them is a guarantee" and "not a guarantee" (T7).

The phrases: 0.

**Injection.** I planted `<script>alert(1)</script><img src=x onerror=1>{{ 7*7 }}{% raw %}` + U+202E + U+2028 + U+200B + `[unverified] planted` as:

- an operating-point id;
- every author, justification (with 10,000 `A`), criterion id, model name and version, source, prevalence label, reference-standard description and fairness text;
- a site level (with 10,000 `A`) and a sex level in the data.

`html.parser` finds no `script`, `img`, `iframe`, `object` or `link` start tag and no `on*` attribute on any of 12 pages. `{{ 7*7 }}` stays literal (up to 218 per page). U+202E appears only as `&#x202e;`. `[unverified] planted` survives every time (T1 up to 218, T8 81). The 10k strings are kept.

**CLI, licence states** (templates `T1,T7,T8`, sockets refused, 0 calls each):

| State | Result |
|---|---|
| ok | exit 0; T1 9 pages, T7 3, T8 3; one footer on every page |
| trial | `TRIAL` on every page |
| grace | `LICENCE EXPIRED - not for submission` on every page |
| expired past grace | exit 4, no HTML; `Next step: proofpack licence install FILE, then run again for T1.html, T7.html, T8.html (docs: /docs/run)` |
| no licence | exit 4 with the `NO LICENCE` watermark in run.json |

- `--templates T9`: `error: unknown --templates id 'T9'; choose from T1, T7, T8`, exit 5, no traceback, in every state.
- `--templates "t1, t7"` is accepted.

**Sample pack.** I built it twice with sockets refused: 0 calls. Sizes: run.json 236,843, T1 142,924, T7 47,830, T8 35,178 bytes, equal to the note. run.json differs only at `/manifest/duration_s`, `/manifest/run_id` and `/manifest/started`. After masking those, T1, T7 and T8 are identical, apart from T8's `Duration (s)` cell. Every page (9 / 3 / 3) carries `SYNTHETIC - illustrative` and `NO LICENCE - not for submission`, and one footer.

**F17.** I ran two CLI runs of one prepared input in two homes. run.json differs at `duration_s`, `run_id` and `started` only. T1, T7 and T8 are identical after masking.

**Imports with jinja2 and markupsafe blocked.** `proofpack`, `proofpack.stats`, `cli`, `run`, `narrate.templates`, `render.sentences`, `render.figures`, `render.format` and `synthetic` import; `jinja2 loaded: False`. `render.t1` needs markupsafe; it is inside `render/`.

**Colours, fonts, external references.** No hex colour outside `tokens.json` in any template or page. `font-family` is only `var(--pp-type-text)` / `var(--pp-type-mono)`. `@import`, `url(`, `<link` and `<script` occur only in the comments of `base.html` and `_print.css.j2`. `http:` is the SVG namespace (one per SVG), and T7's `http(s):` are citation texts.

**Repair-note figures.** Each of the following matches my measurement:

- the golden T1 diff is 46 added lines, each with `at operating point <span class="customer-text inline">op1</span>`;
- the T7 golden diff is the two conventions sentences;
- `proofpack-site` (now `02c42b8`) has no match for the note's grep terms;
- the two-op counts are 26 + 60 + 30 + 8 + 2.

## What I could not check

- A wheel installed into a fresh venv: numpy and every other dependency live in the user site beside the editable `.pth`, and I had no offline source for them.
- Browser rendering of the SVG and the print CSS.
- The day-8 sweep (about 25 minutes).
- The r6 handoff's scripted re-run block, whose scripts live in another session's scratchpad. I re-ran the markers, the sweep, the sample pack and the CLI states instead.
- Why two separately prepared mappings of the same data give different `mapping_sha256` (my first F17 attempt). With one prepared input the property held.

## Sentences I refused to write

- "No sentence on T1 is ambiguous about its operating point": N6 is a counter-example, and B1 is its figure and table counterpart.
- "T1 attaches each criterion to the right table": B1.
- "Every figure coordinate is correct": measured on seven documents, 2,333 coordinates.
- "No page prints a verdict word": only the pages listed were read.
- "The repair is complete": B1 is not a repair-2 defect, but it is a two-operating-point defect in the tables the repair left untouched.
