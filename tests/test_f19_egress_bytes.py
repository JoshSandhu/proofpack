"""F19 (build day 13, E13; D1 section 3.2, section 10 gate 8): the egress bytes of the
synthetic cohort and of a cohort with small cells and real-looking site names
(``proofpack.f19``), searched in every encoded and decoded form ``proofpack.egress.scan``
knows, with the small cells re-derived from ``run.json`` rather than read from the
suppression module.

The CI job ``offline-namespace`` runs this file inside ``unshare -rn`` and uploads its
log as the artefact ``f19-offline-namespace``; locally it runs with the network present
and the telemetry transport replaced by a recorder (no socket is opened).
"""

from __future__ import annotations

import base64
import json
import urllib.parse
from pathlib import Path

import pytest
import yaml

from proofpack import f19
from proofpack.egress import build as build_mod
from proofpack.egress import scan, suppress

pytestmark = [pytest.mark.day13, pytest.mark.fixture]
REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def results() -> dict[str, dict]:
    return {r["cohort"]: r for r in f19.run_all()}


def test_f19_both_cohorts_pass_every_check(results):
    assert set(results) == {"synthetic", "small_cell_real_site_names"}
    for r in results.values():
        assert f19.check(r) == [], r["cohort"]
        assert r["telemetry_sends"] == 1 and r["telemetry_valid"] and r["aggregates_valid"]
        assert r["hits"] == []


def test_f19_the_small_cells_are_the_two_planted_sites_and_every_one_of_their_cells_is_null(
    results,
):
    r = results["small_cell_real_site_names"]
    assert r["small_rows"] == [
        {"attribute": "site", "level": f19.ADDENBROOKES, "n": 9, "events": 4},
        {"attribute": "site", "level": f19.ST_MARYS, "n": 7, "events": 2},
    ]
    assert r["small_cells"] == 14 and r["small_cells_unsuppressed"] == 0
    assert r["structural_violations"] == [] and r["small_value_hits"] == []
    # the small rows' own Numbers hold floats found nowhere else in run.json; they were
    # searched among the parsed payload numbers and (the long ones) in the bytes
    assert r["small_only_values"] >= 50 and r["needles"] > 7
    assert r["sites"] == 5 and r["sites_pseudonymised"] is True
    assert r["socket_calls"] == 0 and r["aggregates_error"] is None
    syn = results["synthetic"]
    assert syn["small_rows"] == [] and syn["sites"] == 3 and syn["socket_calls"] == 0


def test_f19_the_site_names_are_not_in_any_egress_byte_in_any_form(results):
    r = results["small_cell_real_site_names"]
    names = {
        "a": f19.ST_MARYS,
        "b": f19.ADDENBROOKES,
        "c": f19.KONIGSBERG,
        "d": f19.GUYS,
        "e": f19.ROYAL_FREE,
        "f": f19.NOTE_HEADER,
        "g": f19.NOTE_VALUE,
    }
    assert scan.find(r["bytes"], names) == []
    # and nothing a reader would recognise as the start of one
    for b in r["bytes"].values():
        text = b.decode("utf-8")
        for stem in ("Mary", "Addenbrooke", "nigsberg", "Thomas", "Royal", "clinic"):
            assert stem not in text, stem


@pytest.mark.parametrize(
    "form,payload",
    [
        ("utf8", b'{"site": "St Mary\'s"}'),
        ("json_ascii", json.dumps({"s": "Königsberg"}, ensure_ascii=True).encode()),
        ("percent", ("q=" + urllib.parse.quote("Guy's & St Thomas'", safe="")).encode()),
        ("percent_plus", ("q=" + urllib.parse.quote_plus("Royal Free")).encode()),
    ],
)
def test_the_scanner_finds_a_planted_name_in_each_encoded_form(form, payload):
    needles = {
        "st marys": f19.ST_MARYS,
        "konigsberg": f19.KONIGSBERG,
        "guys": f19.GUYS,
        "royal free": f19.ROYAL_FREE,
    }
    hits = scan.find({"p": payload}, needles)
    assert any(h["form"] == form for h in hits), hits


