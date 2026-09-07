# Re-verify — 2026-09-10 — Lane E (E4) — repair **round 2**, regression lens

Fresh session. Remit: prove that each round-2 fix is real, that each new regression test
genuinely bites the pre-repair commit, that no fix was bought by weakening a gate, and
that `not_fixed` is refusal-on-principle rather than quiet reclassification. Repo treated
read-only except this note. Nothing committed, nothing pushed, both of my worktrees
removed.

Commits: pre-repair `5b92fc5` (round 1), repair `e87843d` (HEAD, tree clean, three
commits ahead of `origin/main` at `3bee15c` — day 4 has still never been pushed).

---

## Verdict: **PASS — no blockers.**

All four round-1 blockers (`R1`, `FA-B1`, `FA-B2`, `FA-B3`) are genuinely fixed, and every
regression test genuinely bites: **10 of the new parametrisations fail against `5b92fc5`
before any source change**, and the two that pass there by construction each kill a
mutation that survived round 1. Nothing was weakened. I re-derived the behavioural claim
independently — a 2,248-cell sweep on my own grid at both commits — and it agrees with the
repair note in every direction: **0 point estimates moved, 0 surviving intervals moved, 0
precision tiers lost anywhere.** Four non-blocking items follow, one of which is a gap in
the record rather than in the code.

---

## 1. Each claimed fix, against the pre-repair commit

Worktree at `5b92fc5`, `PYTHONPATH=<wt>/src` confirmed to shadow the editable install
(`proofpack.stats.bootstrap.__file__` resolves inside the worktree), HEAD's
`tests/test_bootstrap.py` copied in, `-p no:cacheprovider`:

```
tests/test_bootstrap.py -> 10 failed, 105 passed
```

| Finding | Regression test | Against `5b92fc5` |
|---|---|---|
| **R1** / **FA-B2** — clustered tier read only the positives | `test_the_clustered_precision_tier_reads_the_scarcer_class` | **7 of 8 FAIL** (40/3, 40/5, 40/9, 60/6, 100/8, 3/40, 9/40) — `AssertionError: ['delong_refused_clustered', 'imprecise'] / assert set() == {'very_low_precision'}` |
| R1 / **FA-N6** — two definitions of "events" in one module | `test_both_auroc_routes_use_one_definition_of_a_scarce_class` | **FAILS** — 9 positives among 409 rows carried no tier |
| **FA-B1** — a class with zero resampling variability rendered an interval | `test_a_class_whose_every_stratum_is_a_singleton_is_refused[True]` and `[False]` | **BOTH FAIL** — `assert None == 'positive'` / `assert None == 'negative'` on `Resampler.deficient_class` |
| **FA-B3** — the load-bearing half of the round-1 D2 fix pinned by no test | `test_a_mixed_outcome_case_counts_towards_both_classes` | passes at `5b92fc5` **by construction** (a missing-test defect) — re-proved by mutation, below |
| FA-N2 (non-blocking, repaired anyway) | `test_one_number_never_carries_two_precision_tiers` | same shape — re-proved by mutation, below |

The 40/12 parametrisation is a genuine **negative control**: it passes at `5b92fc5` as
well as at HEAD, so the test is not a rubber stamp that fires on everything.

All 10 pass at HEAD. Full suite at HEAD, run by me:

```
python -m pytest -q -p no:cacheprovider        -> 243 passed, 1 skipped, 1 xfailed
  PYTHONHASHSEED=12345                         -> 243 passed (no order dependence)
  -m day1 -> 59 passed, 1 skipped   -m day2 -> 40 passed
  -m day3 -> 29 passed, 1 xfailed   -m day4 -> 115 passed
python -m ruff check .                         -> All checks passed!
python -m ruff format --check .                -> 38 files already formatted
python -m proofpack.cli doctor --offline       -> exit 0
```

Pre-day-4 baseline is 59 + 40 + 29 = **128**, unchanged from days 1–3. Day 4 rose 102 →
115 (13 new tests). Every count in the repair claim reproduces exactly.

### The two fixes with no failing test, re-proved by mutation

Mutations applied by me to a detached worktree at `e87843d`, day-4 marker only:

| Mutation | Round 1 | Round 2 | Killed by |
|---|---|---|---|
| **R7** `mixed = 0` in `class_strata` | SURVIVED (102 passed) | **3 failed, 112 passed** | `test_a_mixed_outcome_case_counts_towards_both_classes` + both singleton parametrisations |
| **R16** `with_precision_flags` may add a second tier | SURVIVED (102 passed) | **1 failed, 114 passed** | `test_one_number_never_carries_two_precision_tiers` |
| **R17** clustered tier back to `class_units["positive"]` | (the defect) | **8 failed, 107 passed** | the tier test, all seven imbalanced shapes + the routes test |
| `deficient_class` back to the summed count | (the defect) | **2 failed, 113 passed** | both singleton parametrisations |

