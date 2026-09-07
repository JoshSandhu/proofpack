# Verify — 2026-09-10 — Lane E — E4 bootstrap and clustered path — **SAFETY LENS**

Adversarial verification, fresh session, no stake in the build succeeding. Lens: attack the
safety properties. The repo was treated as read-only apart from this file; all mutation work was
done in a throwaway `git worktree` under the scratchpad, removed afterwards (`git status` clean).

**Verdict: FAIL — 4 blockers, 9 non-blocking.**

The statistics are real and I re-derived them myself. The refusal machinery is well built and
resists most of what I threw at it. What it does not resist is *the caller*: three of the four
blockers are the clustered path being silently bypassed or wrongly refused through ordinary use of
the module's own public API, and the fourth is that the day's headline safety property — the
clustering detection rule — is pinned by no test, so I broke it and all 213 tests passed.

---

## 1. What I re-ran (all commands from `C:/Users/joshs/GPS/ProofPack/proofpack`)

```
$ python -m pytest -q -p no:cacheprovider
213 passed, 1 skipped, 1 xfailed in 24.98s          # matches the note

$ python -m pytest -q -p no:cacheprovider -m day1   -> 59 passed, 1 skipped, 155 deselected
$ python -m pytest -q -p no:cacheprovider -m day2   -> 40 passed, 175 deselected
$ python -m pytest -q -p no:cacheprovider -m day3   -> 29 passed, 185 deselected, 1 xfailed
$ python -m pytest -q -p no:cacheprovider -m day4   -> 85 passed, 130 deselected in 15.35s

$ python -m ruff check .          -> All checks passed!
$ python -m ruff format --check . -> 32 files already formatted   (note says 31; immaterial)
$ python -m proofpack.cli doctor --offline -> All essential checks passed. exit 0
```

Nothing in the note's test counts is overstated.

### Independent re-derivation (my own code, nothing imported from `proofpack`)

`scratchpad/verify-E-safety/independent_f3_f9.py` — Mann–Whitney AUROC and DeLong structural
components written from the definitions:

```
F3 point AUROC: 0.8
independent F3 percentile CI: (0.440000, 1.000000)   usable=2000/2000  sd=0.148423
R2 s9 pinned value (0.44, 1.00) reproduced: True
independent DeLong SE: 0.15491933385   (repo pins 0.15491933384829668)
  naive DeLong SE on duplicated rows k=2: 0.103280   cluster-boot CI == stratified F3 CI: True
  naive DeLong SE on duplicated rows k=3: 0.082808   cluster-boot CI == stratified F3 CI: True
  naive DeLong SE on duplicated rows k=5: 0.063246   cluster-boot CI == stratified F3 CI: True
```

The F3 pin, the DeLong SE to 11 dp, the F9a exact equality and the shrinkage of naive DeLong under
duplication all reproduce from scratch. The numbers in the handoff are not invented.

---

## 2. Blockers

### B1 — `cluster_ids` supplied with `plan` omitted ⇒ DeLong and Wilson run on clustered data, silently

`auroc_ci` and `proportion_ci` both take `plan` and `cluster_ids` as independent optional
arguments. `_resolved()` (`bootstrap.py:543–549`) fabricates `ClusterPlan(False, "none", …)` when
`plan is None` **without ever looking at `cluster_ids`**. A caller who passes the case ids and
forgets the plan therefore gets the analytic interval on clustered rows, with
`analytic_status="used"`, no `delong_refused_clustered` / `wilson_refused_clustered` flag, and no
`W13`.

`scratchpad/verify-E-safety/attack_plan_omitted.py` — 100 rows / 20 cases, rows fully duplicated
within case:

```
declared plan  -> cluster_bootstrap_percentile 0.62 1.0  ['delong_refused_clustered','imprecise'] refused_clustered
plan omitted   -> delong_wald 0.7431564462520859 0.916843553747914 []  used  route= none
prop plan omit -> wilson 0.4038315303659957 0.5961684696340043  []  used
prop declared  -> cluster_bootstrap_percentile 0.42 0.58
```

The DeLong interval is **4.6x narrower** than the correct one and carries no trace of the switch.

