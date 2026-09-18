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
from proofpack.stats.bootstrap import (
    BootstrapPolicy,
    ClusterPlan,
    clustered_by_case,
    clustered_flat,
)
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


def test_the_equal_width_edges_are_arange_over_ten_and_not_linspace():
    """Inspected: the computed floats ``0.1 * 3``, ``0.1 * 6``, ``0.1 * 7`` (each a hair
    above its decimal) and the decimal literals 0.3, 0.6, 0.7. The engine's edges
    ``arange(11) / 10`` equal the literals, so under the right-closed rule a literal is
    the upper edge of bins 2 / 5 / 6 and the computed floats fall in bins 3 / 6 / 7.
    ``numpy.linspace(0, 1, 11)`` edges, whose third edge is ``0.30000000000000004``, put
    the computed floats in bins 2 / 5 / 6 as well (lens 1 of 2026-09-18, FA-N4: the day-6
    docstring said the rule reproduced sklearn's binning, which uses linspace edges)."""
    computed = np.array([0.1 * 3, 0.1 * 6, 0.1 * 7])
    literals = np.array([0.3, 0.6, 0.7])
    assert (computed > literals).all()
    assert equal_width_bin_index(computed).tolist() == [3, 6, 7]
    assert equal_width_bin_index(literals).tolist() == [2, 5, 6]
    linspace_edges = np.linspace(0.0, 1.0, 11)
    assert linspace_edges[3] == 0.30000000000000004 and linspace_edges[3] != 0.3
    under_linspace = np.searchsorted(linspace_edges, computed, side="left") - 1
    assert under_linspace.tolist() == [2, 5, 6]


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
def test_the_200_200_annotation_is_strict_on_both_sides_and_the_flagged_fits_keep_their_intervals(
    events, nonevents, flagged
):
    """``events < 200 or nonevents < 200`` -> flagged; exactly 200 of each is not.

    Inspected on the flagged side: the O:E, slope, intercept and intercept-in-the-large
    Numbers carry ``ci_lo`` / ``ci_hi`` with their analytic method, every quantity has
    an estimate, and all ten bins are present. Lens 1 of 2026-09-18 (RG-N3) planted an
    ``_oe_cell`` that returns ``not_computed_this_run`` below 200 and the test as then
    named passed it; the interval assertions below are what observe that.
    """
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
        # the flag rides on the rendered Number only; on i.i.d. rows the Wilson companion
        # under ``analytic`` does not carry it (at b93e050 the two were one object and the
        # in-place append flagged both; lens 2 of 2026-09-18, RG-N2, records the change)
        assert not any(flag in d["observed"]["analytic"]["flags"] for d in b["decile_curve"])
        assert all(d["observed"]["analytic"]["method"] == "wilson" for d in b["decile_curve"])
    else:
        assert b["curve_flag"] is None and b["flags"] == []
        assert not any(flag in d["observed"]["number"]["flags"] for d in b["decile_curve"])
    # annotation, not suppression: every quantity has an estimate, the four analytic
    # cells keep their intervals and their methods, and every bin is reported
    for key in QUANTITIES:
        assert b[key]["number"]["est"] is not None
    assert b["oe"]["number"]["method"] == "log_delta" and b["oe"]["number"]["ci_lo"] is not None
    for key in ("slope", "intercept", "intercept_large"):
        num = b[key]["number"]
        assert num["method"] == "irls_wald"
        assert num["ci_lo"] is not None and num["ci_hi"] is not None
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
        # 200 events / 200 non-events short on this cohort: the flag rides on the
        # rendered Number, not on the companion (lens 1 of 2026-09-18, FA-N2 M18)
        assert "below_200_events_or_nonevents" in cell["number"]["flags"]
        assert "below_200_events_or_nonevents" not in cell["analytic"]["flags"]
        seen += 1
    assert seen == 17
    # the O:E and the three fits resample cases in one stratum; the Brier cells within class
    for key in ("oe", "intercept_large", "slope", "intercept"):
        assert b[key]["bootstrap"]["resampling"]["units_per_stratum"] == {"all": 200}, key
    assert set(b["brier"]["bootstrap"]["resampling"]["units_per_stratum"]) <= {
        "positive",
        "negative",
        "mixed",
    }
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
    single-stratum case resampler (``clustered_flat``, the route since repair round 1 of
    2026-09-18; build day 6 used ``clustered_by_case``) and the module's generator,
    refitting with statsmodels on every resample."""
    import statsmodels.api as sm

    from proofpack.stats.bootstrap import clustered_flat

    p, y, ids = clustered_arrays(n=120)
    pol = BootstrapPolicy(n_resamples=60, seed=7)
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    b = calibration_block(p, y, d, cluster_ids=ids, policy=pol).block
    resampler = clustered_flat(ids, n_rows=ids.shape[0])
    assert b["slope"]["bootstrap"]["resampling"]["units_per_stratum"] == {"all": 120}
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


def _cases_in_first_appearance_order(ids: np.ndarray) -> list[np.ndarray]:
    seen: dict[Any, int] = {}
    for v in ids.tolist():
        seen.setdefault(v, len(seen))
    rank = np.array([seen[v] for v in ids.tolist()])
    return [np.flatnonzero(rank == j) for j in range(len(seen))]


def test_the_clustered_oe_and_intercept_intervals_are_the_percentile_of_a_one_stratum_bootstrap():
    """Lens 1 of 2026-09-18, FA-B1. Inspected on the lens's cohort (``default_rng(5)``: 200
    rows, ``p = expit(-0.5 + N(0, 1.5))``, ``y ~ U < p``, as 100 declared two-row cases,
    B = 100, seed 1): an independent case bootstrap written here - every case drawn with
    the same probability, ``rng.integers(0, 100, 100)`` per draw from the cell's own
    generator, all rows of a drawn case kept, the O:E as ``sum(y) / sum(p)`` on the drawn
    rows - reproduces the rendered O:E bounds bit for bit; the event count ``O`` takes at
    least two distinct values over those 100 draws, so the bounds the engine must
    reproduce come from draws in which ``O`` varies. At b93e050 the engine drew cases
    within outcome class - every case here is pure or carries one event, so its ``O`` was
    one integer in every draw - and its bounds were (1.0885, 1.2770) at B = 100 against
    this test's (1.0510, 1.3215); at B = 2000 the lens read (1.0911, 1.2709) against the
    analytic (1.0096, 1.3674). The intercept-in-the-large bounds are the percentile of
    statsmodels offset refits on the same draws to 1e-6."""
    import statsmodels.api as sm

    rng0 = np.random.default_rng(5)
    p = 1.0 / (1.0 + np.exp(-(-0.5 + rng0.normal(0.0, 1.5, 200))))
    y = rng0.uniform(size=200) < p
    ids = np.repeat(np.arange(100), 2)
    pol = BootstrapPolicy(n_resamples=100, seed=1)
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    b = calibration_block(p, y, d, cluster_ids=ids, policy=pol).block
    cases = _cases_in_first_appearance_order(ids)
    assert len(cases) == 100 and all(c.shape[0] == 2 for c in cases)
    yf = y.astype(float)
    logit = np.log(p / (1 - p))
    # O:E
    rng = pol.rng(b["oe"]["bootstrap"]["cell_key"])
    values, observed = [], set()
    for _ in range(100):
        sel = rng.integers(0, 100, 100)
        idx = np.concatenate([cases[i] for i in sel])
        observed.add(int(yf[idx].sum()))
        values.append(yf[idx].sum() / p[idx].sum())
    assert len(observed) >= 2, sorted(observed)
    lo, hi = np.quantile(values, [0.025, 0.975])
    oe = b["oe"]["number"]
    assert oe["method"] == "cluster_bootstrap_percentile"
    assert (oe["ci_lo"], oe["ci_hi"]) == (float(lo), float(hi))
    assert oe["est"] == pytest.approx(yf.sum() / p.sum(), abs=1e-12)
    assert b["oe"]["bootstrap"]["resampling"]["units_per_stratum"] == {"all": 100}
    # intercept-in-the-large: statsmodels offset refit on the same draws
    rng = pol.rng(b["intercept_large"]["bootstrap"]["cell_key"])
    refits = []
    for _ in range(100):
        sel = rng.integers(0, 100, 100)
        idx = np.concatenate([cases[i] for i in sel])
        fit = sm.GLM(
            yf[idx], np.ones((idx.shape[0], 1)), family=sm.families.Binomial(), offset=logit[idx]
        ).fit(tol=1e-10)
        refits.append(float(fit.params[0]))
    lo, hi = np.quantile(refits, [0.025, 0.975])
    itl = b["intercept_large"]["number"]
    assert itl["ci_lo"] == pytest.approx(lo, abs=1e-6)
    assert itl["ci_hi"] == pytest.approx(hi, abs=1e-6)
    assert b["intercept_large"]["bootstrap"]["usable_resamples"] == 100


def test_a_clustered_oe_resample_with_one_outcome_class_is_nan_and_counted_as_degenerate():
    """Inspected: 40 declared one-row cases with 2 events (``y[0]``, ``y[1]``), B = 200.
    A draw of 40 cases from 40 misses both event cases in ``(38/40)**40`` = 0.129 of
    draws in expectation; the O:E on such a draw is refused the way the cell refuses
    ``O = 0`` (``single_class``), so the draw is ``nan`` and the interval is refused as
    ``degenerate_resamples`` when fewer than 90 % are usable. The count of usable draws
    is asserted equal to the number of draws that hold at least one event case,
    recomputed here from the cell's own generator."""
    n = 40
    p = np.full(n, 0.1)
    y = np.zeros(n, dtype=bool)
    y[:2] = True
    ids = np.array([f"c{i}" for i in range(n)], dtype=object)
    pol = BootstrapPolicy(n_resamples=200, seed=11)
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    b = calibration_block(p, y, d, cluster_ids=ids, policy=pol).block
    rng = pol.rng(b["oe"]["bootstrap"]["cell_key"])
    with_event = sum(bool((rng.integers(0, n, n) < 2).any()) for _ in range(200))
    assert b["oe"]["bootstrap"]["usable_resamples"] == with_event
    assert with_event < 180  # the construction reaches the refusal at this seed
    oe = b["oe"]["number"]
    assert oe["not_estimable_reason"] == "degenerate_resamples" and oe["ci_lo"] is None
    assert oe["est"] == pytest.approx(2.0 / p.sum(), abs=1e-12)


