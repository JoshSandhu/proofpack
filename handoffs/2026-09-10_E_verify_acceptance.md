# Verify — 2026-09-10 — Lane E — acceptance lens (executing the criteria, auditing the claim-to-code gap)

**Verdict: FAIL.** Four blockers. The statistics are sound and independently
reproducible; the defects are in the *refusal surface* — the part of the module the day
exists to build — and in two typed values that reach the output JSON.

Everything below was re-run by me, from a clean shell, against `5bc69fb`. The repo is
left clean; mutation work was done in a throwaway `git worktree` that has been removed.

---

## 1. The suite, re-run verbatim

Every command the handoff gives, typed exactly as written.

```
$ cd C:/Users/joshs/GPS/ProofPack/proofpack && python -m pytest -q -p no:cacheprovider
213 passed, 1 skipped, 1 xfailed in 24.75s

$ python -m pytest -q -p no:cacheprovider -m day1
59 passed, 1 skipped, 155 deselected in 4.09s
$ python -m pytest -q -p no:cacheprovider -m day2
40 passed, 175 deselected in 1.41s
$ python -m pytest -q -p no:cacheprovider -m day3
29 passed, 185 deselected, 1 xfailed in 1.78s
$ python -m pytest -q -p no:cacheprovider -m day4
85 passed, 130 deselected in 17.45s

$ python -m ruff check .                    -> All checks passed!            (rc 0)
$ python -m ruff format --check .           -> 32 files already formatted    (rc 0)
$ python -m proofpack.cli doctor --offline  -> All essential checks passed.  (rc 0)
```

- **Baseline intact.** 59 + 40 + 29 = 128 = the pre-existing baseline, unchanged.
  `git diff --stat 3bee15c HEAD -- tests/` shows **one file added, none modified** — no
  day-1..3 test was weakened, skipped, xfailed or re-marked to get green.
- **Nothing was skipped to pass.** The only `skip`/`xfail` in the repo are the two
  pre-existing ones (doctor write-access; F13 pROC). `tests/test_bootstrap.py` adds
  none; its two `pytest.importorskip` calls (scipy, jsonschema) both resolve here and in
  CI (`uv sync --all-groups`).
- **85 day-4 tests, all marked.** `--collect-only tests/test_bootstrap.py` = 85;
  `--collect-only -m day4` = 85/215. The counts reconcile exactly.
- **No new dependency.** `git diff 3bee15c HEAD -- pyproject.toml uv.lock` changes only
  the three marker *descriptions*. `uv.lock` untouched. No network import anywhere under
  `src/proofpack/stats/`.

### Per-day CI gate

Marker extraction run verbatim from `ci.yml`:

```
$ python -c "<the exact tomllib snippet from ci.yml>"
day1 day2 day3 day4 day5 day6 day7 day8 day9 day10
```

Loop emulated with the workflow's own rc-5 tolerance: `day1..day4: ok`,
`day5..day10: no tests yet (rc=5, tolerated)`. `day4` **is** registered in
`pyproject.toml` and **is** picked up.
`test_ci_runs_every_declared_day_marker_without_a_hardcoded_list` still holds.

### The conftest no-marker guard still bites

Added `tests/test_zz_unmarked_probe.py` containing a bare `def test_unmarked_probe()`:

```
FAILED tests/test_invariants.py::test_every_collected_test_carries_a_day_marker
1 failed, 213 passed, 1 skipped, 1 xfailed
```

It bites on a full run, which is what CI runs. It does not bite when a single file is run
in isolation — expected, given the collection hook.

### The scipy-free CI job body

Ran the job's Python block locally with a `MetaPathFinder` that makes `scipy`
unimportable: `import proofpack ok without scipy 0.1.0.dev1`, and the F3 assertion
`(0.44, 1.0)` holds. That step is real.

The **wheel** job could not be exercised: no `hatchling`, no `build`, no `uv` on this
machine. The handoff already says so. Carried, not a finding.

---

## 2. Statistics re-derived independently

Written from the published formulae in my own scratch scripts, importing **no** proofpack
code (`scratchpad/verify-E-acceptance/indep_f3.py`, `indep_delong.py`, `indep_f9.py`).

