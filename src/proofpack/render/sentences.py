"""Sentences from the claim template library (build day 9, E9; D4 section 8, D1 section 4.4).

A claim carries no number and no prose: it names a template, the Numbers it reports (RFC
6901 pointers into ``run.json``) and the row it is about. This module turns one claim
into one sentence, and nothing else does:

1. the library key ``{template_id, metric_id, subgroup_id, comparator_id, status}``
   selects the skeleton (:func:`proofpack.narrate.templates.lookup`: the template's own,
   or a recorded variant - the non-proportion ``OVERALL_ESTIMATE`` has no ``k/n``, a
   Number with a typed reason prints the reason instead of an interval);
2. every Number slot is filled **by pointer facet** (E8 carried rows 51, 52): the
   pointers are read through :func:`proofpack.narrate.checker.pointer_facets` into
   selectors (``value``, ``diff``, a family metric such as ``oe`` or ``tpr_gap``, a
   documented scalar's key), and each slot's binding ``<selector>.<facet>`` names the one
   it takes - so a claim binding a subset of ``CALIB_HIERARCHY``'s pointers prints
   ``not reported`` in the missing slots and never shifts a number into another slot;
3. every facet is printed by :mod:`proofpack.render.format` under the metric's rule of
   D4 section 1.2 (a proportion as ``30.8%``, an AUROC to three decimals, a difference in
   signed percentage points); this module does no arithmetic and never rounds;
4. every text slot is filled from the document: the manufacturer's words (level labels,
   operating-point ids, author, date, source; :data:`~proofpack.narrate.templates.
   CUSTOMER_SLOTS`) are returned as ``customer`` parts, which the HTML renderer prints
   escaped inside ``.customer-text``; the status word is a ``status`` part, printed
   inside ``.status``; declared numbers print every digit (``format.declared``).

:func:`render_parts` is the pure core (a skeleton, Numbers by selector, text by slot);
:func:`claim_parts` builds its inputs from a claim and the document. A text slot the
context does not supply raises :class:`SentenceError` (a sentence is never printed with a
hole in it).
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Any

from proofpack.narrate import checker as checker_mod
from proofpack.narrate import templates as lib
from proofpack.render import format as fmt

NOT_REPORTED = "not reported"
#: Selectors that print on the claim metric's own scale (a both-ways or split estimate of
#: the claim's metric), and selectors that are proportions whatever the metric.
_SAME_SCALE_SELECTORS: frozenset[str] = frozenset({"value", "pos", "neg", "complete", "missing"})
_PROPORTION_SELECTORS: frozenset[str] = frozenset(
    {"se_minus", "se_plus", "sp_minus", "sp_plus", "ref", "cur"}
)
#: ``AUROC_ESTIMATE``'s ``method_phrase`` key, from the Number's own method.
AUROC_METHOD_PHRASE_KEYS: dict[str, str] = {
    "delong_logit": "iid",
    "delong_wald": "iid_wald",
    "cluster_bootstrap_percentile": "clustered",
}


class SentenceError(ValueError):
    """A skeleton slot the context does not fill, or an unknown facet or template."""


@dataclass(frozen=True)
class Part:
    """One run of a sentence: ``fixed`` (the skeleton's own text), ``engine`` (a value the
    engine printed), ``customer`` (the manufacturer's words) or ``status`` (a status
    word from ``STATUS_WORDS``)."""

    text: str
    kind: str


def selector_kind(selector: str, metric_id: str | None) -> str:
    """The printing rule (:data:`proofpack.render.format.KINDS`) for one selector."""
    if selector in _SAME_SCALE_SELECTORS:
        return fmt.kind_for(metric_id)
    if selector == "diff":
        return fmt.kind_for(metric_id, difference=True)
    if selector in _PROPORTION_SELECTORS:
        return "proportion"
    return fmt.kind_for(selector)


def facet_text(value: Any, facet: str, kind: str) -> str:
    """One facet of one bound value (a Number dict or a documented scalar)."""
    if facet not in lib.FACETS:
        raise SentenceError(f"unknown facet {facet!r}")
    if value is None:
        return NOT_REPORTED
    if facet == "count":
        return fmt.count(value)
    if facet == "p":
        return fmt.p_value(value)
    if facet == "scalar":
        return fmt.scalar(value)
    if not isinstance(value, dict):
        raise SentenceError(f"facet {facet!r} needs a Number, got {type(value).__name__}")
    if facet == "est":
        return fmt.estimate(value, kind)
    if facet == "ci":
        return fmt.interval(value, kind)
    if facet in ("ci_lo", "ci_hi"):
        return fmt.one_bound(value, facet, kind)
    if facet == "estci":
        return fmt.number(value, kind)
    if facet in ("k", "n"):
        return fmt.count(value.get(facet)) if value.get(facet) is not None else "—"
    if facet == "method":
        m = fmt.text(value.get("method"))
        return lib.METHOD_PHRASES.get(m, m)
    # reason
    if value.get("suppressed"):
        return "suppressed"
    return fmt.text(value.get("not_estimable_reason")) or "no_interval"


def _fill(
    skeleton: str,
    facets: dict[str, tuple[str, ...]],
    numbers: dict[str, Any],
    text: dict[str, Any],
    metric_id: str | None,
    phrases: dict[str, dict[str, str]],
) -> list[Part]:
    parts: list[Part] = []
    seen: dict[str, int] = {}
    for literal, slot, _, _ in string.Formatter().parse(skeleton):
        if literal:
            parts.append(Part(literal, "fixed"))
        if slot is None:
            continue
        i = seen.get(slot, 0)
        seen[slot] = i + 1
        if slot in facets:
            binding = facets[slot][i]
            selector, _, facet = binding.partition(".")
            parts.append(
                Part(
                    facet_text(numbers.get(selector), facet, selector_kind(selector, metric_id)),
                    "engine",
                )
            )
            continue
        if slot in phrases:
            key = text.get(slot)
            if key not in phrases[slot]:
                raise SentenceError(f"slot {slot!r}: no phrase for key {key!r}")
            parts.extend(_fill(phrases[slot][key], {}, numbers, text, metric_id, phrases))
            continue
        if slot == "status_word":
            parts.append(Part(lib.STATUS_WORDS[str(text[slot])], "status"))
            continue
        if slot not in text:
            raise SentenceError(f"slot {slot!r} has no value in the context")
        value = text[slot]
        if slot in lib.DECLARED_SLOTS:
            parts.append(Part(fmt.declared(value), "customer"))
        elif slot in lib.CUSTOMER_SLOTS:
            parts.append(Part(fmt.text(value), "customer"))
        else:
            parts.append(Part(fmt.text(value), "engine"))
    return parts


def render_parts(
    template_id: str,
    *,
    numbers: dict[str, Any] | None = None,
    text: dict[str, Any] | None = None,
    metric_id: str | None = None,
    subgroup_id: Any = None,
    comparator_id: str | None = None,
    status: str | None = None,
) -> list[Part]:
    """One sentence as parts, from the library key and its inputs."""
    if template_id not in lib.LIBRARY:
        raise SentenceError(f"unknown template {template_id!r}")
    skeleton, facets, _ = lib.lookup(template_id, metric_id, subgroup_id, comparator_id, status)
    ctx = dict(text or {})
    if metric_id is not None and "metric_name" not in ctx:
        ctx["metric_name"] = lib.METRIC_NAMES.get(metric_id, metric_id)
    parts = _fill(
        skeleton,
        facets,
        numbers or {},
        ctx,
        metric_id,
        lib.LIBRARY[template_id].phrases or {},
    )
    if skeleton.startswith("{metric_name}") and parts and parts[0].text[:1].islower():
        parts[0] = Part(parts[0].text[:1].upper() + parts[0].text[1:], parts[0].kind)
    return parts


def render_text(template_id: str, **kw: Any) -> str:
    """:func:`render_parts` joined: the sentence as plain text."""
    return "".join(p.text for p in render_parts(template_id, **kw))


# ------------------------------------------------------------------ from a claim


def _unescape(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def claim_numbers(claim: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    """The claim's bound values by selector (see the module docstring, step 2)."""
    family = claim.get("template_id") in checker_mod.METRIC_FAMILIES
    out: dict[str, Any] = {}
    for ref in claim.get("value_refs") or []:
        found, value = checker_mod.resolve_pointer(document, ref)
        if not found:
            continue
        facets = checker_mod.pointer_facets(ref)
        if facets is None:
            selector = _unescape(ref.rsplit("/", 1)[-1])
        elif facets.block is not None:
            selector = "diff"
        elif family:
            selector = str(facets.metric)
        else:
            selector = "value"
        out.setdefault(selector, value)
    return out


