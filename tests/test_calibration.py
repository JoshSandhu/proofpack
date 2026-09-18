"""Day 6 (E6) - ``stats.calibration``: O:E, intercepts, slope, decile curve, Brier, ECE.

What is proved here, and against what:

* **F4** (R2 section 9; ``fixtures/f4_calibration.csv``, ``fixtures/f4_expected.json``):
  calibration-in-the-large and the joint slope / intercept against ``statsmodels
  GLM(Binomial)`` with and without an offset to 1e-6 (estimates *and* Wald standard
  errors); Brier against ``sklearn.metrics.brier_score_loss`` to 1e-9; the O:E ratio, its
  log-delta bounds, the IPA and both ECEs against values computed **in this file** from
  the published formulae (no repo code) to 1e-9. The R ``rms::val.prob`` capture (F13b)
  is day 9's and is marked ``[pending]`` in the fixture.
* The conventions: the right-closed equal-width ECE bins (the rule that reproduces R2's
  0.1255 / 0.1955), the stable-sort decile tie rule, the 200/200 annotation on both sides
  of the boundary, the boundary-score clip, the suppression reasons for ``logit`` /
  ``other`` / ``lower_is_positive``, the typed IRLS outcomes (separation, non-convergence,
  a constant score, a single class), the clustered refusals (DEC-09 / X2 census), DEC-10
  on every decile bin, the Brier cross-check against ``stats.subgroups._brier_cell``, the
  schema, the no-verdict-words grep over the day-6 output, and the scipy-free import.
"""

from __future__ import annotations

import copy
import csv
import importlib
import json
import math
import pathlib
import sys
from statistics import NormalDist
from typing import Any

import jsonschema
import numpy as np
import pytest

from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.io import schema as schema_mod
from proofpack.io.declare import validate_dict
from proofpack.resources import load_json_schema
from proofpack.stats import calibration as calibration_module
from proofpack.stats import subgroups as subgroups_module
from proofpack.stats.bootstrap import BootstrapPolicy, ClusterPlan
from proofpack.stats.calibration import (
    CLIP_EPS,
    CURVE_MIN_EVENTS,
    IRLS_MAX_ITER,
    calibration_block,
    calibration_from_table,
    equal_mass_bins,
    equal_width_bin_index,
    irls_logistic,
    suppression_reason,
)
from proofpack.stats.number import FLAGS, METHODS, NOT_ESTIMABLE_REASONS, Number
from test_subgroups import VERDICT_WORDS, walk_keys_and_strings, walk_numbers

pytestmark = pytest.mark.day6

REPO = pathlib.Path(__file__).resolve().parent.parent
Z = NormalDist().inv_cdf(0.975)
POLICY = BootstrapPolicy(n_resamples=200, seed=20240101)
QUANTITIES = ("oe", "intercept_large", "slope", "intercept", "brier", "brier_ref", "ipa")


# ---------------------------------------------------------------------------- helpers


def f4() -> tuple[np.ndarray, np.ndarray]:
    """The F4 vectors from the committed CSV (comment line skipped)."""
    rows = []
    with (REPO / "fixtures" / "f4_calibration.csv").open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            rows.append(line)
    reader = csv.DictReader(rows)
    p, y = [], []
    for r in reader:
        p.append(float(r["score"]))
        y.append(int(r["y_true"]))
    return np.array(p), np.array(y, dtype=bool)


def expected() -> dict[str, Any]:
    return json.loads((REPO / "fixtures" / "f4_expected.json").read_text(encoding="utf-8"))


def decl(**overrides: Any):
    return validate_dict(make_criteria(**overrides))


def block(p, y, *, policy=POLICY, **kw):
    res = calibration_block(
        np.asarray(p), np.asarray(y, dtype=bool), decl(**kw.pop("crit", {})), policy=policy, **kw
    )
    assert res.block is not None
    return res.block


def hand_ece(y: np.ndarray, p: np.ndarray, bins: list[np.ndarray]) -> float:
    n = y.shape[0]
    return sum(len(b) / n * abs(y[b].mean() - p[b].mean()) for b in bins if len(b))


def hand_equal_width(p: np.ndarray, n_bins: int = 10) -> list[np.ndarray]:
    """Right-closed (lo, hi] bins on arange(n_bins + 1) / n_bins, first bin closed at 0."""
    edges = np.arange(n_bins + 1) / n_bins
    out = []
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        sel = (p > lo) & (p <= hi) if b else (p >= lo) & (p <= hi)
        out.append(np.flatnonzero(sel))
    return out


def hand_equal_mass(p: np.ndarray, n_bins: int = 10) -> list[np.ndarray]:
    order = sorted(range(p.shape[0]), key=lambda i: p[i])  # Python's sort is stable
    size, extra = divmod(len(order), n_bins)
    out, start = [], 0
    for b in range(n_bins):
        width = size + (1 if b < extra else 0)
        out.append(np.array(order[start : start + width], dtype=np.intp))
        start += width
    return out


def cohort_arrays(n: int = 300, seed: int = 20240101, **kw):
    cols = make_cohort(seed=seed, n=n, **kw)
    y = np.array([v == "1" for v in cols["y_true"]], dtype=bool)
    p = np.array(cols["score"], dtype=np.float64)
    return cols, p, y


