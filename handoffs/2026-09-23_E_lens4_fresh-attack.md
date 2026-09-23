# E8 lens 4 (fresh attack, after repair 3) - build day 8, lane E, at `fe35332` - 23 September 2026

**Verdict: FAIL.** Four blockers. Three are new and sit outside the lines repair 3 touched:
the T8 criteria table reads the wrong Number for some operating-point ids (B1); a `y_pred`-only
table with two operating points prints one threshold's numbers under the other threshold and
sets a criterion status from them (B2); and the engine's own `CALIB_NA` claim states a reason
the document contradicts, and the checker accepts it (B3). The fourth (B4) is `free_text`
spellings of listed words that the checker accepts. By the grading rule given to this lens,
every accepted corpus case is a blocker.

Every figure below was measured in this session. Worktrees under
`<scratchpad>/lens-E8-r4-fresh-attack/`: `wt` at `fe35332`, `old` at `0f553c9`, `mut` at
`fe35332` for my mutants, and `w7fa` at `7fa690b` for one comment check. I forced
`PYTHONPATH=<worktree>/src` for each and printed `proofpack.__file__` as that worktree's own
`src\proofpack\__init__.py` before trusting any figure. All four worktrees are removed.
Nothing was committed. This note is the only file I wrote to the main tree. Probe scripts are
in `<scratchpad>/lens-E8-r4-fresh-attack/att/` and outputs in `out/`. I re-ran lens 3's
scripts unchanged, from `prev/`.

## Blockers

### B1 - the T8 criteria table resolves `metric_ref` as a dotted path, so an operating-point id containing `.` or `[n]` prints another operating point's Number, or no Number

`render/html.py::criteria_rows` builds the observed cell from
`claims._dotted_to_pointer(row["metric_ref"])`. The dotted string cannot carry an id that
contains `.`, `[` or `]`. `criteria.py` computes the status from the keys directly, so the
status is right and the printed Number is not. Through the CLI with a valid licence and
300 rows (`att/a2_dotted.py`):

- Operating points `0` (threshold 0.2) and `[0]` (threshold 0.8). T8 row `C_br` (op `[0]`)
  prints `99/101 (98.0%) [93.1, 99.5]`. That is op `0`'s sensitivity. The same row prints
  `0.287` in the compared-value column and `criterion not met`. The engine's own `[0]` Number is
  `est 0.287129 [0.207976, 0.381880]`. **This is a wrong number on the page, beside a status it
  contradicts.**
- Operating point `t0.5`, a natural name for a threshold. Row `C1` prints `—` as the observed
  value beside `criterion met` and `0.842`, although `run.json` holds `est 0.841584 [0.758064,
  0.900072]`. The engine's criterion claim is rejected `value_ref_unresolved` and appears in
  section 7.
- Operating point `a[0`: `internal error: ValueError: not enough values to unpack`, exit 5, no
  directory. This is `_dotted_to_pointer` inside `build_claims`.

All three are identical at `0f553c9`, so the defect is E8's renderer and not a repair-3
regression. Lens 3's ids `a/b` and `op~1` do not reach this: `pointer()` escapes `/` and `~`.

Repro (in `wt`, `PYTHONPATH` forced):
`python -c "import sys;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_cohort,make_criteria;from proofpack.render.html import criteria_rows;C=lambda i,o:dict(id=i,metric='sensitivity',operating_point=o,scope='overall',statistic='point_estimate',comparator='>=',value=0.5,author='A',date='2026-01-01',justification='j');P=lambda i,t:dict(id=i,threshold=t,rule='>=',provenance='prespecified_sap',source='s');c=make_criteria(criteria=[C('C_zero','0'),C('C_br','[0]'),C('C_dot','t0.5')],fairness=None);c['operating_points']=[P('0',0.2),P('[0]',0.8),P('t0.5',0.5)];d=assemble(make_cohort(n=300),c);print([(r['criterion_id'],r['observed'],r['compared_value'],r['status_word']) for r in criteria_rows(d)])"`
prints `[('C_zero', '99/101 (98.0%) [93.1, 99.5]', '0.980', 'criterion met'), ('C_br', '99/101 (98.0%) [93.1, 99.5]', '0.287', 'criterion not met'), ('C_dot', '—', '0.842', 'criterion met')]`.

