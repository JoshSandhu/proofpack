"""F16, the engine half (D1 section 3.2; section 10 gate 3; build day 13, E13): the native
values the site's Pyodide parity test compares against.

D1 section 3.2's F16 row: *all of F1-F8 identical to 1e-9 (closed form) / 1e-6 (IRLS) /
reported rounding (bootstrap) under Pyodide vs native*. F16 has two halves:

* **native** (this module, lane E): :func:`compute` returns, for every value the fixture
  register computes (each register row with an engine function, F1-F11 and F14; F13 and
  F13b need R or the aSAH vectors and are not here), and for the build day 6-10
  statistics the register does not list in full - the whole calibration block on the F4
  rows (E6), the whole paired comparison block and the unpaired DeLong difference on the
  F3 pair (E10), the attainability bounds (E7) and the heterogeneity footnote on the F6
  sites - one entry ``{"value", "tol", "class"}`` per value, or ``{"value": None,
  "reason"}`` when the environment cannot compute it. ``scripts/f16_parity_native.py``
  writes it to :data:`COMMITTED_FILE` with the engine commit it was produced at;
  ``tests/test_f16_parity_native.py`` holds the committed file equal to a fresh native
  run under :func:`compare`.
* **Pyodide** (lane S, ``proofpack-site/tests/e2e/parity.spec.ts``): the same function
  run in the browser and compared with the native file. That half is not run by this
  repository; the site pins engine ``81f1102`` (DEC-43) and moves to a commit carrying this
  module only by a later pin move.

The entry shape and the four ``tol`` labels are the site's at its pinned commit
(``scripts/parity_f1_f6.py`` and ``parity.spec.ts``'s ``compareEntry``): ``closed`` 1e-9,
``irls`` 1e-6 (the site's name for D1 section 9's iterative class; it covers DeLong and
Clopper-Pearson here too), ``bootstrap`` equal after rounding to 4 decimals (half away
from zero upwards, as JavaScript's ``Math.round``), ``exact`` for strings, integers,
booleans and lists of them. ``class`` carries D1's class name beside it. No file is read
except the packaged ``f4_calibration.csv`` (through the register's F4 function), so the
function runs unchanged from the wheel.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

SCHEMA = "proofpack-f16-parity-native/1"
COMMITTED_FILE = "fixtures/f16_parity_native.json"
TOLERANCE = {"closed": 1e-9, "irls": 1e-6}
TOL_LABELS = ("closed", "irls", "bootstrap", "exact")
#: The register's tolerance class -> the site's label (``reported_rounding`` rows are the
#: two bootstrap rows and two closed-form Newcombe rows; :func:`_label_for_row`).
CLASS_TO_LABEL = {"closed_form": "closed", "iterative": "irls"}
#: Rows left out, and why (they are not computable from the engine alone).
LEFT_OUT = {
    "F13": "needs the aSAH vectors, which exist only inside the r-captures job (DEC-77)",
    "F13b": "an R capture of rms::val.prob; the engine values are the F4 IRLS rows here",
}


def _label_for_row(row: Any) -> str:
    if row.tolerance_class == "reported_rounding":
        return "bootstrap" if "bootstrap" in row.id else "closed"
    return CLASS_TO_LABEL[row.tolerance_class]


def _entry(value: Any, tol: str, cls: str | None) -> dict[str, Any]:
    if isinstance(value, float) and not math.isfinite(value):
        return {"value": None, "reason": "non_finite"}
    if isinstance(value, np.generic):
        value = value.item()
    return {"value": value, "tol": tol, "class": cls}


def _absent(reason: str) -> dict[str, Any]:
    return {"value": None, "reason": reason}


def _register_entries() -> dict[str, dict[str, Any]]:
    from proofpack import fixtures as fx  # noqa: PLC0415

    out: dict[str, dict[str, Any]] = {}
    for row in fx.register():
        if row.engine is None or row.tolerance_class in (None, "register"):
            continue
        if row.fixture in LEFT_OUT:
            continue
        block = out.setdefault(row.fixture, {})
        label = _label_for_row(row)
        try:
            got = row.engine()
        except fx.OptionalDependencyMissing as exc:
            block[f"{row.id}"] = _absent(f"optional_dependency_missing: {exc.package}")
            continue
        except Exception as exc:  # noqa: BLE001 - recorded as the entry's reason
            block[f"{row.id}"] = _absent(f"engine_error: {type(exc).__name__}")
            continue
        for name in sorted(got):
            block[f"{row.id}.{name}"] = _entry(got[name], label, row.tolerance_class)
    return out


def _leaf_label(path: tuple[str, ...], parent: Mapping[str, Any], value: Any) -> tuple[str, str]:
    """``(tol, class)`` of one leaf of a statistics block."""
    if isinstance(value, (str, bool, int)) or value is None:
        return "exact", "exact"
    method = str(parent.get("method") or "").lower()
    if "bootstrap" in path or (
        path and path[-1] in ("ci_lo", "ci_hi") and ("bootstrap" in method or "percentile" in method)
    ):
        return "bootstrap", "reported_rounding"  # D1 section 9: bootstrap to reported rounding
    if any(("slope" in p or "intercept" in p) for p in path):
        return "irls", "iterative"  # IRLS slope / intercept
    if "delong" in method:
        return "irls", "iterative"  # D1 section 9: DeLong via placements is iterative
    return "closed", "closed_form"


def _walk(block: Any, prefix: str, out: dict[str, dict[str, Any]]) -> None:
    """Every leaf of ``block`` as one entry keyed ``prefix.path``; a list of scalars is one
    leaf; ``None`` is recorded as absent with the reason ``null_in_engine_output``."""

    def visit(v: Any, path: tuple[str, ...], parent: Mapping[str, Any]) -> None:
        key = ".".join((prefix, *path))
        if isinstance(v, Mapping):
            for k in sorted(v, key=str):
                visit(v[k], (*path, str(k)), v)
        elif isinstance(v, (list, tuple)):
            if all(isinstance(x, (int, float, str, bool)) or x is None for x in v):
                kinds = {type(x) for x in v if x is not None}
                if None in v or not v:
                    out[key] = _entry(list(v), "exact", "exact")
                elif kinds <= {int, float} and float in kinds:
                    tol, cls = _leaf_label(path, parent, 0.0)
                    out[key] = _entry([float(x) for x in v], tol, cls)
                else:
                    out[key] = _entry(list(v), "exact", "exact")
            else:
                for i, x in enumerate(v):
                    visit(x, (*path, str(i)), parent)
        elif v is None:
            out[key] = _absent("null_in_engine_output")
        else:
            if isinstance(v, np.generic):
                v = v.item()
            tol, cls = _leaf_label(path, parent, v)
            out[key] = _entry(v, tol, cls)

    visit(json.loads(json.dumps(block, default=_jsonable)), (), {})


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if hasattr(value, "as_dict"):  # stats.number.Number
        return value.as_dict()
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"not JSON-serialisable: {type(value).__name__}")


def _f4_calibration_block() -> dict[str, Any]:
    from proofpack import fixtures as fx  # noqa: PLC0415

    return fx._f4_block()


def _f5_compare_versions() -> dict[str, Any]:
    """The E10 paired comparison block on the F3 pair: version new = s1, prior = s2, the
    same ten labels, operating point 0.5, B 200, seed 20240101."""
    from proofpack import fixtures as fx  # noqa: PLC0415
    from proofpack.stats.bootstrap import BootstrapPolicy  # noqa: PLC0415
    from proofpack.stats.comparison import (  # noqa: PLC0415
        VersionArrays,
        compare_versions,
        paired_join,
    )

    s1, s2, y = fx._f3_arrays()
    ids = [f"r{i}" for i in range(len(y))]
    new = VersionArrays(pos=y, score=s1, probability=s1, pred={"op1": s1 >= 0.5})
    prior = VersionArrays(pos=y, score=s2, probability=s2, pred={"op1": s2 >= 0.5})
    join = paired_join(ids, ids, y.tolist(), y.tolist())
    return compare_versions(
        new,
        prior,
        paired=True,
        join=join,
        ops=["op1"],
        policy=BootstrapPolicy(n_resamples=200, seed=fx.F3_SEED),
    )


def _f5_unpaired_delong() -> dict[str, Any]:
    from proofpack import fixtures as fx  # noqa: PLC0415
    from proofpack.stats.discrimination import unpaired_delong  # noqa: PLC0415

    s1, s2, y = fx._f3_arrays()
    r = unpaired_delong(s1, y, s2, y)
    return {k: getattr(r, k) for k in r.__dataclass_fields__}


def _f8_attainability() -> dict[str, Any]:
    from proofpack.stats.attainability import attainable, max_lower_bound_at_n  # noqa: PLC0415

    out: dict[str, Any] = {}
    for n in (30, 50, 100, 300):
        out[f"max_lower_bound_at_n{n}"] = max_lower_bound_at_n(n)
        out[f"attainable_0.9_ge_n{n}"] = attainable(0.9, n, ">=")
    return out


def _f6_heterogeneity() -> dict[str, Any]:
    from proofpack import fixtures as fx  # noqa: PLC0415
    from proofpack.stats.subgroups import heterogeneity_footnote  # noqa: PLC0415

    return heterogeneity_footnote(
        {"op1": {"sensitivity": [tuple(c) for c in fx.F6_SITES]}}, clustering_route="none"
    )


#: The statistics blocks beyond the register: (fixture, entry prefix, builder).
BLOCKS: tuple[tuple[str, str, Callable[[], Any]], ...] = (
    ("F4", "E6.calibration_block", _f4_calibration_block),
    ("F5", "E10.compare_versions", _f5_compare_versions),
    ("F5", "E10.unpaired_delong", _f5_unpaired_delong),
    ("F6", "subgroups.heterogeneity_footnote", _f6_heterogeneity),
    ("F8", "E7.attainability", _f8_attainability),
)


def _scipy_available() -> bool:
    try:
        import scipy  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def compute() -> dict[str, Any]:
    """The native (or, run under Pyodide, the browser) values (module docstring)."""
    import sys  # noqa: PLC0415

    from proofpack import __version__  # noqa: PLC0415

    fixtures = _register_entries()
    for fixture, prefix, build in BLOCKS:
        block = fixtures.setdefault(fixture, {})
        try:
            value = build()
        except Exception as exc:  # noqa: BLE001 - recorded as the entry's reason
            block[prefix] = _absent(f"engine_error: {type(exc).__name__}")
            continue
        _walk(value, prefix, block)
    return {
        "schema": SCHEMA,
        "engine_version": __version__,
        "python": ".".join(str(x) for x in sys.version_info[:3]),
        "numpy_version": str(np.__version__),
        "scipy_available": _scipy_available(),
        "left_out": dict(LEFT_OUT),
        "fixtures": {k: dict(sorted(v.items())) for k, v in sorted(fixtures.items())},
    }


# ------------------------------------------------------------------ the comparison


def _js_round4(x: float) -> float:
    return math.floor(x * 1e4 + 0.5) / 1e4


def _flatten(v: Any) -> list[float]:
    if isinstance(v, list):
        return [y for x in v for y in _flatten(x)]
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return [float(v)]
    return []


def compare_entry(native: Mapping[str, Any], other: Mapping[str, Any]) -> tuple[bool, float | None]:
    """``(ok, deviation)`` of one entry, by the rules of the site's ``compareEntry``."""
    if native.get("value") is None or other.get("value") is None:
        ok = (
            native.get("value") is None
            and other.get("value") is None
            and native.get("reason") == other.get("reason")
        )
        return ok, None
    tol = native.get("tol")
    if tol not in TOL_LABELS:
        return False, None
    if tol == "exact":
        a = json.dumps(native["value"], sort_keys=True)
        b = json.dumps(other["value"], sort_keys=True)
        return a == b, None
    a, b = _flatten(native["value"]), _flatten(other["value"])
    if len(a) != len(b):
        return False, None
    if tol == "bootstrap":
        dev = max((abs(_js_round4(x) - _js_round4(y)) for x, y in zip(a, b, strict=True)), default=0.0)
        return dev == 0.0, dev
    dev = max((abs(x - y) for x, y in zip(a, b, strict=True)), default=0.0)
    return dev <= TOLERANCE[tol], dev


