# Lens 4 (fresh attack) - build day 9, lane E, repair 3 at `f72a9af` - 2026-09-24

**Verdict: FAIL.** One blocker:

- **B1.** F5 draws a `paired_difference_vs_prior` criterion as a threshold on the level-estimate axis. `render/figures.py::_criterion_lines` is the function repair 3 rewrote. It now reads the criteria row's `operating_point`, but it still never reads the criterion's `type`. Take a criterion declared as a margin on the new-minus-prior difference: D1 section 2's own example, `C2`, has sensitivity, `type: paired_difference_vs_prior`, `op1`, `ci_lower_bound >= -0.03`. Give it a subgroup scope, and T1 draws it on "F5 - Sensitivity by sex ... at operating point op1" as a dashed line at x = −0.03 on the 0-to-1 sensitivity axis, labelled `customer criterion Cpd (A, 2026-01-01): −0.05` in my run. The run's own `criteria_results` row says `not_assessable`, `requires_compare`. The line sits left of the axis origin (x = 178.5 against x0 = 190). A positive margin (0.6 in my second input) lands inside the plot, among the level estimates.

B1 is not new in repair 3. It reproduces byte for byte at `952bddc`, and none of lenses 1 to 3 fed a paired-difference criterion. It is the same kind of defect as lens-3 FA-B1, which lens 3 graded a blocker and repair 3 closed: a customer's declared value drawn on a plot of a quantity it does not constrain. There, the wrong operating point. Here, the wrong statistic: a difference against the prior version, drawn as a subgroup's own sensitivity or AUROC.

Lens-3 FA-B1 is closed at `f72a9af` on every input I built (details under "What I could not break"). So are lens-3 FA-N1, FA-N3 and FA-N2 = RG-N1, and every lens-1 and lens-2 blocker phrase I re-grepped. The 5 tests in `tests/test_e9_repair3.py` fail at `952bddc`.

Also recorded, each record-and-carry:

- three sentence violations (N1 to N3), all in text repair 3 wrote;
- one surviving non-equivalent mutant in the function repair 3 edited (N4, pre-existing code);
- the table form of lens-3 FA-N1 (N5);
- the carried items, re-measured (N6).

**Worktrees**, all under `scratchpad/lens-E9-r4-fresh-attack/`, all removed at the end:

| Worktree | Commit | Used for |
|---|---|---|
| `wt` | `f72a9af` | suite, markers, lint (both shells), probes, CLI states, sample pack, F17, timing |
| `wt95` | `952bddc` | the pre-fix run of `test_e9_repair3.py`; the B1 repro at the old commit |
| `wtmut` | `f72a9af` | the committed day-9 sweep |
| `wtm2` | `f72a9af` | my 11 mutants |

In each worktree, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's `src\proofpack\__init__.py` before I trusted any figure from it. Every CLI run carried `--offline`. `socket.socket` and `socket.create_connection` were replaced by a function that raises, and every run printed `socket calls 0`. I committed nothing. The only file I wrote in the main tree is this note.

## Blockers

### B1 - F5 draws a paired-difference-vs-prior margin as a threshold on the level-estimate axis

**The input.** `cohort_with_a_thirty_row_site()`, `make_criteria(criteria=[_criterion(id="Cpd", type="paired_difference_vs_prior", operating_point="op1", scope={"attribute": "sex", "level": "F"}, value=-0.05), _criterion(id="C3", operating_point="op2", scope=SEX_F, value=0.70)], fairness=FAIRNESS)`, with `op2` appended (threshold 0.3, `>=`). Run through the CLI: `main(["run", ..., "--offline", "--templates", "T1,T7,T8"])`, licensed, sockets refused.

**What `run.json` says.** `criteria_results`:

- `('Cpd', 'op1', 'not_assessable', 'requires_compare')`;
- `('C3', 'op2', 'met', 'statistic_compared')`;
- the two `fairness:tpr_gap` rows.

**What T1 prints.** Output of `probe/cli.py`, verbatim:

```
rc 0 socket calls 0
F5-sex-sensitivity (['customer criterion Cpd (A, 2026-01-01): −0.05'], 'F5 - Sensitivity by sex. Sensitivity by sex at operating point op1; n per level as in Tabl')
```

