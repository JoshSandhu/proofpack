"""A-P3 item 3 (build day 9, lane A): T12, the CSA-structured software assurance record.

* **golden**: ``tests/fixtures/golden/T12.html`` is the render of the report
  ``proofpack.fixtures.run_fixtures()`` builds, masked (:func:`masked_report`): the
  machine-dependent report fields (``generated``, ``git_sha``, ``git_sha_source``,
  ``platform``, ``python``, ``numpy``, ``scipy``, ``duration_s``), every row's
  ``max_abs_deviation`` (set to 0 where a comparison was made) and the doctor rows' ``info``
  (set to ``masked``). Regenerate with ``PROOFPACK_REGEN_GOLDEN=1 python -m pytest
  tests/test_t12.py -k golden``;
* every report row appears once as ``<tr data-row="<id>">`` with the status text of its
  status; a report with ``F1-wilson`` planted off by 2e-9 prints that row ``not matched``
  and the count cell ``not_matched`` 1;
* the forbidden grep: the checker's ``VERDICT_WORDS`` and ``CERTIFICATION_WORDS`` plus
  ``validated``, ``compliant``, ``certified``, ``qualified`` over the page's text nodes:
  zero hits outside ``.customer-text`` and the D4 section 7.1 / 1.5 verbatim texts (class
  ``disclaimer``); inside those, the hits are exactly ``endorsed`` and ``qualified`` (the
  footer's "qualified statistician" and "no regulator has endorsed this tool");
* every FDA AI-DSF anchor on the page carries "draft guidance (January 2025), not for
  implementation" in its label and its guidance-table row carries ``class="draft"``;
* the ``[unverified`` markings of the Newcombe table and the CSA sentence are on the page
  inside ``.unverified``, and so are F13's and F13b's in the absent state (fixture
  ``no_r_capture``); with run 37332685741's capture committed F13 and F13b carry none, and
  :func:`masked_report` masks the 40-hex sha of this checkout's HEAD in F13's reason, and
  nothing else of it;
* ``fixtures --html`` writes ``T12.html`` under the session's ephemeral-key licence and
  not without one (``PROOFPACK_HOME`` pointed at an empty directory), exit 0 both times.
"""

from __future__ import annotations

import copy
import html
import os
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from conftest import ephemeral_registry
from proofpack import fixtures as fx
from proofpack.cli import main
from proofpack.narrate.checker import CERTIFICATION_WORDS, VERDICT_WORDS
from proofpack.render import t12
from proofpack.resources import load_guidance_map

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "T12.html"
FORBIDDEN = (
    set(VERDICT_WORDS)
    | set(CERTIFICATION_WORDS)
    | {"validated", "compliant", "certified", "qualified"}
)
DRAFT_LABEL = "draft guidance (January 2025), not for implementation"
#: The one token of F13's ``suite_only`` reason that moves with every commit: the 40-hex
#: sha of this checkout's HEAD in "the engine commit is not this checkout's HEAD (<sha>)".
#: :func:`masked_report` masks that sha only, so every other word of the reason, the
#: sentence "this command did not run that comparison on this checkout's engine" included,
#: is compared with the golden (capture repair B1: a mask over the whole clause hid a
#: planted "F13 is verified and matched at this checkout").
F13_HEAD_SHA = re.compile(r"(the engine commit is not this checkout's HEAD \()[0-9a-f]{40}(\))")
#: What the golden carries in place of that sha.
F13_HEAD_SHA_MASK = "[masked: this checkout's HEAD sha]"


def masked_report(report: dict) -> dict:
    r = copy.deepcopy(report)
    r.update(
        generated="2026-09-24T00:00:00Z",
        git_sha=None,
        git_sha_source="masked",
        platform="masked-platform",
        on_reference_platform=False,
        python="3.12.0",
        numpy="x.y.z",
        scipy="x.y.z",
        duration_s=None,
    )
    for row in r["rows"]:
        if row["id"] == "F13" and row["status"] == "suite_only":
            # the capture commit: F13's recorded-comparison reason names this checkout's
            # HEAD's sha (fixtures.f13_recorded_outcome), which moves with every commit;
            # the sha only, never the words around it
            row["reason"] = F13_HEAD_SHA.sub(
                lambda m: m.group(1) + F13_HEAD_SHA_MASK + m.group(2), row["reason"]
            )
        if row["max_abs_deviation"] is not None:
            row["max_abs_deviation"] = 0.0
        for v in row["values"]:
            v["engine"] = v["oracle"]
            v["abs_deviation"] = 0.0
        if row["oracle_source"] and row["oracle_source"].get("library_versions"):
            row["oracle_source"]["library_versions"] = {"masked": "x.y.z"}
    for d in r["doctor"]:
        d["info"] = "masked"
        d["ok"] = True
    return r


