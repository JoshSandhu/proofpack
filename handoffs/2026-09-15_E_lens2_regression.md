# Verify (build day 5, repair round 1) — 2026-09-15 — Lane E — **REGRESSION-AND-RECORD LENS 2**

Repo `proofpack`. Commit under review `9da4401` ("fix E: refuse the heterogeneity test on
clustered rows and the DeLong difference with a frozen arm (day 5, repair round 1)");
pre-fix `d1fd20a`. Repairer's note: scratchpad `notes/E5_repair1.md`. Everything below was
executed in detached worktrees at `9da4401` and `d1fd20a` with `PYTHONPATH=<worktree>/src`
forced and proved (`proofpack.__file__` printed from inside each worktree before any number
was trusted; the editable `.pth` on this machine otherwise imports the main tree).

**Verdict: PASS — 0 blockers, 4 non-blocking.**

Every figure in the repairer's note is true, in both shells. The suite (359 / 1 / 1), `-m day5`
(49), the day markers (59+1 / 40 / 29+1 / 182 — the repair-r7 figures), lint, format, doctor,
the committed sweep (29 / 29 / 0), the `--quick` coverage table (byte-identical between Git
Bash and PowerShell, every cell the note quotes), and the seed-20260916 table (0.940 / 0.950,
0.925 / 0.915, 0.910 / 0.890 — exactly, with a fresh generator per cell). The three tests the
note says fail at `d1fd20a` fail there on the assertion it quotes, not on an import; the four
tests that pass at `d1fd20a` are each proved by a mutant I planted myself (original `-m day5`
`42 passed`, the new test `1 failed` on the quoted line), and the frozen-share test fails when
`>=` is flipped to `>`. Both lens-1 blockers (FA-B1, FA-B2) and the lens-1-regression blocker
(RG-B1) are closed by execution, not by the note. Nothing was skipped, xfailed, deleted or
un-marked. The schema change adds one required enum key and loosens nothing.

---

## Blockers

None.

---

## Non-blocking

### N1 — The share-0.20 shape also straddles the bar: 0.880 at seed 20260916 with one generator stream

The note, `bootstrap.py` and `conventions_T7.md` say the refused 0.20 shape "measured at or
above the bar at every seed tried" and list 0.925 / 0.915 at seed 20260916 (R = 200,
B = 500). That figure reproduces **exactly** when each cell gets `default_rng(20260916)`
afresh. Run with one generator shared across the six cells in share order (the way
`coverage_bar.main()` itself shares one generator), the same seed gives:

| share | N = 30 | N = 120 |
|---|---|---|
| 0.10 | 0.940 | 0.955 |
| 0.20 | **0.880** | 0.915 |
| 0.30 | 0.920 | 0.900 |

So the 0.20 / N = 30 cell has now been measured at 0.932 (recorded, R = 400), 0.900
(`--quick`), 0.925 (fresh generator) and 0.880 (shared generator) — a spread of 0.052, about
two and a half MC standard errors at R = 200. The sentence "met the bar at every seed tried"
is an accurate record of the four runs the note made and is contradicted by a fifth of equal
standing. The decision it supports (keep 0.20, `>=` untouched, the refusal on the conservative
side) is **unchanged and if anything strengthened**: the constant refuses a shape whose coverage
is, on the evidence, near the bar rather than above it. Record the 0.880 beside the others in
`bootstrap.py` and T7 and drop "at every seed tried"; the constant does not move.

Repro: `PYTHONPATH=src python -c "import sys;sys.path.insert(0,'scripts');import coverage_bar as cb,numpy as np;rng=np.random.default_rng(20260916);print([[cb.coverage_auroc(rng,1,3,cb.mixed_cases_for_share(s,3),n,200,500)['coverage'] for n in (30,120)] for s in (0.10,0.20,0.30)])"`
→ `[[0.94, 0.955], [0.88, 0.915], [0.92, 0.9]]` (44 s).

### N2 — Under clustering, `clustered_data_analytic_ci_invalid` takes precedence over `insufficient_levels`

An attribute with fewer than two evaluable levels (all rows Unknown) reports
`insufficient_levels`, `n_levels 0` on the i.i.d. route. Under a declared or detected plan
the same attribute now reports `clustered_data_analytic_ci_invalid`, `n_levels 0`: the test
was not run because the rows are clustered, which is true, but the reason a reader would
want (there was nothing to compare) is masked. Not a wrong number — no p-value either way,
and `n_levels 0` is beside it — and neither docstring nor T7 states the precedence. State it,
or emit `insufficient_levels` first.

