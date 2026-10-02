"""A-P4 repair 3 (2 October 2026, the orchestrator, after lens round 3 at fd9488f ended FAIL
at the cap with one blocker).

- FA3-B1 = RG3-B1: the F2, F3 and F4 PNG legends carry engine numbers (on the synthetic
  document, ``AUROC 0.835 [0.795, 0.876]`` and the calibration slope and intercept with their
  intervals) that no test read; a mutant rounding them to two places survived all 190 ap4
  tests. Each PNG legend's labelled entry is now compared with the SVG legend text of the
  same figure in the rendered T1 page
  (``test_f2_f3_f4_png_legends_equal_the_svg_legend_text``).
- FA2-N1 = FA3-N3: ``$\\foo$`` in a criterion author (or a level) reached matplotlib's
  mathtext parser and ``png_bytes`` raised ``ParseFatalException: Unknown symbol: \\foo``,
  so a licensed run ended at exit 5 after ``run.json``. The drawers now run with
  ``text.parse_math`` off and the string is drawn as written
  (``test_a_dollar_backslash_string_in_a_criterion_author_draws_as_written``).
"""

from __future__ import annotations

import copy
import html
import re

import pytest

from ap4_docx import needs_extra, synthetic_document
from test_render_figures import _criterion, _figure

pytestmark = [pytest.mark.day10, pytest.mark.ap4]


def _svg_legend(figure_html: str, spec: dict) -> str:
    # templates/_figures.html: F2/F3 place the legend at the spec's legend_x/legend_y, F4 at
    # x="90" y="40".
    x, y = spec.get("legend_x", 90), spec.get("legend_y", 40)
    m = re.search(rf'<text class="fig-text" x="{x}" y="{y}">([^<]*)</text>', figure_html)
    assert m, spec["id"]
    return html.unescape(m.group(1))


@needs_extra
def test_f2_f3_f4_png_legends_equal_the_svg_legend_text():
    """F2's PNG legend is ``chance (dashed)`` then the SVG's legend text, and F4's figure
    legend is ``identity (dashed)`` then the SVG's, on the synthetic document; F2's text
    carries ``AUROC 0.835 [0.795, 0.876]`` (lens 3's example) and F4's a slope and an
    intercept. The engine writes no precision-recall array (F3_ABSENT: from v1.1), so F3 is
    checked on a copy of that document given the array ``[[0.0, 1.0], [0.5, 0.75],
    [1.0, 0.3]]``: its legend is ``prevalence baseline (dashed)`` then the SVG's."""
    from proofpack.render import figures, figures_png
    from proofpack.render import t1 as render_t1

    document = synthetic_document()
    with_pr = copy.deepcopy(document)
    tf = with_pr["overall"]["threshold_free"]
    tf["pr"] = [[0.0, 1.0], [0.5, 0.75], [1.0, 0.3]]
    assert figures.f3_pr(document, {}) is None
    cases = [
        (document, figures.f2_roc, figures_png.f2_figure, "chance (dashed)"),
        (with_pr, figures.f3_pr, figures_png.f3_figure, "prevalence baseline (dashed)"),
        (document, figures.f4_calibration, figures_png.f4_figure, "identity (dashed)"),
    ]
    seen = {}
    for doc, svg_fn, png_fn, reference in cases:
        spec, fig = svg_fn(doc, {}), png_fn(doc, {})
        assert spec is not None and fig is not None
        page = render_t1.render_t1(doc)
        svg = _svg_legend(_figure(page, spec["id"]), spec)
        legend = fig.legends[0] if fig.legends else fig.axes[0].get_legend()
        png = [t.get_text() for t in legend.get_texts()]
        assert png == [reference, svg], (spec["id"], png, svg)
        assert re.search(r"\d", svg), (spec["id"], svg)
        seen[spec["id"]] = svg
    assert len(seen) == 3
    assert any("AUROC 0.835 [0.795, 0.876]" in s for s in seen.values()), seen
    assert any("slope" in s and "intercept" in s for s in seen.values()), seen


@needs_extra
def test_a_dollar_backslash_string_in_a_criterion_author_draws_as_written():
    """A ``ci_lower_bound`` criterion on sex/sensitivity/op1 whose author is ``$\\foo$``:
    every F5 PNG is written (``png_bytes`` returns PNG bytes) and the criterion legend entry
    carries ``$\\foo$`` literally. At fd9488f ``png_bytes`` raised ``ValueError`` from
    mathtext (``Unknown symbol: \\foo``)."""
    from assembler import assemble
    from conftest import make_cohort, make_criteria
    from proofpack.render import figures_png

    author = "$" + chr(92) + "foo$"
    doc = assemble(
        make_cohort(n=240), make_criteria(criteria=[_criterion(author=author)], fairness=None)
    )
    figs = figures_png.f5_figures(doc, {})
    legends = []
    for per_metric in figs.values():
        for fig in per_metric:
            assert figures_png.png_bytes(fig).startswith(b"\x89PNG\r\n\x1a\n")
            legend = fig.axes[0].get_legend()
            legends.extend(t.get_text() for t in (legend.get_texts() if legend else []))
    assert any(author in t for t in legends), legends
