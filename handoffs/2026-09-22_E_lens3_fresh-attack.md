# E8 lens 3 (fresh attack, after repair 2) - build day 8, lane E, at `7fa690b` - 23 September 2026

**Verdict: FAIL.** Three blockers. Every figure below was measured in this session in a detached
worktree at `7fa690b` (a second at `657ef11` for the pre-fix comparison), with
`PYTHONPATH=<worktree>/src` forced and `proofpack.__file__` printed as the worktree's own
`src\proofpack\__init__.py` before any number was trusted. Both worktrees are removed. Nothing
was committed; this note is the only file added to the main tree. Probe scripts and outputs:
`<scratchpad>/lens-E8-r3-fresh-attack/attacks/` (`a_overall.py`, `a2_mask.py`, `b_checker.py`,
`b2_checker.py`, `c_renderer.py`, `c2_render.py`, `d_wiring.py`, `d2_followup.py`, `d3_cli.py`,
`e_packaging.py`, `f_opid.py`, `f_opid2.py`, `my_mutants2.py`; outputs in `attacks/out/`).

Lens 2's four blockers, re-run on their literal inputs: **B1 closed** (a blank `y_pred` on a
table without a score column is excluded and counted: 12 blanks give `excluded_missing_score 12,
analysed 108`, two-by-two `{tp 34, fn 7, fp 17, tn 50}` equal to my numpy count on the non-blank
rows; the 20-blanked-positives table through the CLI prints `18/22 (81.8%) [61.5, 92.7]ᵇᶜ`);
**B2 closed on its class** (the 42,849 swaps of lens 2's enumeration: 0 accepted; every analytic
/ decile-curve pointer `value_ref_unbound`); **B3 closed** (fairness-only criteria.yaml: 1
criterion row, no "No acceptance criteria were declared"); **B4 closed on its six spellings**
(`p a s s`, `p.a.s.s`, `pa-ss`, `fa-il`, `unaccept-able`, `well-cali-brated` each
`free_text_verdict_word`). The three blockers below are new: two sit beside B2 and B4 in the
checker, one in the overall block's key assembly.

## Blockers

### B1 - the checker accepts claims whose template states a different metric or the opposite status from the Number and row they bind (template relabelling and slot order are bound by nothing)

Measured on the synthetic document (70 engine claims, all accepted; `b2_checker.py`,
`b_checker.py` B4). **Accepted**, each a single edit of an engine claim:

