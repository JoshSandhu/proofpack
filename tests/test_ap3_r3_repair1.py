"""A-P3 repair 3, repair round 1 (build day 9, lane A): the findings of the two cold lenses
at ``5440295``, each as the literal input fed and the figure asserted.

* FA-N1: ``scripts/capture_fixture_oracles.py --check --committed <file>``, the file being
  a capture made in this test with ``captured.F1d-clopper-pearson.values.cp_hi`` set to
  ``1.0000009`` (same platform and library versions as the script's own capture), exits 1
  and prints ``exact tolerance 0 OUTSIDE`` for that value. Through ``compare()`` on the
  committed file against itself: ``F1-clopper-pearson`` ``cp_hi`` moved by one ulp gives
  False; the 22 iterative values each moved by +9.9e-7 give False and ``50 identical, 0
  differ within their tolerance, 22 differ outside it`` (E10 added F5-delong-pair's four
  iterative values and F5-mcnemar's three closed-form ones), and give True with ``22 differ
  within`` when the committed side is labelled ``planted-platform cp0``. A committed side
  without ``captured_on_platform``, or without ``library_versions``, gives False.
* FA-N6 / RG3-N3 (branches of ``compare()`` no test fed at ``5440295``): the entry
  ``F2-exact`` deleted from one side, an entry ``F99-planted`` with no tolerance class on
  both sides, a top-level key ``planted`` on the fresh side only, and ``F3-delong.kind``
  changed each give False with the line named in the test.
* FA-N7 / RG3-N2: ``ci.yml``'s test job has the step ``oracle capture compared with
  fixtures/oracles_v1.json`` after ``pytest (all markers)``, with ``if: ${{ !cancelled()
  }}`` and the run line ``uv run python scripts/capture_fixture_oracles.py --check``.
* RG3-N4: ``tests/test_wheel_fixtures.py``'s ``PROBE`` imports each of the 14
  ``RUNTIME_MODULES`` and proofpack; ``assert_probe_ran`` given a return code of 1 raises
  AssertionError (a skip would raise ``pytest.skip.Exception``).
* FA-N2, FA-N3, FA-N4, FA-N5, RG3-N1 (sentences): the phrases listed in
  :data:`REFUSED_PHRASES` are absent from the named files, and the phrases in
  :data:`REQUIRED_PHRASES` are present.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "capture_fixture_oracles.py"
COMMITTED = REPO / "fixtures" / "oracles_v1.json"
OTHER_PLATFORM = "planted-platform cp0"


def _capture_module():
    spec = importlib.util.spec_from_file_location("capture_fixture_oracles_rr1", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["capture_fixture_oracles_rr1"] = module
    spec.loader.exec_module(module)
    return module


def _committed() -> dict:
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


def _check(tmp_path: Path, doc: dict) -> subprocess.CompletedProcess:
    path = tmp_path / "oracles_edited.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", "--committed", str(path)],
        capture_output=True,
        text=True,
    )


# ------------------------------------------------------------------------------ FA-N1


def test_fan1_same_platform_f1d_cp_hi_1_0000009_exits_1(tmp_path: Path):
    pytest.importorskip("statsmodels")
    pytest.importorskip("sklearn")
    mod = _capture_module()
    doc = json.loads(mod.dumps(mod.capture()))
    assert doc["captured"]["F1d-clopper-pearson"]["values"]["cp_hi"] == 1.0
    doc["captured"]["F1d-clopper-pearson"]["values"]["cp_hi"] = 1.0000009
    proc = _check(tmp_path, doc)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    lines = proc.stdout.splitlines()
    assert "comparison: exact (same captured_on_platform and library_versions)" in lines
    assert (
        "captured.F1d-clopper-pearson.values.cp_hi: committed 1.0000009 fresh 1.0 abs "
        "difference 9.000e-07 exact tolerance 0 OUTSIDE"
    ) in lines
    counts = "captured values: 71 identical, 0 differ within their tolerance, 1 differ outside it"
    assert counts in lines


def test_fan1_same_platform_one_ulp_is_outside():
    mod = _capture_module()
    base = _committed()
    doc = copy.deepcopy(base)
    values = doc["captured"]["F1-clopper-pearson"]["values"]
    values["cp_hi"] = math.nextafter(values["cp_hi"], math.inf)
    lines, ok = mod.compare(doc, base)
    assert ok is False
    assert any(
        ln.startswith("captured.F1-clopper-pearson.values.cp_hi:")
        and ln.endswith("exact tolerance 0 OUTSIDE")
        for ln in lines
    ), lines


def _iterative_moved(doc: dict, mod, by: float) -> tuple[dict, int]:
    out = copy.deepcopy(doc)
    moved = 0
    for entry, body in out["captured"].items():
        for name in body["values"]:
            if mod.value_class(entry, name) == "iterative":
                body["values"][name] += by
                moved += 1
    return out, moved


def test_fan1_the_18_iterative_values_moved_are_outside_on_the_same_platform_only():
    mod = _capture_module()
    base = _committed()
    doc, moved = _iterative_moved(base, mod, 9.9e-7)
    assert moved == 22  # 18 at 5b1b1f4; E10's F5-delong-pair adds four iterative values
    lines, ok = mod.compare(doc, base)
    assert ok is False
    counts = "captured values: 50 identical, 0 differ within their tolerance, 22 differ outside it"
    assert counts in lines
    doc["captured_on_platform"] = OTHER_PLATFORM
    lines, ok = mod.compare(doc, base)
    assert ok is True
    counts = "captured values: 50 identical, 22 differ within their tolerance, 0 differ outside it"
    assert counts in lines
    assert (
        "comparison: D1 section 9 tolerance classes (captured_on_platform or "
        "library_versions differ)"
    ) in lines


@pytest.mark.parametrize("key", ["captured_on_platform", "library_versions"])
def test_fan1_a_committed_file_without_its_capture_setting_is_false(key: str):
    mod = _capture_module()
    base = _committed()
    doc = copy.deepcopy(base)
    del doc[key]
    lines, ok = mod.compare(doc, base)
    assert ok is False
    assert f"{key}: not recorded in the committed file" in lines


# ------------------------------------------------------------------------------ FA-N6


def test_fan6_an_entry_on_one_side_only_is_false_in_both_directions():
    mod = _capture_module()
    base = _committed()
    doc = copy.deepcopy(base)
    del doc["captured"]["F2-exact"]
    lines, ok = mod.compare(doc, base)
    assert ok is False and "captured.F2-exact: present in the fresh capture only" in lines
    lines, ok = mod.compare(base, doc)
    assert ok is False and "captured.F2-exact: present in the committed file only" in lines


def test_fan6_an_entry_with_no_tolerance_class_is_false():
    mod = _capture_module()
    base = copy.deepcopy(_committed())
    base["captured"]["F99-planted"] = {
        "kind": "captured_formula",
        "source": "planted",
        "values": {"x": 0.5},
    }
    lines, ok = mod.compare(base, copy.deepcopy(base))
    assert ok is False
    assert "captured.F99-planted.values.x: no tolerance class in CAPTURED_CLASS" in lines


def test_fan6_a_top_level_key_on_the_fresh_side_only_is_false():
    mod = _capture_module()
    base = _committed()
    fresh = copy.deepcopy(base)
    fresh["planted"] = 1
    lines, ok = mod.compare(base, fresh)
    assert ok is False and "planted: differs (compared for equality)" in lines


def test_rg3n3_a_changed_kind_is_false():
    mod = _capture_module()
    base = _committed()
    doc = copy.deepcopy(base)
    doc["captured"]["F3-delong"]["kind"] = "captured_library"
    lines, ok = mod.compare(doc, base)
    assert ok is False
    assert "captured.F3-delong.kind: committed 'captured_library' fresh 'captured_formula'" in lines


# ------------------------------------------------------------------------------ FA-N7


def test_fan7_ci_runs_the_oracle_check_after_pytest_unless_cancelled():
    doc = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    steps = doc["jobs"]["test"]["steps"]
    names = [s.get("name") for s in steps]
    pytest_at = names.index("pytest (all markers)")
    check_at = names.index("oracle capture compared with fixtures/oracles_v1.json")
    assert check_at == pytest_at + 1
    step = steps[check_at]
    assert step["if"] == "${{ !cancelled() }}"
    assert step["run"] == "uv run python scripts/capture_fixture_oracles.py --check"


# ------------------------------------------------------------------------------ RG3-N4


def test_rgn4_the_probe_imports_every_runtime_module_and_proofpack():
    import test_wheel_fixtures as twf

    imported: set[str] = set()
    for node in ast.walk(ast.parse(twf.PROBE)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert len(twf.RUNTIME_MODULES) == 14
    assert set(twf.RUNTIME_MODULES) <= imported
    assert "proofpack" in imported


def test_rgn4_a_failed_probe_is_an_assertion_error_not_a_skip():
    import test_wheel_fixtures as twf

    failed = subprocess.CompletedProcess(
        args=["python", "-c", "import nonexistent_lens_module_x"],
        returncode=1,
        stdout="",
        stderr="ModuleNotFoundError: No module named 'nonexistent_lens_module_x'",
    )
    raised: BaseException | None = None
    try:
        twf.assert_probe_ran(failed, "<none>")
    except BaseException as exc:  # noqa: BLE001 - a skip is a BaseException subclass
        raised = exc
    assert type(raised) is AssertionError, type(raised)
    assert "nonexistent_lens_module_x" in str(raised)


# ------------------------------------------------------------------------------ sentences

#: (file, phrase): each phrase was in the file at 5440295 and is refused here.
REFUSED_PHRASES = [
    ("tests/test_fixtures_cmd.py", "def test_the_committed_oracles_equal_a_fresh_capture"),
    ("scripts/capture_fixture_oracles.py", "test_the_committed_oracles_equal_a_fresh_capture"),
    ("tests/test_wheel_fixtures.py", "The test is skipped only when"),
    ("Dockerfile", "docker build has never run"),
    (".dockerignore", "docker build has never run"),
    (".github/workflows/ci.yml", "it has not run anywhere yet"),
    (".github/workflows/ci.yml", "`if: !cancelled()` runs it after a failed pytest step"),
    (".github/dependabot.yml", "Dependabot reads it once the file is on the default branch"),
    (".github/dependabot.yml", '[unverified] the "uv" ecosystem'),
]
#: (file, phrase): each phrase names what was observed or what the code does.
REQUIRED_PHRASES = [
    ("Dockerfile", "run 36005620750"),
    (".dockerignore", "run 36005620750"),
    (".github/workflows/ci.yml", "the digest step failed and the smoke step did not start"),
    (".github/dependabot.yml", "dependabot/uv/*"),
    (".github/dependabot.yml", "would change D1 section 9's reference platform"),
    ("tests/test_wheel_fixtures.py", "``_build_wheel``"),
]


def _prose(name: str) -> str:
    """The file's text with each line's leading ``#`` marker dropped and runs of whitespace
    joined, so a phrase wrapped over two comment lines reads as one."""
    lines = (REPO / name).read_text(encoding="utf-8").splitlines()
    return " ".join(" ".join(ln.strip().removeprefix("#") for ln in lines).split())


@pytest.mark.parametrize("name,phrase", REFUSED_PHRASES)
def test_repair1_refused_phrase_is_absent(name: str, phrase: str):
    assert phrase not in _prose(name)


@pytest.mark.parametrize("name,phrase", REQUIRED_PHRASES)
def test_repair1_required_phrase_is_present(name: str, phrase: str):
    assert phrase in _prose(name)