# --------------------------------------------------------------------------------- F4


@pytest.mark.fixture
def test_f4_fixture_rows_and_recorded_values_match_r2_section_9():
    p, y = f4()
    assert y.astype(int).tolist() == [0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1]
    assert p.tolist() == [i / 100 for i in range(5, 100, 5)] + [0.99]
    exp = expected()
    quoted = exp["r2_quoted"]
    assert exp["hand"]["brier"]["value"] == pytest.approx(quoted["brier"], abs=5e-5)
    assert exp["hand"]["ipa"]["value"] == pytest.approx(quoted["ipa"], abs=5e-5)
    assert exp["hand"]["oe"]["value"] == pytest.approx(quoted["oe"], abs=5e-5)
    assert exp["statsmodels_glm_binomial_offset"]["intercept_large"] == pytest.approx(
        quoted["intercept_large"], abs=5e-5
    )
    assert exp["statsmodels_glm_binomial_joint"]["slope"] == pytest.approx(
        quoted["slope"], abs=5e-5
    )
    assert exp["statsmodels_glm_binomial_joint"]["intercept"] == pytest.approx(
        quoted["intercept"], abs=5e-5
    )
    assert exp["hand"]["ece_equal_width_5"]["value"] == pytest.approx(
        quoted["ece_5_equal_width"], abs=5e-5
    )
    assert exp["hand"]["ece_equal_width_10"]["value"] == pytest.approx(quoted["ece_10"], abs=5e-5)
    assert exp["hand"]["ece_equal_mass_10"]["value"] == pytest.approx(quoted["ece_10"], abs=5e-5)
    assert exp["r_rms_val_prob"]["status"] == "[pending]"
    first = (REPO / "fixtures" / "f4_calibration.csv").read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("#") and "no seed" in first and "R2 section 9" in first


@pytest.mark.fixture
def test_f4_intercept_in_the_large_matches_statsmodels_glm_with_offset_to_1e_6():
    import statsmodels.api as sm

    p, y = f4()
    b = block(p, y)
    logit = np.log(p / (1 - p))
    fit = sm.GLM(
        y.astype(float), np.ones((20, 1)), family=sm.families.Binomial(), offset=logit
    ).fit(tol=1e-10)
    cell = b["intercept_large"]
    assert cell["number"]["est"] == pytest.approx(float(fit.params[0]), abs=1e-6)
    assert cell["detail"]["wald_se"] == pytest.approx(float(fit.bse[0]), abs=1e-6)
    assert cell["number"]["method"] == "irls_wald" and cell["analytic_status"] == "used"
    exp = expected()["statsmodels_glm_binomial_offset"]
    assert cell["number"]["est"] == pytest.approx(exp["intercept_large"], abs=1e-6)
    assert cell["detail"]["wald_se"] == pytest.approx(exp["se"], abs=1e-6)
    assert cell["detail"]["deviance"] == pytest.approx(exp["deviance"], abs=1e-6)
    assert cell["detail"]["model"].endswith("slope fixed at 1")


@pytest.mark.fixture
def test_f4_slope_and_intercept_match_statsmodels_glm_to_1e_6():
    import statsmodels.api as sm

    p, y = f4()
    b = block(p, y)
    logit = np.log(p / (1 - p))
    fit = sm.GLM(
        y.astype(float), np.column_stack([np.ones(20), logit]), family=sm.families.Binomial()
    ).fit(tol=1e-10)
    assert b["intercept"]["number"]["est"] == pytest.approx(float(fit.params[0]), abs=1e-6)
    assert b["slope"]["number"]["est"] == pytest.approx(float(fit.params[1]), abs=1e-6)
    assert b["intercept"]["detail"]["wald_se"] == pytest.approx(float(fit.bse[0]), abs=1e-6)
    assert b["slope"]["detail"]["wald_se"] == pytest.approx(float(fit.bse[1]), abs=1e-6)
    exp = expected()["statsmodels_glm_binomial_joint"]
    assert b["slope"]["number"]["est"] == pytest.approx(exp["slope"], abs=1e-6)
    assert b["intercept"]["number"]["est"] == pytest.approx(exp["intercept"], abs=1e-6)
    assert b["slope"]["detail"]["wald_se"] == pytest.approx(exp["se_slope"], abs=1e-6)
    assert b["intercept"]["detail"]["wald_se"] == pytest.approx(exp["se_intercept"], abs=1e-6)
    for key in ("slope", "intercept"):
        num, se = b[key]["number"], b[key]["detail"]["wald_se"]
        assert num["ci_lo"] == pytest.approx(num["est"] - Z * se, abs=1e-12)
        assert num["ci_hi"] == pytest.approx(num["est"] + Z * se, abs=1e-12)
        assert num["method"] == "irls_wald" and num["n"] == 20


