"""Repair 6 of build day 8 (23 September 2026): regression tests for lens round 6 at
``ea2f743`` - fresh-attack B1 (C0/C1 characters in table cells written raw into
``T8.html``; DEC-66: refused at ingest with a typed halt naming the column), regression B1
(a self-referential YAML alias in ``criteria.yaml`` ended exit 5 ``RecursionError`` in the
DEC-65 walk) with fresh-attack N4's alias chain, the sentence findings RG-N1 / FA-N2 in
``io/declare.py``, and RG-N3 (``design/tokens.json``; DEC-67). Each test names the
literal inputs it feeds and the figures it asserts; the repair-6 note quotes, per test,
the first E line in a worktree at ``941f8a7`` with PYTHONPATH forced.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import yaml

from conftest import make_cohort, make_criteria, write_yaml
from proofpack.errors import EXIT_HALT, HaltError
from proofpack.io import declare, schema
from test_run_cli import _own_home, _prepare, _run

pytestmark = pytest.mark.day8

ROOT = Path(__file__).resolve().parents[1]
#: The bytes lens 6 counted in ``T8.html``: C0 less tab, LF and CR, DEL, and C1 as UTF-8.
RAW_CONTROL = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]|\xc2[\x80-\x9f]")


# ------------------------------------------------ RG-B1: a self-referential alias


def _criteria_yaml(tmp_path: Path, prefix: str = "", edit=None) -> Path:
    """``make_criteria()`` written as YAML, then ``edit`` applied to the text and
    ``prefix`` put before line 1."""
    path = write_yaml(tmp_path / "criteria.yaml", make_criteria())
    text = path.read_text(encoding="utf-8")
    if edit is not None:
        text = edit(text)
    path.write_text(prefix + text, encoding="utf-8")
    return path


def _under_model(text: str) -> str:
    assert "\nmodel:\n" in text
    return text.replace("\nmodel:\n", "\nmodel:\n  extra: &a [*a]\n", 1)


def _in_criteria_0(text: str) -> str:
    assert "\ncriteria:\n- " in text
    return text.replace("\ncriteria:\n- ", "\ncriteria:\n- extra: &a [*a]\n  ", 1)


@pytest.mark.parametrize(
    ("where", "prefix", "edit", "field"),
    [
        ("root", "zz_extra: &a [*a]\n", None, "zz_extra/0"),
        ("model", "", _under_model, "model/extra/0"),
        ("criteria_0", "", _in_criteria_0, "criteria/0/extra/0"),
    ],
    ids=["root", "model", "criteria_0"],
)
def test_a_self_referential_alias_halts_h08_naming_the_path(tmp_path, where, prefix, edit, field):
    """Lens-6 RG-B1's three positions. At ``ea2f743`` each was ``RecursionError`` inside
    ``control_character_at`` (exit 5 through the CLI); at ``2a9a6e2`` the root one was
    ``H08 ... <root>: additionalProperties`` and the other two exit 5 ``ValueError:
    Circular reference detected``."""
    path = _criteria_yaml(tmp_path, prefix, edit)
    with pytest.raises(HaltError) as ei:
        declare.load(path)
    err = ei.value
    assert (err.code, err.detail) == ("H08", {"field": field, "reason": "self_reference"})
    assert err.message == (
        f"declaration invalid at {field}: the value contains itself (a YAML alias inside its "
        "own anchor); remove the alias"
    )


@pytest.mark.parametrize("nul_name", [False, True], ids=["plain", "nul_name"])
def test_the_cli_run_with_a_root_self_referential_alias_exits_3_and_writes_nothing(
    tmp_path, monkeypatch, capsys, nul_name
):
    """Lens-6 RG-B1's repro through ``proofpack run``, a licence installed, ``--offline``:
    ``zz_extra: &a [*a]`` as line 1, alone and with ``name: "Tri\\0age"``. At ``ea2f743``:
    exit 5 ``internal error: RecursionError`` in both. Now: exit 3, the H08 above, no
    ``--out`` directory, no ``Traceback``."""
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=make_cohort(n=200))
    text = yml.read_text(encoding="utf-8")
    if nul_name:
        assert "name: synthetic-classifier" in text
        text = text.replace("name: synthetic-classifier", 'name: "Tri\\0age"')
    yml.write_text("zz_extra: &a [*a]\n" + text, encoding="utf-8")
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out, "--offline")
    printed = capsys.readouterr()
    both = printed.out + printed.err
    assert rc == EXIT_HALT, both
    assert not out.exists()
    assert "HALT H08: declaration invalid at zz_extra/0: the value contains itself" in both
    assert "Traceback" not in both and "RecursionError" not in both


def _alias_chain(levels: int) -> Any:
    lines = ["l0: &l0 [x, x]"] + [f"l{i}: &l{i} [*l{i - 1}, *l{i - 1}]" for i in range(1, levels)]
    return yaml.safe_load("\n".join(lines))[f"l{levels - 1}"]


def test_an_alias_chain_24_deep_is_walked_in_under_two_seconds():
    """Lens-6 FA-N4: ``l0: &l0 [x, x]`` then ``lK: &lK [*lK-1, *lK-1]``, 24 levels (2**24 =
    16,777,216 leaves once expanded, 24 list objects), as ``model.extra``. At ``ea2f743`` a
    chain 20 deep took 0.51 s in ``validate_dict`` (the lens's ``p9_laughs.py``); the walk
    entered every leaf. Now each list object is entered once: ``validate_dict`` accepts the
    document in under 2 s. With ``"\\x01"`` in place of the innermost ``x`` it halts H08
    naming the first path to it, ``model/extra`` then 23 ``0`` steps then ``1``."""
    crit = make_criteria()
    crit["model"]["extra"] = _alias_chain(24)
    t0 = time.perf_counter()
    declare.validate_dict(crit)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, elapsed

    lines = ['l0: &l0 [x, "\\x01"]'] + [f"l{i}: &l{i} [*l{i - 1}, *l{i - 1}]" for i in range(1, 24)]
    crit = make_criteria()
    crit["model"]["extra"] = yaml.safe_load("\n".join(lines))["l23"]
    t0 = time.perf_counter()
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(crit)
    assert time.perf_counter() - t0 < 2.0
    assert ei.value.detail["field"] == "model/extra/" + "0/" * 23 + "1"


def test_a_list_nested_5000_deep_is_walked_without_recursion():
    """A list 5,000 levels deep built in Python (lens 6 fed YAML lists 100 and 300 deep
    through the CLI: exit 3 at both commits). At ``ea2f743`` ``control_character_at``
    raised ``RecursionError`` on it. Now both walks return: ``None`` from each, and the
    path of a U+0001 placed at the bottom is 5,000 ``0`` steps."""
    deep: Any = ["ok"]
    for _ in range(4999):
        deep = [deep]
    assert declare.control_character_at(deep) is None
    assert declare.self_reference_at(deep) is None
    bottom = deep
    for _ in range(4999):
        bottom = bottom[0]
    bottom[0] = "a\x01"
    found = declare.control_character_at(deep)
    assert found == ("/".join(["0"] * 5000), "U+0001")


def test_a_shared_but_not_self_referential_alias_is_accepted():
    """One list object ``["x", "y"]`` held under two keys of ``model`` (``extra_a``,
    ``extra_b``) - what ``extra_a: &s [x, y]`` and ``extra_b: *s`` load as - gives ``None``
    from ``self_reference_at`` and passes ``validate_dict``. At ``941f8a7`` this fails only
    because ``self_reference_at`` did not exist (``AttributeError``)."""
    crit = make_criteria()
    shared = ["x", "y"]
    crit["model"]["extra_a"] = shared
    crit["model"]["extra_b"] = shared
    assert declare.self_reference_at(crit) is None
    declare.validate_dict(crit)


# ------------------------------------------------ RG-N1 / FA-N2: the declare.py sentences


def test_a_missing_block_halts_before_the_control_character_walk():
    """Guard (the order ``_check_control_characters``'s docstring now states; passes at
    ``941f8a7`` too): ``Tri\\x00age`` as the model name with the ``prevalence`` block
    removed halts ``mandatory declaration block(s) missing: prevalence``, which names no
    field (lens-6 RG-N1's first counter-example)."""
    crit = make_criteria()
    crit["model"]["name"] = "Tri\x00age"
    del crit["prevalence"]
    with pytest.raises(HaltError) as ei:
        declare.validate_dict(crit)
    assert (ei.value.code, ei.value.message) == (
        "H08",
        "mandatory declaration block(s) missing: prevalence",
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "and so is a string\nholding a control character",
        "key or value, are H08 naming the field",
        "``None`` if none does",
    ],
)
def test_the_three_declare_sentences_lens_6_measured_false_are_gone(sentence):
    """Lens-6 RG-N1 / FA-N2: the module docstring ("... and so is a string holding a
    control character"; justification ``"a\\tb"`` is accepted and ``clustering.unit``
    ``"pat\\x00ient"`` halts E01), the ``MULTILINE_FIELDS`` comment ("... key or value, are
    H08 naming the field") and the ``control_character_at`` docstring ("``None`` if none
    does"; it raised ``RecursionError`` on a self-referential document). Each was in
    ``io/declare.py`` at ``ea2f743``."""
    text = (ROOT / "src" / "proofpack" / "io" / "declare.py").read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")
    flat = " ".join(text.replace("#:", " ").split())
    assert " ".join(sentence.split()) not in flat


# ------------------------------------------------ FA-B1 / DEC-66: control characters in table cells


def _race_run(tmp_path: Path, monkeypatch, capsys, cols: dict, attribute: str, criterion: bool):
    crit = make_criteria(
        fairness={
            "criterion_of_interest": "tpr_gap",
            "attribute": attribute,
            "bound": 0.2,
            "statistic": "point_estimate",
            "comparator": "<=",
            "author": "A",
            "date": "2026-01-01",
            "justification": "j",
        }
    )
    if attribute not in {s["attribute"] for s in crit["subgroups"]}:
        crit["subgroups"].append(
            {
                "attribute": attribute,
                "prespecified": True,
                "source": "t",
                "reference_level": "largest",
            }
        )
    if criterion:
        crit["criteria"].append(
            {
                "id": "Cstar",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": {"attribute": attribute, "level": "*"},
                "statistic": "point_estimate",
                "comparator": ">=",
                "value": 0.5,
                "author": "A",
                "date": "2026-01-01",
                "justification": "j",
            }
        )
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=cols, crit=crit)
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out, "--offline")
    printed = capsys.readouterr()
    return rc, printed.out + printed.err, out


