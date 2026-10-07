"""Build day 14 (E14 item 3; LW-01 log defect 5): ``--offline``, ``--quiet`` and
``--json-log`` are accepted after every subcommand and sub-subcommand the CLI builds, with
the same effect as before it (/docs/quickstart says they work before and after).

At 3ee5601 ``proofpack licence verify FILE --offline`` exited 2 ``unrecognized arguments:
--offline`` while ``proofpack --offline licence verify FILE`` worked (measured in the
LW-01 walk-through, Windows 11, Python 3.12.10). The parsers are found by walking the
argparse tree :func:`proofpack.cli._build_parser` returns, not from a hand list, so a
parser added later is covered without editing this file.
"""

from __future__ import annotations

import argparse
import json

import pytest

from conftest import ephemeral_registry, write_licence
from proofpack import cli
from proofpack.errors import EXIT_OK

pytestmark = pytest.mark.day14

FLAGS = {"--offline": "offline", "--quiet": "quiet", "--json-log": "json_log"}


def _leaves(parser: argparse.ArgumentParser, path: tuple[str, ...] = ()):
    subs = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    if not subs:
        yield path, parser
        return
    for action in subs:
        for name, child in action.choices.items():
            yield from _leaves(child, (*path, name))


def _required(parser: argparse.ArgumentParser) -> list[str]:
    """A placeholder for every positional and every required option of ``parser``."""
    argv: list[str] = []
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction | argparse._HelpAction):
            continue
        if not a.option_strings:
            argv.append("x")
        elif a.required:
            argv += [a.option_strings[0], "x"]
    return argv


LEAVES = dict(sorted(_leaves(cli._build_parser()), key=lambda t: t[0]))
PATHS = list(LEAVES)


def test_the_walk_finds_every_command_and_the_nested_licence_parsers():
    assert set(PATHS) == {
        ("doctor",),
        ("map",),
        ("run",),
        ("compare",),
        ("fixtures",),
        ("licence", "show"),
        ("licence", "verify"),
        ("licence", "install"),
    }


@pytest.mark.parametrize("flag", sorted(FLAGS))
@pytest.mark.parametrize("path", PATHS, ids=lambda p: "-".join(p))
def test_global_flag_after_the_last_positional_of_every_parser(path, flag, capsys):
    argv = [*path, *_required(LEAVES[path]), flag]
    try:
        ns = cli._build_parser().parse_args(argv)
    except SystemExit as exc:  # argparse's exit 2
        pytest.fail(f"{argv} exited {exc.code}: {capsys.readouterr().err.strip()}")
    assert getattr(ns, FLAGS[flag]) is True, argv
    for other, dest in FLAGS.items():
        if other != flag:
            assert getattr(ns, dest) is False, (argv, dest)


@pytest.mark.parametrize("flag", sorted(FLAGS))
@pytest.mark.parametrize("path", PATHS, ids=lambda p: "-".join(p))
def test_global_flag_before_and_between_subcommands(path, flag):
    tail = _required(LEAVES[path])
    for i in range(len(path) + 1):
        argv = [*path[:i], flag, *path[i:], *tail]
        ns = cli._build_parser().parse_args(argv)
        assert getattr(ns, FLAGS[flag]) is True, argv


def test_all_three_flags_after_the_file_together():
    ns = cli._build_parser().parse_args(
        ["licence", "verify", "f.lic", "--offline", "--quiet", "--json-log"]
    )
    assert (ns.offline, ns.quiet, ns.json_log, ns.file) == (True, True, True, "f.lic")


def test_licence_verify_with_each_flag_after_the_file(tmp_path, capsys):
    lic = write_licence(tmp_path / "proofpack.lic")
    reg = ephemeral_registry()
    rc = cli.main(["licence", "verify", str(lic), "--offline"], registry=reg)
    assert rc == EXIT_OK and "status: ok" in capsys.readouterr().out
    rc = cli.main(["licence", "verify", str(lic), "--json-log"], registry=reg)
    payload = json.loads(capsys.readouterr().out)
    assert rc == EXIT_OK and payload["licence"]["status"] == "ok"
    rc = cli.main(["licence", "verify", str(lic), "--quiet"], registry=reg)
    assert rc == EXIT_OK and capsys.readouterr().out == ""
    # the same output as the flag before the subcommand
    cli.main(["--json-log", "licence", "verify", str(lic)], registry=reg)
    before = capsys.readouterr().out
    cli.main(["licence", "verify", str(lic), "--json-log"], registry=reg)
    assert capsys.readouterr().out == before