The asymmetry is what makes this a defect rather than the caller's problem: the *mirror* case —
plan clustered, `cluster_ids` missing — raises `ValueError("a clustered plan needs cluster_ids")`
and has its own test, `test_a_clustered_plan_without_cluster_ids_is_a_programming_error_not_a_
silent_switch`. One direction is a guarded programming error; the reverse is a silent method
switch. The module's own docstring states the doctrine it breaks: *"A declared `case_id` unit with
no `case_id` column raises rather than quietly degrading to row resampling."*

Section 4 of the note tells day 5 to call these two functions per cell, so this fires within a week.

**Fix.** When `cluster_ids is not None and plan is None`, either raise, or call
`plan_clustering("none", cluster_ids)` so the detected route applies. Regression test: assert
`auroc_ci(..., cluster_ids=<repeated>)` with no plan never returns `analytic_status == "used"`.

### B2 — the clustering **detection rule** is pinned by no test; an arbitrary threshold survives all 213 tests

D1 line 43 is unambiguous: "`n_rows > n_cases` triggers clustered path". HEAD implements exactly
that (`bootstrap.py:277`, `if units < ids.shape[0]:`). Nothing tests it. I replaced it with an
arbitrary threshold in a scratch worktree:

```
mutation M13: bootstrap.py  "if units < ids.shape[0]:"  ->  "if units * 2 < ids.shape[0]:"
PYTHONPATH=<worktree>/src python -m pytest -q -p no:cacheprovider -m day4
  85 passed, 130 deselected in 21.05s
PYTHONPATH=<worktree>/src python -m pytest -q -p no:cacheprovider
  213 passed, 1 skipped, 1 xfailed in 26.30s
```

Concrete damage of that mutation — 100 patients, 10 of whom contribute a second lesion
(110 rows, 100 cases):

```
MUTATED  plan: none     False  n_units 100  n_rows 110
MUTATED  -> delong_wald 0.7851 0.924 []  finding: None
HEAD     plan: detected True   n_units 100  n_rows 110
HEAD     -> cluster_bootstrap_percentile 0.7711 0.9226 ['delong_refused_clustered']  finding: W13
```

Every day-4 fixture uses a uniform `np.repeat(arange(n), k)` with k >= 2, so *partial* clustering —
the realistic case, a handful of patients contributing two lesions — is never exercised. Per the
brief's own rule, a new test that passes against deliberately broken code is a blocker, and this is
the day's headline property (X2).

**Fix.** A test with one repeated `case_id` in an otherwise unique column asserting
`plan_clustering("none", ids).route == "detected"`, plus the same at 2/100 and 10/100 duplication,
and asserting the routed cell's method is `cluster_bootstrap_percentile`.

*(Everything else I mutated was caught — see section 4.)*

### B3 — one mixed-outcome case makes an entire 200-case clustered AUROC "not estimable", with two false statements attached

`clustered_by_case` puts a case whose rows carry both outcomes into its own `mixed` stratum
(`bootstrap.py:386`). `bootstrap_percentile` refuses the whole interval when
`resampler.smallest_stratum < MIN_UNITS_PER_STRATUM` (`bootstrap.py:449`). A `mixed` stratum of
size 1 is entirely ordinary in the canonical clustered design — a multi-lesion study in which
exactly one patient has one malignant and one benign lesion — and it takes down the cell.

`scratchpad/verify-E-safety/attack_singleton_mixed.py` — 200 patients x 2 lesions = 400 rows, 199
patients pure, one mixed:

```
strata sizes: {'positive': 99, 'negative': 100, 'mixed': 1}   smallest: 1
{
 "est": 0.8578214455361384,
 "ci_lo": null, "ci_hi": null, "ci_level": 0.95, "method": "none",
 "n_pos": 199, "n_neg": 201, "n_cases": 200,
 "flags": ["delong_refused_clustered", "very_low_precision"],
 "suppressed": false,
 "not_estimable_reason": "insufficient_clusters"
}
two mixed cases -> cluster_bootstrap_percentile  ci (0.8156, 0.8904)
```

Three separate problems in one Number:

