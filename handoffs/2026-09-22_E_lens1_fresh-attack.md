# E8 lens 1 (fresh attack) - build day 8, lane E, at `29fc04e` - 23 September 2026

**Verdict: FAIL.** Five blockers. Every figure below was measured in this session, in a
detached worktree at `29fc04e` (a second at `7b2ca2a` for the regression comparison, a
third at `29fc04e` for the probes so the mutation sweep could not touch them), with
`PYTHONPATH=<worktree>/src` forced and `proofpack.__file__` printed inside each worktree
before any number was trusted. All three worktrees are removed. Nothing was committed;
this note is the only file added to the main tree. The probe scripts are under
`<scratchpad>/lens-E8-r1-fresh-attack/attacks/` (`a_overall.py`, `b_checker.py`,
`c_renderer.py`, `d_wiring.py`, `e_packaging.py`, `my_mutants.py`); the one-line repros
below are the lines those scripts ran.

## Blockers

### B1 - the checker does not bind the pointer to `metric_id`, `operating_point` or (outside `/subgroups`) `subgroup`; 339 wrong-number bindings accepted

The brief: "claim-binding checker (number ↔ metric_id ↔ subgroup ↔ direction)". At
`29fc04e` `_check_one` never reads `metric_id` or `operating_point` against the pointer,
and compares `subgroup` only with pointers matching `^/subgroups/(\d+)/`. Measured on the
synthetic document (`cohort_with_a_thirty_row_site()`, CRITERIA + FAIRNESS, 70 engine
claims, all 70 accepted):

- every `value_ref` swapped to a sibling metric that resolves: **339 swaps accepted, 0 rejected**
  (e.g. `CL-0001 OVERALL_ESTIMATE metric_id sensitivity` bound to
  `/overall/op1/specificity`, `/overall/op1/ppv`, `/overall/op1/npv`, `/overall/op1/accuracy`,
  `/overall/op1/prevalence`: all accepted);
- one field mutated per claim: **294 mutations accepted**, among them `metric_id` on 82 claims,
  `operating_point` → `op2` (no such operating point) on 82 claims, `operating_point` → `op9`
  accepted, `subgroup` set to `sex = M` on 13 OVERALL_ESTIMATE and 9 CRITERION_STATUS claims;
- the `C_met` criterion claim (`met`, `ci_lower_bound >= 0.5`) bound to `/overall/op1/npv`
  instead of sensitivity: **accepted** (the recomputation runs on the wrong Number and agrees);
- the `C_n30` claim (`site = S3`, accuracy) bound to `/overall/op1/sensitivity`: accepted;
  with `subgroup` changed to `sex = F` as well: accepted;
- `SUBGROUP_ESTIMATE` for `age = 40-65` bound to `/overall/op1/sensitivity`: accepted;
  `OVERALL_ESTIMATE` bound to `/subgroups/4/metrics/op1/sensitivity/number`: accepted;
