"""DOCX rendering through docxtpl (D4 section 9; D5 section 3.5; A-P4, build day 10, lane A).

``render_docx(document, template_id, out_path)`` writes ``T1.docx``, ``T7.docx`` or
``T8.docx`` from a run document and the committed template of the same id
(``templates/<id>.docx``, built by ``scripts/make_docx_templates.py``).

**One context.** The DOCX is rendered from the **same context** the HTML template of that
id is rendered from - :func:`proofpack.render.t1.t1_context`,
:func:`proofpack.render.t7.t7_context`, :func:`proofpack.render.html.t8_context` - and
the Jinja tags in the template name the same keys, so every number, caption and label is
the string the HTML prints. Four kinds of key are HTML-only, and :func:`docx_context`
adds the DOCX's reading beside each (never in place of it):

* the claim sentences (``sentences[*].html``, a ``Markup`` of ``<span>`` elements) - the
  DOCX carries ``rich``, a docxtpl ``RichText`` built from the same
  :func:`proofpack.render.sentences.claim_parts`: customer parts in the ``PP Customer
  Text Inline`` character style, status parts in ``PP Status``, the rest plain;
* the T8 YAML echo (``criteria_yaml_block``, a ``<pre>``) - the DOCX prints
  ``criteria_yaml``, the plain string the same context already carries;
* T7's conventions sections (``subgroup_conventions``, ``calibration_conventions``,
  ``coverage_conventions``, ``conventions_intro``, HTML from
  :func:`proofpack.render.markdown.to_html`) - the DOCX prints ``*_blocks``, the same
  markdown source split into paragraphs by :func:`markdown_blocks` (a pipe table becomes
  one monospace block of its rows; ``**`` and backticks are dropped, the words are the
  file's);
* the figures (``figures.f2`` etc., SVG coordinates) - the DOCX carries ``image``, an
  ``InlineImage`` of the PNG :mod:`proofpack.render.figures_png` draws from the same
  arrays, 160 mm wide, at the figure's position; where the spec is ``None`` the template
  prints the same no-data line the HTML prints.

``css`` (the theme's custom-property block) is unused: the DOCX's colours are the same
tokens, carried by its named styles.

**What the page keeps.** Customer text in ``PP Customer Text`` (paragraphs) or ``PP
Customer Text Inline`` (runs); the placeholder box as ``PP Placeholder``; ``‡`` and
``n.e.`` as text (:mod:`proofpack.render.format` prints them into the context); every
FDA-draft anchor with its map label in the margin-note tables; the criteria table with the
three status words only, in ``PP Status``; the manifest's watermark in every section's
footer beside the short disclaimer. Every string is XML-escaped by the Jinja environment
(``autoescape=True``, ``StrictUndefined``); a customer string is written as it is.

**The extra.** docxtpl, python-docx and matplotlib are imported inside :func:`render_docx`
and :func:`proofpack.render.figures_png` only. :func:`extra_available` asks
``importlib.util.find_spec`` for the three modules without importing them;
:func:`require_extra` raises :class:`DocxExtraMissing` (exit
:data:`proofpack.errors.EXIT_DOCX_EXTRA_MISSING`, one typed line naming the extra) and the
CLI checks it before any statistics run.

**Determinism.** docxtpl saves through python-docx, whose zip writer stamps every entry
with the wall clock; :func:`write_bytes` rewrites the container with every entry's mtime
set to the manifest's ``started`` (to the zip format's two-second resolution) and
``docProps/core.xml``'s created and modified set to the same instant, the author fixed,
so two renders of one ``run.json`` are byte-identical (``tests/test_ap4_roundtrip.py::
test_two_renders_of_one_document_are_byte_identical``, measured on ``win-amd64-cp314``).
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import io
import re
import zipfile
from pathlib import Path
from typing import Any

from proofpack.errors import EXIT_DOCX_EXTRA_MISSING, ProofPackError
from proofpack.render import format as fmt
from proofpack.render import html as render_html
from proofpack.render import markdown, sentences
from proofpack.resources import resource_path

TEMPLATES_DIR = render_html.TEMPLATES_DIR
DOCX_FILES: dict[str, str] = {"T1": "T1.docx", "T7": "T7.docx", "T8": "T8.docx"}
#: The three modules of the ``[docx]`` extra, by import name.
EXTRA_MODULES: tuple[str, ...] = ("docx", "docxtpl", "matplotlib")
EXTRA_LINE = (
    "--format docx needs the [docx] extra (docxtpl, python-docx, matplotlib), which is not "
    'installed: pip install "proofpack[docx]" (docs: /docs/run); nothing was written'
)
#: The character style ids docxtpl's RichText names (python-docx's id of each style name).
STYLE_CUSTOMER_INLINE = "PPCustomerTextInline"
STYLE_STATUS = "PPStatus"
FIGURE_WIDTH_MM = 160


class DocxExtraMissing(ProofPackError):
    """``--format docx`` without the ``[docx]`` extra: one typed line, exit 7."""

    exit_code = EXIT_DOCX_EXTRA_MISSING

    def __init__(self) -> None:
        super().__init__(EXTRA_LINE)


def extra_available() -> bool:
    """Whether every module of the extra can be found, without importing any."""
    return all(importlib.util.find_spec(name) is not None for name in EXTRA_MODULES)


def require_extra() -> None:
    if not extra_available():
        raise DocxExtraMissing()


# ------------------------------------------------------------------ the context


def markdown_blocks(source: str) -> list[dict[str, Any]]:
    """The markdown source as the DOCX prints it: ``[{text, mono}]`` - one entry per
    paragraph or heading (``**`` and backticks dropped), a pipe table as one monospace
    entry of its rows joined with line breaks."""
    out: list[dict[str, Any]] = []
    para: list[str] = []
    table: list[str] = []

    def plain(text: str) -> str:
        return re.sub(r"\*\*(.+?)\*\*", r"\1", text).replace("`", "")

    def flush() -> None:
        if para:
            out.append({"text": plain(" ".join(para)), "mono": False})
            para.clear()
        if table:
            out.append({"text": "\n".join(plain(r) for r in table), "mono": True})
            table.clear()

    for line in source.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("|"):
            if para:
                flush()
            table.append(stripped)
            continue
        if table:
            flush()
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush()
            out.append({"text": plain(m.group(2)), "mono": False})
            continue
        para.append(stripped)
    flush()
    return out


def _rich(claim: dict[str, Any], document: dict[str, Any]) -> Any:
    from docxtpl import RichText  # noqa: PLC0415 - the extra

    rt = RichText()
    for part in sentences.claim_parts(claim, document):
        if part.kind == "customer":
            rt.add(part.text, style=STYLE_CUSTOMER_INLINE)
        elif part.kind == "status":
            rt.add(part.text, style=STYLE_STATUS)
        else:
            rt.add(part.text)
    return rt


def _add_rich(document: dict[str, Any], items: list[dict[str, Any]] | None) -> None:
    if not items:
        return
    by_id = {c.get("claim_id"): c for c in document.get("claims") or []}
    for s in items:
        claim = by_id.get(s.get("id"))
        s["rich"] = _rich(claim, document) if claim is not None else s.get("html", "")


def _t7_blocks(ctx: dict[str, Any]) -> None:
    """The conventions file's sections as markdown blocks, beside the HTML keys."""
    text = resource_path("conventions_T7.md").read_text(encoding="utf-8")
    conv = markdown.sections(text)

    def section(prefix: str) -> str:
        for key, body in conv.items():
            if key.startswith(prefix):
                return body
        raise KeyError(f"conventions_T7.md has no section starting {prefix!r}")

    ctx["subgroup_conventions_blocks"] = markdown_blocks(section("Subgroup tables"))
    ctx["calibration_conventions_blocks"] = markdown_blocks(section("Calibration"))
    ctx["coverage_conventions_blocks"] = markdown_blocks(section("Cluster-bootstrap coverage bar"))
    ctx["conventions_intro_blocks"] = markdown_blocks(conv.get("", "").split("\n", 1)[-1])


