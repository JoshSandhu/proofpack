"""Build day 9 (E9 item 2): T7, the methods appendix, from what the run did.

* **golden**: ``tests/fixtures/golden/T7.html`` is the render of the synthetic document
  T8's golden uses (``assembler.assemble`` on ``cohort_with_a_thirty_row_site`` with
  CRITERIA + FAIRNESS, B = 200, seed 20240101), compared LF-normalised; the assembler
  fixes ``run_id`` / ``started`` / ``duration_s`` and ``manifest.numpy`` is set to
  ``x.y.z``, as for T8. Regenerate with ``PROOFPACK_REGEN_GOLDEN=1``;
* **methods from the run**: three runs through ``proofpack run --templates T7`` (the
  i.i.d. synthetic cohort, a clustered cohort and a y_pred-only table) print three
  different method lists, and each equals the set of ``method`` values this test collects
  from that run's own ``run.json`` with its own walk;
* a **planted** ``[unverified]`` citation (a temporary register) survives to the page
  with ``citation pending verification`` beside it;
* the conventions sentence, the X1 complement sentence and the tolerance text are on the
  page; T7 is written beside ``run.json`` only on a usable licence.
"""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from assembler import assemble
from conftest import ephemeral_registry, make_cohort, make_criteria
from proofpack.cli import main
from proofpack.errors import EXIT_LICENCE, EXIT_OK, EXIT_WARNINGS
from proofpack.render import t7 as render_t7
from test_criteria import CRITERIA, FAIRNESS, cohort_with_a_thirty_row_site
from test_run_cli import _own_home, _prepare

pytestmark = pytest.mark.day9

REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "T7.html"
NUMPY_MASK = "x.y.z"


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    doc = assemble(cohort_with_a_thirty_row_site(), crit)
    doc["manifest"]["numpy"] = NUMPY_MASK
    return doc


def test_golden_t7_matches_the_committed_render(document):
    page = render_t7.render_t7(document).replace("\r\n", "\n")
    if os.environ.get("PROOFPACK_REGEN_GOLDEN") == "1":
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_bytes(page.encode("utf-8"))
    assert GOLDEN.exists(), "regenerate with PROOFPACK_REGEN_GOLDEN=1"
    assert page == GOLDEN.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert NUMPY_MASK in page and "run test-onl" in page  # run_id[:8] in the header
    assert render_t7.render_t7(document) == render_t7.render_t7(document)


def _methods_in_json(node: Any, out: set[str]) -> set[str]:
    """This test's own walk: every object with an ``est`` and a ``method`` key."""
    if isinstance(node, dict):
        if "est" in node and "method" in node:
            out.add(node["method"])
        for v in node.values():
            _methods_in_json(v, out)
    elif isinstance(node, list):
        for v in node:
            _methods_in_json(v, out)
    return out


def _page_methods(page: str) -> set[str]:
    return set(re.findall(r'<tr data-method="([a-z0-9_]+)">', page))


def _run_t7(tmp_path: Path, monkeypatch, cols, crit, name: str) -> tuple[dict, str]:
    base = tmp_path / name
    base.mkdir()
    _own_home(base, monkeypatch)
    csv_path, yml = _prepare(base, cols, crit)
    out = base / "pack"
    rc = main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(out),
            "--offline",
            "--templates",
            "T7",
        ],
        registry=ephemeral_registry(),
    )
    assert rc in (EXIT_OK, EXIT_WARNINGS)
    assert sorted(p.name for p in out.iterdir()) == [
        "T7.html",
        "ingest_report.json",
        "pseudonyms.json",
        "run.json",
    ]
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    page = (out / "T7.html").read_bytes()
    assert b"\r\n" not in page and page.startswith(b"<!DOCTYPE html>")
    assert page.decode("utf-8") == render_t7.render_t7(doc)  # a pure function of run.json
    return doc, page.decode("utf-8")