@pytest.mark.parametrize("prefix", [b"", b"x", b"xy", b"xyz", b'{"a":1,"b":"'])
def test_the_scanner_finds_a_name_inside_base64_at_every_alignment(prefix):
    blob = base64.b64encode(prefix + b"St Mary's" + b" and more bytes after it")
    hits = scan.find({"p": b'{"token":"' + blob + b'"}'}, {"st marys": f19.ST_MARYS})
    forms = {h["form"] for h in hits}
    assert "view:base64_decoded" in forms
    assert any(f.startswith("base64_offset") for f in forms), forms


def test_the_scanner_is_case_insensitive_for_long_needles_and_not_for_short_ones():
    assert scan.find({"p": b'"ST MARY\'S"'}, {"n": f19.ST_MARYS})
    assert scan.find({"p": b'"s1"'}, {"n": "S1"}) == []
    assert scan.find({"p": b'"S1"'}, {"n": "S1"})


def _projection_without_suppression(number, thresholds, *, row_suppressed=False):
    if number is None:
        return suppress.suppressed_number()
    return {
        "est": number.get("est"),
        "ci_lo": number.get("ci_lo"),
        "ci_hi": number.get("ci_hi"),
        "method": number.get("method"),
        "n": number.get("n"),
        "k": number.get("k") if isinstance(number.get("k"), int) else None,
        "suppressed": False,
    }


def test_f19_k_suppression_removed_is_refused_by_the_schema_floor(tmp_path: Path, monkeypatch):
    """Planted: k-suppression removed from the Number projection. The aggregates document
    then carries n 9 and n 7; ``egress_schema.json``'s ``minimum: 10`` on ``n`` refuses it,
    build_aggregates raises (nothing is built, so nothing could be sent) and F19 fails."""
    monkeypatch.setattr(suppress, "project_number", _projection_without_suppression)
    r = f19.run_cohort("planted", f19.small_cell_cohort(), tmp_path / "w")
    assert "less than the minimum of 10" in r["aggregates_error"]
    assert "planted: aggregates_error" in f19.check(r)
    assert "planted: aggregates_valid" in f19.check(r)


def test_f19_small_cell_values_with_their_counts_nulled_are_caught(tmp_path: Path, monkeypatch):
    """Planted: suppression that nulls ``n`` and ``k`` but keeps the estimate and the
    interval, so the schema floor on ``n`` is not reached. F19 finds the small rows'
    cells unsuppressed, their values among the payload numbers and in the bytes."""
    real = suppress.project_number

    def leaky(number, thresholds, *, row_suppressed=False):
        out = real(number, thresholds, row_suppressed=row_suppressed)
        if out["suppressed"] and number is not None:
            # the schema refuses a value beside suppressed: true, so the plant also says
            # suppressed: false, with n and k null
            out = dict(out, est=number.get("est"), ci_lo=number.get("ci_lo"))
            out.update(ci_hi=number.get("ci_hi"), method=number.get("method"), suppressed=False)
        return out

    monkeypatch.setattr(suppress, "project_number", leaky)
    r = f19.run_cohort("planted", f19.small_cell_cohort(), tmp_path / "w")
    assert r["aggregates_error"] is None and r["aggregates_valid"] is True
    assert r["small_cells_unsuppressed"] > 0
    assert r["structural_violations"] and r["small_value_hits"]
    assert any(h["needle"].startswith("small-only value ") for h in r["hits"])
    failed = f19.check(r)
    for name in ("small_cells_unsuppressed", "structural_violations", "small_value_hits", "hits"):
        assert f"planted: {name}" in failed


