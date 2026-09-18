"""Build day 6: the day-5 handoff's carried items 16-19, closed with observers.

Marked ``day6`` (not ``day5``) so the day-5 marker's count stays what the day-5 handoff
records (54). Each test names the mutant it kills, from the day-5 note's table A.

* **16** - the rendered two-sided cluster-bootstrap interval had no oracle: both
  ``values_a - values_b.mean()`` and ``values_a.mean() - values_b`` survived the full
  suite. Closed two ways: (a) an independent two-sided bootstrap written here from the
  public output's cell key, resampling each side's cases with the module's resampler and
  generator and subtracting **per resample** in this test, must reproduce the rendered
  bounds bit for bit; (b) the same recomputation from the index vectors a recording
  resampler saw ``_bootstrap_difference`` draw.
* **17** - no test ran any bootstrap at a level other than 0.95. Two tests: the 0.90
  interval of a cluster-bootstrapped cell must be strictly narrower than its 0.95
  interval and carry ``ci_level: 0.9`` (``test_item17_...``: kills
  ``percentile_bounds(usable, DEFAULT_LEVEL)`` in ``bootstrap.bootstrap_percentile``,
  and for the differences it asserts containment only, which the regression lens of
  2026-09-18 (RG-N1) showed does not observe the two sites in
  ``subgroups._bootstrap_difference``); ``test_item17b_...`` feeds
  ``_bootstrap_difference`` itself two scripted resamplers at level 0.90 and asserts the
  bounds are the 0.05 / 0.95 quantiles of the recorded differences (kills
  ``percentile_bounds(usable, DEFAULT_LEVEL)`` at that site) and that a side whose draws
  are 96 % one value is frozen at 0.90 and not at 0.95 (kills
  ``_frozen_sides(..., DEFAULT_LEVEL)``).
* **18** - the reported counts on a clustered difference: ``n = min(n1, n2)`` as the
  i.i.d. route reports, and ``resample_sd`` is the ``ddof=1`` standard deviation of the
  recorded difference draws.
* **19** - ``_frozen_sides`` at the interval's own level: an 80/20 two-valued side is
  *not* frozen at 0.95 (its 2.5 and 97.5 percentiles differ) where a 25/75 rule would
  call it frozen (kills ``percentile_bounds(finite, 0.5)``).
"""

from __future__ import annotations

import numpy as np
import pytest

from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.stats import subgroups as subgroups_module
from proofpack.stats.bootstrap import BootstrapPolicy, clustered_flat
from proofpack.stats.subgroups import subgroup_analysis
from test_subgroups import _RecordingResampler, clustered_pair

pytestmark = pytest.mark.day6

POLICY = BootstrapPolicy(n_resamples=200, seed=20240101)


def _sides(cols, level_label: str, ref_label: str):
    """Row indices (in analysed-row order), indicators and case ids of the two sides of
    the sensitivity difference ``level - reference`` on the ``sex`` attribute."""
    y = np.array([v == "1" for v in cols["y_true"]], dtype=bool)
    pred = np.array(cols["score"], dtype=float) >= 0.5
    sex = np.array(cols["sex"])
    ids = np.array(cols["case_id"], dtype=object)
    rows_a = np.flatnonzero((sex == level_label) & y)
    rows_b = np.flatnonzero((sex == ref_label) & y)
    return pred[rows_a], ids[rows_a], pred[rows_b], ids[rows_b]


def _run(cols, crit, level: float = 0.95):
    decl = validate_dict(crit)
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, _ = schema_mod.analysis_mask(table, decl.indeterminate_values)
    assert bool(mask.all())  # every row analysed, so analysed-row order is column order
    return subgroup_analysis(table, decl, mask, policy=POLICY, level=level), decl