### B2 - a `y_pred`-only table with two operating points prints the same `y_pred` numbers under both thresholds and sets both criterion statuses from them (a statistical gate: the overall block)

`run.overall_block` computes `pred = y_pred == positive` for **every** declared operating point
when there is no score column, and `stats/subgroups.py` does the same (`predicted[op.id]` from
`y_pred`). H04 cannot check a threshold without a score. Nothing refuses the declaration and
nothing warns. Measured through the CLI (`att/a3_ypred_ops.py`, 300 rows, `y_pred` made at 0.5,
operating points `op_lo` 0.1 and `op_hi` 0.9, criteria `sensitivity point_estimate >= 0.7`
on each). The run exits 0 with `warnings []`. Both blocks are `{tp 85, fn 16, fp 39, tn 160}`,
sensitivity `0.841584 [0.758064, 0.900072]`, and both criteria are `met`. T8 prints `op_hi:
threshold 0.9`. On the same cohort's score column, the sensitivity at 0.9 is **12/101
(0.1188)** and at 0.1 it is **101/101**. The `op_hi` block and the `C_hi met` status do not
describe threshold 0.9. **This is a wrong number and a wrong status.** The same holds at
`0f553c9`, so the defect dates from E8 item 1 (`86b5fdd`). No note mentions it.

Repro: `python -c "import sys;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_cohort,make_criteria;c=make_cohort(n=300,with_y_pred=True);del c['score'];k=make_criteria(criteria=[],fairness=None);k['operating_points']=[dict(id=i,threshold=t,rule='>=',provenance='prespecified_sap',source='s') for i,t in (('op_lo',0.1),('op_hi',0.9))];d=assemble(c,k);print([(o,d['overall'][o]['two_by_two'],round(d['overall'][o]['sensitivity']['est'],4)) for o in ('op_lo','op_hi')], d['warnings'])"`
prints two identical blocks at `0.8416` and `[]`.

### B3 - the engine's `CALIB_NA` claim states "the score was declared as probability, not a probability" on every `y_pred`-only run, and the checker accepts it

`claims._calibration_claims` emits `CALIB_NA` whenever `calibration` is not an object. Rule
8b's new `CALIB_NA` test inspects only that condition. It does not compare the reason. On a
`y_pred`-only document, `calibration_suppressed_reason` is `{reason: no_score_column,
score_type: probability}`. The skeleton filled from the declarations reads "Calibration
statistics are not computed because the score was declared as probability, not a probability."
`checker.check` accepts claim `CL-0060`, and the claim is written to `run.json`. The same
sentence is false for the second suppression reason, `score_not_positive_class_probability`
(a probability oriented `lower_is_positive`). The sentence is true only for
`score_not_probability`. This is the class repair 3 set out to bind: its reason text reads "the
template states what the row or document does not carry". Lens 3 graded `CALIB_NA` accepted
where its sentence is false as part of blocker B1. Nothing renders claim sentences today; E9
will render this one as written.

Repro: `python -c "import sys;sys.path.insert(0,'tests');from assembler import assemble;from conftest import make_cohort,make_criteria;from proofpack.narrate import claims,checker;from proofpack.narrate.templates import LIBRARY;c=make_cohort(n=200,with_y_pred=True);del c['score'];d=assemble(c,make_criteria(criteria=[],fairness=None));n=[x for x in claims.build_claims(d) if x['template_id']=='CALIB_NA'];print(d['calibration_suppressed_reason']['reason'],checker.check(n,d).verdicts[0].accepted,LIBRARY['CALIB_NA'].skeleton.format(score_type=d['declarations']['score']['type']))"`
prints `no_score_column True Calibration statistics are not computed because the score was declared as probability, not a probability.`

