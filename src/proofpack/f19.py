"""F19 (D1 section 3.2; section 10 gate 8; build day 13, E13): the egress bytes of two
cohorts, built and searched.

D1 section 3.2's F19 row: *run with an intersectional cell n=7, events=2 and site names
"St Mary's"; telemetry payload validates against egress_schema.json; no key outside
whitelist; cell suppressed; "St Mary's" absent from every egress byte; --offline run
completes inside unshare -rn*. The engine tabulates no intersectional (two-attribute)
cell in this version, so the n = 7 cell here is a ``site`` level, the smallest cell the
document tabulates (as ``tests/test_egress.py`` has done since build day 8).

:func:`run_cohort` writes one cohort, its declarations (``egress.telemetry: true``,
suppression 10 / 5 / 5) and a confirmed mapping into a directory and runs ``proofpack
run`` in process (``proofpack.cli.main``) with a recording transport in place of
``urllib``: the bytes recorded are the request body the runner would send. While the run
lasts, ``socket.socket``, ``socket.getaddrinfo`` and ``socket.create_connection`` refuse
and count every call (:func:`_no_sockets`), so a transport that bypassed the recorder
would be counted, not sent. It then builds the ``proofpack-aggregates/1`` document from the
written ``run.json`` (no code path sends it at launch; it is checked because it is the
other document ``egress_schema.json`` describes) and checks, on the bytes of both
documents:

* each validates against its ``egress_schema.json`` definition;
* **small cells** - re-derived here from ``run.json`` with this module's own copy of D1
  section 6's rule (:func:`_counts`, :func:`_is_small`), not with
  :mod:`proofpack.egress.suppress`:

  - every aggregates cell of a small subgroup row is the null shape;
  - every aggregates cell, two-by-two table and calibration bin either is the null shape
    with ``suppressed: true`` or carries counts that clear the thresholds on its own
    bytes (``structural_violations``);
  - no float that ``run.json`` holds only inside a small Number (a Number below the
    thresholds on its own counts, or inside a small row, bin or gap) appears among the
    numbers of either parsed payload (``small_value_hits``; exact equality, every length),
    and none whose ``repr`` has :data:`MIN_VALUE_CHARS` characters or more appears in the
    bytes in any form :func:`proofpack.egress.scan.find` searches. A float that also
    occurs outside the small Numbers is not searched (``small_values_shared``);
* **names** - no site name, no free-text value and no original header appears in either
  document's bytes in any form :func:`proofpack.egress.scan.find` searches.

The network half of gate 8 (``--offline`` inside ``unshare -rn``) is Linux only: the CI
job ``offline-namespace`` (``.github/workflows/ci.yml``) runs it, runs
``tests/test_f19_egress_bytes.py`` inside the same namespace and uploads the logs as the
artefact :data:`CI_ARTEFACT`. This module does not see that run.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
import shutil
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from proofpack import halt_fixtures as hf
from proofpack.egress import scan

CI_ARTEFACT = "f19-offline-namespace"
CI_JOB = "offline-namespace"
CI_TEST_FILE = "tests/test_f19_egress_bytes.py"
SEED = 20240101
ST_MARYS = "St Mary's"
ADDENBROOKES = "Addenbrooke's"
KONIGSBERG = "Königsberg"
GUYS = "Guy's & St Thomas'"
ROYAL_FREE = "Royal Free"
NOTE_HEADER = "clinician_note"
NOTE_VALUE = "seen in clinic on Tuesday"
THRESHOLDS = {"min_n": 10, "min_events": 5, "min_nonevents": 5}
#: Small-only floats whose ``repr`` has this many characters or more are also searched in
#: the payload bytes in every encoded form; a shorter one (``0.5``) recurs inside longer
#: numbers as a substring, so it is compared among the parsed numbers only.
MIN_VALUE_CHARS = 10
#: The telemetry key that is a float and is not a statistic: the run's wall time.
TELEMETRY_NON_STATISTIC_FLOATS = ("duration_s",)


def synthetic_cohort() -> dict[str, list[Any]]:
    """The synthetic cohort (seed 20240101, 400 rows, sites ``S1``-``S3``)."""
    from proofpack.synthetic import make_cohort  # noqa: PLC0415

    return make_cohort(seed=SEED, n=400)


def small_cell_cohort() -> dict[str, list[Any]]:
    """The synthetic rows with real-looking site names: ``St Mary's`` 7 rows (2 events,
    5 non-events), ``Addenbrooke's`` 9 rows, ``Königsberg`` and ``Guy's & St Thomas'``
    60 rows each and ``Royal Free`` the rest, plus a free-text column the mapper
    ignores."""
    cols = synthetic_cohort()
    n = len(cols["y_true"])
    site = [ROYAL_FREE] * n
    spans = ((ST_MARYS, 0, 7), (ADDENBROOKES, 7, 16), (KONIGSBERG, 16, 76), (GUYS, 76, 136))
    for name, lo, hi in spans:
        for i in range(lo, hi):
            site[i] = name
    for i in range(7):
        cols["y_true"][i] = "1" if i < 2 else "0"
    cols["site"] = site
    cols[NOTE_HEADER] = [NOTE_VALUE] * n
    return cols


COHORTS = {"synthetic": synthetic_cohort, "small_cell_real_site_names": small_cell_cohort}


class _Recorder:
    def __init__(self) -> None:
        self.bodies: list[bytes] = []

    def __call__(self, url: str, body: bytes, timeout: float) -> int:
        self.bodies.append(bytes(body))
        return 204


@contextlib.contextmanager
def _no_sockets() -> Iterator[list[str]]:
    """``socket.socket``, ``getaddrinfo`` and ``create_connection`` refuse (``OSError``)
    and are counted for the duration; restored afterwards."""
    import socket  # noqa: PLC0415 - not a network call; kept off module level

    names = ("socket", "getaddrinfo", "create_connection")
    saved = {name: getattr(socket, name) for name in names}
    calls: list[str] = []

    def refuse(name: str):
        def _refused(*args: Any, **kwargs: Any) -> Any:
            calls.append(name)
            raise OSError(f"F19: socket.{name} refused during the F19 run")

        return _refused

    for name in names:
        setattr(socket, name, refuse(name))
    try:
        yield calls
    finally:
        for name, fn in saved.items():
            setattr(socket, name, fn)


def _criteria() -> dict[str, Any]:
    crit = hf.fixture_criteria()
    crit["egress"] = {"telemetry": True, "suppression": dict(THRESHOLDS)}
    return crit


# ------------------------------------------------- the rule, this module's own copy


def _counts(number: Mapping[str, Any]) -> tuple[Any, Any, Any]:
    """``(n, events, nonevents)`` of one engine Number as D1 section 6 reads it: a
    proportion's ``n`` / ``k`` / ``n - k``; a two-class statistic's ``n_pos + n_neg`` /
    ``n_pos`` / ``n_neg``; ``n`` alone otherwise."""
    n, k = number.get("n"), number.get("k")
    n_pos, n_neg = number.get("n_pos"), number.get("n_neg")
    if isinstance(n_pos, int) and isinstance(n_neg, int):
        return (n if isinstance(n, int) else n_pos + n_neg), n_pos, n_neg
    if isinstance(n, int) and isinstance(k, int):
        return n, k, n - k
    return (n if isinstance(n, int) else None), None, None


def _is_small(n: Any, events: Any, nonevents: Any) -> bool:
    """D1 section 6: n below 10, events below 5 or non-events below 5; an unknown ``n``
    cannot be shown to clear the floor."""
    if not isinstance(n, int) or n < THRESHOLDS["min_n"]:
        return True
    if isinstance(events, int) and events < THRESHOLDS["min_events"]:
        return True
    return isinstance(nonevents, int) and nonevents < THRESHOLDS["min_nonevents"]


def _small_row(row: Mapping[str, Any]) -> bool:
    n, events = row.get("n"), row.get("events")
    if not isinstance(n, int) or not isinstance(events, int):
        return True
    return _is_small(n, events, n - events)


def _is_number(d: Mapping[str, Any]) -> bool:
    return "est" in d and "method" in d


def _floats(value: Any, out: list[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            out.append(value)
    elif isinstance(value, Mapping):
        for v in value.values():
            _floats(v, out)
    elif isinstance(value, list):
        for v in value:
            _floats(v, out)


def small_only_values(doc: Mapping[str, Any]) -> tuple[set[float], int, int]:
    """``(values, small Numbers, values shared)``: the finite floats ``run.json`` holds
    inside a small Number - one below the thresholds on its own counts, or one inside a
    small subgroup row, a small calibration bin or a fairness gap of a small level - and
    nowhere else in the document."""
    small_levels = {
        (r.get("attribute"), r.get("level"))
        for r in doc.get("subgroups") or []
        if isinstance(r, Mapping) and _small_row(r)
    }
    f_attr = (doc.get("fairness") or {}).get("attribute")
    inside: list[float] = []
    outside: list[float] = []
    n_small = 0

    def walk(v: Any, forced: bool) -> None:
        nonlocal n_small
        if isinstance(v, Mapping):
            here = forced
            if {"attribute", "level", "n", "events"} <= set(v) and _small_row(v):
                here = True
            if {"bin", "n", "events"} <= set(v) and _small_row(v):
                here = True
            if "level" in v and (f_attr, v.get("level")) in small_levels and "attribute" not in v:
                here = True  # a fairness gap of a small level
            if _is_number(v):
                small = here or _is_small(*_counts(v))
                n_small += small
                _floats(v, inside if small else outside)
                return
            for x in v.values():
                walk(x, here)
        elif isinstance(v, list):
            for x in v:
                walk(x, forced)
        else:
            _floats(v, outside)

    walk(doc, False)
    shared = set(inside) & set(outside)
    return set(inside) - shared, n_small, len(shared)


_NULL_NUMBER = {"est", "ci_lo", "ci_hi", "method", "n", "k"}


def _null_number(num: Mapping[str, Any]) -> bool:
    return num.get("suppressed") is True and all(num.get(k) is None for k in _NULL_NUMBER)


def structural_violations(agg: Mapping[str, Any]) -> list[str]:
    """Every aggregates item that is neither the null shape with ``suppressed: true`` nor
    an item whose own counts clear the thresholds, read from the payload alone."""
    bad: list[str] = []
    for i, c in enumerate(agg.get("cells") or []):
        num = c.get("number") or {}
        if num.get("suppressed") is True:
            if not _null_number(num):
                bad.append(f"cells/{i}: suppressed but carries a value")
            continue
        n, k = num.get("n"), num.get("k")
        if not isinstance(n, int) or n < THRESHOLDS["min_n"]:
            bad.append(f"cells/{i}: unsuppressed with n {n!r}")
        elif isinstance(k, int) and _is_small(n, k, n - k):
            bad.append(f"cells/{i}: unsuppressed with n {n}, k {k}")
    for i, t in enumerate(agg.get("two_by_two") or []):
        values = [t.get(x) for x in ("tp", "fn", "fp", "tn")]
        if t.get("suppressed") is True:
            if any(v is not None for v in values):
                bad.append(f"two_by_two/{i}: suppressed but carries a count")
            continue
        if not all(isinstance(v, int) for v in values):
            bad.append(f"two_by_two/{i}: unsuppressed without four counts")
            continue
        tp, fn, fp, tn = values
        if _is_small(tp + fn + fp + tn, tp + fn, fp + tn):
            bad.append(f"two_by_two/{i}: unsuppressed small table")
    for i, b in enumerate(agg.get("calibration_bins") or []):
        obs = b.get("observed") or {}
        if b.get("suppressed") is True:
            if any(b.get(x) is not None for x in ("n", "events", "mean_pred")) or not (
                _null_number(obs)
            ):
                bad.append(f"calibration_bins/{i}: suppressed but carries a value")
            continue
        n, events = b.get("n"), b.get("events")
        if not isinstance(n, int) or not isinstance(events, int):
            bad.append(f"calibration_bins/{i}: unsuppressed without counts")
        elif _is_small(n, events, n - events):
            bad.append(f"calibration_bins/{i}: unsuppressed small bin")
    return bad


def _payload_floats(payloads: Mapping[str, bytes]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for name, data in payloads.items():
        vals: list[float] = []
        if data:
            doc = json.loads(data.decode("utf-8"))
            if name == "telemetry" and isinstance(doc, dict):
                doc = {k: v for k, v in doc.items() if k not in TELEMETRY_NON_STATISTIC_FLOATS}
            _floats(doc, vals)
        out[name] = vals
    return out


# ---------------------------------------------------------------------- the run


def run_cohort(name: str, cols: dict[str, list[Any]], work: Path) -> dict[str, Any]:
    """One cohort through ``proofpack run`` and the two egress documents (module
    docstring). Returns the measured figures and ``bytes`` (the two payloads)."""
    import jsonschema  # noqa: PLC0415

    from proofpack import egress  # noqa: PLC0415
    from proofpack.cli import main  # noqa: PLC0415
    from proofpack.resources import load_json_schema  # noqa: PLC0415

    work.mkdir(parents=True, exist_ok=True)
    home = work / "home"
    home.mkdir()
    table = hf.write_csv(work / "test.csv", cols)
    yml = hf.write_yaml(work / "criteria.yaml", _criteria())
    hf.confirm_mapping(table)
    out = work / "pack"
    rec = _Recorder()
    argv = ["run", "--input", str(table), "--criteria", str(yml), "--out", str(out)]
    argv += ["--format", "json"]
    with (
        _no_sockets() as socket_calls,
        hf._environment(home),
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        rc = main(argv, transport=rec)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    thresholds = egress.thresholds_from_declarations(doc["declarations"].get("egress"))
    aggregates_error = None
    try:
        agg, pmap = egress.build_aggregates(doc, thresholds)
    except egress.EgressError as exc:
        agg, pmap, aggregates_error = {"cells": []}, {}, str(exc)
    agg_bytes = (
        b"" if aggregates_error else json.dumps(agg, ensure_ascii=False, sort_keys=True).encode()
    )
    tele_bytes = rec.bodies[0] if len(rec.bodies) == 1 else b""
    schema = load_json_schema("egress_schema.json")
    defs = schema["$defs"]

    def valid(document: Any, definition: str) -> bool:
        sub = {"$ref": f"#/$defs/{definition}", "$defs": defs}
        return jsonschema.Draft202012Validator(sub).is_valid(document)

    tele_valid = bool(tele_bytes) and valid(json.loads(tele_bytes), "telemetry")
    agg_valid = aggregates_error is None and valid(agg, "aggregates")
    site_map = pmap.get("site", {})
    small_rows = [r for r in doc["subgroups"] if _small_row(r)]
    small_cells = []
    for r in small_rows:
        label = pmap.get(r["attribute"], {}).get(r["level"], r["level"])
        small_cells += [
            c for c in agg["cells"] if c["attribute"] == r["attribute"] and c["level"] == label
        ]
    unsuppressed = [c for c in small_cells if not _null_number(c["number"])]
    payloads = {"telemetry": tele_bytes, "aggregates": agg_bytes}
    small_values, n_small_numbers, n_shared = small_only_values(doc)
    floats = _payload_floats(payloads)
    value_hits = sorted(
        {f"{p}: {v!r}" for p, vals in floats.items() for v in vals if v in small_values}
    )
    sites = sorted({r["level"] for r in doc["subgroups"] if r["attribute"] == "site"})
    needles = {f"site {s}": s for s in sites if s != "Unknown/missing"}
    if NOTE_HEADER in cols:
        needles.update({"original header": NOTE_HEADER, "free-text value": NOTE_VALUE})
    long_values = sorted(repr(v) for v in small_values if len(repr(v)) >= MIN_VALUE_CHARS)
    for v in long_values:
        needles[f"small-only value {v}"] = v
    hits = scan.find(payloads, needles)
    return {
        "cohort": name,
        "exit_code": rc,
        "socket_calls": len(socket_calls),
        "telemetry_sends": len(rec.bodies),
        "telemetry_bytes": len(tele_bytes),
        "aggregates_bytes": len(agg_bytes),
        "aggregates_error": aggregates_error,
        "telemetry_valid": tele_valid,
        "aggregates_valid": agg_valid,
        "aggregates_cells": len(agg["cells"]),
        "sites": len(sites),
        "sites_pseudonymised": sorted(site_map) == [s for s in sites if s != "Unknown/missing"],
        "small_rows": [
            {"attribute": r["attribute"], "level": r["level"], "n": r["n"], "events": r["events"]}
            for r in small_rows
        ],
        "small_cells": len(small_cells),
        "small_cells_unsuppressed": len(unsuppressed),
        "structural_violations": structural_violations(agg),
        "small_numbers": n_small_numbers,
        "small_only_values": len(small_values),
        "small_values_shared": n_shared,
        "small_value_hits": value_hits,
        "needles": len(needles),
        "hits": hits,
        "bytes": payloads,
    }


def check(result: dict[str, Any]) -> list[str]:
    """The names of the checks one cohort's result fails (empty when it passes)."""
    failed = []
    if result["socket_calls"]:
        failed.append("socket_calls")
    if result["telemetry_sends"] != 1:
        failed.append("telemetry_sends")
    if result["aggregates_error"]:
        failed.append("aggregates_error")
    for key in ("telemetry_valid", "aggregates_valid", "sites_pseudonymised"):
        if not result[key]:
            failed.append(key)
    for key in (
        "small_cells_unsuppressed",
        "structural_violations",
        "small_value_hits",
        "hits",
    ):
        if result[key]:
            failed.append(key)
    return [f"{result['cohort']}: {f}" for f in failed]


def run_all() -> list[dict[str, Any]]:
    """:func:`run_cohort` on both cohorts, each in a temporary directory (removed after)."""
    results = []
    for name, make in COHORTS.items():
        tmp = Path(tempfile.mkdtemp(prefix=f"proofpack-f19-{name}-"))
        try:
            results.append(run_cohort(name, make(), tmp / "work"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return results