def test_item16_the_rendered_two_sided_interval_is_the_percentile_of_per_resample_differences():
    cols, crit = clustered_pair(span=False)
    rep, decl = _run(cols, crit)
    row = rep.row("sex", "F")
    se_key = "sensitivity"
    cell = row["diff_vs_reference"]["op1"][se_key]
    assert cell["number"]["method"] == "cluster_bootstrap_percentile"
    ind_a, ids_a, ind_b, ids_b = _sides(cols, "F", "M")
    assert cell["number"]["n"] == min(ind_a.shape[0], ind_b.shape[0])
    # (a) independent two-sided bootstrap from the cell key: a then b, one draw each
    res_a = clustered_flat(ids_a, n_rows=ind_a.shape[0])
    res_b = clustered_flat(ids_b, n_rows=ind_b.shape[0])
    rng = POLICY.rng(cell["bootstrap"]["cell_key"])
    diffs = np.empty(POLICY.n_resamples)
    for b in range(POLICY.n_resamples):
        va = float(ind_a[res_a.draw(rng)].mean())
        vb = float(ind_b[res_b.draw(rng)].mean())
        diffs[b] = va - vb
    lo, hi = np.quantile(diffs, [0.025, 0.975])
    assert cell["number"]["ci_lo"] == float(lo) and cell["number"]["ci_hi"] == float(hi)
    assert cell["number"]["est"] == pytest.approx(ind_a.mean() - ind_b.mean(), abs=1e-12)
    # item 18: the resample sd is the ddof=1 sd of exactly these differences
    assert cell["bootstrap"]["resample_sd"] == float(diffs.std(ddof=1))
    # (b) the same recomputation from the index vectors a recording resampler saw
    log: list[str] = []
    ra = _RecordingResampler(res_a, "a", log)
    rb = _RecordingResampler(res_b, "b", log)
    draw, frozen = subgroups_module._bootstrap_difference(
        lambda idx: float(ind_a[idx].mean()),
        ra,
        lambda idx: float(ind_b[idx].mean()),
        rb,
        POLICY.rng(cell["bootstrap"]["cell_key"]),
        POLICY.n_resamples,
        0.95,
    )
    assert frozen == ()
    va = np.array([float(ind_a[i].mean()) for i in ra.draws])
    vb = np.array([float(ind_b[j].mean()) for j in rb.draws])
    assert np.array_equal(draw.values, va - vb)
    assert (draw.ci_lo, draw.ci_hi) == (cell["number"]["ci_lo"], cell["number"]["ci_hi"])
    # the two one-sided renderings the day-5 note found unobserved (table A, item 16)
    for mutant in (va - vb.mean(), va.mean() - vb):
        m_lo, m_hi = np.quantile(mutant, [0.025, 0.975])
        assert (float(m_lo), float(m_hi)) != (draw.ci_lo, draw.ci_hi)


def test_item17_a_bootstrap_at_level_0_90_is_strictly_inside_its_0_95_interval_and_says_so():
    cols, crit = clustered_pair(span=False)
    rep95, _ = _run(cols, crit, level=0.95)
    rep90, _ = _run(cols, crit, level=0.90)
    checked = 0
    for row95, row90 in zip(rep95.rows, rep90.rows, strict=True):
        for key in ("sensitivity", "specificity", "ppv", "npv", "accuracy"):
            c95 = row95["metrics"]["op1"][key]["number"]
            c90 = row90["metrics"]["op1"][key]["number"]
            if c95["ci_lo"] is None or c90["ci_lo"] is None:
                continue
            assert c95["method"] == c90["method"] == "cluster_bootstrap_percentile"
            assert c90["ci_level"] == 0.9 and c95["ci_level"] == 0.95
            assert c95["ci_lo"] <= c90["ci_lo"] and c90["ci_hi"] <= c95["ci_hi"], (
                row95["level"],
                key,
            )
            assert (c90["ci_hi"] - c90["ci_lo"]) < (c95["ci_hi"] - c95["ci_lo"]), (
                row95["level"],
                key,
            )
            checked += 1
        d95 = row95["diff_vs_complement"]["op1"]["sensitivity"]["number"]
        d90 = row90["diff_vs_complement"]["op1"]["sensitivity"]["number"]
        if d95["ci_lo"] is not None and d90["ci_lo"] is not None:
            assert d95["ci_lo"] <= d90["ci_lo"] and d90["ci_hi"] <= d95["ci_hi"]
            assert d90["ci_level"] == 0.9
            checked += 1
    assert checked >= 20


