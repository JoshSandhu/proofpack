"""Independent review of 11 October 2026: the strings a customer reads at the command line
and in the T12 error ledger carry no internal decision id or spec section number.

Scope: the HALT / warning meanings in ``errors.py``, the ``--help`` text of ``map``, ``run``
and ``compare``, and every string literal that is not a docstring in ``cli.py``, ``run.py``
and ``io/mapping.py``. Comments and docstrings are not customer-visible and are left alone.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from proofpack import errors
from proofpack.cli import main

pytestmark = [pytest.mark.day15, pytest.mark.fix1011]

SRC = Path(errors.__file__).parent
INTERNAL = re.compile(r"DEC-\d|D1 section|D1 §")


def _non_docstring_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first.value))
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
    ]


def test_error_and_warning_meanings_carry_no_internal_reference():
    tables = (
        errors.HALT_CODES,
        errors.SCHEMA_CODES,
        errors.MAPPING_CODES,
        errors.WARN_CODES,
    )
    for table in tables:
        for code, meaning in table.items():
            assert not INTERNAL.search(meaning), (code, meaning)
    assert errors.MAPPING_CODES["E01"] == "composite case key: two or more columns identify a case"
    assert errors.WARN_CODES["W06"] == "single-class site(s) present; site-level metrics limited"


def _help(argv, capsys) -> str:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 0
    return " ".join(capsys.readouterr().out.split())


@pytest.mark.parametrize("argv", [[], ["map"], ["run"], ["compare"]])
def test_help_text_carries_no_internal_reference(argv, capsys):
    out = _help([*argv, "--help"], capsys)
    assert out
    assert not INTERNAL.search(out), out


def test_help_text_keeps_its_plain_wording(capsys):
    assert "map original headers to canonical roles" in _help(["--help"], capsys)
    assert "(run never proposes a mapping itself)" in _help(["run", "--help"], capsys)
    assert "beside the new table" in _help(["compare", "--help"], capsys)


@pytest.mark.parametrize("module", ["cli.py", "run.py", "io/mapping.py"])
def test_customer_visible_string_literals_carry_no_internal_reference(module):
    for text in _non_docstring_literals(SRC / module):
        assert not INTERNAL.search(text), (module, text)
