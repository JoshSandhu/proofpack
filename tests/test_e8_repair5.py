"""Repair 5 of build day 8 (23 September 2026): regression tests for lens-5 FA5-B4 at
``375719c`` (C0 controls in ``criteria.yaml`` customer text written raw into ``T8.html``;
DEC-65: refused at declaration with H08 naming the field) and the sentence finding RG-N6
(three repair-4 docstrings). Each test names the literal inputs it feeds and the figures it
asserts; the repair-5 note quotes, per test, the first E line in a worktree at ``2a9a6e2``
with PYTHONPATH forced.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from assembler import assemble
from conftest import make_cohort, make_criteria
from proofpack.errors import EXIT_HALT, EXIT_OK, HaltError
from proofpack.io import declare
from test_run_cli import _own_home, _prepare, _run

pytestmark = pytest.mark.day8

ROOT = Path(__file__).resolve().parents[1]


def _document() -> dict[str, Any]:
    """``make_criteria`` with a fairness block, a reference-standard description and a
    ``udi_di`` string, so each customer text field the lens-5 probe planted is present."""
    crit = make_criteria(
        fairness={
            "criterion_of_interest": "tpr_gap",
            "attribute": "sex",
            "bound": None,
            "author": "A",
            "date": "2026-01-01",
            "justification": "j",
        }
    )
    crit["model"]["udi_di"] = "udi"
    return crit


def _string_paths(value: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in _string_paths(v, (*path, k))]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in _string_paths(v, (*path, i))]
    return [path] if isinstance(value, str) else []


def _planted(crit: dict[str, Any], path: tuple[Any, ...], text: str) -> dict[str, Any]:
    out = copy.deepcopy(crit)
    node = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = text
    return out


def _halt(crit: dict[str, Any]) -> HaltError:
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(crit)
    return ei.value


# ------------------------------------------------ FA5-B4 / DEC-65: the declaration gate

#: The string fields of :func:`_document`, by path; 43 of them (asserted below).
_PATHS = _string_paths(_document())


def test_the_document_has_the_43_string_fields_the_parametrised_test_feeds():
    assert len(_PATHS) == 43
    assert ("model", "name") in _PATHS and ("criteria", 0, "justification") in _PATHS


@pytest.mark.parametrize("path", _PATHS, ids=["/".join(map(str, p)) for p in _PATHS])
def test_u0001_in_each_string_field_of_the_criteria_document_halts(path):
    """U+0001 after the first character of each of the 43 string fields. The repair-5 probe
    at ``2a9a6e2`` found 16 of them in ``run.json`` and 11 in ``T8.html``, exit 0 or 2
    (``model/name`` 4 times on the page). ``clustering/unit`` splits on U+0001 into two
    tokens and halts E01 first (DEC-11; that case passes at ``2a9a6e2``); each of the other
    42 halts H08 naming it."""
    value = _document()
    for key in path:
        value = value[key]
    err = _halt(_planted(_document(), path, value[:1] + "\x01" + value[1:]))
    name = "/".join(str(p) for p in path)
    if name == "clustering/unit":
        assert err.code == "E01", err
        return
    assert err.code == "H08", err
    assert err.detail == {"field": name, "reason": "control_character", "codepoint": "U+0001"}
    assert err.message == f"declaration invalid at {name}: control character U+0001; remove it"


@pytest.mark.parametrize(
    ("path", "text", "codepoint"),
    [
        (("model", "name"), "Tri\x00age \x01\x1b[31m", "U+0000"),  # lens-5 FA5-B4 literal
        (("model", "name"), "Triage\x1b", "U+001B"),
        (("model", "version"), "1.3\x7f", "U+007F"),
        (("model", "name"), "Triage\x85", "U+0085"),  # C1 NEXT LINE
        (("model", "name"), "Triage\x9f", "U+009F"),
        (("model", "name"), "Tri\tage", "U+0009"),  # tab: single-line field
        (("model", "name"), "Tri\nage", "U+000A"),  # line feed: single-line field
        (("criteria", 0, "author"), "Test\nAuthor", "U+000A"),
        (("operating_points", 0, "id"), "op\x001", "U+0000"),
        (("prevalence", 0, "label"), "intended\tuse", "U+0009"),
        (("criteria", 0, "justification"), "line one\r\nline two", "U+000D"),
        (("criteria", 0, "justification"), "a\x00b", "U+0000"),
        (("reference_standard", "description"), "rs\x0b", "U+000B"),
        (("operating_points", 0, "source"), "SAP\x0c", "U+000C"),
    ],
)
def test_named_control_characters_halt_h08_with_their_code_point(path, text, codepoint):
    """C0 (U+0000, U+000B, U+000C, U+000D, U+001B), DEL (U+007F) and C1 (U+0085, U+009F),
    and tab and line feed in fields outside ``justification`` / ``description`` / ``source``.
    At ``2a9a6e2`` 13 of the 14 documents passed ``validate_dict``; the operating-point id
    ``op``, NUL, ``1`` halted H09 there (the criterion names ``op1``)."""
    err = _halt(_planted(_document(), path, text))
    name = "/".join(str(p) for p in path)
    assert (err.code, err.detail) == (
        "H08",
        {"field": name, "reason": "control_character", "codepoint": codepoint},
    )
    assert "\x00" not in err.message and "\x1b" not in err.message and text not in err.message


def test_tab_and_line_feed_are_accepted_in_the_three_free_text_fields():
    """DEC-65's recorded choice, from D1 section 6's list of free-text declaration fields
    (``justification``, ``description``, ``source``): tab and line feed pass there. U+00A0
    and U+202E in the model name pass too (U+202E is escaped at render:
    ``test_render_t8.py::
    test_html_injection_in_a_justification_and_a_level_label_is_escaped``). A guard: it
    passes at ``2a9a6e2``."""
    crit = _document()
    crit["criteria"][0]["justification"] = "line one\n\tline two\n"
    crit["fairness"]["justification"] = "a\tb"
    crit["reference_standard"]["description"] = "first\nsecond"
    crit["operating_points"][0]["source"] = "SAP v2.1\t\u00a74.3"
    crit["prevalence"][0]["source"] = "registry\n2025"
    crit["model"]["name"] = "Tri\u00a0age \u202e"
    declare.validate_dict(crit)


def test_a_control_character_in_a_key_halts_h08_naming_the_parent():
    """A key ``x\\x01`` inside ``model``: H08 ``model (key)``. At ``2a9a6e2`` this document
    passed ``validate_dict``."""
    crit = _document()
    crit["model"]["x\x01"] = "y"
    err = _halt(crit)
    assert (err.code, err.detail) == (
        "H08",
        {"field": "model (key)", "reason": "control_character", "codepoint": "U+0001"},
    )


def test_version_author_and_justification_halt_through_the_assembler():
    """Lens 5's ``att/nul.py`` route: NUL in the version, the author and the justification
    reached ``render_t8``'s bytes (4, 1 and 1) at ``375719c``. The assembler reads the
    document through ``validate_dict``, so each now halts H08 naming the field."""
    for path in (("model", "version"), ("criteria", 0, "author"), ("criteria", 0, "justification")):
        with pytest.raises(HaltError) as ei:
            assemble(make_cohort(n=150), _planted(_document(), path, "n\x00ul"))
        assert ei.value.code == "H08"
        assert ei.value.detail["field"] == "/".join(map(str, path))


def test_the_cli_run_with_nul_soh_esc_in_the_model_name_exits_3_and_writes_nothing(
    tmp_path, monkeypatch, capsys
):
    """Lens-5 FA5-B4 through the CLI: ``name: "Tri\\0age \\x01\\x1b[31m"`` as YAML escapes, a
    licence installed, ``--offline``. At ``375719c`` this was exit 0 and ``T8.html`` held 4
    NUL, 4 SOH and 4 ESC bytes. Now: exit 3, no ``--out`` directory, and the printed halt
    names ``model/name`` and ``U+0000`` and holds none of the three bytes."""
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=make_cohort(n=200))
    text = yml.read_text(encoding="utf-8")
    text = text.replace("name: synthetic-classifier", 'name: "Tri\\0age \\x01\\x1b[31m"')
    assert 'name: "Tri\\0age' in text
    yml.write_text(text, encoding="utf-8")
    assert yaml.safe_load(text)["model"]["name"] == "Tri\x00age \x01\x1b[31m"
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out, "--offline")
    printed = capsys.readouterr()
    both = printed.out + printed.err
    assert rc == EXIT_HALT, both
    assert not out.exists()
    assert "H08" in both and "model/name" in both and "U+0000" in both
    assert not any(ch in both for ch in ("\x00", "\x01", "\x1b"))


def _set_role(m: dict[str, Any], original: str, role: str) -> None:
    for entry in m["roles"]:
        if entry["original"] == original:
            entry["role"] = role
            entry["confirmed"] = True


def test_a_control_character_in_mapping_text_halts_h08(tmp_path, monkeypatch, capsys):
    """DEC-65 names the mapping too. ``mapping.json`` text a person can write: a role's
    ``notes`` entry ``n\\x01``, ``timestamp`` ``t\\x1b``, and the role ``attr_colour\\n``
    on a ``colour`` column (red / blue). At ``2a9a6e2`` the repair-5 probe measured the
    first two at exit 0 with 0 control bytes in any output file, and the third at exit 3,
    ``HALT H07: mapping.json maps a column to attr_colour`` followed by the line feed. Now
    each run exits 3 with no ``--out`` directory and H08 naming the field."""
    _own_home(tmp_path, monkeypatch)
    cols = make_cohort(n=200)
    cols["colour"] = [("red", "blue")[i % 2] for i in range(200)]
    for tag, edit, field in (
        ("notes", lambda m: m["roles"][0]["notes"].append("n\x01"), "roles/0/notes/0"),
        ("timestamp", lambda m: m.update(timestamp="t\x1b"), "timestamp"),
        ("role", lambda m: _set_role(m, "colour", "attr_colour\n"), "roles/"),
    ):
        d = tmp_path / tag
        d.mkdir()
        csv_path, yml = _prepare(d, cols=cols)
        mp = csv_path.with_name(csv_path.name + ".mapping.json")
        m = json.loads(mp.read_text(encoding="utf-8"))
        edit(m)
        mp.write_text(json.dumps(m), encoding="utf-8")
        out = d / "pack"
        rc = _run(csv_path, yml, out, "--offline")
        printed = capsys.readouterr()
        both = printed.out + printed.err
        assert rc == EXIT_HALT, (tag, both)
        assert not out.exists()
        assert "H08" in both and f"mapping.json invalid at {field}" in both, (tag, both)
        if tag == "role":
            assert "/role: control character U+000A" in both, both


def test_the_unplanted_document_still_runs_through_the_cli(tmp_path, monkeypatch, capsys):
    """Guard (passes at ``2a9a6e2`` too): the same CSV and ``criteria.yaml`` without a
    planted character run with exit 0 and write ``T8.html``."""
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=make_cohort(n=200))
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out, "--offline")
    assert rc == EXIT_OK, capsys.readouterr()
    assert (out / "T8.html").exists()


# ------------------------------------------------ RG-N6: three repair-4 docstrings


@pytest.mark.parametrize(
    "name",
    [
        "test_each_hand_mapped_letter_has_a_literal_the_tr39_readings_do_not_reject",
        "test_prose_the_new_readings_leave_accepted",
        "test_calib_na_is_claimed_and_accepted_only_on_score_not_probability",
    ],
)
def test_the_three_repair4_guards_say_they_pass_at_23f3d9f(name):
    """Lens-5 RG-N6: these pass (the calibration test: its ``score_not_probability`` case)
    at ``23f3d9f``, and at ``2a9a6e2`` their docstrings did not say so."""
    import test_e8_repair4

    doc = " ".join(getattr(test_e8_repair4, name).__doc__.split())
    assert "passes at ``23f3d9f``" in doc, doc


# ------------------------------------------------ DEC-12(ii): the sweep lists the new mutants


def test_the_sweep_lists_the_repair5_mutants():
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mutation_sweep.py"), "--list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    day8 = {ln.split()[0] for ln in proc.stdout.splitlines() if " day8 " in ln}
    assert {
        "declare_dec65_check_not_called",
        "declare_dec65_multiline_everywhere",
        "declare_dec65_multiline_nowhere",
        "declare_dec65_c1_and_del_dropped",
        "declare_dec65_keys_unchecked",
        "mapping_dec65_check_not_called",
        "mapping_dec65_role_not_read",
    } <= day8