@pytest.mark.parametrize(
    "criterion", [False, True], ids=["fairness_row", "fairness_and_level_star"]
)
def test_the_cli_run_with_soh_and_esc_in_race_levels_exits_3_naming_the_column(
    tmp_path, monkeypatch, capsys, criterion
):
    """Lens-6 FA-B1's repro: ``make_cohort(n=400)`` plus ``race`` alternating ``re\\x01d`` /
    ``bl\\x1bue``, a ``tpr_gap`` fairness block on ``race`` with bound 0.2, and (second id)
    a ``level: "*"`` sensitivity criterion on ``race``; a licence, ``--offline``. At
    ``ea2f743``: exit 0 and ``T8.html`` held ``race = re\\x01d`` raw (byte 25,164 in the
    lens's run). Now: exit 3, ``HALT S02: column role 'race' holds a control character
    (U+0001) in 400 row(s)``, no ``--out`` directory, and none of the two bytes printed."""
    cols = make_cohort(n=400)
    cols["race"] = [("re\x01d", "bl\x1bue")[i % 2] for i in range(400)]
    rc, both, out = _race_run(tmp_path, monkeypatch, capsys, cols, "race", criterion)
    assert rc == EXIT_HALT, both
    assert not out.exists()
    assert (
        "HALT S02: column role 'race' holds a control character (U+0001) in 400 row(s); "
        "remove it from the table"
    ) in both
    assert "\x01" not in both and "\x1b" not in both