1. **The headline AUROC of a 400-row study is refused** although 199 of 200 cases resample fine.
   Add a second mixed patient and it computes normally — an arbitrary cliff at exactly one.
2. `not_estimable_reason: "insufficient_clusters"` sits beside `n_cases: 200`. The stated reason is
   **false on its face** and unactionable: the customer cannot tell what to do about it.
3. `very_low_precision` is stamped on a 200-case cohort, because that flag is also driven by
   `resampler.smallest_stratum < LOW_PRECISION_UNITS` (`bootstrap.py:631`). A false precision
   warning in a regulatory pack.

The constant's own comment — *"Below two units in a stratum every resample is identical, there is
nothing to estimate. A mathematical floor, not a reporting convention"* — is true of a
**single-stratum** resampler and false when applied to `min` over three strata: the other 199 cases
still vary. The test covering this path (`test_fewer_than_two_cases_in_a_stratum_is_not_estimable`)
uses a 6-row cohort with one positive case, where refusing is right, so the cliff is invisible.

**Fix.** Apply the floor to the total resampling units, or to a stratum only when it is the sole
stratum; a singleton stratum should contribute deterministically (which is what the bootstrap
already does for it) rather than veto the cell. If a refusal is still wanted, the reason must be
truthful and `very_low_precision` must not be driven off a singleton stratum.

### B4 — `proportion_ci` accepts `cluster_ids` shorter than the cell and silently mixes three row sets into one Number

`clustered_by_case` validates alignment (`"cluster_ids must align with the positives mask"`,
`bootstrap.py:381`). `clustered_flat` — the resampler `proportion_ci` uses — does not.

`scratchpad/verify-E-safety/attack_align.py` — 160 rows / 40 cases:

```
correct                                      : 0.7333333333333333 (0.6333, 0.8333) n= 60
MISALIGNED (ids 160, indicator 60)           : raises IndexError index 72 is out of bounds for axis 0 with size 60
shorter ids than rows (ids 60, indicator 160): NO ERROR -> 0.7375 (0.6333, 0.8333) n= 160
auroc_ci with misaligned ids                 : raises ValueError cluster_ids must align with the positives mask
```

That third line is a Number built from three different row sets: `est = 0.7375` over all 160 rows,
the interval `(0.6333, 0.8333)` resampled from the first 60 rows only, and `n = 160`. No exception,
no flag. Day 5 slices per subgroup cell; this is the shape of mistake it will make.

**Fix.** The same length check `clustered_by_case` already has, in `clustered_flat` (or in
`proportion_ci` before it is called). Two lines and a regression test.

---

## 3. Attacks that did NOT break anything (the module held)

**`Number` invariant** (`attack_number.py`) — every ordinary route is closed:

```
[held] Number with no CI and no reason      : ValueError: Number has no confidence interval and no not_estimable_reason
[held] Number with half-open interval       : ValueError (same)
[held] Number CI + reason                   : ValueError: a Number with an interval must not carry a not_estimable_reason
[held] Number with unknown reason           : ValueError: unknown not_estimable_reason 'because_i_said_so'
[held] setattr ci_lo=None on a frozen Number: FrozenInstanceError: cannot assign to field 'ci_lo'
[held] dataclasses.replace stripping the CI : ValueError (the invariant re-runs in __post_init__)
```

`object.__setattr__` / `__dict__` do bypass `frozen` — that is Python, not a defect, and the JSON
schema catches the result (allOf #2: null `ci_lo` and not suppressed implies `method` must be
`"none"` and a typed reason is required). `flags` is a mutable list on a frozen dataclass and an
unknown flag *can* be appended after construction, but `output_schema_v1.json` rejects it
(`'model_is_safe_for_clinical_use' is not one of [...]`). Pre-existing; defence in depth intact.

**Getting a refused cell to render as a real number** — no. Refusals carry `ci_lo/ci_hi = null`,
`method = "none"` and a typed reason through `as_dict()` and a `json.dumps` round trip. The point
estimate survives beside the refusal by design and is asserted by a test.