@pytest.mark.fixture
def test_f4_brier_matches_sklearn_to_1e_9():
    from sklearn.metrics import brier_score_loss

    p, y = f4()
    b = block(p, y)
    assert b["brier"]["number"]["est"] == pytest.approx(
        brier_score_loss(y.astype(int), p), abs=1e-9
    )
    assert b["brier"]["number"]["est"] == pytest.approx(
        expected()["sklearn_brier"]["brier"], abs=1e-9
    )
    assert b["brier"]["number"]["method"] == "bootstrap_percentile"
    assert b["brier"]["analytic"]["not_estimable_reason"] == "analytic_ci_unavailable"


@pytest.mark.fixture
def test_f4_oe_ipa_and_both_eces_match_the_formulae_computed_here_to_1e_9():
    p, y = f4()
    b = block(p, y)
    yf = y.astype(float)
    o, e, n = yf.sum(), p.sum(), 20
    assert b["oe"]["number"]["est"] == pytest.approx(o / e, abs=1e-9)
    assert b["oe"]["number"]["k"] == 12 and b["oe"]["number"]["n"] == 20
    se = math.sqrt((1 - o / n) / o)
    assert b["oe"]["number"]["ci_lo"] == pytest.approx(math.exp(math.log(o / e) - Z * se), abs=1e-9)
    assert b["oe"]["number"]["ci_hi"] == pytest.approx(math.exp(math.log(o / e) + Z * se), abs=1e-9)
    assert b["oe"]["number"]["method"] == "log_delta"
    brier = float(np.mean((p - yf) ** 2))
    pi = yf.mean()
    ref = pi * (1 - pi)
    assert b["brier_ref"]["number"]["est"] == pytest.approx(ref, abs=1e-9)
    assert b["ipa"]["number"]["est"] == pytest.approx(1 - brier / ref, abs=1e-9)
    ece_w = hand_ece(yf, p, hand_equal_width(p))
    ece_m = hand_ece(yf, p, hand_equal_mass(p))
    assert b["ece_equal_width_10"]["number"]["est"] == pytest.approx(ece_w, abs=1e-9)
    assert b["ece_equal_mass_10"]["number"]["est"] == pytest.approx(ece_m, abs=1e-9)
    exp = expected()["hand"]
    assert ece_w == pytest.approx(exp["ece_equal_width_10"]["value"], abs=1e-9)
    assert ece_m == pytest.approx(exp["ece_equal_mass_10"]["value"], abs=1e-9)
    assert b["oe"]["number"]["ci_lo"] == pytest.approx(exp["oe_ci_95"]["lo"], abs=1e-9)


# --------------------------------------------------------------------------------- ECE


def test_the_two_ece_schemes_differ_where_the_partitions_differ_and_each_states_its_scheme():
    _, p, y = cohort_arrays(n=300)
    b = block(p, y)
    yf = y.astype(float)
    ew, em = b["ece_equal_width_10"], b["ece_equal_mass_10"]
    assert ew["number"]["est"] == pytest.approx(hand_ece(yf, p, hand_equal_width(p)), abs=1e-9)
    assert em["number"]["est"] == pytest.approx(hand_ece(yf, p, hand_equal_mass(p)), abs=1e-9)
    assert abs(ew["number"]["est"] - em["number"]["est"]) > 1e-3
    assert ew["scheme"] == "equal_width" and em["scheme"] == "equal_mass"
    assert ew["bins"] == em["bins"] == 10
    assert ew["edges"] == [i / 10 for i in range(11)]
    assert em["edges"][0] == p.min() and em["edges"][-1] == p.max() and len(em["edges"]) == 11
    for entry in (ew, em):
        assert entry["note"].startswith("supplementary")
        assert entry["number"]["not_estimable_reason"] == "not_computed_this_run"
        assert entry["number"]["ci_lo"] is None and entry["number"]["ci_hi"] is None
        assert "coverage" in entry["ci_not_computed_because"]


def test_the_equal_width_bins_are_right_closed_with_the_first_bin_closed_at_zero():
    p = np.array([0.0, 0.1, 0.10000000001, 0.2, 0.3, 0.7, 0.9, 1.0, 0.05])
    assert equal_width_bin_index(p).tolist() == [0, 0, 1, 1, 2, 6, 8, 9, 0]


def test_the_decile_tie_rule_is_stable_sort_order():
    p = np.array([0.5] * 20 + [0.2] * 5)
    bins = equal_mass_bins(p)
    order = list(range(20, 25)) + list(range(0, 20))  # the 0.2s first, then the 0.5s in row order
    flat = [int(i) for b in bins for i in b]
    assert flat == order
    assert [len(b) for b in bins] == [3, 3, 3, 3, 3, 2, 2, 2, 2, 2]
    y = np.array([True] * 10 + [False] * 10 + [True] * 5)
    b = block(p, y)
    # the five 0.2 rows (all events) fill bin 1 and two thirds of bin 2; the 0.5 rows
    # follow in row order, so rows 0-9 (events) end at bin 5 and rows 10-19 fill 6-10
    assert [d["events"] for d in b["decile_curve"]] == [3, 3, 3, 3, 3, 0, 0, 0, 0, 0]
    assert [d["n"] for d in b["decile_curve"]] == [3, 3, 3, 3, 3, 2, 2, 2, 2, 2]
    assert "stable sort" in b["decile_tie_rule"]