@pytest.mark.parametrize(
    ("column", "levels", "codepoint", "count"),
    [
        ("site", {"S1": "S\x001", "S2": "S\x1b2", "S3": "S3"}, "U+0000", None),
        ("device", ("dev\x00A", "devB"), "U+0000", 200),
        ("attr_colour", ("re\x85d", "bl\x9fue"), "U+0085", 400),
        ("race", ("re\x00d", "blue"), "U+0000", 200),
    ],
    ids=["site_nul_esc", "device_nul", "attr_colour_c1", "race_nul"],
)
def test_the_lens_6_level_star_inputs_exit_3_naming_the_column(
    tmp_path, monkeypatch, capsys, column, levels, codepoint, count
):
    """Lens-6 FA-B1's other rows (``att/p2_star.py``, ``att/p7_site.py``), each with a
    ``level: "*"`` criterion on the column and the fairness block on it: ``site`` cells
    ``S\\x001`` / ``S\\x1b2`` / ``S3``, ``device`` ``dev\\x00A`` / ``devB``, ``attr_colour``
    ``re\\x85d`` / ``bl\\x9fue`` (C1), ``race`` ``re\\x00d`` / ``blue``. At ``ea2f743`` each
    was exit 0 with the level raw in ``T8.html``. Now each is exit 3, S02 naming the
    column and the first code point, and no ``--out`` directory."""
    cols = make_cohort(n=400)
    if isinstance(levels, dict):
        cols[column] = [levels[v] for v in cols[column]]
        count = sum(1 for v in cols[column] if v != "S3")
        first = next(v for v in cols[column] if v != "S3")
        codepoint = f"U+{ord(first[1]):04X}"
    else:
        cols[column] = [levels[i % 2] for i in range(400)]
    rc, both, out = _race_run(tmp_path, monkeypatch, capsys, cols, column, True)
    assert rc == EXIT_HALT, both
    assert not out.exists()
    assert (
        f"HALT S02: column role '{column}' holds a control character ({codepoint}) in "
        f"{count} row(s)"
    ) in both
    assert not RAW_CONTROL.search(both.encode("utf-8"))