class _ScriptedResampler:
    """A resampler whose draw ``b`` is the single row ``b``; ``kind`` clustered, no class
    deficient. Lets a test choose each resample's statistic value exactly."""

    kind = "clustered"
    deficient_class = None

    def __init__(self) -> None:
        self.calls = 0

    def draw(self, rng):
        idx = np.array([self.calls])
        self.calls += 1
        return idx


def test_item17b_the_difference_bootstrap_takes_its_bounds_and_its_frozen_rule_at_the_level_asked():
    """Inspected with ``_bootstrap_difference`` at level 0.90 and B = 200, side a's draws
    scripted as 1.0 on draws 0..191 and 0.5 on draws 192..199 (8 of 200, 4 %), side b's as
    ``0.1 * b / 200``:

    * side a is frozen at 0.90 (its 0.05 and 0.95 quantiles are both 1.0) and not at
      0.95 (its 0.025 quantile is 0.5), so the draw is ``boundary_estimate`` with
      ``frozen == ("a",)`` - a ``_frozen_sides(..., 0.95)`` would return an interval;
    * with side a scripted as ``1.0 - 0.2 * b / 200`` instead (nothing frozen) the bounds
      are the ``alpha/2`` and ``1 - alpha/2`` quantiles (``alpha = 1 - 0.90``) of
      ``values_a - values_b`` computed here, which a
      ``percentile_bounds(usable, 0.95)`` would not reproduce (its bounds are the 0.025 /
      0.975 quantiles, asserted different).
    """
    n = 200
    a_vals = np.where(np.arange(n) < 192, 1.0, 0.5)
    b_vals = 0.1 * np.arange(n) / n
    assert np.quantile(a_vals, [0.05, 0.95]).tolist() == [1.0, 1.0]
    assert np.quantile(a_vals, [0.025, 0.975]).tolist() == [0.5, 1.0]
    rng = POLICY.rng("item17b")
    draw, frozen = subgroups_module._bootstrap_difference(
        lambda idx: float(a_vals[idx[0]]),
        _ScriptedResampler(),
        lambda idx: float(b_vals[idx[0]]),
        _ScriptedResampler(),
        rng,
        n,
        0.90,
    )
    assert frozen == ("a",)
    assert draw.reason == "boundary_estimate" and draw.ci_lo is None and draw.ci_hi is None
    assert np.array_equal(draw.values, a_vals - b_vals)
    # nothing frozen: the bounds are the 0.05 / 0.95 quantiles of the differences
    a_vals = 1.0 - 0.2 * np.arange(n) / n
    draw, frozen = subgroups_module._bootstrap_difference(
        lambda idx: float(a_vals[idx[0]]),
        _ScriptedResampler(),
        lambda idx: float(b_vals[idx[0]]),
        _ScriptedResampler(),
        rng,
        n,
        0.90,
    )
    assert frozen == ()
    alpha = 1.0 - 0.90  # the percentile definition: alpha/2 and 1 - alpha/2 of the draws
    lo, hi = np.quantile(a_vals - b_vals, [alpha / 2.0, 1.0 - alpha / 2.0])
    assert (draw.ci_lo, draw.ci_hi) == (float(lo), float(hi))
    lo95, hi95 = np.quantile(a_vals - b_vals, [0.025, 0.975])
    assert (float(lo95), float(hi95)) != (draw.ci_lo, draw.ci_hi)


def test_item19_frozen_sides_reads_the_intervals_own_level_not_the_interquartile_range():
    eighty_twenty = np.array([0.4] * 80 + [0.6] * 20)
    assert subgroups_module._frozen_sides({"a": eighty_twenty}, 0.95) == ()
    assert subgroups_module._frozen_sides({"a": eighty_twenty}, 0.5) == ("a",)
    ninety_nine = np.array([0.4] * 199 + [0.6])
    assert subgroups_module._frozen_sides({"a": ninety_nine}, 0.95) == ("a",)
    assert subgroups_module._frozen_sides({"a": np.full(50, 0.3), "b": eighty_twenty}, 0.95) == (
        "a",
    )
