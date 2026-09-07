# Re-verify (repair round 3) — 2026-09-10 — Lane E — **REGRESSION LENS**

Repo `proofpack`. Commit under review `1be823f` ("fix E: refuse a class the resampler can
barely vary, and say which quantity refused it"); pre-repair `e87843d`; round-1 repair
`5b92fc5`; original build `5bc69fb`.

**Verdict: PASS — 0 blockers, 6 non-blocking.**

Both claimed fixes are real. Every regression test I was asked to check bites against the
pre-repair code, and the eight parametrisations that carry the blocker fail on the
**behavioural** assertion rather than on a missing attribute. Nothing was skipped, xfailed,
softened or deleted: the entire test diff is 284 insertions and **2** deletions, both of
them the renamed manifest key. The refusal predicate is an `or` added to the existing one,
so it can only refuse more — confirmed on my own 4,056-cell sweep, where 0 refusals turned
back into intervals. `not_fixed` is empty and nothing was reclassified.

---

## 1. Does each claimed fix bite against the old code?

Detached worktree at `e87843d`, HEAD's `tests/test_bootstrap.py` copied in, `PYTHONPATH`
shadowing confirmed (`proofpack.stats.bootstrap.__file__` resolves inside the worktree).

```
17 failed, 114 passed in 16.08s
```

| Test | Fails at `e87843d`? | On what |
|---|---|---|
| `test_a_class_dominated_by_a_frozen_stratum_is_refused` × 8 | yes | **the defect** — `assert resampler.deficient_class == "positive"` → `assert None == 'positive'`, `test_bootstrap.py:1634`, all eight |
| `test_the_same_rows_spread_over_units_the_resampler_can_vary_still_render` × 2 | yes | `AttributeError: frozen_variance_share` (a **control**, not the proof) |
| `test_the_frozen_variance_share_bounds_what_the_freeze_costs` × 3 | yes | `AttributeError: frozen_variance_share` (supporting) |
| `test_the_manifest_names_the_quantity_the_refusal_rule_measures` | yes | `min_units_per_class` still published |
| `test_a_refused_cell_emits_the_quantity_that_decided_the_refusal` | yes | `KeyError: 'resampling'` |
| `test_the_insufficient_clusters_reason_documents_the_rule_actually_in_force` | yes | the false sentence "…is not a shortage" |
| `test_the_policy_records_whether_the_seed_was_declared_or_defaulted` (updated pin) | yes | exact-equality on the whole thresholds dict |

I ran the eight blocker parametrisations with `--tb=line` specifically to check they fail on
the behaviour and not on the new API. All eight stop at line 1634, the `deficient_class`
assertion, which sits **before** any reference to `frozen_variance_share`. That ordering is
deliberate and it is the right call — it is what makes the test a regression test rather
than an API pin.

All 14 selected new/updated tests pass at HEAD. FA2-B1's own repro closes:

```
                    e87843d                              1be823f
deficient_class     None                                 positive
frozen share        (attribute does not exist)           {'positive': 0.9259, 'negative': 0.0}
rendered            0.7347 (0.6190, 0.8435) imprecise    0.7347 (None, None) insufficient_clusters
```

## 2. Was anything weakened to get green?

No.

- **Test diff**: `284 insertions(+), 2 deletions(-)`. The two deletions are
  `"min_units_per_class": 2,` and one comment line, both inside the exhaustive thresholds
  pin, replaced by `min_units_per_class_stratum` + `max_frozen_variance_share` in an
  assertion that is still exact equality on the whole dictionary. No `skip`, no `xfail`, no
  `flaky`, no widened tolerance, no assertion removed. `pytest.approx` appears twice, both
  on float equality against a closed form.
- **Source diff**: the only change to the decision is
  `and max(...) < MIN` → `and (max(...) < MIN or frozen.get(...) >= MAX_FROZEN_VARIANCE_SHARE)`.
  Monotone: the refusal set can only grow. `MIN_UNITS_PER_STRATUM` unchanged at 2, all
  precision constants unchanged, `Number` untouched and still frozen (the new `resampling`
  field is on `CellCI`).
- **Mutation testing — twelve mutations of my own, eleven killed.** In a detached worktree
  at `1be823f`, whole suite each time:

```
M1  disable the frozen-share clause                          8 failed
M2  _Stratum.frozen -> False (nothing is ever frozen)       12 failed
M3  strict ">" instead of ">="                               1 failed   <- the (1,4) boundary case
M4  weight = sum(counts) (row share, not w**2)               8 failed
M5  restore "min_units_per_class" in the manifest            2 failed
M6  "resampling": None in CellCI.as_dict()                   1 failed
M7  mixed strata excluded from the frozen weight             1 failed
M8  revert to the round-2 max-units floor alone              8 failed
M11 MAX_FROZEN_VARIANCE_SHARE = 0.30                         3 failed
M12 MAX_FROZEN_VARIANCE_SHARE = 0.21                         2 failed
M13 MAX_FROZEN_VARIANCE_SHARE = 0.05                         1 failed
M10 drop the max-units half entirely                         0 failed   <- RG3-N1
```

The constant is pinned exactly, in both directions, to one hundredth. M3 confirms the
repair's own account: `>` survives without the `(1, 4)` parametrisation, which sits on the
threshold at a share of exactly 1/5.

## 3. Suite, baseline, hygiene — all re-run by me

```
python -m pytest -q -p no:cacheprovider                    259 passed, 1 skipped, 1 xfailed
PYTHONHASHSEED=987654 (same)                               259 passed, 1 skipped, 1 xfailed
-m day1 / day2 / day3 / day4        59+1s / 40 / 29+1x / 131      (days 1-3 = 128, unchanged)
python -m ruff check .                                     All checks passed!
python -m ruff format --check src tests                    24 files already formatted
python -m proofpack.cli doctor --offline                   exit 0
```

Day 4 goes 115 → 131, which is the 16 new parametrisations. Sibling repos are at their own
HEADs and clean (`gps-automation` 5bf83c5, `proofpack-site` 1870c2f); `proofpack` main tree
clean; `origin/main` still 3bee15c with four local commits; I created three worktrees and
removed all three; I committed nothing and pushed nothing.

## 4. Did the behaviour change anywhere it should not have?

My own sweep, on my own grid (4,056 cells: 3,384 AUROC + 672 proportion over 1,128 cluster
structures crossing pure-positive / pure-negative / mixed case counts with 1, 2 and 5
lesions per case), run at `e87843d` and at `1be823f` and diffed field by field:

```
identical                                   3672
interval -> refused                           364
boundary_estimate -> insufficient_clusters     20
point estimates moved                           0
surviving intervals moved                       0
precision tiers lost                            0
refusals turned back into intervals             0
proportion cells changed                        0
```

Four of the repair's five headline counts reproduce exactly on an independent grid. The
fifth (the reason-code move, RG3-N5) is not in its list.

**Over-refusal audit — all 384, not a sample.** Every newly refused cell satisfies a stated
half of the rule (0 exceptions; frozen share of the named class min 0.250, median 0.333,
max 0.926). For 80 of them drawn at random I then drew 300 resamples and intersected the
named class's rows: in all 80 the named class freezes rows in every draw. **0
over-refusals.**

**Round 2's regression tests are not vacuous under round 3.** HEAD's test file at `5b92fc5`
gives `27 failed, 104 passed`, including all of
`test_a_class_whose_every_stratum_is_a_singleton_is_refused`,
`test_the_clustered_precision_tier_reads_the_scarcer_class` (7) and
`test_both_auroc_routes_use_one_definition_of_a_scarce_class`.

**Degenerate shapes.** `describe()` raises on none of: all-positive stratified, all-negative
clustered, a single row, `clustered_flat` with one case, `clustered_flat` with six. The
`bootstrap.resampling` block json-round-trips on the AUROC and the proportion routes and
carries unit counts and six-dp shares only — no row indices, nothing row-level, so the
aggregates-only rule holds.

**One independent arithmetic check of a load-bearing claim.** The repair says the round-1
D2 fixture freezes `1/397` of the positive variance weight. `_multi_lesion_cohort(200, 2,
mixed=1)` gives 99 pure-positive cases of 2 malignant lesions (weight 2² each = 396) and one
mixed case supplying 1 malignant lesion in a stratum of one unit (weight 1, frozen):
1/397 exactly. The other fixture (40 all-mixed cases, one stratum of 40 units) freezes
nothing. Both claims are true.

## 5. `not_fixed` and needs-from-Josh

`not_fixed` is empty and I found nothing reclassified. The one item that could have been a
defect wearing a decision's clothes is needs-from-Josh 5 — the calibration of
`MAX_FROZEN_VARIANCE_SHARE`. I measured the just-below-threshold regime myself rather than
take it (my own rank-based Mann–Whitney, my own pooled cluster bootstrap oracle, 400
replications at B = 600, coverage against the design's analytic population AUROC
`theta = (m*Phi(1/sqrt(0.8)) + (pairs-m)*Phi(1/sqrt(2)))/pairs`):

```
shape (frozen lesions L, mixed m, 40 neg)  share   engine cov  width | oracle cov  width  tier
L= 1  m= 5                                 0.1667      0.843  0.3065 |    0.900  0.3834  very_low
L= 1  m= 6                                 0.1429      0.895  0.3054 |    0.915  0.3587  very_low
L= 2  m=20                                 0.1667      0.917  0.1898 |    0.930  0.2066  NONE
L= 3  m=45                                 0.1667      0.930  0.1330 |    0.935  0.1408  NONE
L= 4  m=80                                 0.1667      0.930  0.1016 |    0.943  0.1072  NONE
```

The residual below the threshold is real but small — at most 1.3 points below an oracle that
is itself short of nominal — and consistent with the ≤ 8.7 % standard-deviation
understatement the stated bound allows at a share of 1/6. That is a calibration decision, not
the blocker in disguise: FA2-B1's regime was 0.34–0.62 with intervals 2.1× too narrow, and
those shapes are now all refused. **It is a genuine decision for Josh.** See RG3-N3 for the
one thing the note does not tell him.

---

## 6. Non-blocking

**RG3-N1 — the retained `MIN_UNITS_PER_STRATUM` half is behaviourally inert and pinned by no
test.** Deleting the `max(strata[label]) < MIN_UNITS_PER_STRATUM` clause outright leaves the
suite at `259 passed`. I looked for a reachable shape where it decides alone. It fires only
when a class has `pure <= 1` and `mixed <= 1`; every such shape except `(0, 0)` has all its
supplying strata frozen, so the frozen-share half catches it at a share of 1. `(0, 0)` is a
class with no rows, and `auroc_ci` catches that earlier — at HEAD *and* with the clause
removed, an all-negative or all-positive cell returns `not_estimable_reason: single_class`
and an unchanged Number. So the repair note's justification for keeping it — *"it is exact
where a class has no rows"* — does not hold up: that path is unreachable. This is **not** a
behaviour defect (the surviving rule subsumes it everywhere reachable and the published
constant never contradicts a refusal), but it is dead code plus a threshold published in
every customer manifest that decides nothing, which is the trap FA2-N2 named for
`smallest_stratum` — still dead at HEAD too, still referenced by nothing. Day 5: delete
both, or add the test that makes the half load-bearing.

**RG3-N2 — `test_the_frozen_variance_share_bounds_what_the_freeze_costs` is nowhere near
binding.** Measured on the three parametrisations (engine/pooled sd ratio against the
asserted floor `sqrt(1-share) - 0.05`):

```
(20,10)  share 0.9756  bound 0.1562  asserts >= 0.1062  measured 0.4696
(20,60)  share 0.8696  bound 0.3612  asserts >= 0.3112  measured 0.7331
( 6,10)  share 0.7826  bound 0.4663  asserts >= 0.4163  measured 0.7224
```

It confirms the direction (the bound is never violated; the freeze costs something), which is
what it claims to do. It cannot detect a wrong `MAX_FROZEN_VARIANCE_SHARE` — the constant does
not appear in it — and the 0.05 slack plus the 0.95 ceiling leave a very wide corridor. The
constant is pinned exactly elsewhere (M11–M13 above), so nothing is exposed; the test is
weaker than the note implies.

**RG3-N3 — needs-from-Josh 5 is scoped to the tiered shapes and does not say that untiered
shapes also sit below the threshold.** *"the cell already carries the most severe precision
tier"* is true of the shape it names (one frozen patient among five or six positive-supplying
units — 400/400 replications tiered in my run, and my 0.843/0.900 matches its 0.82/0.89).
But `(2,20)`, `(3,45)` and `(4,80)` sit at the *same* 0.1667 share with **no tier at all**,
which is the shape FA2-B1 called "the worst of it". Their residual is 1.3 points or less
below the oracle, so it does not change the answer — but Josh is being asked to decide
whether to tighten the constant and should have the untiered row in front of him. The table
in §5 above is the missing paragraph.

