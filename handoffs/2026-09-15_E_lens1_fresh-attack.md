# Lens 1 (fresh attack) — 2026-09-15 — Lane E day 5 (`stats.subgroups`) at `d1fd20a`

Attacking `d1fd20a` cold. Every number below was measured in this session in a detached
worktree with `PYTHONPATH` forced to that worktree's `src` and proved
(`proofpack.__file__` printed from the worktree before any count was trusted). Nothing
was committed; both worktrees were removed at the end.

## Verdict: **FAIL — 2 blockers, 9 non-blocking, 4 sentence violations.**

The arithmetic is right: Newcombe-10, Wilson, the DeLong placement-value variance, Holm
and the chi-square / Fisher homogeneity tests all agree with my own implementations from
the published formulae to 1e-16 on the fixtures, on 200 random 2×2 pairs, 50 random
score/label pairs, 100 random p-sets and 200 random r×2 tables, and with statsmodels,
scipy and scikit-learn where those exist. The conventions the note lists hold under every
construction I tried except the two below. The injection claim holds on 50 seeds the
builder did not use. The committed mutation sweep reproduces (21/21/0).

The two blockers are both a statistic rendered on a false premise with no flag and no
typed reason — the defect class the whole of day 4 was spent on, on two quantities added
today:

- **B1.** The exploratory heterogeneity footnote computes the Pearson chi-square (and its
  Holm adjustment) on the **rows** of a clustered table. F6 with every patient's row copied
  three times under a declared `case_id` reports χ² 13.898, p 0.00096 (Holm 0.0019) where
  the honest table gives p 0.0986. Every interval in the same block is refused with
  `clustered_data_analytic_ci_invalid`; the p-value beside them is not.
- **B2.** The unpaired DeLong difference is rendered as `delong_wald` when one side's
  DeLong variance is exactly zero (a perfectly separated level) — the condition under
  which the engine's own day-3 rule refuses that side's AUROC as `boundary_estimate`. At
  the just-evaluable 10/10 with a true level AUROC of 0.90, perfect separation happens in
  5.4 % of samples and there the difference interval covers the truth **27 %** of the
  time at a nominal 95 %; the row shows "AUROC n.e." beside "difference 0.31 (0.21, 0.41),
  p 0.0002".

---

## 1. What I re-ran, and what held

