"""A-P3 item 5 (build day 9, lane A): ``scripts/sbom.py`` -> CycloneDX 1.5 JSON.

Fed ``uv.lock`` as committed; asserted: every ``[[package]]`` of the lock other than the
project appears once in ``components`` with ``name``, ``version`` and a ``purl``
``pkg:pypi/<name>@<version>``; the project is ``metadata.component``; two runs write the
same bytes; the ``required`` scope is the 13 packages ``uv export --no-dev --extra stats``
listed on 24 September 2026 less scipy (which is ``optional``); statsmodels, scikit-learn
and pytest are ``excluded``. The CycloneDX JSON schema was not fetched: the fields are
checked here, not against it.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent


def _sbom():
    spec = importlib.util.spec_from_file_location("sbom", REPO / "scripts" / "sbom.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SBOM = _sbom()


@pytest.fixture(scope="module")
def bom() -> dict:
    return SBOM.build_sbom(REPO / "uv.lock")


def test_every_locked_package_is_present_with_a_purl(bom):
    lock = tomllib.loads((REPO / "uv.lock").read_text(encoding="utf-8"))
    locked = {p["name"]: p["version"] for p in lock["package"] if p["name"] != "proofpack"}
    comps = {c["name"]: c for c in bom["components"]}
    assert set(comps) == set(locked) and len(bom["components"]) == len(locked) == 62
    for name, version in locked.items():
        c = comps[name]
        assert c["version"] == version and c["type"] == "library"
        assert c["purl"] == f"pkg:pypi/{name}@{version}" == c["bom-ref"]
    assert bom["bomFormat"] == "CycloneDX" and bom["specVersion"] == "1.5"
    assert bom["version"] == 1 and bom["serialNumber"].startswith("urn:uuid:")
    meta = bom["metadata"]["component"]
    assert meta["name"] == "proofpack" and meta["purl"].startswith("pkg:pypi/proofpack@")
    assert "timestamp" not in bom["metadata"]


def test_the_scopes_follow_the_lock(bom):
    scope = {c["name"]: c["scope"] for c in bom["components"]}
    required = sorted(n for n, s in scope.items() if s == "required")
    assert required == [
        "attrs",
        "cffi",
        "cryptography",
        "jinja2",
        "jsonschema",
        "jsonschema-specifications",
        "markupsafe",
        "numpy",
        "pycparser",
        "pyyaml",
        "referencing",
        "rpds-py",
        "typing-extensions",
    ]
    assert scope["scipy"] == "optional"
    for dev in ("statsmodels", "scikit-learn", "pytest", "ruff", "hypothesis", "pip-audit"):
        assert scope[dev] == "excluded", dev


def test_two_runs_write_identical_bytes(tmp_path: Path):
    outs = []
    for i in (1, 2):
        target = tmp_path / f"sbom{i}.json"
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "sbom.py"), "--out", str(target)],
            capture_output=True,
            text=True,
            env={k: v for k, v in __import__("os").environ.items() if k != "SOURCE_DATE_EPOCH"},
        )
        assert proc.returncode == 0, proc.stderr
        outs.append(target.read_bytes())
    assert outs[0] == outs[1]
    assert json.loads(outs[0])["specVersion"] == "1.5"


def test_the_dependency_graph_refers_only_to_components_in_the_bom(bom):
    refs = {c["bom-ref"] for c in bom["components"]} | {bom["metadata"]["component"]["bom-ref"]}
    for dep in bom["dependencies"]:
        assert dep["ref"] in refs
        assert set(dep["dependsOn"]) <= refs
