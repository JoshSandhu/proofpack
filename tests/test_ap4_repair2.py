"""A-P4 repair round 2 (build day 10, lane A, run on Friday 2 October 2026): the two
lens-2 notes at ``e2c98df`` (``handoffs/2026-09-25_A_ap4_lens2_fresh-attack.md`` and
``..._regression.md``). Each sentence below is closed by a phrase test that fails at
``e2c98df``; the behaviour the corrected sentences name is measured beside them.

* FA2-B1 (blocker): no test read the text drawn in the F5 PNGs. The value text of each row
  and the criterion legend are now compared with the SVG's strings
  (``test_f5_png_value_texts_equal_the_svg_value_texts_in_every_f5_figure``,
  ``test_f5_png_criterion_legend_equals_the_svg_criterion_text``); the mutants
  ``ap4_f5_value_text_two_dp`` and ``ap4_f5_criterion_legend_raw_value`` join the ap4 list.
* RG2-B1 = FA2-S5 (blocker; one root cause): ``render/docx.py`` said a newline or a tab in a
  declaration halts at H08, so the line-break rewrite was reachable through the Python API
  only. Under ``reference_standard.description``, ``operating_points[0].source`` and
  ``criteria[0].justification`` a CLI run reaches it. The docstring now names the fields.
* FA2-S1, FA2-S2: the ``Dockerfile`` and ``ci.yml`` said two CI steps had not run; both ran
  in GitHub Actions run 36020197050 (24 September 2026). The comments now quote what they
  printed.
* FA2-S3: "Neither job had run anywhere"; the main test job had. The text now names
  ``docx-extra`` alone.
* FA2-S4 = RG2-N1: the hidden-extra counts are ``4879ac5``'s; the three texts now name it.
* FA2-S6: "Two rewrites happen after rendering"; tab, form feed and BEL are rewritten too.
* FA2-S7: the extra was said to be imported inside ``render_docx``; it is imported inside
  ``_rich``, ``attach_images`` and ``render_docx_bytes``.
* FA2-S8: a ``matplotlibrc`` in the working directory changed the PNG and DOCX bytes and
  ``text.usetex: True`` ended the pack at exit 5. The drawer now runs under matplotlib's
  built-in rcParams; ``ap4_png_builtin_rc_dropped`` joins the ap4 list.
* RG2-S3: "no customer string is evaluated as a template" and "wherever they occur"
  generalised over a class of inputs; deleted.
* RP2-1 (found here): the determinism paragraph named :func:`write_bytes`, which does not
  exist in ``render/docx.py``; the function is ``fixed_zip``.
"""

from __future__ import annotations

import ast
import copy
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ap4_docx import needs_extra, part, synthetic_document
from conftest import ephemeral_registry
from proofpack.cli import main
from proofpack.errors import EXIT_HALT, EXIT_OK
from test_render_figures import _criterion, _figure, _plot
from test_run_cli import _criteria, _own_home, _prepare

pytestmark = [pytest.mark.day10, pytest.mark.ap4]
REPO = Path(__file__).resolve().parent.parent
DOCX_PY = "src/proofpack/render/docx.py"
FIGURES_PNG = "src/proofpack/render/figures_png.py"

ABSENT = [
    ("Dockerfile", "has not yet run with that step"),
    (".github/workflows/ci.yml", "this step has not run yet"),
    (".github/workflows/ci.yml", "Neither job had run anywhere"),
    ("tests/ap4_docx.py", "Neither job had run"),
    (".github/workflows/ci.yml", "modules hidden (win-amd64-cp314): -m ap4 gave"),
    ("tests/ap4_docx.py", "(win-amd64-cp314, 26 September 2026): ``pytest -m ap4``"),
    ("scripts/mutation_sweep.py", "Measured with the three modules hidden by a ``-p`` plugin"),
    (DOCX_PY, "reachable through the Python API only"),
    (DOCX_PY, "Two rewrites happen after rendering"),
    (DOCX_PY, "no customer string is evaluated as a\ntemplate"),
    (DOCX_PY, "wherever they occur"),
    (DOCX_PY, "imported inside :func:`render_docx`"),
    (DOCX_PY, ":func:`write_bytes`"),
    (DOCX_PY, "two renders of one ``run.json`` are byte-identical"),
    (FIGURES_PNG, "are the theme's tokens"),
    (FIGURES_PNG, "give identical bytes on one machine"),
]
PRESENT = [
    ("Dockerfile", "In GitHub Actions run 36020197050"),
    (
        "Dockerfile",
        "python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9",
    ),
    (".github/workflows/ci.yml", "In GitHub Actions run 36020197050"),
    (".github/workflows/ci.yml", "This job had not run in CI on 2 October 2026"),
    (".github/workflows/ci.yml", "Measured locally at commit 4879ac5 (its 130 ap4 tests)"),
    ("tests/ap4_docx.py", "at commit ``4879ac5`` (its 130 ap4 tests)"),
    ("scripts/mutation_sweep.py", "Measured at commit 4879ac5 (its 130 ap4 tests)"),
    (DOCX_PY, "``MULTILINE_FIELDS`` (DEC-65)"),
    (DOCX_PY, "inside :func:`_rich`,\n:func:`attach_images` and :func:`render_docx_bytes`"),
    (DOCX_PY, ":func:`fixed_zip`\nthen rewrites the container"),
    (FIGURES_PNG, "which is not a token (measured 2 October 2026)"),
    (FIGURES_PNG, '``matplotlib.style.context("default")``'),
]