def test_the_methods_list_is_the_set_of_method_fields_in_each_runs_run_json(
    tmp_path: Path, monkeypatch
):
    iid_cols = cohort_with_a_thirty_row_site()
    iid_crit = make_criteria(criteria=copy.deepcopy(CRITERIA), fairness=FAIRNESS)
    clustered = make_cohort(n=200, with_case_id=True)
    clustered["case_id"] = [f"c{i // 2:06d}" for i in range(200)]
    clustered_crit = make_criteria(
        criteria=[], clustering={"unit": "case_id", "declared_by": "test"}, fairness=None
    )
    ypred = make_cohort(n=200, with_y_pred=True)
    del ypred["score"]
    ypred_crit = make_criteria(criteria=[], fairness=None)
    seen: list[set[str]] = []
    for name, cols, crit in (
        ("iid", iid_cols, iid_crit),
        ("clustered", clustered, clustered_crit),
        ("ypred", ypred, ypred_crit),
    ):
        doc, page = _run_t7(tmp_path, monkeypatch, cols, crit, name)
        expected = _methods_in_json(doc, set())
        assert _page_methods(page) == expected, name
        seen.append(expected)
    iid, clu, yp = seen
    assert iid != clu and iid != yp and clu != yp
    assert "cluster_bootstrap_percentile" in clu and "cluster_bootstrap_percentile" not in iid
    assert "irls_wald" in iid and "irls_wald" not in yp  # no score: no calibration fit


def test_the_page_carries_the_sentences_d4_and_the_master_name(document):
    page = render_t7.render_t7(document)
    assert render_t7.X1_SENTENCE in page
    assert render_t7.TOLERANCE_POLICY in page
    assert "Reporting conventions, not acceptance criteria" in page
    # the conventions file's first paragraph, verbatim through the markdown subset
    assert "These are\nProofPack conventions" not in page
    assert "no regulator specifies them, and none of them is a guarantee" in page
    # DEC-34's 0.897 cell and DEC-35's IPA note ride in the calibration conventions
    assert "0.897" in page and "IPA" in page
    # the fairness impossibility citation keeps its [unverified] marking
    assert "[unverified - cited from memory in R2; not resolved here]" in page
    assert page.count("citation pending verification") >= 5
    assert "Not part of this run: robustness analyses" in page


def test_a_planted_unverified_citation_survives_to_the_page(document, tmp_path):
    cites = render_t7.load_citations()
    planted = {
        "id": "planted_1999",
        "text": "Planted (1999): a test citation that must stay marked",
        "source": "tests/test_render_t7.py",
        "url": None,
        "verified": False,
        "used_by": ["wilson"],
    }
    page = render_t7.render_t7(document, citations=[*cites, planted])
    item = re.search(r'<li data-citation="planted_1999">(.*?)</li>', page, re.S).group(1)
    assert "Planted (1999)" in item and "[unverified] citation pending verification" in item
    assert re.search(r'<li data-open="planted_1999">.*?\[unverified\]', page, re.S)
    # a verified entry prints no marking; an entry naming nothing this run used is not cited
    verified = dict(planted, id="v_2000", verified=True, text="Verified (2000)")
    unused = dict(planted, id="u_2001", used_by=["chi2_psi"], text="Unused (2001)")
    page2 = render_t7.render_t7(document, citations=[verified, unused])
    li = re.search(r'<li data-citation="v_2000">(.*?)</li>', page2, re.S).group(1)
    assert "[unverified]" not in li
    assert 'data-citation="u_2001"' not in page2 and 'data-open="u_2001"' in page2


def test_no_status_word_on_t7_and_the_page_has_no_external_reference(document):
    page = render_t7.render_t7(document)
    body = page.split("<body>", 1)[1]
    text = re.sub(r"<[^>]+>", " ", body)
    assert "criterion met" not in text and "not assessable" not in text
    for bad in ("@import", "url(", "<link", "<script"):
        assert bad not in page
    assert page.count('<section class="page"') == page.count('class="page-footer"') == 3


def test_t7_is_not_written_without_a_usable_licence(tmp_path: Path, monkeypatch, capsys):
    _own_home(tmp_path, monkeypatch, licence=False)
    csv_path, yml = _prepare(tmp_path)
    out = tmp_path / "pack"
    rc = main(
        [
            "run",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(out),
            "--offline",
            "--templates",
            "T7,T8",
        ],
        registry=None,
    )
    assert rc == EXIT_LICENCE
    assert not (out / "T7.html").exists() and not (out / "T8.html").exists()
    assert "HTML not written: licence refused (no_file)" in capsys.readouterr().out
