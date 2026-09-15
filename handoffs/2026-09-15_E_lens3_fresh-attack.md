# Lens 3 (fresh attack, repair round 2) — 2026-09-15 — Lane E day 5 (`stats.subgroups`) at `e4c4f7e`

Attacking `e4c4f7e` cold (the round-2 repair of `9da4401`; the lens-1 and lens-2 notes read
only to re-verify their closures). Every number below was measured in this session in a
detached worktree at `e4c4f7e` (and a second at `9da4401` for the regression proofs) with
`PYTHONPATH` forced to that worktree's `src` and proved (`proofpack.__file__` printed from
the worktree before any count was trusted). Nothing was committed; both worktrees were
removed at the end; the main tree was left as found apart from this file.

## Verdict: **PASS — 0 blockers, 7 non-blocking, 0 sentence violations.**

Lens 2's blocker is closed by execution, not by the note: on its own two shapes rebuilt at my
seed (A perfectly separated in 100 of 2,206 samples; A at 10/10 in 100 of 256) the pre-fix
tree renders a `cluster_bootstrap_percentile` interval that covers the truth in **0.35** /
**0.58** of replicates, and `e4c4f7e` refuses every one of the 200 with `boundary_estimate`,
`frozen_sides ('a',)`. The arithmetic is right: Wilson, Newcombe-10, the DeLong
placement-value variance, Holm and the chi-square / Fisher tests agree with my own
implementations from the published formulae to ≤ 3.6e-16 on the fixtures, 300 random (k, n),
220 random 2×2 pairs (20 at a boundary), 50 random score/label pairs, 100 random p-sets and
200 random r×2 tables, and with statsmodels, scipy and scikit-learn where those exist. The
measurement nobody had made — the coverage of the two-sided cluster bootstrap on shapes that
*render* — is at or above the 0.90 bar on all thirteen shapes I tried (0.904–0.990).

The findings are coverage gaps in the tests, not wrong numbers: two mutants that make every
rendered clustered difference one side's interval alone survive the **full** suite (364
passed), as does a day-4 mutant that makes every bootstrap ignore the requested level. Each is
non-equivalent by construction; none reopens a wrong number today.

---

## 1. What I re-ran, and what held

