"""Guidance anchors from ``design/guidance_map_v1.csv`` (D4 section 1.1; D1 section 3.1
``render.*``: templates never hard-code a section number, and every FDA AI-DSF anchor is
labelled as the draft it is).

:func:`guidance_ref_item` turns one ``internal_id`` into the structured item the
document carries (``guidance_refs``, D1's rule that the draft status is data, not
prose)::

    {"id": "FDA_AIDSF_SUBGROUP_PERF",
     "label": "FDA draft guidance, ... (Docket FDA-2024-D-4488): draft guidance
               (January 2025), not for implementation",
     "draft": true, "url": null}

The label is built from the map row alone: the document title, and for a draft row the
month and year of its ``version_date`` with the qualifier taken from the row's own
``status`` text. A row whose status begins ``draft`` and does not carry ``not for
implementation`` is refused with :class:`AnchorError` - the renderer never prints an
FDA draft anchor without the qualifier (``tests/test_render_t8.py`` plants such a row
in a temporary copy of the map and asserts the refusal). An unknown id is refused the
same way (D4 section 9: no silent blank margin notes).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from proofpack.errors import ProofPackError
from proofpack.resources import load_guidance_map

DRAFT_QUALIFIER = "not for implementation"


class AnchorError(ProofPackError):
    """An anchor the map cannot label: an unknown id, or a draft row without its qualifier."""


def _rows(guidance_map: Any) -> dict[str, dict[str, str]]:
    rows = load_guidance_map() if guidance_map is None else guidance_map
    return {
        str(r["internal_id"]): {str(k): ("" if v is None else str(v)) for k, v in r.items()}
        for r in rows
    }


def month_year(version_date: str) -> str:
    """``2025-01-07`` -> ``January 2025``; any other spelling is returned as written."""
    try:
        d = _dt.date.fromisoformat(version_date.strip())
    except ValueError:
        return version_date.strip()
    return f"{d.strftime('%B')} {d.year}"


def is_draft(row: dict[str, str]) -> bool:
    return row.get("status", "").strip().lower().startswith("draft")


def label_for(row: dict[str, str]) -> str:
    document = row.get("document", "").strip()
    status = row.get("status", "").strip()
    if is_draft(row):
        if DRAFT_QUALIFIER not in status.lower():
            raise AnchorError(
                f"guidance map row {row.get('internal_id')!r} is a draft without the "
                f"{DRAFT_QUALIFIER!r} qualifier in its status ({status!r}); refusing to render"
            )
        # the qualifier as the row spells it, after the word draft and its separator
        tail = status[status.lower().index(DRAFT_QUALIFIER) :]
        return f"{document}: draft guidance ({month_year(row.get('version_date', ''))}), {tail}"
    version = row.get("version_date", "").strip()
    return f"{document} ({version}, {status})" if version else f"{document} ({status})"


def guidance_ref_item(internal_id: str, guidance_map: Any = None) -> dict[str, Any]:
    rows = _rows(guidance_map)
    if internal_id not in rows:
        raise AnchorError(f"unknown guidance anchor {internal_id!r}; not in guidance_map_v1.csv")
    row = rows[internal_id]
    if not row.get("document") or not row.get("status"):
        raise AnchorError(f"guidance map row {internal_id!r} has an empty document or status")
    return {
        "id": internal_id,
        "label": label_for(row),
        "draft": is_draft(row),
        "url": row.get("url") or None,
    }


def resolve(ids: list[str] | tuple[str, ...], guidance_map: Any = None) -> list[dict[str, Any]]:
    """Distinct items in the map's own row order (so two runs list them identically)."""
    wanted = set(ids)
    rows = _rows(guidance_map)
    for i in wanted:
        if i not in rows:
            raise AnchorError(f"unknown guidance anchor {i!r}; not in guidance_map_v1.csv")
    return [guidance_ref_item(i, guidance_map) for i in rows if i in wanted]


def short_list(items: list[dict[str, Any]]) -> str:
    """The footer's ``<document, version/date, draft/final>`` list (D4 section 7.1)."""
    seen: list[str] = []
    for it in items:
        if it["label"] not in seen:
            seen.append(it["label"])
    return "; ".join(seen) if seen else "none"


def with_note_fields(item: dict[str, Any], guidance_map: Any = None) -> dict[str, Any]:
    """``item`` (from :func:`resolve`) plus the two parts of D4 section 1.1's margin note
    the label does not carry: ``section`` and ``estar``, from the map row, each printed
    ``to confirm`` while the row leaves it empty (every AI-DSF row today: D4 section 15's
    open item; E9 prints the gap instead of hiding it)."""
    row = _rows(guidance_map)[item["id"]]
    if row.get("status", "").strip().lower() == "internal":
        # ProofPack's own text (PP_SCOPE, PP_METHODS): no document section, no eSTAR slot
        return {**item, "section": "n/a", "estar": "n/a"}
    return {
        **item,
        "section": row.get("section", "").strip() or "to confirm",
        "estar": row.get("estar_section", "").strip() or "to confirm",
    }