# ------------------------------------------------------------------------- 200 / 200


def _cohort_with_counts(events: int, nonevents: int, seed: int = 5):
    rng = np.random.default_rng(seed)
    y = np.array([True] * events + [False] * nonevents)
    p = np.where(y, rng.uniform(0.4, 0.95, y.shape[0]), rng.uniform(0.05, 0.6, y.shape[0]))
    return p, y


@pytest.mark.parametrize(
    ("events", "nonevents", "flagged"),
    [(199, 300, True), (200, 300, False), (300, 199, True), (300, 200, False), (199, 199, True)],
)
def test_the_200_200_annotation_is_strict_on_both_sides_and_never_suppresses(
    events, nonevents, flagged
):
    """``events < 200 or nonevents < 200`` -> flagged; exactly 200 of each is not."""
    assert CURVE_MIN_EVENTS == 200
    p, y = _cohort_with_counts(events, nonevents)
    b = block(p, y, policy=BootstrapPolicy(n_resamples=50, seed=1))
    flag = "below_200_events_or_nonevents"
    assert flag in FLAGS
    if flagged:
        assert b["curve_flag"]["flag"] == flag
        assert b["curve_flag"]["events"] == events and b["curve_flag"]["nonevents"] == nonevents
        assert "Van Calster 2019" in b["curve_flag"]["note"]
        assert b["flags"] == [flag]
        assert all(flag in d["observed"]["number"]["flags"] for d in b["decile_curve"])
    else:
        assert b["curve_flag"] is None and b["flags"] == []
        assert not any(flag in d["observed"]["number"]["flags"] for d in b["decile_curve"])
    # annotation, never suppression: every quantity and every bin is still reported
    for key in QUANTITIES:
        assert b[key]["number"]["est"] is not None
    assert (
        len(b["decile_curve"]) == 10
        and sum(d["n"] for d in b["decile_curve"]) == events + nonevents
    )
    assert b["convention"] == "ProofPack convention after Van Calster 2019"


# --------------------------------------------------------------------- suppression


@pytest.mark.parametrize("score_type", ["logit", "other"])
def test_score_type_logit_and_other_give_a_null_block_with_the_typed_reason(score_type):
    _, p, y = cohort_arrays(n=100)
    score = np.log(p / (1 - p)) if score_type == "logit" else p * 10
    d = decl(score={"type": score_type, "orientation": "higher_is_positive"})
    assert suppression_reason(d) == "score_not_probability"
    res = calibration_block(score, y, d, policy=POLICY)
    assert res.block is None and res.suppressed_reason == "score_not_probability"
    doc = res.as_document()
    assert doc["calibration"] is None
    assert doc["calibration_suppressed_reason"] == {
        "reason": "score_not_probability",
        "score_type": score_type,
        "orientation": "higher_is_positive",
    }
    assert "score_not_probability" in NOT_ESTIMABLE_REASONS
    schema = load_json_schema("output_schema_v1.json")
    assert "score_not_probability" in schema["$defs"]["notEstimableReason"]["enum"]
    assert (
        "score_not_probability"
        in schema["$defs"]["calibrationSuppressedReason"]["properties"]["reason"]["enum"]
    )


def test_a_lower_is_positive_probability_is_refused_with_its_own_reason_not_transformed():
    """Inheritance item 6: refuse with a reason, never fall back to 1 - p."""
    _, p, y = cohort_arrays(n=100)
    d = decl(score={"type": "probability", "orientation": "lower_is_positive"})
    res = calibration_block(1 - p, y, d, policy=POLICY)
    assert res.block is None
    assert res.suppressed_reason == "score_not_positive_class_probability"
    assert res.as_document()["calibration_suppressed_reason"]["orientation"] == "lower_is_positive"
    assert "score_not_positive_class_probability" in NOT_ESTIMABLE_REASONS
    # the table-level entry point takes the same decision before touching the rows
    cols = make_cohort(n=100)
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, _ = schema_mod.analysis_mask(table, set())
    assert calibration_from_table(table, d, mask, policy=POLICY).block is None


# ------------------------------------------------------------------------ clustering


def clustered_arrays(n: int = 200, rows_per_case: int = 2, seed: int = 20240101):
    cols, p, y = cohort_arrays(n=n, seed=seed, with_case_id=True)
    ids = np.repeat(np.array(cols["case_id"], dtype=object), rows_per_case)
    return np.repeat(p, rows_per_case), np.repeat(y, rows_per_case), ids


