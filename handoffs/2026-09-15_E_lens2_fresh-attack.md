# Lens 2 (fresh attack, repair round 1) — 2026-09-15 — Lane E day 5 (`stats.subgroups`) at `9da4401`

Attacking `9da4401` cold (the repair of `d1fd20a`; lens-1 notes read only to re-verify their
closures). Every number below was measured in this session in a detached worktree at
`9da4401` (and a second at `d1fd20a` for the regression proof) with `PYTHONPATH` forced to
that worktree's `src` and proved (`proofpack.__file__` printed from the worktree before any
count was trusted). Nothing was committed; both worktrees were removed at the end.

## Verdict: **FAIL — 1 blocker, 11 non-blocking, 5 sentence violations.**

Both lens-1 blockers are closed on the route they were found on, and the closures hold under
my constructions: the heterogeneity chi-square is a typed refusal under `declared` and
`detected` (my spanning-case and one-row-per-case constructions, F6 tripled), and the unpaired
DeLong difference refuses when either arm's variance is zero (perfect separation in either
arm, reversed separation, constant scores, both arms separated). RG-B1 is closed (the 30-cell
numpy pin; the four inverted-proportion mutants die). The arithmetic is right: Wilson,
Newcombe-10, the DeLong placement-value variance, Holm and the chi-square / Fisher tests agree
with my own implementations from the published formulae to ≤ 3e-15 on the fixtures, 300 random
(k, n), 200 random 2×2 pairs, 50 random score/label pairs, 100 random p-sets and 200 random
r×2 tables, and with statsmodels, scipy and scikit-learn where those exist.

The blocker is FA-B2's shape on the route the repair did not touch. **Under a clustered
plan, a difference whose one side is frozen in every resample — a perfectly separated level's
AUROC, or a level's proportion at 0/n or n/n — is rendered `cluster_bootstrap_percentile`
with an interval that is the other side's alone, no flag, no reason,** while the same row's
own cell two keys away is refused `boundary_estimate`. Measured conditional on the shape
(R = 200, B = 200, seed 2026): the AUROC difference covers the truth in **0.295** of
replicates at a nominal 0.95; the sensitivity difference in **0.615**. The repair test's own
`separated_level_cohort()` reproduces it the moment each row is duplicated under a `case_id`.

---

## 1. What I re-ran, and what held

