"""Build day 11 (E11) item 4, DEC-70 (a): the Newcombe 1998 (paired data) fetch.

Fetched once on 2 October 2026, a free copy only: the DOI resolves (302) to Wiley, which
returned 403 (nothing paid, no sign-in); one web search named an openly hosted course copy
(``eiti.uottawa.ca``), which returned the publisher's typeset PDF (16 pages, SHA-256
``90a3a049...0f87``). Its page 5 prints methods 8 and 10, and pages 7-8 print Table III; the
method 10 rows are transcribed into ``fixtures/newcombe1998_paired.json``.

* This test's own Wilson / method 10 derivation (written here from the printed formula, no
  repository code) reproduces all 35 compared limits to the printed four decimals; the one
  excluded limit (``e 1 f 97 g 1 h 1`` lower, printed 0.8736 for method 10 and 0.8737 for
  method 8, which the paper's definition makes the same number when ``eh < fg``) rounds to
  0.8737.
* ``proportions.difference_paired`` equals that derivation to 1e-12 on all 18 rows and on
  F5's ``e 80, f 2, g 10, h 8`` (``-0.08 [-0.1554, -0.0102]``).
* The register row ``F5-newcombe-paired`` is ``matched`` on 35 values with no
  ``[unverified]`` marking (at ``ad66073`` it was ``no_independent_oracle``, ``[unverified]``).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from proofpack import fixtures as fx
from proofpack.stats.proportions import difference_paired

pytestmark = pytest.mark.day11

REPO = Path(__file__).resolve().parent.parent
TRANSCRIPTION = REPO / "fixtures" / "newcombe1998_paired.json"
Z = 1.959963984540054


def _wilson(k: int, n: int) -> tuple[float, float]:
    """Roots of |pi - k/n| = z sqrt(pi (1 - pi) / n) (page 5's definition of l, u)."""
    p = k / n
    centre = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return centre - half, centre + half


def method10(e: int, f: int, g: int, h: int) -> tuple[float, float, float]:
    """Page 5: theta-hat = (f - g) / n; delta, epsilon from the Wilson limits of (e + f)/n
    and (e + g)/n and phi-hat, whose numerator eh - fg is replaced by max(eh - fg - n/2, 0)
    when eh > fg; phi-hat = 0 when its denominator is 0."""
    n = e + f + g + h
    p2, p3 = (e + f) / n, (e + g) / n
    l2, u2 = _wilson(e + f, n)
    l3, u3 = _wilson(e + g, n)
    num = e * h - f * g
    if num > 0:
        num = max(num - n / 2, 0)
    den = math.sqrt((e + f) * (g + h) * (e + g) * (f + h))
    phi = 0.0 if den == 0 else num / den
    dl2, du2, dl3, du3 = p2 - l2, u2 - p2, p3 - l3, u3 - p3
    delta = math.sqrt(max(dl2**2 - 2 * phi * dl2 * du3 + du3**2, 0.0))
    eps = math.sqrt(max(du2**2 - 2 * phi * du2 * dl3 + dl3**2, 0.0))
    theta = (f - g) / n
    return theta, theta - delta, theta + eps


@pytest.fixture(scope="module")
def table() -> dict:
    return json.loads(TRANSCRIPTION.read_text(encoding="utf-8"))


def test_the_transcription_records_its_primary_source_and_its_one_exclusion(table):
    prov = table["provenance"]
    assert prov["transcribed_from_primary_pdf"] is True
    assert "90a3a04944c41bebde4d92d4b9cce9c77f3b67f407433b7a103bebc35e0d0f87" in " ".join(
        prov["attempts"]
    )
    assert "403" in prov["attempts"][1] and "302" in prov["attempts"][0]
    assert "[unverified" not in json.dumps(table)
    cells = [(r["e"], r["f"], r["g"], r["h"]) for r in table["rows"]]
    assert cells == [c[:4] for c in fx.F5_NEWCOMBE_PAIRED_CASES]
    [x] = table["excluded"]
    assert (x["e"], x["f"], x["g"], x["h"], x["value"]) == (1, 97, 1, 1, "method10 lower")
    assert (x["printed"], x["printed_method8_same_row"]) == (0.8736, 0.8737)


def test_the_hand_derivation_reproduces_every_compared_printed_limit(table):
    half = 0.5e-4 + 1e-12
    compared = 0
    for r in table["rows"]:
        _, lo, hi = method10(r["e"], r["f"], r["g"], r["h"])
        for side, value in (("lower", lo), ("upper", hi)):
            if side in r["method10"]:
                assert abs(value - r["method10"][side]) <= half, (r, side, value)
                compared += 1
    assert compared == 35
    # the excluded limit: eh - fg < 0, so methods 8 and 10 coincide; 0.8737 is method 8's
    _, lo, _ = method10(1, 97, 1, 1)
    assert round(lo, 4) == 0.8737 and abs(lo - 0.873672) < 1e-6


def test_difference_paired_equals_the_hand_derivation_on_table_iii_and_f5(table):
    rows = [(r["e"], r["f"], r["g"], r["h"]) for r in table["rows"]] + [(80, 2, 10, 8)]
    for cells in rows:
        num = difference_paired(*cells)
        theta, lo, hi = method10(*cells)
        assert num.method == "newcombe_paired"
        assert abs(num.est - theta) <= 1e-12 and abs(num.ci_lo - lo) <= 1e-12
        assert abs(num.ci_hi - hi) <= 1e-12, cells
    f5 = difference_paired(80, 2, 10, 8)
    assert (round(f5.est, 4), round(f5.ci_lo, 4), round(f5.ci_hi, 4)) == (-0.08, -0.1554, -0.0102)


def test_the_register_row_is_matched_on_35_values_with_no_unverified_marking():
    report = fx.run_fixtures(doctor=False)
    row = next(r for r in report["rows"] if r["id"] == "F5-newcombe-paired")
    assert row["status"] == "matched" and row["n_values_compared"] == 35
    assert row["max_abs_deviation"] <= fx.rounding_tolerance(4)
    src = row["oracle_source"]
    assert src["kind"] == "published_table" and src["unverified"] is False
    assert src["file"] == "fixtures/newcombe1998_paired.json"
    assert "e 1 f 97 g 1 h 1 method10 lower not compared" in src["detail"]
    assert "[unverified" not in json.dumps(row)
    assert report["summary"]["no_independent_oracle"] == 0


def test_the_paired_method_cites_the_verified_entry_only():
    import yaml

    doc = yaml.safe_load((REPO / "design" / "citations.yaml").read_text(encoding="utf-8"))
    users = [c for c in doc["citations"] if "newcombe_paired" in (c.get("used_by") or [])]
    assert [c["id"] for c in users] == ["newcombe_1998_paired"]
    assert users[0]["verified"] is True
