# Re-verify (round 4, fresh-attack lens) — 2026-09-10 — Lane E (E4 bootstrap and clustered path)

Attacking `1be823f` cold, as if the three previous rounds had not happened. Repair round 3
claimed two blockers fixed (FA2-B1, FA2-B2) and nothing deferred.

## Verdict: **PASS — 0 blockers, 6 non-blocking.**

Both round-3 fixes are real, and this is the first round in which I could not construct a
clustered AUROC cell that renders a materially wrong interval. The new rule was
re-derived from its own definition and matched the engine on **13,488** cluster
structures; an independent **65,272-cell** sweep at `e87843d` and at `1be823f` reproduces
all five of the repair's directional claims exactly; **10 of 12** mutations of the new code
are killed by the suite; and the frozen-share bound the constant rests on
(`sd understated by at most 1 - sqrt(1 - share)`) held in every one of the five shapes I
measured it against, which is the load-bearing claim and the one nobody had checked from
outside.

The two mutation survivors are both the same dead half of the rule that the round-4
regression lens found independently (its RG3-N1, my M10) — not a behaviour defect. My own
new attacks found the residual blind spot of a *freeze*-based rule (a class resting on one
**dominant but not frozen** patient), measured it on both routes, and it costs 1.6 and 2.4
coverage points against an oracle that is itself 1–2 points short. That is not a blocker; it
is the sentence day 5 should carry.

---

## 1. What I re-ran, and what held