| Check | Result |
|---|---|
| Suite at `9da4401` (worktree, `PYTHONPATH` proved) | `359 passed, 1 skipped, 1 xfailed in 41.88s` (note: 38.88 s) |
| `-m day5` | `49 passed, 312 deselected in 15.66s` |
| `-m day1` / `day2` / `day3` / `day4` | `59 passed, 1 skipped` / `40 passed` / `29 passed, 1 xfailed` / `182 passed` — identical to the repair-r7 block and the repair note |
| repair-r7's 27 `test_bootstrap.py` tests | `27 passed, 155 deselected` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `50 files already formatted` |
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.` |
| Day-4 constants | `MIN_UNITS_PER_STRATUM = 2`, `MAX_FROZEN_VARIANCE_SHARE = 0.20` — unchanged; only their docstrings moved in the diff |
| Tests weakened | none: `git diff --name-status d1fd20a 9da4401 -- tests/` → `M tests/test_subgroups.py` only; no skip/xfail/`.only` added, nothing deleted, no marker removed; `pyproject.toml` and CI untouched; the seven new tests carry no marker of their own and are collected by the file's `day5` mark |
| Regression proof (new `tests/test_subgroups.py` copied into the `d1fd20a` worktree) | `3 failed, 4 passed` — the three E lines the repair note quotes (`KeyError: 'clustering_route'`; `assert (None == 'boundary_estimate')` with the `delong_wald` Number; `Expected regex: 'analysed rows'`). The note says "3 failed, 5 passed"; the `-k` expression selects seven tests |
| `scripts/mutation_sweep.py --marker day5` | **29 planted, 29 killed, 0 survived; 334 s** (note: 341 s) |
| `scripts/coverage_bar.py --quick` | 38 s wall (docstring: 41 s); `loosest feasible pair: None`; share-0.20 row **0.900 / 0.870** at the recorded seed |
| Schema | the separated cohort (i.i.d. and clustered), one level, S3-all-excluded, F6 tripled (detected), two operating points: 0 errors each against `output_schema_v1.json` |

### Re-derivations (my code, no repo code for the statistic under test; `probe/rederive.py`, seed 20260915)

| Statistic | Written from | Compared on | Max abs deviation |
|---|---|---|---|
| Wilson score limits | Newcombe 1998 method 3 (centre / radius form) | 300 random (k, n) vs `wilson_bounds` and `statsmodels.proportion_confint(method="wilson")` | 2.2e-16 / 2.2e-16; F8 half-widths 0.0851 / 0.0596 / 0.0341 reproduced |
| Newcombe method 10 | square-and-add of the Wilson limits | 200 random pairs (20 at 0/n or n/n) vs `newcombe10_bounds`; `difference_unpaired` method/`n` asserted | 2.2e-16; F14: (0.0524, 0.3339), (0.1705, 0.8090), (0.6791, 1.0000), frozen 30/40 vs 100/120 → (−0.2453, 0.0493) |
| DeLong 1988 variance | placement values `V10_i = mean_j psi(x_i, y_j)`, `V01_j = mean_i psi`, `S10/m + S01/n`, ddof 1 | 50 random score/label pairs (a third rounded to create ties) vs `unpaired_delong` and `sklearn.roc_auc_score` | AUC 3.3e-16, relative variance 2.8e-16, Wald bounds 3.3e-16, two-sided p 2.9e-15 |
| Holm step-down | Holm 1979 | 100 random p-sets vs `holm()` and `multipletests(method="holm")` | 0.0 / 0.0; F6 → [0.036, 0.08, 0.30] |
| Pearson χ² of homogeneity, Fisher exact | `sum (O−E)²/E`, hypergeometric pmf sum | F6 (4.6327, df 2, p 0.0986; Fisher 0.1084) and 200 random r×2 tables vs `_homogeneity_test`, `chi2_contingency(correction=False)`, `fisher_exact`; Fisher branch taken exactly when r = 2 and min expected < 5 (13 of 200) | 0.0 / 5.6e-17 |

### Injection at 50 seeds neither the builder nor lens 1 used (41000–41049, n = 5,000, B = 200, 4 s)

B's `diff_vs_complement` interval excludes 0 in **49/50**; covers the true −0.06 in 47/50. A
and C cover their true +0.0292 in 49/50 and 48/50 and cover 0 in 15/50 and 22/50. B against
the declared reference A excludes 0 in 49/50 and covers −0.06 in 48/50. The ≥ 90 % claim
holds on my seeds.

### DEC-08 script at another seed and B (seed 7777, R = 200, B = 500, MC se 0.021; `probe/dec08_seed.py`, the committed script's own shape generators)

| shape | N = 30 | N = 120 | renders under (2, 0.20)? |
|---|---|---|---|
| AUROC share 0.05 (m = 171) | 0.940 | 0.955 | yes |
| AUROC share 0.10 (m = 81) | 0.940 | 0.935 | yes |
| AUROC share 0.20 (m = 36) | 0.910 | 0.930 | no (refused) |
| AUROC share 0.30 (m = 21) | 0.930 | 0.885 | no |
| AUROC u = 2 pure cases, m = 0 | 0.700 | 0.635 | **yes** |
| AUROC u = 3 / u = 5, m = 0 | 0.840 / 0.870 | 0.730 / 0.775 | **yes** |

Proportion cell (renders at every u ≥ 2): p = 0.5 → u = 2: 0.435 / 0.435 (w = 1 / 3), u = 5:
0.900 / 0.820, u = 10: 0.975 / 0.930; p = 0.9 → u = 2: **0.160** / 0.335, u = 5: 0.390 /
0.685, u = 10: 0.665 / 0.900, u = 20: 0.910 / 0.900, u = 40: 0.905 / 0.935. **Minimum
coverage over the 30 rendered shapes: 0.160; 14 of 30 rendered shapes are below the bar.**
The frozen-share half holds at my seed (rendered shapes ≥ 0.935; the refused 0.20 shape
again ≥ 0.90; 0.30 straddles). The `MIN_UNITS_PER_STRATUM = 2` half does not, on either
family — the escalated item, restated in T7, and see N3 for the sentence that mis-scopes it.

---

## 2. Blocker

### B1 — under clustering, a difference with one side frozen is rendered from the other side alone (blocker, wrong interval, no flag)

`_bootstrap_difference` refuses when a side's resampler has a deficient class and when the
two-sided draw has `lo == hi`. It does not look at either side's draw on its own. When side
a's statistic is the same in every resample — a level perfectly separated (AUROC 1.0 or 0.0
in every case-resample), a level with constant scores (0.5 in every resample), or a level's
proportion at k = n or k = 0 — `values = const − stat_b(draw)` and the percentile interval
is the interval of side b alone, shifted. The engine's own single-cell rule on the same data
refuses: `proportion_ci` / `auroc_ci` under clustering hit `lo == hi` in
`bootstrap_percentile` and return `boundary_estimate`, which is what the row's `metrics`
cell shows. The difference cell beside it renders with `cluster_bootstrap_percentile`,
`analytic_status: refused_clustered`, flags `['delong_refused_clustered', ...]` /
`['newcombe_refused_clustered', ...]`, and `not_estimable_reason: null`.

Repro (one line each; `probe/repro_b1.py`, the repair test's own cohort, each row duplicated
under a `case_id`, clustering declared):

```
c = separated_level_cohort(); d = {k: [v[i//2] for i in range(2*len(c["y_true"]))] for k, v in c.items()}; d["case_id"] = [f"c{i//2}" for i in range(2*len(c["y_true"]))]
rep = run(d, criteria_for(SITE_REF_B, clustering={"unit": "case_id", "declared_by": "t"})); r = rep.row("site", "A")
r["metrics"]["auroc"]["number"]         → est 1.0, ci None, boundary_estimate, ['delong_refused_clustered', 'very_low_precision']
r["diff_vs_reference"]["auroc"]["number"] → est 0.2256 (0.1599, 0.3054) cluster_bootstrap_percentile, reason None, resampling.a.deficient_class None
r["metrics"]["op1"]["sensitivity"]["number"] → est 1.0, k 20, n 20, n_cases 10, boundary_estimate
r["diff_vs_reference"]["op1"]["sensitivity"]["number"] → est 0.35 (0.25, 0.4671) cluster_bootstrap_percentile, reason None
```

The i.i.d. twin of the first pair is exactly what `test_unpaired_delong_refuses_the_difference_
when_either_arm_has_zero_variance` asserts is refused; the same rows with a case column
render. Also reproduced on `attack2.py`'s constant-score and reversed-separation levels
(clustered `const`: own 0.5 `boundary_estimate`, difference −0.2547 (−0.3241, −0.1770);
clustered `perfect_reversed`: own 0.0, difference −0.7134 (−0.7790, −0.6334)).

Measured (`probe/frozen_arm_clustered.py`, one row per case with clustering declared — the
route a lesion-level table with a declared `case_id` takes — R = 200 rendered replicates
conditioned on the shape, B = 200, seed 2026):

- **AUROC**: A = 10/10 cases with true AUROC 0.898 (binormal), B = 60/60 at 0.750; A came
  out perfectly separated in 200 of 3,713 samples (5.4 %); the rendered difference covered
  the true 0.148 in **0.295** (MC se 0.035), mean width 0.170; flags
  `['delong_refused_clustered', 'very_low_precision']`.
- **Sensitivity**: A = 10 positive cases at true 0.90 observed 10/10 (200 of 600 samples,
  33 %), B = 60 at 0.80; the rendered difference covered the true 0.10 in **0.615** (MC se
  0.035), mean width 0.194; flags `['newcombe_refused_clustered', 'very_low_precision',
  'imprecise']`. For scale, Newcombe-10 on the same 10/10 vs 48/60 gives (−0.089, 0.318).

Why blocker: a wrong interval with no flag and no typed reason, contradicting the refusal
printed for the same level in the same row — the class the day-4 repairs and FA-B2 were
about. A 10-case subgroup at 10/10 sensitivity is the ordinary case in a small clustered
validation table, not a corner. Repair shape: in `_bootstrap_difference`, refuse with
`boundary_estimate` when either side's draws are all identical (the single-cell rule applied
per side), estimate carried; a test on `separated_level_cohort()` duplicated under a
`case_id` for both the AUROC and the proportion difference that fails against `9da4401`; a
sweep mutant. Reachability: through `subgroup_analysis` (the day-5 public API); the CLI
pipeline does not call it yet, so no customer reaches it today — it reaches every customer
the day it is wired.

**Sentence falsified (T7, "Differences"):** "The AUROC difference is refused with
`boundary_estimate` (estimate carried, no z, no p) when either side's DeLong variance is zero
— a perfectly separated side, whose own AUROC the engine already refuses for the same
reason — because the interval would then be the other side's alone." Under clustering a
perfectly separated side is refused for the same reason on its own cell, the interval is the
other side's alone, and the difference is not refused.

---

## 3. Non-blocking (record and carry)

**N1 — the `delong_wald` difference interval can leave [−1, 1] with no flag and no clip.**
3,000 draws of 10/10 vs 10/10 arms (binormal ±2): max `ci_hi` **1.088** with est 0.890,
`flags == []`. The single-AUROC path (day 3) clips the Wald bounds to [0, 1] and flags
`wald_interval_exceeds_unit_range`; the difference path does neither, and Newcombe-10 clamps
its bounds to [−1, 1]. Reachable with a level near 1.0 against a level below 0.5 at 10/10.
Not a wrong number under its method; an impossible bound printed without the annotation the
engine gives the same event elsewhere.

**N2 — a sentence that contradicts its own parenthetical (sentence violation).** T7: "That
refused shape measured at or above the bar at every seed tried — 0.932 / 0.915 in the
recorded run (Monte-Carlo error 0.015), 0.900 / **0.870** at `--quick`, 0.925 / 0.915 at seed
20260916". `bootstrap.py`'s `MAX_FROZEN_VARIANCE_SHARE` docstring: "a shape that measured at
or above the bar (0.932 / 0.915; 0.900 / 0.870 at `--quick`, R = 100; …)". The repair note:
"the 0.20 shape met the bar at every seed tried". 0.870 < 0.90, re-measured this session at
the recorded seed (`--quick`, 38 s). The sentence needs "at R ≥ 200" or to say the quick run
put the N = 120 cell below the bar. This is the FA-N1 sentence class re-entering through the
FA-N1 repair.

**N3 — "not implemented for the proportion route" mis-scopes the DEC-08 gap (sentence
violation).** T7's last paragraph: "The DEC-08 refusal-below-the-bar is **not implemented**
for the proportion route". The AUROC route renders the u = 2, m = 0 shape at 0.715 / 0.620 in
the recorded table two sections above, and at 0.700 / 0.635 at my seed. The refusal below the
bar is not implemented on either route; the sentence implies it is on one.

**N4 — the RG-N2 repair introduced a test name asserting an ordering the test does not
inspect (sentence violation).** `test_the_two_sided_bootstrap_draws_side_b_from_the_cell_
generator_after_side_a`, docstring "within one run side a and side b must consume the *same*
generator in turn". Mutant `L2_side_b_drawn_before_side_a` (side b's draw taken before side
a's, same generator) **survives `-m day5`**; it is not equivalent — on the test's own index
vectors the interval is (0.0, 0.4643) with a-then-b and (0.0696, 0.4762) with b-then-a
(`probe/order.py`). The test inspects that both sides move with the generator and that a
seed reproduces; it does not inspect order. Rename to what it inspects, or record the two
index sequences and assert their interleaving.

**N5 — the verdict tokeniser's docstring over-claims (sentence violation, minor).**
`test_the_verdict_grep_flags_every_phrase_the_brief_names`: "Each phrase, and its hyphenated
and inflected spellings, must trip the tokeniser". `_verdict_flagged` on "passing",
"failing", "meets", "verdicts", "miscalibrated", "satisfied", "successful" → `False`
(`probe/verdict.py`). No output today carries them; the sentence claims more than the set
holds.

**N6 — lens mutation sweep: 18 planted, 5 killed, 13 survived** (`probe/my_mutants.py`,
driven through the committed script's `make_copy` / `plant` / `run_marker`, `PYTHONPATH`
asserted in the copy). New survivors, not on lens 1's or RG's lists: the two-sided bootstrap
refuses on **side a's deficient class only** (`for res in (res_a,)`); a **zero-width
two-sided interval is rendered** (the `lo == hi` refusal removed); the **clustered proportion
difference's sign** flipped (`d = k2/n2 − k1/n1`; the i.i.d. sign is pinned, the clustered
one is not); and N4's ordering mutant. Re-confirmed survivors from lens 1 / RG: Yates on the
two-level χ², the Unknown row entering the homogeneity test, clustered `n_cases = max`,
`event_units` in rows, AUROC-difference evaluability on side a only, orientation ignored,
single-class Brier not refused, clustered proportion difference without tier flags, declared
reference not stripped. Killed: the detected route running the χ² (the FA-B1 test), the
complement including the level itself (F14's complement test — X1 in substance is pinned),
the clustered footnote refusal with the wrong typed reason, the frozen-arm guard on arm a
only, the DeLong p-value one-sided. Every survivor changes behaviour; each was verified
correct today by construction (§4).

**N7 — a level with zero analysed rows leaves no trace.** All S3 scores missing →
`level_order ['S1', 'S2']`, no S3 row, `n_unknown_missing 0`; a declared band with no rows
(`[[0,40],[40,65],[65,80],[80,200],[0,200]]`) → four rows, the fifth band nowhere; a declared
`reference_level` that is absent halts H09 when other levels exist but returns
`reference_level: None` without a halt when every row is Unknown (`_choose_reference` returns
before checking the label). `flow.excluded_missing_score` counts the rows, not the level.
Annotate-never-omit at row level: an attribute block could carry the levels observed in the
table but absent from the analysed rows.

**N8 — under clustering the footnote's typed reason names clustering where there was never
a test to run.** One evaluable level → `n_levels 1, clustered_data_analytic_ci_invalid`;
every row Unknown → `n_levels 0`, same reason; the i.i.d. route says `insufficient_levels`
for both. Both reasons are true; the one printed is the less informative.

**N9 — `heterogeneity_footnote` is public with `clustering_route="none"` as the default**, so
a direct call that forgets the argument computes the row test
(`heterogeneity_footnote({"op1": {"sensitivity": F6}})` → p 0.0986). `subgroup_analysis`
always passes the route; only a direct caller reaches this.

**N10 — note accuracy.** "3 failed, 5 passed" for the regression proof: 3 failed, 4 passed
(seven tests selected). `--quick` "41 s": 38 s here. The sweep "341 s": 334 s. Numbers, not
defects.

**N11 — committed sweep bookkeeping (pre-existing).** Mutant `unknown_row_not_marked` carries
`what="the output schema no longer accepts one of the day-5 typed reasons"`, a copy of the
next mutant's text.

**Carried from lens 1, re-verified still reproducing today:** FA-N3 (i.i.d. Newcombe
differences carry no tier: S3 n = 5, half-width 0.377, `flags []`); FA-N5 (bands
`[[0,50],[40,65],[65,200]]` → the row labelled `40-65` holds ages 50–64, 45 forty-somethings
sit in `0-50`; `[[65,0]]`, `[[40,40]]` → 300 in Unknown, no halt); FA-N6 (`Unknown`, `nan`,
`NaN`, ``, ` `, `None`, `null`, `NA`, `N/A`, `unknown`, `missing` all merge into the Unknown
row; `-` is a level; NFC and NFD `Zürich` are two levels of 100 rows each; `S1` and
`S1\u200b` are two levels); FA-N8 (the same threshold declared thrice → `family_size 6`,
Holm 0.5235 where one copy gives 0.1745; a duplicate op *id* halts H08); FA-N9 (Fisher at
r = 2 only). Not re-listed as findings.

---

## 4. What I could not break (this is evidence)

- **FA-B1 closed.** Declared and detected, on F6 tripled and on my spanning-case cohort:
  every footnote entry `test None, p_raw None, p_holm None, n_levels 3,
  clustered_data_analytic_ci_invalid`, `family_size 0`, route recorded; the χ² on the same
  rows without ids is 3 × 4.6327; a declared `case_id` with one row per case is also refused
  (conservative, by the day-4 declared rule). An explicit `plan` + `cluster_ids` → refused;
  `ClusterPlan(True, 'declared', 100, 100)` over unique ids → `ValueError contradicts`.
- **FA-B2 closed on the i.i.d. route.** Perfect separation in arm a, in arm b, reversed
  (AUC 0.0), constant scores, both arms separated → `boundary_estimate`, est carried, `z` /
  `p_value` `None`, `analytic_status unavailable`; the guard is at zero — an arm with
  `S10 = 0` but `S01 > 0` (AUC 0.90, var 0.01) renders `delong_wald`.
- **RG-B1 closed:** the 30-cell numpy pin passes; the four proportion mutants die in the
  committed sweep.
- **X1.** No `diff_vs_overall` and no string `overall` in any output of any construction
  (one level, all-Unknown, spanning case, two operating points, 100k rows, y_pred-only,
  lower-is-positive); the complement-includes-the-level mutant is killed by F14.
- **DEC-10.** Census over every serialised Number in fourteen constructed reports: every
  per-level proportion is `wilson` (i.i.d.) or `cluster_bootstrap_percentile` (clustered) or
  `none` with a typed reason; no `wilson`, `newcombe10`, `delong_*` anywhere under a declared
  or detected plan (354 Numbers: 160 `cluster_bootstrap_percentile`, 194 `none`).
- **Number invariant.** Every Number in every construction re-validates through
  `Number(**d)`: a CI or a reason in `NOT_ESTIMABLE_REASONS`, no half-open interval, no
  `method: none` with an interval, no inverted bounds.
- **No verdict word** in any key or string of any output (pass/fail/verdict/met/consistent/
  acceptable/unbiased/calibrated/passes/fails); every `p_raw` / `p_holm` is a float or
  `None`; a p-value never sits beside a reason.
- **Reference rule.** Unknown row largest (200 of 300) → reference S1
  (`largest_tie_first_in_level_order`); `Unknown/missing`, `unknown`, `NA`, `nan`, ``, `s1`,
  `S1\u200b`, `1`, `1.0` → H09 with `reference_level` in `detail`; `" S1 "` → S1.
- **Boundary levels.** 0 positives → sensitivity `zero_denominator`, PPV 0/50 Wilson
  (0, 0.071), AUROC `insufficient_positives` on the cell and both differences, Brier
  `single_class` with est, tier `very_low_precision` (events 0); 0 negatives → specificity
  `zero_denominator`, NPV 0/n, `insufficient_negatives`; the level leaves the χ² table
  (`n_levels 2`). All-Unknown → no reference, `diff_vs_reference` and `diff_vs_complement`
  `None`, fairness `gaps: []`, footnote `insufficient_levels` with `n_levels 0`.
- **Clustered refusals.** A case spanning two sites → `cases_span_both_groups` on
  specificity, accuracy and AUROC of every difference its rows enter, companion
  `clustered_data_analytic_ci_invalid`, footnote refused; the same under `unit: none`
  (`detected`). A single-case complement → `zero_denominator` / `insufficient_positives`
  (the case was all-negative), the single-case level `n_units 1`, tier
  `not_evaluable_shown_for_transparency`.
- **Orientation.** `lower_is_positive` with rule `<=`: per-level AUROC equals
  `roc_auc_score(y, −score)` to 6 dp on three sites; sensitivity equals the hand count;
  Brier `not_computed_this_run`. `y_pred`-only: proportions Wilson, AUROC and its
  differences `not_computed_this_run`.
- **Scale.** 100,000 i.i.d. rows, 5 sites, 3 attributes: 3.0 s. 30,000 rows over 15,000
  declared cases, two attributes, B = 200: 29.6 s.
- **NaN scores** inside a level are excluded before banding; site rows sum to 281 =
  `flow.included`.
- **Two operating points** (clustered and i.i.d.): `metrics` keys `op1, op2, auroc, brier`;
  four footnote entries; one Holm family per attribute.
- **Sweep isolation.** `assert_imports_from_copy` resolved to the copy in every run;
  `.pth` editable-install entries sit after `PYTHONPATH` on `sys.path`, which is why the
  copy wins — I found no third way to defeat it beyond RG-N6's two.

## 5. Sentences refused / falsified

Falsified by construction (each a finding above): the T7 "refused … because the interval
would then be the other side's alone" sentence (B1); "at or above the bar at every seed
tried" beside 0.870 (N2); "not implemented for the proportion route" (N3); the
`…_after_side_a` test name and "in turn" (N4); "its hyphenated and inflected spellings must
trip the tokeniser" (N5).

Sentences I refused to write in this note: "the subgroup module is now correct under
clustering" (B1); "the frozen-arm shape is closed" (closed on one route of two); "the
coverage bar holds" (14 of 30 rendered shapes below it at my seed, on the escalated half);
"the day-5 suite pins the clustered differences" (sign, side-b deficiency and zero width are
unobserved); "the mutation sweep shows the tests have teeth" (29 declared mutants die; 13 of
my 18 do not).

## 6. Could not check

- `--full` (743–781 s) not re-run; the recorded R = 400 table was compared against my
  R = 200 / B = 500 run at seed 7777 only.
- pROC `roc.test(paired = FALSE)` — no capture; `[unverified]` stands.
- Newcombe 1998 Table II against the primary PDF — `[unverified]` stands; my formula
  reproduces the fixture to 4 dp.
- The 20,000-replicate 0.269 figure in the `unpaired_delong` docstring — not re-run; my
  clustered twin of the same shape measured 0.295 at R = 200.
- The renderer's reading of `tier` against a difference's flags (FA-N3) — no renderer yet.

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider          # 359 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day5  # 49 passed, 312 deselected
python -m ruff check . && python -m ruff format --check .
python scripts/mutation_sweep.py --marker day5   # 29 planted, 29 killed, 0 survived
python scripts/coverage_bar.py --quick           # share 0.20 row: 0.900 / 0.870
```
Attack scripts (`rederive.py`, `attack1.py`, `attack2.py`, `frozen_arm_clustered.py`,
`dec08_seed.py`, `injection.py`, `my_mutants.py`, `order.py`, `repro_b1.py`) lived in the
session scratchpad `lens-E5-r2-fresh-attack/probe/` and were not committed; every
construction is described inline so it can be rebuilt from this note. Worktrees removed; the
main tree was left as found apart from this file.