def docx_context(document: dict[str, Any], template_id: str) -> dict[str, Any]:
    """The HTML context of ``template_id`` with the DOCX's readings of its HTML-only keys
    added (module docstring). No figure image yet: :func:`attach_images` adds those once
    the template is open, because an ``InlineImage`` binds to it."""
    if template_id == "T1":
        from proofpack.render.t1 import t1_context  # noqa: PLC0415 - imports jinja2 lazily

        ctx = t1_context(document)
        for p in ctx["performance"]:
            _add_rich(document, p["sentences"])
        _add_rich(document, ctx["auroc_sentences"])
        _add_rich(document, ctx["calibration"].get("sentences"))
        for s in ctx["subgroups"]:
            _add_rich(document, s["sentences"])
        if ctx["fairness"]:
            _add_rich(document, ctx["fairness"]["sentences"])
        _add_rich(document, ctx["criterion_sentences"])
        return ctx
    if template_id == "T7":
        from proofpack.render.t7 import t7_context  # noqa: PLC0415

        ctx = t7_context(document)
        _t7_blocks(ctx)
        return ctx
    if template_id == "T8":
        return render_html.t8_context(document)
    raise ValueError(f"no DOCX template for {template_id!r}")


def attach_images(tpl: Any, ctx: dict[str, Any], document: dict[str, Any]) -> dict[str, bytes]:
    """T1's figures as ``InlineImage`` objects at ``ctx["figures"][...]["image"]``, drawn
    by :mod:`proofpack.render.figures_png` from the same arrays; returns the PNG bytes by
    figure id (the tests measure them)."""
    from docx.shared import Mm  # noqa: PLC0415 - the extra
    from docxtpl import InlineImage  # noqa: PLC0415

    from proofpack.render import figures_png  # noqa: PLC0415

    refs_by_id = {r["id"]: r for r in ctx.get("guidance_refs") or []}
    figs = figures_png.all_figures(document, refs_by_id)
    specs = ctx["figures"]
    pngs: dict[str, bytes] = {}

    def attach(spec: dict[str, Any] | None, fig: Any) -> None:
        if spec is None or fig is None:
            return
        data = figures_png.png_bytes(fig)
        pngs[spec["id"]] = data
        spec["image"] = InlineImage(tpl, io.BytesIO(data), width=Mm(FIGURE_WIDTH_MM))

    for key in ("f2", "f3", "f4"):
        attach(specs.get(key), figs[key])
    for attribute, spec_list in (specs.get("f5") or {}).items():
        for spec, fig in zip(spec_list, figs["f5"].get(attribute, []), strict=True):
            attach(spec, fig)
    return pngs


