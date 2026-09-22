"""HTML rendering through jinja2 (build day 8, E8): T8 (D4 section 11) from a run document.

jinja2 is imported here only, inside :func:`environment`; the module imports without it
and :class:`RendererUnavailable` names the missing package. The environment has
autoescape **on** for every template, ``StrictUndefined`` (a missing key fails the
render loudly rather than printing blank), and no template does arithmetic: every
number on the page comes through the ``fmt_*`` filters, which are
:mod:`proofpack.render.format` (D4 section 1.2) and nothing else.

What the page carries and where it comes from:

* one ``<style>`` block whose values are the theme's custom properties inlined from
  ``design/tokens.json`` (:mod:`proofpack.render.theme`) - the only source of colour,
  type and spacing; no ``@import``, ``url(``, ``<link>``, ``<script>`` or external font;
* the D4 section 7.1 short disclaimer as the footer of **every** page section (and once
  more as the fixed print footer), with the manifest's watermark word beside it when
  present; the date and version are the manifest's, never ``now()``;
* the anchors' labels from :mod:`proofpack.render.anchors` (the map row, never the
  template), each ``guidance_refs`` row carrying the map's ``internal_id`` as its HTML id;
* section 7's counts computed here in Python from the document
  (:func:`narrative_integrity`), not typed in the template;
* customer text (justifications, the ``criteria.yaml`` echo, level labels) rendered
  verbatim and escaped, in the ``customer-text`` style D4 section 1.3 asks for, so a
  reviewer cannot mistake it for engine output. The engine never rewrites a customer's
  words: a justification containing ``pass`` is printed as written, escaped; the page's
  verdict grep (``tests/test_render_t8.py``) treats hits inside ``.customer-text`` as
  the customer's and asserts they occur nowhere else. Bidirectional control characters
  (U+202A-U+202E, U+2066-U+2069, U+200E-U+200F) in any string are written as numeric
  character references so a right-to-left override in a label cannot reorder the page.

``render_t8(document)`` returns the page as a string; :func:`write_t8` writes it as UTF-8
with ``\\n`` line endings. The HTML is a pure function of the document and the template
version: no timestamp, no random id, no environment value reaches the page.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from proofpack import __version__
from proofpack.errors import WARN_CODES, ProofPackError
from proofpack.narrate import claims as claims_mod
from proofpack.narrate.checker import resolve_pointer
from proofpack.narrate.templates import NARRATIVE_FOOTER, STATUS_WORDS
from proofpack.render import anchors
from proofpack.render import format as fmt
from proofpack.render.theme import css_root_block
from proofpack.scope import LONG_FORM_ITEMS, LONG_FORM_TITLE, SHORT_FORM

#: Inside the package, so a built wheel carries the templates with the code (a
#: repository-root ``templates/`` directory would not ship; D4 section 9 names the
#: file names, the location is the E8 build note's decision).
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
T8_FILE = "T8.html"
#: The anchors T8's own sections cite (D4 section 11), resolved through the map like a
#: claim's ``guidance_ref``; they join the document's ``guidance_refs`` in section 9.
T8_ANCHORS: dict[str, str] = {
    "disclaimer": "PP_SCOPE",
    "manifest": "PP_METHODS",
    "declarations": "FDA_AIDSF_DATA_MGMT",
    "criteria": "FDA_AIDSF_PERF_VALIDATION",
    "ledger": "FDA_PCCP_MP1_DATA",
    "narrative": "PP_SCOPE",
}
_BIDI = re.compile("[‪-‮⁦-⁩‎‏]")


class RendererUnavailable(ProofPackError):
    """jinja2 is not installed: ``pip install jinja2>=3.1`` (a runtime dependency of the
    package; the HTML renderer is the only importer)."""

    def __init__(self, package: str = "jinja2") -> None:
        self.package = package
        super().__init__(
            f"the HTML renderer needs the package {package!r}, which is not installed "
            f"(install proofpack with its dependencies: {package}>=3.1)"
        )


class TemplateNotBuilt(ProofPackError):
    """A template id the CLI accepts but E8 does not render (T1, T7: E9)."""


def environment() -> Any:
    """A jinja2 environment over ``templates/``: autoescape on, ``StrictUndefined``."""
    try:
        import jinja2  # noqa: PLC0415 - imported here only, so `import proofpack` needs no jinja2
    except ImportError as exc:
        raise RendererUnavailable("jinja2") from exc
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(
        {
            "fmt_number": fmt.number,
            "fmt_count": fmt.count,
            "fmt_scalar": fmt.scalar,
            "fmt_text": fmt.text,
            "fmt_method": fmt.method,
            "fmt_p": fmt.p_value,
        }
    )
    return env


def neutralise_bidi(html: str) -> str:
    return _BIDI.sub(lambda m: f"&#x{ord(m.group(0)):x};", html)


# ----------------------------------------------------------------- page furniture


def footer_text(document: dict[str, Any], refs: list[dict[str, Any]]) -> str:
    manifest = document["manifest"]
    return SHORT_FORM.format(
        version=manifest.get("engine_version") or __version__,
        date=fmt.text(manifest.get("started")),
        guidance_refs=anchors.short_list(refs),
    )


def header_text(document: dict[str, Any], template_name: str) -> str:
    model = (document.get("declarations") or {}).get("model") or {}
    run_id = fmt.text(document["manifest"].get("run_id"))[:8]
    return (
        f"{fmt.text(model.get('name'))} v{fmt.text(model.get('version'))} · "
        f"{template_name} · ProofPack v{document['manifest'].get('engine_version') or __version__}"
        f" · run {run_id}"
    )


def furniture(
    document: dict[str, Any], template_name: str, refs: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "css": css_root_block(),
        "header": header_text(document, template_name),
        "footer": footer_text(document, refs),
        "watermark": document["manifest"].get("watermark"),
        "narrative_footer": NARRATIVE_FOOTER,
    }


# ----------------------------------------------------------------- T8 sections


def _walk_numbers(node: Any):
    if isinstance(node, dict):
        if {"est", "ci_lo", "ci_hi", "method", "suppressed"} <= set(node):
            yield node
        for v in node.values():
            yield from _walk_numbers(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_numbers(v)


def narrative_integrity(document: dict[str, Any]) -> dict[str, Any]:
    """T8 section 7 (D4 section 11 item 7) plus the counts the brief asks the page to
    carry: computed from the document, never typed."""
    rejections = document.get("claim_rejections") or []
    rows = document.get("criteria_results") or []
    status_counts = Counter(r.get("status") for r in rows)
    return {
        "claims_generated": len(document.get("claims") or []),
        "claims_rejected": len(rejections),
        "claims_substituted": sum(1 for r in rejections if r.get("substituted")),
        "rejection_reasons": sorted(Counter(r.get("reason_code") for r in rejections).items()),
        "rows_analysed": (document.get("flow") or {}).get("analysed"),
        "subgroup_rows": len(document.get("subgroups") or []),
        "criteria_rows": len(rows),
        "criteria_by_status": [(s, status_counts.get(s, 0)) for s in STATUS_WORDS],
        "suppressed_cells": sum(1 for n in _walk_numbers(document) if n.get("suppressed")),
        "warnings": len(document.get("warnings") or []),
        "halts": len(document.get("halts") or []),
    }


def _authored(document: dict[str, Any], criterion_id: str) -> str:
    decl = document.get("declarations") or {}
    pairs: list[str] = []
    for c in decl.get("criteria") or []:
        if str(c.get("id")) == criterion_id:
            pair = f"{fmt.text(c.get('author'))} · {fmt.text(c.get('date'))}"
            if pair not in pairs:
                pairs.append(pair)
    if criterion_id.startswith("fairness:"):
        f = decl.get("fairness") or {}
        pairs.append(f"{fmt.text(f.get('author'))} · {fmt.text(f.get('date'))}")
    return "; ".join(pairs) if pairs else "—"


def _justification(document: dict[str, Any], criterion_id: str) -> str:
    decl = document.get("declarations") or {}
    texts: list[str] = []
    for c in decl.get("criteria") or []:
        if str(c.get("id")) == criterion_id and c.get("justification") not in texts:
            texts.append(fmt.text(c.get("justification")))
    if criterion_id.startswith("fairness:"):
        texts.append(fmt.text((decl.get("fairness") or {}).get("justification")))
    return " / ".join(texts)


def _scope_text(scope: Any) -> str:
    if isinstance(scope, dict):
        return f"{fmt.text(scope.get('attribute'))} = {fmt.text(scope.get('level'))}"
    return fmt.text(scope)


def criteria_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Table 5.6, one entry per ``criteria_results`` row **by position**; the observed
    Number is the row's own ``metric_ref`` resolved in the document and printed by the
    metric's rule; the declared value, compared value and the attainability bound are
    printed on the unit scale to three decimals (the scale the customer wrote)."""
    out: list[dict[str, Any]] = []
    for i, row in enumerate(document.get("criteria_results") or []):
        ref = claims_mod._dotted_to_pointer(row.get("metric_ref"))
        number = None
        if ref is not None:
            found, value = resolve_pointer(document, ref)
            number = value if found and isinstance(value, dict) else None
        kind = fmt.kind_for(
            row.get("metric"), difference=str(row.get("metric", "")).endswith("_gap")
        )
        out.append(
            {
                "position": i + 1,
                "criterion_id": fmt.text(row.get("criterion_id")),
                "metric": fmt.text(row.get("metric")),
                "scope": _scope_text(row.get("scope")),
                "operating_point": fmt.text(row.get("operating_point")) or "—",
                "statistic": fmt.text(row.get("statistic")).replace("_", " "),
                "comparator": fmt.text(row.get("comparator")),
                "value": fmt.scalar(row.get("value")),
                "authored": _authored(document, str(row.get("criterion_id"))),
                "observed": fmt.number(number, kind) if number is not None else "—",
                "n": fmt.count(row.get("n")) if row.get("n") is not None else "—",
                "method": fmt.text(row.get("method")) or "—",
                "compared_value": fmt.scalar(row.get("compared_value")),
                "status_word": STATUS_WORDS[row["status"]],
                "reason_code": fmt.text(row.get("reason_code")),
                "attainable_at_n": fmt.scalar(row.get("attainable_at_n")),
                "max_lower_bound_at_n": fmt.scalar(row.get("max_lower_bound_at_n")),
                "detail": "; ".join(f"{k}: {v}" for k, v in (row.get("detail") or {}).items()),
                "justification": _justification(document, str(row.get("criterion_id"))),
            }
        )
    return out


