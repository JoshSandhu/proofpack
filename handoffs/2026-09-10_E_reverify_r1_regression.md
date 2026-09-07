# Re-verify — 2026-09-10 — Lane E (E4) — repair round 1, **regression lens**

Fresh session. Remit: prove that each claimed fix is real, that each regression test
genuinely bites the pre-repair code, that no fix was bought by weakening a gate, and that
the `not_fixed` list is refusal-on-principle rather than quiet reclassification. Repo
treated read-only except this note; nothing committed, nothing pushed, no worktree of
mine left behind.

Commits: pre-repair `5bc69fb`, repair `5b92fc5` (HEAD, tree clean).

---

## Verdict: **FAIL — one blocker.**

All seven defects are genuinely fixed and every regression test genuinely bites. But the
repair **removed a precision-tier flag that the pre-repair code emitted** on clustered
AUROC cells with an imbalanced class — on nine of eleven shapes I probed — while the
note's section 4 states in terms that nothing was weakened. The new tests cannot see it,
because every one of them builds a perfectly balanced cohort.

---

## R1 (blocker) — the repair silently dropped `very_low_precision` from imbalanced clustered AUROC cells

`src/proofpack/stats/bootstrap.py:771`

```python
flags += precision_flags(n_cases, resampler.class_units.get("positive"))
```

against the i.i.d. branch forty lines below, `bootstrap.py:811`, which for the same
metric uses the **minority** class:

```text
*precision_flags(n_pos + n_neg, min(n_pos, n_neg)),
```

The clustered branch feeds only the positive class in as `n_events`, so R2 §3.3's
"events < 5" clause never fires when it is the *negatives* that are scarce, and the
`n_units` clause is satisfied by the total case count. Pre-repair the flag came from
`resampler.smallest_stratum < LOW_PRECISION_UNITS`, which caught both directions at a
threshold of ten. Measured at both commits (`window.py`, seed 5, k = 3 lesions per case,
B = 120):

| positive cases | negative cases | n_cases | pre-repair tier | HEAD tier |
|---|---|---|---|---|
| 40 | 3 | 43 | `very_low_precision` | **none** |
| 40 | 5 | 45 | `very_low_precision` | **none** |
| 40 | 9 | 49 | `very_low_precision` | **none** |
| 60 | 6 | 66 | `very_low_precision` | **none** |
| 100 | 8 | 108 | `very_low_precision` | **none** |
| 7 | 40 | 47 | `very_low_precision` | **none** |
| 9 | 40 | 49 | `very_low_precision` | **none** |
| 3 | 40 | 43 | `very_low_precision` | `very_low_precision` (positives < 5) |
| 40 | 12 | 52 | none | none |

The window is every clustered AUROC cell with `n_cases >= 30` where the minority class
supplies fewer than ten cases and the positive class supplies five or more — a common
subgroup shape (a rare site, a small age band) in exactly the table a regulator reads.

`imprecise` does not always cover it. One cell, `precision_probe3.py`:

```
est=0.9681 ci=(0.9175,1.0000) half_width=0.0413 n_pos=400 n_neg=8 n_cases=204
HEAD        flags = ['delong_refused_clustered']
5bc69fb     flags = ['delong_refused_clustered', 'very_low_precision']
```

An AUROC of 0.97 (0.92, 1.00) resting on **four negative patients**, rendered with no
precision tier at all. Half-width 0.041, so `imprecise` does not fire either.

**Why the new test cannot see it.**
`test_the_precision_tier_follows_r2_section_3_3_on_the_cells_units` is parametrised at
6 / 20 / 60 cases and builds its cohort with `_multi_lesion_cohort`, which is balanced by
construction (`[True] * (n // 2) + [False] * (n - n // 2)`). The positive and negative
class counts are always equal, so the asymmetry between line 771 and line 811 is
invisible to it.

**Why it matters.** The tier is the annotation a reviewer uses to decide whether a
subgroup row is evaluable; R2 §3.3 is explicit that nothing is suppressed and everything
is annotated, so losing the annotation is precisely the failure the tier exists to
prevent. It also contradicts the repair note's own section 4 ("No gate loosened … no
assertion deleted"), which lists three changed assertions and not this — so the audit
trail Josh reads is wrong on this point.

