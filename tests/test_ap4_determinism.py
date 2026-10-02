"""A-P4 item 8 (build day 10, lane A): DETERMINISM of the ``.docx`` container (D4 section 9;
D5 section 3.5 "byte-identity of the .docx container additionally needs the zip entry
mtimes fixed").

``render/docx.py`` rewrites docxtpl's zip with every entry's mtime set to the manifest's
``started`` (the zip format's two-second resolution) and ``docProps/core.xml``'s created and
modified set to the same instant, the author fixed. Measured here, on this machine: two
renders of one document are byte-identical for T1, T7 and T8; every entry's mtime equals
``started``; a different ``started`` changes the bytes (so the stamp is the manifest's,
not a constant); a manifest without ``started`` stamps the zip epoch; the embedded PNGs are
identical part for part. Byte identity across platforms is not claimed (matplotlib's
raster depends on the FreeType and font versions it finds) - text identity is what the
round-trip tests claim on every platform.
"""

from __future__ import annotations

import copy
import datetime as dt
import io
import re
import zipfile

import pytest

from ap4_docx import needs_extra, paragraph_texts, part, synthetic_document
from proofpack.render import docx as render_docx

pytestmark = [pytest.mark.day10, pytest.mark.ap4, needs_extra]

IDS = ("T1", "T7", "T8")


@pytest.fixture(scope="module")
def document():
    return synthetic_document(watermark="TRIAL")


def _mtimes(data: bytes) -> set[tuple[int, ...]]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {zi.date_time for zi in z.infolist()}


@pytest.mark.parametrize("template_id", IDS)
def test_two_renders_of_one_document_are_byte_identical(document, template_id):
    a = render_docx.render_docx_bytes(document, template_id)
    b = render_docx.render_docx_bytes(document, template_id)
    assert a == b and len(a) > 10_000
    with zipfile.ZipFile(io.BytesIO(a)) as za, zipfile.ZipFile(io.BytesIO(b)) as zb:
        for name in za.namelist():
            assert za.read(name) == zb.read(name), name
        media = [n for n in za.namelist() if n.startswith("word/media/")]
        assert len(media) == {"T1": 11, "T7": 0, "T8": 0}[template_id]


@pytest.mark.parametrize("template_id", IDS)
def test_every_entry_mtime_and_the_core_properties_are_the_manifests_started(document, template_id):
    data = render_docx.render_docx_bytes(document, template_id)
    started = document["manifest"]["started"]
    stamp = render_docx.started_datetime(document)
    assert stamp == dt.datetime.fromisoformat(started.replace("Z", "+00:00")).replace(tzinfo=None)
    assert _mtimes(data) == {
        (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)
    }
    core = part(data, "docProps/core.xml")
    iso = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert re.search(r"<dcterms:created[^>]*>" + re.escape(iso) + "<", core)
    assert re.search(r"<dcterms:modified[^>]*>" + re.escape(iso) + "<", core)
    assert "<dc:creator>ProofPack</dc:creator>" in core
    assert "<cp:lastModifiedBy>ProofPack</cp:lastModifiedBy>" in core
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert all(zi.compress_type == zipfile.ZIP_DEFLATED for zi in z.infolist())
        assert len({zi.external_attr for zi in z.infolist()}) == 1  # zipfile's one default


def test_a_different_started_changes_the_bytes_and_a_missing_one_stamps_the_zip_epoch(document):
    doc = copy.deepcopy(document)
    doc["manifest"]["started"] = "2026-10-15T09:30:00Z"
    a = render_docx.render_docx_bytes(document, "T8")
    b = render_docx.render_docx_bytes(doc, "T8")
    assert a != b
    assert _mtimes(b) == {(2026, 10, 15, 9, 30, 0)}
    # the text differs where started is printed (T8's manifest table) and nowhere else
    ta, tb = paragraph_texts(a), paragraph_texts(b)
    assert ta != tb
    assert [t.replace("2026-09-18T00:00:00Z", "X") for t in ta] == [
        t.replace("2026-10-15T09:30:00Z", "X") for t in tb
    ]
    without = copy.deepcopy(document)
    del without["manifest"]["started"]
    assert render_docx.started_datetime(without) == dt.datetime(1980, 1, 1)
    assert render_docx.started_datetime({"manifest": {"started": "not a date"}}) == dt.datetime(
        1980, 1, 1
    )
    assert render_docx.started_datetime({"manifest": {"started": "2026-09-18T00:00:00.789Z"}}) == (
        dt.datetime(2026, 9, 18, 0, 0, 0)
    )


def test_fixed_zip_keeps_entry_order_and_content():
    src = io.BytesIO()
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("b.txt", b"b")
        z.writestr("a.txt", b"a")
    fixed = render_docx.fixed_zip(src.getvalue(), dt.datetime(2026, 1, 2, 3, 4, 5))
    with zipfile.ZipFile(io.BytesIO(fixed)) as z:
        assert z.namelist() == ["b.txt", "a.txt"]
        assert z.read("a.txt") == b"a" and z.read("b.txt") == b"b"
        assert {zi.date_time for zi in z.infolist()} == {(2026, 1, 2, 3, 4, 4)}  # 2 s resolution
    twice = render_docx.fixed_zip(fixed, dt.datetime(2026, 1, 2, 3, 4, 5))
    assert twice == fixed