def compare(native: Mapping[str, Any], other: Mapping[str, Any]) -> dict[str, Any]:
    """Every fixture and entry of ``native`` against ``other``: ``failures`` (empty when
    every entry agrees and the fixture and key sets are equal), per-fixture counts and the
    largest deviation, and how many numeric entries are bit-for-bit equal."""
    failures: list[str] = []
    per: dict[str, dict[str, Any]] = {}
    nf, of = native.get("fixtures") or {}, other.get("fixtures") or {}
    if sorted(nf) != sorted(of):
        failures.append(f"fixture sets differ: {sorted(nf)} vs {sorted(of)}")
    entries = equal_bits = 0
    for fixture in sorted(nf):
        n, o = nf[fixture], of.get(fixture) or {}
        if sorted(n) != sorted(o):
            missing = sorted(set(n) - set(o))[:5]
            extra = sorted(set(o) - set(n))[:5]
            failures.append(f"{fixture}: key sets differ (missing {missing}, extra {extra})")
        worst = 0.0
        compared = absent = 0
        for key in sorted(n):
            if key not in o:
                continue
            entries += 1
            ok, dev = compare_entry(n[key], o[key])
            if not ok:
                failures.append(f"{fixture}.{key}: {n[key]!r} vs {o[key]!r}")
            if dev is not None:
                compared += 1
                worst = max(worst, dev)
                if json.dumps(n[key]["value"]) == json.dumps(o[key]["value"]):
                    equal_bits += 1
            elif n[key].get("value") is None:
                absent += 1
        per[fixture] = {
            "entries": len(n),
            "compared_numeric": compared,
            "absent": absent,
            "max_abs_deviation": worst,
        }
    return {
        "failures": failures,
        "entries": entries,
        "numeric_bit_equal": equal_bits,
        "fixtures": per,
    }
