"""Hypothesis fuzz on the input schema and the declarations loader.

Invariant: for any table (mixed types, NaNs, duplicate ids, single-class sites,
unknown levels) and any mutated criteria mapping, ingest either succeeds with
consistent flow counts or raises :class:`HaltError` - never any other exception.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from conftest import make_criteria
from proofpack.errors import HALT_CODES, SCHEMA_CODES, HaltError
from proofpack.gates import auroc_mann_whitney, ingest
from proofpack.io import declare
from proofpack.io.schema import coarsen_date, table_from_columns

pytestmark = pytest.mark.day1

# Each column is drawn from a clean pool most of the time and a dirty pool sometimes, so
# both the success path and every S-/H-code are exercised.
_clean_label = st.sampled_from(["0", "1", 0, 1])
_dirty_label = st.sampled_from(["0", "1", "2", "indeterminate", "", "NA", None, 1.0, True])
_clean_score = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_dirty_score = st.one_of(
    st.floats(min_value=-0.5, max_value=1.5, allow_nan=False, allow_infinity=False),
    st.sampled_from(["", "NA", "abc", None, float("nan"), "inf"]),
)
_clean_level = st.sampled_from(["F", "M"])
_dirty_level = st.sampled_from(["F", "M", "X", "", "unknown", None])
_site = st.sampled_from(["S1", "S2", "S3", None])
_rid = st.one_of(st.integers(min_value=0, max_value=5), st.none())
_clean_date = st.sampled_from(["2026-01-01", "2025-12-31", "2026-07-04"])
_dirty_date = st.sampled_from(["2026-01-01", "bad", None, "2026-13-01"])


@st.composite
def _column(draw, clean, dirty, n):
    pool = dirty if draw(st.integers(0, 4)) == 0 else clean
    return draw(st.lists(pool, min_size=n, max_size=n))


@st.composite
def tables(draw):
    n = draw(st.integers(min_value=0, max_value=40))
    cols = {
        "y_true": draw(_column(_clean_label, _dirty_label, n)),
        "score": draw(_column(_clean_score, _dirty_score, n)),
        "sex": draw(_column(_clean_level, _dirty_level, n)),
        "site": draw(st.lists(_site, min_size=n, max_size=n)),
        "age": draw(st.lists(st.one_of(st.integers(0, 120), st.none()), min_size=n, max_size=n)),
    }
    if draw(st.booleans()):
        cols["row_id"] = draw(st.lists(_rid, min_size=n, max_size=n))
    if draw(st.booleans()):
        cols["case_id"] = draw(st.lists(_rid, min_size=n, max_size=n))
    if draw(st.integers(0, 3)) == 0:
        cols["y_pred"] = draw(_column(_clean_label, _dirty_label, n))
    if draw(st.integers(0, 3)) == 0:
        cols["event_date"] = draw(_column(_clean_date, _dirty_date, n))
    if draw(st.integers(0, 5)) == 0:
        cols.pop("score")
        if "y_pred" not in cols:
            cols["y_pred"] = draw(_column(_clean_label, _dirty_label, n))
    return cols


@st.composite
def criteria_variants(draw):
    crit = make_criteria()
    if draw(st.booleans()):
        crit["indeterminates"] = {"policy": "report_both_ways", "values": ["indeterminate", "2"]}
    if draw(st.booleans()):
        crit["clustering"] = {"unit": "case_id", "declared_by": "fuzz"}
    if draw(st.booleans()):
        crit["period"] = {
            "column": "event_date",
            "granularity": draw(st.sampled_from(["quarter", "month", "year"])),
        }
    if draw(st.integers(0, 3)) == 0:
        crit["score"]["type"] = draw(st.sampled_from(["logit", "other"]))
    if draw(st.integers(0, 3)) == 0:
        crit["score"]["orientation"] = "lower_is_positive"
    if draw(st.integers(0, 3)) == 0:
        crit["criteria"][0]["scope"] = {
            "attribute": draw(st.sampled_from(["sex", "site", "race"])),
            "level": draw(st.sampled_from(["F", "*", "Q"])),
        }
    if draw(st.booleans()):
        crit["subgroups"] = [s for s in crit["subgroups"] if s["attribute"] != "age"]
    return crit


@settings(
    max_examples=300,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(cols=tables(), crit=criteria_variants())
def test_ingest_halts_or_succeeds_never_crashes(cols, crit):
    decl = declare.validate_dict(crit)
    try:
        res = ingest(table_from_columns(cols), decl)
    except HaltError as exc:
        assert exc.code in HALT_CODES or exc.code in SCHEMA_CODES
        assert exc.exit_code == 3
        return
    t = res.table
    f = t.flow
    n_dev = 0
    assert (
        (
            f.included
            + f.excluded_missing_y_true
            + f.excluded_missing_score
            + f.indeterminate
            + n_dev
        )
        == f.n_rows
        == len(cols["y_true"])
    )
    assert res.mask.sum() == f.included
    assert f.included > 0  # H06 guarantees analysable rows with both classes
    for a, arr in t.attributes.items():
        assert None not in arr.tolist(), a  # missing -> "Unknown/missing", never dropped
    if t.period is not None:
        for v in t.period.tolist():
            assert v is None or len(v) <= 7  # coarsened, never a full date
    if t.score is not None and decl.score_type == "probability":
        s = t.score[~np.isnan(t.score)]
        assert ((s >= 0) & (s <= 1)).all()


_key_pool = [
    "schema_version",
    "model",
    "task",
    "classes",
    "score",
    "operating_points",
    "reference_standard",
    "indeterminates",
    "clustering",
    "prevalence",
    "subgroups",
    "criteria",
    "fairness",
    "ledger",
    "period",
    "egress",
    "bootstrap",
]


@settings(max_examples=200, deadline=None)
@given(
    drop=st.lists(st.sampled_from(_key_pool), max_size=4),
    junk=st.dictionaries(
        st.sampled_from(_key_pool),
        st.one_of(
            st.none(),
            st.integers(),
            st.text(max_size=5),
            st.lists(st.integers(), max_size=2),
            st.dictionaries(st.text(max_size=4), st.integers(), max_size=2),
        ),
        max_size=3,
    ),
)
def test_declare_only_h08_or_h09(drop, junk):
    crit = make_criteria()
    for k in drop:
        crit.pop(k, None)
    crit.update(junk)
    try:
        declare.validate_dict(crit)
    except HaltError as exc:
        assert exc.code in ("H08", "H09")


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.sampled_from(["author", "date", "justification"]), min_size=1, max_size=3),
    st.sampled_from(["", "   ", None]),
)
def test_declare_authored_fields_required(fields, blank):
    crit = make_criteria()
    for f in fields:
        crit["criteria"][0][f] = blank
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(crit)
    assert ei.value.code == "H08"


@settings(max_examples=100, deadline=None)
@given(
    st.integers(1900, 2100),
    st.integers(1, 12),
    st.integers(1, 28),
    st.sampled_from(["quarter", "month", "year"]),
)
def test_coarsen_date_never_keeps_day(y, m, d, g):
    out = coarsen_date(f"{y:04d}-{m:02d}-{d:02d}", g)
    assert f"{d:02d}" not in out[5:] or g != "quarter"
    assert len(out) in (4, 7)
    if g == "quarter":
        assert out.endswith(f"Q{(m - 1) // 3 + 1}")


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.floats(0, 1, allow_nan=False), min_size=2, max_size=60),
    st.lists(st.booleans(), min_size=2, max_size=60),
)
def test_auroc_matches_scipy_mann_whitney(scores, flags):
    scipy_stats = pytest.importorskip("scipy.stats")
    n = min(len(scores), len(flags))
    s = np.array(scores[:n])
    pos = np.array(flags[:n], dtype=bool)
    if pos.sum() == 0 or (~pos).sum() == 0:
        return
    u = scipy_stats.mannwhitneyu(s[pos], s[~pos], alternative="two-sided").statistic
    expected = u / (pos.sum() * (~pos).sum())
    assert math.isclose(auroc_mann_whitney(s, pos), expected, abs_tol=1e-12)