# ------------------------------------------------------------------ the render


def _environment() -> Any:
    import jinja2  # noqa: PLC0415

    env = jinja2.Environment(autoescape=True, undefined=jinja2.StrictUndefined)
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


def started_datetime(document: dict[str, Any]) -> _dt.datetime:
    """``manifest.started`` as a naive UTC datetime (the timestamp the container and the
    core properties carry); 1980-01-01 when the manifest has none (the zip epoch)."""
    raw = (document.get("manifest") or {}).get("started")
    if isinstance(raw, str):
        try:
            d = _dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if d.tzinfo is not None:
                d = d.astimezone(_dt.UTC).replace(tzinfo=None)
            return d.replace(microsecond=0)
        except ValueError:
            pass
    return _dt.datetime(1980, 1, 1)


def fixed_zip(data: bytes, stamp: _dt.datetime) -> bytes:
    """``data`` (a zip) rewritten with every entry's mtime set to ``stamp`` and one
    compression setting, entries in their original order."""
    stamp = max(stamp, _dt.datetime(1980, 1, 1))
    date_time = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            zi = zipfile.ZipInfo(info.filename, date_time=date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0
            dst.writestr(zi, src.read(info.filename), compresslevel=6)
    return out.getvalue()


def render_docx_bytes(document: dict[str, Any], template_id: str) -> bytes:
    """The rendered document as bytes (see :func:`render_docx`)."""
    require_extra()
    from docxtpl import DocxTemplate  # noqa: PLC0415 - the extra

    if template_id not in DOCX_FILES:
        raise ValueError(f"no DOCX template for {template_id!r}")
    tpl = DocxTemplate(str(TEMPLATES_DIR / DOCX_FILES[template_id]))
    ctx = docx_context(document, template_id)
    if template_id == "T1":
        attach_images(tpl, ctx, document)
    tpl.render(ctx, jinja_env=_environment(), autoescape=True)
    stamp = started_datetime(document)
    props = tpl.docx.core_properties
    props.author = "ProofPack"
    props.last_modified_by = "ProofPack"
    props.title = str(ctx.get("title") or ctx.get("template_name") or template_id)
    props.created = stamp
    props.modified = stamp
    props.revision = 1
    buf = io.BytesIO()
    tpl.save(buf)
    return fixed_zip(buf.getvalue(), stamp)


def render_docx(document: dict[str, Any], template_id: str, out_path: str | Path) -> Path:
    """Write ``template_id``'s DOCX for ``document`` to ``out_path`` and return it."""
    target = Path(out_path)
    target.write_bytes(render_docx_bytes(document, template_id))
    return target


def write_docx(template_id: str):
    """``--templates`` id -> the writer ``(document, out_dir) -> Path`` for ``run``."""

    def write(document: dict[str, Any], out_dir: str | Path) -> Path:
        return render_docx(document, template_id, Path(out_dir) / DOCX_FILES[template_id])

    return write
