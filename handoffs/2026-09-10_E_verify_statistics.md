# Verify — 2026-09-10 — Lane E (E4 bootstrap and clustered path) — STATISTICS lens

Adversarial verification. Independent re-derivation only: every statistic below was
re-implemented from the published formula in
`.../scratchpad/verify-E-statistics/indep.py`, which imports **nothing** from
`proofpack` (AUROC as a raw Mann–Whitney double loop; DeLong 1988 variance from the
structural components V10/V01 by direct O(n·m) computation, not the Sun–Xu midrank
shortcut; Wilson from the score-interval algebra; percentile bootstrap; stratified and
cluster resamplers). scikit-learn and scipy used as oracles; plain Monte Carlo where
no closed form exists.

**Verdict: FAIL — 3 blockers.** The resampling mathematics is right; I could not break
it. All three blockers are in what the module *says about* its own numbers, and two of
them fire in the exact multi-lesion use case the module was written for.

---

## 1. What I re-derived, and what agreed

| Claim | My independent value | Engine / handoff | Agreement |
|---|---|---|---|
| F3 AUROC | 0.8000 (brute-force MW, and `sklearn.roc_auc_score`) | 0.80 | exact |
| F3 DeLong SE | 0.15491933384829668 (direct V10/V01, ddof=1) | 0.15491933384829668 | exact |
| F3 stratified bootstrap CI, B=2000, `default_rng(20240101)` | **(0.44, 1.00)** | (0.44, 1.00) | exact |
| F3 bootstrap resample sd | 0.14842279023900326 | 0.14842 | exact |
| τ from the handoff's own formula | 0.0600 | 0.0600 | exact |
| worst endpoint gap over the 13 quoted seeds | 0.0564 | 0.0564 | exact |
| 60/class shortfall cohort | AUC 0.8517, SE 0.03444, gap 0.00722, τ 0.00617 | same | exact |

My resampler was written from the description in R2 §9 ("positives and negatives
resampled separately") without reading the engine's code path, and it lands on the
same pinned interval **and the same resample standard deviation to 17 significant
figures**. Note that R2 §9 itself says "all computed this session", so the pin was
*not* an independent oracle before today; it is now.

**Cluster bootstrap resamples clusters, not rows.** Confirmed by construction and by
agreement with my own pooled/stratified block bootstrap:

```
$ python check2_cluster.py
4 0.0   11 | eng ratio 0.972 | mine ratio 0.902 | pred 1.000
4 0.3   11 | eng ratio 1.347 | mine ratio 1.253 | pred 1.378
4 0.6   11 | eng ratio 1.631 | mine ratio 1.549 | pred 1.673
4 0.9   11 | eng ratio 1.923 | mine ratio 1.823 | pred 1.924
k=3 seed=11 engine ratio 1.854  mine ratio 1.718  sqrt(k)=1.732
k=5 seed=11 engine ratio 2.350  mine ratio 2.216  sqrt(k)=2.236
```

The design-effect check `sqrt(1+(k−1)ρ)` is reproduced by both implementations at
ρ = 0, 0.3, 0.6, 0.9. **The ρ = 0 negative control holds** — the cluster bootstrap does
not simply widen everything.

**Coverage, which is the claim that actually matters.** 1500 replications, 40 cases ×
5 perfectly-correlated rows, p = 0.70, MC se 0.0056:

```
$ python check8_coverage.py
  engine cluster-bootstrap coverage : 0.960  (1500/1500 formed, mean width 0.2751)
  naive Wilson on the 200 ROWS      : 0.611   <-- the interval the engine refuses
  Wilson on the 40 CASES (oracle)   : 0.948
```

The X2 refusal of Wilson under clustering is not a formality: the interval it refuses
covers 61 % of the time. This is the strongest evidence in the day's work and it holds.

**Seeding.** Same seed → bit-identical. Different seed → different, and stable on
re-run. Per-cell streams independent of cell order and of `PYTHONHASHSEED`. No global
RNG. All re-run and all true.

## 2. Is the F3 tolerance honest? — interrogated, and it survives, but read it narrowly

I computed the Monte-Carlo standard error myself rather than trusting the model: 300
*independent* B = 2000 bootstraps of F3.

```
$ python check1_f3.py
  ci_lo  mean 0.45622  sd 0.01989  min 0.4400 max 0.5200
  ci_hi  mean 1.00000  sd 0.00000  min 1.0000 max 1.0000
  unique ci_hi values: [1.0]
```

* The handoff's model predicts an endpoint error of 0.0200 (the AUROC grid term
  `0.5/(n_pos·n_neg)` dominating the smooth term `0.0598·sd` = 0.0089). **Measured
  0.0199.** The model is right, and I derived τ = 3 × 0.0200 = 0.0600 from the stated
  formula independently — it was **not** widened to pass.
