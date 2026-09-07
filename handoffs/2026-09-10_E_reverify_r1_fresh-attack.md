# Re-verify (repair round 1) — 2026-09-10 — Lane E — **FRESH-ATTACK LENS**

Fresh session, no stake in the repair succeeding. Brief: attack the repaired tree as if I
had never seen it, and check the repair did not open a new hole. Repo treated as
read-only apart from this file; two throwaway `git worktree`s were used and removed
(`git worktree list` shows only the main tree, `git status --porcelain` is clean apart
from this note and the sibling lens's note).

**Verdict: FAIL — 3 blockers, 11 non-blocking.**

The seven original defects are genuinely fixed — I re-ran every one of the three
verifiers' blocker probes against `5b92fc5` and all seven now behave correctly, and the
note's own pre-repair reproduction recipe reproduces exactly (10 failed, 1 passed). The
F3 pin, the DeLong SE and the resample sd all reproduce to 17 significant figures from
code that imports nothing from `proofpack`, so no pinned number moved.

**But the D2 repair over-relaxed the refusal and opened a new hole.** A clustered cell
whose positive class is supplied by one pure case plus one mixed case passes the new
class floor with a count of two, yet contributes *identical rows to every resample*.
The engine now renders an interval there — 15× too narrow on one draw, **coverage 0.233
against a nominal 0.95** over 300 replications — where the pre-repair code correctly
refused. Two further blockers are a precision tier the repair silently dropped on one
side, and the load-bearing half of the D2 fix being pinned by no test.

---

## 1. What I re-ran, and what held

```
$ python -m pytest -q -p no:cacheprovider          230 passed, 1 skipped, 1 xfailed
   PYTHONHASHSEED=0 / 12345                        230 passed both times (no order dependence)
$ -m day1 59 passed 1 skipped | -m day2 40 passed | -m day3 29 passed 1 xfailed
$ -m day4 102 passed, 130 deselected
$ python -m ruff check .                           All checks passed!
$ python -m ruff format --check src tests          24 files already formatted
$ python -m proofpack.cli doctor --offline         exit 0
```
Every count in the repair claim is exact.

**Independent re-derivation** (`scratchpad/reverify-E-fresh-attack-r1/indep_f3b.py`,
importing nothing from `proofpack` — Mann–Whitney AUROC by double loop, DeLong V10/V01
from the structural components, my own stratified percentile bootstrap):

```
independent F3 AUROC      : 0.8                        engine 0.8
independent F3 DeLong SE  : 0.15491933384829668        engine 0.15491933384829668
independent F3 percentile : (0.44, 1.0)                engine (0.44, 1.0)
independent resample sd   : 0.14842279023900326        engine 0.14842279023900326
```
The repair did not move a pinned number.

**All seven original defects re-probed on the repaired tree** (`rerun_originals.py`):

| Defect | Probe | Result |
|---|---|---|
| D1 X2 bypass | `cluster_ids` given, `plan` omitted | `cluster_bootstrap_percentile`, `refused_clustered`, route `detected`, `delong_refused_clustered` — **fixed**; the contradiction (plan asserts independence over repeating ids) raises |
| D2 mixed case | 200 patients, one mixed | interval formed — **fixed** |
| D3 typed reason | 25/1 and 1/25 | `insufficient_negatives` / `insufficient_positives` — **fixed** |
| D4 perfect separation | 30/30 | `analytic_status: unavailable`, no `ci_pending_bootstrap` — **fixed** |
| D5 `n_cases` | 36-row slice under a 40-case run plan | `n_cases: 12`, `<= n_pos + n_neg` — **fixed** |
| D6 detection rule | 1, 2, 10 duplicates of 100 | route `detected`, W13 at all three — **fixed** |
| D7 alignment | 200 ids over 400 rows in `proportion_ci` | raises — **fixed** |

**Safety properties re-attacked and holding.** The `Number` invariant is closed on every
ordinary route (no-CI-no-reason, half-open interval, CI-plus-reason, unknown reason,
`setattr` on the frozen dataclass, `dataclasses.replace` stripping the CI — all raise).
`--offline` makes zero network calls with `socket`/`ssl` replaced by a raising stub
(doctor exit 0, full suite 230 passed under the block). `scipy` blocked by a `meta_path`
finder: `import proofpack` works, `scipy` never enters `sys.modules`. Every repaired
`Number` I could construct validates against `schema/output_schema_v1.json`, and the
three enums are still in sync between code and schema. `CellCI.as_dict()` emits
`usable_resamples` and `resample_sd`, never the 2000 resample values — no row-level
egress. No certification, approval, endorsement or verdict language anywhere in the
day-4 diff. The `[unverified]` guard's file-scope escape is genuinely closed: appending
the safety verifier's unmarked Newcombe renderer to `bootstrap.py` (which carries a
marked Efron & Tibshirani citation) now **fails** `test_no_source_or_template_emits_an_
unverified_value_unmarked`, where at `5bc69fb` it passed.

