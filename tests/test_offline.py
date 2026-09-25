"""Build day 8, lane A (A-P2): ``--offline`` = zero sockets (D1 section 6 and 7).

E7's test made ``socket.socket`` and ``socket.create_connection`` raise around ``run``.
This extends it: ``socket.socket``, ``socket.getaddrinfo`` and ``socket.create_connection``
all raise, the telemetry transport raises too, and ``run``, ``compare``, ``map``,
``doctor`` and ``licence verify`` each complete under ``--offline``. ``proofpack
fixtures`` (A-P3, build day 9) joined the list: ``test_fixtures_offline_opens_no_socket``
runs it with ``--html`` under a licence and with ``--r-captures`` (it carries ``day9`` and
``ap3`` beside this module's markers). The CI job ``offline-namespace``
(.github/workflows/ci.yml) runs one whole ``proofpack run`` inside ``unshare -rn`` with
and without ``--offline``; its first run is GitHub Actions run 35911876338 at ``eda8a35``
(23 September 2026), job "proofpack run inside unshare -rn (no network)", conclusion
success (read with ``gh run view`` on 24 September 2026). The tests here do not depend
on it.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from conftest import (
    NETWORK_ATTEMPTS,
    REAL_TRANSPORT,
    confirmed_mapping,
    ephemeral_registry,
    write_licence,
)
from proofpack.cli import main
from proofpack.errors import EXIT_OK, EXIT_WARNINGS
from test_egress import f19_cohort, f19_criteria, prepare, run_cli, write_csv

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


def test_telemetry_false_with_the_real_transport_and_sockets_refused_opens_no_socket(
    tmp_path: Path, monkeypatch, capsys, no_sockets
):
    """A-P2 lens 1 RG-N5: ``egress.telemetry: false`` without ``--offline``, the real
    ``urllib`` transport handed to ``main`` and the three socket entry points refused
    (the lens's probe P4, now a test). The sweep's ``ap2_telemetry_false_ignored`` mutant
    is what fails it."""
    csv_path, yml, out = prepare(tmp_path, monkeypatch, crit=f19_criteria(telemetry=False))
    assert run_cli(csv_path, yml, out, transport=REAL_TRANSPORT) == EXIT_OK
    printed = capsys.readouterr().out
    assert no_sockets.calls == [] and NETWORK_ATTEMPTS == []
    assert "telemetry skipped (egress.telemetry: false); nothing was sent" in printed
    assert (out / "run.json").exists()


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


@pytest.mark.day9
@pytest.mark.ap3
def test_fixtures_offline_opens_no_socket(tmp_path: Path, capsys, no_sockets):
    rc = main(
        ["fixtures", "--offline", "--out", str(tmp_path), "--html", "--r-captures"],
        registry=ephemeral_registry(),
    )
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    assert (tmp_path / "fixtures_report.json").exists() and (tmp_path / "T12.html").exists()
    assert no_sockets.calls == [] and NETWORK_ATTEMPTS == []
    # without --offline the command is the same: it has no network step to skip
    assert main(["fixtures", "--out", str(tmp_path)], registry=ephemeral_registry()) == EXIT_OK
    assert no_sockets.calls == []


def test_the_ci_namespace_job_and_its_script_exist_and_assert_both_invocations():
    repo = Path(__file__).resolve().parent.parent
    workflow = repo / ".github" / "workflows" / "ci.yml"
    # no skip (lens FA2-R5): scripts/mutation_sweep.py's COPIED tuple includes .github
    assert workflow.exists(), f"{workflow} is missing"
    ci = workflow.read_text(encoding="utf-8")
    assert "offline-namespace:" in ci and "unshare -rn" in ci
    assert "ci_namespace_run.py --offline" in ci and "ci_namespace_run.py --online" in ci
    assert "[W16]" in ci and "telemetry skipped (--offline)" in ci
    script = (repo / "scripts" / "ci_namespace_run.py").read_text(encoding="utf-8")
    assert "run.json" in script and "ephemeral_registry" in script


@pytest.mark.day10
def test_compare_with_t2_offline_opens_no_socket(tmp_path: Path, monkeypatch, capsys, no_sockets):
    """E10: the full ``compare`` - statistics, T2.html under a licence - with the three
    socket entry points refused; then without ``--offline`` and with the refusing
    transport in place, so the only socket the command could open is the transport's."""
    import shutil

    from conftest import write_licence

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    write_licence(home / "proofpack.lic")
    fx = Path(__file__).resolve().parent / "fixtures" / "f5"
    for name in ("f5_new.csv", "f5_prior.csv", "criteria.yaml"):
        shutil.copy(fx / name, tmp_path / name)
    confirmed_mapping(tmp_path / "f5_new.csv")
    argv = [
        "compare",
        "--input",
        str(tmp_path / "f5_new.csv"),
        "--prior",
        str(tmp_path / "f5_prior.csv"),
        "--criteria",
        str(tmp_path / "criteria.yaml"),
        "--out",
        str(tmp_path / "pack"),
    ]
    rc = main([*argv, "--offline"], registry=ephemeral_registry())
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    assert (tmp_path / "pack" / "T2.html").exists() and (tmp_path / "pack" / "run.json").exists()
    assert no_sockets.calls == [] and NETWORK_ATTEMPTS == []
    assert "telemetry skipped (--offline); nothing was sent" in printed
    # the fixture declares egress.telemetry: false, so without --offline nothing is sent
    rc = main([*argv, "--out", str(tmp_path / "pack2")], registry=ephemeral_registry())
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    assert no_sockets.calls == [] and NETWORK_ATTEMPTS == []
    assert "telemetry skipped (egress.telemetry: false)" in printed
