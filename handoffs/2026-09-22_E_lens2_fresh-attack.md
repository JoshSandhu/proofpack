# E8 lens 2 (fresh attack, after repair 1) - build day 8, lane E, at `657ef11` - 23 September 2026

**Verdict: FAIL.** Four blockers. Every figure below was measured in this session in a
detached worktree at `657ef117974f9543faea61be01b2469d5155bb4e` (a second at `29fc04e` for
the pre-fix comparison), with `PYTHONPATH=<worktree>/src` forced and `proofpack.__file__`
printed as the worktree's own `src\proofpack\__init__.py` before any number was trusted.
Both worktrees are removed. Nothing was committed; this note is the only file added to the
main tree. The probe scripts and their outputs are under
`<scratchpad>/lens-E8-r2-fresh-attack/attacks/` (`a_overall.py`, `b_checker.py`,
`c_renderer.py`, `d_wiring.py`, `d2_followup.py`, `e_packaging.py`, `my_mutants.py`;
outputs in `attacks/out/`); each one-line repro below is a line those scripts ran.

Lens-1's five blockers: B1, B2, B3, B4, B5 each close on the literal inputs lens 1 fed
(the 18 named claims and 580 sibling swaps are rejected; the 16 spellings are rejected; the
`yes`/`no` table is H02 and exit 3; `0.4275` prints `0.4275`; a `criteria.yaml` without
`prior_version` renders and exits 0). Two of them reopen one step to the side: B1 through a
pointer shape rule 4 does not read (blocker B2 below) and B3 through a `y_pred` cell that is
blank or carries the indeterminate value (blocker B1 below).

## Blockers

### B1 - a blank or indeterminate-valued `y_pred` cell in a `y_pred`-only table is scored as "predicted negative": a wrong number and a wrong status reach `run.json` and T8

`gate_h02` skips `None` (`if v is not None`) and admits `indeterminates.values`; `analysis_mask`
excludes a row for a missing `y_true` or a missing `score` and never reads `y_pred`; `overall_block`
then computes `pred = y_pred == decl.positive`, which is `False` on a blank and on `NA`. Measured
through the plain CLI (`d2_followup.py` D9b, valid test-only licence, 120-row `y_pred`-only table,
the `y_pred` of 20 positives blanked, `C1 sensitivity ci_lower_bound >= 0.8`):

- `exit 0`, `T8.html` written, `halts []`, `warnings []`, `flow {rows_read 120,
  excluded_missing_score 0, analysed 120}`;
- `overall.op1.two_by_two {tp 18, fn 24, fp 20, tn 58}`; my numpy count on the 100 non-blank rows
  `{tp 18, fn 4, fp 20, tn 58}`;
- `sensitivity 18/42 est 0.4286` where the non-blank rows give `18/22 = 0.8182`; the page's
  observed cell `18/42 (42.9%) [29.1, 57.8]ᶜ` beside `criterion not met`.

With every tenth `y_pred` blanked instead (`a_overall.py` A5, 12 blanks, 1 of them a positive):
`{tp 34, fn 8, fp 17, tn 61}` against `{tp 34, fn 7, fp 17, tn 50}` on the non-blank rows;
`flow.analysed 120`. With `y_pred` carrying the declared indeterminate value `NA` under
`report_both_ways` (`d2_followup.py` A6b): `gate_h02` returns `None`, `flow.indeterminate 0`,
the 12 `NA` rows land in `fn` / `tn`, `indeterminate_as_positive` is `None`. Beside a score
column a blank `y_pred` is harmless (the score decides; A9).

Sentence violations: `gates.py` `gate_h02` docstring "`y_true` and, when the column is present,
`y_pred` hold only the declared classes and indeterminate values" - a column holding 12 blanks
passes; README "halts H02 naming the column, before any statistic" and the repair note "any value
outside classes ∪ indeterminates.values is H02" - a blank is outside both and no HALT fires.

Repro (worktree root, `PYTHONPATH` forced, `PYTHONIOENCODING=utf-8`):
`python -c "import sys;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_cohort,make_criteria;c=make_cohort(n=120,with_y_pred=True);del c['score'];c['y_pred']=[None if i%10==0 else v for i,v in enumerate(c['y_pred'])];d=assemble(c,make_criteria(criteria=[],fairness=None));print(d['flow']['analysed'],d['overall']['op1']['two_by_two'])"`
prints `120 {'tp': 34, 'fn': 8, 'fp': 17, 'tn': 61}`.