**Mutation testing — 18 mutations of the repaired paths, 15 caught, 2 survived, 1 mis-typed.**
Detached worktree at `5b92fc5`, `PYTHONPATH=<wt>/src`, `-p no:cacheprovider -m day4`.

| # | Mutation of a repaired line | Result |
|---|---|---|
| R1 | `_resolved` ignores `cluster_ids` when `plan is None` | caught (1 failed) |
| R2 | `_resolved` drops the contradiction raise | caught |
| R3 | `n_cases` back to `cplan.n_units` | caught |
| R4 | `_refusal_reason` always `insufficient_positives` | caught |
| R5 | `clustered_flat` drops the alignment check | caught |
| R6 | refusal back to `min` over internal strata | caught |
| **R7** | **`class_units` stops counting `mixed` towards both** | **SURVIVED — 102 passed** → FA-B3 |
| R8 | `analytic_status` always `"used"` | caught |
| R9 | precision tiers swapped | caught |
| R10 | `precision_flags` returns nothing | caught |
| R11 | clustered proportion loses `n_cases` | caught |
| R12 | detection needs 2× duplication (the old M13 survivor) | caught |
| R13 | `Finding` code validation removed | caught |
| R14 | negative seed accepted again | caught |
| R15 | `[unverified]` guard back to whole-file scope | caught (proved by hand, above) |
| **R16** | **`with_precision_flags` may add a second tier** | **SURVIVED — 102 passed** → FA-N2 |
| R17 | precision events from the *scarcer* class (my proposed fix) | 230 passed → FA-B2 is unpinned |
| R18 | the FA-B1 fix (below) | 230 passed → FA-B1 is cheap to close |

---

## 2. BLOCKERS

### FA-B1 — the new class floor lets a class with **zero resampling variability** render an interval; the pre-repair code refused it

`src/proofpack/stats/bootstrap.py:395` (`Resampler.class_units`) counts a `mixed`
cluster towards **both** outcome classes, and `:414` (`deficient_class`) refuses only
when that *sum* is below 2. So a cell whose strata are `{positive: 1, mixed: 1,
negative: 60}` reports `class_units == {'positive': 2, 'negative': 61}` and is not
refused. But the positive stratum draws 1 unit from 1 and the mixed stratum draws 1 from
1, so **every resample contains exactly the same positive rows**:

```
$ python attack_deterministic_class.py
strata      : {'positive': 1, 'negative': 60, 'mixed': 1}
class_units : {'positive': 2, 'negative': 61}  deficient: None
distinct positive-row multisets over 500 resamples: 1
the positive side of every resample is identical  : True
```

That is precisely the condition the constant's own comment (`:136–142`) says must
refuse: *"Below two independent units supplying an outcome class, that class contributes
the same rows to every resample and the interval would carry no uncertainty about it. A
mathematical floor, not a reporting convention."* Two units split one-and-one across the
pure and the mixed stratum satisfy the count and violate the rationale.

**Pre-repair versus post-repair on the identical cell** (`shape_prepost.py`, 62 patients,
124 lesions, one mixed):

```
5bc69fb  : ci_lo null, ci_hi null, method "none", not_estimable_reason "insufficient_clusters"
5b92fc5  : ci (0.4793, 0.5923), method "cluster_bootstrap_percentile", reason null
```

**Measured, not asserted.** Conditional coverage over 300 replications of that fixed case
composition, scores N(1,1) vs N(0,1) so the true lesion-level AUROC is
Φ(1/√2) = 0.760250 (`cov_det.py`, B = 400, MC se 0.0126):

