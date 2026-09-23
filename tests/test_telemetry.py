"""Build day 8, lane A (A-P2): the telemetry send (D1 section 6).

``send`` makes one HTTP request with a 5 s timeout, does not follow a 3xx answer and
never raises an ``Exception``; a failure is one W16
line and nothing else changes - the exit code is the run's and ``run.json`` is untouched
(hashed before and after). The real ``urllib`` transport is exercised against a loopback
``http.server`` (a socket on 127.0.0.1, opened by this test on purpose); every CLI run in
this file uses a recording transport, and the suite-wide guard in ``conftest`` would turn
any reach for the real one into a test failure.
"""

from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from conftest import NETWORK_ATTEMPTS, REAL_TRANSPORT, write_licence
from proofpack.egress import telemetry
from proofpack.errors import EXIT_LICENCE, EXIT_OK
from test_egress import Recorder, f19_criteria, prepare, run_cli

pytestmark = [pytest.mark.day8, pytest.mark.ap2]

GOOD = {
    "schema": "proofpack-telemetry/1",
    "licence_id": "lic_0123456789abcdef0123456789abcdef",
    "run_id": "9822b658-0a43-4b13-9b86-9ec1a74b0e19",
    "engine_version": "0.1.0.dev1",
    "platform": "linux-x86_64-cp312",
    "manifest_sha256": "f" * 64,
    "duration_s": 1.5,
    "halt_code": None,
    "row_count_bucket": "<1k",
    "timestamp": "2026-09-22T13:29:12Z",
}


# ------------------------------------------------------------------- send() semantics


def test_constants_are_the_documented_ones():
    assert telemetry.TELEMETRY_URL == "https://proofpack.globalphoenix.co.uk/api/telemetry"
    assert telemetry.TIMEOUT_S == 5.0
    assert telemetry.USER_AGENT == "proofpack-telemetry/1"


def test_send_204_is_sent_and_the_body_is_compact_sorted_json():
    rec = Recorder(204)
    r = telemetry.send(GOOD, transport=rec)
    assert r == telemetry.SendResult(True, 204, None)
    assert r.line() == "telemetry sent (http 204) to " + telemetry.TELEMETRY_URL
    assert rec.calls[0]["timeout"] == 5.0
    assert rec.calls[0]["url"] == telemetry.TELEMETRY_URL
    assert json.loads(rec.calls[0]["body"]) == GOOD
    assert rec.calls[0]["body"] == json.dumps(GOOD, sort_keys=True, separators=(",", ":")).encode()


@pytest.mark.parametrize("status", [500, 400, 404, 301, 199])
def test_send_non_2xx_is_not_sent_with_the_status(status):
    r = telemetry.send(GOOD, transport=Recorder(status))
    assert r == telemetry.SendResult(False, status, "http_error")
    assert r.line().startswith("[W16] telemetry not sent (http_error, http ")
    assert "run.json and the exit code are unchanged" in r.line()


@pytest.mark.parametrize(
    "exc, reason",
    [
        (TimeoutError("timed out"), "timeout"),
        (ConnectionRefusedError(111, "refused"), "connection_refused"),
        (socket.gaierror(-2, "Name or service not known"), "unreachable"),
        (OSError(101, "Network is unreachable"), "unreachable"),
        (RuntimeError("boom"), "transport_error"),
        (ValueError("bad"), "transport_error"),
    ],
)
def test_send_never_raises_and_classifies_the_failure(exc, reason):
    def failing(url, body, timeout):
        raise exc

    r = telemetry.send(GOOD, transport=failing)
    assert r == telemetry.SendResult(False, None, reason)
    assert reason in telemetry.REASON_CODES


def test_send_classifies_a_urlerror_wrapping_the_cause():
    import urllib.error

    def failing(url, body, timeout):
        raise urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))

    assert telemetry.send(GOOD, transport=failing).reason_code == "unreachable"

    def refused(url, body, timeout):
        raise urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))

    assert telemetry.send(GOOD, transport=refused).reason_code == "connection_refused"


def test_send_refuses_an_invalid_payload_before_any_transport_call():
    rec = Recorder(204)
    for bad in (
        {**GOOD, "site": "St Mary's"},
        {**GOOD, "row_count_bucket": "7 rows"},
        {k: v for k, v in GOOD.items() if k != "run_id"},
        {**GOOD, "licence_id": "L-1"},
        {**GOOD, "duration_s": -1},
    ):
        assert telemetry.send(bad, transport=rec) == telemetry.SendResult(
            False, None, "payload_invalid"
        )
    assert rec.calls == []


