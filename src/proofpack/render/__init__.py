"""Document rendering (build day 8, E8): HTML through jinja2, the theme from
``design/tokens.json``, the D4 section 1.2 number formatting.

``import proofpack.render`` never imports jinja2: the package is importable with jinja2
absent, and only :mod:`proofpack.render.html` imports it, inside the functions that need
it, raising :class:`proofpack.render.html.RendererUnavailable` (naming the package) when
it is missing. ``tests/test_render_theme.py`` hides jinja2 from ``sys.modules`` and
asserts ``proofpack``, ``proofpack.stats``, ``proofpack.narrate`` and this package still
import.
"""
