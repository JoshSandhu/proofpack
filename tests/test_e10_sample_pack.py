"""Build day 10 (E10 item 6): ``scripts/build_sample_pack.py --compare``.

* with ``--compare`` the script writes ``compare.json`` and ``T2.html`` beside the four
  E9 files; the prior version is the synthetic recipe (``proofpack.synthetic.
  perturb_scores`` at the sample seed); two builds are byte-identical after the E9 mask
  (``run_id`` whole and as the header's eight characters, ``started``, ``duration_s``);
* every page of T2 carries ``SYNTHETIC - illustrative`` and ``NO LICENCE`` in its footer
  and the cover stamp; T2 is a pure function of the ``compare.json`` beside it;
* the sample declares no criterion, so T2-3 prints no margin and no status column;
* without ``--compare`` the four files alone are written (the E9 test still holds).
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from proofpack.licence.verify import WATERMARK_NO_LICENCE
from proofpack.render.t2 import render_t2
from proofpack.scope import SYNTHETIC_MARK
from test_render_t8 import footers_per_page
from test_sample_pack import _masked

pytestmark = pytest.mark.day10

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_sample_pack.py"


def _script():
    spec = importlib.util.spec_from_file_location("build_sample_pack", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def builds(tmp_path_factory) -> tuple[Path, Path]:
    mod = _script()
    a, b = tmp_path_factory.mktemp("cmp_a"), tmp_path_factory.mktemp("cmp_b")
    assert mod.main(["--out", str(a), "--compare"]) == 0
    assert mod.main(["--out", str(b), "--compare"]) == 0
    return a, b


def test_two_compare_builds_are_identical_after_masking(builds):
    a, b = builds
    names = ["T1.html", "T2.html", "T7.html", "T8.html", "compare.json", "run.json"]
    assert sorted(p.name for p in a.iterdir()) == names
    da, db = _masked(a), _masked(b)
    # _masked reads run.json's run_id; compare.json has its own: mask that too
    for files, out in ((da, a), (db, b)):
        cmp_doc = json.loads((out / "compare.json").read_text(encoding="utf-8"))
        m = cmp_doc["manifest"]
        for name in ("compare.json", "T2.html"):
            text = files[name].decode("utf-8")
            text = text.replace(m["run_id"], "<run_id>").replace(m["run_id"][:8], "<run_id8>")
            text = text.replace(m["started"], "<started>")
            text = re.sub(r'"duration_s": [0-9.]+', '"duration_s": <d>', text)
            files[name] = text.encode("utf-8")
    assert da.keys() == db.keys()
    for name in da:
        assert da[name] == db[name], name


def test_t2_is_marked_synthetic_on_every_page_and_is_a_function_of_compare_json(builds):
    a, _ = builds
    doc = json.loads((a / "compare.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["data_marking"] == SYNTHETIC_MARK
    assert doc["manifest"]["watermark"] == WATERMARK_NO_LICENCE
    assert doc["comparison"]["paired"] is True and doc["comparison"]["n_pairs"] == 400
    page = (a / "T2.html").read_text(encoding="utf-8")
    assert page == render_t2(doc)
    sections = page.count('<section class="page')
    footers = re.findall(r'<footer class="page-footer">(.*?)</footer>', page, re.S)
    assert sections == 5 and footers_per_page(page) == [1] * sections
    assert all(SYNTHETIC_MARK in f and WATERMARK_NO_LICENCE in f for f in footers)
    assert f'<p class="stamp" data-mark="data">{SYNTHETIC_MARK}</p>' in page
    assert b"\r\n" not in (a / "T2.html").read_bytes()
    # no criterion is authored by ProofPack: no margin, no status column, no status word
    table = re.search(r'<table class="comparison">.*?</table>', page, re.S).group(0)
    assert "Margin" not in table and 'class="status"' not in table
    assert doc["declarations"]["criteria"] == [] and doc["criteria_results"] == []
    body = re.sub(r"<[^>]+>", " ", page.split("<body>", 1)[1])
    assert "criterion met" not in body and "not assessable" not in body


def test_the_prior_is_the_recorded_recipe(builds):
    from proofpack.synthetic import make_cohort, perturb_scores

    a, _ = builds
    mod = _script()
    doc = json.loads((a / "compare.json").read_text(encoding="utf-8"))
    cols = make_cohort(seed=mod.SEED, n=mod.N_ROWS)
    prior_scores = perturb_scores(cols["score"], mod.SEED)
    # the prior's own overall block was computed from those scores: its accuracy k at
    # the sample threshold equals a direct count
    correct = sum(
        1 for y, p in zip(cols["y_true"], prior_scores, strict=True) if (p >= 0.5) == (y == "1")
    )
    assert doc["comparison"]["prior"]["overall"]["op1"]["accuracy"]["k"] == correct
    assert doc["comparison"]["prior_version"] is None


def test_without_the_flag_the_four_files_alone_are_written(tmp_path):
    mod = _script()
    assert mod.main(["--out", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "T1.html",
        "T7.html",
        "T8.html",
        "run.json",
    ]
    assert mod.COMPARE_FILES == ("compare.json", "T2.html")