| Quantity | My independent value | Handoff / R2 §9 |
|---|---|---|
| F3 AUROC | 0.80 | 0.80 |
| F3 percentile CI, `default_rng(20240101)`, B=2000, pos then neg | **(0.44, 1.00)** under all five quantile conventions | (0.44, 1.00) |
| F3 bootstrap sd | 0.14842279023900326 | 0.14842 |
| DeLong SE (structural components, `ddof=1`) | 0.15491933384829668 | 0.1549 |
| Wald CI | (0.49636, 1.10364) | (0.4964, 1.1036) |
| Logit CI | (0.37486, 0.96388) | (0.3749, 0.9639) |
| τ = 3·max(0.0598·sd, ½·spacing) | 0.0600 (grid term 0.02 dominates 0.00925) | 0.0600 |
| Endpoint gaps vs clamped Wald | 0.05636 and 0.00000 | 0.0564, 0.0000 |
| sd/SE − 1 | −4.19 % against band 24.74 % | −4.2 %, 24.7 % |
| F9b width ratio, k=3, seeds 11/12/13 | 1.854 / 1.748 / 1.772 | 1.748, 1.772, 1.854 |
| F9b width ratio, k=5 | 2.350 / 2.261 / 2.255 | 2.255, 2.261, 2.350 |
| F9b ρ-control, k=4, ρ=0 | 0.974 / 0.994 / 1.035 | 0.974, 0.994, 1.035 |
| ρ = 0.3 / 0.6 / 0.9 | 1.302–1.338 / 1.581–1.639 / 1.812–1.919 | identical |

Every number in the handoff's §2 reproduces to the digits printed. The mathematics is not
the problem here.

---

## 3. Mutation tests — what the suite does catch

Worktree at `5bc69fb`, `PYTHONPATH=<worktree>/src`, `-p no:cacheprovider`, reverted after
each.

| Mutation | Result |
|---|---|
| Clustered resampler draws rows instead of whole cases | **14 failed** (all of F9, plus the small-stratum refusal) |
| `flags = ["delong_refused_clustered"]` becomes `[]` | **1 failed** (the X2 JSON test) |
| Disable the *detected* clustering branch in `plan_clustering` | **1 failed** |
| `MIN_USABLE_FRACTION` 0.90 → 0.0 | **1 failed** |
| Drop `insufficient_clusters` from `output_schema_v1.json` | **1 failed** (enum sync) |
| `clustered_by_case` → `clustered_flat` inside `auroc_ci` | **1 failed** |
| Clustered proportion resamples rows but keeps the `cluster_bootstrap_percentile` label | **1 failed** |
| `SMALL_CLASS` 10 → 3 | **1 failed** |
| `np.random.seed(0)` inside `bootstrap.py` | **1 failed** (the `ast` guard) |
| Unmarked test added | **1 failed** (marker guard) |

That is a genuinely load-bearing suite. **One mutation escaped** — see N3.

**BCa really is deferred, not half-present.**
`grep -rni "bca\|accelerat\|jackknife\|bias_correct" src/ schema/` returns only docstring
prose, the reserved enum value, the schema description and the `SUPPORTED_INTERVALS`
guard. No dead function, no unused acceleration parameter, no docstring promising a
behaviour that is absent. End to end: a `criteria.yaml` with `bootstrap.interval: bca` is
rejected by `jsonschema` against the real packaged schema
(`'bca' is not one of ['percentile']`), and `policy_from_declarations` raises. Confirmed
against a **real** `Declarations` object (`validate_dict`), not only the test's stub:
`{'B': 5000, 'seed': 42, 'interval': 'percentile', 'seed_source': 'declared', 'b_source': 'declared'}`.

---

## 4. BLOCKERS

### B1 — X2 is defeated by a plausible call: clustered data silently receives a DeLong / Wilson interval

`auroc_ci` and `proportion_ci` accept `cluster_ids` and **silently ignore them** when
`plan` is omitted (or says i.i.d.). Nothing raises, nothing is flagged, nothing is
recorded. The mirror-image mistake — clustered plan, missing `cluster_ids` — *does* raise,
and there is a test for it. The asymmetry is the defect: the module has the evidence of
clustering in its hand and does not look at it.

`scratchpad/verify-E-acceptance/probe6.py`, 40 cases × 4 rows, complete within-case
correlation:

```
plan omitted, cluster_ids given ->
  method: delong_wald   CI: (0.7633, 0.8917)
  flags: []   analytic_status: used   route: none
proportion, plan omitted -> wilson (0.6512, 0.7883) []

correct clustered CI: (0.6786, 0.9413)
```

The rendered interval is **2.1× too narrow**, carries `analytic_status: "used"`, and has
no flag and no companion refusal — there is no trace in the output JSON that anything
happened. This is precisely the failure X2 exists to prevent.

It is reachable from the day-5 call shape the handoff itself prescribes: both `plan` and
`cluster_ids` are keyword-optional with defaults, so forgetting `plan=` on one cell out of
forty is a one-token slip with no test and no runtime signal.

**Fix:** when `cluster_ids` is supplied and the resolved plan is not clustered, either
raise (matching the sibling path) or re-run detection through `plan_clustering`.
Regression test: `auroc_ci(s, y, cell_key="c", cluster_ids=repeating_ids)` must not return
`analytic_status == "used"`.

### B2 — `clustered_flat` does not check that `cluster_ids` align with the data