**Suggested fix (two tokens plus a test).** Make line 771 mirror line 811 —
`min(resampler.class_units["positive"], resampler.class_units["negative"])` — and, because
that still leaves the 5–9 minority-case band unflagged where `smallest_stratum < 10` used
to flag it, additionally keep the pre-repair floor: emit `very_low_precision` when the
minority class supplies fewer than `LOW_PRECISION_UNITS` units. Then re-parametrise the
precision test over an imbalanced cohort (40 positive / 3 negative cases), which fails
against `5b92fc5` and passes against the fix. One definition of "events" for both AUROC
branches, or a written reason why they differ.

---

## What I re-ran, and what held

### The suite

```
python -m pytest -q -p no:cacheprovider      -> 230 passed, 1 skipped, 1 xfailed
  -m day1 -> 59 passed, 1 skipped   -m day2 -> 40 passed
  -m day3 -> 29 passed, 1 xfailed   -m day4 -> 102 passed
python -m ruff check .                       -> All checks passed!
python -m ruff format --check src tests      -> 24 files already formatted
python -m proofpack.cli doctor --offline     -> exit 0
```

The pre-day-4 baseline is day1 + day2 + day3 = 59 + 40 + 29 = **128**, exactly the
recorded baseline; 102 − 85 = 17 new tests, all under the module-level `day4` mark. Every
number in the repair claim reproduced.

### Each fix, against `5bc69fb` in a throwaway worktree

Worktree at `5bc69fb` with `PYTHONPATH=<wt>/src`, confirmed to shadow the editable
install (`proofpack.stats.bootstrap.__file__` resolves inside the worktree). New test
files copied in. `tests/test_bootstrap.py` alone: **12 failed, 90 passed**.

| Claimed fix | Regression test | Against `5bc69fb` |
|---|---|---|
| stats B1 / acc B3 — `n_cases` from the run plan | `test_n_cases_is_the_cells_own_case_count_not_the_runs` | **FAILS** `assert 40 == 12` |
| stats B2a / safety B3 — one mixed case vetoes the cell | `test_one_mixed_outcome_case_does_not_veto_a_two_hundred_case_cohort` | **FAILS** `AssertionError: insufficient_clusters` |
| stats B2b / acc B4 / safety N1 — wrong class named | `test_the_refusal_names_the_class_that_is_actually_short` | **FAILS** `'insufficient_positives' == 'insufficient_negatives'` |
| stats B3 — false `ci_pending_bootstrap` + `used` | `test_a_perfectly_separated_cell_promises_no_bootstrap_and_claims_no_analytic_ci` | **FAILS** `'ci_pending_bootstrap' not in ['ci_pending_bootstrap']` |
| safety B1 / acc B1 — X2 defeated by omitting `plan` | `test_cluster_ids_without_a_plan_never_reach_delong_or_wilson` | **FAILS** `assert 'used' != 'used'` |
| safety B4 / acc B2 / stats N4 — misaligned `cluster_ids` | `test_a_clustered_proportion_refuses_cluster_ids_that_do_not_align` | **FAILS** `DID NOT RAISE ValueError` |
| safety B2 — detection rule undefended | `test_any_repeated_case_id_triggers_the_clustered_path[1\|2\|10]` | passes at `5bc69fb` (no code change claimed) — **re-proved by mutation, below** |

All twelve pass at HEAD (day4: 102 passed).

The repair agent's quoted failure line numbers (1061, 1083, 1100, 1119, 1133, 1188) sit
roughly fifteen lines below what the committed file actually reports (1076, 1100, 1117,
1136, 1150, 1205) — taken from a draft of the test file. The assertions and messages match
exactly; cosmetic only.

**The one fix with no code change, independently re-proved.** I applied the safety
verifier's M13 mutation myself in the worktree — `if units < ids.shape[0]:` becomes
`if units * 2 < ids.shape[0]:` in `plan_clustering` — and ran the **pre-repair** suite:
`213 passed, 1 skipped, 1 xfailed`. The mutation survives the entire day-4 suite as built.
With the new test file copied in, all three parametrisations die with
`assert (False, 'none') == (True, 'detected')`. D6 is genuinely pinned now.

### Weakening audit

- **No skips, no xfails, no flaky marks added.** The `mark.skip|xfail` count is 1 in
  `tests/test_discrimination.py` at both commits — the pre-existing F13 pROC xfail.