```
engine : formed 300, refused 0, coverage 0.233, mean width 0.0933
oracle : coverage 0.600, mean width 0.3074     (my own pooled cluster bootstrap)
```

**0.233 against a nominal 0.95.** On a single cohort (`attack_det2.py`, seed 13) the
engine renders width 0.0303 where the independently written pooled cluster bootstrap
gives 0.4667 — **15× too narrow**. The only annotation is `very_low_precision`, which a
reviewer reads as "wide interval, treat with care" beside an interval of width 0.03.

This is reachable in the design the module exists for: a subgroup cell in a multi-lesion
study in which two patients supply the positive lesions and one of them also supplies a
benign one. Under `--offline`, no misuse, no forgotten argument.

It also falsifies the consolidated note's §4: *"a class supplied by fewer than two
independent units still refuses (nothing that refused for a real shortage now passes)"*.
The shortage here is real — zero variability — and it now passes.

**Fix, proved cheap.** Refuse when, for either outcome class, `max(pure_stratum_units,
mixed_units) < MIN_UNITS_PER_STRATUM`, scoped to the `positive`/`negative`/`mixed`
labelling (leave the `all` stratum of `clustered_flat` and the stratified resampler
alone). I applied exactly that in a worktree: **230 passed, 1 skipped, 1 xfailed**, the
degenerate cell returns to `insufficient_clusters`, and the D2 regression test (199 pure
cases + 1 mixed) still forms its interval. Ten lines, no test weakened.

**Regression test it needs:** strata `{positive: 1, mixed: 1, negative: 60}` →
`has_ci is False` and `not_estimable_reason == "insufficient_clusters"`; and the mirror
`{negative: 1, mixed: 1, positive: 60}`.

### FA-B2 — the clustered precision tier reads only the positive class, so a clustered AUROC resting on three negative patients now carries **no tier at all**

`bootstrap.py:771` — `flags += precision_flags(n_cases, resampler.class_units.get("positive"))`.
The events argument is hard-wired to the positive class, so R2 §3.3's `events < 5` tier
can only ever fire on a positive shortage. Two mirror-image cohorts, 2 rows per case
(`attack_events_asym.py`):

```
                                        5b92fc5 (post-repair)                       5bc69fb (pre-repair)
60 positive cases vs  3 negative cases  ['delong_refused_clustered','imprecise']    [...,'very_low_precision','imprecise']
 3 positive cases vs 60 negative cases  [...,'very_low_precision','imprecise']      [...,'very_low_precision','imprecise']
60 positive cases vs  8 negative cases  ['delong_refused_clustered','imprecise']    [...,'very_low_precision','imprecise']
```