| Check | Result |
|---|---|
| Suite at `e4c4f7e` (worktree, `PYTHONPATH` proved) | `364 passed, 1 skipped, 1 xfailed in 43.86s` (note: 38.63 s) |
| `-m day5` | `54 passed, 312 deselected in 17.52s` |
| `-m day1` / `day2` / `day3` / `day4` | `59 passed, 1 skipped` / `40 passed` / `29 passed, 1 xfailed` / `182 passed` — identical to the repair-r7 block and both repair notes |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `52 files already formatted` |
| `python -m proofpack.cli doctor --offline` | `All essential checks passed.` |
| `scripts/mutation_sweep.py --marker day5` | **34 planted, 34 killed, 0 survived; 433 s** (note: 405 s) |
| `scripts/coverage_bar.py --quick` | 39 s; table byte-identical to the recorded one (share 0.20 row **0.900 / 0.870**; `loosest feasible pair: None`) |
| seed 20260916, one generator shared across cells, R = 200, B = 500 | `[[0.94, 0.955], [0.88, 0.915], [0.92, 0.9]]` — the **0.880** T7 now records reproduces exactly |
| Day-4 constants at `3ea2bfd` / `9da4401` / `e4c4f7e` | `MIN_UNITS_PER_STRATUM = 2`, `MAX_FROZEN_VARIANCE_SHARE = 0.20`, `LOW/VERY_LOW_PRECISION_UNITS = 10/30`, `FEW_EVENTS = 5`, `MIN_USABLE_FRACTION = 0.90` — unchanged; only docstrings moved |
| Tests weakened | none: `git diff --name-status` touches `tests/test_subgroups.py` only; no `skip`/`xfail`/`.only` added, no test deleted, no marker removed; 49 → 54 `def test_` (five new, one renamed); `pyproject.toml`, `schema/`, CI untouched |
| Regression proof (new `tests/test_subgroups.py` copied into the `9da4401` worktree, the note's `-k`) | **`5 failed, 2 passed, 47 deselected in 1.65s`** — the five E lines the note quotes verbatim (`assert None == 'boundary_estimate'` with `ci_lo 0.1598…`; `no attribute '_frozen_sides'`; `'clustered_da…ic_ci_invalid' == 'insufficient_levels'`; `DID NOT RAISE TypeError`; `'at every seed tried' not in …`) |
| Output diff `9da4401` → `e4c4f7e` on five cohorts (i.i.d. 400; clustered 3-site; detected ×3; F6 clustered; separated clustered) | i.i.d.: byte-identical. Clustered: the only changes are the added `frozen_sides` key and the cells whose one side is frozen (3 cells on the 3-site cohort — an `80-200` age band at 24/24 sensitivity and 32/32 NPV, own cells already `boundary_estimate`; 14 on the separated cohort). **0 rendered non-frozen cells differ**, as the note claims |
| `import proofpack.stats.subgroups` with `scipy`, `statsmodels`, `sklearn` hidden | imports; `_homogeneity_test` → `scipy_unavailable` |
| Schema | every constructed report (§4) validates against `output_schema_v1.json` with 0 errors, the frozen-refused fairness block included |
| FA-N11 (lens 2) | does not reproduce at `9da4401` or `e4c4f7e`: `unknown_row_not_marked` carries its own `what` — the repairer is right |

### Re-derivations (my code, no repo code for the statistic under test; `probe/rederive.py`, seed 31337)

| Statistic | Written from | Compared on | Max abs deviation |
|---|---|---|---|
| Wilson score limits | Newcombe 1998 method 3 (centre / radius form) | 300 random (k, n) vs `wilson_bounds` and `statsmodels.proportion_confint(method="wilson")` | 2.2e-16 / 3.3e-16; F8 half-widths 0.0851 / 0.0596 / 0.0341 reproduced |
| Newcombe method 10 | square-and-add of the Wilson limits | 220 random pairs (10 at n/n, 10 at 0/n vs n/n) vs `newcombe10_bounds` and `difference_unpaired` (method `newcombe10`, `n = min` asserted) | 3.6e-16; est 0.0; F14: (0.0524, 0.3339), (0.1705, 0.8090), (0.6791, 1.0000) reproduced to 4 dp; hand 30/40 vs 100/120 → (−0.2453, 0.0493) |
| DeLong 1988 variance | placement values `V10_i = mean_j psi`, `V01_j = mean_i psi`, `S10/m + S01/n`, ddof 1 | 50 random score/label pairs (a third rounded to make ties) vs `delong_variance`, `sklearn.roc_auc_score`, and the unpaired difference's Wald bounds and two-sided p vs `unpaired_delong` | AUC 2.2e-16, relative variance 2.6e-16, sklearn 2.2e-16, Wald bounds 3.3e-16, p 3.3e-15 |
| Holm step-down | Holm 1979 | 100 random p-sets vs `holm()` and `multipletests(method="holm")` | 0.0 / 0.0; F6 → [0.036, 0.08, 0.30] |
| Pearson χ² of homogeneity, Fisher exact | `sum (O−E)²/E` with scipy's χ² tail; hypergeometric pmf sum | F6 (4.6327, df 2, p 0.0986; Fisher site 1 vs 2 0.1084) and 200 random r×2 tables vs `_homogeneity_test`, `chi2_contingency(correction=False)`, `fisher_exact`; the Fisher branch taken exactly when r = 2 and min expected < 5 (5 of 200) | 0.0 / 1.1e-16 |

### The measurement nobody had made: coverage of the two-sided cluster bootstrap on shapes that render (`probe/two_sided_coverage.py`, R = 300, B = 200, seed 20260915, MC se 0.017)

Lens 2 measured the interval *conditional on a frozen side*; the repair refuses that. What
does the engine's `_bootstrap_difference` cover on the shapes it now renders? Coverage is over
rendered replicates; refusals are counted beside it.

| Proportion difference (truth `pa − pb`) | coverage | rendered / refused |
|---|---|---|
| 10 cases w=1 p=0.9 vs 60 w=1 p=0.8 | 0.990 | 205 / 95 `boundary_estimate` |
| 10 w=1 0.5 vs 60 w=1 0.5 | 0.946 | 298 / 2 |
| 20 w=1 0.85 vs 60 w=1 0.8 | 0.939 | 294 / 6 |
| 10 w=3 0.9 vs 60 w=3 0.8 (intra-case correlation 0.5) | 0.952 | 273 / 27 |
| 20 w=3 0.8 vs 80 w=3 0.8 | 0.920 | 300 / 0 |
| 30 w=1 0.8 vs 30 w=1 0.8 | 0.947 | 300 / 0 |
| 40 w=3 0.9 vs 120 w=3 0.9 | 0.953 | 300 / 0 |
| 5 w=3 0.8 vs 60 w=3 0.8 | **0.904** | 271 / 29 |

| AUROC difference (truth `Φ(da/√2) − Φ(db/√2)`) | coverage | rendered / refused |
|---|---|---|
| 10/10 vs 60/60 cases, w=1, da 2.0 db 1.0 | 0.928 | 277 / 23 |
| 15/15 vs 60/60, w=1, 1.5 / 1.0 | 0.946 | 298 / 2 |
| 10/10 vs 60/60, w=3, 1.5 / 1.0 | 0.923 | 300 / 0 |
| 30/30 vs 30/30, w=1, 1.5 / 1.5 | 0.940 | 300 / 0 |
| 20/20 vs 80/80, w=3, 1.5 / 1.0 | 0.933 | 300 / 0 |

Every rendered shape is at or above the bar; the 5-case level sits on it (0.904, se 0.017),
which is the `not_evaluable_shown_for_transparency` tier and is annotated as such.

### Injection at 50 seeds none of the builder, lens 1 or lens 2 used (61000–61049, n = 5,000, B = 200; `probe/injection.py`)

i.i.d. (`delong_wald`, 4 s): B's `diff_vs_complement` excludes 0 in **50/50**, covers −0.06
in 48/50; A and C cover their true +0.0292 in 46/50 and 44/50 and cover 0 in 18/50 and
24/50; B vs the declared reference A excludes 0 in 49/50, covers −0.06 in 47/50. **The same
50 cohorts with every row duplicated under a `case_id`** (`cluster_bootstrap_percentile`,
171 s): B vs complement excludes 0 in **50/50**, covers −0.06 in 47/50; A / C cover their
truth in 46/50 and 42/50; B vs A excludes 0 in 49/50, covers in 48/50. The ≥ 90 % claim
holds on my seeds on both routes.

### DEC-08 grid at another seed and B (seed 424242, R = 200, B = 300, MC se 0.021; one generator shared across cells as `main()` does; `probe`, the committed script's own generators)

| shape | N = 30 | N = 120 | renders under (2, 0.20)? |
|---|---|---|---|
| AUROC share 0.05 (m = 171) | 0.935 | 0.940 | yes |
| AUROC share 0.10 (m = 81) | 0.940 | 0.915 | yes |
| AUROC share 0.20 (m = 36) | 0.945 | **0.895** | no (refused) |
| AUROC share 0.30 (m = 21) | 0.895 | 0.870 | no |
| AUROC u = 2 / 3 / 5 pure cases, m = 0 | 0.665 / 0.790 / 0.905 | 0.575 / 0.755 / 0.905 | **yes** |

Proportion cell (w = 1 / w = 3): p = 0.5 → u = 2: 0.440 / 0.520, u = 5: 0.935 / 0.875,
u = 10: 0.975 / 0.920, u = 20: 0.965 / 0.950, u = 40: 0.980 / 0.950; p = 0.9 → u = 2:
**0.220** / 0.375, u = 5: 0.380 / 0.695, u = 10: 0.585 / 0.940, u = 20: 0.850 / 0.865,
u = 40: 0.955 / 0.940. **Minimum coverage over the 30 rendered shapes: 0.220; 14 of 30
below the bar** — the same count lens 2 found at seed 7777 (0.160; 14 of 30). The
frozen-share half holds at my seed (rendered shapes ≥ 0.915); the refused 0.20 shape puts a
third cell below the bar in what is now ten measurements (0.895 here beside 0.870 and 0.880),
consistent with T7's "sits near the bar, not above it". The `MIN_UNITS_PER_STRATUM = 2`
half does not hold on either family; T7 says so ("not implemented on either route") and
that is the escalated item, not a new finding.

---

## 2. Blockers

None.

---

## 3. Non-blocking (record and carry)

**N1 — the rendered two-sided cluster-bootstrap interval has no oracle test: two mutants that
make it one side's interval alone survive the full suite.** `values = values_a - values_b` →
`values_a - values_b.mean()` (the interval is side a's alone, shifted) and → `values_a.mean()
- values_b` (side b's alone): **`364 passed, 1 skipped, 1 xfailed`** each, planted through
the committed script's copy with `.github` and `scripts` added so the whole suite runs
(`probe/my_mutants.py`). Non-equivalent on a 20-case 0.8 vs 60-case 0.7 proportion pair at
seed 1, B = 200: engine (−0.3004, 0.1500); side-b-collapsed (−0.3114, 0.1386);
side-a-collapsed (−0.1738, 0.0433). This is FA-B1's defect class — an interval that is one
side's alone — for every rendered cell rather than the frozen ones, and the only thing
standing between a regression there and a green build is a lens re-measuring coverage. The
engine is right today (the thirteen-shape table above). Close with a test that recomputes
one clustered difference's percentile bounds from the two sides' recorded draws
(`_RecordingResampler` already exists) or from an independent two-sided bootstrap written in
the test. Repro: plant either replacement in `_bootstrap_difference`, run the suite.

**N2 — no test in the suite runs any bootstrap at a level other than 0.95.** Day-4
`bootstrap_percentile` with `percentile_bounds(usable, DEFAULT_LEVEL)` in place of `level`
survives the full suite (`364 passed`), and so does `_frozen_sides(..., DEFAULT_LEVEL)`.
Under the first, a run at `level = 0.90` would print the 0.95 interval labelled
`ci_level 0.90` in every bootstrap cell. Reachability today: `level` is a keyword of
`subgroup_analysis` / the cell functions only — `cli.py` calls no statistics yet and
`criteria_schema.json` has no interval level — so no customer reaches it; it reaches every
customer the day a level becomes declarable. Repro: `python -c` the two mutants above; or
`run(cols, crit, level=0.90)` and compare a bootstrap cell's bounds to `level=0.95`.

**N3 — reported counts on the clustered difference are unpinned.** `counts = {"n": max(n1,
n2), …}` in `_proportion_difference` (the i.i.d. route's `difference_unpaired` reports
`n = min`) and `usable.std(ddof=0)` for the cell's `resample_sd` both survive the full suite.
Neither moves the estimate or the bounds; both are numbers printed in the pack. Same class as
lens 2's `n_cases = max` survivor, still surviving.

**N4 — `_frozen_sides` ignores its `level` at the function level without a test noticing:**
`percentile_bounds(finite, 0.5)` survives `-m day5` and the full suite; the unit test's arrays
(all-constant, 199-of-200, linspace) do not separate the 25/75 quantiles from the 2.5/97.5
ones. Non-equivalent at the function: a side constant in 80 % of its draws is refused by the
mutant and rendered by the engine. I did not find a cohort that produces such a side through
the public API (a 10/10 level with one cross-class tie at the boundary is at 1.0 in 0.545 of
resamples, q25 0.99 ≠ 1.0), so this is a unit-test gap, not a reachable behaviour today. Add
an 80/20 array to `test_frozen_sides_applies_the_single_cell_percentile_rule_to_each_side`.

**N5 — a test docstring's figures are at a resample count the test does not use.**
`test_the_two_sided_bootstrap_draws_side_a_then_side_b_from_the_cell_generator`: "on these
index vectors that mutant moves the interval from (0.0, 0.4643) to (0.0696, 0.4762)". Those
figures reproduce exactly at seed 1 with **200** resamples; the test runs 50, where the move
is (0.0741, 0.4048) → (0.0741, 0.4946) (seed 2, 50: (0.0, 0.5289) → (0.0741, 0.4827)). The
claim — the mutant moves the interval — is true at both; the sentence should say B = 200.
Not a sentence violation; a number without its condition.

**N6 — T7's frozen-side sentence is narrower than its plain reading.** "a difference is
refused with `boundary_estimate` (estimate carried) when either side is frozen": a side with
exactly one case — frozen in every sense a reader would use — is refused *before any draw*
with `insufficient_clusters` and `frozen_sides []` (level A of one case beside B of 100:
accuracy difference `est 0.2, insufficient_clusters, resampling.a.deficient_class 'all'`).
T7's own definition ("when the side's own resampled statistic has a zero-width percentile
interval") excludes the case, because that side is never resampled, and the code docstring
states the precedence; the typed reason printed is the more informative one. Wording only.

**N7 — carried from lens 2, re-verified still reproducing:** the `delong_wald` difference
bound leaves [−1, 1] unclipped and unflagged (max `ci_hi` **1.082** over 2,000 10/10-vs-10/10
draws at seed 2); i.i.d. Newcombe differences carry no tier (`make_cohort(n=80)` S3: `n 5`,
half-width 0.34, `flags []`, row tier `very_low_precision`); a declared reference on an
all-Unknown attribute does not halt (`reference_level: None`, no H09); the same threshold
declared twice doubles the Holm family (`family_size 4`); overlapping bands
`[[0,50],[40,65],[65,200]]` → the `40-65` row holds 54 rows and the 40–49s sit in `0-50`;
`[[65,0]]` / `[[40,40]]` → 300 in Unknown, no halt; `Unknown`, `nan`, ``, `NA`, `None`,
`unknown` merge into the Unknown row, `-` is a level; NFC and NFD `Zürich` are two levels.
Not re-listed as findings.

**Equivalent through the public API, not a finding:** removing the `degenerate_resamples`
check from the two-sided route survives, but no cohort can reach it — `clustered_by_case`
draws each outcome stratum on its own, so a resample never lacks a class and the AUROC
statistic never returns NaN; a proportion's mean never does.

---

## 4. What I could not break (this is evidence)

- **Lens 2 FA-B1 closed on every construction I tried.** Level at 0/n sensitivity (own
  `boundary_estimate` at 0.0, difference `est −0.8, boundary_estimate, frozen ['a']`);
  constant-score level (own AUROC 0.5, difference `0.0278` refused, `frozen ['a']`; its
  i.i.d. twin `boundary_estimate` via `unpaired_delong`, `variance_a 0.0`); both sides
  separated (`frozen ['a', 'b']`, est 0.0); a separated level made only of *mixed* cases
  (each case one positive and one negative: own 1.0, difference 0.1828 refused,
  `frozen ['a']`); the frozen level against a complement that contains an Unknown row
  (refused, `['a']`); run levels 0.90 and 0.99 (refused, `ci_level` carried); a level frozen
  on specificity (15/15) and PPV (8/8) but not sensitivity (8/12): exactly those two
  differences refused, sensitivity and NPV rendered. The `est` of every refusal is level
  minus other. The fairness block re-reads the refusals: `tpr_gap`/`ppv_gap`/`npv_gap`
  `boundary_estimate` with `frozen ['a']`, `fpr_gap` mirrored to −0.3333 with the reason
  kept, `selection_rate_gap` rendered (A's selection rate 10/20 varies), `auroc_gap`
  refused; 0 schema errors.
- **Near-frozen renders by the documented rule, and only the documented rule.** A 10/10
  level with one negative above every positive (own AUROC 0.9 (0.6, 1.0)) has its
  difference rendered 0.245 (0.060, 0.410), `frozen []`. I looked for a side frozen in more
  than 95 % of resamples that is not frozen in all of them and found none reachable: a
  proportion at k/n resamples to n/n with probability `(k/n)^n ≤ 0.37`, and an AUROC side
  needs a specific unit absent, `≤ 0.35` per unit — the repairer's refused sentence ("a
  side frozen in fewer than 95 % of resamples renders") is conservative in practice.
- **FA-N8 / RG-N2 and FA-N9 closed.** One level and all-Unknown under `declared` and
  `detected`: every entry `insufficient_levels` with `n_levels 1` / `0`; a two-level
  clustered attribute: `clustered_data_analytic_ci_invalid`; the function itself with
  `[(45,5)]`, `[(0,10),(0,12)]`, `[(40,10),(38,12)]` under `declared` →
  `insufficient_levels` / clustered / clustered, `family_size 0`; under `none` →
  `insufficient_levels` / `boundary_estimate` / p 0.629, `family_size 1`; the call without
  `clustering_route` → `TypeError: missing 1 required keyword-only argument`; `"bogus"` →
  `ValueError`.
- **The three falsified sentences are gone and the replacements are true.** "at every seed
  tried" absent from T7 and `bootstrap.py`; the eight cells listed (0.932 / 0.915, 0.900 /
  0.870, 0.925 / 0.915, 0.880 / 0.915) — the two I could re-run reproduce exactly; "two of
  the eight cells are below the bar" counts; "six of eight cells over four runs" counts;
  "not implemented on either route" — the u = 2, m = 0 AUROC shape renders through
  `auroc_ci` (0.978 (0.933, 1.0) `cluster_bootstrap_percentile`, `deficient_class None`) and
  the 10-case p = 0.9 cell through `proportion_ci` (0.8 (0.5, 1.0), `very_low_precision`,
  `imprecise`), each with its tier and no refusal, as T7 says.
- **No guarantee-class sentence was added.** Every `+` line of the diff grepped for
  guarantee / prevent / ensure / never / always / closed / correct: the two hits are "This
  is a measurement on the grid's shapes, not a guarantee" and "a side whose class the
  resampler cannot vary".
- **X1.** No `diff_vs_overall` and no string `overall` in any of the 30-odd constructed
  outputs (one level, all-Unknown, spanning case, single-case complement, two operating
  points, 100k rows, `y_pred`-only, lower-is-positive, every frozen shape above).
- **DEC-10.** Census over every serialised Number in every construction: every per-level
  proportion is `wilson`, `cluster_bootstrap_percentile` or `none` with a typed reason; no
  `wilson` / `newcombe10` / `delong_*` under a declared or detected plan; every Number
  re-validates through `Number(**d)` (a CI or a reason in `NOT_ESTIMABLE_REASONS`, no
  half-open interval, no `method: none` with an interval, no inverted bounds); no verdict
  word in any key or string (the 40-word tokeniser, plus `passed`, `failed`, `unmet`,
  `compliant`, `significant`, `approved` probed by hand); no `*status*` key but
  `analytic_status`; every p-value a float or `None`, never beside a reason.
- **Reference rule.** Unknown row largest (150 of 246) → reference S1 by `largest`;
  declared absent → H09 with `reference_level` in `detail`; declared on rows all excluded by
  the mask → H09 "not a level of the analysed rows".
- **Boundary levels.** 0 positives → sensitivity `zero_denominator`, AUROC
  `insufficient_positives` on the cell and the difference, Brier `single_class` with est,
  tier `very_low_precision`; 0 negatives → specificity `zero_denominator`,
  `insufficient_negatives`, NPV 0/n Wilson (0, 0.434).
- **Clustered refusals.** A case spanning two sites → `cases_span_both_groups` on accuracy
  and AUROC with companion `clustered_data_analytic_ci_invalid`, footnote refused; a
  single-case complement → `insufficient_clusters`, the single-case row `n_units 1`, tier
  `not_evaluable_shown_for_transparency`.
- **Orientation, scale, NaN.** `lower_is_positive` with rule `<=`: per-level AUROC equals
  `roc_auc_score(y, −score)` to 6 dp on three sites, Brier `not_computed_this_run`;
  `y_pred`-only: AUROC and its differences `not_computed_this_run`; 100,000 i.i.d. rows, 5
  sites, 3 attributes: **3.3 s**; NaN scores excluded before banding (85 of 96 rows
  analysed, site rows sum to 85); two operating points → `op1, op2, auroc, brier`, four
  footnote entries, one family.
- **Determinism of the restructured loop.** The five-cohort output diff above: every
  rendered clustered cell that was not frozen is bit-identical between `9da4401` and
  `e4c4f7e` — the generator is consumed in the same order.

## 5. Sentences refused / falsified

Falsified by construction: none of the sentences the diff adds. N5 and N6 are imprecisions
with true claims behind them, recorded above.

Sentences I refused to write in this note: "the two-sided cluster bootstrap is now correct"
(its rendered coverage was measured on thirteen shapes at one seed; N1 shows nothing in the
suite would notice it becoming wrong); "the frozen-side rule is closed" (closed on every
shape I constructed; the near-frozen band is unreachable in practice, not in principle);
"the suite pins the clustered differences" (seven of my fifteen mutants survive the full
suite); "the coverage bar holds" (14 of 30 rendered shapes below it at my seed on the
escalated half); "the mutation sweep shows the tests have teeth" (it shows 34 declared
mutants die; the interval-collapse mutants do not); "no customer can obtain a wrong number
from this module" (none of my constructions produced one; the CLI does not call it yet, so
the customer path is not yet the path I attacked).

## 6. Could not check

- `--full` (743–781 s) not re-run; the recorded R = 400 table was compared against my
  R = 200 / B = 300 run at seed 424242 and the byte-identical `--quick` run.
- pROC `roc.test(paired = FALSE)` — no capture; `[unverified]` stands.
- Newcombe 1998 Table II against the primary PDF — `[unverified]` stands; my formula
  reproduces the fixture to 4 dp.
- Lens 2's exact 0.295 / 0.615 figures (its script was not committed); my rebuild of the
  same shapes at seed 777 gives 0.35 / 0.58 pre-fix and 100/100 refused post-fix.
- The renderer's reading of `frozen_sides` and of `tier` against a difference's flags —
  no renderer yet (the repair note's open question 1).

## Re-run these

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider          # 364 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day5  # 54 passed, 312 deselected
python -m ruff check . && python -m ruff format --check .
python scripts/mutation_sweep.py --marker day5   # 34 planted, 34 killed, 0 survived; 433 s here
python scripts/coverage_bar.py --quick           # share 0.20 row: 0.900 / 0.870; 39 s
```
Attack scripts (`rederive.py`, `attack1.py`, `dump.py`, `two_sided_coverage.py`,
`injection.py`, `frozen_arm.py`, `my_mutants.py`) lived in the session scratchpad
`lens-E5-r3-fresh-attack/probe/` and were not committed; every construction is described
inline so it can be rebuilt from this note. Worktrees removed.