@pytest.mark.parametrize("name,phrase", ABSENT)
def test_the_false_sentence_is_absent(name: str, phrase: str):
    assert phrase not in (REPO / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name,phrase", PRESENT)
def test_the_corrected_sentence_is_present(name: str, phrase: str):
    assert phrase in (REPO / name).read_text(encoding="utf-8")


def test_the_three_new_mutants_are_in_the_ap4_list():
    """Only ids, marker, day and file: the pattern count is ``test_sweep_ap4``'s (a pattern
    check here would fail first under ``-x`` and hide the behavioural kill)."""
    from test_sweep_ap4 import _sweep

    mod = _sweep()
    by_id = {m.id: m for m in mod.MUTANTS}
    for mid in (
        "ap4_f5_value_text_two_dp",
        "ap4_f5_criterion_legend_raw_value",
        "ap4_png_builtin_rc_dropped",
    ):
        m = by_id[mid]
        assert m.marker == "ap4" and m.day == 10 and m.file == FIGURES_PNG, mid


# ------------------------------------------------------------------ FA2-S7 (inspection)


def test_the_extra_imports_in_docx_py_sit_in_three_named_functions():
    """Inspects ``render/docx.py``'s syntax tree: each import of ``docx``, ``docxtpl`` or
    ``matplotlib`` (any submodule) and each import of ``figures_png``, with the function
    that holds it. None is at module level."""
    tree = ast.parse((REPO / DOCX_PY).read_text(encoding="utf-8"))
    found: dict[str, set[str]] = {}

    def roots(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Import):
            return [a.name for a in node.names]
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            return [mod] + [f"{mod}.{a.name}" for a in node.names]
        return []

    def extra(names: list[str]) -> set[str]:
        out = set()
        for n in names:
            top = n.split(".")[0]
            if top in ("docx", "docxtpl", "matplotlib"):
                out.add(top)
            if n.endswith("figures_png"):
                out.add("figures_png")
        return out

    for node in tree.body:
        assert not extra(roots(node)), ast.dump(node)[:120]
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef):
            for node in ast.walk(fn):
                for name in extra(roots(node)):
                    found.setdefault(name, set()).add(fn.name)
    assert found == {
        "docxtpl": {"_rich", "attach_images", "render_docx_bytes"},
        "docx": {"attach_images"},
        "figures_png": {"attach_images"},
    }, found


# ------------------------------------------------------------------ FA2-B1 (the F5 texts)


@pytest.fixture(scope="module")
def document():
    return synthetic_document()


def _svg_values(plot: str) -> list[str]:
    return [
        html.unescape(t)
        for t in re.findall(
            r'<text class="fig-text fig-value" x="[^"]+" y="[^"]+">([^<]*)</text>', plot
        )
    ]


@needs_extra
def test_f5_png_value_texts_equal_the_svg_value_texts_in_every_f5_figure(document):
    """The nine F5 figures of the synthetic document: each figure's ``ax.texts`` (the value
    beside each row, top down) equal the SVG's ``fig-value`` texts in order, and the row
    ``29/37 (78.4%) [62.8, 88.6]ᶜ`` is among them (lens 2 FA2-B1's example row)."""
    from proofpack.render import figures, figures_png
    from proofpack.render import t1 as render_t1

    page = render_t1.render_t1(document)
    figs = figures_png.f5_figures(document, {})
    specs = figures.f5_forest(document, {})
    seen, every = 0, []
    for attribute, per_metric in figs.items():
        for fig, spec in zip(per_metric, specs[attribute], strict=True):
            _, plot = _plot(_figure(page, spec["id"]))
            want = _svg_values(plot)
            (ax,) = fig.axes
            got = [t.get_text() for t in ax.texts]
            assert got == want and len(want) >= 2, (spec["id"], got, want)
            assert fig.texts == [], spec["id"]
            every.extend(got)
            seen += 1
    assert seen == 9
    assert "29/37 (78.4%) [62.8, 88.6]ᶜ" in every