**`--offline` makes zero network calls** — proved rather than assumed. A `sitecustomize.py`
replacing `socket.socket`, `create_connection`, `getaddrinfo`, `gethostbyname`, `socketpair` and
`ssl.SSLContext.wrap_socket` with a raising stub, injected via `PYTHONPATH`:

```
$ PYTHONPATH=<scratch>/noNet python -m proofpack.cli doctor --offline
  [ok  ] network   skipped (--offline)      All essential checks passed.   EXIT=0
$ PYTHONPATH=<scratch>/noNet python -m pytest -q -p no:cacheprovider
  213 passed, 1 skipped, 1 xfailed in 21.94s
```

The blocker itself is live (`socket.getaddrinfo('example.com', 80)` raises `NetworkBlocked`).
Doctor *without* `--offline` reports "network: not attempted — no outbound call exists yet", so the
engine has no network path at all today.

**No scipy under `src/proofpack`; `import proofpack` works without it** — blocked `scipy` with a
raising `sys.meta_path` finder:

```
F3 interval without scipy: (0.44, 1.0)
clustered cell without scipy: cluster_bootstrap_percentile 0.44 1.0
scipy in sys.modules: False
(control) import scipy -> blocked -> scipy blocked by verifier: scipy
```

The only `scipy` reference under `src/` is the lazy, documented import inside Clopper-Pearson
(`proportions.py:128`), which already carries the typed reason `scipy_unavailable`.

**Cross-process reproducibility** — the same clustered cell under `PYTHONHASHSEED` 0, 1, 12345 and
`random` gives byte-identical JSON. Confirmed independently of the repo's own subprocess test.

**Nothing added today sets an acceptance criterion, a margin or a verdict** —
`grep -niE "verdict|pass(ed|es)|fail(ed|s)|acceptab|adequate|satisfactor|good|meets|compliant|safe"`
over `bootstrap.py` returns nothing. The new constants (B, seed, `SMALL_CLASS`,
`MIN_UNITS_PER_STRATUM`, `MIN_USABLE_FRACTION`, `LOW_PRECISION_UNITS`) are method parameters, not
thresholds on model performance. No `criteria.yaml` field is authored or defaulted by the engine
beyond the declared/defaulted provenance the policy already records.

**The `[unverified]` guard is not vacuous** — checked three ways (section 5).

---

## 4. Mutation testing — 19 mutations, 16 caught, 3 survived

Run in a detached `git worktree` with `PYTHONPATH=<worktree>/src` (shadowing verified: the imported
module resolved to the worktree copy) and `-p no:cacheprovider -m day4`.

| # | Mutation | Result |
|---|---|---|
| M1 | `MIN_UNITS_PER_STRATUM` 2 -> 1 | **caught** (1 failed) |
| M2 | `MIN_USABLE_FRACTION` 0.90 -> 0.0 | **caught** (1 failed) |
| M3 | `DEFAULT_B` 2000 -> 500 | **caught** (6 failed) |
| M4 | `DEFAULT_SEED` 20240101 -> 20240102 | **SURVIVED** (85 passed) — N3 |
| M5 | `LOW_PRECISION_UNITS` 10 -> 0 | **SURVIVED** (85 passed) — N3 |
| M6 | `rng.integers(0,m,m)` -> `m-1` (drop a unit per stratum) | **caught** (10 failed) |
| M7 | clustered draw resamples rows, not cases | **caught** (13 failed) |
| M8 | mixed cases folded into the positive stratum | **caught** (1 failed) |
| M9 | percentile `alpha/2` -> `alpha` | **caught** (4 failed) |
| M10 | `min(n_pos,n_neg) >= SMALL_CLASS` -> `>` | **caught** (1 failed) |
| M11 | drop the `delong_refused_clustered` flag | **caught** (1 failed) |
| M12 | drop the `wilson_refused_clustered` flag | **caught** (1 failed) |
| M13 | detection `units < n_rows` -> `units*2 < n_rows` | **SURVIVED — 213 passed** -> **B2** |
| M14 | suppress the `W13` finding on the detected route | **caught** (1 failed) |
| M15 | `cell_entropy` uses the process-salted builtin `hash()` | **caught** (2 failed) |
| M16 | typed reason swapped to `not_computed_this_run` | **caught** (5 failed) |
| M17 | a refused draw renders a fabricated +/-0.05 interval | **caught** (2 failed) |
| M18 | drop the companion `analytic` Number (`analytic=None`) | **caught** (5 failed) |
| M19 | clustered AUROC quietly takes DeLong (`if False:`) | **caught** (7 failed) |