* But the criterion it certifies is weaker than the sentence "reproduces the DeLong CI"
  suggests, in two specific ways that Josh should not have to discover later:
  - **The upper endpoint is vacuous.** The bootstrap `ci_hi` is exactly 1.0 in all 60
    seeds I tried; the DeLong Wald upper limit is 1.1036 clamped to 1.0. The 0.0000 gap
    is an identity between a boundary and a clamp, not an agreement.
  - **The lower-endpoint gap is systematic, not noise.** 0.0564 against a measured MC
    sd of 0.0199 — 2.8 standard deviations, and the mean gap is 0.0402 (2.0 sd). A
    3-sigma tolerance admits a 2-sigma bias by construction. Over 413 seeds the gap
    never exceeded τ (max 0.0564, headroom 6 %), so the test is stable — it is the
    *interpretation* that is loose, not the number.
* The substantive claim (§2c of the handoff — the bootstrap sd reproduces the DeLong
  SE across the grid) is real. I re-derived the grid myself: 74 of 84 cells asserted,
  median band usage 20 %, worst cell 96 %. It is a genuine constraint, though see N2.

Conclusion: the F3 acceptance criterion is **met as stated in the handoff §2(b)/(c)
and only as stated there**. Not a blocker. The handoff's own qualification is accurate
and I could not find a way in which it overclaims.

## 3. Mutation testing — 12 deliberate breakages

Run in a detached `git worktree` under the scratchpad with `PYTHONPATH=<wt>/src`,
`-p no:cacheprovider`, `-m day4` (baseline 85 passed). Worktree removed; main tree
clean.

| # | mutation | result |
|---|---|---|
| M1 | `clustered_by_case` draws rows, not cases | **14 failed** |
| M2 | percentile tails 5/95 instead of 2.5/97.5 | **4 failed** |
| M3 | draw m−1 units per stratum | **10 failed** |
| M4 | units drawn without replacement | **55 failed** |
| M5 | `n_cases` = the *cell's* own case count | **0 failed** ← see B1 |
| M6 | drop `analytic_ci_replaced_small_class` | **1 failed** |
| M7 | stratified resampler ignores strata | **16 failed** (incl. the tolerance test on its own) |
| M8 | `MIN_USABLE_FRACTION = 0.0` | **1 failed** |
| M10 | emit the zero-width interval instead of refusing | **1 failed** |
| M11 | `rng_for_cell` ignores the cell key | **2 failed** |
| M12 | `clustered_by_case` pools all cases into one stratum | **10 failed** |

Eleven of twelve caught. The one that is not caught is B1.

---

## BLOCKERS

### B1 — every clustered `Number` reports the **run's** case count, not the cell's

`src/proofpack/stats/bootstrap.py:627` and `:641` both set `n_cases=cplan.n_units`.
`ClusterPlan` is a **run-level** object — and the handoff's own day-5 instruction is
"Build one `BootstrapPolicy` and one `ClusterPlan` for the run and pass them to every
cell". So every subgroup cell will print the whole run's case count.

```
$ python check5.py
run plan: {'clustered': True, 'route': 'declared', 'unit': 'case_id', 'n_rows': 120, 'n_units': 40}
cell rows: 36  TRUE cases in the cell: 12
Number: {"est": 0.657..., "n_pos": 15, "n_neg": 21, "n_cases": 40, ...}
--> n_cases reported = 40
```

15 + 21 = 36 rows over **40 cases** — arithmetically impossible, and it will print that
way in the subgroup table. The interval itself is correct (the resampler is built from
the cell's own `cluster_ids`); only the reported count is wrong.

D1 §4.1 line 201: "For AUROC `n` is replaced by `n_pos`, `n_neg` (and `n_cases` when
clustered)" — a per-Number count of the analysed data, which this is not.