Repro: `run(cols_all_unknown_with_case_id, criteria_for(SITE, clustering={"unit":"case_id","declared_by":"t"})).attribute("site")["heterogeneity"]["tests"]`
→ `[('sensitivity', 0, 'clustered_data_analytic_ci_invalid'), ('specificity', 0, 'clustered_data_analytic_ci_invalid')]`; the same columns without `case_id` → `insufficient_levels`.

### N3 — The note's "3 failed, 5 passed" is 3 failed, 4 passed

The `-k` expression selects seven tests (42 + 7 = 49); at `d1fd20a` with the new
`tests/test_subgroups.py` copied in the result is `3 failed, 4 passed, 42 deselected`, on
the repaired tree `7 passed, 42 deselected`. The three failures and their first `E` lines
are exactly as the note's table quotes. Arithmetic in the note only.

### N4 — Timing sentences

`--quick`: 38 s (Git Bash) / 39.6 s (PowerShell) against the docstring's "41 s measured
2026-09-15"; the committed sweep 334 s against the note's 341 s. Within run-to-run noise;
the numbers, not the seconds, are what is recorded. The `--full` run (743–781 s) was not
re-run this session (see "Could not check").

---

## What I could not break (evidence)

**Suite and commands, both shells, worktree at `9da4401`:**

```
python -m pytest -q -p no:cacheprovider           359 passed, 1 skipped, 1 xfailed   (40.86 s bash / 38.68 s ps)
python -m pytest -q -p no:cacheprovider -m day5   49 passed, 312 deselected           (15.50 s / 15.44 s)
-m day1 / day2 / day3 / day4                      59+1 skipped / 40 / 29+1 xfailed / 182   (both shells; = repair-r7)
python -m ruff check .                            All checks passed!                  (both)
python -m ruff format --check .                   50 files already formatted          (both)
python -m proofpack.cli doctor --offline          All essential checks passed.        (both)
python scripts/mutation_sweep.py --marker day5    29 planted, 29 killed, 0 survived; 334 s   (note: 341 s)
python scripts/coverage_bar.py --quick            38 s bash / 39.6 s ps; outputs byte-identical (elapsed line excluded)
                                                  0.05 → 0.960 / 0.900; 0.10 → 0.860 / 0.930; 0.20 → 0.900 / 0.870;
                                                  0.30 → 0.850 / 0.880; loosest feasible pair: None   (= note)
repair-r7's 27 bootstrap tests (the note's -k)    27 passed, 155 deselected           (both)
this round's seven tests (the note's -k)          7 passed, 42 deselected             (both)
```

**Fails pre-fix** (`d1fd20a` worktree, `PYTHONPATH` proved, new `tests/test_subgroups.py`
copied in, the seven tests): `3 failed, 4 passed`. First `E` lines, verbatim:

- `test_the_heterogeneity_footnote_is_refused_on_clustered_rows_with_the_dec09_typed_reason` → `E           KeyError: 'clustering_route'`
- `test_unpaired_delong_refuses_the_difference_when_either_arm_has_zero_variance` → `E           AssertionError: assert (None == 'boundary_estimate')` / `where None = Number(est=0.2255555555555555, ci_lo=0.14421795320756903, ci_hi=0.306893157903542, ci_level=0.95, method='delong_wald', ...)`
- `test_a_declared_reference_whose_rows_are_all_excluded_halts_h09_naming_the_analysed_rows` → `E       AssertionError: Regex pattern did not match.` / `Expected regex: 'analysed rows'` / `Actual message: 'H09: subgroup reference_level is not an observed level'`

All three are the assertion the note quotes; none is an import or attribute abort.