### B4 - `free_text` accepts spellings of listed words: 35 homoglyph literals, five `well calibrated` spellings with a suffix, and three of the orchestrator's named corpus cases

I fed each case bare and inside "The model was {} here." (`att/b_corpus.py`, `att/b3_homo.py`,
`att/s_sentences.py`). Every one below returns `None` from `free_text_reason` and is accepted
by `checker.check` on `CL-0001`:

- **Look-alikes of letters in listed words** (37 fed; these 33 spell a listed word and are accepted): `fai|` (U+007C), `fai∣`
  (U+2223), `faił`, `faiɫ`, `faiƖ`, `faiߊ`, `faiⵏ`, `faiꓲ`, `fai׀`, `faiΙ` (Greek capital
  iota), `faiІ` (Cyrillic capital І), `faɩl`, `ⲣass`, `⍴ass`, `ꓑass` (Lisu), `p⍺ss`,
  `paꓢs`, `paꮪs`, `gⲟⲟd`, `gဝဝd`, `gഠഠd`, `ⲟk`, `ցood`, `m℮℮ts`, `mҽҽts`, `սnbiased`,
  `ⲥonsistent`, `veгdict`, `ѵerdict`, `saꞙe`, `unbi⍺sed`, `ᏚAFE`, `ꓳꓗ`. Also the analogues of
  repair 3's own `faiI`: `faiＩ` (fullwidth I) and `fai𝐈` (mathematical bold I). The
  capital-`I` reading replaces ASCII `I` only.
- **`well calibrated` with a separator and a suffix**: `well calibratedness`,
  `well_calibratedness`, `well.calibratedness`, `well\u00a0calibratedness`, `Well
  calibratedly`. Repair 3's substring rule removes hyphens only. These spellings were also
  accepted at `657ef11` and `7fa690b`, so they are not a regression.
- **The orchestrator's named cases**: `&sect; eight`, `ninety` and `Roman IV`. In an escaped
  page, `&sect;` prints as its six characters, not as `§`. Lenses 2 and 3 carried `ninety` and
  `Roman IV` as recorded, pending needs-from-Josh 2 of the repair-1 note. I list them here
  because the rule given to me grades every accepted case as a blocker.

DEC-60 says the rule covers the Unicode TR39 confusables. Repair 3 did not fetch the data.
Whether TR39 lists each letter above is **[unverified]**: I did not fetch `confusables.txt`,
because a download needs Josh's approval. The orchestrator's other named cases are each
rejected with the expected code: `раss` (Cyrillic р and а), `pa\u200dss`, `p a s s`,
`passing`, `failed`, `un-biased`, `Roman Ⅳ` (as a digit), `per ‰`, `&#167;` (as a digit),
`paѕѕ`, `faіl`, `𝓅𝒶𝓈𝓈`.

Repro: `python -c "from proofpack.narrate.checker import free_text_reason as f;print([f(t) for t in ('fai\u0399','\ua4d1ass','g\u2c9f\u2c9fd','fai\uff29','well calibratedness','&sect; eight')])"`
prints six `None`.

## Non-blocking (record and carry)

1. **Customer words outside `.customer-text`.** I set model name `Safe triage`, version `2
   unbiased` and operating-point id `pass`. The page test's own helper
   (`test_render_t8._status_and_forbidden_hits`) then finds 4 forbidden-word hits outside the
   disclaimer and `.customer-text`: the page header on each of 3 pages (`safe`, `unbiased`), and
   the criteria table's operating-point cell (`pass`). The `<title>` carries them too. The
   result is the same at `0f553c9`. I grade this record-and-carry because the words are the
   manufacturer's own names and D4 section 1.5 prescribes the header. If D4 section 1.2's
   "Forbidden anywhere in rendered output" is read literally, it is a blocker. That is Josh's
   decision.