@needs_extra
def test_f5_png_criterion_legend_equals_the_svg_criterion_text():
    """A ``ci_lower_bound`` criterion on sex/sensitivity/op1 with ``value: 0.00001``
    (``fmt.declared`` prints ``0.00001``; ``repr`` prints ``1e-05``): the PNG legend's
    ``(heavy dashed)`` entry, less that suffix, equals the SVG's criterion text, which is
    ``customer criterion C_sex (Dr A., 2026-03-01): 0.00001``."""
    from assembler import assemble
    from conftest import make_cohort, make_criteria
    from proofpack.render import figures, figures_png
    from proofpack.render import t1 as render_t1

    doc = assemble(
        make_cohort(n=240), make_criteria(criteria=[_criterion(value=0.00001)], fairness=None)
    )
    page = render_t1.render_t1(doc)
    figs = figures_png.f5_figures(doc, {})
    specs = figures.f5_forest(doc, {})
    pairs = []
    for attribute, per_metric in figs.items():
        for fig, spec in zip(per_metric, specs[attribute], strict=True):
            _, plot = _plot(_figure(page, spec["id"]))
            svg = [
                html.unescape(t)
                for t in re.findall(r'y="14" text-anchor="middle">([^<]+)</text>', plot)
            ]
            legend = fig.axes[0].get_legend()
            png = [
                t.get_text().removesuffix(" (heavy dashed)")
                for t in (legend.get_texts() if legend is not None else [])
                if t.get_text().endswith(" (heavy dashed)")
            ]
            assert png == svg, (spec["id"], png, svg)
            pairs.extend(png)
    assert pairs == ["customer criterion C_sex (Dr A., 2026-03-01): 0.00001"]


# ------------------------------------------------------------------ FA2-S8 (matplotlibrc)

HOSTILE_RC = (
    "axes.grid: True\n"
    "savefig.transparent: True\n"
    "text.color: red\n"
    "legend.labelcolor: red\n"
    "text.usetex: True\n"
    "lines.linewidth: 5\n"
    "font.size: 20\n"
)
SHA_SCRIPT = r"""
import hashlib, json, sys
import proofpack
from proofpack.render import anchors, docx, figures_png
with open(sys.argv[1], encoding="utf-8") as fh:
    doc = json.load(fh)
refs = {r["id"]: r for r in anchors.resolve([r["id"] for r in doc.get("guidance_refs") or []])}
f = figures_png.all_figures(doc, refs)
figs = [f["f2"], f["f4"]] + [x for per in f["f5"].values() for x in per]
out = {"file": proofpack.__file__, "png": [], "T1": None}
for fig in figs:
    out["png"].append(hashlib.sha256(figures_png.png_bytes(fig)).hexdigest())
out["T1"] = hashlib.sha256(docx.render_docx_bytes(doc, "T1")).hexdigest()
print(json.dumps(out))
"""


@needs_extra
def test_a_matplotlibrc_in_the_working_directory_changes_no_png_byte(tmp_path, document):
    """Two subprocesses render the synthetic document's eleven PNGs and its ``T1.docx``: one
    from a directory holding a ``matplotlibrc`` (:data:`HOSTILE_RC`: ``axes.grid``,
    ``savefig.transparent``, ``text.color: red``, ``legend.labelcolor: red``,
    ``text.usetex: True``, ``lines.linewidth: 5``, ``font.size: 20``), one from a directory
    holding none. Each exits 0, and the twelve SHA-256 values are equal. At ``e2c98df`` the
    first subprocess exited 1 with ``RuntimeError: Failed to process string with tex because
    latex could not be found``."""
    doc_path = tmp_path / "doc.json"
    doc_path.write_text(json.dumps(document, allow_nan=False), encoding="utf-8")
    script = tmp_path / "shas.py"
    script.write_text(SHA_SCRIPT, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "MATPLOTLIBRC"}
    env["PYTHONPATH"] = str(REPO / "src")
    results = {}
    for name, rc_text in (("clean", None), ("hostile", HOSTILE_RC)):
        cwd = tmp_path / name
        cwd.mkdir()
        if rc_text is not None:
            (cwd / "matplotlibrc").write_text(rc_text, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(script), str(doc_path)],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        assert proc.returncode == 0, (name, proc.stderr[-2000:])
        out = json.loads(proc.stdout.strip().splitlines()[-1])
        assert Path(out["file"]).resolve().is_relative_to((REPO / "src").resolve()), out["file"]
        results[name] = out
    assert len(results["clean"]["png"]) == 11
    assert results["hostile"]["png"] == results["clean"]["png"]
    assert results["hostile"]["T1"] == results["clean"]["T1"]