M6/M7/M9 are the resampler's core and are well covered. M11/M12/M14/M16–M19 show that the refusal
machinery itself is genuinely tested, not merely asserted in prose.

---

## 5. `[unverified]` markings

The guard (`tests/test_invariants.py`) is **not vacuous** — I broke it twice and it fired:

```
U2: an unmarked Newcombe interval in a NEW src file with no [unverified] anywhere
    -> FAILED tests/test_invariants.py::test_no_source_or_template_emits_an_unverified_value_unmarked
U3: "[unverified" -> "[verified" in fixtures/newcombe_table2.json
    -> 2 failed (the self-test and the repo sweep)
```

But it is **file-scoped, not value-scoped** — `unmarked_unverified_values` returns `[]` if
`"[unverified"` appears anywhere in the file:

```
U1: the SAME unmarked renderer appended to src/proofpack/stats/bootstrap.py
    -> 8 passed        # bootstrap.py already contains an [unverified] Efron & Tibshirani citation
```

Today's commit added the third such exemption (`git grep -l "\[unverified" -- src/`:
`discrimination.py` and `proportions.py` at HEAD~1; `bootstrap.py` as well at HEAD). Nothing leaks
today because no renderer exists — but the guard's stated purpose is to "fire the moment a real
renderer lands (day 5+)", and three stats modules are now blind to it. Non-blocking (N2), but fix
it before any rendering code goes near `src/proofpack/stats/`.

---

## 6. Non-blocking findings

**N1 — a wrong typed reason: `insufficient_positives` when it is the negatives that are short.**
`bootstrap_percentile` (`bootstrap.py:457–461`) picks the reason from `resampler.kind`, not from
which stratum is short; `stratified_by_outcome` labels both strata but `smallest_stratum` throws
the label away. `insufficient_negatives` is in the enum and is emitted by no code path.

```
n_pos=20 n_neg=1 -> reason: insufficient_positives     (the negative stratum is the short one)
n_pos=1  n_neg=20 -> reason: insufficient_positives
```

Reachable through `auroc_ci` on any i.i.d. cell with one class of size 1. The refusal is correct;
only the stated reason is false — but the customer's remedial action ("collect more positives")
would be the wrong one, and `n_pos: 20, n_neg: 1, insufficient_positives` is self-contradictory on
the page. Highest-priority non-blocker.

**N2 — the `[unverified]` guard is file-scoped.** See section 5. Fix: match per line or per
paragraph, or exclude module docstrings from the exemption.

**N3 — `DEFAULT_SEED` and `LOW_PRECISION_UNITS` are pinned by no test** (M4, M5 survived). Changing
the engine's default seed silently changes every customer's intervals between releases, and
reproducibility of a pack against a re-run is part of what is sold; the F3 pin test hardcodes
`default_rng(20240101)` in the test rather than referencing `DEFAULT_SEED`, so the constant is
untied. `LOW_PRECISION_UNITS` -> 0 deletes the `very_low_precision` flag from every clustered cell
with no test noticing.

**N4 — a declared negative seed passes the criteria schema and crashes numpy mid-run.**
`criteria_schema.json` has `"seed": {"type": "integer"}` with no `minimum`. `{"seed": -1}`
validates, `BootstrapPolicy` accepts it, and the first cell raises the raw
`ValueError: expected non-negative integer` from `default_rng`. Add `"minimum": 0`, or validate in
`BootstrapPolicy.__post_init__` the way `interval` already is.

**N5 — B far below the documented minimum is accepted silently.** The module docstring and R2 §1.5
require B >= 1000; `criteria_schema.json` allows `"minimum": 1`. On F3:

```
B=   2  -> bootstrap_percentile  ci=(0.607, 0.873)     # 4x too narrow
B=2000  -> bootstrap_percentile  ci=(0.480, 1.000)
```