| Check | Result |
|---|---|
| Suite at `d1fd20a` (worktree, `PYTHONPATH` proved) | `352 passed, 1 skipped, 1 xfailed in 41.24s` |
| `-m day5` | `42 passed, 312 deselected` |
| `-m day1` / `day2` / `day3` / `day4` | `59 passed, 1 skipped` / `40 passed` / `29 passed, 1 xfailed` / `182 passed` — identical to the round-7 repair note's block |
| Suite at `3ea2bfd` (second worktree) | `310 passed, 1 skipped, 1 xfailed` — the difference is exactly the 42 day-5 tests |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `48 files already formatted` |
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.` |
| Day-4 constants | `MIN_UNITS_PER_STRATUM = 2`, `MAX_FROZEN_VARIANCE_SHARE = 0.20` — only their docstrings changed in the diff |
| `import proofpack.stats.subgroups` with `sys.modules["scipy"] = None` | imports; `_homogeneity_test` returns `scipy_unavailable`; no `statsmodels`/`sklearn` module loaded |
| Tests weakened | none: no skip/xfail/`.only` added, nothing deleted, no marker removed; the new `slow` mark is not deselected by CI (`-m dayN` per marker) |
| `scripts/mutation_sweep.py --marker day5` | **21 planted, 21 killed, 0 survived; 205 s** (note said 194 s) |
| `scripts/coverage_bar.py --quick` at the recorded seed | 40 s; feasibility block prints `loosest feasible pair: None` (the note does not quote this block — see N1) |

### Re-derivations (my code, no repo code for the statistic under test)

| Statistic | Written from | Compared on | Max abs deviation |
|---|---|---|---|
| Wilson score limits | Newcombe 1998 method 3 formula | 300 random (k, n) vs engine and `statsmodels.proportion_confint(method="wilson")` | 2.2e-16 / 2.2e-16; F8 half-widths 0.0851 / 0.0596 / 0.0341 reproduced |
| Newcombe method 10 | square-and-add of the Wilson limits | 200 random 2×2 pairs incl. 20 double-boundary pairs vs `newcombe10_bounds` | 2.2e-16; F14 fixture's three examples to 4 dp; hand case 30/40 vs 100/120 → (−0.2453, 0.0493) |
| DeLong 1988 variance | placement values `V10_i = mean_j psi(x_i, y_j)`, `S10/m + S01/n` with ddof 1 | 50 random score/label pairs (a third with ties) vs `unpaired_delong` and `sklearn.roc_auc_score` | AUC 1.1e-16, relative variance 4.2e-16, Wald bounds 2.4e-16, p-value 1e-9 |
| Holm step-down | Holm 1979 | 100 random p-sets vs `holm()` and `multipletests(method="holm")` | 0.0 / 0.0; F6 → [0.036, 0.08, 0.30] |
| Pearson χ² of homogeneity, Fisher exact | `sum (O−E)²/E`, hypergeometric pmf sum | F6 (χ² 4.6327, df 2, p 0.0986; Fisher 0.1084) and 200 random r×2 tables vs `_homogeneity_test`, `chi2_contingency(correction=False)`, `fisher_exact`; the Fisher branch taken exactly when r = 2 and min expected < 5 | 0.0 / 1.1e-16 |

---

## 2. Blockers

### B1 — the heterogeneity p-value is computed on clustered rows with no refusal and no flag (blocker, wrong number)

`_attribute_block` builds `(tp, fn)` / `(tn, fp)` per level from **rows** and hands them
to `_homogeneity_test` whatever `arrays.plan` says. Under a declared or detected
clustered plan the module refuses Wilson, Newcombe and DeLong on those same rows with the
DEC-09 typed reason, and then prints a Pearson χ² p-value and a Holm-adjusted p-value on
them with nothing in the footnote mentioning clustering.

Repro (one line each):

```
# in the worktree, PYTHONPATH=src, tests/ on sys.path; decl declares site, clustering.unit: case_id
base = counts_cohort({"site1": (45,5,10,40), "site2": (38,12,10,40), "site3": (27,3,10,40)})
cols = {k: [v[i//3] for i in range(len(v)*3)] for k, v in base.items()}
cols["case_id"] = [f"c{i//3}" for i in range(150*3)]
rep.attribute("site")["heterogeneity"]["tests"][0]
→ sensitivity: {'test': 'chi2_homogeneity', 'statistic': 13.898, 'df': 2, 'p_raw': 0.00096, 'p_holm': 0.0019}
→ the same cohort one row per patient (F6): statistic 4.6327, p 0.0986
→ the same block's own sensitivity cell: method cluster_bootstrap_percentile, analytic clustered_data_analytic_ci_invalid
```

Second construction, 60 patients × 5 identical rows, random sites: p_raw 0.00046 and
3.5e-6 (clustered rows) vs 0.215 and 0.081 (one row per patient). `json.dumps` of the
footnote contains no "cluster".

Why blocker: a customer with a lesion-level table and a declared `case_id` obtains
p-values that are anti-conservative by the design effect, in a document whose every
interval on the same page says the rows are not independent. The footnote's
"exploratory" label does not make the number right, and R2 section 3.4's "never let a
p-value clear a subgroup" cuts the other way here — a Holm p of 0.0019 beside a
subgroup is exactly what a reviewer reads. Repair options: refuse with
`clustered_data_analytic_ci_invalid` (typed reason already exists; `heterogeneityTest`
already carries `not_estimable_reason`), or a case-level test with its own method
string; either way a test with the F6-copied-3× cohort that fails against `d1fd20a`.

### B2 — a `delong_wald` difference is rendered with one arm's variance frozen at zero (blocker, wrong interval, no flag)

`unpaired_delong` refuses only when `var_a + var_b == 0`. Day 3's `auroc_number` refuses
a **single** AUROC whenever `se == 0` ("the Wald interval is also useless",
`boundary_estimate`), and `_auroc_cell` shows exactly that for the level. The
difference cell in the same row then reports `delong_wald` with `variance_a: 0.0` in its
detail and an interval that is the other side's alone.

Repro: level A 10 positives scoring 0.80–0.90, 10 negatives 0.10–0.20; level B 60/60
overlapping; `run({"y_true": y, "score": s, "site": a})`:

```
A own auroc:            est=1.0  reason=boundary_estimate  method=none
A diff_vs_reference:    est=0.3103 ci=(0.2148, 0.4058) method=delong_wald flags=[] var_a=0.0 var_b=0.00237  z=3.72 p=0.0002
move ONE A positive to 0.15:  own auroc 0.930 (0.606, 0.991);  diff 0.2403 (0.0705, 0.4101) var_a=0.00513
```

One row moving inside the negatives changes the difference's half-width from 0.096 to
0.170; the perfectly separated case is the narrower one. Measured (20,000 replicates,
A = 10/10, B = 60/60, seed 2026): with true AUROC_A = 0.898, A is perfectly separated in
1,074 replicates and the rendered `delong_wald` difference covers the true difference in
**0.269** of them (0.943 when not separated); at true AUROC_A = 0.940, separated in
2,843 and covered in **0.728**. A 10/10 level with a good model is the ordinary case
where this fires — 5–14 % of such subgroups. The constant-score case (AUROC exactly 0.5,
var 0) renders the same way (`est=-0.2861 (−0.3988, −0.1734) delong_wald`).

Why blocker: a wrong interval and a "significant" p-value in `detail`, no flag, no reason,
directly contradicting the refusal printed for the same level two keys away. Repair:
refuse the difference when either arm's variance is zero (`boundary_estimate` on the
difference, reason carried; or route to the stratified bootstrap with the switch flagged —
the bootstrap on this exact data gave (0.2172, 0.4131), no better, so refusal is the
honest one), and a test with the 10/10 perfectly separated level that fails against
`d1fd20a`. The same guard belongs in `unpaired_delong` itself since it is public.

---

## 3. Non-blocking (record and carry)

**N1 — the `MAX_FROZEN_VARIANCE_SHARE = 0.20` justification is falsified by the engine's own rule (sentence violation).**
`deficient_class` refuses at `frozen >= MAX_FROZEN_VARIANCE_SHARE`, and the script's
`renders()` says the same. The share-0.20 shape (m = 36, 9/(9+36) = 0.2 exactly) is
therefore **refused**: `clustered_by_case` on that cohort gives `frozen_variance_share
0.2, deficient_class = 'positive'`. So the shapes the constant renders are 0.05 and 0.10
only, and "the first refused shape" is 0.20 — which covered 0.932 / 0.915 in the
builder's full run, 0.900 / 0.870 at `--quick`, and 0.925 / 0.900 at my seed 7
(R = 200, B = 500). Three sentences are false as written: bootstrap.py "Every measured
shape this constant lets through covers at or above the bar and the first refused shape
is below it"; conventions_T7.md "(kept: every measured shape it renders covers at or
above 0.90 and the first refused shape is below it)"; the note "0.20 is the loosest
*measured* value, not an extrapolation" — under the `>=` rule the loosest measured value
the feasibility logic would accept for this dimension is 0.30 (which refuses the 0.30
shape). At seed 7 the 0.30 shape itself covered 0.930 / 0.915, against 0.863 / 0.873 in
the recorded run, a gap of three Monte-Carlo standard errors — the table is
seed-sensitive at the level of the decision it supports. DEC-08 says a shape measured
≥ 0.90 renders; this one is refused. Not a wrong number for a customer (a conservative
refusal with a typed reason), so not a blocker; but the day's central DEC-08 claim is
misread by one boundary and needs re-stating with the `>=` rule in view. Minimum
coverage I measured per rendered shape under the current constants: share 0.05 → 0.900
(quick, N = 120), share 0.10 → 0.860 (quick, N = 30, B = 200); at R = 200 / B = 500 all
four rendered AUROC shapes were ≥ 0.910.

**N2 — `MIN_UNITS_PER_STRATUM` re-measured at another seed: the note's conclusion stands.**
Seed 7, R = 200, B = 500: proportion cell at p = 0.9, w = 1: u = 10 → 0.615, u = 20 →
0.865, u = 40 → 0.900; at w = 3: 0.900 / 0.915 / 0.935. AUROC, u pure cases alone: u = 2
→ 0.680 / 0.635, u = 5 → 0.875 / 0.795. `loosest feasible pair: None` at every seed. The
needs-from-Josh item is real.

**N3 — i.i.d. Newcombe differences carry no tier and no `imprecise` flag; the clustered
route's differences carry both.** `difference_unpaired` never calls
`with_precision_flags()`; `_number_from_draw` does. On `make_cohort(n=80)` the site S3
sensitivity difference has `n = 5`, half-width 0.34 and `flags = []`; the same shape
under clustering renders `['newcombe_refused_clustered', 'not_evaluable_shown_for_transparency', 'imprecise']`.
The row carries the tier, so the reader is not blind, but DEC-08's "a cell renders with
its tier annotation" is honoured on one route and not the other. The T7 sentence
"a Wilson half-width above 0.10 is imprecise" is also attached to cluster-bootstrap
half-widths, which are not Wilson.

**N4 — lens mutation sweep: 19 planted, 5 killed, 14 survived** (list in §5).
The survivors that matter: `ppv` conditioned on reference-positive rows and `npv` with
its indicator inverted both pass all 42 day-5 tests — no test observes a per-level PPV
or NPV value or its k/n. The engine is right (I checked all six proportions per level
against a direct numpy computation on `make_cohort(n=400)`: max deviation 0), but a
regression in either would ship green. Likewise Yates on the two-level χ², the Unknown
row entering the homogeneity test, a (0, 0) level entering it, `event_units` counted in
rows, and the clustered difference's `n_cases` taken from the larger side. None reopens a
wrong number today; all are named conventions with no test pinning them.

**N5 — overlapping / empty / inverted age bands are accepted silently.** `[[0,50],[40,65],
[65,200]]` → the band labelled `40-65` holds ages 50–64 only (first band wins; 45 rows
aged 40–49 sit in `0-50`); `[[65,0]]` and `[[40,40]]` put every patient in the Unknown row
with `n_outside_bands = 300` and no halt. The label `40-65` is then untrue of its row.
Customer-authored, visible in `n_outside_bands`, but a mislabelled subgroup row in a
regulatory table deserves H08 (bands must be disjoint, `lo < hi`).

**N6 — level names that collide with the Unknown row.** A customer level literally
`Unknown/missing`, or `Unknown`, `unknown `, `None`, `nan`, `NA`, `` (all day-1 missing
tokens) merges into the Unknown row and is counted in `n_unknown_missing`. NFC and NFD
spellings of `Zürich` become two levels of identical appearance (`largest_tie_first_in_level_order`).
Day-1 territory; recorded because the subgroup table is where a reviewer sees it.

**N7 — a declared reference level with zero analysed rows halts H09 "not an observed
level".** All `S3` rows given a missing score → `check_references` passes (S3 is observed
in the raw table) and `subgroup_analysis` halts with a message that is untrue (it was
observed; it was excluded). Wording only.

**N8 — a duplicated operating point (same threshold, different id) doubles the Holm
family.** `op1`/`op2` both at 0.5 → `family_size 4`, the identical test counted twice,
`p_holm` 0.3451 where one copy gives 0.1726. Customer error; an H08 on duplicate
(threshold, rule) pairs would close it.

**N9 — Fisher is restricted to r = 2.** R2 section 3.4 says Fisher "when any expected cell
< 5"; for r ≥ 3 with a small expected cell the module reports the χ² (no Freeman–Halton
in scipy) and carries `min_expected` so the reader can see it. A documented deviation,
not a defect; T7 says "exactly two levels".

---

## 4. What I could not break (this is evidence)

- **X1.** No `diff_vs_overall` and no string `overall` in any output of any construction
  (one level, all-Unknown, two levels, 100k rows, clustered, comparator, two operating
  points); the row schema has `additionalProperties: false` and rejects one planted.
- **DEC-10.** Census over every serialised Number on an i.i.d. and a clustered cohort:
  54 per-level proportion Numbers `wilson` (i.i.d.), all `cluster_bootstrap_percentile`
  with `wilson_refused_clustered` (clustered); differences `newcombe10` / `cluster_bootstrap_percentile`;
  no `delong_*`, `wilson` or `newcombe10` anywhere under a declared **or detected** plan;
  no `log_delta`/`irls_wald`. `paired_delong` and `two_by_two_metrics` are not imported.
- **Number invariant.** Every Number in 20 constructed outputs has a CI or a reason in
  `NOT_ESTIMABLE_REASONS`; no `method: none` with an interval; every flag in `FLAGS`.
- **No verdict word** in any key or string of any output (regex over
  pass/fail/verdict/met/consistent/acceptable/unbiased/well calibrated); no `status` key;
  no p-value anywhere becomes anything but a number.
- **Clustered refusals.** A case spanning two sites → `cases_span_both_groups` on every
  difference whose rows it enters, companion `clustered_data_analytic_ci_invalid`,
  `analytic_status unavailable`; the same under `clustering.unit: none` with repeated
  ids (`detected`). The rows-that-enter rule: a spanning case positive in S1 and negative
  in S2 leaves the sensitivity, specificity **and** PPV differences bootstrapped and
  refuses accuracy — consistent with decision 13. A complement that is a single case →
  `insufficient_clusters`, `n_cases 1`, tier `not_evaluable_shown_for_transparency`.
- **Reference rule.** Unknown row largest (200 of 300) under `largest` → reference S1;
  `reference_level: "Unknown/missing"` → H09; `"NA"` → H09; absent → H09; `" S1"` and
  `"S1 "` → accepted as S1 (strip); `1` and `"1"` match a level `1`; `1.0` → H09.
- **Boundary levels.** 0 positives → sensitivity `zero_denominator`, AUROC
  `insufficient_positives` on the level and on both differences, Brier `single_class`,
  tier `very_low_precision` from `event_units 0`; the level leaves the sensitivity
  homogeneity table (`n_levels 2` of 3). All-Unknown attribute → no reference, no
  differences, fairness `gaps: []`, footnote `insufficient_levels` with `n_levels 0`.
- **Fairness.** `fpr_gap` = −(specificity difference) with mirrored bounds, and equal to
  Newcombe-10 on the FP counts directly to 1e-16; `[unverified` present and enforced
  by the schema pattern; `bound`, `author`, `date`, `justification` echoed; no status.
- **Injection at 50 seeds the builder did not use** (30000–30049, n = 5,000, B = 200,
  4 s): B's `diff_vs_complement` interval excludes 0 in **50/50**; covers the true −0.06
  in 48/50; A and C cover their true +0.0292 in 46/50 and 48/50 and cover 0 in 18/50 and
  19/50; B vs a declared reference A covers −0.06 in 49/50 and excludes 0 in 49/50.
- **Scale.** 100,000 i.i.d. rows, 5 sites: 3.3 s. 20,000 rows over 10,000 cases, B = 200,
  declared clustering: 13.0 s.
- **NaN scores** inside a level are excluded by the analysis mask before banding; row
  counts over an attribute sum to `flow.included`.
- **Schema.** `subgroups`, `subgroup_attributes` and `fairness` of the edge outputs
  (all-Unknown, one level, AUROC 1.0 / 0.5, single-case complement) validate against
  their `$defs` with 0 errors.
- **Determinism.** Same output twice; a different seed moves only the bootstrap bounds.
- **Lower-is-positive** orientation: AUROC 0.870 (flipped correctly); Brier
  `not_computed_this_run` with `score_type` in detail. `y_pred`-only table: proportions
  computed, AUROC and its differences `not_computed_this_run`.

## 5. Mutation sweep — the lens's own 19 mutants (not on the committed list)

Planted with the committed script's own `plant`/`run_marker` machinery against `-m day5`
(copy of the tree, `PYTHONPATH` asserted). **19 planted, 5 killed, 14 survived; 314 s.**
Every survivor changes behaviour; none is equivalent.

| Mutant (`stats/subgroups.py` unless noted) | What it changes | Result |
|---|---|---|
| `npv` indicator `~pos[sel]` → `pos[sel]` | NPV becomes 1 − NPV | **SURVIVED** |
| `ppv` conditioned on `pos` instead of `pred` | PPV becomes sensitivity | **SURVIVED** |
| Unknown row enters the homogeneity test | contradicts decision 12 | **SURVIVED** |
| a (0, 0) level enters the χ² table | scipy raises on the zero expected cell | **SURVIVED** |
| `correction=True` (Yates) on the two-level χ² | different p | **SURVIVED** |
| clustered difference `n_cases = max(...)` | wrong count, wrong tier | **SURVIVED** |
| `event_units = events` (rows, not cases) | wrong row tier under clustering | **SURVIVED** |
| AUROC difference evaluability checks side a only | `delong_covariance` raises on a 1-positive complement | **SURVIVED** |
| overlapping bands: last band wins | convention inverted | **SURVIVED** |
| declared `reference_level` not stripped | `" S1"` → H09 | **SURVIVED** |
| row tier ignores event units | | killed |
| clustered proportion difference drops `precision_flags` | no tier on the difference | **SURVIVED** |
| `discrimination.py`: `unpaired_delong` renders a zero-width `delong_wald` at `se == 0` | the B2 shape, made worse | **SURVIVED** |
| orientation ignored (`score = raw_score` always) | AUROC of a `lower_is_positive` model < 0.5 | **SURVIVED** |
| Brier computed on a `lower_is_positive` probability | wrong Brier | **SURVIVED** |
| selection rate = prevalence | | killed |
| `diff_vs_complement` silently = `diff_vs_reference` | | killed |
| `n_unknown_missing` counts only `None` | | killed |
| `discrimination.py`: p-value one-sided | | killed |

Read with the committed sweep's 21/21: the committed list is drawn from the tests, so it
measures the tests' reach over the conventions the builder chose to pin, not the module's.
Fourteen behaviours a customer would see — including two of the six proportions in every
row and both score-orientation paths — have no observer in `-m day5`. The engine is right
on every one of them today (each was checked by construction above); the gap is that a
regression in any of them ships green.

## 6. Sentences refused / falsified

Falsified by construction (each is a finding above): the three `MAX_FROZEN_VARIANCE_SHARE`
sentences in N1; the T7 sentence "Nothing beside a p-value is a status" is true, but the
p-value beside it is computed on dependent rows (B1); "z and the two-sided p are detail,
never a verdict" is true and the p in B2 is 0.0002 from a frozen arm.

Sentences I refused to write in this note: "the subgroup module is now correct under
clustering" (B1 says otherwise); "the coverage bar holds" (it was measured on a grid at
one seed and moved by 0.07 at another); "the day-5 suite would catch a wrong PPV/NPV"
(it would not — N4).

## 7. Could not check

- `--full` coverage run (743 s claimed) — not re-run; the recorded table's values at
  R = 400 were compared against my R = 200 / B = 500 run only.
- The 300-seed 0.933 / 0.943 DeLong coverage figure in the F18 test docstring — 50 new
  seeds gave 0.96 / 0.98, consistent, not the same experiment.
- Newcombe 1998 Table II and Kleinberg/Chouldechova — primary sources not fetched; the
  `[unverified]` markings are carried, and my formula reproduces the fixture to 4 dp.
- pROC on the unpaired difference — no capture exists.
- The renderer's use of `tier` vs the difference cell's flags (N3) — no renderer yet.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider          # 352 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day5  # 42 passed
python scripts/mutation_sweep.py --marker day5   # 21 planted, 21 killed, 0 survived
python scripts/coverage_bar.py --quick           # feasibility: loosest feasible pair None
```
Attack scripts (rederive.py, attack1.py, attack2.py, my_mutants.py) lived in the session
scratchpad `lens-E5-r1-fresh-attack/` and were not committed; the constructions are
described inline above so each can be rebuilt from this note.