Same evidential situation, different annotation, purely because of which class is short.
The repair **removed** a precision tier the pre-repair code carried, on cells that R2
§3.3 says should not be evaluated at all ("AUROC per group requires ≥10 positives **and**
≥10 negatives, else omit with reason"). `imprecise` is not a substitute: it is a Wilson
half-width heuristic and it does not fire when the interval is narrow — in FA-B1's cell
it does not fire.

This contradicts the consolidated note's §4 claim that no gate was loosened.

**Fix, proved cheap and unpinned.** `precision_flags(n_cases, min(resampler.class_units.values()))`
→ **230 passed, 1 skipped, 1 xfailed** (mutation R17). No test pins the current
behaviour, so a regression test is needed as well as the fix: 60 positive cases against
3 negative cases must carry a precision tier.

### FA-B3 — the load-bearing half of the D2 repair is pinned by no test, and deleting it refuses the canonical multi-lesion cohort

Mutation **R7** replaces `mixed = sizes.get("mixed", 0)` with `mixed = 0` at
`bootstrap.py:407`, i.e. stops a mixed cluster counting towards either class — the exact
clause the repair's own docstring calls the reason the fix works. **All 102 day-4 tests
pass** (and all 230 overall). The D2 regression test cannot see it, because its cohort is
199 *pure* cases plus one mixed, so the pure strata carry the count on their own.

The clause is load-bearing on the canonical design. 40 patients, each with one malignant
and one benign lesion — the multi-lesion study the `mixed` stratum was invented for:

```
strata: {'mixed': 40}   class_units: {'positive': 40, 'negative': 40}   deficient: None
with the clause    : cluster_bootstrap_percentile, ci (0.6025, 0.8344)
without the clause : class_units {'positive': 0, 'negative': 0} -> refused, insufficient_clusters
```

An 80-lesion, 40-patient AUROC would silently lose its interval and no test would notice.
This is the same standard the safety verifier applied to D6/B2 — the day's headline rule
pinned by no test — and the repair accepted that as a blocker.

**Regression test it needs:** an all-mixed cohort (every case carries one row of each
outcome) must form an interval, and `class_units` must report the case count for both
classes. It must fail against `mixed = 0`.

---

## 3. Non-blocking

**FA-N1 — a run that honestly declares `clustering.unit: case_id` on a one-row-per-case
table gets a typed reason that is false on the face of the Number.** `plan_clustering`
returns `clustered=True` on the `declared` route regardless of whether `n_units == n_rows`,
so DeLong is refused and the companion Number carries
`clustered_data_analytic_ci_invalid` ("rows are not independent") beside
`n_pos: 30, n_neg: 30, n_cases: 60` — one row per case, demonstrably independent:

```
plan  : {'clustered': True, 'route': 'declared', 'unit': 'case_id', 'n_rows': 60, 'n_units': 60}
render: cluster_bootstrap_percentile (0.7367, 0.9333) ['delong_refused_clustered']
compan: reason "clustered_data_analytic_ci_invalid", n_pos 30, n_neg 30, n_cases 60
same data, undeclared: delong_wald (0.7455, 0.9456)
```

This is the same failure mode as D3 (`insufficient_positives` beside `n_pos: 25`), which
was accepted as a blocker — a typed reason contradicted by the counts printed next to it,
rendered into the pack. It is *pre-existing*, not a repair regression, and none of the
three lenses raised it, which is why I file it here rather than as a blocker. Fix: treat
a declared plan with `n_units == n_rows` as unclustered, or give it a truthful reason.

**FA-N2 — `Number.with_precision_flags`'s new single-tier guard is pinned by no test.**
Mutation R16 (`if n is not None:` in place of the `PRECISION_TIERS` intersection) passes
all 230. The note repairs acc N1 partly by promising "one Number must not carry two
tiers"; nothing enforces it.

**FA-N3 — the global-RNG AST guard still escapes on an aliased import.** The repair
closed `from numpy.random import seed`. Three forms still escape
(`ast_escapes.py`): `import numpy.random as nr; nr.seed(0)`, `import random as rnd;
rnd.seed(0)`, `from numpy import random as r; r.seed(0)`. Hygiene, not correctness — the
code holds — but the module docstring now claims the guard covers the import form, and it
covers one of them.

**FA-N4 — the `clustered_flat` alignment guard is opt-in.** `clustered_flat(ids)` with
`n_rows` omitted still builds a resampler from whatever it is handed, and the function is
in `__all__`. `proportion_ci` passes `n_rows`, so the reachable path is closed; a day-5
caller reaching the resampler directly is not.

**FA-N5 — omitting the plan on a *declared*-clustered run produces a W13 whose text is
false.** `_resolved` routes a missing plan through `plan_clustering("none", ids)`, so the
route is `detected` and `ClusterPlan.finding()` emits "clustering detected ... although
clustering.unit is 'none'" — a statement about the customer's `criteria.yaml` that the
engine has not read. Safe direction (the cluster bootstrap is used either way), but the
warning would be wrong in the pack. Ties to open question 1.

**FA-N6 — the i.i.d. small-class AUROC lost its precision tier on imbalanced cells.**
`bootstrap.py:806` now derives the tier from `precision_flags(n_pos + n_neg, min(n_pos, n_neg))`,
so 9 positives against 400 negatives gets **no** tier (409 units, 9 events), where the
pre-repair branch hard-coded `very_low_precision`. That is literal R2 §3.3 and defensible,
but it is a loosening in a regime R2 separately says to omit, and the note's §4 does not
mention it.

**FA-N7 — one substantive sub-finding was dropped in consolidation.** The statistics note's
N2 had two halves; the consolidated §3 records only the first (the grid-exclusion count).
The second — "the tightest asserted cell uses 96 % of its band, one cohort seed away from
a spurious CI failure" — is not carried anywhere. I recounted the grid independently: **75
asserted, 9 skipped of 84**, so the consolidated note's "nine of the 84" is right and the
statistics note's "10" was wrong; and the worst asserted cell is n = 30, sep = 3.0, cohort
seed 101, at **95.9 % of its band**. That is a flaky-CI risk on a test that has never run
in CI.

**FA-N8 — `cluster_ids` hygiene.** `np.unique` collapses NaN, so two rows with a missing
`case_id` are silently treated as the same patient (`plan_clustering("none", [1.0, nan,
nan, 2.0])` → `n_units 3` over 4 rows, route `detected`); a `None` id raises a raw
`TypeError` from numpy rather than a typed halt. Day-5 wiring must guarantee ingest
rejects a null `case_id` before this point.

**FA-N9 — CI has still never executed** and the wheel job is still unexercised locally (no
`hatchling`, no `build`, no `uv`). Carried from days 1–3 by every lens.

**FA-N10 — the consolidated note points Josh at a path he cannot open.** §1 cites
"`scratchpad/reproduce_verifier_cases.py`"; that is a session temp directory outside the
repo. Either commit it under `tests/` or drop the reference.

**FA-N11 — the effective decision count is seven, not five.** §6 items 1–2 plus §7's five
open questions are seven decisions for one evening. §6.1 and §7.1 are marked as the more
pressing ones, which helps; an explicit "answer these two first" line would help more.

---

## 4. Is the consolidated note an honest record?

**Substantially yes**, with two sentences that need correcting.

- Every one of the eleven blockers raised by the three lenses is carried into
  `2026-09-10_E_verify.md`, correctly deduplicated to seven defects, and each is genuinely
  repaired — I re-ran all seven probes myself.
- Nothing is described as fixed when it was deferred. The six "recorded, not repaired"
  items match what the lens notes said, and each says why.
- The reproduction recipe in §5 works exactly as printed: HEAD's `tests/` against
  `5bc69fb` gives **10 failed, 1 passed**.
- The per-day counts, the suite counts, the ruff figures and `doctor --offline` all
  reproduce exactly.
- No test was skipped, xfailed, deleted or weakened; `git diff 5bc69fb 5b92fc5 -- tests/`
  shows three changed assertions, each tightened or corrected as described.

Two claims in §4 are not true as written, and both are the subject of blockers above:

1. *"a class supplied by fewer than two independent units still refuses (nothing that
   refused for a real shortage now passes)"* — FA-B1.
