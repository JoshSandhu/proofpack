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


def draft_qualifier(internal_id: str, guidance_map: Any = None) -> str:
    """The qualifier a draft row's label carries after its title - ``draft guidance
    (January 2025), not for implementation`` for every AI-DSF row today - built by
    :func:`label_for` from the row alone. A final row, an unknown id or a draft without
    ``not for implementation`` is refused with :class:`AnchorError` (E11 item 1: the T1
    header line names the AI-DSF draft and carries this qualifier in the line itself)."""
    rows = _rows(guidance_map)
    if internal_id not in rows:
        raise AnchorError(f"unknown guidance anchor {internal_id!r}; not in guidance_map_v1.csv")
    row = rows[internal_id]
    if not is_draft(row):
        raise AnchorError(f"guidance map row {internal_id!r} is not a draft; it has no qualifier")
    label = label_for(row)
    return label[len(row.get("document", "").strip()) + 2 :]


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


def is_internal(row: dict[str, str]) -> bool:
    """A ProofPack-internal row (``PP_SCOPE``, ``PP_METHODS``): ProofPack's own text, not a
    regulatory reference - the map's ``status`` column reads ``internal``."""
    return row.get("status", "").strip().lower() == "internal"


def cover_documents(items: list[dict[str, Any]], guidance_map: Any = None) -> list[dict[str, Any]]:
    """The cover row ``Guidance versions referenced`` (T1, T2, T8; E14 item 1): each
    distinct guidance document once, by its map label (document, version or date, status
    - the draft qualifier stays in the label), in the order of ``items``, each item the
    first of ``items`` that carries the label (so the cover links to the guidance table's
    first row for it), and never a ProofPack-internal row. The guidance table itself keeps
    every id (the full register). At 3ee5601 the cover printed every item: on a licensed
    run of the 5,000-row synthetic cohort, T1's cover had 19 entries - the AI-DSF draft
    title 12 times and two ``ProofPack internal`` entries - for 3 documents."""
    rows = _rows(guidance_map)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for it in items:
        row = rows.get(str(it["id"]))
        if row is not None and is_internal(row):
            continue
        if it["label"] in seen:
            continue
        seen.add(it["label"])
        out.append(it)
    return out


def distinct_notes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One block's margin notes (items from :func:`with_note_fields`) with each visible
    line printed once (E14 item 2): items whose label, section and eSTAR text are all
    equal print as the first of them, which carries the other ids in ``also`` (rendered
    as the note's ``data-also`` attribute, so every anchor of the block is still cited);
    items that differ in any visible part stay. Returns copies; ``items`` is not changed
    (the DOCX template reads the same context, and prints a merged line's ids together in
    one bracket). At 3ee5601 T1 section 7 printed four lines, two of them repeats."""
    out: list[dict[str, Any]] = []
    first: dict[tuple[str, str, str], dict[str, Any]] = {}
    for it in items:
        key = (str(it["label"]), str(it["section"]), str(it["estar"]))
        if key in first:
            first[key]["also"].append(it["id"])
            continue
        copy = {**it, "also": []}
        first[key] = copy
        out.append(copy)
    return out


def with_note_fields(item: dict[str, Any], guidance_map: Any = None) -> dict[str, Any]:
    """``item`` (from :func:`resolve`) plus the two parts of D4 section 1.1's margin note
    the label does not carry: ``section`` and ``estar``, from the map row, each printed
    ``to confirm`` while the row leaves it empty (every AI-DSF row today: D4 section 15's
    open item; E9 prints the gap instead of hiding it)."""
    row = _rows(guidance_map)[item["id"]]
    if is_internal(row):
        # ProofPack's own text (PP_SCOPE, PP_METHODS): no document section, no eSTAR slot
        return {**item, "section": "n/a", "estar": "n/a"}
    return {
        **item,
        "section": row.get("section", "").strip() or "to confirm",
        "estar": row.get("estar_section", "").strip() or "to confirm",
    }