- **No test function deleted.** The only removed lines under `tests/` are the body of
  `test_nothing_touches_a_global_random_number_generator`, refactored into
  `global_rng_offenders()` which additionally walks `ast.ImportFrom` — strictly stronger,
  and its own new test proves the escape.
- **The pinned `BootstrapPolicy.as_dict()` test gained a `thresholds` block and is still
  an exact-equality pin**, not a subset check.
- **The SE-grid test gained a vacuity assertion.** I re-derived the exclusion count by
  walking the grid myself (`grid_count.py`): 84 cells, **9 excluded**, 75 asserted, all
  nine in the separation = 3.0 column. The corrected comment ("nine of the 84") is right;
  the acceptance note's "10 of the 84" was the wrong figure.
- **Three assertions changed, all tightening**: `ci_pending_bootstrap` `in` becomes
  `not in` in the day-3 discrimination test, the `thresholds` pin, and the grid comment.
  Verified by reading every `-` line of the diff.
- **The `[unverified]` guard change is a tightening**: file-scoped becomes paragraph-scoped.
- **The schema changes are tightenings** (`additionalProperties: false` on `bootstrap`,
  `"minimum": 0` on `seed`), not relaxations.
- **No number moved.** I swept 784 routing cells (AUROC and proportion × declared and
  i.i.d. × 7 × 7 class-case counts × k ∈ {1,3} × mixed ∈ {0,1}) at both commits and
  diffed the records: **0 point estimates changed, 0 existing intervals moved.** 41
  intervals newly form where the old code refused. Every difference falls inside a claimed
  repair category except R1 above, which the sweep's small cohorts could not reach and my
  targeted probe did.
- **F3 pin intact with scipy blocked** by a `meta_path` finder: rendered
  `bootstrap_percentile (0.44, 1.00)`; the clustered cell over the same rows tripled
  returns `cluster_bootstrap_percentile (0.44, 1.00)` with `n_cases = 10` — the F9
  register half still exact, and `n_cases` now the cell's own.
- `Number.__dataclass_params__.frozen` is `True`. A clustered proportion's `as_dict()`
  round-trips through `json.dumps` and both its Numbers validate against
  `output_schema_v1.json` with the new `n_cases` field.
- `Finding` code validation does not break another lane: the only four constructors under
  `src/` use W06, W10, W12 and W13, all registered in `WARN_CODES`.

### The `not_fixed` list

All seven checked. None is a defect quietly reclassified.

- **stats N1** (the F3 sentence must not be quoted bare) — genuinely nothing to fix in
  code; carried as a standing instruction. Correct.
