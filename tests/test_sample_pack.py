"""Build day 9 (E9 item 6): the ``/sample-pack`` artefact and E8 carried row 23.

* ``scripts/build_sample_pack.py`` run twice writes the same four files - ``run.json``,
  ``T1.html``, ``T7.html``, ``T8.html`` - and the two builds are byte-identical once
  ``run_id`` (whole and as the header's first eight characters), ``started`` and
  ``duration_s`` are masked;
* every page of every document carries ``SYNTHETIC - illustrative`` in its footer and the
  cover stamp (``proofpack.scope.SYNTHETIC_MARK``, read, not retyped), and the manifest
  carries it as ``data_marking`` beside DEC-48's ``NO LICENCE`` mark;
* the sample declares no acceptance criterion (ProofPack never authors one) and T8
  section 7 then prints no status word (row 23);
* each page is a pure function of the ``run.json`` beside it; the script takes no input
  path.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from proofpack.licence.verify import WATERMARK_NO_LICENCE
from proofpack.render.html import render_t8
from proofpack.render.t1 import render_t1
from proofpack.render.t7 import render_t7
from proofpack.scope import SYNTHETIC_MARK

pytestmark = pytest.mark.day9

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_sample_pack.py"


def _script():
    spec = importlib.util.spec_from_file_location("build_sample_pack", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _masked(out: Path) -> dict[str, bytes]:
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    m = doc["manifest"]
    files = {}
    for name in sorted(p.name for p in out.iterdir()):
        text = (out / name).read_text(encoding="utf-8")
        text = text.replace(m["run_id"], "<run_id>").replace(m["run_id"][:8], "<run_id8>")
        text = text.replace(m["started"], "<started>")
        text = re.sub(r'"duration_s": [0-9.]+', '"duration_s": <d>', text)
        text = re.sub(r"(Duration \(s\)</th><td class=\"mono\">)[0-9.]+", r"\1<d>", text)
        files[name] = text.encode("utf-8")
    return files


@pytest.fixture(scope="module")
def builds(tmp_path_factory) -> tuple[Path, Path]:
    mod = _script()
    a, b = tmp_path_factory.mktemp("sample_a"), tmp_path_factory.mktemp("sample_b")
    assert mod.main(["--out", str(a)]) == 0
    assert mod.main(["--out", str(b)]) == 0
    return a, b


def test_two_builds_are_identical_after_masking_run_id_started_and_duration(builds):
    a, b = builds
    assert sorted(p.name for p in a.iterdir()) == ["T1.html", "T7.html", "T8.html", "run.json"]
    da, db = _masked(a), _masked(b)
    assert da.keys() == db.keys()
    for name in da:
        assert da[name] == db[name], name
    ja = json.loads((a / "run.json").read_text(encoding="utf-8"))
    jb = json.loads((b / "run.json").read_text(encoding="utf-8"))
    assert ja["manifest"]["run_id"] != jb["manifest"]["run_id"]  # the mask did something
    assert ja["manifest"]["mapping_sha256"] == jb["manifest"]["mapping_sha256"]


def test_every_page_of_every_document_is_marked_synthetic(builds):
    a, _ = builds
    doc = json.loads((a / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["data_marking"] == SYNTHETIC_MARK
    assert doc["manifest"]["watermark"] == WATERMARK_NO_LICENCE
    for name in ("T1.html", "T7.html", "T8.html"):
        page = (a / name).read_text(encoding="utf-8")
        sections = page.count('<section class="page')
        footers = re.findall(r'<footer class="page-footer">(.*?)</footer>', page, re.S)
        assert sections >= 3 and len(footers) == sections
        assert all(SYNTHETIC_MARK in f for f in footers), name
        assert SYNTHETIC_MARK in page.split('<div class="print-footer">', 1)[1]
        assert f'<p class="stamp" data-mark="data">{SYNTHETIC_MARK}</p>' in page, name
        assert b"\r\n" not in (a / name).read_bytes()


def test_the_pages_are_pure_functions_of_run_json_and_no_criterion_is_authored(builds):
    a, _ = builds
    doc = json.loads((a / "run.json").read_text(encoding="utf-8"))
    for name, render in (("T1.html", render_t1), ("T7.html", render_t7), ("T8.html", render_t8)):
        assert (a / name).read_text(encoding="utf-8") == render(doc), name
    assert doc["declarations"]["criteria"] == [] and doc["criteria_results"] == []
    assert doc["claim_rejections"] == [] and doc["claims"]
    t8 = (a / "T8.html").read_text(encoding="utf-8")
    body = re.sub(r"<[^>]+>", " ", t8.split("<body>", 1)[1])
    # E8 carried row 23: section 7 printed the three status words with no criteria
    assert "criterion met" not in body and "not assessable" not in body
    assert 'data-count="criteria_met"' not in t8
    assert "No acceptance criteria were declared; estimates and intervals only." in t8


def test_the_script_takes_no_input_path():
    mod = _script()
    with pytest.raises(SystemExit):
        mod.main(["--out", "x", "--input", "customer.csv"])
    with pytest.raises(SystemExit):
        mod.main([])