def test_the_default_transport_is_urllib_and_no_network_module_is_imported_at_module_level():
    assert REAL_TRANSPORT.__name__ == "urllib_transport"
    src = Path(telemetry.__file__).read_text(encoding="utf-8")
    top_level = [
        ln
        for ln in src.splitlines()
        if ln.startswith(("import socket", "import urllib", "from urllib", "import http"))
    ]
    assert top_level == []
    root = Path(telemetry.__file__).resolve().parents[1]
    offenders = []
    for p in root.rglob("*.py"):
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.startswith(
                (
                    "import socket",
                    "from socket",
                    "import urllib",
                    "from urllib",
                    "import http",
                    "from http",
                    "import requests",
                )
            ):
                offenders.append(f"{p.name}: {ln}")
    assert offenders == []


# ---------------------------------------------------- the real transport on loopback


class _Handler(BaseHTTPRequestHandler):
    status = 204
    delay = 0.0
    seen: list[dict] = []

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        _Handler.seen.append(
            {
                "path": self.path,
                "content_type": self.headers.get("Content-Type"),
                "user_agent": self.headers.get("User-Agent"),
                "body": body,
            }
        )
        time.sleep(_Handler.delay)
        self.send_response(_Handler.status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):  # silence
        return


@pytest.fixture
def loopback():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    _Handler.seen = []
    _Handler.status = 204
    _Handler.delay = 0.0
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/api/telemetry"
    finally:
        srv.shutdown()
        srv.server_close()


def test_real_transport_posts_json_and_reads_204(loopback):
    r = telemetry.send(GOOD, url=loopback, transport=REAL_TRANSPORT)
    assert r == telemetry.SendResult(True, 204, None)
    assert len(_Handler.seen) == 1
    seen = _Handler.seen[0]
    assert seen["path"] == "/api/telemetry"
    assert seen["content_type"] == "application/json"
    assert seen["user_agent"] == "proofpack-telemetry/1"
    assert json.loads(seen["body"]) == GOOD


def test_real_transport_500_is_http_error_and_a_slow_server_is_a_timeout(loopback):
    _Handler.status = 500
    r = telemetry.send(GOOD, url=loopback, transport=REAL_TRANSPORT)
    assert r == telemetry.SendResult(False, 500, "http_error")
    _Handler.status = 204
    _Handler.delay = 1.0
    r = telemetry.send(GOOD, url=loopback, transport=REAL_TRANSPORT, timeout=0.2)
    assert r == telemetry.SendResult(False, None, "timeout")
    _Handler.delay = 0.0


class _Redirecting(BaseHTTPRequestHandler):
    """Answers every POST with a 3xx and a Location on another listener."""

    status = 302
    location = ""
    seen: list[str] = []

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        _Redirecting.seen.append(f"POST {self.path}")
        self.send_response(_Redirecting.status)
        self.send_header("Location", _Redirecting.location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):  # silence
        return


class _Elsewhere(BaseHTTPRequestHandler):
    """The Location host: records every request it receives, whatever the method."""

    seen: list[str] = []

    def _record(self):
        _Elsewhere.seen.append(f"{self.command} {self.path} ua={self.headers.get('User-Agent')}")
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = do_POST = do_HEAD = _record  # noqa: N815 - http.server API

    def log_message(self, *a):  # silence
        return


@pytest.fixture
def redirecting():
    """Two loopback listeners: the first answers a 3xx with a Location on the second."""
    second = HTTPServer(("127.0.0.1", 0), _Elsewhere)
    first = HTTPServer(("127.0.0.1", 0), _Redirecting)
    for srv in (second, first):
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    _Elsewhere.seen = []
    _Redirecting.seen = []
    _Redirecting.location = f"http://127.0.0.1:{second.server_address[1]}/elsewhere"
    try:
        yield f"http://127.0.0.1:{first.server_address[1]}/api/telemetry"
    finally:
        for srv in (first, second):
            srv.shutdown()
            srv.server_close()


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_a_redirect_answer_is_not_followed_and_the_location_host_receives_nothing(
    redirecting, status
):
    """A-P2 lens 1 FA-N1: at 4d61b6e ``urllib``'s default opener turned a POST answered
    301/302/303 into a GET of the Location host and ``send`` reported ``sent`` with the
    second host's status. Now every 3xx is ``http_error`` with that status and the second
    listener receives nothing."""
    _Redirecting.status = status
    r = telemetry.send(GOOD, url=redirecting, transport=REAL_TRANSPORT)
    assert r == telemetry.SendResult(False, status, "http_error")
    assert _Redirecting.seen == ["POST /api/telemetry"]
    assert _Elsewhere.seen == []