### B2 - rule 4 reads eight pointer shapes; 225 of the synthetic document's 418 Numbers sit at other paths and a claim bound to one of them is bound by nothing (lens-1 B1 reopened)

`pointer_facets` returns `None` off the eight shapes and rules 4 and 6 `continue` on `None`.
Every day-4 cell's `analytic` Number, every `decile_curve[i].observed` Number and every
`diff_vs_*/auroc/number` is off the shapes (`b_checker.py` B3: 418 Number paths, 225 off-shape,
39 distinct kinds). Measured on the synthetic document (70 engine claims, all accepted):

- `SUBGROUP_ESTIMATE` for `age = 40-65` (row 1) bound to
  `/subgroups/0/metrics/op1/sensitivity/analytic` (row 0, `age = 0-40`): **accepted**;
- `OVERALL_ESTIMATE sensitivity op1` bound to `/subgroups/0/metrics/op1/sensitivity/analytic`,
  to `/calibration/oe/analytic`, to `/fairness/gaps/0/operating_points/op1/tpr_gap/analytic`,
  to `/calibration/decile_curve/0/observed/number`: each **accepted**;
- every `value_ref` of every engine claim swapped to every other Number path in the document:
  **13,962 of 42,849 swaps accepted** (the builder's test enumerates siblings within one block
  and finds 0 of 580; both figures are right for their enumerations).