def _declaration_entry(document: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    decl = document.get("declarations") or {}
    index = row.get("declaration_index")
    if index is None:
        return decl.get("fairness") or {}
    entries = decl.get("criteria") or []
    if isinstance(index, int) and 0 <= index < len(entries) and isinstance(entries[index], dict):
        return entries[index]
    return {}


def scope_text(row: dict[str, Any]) -> str:
    scope = row.get("scope")
    base = (
        f"{fmt.text(scope.get('attribute'))} = {fmt.text(scope.get('level'))}"
        if isinstance(scope, dict)
        else fmt.text(scope)
    )
    op = row.get("operating_point")
    return f"{base}, {fmt.text(op)}" if op else base


def claim_key(claim: dict[str, Any]) -> dict[str, Any]:
    """The library key of a claim (D1 section 3.1)."""
    if claim.get("template_id") in checker_mod.CRITERION_TEMPLATES:
        status = claim.get("status")
    else:
        status = "not_assessable" if claim.get("relation") == "not_assessable" else None
    return {
        "metric_id": claim.get("metric_id"),
        "subgroup_id": claim.get("subgroup"),
        "comparator_id": claim.get("comparator_id"),
        "status": status,
    }


def claim_text(claim: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    """The text slots of one claim, read from the claim and the document."""
    ctx: dict[str, Any] = {}
    if claim.get("operating_point") is not None:
        ctx["op_id"] = claim["operating_point"]
    sub = claim.get("subgroup")
    if isinstance(sub, dict):
        ctx["attribute"] = sub.get("attribute")
        ctx["level"] = sub.get("level")
    ref = claim.get("reference")
    if isinstance(ref, dict):
        ctx["reference_level"] = ref.get("level")
    tid = claim.get("template_id")
    decl = document.get("declarations") or {}
    if tid == "AUROC_ESTIMATE":
        numbers = claim_numbers(claim, document)
        num = numbers.get("value") if isinstance(numbers.get("value"), dict) else {}
        ctx["method_phrase"] = AUROC_METHOD_PHRASE_KEYS.get(str(num.get("method")), "iid_wald")
        n_cases = num.get("n_cases")
        if n_cases is None:
            n_cases = (document.get("flow") or {}).get("n_cases")
        ctx["n_cases"] = fmt.count(n_cases)
    if tid == "CALIB_NA":
        ctx["score_type"] = (decl.get("score") or {}).get("type")
    if tid in checker_mod.CRITERION_TEMPLATES:
        rows = document.get("criteria_results") or []
        i = claim.get("criterion_index")
        row = rows[i] if isinstance(i, int) and 0 <= i < len(rows) else {}
        entry = _declaration_entry(document, row)
        ctx.update(
            {
                "criterion_id": row.get("criterion_id"),
                "scope": scope_text(row),
                "statistic": lib.STATISTIC_NAMES.get(
                    str(row.get("statistic")), fmt.text(row.get("statistic"))
                ),
                "comparator": fmt.text(row.get("comparator")),
                "value": fmt.declared(row.get("value")),
                "author": entry.get("author"),
                "date": entry.get("date"),
                "status_word": row.get("status"),
                "reason_clause": (
                    f" ({fmt.text(row.get('reason_code'))})"
                    if row.get("status") == "not_assessable"
                    else ""
                ),
            }
        )
        if tid == "ATTAINABILITY_NOTE":
            ctx["attainable_phrase"] = "true" if row.get("attainable_at_n") else "false"
    return ctx


def claim_parts(claim: dict[str, Any], document: dict[str, Any]) -> list[Part]:
    """The sentence one claim prints (the claims in ``run.json`` are already the checked
    list: accepted claims and, for a rejected one, the deterministic template claim of
    its slot - E8's :func:`proofpack.narrate.checker.resolve`)."""
    tid = str(claim.get("template_id"))
    key = claim_key(claim)
    text = claim_text(claim, document)
    return render_parts(
        tid,
        numbers=claim_numbers(claim, document),
        text=text,
        **key,
    )


def claim_sentence(claim: dict[str, Any], document: dict[str, Any]) -> str:
    return "".join(p.text for p in claim_parts(claim, document))