The SVG (`probe/p3b.py`, the same criterion through `assemble` + `render_t1`):

```
data-map 190.0 20.0 230.0 52.0 0.0 1.0 0.0 1.0
<path class="fig-criterion" fill="none" data-role="criterion" d="M178.5,20.0 L178.5,72.0"/>
<text class="fig-text" x="178.5" y="14" text-anchor="middle">customer criterion Cpd (A, 2026-01-01): −0.05
```

x = 190 + (−0.05 − 0) / (1 − 0) × 230 = 178.5, so the line is placed exactly as if −0.05 were a sensitivity.

With `value=0.60` and a second paired-difference criterion on `auroc` (`Cauc_pd`, value 0.55, no operating point), `probe/p3.py` prints:

- `F5-sex-sensitivity (['customer criterion Cpd (A, 2026-01-01): 0.6'], ...)`;
- `F5-sex-auroc (['customer criterion Cauc_pd (A, 2026-01-01): 0.55'], ...)`.

Both rows are `not_assessable` in `run.json`. T1-11 also prints both, as `Cpd (row 1) → not assessable` and `Cauc_pd (row 2) → not assessable`. Those statuses are the run's own, and correct.

**At `952bddc`.** `probe/p3b.py` and `probe/p3.py` print the same `data-map`, the same `d="M178.5,20.0 L178.5,72.0"` and the same two labels.

**Why it is a blocker.** A declared number reaches a figure at a position that means something else. A reader of "Sensitivity by sex at operating point op1" reads the dashed line as the customer's threshold on sex = F's sensitivity. The customer declared a margin on the difference between the new and the prior version, and the run did not evaluate it (`requires_compare`). This is lens-3 FA-B1's kind, a declared value on the wrong plot, carried by the statistic rather than the operating point.

**Where.** `_criterion_lines` filters on `scope.attribute`, `metric`, `operating_point`, `statistic == "ci_lower_bound"` and a numeric `value`. The criteria row does not carry `type` (`probe/p3.py` prints `'type': None` for both rows). The declaration entry does: the function already reads `entries[declaration_index]` for the author and date. D4 section 6's F5 row says "if a criterion with `ci_lower_bound` scope on this attribute exists"; D1 section 2 marks `paired_difference_vs_prior` "compare only". No test feeds a paired-difference criterion to T1.

**Repro (one line):** in `tests/`, `render_t1.render_t1(assemble(cohort_with_a_thirty_row_site(), make_criteria(criteria=[_criterion(id="Cpd", type="paired_difference_vs_prior", scope={"attribute": "sex", "level": "F"}, value=-0.05)], fairness=None)))` contains `customer criterion Cpd (A, 2026-01-01): −0.05` inside `<figure ... id="F5-sex-sensitivity">`.

## Non-blocking (record-and-carry)

- **N1 (sentence_violation, new in repair 3) - `tests/test_e9_repair3.py`'s docstring: "the first `E` line of each is in the repair note".** The repair note is `workflows/notes-day9/E9_repair3.md`, which the orchestrator wrote because the repairer's session ended first. It contains no `E` line: `grep -c "^E \|E   \|AssertionError"` prints `0`. The other half of that sentence, "Every test below was run in a `952bddc` worktree ... and failed there", matches my measurement (below). Whether the repairer ran them cannot be known from any file.
- **N2 (sentence_violation, minor, new in repair 3) - "A row with no operating point (an ``auroc`` criterion: D1 section 2's H09 rules ...)".** This is in the comment in `render/t1.py::subgroup_blocks`, and the same parenthetical is in the commit message. `probe/p1.py` gives three other kinds of criteria row with `operating_point: None`, each printed under both operating points' T1-11:
  - `Ccal` (`calibration_slope`, `not_assessable`), row 5;
  - `fairness:auroc_gap` (fairness `criterion_of_interest: auroc_gap`), row 8;
  - `Cauc_pd` (`probe/p3.py`, a paired-difference `auroc` row).

  The code does the right thing with all three. The sentence names one kind only. The same function's docstring reads "... with each criterion scoped on the attribute and level and declared on that operating point or on none". A criterion scoped on the reference level is printed in no T1-11: `Cstar` at sex = M (row 4 of `probe/p1.py`) appears only in T1-17, because the reference row is skipped. That behaviour predates repair 3, but repair 3 wrote the sentence.
