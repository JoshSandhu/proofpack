"""F19 (build day 13, E13; D1 section 3.2, section 10 gate 8): the egress bytes of the
synthetic cohort and of a cohort with small cells and real-looking site names
(``proofpack.f19``), searched in every encoded and decoded form ``proofpack.egress.scan``
knows, with the small cells re-derived from ``run.json`` rather than read from the
suppression module.

The CI job ``offline-namespace`` runs this file inside the network namespace its first
step chose (``unshare -rn`` where the runner allows unprivileged user namespaces, ``sudo
unshare -n`` otherwise; the job writes which to ``namespace.txt``, and its three runs at
941c8e4 logged ``sudo unshare -n``) and uploads its log as the artefact
``f19-offline-namespace``. Locally it runs with the network present and the telemetry
transport replaced by a recorder.
"""

from __future__ import annotations

import base64
import json
import socket
import urllib.parse
from pathlib import Path

import pytest
import yaml

from proofpack import f19
from proofpack.egress import build as build_mod
from proofpack.egress import scan, suppress

pytestmark = [pytest.mark.day13, pytest.mark.fixture]
#: ``socket.socket`` as this module imported it, before any F19 run installs the guard.
SOCKET_TAKEN_AT_IMPORT = socket.socket
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


def test_f19_a_send_that_calls_getaddrinfo_and_create_connection_itself_is_counted(
    tmp_path: Path, monkeypatch
):
    """Planted: the telemetry send ignores the transport it is given and calls
    ``socket.getaddrinfo`` and then ``socket.create_connection`` itself, through the module
    attributes, to a ``.invalid`` host (RFC 6761, never resolves). The socket guard refuses
    both and counts them; nothing is recorded. A socket made through another name is not
    counted: :func:`test_f19_a_socket_made_through_a_reference_taken_before_the_run_is_not_counted`.

    Gate repair (run 37453449607, job offline-namespace, at fdc2a25): the first version of
    this plant went through the real urllib transport restored from ``conftest``; it
    passed on win-amd64-cp314 and in the CI job ``pytest + ruff``, and failed inside the
    job's namespace (``sudo unshare -n`` on that run) with ``socket_calls`` 0 - the urllib
    path never reached a patched
    socket function there. Why was not diagnosed [unverified]; the plant now opens the
    socket itself, so it measures the guard and nothing else."""
    import socket

    from proofpack.egress import telemetry

    def bypass(payload, url=telemetry.TELEMETRY_URL, transport=None, *, timeout=1.0):
        for attempt in (
            lambda: socket.getaddrinfo("f19-plant.invalid", 80),
            lambda: socket.create_connection(("f19-plant.invalid", 80), timeout=1.0),
        ):
            try:
                attempt()
            except OSError:
                pass
        return telemetry.SendResult(False, None, "transport_error")

    monkeypatch.setattr(telemetry, "send", bypass)
    r = f19.run_cohort("planted", f19.synthetic_cohort(), tmp_path / "w")
    assert r["socket_calls"] == 2 and r["telemetry_sends"] == 0
    assert "planted: socket_calls" in f19.check(r)
    assert "planted: telemetry_sends" in f19.check(r)


@pytest.mark.parametrize("route", ["reference_taken_at_import", "_socket.socket"])
def test_f19_a_socket_made_through_a_reference_taken_before_the_run_is_not_counted(
    tmp_path: Path, monkeypatch, route: str
):
    """The limit of the guard (E13 lens 1 counter-examples FA-B4 and RG-B1): the send
    makes a socket through ``socket.socket`` as this module imported it (before the guard
    is installed) or through ``_socket.socket``, closes it unconnected, then sends through
    the recorder as the real send does. The socket is made (not refused), ``socket_calls``
    is 0 and every F19 check passes. ``f19``'s docstring says only calls that reach the
    three module attributes are seen; this test pins that sentence's limit."""
    import _socket

    from proofpack.egress import telemetry

    real_send = telemetry.send
    made: list[str] = []

    def send(*args, **kwargs):
        early = route == "reference_taken_at_import"
        sock = SOCKET_TAKEN_AT_IMPORT() if early else _socket.socket()
        made.append(type(sock).__name__)
        sock.close()
        return real_send(*args, **kwargs)

    monkeypatch.setattr(telemetry, "send", send)
    r = f19.run_cohort("limit", f19.small_cell_cohort(), tmp_path / "w")
    assert len(made) == 1
    assert r["socket_calls"] == 0 and r["telemetry_sends"] == 1
    assert f19.check(r) == []


def test_f19_the_socket_guard_refuses_counts_and_restores():
    import socket

    before = (socket.socket, socket.getaddrinfo, socket.create_connection)
    with f19._no_sockets() as calls:
        for name, call in (
            ("socket", lambda: socket.socket()),
            ("getaddrinfo", lambda: socket.getaddrinfo("f19-plant.invalid", 80)),
            ("create_connection", lambda: socket.create_connection(("f19-plant.invalid", 80))),
        ):
            with pytest.raises(OSError, match=f"socket.{name} refused"):
                call()
    assert calls == ["socket", "getaddrinfo", "create_connection"]
    assert (socket.socket, socket.getaddrinfo, socket.create_connection) == before


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
    assert 'NS="unshare -rn"' in runs and 'NS="sudo unshare -n"' in runs
    assert 'echo "$NS" > namespace.txt' in runs
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