2. *"No gate loosened"* — FA-B2 (a precision tier removed from clustered cells with a
   scarce negative class) and FA-N6 (the same for imbalanced i.i.d. small-class cells).

One sub-finding was lost in consolidation (FA-N7).

## 5. Needs-from-Josh: complete and actionable?

Yes, with the caveat at FA-N11. The two standing decisions (F1/MCC intervals; the R2 §1.3
substitution) each arrive with a measurement attached and ask for one sentence, which is
the right shape for a ten-hour week. Nothing in this note adds a decision for Josh —
all three blockers are engineering repairs with proved-cheap fixes, not choices about a
customer's analysis. No secrets, accounts or spend are implied by any of them.

## 6. Commands

```
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider            # 230 passed, 1 skipped, 1 xfailed
python -m ruff check . && python -m ruff format --check src tests
python -m proofpack.cli doctor --offline

cd <scratch>/reverify-E-fresh-attack-r1
python indep_f3b.py                 # independent F3 pin, DeLong SE, resample sd
python rerun_originals.py           # all seven original defects re-probed
python attack_deterministic_class.py# FA-B1: the positive side of every resample is identical
python shape_prepost.py             # FA-B1: 5bc69fb refuses, 5b92fc5 renders
python cov_det.py 300               # FA-B1: coverage 0.233 vs oracle 0.600
python attack_det2.py               # FA-B1: width ratio 0.065 against the oracle
python attack_events_asym.py        # FA-B2: the precision tier only reads the positives
python ast_escapes.py               # FA-N3: three aliased-import escapes
python mutate.py ; python mutate2.py# 18 mutations of the repaired lines
```

Worktrees removed; `git worktree list` shows only the main tree and `git status
--porcelain` is clean apart from the two re-verify notes.