No flag, no reason — the only signal is `B: 2` in the manifest, which is why this is not a blocker.
Set the schema minimum to 1000, or flag a below-minimum B.

**N6 — up to 10 % of resamples can be dropped and the interval formed from the survivors, with no
flag on the Number.** With 7.7 % degenerate draws: `reason=None ci=(0.0, 0.857) usable=1847/2000`.
The percentile interval is then taken from a distribution conditioned on non-degeneracy, which is
biased, and the rendered `Number` says only `bootstrap_percentile`.
`CellCI.bootstrap.usable_resamples` records the count, so it is discoverable in the JSON but not on
the number itself. This also makes `MIN_USABLE_FRACTION = 0.90` (open question 5 in the note)
load-bearing: it is the line between "biased interval, unflagged" and "typed refusal".

**N7 — a clustered proportion carries no `n_cases`.** 20 patients x 8 rows gives
`{"est": 0.75, "n": 160, "k": 120, "method": "cluster_bootstrap_percentile", ...}`. A subgroup table
prints `n = 160` for a sensitivity whose effective sample size is 20. D1 §4.1 requires `n_cases`
only for AUROC, so this is a design gap rather than a spec breach — but `auroc_ci` already
populates it and `proportion_ci` should too, before day 5 prints denominators.

**N8 — the X2 refusal is enforced only in the routing wrapper, not at the analytic primitives.**
`discrimination.auroc_number` and `proportions.proportion` are public and return unguarded
intervals on clustered rows:

```
day-3 auroc_number on 50 clustered rows: delong_logit 0.6483 0.8967 []
day-2 proportion   on 50 clustered rows: wilson       0.4618 0.7239 ['imprecise']
```

Correct in isolation, but nothing stops `stats.subgroups` calling them directly on day 5 and
bypassing X2 entirely. Worth an AST test on day 5 asserting the subgroup module reaches AUROC and
proportions only through `bootstrap.auroc_ci` / `bootstrap.proportion_ci`.

**N9 — `BootstrapPolicy.as_dict()` records B, seed and interval but not the thresholds that decide
whether a cell is estimable** (`MIN_UNITS_PER_STRATUM`, `MIN_USABLE_FRACTION`,
`LOW_PRECISION_UNITS`, `SMALL_CLASS`). T7 is required to state "the methods actually used"; these
are engine constants a reviewer cannot see. Cheap to add to the manifest block.

---

## 7. On the note's own honesty

The §2(b) treatment of F3 is the most careful thing in this repo so far: the tolerance is derived
before measuring, the claim is explicitly asserted *not* to generalise, and
`test_the_endpoint_tolerance_is_not_claimed_beyond_f3` encodes the failure so it cannot be quietly
widened later. §2(c)'s variance claim is the right one to lean on, and my independent re-derivation
supports it. I found no overstatement anywhere in the note. The defects above are things the note
does not know about, not things it papers over.

Caveat repeated from the note and confirmed: **CI has still never executed** — nothing pushed. The
scipy-free job's new F3 assertion is correct (I ran the equivalent locally, section 3), but the
wheel job remains unexercised.

---

## 8. Repair order

1. **B1** and **B4** together — the guards `auroc_ci` / `clustered_by_case` already have, applied to
   the `plan is None` case and to `clustered_flat`. Two regression tests.
2. **B2** — the detection test at 1, 2 and 10 duplicated ids out of 100. It must fail against
   `units * 2 < ids.shape[0]`.
3. **B3** — the singleton-stratum floor, plus the truthful reason and the `very_low_precision`
   source. Regression test: 200 cases, exactly one mixed, asserting the interval exists.
4. **N1** while in `bootstrap_percentile` — pick the reason from the short stratum's label.

Scratch scripts for every attack above are in
`.../scratchpad/verify-E-safety/` (`attack_plan_omitted.py`, `attack_detect.py`,
`attack_singleton_mixed.py`, `attack_number.py`, `attack_align.py`, `attack_policy.py`,
`attack_b.py`, `attack_degen.py`, `independent_f3_f9.py`, `mutate.sh`, `noNet/`, `noScipy/`).