def test_f19_a_send_that_bypasses_the_recorder_is_counted_and_refused(tmp_path: Path, monkeypatch):
    """Planted: the telemetry send ignores the transport it is given and calls the real
    urllib transport. The socket guard refuses the connection and counts it; nothing is
    recorded. The real transport is restored for this test only (conftest replaces it
    with a refusing one) and the URL is under ``.invalid`` (RFC 6761: never resolves)."""
    from conftest import REAL_TRANSPORT
    from proofpack.egress import telemetry

    real_send = telemetry.send

    def bypass(payload, url=telemetry.TELEMETRY_URL, transport=None, *, timeout=1.0):
        return real_send(payload, url="http://f19-plant.invalid/", transport=None, timeout=1.0)

    monkeypatch.setattr(telemetry, "urllib_transport", REAL_TRANSPORT)
    monkeypatch.setattr(telemetry, "send", bypass)
    r = f19.run_cohort("planted", f19.synthetic_cohort(), tmp_path / "w")
    assert r["socket_calls"] >= 1 and r["telemetry_sends"] == 0
    assert "planted: socket_calls" in f19.check(r)
    assert "planted: telemetry_sends" in f19.check(r)


def test_f19_a_site_name_that_bypasses_pseudonymisation_is_caught(tmp_path: Path, monkeypatch):
    """Planted: the aggregates document's bytes carry an original site name (the schema
    would refuse it as a level, so it is planted after the build)."""
    from proofpack import egress

    real = egress.build_aggregates

    def leaky(doc, thresholds=None):
        agg, pmap = real(doc, thresholds)
        agg = dict(agg)
        agg["cells"] = [dict(agg["cells"][0], note=f19.ST_MARYS), *agg["cells"][1:]]
        return agg, pmap

    monkeypatch.setattr(egress, "build_aggregates", leaky)
    r = f19.run_cohort("planted", f19.small_cell_cohort(), tmp_path / "w")
    assert any(h["needle"] == f"site {f19.ST_MARYS}" for h in r["hits"])
    assert "planted: aggregates_valid" in f19.check(r)


def test_f19_suppression_is_applied_before_the_projection_and_the_serialisation(
    tmp_path: Path, monkeypatch
):
    """The candidate document handed to ``whitelist.project`` already holds the null shape
    for every cell of a small row: suppression is not a step after projection."""
    seen: list[dict] = []
    real = build_mod.whitelist.project

    def spy(candidate, schema, sub, *rest):
        if not rest:  # the top-level call; the recursion passes a path
            seen.append(json.loads(json.dumps(candidate)))
        return real(candidate, schema, sub, *rest)

    monkeypatch.setattr(build_mod.whitelist, "project", spy)
    r = f19.run_cohort("spy", f19.small_cell_cohort(), tmp_path / "w")
    assert f19.check(r) == []
    pmap = json.loads((tmp_path / "w" / "pack" / "pseudonyms.json").read_text("utf-8"))
    labels = {pmap["attributes"]["site"][s] for s in (f19.ST_MARYS, f19.ADDENBROOKES)}
    candidates = [c for c in seen if c.get("schema") == "proofpack-aggregates/1"]
    assert len(candidates) == 1
    small = [c for c in candidates[0]["cells"] if c["attribute"] == "site" and c["level"] in labels]
    assert len(small) == 14
    assert all(c["number"] == suppress.suppressed_number() for c in small)


def test_f19_the_namespace_job_runs_this_file_and_uploads_the_named_artefact():
    ci = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    steps = ci["jobs"][f19.CI_JOB]["steps"]
    runs = "\n".join(str(s.get("run", "")) for s in steps)
    assert "unshare -rn" in runs
    assert (
        "$NS .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_f19_egress_bytes.py"
        in runs
    )
    assert f19.CI_TEST_FILE == "tests/test_f19_egress_bytes.py"
    uploads = [s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert len(uploads) == 1
    assert uploads[0]["with"]["name"] == f19.CI_ARTEFACT == "f19-offline-namespace"
    assert uploads[0]["uses"] == "actions/upload-artifact@v4"  # pinned as ci.yml pins
    for name in ("namespace.txt", "offline.txt", "online.txt", "f19_pytest.txt"):
        assert name in uploads[0]["with"]["path"]
