"""F16, the engine half (build day 13, E13): the committed native parity values equal a
fresh native run.

``fixtures/f16_parity_native.json`` was written by ``scripts/f16_parity_native.py`` from a
clean tree; its ``generated.engine_commit`` names that commit. This file compares it with
``proofpack.parity.compute()`` run now, under ``proofpack.parity.compare`` - the rules of
the site's ``parity.spec.ts`` ``compareEntry`` (closed 1e-9, irls 1e-6, bootstrap equal at
4 decimals, exact). That is native against native: the Pyodide half is lane S's
(``proofpack-site/tests/e2e/parity.spec.ts``, after a pin move past DEC-43's ``81f1102``) and
is not run here.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path

import pytest

from proofpack import fixtures as fx
from proofpack import parity

pytestmark = [pytest.mark.day13, pytest.mark.fixture]
REPO = Path(__file__).resolve().parent.parent
COMMITTED = REPO / parity.COMMITTED_FILE


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fresh() -> dict:
    return parity.compute()


def test_the_committed_file_equals_a_fresh_native_run_within_the_f16_tolerances(committed, fresh):
    result = parity.compare(committed, fresh)
    assert result["failures"] == [], result["failures"][:10]
    assert result["entries"] == sum(len(v) for v in committed["fixtures"].values())
    assert result["entries"] >= 800
    assert sorted(committed["fixtures"]) == sorted(fresh["fixtures"])


def test_the_committed_file_names_the_clean_engine_commit_that_produced_it(committed):
    gen = committed["generated"]
    assert re.fullmatch(r"[0-9a-f]{40}", gen["engine_commit"])
    assert gen["tree_clean"] is True and gen["by"] == "scripts/f16_parity_native.py"
    assert committed["schema"] == parity.SCHEMA
    ancestor = subprocess.run(
        ["git", "-C", str(REPO), "merge-base", "--is-ancestor", gen["engine_commit"], "HEAD"],
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        # a shallow CI checkout (actions/checkout fetch-depth 1) has no history to ask
        shallow = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--is-shallow-repository"],
            capture_output=True,
            text=True,
        )
        assert shallow.stdout.strip() == "true", ancestor.stderr


def test_every_non_register_class_row_with_an_engine_is_in_the_file_except_f13_f13b(committed):
    keys = {k for v in committed["fixtures"].values() for k in v}
    for row in fx.register():
        if row.engine is None or row.tolerance_class in (None, "register"):
            continue
        if row.fixture in parity.LEFT_OUT:
            continue
        assert any(k == row.id or k.startswith(row.id + ".") for k in keys), row.id
        for name in row.compares:
            assert f"{row.id}.{name}" in committed["fixtures"][row.fixture], (row.id, name)
    assert set(parity.LEFT_OUT) == {"F13", "F13b"}


def _numbers(v) -> list[float]:
    if isinstance(v, list):
        return [y for x in v for y in _numbers(x)]
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return [float(v)]
    return []


def test_every_register_class_value_is_in_the_file(committed, fresh):
    """E13 repair 1, lens FA-B1: ``_register_entries`` skips the rows whose tolerance class
    is ``register`` (F1, F1b, F1c, F1d, F2, F3, F4, F5, F6 and F8 ``-register``). Each of
    their values, computed now, must equal (exactly) the value of an entry of a fresh
    ``parity.compute()`` for the same fixture, and that entry's key must be in the committed
    file (whose values ``compare`` holds to the fresh run under the labelled tolerances).
    At 941c8e4 F5-register's ``accuracy_diff`` (-0.08) was in no entry.

    Gate repair (run 37463363415, at a894fee): the first version looked the values up in
    the committed file, written on win-amd64-cp314, by exact equality; on the Linux runner
    ``F3-register.paired_p`` computed 0.05934643879192011 against the file's
    0.0593464387919201 and the test failed."""
    seen = 0
    for row in fx.register():
        if row.engine is None or row.tolerance_class != "register":
            continue
        block = fresh["fixtures"][row.fixture]
        for name, value in row.engine().items():
            keys = [k for k, e in block.items() if float(value) in _numbers(e.get("value"))]
            assert keys, (row.id, name, value)
            assert any(k in committed["fixtures"][row.fixture] for k in keys), (row.id, name)
            seen += 1
    assert seen == 67


def test_f5_accuracy_difference_is_in_the_file_with_its_interval(committed):
    f5 = committed["fixtures"]["F5"]
    assert f5["F5-register.accuracy_diff.est"] == {
        "value": -0.08,
        "tol": "closed",
        "class": "closed_form",
    }
    assert f5["F5-register.accuracy_diff.method"]["value"] == "newcombe_paired"
    assert f5["F5-register.accuracy_diff.n"]["value"] == 100
    assert abs(f5["F5-register.accuracy_diff.ci_lo"]["value"] - -0.1553563811022839) < 1e-12
    assert abs(f5["F5-register.accuracy_diff.ci_hi"]["value"] - -0.010249291949335215) < 1e-12


@pytest.mark.parametrize(
    "tol,cls,delta",
    [
        ("bootstrap", "closed_form", 3.0e-5),  # lens FA-B2's plant: label widened, value moved
        ("bootstrap", "closed_form", 0.0),  # the label alone
        ("closed", "reported_rounding", 0.0),  # the class alone
    ],
)
def test_compare_fails_when_the_two_labels_differ(committed, fresh, tol, cls, delta):
    """E13 repair 1, lens FA-B2: ``F1-wilson.wilson_lo`` is ``closed`` / ``closed_form``
    in a fresh run. The committed copy is planted with the label (and value) given; at
    941c8e4 the first case agreed (the label was read from the committed side only)."""
    planted = copy.deepcopy(committed)
    entry = planted["fixtures"]["F1"]["F1-wilson.wilson_lo"]
    assert fresh["fixtures"]["F1"]["F1-wilson.wilson_lo"]["tol"] == "closed"
    entry.update(tol=tol, **{"class": cls})
    entry["value"] += delta
    failures = parity.compare(planted, fresh)["failures"]
    assert len(failures) == 1 and failures[0].startswith("F1.F1-wilson.wilson_lo:"), failures


def test_the_e6_to_e10_blocks_are_in_the_file(committed):
    prefixes = {p for _, p, _ in parity.BLOCKS}
    for fixture, prefix, _ in parity.BLOCKS:
        assert any(k.startswith(prefix + ".") for k in committed["fixtures"][fixture]), prefix
    assert prefixes == {
        "F5-register.accuracy_diff",
        "E6.calibration_block",
        "E10.compare_versions",
        "E10.unpaired_delong",
        "subgroups.heterogeneity_footnote",
        "E7.attainability",
    }
    f4 = committed["fixtures"]["F4"]
    assert f4["E6.calibration_block.slope.number.est"]["tol"] == "irls"
    assert f4["E6.calibration_block.brier.number.ci_lo"]["tol"] == "bootstrap"
    assert f4["E6.calibration_block.oe.number.est"]["tol"] == "closed"
    f5 = committed["fixtures"]["F5"]
    assert f5["E10.unpaired_delong.difference.ci_lo"]["tol"] == "irls"


def test_every_entry_has_the_site_shape_and_one_of_its_four_labels(committed):
    for fixture, block in committed["fixtures"].items():
        for key, e in block.items():
            if e["value"] is None:
                assert set(e) == {"value", "reason"} and e["reason"], (fixture, key)
            else:
                assert e["tol"] in parity.TOL_LABELS, (fixture, key)
                assert set(e) == {"value", "tol", "class"}, (fixture, key)


def _first(committed: dict, tol: str) -> tuple[str, str, float]:
    for fixture, block in committed["fixtures"].items():
        for key, e in block.items():
            if e.get("tol") == tol and isinstance(e["value"], float):
                return fixture, key, e["value"]
    raise AssertionError(tol)


@pytest.mark.parametrize(
    "tol,delta,ok",
    [
        ("closed", 5e-10, True),
        ("closed", 2e-9, False),
        ("irls", 5e-7, True),
        ("irls", 2e-6, False),
    ],
)
def test_compare_catches_a_planted_numeric_drift_beyond_the_tolerance(committed, tol, delta, ok):
    planted = copy.deepcopy(committed)
    fixture, key, value = _first(committed, tol)
    planted["fixtures"][fixture][key]["value"] = value + delta
    assert (parity.compare(committed, planted)["failures"] == []) is ok


def test_compare_rounds_bootstrap_entries_to_four_decimals(committed):
    fixture, key, value = _first(committed, "bootstrap")
    near = copy.deepcopy(committed)
    near["fixtures"][fixture][key]["value"] = parity._js_round4(value) + 1e-6
    far = copy.deepcopy(committed)
    far["fixtures"][fixture][key]["value"] = value + 2e-4
    same_rounding = parity._js_round4(value + 0) == parity._js_round4(
        parity._js_round4(value) + 1e-6
    )
    assert (parity.compare(committed, near)["failures"] == []) is same_rounding
    assert parity.compare(committed, far)["failures"] != []


def test_compare_catches_a_missing_key_an_exact_change_and_a_reason_change(committed):
    fixture = "F5"
    key_exact = next(
        k for k, e in committed["fixtures"][fixture].items() if e.get("tol") == "exact"
    )
    key_null = next(k for k, e in committed["fixtures"][fixture].items() if e["value"] is None)
    a = copy.deepcopy(committed)
    del a["fixtures"][fixture][key_exact]
    b = copy.deepcopy(committed)
    b["fixtures"][fixture][key_exact]["value"] = "planted"
    c = copy.deepcopy(committed)
    c["fixtures"][fixture][key_null]["reason"] = "planted"
    for planted in (a, b, c):
        assert parity.compare(committed, planted)["failures"] != []


def test_the_check_command_agrees(capsys):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "f16_parity_native", REPO / "scripts" / "f16_parity_native.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["f16_parity_native"] = module
    spec.loader.exec_module(module)
    assert module.main(["--check", "--out", str(COMMITTED)]) == 0
    assert "0 failures" in capsys.readouterr().out