FA-B3 and FA-N2 are therefore genuinely pinned, not merely asserted.

### The new code is itself pinned, not just exercised

Four further mutations of lines the repair added, full suite:

| Mutation of the new code | Result |
|---|---|
| drop the `scarcest < LOW_PRECISION_UNITS` floor clause in `auroc_precision_flags` | **6 failed** |
| `scarcest = max(...)` instead of `min(...)` | **8 failed** |
| i.i.d. branch back to `precision_flags(n_pos + n_neg, min(n_pos, n_neg))` | **1 failed** |
| `deficient_class` uses `min` over strata instead of `max` | **64 failed** |

Nothing the repair added is dead or unobserved.

---

## 2. Weakening audit — read every deletion

`git diff 5b92fc5 e87843d` touches five files: `src/proofpack/stats/bootstrap.py`,
`tests/test_bootstrap.py` and three handoff notes. **No schema, no CI file, no
`pyproject.toml`, no config.**

- **`tests/` diff is 224 added, 0 deleted.** No assertion changed, no test function
  removed, no parametrisation narrowed. The existing balanced 6/20/60 precision test is
  byte-identical.
- **No skip, xfail or flaky mark added anywhere in code.** Every `skip`/`xfail` string in
  the diff is prose inside a Markdown note. The suite's one skip
  (`test_doctor_cli.py:57`, write access cannot be revoked for this user) and one xfail
  (F13 pROC, pending the day-12 capture) are both pre-existing.
- **No tolerance, `approx`, `noqa` or `filterwarnings` in the added lines.** The new
  assertions are exact set equality and exact integer equality.
- **The refusal rule is strictly stronger, provably.** `max(strata) <= sum(strata)`, so
  `max < 2` implies nothing that refused before now passes; and for a class the strata are
  exactly (pure, mixed), so `max < 2` holds **iff** every contributing stratum is a
  singleton, which is exactly the condition under which the class cannot vary. The
  criterion is an identity, not a heuristic.
- **`smallest_stratum` was not deleted to hide anything** — it is retained and explicitly
  demoted to a diagnostic in its own docstring.
- **The one Markdown edit inside a lens note is what the repair says it is.** I flipped
  the fence back from a `python` tag to a `text` tag in a worktree copy of
  `2026-09-10_E_reverify_r1_regression.md`: `ruff format --check .` then reports **1 file
  would be reformatted**. ruff 0.16.6 formats Python fences inside Markdown (24 `.py` +
  14 `.md` = the 38 files it reports), so the tag change was genuinely forced by the
  gate, and the quoted evidence line inside that fence is unaltered.

### The behavioural claim, re-derived on my own grid

I did not reuse the repair's sweep. Mine: AUROC **and** proportion × declared and i.i.d.
routes × class-case counts {0,1,2,3,5,8,9,12,40} squared × mixed in {0,1,2} × k in
{1,2,3} — **2,248 cells**, run at both commits and diffed field by field.

| cells | change |
|---|---|
| 2,097 | identical |
| 123 | gain `very_low_precision` |
| 28 | interval → `insufficient_clusters` |
| 2 | `boundary_estimate` → `insufficient_clusters` |
| 0 | **point estimates moved** |
| 0 | **surviving intervals moved** |
| 0 | **precision tiers lost** |
| 0 | new exceptions, and 0 proportion cells changed at all |

Then I checked the two directions that could hide a weakening, by measurement:

- **Every one of the 28 cells that lost its interval really cannot be resampled.** For
  each, I drew 300 resamples and collected the row multiset of the named deficient class:
  **cells refused whose named class does vary = 0.** No over-refusal.
- **Every gained tier is deserved.** All 123 have a scarcer class below
  `LOW_PRECISION_UNITS`; the largest scarcest count among them is **9**. No tier fires
  where both classes reach ten. No Number at HEAD carries two tiers.
- **The 16 lost `imprecise` flags are all inside the 28** — there is no interval left to
  be imprecise about. `not_evaluable_shown_for_transparency` is never lost and never
  downgraded to `very_low_precision`.

The rendered defect the round-1 lens opened on is closed in output, not just in tests:
200 positive cases against 4 negative cases now renders
`est=0.9375 ci=(0.9001,0.9765) n_cases=204 flags=['delong_refused_clustered',
'very_low_precision']` — the tier is back on a narrow interval where `imprecise` cannot
fire.

---

## 3. The `not_fixed` list

**Empty, and honestly so.** Round 1 produced exactly four blockers across two lenses —
`R1` (regression lens) and `FA-B1`, `FA-B2`, `FA-B3` (fresh-attack lens) — and all four
appear in `fixed`, deduplicated to three defects with `R1` and `FA-B2` correctly
identified as one. No blocker was reclassified, downgraded or dropped. Two non-blocking
items (`FA-N6`, `FA-N2`) and one more (regression-lens `N1`, the untruthful
`boundary_estimate`) were repaired as well, each with the fix visible in my sweep.

