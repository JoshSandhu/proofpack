"""A-P3 repair 2 (build day 9, lane A): the lens-2 findings at ``a09a0ef``, each as the
literal input the lens fed and the figure it measured.

* FA2-B1: through ``main(["fixtures", "--offline", ...])``, with one value deleted from the
  oracle: ``captured.F1-wilson.values.wilson_lo`` gives row ``F1-wilson`` not matched,
  reason ``oracle value missing: wilson_lo``, exit 6 (at ``a09a0ef``: matched, 1 value,
  exit 0); ``register.F1.wilson_lo`` gives ``F1-register`` not matched; the Newcombe
  example ``9/10 - 3/10`` removed gives ``F14-newcombe`` not matched with its four names.
  With the engine's ``wilson_lo`` moved by 1e-6 and the oracle's deleted, the row is not
  matched (the lens's in-process case).
* FA2-R2: a tree ``<X>/src/proofpack`` whose ``<X>/pyproject.toml`` names ``customer``, or
  is absent, with ``<X>/fixtures/newcombe_table2.json`` planted with status ``checked``:
  F14 is ``no_oracle_recorded`` with :data:`proofpack.fixtures.NEWCOMBE_ABSENT`, and a
  planted ``<X>/fixtures/r/proc_asah.json`` leaves the R-capture status
  ``r_captures_not_captured``.
* RG2-N3: ``oracles_v1.json`` truncated to ``{"captured": ``: exit 6 (at ``a09a0ef``:
  exit 5, no report), report written, ``matched 4, not matched 26``, each of the 26 with
  reason ``oracle_file_unreadable: oracles_v1.json (JSONDecodeError)``.
* FA2-R8: an engine value ``True`` gives the reason ``engine value not a number (bool)``.
* FA2-R4: each tolerance rule's text lists the ids of exactly the register rows of its
  class.
* FA2-R9: F17's ``compare`` on a run and a copy of it with ``T8.html`` added gives
  ``identical`` false and ``file_names`` not equal.
* FA2-R1 / RG2-N1: the inputs that tell the four surviving mutants from the code (these
  pass at ``a09a0ef``; they are here so that the mutants fail).
* The sentences lens 2 found false (FA2-R2, R3, R4, R5, R6, RG2-S1) are absent from the
  files that carried them.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest
import yaml

from conftest import ephemeral_registry
from proofpack import fixtures as fx
from proofpack import resources
from proofpack.cli import main
from proofpack.errors import EXIT_FIXTURES_NOT_MATCHED

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent


def _cli(tmp_path: Path) -> tuple[int, dict | None]:
    rc = main(["fixtures", "--offline", "--out", str(tmp_path)], registry=ephemeral_registry())
    path = tmp_path / fx.REPORT_FILE
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return rc, doc


def _row(doc: dict, row_id: str) -> dict:
    return next(r for r in doc["rows"] if r["id"] == row_id)


def _not_matched(doc: dict) -> dict[str, str]:
    return {r["id"]: r["reason"] for r in doc["rows"] if r["status"] == "not_matched"}


# ------------------------------------------------------ FA2-B1: a deleted oracle value


def _without_wilson_lo(o: dict) -> None:
    del o["oracles_v1.json"]["captured"]["F1-wilson"]["values"]["wilson_lo"]


def _without_register_wilson_lo(o: dict) -> None:
    del o["oracles_v1.json"]["register"]["F1"]["wilson_lo"]


def _without_newcombe_example(o: dict) -> None:
    doc = o["newcombe_table2.json"]
    doc["examples"] = [ex for ex in doc["examples"] if ex["label"] != "9/10 - 3/10"]


NEWCOMBE_9_10 = [
    "9/10 - 3/10 method10 lower",
    "9/10 - 3/10 method10 upper",
    "9/10 - 3/10 method11 lower",
    "9/10 - 3/10 method11 upper",
]


@pytest.mark.parametrize(
    ("delete", "row_id", "n_values", "reason"),
    [
        (_without_wilson_lo, "F1-wilson", 2, "oracle value missing: wilson_lo"),
        (_without_register_wilson_lo, "F1-register", 4, "oracle value missing: wilson_lo"),
        (
            _without_newcombe_example,
            "F14-newcombe",
            12,
            "; ".join(f"oracle value missing: {n}" for n in NEWCOMBE_9_10),
        ),
    ],
)
def test_a_deleted_oracle_value_is_not_matched_and_exits_6(
    tmp_path, monkeypatch, delete, row_id, n_values, reason
):
    oracles = copy.deepcopy(fx.load_oracles())
    delete(oracles)
    monkeypatch.setattr(fx, "load_oracles", lambda: oracles)
    rc, doc = _cli(tmp_path)
    assert rc == EXIT_FIXTURES_NOT_MATCHED == 6
    assert doc is not None and doc["exit_code"] == 6
    fx.validate_report(doc)
    assert _not_matched(doc) == {row_id: reason}
    row = _row(doc, row_id)
    assert row["matched"] is False and row["max_abs_deviation"] is None
    assert row["n_values_compared"] == n_values
    missing = [v for v in row["values"] if v["oracle"] is None]
    assert all(v["within"] is False and v["tolerance"] is None for v in missing)
    assert len(missing) == (4 if row_id == "F14-newcombe" else 1)


def test_an_engine_value_off_by_1e_6_with_its_oracle_value_deleted_is_not_matched(
    monkeypatch,
):
    real = fx._f1_wilson

    def moved(k, n):
        out = real(k, n)
        out["wilson_lo"] += 1e-6
        return out

    monkeypatch.setattr(fx, "_f1_wilson", moved)
    oracles = copy.deepcopy(fx.load_oracles())
    _without_wilson_lo(oracles)
    rep = fx.run_fixtures(oracles=oracles, doctor=False)
    assert _row(rep, "F1-wilson")["status"] == "not_matched"
    assert rep["exit_code"] == 6


def test_every_compared_row_declares_the_names_its_engine_and_oracle_carry():
    oracles = fx.load_oracles()
    for row in fx.register():
        if row.engine is None or row.oracle is None:
            assert row.compares == (), row.id
            continue
        engine = set(row.engine())
        oracle = set(row.oracle(oracles)[0])
        assert len(row.compares) == len(set(row.compares)) >= 1, row.id
        assert set(row.compares) == engine == oracle, row.id


def test_f14_labels_in_the_file_are_the_cases_the_engine_computes():
    doc = fx.load_oracles()[fx.NEWCOMBE_FILE]
    labels = [ex["label"] for ex in doc["examples"]]
    assert labels == [f"{a}/{b} - {c}/{d}" for a, b, c, d in fx.F14_CASES]
    assert [(ex["k1"], ex["n1"], ex["k2"], ex["n2"]) for ex in doc["examples"]] == list(
        fx.F14_CASES
    )


# ------------------------------------------ FA2-R2: the Newcombe file outside the package

NEWCOMBE = "newcombe_table2.json"


def _tree(root: Path, project: str | None) -> Path:
    """``<root>/src/proofpack/fixtures.py`` (empty), ``<root>/pyproject.toml`` naming
    ``project`` (none when ``None``), ``<root>/fixtures/newcombe_table2.json`` copied from
    this repository with ``provenance.status`` set to ``checked``, and
    ``<root>/fixtures/r/proc_asah.json``."""
    if project is not None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "pyproject.toml").write_text(f'[project]\nname = "{project}"\n', "utf-8")
    target = root / "src" / "proofpack" / "fixtures.py"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    planted = json.loads((REPO / "fixtures" / NEWCOMBE).read_text(encoding="utf-8"))
    planted["provenance"]["status"] = "checked"
    (root / "fixtures" / "r").mkdir(parents=True)
    (root / "fixtures" / NEWCOMBE).write_text(json.dumps(planted), encoding="utf-8")
    (root / "fixtures" / "r" / "proc_asah.json").write_text("{}", encoding="utf-8")
    return target


def _as_if_installed_at(monkeypatch, target: Path) -> None:
    """The package's own directory is ``target.parent`` for fixtures.py and resources.py
    (lens FA2-R2 installed the wheel with ``pip --target X/src``)."""
    monkeypatch.setattr(fx, "__file__", str(target))
    monkeypatch.setattr(resources, "_PKG_DIR", target.parent)
    monkeypatch.setattr(resources, "_REPO_ROOT", target.parent.parent.parent, raising=False)


def _f14(oracles: dict) -> dict:
    return fx.compare_row(next(r for r in fx.register() if r.id == "F14-newcombe"), oracles)


@pytest.mark.parametrize("project", ["customer", None])
def test_a_newcombe_file_beside_an_installed_package_is_not_read(tmp_path, monkeypatch, project):
    _as_if_installed_at(monkeypatch, _tree(tmp_path / "X", project))
    f14 = _f14(fx.load_oracles())
    assert f14["status"] == "no_oracle_recorded" and f14["reason"] == fx.NEWCOMBE_ABSENT
    assert f14["oracle_source"] is None
    assert fx.r_captures_status()["status"] == fx.R_CAPTURES_NOT_CAPTURED
    assert NEWCOMBE not in resources._CANDIDATES


def test_in_a_tree_whose_pyproject_names_proofpack_the_newcombe_file_is_read(tmp_path, monkeypatch):
    _as_if_installed_at(monkeypatch, _tree(tmp_path / "Y", "proofpack"))
    assert fx.source_checkout_root() == (tmp_path / "Y").resolve()
    f14 = _f14(fx.load_oracles())
    assert f14["status"] == "matched" and f14["oracle_source"]["marking"] == "checked"


# ------------------------------------------------ RG2-N3: an oracle file that does not parse


def test_a_truncated_oracle_file_is_not_matched_and_the_report_is_written(tmp_path, monkeypatch):
    truncated = tmp_path / "oracles_v1.json"
    truncated.write_text('{"captured": \n', encoding="utf-8")
    real = fx.resource_path
    monkeypatch.setattr(
        fx, "resource_path", lambda name: truncated if name == "oracles_v1.json" else real(name)
    )
    rc, doc = _cli(tmp_path / "out")
    assert rc == 6 and doc is not None
    fx.validate_report(doc)
    assert doc["summary"]["matched"] == 4 and doc["summary"]["not_matched"] == 26
    assert set(_not_matched(doc).values()) == {
        "oracle_file_unreadable: oracles_v1.json (JSONDecodeError)"
    }


def test_a_truncated_newcombe_file_is_not_matched_not_absent(tmp_path, monkeypatch):
    target = _tree(tmp_path / "Z", "proofpack")
    (tmp_path / "Z" / "fixtures" / NEWCOMBE).write_text('{"x": ', encoding="utf-8")
    _as_if_installed_at(monkeypatch, target)
    f14 = _f14(fx.load_oracles())
    assert f14["status"] == "not_matched"
    assert f14["reason"] == "oracle_file_unreadable: newcombe_table2.json (JSONDecodeError)"


# --------------------------------------------------------- FA2-R8, and the lens-2 mutants


def _planted(engine, expected: dict, compares: tuple[str, ...] = ()) -> dict:
    # ``compares`` is passed only when given, so that the rows without it build at a09a0ef
    extra = {"compares": compares} if compares else {}
    row = fx.Row(
        "F8-planted",
        "F8",
        "planted",
        tolerance_class="closed_form",
        engine=engine,
        oracle=lambda o: (expected, {k: 1e-9 for k in expected}, {}),
        **extra,
    )
    return fx.compare_row(row, {})


def test_a_bool_engine_value_is_reported_as_not_a_number():
    out = _planted(lambda: {"a": True}, {"a": 1.0})
    assert out["status"] == "not_matched"
    assert out["reason"] == "engine value not a number (bool): a"


def test_a_non_dict_engine_result_is_not_matched():  # lens RG2-N1 M12
    out = _planted(lambda: [1.0], {"a": 1.0})
    assert out["status"] == "not_matched" and out["reason"] == "engine_error: returned list"


@pytest.mark.parametrize(
    ("oracle_value", "reason"),
    [(None, "oracle value missing: a"), (math.nan, "oracle value not finite (nan): a")],
)
def test_a_null_or_nan_oracle_value_is_not_matched(oracle_value, reason):  # RG2-N1 M14
    out = _planted(lambda: {"a": 1.0}, {"a": oracle_value})
    assert out["status"] == "not_matched" and out["reason"] == reason
    assert out["max_abs_deviation"] is None


def test_a_row_with_no_value_has_no_largest_deviation():  # lens FA2-R1
    out = _planted(lambda: {}, {})
    assert out["status"] == "not_matched" and out["reason"] == "no value compared"
    assert out["max_abs_deviation"] is None and out["n_values_compared"] == 0


def test_a_declared_name_neither_side_carries_is_not_matched():
    out = _planted(lambda: {"a": 1.0}, {"a": 1.0}, compares=("a", "b"))
    assert out["status"] == "not_matched"
    assert out["reason"] == "engine value missing: b; oracle value missing: b"


def test_git_sha_is_null_for_src_proofpack_under_a_pyproject_naming_customer(
    tmp_path, monkeypatch
):  # lens FA2-R1 / RG2-N1 M5: the path matches, the project name does not
    root = tmp_path / "X"
    target = _tree(root, "customer")
    (root / ".git").mkdir()
    calls: list = []
    fake = types.SimpleNamespace(
        run=lambda *a, **k: calls.append(a), SubprocessError=subprocess.SubprocessError
    )
    monkeypatch.setattr(fx, "subprocess", fake)
    monkeypatch.setattr(fx, "__file__", str(target))
    assert fx.git_sha() == (None, fx.NOT_THE_PROOFPACK_CHECKOUT)
    assert calls == []


# ------------------------------------------------------------- FA2-R4: tolerance rules


@pytest.mark.parametrize("cls", ["closed_form", "iterative", "reported_rounding"])
def test_each_tolerance_rule_lists_its_rows(cls):
    listed = set(re.findall(r"\bF\d+[a-d]?-[a-z](?:[a-z-]*[a-z])?", fx.TOLERANCE_RULES[cls]))
    rows = {r.id for r in fx.register() if r.tolerance_class == cls}
    assert listed == rows


# -------------------------------------------------------------- FA2-R9: F17's file sets


def _f17():
    spec = importlib.util.spec_from_file_location(
        "f17_determinism", REPO / "scripts" / "f17_determinism.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["f17_determinism"] = module
    spec.loader.exec_module(module)
    return module


def test_f17_detects_a_file_added_to_one_run(tmp_path):
    f17 = _f17()
    table, criteria, mapping = f17.write_inputs(tmp_path / "in", 400)
    f17.run_once(table, criteria, mapping, tmp_path / "run1", tmp_path / "home1")
    shutil.copytree(tmp_path / "run1", tmp_path / "run2")
    assert f17.compare(tmp_path / "run1", tmp_path / "run2")["identical"] is True
    (tmp_path / "run2" / "T8.html").write_text("<p></p>", encoding="utf-8")
    cmp = f17.compare(tmp_path / "run1", tmp_path / "run2")
    assert cmp["identical"] is False and cmp["checks"]["file_names"]["equal"] is False
    assert "T8.html" in cmp["file_names"][1] and "T8.html" not in cmp["file_names"][0]


# --------------------------------------------------- FA2-R6: the ZAP job's upload step


def test_the_zap_upload_step_runs_after_a_failed_scan():
    rel = yaml.safe_load((REPO / ".github" / "workflows" / "release.yml").read_text("utf-8"))
    steps = rel["jobs"]["zap-baseline"]["steps"]
    upload = next(s for s in steps if str(s.get("uses", "")).startswith("actions/upload"))
    assert upload.get("if") == "always()"


# ------------------------------------------------- the sentences lens 2 found false


REFUSED = {
    "src/proofpack/fixtures.py": (
        "F14 is compared in a source checkout only",
        "which D1 section 9 does not name",
        "this report also applies it to",
    ),
    ".github/workflows/release.yml": (
        "the job does not fail on findings",
        "test_every_engine_run_in_a_workflow_carries_offline",
    ),
    "tests/test_workflows.py": (
        "def test_every_engine_run_in_a_workflow_carries_offline",
        "An image or program named by a word containing",
    ),
    "tests/test_offline.py": (
        "the mutation sweep's copy holds src/tests/schema/scripts only",
        "no .github/workflows/ci.yml here",
    ),
    "tests/test_ap3_repair1.py": (
        "def test_the_tolerance_rules_cite_d1_section_9_only_for_what_it_names",
    ),
    "tests/test_dockerfile.py": ("def test_no_add_from_a_url_and_no_download_in_run",),
}


@pytest.mark.parametrize("rel", sorted(REFUSED))
def test_the_sentences_lens_2_found_false_are_gone(rel):
    text = " ".join((REPO / rel).read_text(encoding="utf-8").split())
    for sentence in REFUSED[rel]:
        assert sentence not in text, (rel, sentence)