# ------------------------------------------------------------------ FA2-S6 (docxtpl's rewrites)


@needs_extra
def test_tab_form_feed_and_bel_in_model_name_change_the_t8_xml(document):
    """``declarations.model.name`` of T8 set to ``ab``, ``a`` + tab + ``b``, ``a`` + U+000C +
    ``b`` and ``a`` + U+0007 + ``b``: the counts of ``<w:tab/>``, ``w:type="page"`` and
    ``<w:p>`` in ``word/document.xml``, each against ``ab``."""
    from proofpack.render import docx as render_docx

    def counts(name: str) -> tuple[int, int, int]:
        doc = copy.deepcopy(document)
        doc["declarations"]["model"]["name"] = name
        xml = part(render_docx.render_docx_bytes(doc, "T8"), "word/document.xml")
        return (
            xml.count("<w:tab/>"),
            xml.count('w:type="page"'),
            len(re.findall(r"<w:p[ >]", xml)),
        )

    tab0, page0, p0 = counts("ab")
    assert counts("a\tb") == (tab0 + 1, page0, p0)
    assert counts("a\x0cb") == (tab0, page0 + 1, p0 + 2)
    assert counts("a\x07b") == (tab0, page0, p0 + 1)


# ------------------------------------------------------------------ RG2-B1 = FA2-S5 (the CLI)


def _cli(tmp_path, monkeypatch, crit, *flags):
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, crit=crit)
    out = tmp_path / "pack"
    rc = main(
        ["run", "--input", str(csv_path), "--criteria", str(yml), "--out", str(out), "--offline"]
        + list(flags),
        registry=ephemeral_registry(),
    )
    return rc, out


@needs_extra
def test_a_newline_and_a_tab_in_three_declaration_fields_reach_the_t8_docx_through_the_cli(
    tmp_path, monkeypatch, capsys
):
    """``criteria.yaml`` with ``reference_standard.description`` ``QQa`` + newline +
    ``bZZ``, ``operating_points[0].source`` ``TTa`` + tab + ``bUU`` and
    ``criteria[0].justification`` ``JJa`` + newline + ``bKK``; ``run --format docx
    --templates T8 --offline`` with a licence: exit 0, and ``T8.docx`` carries a
    ``<w:br/>`` after ``QQa`` and after ``JJa`` and a ``<w:tab/>`` run between ``TTa`` and
    ``bUU``."""
    crit = _criteria()
    crit["reference_standard"]["description"] = "QQa\nbZZ"
    crit["operating_points"][0]["source"] = "TTa\tbUU"
    crit["criteria"][0]["justification"] = "JJa\nbKK"
    rc, out = _cli(tmp_path, monkeypatch, crit, "--format", "docx", "--templates", "T8")
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    xml = part((out / "T8.docx").read_bytes(), "word/document.xml")
    assert re.search(r"QQa</w:t>\s*<w:br/>\s*<w:t[^>]*>bZZ", xml)
    assert re.search(r"JJa</w:t>\s*<w:br/>\s*<w:t[^>]*>bKK", xml)
    assert re.search(r"TTa</w:t></w:r>\s*<w:r>\s*<w:tab/>\s*</w:r>\s*<w:r>\s*<w:t[^>]*>bUU", xml)


@needs_extra
@pytest.mark.parametrize("name, code", [("a\nb", "U+000A"), ("a\tb", "U+0009")])
def test_a_newline_or_a_tab_in_model_name_halts_h08_and_writes_nothing(
    tmp_path, monkeypatch, capsys, name, code
):
    """``model.name`` ``a`` + newline + ``b`` and ``a`` + tab + ``b``: exit 3, the H08 line
    naming ``model/name`` and the code point, and no out directory."""
    crit = _criteria()
    crit["model"]["name"] = name
    rc, out = _cli(tmp_path, monkeypatch, crit, "--format", "docx", "--templates", "T8")
    printed = capsys.readouterr()
    text = printed.out + printed.err
    assert rc == EXIT_HALT == 3, text
    assert "HALT H08: declaration invalid at model/name: control character " + code in text
    assert not out.exists()