**No test can see it.** Mutation M5 replaced `cplan.n_units` with the cell's own
`len(unique(cluster_ids))` — the statistically correct value — and all 85 day-4 tests
still passed, because every test builds the plan over exactly the rows of the cell.

*Fix:* take `n_cases` from the resampler (`resampler.n_units`) or from
`np.unique(cluster_ids)` inside `auroc_ci`, never from `plan`. Regression test: a
subgroup slice under a run-level plan, asserting `n_cases <= n_pos + n_neg`.

### B2 — one mixed-outcome patient can delete the AUROC interval, and a small stratum mislabels a large cohort

`bootstrap_percentile` refuses the whole interval when **any** stratum has fewer than
two units (`:449`), and `auroc_ci` attaches `very_low_precision` when **any** stratum
has fewer than ten (`:631`). `clustered_by_case` creates a third `mixed` stratum for
cases whose rows carry both outcomes — the multi-lesion patient the module docstring
names as the reason the stratum exists. In that design the strata are small *by
construction*.

200 patients, 2 lesions each, **one** patient made mixed:

```
$ python check12_mixed.py
strata sizes with one mixed patient: {'positive': 99, 'negative': 100, 'mixed': 1}  smallest: 1
with ONE mixed patient: {"est": 0.820, "ci_lo": null, "ci_hi": null, "method": "none",
  "n_pos": 199, "n_neg": 201, "n_cases": 200,
  "flags": ["delong_refused_clustered","very_low_precision"],
  "not_estimable_reason": "insufficient_clusters"}
```

A 400-lesion, 200-patient AUROC loses its interval entirely, with a typed reason that
reads "fewer than two cases in a resampling stratum" while the cohort has 200 cases —
and is simultaneously flagged "very low precision". With **two** mixed patients the
interval returns, still flagged `very_low_precision`.

Rate over simulated multi-lesion cohorts (patient effect + lesion noise, 3 lesions per
patient, 200 cohorts each):

```
$ python check14_flags.py
N=40 patients:  NO INTERVAL: insufficient_clusters  19/200 ;  very_low_precision 200/200
N=100 patients: very_low_precision  67/200
N=300 patients: (clean)
```

So at 100 patients / 300 lesions a third of cohorts carry a precision tier a reviewer
reads as "this cell cannot be relied on", caused by an internal resampling stratum, not
by the cell's sample size. R2 §3.3 tiers are about the evidence, not about the
resampler's bookkeeping.

Coverage in the same design (500 reps, MC se 0.0097, true AUROC 0.76624):

```
$ python check13_mixedcov.py
N=40  engine: coverage 0.901 over 474 formed, 26 REFUSED  | my pooled cluster bootstrap 0.922 over 500
N=100 engine: coverage 0.930 over 500 formed, 0 REFUSED   | my pooled cluster bootstrap 0.940 over 500
```

Pooling the mixed clusters with the rest loses nothing and refuses nothing.

**Same code line, second defect:** the refusal names the wrong class in the i.i.d.
branch. `:460` returns `insufficient_positives` whenever the smaller stratum is short,
regardless of which one it is:

```
$ python check3_edges.py
=== 3. i.i.d. AUROC with n_neg=1, n_pos=25 ===
  number reason: insufficient_positives  n_pos 25 n_neg 1     <-- false
  analytic reason: insufficient_negatives                     <-- correct, on the companion
```

A Number that says "insufficient positives" beside `n_pos: 25` is a false statement in
the pack, and `insufficient_negatives` is already in the enum.

*Fix:* refuse on the number of resampling units **in the cell** (and pool a stratum
that cannot be resampled rather than failing the cell); base `very_low_precision` on
the cell's unit count; pick the reason from which class is actually short. Regression
tests: 200 cases with one mixed case → interval formed and no `very_low_precision`;
n_pos 25 / n_neg 1 → `insufficient_negatives`.

### B3 — a shipped v1 Number promises a bootstrap that has already landed, and the audit trail says the analytic method was "used" when nothing was

`auroc_ci:656` returns `CellCI(analytic, analytic, "used", ...)` for every i.i.d. cell
with both classes ≥ 10, **including** the cells where `auroc_number` produced no
interval (AUROC exactly 0 or 1, or SE 0 — perfect separation, which is routine in small
subgroups).

