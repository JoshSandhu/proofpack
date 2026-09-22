"""``proofpack doctor`` - environment self-check (D1 section 7).

Reports Python/numpy/scipy versions, the docx extra, write access, licence
status, network reachability (never attempted on day 1 and skipped with
``--offline``) and the reference-platform check. Makes no outbound call.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import platform
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from proofpack import __version__
from proofpack.resources import guidance_ids, load_json_schema

REFERENCE_PLATFORM = "linux-x86_64-cp312"


@dataclass
class Check:
    name: str
    ok: bool
    info: str
    essential: bool = True


def current_platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    return f"{system}-{machine}-cp{sys.version_info.major}{sys.version_info.minor}"


def _version_of(module: str, dist: str | None = None) -> str | None:
    try:
        importlib.import_module(module)
    except ImportError:
        return None
    try:
        return importlib.metadata.version(dist or module)
    except importlib.metadata.PackageNotFoundError:
        return "present"


def run_checks(*, offline: bool = False, cwd: str | Path | None = None) -> list[Check]:
    checks: list[Check] = []
    py_ok = sys.version_info >= (3, 12)
    checks.append(
        Check("python", py_ok, platform.python_version() + ("" if py_ok else " (3.12+ required)"))
    )

    for mod, dist, essential in (
        ("numpy", None, True),
        ("yaml", "pyyaml", True),
        ("jsonschema", None, True),
    ):
        v = _version_of(mod, dist)
        checks.append(Check(mod, v is not None, v or "missing", essential))

    scipy_v = _version_of("scipy")
    checks.append(
        Check(
            "scipy (optional extra)",
            True,
            scipy_v
            or "not installed - Clopper-Pearson and chi-square paths unavailable until installed",
            essential=False,
        )
    )
    docx_v = _version_of("docxtpl")
    checks.append(
        Check("docx extra", True, docx_v or "not installed - HTML/JSON only", essential=False)
    )

    for name in (
        "schema_v1.json",
        "criteria_schema.json",
        "claims_schema.json",
        "egress_schema.json",
        "output_schema_v1.json",
    ):
        try:
            load_json_schema(name)
            checks.append(Check(f"schema {name}", True, "loads"))
        except Exception as exc:  # noqa: BLE001 - doctor reports, never raises
            checks.append(Check(f"schema {name}", False, type(exc).__name__))
    try:
        n = len(guidance_ids())
        checks.append(Check("guidance_map_v1.csv", n > 0, f"{n} internal ids"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("guidance_map_v1.csv", False, type(exc).__name__))

    target = Path(cwd or os.getcwd())
    try:
        with tempfile.NamedTemporaryFile(dir=target, prefix=".proofpack-doctor-", delete=True):
            pass
        checks.append(Check("write access", True, str(target)))
    except OSError as exc:
        checks.append(Check("write access", False, f"{type(exc).__name__} in {target}"))

    # build day 7 (E7): the file the CLI would read, verified against the shipped key
    # (proofpack.licence: PROOFPACK_LICENCE, the per-user location, then ./proofpack.lic)
    from proofpack import licence as licence_mod

    lic = licence_mod.installed_path()
    if lic is None:
        lic_text = "no licence file found - doctor/map/fixtures always work; run/compare need one"
    else:
        result = licence_mod.verify(lic)
        lic_text = f"{lic}: {result.status} ({result.reason_code})"
        if result.tier:
            lic_text += f", tier {result.tier}, expires {result.expires}"
        if result.watermark:
            lic_text += f", watermark {result.watermark}"
    checks.append(Check("licence", True, lic_text, essential=False))
    checks.append(
        Check(
            "network",
            True,
            "skipped (--offline)"
            if offline
            else (
                "not attempted by doctor; the one outbound call is run's telemetry POST to "
                "https://proofpack.globalphoenix.co.uk/api/telemetry (schema, licence_id, "
                "run_id, engine_version, platform, manifest_sha256, duration_s, halt_code, "
                "row_count_bucket, timestamp), off with --offline or egress.telemetry: false"
            ),
            essential=False,
        )
    )
    tag = current_platform_tag()
    checks.append(
        Check(
            "reference platform",
            True,
            f"{tag}"
            + (
                ""
                if tag == REFERENCE_PLATFORM
                else f" (reference is {REFERENCE_PLATFORM}; tolerances per T7 apply)"
            ),
            essential=False,
        )
    )
    checks.append(Check("engine version", True, __version__, essential=False))
    return checks


def format_checks(checks: list[Check]) -> str:
    width = max(len(c.name) for c in checks)
    lines = ["proofpack doctor"]
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        lines.append(f"  [{mark}] {c.name.ljust(width)}  {c.info}")
    ok = all(c.ok for c in checks if c.essential)
    lines.append("")
    lines.append("All essential checks passed." if ok else "Essential check(s) FAILED.")
    lines.append(
        "Next step: proofpack declare --out criteria.yaml, then proofpack map --input "
        "test.csv --criteria criteria.yaml"
    )
    return "\n".join(lines)


def doctor_ok(checks: list[Check]) -> bool:
    return all(c.ok for c in checks if c.essential)
