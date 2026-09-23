"""Pseudonymisation before egress (D1 section 6, "Aggregate payload rules", third
bullet): *``site``, ``device``, ``protocol`` and all ``attr_*`` levels replaced by ``Site
A, Site B ...``, ``Device A ...``, ``Level A ...`` in egress; the map is written to
``pseudonyms.json`` locally only.*

**Order (a decision, recorded in ``schema/egress_schema.json`` ``x-proofpack.
pseudonym_order``):** within one attribute, the original labels sorted by Unicode code
point (``sorted()`` on ``str``, locale-independent, the same on every platform) receive
``A``, ``B`` ... ``Z``, ``AA``, ``AB`` ... in that order. Not by size: the engine's own
level order for ``site`` is largest-first, and a rank by size would have to be re-derived
by any reader; code-point order is one line to state and one line to check.

**Collision rule (F19's ``Site A``):** an original label that happens to read like a
pseudonym is treated like any other label - it takes the position its code-point order
gives it, so the bytes ``Site A`` in a payload denote whichever original sorted first, not
the customer's site called ``Site A``. The map is a bijection on every attribute, written
locally so the customer can read the payload back; ``tests/test_egress.py::
test_f19_a_site_named_like_a_pseudonym_is_remapped_and_the_map_is_a_bijection`` pins it.

**Which levels:** every level of ``site``, ``device``, ``protocol`` and ``attr_*``. The
engine's own ``Unknown/missing`` row (``io.schema.UNKNOWN_LEVEL``) keeps its label - it is
the engine's word, not the customer's. A level of any other attribute (``sex``, ``age``)
passes through when it is a short token (:data:`TOKEN`: ``F``, ``Male``, ``40-65``) and is
pseudonymised with the ``Level`` prefix when it is not. The token rule reads the shape,
not the meaning: a ``sex`` column whose values are ``1987-03-04``, ``NHS4857773456`` and
``Jane.Doe-1961`` passes all three verbatim into the aggregates document's ``level``
field (measured 23 September 2026, ``tests/test_egress.py::
test_a_date_shaped_level_of_the_sex_column_passes_the_token_rule_verbatim``). No code
path sends the aggregates document at launch (``build.py``); before one does, this rule
needs an allow-list of engine-made labels in place of :data:`TOKEN`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from proofpack.io.schema import UNKNOWN_LEVEL

#: Attribute -> pseudonym prefix (D1 section 6). ``attr_*`` columns use :data:`LEVEL_PREFIX`.
PSEUDONYM_PREFIX: dict[str, str] = {"site": "Site", "device": "Device", "protocol": "Protocol"}
LEVEL_PREFIX = "Level"
ATTR_PREFIX = "attr_"
#: A level that may pass through unpseudonymised on an attribute D1 does not list.
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+-]{0,15}$")
PSEUDONYMS_JSON = "pseudonyms.json"
PSEUDONYMS_SCHEMA = "proofpack-pseudonyms/1"
ORDER_SENTENCE = (
    "within each attribute the original labels sorted by Unicode code point receive "
    "A, B ... Z, AA, AB ...; the Unknown/missing row keeps the engine's label"
)


def always_pseudonymised(attribute: str) -> bool:
    return attribute in PSEUDONYM_PREFIX or attribute.startswith(ATTR_PREFIX)


def prefix_for(attribute: str) -> str:
    return PSEUDONYM_PREFIX.get(attribute, LEVEL_PREFIX)


def letters(index: int) -> str:
    """``0 -> A``, ``25 -> Z``, ``26 -> AA``, ``701 -> ZZ``, ``702 -> AAA``."""
    if index < 0:
        raise ValueError(index)
    out = ""
    i = index
    while True:
        out = chr(ord("A") + i % 26) + out
        i = i // 26 - 1
        if i < 0:
            return out


def levels_in(document: Mapping[str, Any]) -> dict[str, set[str]]:
    """Every (attribute, level) the document tabulates: ``subgroup_attributes[*].
    level_order``, ``subgroups[*]``, ``fairness.gaps[*]`` and ``table1.test``."""
    found: dict[str, set[str]] = {}

    def add(attribute: Any, level: Any) -> None:
        if isinstance(attribute, str) and isinstance(level, str):
            found.setdefault(attribute, set()).add(level)

    for a in document.get("subgroup_attributes") or []:
        for lv in a.get("level_order") or []:
            add(a.get("attribute"), lv)
    for row in document.get("subgroups") or []:
        add(row.get("attribute"), row.get("level"))
    fairness = document.get("fairness") or {}
    for gap in fairness.get("gaps") or []:
        add(fairness.get("attribute"), gap.get("level"))
    table1 = document.get("table1") or {}
    for attribute, block in (table1.get("test") or {}).items():
        if isinstance(block, Mapping):
            for lv in block:
                add(attribute, lv)
    return found


def build_map(
    document: Mapping[str, Any], *, levels: Mapping[str, Iterable[str]] | None = None
) -> dict[str, dict[str, str]]:
    """``{attribute: {original: pseudonym}}`` for every level that must not leave as
    written. ``levels`` overrides :func:`levels_in` for a caller that already has them."""
    source = levels if levels is not None else levels_in(document)
    out: dict[str, dict[str, str]] = {}
    for attribute in sorted(source):
        originals = sorted(
            {lv for lv in source[attribute] if lv != UNKNOWN_LEVEL},
        )
        if always_pseudonymised(attribute):
            chosen = originals
        else:
            chosen = [lv for lv in originals if not TOKEN.match(lv)]
        if not chosen:
            continue
        prefix = prefix_for(attribute)
        out[attribute] = {orig: f"{prefix} {letters(i)}" for i, orig in enumerate(chosen)}
    return out


def pseudonym(mapping: Mapping[str, Mapping[str, str]], attribute: str, level: str) -> str:
    """The egress label of one level: the mapped pseudonym, the Unknown/missing row's own
    label, or the token itself. Raises ``KeyError`` for an unmapped non-token level, so
    an omission in the map is an error and never a pass-through."""
    if level == UNKNOWN_LEVEL:
        return level
    mapped = mapping.get(attribute, {})
    if level in mapped:
        return mapped[level]
    if not always_pseudonymised(attribute) and TOKEN.match(level):
        return level
    raise KeyError(f"no pseudonym for a level of {attribute!r}")


def pseudonyms_document(
    mapping: Mapping[str, Mapping[str, str]], *, run_id: str | None
) -> dict[str, Any]:
    """The local ``pseudonyms.json``: the map, the order rule and the run it belongs to."""
    return {
        "schema": PSEUDONYMS_SCHEMA,
        "run_id": run_id,
        "order": ORDER_SENTENCE,
        "local_only": True,
        "attributes": {a: dict(m) for a, m in mapping.items()},
    }