```
$ python check11_tiers.py
=== stale ci_pending_bootstrap flag survives day 4 ===
  rendered AUROC Number: {"est": 1.0, "ci_lo": null, "ci_hi": null, "method": "none",
    "n_pos": 30, "n_neg": 30, "flags": ["ci_pending_bootstrap"],
    "not_estimable_reason": "boundary_estimate"}
  analytic_status: used (claims the analytic interval IS the rendered one)
```

Two false statements reaching the document:

1. `ci_pending_bootstrap` is defined in `number.py` as "day-4 bootstrap will fill this
   interval". Day 4 has landed. A pack rendered from this JSON tells a regulator the
   number is provisional and a later version will complete it. That is not true and
   will not become true.
2. `analytic_status: "used"` is documented as "the analytic interval is the rendered
   one". There is no interval. `ANALYTIC_STATUS` already contains `unavailable` for
   exactly this case and nothing ever emits it from this branch.

Reachable from a plain call — no clustering, no small class, no misuse — and a
perfectly-separated subgroup is one of the most likely things in a real subgroup table.

*Fix:* in `auroc_ci`, when the analytic Number carries no interval, return
`analytic_status="unavailable"` and drop `ci_pending_bootstrap` (either by not
propagating day-3's flag or by removing it from `FLAGS` now that day 4 exists).
Regression test: 30/30 with perfect separation → `analytic_status == "unavailable"` and
`"ci_pending_bootstrap" not in flags`.

---

## NON-BLOCKING

**N1 — the F3 acceptance sentence should not be quoted bare.** Upper endpoint agreement
is a clamp-meets-boundary identity; lower-endpoint gap is 2.8 measured MC sd inside a
3-sd tolerance. Detail and numbers in §2 above. The handoff §2(b) already says this;
this is a request that the wording survive into T7 and into any sales material.

**N2 — the handoff understates the grid exclusion by 10×.** §2(c) says "One grid cell
is excluded". The `continue` on `auc > NON_DEGENERATE_AUC` skips **10 of the 84** cells
(`check15_grid.py`: "grid cells asserted: 74 ; skipped as degenerate: 10"). Separately,
the tightest asserted cell (n = 30, sep = 3.0, cohort seed 101) uses 96 % of its band —
one cohort seed away from a spurious CI failure.

**N3 — the R2 §1.3 substitution below 10 per class makes coverage worse, measurably.**
1200 reps, true AUROC 0.7602:

```
$ python check9_smallclass.py
n=8/class : percentile bootstrap (RENDERED) coverage 0.923, width 0.455
            DeLong logit (the one it replaces) coverage 0.978, width 0.476
n=5/class : bootstrap 0.959 / logit 0.983
```

0.923 against a nominal 0.95 with MC se 0.0077 is a real under-coverage, in exactly the
regime where the engine renders the bootstrap. This is hard evidence for the handoff's
Needs-from-Josh #2 — DeLong-logit is conservative there and the bootstrap is
anti-conservative, and for a regulatory pack conservative is the safer error.

**N4 — `proportion_ci` accepts misaligned `cluster_ids` silently; `auroc_ci` raises.**

```
$ python check7_align2.py
aligned   : est 0.8000  CI (0.6667, 0.9333)  n=120 k=96
misaligned: est 0.8000  CI (0.6667, 1.0000)  n=120 k=96   <-- built from 60 of the 120 rows
```

`clustered_by_case` checks `ids.shape[0] != pos.shape[0]`; `clustered_flat` does not.
Day 5 is about to wire both. Add the same length check.

**N5 — the precision tier for a clustered proportion is computed from the row count.**
6 cases × 20 rows gives `n=120`, so `with_precision_flags` sees 120 and the n < 10 tier
never applies; the cell is only rescued by the stratum-based flag (which is B2's other
half). Under clustering the effective n is the case count.

**N6 — `boundary_estimate` is returned for any zero-width resample distribution**,
including at est = 0.5 (four cases, each with one success out of two rows). The enum
comment says "estimate on 0 or 1; the delta method is invalid there". Either widen the
comment or add a reason for "degenerate resample distribution".

**N7 — the interval is not a pure function of (data, seed, cell key): row order moves
it.** Same 16 rows, same key, 60 permutations:

```
$ python check16_perm.py
canonical: (0.671875, 1.0)
   (0.640625, 1.0) x1  (0.655859, 1.0) x1  (0.65625, 1.0) x21
   (0.671484, 1.0) x5  (0.671875, 1.0) x24 (0.687109, 1.0) x2  (0.6875, 1.0) x6
AUROC support spacing 1/(8*8) = 0.015625
```

A span of three support steps — Monte-Carlo variation, not bias, and inherent to any
seeded bootstrap. But a customer who re-sorts their CSV gets a different published CI,
and "reproducibility is part of what a customer is buying" (module docstring). One
sentence in T7, or canonicalise the row order before resampling.

**N8 — `criteria.bootstrap` has no `additionalProperties: false`**, so
`bootstrap: {b: 10000}` validates and is silently defaulted. Detectable afterwards
(`b_source: engine_default` in the manifest) and consistent with every other block in
`criteria_schema.json`, so pre-existing rather than a day-4 regression.

**N9 — CI has still never executed.** The `import-without-scipy` job does contain the
F3 reproduction the handoff claims (`.github/workflows/ci.yml:104–143`, verified by
reading), but nothing has been pushed. Carried from days 1–3.

---

## What I tried that did NOT break

* Percentile index convention: `np.quantile` linear vs `lower`/`higher`/`nearest` — the
  F3 pin is identical under all four (endpoints sit on support points). Efron's
  `floor((B+1)a)` order statistic differs by a sub-MC-error fraction of an index.
* Degenerate resamples for AUROC: outcome stratification makes single-class resamples
  essentially unreachable, so `degenerate_resamples` (open question 5) is indeed dead
  code for AUROC and proportions today. Not a defect; the threshold is untested because
  it is unreachable.
* Seeding under `PYTHONHASHSEED=0` vs `12345`, cell ordering, and interleaved cells —
  all stable. The AST scan for global RNG use is genuine (M11 fails it).
* BCa end-to-end: `bootstrap: {interval: bca}` in a real `criteria.yaml` is refused at
  declaration time with `HaltError H08: declaration invalid at bootstrap/interval: enum`.
  Nothing emits `bootstrap_bca`.
* Declared seed/B end-to-end through `io.declare.load` → `policy_from_declarations`:
  `{'B': 5000, 'seed': 4242, 'seed_source': 'declared', 'b_source': 'declared'}`.
* Enum sync between `number.py` and `schema/output_schema_v1.json` — checked
  independently by loading both, all three enums equal as sets.
* Zero network: the 85 day-4 tests pass with `socket.socket` monkey-patched to raise.
* `python -m ruff check .` → All checks passed; `ruff format --check` → 32 files
  already formatted.
* Full suite reproduced: **213 passed, 1 skipped, 1 xfailed in 24.00s**, matching the
  handoff exactly.

## Commands

```
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider                    # 213 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day4            # 85 passed, 130 deselected
python -m ruff check . && python -m ruff format --check .

cd .../scratchpad/verify-E-statistics
python check1_f3.py        # independent F3 pin + measured MC standard error
python check2_cluster.py   # engine vs my own cluster bootstrap, design effects
python check3_edges.py     # row order, boundary cells, wrong typed reason
python check5.py           # B1: n_cases on a subgroup cell
python check7_align2.py    # N4: silent misaligned cluster_ids
python check8_coverage.py  # clustered proportion coverage 0.960 vs Wilson-on-rows 0.611
python check9_smallclass.py# N3: small-class substitution coverage
python check10_claims.py   # re-derivation of every numeric claim in the handoff
python check11_tiers.py    # B3 and N5
python check12_mixed.py    # B2: one mixed patient deletes the interval
python check13_mixedcov.py # B2: coverage and refusal rate in multi-lesion cohorts
python check14_flags.py    # B2: refusal / very_low_precision rates
python check15_grid.py     # N2: 74 of 84 grid cells asserted
python check16_perm.py     # N7: row-order sensitivity
```

Repo left read-only apart from this file; the mutation worktree was removed with
`git worktree remove --force` and `git status --porcelain` on the main tree is clean.