def _cells(**planted: str) -> dict[str, list]:
    """A 40-row table in canonical names with every column ``validate`` reads a cell from,
    one cell (row 7) replaced per keyword."""
    n = 40
    cols: dict[str, list] = {
        "row_id": [f"r{i}" for i in range(n)],
        "case_id": [f"c{i}" for i in range(n)],
        "y_true": [str(i % 2) for i in range(n)],
        "score": [f"0.{i % 9 + 1}" for i in range(n)],
        "y_pred": [str(i % 2) for i in range(n)],
        "indeterminate": ["0"] * n,
        "age": [str(30 + i) for i in range(n)],
        "age_band": ["18-64"] * n,
        "sex": [("F", "M")[i % 2] for i in range(n)],
        "race": ["a"] * n,
        "ethnicity": ["b"] * n,
        "site": ["S1"] * n,
        "device": ["d"] * n,
        "protocol": ["p"] * n,
        "severity": ["s"] * n,
        "period": ["2024-Q1"] * n,
        "model_version": ["1.3"] * n,
        "dataset": ["test"] * n,
        "attr_colour": ["red"] * n,
        "rater_1": ["x"] * n,
        "notes": ["free text"] * n,
    }
    for name, value in planted.items():
        cols[name][7] = value
    return cols


#: Each column :func:`_cells` holds that ``validate`` reads, with a cell holding one
#: character from each end of the three ranges; ``rater_1`` and ``notes`` are not read.
_PLANTS = [
    ("row_id", "r\x007", "U+0000"),
    ("case_id", "c\x1f7", "U+001F"),
    ("y_true", "1\x01", "U+0001"),
    ("score", "0.\x015", "U+0001"),
    ("y_pred", "1\x7f", "U+007F"),
    ("indeterminate", "0\x1b", "U+001B"),
    ("age", "3\x087", "U+0008"),
    ("age_band", "18\x0b64", "U+000B"),
    ("sex", "F\x0cM", "U+000C"),
    ("race", "a\x0db", "U+000D"),
    ("ethnicity", "b\tc", "U+0009"),
    ("site", "S\n1", "U+000A"),
    ("device", "d\x80", "U+0080"),
    ("protocol", "p\x85q", "U+0085"),
    ("severity", "s\x9f", "U+009F"),
    ("period", "2024-Q1\x1b[31m", "U+001B"),
    ("model_version", "1.\x003", "U+0000"),
    ("dataset", "te\x01st", "U+0001"),
    ("attr_colour", "re\x01d", "U+0001"),
]


def test_the_plants_cover_every_column_validate_reads_from_the_table():
    raw = schema.table_from_columns(_cells())
    assert schema.columns_read_by_validate(raw) == [c for c, _t, _p in _PLANTS]