- **stats N3** (R2 §1.3 substitution covers 0.923 against DeLong-logit's 0.978) — a real,
  live under-coverage in shipped behaviour, but choosing which interval is primary is a
  vendor analysis decision CLAUDE.md forbids the engine taking. Correctly escalated with
  the measurement attached. It should not sit open past day 5.
- **stats N7** (row-order sensitivity) — genuine design decision; the fix would move every
  pinned interval including F3.
- **safety N5** (B below 1000 accepted silently) — escalated rather than pre-empting the
  Pyodide question, and the value reaches the manifest. Fair.
- **safety N6** (dropped resamples unflagged) — I confirmed the unreachability argument
  myself: both resamplers stratify, a `mixed` cluster carries rows of both outcomes, so no
  AUROC resample can be single-class, and the proportion statistic is a mean. Dead code
  until day 8. Correctly recorded.
- **safety N8** (X2 at the routing wrapper, not the analytic primitives) — genuine day-5
  obligation, and the note names the AST test that discharges it.
- **CI has never executed** — nothing pushed, and the brief forbids pushing. Carried
  honestly from days 1–3.

---

## Non-blocking

- **N1 — `boundary_estimate` is now returned for a cell whose estimate is 0.40.** The
  class floor was relaxed so a `mixed` case counts towards both outcomes; a cohort of one
  pure-positive case, one pure-negative case and one mixed case therefore passes the floor
  (positives 2, negatives 2) but leaves all three strata singletons, making every resample
  identical, so the zero-width branch fires. Sweep record `auroc/declared npc=2 nnc=1 k=3
  mixed=1`: `est 0.40, method none, not_estimable_reason 'boundary_estimate'` at HEAD,
  where `5bc69fb` said `insufficient_clusters`. That is the same class of untruthful typed
  reason as D3, reintroduced elsewhere by D2's fix. The enum comment in `number.py` was
  widened to cover it, so it is documented rather than silent, and the cell also carries
  `not_evaluable_shown_for_transparency`. The shape is narrow — exactly three cases, one
  of them mixed. It deserves a reason that says what is actually wrong (too few
  independent units) rather than one that says the estimate is at a boundary when it
  is 0.40.
- **N2 — `clustered_flat`'s alignment check is opt-in.** `n_rows` is an optional parameter
  on a function exported in `__all__`, so `clustered_flat(ids)` called directly still
  builds a resampler over a prefix without complaint. `proportion_ci` passes it and the
  regression test pins both paths, but the guard is a caller convention rather than an
  invariant. Same shape as safety N8; fold it into that day-5 AST test.
- **N3 — the i.i.d. AUROC branch with both classes ≥ 10 carries no precision tier at all.**
  `auroc_ci` returns the day-3 `analytic` Number unchanged there, and `Number.n` is `None`
  on every AUROC Number, so `with_precision_flags` adds nothing. Pre-existing from day 3,
  not a repair regression — but once R1 is fixed it will be the only AUROC route with no
  tier, and day 5's subgroup table needs one rule.
- **N4 — the repair left two worktrees registered.** `git worktree list` in this repo
  shows `scratchpad/wt-mut` (5b92fc5) and `scratchpad/wt-pre` (5bc69fb) from the repair
  session, despite the claim "Worktree removed". Harmless, but a future `git worktree` here
  will list them. `git worktree remove --force` on both, then `prune`. I left them alone
  rather than touch repo state.
- **N5 — the "events < 5" half of R2 §3.3 is unimplemented for proportions.**
  `precision_flags(n_cases)` at `bootstrap.py:871` passes no event count, and
  `Number.with_precision_flags` never had one, so a clustered sensitivity of 2/50 cases
  carries no `very_low_precision`. Pre-existing in both directions; not a regression.

---

## Commands to reproduce this note

```
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider            # 230 passed, 1 skipped, 1 xfailed
python -m ruff check . && python -m ruff format --check src tests
python -m proofpack.cli doctor --offline

# the regression tests against the pre-repair commit
git worktree add --detach <scratch>/wt 5bc69fb
cp tests/test_bootstrap.py tests/test_discrimination.py tests/test_invariants.py <scratch>/wt/tests/
cd <scratch>/wt && PYTHONPATH=<scratch>/wt/src python -m pytest -q -p no:cacheprovider \
  tests/test_bootstrap.py                            # 12 failed, 90 passed

# the one fix with no code change, re-proved by mutation
cd <scratch>/wt && git checkout -- .
sed -i "s/if units < ids.shape\[0\]:/if units * 2 < ids.shape[0]:/" src/proofpack/stats/bootstrap.py
PYTHONPATH=<scratch>/wt/src python -m pytest -q -p no:cacheprovider    # 213 passed: mutation survives
cp <repo>/tests/test_bootstrap.py tests/
PYTHONPATH=<scratch>/wt/src python -m pytest -q -p no:cacheprovider \
  tests/test_bootstrap.py -k any_repeated_case_id    # 3 failed
git worktree remove --force <scratch>/wt
```

The R1 probes are in the scratchpad: `window.py` (the tier table), `precision_probe3.py`
(the 0.97 over four negative patients), `sweep.py` with `sweep_pre.txt` / `sweep_head.txt`
(the 784-cell behavioural diff), `grid_count.py` (nine of 84), `noscipy.py` (F3 with scipy
blocked), all under
`C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/0a05ffb0-bd0c-4d5d-b08b-44493ddbbc8f/scratchpad/reverify-E-regression-r1/`.

## Needs from Josh

Nothing new. R1 is a code fix for the repair agent, not a decision for you. The two
standing decisions — day-2 §6 Q1 (F1 and MCC) and day-3 §6 Q3 (the literal R2 §1.3 reading
against DeLong-logit, with the 0.923-versus-0.978 coverage measurement attached) — are
correctly escalated, and both now block what day 5 inherits.