def test_the_flat_resampler_holds_o_at_100_on_100_two_row_cases_of_one_event_each():
    """Lens 2 of 2026-09-18, RG-N5: the module docstring said the single-stratum case
    resampler makes ``O`` vary from draw to draw. Inspected: 100 declared two-row cases
    each carrying one event and one non-event, 500 draws of ``clustered_flat`` - the
    distinct values of ``O`` are ``{100}`` - and the O:E on those rows (``default_rng(7)``,
    ``p ~ U(0.2, 0.8)``, B = 200, seed 3) still renders ``cluster_bootstrap_percentile``
    with 200 usable draws and ``ci_lo < est < ci_hi``, from the variation of ``E``."""
    ids = np.repeat(np.array([f"c{i}" for i in range(100)], dtype=object), 2)
    y = np.tile([True, False], 100)
    resampler = clustered_flat(ids, n_rows=200)
    g = np.random.default_rng(0)
    assert {int(y[resampler.draw(g)].sum()) for _ in range(500)} == {100}
    p = np.random.default_rng(7).uniform(0.2, 0.8, 200)
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    b = calibration_block(
        p, y, d, cluster_ids=ids, policy=BootstrapPolicy(n_resamples=200, seed=3)
    ).block
    oe = b["oe"]["number"]
    assert oe["method"] == "cluster_bootstrap_percentile"
    assert b["oe"]["bootstrap"]["usable_resamples"] == 200
    assert oe["est"] == pytest.approx(100.0 / p.sum(), abs=1e-12)
    assert oe["ci_lo"] < oe["est"] < oe["ci_hi"]
    assert b["oe"]["bootstrap"]["resampling"]["units_per_stratum"] == {"all": 100}
    assert "varies from draw to draw" not in calibration_module.__doc__