- **N3 (sentence_violation, minor, new in repair 3) - the test name `test_each_t1_11_prints_the_criteria_rows_of_its_own_operating_point_and_c5`.** Its regex reads only `data-attribute="sex"` tables, and within them the `F` row. The document has age and site T1-11 tables too. The lens-2 FA-N3 and lens-3 N2 kind again. A name that describes what it checks: `..._sex_f_t1_11_rows_at_op1_and_op2_carry_their_own_criteria_and_c5`.
- **N4 - a surviving non-equivalent mutant in `_criterion_lines`: `f5_dedupe_by_id_only`.** It changes `key = (criterion_id, float(value))` to `(criterion_id, 0.0)`. Result: `154 passed` against `-m "day9 and not slow"`. The mutant is not equivalent: `probe/p6.py` declares `C1` twice at op1 on sex = F, with values 0.4 and 0.3. `run.json` has two rows, both `met`. F5 draws `['customer criterion C1 (A, 2026-01-01): 0.4', 'customer criterion C1 (A, 2026-01-01): 0.3']`, and the mutant would draw one. This is pre-existing code, not repair 3's.
- **N5 - the table form of lens-3 FA-N1.** On the two-op document, Table T1-13 prints the op-less AUROC gap in rows labelled by operating point: `F op1 ... +0.079 [−0.002, +0.160]` and `F op2 ... +0.079 [−0.002, +0.160]`. The same holds for T1-10's AUROC column and T1-11's Δ AUROC column: each is printed in both per-operating-point tables, and neither says the value is op-free. Repair 3 fixed the sentence only. The code comment says T1-11's column is printed "under every operating point" by design. Record only. A column note ("AUROC: no operating point") would close it.
- **N6 - carried, re-measured unchanged at `f72a9af`:**
  - lens-3 N5: an operating-point id containing `/` loses its claims. My injection op id (it contains `</script>`) printed T1-11 correctly, but only op1's fairness sentence.
  - lens-3 N6, N7 (F5 draws the first operating point only), N8, N9.
  - FA-N5: exact-half rounding. My probe formatted −0.0345 as `−3.5`: the double is −3.45000000000000017763568394002504646778106689453125, so this follows the documented rule.
  - FA-N8: U+2028 / U+200B carried raw.
  - FA-N9: the T1 title "FDA AI-DSF performance evidence attachment set" is the one unlabelled mention, 1 per T1.
  - RG-N5: `endorsed`, 1 per page.
  - `guarantee` in T7's negations, 2 per T7 (1 on `y_pred`).
  - The T7 paragraph now says "(estimate carried, no z, no p)" without having introduced z and p. The phrase is true: `probe/p5.py`'s perfectly separated S3 site gives `z: None, p_value: None` on both `boundary_estimate` cells. Cosmetic.

## Mutation

The committed day-9 sweep (`python scripts/mutation_sweep.py --marker day9`, Git Bash, `wtmut`) printed `17 planted, 17 killed, 0 survived; 206 s`, exit 0. The list is 17, as the commit says, with the two repair-3 mutants included.

My mutants (`probe/mutants.py`, `wtm2`, each run against `-m "day9 and not slow" -x`, the file restored after each):

