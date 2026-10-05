"""F19 (D1 section 3.2; section 10 gate 8; build day 13, E13): the egress bytes of two
cohorts, built and searched.

D1 section 3.2's F19 row: *run with an intersectional cell n=7, events=2 and site names
"St Mary's"; telemetry payload validates against egress_schema.json; no key outside
whitelist; cell suppressed; "St Mary's" absent from every egress byte; --offline run
completes inside unshare -rn*. The engine tabulates no intersectional (two-attribute)
cell in this version, so the n = 7 cell here is a ``site`` level, the smallest cell the
document tabulates (as ``tests/test_egress.py`` has done since build day 8).

:func:`run_cohort` writes one cohort, its declarations (``egress.telemetry: true``,
suppression 10 / 5 / 5) and a confirmed mapping into a directory, runs ``proofpack run``
in process (``proofpack.cli.main``) with a recording transport in place of ``urllib``
(no socket is opened; the bytes recorded are the request body the runner would send),
then builds the ``proofpack-aggregates/1`` document from the written ``run.json``
(no code path sends it at launch; it is checked because it is the other document
``egress_schema.json`` describes) and checks:

* both documents validate against ``egress_schema.json`` (its root ``oneOf``);
* the subgroup rows that are small under the declared thresholds - re-derived here from
  ``run.json``'s own ``n`` and ``events`` and the declared numbers, not by
  :mod:`proofpack.egress.suppress` - have every aggregates cell suppressed (``est``,
  ``ci_lo``, ``ci_hi``, ``method``, ``n`` and ``k`` null);
* no site name, no free-text value, no original header and no interval bound of a small
  row (:data:`MIN_VALUE_CHARS`) appears in either document's bytes in any
  form :func:`proofpack.egress.scan.find` searches.

The network half of gate 8 (``--offline`` inside ``unshare -rn``) is Linux only: the CI
job ``offline-namespace`` (``.github/workflows/ci.yml``) runs it and uploads the
artefact :data:`CI_ARTEFACT`. This module does not see that run.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from proofpack import halt_fixtures as hf
from proofpack.egress import scan

CI_ARTEFACT = "f19-offline-namespace"
CI_JOB = "offline-namespace"
SEED = 20240101
ST_MARYS = "St Mary's"
ADDENBROOKES = "Addenbrooke's"
KONIGSBERG = "Königsberg"
GUYS = "Guy's & St Thomas'"
ROYAL_FREE = "Royal Free"
NOTE_HEADER = "clinician_note"
NOTE_VALUE = "seen in clinic on Tuesday"
THRESHOLDS = {"min_n": 10, "min_events": 5, "min_nonevents": 5}
#: The interval bounds of a small row searched for: ``ci_lo`` and ``ci_hi`` whose ``repr``
#: has ten characters or more. Estimates are not searched: measured on 6 October 2026, the
#: small row ``Addenbrooke's`` (n 9) has an estimate 0.6666666666666666 that recurs in the
#: unsuppressed cells age 65-80 sensitivity (18/27) and Site C ppv (14/21); a short value
#: such as 0.5 recurs legitimately too.
MIN_VALUE_CHARS = 10


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


def _criteria() -> dict[str, Any]:
    crit = hf.fixture_criteria()
    crit["egress"] = {"telemetry": True, "suppression": dict(THRESHOLDS)}
    return crit


def _small(row: dict[str, Any]) -> bool:
    n, events = row.get("n"), row.get("events")
    if not isinstance(n, int) or not isinstance(events, int):
        return True
    return (
        n < THRESHOLDS["min_n"]
        or events < THRESHOLDS["min_events"]
        or n - events < THRESHOLDS["min_nonevents"]
    )


def _long_values(row: dict[str, Any]) -> list[str]:
    out: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for key, x in v.items():
                if key in ("ci_lo", "ci_hi") and isinstance(x, float):
                    if len(repr(x)) >= MIN_VALUE_CHARS:
                        out.append(repr(x))
                else:
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(row.get("metrics") or {})
    return sorted(set(out))


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
        hf._environment(home),
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        rc = main(argv, transport=rec)
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    thresholds = egress.thresholds_from_declarations(doc["declarations"].get("egress"))
    agg, pmap = egress.build_aggregates(doc, thresholds)
    agg_bytes = json.dumps(agg, ensure_ascii=False, sort_keys=True).encode("utf-8")
    tele_bytes = rec.bodies[0] if len(rec.bodies) == 1 else b""
    schema = load_json_schema("egress_schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    tele_valid = bool(tele_bytes) and validator.is_valid(json.loads(tele_bytes))
    agg_valid = validator.is_valid(agg)
    site_map = pmap.get("site", {})
    small_rows = [r for r in doc["subgroups"] if _small(r)]
    small_cells = []
    for r in small_rows:
        label = pmap.get(r["attribute"], {}).get(r["level"], r["level"])
        small_cells += [
            c for c in agg["cells"] if c["attribute"] == r["attribute"] and c["level"] == label
        ]
    unsuppressed = [
        c
        for c in small_cells
        if c["number"]["suppressed"] is not True
        or any(c["number"][k] is not None for k in ("est", "ci_lo", "ci_hi", "method", "n", "k"))
    ]
    sites = sorted({r["level"] for r in doc["subgroups"] if r["attribute"] == "site"})
    needles = {f"site {s}": s for s in sites if s != "Unknown/missing"}
    if NOTE_HEADER in cols:
        needles.update({"original header": NOTE_HEADER, "free-text value": NOTE_VALUE})
    for r in small_rows:
        for v in _long_values(r):
            needles[f"small row {r['attribute']}={r['level']} value {v}"] = v
    payloads = {"telemetry": tele_bytes, "aggregates": agg_bytes}
    hits = scan.find(payloads, needles)
    return {
        "cohort": name,
        "exit_code": rc,
        "telemetry_sends": len(rec.bodies),
        "telemetry_bytes": len(tele_bytes),
        "aggregates_bytes": len(agg_bytes),
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
        "needles": len(needles),
        "hits": hits,
        "bytes": payloads,
    }


def check(result: dict[str, Any]) -> list[str]:
    """The names of the checks one cohort's result fails (empty when it passes)."""
    failed = []
    if result["telemetry_sends"] != 1:
        failed.append("telemetry_sends")
    for key in ("telemetry_valid", "aggregates_valid", "sites_pseudonymised"):
        if not result[key]:
            failed.append(key)
    if result["small_cells_unsuppressed"]:
        failed.append("small_cells_unsuppressed")
    if result["hits"]:
        failed.append("hits")
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