def test_one_case_holding_180_of_200_rows_is_insufficient_clusters_on_the_oe_and_the_fits():
    """Inspected: ``default_rng(3)``, 200 rows, ``p ~ U(0.05, 0.95)``, ``y ~ U < p``, one
    declared case ``big`` holding rows 0..179 beside twenty one-row cases (lens 1 of
    2026-09-18 listed this input under "could not break": all seven quantities
    ``insufficient_clusters``). The O:E and the three fits are refused
    ``insufficient_clusters`` with ``very_low_precision`` (21 cases) and no interval, the
    companion is the DEC-09 refusal, ``bootstrap.resampling.class_units_guard`` names a
    deficient class and ``usable_resamples`` is 0; the Brier and IPA are refused the same
    way by their own resampler. The single-stratum resampler's own rule alone would not
    refuse (``units_per_stratum == {"all": 21}``, nothing frozen), which is why the guard
    exists."""
    rng = np.random.default_rng(3)
    p = rng.uniform(0.05, 0.95, 200)
    y = rng.uniform(size=200) < p
    ids = np.array(["big"] * 180 + [f"c{i}" for i in range(20)], dtype=object)
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    b = calibration_block(
        p, y, d, cluster_ids=ids, policy=BootstrapPolicy(n_resamples=50, seed=1)
    ).block
    for key in ("oe", "intercept_large", "slope", "intercept", "brier", "ipa"):
        num = b[key]["number"]
        assert num["not_estimable_reason"] == "insufficient_clusters", key
        assert num["ci_lo"] is None and num["est"] is not None
        assert "very_low_precision" in num["flags"] and num["n_cases"] == 21
        assert b[key]["analytic"]["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"
        assert b[key]["bootstrap"]["usable_resamples"] == 0
    for key in ("oe", "intercept_large", "slope", "intercept"):
        res = b[key]["bootstrap"]["resampling"]
        assert res["units_per_stratum"] == {"all": 21} and res["deficient_class"] is None
        assert res["class_units_guard"]["deficient_class"] in ("positive", "negative")
        assert res["class_units_guard"]["units_per_stratum"]["mixed"] == 1
    assert b["brier_ref"]["number"]["not_estimable_reason"] == "fixed_by_outcome_stratification"


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


def test_each_decile_bins_cluster_bootstrap_groups_the_bins_own_rows_by_case():
    """Lens 2 of 2026-09-18, FA-N5 L2-2: a ``_decile_curve`` that passed a same-length
    *prefix* of the case column instead of ``ids[rows]`` survived the whole suite, because
    every clustered test cohort is built by ``np.repeat`` (a case's rows are identical and
    adjacent, so the prefix grouping coincides with the true one). Inspected: 200 declared
    two-row cases whose two rows differ in score (``default_rng(2)``, ``p ~ U(0.02,
    0.98)``, ``y ~ U < p``, B = 200, seed 5); bin 3 holds 40 rows from 38 distinct cases
    and its interval is (0.09756..., 0.35897...); and on every one of the ten bins an
    independent case bootstrap written here - the bin's rows grouped by their own case
    ids in first-appearance order, ``m`` cases drawn from ``m`` with the cell's own
    generator - reproduces the rendered bounds within 1e-12 and the case count exactly.
    With the prefix mutant bin 3 reads 20 cases and (0.1, 0.35)."""
    rng = np.random.default_rng(2)
    n = 400
    ids = np.repeat(np.array([f"c{i}" for i in range(200)], dtype=object), 2)
    p = rng.uniform(0.02, 0.98, n)
    y = rng.uniform(size=n) < p
    policy = BootstrapPolicy(n_resamples=200, seed=5)
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    b = calibration_block(p, y, d, cluster_ids=ids, policy=policy).block
    bins = hand_equal_mass(p)
    cases_per_bin = [38, 36, 38, 39, 40, 39, 39, 38, 38, 37]
    assert [len(set(ids[rows].tolist())) for rows in bins] == cases_per_bin
    for k, rows in enumerate(bins):
        entry = b["decile_curve"][k]
        num = entry["observed"]["number"]
        groups: dict[str, list[int]] = {}
        for j, case in enumerate(ids[rows].tolist()):
            groups.setdefault(case, []).append(j)
        units = [np.array(g) for g in groups.values()]
        m = len(units)
        assert num["n_cases"] == m
        assert entry["observed"]["bootstrap"]["resampling"]["units_per_stratum"] == {"all": m}
        g = policy.rng(entry["observed"]["bootstrap"]["cell_key"])
        ind = y[rows]
        values = []
        for _ in range(policy.n_resamples):
            sel = g.integers(0, m, m)
            values.append(float(ind[np.concatenate([units[i] for i in sel])].mean()))
        lo, hi = np.quantile(values, [0.025, 0.975])
        assert num["method"] == "cluster_bootstrap_percentile", k
        assert num["ci_lo"] == pytest.approx(float(lo), abs=1e-12), k
        assert num["ci_hi"] == pytest.approx(float(hi), abs=1e-12), k
    bin3 = b["decile_curve"][2]["observed"]["number"]
    assert bin3["n"] == 40 and bin3["n_cases"] == 38
    assert bin3["ci_lo"] == pytest.approx(0.0975609756097561, abs=1e-12)
    assert bin3["ci_hi"] == pytest.approx(0.358974358974359, abs=1e-12)


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


def _case_class_counts(y: np.ndarray, ids: np.ndarray) -> dict[str, set[tuple[int, int]]]:
    """Per stratum (pure-positive, pure-negative, mixed), the set of (events, non-events)
    pairs its cases carry. One pair per stratum means every draw has the same prevalence."""
    out: dict[str, set[tuple[int, int]]] = {"positive": set(), "negative": set(), "mixed": set()}
    for case in np.unique(ids):
        got = y[ids == case]
        k, m = int(got.sum()), int((~got).sum())
        out["positive" if m == 0 else "negative" if k == 0 else "mixed"].add((k, m))
    return out


def test_brier_ref_is_fixed_when_every_unit_in_a_stratum_carries_the_same_class_counts():
    """Lens 1 of 2026-09-18, FA-B3 / RG-B3. Inspected: ``default_rng(1)``, 100 declared
    cases, ``p ~ U(0.05, 0.95)``, ``y ~ U < p``. With two rows per case (48 mixed cases,
    each one event and one non-event; the pure strata (1, 0) / (0, 1)) every stratum's
    cases carry one (events, non-events) pair, so the resampled prevalence cannot move and
    ``brier_ref`` is ``fixed_by_outcome_stratification`` (it was ``boundary_estimate``,
    method ``none``, at b93e050). With three rows per case (mixed cases split (1, 2) and
    (2, 1)) it is bootstrapped with an interval, and the IPA has one either way."""
    for rows_per_case, expect_fixed in ((2, True), (3, False)):
        rng = np.random.default_rng(1)
        n_rows = 100 * rows_per_case
        p = rng.uniform(0.05, 0.95, n_rows)
        y = rng.random(n_rows) < p
        ids = np.repeat(np.array([f"c{i}" for i in range(100)], dtype=object), rows_per_case)
        counts = _case_class_counts(y, ids)
        # the literal case counts the docstring names, measured (lens 2 RG-N6): 48 mixed
        # two-row cases carrying (1, 1); with three rows, 72 mixed cases split (1, 2) / (2, 1)
        n_mixed = sum(1 for case in np.unique(ids) if 0 < y[ids == case].sum() < rows_per_case)
        assert n_mixed == {2: 48, 3: 72}[rows_per_case]
        assert counts["mixed"] == {2: {(1, 1)}, 3: {(1, 2), (2, 1)}}[rows_per_case]
        invariant = all(len(pairs) <= 1 for pairs in counts.values())
        assert invariant is expect_fixed, counts
        d = decl(clustering={"unit": "case_id", "declared_by": "t"})
        b = calibration_block(
            p, y, d, cluster_ids=ids, policy=BootstrapPolicy(n_resamples=100, seed=2)
        ).block
        ref = b["brier_ref"]["number"]
        pi = y.mean()
        assert ref["est"] == pytest.approx(pi * (1 - pi), abs=1e-12)
        if expect_fixed:
            assert ref["not_estimable_reason"] == "fixed_by_outcome_stratification"
            assert ref["method"] == "none"
        else:
            assert ref["method"] == "cluster_bootstrap_percentile" and ref["ci_lo"] < ref["ci_hi"]
        assert b["ipa"]["number"]["ci_lo"] is not None, rows_per_case
        assert b["brier"]["number"]["method"] == "cluster_bootstrap_percentile"


def _cases(spec: list[tuple[int, int, int]]) -> tuple[np.ndarray, np.ndarray]:
    """``(count, events, non_events)`` triples -> labels and case ids, one id per case."""
    y: list[int] = []
    ids: list[str] = []
    for j, (count, ev, ne) in enumerate(spec):
        for i in range(count):
            y += [1] * ev + [0] * ne
            ids += [f"s{j}u{i}"] * (ev + ne)
    return np.array(y, dtype=bool), np.array(ids, dtype=object)


PREVALENCE_SHAPES: list[tuple[str, list[tuple[int, int, int]], bool]] = [
    # (name, [(cases, events, non-events), ...], every draw carries the cohort prevalence)
    ("mixed (1,1) x 30 + (2,2) x 30", [(30, 1, 1), (30, 2, 2)], True),  # lens 2 FA-N1 A
    (
        "pure 10 / 10 one-row + mixed (1,1) x 20 + (2,2) x 20",
        [(10, 1, 0), (10, 0, 1), (20, 1, 1), (20, 2, 2)],
        True,
    ),  # FA-N1 B
    (
        "pure 10 / 12 one-row + mixed (1,1) x 20 + (2,2) x 20",
        [(10, 1, 0), (12, 0, 1), (20, 1, 1), (20, 2, 2)],
        False,
    ),  # FA-N1 control
    ("mixed (1,2) x 30 + (2,4) x 30", [(30, 1, 2), (30, 2, 4)], True),  # FA-N1 D
    (
        "pure 10 pos / 20 neg one-row + mixed (1,2) x 12 + (2,4) x 12",
        [(10, 1, 0), (20, 0, 1), (12, 1, 2), (12, 2, 4)],
        True,
    ),  # RG-N1
    (
        "pure positive of 1 and 2 rows (5 each) + 10 one-row negatives",
        [(5, 1, 0), (5, 2, 0), (10, 0, 1)],
        False,
    ),
    (
        "mixed (1,1) x 10 + (1,2) x 10 beside 5 one-row pos + 5 one-row neg",
        [(10, 1, 1), (10, 1, 2), (5, 1, 0), (5, 0, 1)],
        False,
    ),  # RG-N5 third bullet
    (
        "mixed (1,1) x 20 + 10 one-row pos + 15 one-row neg",
        [(20, 1, 1), (10, 1, 0), (15, 0, 1)],
        True,
    ),
    ("mixed (1,2) and (2,3) beside 2 one-row pos", [(1, 1, 2), (1, 2, 3), (2, 1, 0)], True),
    (
        "pure cases of one and three rows, 10 of each kind",
        [(10, 1, 0), (10, 3, 0), (10, 0, 1), (10, 0, 3)],
        False,
    ),
    ("100 one-row cases, 30 positive", [(30, 1, 0), (70, 0, 1)], True),
]


def test_the_prevalence_rule_agrees_with_the_resamplers_own_draws_on_eleven_shapes():
    """Lens 2 of 2026-09-18, FA-N1 / RG-N1: the round-1 rule (every unit of a stratum
    carrying identical class counts) returned ``False`` on 30 mixed cases of (1, 1) beside
    30 of (2, 2), whose every draw carries the prevalence 0.5, and ``brier_ref`` rendered
    ``boundary_estimate``. Inspected: for each of the eleven shapes above,
    ``_prevalence_invariant`` on the module's ``clustered_by_case`` resampler equals
    "500 draws of that resampler give one distinct prevalence"; the count of distinct
    prevalences is 1 on the five shapes marked ``True`` and 16, 11, 13, 92 on four of the
    ``False`` ones; and through ``calibration_block`` the first, fourth and fifth shapes
    render ``brier_ref`` as ``fixed_by_outcome_stratification`` (``boundary_estimate`` at
    a5a5ed8) while the control renders ``cluster_bootstrap_percentile`` with an interval."""
    d = decl(clustering={"unit": "case_id", "declared_by": "t"})
    distinct: dict[str, int] = {}
    for name, spec, expect in PREVALENCE_SHAPES:
        y, ids = _cases(spec)
        resampler = clustered_by_case(y, ids)
        g = np.random.default_rng(0)
        prevs = {round(float(y[resampler.draw(g)].mean()), 12) for _ in range(500)}
        distinct[name] = len(prevs)
        assert calibration_module._prevalence_invariant(resampler) is expect, (name, prevs)
        assert (len(prevs) == 1) is expect, (name, len(prevs))
    assert distinct["pure 10 / 12 one-row + mixed (1,1) x 20 + (2,2) x 20"] == 16
    assert distinct["pure positive of 1 and 2 rows (5 each) + 10 one-row negatives"] == 11
    assert distinct["mixed (1,1) x 10 + (1,2) x 10 beside 5 one-row pos + 5 one-row neg"] == 13
    assert distinct["pure cases of one and three rows, 10 of each kind"] == 92
    rng = np.random.default_rng(4)
    for index, reason in ((0, "fixed"), (3, "fixed"), (4, "fixed"), (2, "bootstrapped")):
        name, spec, _ = PREVALENCE_SHAPES[index]
        y, ids = _cases(spec)
        p = rng.uniform(0.2, 0.8, y.shape[0])
        b = calibration_block(
            p, y, d, cluster_ids=ids, policy=BootstrapPolicy(n_resamples=200, seed=3)
        ).block
        ref = b["brier_ref"]["number"]
        pi = y.mean()
        assert ref["est"] == pytest.approx(pi * (1 - pi), abs=1e-12), name
        if reason == "fixed":
            assert ref["not_estimable_reason"] == "fixed_by_outcome_stratification", name
            assert ref["method"] == "none" and ref["ci_lo"] is None, name
        else:
            assert ref["method"] == "cluster_bootstrap_percentile", name
            assert ref["ci_lo"] is not None and ref["ci_lo"] < ref["ci_hi"], name
        assert b["ipa"]["number"]["ci_lo"] is not None, name
        companion = b["brier_ref"]["analytic"]
        assert companion["not_estimable_reason"] == "clustered_data_analytic_ci_invalid"


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


def test_irls_not_converged_at_iteration_one_names_the_step_halving_exit_not_the_budget():
    """Lens 2 of 2026-09-18, FA-N2: the module docstring said ``irls_not_converged`` is
    emitted when the iteration budget runs out; on 50 rows all at ``p = 1.0`` with 12
    events (every score clipped to ``1 - 1e-12``) the offset fit's first Newton step is
    refused by all ``MAX_STEP_HALVINGS`` halvings and the reason is emitted at
    ``iterations: 1`` with the budget of ``IRLS_MAX_ITER`` untouched. Inspected: the
    direct fit and the block's ``intercept_large`` both read ``irls_not_converged`` at
    iteration 1; the joint model on the same rows is ``constant_score``; the block
    serialises without NaN; and the docstring names that exit (the sentences test greps
    the old one out)."""
    p = np.full(50, 1.0)
    y = np.zeros(50, dtype=bool)
    y[:12] = True
    clipped = np.clip(p, CLIP_EPS, 1 - CLIP_EPS)
    fit = calibration_module._fit_offset(y.astype(float), np.log(clipped / (1 - clipped)))
    assert fit.reason == "irls_not_converged" and fit.iterations == 1 < IRLS_MAX_ITER
    assert fit.beta is None and fit.se is None
    b = block(p, y, policy=BootstrapPolicy(n_resamples=50, seed=1))
    cell = b["intercept_large"]
    assert cell["number"]["not_estimable_reason"] == "irls_not_converged"
    assert cell["detail"]["iterations"] == 1 and cell["detail"]["outcome"] == "irls_not_converged"
    assert "scores_clipped_for_logit" in cell["number"]["flags"] and b["n_clipped"] == 50
    assert b["slope"]["number"]["not_estimable_reason"] == "constant_score"
    json.dumps(b, allow_nan=False)
    doc = calibration_module.__doc__
    assert "halvings of one Newton step all raise the deviance" in doc
    assert "detail.iterations`` is then that step's index: 1 on 50 rows all at ``p = 1.0``" in doc


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


@pytest.mark.parametrize("n", [1, 2, 5, 9])
@pytest.mark.parametrize("route", ["none", "declared"])
def test_a_cohort_of_one_to_nine_rows_renders_ten_bins_with_the_empty_ones_zero_denominator(
    n, route
):
    """Lens 1 of 2026-09-18, FA-B2 / RG-B1: ``calibration_block`` raised numpy's
    ``zero-size array to reduction operation maximum`` for N = 1..9 at b93e050.
    Inspected at N = 1, 2, 5, 9, i.i.d. and under a declared plan of two-row case ids:
    a block is returned, it validates against ``calibrationBlock``, ten bins are present,
    bins ``n + 1``.. 10 carry ``n: 0`` and ``zero_denominator``, ``ece_equal_mass_10.edges``
    has ``n + 1`` entries, and the JSON has no NaN."""
    p = np.random.default_rng(n).uniform(0.1, 0.9, n)
    y = np.arange(n) % 2 == 0
    ids = None
    crit: dict[str, Any] = {}
    if route == "declared":
        ids = np.array([f"c{i // 2}" for i in range(n)], dtype=object)
        crit = {"clustering": {"unit": "case_id", "declared_by": "t"}}
    res = calibration_block(
        p, y, decl(**crit), cluster_ids=ids, policy=BootstrapPolicy(n_resamples=50, seed=1)
    )
    b = res.block
    assert b is not None and b["n"] == n and b["clustering_route"] == route
    json.dumps(res.as_document(), allow_nan=False)
    schema = load_json_schema("output_schema_v1.json")
    v = jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/calibrationBlock", "$defs": schema["$defs"]}
    )
    assert list(v.iter_errors(b)) == []
    assert len(b["decile_curve"]) == 10
    for i, d_ in enumerate(b["decile_curve"]):
        if i < n:
            assert d_["n"] == 1 and d_["mean_pred"] is not None
        else:
            assert d_["n"] == 0 and d_["events"] == 0 and d_["mean_pred"] is None
            assert d_["observed"]["number"]["not_estimable_reason"] == "zero_denominator"
    assert len(b["ece_equal_mass_10"]["edges"]) == n + 1
    assert b["ece_equal_mass_10"]["edges"][-1] == float(p.max())
    for key in QUANTITIES:
        Number(**b[key]["number"])


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