- `AUROC_ESTIMATE` bound to `/overall/op1/sensitivity`: accepted; `OVERALL_ESTIMATE` bound to
  the count `/overall/op1/two_by_two/tp` alone: accepted (a documented scalar satisfies
  `refs (1, 1)` and the relation rule falls through to the claim's own word);
- `SUBGROUP_ESTIMATE_WITH_DIFF` with both refs the same `diff_vs_reference` cell: accepted;
  `CALIB_HIERARCHY` with the `oe` pointer four times and `FAIRNESS_GAP` with the `tpr_gap`
  pointer four times: accepted.

Nothing on today's page is wrong because of this: the engine's own claims bind correctly
and T8 prints no claim sentence. It is a blocker because the deliverable is the checker,
the corpus is the acceptance test, and a claim under any template can carry any Number
of the document as long as the sign and the row's status happen to agree.

Sentence violation: `checker.py` rule 5 says `subgroup_mismatch` is "the right number
attached to the wrong subgroup"; the counter-example `subgroup age = 40-65` with
`value_refs ['/overall/op1/sensitivity']` is the right number attached to the wrong
subgroup and is accepted.

Repro (worktree root, PYTHONPATH forced):
`python -c "import sys,copy;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_criteria;from test_criteria import CRITERIA,FAIRNESS,cohort_with_a_thirty_row_site;from proofpack.narrate import checker,claims;d=assemble(cohort_with_a_thirty_row_site(),make_criteria(criteria=copy.deepcopy(CRITERIA),fairness=FAIRNESS));c=copy.deepcopy(claims.build_claims(d)[0]);c['value_refs']=['/overall/op1/specificity'];print(checker.check([c],d).verdicts[0].accepted)"`
prints `True` (the claim says `sensitivity`).

### B2 - the free_text token rule is evaded by nine spellings of listed words; each is an accepted corpus case

`free_text_reason` lower-cases, NFKC-normalises, then splits on `[^a-z\-]+` and matches
whole words. Fed on an accepted `OVERALL_ESTIMATE` claim, these were **accepted**:

| free_text | why it passes |
|---|---|
| `p\u0430ss` (Cyrillic а) and `\u0440\u0430ss` | the Cyrillic letters split the word into `ss` |
| `pa\u200dss` (ZWJ), `pa\u200css` (ZWNJ), `pa\u00adss` (soft hyphen) | NFKC keeps the format character; the split yields `pa`, `ss` |
| `un-biased`, `pass-`, `-pass`, `verdict-like`, `fail-safe` | the hyphen is kept inside the token, so `pass-` ≠ `pass` |
| `me\u0301ets` (combining acute) | NFKC composes to `méets`; `é` splits the word |
| `paß` | `ß` splits the word (NFKC does not fold it) |
| `non\u2011inferior` (U+2011) | U+2011 is not `-`; `non` and `inferior` are not listed, although `non-inferior` is |

Rejected as expected: `passing`, `failed`, `PASS`, fullwidth `ｐａｓｓ`, `paſs` (long s
folds), `well‑calibrated` with U+2011 (only because `calibrated` is itself listed),
`Ⅳ`, `五`, `⑩`, `x²`, `‰`, `well calibrated`, `ok`, `meets`, `compliant`, `fda-cleared`,
`approved`, `endorsement`, `guidance_ref`.

No engine claim carries `free_text` at `29fc04e` (all 70 are `null`) and T8 prints no
claim text, so no page is affected today. It is a blocker by the grading rule (an accepted
corpus case) and because the checker is the only gate an LLM re-orderer will face.

Repro: `python -c "from proofpack.narrate.checker import free_text_reason as f;print(f('p\u0430ss'),f('pa\u200dss'),f('un-biased'),f('pass-'))"` prints `None None None None`.

### B3 - a y_pred-only table whose labels are not the declared classes passes every gate and prints sensitivity `0/42 (0.0%) [0.0, 8.4]` and `criterion not met`

`make_cohort(n=120, with_y_pred=True)` with the score column deleted and `y_pred`
rewritten as `yes` / `no` (classes declared `1` / `0`), through the CLI with a confirmed
mapping and a valid licence: exit 0, `T8.html` written, `halts []`, `warnings []`,
`overall.op1.two_by_two {tp 0, fn 42, fp 0, tn 78}`, `overall.op1.sensitivity est 0.0 k 0
n 42 ci (0.0, 0.0838) method wilson`, `criteria_results [('C1', 'not_met', 0.0)]`, and the
page's observed cell `0/42 (0.0%) [0.0, 8.4]`. H02 reads `y_true` only; H04 needs a score;
`overall_block` (E8 item 1) computes `pred = y_pred == decl.positive`, so every row of a
column in another vocabulary is "predicted negative". A wrong number and a wrong status
reach the page from a table that should HALT. Through the subgroup route the same rows
give the same zeros (day 4), so the class is older than E8; E8 is where it first reaches
`overall` and T8.

Repro: `attacks/d_wiring.py` section D9 (the CLI call is
`main(["run","--input",csv,"--criteria",yml,"--out",out], registry=ephemeral_registry())`
on that table); the engine-level line is
`python -c "import sys;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_cohort,make_criteria;c=make_cohort(n=100,with_y_pred=True);del c['score'];c['y_pred']=['yes' if v=='1' else 'no' for v in c['y_pred']];d=assemble(c,make_criteria());print(d['overall']['op1']['two_by_two'],d['overall']['op1']['sensitivity']['est'])"`
→ `{'tp': 0, 'fn': 26, 'fp': 0, 'tn': 74} 0.0`.

### B4 - declared thresholds, criterion values, prevalence and the fairness bound print rounded to three decimals, under a caption that says "as the manufacturer wrote the value"

`declaration_rows` and `criteria_rows` pass the customer's declared numbers through
`fmt.scalar(x)` = `format(x, ".3f")`. Measured on a criteria.yaml with `threshold 0.4275`,
`criteria[0].value 0.8525`, `prevalence[0].value 0.0125`, `fairness.bound 0.1005`: the page
prints `threshold 0.427`, Value `0.853`, `intended-use, test: 0.013`, `bound 0.101`. The
YAML echo below the table carries `0.4275` and `0.8525`, so one page states two thresholds.
The criteria caption reads "the declared value, the compared statistic and the largest
attainable lower bound print on the unit scale to three decimals, as the manufacturer
wrote the value" - false for any declaration with more than three decimals. D4 section 1.2
governs estimates; a declaration is the customer's number and has no rounding rule. The
T1-1 declarations table is the one VV fatal 4 asks a reviewer to read.

Sentence violation: the caption sentence above (`T8.html` line 90) and `criteria_rows`'s
docstring "(the scale the customer wrote)" - the scale is kept, the digits are not.

Repro: `attacks/c_renderer.py` section C10; or set `threshold: 0.4275` in any
criteria.yaml, run, and grep `T8.html` for `threshold 0.427`.

### B5 - a criteria.yaml without the optional `model.prior_version` makes `proofpack run` exit 5 after writing run.json

`criteria_schema.json` requires `model.name` and `model.version` only. `T8.html` line 16
reads `document.declarations.model.prior_version` under `StrictUndefined`. With the
synthetic criteria minus that key, through the CLI on a valid licence: `run.json` and
`ingest_report.json` written, then stderr `internal error: UndefinedError: 'dict object'
has no attribute 'prior_version'`, exit 5, no `T8.html`. (`udi_di` absent renders; `prior_version:
null` renders.) A schema-valid declaration is refused by the renderer with an internal
error rather than a typed line.

Repro: `attacks/d_wiring.py` section D10; or delete `prior_version` from the model block
of any valid criteria.yaml and run with `--format json,html`.

## Non-blocking (record and carry)

1. **Author · date and justification are looked up by `criterion_id`, not by position.**
   Two criteria with `id: C_dup` (values 0.5 and 0.99, authors "Author One" / "Author Two",
   two justifications): row 1 (`0.500`, criterion met) and row 2 (`0.990`, criterion not
   met) both print `Author One · 2026-01-01; Author Two · 2026-02-02` and
   `first justification / second justification`. Nothing is lost, but the reviewer cannot
   tell which justification belongs to which row. The caption's "rows are addressed by
   position, never by id" is false for these two columns (sentence violation).
   `_authored` / `_justification` in `render/html.py`.
2. **Surviving lens mutants (statistical gate).** 22 mutants of my own over the day-8
   marker (`my_mutants.txt`): 18 killed, 4 survived (2 non-equivalent, 2 equivalent). `run_prevalence_wrong_key` - the
   clustered overall prevalence computed on `~pos` - **survives all 158 day-8 tests**; the
   value at `29fc04e` is right (87/300 = 0.29 on my fixture, equal to the pooled count), so
   nothing is wrong today, but no test pins the clustered prevalence. `anchors_month_year_fixed`
   (`month_year()` returning "January 2025" whatever the date) survives because every draft
   row in the map is dated 2025-01-07. `fmt_typed_reason_prints_est` and
   `claims_relation_typed_reason_estimate` survive and are equivalent: `Number.__post_init__`
   refuses a typed reason beside an interval, so no engine Number reaches either branch.
3. **Free-text words the rule does not name** were accepted: `ninety`, `IV`, `percent`,
   `&sect;` (rendered as the six literal characters), `guidances`, `C.F.R.`, `FDAcleared`,
   `accepted`, `unsafe`, `safely`, `acceptably`, `biases`, `calibration`, `noninferiority`.
   D1 section 4.4 lists digits, `%`, the verdict words, `§`, `CFR` and `guidance`; whether
   number words and inflections belong on the list is a decision, not a defect.
4. **Other checker gaps, all latent today:** `metric_id: calibration_by_group` accepted
   although the docstring says "in D1 section 4.3's enum" (the code adds it; sentence
   violation); `guidance_ref` may be any map row (`FDA_PCCP_MP1_DATA` on a subgroup claim
   accepted - D1's rule is "in the map", so as specified); two claims with the same
   `claim_id` accepted; `resolve()` given two rejected claims on one slot appends the same
   substitute twice (`final ids ['CL-0001', 'CL-0001']`), so T8 section 7's "claims
   generated" would count it twice; `comparator_id '>'` on an `OVERALL_ESTIMATE` accepted;
   `template_id` swapped `OVERALL_ESTIMATE` ↔ `SUBGROUP_ESTIMATE` accepted; `criterion_index`
   moved between the three `C_f1_site` rows accepted (the claim's `subgroup` is never
   compared with the row's `scope`).
5. **`calibration: null` beside `calibration_suppressed_reason` prints nothing on T8.** With
   the block nulled and the reason `no_score_column`, the string does not appear on the page
   (T8 has no calibration section; D4 section 11 does not list one). E7 "Tomorrow needs" 3
   binds the day-8/9 renderer to read it; T1 (E9) is where it can print. DEC-35's IPA
   annotation is likewise not exercised by T8.
6. **A NUL byte in customer text reaches the page raw** (`b"\x00"` in the bytes); the bidi
   controls U+202A-202E, U+2066-2069, U+200E-200F are written as character references as
   documented. Eleven other injection strings (`<script>`, `<img onerror>`, `&lt;`,
   `{{ 7*7 }}`, `{% raw %}`, `]]>`, `</td></tr></table><b>`, `javascript:`, a 10,000-character
   string, an emoji) rendered escaped in every slot fed (justification, author, model name and
   version, operating-point source, reference-standard description, prevalence label and
   source, clustering declared_by, fairness author and justification, the `sex` level label).
7. **The draft label is not D4 section 1.1's verbatim string.** D4: "per draft guidance
   (Jan 2025), not for implementation"; the page: "draft guidance (January 2025), not for
   implementation" (the task text names the built spelling; recorded as the deviation).
8. **Mixed scales on one criteria row.** The fairness row prints Value `0.100` and Compared
   `0.217` on the unit scale beside Observed `+7.0 [−7.9, +21.7]` in percentage points.
9. **CLI hints.** `--templates T1` alone (licence ok) writes no document and prints
   "Next step: run again with --format json,html for T8.html" although the format already
   included html - the fix is `--templates T8`. `--format ''` yields json only while
   `--templates ''` yields T8.
10. **`@page { size: var(--pp-print-page-size); margin: var(--pp-print-page-margin) }`** -
    custom properties inside `@page` were not checked in a browser (could not check, below).
11. **`base.html` carries `font-weight: 600` / `700`** and layout literals (`margin: 0 auto`,
    `width: 100%`) that are not in `tokens.json`; the hex, px and font-family greps are clean
    (18 hex values on the page, all token values; 0 px literals outside the token file).
12. **D4 section 11 items 4 and 10** are not built: section 4 prints a sentence saying the
    mapping report is not printed; `customer_sections_outstanding` is the literal `[]`.
    Stated on the page; carried.
13. **Observed in passing, not E8's:** a bare `date: 2026-01-01` in criteria.yaml is parsed
    by `yaml.safe_load` as a `date` object and refused at declaration (`H08: ... criteria/0/date:
    type`); a customer must quote it.
14. **tokens.json contrast:** recomputed here with the sRGB formula: honesty 6.80, stop 10.02,
    ok 9.11, ink 16.46, ink-soft 7.09, ink-faint 4.57, line 1.34, on-brand/brand 11.69,
    brand/brand-soft 9.97 - the builder's `contrast_computed` figures, so D5's three stated
    figures are the wrong ones (needs-from-Josh 1 of the E8 note stands).

## Could not break

- **The clustered overall block.** 300 rows in 100 cases (3 rows per case, seed 7): the
  engine's two-by-two `{tp 69, fn 18, fp 30, tn 183}` equals my numpy count from the
  analysis-mask rows; est for sensitivity, specificity, PPV, NPV, accuracy, prevalence equals
  the pooled k/n (69/87, 183/213, 69/99, 183/201, 252/300, 87/300) with deviation 0.00e+00 on
  all six; every cell `cluster_bootstrap_percentile` with `wilson_refused_clustered` and
  `n_cases`; calling `proportion_ci` myself on `_conditioned` rows with `_overall_cell_key`,
  the same policy and plan gives a dict equal to the block's on all five metrics; youden,
  balanced_accuracy, lr_pos, lr_neg, dor, f1, mcc carry `clustered_data_analytic_ci_invalid`,
  `ci (None, None)`, `method none`, the `two_by_two_metrics` estimate; AUROC
  `cluster_bootstrap_percentile`, `delong_refused_clustered`, `auroc_wald None`, 301 ROC points;
  `threshold_free.prevalence == op1.prevalence`. A one-level `site` stratum on the same rows,
  seed and B: same estimates, intervals differ by 1.5e-3 to 6.2e-3 (own bootstrap stream per
  the docstring). One cluster: `insufficient_clusters`, no interval; two clusters and every
  row its own cluster: intervals present; `json.dumps(allow_nan=False)` succeeds on each.
  y_pred-only: normal, one-class `y_true`, `y_pred` all 1, all 0, integer 0/1: the two-by-two
  equals my hand count in each; `threshold_free.auroc not_computed_this_run`,
  `suppressed_reason no_score_column`, `roc []`, `calibration None` with the reason block;
  y_pred-only and clustered routes the operating point through the cluster bootstrap.
  `git diff 7b2ca2a 29fc04e -- src/proofpack/stats/` is 0 lines.
- **The renderer.** Footers: 3 page sections / 3 `page-footer` / 1 `print-footer` on
  documents with 0, 1 and 40 criteria rows; `render_pages` with 0, 1, 5 bodies gives n / n.
  The FDA AI-DSF draft label stands beside all 14 rendered mentions of the document; the
  structured `guidance_refs` carry `draft true` and the label on all three; a map row without
  the qualifier is refused (`AnchorError`); a planted row dated 2026-03-01 prints "March 2026",
  so the label is built from the row. Watermarks `TRIAL`, `LICENCE EXPIRED - not for
  submission`, `<b>x</b>` (escaped) each appear in 4 footers and 2 stamps; absent → 0 and the
  "No synthetic, demonstration or trial marking" line. A typed reason prints
  `n.e. (insufficient_positives)` with no digit though `est` was 0.75; a suppressed cell
  prints `‡`, no digit, and section 7 counts it; `[unverified]` survives (8 occurrences
  planted in a justification and the model name). Every observed cell of the synthetic
  criteria table (9 rows) equals my own D4 section 1.2 derivation from run.json, and the
  Value / n / Compared / Max-LB cells of the first six rows equal `format(x, ".3f")` or the
  bare count; all 76 digit runs in the rendered text trace to a run.json value at full or
  D4 precision, a claims count, or fixed template text. No status phrase outside `.status`;
  `endorsed` (6) and `approved` (1) only in the verbatim D4 cover note and disclaimer.
  Rendering the same document twice is byte-identical; the golden regenerates to the
  committed 39,638 bytes (equal after LF normalisation).
- **The wiring.** Valid licence: exit 0, `T8.html` beside `run.json`, no CRLF, no BOM,
  run.json validates against `output_schema_v1.json` with 0 errors, 20 top-level keys, 70
  claims, 0 rejections, 3 guidance refs. Grace: exit 0, HTML with the watermark 7 times.
  Expired past grace and no file: exit 4, `run.json` + `ingest_report.json` only, the typed
  "HTML not written" line. Trial: `TRIAL` in 2 stamps and 4 footers. `--templates T9`,
  `--format docx`, `--format pdf,json`: exit 5 with the typed error and no directory.
  `--offline --format json,html` with `socket.socket`, `create_connection`, `getaddrinfo` and
  `urlopen` replaced by raisers: exit 0, 0 calls, no proofpack module holding a socket /
  urllib / http name. Two runs in one process: top-level blocks differing `ledger`,
  `manifest`; manifest keys differing `duration_s`, `ledger_count`, `run_id` (`started` equal
  within the second); claims, rejections and guidance_refs equal; the two T8.html files equal
  after masking those fields. jinja2 hidden at run time: exit 5 with the typed
  `RendererUnavailable` line, run.json written. `doctor --offline` exit 0.
- **Packaging.** With `jinja2` and `markupsafe` set to `None` in `sys.modules`: `proofpack`,
  `.stats`, `.narrate`, `.narrate.checker`, `.render`, `.render.html`, `.run`, `.cli` import;
  `environment()` raises `RendererUnavailable` naming jinja2; with scipy, cryptography,
  statsmodels, sklearn, jinja2 and markupsafe all hidden, `proofpack`, `.stats`, `.narrate`,
  `.render` import. `python -m uv build --wheel`: the wheel carries
  `proofpack/templates/{T8,base,pages}.html` and `proofpack/_schema/tokens.json` beside the
  six other resources; `Requires-Dist` lists `jinja2>=3.1`. Installed `--no-deps --no-index`
  into a fresh `python -m venv` (no `.pth` in its site-packages, `ENABLE_USER_SITE False`):
  `proofpack.__file__`, `resource_path("tokens.json")` and the guidance map all resolve inside
  the venv, 19 colour tokens, the three templates present. `uv.lock`: `jinja2 3.1.6`,
  `markupsafe 3.0.3`, `{ name = "jinja2", specifier = ">=3.1" }` under `proofpack`; `ci.yml`
  runs `uv sync --all-groups --locked` and the wheel job asserts `tokens.json` resolves.
- **The committed sweep and the regression.** `python scripts/mutation_sweep.py --marker day8`
  in the worktree: `15 planted, 15 killed, 0 survived; 119 s`, tree clean after. Markers at
  `29fc04e`: day8 158, day7 139, day6 285, day5 54, day4 182, day3 29 + 1 xfailed, day2 40,
  day1 59 + 1 skipped; at `7b2ca2a`: day7 139, day6 285, day5 54, day4 182. Full suite at
  `29fc04e` in the worktree: `946 passed, 1 skipped, 1 xfailed in 102.90s`. `ruff check`
  clean; `ruff format --check`: 126 files already formatted. The corpus holds 85 files and
  `test_claims.py` collects 99 tests.

## Could not check

- `@page` with `var()` in a real print engine (no browser driven in this session).
- The two-shell run: Git Bash only; PowerShell 5.1 not run.
- DOCX, T1, T7, the Pyodide demo and the site's pinned engine (`a0c9abc`): out of E8's scope;
  the E8 note's DEC-43 list of CLI changes is complete against what I ran (`--format`,
  `--templates`, `T8.html`, the three JSON keys, `overall` non-null on clustered and
  y_pred-only, `threshold_free.suppressed_reason`, the new next-step hints).
- A criteria table of twenty engine-bound cells: the synthetic document has 9 criteria rows,
  all re-derived; the builder's 22-row test (`_criteria_twenty`) was run, not re-derived by
  hand beyond those 9 observed cells and 30 scalar cells.
- Whether "a corpus case accepted" is meant to grade the number-word and inflection cases
  in non-blocking 3 as blockers; I graded only evasions of listed tokens as B2.

## Sentences I refused to write

- "The checker binds every claim to its Number." Refused: B1.
- "The renderer escapes every injection." Written instead: the twelve literal strings fed and
  the one (NUL) that reaches the bytes.
- "No number on the page is untraceable to run.json." Written instead: 76 digit runs on the
  synthetic page, each traced.
- "The clustered overall block is correct." Written instead: six pooled counts with 0.00e+00
  deviation on one 300-row fixture, and the surviving prevalence mutant.
- "The wheel test proves the packaging." Written instead: the files listed in the wheel and
  the paths printed inside one fresh venv on this machine.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
git worktree add --detach <path> 29fc04e && cd <path>
PYTHONPATH=<path>/src python -c "import proofpack;print(proofpack.__file__)"
PYTHONPATH=<path>/src python -m pytest -q -p no:cacheprovider            # 946 passed, 1 skipped, 1 xfailed
PYTHONPATH=<path>/src python -m pytest -q -p no:cacheprovider -m day8    # 158 passed
PYTHONPATH=<path>/src python scripts/mutation_sweep.py --marker day8     # 15 planted, 15 killed, 0 survived
PYTHONIOENCODING=utf-8 python <scratchpad>/lens-E8-r1-fresh-attack/attacks/b_checker.py   # B1, B2
PYTHONIOENCODING=utf-8 python <scratchpad>/lens-E8-r1-fresh-attack/attacks/d_wiring.py    # B3, B5, non-blocking 1
PYTHONIOENCODING=utf-8 python <scratchpad>/lens-E8-r1-fresh-attack/attacks/c_renderer.py  # B4 (section C10)
python <scratchpad>/lens-E8-r1-fresh-attack/attacks/my_mutants.py        # 22 mutants: 18 killed, 4 survived
```
(the attack scripts hard-code the scratchpad worktree path `eng-attack`; recreate it with
`git worktree add --detach <scratchpad>/lens-E8-r1-fresh-attack/eng-attack 29fc04e` first.)

## What the repair needs

B1 and B2 are checker rules with corpus cases (bind `metric_id` and `operating_point` to
the pointer's path segments; bind `subgroup` to every pointer, not only `/subgroups`;
normalise free_text by stripping Cf/Mn characters and mapping confusables before the word
split, and split on hyphens too). B3 is a declaration-time or ingest gate: `y_pred` values
must be a subset of the declared classes (and the indeterminate values) when no score
column is present - the H02 shape. B4 is `fmt.scalar` on declared values: print the
declared number as declared (`repr` of the YAML scalar, or the YAML text), and change the
caption. B5 is `model.prior_version` read through `.get` in Python, not in the template.
Each touches a statistical gate only through B3; B3's repair takes a DEC-12(i) lens.