@pytest.fixture(scope="module")
def report() -> dict:
    return fx.run_fixtures()


@pytest.fixture(scope="module")
def page(report) -> str:
    return t12.render_t12(report)


class _Walker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[set[str]] = []
        self.skip = 0
        self.nodes: list[tuple[str, set[str]]] = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(set((dict(attrs).get("class") or "").split()))
        if tag in ("style", "title", "script"):
            self.skip += 1

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()
        if tag in ("style", "title", "script"):
            self.skip -= 1

    def handle_data(self, data):
        if self.skip or not data.strip():
            return
        scope: set[str] = set()
        for s in self.stack:
            scope |= s
        self.nodes.append((data, scope))


def forbidden_hits(page: str) -> tuple[list, list]:
    w = _Walker()
    w.feed(page)
    outside, inside = [], []
    for text, scope in w.nodes:
        words = set(re.split(r"[^a-z]+", text.lower())) - {""}
        hit = words & FORBIDDEN
        if not hit:
            continue
        (inside if scope & {"customer-text", "disclaimer"} else outside).append(
            (sorted(hit), text.strip()[:60])
        )
    return outside, inside


def test_golden_t12_matches_the_committed_render(report):
    page = t12.render_t12(masked_report(report)).replace("\r\n", "\n")
    if os.environ.get("PROOFPACK_REGEN_GOLDEN") == "1":
        GOLDEN.write_bytes(page.encode("utf-8"))
    assert GOLDEN.exists(), "regenerate with PROOFPACK_REGEN_GOLDEN=1"
    assert page == GOLDEN.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert t12.render_t12(masked_report(report)) == t12.render_t12(masked_report(report))


#: :data:`t12.SUITE_ONLY_RECORDED_TEXT`, written out.
RECORDED_TEXT = (
    "compared inside a CI job; deviations recomputed by this command from the recorded values"
)


def test_the_suite_only_status_cell_names_who_checked_the_row(report, page):
    """E13 repair 1, lens FA-B5: at 941c8e4 every ``suite_only`` row printed "compared by
    the test suite only", F12, F16, F17 and F19 included, which this command measures
    itself. Now a ``suite_only`` row with ``evidence.measured_by_this_command`` prints
    :data:`t12.SUITE_ONLY_MEASURED_TEXT`; one with a numeric ``max_abs_deviation`` (F13
    read from the r-captures job's record; E13 repair 2, lens 2 FA-B2: at bcb1dac it
    printed "not by this command") prints :data:`t12.SUITE_ONLY_RECORDED_TEXT`; the others
    (F18, F20 here) print "checked by the test suite or a CI job, not by this command"."""
    assert "compared by the test suite only" not in page
    assert not any("compared by the test suite only" in x for x in fx.summary_lines(report, None))
    measured, recorded, other = set(), set(), set()
    for row in report["rows"]:
        if row["status"] != "suite_only":
            continue
        cells = re.findall(rf'<tr data-row="{re.escape(row["id"])}">(.*?)</tr>', page)
        cell = re.search(r'data-status="suite_only">([^<]*)</td>', cells[0])
        assert cell is not None, row["id"]
        if (row.get("evidence") or {}).get("measured_by_this_command") is not None:
            measured.add(row["id"])
            assert cell.group(1) == t12.SUITE_ONLY_MEASURED_TEXT, row["id"]
        elif row["max_abs_deviation"] is not None:
            recorded.add(row["id"])
            assert cell.group(1) == RECORDED_TEXT, row["id"]
        else:
            other.add(row["id"])
            assert cell.group(1) == "checked by the test suite or a CI job, not by this command"
    assert {"F12", "F17", "F19"} <= measured
    assert {"F18", "F20"} <= other
    f13 = next(r for r in report["rows"] if r["id"] == "F13")
    if f13["status"] == "suite_only":
        assert recorded == {"F13"} and "recomputed here" in f13["reason"]