2. **Sentence violations in repair 3's added text.** Each one was falsified by a counter-example
   I ran:
   - README, the `schema_v1.json` `y_pred` description and the `output_schema_v1.json`
     `excluded_missing_score` description each say a blank `y_pred` is "counted under
     `flow.excluded_missing_score` when the row's `y_true` is present". The counter-example
     has a `dataset` column with 20 `dev` rows: of 12 blank-`y_pred` rows with `y_true`
     present, the flow gives `excluded_missing_score 10`. Two are `dev_rows`.
   - The `templates.py` docstring says "One skeleton differs from D4 section 8's text:
     `FLOW_COUNTS`". Two more skeletons differ from the D4 text: `CRITERION_STATUS` prints
     ` - ` where D4 has ` — `, and `KS_RESULT` prints `Kolmogorov-Smirnov` where D4 has an en
     dash.
   - The `_BEFORE_NFKC` comment says "NFKC turns the Greek lunate sigma (U+03F2, and its
     capital U+03F9) into a final sigma". NFKC(U+03F9) is U+03A3, GREEK CAPITAL LETTER SIGMA.
   - The `_HOMOGLYPHS_R3` comment lists "ꮲ (U+ABB2)" among "the capital forms". U+ABB2 is
     CHEROKEE SMALL LETTER TLV. It does case-fold to U+13E2.
   - The `_SMALL_CAPITALS` comment reads "The Latin small capitals (U+1D00-U+1D22, ...)". Nine
     small capitals in that range are unmapped (U+1D01, 1D03, 1D06, 1D0C, 1D0E, 1D10, 1D15, 1D19,
     1D1A), and so are U+A7AF and U+0276.
   - The `_readings` docstring says "every capital `I` read as `l`". Only ASCII `I` is read that
     way: `faiＩ` is accepted.
3. **My own mutants** (`att/my_mutants.py`, `-m day8`, 12 planted, tree clean afterwards).
   Killed: 4. Survived, and in my judgement not equivalent (none of them changes what the engine
   emits today):
   - `reserved_first_op_only`: the gate reads `op_ids[:1]`. The tests feed each reserved id as
     the only operating point. At HEAD a second operating point `brier` does halt H08.
   - `reserved_casefold`: this widens the refusal. No test feeds `Threshold_Free`.
   - `shapes_subgroup_estimate_op_only`: at HEAD, `SUBGROUP_ESTIMATE` bound to
     `/subgroups/i/metrics/auroc/number` is accepted, and no test pins that.
   - `capital_i_reads_text_not_raw`.
   - `wellcal_substring_full_only`: `weIl-calibratedness` is rejected only through the
     capital-`I` reading.
   - `flow_scalar_slots_site_count_any`: `SITE_COUNT` over `/flow/n_cases`. Corpus `137` feeds
     `rows_read` only.

   Survived and equivalent on engine documents: `slot_order_allows_repeats` and
   `calib_na_only_when_reason`.
4. **Derived words accepted** (whole-word matching, as documented): `unbiasedness`,
   `consistently`, `safely`, `passable`, `acceptably`, `verdictive`, `goodness`, `clearances`,
   `approvals`, and still `guidances` and `unsafe`. `well-calibratedness` is rejected. The
   same kind of affix on the other listed words is not.
5. **D4 section 1.2 says Clopper-Pearson is shown alongside Wilson at k = 0 or k = n.** No
   document carries it: `stats.proportions.proportion_exact_alternative` has no caller in
   `src/`. T8 prints one interval. This data gap predates E8.
6. **`claim_id` with fullwidth digits is accepted.** `CL-０００１` passes, because
   `re.fullmatch(r"CL-\d{4,}")` matches Unicode digits.