def test_the_sentences_the_day6_lenses_falsified_are_gone_from_the_shipped_text():
    """The day-5 pattern: each phrase below was asserted in shipped text at the named sha
    (b93e050 for the lens-1 list, a5a5ed8 for the lens-2 list; each was grepped there,
    whitespace collapsed, before it was listed) and falsified by a constructed input run
    by that lens (the finding id beside it). Inspected: the phrase is absent from the
    named file with runs of whitespace collapsed to one space (lens 2 FA-N6: one lens-1
    phrase was line-wrapped at b93e050 and its assertion observed nothing), and the ECE
    reason string a customer's block carries does not claim what happens in every
    resample."""
    src = REPO / "src" / "proofpack" / "stats"
    files = {
        "calibration.py": src / "calibration.py",
        "descriptive.py": src / "descriptive.py",
        "number.py": src / "number.py",
        "f4_expected.json": REPO / "fixtures" / "f4_expected.json",
        "coverage_calibration.py": REPO / "scripts" / "coverage_calibration.py",
    }
    texts = {k: " ".join(path.read_text(encoding="utf-8").split()) for k, path in files.items()}
    gone_at_b93e050 = [
        ("calibration.py", "overstates it in every resample"),  # FA-B4 / RG-B2
        ("calibration.py", "calibration_curve"),  # FA-N4
        ("calibration.py", "or whose cases mix outcomes the prevalence does vary"),  # FA-B3
        ("calibration.py", "no mixed stratum"),  # FA-B3
        ("calibration.py", "flags.append("),  # FA-N7: number.py's in-place sentence
        ("descriptive.py", "no row value, header or id leaves this module"),  # FA-N3
        ("f4_expected.json", "its SE equals the observed information at the MLE"),  # FA-N1
        ("f4_expected.json", "penultimate iteration's weights"),  # RG-N4
    ]
    gone_at_a5a5ed8 = [
        ("calibration.py", "is the same in every draw exactly when"),  # FA-N1 / RG-N1
        ("calibration.py", "Whether every resample keeps the prevalence"),  # FA-N1 / RG-N1
        ("calibration.py", "are fixed exactly when every one of its units"),  # FA-N1 / RG-N1
        ("calibration.py", "when the iteration budget runs out"),  # FA-N2
        ("calibration.py", "varies from draw to draw"),  # RG-N5
        ("calibration.py", "at the same integer in every draw whenever"),  # RG-N5
        ("number.py", "every mixed case carries one event"),  # RG-N5
        ("number.py", "the iteration budget ran out"),  # FA-N2
        ("descriptive.py", "numeric row value is a key or a value here"),  # RG-N5
        ("coverage_calibration.py", "is the same integer in every draw"),  # RG-N5
    ]
    for name, phrase in gone_at_b93e050 + gone_at_a5a5ed8:
        assert phrase not in texts[name], (name, phrase)
    _, p, y = cohort_arrays(n=100)
    b = block(p, y)
    for key in ("ece_equal_width_10", "ece_equal_mass_10"):
        why = b[key]["ci_not_computed_because"]
        assert "every resample" not in why and "overstates" not in why
        assert "no coverage run" in why and "0.90" in why
