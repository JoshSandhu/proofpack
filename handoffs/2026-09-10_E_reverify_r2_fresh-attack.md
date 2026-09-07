# Re-verify (repair round 2) — 2026-09-10 — Lane E — **FRESH-ATTACK LENS**

Repo `proofpack`, commit under attack `e87843d` ("fix E: the clustered class floor and
the AUROC precision tier"), pre-repair `5b92fc5`, original build `5bc69fb`.

**Verdict: FAIL — 2 blockers.**

The round-2 repair does what the round-1 fresh-attack lens asked, and it does it well:
every claim in the repair note that I could check is true, all ten new regression tests
genuinely fail against `5b92fc5`, fifteen mutations of the repaired lines are all caught,
and no pinned number moved. It is nevertheless not finished. **FA-B1's remedy was
prescribed as `max(pure_units, mixed_units) >= 2` and implemented exactly as prescribed,
but the prescription is narrower than the defect.** A class does not have to be *totally*
frozen to be under-resampled: a singleton stratum contributes the same rows to every
resample whether or not the other strata vary, and when it carries most of the class's
rows the interval is still far too narrow. Measured on a deterministic cohort the engine
now renders `AUROC 0.735 (0.622, 0.847)` where an independently written pooled cluster
bootstrap gives `(0.397, 0.860)` — **2.1x too narrow**, coverage 0.34–0.62 against a
nominal 0.95 over 250 replications — and `5bc69fb` refused that cell outright.

---

## 1. What I re-ran, and what held

Everything below was run by me on `e87843d`, not read from a note.

| Attack | Result |
|---|---|
| Full suite | `243 passed, 1 skipped, 1 xfailed` — matches the repair claim |
| Per-day markers | day1 59+1s, day2 40, day3 29+1x, day4 **115** — matches |
| `ruff check .` / `format --check src tests` | clean / `24 files already formatted` |
| **F3 re-derived from scratch** (my own Mann–Whitney double loop, my own stratified resampler, nothing imported from `proofpack`) | `(0.44, 1.0)`, resample sd `0.14842279023900326` |
| **DeLong SE re-derived** from the V10/V01 structural components | `0.15491933384829668` |
| Same three with `scipy` blocked at `__import__` | identical; `scipy` never in `sys.modules` |
| `doctor --offline` with `socket.socket` replaced by a raising stub | exit 0, zero network calls |
| X2 symmetry: ids with no plan / plan asserting independence over repeating ids / clustered plan with no ids / declared unit with no column / misaligned `clustered_flat` | all route clustered or raise, correctly |
| `Number` frozen; `Number(est=...)` with no CI and no reason | `FrozenInstanceError` / `ValueError` |
| Invariant sweep, 248 routed cells across 125 cluster structures x declared/detected | every Number has a CI or a typed reason; every one validates against `schema/output_schema_v1.json`; no Number ever carries two precision tiers |
| Declared vs detected, **same cell key** | byte-identical Numbers, only `route` differs |
| Cross-process determinism | identical JSON under `PYTHONHASHSEED=1` and `=987654` |
| `[unverified]` paragraph guard | appending the real F14 values `0.0524 to 0.3339` to `bootstrap.py` fails `test_no_source_or_template_emits_an_unverified_value_unmarked` |
| The ten new regression tests against `5b92fc5` (HEAD tests copied into a detached worktree, `PYTHONPATH` shadowing confirmed) | `10 failed, 105 passed` — exactly the failures the repair claims |
| Test-file diff `5b92fc5 -> e87843d` | `224 insertions, 0 deletions`; no `skip`, no `xfail`, no assertion changed. The repair's "changed no existing assertion and deleted no test" is true |
| The "one token in a lens note" claim | true — line 34 of the regression note is a `text` fence and the quoted fragment `*precision_flags(n_pos + n_neg, min(n_pos, n_neg)),` is byte-identical |
| 2,640-cell behavioural sweep at `5b92fc5` and `e87843d`, diffed | **0 point estimates moved, 0 surviving intervals moved, 0 precision tiers lost, 133 gained**, 32 cells return to `insufficient_clusters`, 12 move `boundary_estimate -> insufficient_clusters`. The repair's counts differ only because its grid differs |
| Same sweep at `5bc69fb` vs `e87843d` | 248 AUROC cells lose a tier — I checked every one: all have both classes >= 10 units **and** >= 30 cases, so all 248 are the intended correction of the old `smallest_stratum` tier, not a loss |

**Mutation testing — fifteen mutations, all fifteen caught.** In a detached worktree at
`e87843d` with `PYTHONPATH` shadowing the editable install:

```
M1  deficient_class max -> sum   (revert R2-D1)                2 failed
M2  clustered tier reads positives only (revert R2-D2)         8 failed
M3  drop the 5..9 scarce-class clause                          6 failed
M4  mixed counts towards neither class (FA-B3's mutation R7)   3 failed
M5  deficient_class max -> min   (pre-round-1 floor)          64 failed
M6  auroc_precision_flags min -> max                           8 failed
M7  i.i.d. route back to precision_flags(min(n_pos,n_neg))     1 failed
M8  _resolved ignores cluster_ids when plan is None (D1)       1 failed
M9  n_cases from the run plan, not the cell (D5)               1 failed
M10 refusal always names positives (D3)                        1 failed
M11 clustered_flat drops its alignment check (D7)              1 failed
M13 MIN_UNITS_PER_STRATUM = 1                                  5 failed
M14 LOW_PRECISION_UNITS = 5                                    9 failed
M15 DEFAULT_SEED = 20240102                                    1 failed
M16 unmarked F14 Newcombe values appended to bootstrap.py      1 failed
```

**A new attack the earlier lenses did not run, which found nothing — worth recording.**
For every cluster structure `(pure_pos, pure_neg, mixed)` with each count in 0..3 I built
a real cohort, asked the engine for the cell, and *independently measured* whether each
outcome class varies across resamples (distinct multisets of that class's row indices over
400 draws, using my own resampler written from the documented scheme). **0 under-refusals
and 0 over-refusals across 57 structures.** Against total freezing, the R2-D1 fix is
exactly right.

---

## 2. BLOCKERS

### FA2-B1 — a class dominated by a **frozen** stratum still renders an interval, 2.1x too narrow, and the original build refused it

`src/proofpack/stats/bootstrap.py:476` (`Resampler.deficient_class`) refuses a class only
when the **largest** stratum supplying it is below `MIN_UNITS_PER_STRATUM`. That closes the
shape FA-B1 named. It does not close the mechanism FA-B1 *described*, which the property's
own docstring states two lines above:

> "Each stratum is drawn independently, `m` units from `m`; a stratum holding a single
> unit therefore contributes *that unit* to every resample."

That is true regardless of what the other strata do. One pure-positive patient with five
malignant lesions is a singleton stratum: its five rows are in every one of the 2000
resamples. Add two mixed patients and `max(1, 2) = 2` clears the floor, while 71 % of the
positive rows are frozen.

**Deterministic repro** (`repro_frozen.py`; one patient with 5 malignant lesions, two
patients with one malignant and one benign lesion, forty patients with one benign lesion —
43 patients, 49 lesions, `--offline`, no misuse, no forgotten argument):

```
units_per_stratum: {'positive': 1, 'negative': 40, 'mixed': 2}
class_strata     : {'positive': (1, 2), 'negative': (40, 2)}
deficient_class  : None

rendered: est 0.7347  ci (0.6224, 0.8469)  width 0.2245
          method cluster_bootstrap_percentile
          flags ['delong_refused_clustered', 'very_low_precision', 'imprecise']  n_cases 43

positive rows present in EVERY resample: 5 of 7 (71%)
oracle pooled cluster bootstrap (mine, resamples all 43 cases): (0.3971, 0.8602) width 0.4631
engine interval is 2.1x narrower than the oracle

same cohort at 5bc69fb: REFUSED, insufficient_clusters
```

**Coverage, measured not argued.** Fixed case composition, case-level effect variance
rho = 0.6 plus per-row noise so the marginals are N(1,1) and N(0,1) and the true
lesion-level AUROC is Phi(1/sqrt2) = 0.760250. 250–300 replications, B = 400, MC se ~ 0.03:

```
shape (pure-pos lesions L, mixed m, 40 negatives)  engine cov  width | oracle cov  width  tier
L= 1  m= 2                                             0.618  0.2793 |    0.775  0.4475  very_low_precision
L= 5  m= 2                                             0.440  0.1844 |    0.812  0.4332  very_low_precision
L= 5  m= 3                                             0.564  0.2025 |    0.892  0.4466  very_low_precision
L=20  m= 2                                             0.336  0.1476 |    0.836  0.4234  very_low_precision
L=20  m= 3                                             0.392  0.1513 |    0.896  0.4516  very_low_precision
L=20  m=10                                             0.412  0.1478 |    0.928  0.3051  ** NO TIER **
L= 1  m= 1  (the FA-B1 shape)                       refused, insufficient_clusters  (correct)
```

The last row is the worst of it: at `L=20, m=10` the cell has 11 positive class units and
51 cases, so it clears both `LOW_PRECISION_UNITS` and `VERY_LOW_PRECISION_UNITS` and carries
**no precision tier at all** — only `imprecise` on some draws — while covering the truth
41 % of the time at a nominal 95 %. That is worse than the FA-B1 evidence the repair note
calls "the one that matters" (0.233 with `very_low_precision`).

**It is not small-n; it is the frozen stratum.** Matched controls, the same 12 positive
rows across the same three positive-supplying units, run in the same script:

```
A frozen  1 pure-pos case of 10 lesions + 2 mixed + 40 neg : coverage 0.390  width 0.1635
B control 3 pure-pos cases (10, 1, 1 lesions) + 40 neg     : coverage 0.813  width 0.4051
                                                             oracle 0.839  width 0.4462
```

Remove the freeze and coverage goes 0.390 -> 0.813 while the width lands on the oracle.

**Why this is a blocker and not a small-sample caveat.** `5bc69fb` refused every one of
these cells (`min` over strata = 1). Round 1 made them render; round 2 was chartered to
close exactly that regression and closed only its endpoint. The output is a confidence
interval in a pack a customer hands to a regulator, on the multi-lesion design the `mixed`
stratum exists for, with an annotation that reads "treat with care" at best and nothing at
worst.

**Exposure.** In my 2,640-cell sweep, 108 of the 1,156 rendered AUROC cells have at least a
third of a class's rows in a frozen singleton stratum. The untiered variant needs a case
carrying many same-class rows, so it is rarer than the tiered one — but the tiered one (one
patient with a handful of same-class lesions plus two or three mixed patients) is an
ordinary subgroup row.

**Suggested fix.** Keep `max(...) >= MIN_UNITS_PER_STRATUM` and add the quantitative half
the mechanism implies: compute, per class, the share of the class's **rows** that sit in
strata of a single unit, and refuse with `insufficient_clusters` when that share exceeds a
declared constant — a third is where my measurements turn bad — with the constant recorded
in `BootstrapPolicy.as_dict()["thresholds"]` beside the others. Compatible with both
existing regression fixtures: the round-1 D2 cohort (199 pure + 1 mixed) has a frozen share
of 1/399, and `test_a_mixed_outcome_case_counts_towards_both_classes` (40 all-mixed cases)
has no singleton stratum at all. The regression test wants the shape above, and it should
*measure* the frozen row share rather than assert it, for the same reason the R2-D1 test
measures its zero-variability property.

**Why the existing test cannot see it.**
`test_a_class_whose_every_stratum_is_a_singleton_is_refused` asserts `len(seen) == 1` over
200 draws — total freezing. Partial freezing gives `len(seen) > 1` and passes.

### FA2-B2 — the rendered manifest and the `NOT_ESTIMABLE_REASONS` documentation both still describe the round-1 rule that round 2 deleted

Round 2 changed the refusal criterion from a count over the class to a test on the largest
stratum supplying it. Two shipped artefacts were not brought with it.

**(a) The manifest.** `BootstrapPolicy.as_dict()["thresholds"]["min_units_per_class"]`
(`bootstrap.py:284`) is emitted into every `CellCI.as_dict()`, and its own docstring says
why it exists: *"a reviewer cannot check the refusals without seeing them."* After round 2
a reviewer still cannot, and worse, the manifest contradicts the refusal. Actual engine
output, one cell, 202 patients, one pure-positive and one mixed:

```
"not_estimable_reason": "insufficient_clusters",
"n_pos": 2, "n_neg": 201, "n_cases": 202,
"thresholds": { "min_units_per_class": 2, ... }
```

`Resampler.class_units` for that cell is `{'positive': 2, 'negative': 201}`. The pack states
a threshold of two units per class, the class has two, 202 clusters are reported, and the
cell is refused for "insufficient clusters". Nothing in the output names the quantity that
actually decided it (`max(class_strata['positive']) = 1`). This is the shape of round-1
defect D3, whose stated principle was that `insufficient_positives` beside `n_pos: 199`
"would be the same lie"; here it is `insufficient_clusters` beside `n_cases: 202`.

**(b) The enum comment.** `src/proofpack/stats/number.py:78-81` still reads:

> `insufficient_clusters` — "fewer than two independent cases supplying an outcome class.
> **Counted over the cell: a case carrying both outcomes counts towards both, so one mixed
> multi-lesion patient is not a shortage.**"

Under `e87843d` one mixed patient plus one pure patient *is* a shortage — that is R2-D1.
The typed reason's own definition is now false, in the module CLAUDE.md points at for "an
explicit documented reason why a CI is unavailable".

**Suggested fix.** Rename the manifest key to what the rule measures (e.g.
`min_units_per_class_stratum`), emit the deciding quantity so a reviewer can check the
refusal, and rewrite the `number.py` comment to the round-2 rule. No behaviour change;
about fifteen lines. If FA2-B1 is fixed as suggested, the new frozen-share constant lands
in the same block and the comment can be written once.

---

## 3. Non-blocking

**FA2-N1 — `auroc_precision_flags` gives the *less severe* tier for the condition R2 §3.3
calls not evaluable.** R2 §3.3 line 94 is *"AUROC per group requires >=10 positives **and**
>=10 negatives, else omit with reason."* `bootstrap.py:205-208` gives a class below ten
`very_low_precision`, and the docstring says that is deliberate ("stays at *very low
precision* rather than escalating"). But round-1 acceptance-lens N1 was accepted on exactly
this argument in the other dimension — *"the tier was the less severe of the two:
`very_low_precision` below n = 10 where R2 §3.3 says
`not_evaluable_shown_for_transparency`"* — and the repair note's own justification for
R2-D2 quotes line 94 as the reason the tier must read both classes. One rule, two
severities, depending on which count is short. Day 5 has to settle the tiers anyway (verify
note §7 open question 5); settle this with them.

**FA2-N2 — `Resampler.smallest_stratum` is now referenced by nothing** in `src` or `tests`
(grep finds only its own definition). It is a public property on a public frozen dataclass
whose docstring warns that using it was the defect. Dead, untested code naming the wrong
quantity is a trap for day 5. Delete it, or keep it and pin it.

**FA2-N3 — the sweep sentence in the consolidated note is scoped, but reads absolute.** §2
ends *"No precision tier is lost anywhere."* True of the `5b92fc5 -> e87843d` sweep it sits
under. Against the original build, 248 AUROC cells lose a tier. **I checked all 248 and
every one is justified** (both classes >= 10 units and >= 30 cases — the old
`smallest_stratum` tier was the defect round 1 fixed), so the behaviour is right. But §5 of
that same note exists to correct a previously-false absolute claim of identical shape ("No
gate loosened"), so this wording deserves its scope stated.

**FA2-N4 — one decision the engine is currently taking on the customer's behalf is not in
needs-from-Josh.** R2 §3.3 line 94 says an AUROC per group below ten in a class should be
*omitted with reason*; the engine renders it and annotates instead, on the strength of line
93's "suppress nothing; annotate". Both readings are defensible and they are in tension in
R2 itself — which makes it a presentation decision about what appears in a customer's pack,
not an engineering one. It is not listed. One sentence from Josh, and day 5's subgroup
table inherits it along with the tier rule.

**FA2-N5 — CI has still never executed**, nothing has been pushed, and the wheel job
remains unexercised locally (no `hatchling`, no `build`, no `uv` on this machine). Carried
by every lens since day 1; recorded again so the number of days it has been true stays
visible.

**FA2-N6 — housekeeping claims check out.** `git worktree list` showed two registrations
(`reverify-E-regression-r2/wt-mut`, `wt-pre`) while I worked; they belong to the concurrent
round-2 regression lens and both cleared themselves, so the repair's "no worktrees left
registered" was accurate. `ruff format --check .` now reports 39 rather than the note's 38,
for the reason acceptance-N6 gave: ruff 0.16 formats Markdown, so the count rises with
every handoff note written. Quote `--check src tests` (24), never the bare count.

---

## 4. Is the consolidated `_verify.md` an honest record?

**Yes, with the one scoping wrinkle at FA2-N3.** I checked it finding by finding.

- Every blocker and every non-blocking observation raised by the two round-2 lenses is
  present. FA-B1/B2/B3 -> R2-D1/D2/D3; FA-N1 through FA-N8 and FA-N10 are named; FA-N9 (CI
  has never executed) and FA-N11 (too many open decisions) are carried in substance rather
  than by id — and FA-N11 is answered by the new "**Answer 1 and 2 — the rest can wait**"
  line in §6, which is the right response to it. Regression-lens N1–N5 are all recorded.
- **Nothing is described as fixed that was deferred.** R2-D3 and FA-N2 are stated plainly as
  missing-test defects with no code change, and I confirmed both by mutation: `mixed = 0`
  fails 3 tests at HEAD, and it survived all 102 at `5b92fc5`.
- The two corrections in §5 ("a class supplied by fewer than two independent units still
  refuses" and "No gate loosened" were both false) are the kind of record that makes the
  rest of the note trustworthy. They are correct, and correcting rather than editing them
  is the right call.
- The claim "no point estimate and no surviving interval has moved at any point in either
  round" reproduces on my own independent grid: 0 and 0 in both directions.

The one thing the note cannot know, and therefore does not say, is that its central fix is
partial. §2's summary — *"The floor now asks whether the resampler can actually vary the
class, not how many units it can count"* — is the claim FA2-B1 falsifies: the floor asks
whether the resampler can vary the class **at all**, and a class it can barely vary passes.

## 5. Are the needs-from-Josh complete and actionable?

**Nearly.** Five items, correctly triaged, each answerable in one sentence, none of them
new, none needing spend, an account or a secret. The two live ones (day-2 §6 Q1 on F1/MCC;
day-3 §6 Q3 on R2 §1.3 with the 0.923-against-0.978 coverage measurement attached) are
stated with the evidence a ten-hour-a-week reviewer needs to answer them without opening
the code, which is the standard to aim at. Item 5 — should a repair that touches a
statistical gate be verified as adversarially as a build — is worth answering **yes** on the
strength of this round alone: FA2-B1 exists because the repair of a repair was attacked
again, and every check was green.

Two gaps:

1. **FA2-N4** — the "annotate rather than omit" reading of R2 §3.3 line 94 is a decision
   about a customer's pack that the code has taken silently. Add it.
2. Neither blocker above is a decision for Josh; both are repair-round-3 code work. Say so
   explicitly in the next note, so the list stays a decision list.

---

## 6. Commands

```
cd C:/Users/joshs/GPS/ProofPack/proofpack
python -m pytest -q -p no:cacheprovider                 # 243 passed, 1 skipped, 1 xfailed
python -m pytest -q -p no:cacheprovider -m day4         # 115 passed
python -m ruff check . && python -m ruff format --check src tests
python -m proofpack.cli doctor --offline                # exit 0
```

FA2-B1 reproduces from the repo with numpy alone:

```text
import numpy as np
from proofpack.stats.bootstrap import auroc_ci, BootstrapPolicy, clustered_by_case
rng = np.random.default_rng(20260910)
S, Y, C = [], [], []
u = rng.normal(0, 0.775)
for _ in range(5):                       # one patient, five malignant lesions
    S.append(1 + u + rng.normal(0, 0.632)); Y.append(True);  C.append(0)
for c in (1, 2):                         # two patients, one malignant + one benign
    u = rng.normal(0, 0.775)
    S.append(1 + u + rng.normal(0, 0.632)); Y.append(True);  C.append(c)
    S.append(0 + u + rng.normal(0, 0.632)); Y.append(False); C.append(c)
for c in range(3, 43):                   # forty patients, one benign lesion
    u = rng.normal(0, 0.775)
    S.append(0 + u + rng.normal(0, 0.632)); Y.append(False); C.append(c)
S, Y, C = np.array(S), np.array(Y, bool), np.array(C)
print(clustered_by_case(Y, C).deficient_class)          # None  <- should refuse
n = auroc_ci(S, Y, cell_key="k", policy=BootstrapPolicy(n_resamples=2000), cluster_ids=C).number
print(n.est, (n.ci_lo, n.ci_hi), n.flags)               # 0.7347 (0.6224, 0.8469) very_low_precision
```

Scratch work — the independent F3/DeLong derivation, the exhaustive structure audit, the
coverage and control scripts, the three-commit sweep and its diff — is in
`C:/Users/joshs/AppData/Local/Temp/claude/C--Users-joshs-GPS-ProofPack/0a05ffb0-bd0c-4d5d-b08b-44493ddbbc8f/scratchpad/reverify-E-fresh-attack-r2/`
(`indep.py`, `attack_floor.py`, `attack_frozen.py`, `attack_frozen_control.py`,
`attack_frozen_map.py`, `repro_frozen.py`, `attack_safety.py`, `attack_truthfulness.py`,
`sweep.py`, `diff.py`, `analyse.py`). Every one imports only `numpy`, `jsonschema` and
`proofpack`, so they can be rewritten from the tables above if the temp directory is gone.
The three worktrees I created are removed and the main tree is clean; I committed nothing
and pushed nothing.