7. **Carried from lens 3 and still reproducing.** Lens 2's single-field sweep gives
   `mutations: 8988 accepted: 11`:
   - 7 are `metric_id` swaps inside `CALIB_HIERARCHY` and `FAIRNESS_GAP`;
   - `C_met` relabelled `ATTAINABILITY_NOTE`;
   - `CL-0063` / `CL-0070` relabelled `CRITERION_NOT_MET_RECORD` (both rows are `not_met`,
     which is true);
   - `CL-0063` relabelled `ATTAINABILITY_NOTE`.

   Also still reproducing:
   - two accepted claims on one slot are both kept (`['CL-0001', 'CL-9999']`);
   - `--format HTML` folds to `html`;
   - a run with no licence file is watermarked `LICENCE EXPIRED - not for submission`;
   - section 7 prints the three status words on a document with no criteria.

## What I could not break (evidence)

- **The overall block**, re-derived with my own numpy. The day-4 constants and intervals are
  untouched: `git diff 0f553c9 fe35332 -- src/proofpack/stats/ src/proofpack/run.py
  src/proofpack/criteria.py` is empty, and `git diff 7b2ca2a fe35332 -- src/proofpack/stats/`
  is also empty.
  - Clustered fixture, 300 rows in 100 cases: the two-by-two `{tp 69, fn 18, fp 30, tn 183}`
    equals my count. Sensitivity, specificity, PPV, NPV, accuracy and prevalence each deviate
    by `0.00e+00`, with method `cluster_bootstrap_percentile` and flag
    `wilson_refused_clustered`. `proportion_ci` on the same rows, ids, seed and B equals the
    block on all five proportions. Youden, balanced accuracy, LR+, LR-, DOR, F1 and MCC each
    carry `clustered_data_analytic_ci_invalid`, `ci (None, None)`, method `none`.
  - One `site` stratum on the same rows: the estimates are equal and the intervals differ by
    1.48e-3 to 6.24e-3 (the subgroup draws its own bootstrap stream).
  - One cluster gives `insufficient_clusters`. Two clusters, and every row its own cluster, give
    intervals.
  - Clustered `y_pred`-only (240 rows in 60 cases): the two-by-two equals my count with no
    class removed, with one class only, with every prediction 1, and with one blank per
    cluster. Blank `case_id` halts S05.
  - Unclustered `y_pred`-only: the two-by-two equals my count on the normal table, one class,
    all 1, all 0, and integer values.
  - A point-estimate criterion on LR+, F1, MCC and DOR in a clustered run gives `not_assessable`
    / `no_interval`, with `n.e. (clustered_data_analytic_ci_invalid)` and no digit printed.
- **Twenty-two cells re-derived by hand from `run.json`**, using D4 section 1.2 with my own
  `Decimal` half-even formatter, on a new clustered CLI run (360 rows, 120 cases, 22 criteria
  rows): **0 mismatches**. The cells cover:
  - the proportions, `k/n (xx.x%) [lo, hi]`;
  - AUROC and Brier to three decimals;
  - four typed-reason cells;
  - the three `level: *` rows;
  - the fairness-gap `n.e. (cases_span_both_groups)`.

  The tier superscripts I derived from n and the half-width agree with the page on all 22.
  Lens 3's own script re-derived another 22 rows with 0 mismatches, and 60 Wilson cells with a
  worst deviation of `2.22e-16`.