def test_every_report_row_appears_in_t12(report, page):
    for row in report["rows"]:
        cells = re.findall(rf'<tr data-row="{re.escape(row["id"])}">(.*?)</tr>', page)
        assert len(cells) == 1, row["id"]
        status = re.search(
            r'<td class="fixture-status" data-status="([a-z_]+)">([^<]*)</td>', cells[0]
        )
        assert status is not None, row["id"]
        assert status.group(1) == row["status"]
        assert status.group(2) == t12.status_text(row)
    assert page.count('<tr data-row="') == len(report["rows"]) == 46
    counts = dict(re.findall(r'data-count="([a-z_]+)">([^<]*)</td>', page))
    for key in (
        "rows",
        "matched",
        "not_matched",
        "no_oracle_recorded",
        "no_independent_oracle",
        "not_built",
        "suite_only",
    ):
        assert counts[key] == str(report["summary"][key]), key


def test_a_not_matched_row_prints_as_not_matched():
    oracles = copy.deepcopy(fx.load_oracles())
    oracles["oracles_v1.json"]["captured"]["F1-wilson"]["values"]["wilson_lo"] += 2e-9
    rep = fx.run_fixtures(oracles=oracles, doctor=False)
    page = t12.render_t12(rep)
    row = re.search(r'<tr data-row="F1-wilson">(.*?)</tr>', page).group(1)
    assert '<td class="fixture-status" data-status="not_matched">not matched</td>' in row
    assert "outside tolerance: wilson_lo" in row
    assert 'data-count="not_matched">1</td>' in page
    assert 'data-count="exit_code">6</td>' in page
    outside, _ = forbidden_hits(page)
    assert outside == []


def test_no_forbidden_word_outside_customer_text_and_the_verbatim_disclaimer(report, page):
    outside, inside = forbidden_hits(page)
    assert outside == []
    assert {w for hit, _ in inside for w in hit} == {"endorsed", "qualified"}
    # the same with a licence watermark on the page, and on the masked golden render
    for other in (
        t12.render_t12(report, watermark="LICENCE EXPIRED - not for submission"),
        t12.render_t12(masked_report(report)),
    ):
        assert forbidden_hits(other)[0] == []


def test_every_fda_draft_anchor_is_labelled_on_the_page(page):
    rows = {r["internal_id"]: r for r in load_guidance_map()}
    ids = re.findall(r'<tr id="([A-Z0-9_]+)"', page)
    assert set(ids) == set(t12.T12_ANCHORS.values())
    drafts = [i for i in ids if rows[i]["status"].lower().startswith("draft")]
    assert drafts == ["FDA_AIDSF_PERF_VALIDATION"]
    for i in drafts:
        row = re.search(rf'<tr id="{i}" class="draft">(.*?)</tr>', page)
        assert row is not None and DRAFT_LABEL in row.group(1)
    notes = re.findall(r'<aside class="margin-note draft">(.*?)</aside>', page)
    assert notes and all(DRAFT_LABEL in n for n in notes)


def _unverified_spans(page: str) -> list[str]:
    return [html.unescape(x) for x in re.findall(r'<span class="unverified">([^<]*)</span>', page)]


def test_unverified_markings_survive_to_the_page_without_an_r_capture(no_r_capture):
    """The absent state (no R capture committed): F13's and F13b's markings survive."""
    spans = _unverified_spans(t12.render_t12(fx.run_fixtures(doctor=False)))
    assert any(s.startswith("[unverified until captured] the pROC capture") for s in spans)
    assert any(s.startswith("[unverified until captured] the rms::val.prob") for s in spans)
    assert "[unverified against the primary PDF]" in spans
    assert t12.CSA_UNVERIFIED in spans


def test_unverified_markings_survive_to_the_page(page):
    spans = _unverified_spans(page)
    # the capture commit (run 37332685741): F13 and F13b carry no [unverified until
    # captured] marking; the absent state is the test above
    assert not any(s.startswith("[unverified until captured]") for s in spans)
    assert "[unverified against the primary PDF]" in spans
    assert t12.CSA_UNVERIFIED in spans


