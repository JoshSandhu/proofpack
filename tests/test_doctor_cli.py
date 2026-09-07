"""doctor, CLI surface, packaged resources, scope strings and the guidance map structure."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

from proofpack import __version__, scope
from proofpack.cli import main
from proofpack.doctor import doctor_ok, format_checks, run_checks
from proofpack.errors import EXIT_OK
from proofpack.io.declare import metric_ids
from proofpack.resources import guidance_ids, load_guidance_map, load_json_schema, resource_path

pytestmark = pytest.mark.day1


def test_doctor_passes_here(tmp_path: Path):
    checks = run_checks(offline=True, cwd=tmp_path)
    assert doctor_ok(checks), format_checks(checks)
    names = {c.name for c in checks}
    for expected in (
        "python",
        "numpy",
        "scipy (optional extra)",
        "docx extra",
        "write access",
        "licence",
        "network",
        "reference platform",
    ):
        assert expected in names
    assert next(c for c in checks if c.name == "network").info == "skipped (--offline)"


def test_doctor_cli_both_flag_positions(capsys):
    assert main(["doctor", "--offline"]) == EXIT_OK
    assert main(["--offline", "doctor"]) == EXIT_OK
    assert main(["doctor", "--json-log"]) == EXIT_OK
    out = capsys.readouterr().out
    payload = json.loads(out.strip().splitlines()[-1])
    assert "doctor" in payload


def test_doctor_write_access_failure_is_reported(tmp_path: Path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        checks = run_checks(offline=True, cwd=ro)
        wa = next(c for c in checks if c.name == "write access")
        if wa.ok:  # running as root: the OS grants the write anyway
            pytest.skip("write access cannot be revoked for this user")
        assert not doctor_ok(checks)
    finally:
        ro.chmod(0o700)


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["--version"])
    assert ei.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_scipy_in_import_graph():
    """Importing the day-1 modules must not pull scipy in (CI runs a scipy-less job too)."""
    before = "scipy" in sys.modules
    import proofpack.cli  # noqa: F401
    import proofpack.doctor  # noqa: F401
    import proofpack.gates  # noqa: F401
    import proofpack.io.declare  # noqa: F401
    import proofpack.io.mapping  # noqa: F401
    import proofpack.io.schema  # noqa: F401

    assert ("scipy" in sys.modules) == before


def test_packaged_schemas_load_and_are_draft_2020():
    for name in (
        "schema_v1.json",
        "criteria_schema.json",
        "claims_schema.json",
        "egress_schema.json",
    ):
        s = load_json_schema(name)
        assert s["$schema"].endswith("2020-12/schema"), name
        assert resource_path(name).exists()


def test_schema_v1_lists_every_halt_code():
    s = load_json_schema("schema_v1.json")
    assert s["x-proofpack"]["halt_gates"] == [f"H{i:02d}" for i in range(1, 13)]


def test_metric_enum_matches_d1_section_4_3():
    ids = metric_ids()
    for m in (
        "sensitivity",
        "specificity",
        "ppa",
        "npa",
        "ppv",
        "npv",
        "auroc",
        "auprc",
        "brier",
        "calibration_slope",
        "tpr_gap",
        "psi",
        "prevalence",
        "kappa",
        "dice_median",
    ):
        assert m in ids


def test_guidance_map_structure_and_blank_sections():
    rows = load_guidance_map()
    assert {
        "internal_id",
        "document",
        "version_date",
        "status",
        "section",
        "estar_section",
        "notes",
    } <= set(rows[0].keys())
    ids = [r["internal_id"] for r in rows]
    assert len(ids) == len(set(ids))
    for r in rows:
        assert r["section"] == "", f"{r['internal_id']}: section must be blank for Josh"
        assert r["internal_id"].isupper() or "_" in r["internal_id"]
    for must in (
        "FDA_AIDSF_SUBGROUP_PERF",
        "FDA_STAT2007_CI",
        "FDA_PCCP_MP3_PERF_EVAL",
        "GB_PMS_44ZM3",
        "EU_MDR_ART86_1",
        "PP_SCOPE",
        "PP_METHODS",
    ):
        assert must in guidance_ids()
    # the CSV is well-formed for a plain csv reader too
    with resource_path("guidance_map_v1.csv").open(encoding="utf-8", newline="") as fh:
        assert len(list(csv.reader(fh))) == len(rows) + 1


def test_scope_strings_present_and_unnumbered():
    assert "not a regulatory opinion" in scope.SHORT_FORM
    assert len(scope.LONG_FORM_ITEMS) == 8
    titles = [t for t, _ in scope.LONG_FORM_ITEMS]
    assert titles[0] == "What ProofPack is."
    assert titles[-1] == "Synthetic or demonstration data."
    rendered = scope.SHORT_FORM.format(version=__version__, date="2026-09-07", guidance_refs="none")
    assert __version__ in rendered


def test_egress_telemetry_skeleton_rejects_row_level_fields():
    jsonschema = pytest.importorskip("jsonschema")
    s = load_json_schema("egress_schema.json")
    ok = {
        "schema": "proofpack-telemetry/1",
        "licence_id": "L-1",
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
        "engine_version": "0.1.0",
        "platform": "linux-x86_64-cp312",
        "manifest_sha256": "0" * 64,
        "duration_s": 1.0,
        "halt_code": None,
        "row_count_bucket": "<1k",
        "timestamp": "2026-09-07T00:00:00Z",
    }
    jsonschema.Draft202012Validator(s).validate(ok)
    bad = dict(ok, column_names=["y_true"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(s).validate(bad)
