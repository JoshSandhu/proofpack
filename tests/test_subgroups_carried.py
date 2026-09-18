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
* **17** - no test ran any bootstrap at a level other than 0.95: the 0.90 interval of a
  cluster-bootstrapped cell must be strictly inside its 0.95 interval and carry
  ``ci_level: 0.9`` (kills ``percentile_bounds(usable, DEFAULT_LEVEL)``).
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


def test_item19_frozen_sides_reads_the_intervals_own_level_not_the_interquartile_range():
    eighty_twenty = np.array([0.4] * 80 + [0.6] * 20)
    assert subgroups_module._frozen_sides({"a": eighty_twenty}, 0.95) == ()
    assert subgroups_module._frozen_sides({"a": eighty_twenty}, 0.5) == ("a",)
    ninety_nine = np.array([0.4] * 199 + [0.6])
    assert subgroups_module._frozen_sides({"a": ninety_nine}, 0.95) == ("a",)
    assert subgroups_module._frozen_sides({"a": np.full(50, 0.3), "b": eighty_twenty}, 0.95) == (
        "a",
    )