def test_capture_repair_b1_the_committed_f13_reason_says_this_command_did_not_run_it(report):
    """Capture repair B1 (cold lens on 78bd085): with run 37332685741's capture committed,
    F13's reason, word for word, with this checkout's HEAD read by ``git rev-parse HEAD``
    (never the engine commit 9d285d9 the job ran). The lens's plant ("... run that
    comparison here; F13 is verified and matched at this checkout") fails here and in the
    golden."""
    head, _ = fx.git_sha()
    assert head is not None and len(head) == 40
    engine = "9d285d986fedd6f6e43fb2c6bfd1497307adbfa1"
    assert head != engine
    f13 = next(r for r in report["rows"] if r["id"] == "F13")
    assert f13["status"] == "suite_only" and f13["matched"] is False
    assert f13["reason"] == (
        "compared inside the r-captures job, not by this command: GitHub run 37332685741 "
        f"recorded 16 values of the engine at commit {engine} against pROC "
        "(proc_asah.json), max abs deviation 2.7755575615628914e-17, each within 1e-6 as "
        "recomputed here from the recorded engine and R numbers; the engine commit is not "
        f"this checkout's HEAD ({head}); this command did not run that comparison on this "
        "checkout's engine. The aSAH vectors are never committed (DEC-77), so a local "
        "re-check needs R: the r-captures job (fixtures/r/README.md)"
    )
    for word in ("matched", "verified", "validated"):
        assert word not in f13["reason"].lower(), word
    masked = next(r for r in masked_report(report)["rows"] if r["id"] == "F13")
    assert masked["reason"] == f13["reason"].replace(head, F13_HEAD_SHA_MASK)
    assert masked["reason"].count(F13_HEAD_SHA_MASK) == 1


def test_the_required_sentences_are_on_the_page(page):
    text = html.unescape(page)
    assert t12.SUPPORTS_SENTENCE == (
        "This record supports, does not replace, the manufacturer's own validation."
    )
    assert text.count(t12.SUPPORTS_SENTENCE) == 2
    assert t12.PRINT_SENTENCE in text and "print this HTML page to PDF" in text
    assert "Hash identity is claimed on the reference platform only" in text
    assert "python:3.12-slim linux/amd64" in text
    assert "ProofPack signs nothing." in page
    # four checklist steps, each with four blank sign-off cells
    for step in ("doctor", "fixtures", "mapping", "declarations"):
        row = re.search(rf'<tr data-step="{step}">(.*?)</tr>', page).group(1)
        assert row.count('<td class="signoff"></td>') == 4, step
    # the intended-use slot is the placeholder, never engine-drafted text
    assert "[CUSTOMER TEXT REQUIRED - intended use of ProofPack" in page
    assert "INCOMPLETE - customer sections outstanding: 1" in page


def test_the_failure_mode_table_lists_every_engine_code(page):
    from proofpack import errors

    for code in (
        list(errors.HALT_CODES)
        + list(errors.SCHEMA_CODES)
        + list(errors.MAPPING_CODES)
        + list(errors.WARN_CODES)
    ):
        assert f'<tr data-code="{code}">' in page, code
    assert '<tr data-code="exit 6">' in page


def test_fixtures_html_writes_t12_under_a_licence_and_not_without(tmp_path, monkeypatch, capsys):
    rc = main(
        ["fixtures", "--offline", "--out", str(tmp_path / "a"), "--html"],
        registry=ephemeral_registry(),
    )
    out = capsys.readouterr().out
    assert rc == 0 and (tmp_path / "a" / "T12.html").exists(), out
    assert "document written:" in out
    empty = tmp_path / "home"
    empty.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(empty))
    rc = main(
        ["fixtures", "--offline", "--out", str(tmp_path / "b"), "--html"],
        registry=ephemeral_registry(),
    )
    out = capsys.readouterr().out
    assert rc == 0 and not (tmp_path / "b" / "T12.html").exists()
    assert (tmp_path / "b" / "fixtures_report.json").exists()
    assert "T12.html not written: licence refused (no_file)" in out


def test_the_release_script_renders_t12_from_a_report_with_the_no_licence_mark(tmp_path, report):
    import subprocess
    import sys

    path = fx.write_report(report, tmp_path)
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "build_t12.py"),
            "--report",
            str(path),
            "--out",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    page = (tmp_path / "out" / "T12.html").read_text(encoding="utf-8")
    assert "NO LICENCE - not for submission" in page
    assert page.count('<tr data-row="') == len(report["rows"])
    assert forbidden_hits(page)[0] == []
