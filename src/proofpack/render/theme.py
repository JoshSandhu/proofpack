"""The theme: ``design/tokens.json`` read once through :func:`proofpack.resources.resource_path`
(D5 section 4: the engine repository is the master copy, shipped in the wheel as
``proofpack/_schema/tokens.json`` beside the guidance map) and exposed as the values the
templates use and as one CSS custom-property block.

The templates carry no colour, type or spacing literal of their own: ``base.html``'s one
``<style>`` block references ``var(--pp-*)`` and the values come from :func:`css_variables`
inlined by :mod:`proofpack.render.html`. ``tests/test_render_theme.py`` greps the
templates for hex colours and the rendered HTML for ``@import``, ``url(``, ``<link`` and
``<script`` (must be none, D5 section 3.5) and asserts every ``--pp-`` value in the
rendered page equals the token file's.

``stop`` and ``ok`` are never applied to a customer's criterion status (D5 section 3.1,
principle 3): the criteria table's status cells use ``ink`` only.
"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

from proofpack.resources import resource_path

TOKENS_FILE = "tokens.json"


@cache
def tokens() -> dict[str, Any]:
    """The token file as parsed; cached for the process."""
    with resource_path(TOKENS_FILE).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def color(name: str) -> str:
    """The hex value of one colour token (``KeyError`` on an unknown name)."""
    return str(tokens()["color"][name]["value"])


def _flatten(prefix: str, node: Any, out: dict[str, str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _flatten(f"{prefix}-{key.replace('_', '-')}", value, out)
    else:
        out[prefix] = str(node)


def css_variables() -> dict[str, str]:
    """Every value the templates may use, as ``--pp-<group>-<name>`` custom properties.

    Colours are ``--pp-color-<token>`` (the value only; the role and contrast are data
    for the drift and contrast tests, not for the page); ``type``, ``space``, ``radius``,
    ``layout`` and ``print`` are flattened by key path with ``_`` written as ``-``
    (``--pp-print-page-margin``).
    """
    t = tokens()
    out: dict[str, str] = {}
    for name, entry in t["color"].items():
        out[f"--pp-color-{name}"] = str(entry["value"])
    for group in ("type", "space", "radius", "layout", "print"):
        _flatten(f"--pp-{group}", t[group], out)
    return out


def css_root_block() -> str:
    """The ``:root { ... }`` declaration block, one property per line, sorted."""
    lines = [f"  {k}: {v};" for k, v in sorted(css_variables().items())]
    return ":root {\n" + "\n".join(lines) + "\n}"