| Attack | Result |
|---|---|
| Suite at HEAD | `259 passed, 1 skipped, 1 xfailed`; days 1–3 unchanged at 59 + 40 + 29 = **128**; day4 **131** |
| Identical under `PYTHONHASHSEED=987654` | yes, `259 passed` |
| `ruff check .` / `ruff format --check .` | all checks passed / 40 files already formatted |
| `proofpack doctor --offline` | exit 0 |
| **F3 pin, re-derived** — my own stratified resampler, nothing imported from `proofpack.stats.bootstrap` | interval `(0.44, 1.00)` and sd `0.14842279023900326` — identical to seventeen significant figures |
| **`Number` invariant**, 1,188 cells over all five routes: every rendered and companion Number JSON-round-tripped, validated against `schema/output_schema_v1.json`, and required to carry est + method + some `n` + either a CI or a reason inside `NOT_ESTIMABLE_REASONS` | **0 violations** |
| **Offline**, with `socket.socket`, `create_connection`, `getaddrinfo` and `urlopen` replaced by a raising stub: clustered cell computed, `doctor --offline` run | no network call attempted, exit 0 |
| **`[unverified]` guard** — an unmarked Newcombe citation appended next to the new constant in a worktree | `test_no_source_or_template_emits_an_unverified_value_unmarked` fails. The guard reaches the new code |
| **Cross-process determinism of the new manifest block** — three `PYTHONHASHSEED` values | byte-identical JSON |
| **Refusal invariance** — 200 random row permutations plus random `case_id` renames over five cohorts | `deficient_class` and every `frozen_variance_share` unchanged. A customer cannot flip a refusal by re-sorting or renaming |
| Every new test against `e87843d` (HEAD's `tests/` copied into a worktree, module resolution confirmed) | **17 failed, 114 passed** — every new parametrisation bites, on the behaviour, not on a missing attribute |
| Repair scope | the `src` diff touches two files, adds no import, no dependency, no schema change, no CI change; the `tests` diff deletes exactly two lines, both the renamed manifest key; no new `skip`/`xfail` |

**Not an acceptance criterion.** I checked `MAX_FROZEN_VARIANCE_SHARE` against the rule that
ProofPack never sets a margin. It decides *estimability*, not a verdict on a model: it can
only ever turn an interval into a typed refusal, never into a pass or a fail; it is not
customer-declarable; it is published in `thresholds`; and the choice of its value is in
front of Josh at needs-from-Josh 5. That is the right side of the line.

---

## 2. The two round-3 fixes, checked from outside

### R3-D1 — the frozen-variance rule

**The quantity is right.** I re-implemented `sum_frozen w**2 / sum_all w**2` from the
docstring's definition, in my own code, and compared it with `Resampler.frozen_variance_share`
over **13,488** cluster structures spanning pure/mixed/negative strata, lesion counts 1–20 and
case counts 0–60: **0 mismatches**, to 1e-12.

**The bound is right, and it is the claim that matters.** `MAX_FROZEN_VARIANCE_SHARE` is
justified by "the standard deviation is understated by at most `1 - sqrt(1 - share)`". I
measured the actual width shortfall against an independently written **pooled** cluster
bootstrap (cases resampled with replacement, no outcome strata) on the same cohorts:

| shape | share | bound predicts ≤ | measured shortfall |
|---|---|---|---|
| 1 pure-positive case of 3 lesions, 40 mixed | 0.184 | 9.7 % | 5.1 % |
| 1 pure-positive case of 3 lesions, 36 mixed | 0.200 | 10.6 % | 5.3 % |
| 1 pure-positive case of 2 lesions, 10 mixed | 0.286 | 15.5 % | 12.8 % |
| 1 pure-positive case of 20 lesions, 60 mixed | 0.870 | 63.9 % | 26.6 % |
| the FA2-B1 shape (5 lesions, 2 mixed) | 0.926 | 72.8 % | 57.7 % |

The bound holds in every one, and it is not so loose as to be vacuous. **It is an upper
bound, as the module claims.**

**The threshold is calibrated where the module says it is.** Coverage of what the engine
*would* render, with the rule disabled in memory only (`bs.MAX_FROZEN_VARIANCE_SHARE = 9.9`;
the repo was never modified), against a target defined as the estimator's own centre — the
generous definition, so these are ceilings:

| shape | share | tier? | would render | pooled oracle |
|---|---|---|---|---|
| 1×3 lesions + 40 mixed (**admitted**) | 0.184 | none | **0.917** | 0.945 |
| 1×3 lesions + 36 mixed (refused, exactly on the line) | 0.200 | none | 0.915 | 0.935 |
| 1×2 lesions + 10 mixed + 20 neg (refused) | 0.286 | none | 0.905 | 0.940 |
| 1×8 lesions + 40 mixed (refused, **largest cohort my sweep refuses**) | 0.286 | none | 0.897 | 0.932 |
| 1×20 lesions + 60 mixed (refused) | 0.870 | none | **0.728** | 0.932 |
| the FA2-B1 shape (refused) | 0.926 | very_low | **0.507** | 0.848 |

R = 400 replications each, MC se ≈ 0.014. The line sits where the cost of the freeze is
about two coverage points, and the cost rises steeply above it. **The refusals are not
over-refusals**: even the largest cohort newly refused (41 positive-supplying patients) would
render an interval 3.5 points short of the achievable one. And the shape the previous rule
admitted at 61 cases with **no tier at all** covered 0.728 — that is the defect, and it is
closed.

**The behaviour change, swept independently.** My own 65,272-cell grid (structures crossed
over pure-positive / pure-negative / mixed case counts and lesion counts, on both AUROC routes
and both proportion routes), run at `e87843d` and at `1be823f` with identical inputs:

```
changed cells: 2364 of 65272          all of them on the clustered AUROC route
  2214  interval -> insufficient_clusters
   150  boundary_estimate -> insufficient_clusters
EST MOVED=0   INTERVAL MOVED=0   TIER LOST=0   REFUSAL->INTERVAL=0
no proportion cell changed, on either route
```

All five of the repair's directional claims reproduce. Of the 2,214 new refusals the minimum
frozen share is **0.250** — nothing was refused by a rounding edge — the median refused class
has 4 units, and 165 of them previously carried no precision tier at all.

**The two shipped multi-lesion fixtures are untouched, exactly as claimed**: the 200-case
cohort freezes 0.0025189 = 1/397 of the positive variance weight, the 40 all-mixed cohort
freezes 0.0.

### R3-D2 — the manifest and the typed reason

`CellCI.as_dict()["bootstrap"]["resampling"]` now carries the deciding quantities, JSON
round-trips, is byte-stable across processes, and appears on all three resampling routes and
on none of the analytic ones. A refused cell prints, beside the reason:

```
{"kind": "clustered", "units_per_stratum": {"positive": 1, "negative": 20, "mixed": 10},
 "class_strata": {"positive": [1, 10], "negative": [20, 10]},
 "class_units": {"positive": 11, "negative": 30},
 "frozen_variance_share": {"positive": 0.285714, "negative": 0.0},
 "deficient_class": "positive"}
```

A reviewer can now check `0.285714 >= 0.20` against the constant printed in the same block.
That is what FA2-B2 asked for and it is delivered.

---

## 3. Five attacks the earlier lenses did not try

**FA3-N1 — the blind spot of a *freeze*-based rule is the *dominant* unit, and I measured
it.** The rule fires only on a stratum of one. A class can rest on one patient without that
patient being frozen. Twelve mixed patients, one of whom carries 30 malignant lesions and
eleven one each, beside 30 benign patients: **Kish effective positive units 1.85**, frozen
share **0.0**, `deficient_class` `None`, 42 cases and 12 positive class units so **no R2 §3.3
tier fires**, and the cell renders. Coverage **0.920** against the pooled oracle's 0.936
(R = 500). The resampler *can* vary that patient's multiplicity, which is why the damage is
1.6 points and not the 20–40 the frozen shapes cost — so this is not a defect. It is the
reason the natural generalisation of the rule is an effective-sample-size (Kish) floor rather
than a freeze test, and day 5 should decide whether it wants one.

**FA3-N2 — the same probe on the clustered *proportion* route, which the freeze rule cannot
reach at all.** `clustered_flat` builds a single stratum, so a proportion is only ever
refused when the whole cell is one case. One patient with 60 lesions among 39 single-lesion
patients: 40 cases, no tier, an interval in 600/600 replications, coverage **0.928** against
**0.952** for the same cohort with the lesions spread evenly. A 2.4-point residual, same
mechanism, and it is the half of the story `needs-from-Josh 5` does not mention.

**FA3-N3 — the new manifest block publishes a quantity from which one patient's lesion count
is exactly recoverable.** From the block above, `class_strata.positive = [1, 10]` says there
is exactly one pure-positive patient in the cell, and `share = w²/(w² + M)` inverts to
`w = 2.0000` — that patient's lesion count, decoded to four decimal places. Nothing egresses
on day 4 (no code here reads or writes a file) and counts of similar granularity already
appear in every `Number`, so this is not a breach today. But it is a *derived per-individual
attribute*, in a block no suppression rule knows about, in a cell that could be
"female / site B / 70–79". When K-suppression lands it must cover `bootstrap.resampling`,
not only the `Number` fields — rounding the published share to two decimals, or suppressing
the block below the same K, both close it.

**FA3-N4 — `Number` is frozen, but `Number.flags` is a plain list and the closed flag enum is
enforced only in `__post_init__`.** `n.flags.append("not-in-the-enum")` succeeds on a
constructed Number and the value reaches `as_dict()`. `with_precision_flags()` relies on
exactly this mutation, so it is deliberate. No current path emits an out-of-enum flag and
`as_dict()` copies the list rather than aliasing it, so nothing is exposed today — but
"flags are a closed enum" is a construction-time guarantee only, and day 5's renderer is the
first code that will both read flags and add them.

**FA3-N5 — `handoffs/2026-09-10_E.md`, one of the notes Josh reads, still describes the
round-1 refusal rule.** §1 says *"fewer than two units in a stratum → `insufficient_clusters`"*
— replaced in round 2 and replaced again in round 3 — and §2 still reports "85 tests" and
"213 passed" against today's 131 and 259. It carries no pointer to the consolidated verify
note. This is the same defect FA2-B2 was raised as a **blocker** for, one document over; it is
non-blocking only because that document is internal. One line at the top of the build note
("superseded on three points — see `2026-09-10_E_verify.md`") fixes it.

*(One more, not numbered because it is inherent rather than a defect: the X2 auto-switch
detects clustering from repeated `case_id` values, so a customer who assigns a unique
`case_id` per lesion gets DeLong with no warning and no way for the engine to know. That is
the declaration boundary, not a bug; it belongs in the T7 methods sentence day 5 writes.)*

---

## 4. Mutation testing of the repaired paths

Twelve mutations in a detached worktree at `1be823f`, day-4 suite each time. **Ten killed.**

| | mutation | result |
|---|---|---|
| M1 | `>=` becomes `>` on the threshold | killed — `..._is_refused[1-4]`, the exact-boundary parametrisation |
| M2 | `_Stratum.frozen` always `False` | killed |
| M3 | `MAX_FROZEN_VARIANCE_SHARE = 0.99` | killed (manifest pin, then behaviour) |
| M4 | row share instead of variance weight (`c` for `c*c`) | killed |
| M5 | mixed strata excluded from the frozen weight | killed |
| M6 | `resampling` dropped from the manifest | killed |
| M7 | manifest key reverted to `min_units_per_class` | killed |
| M8 | clustered strata built without the class split | killed |
| M9 | `describe()` hides `deficient_class` | killed |
| M12 | the false round-1 enum comment restored | killed |
| **M10** | **the `MIN_UNITS_PER_STRATUM` half deleted outright** | **SURVIVED — 131 passed** |
| **M11** | published share rounded to 1 dp instead of 6 | **SURVIVED** |

M10 is RG3-N1, which the round-4 regression lens reached independently and by a different
route; I agree with its analysis in full. The half is behaviourally inert: the only shapes it
decides alone are classes with no rows, and `auroc_ci` returns `single_class` before the
resampler is built. It is dead code plus a constant published in every customer manifest as a
deciding threshold that decides nothing — the trap FA2-N2 already named for
`smallest_stratum`. M11 is cosmetic: at 1 dp a share of 0.24 prints as 0.2, which is the
threshold itself, so a reviewer could no longer tell which side of the line the cell fell on.
Both are day-5 work; neither is a behaviour defect.

---

## 5. Is the consolidated note honest? Are the needs-from-Josh complete?

**Honest, and I could not find a finding it drops.** I extracted every finding id from all
seven lens notes and checked each against `2026-09-10_E_verify.md`: statistics B1–B3 / N1–N9,
safety B1–B4 / N1–N9, acceptance B1–B4 / N1–N8, round-2 regression N1–N8, round-2 fresh attack
FA-B1–B3 / FA-N1–N11, round-3 regression N1–N4, round-3 fresh attack FA2-B1–B2 / FA2-N1–N6.
All appear, and the round-3 items are attributed to the right lens and the right substance (I
checked `Regression-N1` line by line against the note it came from). Nothing described as
fixed is in fact deferred — I proved both round-3 fixes independently above — and `not_fixed`
is genuinely empty. The note's §6 goes out of its way to record two of its own earlier
sentences as false; that is the behaviour you want from this document.

Two accuracy nits, both harmless and both also found by the parallel lens: the repair claims
`16 failed` against `e87843d` where the deterministic count is **17** (more failures than
claimed, so nothing is hidden — RG3-N4), and the 150 `boundary_estimate →
insufficient_clusters` moves in my sweep (20 in the regression lens's smaller grid) are not in
the headline counts (RG3-N5).

**Needs-from-Josh: complete and actionable, with one measurement missing.** All seven items in
§8 are single-sentence decisions with the measurement attached, which is the right shape for a
ten-hour week; the two new ones (the R2 §3.3 omit-vs-annotate tension, and the value of the
constant) are the only real choices round 3 created and both are genuinely his. The gap is
inside item 5: *"the cell already carries the most severe precision tier"* is true of the shape
it names but **not** of every shape below the threshold — I measured an admitted cell at share
0.184, 41 positive-supplying patients, **no tier**, covering 0.917 against an oracle's 0.945.
He is being asked whether to tighten the constant and the untiered row belongs in front of him.
(Same as RG3-N3, reached independently; two lenses, two grids, one conclusion.)

The push item — `origin/main` at `3bee15c`, four day-4 commits local, CI never executed since
day 1 — is carried in §5 of the consolidated note but not in §8. It is the oldest open item in
the lane and the only thing on the list that is an action rather than a decision.

---

## 6. Non-blocking, in the order I would spend time on them

1. **FA3-N5** — the build handoff describes the round-1 refusal rule and pre-repair test
   counts. One superseded line. (Cheapest, and it is a note Josh reads.)
2. **FA3-N3** — K-suppression must cover `bootstrap.resampling`, not only the `Number`
   fields; the frozen share inverts to one patient's lesion count. Day 5, or whenever egress
   lands.
3. **M10 / RG3-N1** — the `MIN_UNITS_PER_STRATUM` half is inert and unpinned, and its constant
   is published as a deciding threshold. Delete it and `smallest_stratum`, or add the test
   that makes it load-bearing.
4. **FA3-N1 / FA3-N2** — a class resting on one *dominant* (not frozen) patient renders
   untiered at 0.920 (AUROC) and 0.928 (proportion) against oracles of 0.936 and 0.952. The
   generalisation is an effective-units floor. Decide it on day 5 with the tier rule.
5. **FA3-N4** — `Number.flags` is mutable, so the closed flag enum is a construction-time
   guarantee only. Relevant the moment the renderer touches flags.
6. **M11** — the published `frozen_variance_share` precision is pinned by no test.

---

## 7. Commands

Everything below runs from the repo. Nothing in this note depends on a temp directory.

```bash
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider                 # 259 passed, 1 skipped, 1 xfailed
for m in day1 day2 day3 day4; do python -m pytest -q -m $m; done   # 59+1s / 40 / 29+1x / 131
PYTHONHASHSEED=987654 python -m pytest -q -p no:cacheprovider
python -m ruff check . && python -m ruff format --check .
python -m proofpack.cli doctor --offline
```

The frozen share, re-derived and compared — this is the whole of that check, inline:

```python
import numpy as np
from proofpack.stats.bootstrap import clustered_by_case

ids = np.array([0, 0, 0, 0, 0, 1, 1, 2, 2])  # one 5-lesion malignant case, two mixed
pos = np.array([1, 1, 1, 1, 1, 1, 0, 1, 0], dtype=bool)
r = clustered_by_case(pos, ids)
assert r.frozen_variance_share["positive"] == 25 / (25 + 1 + 1)  # sum_frozen w^2 / sum_all w^2
assert r.deficient_class == "positive"
```

The bound and the coverage tables in §2 come from: build the cohort; set
`proofpack.stats.bootstrap.MAX_FROZEN_VARIANCE_SHARE = 9.9` **in memory**; draw 400 replicates
of `u_case + e_row + 1.0*positive` with `u ~ N(0,1)`; count how often `auroc_ci(...)`'s
interval covers the mean of 3,000 point estimates on the same design; the comparator resamples
all cases with replacement in a single stratum. No file in the repo was modified at any point
— `git status` is clean and both worktrees I used were removed.

The 65,272-cell sweep is `itertools.product` over
`(pure_pos, lesions, pure_neg, lesions, mixed, mixed_pos, mixed_neg)` with scores seeded from
`blake2b(structure_key)`, run once with `PYTHONPATH=<worktree at e87843d>/src` **and the
working directory inside that worktree** — with the editable install present, `PYTHONPATH`
alone does not shadow it, which silently produced a zero-diff on my first attempt. Check
`proofpack.stats.bootstrap.__file__` before trusting any cross-commit sweep.
