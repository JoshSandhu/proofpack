# Verify (build day 5, repair round 2) — 2026-09-15 — Lane E — **REGRESSION-AND-RECORD LENS 3**

Repo `proofpack`. Commit under review `e4c4f7e` ("fix E: refuse a clustered difference whose one
side is frozen, and the three sentences lens 2 falsified (day 5, repair round 2)"); pre-fix
`9da4401`. Repairer's note: scratchpad `notes/E5_repair2.md`. Everything below was executed in
detached worktrees at `e4c4f7e` and `9da4401` with `PYTHONPATH=<worktree>/src` forced and
proved (`proofpack.__file__` printed from inside each worktree before any number was trusted;
unforced, the editable `.pth` on this machine imports the main tree — printed and confirmed).

**Verdict: PASS — 0 blockers, 5 non-blocking.**

Every figure in the repairer's note reproduces, in both shells: the suite (364 / 1 / 1),
`-m day5` (54), the day markers (59+1 / 40 / 29+1 / 182 — the repair-r7 figures), lint, format,
doctor, the committed sweep (34 / 34 / 0), the `--quick` coverage table (byte-identical between
Git Bash and PowerShell, elapsed line excluded; share-0.20 row 0.900 / 0.870), the seed-20260916
shared-generator table (`[[0.94, 0.955], [0.88, 0.915], [0.92, 0.9]]`) and the fresh-generator
0.925 / 0.915. The five tests the note says fail at `9da4401` fail there on the E line it
quotes; the two that pass there are each proved by the mutant the note describes, which I
planted myself. My rebuild of lens 2's 18 mutants gives 18 / 8 / 10 with exactly the ten
survivors the note names. Lens 2's blocker FA-B1 is closed by execution on the lens's repro,
on my own 200-sample conditioned shapes (200 / 200 refused on both), and on constant-score,
reversed-separation and both-sides-frozen levels. Lens 1's B1 / B2 and RG-B1 stay closed.
Nothing was skipped, xfailed, deleted or un-marked; the schema is untouched in this diff.

---

## Blockers

None.

---

## Non-blocking

### N1 — "20 cells of `clustered_pair()`, 0 differ" is true of the non-frozen cells and silent on the four that did change

Every leaf of the `clustered_pair(span=False)` document compared between `9da4401` and
`e4c4f7e`: 8,809 vs 8,810 leaves; 101 `cluster_bootstrap_percentile` difference cells
byte-identical; **four** difference cells changed — `age 80-200` (34 units) sensitivity
(own cell 24/24, `boundary_estimate`) and npv (own 32/32, `boundary_estimate`), against the
reference and against the complement — from a rendered interval (e.g. sensitivity vs
reference 0.2174 (0.0870, 0.3913)) to `boundary_estimate`, `frozen_sides ['a']`. That is the
repair doing what it says on a cohort the note did not name. Two things the note's "flags
kept" glosses: the `imprecise` tier flag that rode on the pre-fix rendered interval is gone
(there is no interval to measure a half-width on; the own cell never carried it either), and
the test asserts only the clustered flag. Not a defect; the record is incomplete.

Repro: `PYTHONPATH=<wt>/src python probe/dump_clustered_pair.py out.json` at each sha, diff the
leaves.

### N2 — The renamed order test's docstring quotes an interval pair measured at B = 200 while the test draws 50

`test_the_two_sided_bootstrap_draws_side_a_then_side_b_from_the_cell_generator`: "on these index
vectors that mutant moves the interval from (0.0, 0.4643) to (0.0696, 0.4762)". The note says
the lens's `order.py` figures "were not re-run". I re-ran them: at **B = 200, seed 1** the
engine's loop gives exactly (0.0, 0.4643) a-then-b and (0.0696, 0.4762) b-then-a. The test's
own `_record_two_sided` draws **n = 50** at seed 1, where the pair is (0.0741, 0.4048) →
(0.0741, 0.4946) (seed 2: (0.0, 0.5289) a-then-b). The figure is real and now measured; the
docstring omits the B it was measured at. Shipped text quoting a number the builder did not
measure — add "at B = 200".

### N3 — `test_frozen_sides_applies_the_single_cell_percentile_rule_to_each_side` cannot fail on an assertion pre-fix

At `9da4401` it aborts on `AttributeError: module 'proofpack.stats.subgroups' has no attribute
'_frozen_sides'` — exactly what the note quotes, and unavoidable for a unit test of a function
the repair introduces. It pins the rule only on the repaired tree (a constant side, a
199-of-200 constant side, a NaN among constants, an all-NaN side not named). The behavioural
pin pre-fix is `test_the_two_sided_cluster_bootstrap_refuses_a_difference_whose_one_side_is_frozen`,
which fails at `9da4401` on `assert None == 'boundary_estimate'` with the 0.2256 (0.1599,
0.3054) Number. Recorded; no action.

### N4 — `_record_two_sided` (new test helper) has no docstring

Every other new function and helper in the diff carries one naming what it builds or inspects.

### N5 — Timing and one favourable spelling difference

Sweep 432 s here (note 405 s; both under concurrent load — my lens-mutant rerun ran alongside).
`--quick` 39 s (Git Bash) / 40 s (PowerShell). My spelling of lens 2's "Unknown row enters the
homogeneity test" mutant (`evaluable = list(attr.levels)`) is **killed** on `e4c4f7e` by
`test_fewer_than_two_evaluable_levels_is_insufficient_levels_on_every_route` (all-Unknown now
asserts `n_levels 0`); the note lists it as still unobserved. The lens's exact spelling was not
available to me. My other 17 spellings match the note's outcomes one for one.

---

## What I could not break (evidence)

**Suite and commands, both shells, worktree at `e4c4f7e`:**

```
python -m pytest -q -p no:cacheprovider           364 passed, 1 skipped, 1 xfailed   (43.75 s bash / 42.59 s ps)
python -m pytest -q -p no:cacheprovider -m day5   54 passed, 312 deselected           (17.83 s / 18.45 s)
-m day1 / day2 / day3 / day4                      59+1 skipped / 40 / 29+1 xfailed / 182   (both shells; = repair-r7)
python -m ruff check .                            All checks passed!                  (both)
python -m ruff format --check .                   52 files already formatted          (both)
python -m proofpack.cli doctor --offline          All essential checks passed.        (both)
python scripts/mutation_sweep.py --marker day5    34 planted, 34 killed, 0 survived; 432 s   (note: 405 s)
python scripts/coverage_bar.py --quick            39 s bash / 40 s ps; 81 lines byte-identical (elapsed excluded)
                                                  0.05 → 0.960 / 0.900; 0.10 → 0.860 / 0.930; 0.20 → 0.900 / 0.870;
                                                  0.30 → 0.850 / 0.880; loosest feasible pair: None   (= note, = lens 2)
seed 20260916, one shared generator, R=200 B=500  [[0.94, 0.955], [0.88, 0.915], [0.92, 0.9]]   (54 s; = note)
seed 20260916, fresh generator, share 0.20        [0.925, 0.915]                      (= note)
repair-r7's 27 bootstrap tests (the note's -k)    27 passed, 155 deselected           (both)
round-1's seven tests (the note's -k)             7 passed, 47 deselected             (both)
this round's seven tests (the note's -k)          7 passed, 47 deselected             (both)
```

**Fails pre-fix** (`9da4401` worktree, `PYTHONPATH` proved, new `tests/test_subgroups.py` copied
in, the seven tests): `5 failed, 2 passed, 47 deselected in 1.65s`. First `E` lines, verbatim,
each the line the note's table quotes:

- `..._refuses_a_difference_whose_one_side_is_frozen` → `E                   AssertionError: ('a', 'diff_vs_reference', {'est': 0.2255555555555555, 'ci_lo': 0.1598541666666667, 'ci_hi': 0.30539583333333337, 'ci_level': 0.95, ...})` / `assert None == 'boundary_estimate'`
- `test_frozen_sides_applies_the_single_cell_percentile_rule_to_each_side` → `E       AttributeError: module 'proofpack.stats.subgroups' has no attribute '_frozen_sides'` (N3)
- `test_fewer_than_two_evaluable_levels_is_insufficient_levels_on_every_route` → `E                   AssertionError: ('declared', 0, {'operating_point': 'op1', 'metric': 'sensitivity', 'test': None, 'statistic': None, ...})` / `assert 'clustered_da...ic_ci_invalid' == 'insufficient_levels'`
- `test_the_heterogeneity_footnote_has_no_default_clustering_route` → `E       Failed: DID NOT RAISE TypeError`
- `test_the_sentences_lens_2_falsified_are_gone_from_the_shipped_text` → `E           AssertionError: assert 'at every seed tried' not in '# ProofPack...this file.\n'`

**Mutant proofs for the two tests that pass at `9da4401`** (planted by me in the `9da4401`
worktree, pattern asserted to match once):

| mutant | original `9da4401` `-m day5` | new test |
|---|---|---|
| b drawn before a (`_vb = stat_b(res_b.draw(rng)); values[b] = stat_a(res_a.draw(rng)) - _vb`) | `49 passed` (SURVIVED) | `1 failed`: `E       AssertionError: ['b', 'a', 'b', 'a', 'b', 'a']` / `assert ['b', 'a', ...] == ['a', 'b', ...]` |
| the seven inflections stripped from `VERDICT_WORDS` (phrase list kept) | — | `1 failed`: `E           AssertionError: passing` / `assert False` / `where False = _verdict_flagged('passing')` |

**Lens 2's blocker FA-B1, before and after** (the lens's `repro_b1.py` rebuilt through the test
module's own helpers; each row duplicated under a case id, clustering declared):

```
                              9da4401                                                        e4c4f7e
A own auroc                   1.0, boundary_estimate                                          unchanged
A diff_vs_reference auroc     0.2256 (0.1599, 0.3054) cluster_bootstrap_percentile, reason None  0.2256 (None, None) none, boundary_estimate, frozen_sides ['a'], analytic_status refused_clustered
A diff_vs_complement auroc    0.2256 (0.1518, 0.3023) rendered                                  refused, frozen_sides ['a']
A own sens                    1.0 (20/20, 10 cases), boundary_estimate                          unchanged
A diff_vs_reference sens      0.35 (0.25, 0.4671) rendered                                      0.35 (None, None) none, boundary_estimate, frozen_sides ['a']
B diff_vs_complement auroc    -0.2256 (-0.2974, -0.1552) rendered                               refused, frozen_sides ['b']
B diff_vs_complement sens     -0.35 (-0.4671, -0.2167) rendered                                 refused, frozen_sides ['b']
B own auroc                   0.7744 (0.6980, 0.8431) cluster_bootstrap_percentile              unchanged
```

**My own conditioned shapes on `e4c4f7e`** (`probe/frozen_count.py`, one row per case,
clustering declared, R = 200 rendered samples, B = 200, my generator at seed 2026 — not the
lens's draws): AUROC, A = 10/10 binormal d' = 1.8 (true 0.898) beside B = 60/60 at d' = 0.954
(true 0.750), A separated in 200 of **4,127** draws → `{('none', 'boundary_estimate'): 200}`,
`frozen_sides {('a',): 200}`, 27 s. Sensitivity, A = 10 positive cases at 0.90 observed 10/10
in 200 of **563** → the same, 14 s. (The note's 3,713 / 600 are the lens's draws; mine differ
because the generator does.)

**The pre-fix interval those shapes rendered, re-measured at `9da4401`** with the same
generator (the 0.295 / 0.615 figures now in T7 and the `_bootstrap_difference` docstring,
attributed to lens 2): AUROC difference covered the true 0.1484 in **0.335** of 200 rendered
replicates, mean width 0.167; sensitivity difference covered the true 0.10 in **0.560**, mean
width 0.192. Both within Monte-Carlo error (0.035) of the shipped figures; both far below 0.95.

**Attack shapes on `e4c4f7e`** (`probe/attack_shapes.py`, clustering declared): constant-score
A (own 0.5 `boundary_estimate`) → A vs reference −0.2569 refused `frozen ['a']`, B vs
complement +0.2569 refused `frozen ['b']`; reversed separation (own 0.0) → −0.8214 / +0.8214
refused, sides named the same way; A and reference C both separated → A vs C AUROC 0.0 and
sensitivity 0.0 refused `frozen ['a', 'b']`, B vs C refused `['b']`, A vs complement refused
`['a']`; A's sensitivity at 0/10 → −0.7667 refused `['a']`, and its specificity (10/10) 0.3000
refused `['a']`. Every one: method `none`, no bounds, estimate carried, `analytic_status
refused_clustered`.

**The zero-width survivor (`if frozen or lo == hi:` → `if frozen:`).** The note says no one
tried to construct a zero-width difference with neither side frozen. I tried: two-valued sides
with independent off-mode mass 0.02–0.10 on each, B = 200, 10,000 trials → 5,239 with neither
side frozen by `_frozen_sides`, **0** of them with `lo == hi` on the difference. On these
constructions the `lo == hi` term after the per-side check was never the deciding branch;
that is what I measured, not a proof the branch is dead.

**Lens 1 blockers and RG-B1, my constructions on `e4c4f7e`** (`probe/closures.py`): F6 tripled
under a case id, declared and detected → every footnote entry `clustered_data_analytic_ci_invalid`,
`p_raw None`, `family_size 0`, route recorded; one row per patient → `chi2_homogeneity 4.6327,
p 0.0986`. Unpaired DeLong i.i.d.: separated / reversed / constant-score arm a → `boundary_estimate`,
method `none`, `z None`, `p None`, `variance_a 0.0`; both arms → refused; an arm at
`variance_a 0.01` renders `delong_wald` (the guard is at zero). PPV / NPV / accuracy /
sensitivity for `sex = F` on `make_cohort(400)` equal my numpy hand counts on the raw columns
to 6 dp (0.6375 / 0.881356 / 0.782828 / 0.784615).

**Carried items, still reproducing** (as the note says): FA-N1 max `delong_wald` `ci_hi`
**1.0796** over 3,000 draws of 10/10 vs 10/10 binormal ±2 arms, `flags []`; FA-N7 all S3 scores
missing → `level_order ['S1', 'S2']`, no trace of S3. FA-N11 does **not** reproduce, as the note
says: at `9da4401` `unknown_row_not_marked` carries `what="Unknown row membership: missing
rows form a level not marked is_unknown_row"`.

**Lens 2's 18 mutants, my rebuild** (`probe/lens_mutants_rerun.py`, through the committed
sweep's `make_copy` / `plant` / `run_marker`, import asserted from the copy): **18 planted,
8 killed, 10 survived; 318 s.** Survivors, the note's ten exactly:
`L2_deficient_check_side_a_only`, `L2_zero_width_difference_rendered`, `L2_yates_on_two_levels`,
`L2_clustered_prop_diff_n_cases_max`, `L2_event_units_are_rows`,
`L2_auroc_diff_evaluability_side_a_only`, `L2_orientation_ignored`,
`L2_single_class_brier_not_refused`, `L2_clustered_prop_diff_no_tier`,
`L2_declared_reference_not_stripped`. Killed: `L2_side_b_drawn_before_side_a` (new this round),
`L2_clustered_prop_diff_sign` (new this round), `L2_detected_route_runs_the_chi_square`,
`L2_complement_is_the_whole_attribute`, `L2_clustered_refusal_wrong_reason`,
`L2_delong_guard_side_a_only`, `L2_delong_p_from_one_tail`, and my `L2_unknown_row_enters_homogeneity` (N5).

**Frozen fixture values, re-derived from the published formulae without repo code** (Wilson
centre / radius form, Newcombe-10 square-and-add, `sum (O−E)²/E` with p = e^(−χ²/2) at df 2,
Holm step-down with running maximum): F14 (0.0524, 0.3339), (0.1705, 0.8090), (0.6791,
1.0000); `F14_COMPLEMENT_FROZEN` 30/40 vs 100/120 → −0.0833 (−0.2453, 0.0493); F8 half-widths
0.0851 / 0.0596 / 0.0341; F6 χ² 4.6327, p 0.0986; Holm [0.036, 0.08, 0.30]. Each equals the
value the test asserts at `approx4` (abs 5e-5). The F14 test's docstring and
`fixtures/newcombe_table2.json` carry `[unverified against the primary PDF]` unchanged, and
`newcombe_fixture()` asserts the fixture's `provenance.status` string. Untouched by this diff.

**Nothing weakened.** `git diff --name-status 9da4401 e4c4f7e -- tests/` → `M tests/test_subgroups.py`;
against `3ea2bfd` → `A tests/test_subgroups.py` only. Added lines contain no `skip`, `xfail`,
`.only`, `TODO`, `FIXME`; no `pytest.mark` line removed; `pyproject.toml`, `conftest.py`, CI and
`schema/` untouched in this diff (the schema diff against `3ea2bfd` is the day-5 build's:
`subgroups` items typed, `fairness` typed, two reasons and one flag added to enums,
`clustering_route` required — tightening, nothing loosened). The new tests sit under the
file's `pytestmark = pytest.mark.day5`. The commit ends with the required `Co-Authored-By`
line; the main tree is clean apart from this file.

**Constants.** `bootstrap.py` line 210 `MIN_UNITS_PER_STRATUM = 2`, line 259
`MAX_FROZEN_VARIANCE_SHARE = 0.20`; `design/conventions_T7.md` records the same two values;
the `>=` rule is untouched. T7's new prose cites 0.715 / 0.620 (u = 2, m = 0), 0.672 (10 cases
at p = 0.9), 0.932 / 0.915 and 0.863 / 0.873 — each present in T7's own recorded table.

**Schema.** `bootstrap` in the cell definition is `{"type": ["object", "null"]}` (free), so
`resampling.frozen_sides` needs no schema change (the note's decision 2 holds); the FA-B1 test
validates the refused-difference document against `output_schema_v1.json` with 0 errors, and
the `clustered_pair()` documents at both shas serialise with only `frozen_sides` as a new key.

**scipy-free import, cold process:** `sys.modules["scipy"] = None` → `import proofpack`,
`proofpack.stats`, `proofpack.stats.subgroups` succeed from the worktree; `statsmodels` and
`sklearn` not loaded; `_homogeneity_test` → `scipy_unavailable`;
`heterogeneity_footnote(..., clustering_route="detected")` → `clustered_data_analytic_ci_invalid`.

**Hard-rule sentences in the diff.** Every added sentence that names a behaviour was checked
against a run counter-example: the `TypeError` on a missing `clustering_route` (fails pre-fix
"DID NOT RAISE"); `insufficient_levels` on every route (fails pre-fix on the quoted assertion);
the per-side frozen refusal (fails pre-fix on the 0.2256 interval; the committed
`frozen_side_check_removed` and `frozen_check_side_a_only` mutants die); "the log reads a, b,
a, b" (the b-before-a mutant survives `9da4401`'s suite and fails the new test). The one
sentence that reads as a guarantee — `_bootstrap_difference`: "the draw is a pure function of
the cell key like every other cell" — is round-1 text the note says it kept deliberately; the
determinism test and the `side_b_from_a_fixed_generator` mutant (killed) are its
counter-examples, and the sentence would be more exact as "of the policy seed, the cell key and
the data". Not re-raised. The `MAX_FROZEN_VARIANCE_SHARE` docstring ends "not a guarantee";
`_frozen_sides` names `bootstrap_percentile`'s rule; the verdict-grep docstring says what the
tokeniser does not do ("not a stemmer"). The three sentences lens 2 falsified are gone from
T7 and `bootstrap.py` (the grep test, plus my own read of the diff).

**Docstrings of new functions.** `_frozen_sides` names the single-cell rule it applies
(`bootstrap_percentile`) and the three shapes it fires on; `separated_level_cohort_with_case_ids`
names its construction and the lens id; `_record_two_sided` has none (N4). No new statistic
was introduced this round, so no new oracle was due; the only new number in shipped text is
the N2 pair, now measured.

## What I could not check

- `coverage_bar.py --full` (743–781 s): not re-run; the script did not change in this diff.
- pROC `roc.test(paired = FALSE)` — no R capture; `[unverified]` stands.
- Newcombe 1998 Table II against the primary PDF — `[unverified]` stands; my formula
  reproduces the fixture to 4 dp.
- The lens's exact draw counts (3,713 / 600) and exact coverage figures (0.295 / 0.615) — the
  lens's generator is not committed; my own gives 4,127 / 563 and 0.335 / 0.560.
- The lens's exact spelling of eight of its 18 mutants — rebuilt from the note's descriptions;
  outcomes match on 17, and my eighteenth is killed where the note's is not (N5).
- Josh's two decisions (DEC-08 on the `MIN_UNITS_PER_STRATUM` half; `>=` vs `>`) — decisions,
  not checks.

## Sentences I refused to write

- "FA-B1 is closed" — it is refused on every shape I constructed and on 200 / 200 conditioned
  samples of each of two shapes; a side frozen in fewer than about 95 % of resamples renders by
  the same rule that renders its own cell, and the coverage of those rendered shapes was not
  measured by the note or by me.
- "The suite pins the two-sided bootstrap" — ten of the lens's mutants survive `-m day5` on
  this tree, in my spellings as in the note's.
- "The zero-width branch is dead code" — 0 of 5,239 constructions reached it; that is not a proof.
- "The `clustered_pair()` cohort is unchanged" — four cells changed, correctly (N1).
- "The sweep shows the tests have teeth" — it shows 34 declared mutants die.

Worktrees `lens-E5-r3-regression/wt-new` and `/wt-old` removed after this note was written; the
main tree was left as found apart from this file. Probe scripts (`repro_b1.py`,
`dump_clustered_pair.py`, `frozen_count.py`, `prefix_coverage.py`, `attack_shapes.py`,
`closures.py`, `lens_mutants_rerun.py`) lived in the session scratchpad and were not committed;
every construction is described inline.