def test_a_302_through_the_cli_prints_w16_and_the_location_host_receives_nothing(
    tmp_path: Path, monkeypatch, capsys, redirecting
):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    _Redirecting.status = 302

    def to_loopback(url, body, timeout):
        assert url == telemetry.TELEMETRY_URL
        return REAL_TRANSPORT(redirecting, body, timeout)

    rc = run_cli(csv_path, yml, out, transport=to_loopback)
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    lines = [ln.strip() for ln in printed.splitlines() if "[W16]" in ln]
    assert lines == [
        "[W16] telemetry not sent (http_error, http 302); run.json and the exit code are unchanged"
    ]
    assert "telemetry sent" not in printed
    assert _Redirecting.seen == ["POST /api/telemetry"]
    assert _Elsewhere.seen == []


def test_send_refuses_a_trailing_newline_in_licence_id_and_platform():
    """A-P2 lens 1 FA-N3: ``jsonschema`` alone accepts ``"lic_abc\\n"``; ``send`` projects
    through the whitelist first and answers ``payload_invalid`` without a transport call."""
    for key, value in (("licence_id", "lic_abc\n"), ("platform", "win-amd64-cp314\n")):
        rec = Recorder(204)
        r = telemetry.send({**GOOD, key: value}, transport=rec)
        assert r == telemetry.SendResult(False, None, "payload_invalid"), key
        assert rec.calls == []


def test_real_transport_connection_refused_on_a_closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    r = telemetry.send(GOOD, url=f"http://127.0.0.1:{port}/api/telemetry", transport=REAL_TRANSPORT)
    assert r.sent is False and r.reason_code in ("connection_refused", "transport_error", "timeout")


# ------------------------------------------------------ the CLI: isolation of the send


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "failure, reason",
    [
        (500, "http_error, http 500"),
        (TimeoutError("timed out"), "timeout"),
        (ConnectionRefusedError(111, "refused"), "connection_refused"),
    ],
)
def test_a_failed_send_prints_one_w16_line_and_leaves_exit_code_and_documents(
    tmp_path: Path, monkeypatch, capsys, failure, reason
):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    hashes: dict[str, str] = {}

    def transport(url, body, timeout):
        # the send happens after run.json exists
        for name in ("run.json", "ingest_report.json", "pseudonyms.json"):
            hashes[name] = _hash(out / name)
        if isinstance(failure, int):
            return failure
        raise failure

    rc = run_cli(csv_path, yml, out, transport=transport)
    printed = capsys.readouterr().out
    assert rc == EXIT_OK, printed
    assert len(hashes) == 3
    for name, h in hashes.items():
        assert _hash(out / name) == h, name
    lines = [ln for ln in printed.splitlines() if "[W16]" in ln]
    assert len(lines) == 1
    assert lines[0].strip() == (
        f"[W16] telemetry not sent ({reason}); run.json and the exit code are unchanged"
    )
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert [w["code"] for w in doc["warnings"]] == []  # never appended to the document
    assert "W16" not in (out / "run.json").read_text(encoding="utf-8")


def test_the_exit_code_with_a_failed_send_equals_the_exit_code_offline(
    tmp_path: Path, monkeypatch, capsys
):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    rc_online = run_cli(csv_path, yml, out, transport=Recorder(503))
    rc_offline = run_cli(csv_path, yml, tmp_path / "pack2", "--offline", transport=Recorder(204))
    capsys.readouterr()
    assert rc_online == rc_offline == EXIT_OK


def test_the_send_happens_after_run_json_exists_and_reads_the_final_bytes(
    tmp_path: Path, monkeypatch, capsys
):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    rec = Recorder(204, out)
    assert run_cli(csv_path, yml, out, transport=rec) == EXIT_OK
    capsys.readouterr()
    assert rec.calls[0]["run_json_exists"] is True
    assert rec.calls[0]["run_json_sha256"] == _hash(out / "run.json")