**Mutant proofs for the four tests that pass at `d1fd20a`** (my own script, each mutant
planted in the `d1fd20a` worktree with the pattern asserted to match exactly once; the
*original* `d1fd20a` test file run under `-m day5`, then the *new* file's single test):

| mutant | original `-m day5` | new test |
|---|---|---|
| `ppv` → `~pos[sel]` | `42 passed` (SURVIVED) | `1 failed`: `('sex', 'F', 'ppv', {'est': 0.3625, ...})` / `assert (29 == 51)` |
| `npv` → `pos[sel]` | `42 passed` | `1 failed`: `('sex', 'F', 'npv', {'est': 0.11864406779661017, ...})` / `assert (14 == 104)` |
| `accuracy` → `pos != pred` | `42 passed` | `1 failed`: `('sex', 'F', 'accuracy', {'est': 0.21717171717171718, ...})` / `assert (43 == 155)` |
| `ppv` conditioned on `pos` | `42 passed` | `1 failed`: `('sex', 'F', 'ppv', {'est': 1.0, ...})` / `assert (65 == 51)` |
| side b from `default_rng(b)` | `42 passed` | `1 failed`: `E       AssertionError: 0` / `assert 0 > 40` (the first assertion, as the docstring says) |
| `VERDICT_WORDS` without `calibrated`/`passes`/`fails` | — | `test_the_verdict_grep_flags_every_phrase_the_brief_names` `1 failed`: `AssertionError: passes` |
| `bootstrap.py` `>=` → `>` (on `9da4401`) | — | `test_the_frozen_share_rule_refuses_the_share_exactly_at_the_constant` `1 failed`: `assert None == 'positive'`; full suite `2 failed, 357 passed` |

**Both lens-1 blockers, reproduced before and after** (`probe.py`, the lens's F6-×3 cohort
and its 10/10-separated shape at my own seed 1):

```
FA-B1 declared:  route=declared  test=None p_raw=None reason=clustered_data_analytic_ci_invalid family_size=0 'cluster' in json=True n_levels=3
FA-B1 detected:  route=detected  (same)
       companion sensitivity cell: method cluster_bootstrap_percentile, analytic clustered_data_analytic_ci_invalid
FA-B1 one row per patient: 4.6327, p 0.0986, route none;  tripled rows, no ids: route none, statistic 13.898 (= 3 × 4.6327)
       hand chi-square on [[45,5],[38,12],[27,3]]: 4.6327, p = e^(−χ²/2) = 0.0986;  on the ×3 table: 13.898, p 0.00096
FA-B2 A own auroc: 1.0 boundary_estimate none
FA-B2 A diff_vs_reference: 0.2128 (None, None) method none, boundary_estimate, analytic_status unavailable, z None, p None, variance_a 0.0
       both arms frozen → boundary_estimate; one A positive moved to 0.15 → delong_wald, variance_a 0.00113, z 3.41;
       one cross-class tie (AUC 0.995) → delong_wald, variance_a 0.00327 — the guard is at zero, not near it
       my own placement-value DeLong (V10 = mean_j ψ, V01 = mean_i ψ, S10/m + S01/n, ddof 1): A (1.0, 0.0), B (0.78722, 0.0017344) — engine identical
```

`delong_covariance` raises below two positives or two negatives, so no NaN variance reaches
the `<= 0.0` guard (I looked for a NaN path through the new branch and found none).

**RG-N7's three attempts re-run on the repaired tree:** (i) `clustering.unit: case_id`, no
`case_id` column → `ValueError clustering.unit is 'case_id' but no case_id column was
supplied`; (ii) `ClusterPlan(False, "none", ...)` over a repeating column → `ValueError the
supplied ClusterPlan contradicts the case column over the analysed rows`; (iii) ids omitted,
unit `none`, repeating column → every proportion `cluster_bootstrap_percentile` / `none`,
route `detected`, footnote refused. DEC-10 census on that report: no `wilson`, `newcombe10`
or `delong_*` anywhere.

**Lens-1 "could not break", re-checked on four reports** (i.i.d. 400 rows; declared;
detected; the separated-level cohort): schema errors 0 / 0 / 0 / 0; 354 / 118 / 118 / 74
serialised Numbers, each with a CI or a reason in `NOT_ESTIMABLE_REASONS`, none `method:
none` with an interval, every flag in `FLAGS`; no verdict word (the extended set) in any key
or string; no `diff_vs_overall`; no `"status"` key. Lens-1-regression N3 (the 10-case
clustered cell at 9/10 renders `0.9 (0.7, 1.0)` with its tier flags, no refusal) still
reproduces — it is carried, and T7 now says so.

**Frozen fixture values, re-derived from the published formulae without repo code:**

| value | mine | fixture / test | test precision |
|---|---|---|---|
| F14 56/70 vs 48/80 | (0.0524, 0.3339), dev 3.1e-5 / 2.7e-5 | same | 5e-5 |
| F14 9/10 vs 3/10 | (0.1705, 0.8090), dev 2.3e-5 / 1.8e-5 | same | 5e-5 |
| F14 10/10 vs 0/20 | (0.6791, 1.0000), dev 1.4e-5 / 0 | same | 5e-5 |
| frozen complement 30/40 vs 100/120 | −0.0833 (−0.2453, 0.0493), dev 1e-6 / 1.4e-5 | `F14_COMPLEMENT_FROZEN` | 5e-5 |
| F8 Wilson half-width p = 0.9, n = 50 / 100 / 300 | 0.0851 / 0.0596 / 0.0341, dev ≤ 3.7e-5 | same | 5e-5 |
| F6 χ², p; Fisher; Holm | 4.6327, 0.0986; 0.1084; [0.036, 0.08, 0.30] | same | 5e-5 |

The F14 test's docstring and `fixtures/newcombe_table2.json` carry
`[unverified against the primary PDF]` unchanged, and the test asserts the fixture's
`provenance.status` string (line 338). These sections were not touched by the diff.

**Nothing weakened.** `git diff --name-status d1fd20a 9da4401 -- tests/` → `M tests/test_subgroups.py`;
against `3ea2bfd` → `A` only. The diff adds no `skip`, `xfail`, `.only`, `TODO`, `FIXME`
and removes no `pytest.mark`; `pyproject.toml`, `conftest.py` and CI untouched; the new
tests sit under the module-level `pytestmark = pytest.mark.day5`. The main tree is
`ahead 10` of `origin/main` — not pushed. The commit ends with the required
`Co-Authored-By` line.

**Schema.** The only change to `output_schema_v1.json` is nine added lines: `clustering_route`
in the footnote's `required` and as an enum `none` / `declared` / `detected`. A footnote
without it is rejected (the test deletes the key and asserts errors; I confirmed on the
declared report). The AUROC-difference `detail` block is a free `object`, so `z: null` /
`p_value: null` validate (0 errors on the separated-level report).

**Constants.** `bootstrap.py`: `MIN_UNITS_PER_STRATUM = 2`, `MAX_FROZEN_VARIANCE_SHARE = 0.20`;
`conventions_T7.md` records the same two values; only docstrings and prose changed.

**scipy-free import, cold process:** `sys.modules["scipy"] = None` before any import →
`import proofpack`, `proofpack.stats`, `proofpack.stats.subgroups` succeed from the
worktree; `statsmodels` and `sklearn` not loaded; `_homogeneity_test` → `scipy_unavailable`;
`heterogeneity_footnote(..., clustering_route="detected")` → `clustered_data_analytic_ci_invalid`.

**Hard-rule sentences in the diff.** Each sentence that names what a check inspects was
checked against the test it cites; I found none asserting a guarantee. The one behavioural
claim without a recorded counter-example — `scripts/mutation_sweep.py`: "`proofpack.__file__`
must resolve under the copy's `src` or the sweep exits" — I exercised: `assert_imports_from_copy`
on an empty copy raised `SystemExit: proofpack resolves to C:\...\GPS\ProofPack\proofpack\src\proofpack\__init__.py, not the copy under ...`.
The exit branch fires. "Neither repair widens a gate" holds by inspection: the old
`unpaired_delong` refused only at `var_a + var_b == 0` (both zero); the new one at either
zero, a superset; the footnote refuses on two routes it previously computed.

**Docstrings.** `unpaired_delong` names DeLong 1988 and pROC `[unverified]`;
`heterogeneity_footnote` names the F6 figures and the lens measurement;
`_clustered_refusal` computes no statistic and says so; the two new test cohorts and
`_RecordingResampler` carry docstrings naming what they build.

## What I could not check

- `coverage_bar.py --full` (743–781 s): not re-run this session; lens 1 reproduced all 60
  cells byte-for-byte at `d1fd20a`, and the script's code did not change in this diff (docstring only).
- pROC `roc.test(paired = FALSE)` — no R capture; `[unverified]` stands.
- Newcombe 1998 Table II against the primary PDF — `[unverified]` stands.
- The lens's 20,000-replicate 0.269 coverage figure quoted in the `unpaired_delong`
  docstring — not re-measured; the shape it describes (`variance_a = 0.0`, `delong_wald`
  rendered) reproduced at `d1fd20a` and is refused at `9da4401`.
- Josh's two decisions (DEC-08 on the proportion route; `>=` vs `>`) — decisions, not checks.

## Sentences I refused to write

- "The 0.20 shape meets the bar" — measured 0.880 at one generator stream (N1).
- "The repair closes clustering for the subgroup module" — it refuses the footnote on two
  routes on the cohorts I ran; fourteen lens-1 survivors remain unobserved by `-m day5`, as
  the note lists.
- "The seven tests pin the repair" — three fail pre-fix on their assertion; four pin
  behaviour only through the mutants tabulated above, which is what the note claims and no more.
- "The sweep's 29/29 shows the tests have teeth" — it shows 29 declared mutants die.

Worktrees `lens-E5-r2-regression/new` and `/old` removed after this note was written; the
main tree was left clean apart from this file.