`clustered_by_case` raises on a length mismatch; `clustered_flat` — the clustered
*proportion* path — has no such check. With `cluster_ids` shorter than the indicator the
point estimate is computed over all rows and the interval over a **prefix**, and a
fully-formed, plausible Number is returned.

`scratchpad/verify-E-acceptance/probe8.py`, 400 rows / 100 cases, caller passes the first
200 ids:

```
MISALIGNED accepted. est 0.815 n 400 k 326 CI (0.79, 0.885) cluster_bootstrap_percentile ['wilson_refused_clustered']
CORRECT           est 0.815 n 400 k 326 CI (0.78, 0.85)
```

Same `est`, same `n`, same `k`, same `method`, same flag — a different interval, with no
error and no marking. Nothing distinguishes the wrong output from the right one.

**Fix:** the same `if ids.shape[0] != n: raise` that `clustered_by_case` already carries,
in `clustered_flat` (or in `proportion_ci` before it is called).

### B3 — `Number.n_cases` reports the run's case count on every subgroup cell

`auroc_ci` sets `n_cases=cplan.n_units` — the count from the run-level `ClusterPlan` —
while the resampling correctly uses the cell's own cases. Under the usage the handoff
prescribes for day 5 ("Build one `BootstrapPolicy` and one `ClusterPlan` for the run and
pass them to every cell"), every subgroup cell reports the wrong number of cases.

`scratchpad/verify-E-acceptance/probe1.py`:

```
run plan: {'clustered': True, 'route': 'declared', 'unit': 'case_id', 'n_rows': 120, 'n_units': 40}
cell rows: 60   true cell cases: 20
Number.n_cases reported: 40     <-- wrong
analytic n_cases: 40            <-- wrong
```

The existing test exercises only a cell that *is* the whole cohort, so it cannot see this.
The handoff then tells day 5 to print `n_cases` beside `n_pos`/`n_neg` (D1 §4.1), which
ships the wrong count into the subgroup table.

**Fix:** `n_cases=resampler.n_units`. Regression test: a run-level plan plus a cell-level
`cluster_ids` subset must report the subset's case count.

### B4 — `insufficient_positives` is emitted when the negatives are the scarce class

`bootstrap_percentile` maps a too-small stratum to
`"insufficient_clusters" if resampler.kind == "clustered" else "insufficient_positives"`.
For the stratified resampler the smallest stratum can be either class, so a cell with
plenty of positives and one negative is told it has insufficient positives — with
`n_pos: 9` sitting on the same Number, contradicting it.

`scratchpad/verify-E-acceptance/probe2.py`:

```
n_pos=9 n_neg=1 -> insufficient_positives | est 1.0 | n_pos 9 n_neg 1
n_pos=1 n_neg=9 -> insufficient_positives
```

`insufficient_negatives` is already in `NOT_ESTIMABLE_REASONS` and in
`output_schema_v1.json`; the correct value exists and was not used. This is a typed reason
in the output JSON, and D4 renders it into the pack — a wrong sentence handed to a
regulator, and a directly misleading one, because it names the wrong column to fix.

The handoff also mis-describes the code here: §1 says "fewer than two units in a stratum →
`insufficient_clusters`" without qualification. Only the clustered path does that.

**Fix:** choose the reason from which stratum is short (`positive` →
`insufficient_positives`, `negative` → `insufficient_negatives`), not from the resampler
kind.

---

## 5. Non-blocking

**N1 — the precision tier is the wrong one of the two.** `LOW_PRECISION_UNITS = 10`
carries the comment "(R2 section 3.3 precision tiers)", but R2 §3.3 says `n<10` →
`not_evaluable_shown_for_transparency` and `10≤n<30` → `very_low_precision`. The module
attaches `very_low_precision` when the smallest stratum is **below** 10 — the less severe
label on the least reliable cells. Measured: a clustered AUROC with 6 cases per class, and
an i.i.d. cell with 3 positives against 400 negatives, both come back
`['…refused_clustered' | 'analytic_ci_replaced_small_class', 'very_low_precision', 'imprecise']`.
Separately, `Number.with_precision_flags()` keys off `self.n`, which is `None` on every
AUROC Number, so it never fires there at all. Day 5's subgroup table assigns tiers from `n`
per D1 §145 and will attach `not_evaluable_shown_for_transparency` to the same cells — the
Number would then carry two contradictory tiers. Resolve before day 5 wires it up.

**N2 — "One grid cell is excluded" understates it by eight.** The guard in
`test_the_bootstrap_standard_error_reproduces_delongs_across_a_grid` is
`if se == 0.0 or auc > NON_DEGENERATE_AUC: continue`, and it fires on **9 of the 84** grid
cells, not one — the whole `separation = 3.0` column at every n from 5 to 200. I re-ran the
nine excluded cells against the band (`probe4.py`):

```
   n  sep  seed     auc       se      rel    band  verdict
   5  3.0   103     1.0      0.0      inf  0.2474  FAIL   (degenerate; no ratio exists)
  10  3.0   101    0.99  0.01414   0.1578  0.1474  FAIL   <- the one the handoff names
  20  3.0   101  0.9825   0.0143   0.0383  0.0974  PASS
  30  3.0   102  0.9889  0.00841    0.051  0.0808  PASS
  30  3.0   103  0.9822  0.01169  -0.0088  0.0808  PASS
  60  3.0   101  0.9831  0.00797   0.0112  0.0641  PASS
 100  3.0   103  0.9847  0.00576  -0.0278  0.0574  PASS
 200  3.0   101   0.982  0.00523  -0.0134  0.0524  PASS
 200  3.0   103  0.9835  0.00514   0.0198  0.0524  PASS
```

The substance survives — the exclusion is conservative and only one non-degenerate cell
actually fails — but the note as written tells Josh that 83 of 84 cells were checked when
75 were. Correct the sentence. Related: nothing asserts that a parametrisation left at
least one cell to check, so a fully excluded `(n, separation)` pair would pass vacuously
and green. None is fully excluded today.

**N3 — the global-RNG guard misses the import-form escape.** The `ast` walk inspects
`ast.Attribute` chains only. I added `from numpy.random import seed as _global_seed` plus a
call to it inside `cell_entropy`: **85 passed, 130 deselected** — not caught. The handoff's
wording ("rejects any `np.random.*` / `random.*` **attribute**") is literally accurate and
the escape does not change any number, so this is hygiene rather than correctness. Worth an
`ImportFrom` check while the file is open.

**N4 — clustered proportion Numbers carry no `n_cases`.** `proportion_ci` sets `n` and `k`
only, so the document would show `n = 160` beside a cluster-bootstrap interval with no
indication that there are only 40 independent units. The handoff's claim is scoped to
AUROC and is therefore honest, but the reader of the pack is not served.

**N5 — `Finding.code` is unvalidated.** `HaltError.__post_init__` rejects an unknown H-code
against a closed registry; `Finding` accepts any string. `W13` is invented here,
`W10`/`W12` on day 1, and only `W06` appears anywhere in the spec. A typo or a collision
cannot be caught. Cheap to add a `WARN_CODES` registry alongside `HALT_CODES`.

**N6 — the ruff line in the handoff is off by one.** The note records
`31 files already formatted`; HEAD gives **32** here (ruff 0.16.6), and `3bee15c` gives 29.
Both pass, so this is cosmetic — but Josh will type the command and see a different number.

**N7 — the `[unverified]` marking is in the code but not in the handoff.** The module
docstring correctly marks the Efron & Tibshirani (1993) citation
`[unverified — cited from R2 §1.5 … the book was not fetched in this build environment]`.
That is the right call and it is well done. CLAUDE.md asks that it also be *said in the
handoff*; §2 and §5 do not mention it. No invented citation was found anywhere in the
day's diff — I checked every reference in `bootstrap.py` and `test_bootstrap.py` against
R2 §9 and §1.3/1.5.

**N8 — carried, not new.** CI has still never executed (nothing pushed) and the wheel job
is still unexercised locally. The handoff says both.

---

## 6. What I tried that did NOT break

- Reproducing F3 from scratch under five quantile conventions — exact.
- DeLong SE, Wald and logit intervals from the structural-components formula — exact to
  ten-plus significant figures against the test's pinned constant.
- The whole F9 design-effect story, reimplemented independently — every ratio in the
  handoff reproduced, including the ρ = 0 negative control. The module is genuinely not
  simply widening clustered intervals.
- Seed determinism: same seed → identical draws; the two-subprocess `PYTHONHASHSEED` test
  runs and passes; the `cell_entropy` golden values hold.
- BCa deferral, end to end, through the real schema and the real `Declarations` object.
- Enum sync across code and `output_schema_v1.json` for all three enums; every Number the
  module emits validates against the packaged schema.
- Narrowing `bootstrap.interval` breaks no fixture: nothing anywhere in the three repos
  declares `bca`, and only `egress_schema.json` is vendored into the site.
- Day-1 gate H05 and the new W13 route do not collide: H05 halts on repeated `case_id` with
  *conflicting* `y_true` under `clustering.unit: none`; W13 covers the consistent case that
  survives it.
- No row-level egress, no network, no LLM, no new dependency, `--offline` clean.

## 7. Repo state

`git status --porcelain` in `proofpack` is empty apart from this file. My worktree
(`scratchpad/wt-acceptance`) has been removed with `git worktree remove --force`;
`git worktree list` shows only the two belonging to the other verifiers. Nothing was
committed and nothing was pushed.
