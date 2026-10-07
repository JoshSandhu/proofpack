"""E14 repair 2 (build day 14, lane E): the findings of the two cold lenses on ``e67c5fa``
(``handoffs/2026-10-07_E_e14_lens2_fresh-attack.md`` and
``handoffs/2026-10-07_E_e14_lens2_regression.md``).

* FA-B1 / RG-N2: e67c5fa's meta-test was named ``..._every_e14_docx_test_is_selected_by_ap4_
  and_takes_the_extra_rule`` and took only the E14 tests whose source held the text
  ``render_docx``. A test that opened ``T1.docx`` after ``pytest.importorskip("docx")`` with
  no ``ap4`` mark passed it (lens 2 fresh-attack, mutant T3). It is deleted. Its
  replacement below,
  :func:`test_fa_b1_other_e14_modules_tests_naming_docx_or_importorskip_carry_ap4_and_needs_extra`,
  takes the ``test*`` functions of the ``test_e14_*`` modules (this file excluded), module
  level, inside ``if``/``try`` blocks and in (nested) ``Test*`` classes (orchestrator
  after-cap repair, lens 3 FA-B1), whose code - decorators, argument names and body, with the
  docstring and comments left out - holds a name, attribute, import or string containing
  ``docx`` in any case, or the name ``importorskip``, directly or through a module-level
  function or module-level lambda of the same module that the test names or takes as an
  argument. It also asserts that no such test calls ``importorskip`` (restored after lens 3
  FA-B2 = RG-B1; repair 2 had dropped e67c5fa's guard without recording it). It does not
  read fixtures or helpers defined in other modules. It asserts that set is exactly the two
  E14 DOCX tests, that each carries ``ap4`` (its own, its class's or its module's marks),
  and that its one ``skipif`` is the mark object :data:`ap4_docx.needs_extra` stores. At
  e67c5fa, with lens 2's T3 appended to ``test_e14_cover_row.py`` or its T5 to
  ``test_e14_global_flags.py``, or with ``@needs_extra`` replaced by ``skipif(True,
  reason=SKIP_REASON)``, e67c5fa's meta-test gave ``1 passed`` and this one, with this
  commit's ``test_e14_repair1.py`` copied in beside it, ``1 failed``.
* FA-B2 / RG-N1 / RG-O1: commit messages ``834634c`` and ``e67c5fa`` each quote a sentence
  the lenses found false. The branch history is not rewritten; the corrections are in
  ``handoffs/2026-10-07_E14_commit_message_corrections.md``, committed on the branch.
* RG-N3: e67c5fa's ``test_e14_repair1.py`` docstring said "every CI job skipped them"; in run
  37631774505 the job ``pytest + ruff`` skipped them and the job ``pytest -m ap4 with the
  [docx] extra installed`` did not select them (they carried no ``ap4`` mark).
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from ap4_docx import SKIP_REASON, needs_extra

pytestmark = pytest.mark.day14

REPO = Path(__file__).resolve().parent.parent
CORRECTIONS = REPO / "handoffs" / "2026-10-07_E14_commit_message_corrections.md"
COVER_TEST = "test_docx_cover_row_text_equals_the_html_cover_labels_in_order"
MARGIN_TEST = "test_docx_t1_prints_each_repeated_line_once_naming_every_id"


def _texts(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.alias):
        return [node.name, node.asname or ""]
    if isinstance(node, ast.ImportFrom):
        return [node.module or ""]
    if isinstance(node, ast.arg):
        return [node.arg]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def _code_nodes(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    """The function's decorators, arguments and body, the docstring left out (comments are
    not in the AST)."""
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    return [*fn.decorator_list, fn.args, *body]


def _names_docx(fn, helpers: dict[str, ast.AST], seen: set[str]) -> bool:
    for top in _code_nodes(fn):
        for node in ast.walk(top):
            texts = _texts(node)
            if any("docx" in t.lower() or t == "importorskip" for t in texts):
                return True
            if isinstance(node, (ast.Name, ast.arg)):
                for name in texts:
                    if name in helpers and name not in seen:
                        seen.add(name)
                        if _names_docx(helpers[name], helpers, seen):
                            return True
    return False


def docx_tests_in_source(source: str) -> list[tuple[str | None, str]]:
    """``(owner or None, name)`` of each ``test*`` function in ``source`` whose code names
    ``docx`` or ``importorskip`` (see the module docstring). Orchestrator after-cap repair
    (lens 3 FA-B1): a test at ANY depth is taken - module level, inside ``if`` or ``try``
    blocks, and inside ``Test*`` classes nested in ``Test*`` classes (owner is the dotted
    class path) - and a module-level ``name = lambda ...`` counts as a helper like a def."""
    tree = ast.parse(source)
    defs = (ast.FunctionDef, ast.AsyncFunctionDef)
    helpers: dict[str, ast.AST] = {}
    for n in ast.walk(tree):
        if isinstance(n, defs):
            helpers.setdefault(n.name, n)
        elif isinstance(n, ast.Assign) and isinstance(n.value, ast.Lambda):
            for target in n.targets:
                if isinstance(target, ast.Name):
                    lam = n.value
                    helpers.setdefault(
                        target.id,
                        ast.FunctionDef(
                            name=target.id,
                            args=lam.args,
                            body=[ast.Expr(lam.body)],
                            decorator_list=[],
                        ),
                    )
    tests: list[tuple[str | None, ast.AST]] = []

    def visit(node: ast.AST, owner: str | None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, f"{owner}.{child.name}" if owner else child.name)
            elif isinstance(child, defs):
                if child.name.startswith("test"):
                    tests.append((owner, child))
            else:
                visit(child, owner)

    visit(tree, None)
    return [(owner, fn.name) for owner, fn in tests if _names_docx(fn, helpers, {fn.name})]


def _marks(obj) -> list:
    marks = getattr(obj, "pytestmark", [])
    return list(marks) if isinstance(marks, list) else [marks]


def test_fa_b1_other_e14_modules_tests_naming_docx_or_importorskip_carry_ap4_and_needs_extra():
    found = []
    for path in sorted((REPO / "tests").glob("test_e14_*.py")):
        if path.stem == Path(__file__).stem:
            continue
        module = importlib.import_module(path.stem)
        for owner, name in docx_tests_in_source(path.read_text(encoding="utf-8")):
            holder = module
            for part in (owner or "").split(".") if owner else []:
                holder = getattr(holder, part)
            fn = getattr(holder, name)
            marks = _marks(fn) + (_marks(holder) if owner else []) + _marks(module)
            found.append((path.stem, owner, name, marks))
    assert {(m, o, n) for m, o, n, _ in found} == {
        ("test_e14_cover_row", None, COVER_TEST),
        ("test_e14_margin_notes", None, MARGIN_TEST),
    }
    for module, _owner, name, marks in found:
        assert "ap4" in {m.name for m in marks}, (module, name)
        skips = [m for m in marks if m.name == "skipif"]
        assert [m.kwargs.get("reason") for m in skips] == [SKIP_REASON], (module, name)
        # the mark object ap4_docx.needs_extra stores, not a skipif copied with its reason
        assert skips[0] is needs_extra.mark, (module, name, skips[0].args)
    # Orchestrator after-cap repair (lens 3 FA-B2 = RG-B1): repair 2 dropped e67c5fa's guard
    # that the DOCX tests never call importorskip (a silent skip when the extra is missing);
    # it is restored here for every test the scan finds.
    import inspect

    for module, owner, name, _ in found:
        holder = importlib.import_module(module)
        for part in (owner or "").split(".") if owner else []:
            holder = getattr(holder, part)
        assert "importorskip" not in inspect.getsource(getattr(holder, name)), (module, name)


# Literal inputs of the scanner test: lens 2's two counter-examples (fresh-attack T3: a CLI
# run with --format docx read through importorskip("docx"); regression T5: importorskip
# alone), a CLI run with --format docx and no importorskip, one through a same-module
# helper, one through a fixture argument, one in a class, and two controls that mention
# DOCX only in a comment or the docstring.
FLAGGED = {
    "lens2_fa_t3_cli_docx": (
        "def test_cover_via_the_cli(tmp_path):\n"
        "    d = pytest.importorskip('docx')\n"
        "    argv = ['run', '--templates', 'T1', '--format', 'docx', '--offline']\n"
        "    assert cli.main(argv) == 0\n"
    ),
    "lens2_rg_t5_importorskip": (
        "def test_extra_docx_via_cli(tmp_path):\n    pytest.importorskip('docx')\n"
    ),
    "helper": (
        "def _render(doc):\n    return render_docx.render_docx_bytes(doc, 'T1')\n\n"
        "def test_helper(document):\n    assert _render(document)\n"
    ),
    "cli_format_docx_only": (
        "def test_cli(tmp_path):\n"
        "    assert cli.main(['run', '--format', 'docx', '--offline']) == 0\n"
    ),
    "fixture_argument": (
        "@pytest.fixture\ndef rendered():\n    import docx\n    return docx\n\n"
        "def test_fixture(rendered):\n    assert rendered\n"
    ),
    "class_method": (
        "class TestDocx:\n    def test_bytes(self):\n        importorskip('python-docx')\n"
    ),
}
NOT_FLAGGED = {
    "comment_only": (
        "def test_lines():\n    # the DOCX template reads the same context\n    assert 1\n"
    ),
    "docstring_only": ('def test_lines():\n    """The DOCX cell."""\n    assert 1\n'),
}


@pytest.mark.parametrize("key", sorted(FLAGGED))
def test_the_scanner_takes_lens_2s_counter_examples(key: str):
    assert docx_tests_in_source(FLAGGED[key]), key


@pytest.mark.parametrize("key", sorted(NOT_FLAGGED))
def test_the_scanner_leaves_comment_and_docstring_mentions(key: str):
    assert docx_tests_in_source(NOT_FLAGGED[key]) == [], key


def test_rg_o1_fa_b2_the_commit_message_corrections_are_on_the_branch():
    text = " ".join(CORRECTIONS.read_text(encoding="utf-8").split())
    for needle in (
        "834634c",
        "told nothing about how to accept",
        "answer a or q",
        "e67c5fa",
        "assert 'ap4' in set()",
        "Extra items in the left set",
    ):
        assert needle in text, needle


FALSE = [
    # FA-B1 / RG-N2: the name said "every E14 DOCX test"; it took only tests naming render_docx
    ("tests/test_e14_repair1.py", "every_e14_docx_test_is_selected_by_ap4"),
    # RG-N3: run 37631774505's docx-extra job did not select them (no ap4 mark)
    ("tests/test_e14_repair1.py", "every CI job skipped them"),
]


@pytest.mark.parametrize(("rel", "phrase"), FALSE, ids=[p for _, p in FALSE])
def test_the_sentences_lens_2_found_false_are_gone(rel: str, phrase: str):
    assert phrase not in (REPO / rel).read_text(encoding="utf-8")
