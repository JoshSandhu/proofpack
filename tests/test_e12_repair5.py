"""E12 repair 5 (orchestrator, Monday 5 October 2026): the four blockers of the lens-5
fresh-attack note (``handoffs/2026-10-05_E_e12_lens5_fresh-attack.md``).

* FA-B1: mutant K11 (``f13_recorded_outcome`` looping over ``F13_NAMES[:-1]``) survived the
  suite. ``test_fa_b1_each_f13_name_is_checked`` perturbs and deletes each of the 16 names in
  turn; under K11 the last name's cases read ``suite_only``.
* FA-B2: mutant G11 (the upload guard's label appending ``p.stem``) printed most of a vectors
  row and survived. ``test_fa_b2_no_eight_character_run_of_a_vectors_row_reaches_the_output``
  looks for every eight-character run of every data row in the guard's output, not only
  whole rows.
* FA-B3, FA-B4: two false sentences, now rewritten; the two ``test_fa_b3``/``test_fa_b4``
  tests read the new wording.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import test_day12_r_captures as d12
import test_e12_repair4 as r4
from proofpack import fixtures as fx

pytestmark = pytest.mark.day12

REPO = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("how", ["engine +2e-6", "name deleted"])
@pytest.mark.parametrize("name", fx.F13_NAMES)
def test_fa_b1_each_f13_name_is_checked(tmp_path, monkeypatch, name, how):
    """The synthetic capture's ``f13_engine_comparison.json`` with one name's ``engine``
    value moved by +2e-6 (outside the 1e-6 tolerance), or that name's record deleted, read
    with ``vectors=None``: row F13 is ``not_matched``. The unedited record reads
    ``suite_only`` (the control)."""
    cap = r4._capture(tmp_path)
    monkeypatch.setattr(fx, "git_sha", lambda: (d12.SYNTHETIC_ENGINE_SHA, "test"))
    row, _ = r4._row_and_exit(fx.load_r_captures(cap, vectors=None))
    assert row["status"] == "suite_only", row["reason"]
    path = cap / "f13_engine_comparison.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if how == "name deleted":
        del doc["values"][name]
    else:
        doc["values"][name]["engine"] += 2e-6
    path.write_text(json.dumps(doc), encoding="utf-8")
    row, _ = r4._row_and_exit(fx.load_r_captures(cap, vectors=None))
    assert row["status"] == "not_matched", (name, how, row["reason"])


@pytest.mark.parametrize("plant", r4.GUARD_NAME_PLANTS)
def test_fa_b2_no_eight_character_run_of_a_vectors_row_reaches_the_output(tmp_path, plant):
    """The repair-4 plants (an entry named with the synthetic vectors' fifth data line), run
    through the guard: no run of eight consecutive characters of any of the 80 data rows
    appears in its stdout or stderr. Under G11 the output held ``5,Good,0,0.13,6`` (the
    planted name's stem), which the repair-4 whole-line test did not see."""
    cap = r4._capture(tmp_path)
    up = tmp_path / "upload"
    up.mkdir()
    for name in d12.DEC77_UPLOADED:
        (up / name).write_bytes((cap / name).read_bytes())
    lines = r4._vector_lines(cap)
    rows = lines[1:]
    assert len(rows) == 80
    line = lines[5]
    if plant == r4.GUARD_NAME_PLANTS[0]:
        (up / line).write_bytes(b"")
    elif plant == r4.GUARD_NAME_PLANTS[1]:
        (up / line).mkdir()
        (up / line / "a.json").write_bytes(b"{}")
    else:
        (up / "sub").mkdir()
        (up / "sub" / line).write_bytes(b"")
    proc = r4._guard(up, cap / "asah_vectors.csv", tmp_path)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1, out
    runs = {row[i : i + 8] for row in rows for i in range(len(row) - 7)}
    assert sorted(r for r in runs if r in out) == []


def test_fa_b3_the_guard_docstring_names_the_directory_argument():
    text = (REPO / "scripts" / "r_upload_guard.py").read_text(encoding="utf-8")
    assert "the directory argument it was given" in " ".join(text.split())


def test_fa_b4_capture_r_header_says_written_to_stop_not_stops():
    head = "\n".join(
        (REPO / "fixtures" / "r" / "capture.R").read_text(encoding="utf-8").splitlines()[:16]
    )
    flat = " ".join(head.replace("#", " ").split())
    assert "The script stops unless" not in flat
    assert "The script is written to stop when" in flat
    assert "not run here: no R" in flat