@pytest.mark.parametrize("route", ["declared", "detected"])
def test_a_clustered_plan_refuses_every_analytic_interval_and_routes_to_the_cluster_bootstrap(
    route,
):
    """Census (DEC-09 / X2): under clustering every analytic status is the refusal."""
    p, y, ids = clustered_arrays()
    crit = {"clustering": {"unit": "case_id", "declared_by": "t"}} if route == "declared" else {}
    d = decl(**crit)
    b = calibration_block(p, y, d, cluster_ids=ids, policy=POLICY).block
    assert b["clustering_route"] == route and b["n_cases"] == 200 and b["n"] == 400
    seen = 0
    for key in QUANTITIES:
        cell = b[key]
        assert cell["clustering_route"] == route
        assert cell["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid", key
        assert cell["analytic_status"] in ("refused_clustered", "unavailable"), key
        assert cell["number"]["method"] in ("cluster_bootstrap_percentile", "none"), key
        assert cell["bootstrap"]["resampling"]["kind"] == "clustered"
        assert cell["number"]["n_cases"] == 200
        seen += 1
    assert b["oe"]["number"]["flags"][0] == "log_delta_refused_clustered"
    for key in ("intercept_large", "slope", "intercept"):
        assert b[key]["number"]["flags"][0] == "irls_wald_refused_clustered"
        assert b[key]["number"]["ci_lo"] is not None
    for d_ in b["decile_curve"]:
        cell = d_["observed"]
        assert cell["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
        assert cell["number"]["method"] in ("cluster_bootstrap_percentile", "none")
        assert "wilson_refused_clustered" in cell["number"]["flags"]
        seen += 1
    assert seen == 17
    for path, num in walk_numbers(b):
        assert num["method"] not in ("wilson", "log_delta", "irls_wald", "bootstrap_percentile"), (
            path
        )
    # the point estimates do not move with the interval (rows are the estimand)
    iid = block(p[::2], y[::2], policy=POLICY)
    for key in ("oe", "slope", "intercept", "intercept_large", "brier"):
        assert b[key]["number"]["est"] == pytest.approx(iid[key]["number"]["est"], abs=1e-9)


def test_the_clustered_slope_interval_is_the_percentile_of_refits_on_resampled_cases():
    """Independent oracle: rebuild the cluster bootstrap of the slope in this test with the
    module's resampler and generator, refitting with statsmodels on every resample."""
    import statsmodels.api as sm

    from proofpack.stats.bootstrap import clustered_by_case

    p, y, ids = clustered_arrays(n=120)
    pol = BootstrapPolicy(n_resamples=60, seed=7)
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    b = calibration_block(p, y, d, cluster_ids=ids, policy=pol).block
    resampler = clustered_by_case(y, ids)
    rng = pol.rng(json.dumps(["calibration", "slope"]))
    logit = np.log(p / (1 - p))
    values = []
    for _ in range(60):
        idx = resampler.draw(rng)
        fit = sm.GLM(
            y[idx].astype(float),
            np.column_stack([np.ones(idx.shape[0]), logit[idx]]),
            family=sm.families.Binomial(),
        ).fit(tol=1e-10)
        values.append(float(fit.params[1]))
    lo, hi = np.quantile(values, [0.025, 0.975])
    assert b["slope"]["number"]["ci_lo"] == pytest.approx(lo, abs=1e-6)
    assert b["slope"]["number"]["ci_hi"] == pytest.approx(hi, abs=1e-6)
    assert b["slope"]["bootstrap"]["usable_resamples"] == 60


def test_a_supplied_plan_that_contradicts_the_case_column_is_refused():
    p, y, ids = clustered_arrays(n=50)
    d = decl()
    with pytest.raises(ValueError, match="contradicts"):
        calibration_block(p, y, d, cluster_ids=ids, plan=ClusterPlan(False, "none", 100, 100))
    with pytest.raises(ValueError):
        calibration_block(p, y, decl(clustering={"unit": "case_id", "declared_by": "t"}))


# ------------------------------------------------------------------------------ DEC-10


def test_dec10_every_decile_bin_number_is_wilson_or_the_cluster_bootstrap():
    _, p, y = cohort_arrays(n=300)
    b = block(p, y)
    for d_ in b["decile_curve"]:
        num = d_["observed"]["number"]
        assert num["method"] == "wilson" and num["ci_lo"] is not None
        assert num["n"] == d_["n"] and num["k"] == d_["events"]
        assert d_["score_min"] <= d_["mean_pred"] <= d_["score_max"]
    assert [d_["n"] for d_ in b["decile_curve"]] == [30] * 10
    assert sum(d_["events"] for d_ in b["decile_curve"]) == b["events"] == int(y.sum())
    p2, y2, ids = clustered_arrays()
    b2 = calibration_block(p2, y2, decl(), cluster_ids=ids, policy=POLICY).block
    for d_ in b2["decile_curve"]:
        num = d_["observed"]["number"]
        assert num["method"] in ("cluster_bootstrap_percentile", "none")
    for name, blk in (("iid", b), ("clustered", b2)):
        for path, num in walk_numbers(blk):
            assert num["method"] in METHODS, (name, path)
            Number(**num)
            assert (num["ci_lo"] is not None) or num[
                "not_estimable_reason"
            ] in NOT_ESTIMABLE_REASONS
            assert all(f in FLAGS for f in num["flags"])


# ------------------------------------------------------------------------------- Brier


def test_the_overall_brier_equals_the_subgroup_module_brier_cell_on_the_whole_cohort():
    cols = make_cohort(n=300)
    d = decl()
    table = schema_mod.validate(schema_mod.table_from_columns(cols), period=None)
    mask, _ = schema_mod.analysis_mask(table, d.indeterminate_values)
    cal = calibration_from_table(table, d, mask, policy=POLICY).block
    arrays = subgroups_module._arrays(table, d, mask, None, None, POLICY, 0.95)
    rows = np.arange(int(mask.sum()))
    cell, detail = subgroups_module._brier_cell(arrays, rows, json.dumps(["calibration", "brier"]))
    ours = cal["brier"]["number"]
    theirs = cell.number.as_dict()
    assert ours["est"] == theirs["est"]
    assert ours["ci_lo"] == theirs["ci_lo"] and ours["ci_hi"] == theirs["ci_hi"]
    assert ours["method"] == theirs["method"] == "bootstrap_percentile"
    assert cal["brier"]["bootstrap"]["resample_sd"] == cell.resample_sd
    # and the clustered twin, bit for bit under the same key
    n = 200
    dup = {
        k: [v[i // 2] for i in range(2 * n)] for k, v in make_cohort(n=n, with_case_id=True).items()
    }
    dup["row_id"] = [f"r{i:05d}" for i in range(2 * n)]
    dc = decl(clustering={"unit": "case_id", "declared_by": "t"})
    table = schema_mod.validate(schema_mod.table_from_columns(dup), period=None)
    mask, _ = schema_mod.analysis_mask(table, dc.indeterminate_values)
    cal = calibration_from_table(table, dc, mask, policy=POLICY).block
    arrays = subgroups_module._arrays(table, dc, mask, None, None, POLICY, 0.95)
    cell, _ = subgroups_module._brier_cell(
        arrays, np.arange(2 * n), json.dumps(["calibration", "brier"])
    )
    assert cal["brier"]["number"] == cell.number.as_dict()


def test_brier_ref_is_fixed_under_outcome_stratification_and_varies_when_case_sizes_differ():
    _, p, y = cohort_arrays(n=200)
    b = block(p, y)
    ref = b["brier_ref"]["number"]
    pi = y.mean()
    assert ref["est"] == pytest.approx(pi * (1 - pi), abs=1e-12)
    assert ref["not_estimable_reason"] == "fixed_by_outcome_stratification"
    assert b["brier_ref"]["bootstrap"]["resampling"]["kind"] == "stratified"
    # cases of one and three rows: the drawn row count per class varies, so does the prevalence
    sizes = np.where(np.arange(200) % 2 == 0, 1, 3)
    p2, y2 = np.repeat(p, sizes), np.repeat(y, sizes)
    ids = np.repeat(np.array([f"c{i}" for i in range(200)], dtype=object), sizes)
    b2 = calibration_block(p2, y2, decl(), cluster_ids=ids, policy=POLICY).block
    ref2 = b2["brier_ref"]["number"]
    assert ref2["method"] == "cluster_bootstrap_percentile" and ref2["ci_lo"] < ref2["ci_hi"]
    assert b2["ipa"]["number"]["ci_lo"] is not None


# ------------------------------------------------------------------ typed IRLS outcomes


def test_separation_and_non_convergence_are_typed_reasons_never_inf_nan_or_a_traceback():
    p = np.linspace(0.01, 0.99, 60)
    y = p > 0.5
    b = block(p, y)
    for key in ("slope", "intercept"):
        assert b[key]["number"]["est"] is None
        assert b[key]["number"]["not_estimable_reason"] == "complete_separation"
        assert b[key]["detail"]["outcome"] == "complete_separation"
    # the offset model has no slope to run away with: it converges at a = 0 here
    assert b["intercept_large"]["number"]["not_estimable_reason"] is None
    json.dumps(b, allow_nan=False)  # no inf or nan anywhere in the block
    x = np.column_stack([np.ones(60), np.log(p / (1 - p))])
    fit = irls_logistic(y, x, max_iter=1)
    assert fit.reason == "irls_not_converged" and fit.beta is None and fit.se is None
    assert IRLS_MAX_ITER >= 25
    # quasi-separation with one crossing row still ends in a typed outcome
    y2 = y.copy()
    y2[30] = not y2[30]
    fit2 = irls_logistic(y2, x)
    assert fit2.reason in (None, "complete_separation", "irls_not_converged")
    if fit2.reason is None:
        assert np.all(np.isfinite(fit2.beta)) and np.all(np.isfinite(fit2.se))
    for reason in ("complete_separation", "irls_not_converged", "constant_score"):
        assert reason in NOT_ESTIMABLE_REASONS


def test_a_constant_score_is_constant_score_for_the_slope_and_the_offset_intercept_still_fits():
    p = np.full(40, 0.3)
    y = np.arange(40) % 4 == 0
    b = block(p, y)
    assert b["slope"]["number"]["not_estimable_reason"] == "constant_score"
    assert b["intercept"]["number"]["not_estimable_reason"] == "constant_score"
    # logit P = a + logit(0.3), so a = logit(0.25) - logit(0.3) exactly
    a = math.log(0.25 / 0.75) - math.log(0.3 / 0.7)
    assert b["intercept_large"]["number"]["est"] == pytest.approx(a, abs=1e-9)


def test_a_single_class_cohort_is_single_class_everywhere_a_fit_or_a_ratio_needs_both():
    p = np.linspace(0.05, 0.95, 40)
    for y in (np.ones(40, dtype=bool), np.zeros(40, dtype=bool)):
        b = block(p, y)
        for key in QUANTITIES:
            assert b[key]["number"]["not_estimable_reason"] == "single_class", key
            assert b[key]["number"]["ci_lo"] is None
        assert b["brier"]["number"]["est"] == pytest.approx(float(np.mean((p - y) ** 2)))
        assert b["oe"]["number"]["est"] == pytest.approx(y.sum() / p.sum())
        assert len(b["decile_curve"]) == 10  # the curve is still tabulated
        json.dumps(b, allow_nan=False)


# ------------------------------------------------------------------- boundary scores


def test_scores_at_exactly_0_and_1_are_clipped_for_the_logit_models_only_and_counted():
    import statsmodels.api as sm

    rng = np.random.default_rng(11)
    p = rng.uniform(0.05, 0.95, 60).round(3)
    y = rng.random(60) < p
    p[0], p[1], p[2] = 0.0, 1.0, 1.0
    y[0], y[1], y[2] = False, True, False
    b = block(p, y)
    assert b["n_clipped"] == 3 and b["clip_eps"] == CLIP_EPS == 1e-12
    for key in ("intercept_large", "slope", "intercept"):
        assert "scores_clipped_for_logit" in b[key]["number"]["flags"], key
    for key in ("oe", "brier", "ipa"):
        assert "scores_clipped_for_logit" not in b[key]["number"]["flags"], key
    clipped = np.clip(p, 1e-12, 1 - 1e-12)
    logit = np.log(clipped / (1 - clipped))
    fit = sm.GLM(
        y.astype(float), np.column_stack([np.ones(60), logit]), family=sm.families.Binomial()
    ).fit(tol=1e-10)
    assert b["slope"]["number"]["est"] == pytest.approx(float(fit.params[1]), abs=1e-6)
    assert b["intercept"]["number"]["est"] == pytest.approx(float(fit.params[0]), abs=1e-6)
    off = sm.GLM(
        y.astype(float), np.ones((60, 1)), family=sm.families.Binomial(), offset=logit
    ).fit(tol=1e-10)
    assert b["intercept_large"]["number"]["est"] == pytest.approx(float(off.params[0]), abs=1e-6)
    # the unclipped quantities use the raw score
    assert b["oe"]["number"]["est"] == pytest.approx(y.sum() / p.sum(), abs=1e-12)
    assert b["brier"]["number"]["est"] == pytest.approx(float(np.mean((p - y) ** 2)), abs=1e-12)
    assert b["decile_curve"][0]["score_min"] == 0.0 and b["decile_curve"][-1]["score_max"] == 1.0
    json.dumps(b, allow_nan=False)
    # a different epsilon is a different slope: the test pins the value, not just the flag
    loose = np.clip(p, 1e-6, 1 - 1e-6)
    fit_loose = sm.GLM(
        y.astype(float),
        np.column_stack([np.ones(60), np.log(loose / (1 - loose))]),
        family=sm.families.Binomial(),
    ).fit(tol=1e-10)
    assert abs(float(fit_loose.params[1]) - b["slope"]["number"]["est"]) > 1e-4
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        block(np.array([0.5, 1.2, 0.3]), np.array([1, 0, 1]))


# ---------------------------------------------------------------------- small cohort


def test_an_n25_cohort_still_shapes_every_number_with_its_tier_annotation():
    _, p, y = cohort_arrays(n=25)
    b = block(p, y, policy=BootstrapPolicy(n_resamples=100, seed=3))
    schema = load_json_schema("output_schema_v1.json")
    v = jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/calibrationBlock", "$defs": schema["$defs"]}
    )
    assert list(v.iter_errors(b)) == []
    for d_ in b["decile_curve"]:
        assert 2 <= d_["n"] <= 3
        assert "not_evaluable_shown_for_transparency" in d_["observed"]["number"]["flags"]
    for key in QUANTITIES:
        num = b[key]["number"]
        Number(**num)
        assert "very_low_precision" in num["flags"], key
    assert b["curve_flag"]["flag"] == "below_200_events_or_nonevents"


# ------------------------------------------------------------ schema, verdicts, enums


@pytest.fixture(scope="module")
def documents() -> dict[str, dict[str, Any]]:
    pol = BootstrapPolicy(n_resamples=100, seed=20240101)
    iid = assemble(make_cohort(n=300), policy=pol)
    n = 150
    dup = {
        k: [v[i // 2] for i in range(2 * n)] for k, v in make_cohort(n=n, with_case_id=True).items()
    }
    dup["row_id"] = [f"r{i:05d}" for i in range(2 * n)]
    declared = assemble(
        dup, make_criteria(clustering={"unit": "case_id", "declared_by": "t"}), policy=pol
    )
    detected = assemble(dup, make_criteria(), policy=pol)
    cols = make_cohort(n=200)
    cols["score"] = [round(math.log(s / (1 - s)), 6) for s in cols["score"]]
    logit = assemble(
        cols,
        make_criteria(score={"type": "logit", "orientation": "higher_is_positive"}),
        policy=pol,
    )
    return {"iid": iid, "declared": declared, "detected": detected, "logit": logit}


def test_the_assembled_document_validates_against_the_output_schema(documents):
    """The named acceptance test: one full document from the day-2/4/5/6 blocks on the
    synthetic cohort, validated against ``schema/output_schema_v1.json``. The assembly
    itself is test-only (``tests/assembler.py``); the engine's wiring is E7's."""
    schema = load_json_schema("output_schema_v1.json")
    validator = jsonschema.Draft202012Validator(schema)
    for name, doc in documents.items():
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
        assert errors == [], (name, [(list(e.absolute_path), e.message[:160]) for e in errors[:5]])
        assert {
            "flow",
            "table1",
            "missingness",
            "calibration",
            "calibration_suppressed_reason",
        } <= set(doc)
    assert documents["logit"]["calibration"] is None
    assert documents["logit"]["calibration_suppressed_reason"]["reason"] == "score_not_probability"
    assert documents["iid"]["calibration_suppressed_reason"] is None
    assert documents["detected"]["warnings"][0]["code"] == "W13"
    assert (
        documents["detected"]["flow"]["clustered"]
        and documents["detected"]["flow"]["clustering_route"] == "detected"
    )
    assert documents["declared"]["calibration"]["clustering_route"] == "declared"


def test_the_schema_rejects_a_block_that_drops_the_scheme_or_smuggles_a_reason_into_a_present_block(
    documents,
):
    schema = load_json_schema("output_schema_v1.json")
    validator = jsonschema.Draft202012Validator(schema)
    doc = documents["iid"]
    bad = copy.deepcopy(doc)
    del bad["calibration"]["ece_equal_width_10"]["scheme"]
    assert any(validator.iter_errors(bad))
    bad = copy.deepcopy(doc)
    bad["calibration"]["suppressed_reason"] = "score_not_probability"
    assert any(validator.iter_errors(bad))
    bad = copy.deepcopy(doc)
    bad["calibration"]["curve_flag"]["flag"] = "very_low_precision"
    assert any(validator.iter_errors(bad))
    bad = copy.deepcopy(doc)
    bad["calibration"]["decile_curve"].pop()
    assert any(validator.iter_errors(bad))
    bad = copy.deepcopy(doc)
    bad["calibration_suppressed_reason"] = {
        "reason": "not_computed_this_run",
        "score_type": "logit",
        "orientation": "higher_is_positive",
    }
    assert any(validator.iter_errors(bad))


def test_no_verdict_word_appears_in_any_key_or_engine_string_of_the_day6_output(documents):
    import re

    def flagged(token: str) -> bool:
        return bool(set(re.split(r"[^a-z]+", token.lower())) & VERDICT_WORDS)

    for name, doc in documents.items():
        engine = {k: v for k, v in doc.items() if k != "declarations"}
        for token in walk_keys_and_strings(engine):
            assert not flagged(token), (name, token)
    assert flagged("well calibrated") and flagged("miscalibrated") and not flagged("calibration")


def test_every_number_in_the_day6_output_has_a_ci_or_a_typed_reason(documents):
    for name, doc in documents.items():
        seen = 0
        for path, num in walk_numbers({k: doc[k] for k in ("calibration",) if doc[k] is not None}):
            seen += 1
            Number(**num)
            has_ci = num["ci_lo"] is not None and num["ci_hi"] is not None
            assert has_ci or num["not_estimable_reason"] in NOT_ESTIMABLE_REASONS, (name, path)
        assert seen == (0 if name == "logit" else 36), name  # 7 x 2 + 2 ECE + 10 x 2


def test_the_enums_added_today_agree_between_code_and_schema():
    schema = load_json_schema("output_schema_v1.json")
    assert set(schema["$defs"]["notEstimableReason"]["enum"]) == NOT_ESTIMABLE_REASONS
    assert set(schema["$defs"]["flag"]["enum"]) == FLAGS
    assert set(schema["$defs"]["method"]["enum"]) == METHODS
    assert {
        "score_not_probability",
        "score_not_positive_class_probability",
        "irls_not_converged",
        "complete_separation",
        "constant_score",
        "fixed_by_outcome_stratification",
    } <= NOT_ESTIMABLE_REASONS
    assert {
        "below_200_events_or_nonevents",
        "scores_clipped_for_logit",
        "log_delta_refused_clustered",
        "irls_wald_refused_clustered",
    } <= FLAGS


# ------------------------------------------------------------------------- no scipy


def test_calibration_imports_and_runs_with_scipy_hidden(monkeypatch):
    for name in list(sys.modules):
        if name == "scipy" or name.startswith("scipy."):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "scipy", None)
    monkeypatch.setitem(sys.modules, "scipy.stats", None)
    mod = importlib.reload(calibration_module)
    p, y = f4()
    b = mod.calibration_block(p, y, decl(), policy=POLICY).block
    assert b["slope"]["number"]["est"] == pytest.approx(
        expected()["statsmodels_glm_binomial_joint"]["slope"], abs=1e-6
    )
    src = (REPO / "src/proofpack/stats/calibration.py").read_text(encoding="utf-8")
    assert "scipy" not in src.split('"""', 2)[2].replace("nothing here imports scipy", "")
    importlib.reload(calibration_module)