@pytest.mark.parametrize(("column", "text", "codepoint"), _PLANTS, ids=[p[0] for p in _PLANTS])
def test_a_control_character_in_a_cell_of_each_read_column_halts_s02(column, text, codepoint):
    """One cell (row 7 of 40) per column, the character inside the cell. At ``941f8a7``
    ``score``, ``indeterminate``, ``age`` and ``dataset`` halted S02 with their type
    message (no ``reason``) and the other 15 passed ``validate``. Now each is S02 with
    ``{"role", "reason": "control_character", "codepoint", "count": 1}``."""
    raw = schema.table_from_columns(_cells(**{column: text}))
    with pytest.raises(HaltError) as ei:
        schema.validate(raw)
    err = ei.value
    assert (err.code, err.detail) == (
        "S02",
        {"role": column, "reason": "control_character", "codepoint": codepoint, "count": 1},
    )
    assert err.message == (
        f"column role {column!r} holds a control character ({codepoint}) in 1 row(s); "
        "remove it from the table"
    )
    assert text not in err.message


def test_cells_of_columns_validate_does_not_read_and_edge_whitespace_pass():
    """Guard (passes at ``941f8a7`` too): U+0001 in ``rater_1`` and ``notes`` (counted,
    never read), and ``S1\\t`` in ``site``, whose tab ``_norm_cell``'s ``strip()`` removes."""
    raw = schema.table_from_columns(_cells(rater_1="x\x01", notes="n\x1b[31m"))
    schema.validate(raw)
    raw = schema.table_from_columns(_cells(site="S1\t"))
    assert raw.columns["site"][7] == "S1"
    schema.validate(raw)


def test_a_trailing_tab_in_a_site_cell_is_stripped_before_the_check(tmp_path, monkeypatch, capsys):
    """Guard (passes at ``941f8a7`` too), through ``proofpack run``: ``site`` cells ``S1\\t``
    in a CSV run with exit 0; the tab is gone before ``validate`` reads the cell."""
    cols = make_cohort(n=200)
    cols["site"] = [v + "\t" if v == "S1" else v for v in cols["site"]]
    _own_home(tmp_path, monkeypatch)
    csv_path, yml = _prepare(tmp_path, cols=cols)
    out = tmp_path / "pack"
    rc = _run(csv_path, yml, out, "--offline")
    printed = capsys.readouterr()
    assert rc == 0, printed.out + printed.err
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert "\t" not in json.dumps(doc["subgroups"], ensure_ascii=False)


# ------------------------------------------------ RG-N3 / DEC-67: design/tokens.json


def test_tokens_json_pairs_honesty_stop_and_ok_with_their_own_bg_surfaces():
    """Lens-6 RG-N3, DEC-67. At ``941f8a7`` the three tokens were ``"on": "bg"`` with
    ``contrast_computed`` 6.80, 10.02 and 9.11, and ``source`` said three of D5's ratios "do
    not match the formula". Now: ``on`` is ``honesty-bg`` / ``stop-bg`` / ``ok-bg``,
    ``contrast`` is D5's 6.2 / 8.7 / 7.9 verbatim, ``contrast_computed`` is 6.19 / 8.65 /
    7.88, and the sentence is gone."""
    t = json.loads((ROOT / "design" / "tokens.json").read_text(encoding="utf-8"))
    got = {
        name: (
            t["color"][name]["on"],
            t["color"][name]["contrast"],
            t["color"][name]["contrast_computed"],
        )
        for name in ("honesty", "stop", "ok")
    }
    assert got == {
        "honesty": ("honesty-bg", "6.2:1", "6.19:1"),
        "stop": ("stop-bg", "8.7:1", "8.65:1"),
        "ok": ("ok-bg", "7.9:1", "7.88:1"),
    }
    assert "do not match the formula" not in t["source"]
    assert "6.80" not in t["source"] and "10.02" not in t["source"] and "9.11" not in t["source"]


# ------------------------------------------------ DEC-12(ii): the sweep lists the new mutants


def test_the_sweep_lists_the_repair6_mutants():
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
        "schema_dec66_check_not_called",
        "schema_dec66_c1_dropped",
        "declare_self_reference_check_dropped",
        "declare_walk_enters_shared_objects_again",
    } <= day8