def manifest_rows(document: dict[str, Any]) -> list[tuple[str, str]]:
    m = document["manifest"]
    order = (
        ("run_id", "Run id"),
        ("engine_version", "Engine version"),
        ("platform", "Platform"),
        ("python", "Python"),
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("reference_platform", "Reference platform"),
        ("input_sha256", "Input SHA-256"),
        ("criteria_sha256", "criteria.yaml SHA-256"),
        ("mapping_sha256", "mapping.json SHA-256"),
        ("seed", "Seed"),
        ("B", "Bootstrap resamples (B)"),
        ("started", "Started (UTC)"),
        ("duration_s", "Duration (s)"),
        ("licence_id", "Licence id"),
        ("tier", "Licence tier"),
        ("ledger_count", "Ledger count"),
        ("watermark", "Watermark"),
    )
    return [
        (label, fmt.scalar(m.get(key)) if not isinstance(m.get(key), str) else m[key])
        for key, label in order
    ]


def declaration_rows(document: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """Table T1-1: the declarations that shape every number, positive class and score
    orientation highlighted (D4 section 11 item 3; VV fatal 4)."""
    d = document.get("declarations") or {}
    classes, score = d.get("classes") or {}, d.get("score") or {}
    ops = "; ".join(
        f"{fmt.text(o.get('id'))}: threshold {fmt.scalar(o.get('threshold'))} "
        f"rule {fmt.text(o.get('rule'))}, {fmt.text(o.get('provenance'))} "
        f"({fmt.text(o.get('source'))})"
        for o in d.get("operating_points") or []
    )
    ref = d.get("reference_standard") or {}
    ind = d.get("indeterminates") or {}
    clu = d.get("clustering") or {}
    prev = "; ".join(
        f"{fmt.text(p.get('label'))}: {fmt.scalar(p.get('value'))} ({fmt.text(p.get('source'))})"
        for p in d.get("prevalence") or []
    )
    subs = "; ".join(
        f"{fmt.text(s.get('attribute'))} (reference {fmt.text(s.get('reference_level'))}; "
        f"{'pre-specified' if s.get('prespecified') else 'exploratory'})"
        for s in d.get("subgroups") or []
    )
    fair = d.get("fairness") or {}
    return [
        ("Positive class", fmt.text(classes.get("positive")), True),
        ("Negative class", fmt.text(classes.get("negative")), False),
        ("Score type", fmt.text(score.get("type")), False),
        ("Score orientation", fmt.text(score.get("orientation")), True),
        ("Operating points", ops, False),
        (
            "Reference standard",
            f"{fmt.text(ref.get('type'))} ({fmt.text(ref.get('description'))})",
            False,
        ),
        ("Indeterminates", f"{fmt.text(ind.get('policy'))} {fmt.text(ind.get('values'))}", False),
        (
            "Clustering unit",
            f"{fmt.text(clu.get('unit'))} (declared by {fmt.text(clu.get('declared_by'))})",
            False,
        ),
        ("Intended-use prevalence", prev, False),
        ("Subgroups", subs, False),
        (
            "Fairness criterion of interest",
            f"{fmt.text(fair.get('criterion_of_interest'))} on "
            f"{fmt.text(fair.get('attribute'))}; bound {fmt.scalar(fair.get('bound'))} "
            f"({fmt.text(fair.get('statistic'))} {fmt.text(fair.get('comparator'))})"
            if fair
            else "none declared",
            False,
        ),
    ]


def warning_rows(document: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "code": fmt.text(w.get("code")),
            "text": WARN_CODES.get(str(w.get("code")), ""),
            "params": ", ".join(f"{k} {v}" for k, v in (w.get("params") or {}).items()),
        }
        for w in document.get("warnings") or []
    ]