Accepted shapes sharing the cause, each run (`b_checker.py` B2, B4): `OVERALL_ESTIMATE` with
`metric_id null` bound to `/overall/op1/npv` (documented in the docstring as unbound - so a
claim can drop its metric and take any Number); `OVERALL_ESTIMATE sensitivity` with relation
`not_assessable` bound to `/overall/op1/two_by_two/tp` or `/flow/analysed` (a full sensitivity
Number exists; the claim says it was not assessable); `SUBGROUP_ESTIMATE_WITH_DIFF` with the
estimate and difference pointers swapped (the sentence's `{est}` slot would take the difference);
the same claim with `reference null` or with `diff_vs_complement` while `reference` still names
`sex = M`; `AUROC_ESTIMATE` with `operating_point op1`; `template_id` changed from
`OVERALL_ESTIMATE` to any of 20 templates outside the seven rule 4 knows (`PAIRED_DIFF`,
`PSI_RESULT`, `PERIOD_METRIC_ROW`, `LEDGER_STATEMENT`, ...): 260 accepted on the 13 overall
claims, 285 on the subgroup claims, 18 on the criterion claims (8,988 single-field mutations,
685 accepted, every one of them one of these shapes). Nothing on today's page is wrong because
of this: T8 prints no claim sentence.

Sentence violations: `checker.py` rule 6 docstring "every Number pointer of a claim without one
reads an overall or calibration path (`subgroup_mismatch`)" - the analytic subgroup pointer above
is accepted on a claim without a subgroup; the repair note "The rule-5 sentence 'the right number
attached to the wrong subgroup' is now true for every pointer shape" and "a claim without a
subgroup binds only overall / calibration paths" - false for the shape above. The note's open
question 2 names the cause; it is a defect, not a question, because the corpus is the acceptance
test and this is the lens-1 B1 class.

Repro: `python -c "import sys,copy;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_criteria;from test_criteria import CRITERIA,FAIRNESS,cohort_with_a_thirty_row_site;from proofpack.narrate import checker,claims;d=assemble(cohort_with_a_thirty_row_site(),make_criteria(criteria=copy.deepcopy(CRITERIA),fairness=FAIRNESS));c=copy.deepcopy(claims.build_claims(d)[0]);c['value_refs']=['/subgroups/0/metrics/op1/sensitivity/analytic'];print(checker.check([c],d).verdicts[0].accepted)"`
prints `True` (the claim is `OVERALL_ESTIMATE sensitivity op1`, no subgroup).

### B3 - a `criteria.yaml` with a fairness bound and no `criteria` list yields a `not_met` row in `criteria_results` and a page that says "No acceptance criteria were declared"

`t8_context` sets `has_criteria = bool(declarations.criteria)`; `criteria.py` emits the
`fairness:<criterion>` row from the fairness block whatever the `criteria` list. Measured through
the plain CLI (`d_wiring.py` D10, `make_criteria(criteria=None, fairness=FAIRNESS)`, the 400-row
fixture): `exit 0`, `criteria_results [('fairness:tpr_gap', 'not_met')]`, the console line
`criteria rows: 0 met, 1 not met, 0 not assessable`; `T8.html` prints "No acceptance criteria
were declared; estimates and intervals only.", 0 `criterion-row` elements, and section 7's
`criteria_not_met` cell `1` on the same page. A criterion status run.json carries does not reach
the table, and the caption contradicts the count two sections below it. The output schema
validates the document. E8 code (`has_criteria`), untouched by the repair, reachable by any
customer who declares a fairness bound without a `criteria` list.

Repro: `d_wiring.py` section D10; or delete the `criteria:` list from the synthetic criteria.yaml,
keep `fairness.bound`, run, and grep `T8.html` for `No acceptance criteria were declared`.

### B4 - six further spellings of listed verdict words are accepted in `free_text`

Graded by the rule this lens was given (an accepted corpus case is a blocker; `p a s s` is one of
the fifteen cases named for this round). On an accepted `OVERALL_ESTIMATE` claim
(`b_checker.py` B1), **accepted**: `p a s s`, `p.a.s.s`, `pa-ss`, `fa-il`, `unaccept-able`,
`well-cali-brated` (`_words` splits on the hyphen, so `pa` and `ss` are the tokens; a space or a
full stop does the same). Rejected: the lens-1 twelve, `passing`, `failed`, `un-biased`,
`PASSED`, `nonINFERIOR`, `well calibräted`, `p4ss`, `‰`, `&sect; 3` (the digit), `guidance_ref`.
This is lens-1 B2's class with an open-ended tail; the rule as built matches whole tokens after
normalisation and no rule can close "a letter, a separator, a letter" without a decision on what
`free_text` is for (needs-from-Josh 2 of the repair note stands; my view is that the gate is
against accidental verdict words, not a human evading it, and that the decision belongs to
Josh - but the rule I was given grades it here).

Repro: `python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('p a s s'),f('pa-ss'),f('fa-il'))"` prints `None None None`.

## Non-blocking (record and carry)

1. **`declared()` spells a float positionally where `run.json` spells it with an exponent.**
   `fmt.declared(1e22)` is `10000000000000000000000` (run.json: `1e+22`); `5e-324` prints 324
   digits; `-0.0` prints `−0.0`; `inf` prints `Infinity` (unreachable: `canonical_json` refuses).
   The docstring's "every digit run.json carries" holds; "one threshold on one page" (html.py)
   does not for such a value, since the YAML echo prints `1.0e+22`. Plausible thresholds
   (`0.4275`, `0.30000000000000004`, `1.0`, `100.0`) print as run.json spells them.
2. **Section 7 prints the three status words on a document with no criteria at all**
   (`c_renderer.py` C12: `criterion met` / `criterion not met` / `not assessable` as row headers
   with count 0). D4 section 14 "criteria gating: with criteria absent: no status word anywhere".
   The day-6/7 verdict walk allows them inside `.status`. E8-era, not the repair's.
3. **Two accepted claims with different ids on one slot are both kept by `resolve`**
   (`final ids ['CL-0001', 'CL-9999']`, no rejection): section 7's "claims generated" counts the
   slot twice. The `filled` set governs substitutes only, as the docstring says.
4. **Three of my eight mutants survive `-m day8`** (`my_mutants.py`; the committed sweep is
   `28 planted, 28 killed, 0 survived; 178 s`, tree clean after): rule 6 refusing an off-shape
   pointer on a subgroup claim (no test feeds one - B2); `_declaration_for` wrapping an
   out-of-range `declaration_index` (no test feeds one; unreachable from the engine); H02 on
   `y_pred` skipped when a score column is present - the README and the note say "with or without
   a score column" and the test feeds the without case only. My A8 run shows it fires with a
   score (`HALT H02 {'column': 'y_pred', 'n_unknown_values': 2, 'n_declared': 2}`), so the
   sentence is true and unpinned. The other five are killed by the named tests.
5. **`test_the_clustered_overall_prevalence_is_the_pooled_positive_share` passes at `29fc04e`**
   (`42 failed, 111 passed` there with the three files and thirty corpus files copied in; the note
   says 41 + the two-operating-point test, which is the same 42). The note declares it as a pin for
   `run_prevalence_wrong_key`, not a regression test; recorded, not graded as the blocker class.
6. **Free-text words the rule does not name are still accepted**: `Roman IV`, `ninety`,
   `the guidances` (lens-1 FA-N3; needs-from-Josh 2).
7. **`declaration_index: true` reads entry 0** (`isinstance(True, int)`); unreachable (the schema's
   `integer` excludes booleans and the engine writes `int | None`).
8. **Figures that differ from the note by one**: `ruff format --check` reports `129 files already
   formatted` in the worktree (note: 130). The golden is `i/lf w/crlf` in the working tree; the
   test normalises both sides; regenerated here it is 39,800 bytes LF and equal.
9. **A `y_true` of `NA` declared as the indeterminate value is counted as
   `excluded_missing_label 12, indeterminate 0`** (`d2_followup.py` A6c): the day-1 loader reads
   `NA` as missing before the indeterminate rule sees it. Outside E8; recorded so the next lens
   does not chase it under B1.
10. **`check` docstring "reads no environment"**: it reads two packaged files
    (`output_schema_v1.json`, the guidance map). Wording.
11. **`--format HTML`** yields `["html"]` and still writes `run.json` (`write_run` is
    unconditional); `--templates ''` gives T8 while `--format ''` gives json only (lens-1 N9,
    unchanged). The no-licence watermark is `LICENCE EXPIRED - not for submission` (DEC-48's
    `NO LICENCE` string is E9's; rendered as the manifest's string, as this lens was told).

## Could not break

- **The overall block (statistical gate).** `git diff 29fc04e 657ef11 -- src/proofpack/stats/`
  is empty; the seven day-4/5/6 constants read `DEFAULT_B 2000`, `DEFAULT_SEED 20240101`,
  `DEFAULT_LEVEL 0.95`, `MIN_UNITS_PER_STRATUM 2`, `MAX_FROZEN_VARIANCE_SHARE 0.20`,
  `MIN_USABLE_FRACTION 0.90`, `CLIP_EPS 1e-12`. 300 rows in 100 three-row cases (seed 7): the
  engine's `{tp 69, fn 18, fp 30, tn 183}` equals my numpy count; sensitivity, specificity, PPV,
  NPV, accuracy, prevalence equal the pooled 69/87, 183/213, 69/99, 183/201, 252/300, 87/300
  with deviation `0.00e+00` on all six, every one `cluster_bootstrap_percentile` with
  `wilson_refused_clustered` and `n_cases`; `proportion_ci` called by me with
  `_overall_cell_key("op1", <metric>)` on `_conditioned` rows gives a dict equal to the block's on
  all five; youden, balanced_accuracy, lr_pos, lr_neg, dor, f1, mcc each
  `clustered_data_analytic_ci_invalid`, `ci (None, None)`, `method none`; AUROC
  `cluster_bootstrap_percentile` / `delong_refused_clustered`, `auroc_wald None`, 301 ROC points;
  `threshold_free.prevalence == op1.prevalence`. One `site` stratum on the same rows, seed and B:
  estimates equal, intervals differ by 1.5e-3 to 6.2e-3 (own bootstrap stream per the docstring).
  One cluster: `insufficient_clusters`, no interval; two clusters and every row its own cluster:
  intervals present; `json.dumps(allow_nan=False)` succeeds on each. `y_pred`-only: normal,
  one-class `y_true`, all-1, all-0, integer columns - the two-by-two equals my hand count in each,
  `threshold_free.auroc not_computed_this_run`, `suppressed_reason no_score_column`. `y_pred`
  `True`/`False` and `1.0`/`0.0` beside classes `1`/`0`: H02 naming `y_pred`; ` 1` is stripped at
  ingest and matches. `yes`/`no` beside a score column: H02 (before H04).
- **The checker on the literal cases.** All 70 engine claims accepted; every swap to a sibling
  metric rejected (`metric_mismatch`); the fifteen named cases: `раss`, ZWJ, `passing`, `failed`,
  `un-biased`, `‰`, `&sect; 3`, `guidance_ref`, a list value_ref (`value_ref_not_a_number`), a
  trailing slash / a double slash / no slash (`value_ref_unresolved`), `met ` and `MET`
  (`status_not_in_enum`), `overall_estimate` (`template_unknown`), a sibling metric
  (`metric_mismatch`), a difference claim with one cell twice (`value_ref_duplicate`), `>=` on the
  fairness row declared `<=` (`comparator_mismatch`), `CL-0001 ` and `cl-0001`
  (`claim_id_invalid`), a lower-case guidance id (`guidance_ref_unknown`), a subgroup level `0`
  (`subgroup_not_in_document`); `free_text` non-strings all `free_text_digit`; `[]` on a document
  with criteria `no_claims_for_criteria`; `None` `not_an_object`. 8,988 single-field mutations:
  every `metric_id` swap to another metric rejected (only `null` accepted - B2), every
  `operating_point` swap rejected except `op1` on `AUROC_ESTIMATE`, every `subgroup`, `status`,
  `relation`, `comparator_id` and `criterion_index` swap rejected, every `reference` swap rejected
  except to `null`. The corpus is 115 files covering all 42 codes.
- **The renderer.** Thirteen payloads (`<script>`, `<img onerror>`, `&lt;`, `{{ 7*7 }}`,
  `{% raw %}`, U+202E, NUL, a 10,000-character string, an emoji, `]]>`, `</td></tr></table><b>`,
  `javascript:`, a literal `&#x202e;`) into model name / version / prior version, every
  criterion's id, author, date and justification, the fairness author and justification, the
  operating-point source and provenance, the reference-standard description, the prevalence label
  and source, the clustering declarer, the criteria rows' ids and scope levels, the `site` level
  labels, the watermark, the run id, a warning code and a rejection row: no raw tag in the bytes,
  `&lt;script&gt;` present, `&amp;lt;` for the customer's `&lt;`, `{{ 7*7 }}` and `{% raw %}`
  literal (no `49`), U+202E absent and `&#x202e;` present (111 times, the title included), the NUL
  byte absent from the bytes (lens 1 saw it raw at `29fc04e`; not present here), the 10k string
  verbatim, the emoji verbatim, the customer's own `&#x202e;` doubled to `&amp;#x202e;` and not
  decoded to the override. Page: 0 `@import`, `url(`, `<link`, `<script`, `http:`, `https:`; 19
  hex values all token values; px literals `1 2 3 4 6 8 17` all token values; font families
  `var(--pp-type-text)` / `var(--pp-type-mono)`; 0 `@font-face`; the templates' only such strings
  are in `base.html`'s comment. Footers 3 / 3 / 3 on 0, 1 and 40 criteria rows (one print footer);
  `render_pages` 0/1/5. A typed reason prints `n.e. (insufficient_positives)` with no `75`; a
  suppressed cell `‡` and section 7 counts 1; `[unverified` eight times from two plantings; two
  `C_dup` entries and a `level: *` entry print `Author One`, `Author Two`, `Author Three ×3`, the
  fairness row `Dr F.`, justifications `first, second, third, third, third, intended-use
  population`; three rejections (`relation_mismatch`, `metric_mismatch`, `missing_key`) each in
  section 7 with counts 66 / 3 / 2 equal to `len(final)`, `len(rej)` and the substituted sum; the
  FDA AI-DSF draft label stands beside all 14 mentions (the 4 unlabelled mentions are the PCCP
  final guidance and the disclaimer's own item 5) and in the three structured `guidance_refs`;
  watermarks `TRIAL`, `LICENCE EXPIRED - not for submission`, `NO LICENCE - not for submission`
  each 4 tags and 2 stamps, `None` and `""` 0 with the "No synthetic" line. Twenty-two criteria
  rows on my own criteria.yaml (six proportions, AUROC, Brier, O:E, IPA, slope, intercept,
  `level: *` on site and sex, Youden, LR+, F1, a gap): all 22 observed cells, 22 Value cells, 22
  Compared cells and 22 `n` cells equal my own D4 section 1.2 formatting from run.json character
  by character (`96/128 (75.0%) [66.8, 81.7]`, `0.835 [0.795, 0.876]`, `−0.749 [−1.005, −0.493]`,
  `8/13 (61.5%) [35.5, 82.3]ᵇᶜ`, `n.e. (analytic_ci_unavailable)`, `+7.0 [−7.9, +21.7]`); every
  digit run in the page's text nodes traces to a run.json value, a count, a section number or the
  disclaimer's citations (the seven "untraced" are the `04` of `2024-12-04` and `2026-09-18T00` split
  by my regex). The golden regenerates to 39,800 bytes LF, equal; two renders identical; the
  forbidden-word walk outside `.customer-text`, `.status` and the disclaimer: 0 hits on both
  documents; `model` absent / `name None` / `declarations` absent render (` v `).
- **The wiring** (test-only licence through `main(..., registry=)`): valid → exit 0,
  `T8.html` + `ingest_report.json` + `run.json`, 20 keys, 70 claims, 0 rejections, 3 guidance
  refs, `declaration_index [0, 1, 2, 2, 2, 3, 4, 5, None]`, validates with 0 errors, 40,145 bytes,
  no CRLF, no BOM; grace → exit 0, HTML with the watermark 7 times; expired past grace → exit 4,
  JSON only, the typed "HTML not written" line; no file → exit 4, JSON only; trial → `TRIAL` 7
  times; `--templates T1` → exit 0, no document, the "not built in E8" line; `--format docx`,
  `pdf,json`, `--templates T9` → exit 5, no directory, the typed line; `--offline --format
  json,html` with `socket.socket`, `create_connection`, `getaddrinfo`, `urlopen` raising → exit
  0, 0 calls, 37 proofpack modules loaded, none holding a socket / urllib / http name; two runs
  → top-level blocks differing `ledger`, `manifest`; manifest keys `duration_s`, `ledger_count`,
  `run_id`; claims, rejections, guidance_refs, criteria_results equal; the two `T8.html` differ in
  10 lines, all run-id, duration, ledger-count, acceptance-runs or header lines; `--json-log`
  carries the six E8 keys. Plain CLI, no licence, the E7 `e2e_shell` fixture, both shells:
  identical six lines ending `HTML not written: licence refused (no_file); run.json only ...` /
  `Next step: proofpack licence install FILE, then run again for T8.html (docs: /docs/run)`,
  `exit 4`, `run.json` 253,943 bytes in each, equal after blanking `run_id`, `started`,
  `duration_s` and the ledger. `doctor --offline` exit 0 with the note's last line and `licence
  show` exit 4 in both shells.
- **Packaging.** With `jinja2`, `markupsafe`, `scipy`, `cryptography`, `statsmodels`, `sklearn`
  set to `None` in `sys.modules`: `proofpack`, `.stats`, `.narrate`, `.narrate.checker`,
  `.render`, `.render.format`, `.render.html`, `.criteria`, `.run`, `.cli` import, none of the
  hidden modules loads, `environment()` raises `RendererUnavailable` naming `jinja2`. `python -m
  uv build --wheel`: the wheel carries the three templates and `proofpack/_schema/tokens.json`,
  `Requires-Dist: jinja2>=3.1`; installed `--no-deps --no-index` into a fresh `python -m venv`
  (no `.pth` in its site-packages): `proofpack.__file__` and `resource_path("tokens.json")` print
  venv paths with and without `PYTHONNOUSERSITE=1`. `uv.lock`: `jinja2 3.1.6`, `markupsafe`,
  `{ name = "jinja2", specifier = ">=3.1" }`; `uv lock --check --offline` resolved 63 packages;
  `ci.yml` runs `uv sync --all-groups --locked` twice and the wheel job asserts `tokens.json`.
  `tests/test_render_theme.py`: 13 passed (the wheel test ran, not skipped).
- **The suite, the markers and the regression.** Worktree at `657ef11`: `988 passed, 1 skipped,
  1 xfailed in 74.79s`; `-m day8` 200, `day7` 139, `day6` 285, `day5` 54, `day4` 182, `day3` 29 +
  1 xfailed, `day2` 40, `day1` 59 + 1 skipped - the note's counts and lens-1's day-1..7 counts;
  `ruff check` clean, `ruff format --check` 129 files; PowerShell `-m day8` 200 passed. Pre-fix at
  `29fc04e` with the three test files and thirty corpus files copied in: `42 failed, 111 passed`,
  the failures being the nine other `test_e8_repair1` functions, `test_declared_values_print_
  every_digit`, the two corpus-count tests and the thirty new corpus cases.

## Could not check

- `@page` with `var()` and `unicode-bidi: isolate` in a browser (none driven).
- CI on the reference platform (the engine is not pushed; never push).
- A real-licence `run --format json,html` from the plain CLI (no signing key here; the HTML
  path was measured through the test-only registry in both shells, the plain CLI without a
  licence in both).
- DOCX, T1, T7, the Pyodide demo and the site's pinned engine `a0c9abc` (out of E8's scope; the
  repair note's DEC-43 list matches what I ran, with `--format HTML` folding to `html` added).
- Whether B4's class is meant to be graded as blockers at all - I applied the rule I was given
  and said so in the finding.

## Sentences I refused to write

- "The checker binds every claim to its Number." Refused: B2 (13,962 accepted swaps).
- "H02 catches a y_pred the engine cannot score." Refused: B1 (a blank and an `NA` pass).
- "The renderer escapes every injection." Written instead: the thirteen literal payloads, the
  slots fed and what the bytes hold for each.
- "Every number on the page traces to run.json." Written instead: 22 rows re-derived by hand and
  the seven regex-split date fragments named.
- "The clustered overall block is correct." Written instead: six pooled counts with `0.00e+00`
  deviation on one 300-row fixture and `proportion_ci` equal on five cells.
- "free_text cannot spell a verdict word." Refused: B4.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
git worktree add --detach <path> 657ef117974f9543faea61be01b2469d5155bb4e && cd <path>
PYTHONPATH=<path>/src python -c "import proofpack;print(proofpack.__file__)"      # must print <path>
PYTHONPATH=<path>/src python -m pytest -q -p no:cacheprovider                     # 988 passed, 1 skipped, 1 xfailed
PYTHONPATH=<path>/src python -m pytest -q -p no:cacheprovider -m day8             # 200 passed
PYTHONPATH=<path>/src python scripts/mutation_sweep.py --marker day8              # 28 planted, 28 killed, 0 survived
S=<scratchpad>/lens-E8-r2-fresh-attack/attacks      # harness.py hard-codes the worktree path wt-657ef11; edit LENS_WT
PYTHONIOENCODING=utf-8 python $S/a_overall.py       # A5, A6-A8 (B1 engine-level)
PYTHONIOENCODING=utf-8 python $S/d2_followup.py     # D9b (B1 through the CLI), A6b
PYTHONIOENCODING=utf-8 python $S/b_checker.py       # B2 (B2, B3, B5 sections), B4 (B1 section)
PYTHONIOENCODING=utf-8 python $S/d_wiring.py        # D10 (B3), D1-D8, D11
PYTHONIOENCODING=utf-8 python $S/c_renderer.py      # C1-C17
PYTHONIOENCODING=utf-8 python $S/e_packaging.py     # E1-E4
PYTHONIOENCODING=utf-8 python $S/my_mutants.py      # 8 mutants: 5 killed, 3 survived
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force <path>
```

## What the repair needs

B1: exclude a row whose `y_pred` is missing from the analysis mask when no score column exists
(a `flow.excluded_missing_score`-style count naming `y_pred`), and route a `y_pred` equal to an
indeterminate value through the indeterminate policy, not into `fn` / `tn`; a test feeding the
20-blanked-positives table and asserting `18/22` or a HALT. B1 touches a statistical gate: DEC-12
(i) lens again. B2: refuse a Number pointer off the eight shapes outright (`value_ref_unbound`,
a new code with a corpus case), or add shapes for `analytic` and the decile curve and bind them;
decide whether `metric_id null` may bind a Number at all, whether a template outside the seven
may carry a Number, and whether `not_assessable` may be stated beside a count when the metric's
Number exists. B3: `has_criteria` from `criteria_results` (or from the fairness bound as well),
with a test feeding the fairness-only criteria.yaml. B4: Josh's decision on the rule's scope.