`handoffs/2026-09-10_E_verify.md` was rewritten as the two-round record and **corrects two
sentences it carried after round 1 that the fresh-attack lens proved false**, quoting them
rather than editing them away. I checked every deletion in that file's diff: the removals
are the superseded round-1 summary, not a downgrade of any finding.

---

## 4. Non-blocking

- **N1 — regression-lens N3 is the only round-1 non-blocking item the round-2 record does
  not carry, and the repair has now made it sharper.** The new helper's docstring says it
  gives "one definition of a scarce class for **both** AUROC routes". There are three, and
  the DeLong route still has none. Measured at HEAD on one evidential shape:

  ```
  iid DeLong 12/12      : delong_logit  []  n=None
  clustered 12/12 cases : cluster_bootstrap_percentile  ['delong_refused_clustered', 'imprecise', 'very_low_precision']
  iid small-class 8/40  : bootstrap_percentile  ['analytic_ci_replaced_small_class', 'imprecise', 'very_low_precision']
  ```

  24 units is below `VERY_LOW_PRECISION_UNITS`, so two routes tier it and one does not.
  Not a weakening — nothing was lost, the sweep proves that — and pre-existing since day
  3. But it is exactly what the round-1 lens predicted would happen once R1 was fixed, and
  day 5's subgroup table needs one rule across all three routes. It belongs in the record
  beside `FA-N1`, `FA-N3`, `FA-N4`, `FA-N5`, `FA-N8` and regression-`N5`, which are all
  carried.
- **N2 — three test counts in the repair claim are one short.** I measure `10 failed, 105
  passed` against `5b92fc5` where the claim says `104`; `3 failed, 112 passed` under the
  R7 mutation where it says `111`; and the same `111` is quoted for a run that now totals
  115. The failures, the messages and the identified tests all match exactly; the passing
  totals were evidently taken before the last test was added. Same cosmetic class as round
  1's off-by-fifteen line numbers. Harmless, but it is the second round running.
- **N3 — `handoffs/2026-09-10_E_verify.md` has two sections numbered `## 5.`**
  ("Nothing was weakened…" and "Commands"). Cosmetic, in the one document Josh reads.
- **N4 — the sibling repos.** `proofpack-site` is clean at `6981308` (lane S) and
  `gps-automation` is at `8430548` (lane A) with a **dirty working tree** — modified
  `src/gps_outreach/{mime_sender,run,templates}.py`, a modified lane-A verify note and an
  untracked lane-A re-verify note. That is lane A's own session in flight, not this
  repair: no E commit exists in either repo and the E diff touches only `proofpack`. Noted
  so it is not mistaken later for E spill.
- **CI has still never executed.** `origin/main` is at `3bee15c`; all three day-4 commits
  are local. Carried from days 1–3 by every lens.

---

## 5. Commands to reproduce this note

```
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider            # 243 passed, 1 skipped, 1 xfailed
python -m ruff check . && python -m ruff format --check .
python -m proofpack.cli doctor --offline

# the regression tests against the pre-repair commit
git worktree add --detach <scratch>/wt-pre 5b92fc5
cp tests/test_bootstrap.py <scratch>/wt-pre/tests/
cd <scratch>/wt-pre && PYTHONPATH=<scratch>/wt-pre/src python -m pytest -q \
  -p no:cacheprovider tests/test_bootstrap.py      # 10 failed, 105 passed

# the two fixes with no failing test, re-proved by mutation at HEAD
git worktree add --detach <scratch>/wt-mut e87843d
# in wt-mut/src/proofpack/stats/bootstrap.py replace the class_strata line
#   mixed = sizes.get("mixed", 0)      ->      mixed = 0
cd <scratch>/wt-mut && PYTHONPATH=<scratch>/wt-mut/src python -m pytest -q \
  -p no:cacheprovider -m day4                      # 3 failed, 112 passed
git worktree remove --force <scratch>/wt-pre <scratch>/wt-mut
```

Scripts in
`C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/0a05ffb0-bd0c-4d5d-b08b-44493ddbbc8f/scratchpad/reverify-E-regression-r2/`:
`sweep.py` with `sweep_pre.jsonl` / `sweep_head.jsonl` (the 2,248-cell behavioural diff),
`diff.py` (the change table), `measure_lost.py` (zero-variability measured on all 28
refusals), `gained.py` (the 123 gained tiers audited), `routes.py` (the three-route
comparison and the R1 probe).

## 6. Needs from Josh

Nothing new from this lens. The four items in the repair's list are correctly shaped: two
are the standing day-2 and day-3 decisions with measurements attached, one is
informational, and the fourth — whether a repair touching a statistical gate should always
be verified as adversarially as a build — is a process question this round answers for
itself. Round 2 existed because round 1 was re-verified, and round 1 had made one number
materially worse (coverage 0.233 against a nominal 0.95) with every check green. I would
accept the rule.