def out_of_scope_items() -> list[str]:
    body = LONG_FORM_ITEMS[3][1]
    return [s.strip().rstrip(".") for s in body.split(";") if s.strip()]


def t8_context(document: dict[str, Any], guidance_map: Any = None) -> dict[str, Any]:
    ids = [
        r["id"] for r in document.get("guidance_refs") or [] if isinstance(r, dict) and r.get("id")
    ]
    ids += list(T8_ANCHORS.values())
    refs = anchors.resolve(ids, guidance_map)
    by_id = {r["id"]: r for r in refs}
    ledger = document.get("ledger") or {}
    declared_limit = ((document.get("declarations") or {}).get("ledger") or {}).get(
        "warn_after_acceptance_runs"
    )
    ctx = {
        "template_name": "T8 · Run manifest, declarations, scope and disclaimer",
        "document": document,
        "long_form_title": LONG_FORM_TITLE,
        "long_form_items": LONG_FORM_ITEMS,
        "manifest_rows": manifest_rows(document),
        "declaration_rows": declaration_rows(document),
        # the declarations block of run.json re-serialised as YAML with sorted keys - the
        # canonical order run.json itself uses - so the page is a pure function of the
        # written document; the file's own bytes are represented by criteria_sha256
        "criteria_yaml": yaml.safe_dump(
            document.get("declarations") or {}, sort_keys=True, allow_unicode=True
        ),
        "criteria_rows": criteria_rows(document),
        "has_criteria": bool((document.get("declarations") or {}).get("criteria")),
        "warning_rows": warning_rows(document),
        "halts": document.get("halts") or [],
        "ledger": {
            "test_set_sha256": fmt.text(ledger.get("test_set_sha256")),
            "acceptance_runs": fmt.count(ledger.get("acceptance_runs")),
            "counted": bool(ledger.get("counted")),
            "warn_limit": fmt.count(ledger.get("warn_limit")),
            "declared_limit": fmt.count(declared_limit),
            "ledger_count": fmt.count(document["manifest"].get("ledger_count")),
        },
        "integrity": narrative_integrity(document),
        "rejections": document.get("claim_rejections") or [],
        "out_of_scope": out_of_scope_items(),
        "guidance_refs": refs,
        "anchor": {key: by_id[value] for key, value in T8_ANCHORS.items()},
        "customer_sections_outstanding": [],
        "status_words": STATUS_WORDS,
    }
    ctx.update(furniture(document, "T8", refs))
    return ctx


def render_t8(document: dict[str, Any], *, guidance_map: Any = None) -> str:
    env = environment()
    html = env.get_template(T8_FILE).render(**t8_context(document, guidance_map))
    return neutralise_bidi(html)


def render_pages(
    document: dict[str, Any], pages: list[str], *, template_name: str = "pages"
) -> str:
    """The base furniture around pre-rendered page bodies (the footer-per-page test's
    one- and two-page documents)."""
    env = environment()
    from markupsafe import Markup  # noqa: PLC0415 - MarkupSafe ships with jinja2

    refs = anchors.resolve([r["id"] for r in document.get("guidance_refs") or []])
    ctx = furniture(document, template_name, refs)
    html = env.get_template("pages.html").render(pages=[Markup(p) for p in pages], **ctx)
    return neutralise_bidi(html)


def write_t8(document: dict[str, Any], out_dir: str | Path) -> Path:
    target = Path(out_dir) / T8_FILE
    target.write_bytes(render_t8(document).encode("utf-8"))
    return target