| Mutant | Result |
|---|---|
| `t1_none_rows_dropped` (`row_op is None or` removed) | killed, `test_each_t1_11_...` |
| `t1_first_op_only` (compare with the first operating point) | killed, the same |
| `t1_none_rows_only` | killed, the same |
| `f5_auroc_plot_gets_overall_op` | killed, `test_an_op2_criterion_draws_no_line_...` |
| `f5_last_op` (lines read the last operating point) | killed, the same |
| `f5_caption_last_op` (lens-3 N4's survivor) | **killed now**, the same test |
| `f5_op_rule_as_t1` (F5 also draws op-less rows on threshold plots) | killed only by `test_sweep_day9.py`'s pattern count; equivalent on declared input, because H09 gives every threshold-metric row an operating point |
| `tpl_fair_no_noop_phrase` | killed, `test_the_fairness_gap_sentence_...` |
| `tpl_fair_auroc_ci_from_ppv` (AUROC `ci` bound to `ppv_gap.ci`) | killed, the same |
| `conv_zp_restored` | killed, `test_t7_prints_no_z_p_location_sentence_...` |
| **`f5_dedupe_by_id_only`** | **survived**, `154 passed`: non-equivalent (N4) |

11 planted: 10 killed, 1 survived.

## What I could not break (with figures)

**Suite and lint** (`wt`, `PROOFPACK_TR39_FULL` = `workflows/data/confusables-18.0.0.txt`):

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| full suite | `1411 passed, 1 skipped, 1 xfailed` (154.71 s)* | `1411 passed, 1 skipped, 1 xfailed in 127.83s` |
| `-m day9` / `day8` / `day7` / `day6` | `155` / `468`* / `139` / `285 passed` | `155` / `468` / `139` / `285 passed` |
| `-m day5` | `54 passed` | - |
| `ruff check` / `ruff format --check` | `All checks passed!` / `195 files already formatted` | the same |

\* My first Git Bash run set `PROOFPACK_TR39_FULL=1`, which that test reads as a path. It printed `1410 passed, 2 skipped` and `day8 467 passed, 1 skipped`. The skipped test, `test_e8_repair4.py::test_the_vendored_tr39_subset_regenerates_from_the_full_file`, then gave `1 passed` when run with the real path. The counts equal the orchestrator's (1411 / 155 / 195 files).

**Pre-fix.** `tests/test_e9_repair3.py` copied alone into `wt95` (`952bddc`, its own `test_e9_repair2.py`) gave `5 failed`. The first `E` lines:

- the F5 dict, with `'F5-sex-sensitivity': ['customer criterion C3 (A, 2026-01-01): 0.7', 'customer criterion C4 (A, 2026-01-01): 0.6']`;
- the T1-11 dict, where op1 and op2 each list C3, C4, C5 and both `fairness:tpr_gap` rows;
- `'For F versus M at operating point op1: TPR gap ... AUROC gap +0.079 ...'`;
- `'written to run.json beside the' is contained here`;
- `'state_what_they_inspect' is contained here`.

With the new `test_e9_repair2.py` and `test_e9_templates.py` copied in as well, the three files gave `7 failed, 84 passed`. That run is an artefact: the FA-N2 test reads the repair-2 file from disk, so it passed.

**No statistics changed.** `git diff --stat 952bddc f72a9af` over `stats/`, `gates.py`, `criteria.py`, `egress/`, `narrate/checker.py`, `narrate/claims.py`, `io/`, `schema/`, `render/format.py`, `run.py`, `cli.py`, `pyproject.toml`, `uv.lock`, `design/tokens.json`, `design/guidance_map_v1.csv` and `.github` prints nothing. So does `eda8a35..f72a9af` over `stats/`, `gates.py`, `criteria.py`, `egress/` and `tokens.json`.

`git diff --name-status 952bddc f72a9af -- tests/` gives `M` for the two goldens, `test_e9_repair2.py` and `test_e9_templates.py`, and `A` for `test_e9_repair3.py`. There is no `D` and no skip or xfail added. The one assertion that flipped (the z/p sentence, from present to absent) follows the deleted text.

**Lens-3 FA-B1 closed, beyond the repair's own input:**

- `probe/p1.py` (two-op, eight criteria rows):
  - `C1` declared at op1 and again at op2 (same value 0.4) draws one F5 line, from the op1 row. Op1's T1-11 prints `C1 (row 1)` and op2's prints `C1 (row 2)`.
  - `Cstar` (`level: "*"`, op2) appears only in op2's T1-11.
  - `Cspec2` (specificity, op2) draws nothing on the op1 specificity plot and appears only in op2's T1-11.
  - `Cub` (`ci_upper_bound`, op1) draws no line and prints in op1 only.
  - The op-less rows (N2) print under both operating points. Every status equals its `criteria_results` row by position.
- `probe/p2.py`, operating points declared `opZ` then `op1`: `overall` keys `['opZ', 'op1', 'threshold_free']`. F5 is captioned "at operating point opZ" and draws `Cb` (opZ) only. T1-11 opZ prints `Cb (row 2)` and op1 prints `Ca (row 1)`.
- Comparator run: F5 "PPA by sex at operating point op1" draws `Cppa1` only. T1-11 op1 prints `Cppa1 (row 1)` and op2 prints `Cppa2 (row 2)`. `Csens1` (sensitivity under a comparator) is `not_assessable` and draws nothing.
- Injection op id (`opX` + `<script>alert(1)</script><img src=x onerror=1>{{ 7*7 }}{% raw %}` + U+202E U+2028 U+200B + `[unverified] planted`), with a criterion declared on it:
  - its T1-11 prints that criterion (row 1) and op1's does not;
  - `html.parser` finds no `script`, `img`, `iframe`, `object` or `link` start tag and no `on*` attribute;
  - `{{ 7*7 }}` stays literal 130 times, U+202E appears only as `&#x202e;` (130), and `[unverified] planted` survives 130 times;
  - 10,000-character author and justification strings are kept.
- Through the CLI (`probe/states.py`, C3 at op2 and C4 at op1): rc 0, 0 socket calls.

**FA-N1 closed.** Output of `probe/docs.py`:

- the two-op `FAIRNESS_GAP` sentences print `+0.079 [−0.002, +0.160]` after "AUROC gap (no operating point)" at op1 and at op2;
- clustered: `AUROC gap (no operating point) n.e. (cases_span_both_groups) [no interval]`;
- `y_pred`: `n.e. (not_computed_this_run) [no interval]`.

Each reason equals `/fairness/gaps/0/auroc_gap/number/not_estimable_reason` in that run.

The skeleton from literal Numbers (TPR 0.0712 [−0.0213, 0.1634], FPR −0.0345 [−0.0891, 0.0123], PPV 0.0 [−0.0432, 0.0521], AUROC −0.0123 [−0.0456, 0.0234]) gives `TPR gap +7.1 [−2.1, +16.3], FPR gap −3.5 [−8.9, +1.2], PPV gap 0.0 [−4.3, +5.2]; AUROC gap (no operating point) −0.012 [−0.046, +0.023]`. Every facet is in its slot. A typed `boundary_estimate` in each of the four positions prints `n.e. (boundary_estimate) [no interval]` in that position only. −0.00004 prints `0.0`.

**FA-N3 closed.** "z and the two-sided p", "written to run.json beside", "printed as detail" and "No target is compared to" occur 0 times on the i.i.d., two-op, clustered and `y_pred` T7s. "no z, no p" occurs once.

**Earlier blockers.** On the clustered T1/T7, "Wilson score for proportions, DeLong for AUROC" and "Newcombe method 10 for proportions" occur 0 times. `verdict` occurs 0 times on every page I rendered.

**Skeleton text against D4 section 8.** My comparison of all 56 library skeletons to D4's table found these differences:

- FLOW_COUNTS;
- REF_STD_TYPE_NOTE;
- SUBGROUP_ESTIMATE_WITH_DIFF;
- CRITERION_STATUS;
- FAIRNESS_GAP;
- KS_RESULT;
- the recorded addition SUBGROUP_ESTIMATE.

That is exactly the module docstring's list. The other four "not in D4" hits are my parser failing on D4's four-id row. No skeleton carries a forbidden word outside the three status phrases.

**Cells** (`probe/cells.py`: `Decimal(repr(x))`, half-even, never importing `render.format`). It compared 603 `data-ref` cells on the i.i.d., two-op, clustered and `y_pred` T1s. There are 0 real mismatches. The 8 my script flags are its own: it wrote `-` where the page correctly prints U+2212, and it misread O:E's `k`.

**Forbidden words** (`probe/words.py`): the checker's `VERDICT_WORDS` ∪ `CERTIFICATION_WORDS` ∪ `test_render_t8.FORBIDDEN_ON_PAGE` ∪ the brief's list, plus the phrases "model is", "performs well", "no evidence of bias" and "well calibrated". The scope was T1/T7 of five documents and the CLI T1/T7/T8, outside `.status`, `.disclaimer` and `.customer-text`. The only hits are `endorsed` (1 per page) and `guarantee` (T7 negations).

**Anchors.** Every `<a href="#FDA_AIDSF_*">` carries "draft guidance (January 2025), not for implementation": T1 27/27 on every document, T7 3/3, T8 6/6. So does every figcaption (11/11 on the two-op, clustered and B1 T1s, 9/9 on `y_pred`). No `fill` other than `none`. `<rect>` occurs 10 times per T1 with a score, 0 on `y_pred`: the histogram strip, as lens 3 found.

**External references, colours, fonts** (the two-op T1, clustered T7, CLI T8): `@import`, `url(`, `<link` and `<script` occur 0 times each. `http:` is the SVG namespace (11 on T1). `https:` appears twice, both in T7 citations. No hex colour outside `tokens.json`. `font-family` is only `var(--pp-type-text)` / `var(--pp-type-mono)`.

**CLI, licence states** (`probe/states.py`, two-op criteria, `--templates T1,T7,T8`, 0 socket calls each). The counts are page footers and watermark strings:

| State | Result |
|---|---|
| ok | rc 0; T1 9 footers, T7 3, T8 3 |
| trial | rc 0; `TRIAL` T1 12, T7 5, T8 8 |
| grace | rc 0; `LICENCE EXPIRED - not for submission` T1 11, T7 5, T8 7 |
| expired past grace | rc 4, no HTML; `Next step: proofpack licence install FILE, then run again for T1.html, T7.html, T8.html (docs: /docs/run)` |
| no licence | rc 4, `licence refused (no_file)`, the same next-step line |

- `--templates T9` in each state: rc 5, `error: unknown --templates id 'T9'; choose from T1, T7, T8`, no traceback.
- The one `TRIAL` on the licensed T1 is the disclaimer sentence that names the marks.

**Sample pack**, built twice (`scripts/build_sample_pack.py`, sockets refused, 0 calls). Sizes: run.json 236,843, T1 142,924, T7 47,666, T8 35,178 bytes. T7 is 164 bytes smaller than lens 3's 47,830: the deleted z/p sentence.

- run.json differs only at `/manifest/run_id`, `/manifest/duration_s` and `/manifest/started`.
- T1, T7 and T8 are identical after masking those values (T8's duration cell included).
- T1 has 9 footers, each carrying `NO LICENCE - not for submission · SYNTHETIC - illustrative`.

**F17.** One prepared two-op input, run in two homes: run.json differs at `duration_s`, `run_id` and `started` only. T1, T7 and T8 are identical after masking.

**100,000 rows** (`tests/test_render_timing.py -s`, Git Bash): `run --templates T1,T7,T8 4.95 s; T1+T7+T8 renders from run.json 0.28 s; T1 3693048 bytes`.

**Imports with jinja2 and markupsafe blocked by a meta-path finder.** `proofpack`, `proofpack.stats`, `cli`, `run`, `narrate.templates`, `render.sentences`, `render.figures` and `render.format` import, and `jinja2 loaded: False`.

**Commit-message and note figures.** Each matches my measurement:

- 5 tests, each failing at `952bddc`;
- 17 day-9 sweep mutants;
- no `stats/`, gates, criteria, checker, schema, `run.py`, CLI or `tokens.json` change;
- the orchestrator's 1411 / 155 / lint.

## What I could not check

- A wheel installed into a fresh venv (not attempted this round; lens-3 regression did it at `e17a510`, and repair 3 changes `design/conventions_T7.md`, which the wheel force-includes).
- Browser rendering of the new `FAIRNESS_GAP` sentence and of an off-axis criterion line.
- The day-8 sweep (about 25 minutes).
- The r6 handoff's scripted re-run block: its scripts live in another session's scratchpad. I re-ran the markers, the day-9 sweep, the sample pack, the CLI states, F17 and the imports instead.
- Whether a customer would scope a `paired_difference_vs_prior` criterion on a subgroup in practice. The schema and `io/declare.py` accept it, and the CLI runs it to rc 0.

## Sentences I refused to write

- "F5 draws each criterion on the right plot." B1 is a counter-example. Written instead: on the eight-row, reversed-order, comparator and injection inputs above, F5 draws only rows whose `operating_point` equals the plot's.
- "Every op-less criteria row is an AUROC criterion." N2.
- "The repair's tests each failed at `952bddc`, as the note records." They fail, but the note records no `E` line (N1).
- "No page prints a verdict word." Only the pages listed were read.
- "Repair 3 introduced no defect." B1 predates it. N1 to N3 are in its text.
