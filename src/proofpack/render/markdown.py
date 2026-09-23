"""The small Markdown subset ``design/conventions_T7.md`` is written in, as HTML (E9).

T7 inserts the conventions file's paragraphs verbatim (the file's own first line says
so). No Markdown package is a dependency: the file uses headings (``#``), paragraphs,
pipe tables, ``**bold**`` and ``code`` spans only, and this module renders exactly that
and nothing else. Every character of the source is HTML-escaped before the two inline
rules apply, so the output can carry no element the source did not name. Headings are
shifted to sit under the T7 section that prints them (``##`` becomes ``<h3>``).
"""

from __future__ import annotations

import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    out = html.escape(text, quote=True)
    out = _CODE.sub(r"<code>\1</code>", out)
    return _BOLD.sub(r"<strong>\1</strong>", out)


def _table(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    body = [r for r in cells if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    if not body:
        return ""
    head, rest = body[0], body[1:]
    out = ['<div class="table-wrap"><table class="conventions-table">', "<thead><tr>"]
    out += [f'<th scope="col">{_inline(c)}</th>' for c in head]
    out.append("</tr></thead><tbody>")
    for r in rest:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def to_html(source: str, *, shift: int = 1) -> str:
    """Render ``source``; a heading of level ``n`` becomes ``<h{n + shift}>`` (at most h6)."""
    blocks: list[str] = []
    para: list[str] = []
    table: list[str] = []

    def flush() -> None:
        if para:
            blocks.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()
        if table:
            blocks.append(_table(table))
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
            level = min(6, len(m.group(1)) + shift)
            blocks.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            continue
        para.append(stripped)
    flush()
    return "\n".join(blocks)


def sections(source: str) -> dict[str, str]:
    """The file split at its ``##`` headings: ``{heading text: body markdown}``; the text
    before the first ``##`` is under the key ``""``."""
    out: dict[str, str] = {}
    key = ""
    buf: list[str] = []
    for line in source.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^##\s+(.*)$", line)
        if m and not line.startswith("###"):
            out[key] = "\n".join(buf).strip("\n")
            key, buf = m.group(1).strip(), []
            continue
        buf.append(line)
    out[key] = "\n".join(buf).strip("\n")
    return out