def test_telemetry_false_never_calls_the_transport(tmp_path: Path, monkeypatch, capsys):
    csv_path, yml, out = prepare(tmp_path, monkeypatch, crit=f19_criteria(telemetry=False))
    rec = Recorder(204, out)
    assert run_cli(csv_path, yml, out, transport=rec) == EXIT_OK
    printed = capsys.readouterr().out
    assert rec.calls == [] and NETWORK_ATTEMPTS == []
    assert "telemetry skipped (egress.telemetry: false); nothing was sent" in printed
    assert (out / "run.json").exists() and (out / "pseudonyms.json").exists()


def test_offline_never_calls_the_transport(tmp_path: Path, monkeypatch, capsys):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    rec = Recorder(204, out)
    assert run_cli(csv_path, yml, out, "--offline", transport=rec) == EXIT_OK
    printed = capsys.readouterr().out
    assert rec.calls == [] and NETWORK_ATTEMPTS == []
    assert "telemetry skipped (--offline); nothing was sent" in printed


def test_an_absent_egress_block_is_opt_out_so_the_send_happens(tmp_path: Path, monkeypatch, capsys):
    crit = f19_criteria()
    del crit["egress"]
    csv_path, yml, out = prepare(tmp_path, monkeypatch, crit=crit)
    rec = Recorder(204, out)
    assert run_cli(csv_path, yml, out, transport=rec) == EXIT_OK
    capsys.readouterr()
    assert len(rec.calls) == 1
    assert telemetry.telemetry_enabled(None) is True
    assert telemetry.telemetry_enabled({"egress": {"telemetry": False}}) is False
    assert telemetry.telemetry_enabled({"egress": {"telemetry": 0}}) is True  # only false


def test_a_refused_licence_sends_a_null_licence_id_and_exit_4_is_unchanged(
    tmp_path: Path, monkeypatch, capsys
):
    csv_path, yml, out = prepare(tmp_path, monkeypatch, licence=False)
    home = tmp_path / "home"
    # a file signed by the ephemeral key, verified against the SHIPPED registry: refused
    write_licence(home / "proofpack.lic")
    rec = Recorder(204, out)
    rc = run_cli(csv_path, yml, out, transport=rec, registry=None)
    printed = capsys.readouterr().out
    assert rc == EXIT_LICENCE, printed
    payload = json.loads(rec.calls[0]["body"])
    assert payload["licence_id"] is None
    doc = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert doc["manifest"]["watermark"] is not None
    assert "licence refused (" in printed  # unknown_key_id on the shipped registry


def test_json_log_carries_the_telemetry_result_and_the_skip_reason(
    tmp_path: Path, monkeypatch, capsys
):
    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    assert run_cli(csv_path, yml, out, "--json-log", transport=Recorder(502)) == EXIT_OK
    entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert entry["run"]["telemetry"] == {"sent": False, "status": 502, "reason_code": "http_error"}
    assert entry["run"]["exit_code"] == EXIT_OK
    assert run_cli(csv_path, yml, tmp_path / "p2", "--json-log", "--offline") == EXIT_OK
    entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert entry["run"]["telemetry"] == {"skipped": "--offline"}


def test_the_next_step_hint_and_doctor_say_what_is_sent_and_how_to_turn_it_off(
    tmp_path: Path, monkeypatch, capsys
):
    from proofpack.cli import TELEMETRY_SENTENCE, main

    csv_path, yml, out = prepare(tmp_path, monkeypatch)
    assert run_cli(csv_path, yml, out, transport=Recorder(204)) == EXIT_OK
    printed = capsys.readouterr().out
    assert TELEMETRY_SENTENCE in printed
    for key in (
        "schema",
        "licence_id",
        "run_id",
        "engine_version",
        "platform",
        "manifest_sha256",
        "duration_s",
        "halt_code",
        "row_count_bucket",
        "timestamp",
    ):
        assert key in TELEMETRY_SENTENCE
    assert "--offline" in TELEMETRY_SENTENCE and "egress.telemetry: false" in TELEMETRY_SENTENCE
    assert "https://proofpack.globalphoenix.co.uk/api/telemetry" in TELEMETRY_SENTENCE
    assert main(["doctor"]) == EXIT_OK
    doctor_out = capsys.readouterr().out
    assert "run's telemetry POST" in doctor_out and "egress.telemetry: false" in doctor_out
    assert main(["doctor", "--offline"]) == EXIT_OK
    assert "skipped (--offline)" in capsys.readouterr().out