- **The checker.**
  - The orchestrator's structural cases each get the expected code:
    - a list target (`/subgroups`): `value_ref_not_a_number`;
    - a trailing slash or a doubled slash: `value_ref_unresolved`;
    - `met ` and `MET`: `status_not_in_enum`;
    - `overall_estimate` and a trailing space: `template_unknown`;
    - `specificity` on a sensitivity pointer: `metric_mismatch`;
    - the same cell twice in a difference claim: `value_ref_duplicate`;
    - `<=` on a `>=` row: `comparator_mismatch`;
    - a `guidance` key beside `guidance_ref`: `unknown_key`;
    - lower-case `guidance_ref`: `guidance_ref_unknown`;
    - `criterion_index` `True` or `0.0`: `criterion_index_invalid`.
  - Lens 2's B5 sweep: `swaps: 42849 accepted: 0`.
  - All nine of lens 3's FA-B2 literals and every FA-B1 relabel case are rejected with the
    named code.
  - **Differential fuzz** (`att/b4_fuzz.py`): 51 listed words × 2,552 code points from 19
    blocks × 5 placements gives 650,760 texts. Rejected at `657ef11` or `7fa690b` and accepted
    at `fe35332`: **0**.
- **The FA-B3 declaration gate** (DEC-12(i)).
  - `threshold_free`, `auroc`, `brier` halt H08, at any position in the list.
  - `Threshold_Free`, `THRESHOLD_FREE`, `AUROC`, `Brier`, the id with a leading or trailing
    space, `threshold‐free`, `threshold_ｆree` and `auroc\u200b` are each accepted. Each runs
    clean as a distinct key: for example `Threshold_Free` gives 64 claims, 0 rejected, and C1
    `met` from its own block.
  - The same is true of `roc`, `auprc`, `prevalence`, `two_by_two`, `number`, `auroc_gap`,
    `sensitivity` and `metrics`.
  - No other key sits beside operating-point ids in `overall`, subgroup `metrics`, the
    `diff_vs_*` blocks or the fairness gaps (read in `run.py` and `stats/subgroups.py`).
  - B1 above is the one pointer-escape route I found. It does not pass through this gate.
- **The renderer.** Lens 3's `c_renderer.py` / `c2_render.py` re-run at `fe35332`:
  - thirteen payloads: no raw tag, no NUL byte, U+202E written as `&#x202e;` (111 times),
    `{{ 7*7 }}` kept literal;
  - 0 `@import` / `url(` / `<link` / `<script` / `http:` / `https:`;
  - 19 hex colours and 7 px values, all from `tokens.json`;
  - footers 3/3/3 on 0, 1 and 40 rows; `render_pages` 0/1/5 pages give 0/1/5 footers;
  - `[unverified]` 8 times;
  - the draft label beside all 14 AI-DSF mentions and on 3 structured `guidance_refs`;
  - the watermarks `TRIAL`, `LICENCE EXPIRED`, `NO LICENCE`: 4 tags each;
  - the same document rendered twice is identical, and the golden (39,800 bytes) is equal.