- `CL-0062` (`CRITERION_STATUS`, `C_met`, status `met`) relabelled **`CRITERION_NOT_MET_RECORD`**,
  whose skeleton reads "Record of criterion not met: {criterion_id} ..." - a wrong status in the
  sentence; the same relabel is accepted on all nine criterion claims, and `ATTAINABILITY_NOTE`
  on all nine (18 of `b_checker.py` B4's 39 accepted single-field mutations);
- `CL-0001` (`OVERALL_ESTIMATE sensitivity op1`, `/overall/op1/sensitivity`) relabelled
  **`AUROC_ESTIMATE`** ("AUROC was {est} ...") - the sensitivity bound under the AUROC sentence;
  accepted for all 13 overall claims;
- `CL-0061` (`FAIRNESS_GAP`) with the `tpr_gap` and `fpr_gap` pointers swapped, and with all four
  reversed; `CL-0060` (`CALIB_HIERARCHY`) with `oe` and `slope` swapped, and reversed - the
  `{tpr_gap}` / `{oe}` slots would take the other cell (rule 4 checks slot order for
  `SUBGROUP_ESTIMATE_WITH_DIFF` only);
- `CALIB_NA` ("Calibration statistics are not computed because the score was declared as ...")
  with no pointers on this document, whose calibration block is present;
- count templates bound to another count: `SITE_COUNT` to `/flow/rows_read`, `LEDGER_STATEMENT`
  to `/criteria_results/0/value` and `/fairness/bound`, `DUPLICATES_NOTE` to `/manifest/seed`,
  `FLOW_COUNTS` with its seven flow pointers reversed, and `FLOW_COUNTS` carrying `metric_id
  sensitivity`, `op1` and `subgroup sex = F` over `/flow/analysed` (the orchestrator's open
  observation; `tests/test_e8_repair2.py::test_a_claim_bound_to_a_documented_scalar_must_state_not_assessable`
  asserts the `metric_id sensitivity` / `op1` variant is accepted).

Every one of these is also accepted at `657ef11` (same script, base worktree): the defect is E8's,
not repair 2's; lens 1 and lens 2 fed single-pointer swaps and never a permutation or a relabel
inside the bound set. Graded by the rule this lens was given (a corpus case accepted; a wrong
status reaching a claim). Nothing on today's page is wrong because of it: T8 prints no claim
sentence and no sentence renderer exists yet - if E9 fills slots by pointer facet rather than
position, the four permutation cases become harmless; the relabels and `CALIB_NA` do not.

Sentence violation: `checker.py` rule 4 docstring "every pointer's operating point equals the
claim's - null equals null, so `AUROC_ESTIMATE` with `op1` is refused" - `AUROC_ESTIMATE` with
`op1` bound to `/overall/op1/sensitivity` is accepted.

Repro (worktree root, `PYTHONPATH` forced):
`python -c "import sys,copy;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_criteria;from test_criteria import CRITERIA,FAIRNESS,cohort_with_a_thirty_row_site;from proofpack.narrate import checker,claims;d=assemble(cohort_with_a_thirty_row_site(),make_criteria(criteria=copy.deepcopy(CRITERIA),fairness=FAIRNESS));e=claims.build_claims(d);print([checker.check([c],d).verdicts[0].accepted for c in ({**e[0],'template_id':'AUROC_ESTIMATE'},{**e[61],'template_id':'CRITERION_NOT_MET_RECORD'})])"`
prints `[True, True]` (`e[61]` is `CL-0062`, status `met`).

### B2 - nine further homoglyph spellings of listed words pass `free_text`

Accepted (`b2_checker.py` N1): `pɑss` (Latin alpha U+0251), `unbiɑsed`, `faiI` (capital I for l),
`ƒail` (U+0192), `faiǀ` (U+01C0), `gօօd` (Armenian oh U+0585), `ϲonsistent` (Greek lunate sigma
U+03F2), `Ꮲass` (Cherokee U+13E2), `rneets`. Also accepted and not counted as blockers:
`\u202essap` (the override is `Cf` and dropped; the word reads `ssap`), `ssɐd`, `unsafe`.
Rejected, 23 of my new cases: fullwidth `ｐａｓｓ`, math-bold `𝐩𝐚𝐬𝐬`, circled `ⓟⓐⓢⓢ`, U+2060,
U+180E, U+3164, U+034F, U+FE0F and a tag character inside `pass`, `p̶a̶s̶s̶`, `certiﬁed`,
`FDA–cleared`, `C.F.R.`, `s a f e`, `guіdance` (Cyrillic i), `ΡΑSS`, `pa'ss`, `p_a_s_s`,
`pa/ss`, `the model is good`, `ıs ok`, `mеt`, `ᴜnbiased`. The rule as built maps a closed list of
confusables; the tail is open. Graded by the rule given (an accepted corpus case is a blocker);
my view, as lens 2's, is that the decision on what the gate defends against is Josh's
(needs-from-Josh 2 of the repair-1 note), and `free_text` is `null` on every engine claim.

Sentence violation: `_tokens` docstring "The runs of letters and hyphens in normalised text" -
`ɑ` is a letter and ends a run (`pɑss` gives the tokens `p`, `ss`).

Repro: `python -c "from proofpack.narrate.checker import free_text_reason as f;print([f(t) for t in ('p\u0251ss','faiI','\u0192ail')])"` prints `[None, None, None]`.

### B3 - an operating point declared with id `threshold_free` loses its whole block; a criterion on it prints `not assessable` for a metric that was computed

`overall_block` writes `out[op.id] = block` and then `out["threshold_free"] = {...}` over it.
Measured (`f_opid2.py`, plain `main` with a test-only licence, 200 rows, `C1 sensitivity
ci_lower_bound >= 0.5` at operating point `threshold_free`): `exit 0`, no warning, `overall` keys
`['threshold_free']` holding `auprc, auroc, auroc_wald, prevalence, roc` only (no sensitivity, no
two-by-two), `criteria_results [('C1', 'not_assessable', 'metric_not_computed', None)]`, T8 written
with that row, 46 claim rejections in section 7. The declaration is accepted (no H08). The same
assignment is at `ab729d3` (E7) and `86b5fdd` (E8 item 1) rewrote the function and kept it: graded
as a wrong status reaching the page. Ids `two_by_two` and `0` run clean (60 claims, 0 rejected).

Repro: `python -c "import sys;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_cohort,make_criteria;c=make_criteria(criteria=[],fairness=None);c['operating_points'][0]['id']='threshold_free';d=assemble(make_cohort(n=200),c);print(sorted(d['overall']['threshold_free']))"`
prints `['auprc', 'auroc', 'auroc_wald', 'prevalence', 'roc']`.

## Non-blocking (record and carry)

1. **Repair 2 changed the score path and no test pins it.** A `y_pred` equal to a declared
   indeterminate value now marks the row indeterminate *beside a score column* too: 120 rows,
   12 `y_pred = indeterminate`, `report_both_ways` -> at `7fa690b` `indeterminate 12, analysed
   108`, AUROC `0.8817` (41 / 67); at `657ef11` `indeterminate 0, analysed 120`, AUROC `0.8632`
   (42 / 78). Consistent with D1 section 2 (the 0/1 column is "an alternative to listing
   indeterminate values in `y_true`/`y_pred`"), but my mutant restricting the new rule to
   no-score tables (`mask_ypred_indet_only_without_score`) **survives `-m day8` and the full
   suite** (`1012 passed, 1 skipped, 1 xfailed`), and the note's "CLI / output changes S4 must
   know" does not list it.
2. **Mutants of my own** (`my_mutants2.py`, ten, `-m day8`, tree clean after): 6 killed; survived:
   the one above; `checker_smallcap_s_unmapped` (U+A731 `ꜱ` dropped from `CONFUSABLES`; no test
   feeds it; non-equivalent); `checker_auroc_gap_exemption_any_op` and
   `html_has_criteria_rows_only` (equivalent on engine documents: the `auroc_gap` shape carries no
   operating point; every criteria entry yields a row).
3. **Sentence violations, wording only.** `gates.py` `gate_h02` docstring "a blank cell ... is not
   read here - `analysis_mask` excludes it and counts it": a blank `y_pred` beside a score column is
   neither (12 blanks -> `excluded_missing_score 0, analysed 120`). `schema_v1.json` `y_pred`
   description and README "a blank `y_pred` ... counted under `flow.excluded_missing_score`": a row
   whose `y_true` is also blank counts under `excluded_missing_label` (12 blank `y_pred`, 6 of them
   on blank-label rows -> `excluded_missing_label 6, excluded_missing_score 6`).
4. **`FLOW_COUNTS`' skeleton says "{excluded_missing_score} lacked a score"**; on a `y_pred`-only
   table those rows lack a `y_pred`. Not rendered today.
5. **Operating-point ids `a/b` and `op~1`**: 58 of 60 engine claims rejected
   `operating_point_mismatch` (the facet regex reads the `~1`-escaped pointer). False refusals,
   section 7 counts them; reachable only by such an id.
6. **A subgroup level whose every row is excluded vanishes** from `subgroups` (sex `F`, 50 rows,
   every `y_pred` blank -> only `M` listed; the same with every score `NaN`, so pre-existing
   day-4 behaviour now reachable on the `y_pred` path). A DEC-08 question for the E9 note.
7. Carried from lens 2, still reproducing: section 7 prints the three status words with no
   criteria; two accepted claims on one slot are both kept (`['CL-0001', 'CL-9999']`); `Roman IV`,
   `ninety`, `the guidances` accepted; `declared(1e22)` positional; `--format HTML` folds to
   `html`; the no-licence watermark is `LICENCE EXPIRED - not for submission`.

## Could not break

- **The overall block.** `git diff 7b2ca2a 7fa690b -- src/proofpack/stats/` is empty; constants
  `DEFAULT_B 2000`, `DEFAULT_SEED 20240101`, `DEFAULT_LEVEL 0.95`, `MIN_UNITS_PER_STRATUM 2`,
  `MAX_FROZEN_VARIANCE_SHARE 0.2`, `MIN_USABLE_FRACTION 0.9`, `CLIP_EPS 1e-12`. Clustered, 300
  rows in 100 cases (seed 7): engine two-by-two `{tp 69, fn 18, fp 30, tn 183}` equals my numpy
  count; sensitivity, specificity, PPV, NPV, accuracy, prevalence deviation `0.00e+00` on all six,
  each `cluster_bootstrap_percentile` with `wilson_refused_clustered`; `proportion_ci` with the
  same cell key equal on five; youden, balanced accuracy, LR+, LR-, DOR, F1, MCC each
  `clustered_data_analytic_ci_invalid`, `ci (None, None)`, `method none`. One `site` stratum on
  the same rows: estimates equal, intervals differ by 1.48e-3 to 6.24e-3 (own bootstrap stream, as
  the docstring says). One cluster: `insufficient_clusters`; two clusters and every row its own
  cluster: intervals present. Clustered `y_pred`-only with every seventh `y_pred` blank: 43
  excluded, `{tp 61, fn 14, fp 26, tn 156}` equal to my count. `y_pred`-only one-class,
  all-1, all-0, integer column: two-by-two equal to my count each. Missing tokens ` `, `NULL`,
  `nan`, `N/A`, `NaN`, tab, `None`, `na` -> excluded; `none`, `-`, `.`, `?` -> H02, exit 3 through
  the CLI. Flow identity holds in every case (`120 = 0+6+6+0+108`, `12+0+0+0+108`,
  `0+0+6+6+108`). All blank -> `analysed 0`, no raise. Integer indeterminate `9` -> 12
  indeterminate. 60 i.i.d. Wilson cells of the synthetic run re-derived from k/n with my own
  formula: worst deviation `2.22e-16`; four `y_pred`-only page cells by hand: `37/47 (78.7%)
  [65.1, 88.0]`, `21/24 (87.5%) [69.0, 95.7]`, `18/22 (81.8%) [61.5, 92.7]`, `34/41 (82.9%)
  [68.7, 91.5]`, each equal to the page.
- **The checker on the literal cases.** Lens 2's fifteen named cases all rejected as lens 2
  listed; `metric_id null` -> `metric_mismatch`; scalar under an estimate template, swapped
  difference slots, off-template difference block, analytic pointers -> `value_ref_unbound`;
  complement difference with `reference` still `sex = M` -> `reference_mismatch`; leading-zero
  index aliases `/subgroups/00/...`, `/fairness/gaps/00/...` -> `value_ref_unresolved`.
- **The renderer.** Lens 2's thirteen payloads rerun (`c_renderer.py`): no raw tag, `{{ 7*7 }}`
  literal, U+202E as `&#x202e;` (111), no NUL byte, 10k string and emoji verbatim; page 0
  `@import` / `url(` / `<link` / `<script` / `http:` / `https:`, 19 hex and 7 px values all
  tokens; footers 3/3/3 on 0, 1 and 40 rows; typed reason prints `n.e. (insufficient_positives)`
  with no `0.75` / `75.0`; `[unverified` 8 times; duplicate id and `level: *` rows by position;
  three rejections in section 7; draft label beside all 14 FDA AI-DSF mentions and in 3
  structured `guidance_refs`; watermarks `TRIAL` / `LICENCE EXPIRED` / `NO LICENCE` 4 tags each;
  22 criteria rows re-derived, 0 mismatches; golden 39,800 bytes, equal; forbidden-word walk 0
  hits. `y_pred`-only page: `C2 brier` prints `calibration_suppressed` and `reason:
  no_score_column`, `C3 auroc` prints `n.e. (not_computed_this_run)`.
- **The wiring.** valid -> exit 0, 70 claims, validates; grace -> HTML, watermark 7 times;
  expired -> exit 4, JSON only; no file -> exit 4; trial -> `TRIAL` 7; `--templates T1` -> exit 0
  and the typed line; `docx` / `pdf,json` / `T9` -> exit 5, no directory; `--offline` with four
  socket entry points raising -> 0 calls; two runs differ only in ledger / manifest run id and the
  seven expected T8 line kinds. Plain CLI, no licence, E7 `e2e_shell`: exit 4, `run.json`
  253,943 bytes in Git Bash and in PowerShell 5.1; `doctor --offline` exit 0.
- **Packaging.** jinja2, markupsafe, scipy, cryptography, statsmodels, sklearn hidden: all ten
  modules import, none loads, `environment()` raises `RendererUnavailable` naming `jinja2`. Wheel
  built (`uv build`), three templates and `_schema/tokens.json` in it, `Requires-Dist:
  jinja2>=3.1`; fresh venv, no `.pth`, `proofpack.__file__` and `tokens.json` inside the venv with
  and without `PYTHONNOUSERSITE=1`. `uv lock --check --offline` rc 0 (63 packages); `ci.yml` runs
  `uv sync --all-groups --locked` twice. `test_render_theme.py` 13 passed.
- **Suite and regression.** `7fa690b` worktree: `1012 passed, 1 skipped, 1 xfailed`; day8 224,
  day7 139, day6 285, day5 54, day4 182, day3 29 + 1 xfailed, day2 40, day1 59 + 1 skipped;
  PowerShell day8 224; `ruff check` clean; `ruff format --check` 132 files. Committed sweep
  `--marker day8`: `41 planted, 41 killed, 0 survived; 297 s`; `--list` 212 lines. Pre-fix at
  `657ef11` with the three changed test files and 15 corpus files copied in:
  `test_e8_repair2.py` 7 failed, 2 passed (the two the note names); three files 27 failed, 137
  passed; the first `E` lines match the docstrings (`assert (0 == 60)`, 13,962 swaps,
  "No acceptance criteria were declared").

## Could not check

- The bidi override inside `.customer-text` in a browser; CI on the reference platform (never
  pushed); a real-licence plain-CLI HTML run (no signing key).
- How E9's sentence renderer fills slots (by position or by facet): B1's permutation cases
  depend on it; the relabel and `CALIB_NA` cases do not.
- DOCX, T1, T7 and the site's pinned engine `a0c9abc` (outside E8).

## Sentences I refused to write

- "The checker binds every claim to its Number." Refused: B1.
- "free_text cannot carry a verdict word." Refused: B2.
- "The overall block is correct on every declaration." Written instead: the pooled counts on
  one 300-row clustered fixture at `0.00e+00`, and B3.
- "Repair 2 changes nothing beside a score column." Refused: non-blocking 1.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
git worktree add --detach <path> 7fa690b && cd <path>
PYTHONPATH=<path>/src python -c "import proofpack;print(proofpack.__file__)"   # must print <path>
PYTHONPATH=<path>/src python -m pytest -q -p no:cacheprovider                  # 1012 passed, 1 skipped, 1 xfailed
PYTHONPATH=<path>/src python scripts/mutation_sweep.py --marker day8           # 41 planted, 41 killed, 0 survived
S=<scratchpad>/lens-E8-r3-fresh-attack/attacks     # scripts read LENS_WT; e_packaging.py / my_mutants2.py hard-code wt
LENS_WT=<path> PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/b2_checker.py   # B1, B2
LENS_WT=<path> PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/f_opid2.py      # B3
LENS_WT=<path> PYTHONPATH=<path>/src PYTHONIOENCODING=utf-8 python $S/a2_mask.py      # N1 (R2), N3, N6
PYTHONIOENCODING=utf-8 python $S/my_mutants2.py                                      # 6 killed, 4 survived
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force <path>
```

## What the repair needs

B1: bind the template to the metric family it names (`AUROC_ESTIMATE` -> `auroc`, `CALIB_*` ->
calibration cells, `CALIB_NA` only where `calibration` is null), bind `CRITERION_NOT_MET_RECORD`
to `not_met` rows, bind slot order for `FAIRNESS_GAP` and `CALIB_HIERARCHY` (or record that E9
fills by facet), and give each count template the scalar paths it may read; corpus cases for each.
B2: Josh's decision on the gate's scope, then either a wider confusable map or the recorded
limit. B3: refuse an operating-point id equal to `threshold_free` at declaration (typed H08) with
a test; this is `overall_block`, a statistical gate - DEC-12 (i) applies.