**RG3-N4 — the repair's failure count is one short.** It reports `16 failed, 114 passed`
against `e87843d`; I get `17 failed, 114 passed`, deterministically. The extra is the updated
`test_the_policy_records_whether_the_seed_was_declared_or_defaulted` pin, which the note
counts under FA2-B2's "all four bite" but not in the headline. More failures than claimed, so
nothing is hidden — but the two numbers in the same note should agree.

**RG3-N5 — 20 cells move `boundary_estimate` → `insufficient_clusters`,** and that move is not
in the repair's five headline counts (round 2 had 12 of the same shape, and its note did
record them). Both are refusals with a typed reason and the new `resampling` block carries the
deciding quantity, so no information is lost; it is a reason-code change that a reader of the
five counts would not expect.

**RG3-N6 — CI has still never executed.** `origin/main` is at `3bee15c`; `5bc69fb`, `5b92fc5`,
`e87843d` and `1be823f` are all local. The wheel job remains unexercised locally (no
hatchling, no build, no uv on this machine). Carried by every lens since day 1; recorded again
so the count of days stays visible.

---

## 7. Commands

```
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider                    # 259 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day4            # 131 passed
python -m ruff check . && python -m ruff format --check src tests
python -m proofpack.cli doctor --offline                   # exit 0

# the regression check itself
git worktree add --detach <scratch>/wt-pre e87843d
cp tests/test_bootstrap.py <scratch>/wt-pre/tests/test_bootstrap.py
cd <scratch>/wt-pre && PYTHONPATH=<scratch>/wt-pre/src python -m pytest -q -p no:cacheprovider \
    tests/test_bootstrap.py                                # 17 failed, 114 passed
PYTHONPATH=<scratch>/wt-pre/src python -m pytest -q -p no:cacheprovider tests/test_bootstrap.py \
    -k frozen_stratum_is_refused --tb=line                 # all 8 stop at line 1634
```

Scratch work — the sweep and its diff, the over-refusal audit, the coverage simulation with
its own oracle, the boundary probe, the degenerate-shape probe, the FA2-B1 repro and the
mutation runs — is in
`C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/0a05ffb0-bd0c-4d5d-b08b-44493ddbbc8f/scratchpad/reverify-E-regression-r3/`
(`sweep.py`, `cov.py`, `boundary.py`, `edge.py`, `repro_fa2b1.py`, `zero_class.py`,
`head.json`, `pre.json`). Every one imports only `numpy` and `proofpack`, so they can be
rewritten from the tables above if the temp directory is gone. All three worktrees I created
are removed; the main tree is clean; I committed nothing and pushed nothing.