- **The wiring** (my own `att/d_wire.py`, plus lens 3's `d_wiring.py`).
  - `--offline --format json,html` with `telemetry: true` and eight network entry points
    raising (`socket.socket`, `create_connection`, `getaddrinfo`, `gethostbyname`, `urlopen`,
    `HTTP(S)Connection.connect`, `SSLContext.wrap_socket`): exit 0 and **0 calls**, run twice.
  - F17 with 70 claims: only `run_id`, `started`, `duration_s` and `mapping_sha256` differ.
    `mapping_sha256` differs because my harness writes a separate mapping file per run.
    `run.json` validates. T8 after masking differs on the mapping-SHA row only.
  - Grace licence: HTML written, watermark 7 times. Expired licence: exit 4, JSON only. No
    licence file: exit 4. `--templates T1`: exit 0 with the typed line. `docx`, `pdf,json`
    and `T9`: exit 5, no directory.
- **Packaging.** With jinja2, markupsafe, scipy, cryptography, statsmodels and sklearn hidden,
  all eight modules import and `environment()` raises `RendererUnavailable`. `uv build` gives a
  wheel with the three templates, `_schema/tokens.json` and `Requires-Dist: jinja2>=3.1`. In a
  fresh venv with no `.pth`, `proofpack.__file__` and `tokens.json` resolve inside the venv, with
  and without `PYTHONNOUSERSITE=1`. `uv lock --check --offline` gives rc 0 (63 packages).
  `ci.yml` runs `uv sync --all-groups --locked` 3 times. `test_render_theme.py` gives 13 passed.
- **Suite, markers, lint and sweep** (`wt`).
  - Full suite: `1122 passed, 1 skipped, 1 xfailed`.
  - Markers: `day8` 334 (PowerShell 5.1: 334), `day7` 139, `day6` 285, `day5` 54, `day4` 182,
    `day3` 29 + 1 xfailed, `day2` 40, `day1` 59 + 1 skipped, `ap2` 88. Days 1-7 equal lens 3's
    `7fa690b` counts.
  - `ruff check`: `All checks passed!`. `ruff format --check`: `153 files already formatted`.
  - Committed sweep `--marker day8`: **`79 planted, 79 killed, 0 survived; 902 s`**, including
    the restored `checker_format_characters_kept` and both `declare_reserved_*` mutants.
  - Pre-fix: the four changed test files and 11 corpus files copied into `0f553c9` give `22
    failed, 154 passed`. The three repair-3 tests that pass there are the ones the note
    declares as pins.
  - The `_JOIN_RUN` comment re-measured at `7fa690b` with 13 planted: `224 passed`, as stated.

## What I could not check

- TR39 `confusables.txt`: not fetched (DEC-60; the download needs Josh's approval). TR39
  membership of every literal in B4 is [unverified].
- A browser rendering of `.customer-text` bidi isolation; CI on the reference platform (the
  engine is not pushed); a real-licence plain-CLI run (there is no signing key).
- How E9 fills template slots, which decides whether the lens-3 permutation class matters.

## Sentences I refused to write

- "The reserved-id gate closes every collision of an operating-point id with a document key."
  Written instead: the ids fed above, and B1.
- "The overall block is correct on every table." Written instead: the fixtures and deviations
  above, and B2.
- "The renderer prints only numbers from `run.json`, correctly." Written instead: 22 cells
  matched, and B1's counter-example.
- "`free_text` rejects look-alike spellings." Written instead: B4's 43 accepted texts.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
git worktree add --detach <path> fe35332
PYTHONPATH=<path>/src python -c "import proofpack;print(proofpack.__file__)"   # must print <path>
PYTHONPATH=<path>/src python -m pytest -q -p no:cacheprovider                  # 1122 passed, 1 skipped, 1 xfailed
S=<scratchpad>/lens-E8-r4-fresh-attack/att          # scripts read LENS_WT (default: .../wt)
LENS_WT=<path> PYTHONIOENCODING=utf-8 python $S/a2_dotted.py    # B1
LENS_WT=<path> PYTHONIOENCODING=utf-8 python $S/a3_ypred_ops.py # B2
LENS_WT=<path> PYTHONIOENCODING=utf-8 python $S/b5_calibna.py   # B3
LENS_WT=<path> PYTHONIOENCODING=utf-8 python $S/b3_homo.py      # B4
git -C C:/Users/joshs/GPS/ProofPack/proofpack worktree remove --force <path>
```

## What the repair needs

- **B1:** resolve a criteria row's Number from `criterion_id` position plus the structured
  fields (`operating_point`, `metric`, `scope`), not from the dotted string. Alternatively,
  refuse ids containing `.`, `[` or `]` at declaration with a typed H08. Either way, add a test
  feeding `0` / `[0]` and `t0.5`.
- **B2:** refuse a `y_pred`-only table with more than one operating point (typed), or document
  and print which threshold `y_pred` represents. This is a statistical gate: DEC-12(i).
- **B3:** bind `CALIB_NA` to `calibration_suppressed_reason.reason == score_not_probability`,
  and give the other two reasons a template that states them.
- **B4:** Josh's TR39 decision (DEC-60) and the fetch; a separator-tolerant rule for the
  `well calibrated` phrase; and Josh's decision on `ninety` / `Roman IV` / `&sect;`.
