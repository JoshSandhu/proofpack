"""Build day 8, lane A (A-P2): ``--offline`` = zero sockets (D1 section 6 and 7).

E7's test made ``socket.socket`` and ``socket.create_connection`` raise around ``run``.
This extends it: ``socket.socket``, ``socket.getaddrinfo`` and ``socket.create_connection``
all raise, the telemetry transport raises too, and ``run``, ``compare``, ``map``,
``doctor`` and ``licence verify`` each complete under ``--offline``. ``proofpack
fixtures`` is not a subcommand at 7b2ca2a (D1 section 7 lists it; it is not built), so
it is not here. The CI job ``offline-namespace`` (.github/workflows/ci.yml) runs the
whole ``proofpack run`` inside ``unshare -rn`` with and without ``--offline``.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from conftest import NETWORK_ATTEMPTS, confirmed_mapping, ephemeral_registry, write_licence
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from test_egress import f19_cohort, prepare, run_cli, write_csv

pytestmark = [pytest.mark.day8, pytest.mark.ap2]


class Sockets:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def refuse(self, name):
        def _refuse(*a, **k):
            self.calls.append(name)
            raise AssertionError(f"socket.{name} was called")

        return _refuse


@pytest.fixture
def no_sockets(monkeypatch) -> Sockets:
    s = Sockets()
    for name in ("socket", "getaddrinfo", "create_connection"):
        monkeypatch.setattr(socket, name, s.refuse(name))
    return s


def test_run_offline_opens_no_socket_and_calls_no_transport(
    tmp_path: Path, monkeypatch, capsys, no_sockets
):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    called = []

    def transport(url, body, timeout):
        called.append(url)
        return 204

    assert run_cli(csv_path, yml, out, "--offline", transport=transport) == EXIT_OK
    assert (out / "run.json").exists() and (out / "pseudonyms.json").exists()
    assert no_sockets.calls == [] and called == [] and NETWORK_ATTEMPTS == []
    assert "telemetry skipped (--offline)" in capsys.readouterr().out


def test_run_online_with_a_recording_transport_opens_no_socket_itself(
    tmp_path: Path, monkeypatch, capsys, no_sockets
):
    """The only socket the engine could ever open is the transport's; with the transport
    replaced, a run without ``--offline`` still touches ``socket`` nowhere."""
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    called = []

    def transport(url, body, timeout):
        called.append(url)
        return 204

    assert run_cli(csv_path, yml, out, transport=transport) == EXIT_OK
    capsys.readouterr()
    assert no_sockets.calls == [] and len(called) == 1


def test_map_yes_offline_opens_no_socket(tmp_path: Path, monkeypatch, capsys, no_sockets):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    prior = csv_path.with_name(csv_path.name + ".mapping.json")
    rc = main(
        [
            "map",
            "--input",
            str(csv_path),
            "--criteria",
            str(yml),
            "--out",
            str(prior),
            "--yes",
            "--offline",
        ],
        registry=ephemeral_registry(),
    )
    assert rc == EXIT_OK, capsys.readouterr().out
    assert no_sockets.calls == []


def test_compare_offline_opens_no_socket(tmp_path: Path, monkeypatch, capsys, no_sockets):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    prior_csv = write_csv(tmp_path / "prior.csv", f19_cohort())
    mapping = confirmed_mapping(csv_path)
    rc = main(
        [
            "compare",
            "--input",
            str(csv_path),
            "--prior",
            str(prior_csv),
            "--criteria",
            str(yml),
            "--mapping",
            str(mapping),
            "--out",
            str(out),
            "--yes",
            "--offline",
        ],
        registry=ephemeral_registry(),
    )
    printed = capsys.readouterr()
    assert rc in (EXIT_OK, EXIT_WARNINGS), printed
    assert (out / "compare_ingest_report.json").exists()
    assert no_sockets.calls == []
    report = json.loads((out / "compare_ingest_report.json").read_text(encoding="utf-8"))
    assert report["paired"] is True


def test_doctor_offline_opens_no_socket(capsys, no_sockets):
    assert main(["doctor", "--offline"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "skipped (--offline)" in out and no_sockets.calls == []
    assert main(["doctor"]) == EXIT_OK  # doctor itself never attempts the network
    assert no_sockets.calls == []


def test_licence_verify_offline_opens_no_socket(tmp_path: Path, capsys, no_sockets):
    lic = write_licence(tmp_path / "a.lic")
    # the global flag goes before the subcommand here: ``licence verify FILE --offline`` is
    # refused by argparse at 7b2ca2a (the ``common`` parent is on ``licence``, not on
    # ``verify``; SystemExit 2, measured 22 September) - carried as a CLI nit
    rc = main(["--offline", "licence", "verify", str(lic)], registry=ephemeral_registry())
    assert rc == EXIT_OK, capsys.readouterr().out
    assert no_sockets.calls == []


def test_the_ci_namespace_job_and_its_script_exist_and_assert_both_invocations():
    repo = Path(__file__).resolve().parent.parent
    workflow = repo / ".github" / "workflows" / "ci.yml"
    if not workflow.exists():
        # the mutation sweep's copy holds src/tests/schema/scripts only (its COPIED tuple);
        # the job's presence is asserted in the real tree, not in the copy
        pytest.skip("no .github/workflows/ci.yml here (the mutation sweep's copy)")
    ci = workflow.read_text(encoding="utf-8")
    assert "offline-namespace:" in ci and "unshare -rn" in ci
    assert "ci_namespace_run.py --offline" in ci and "ci_namespace_run.py --online" in ci
    assert "[W16]" in ci and "telemetry skipped (--offline)" in ci
    script = (repo / "scripts" / "ci_namespace_run.py").read_text(encoding="utf-8")
    assert "run.json" in script and "ephemeral_registry" in script
