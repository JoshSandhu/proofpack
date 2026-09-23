"""The telemetry POST (D1 section 6): *at launch the runner makes at most one outbound
call*, this one, and *``--offline`` = zero sockets* skips it entirely.

:data:`TELEMETRY_URL` is the one endpoint, ``https://proofpack.globalphoenix.co.uk/api/
telemetry`` (the site's Pages Function of the same build day, which stores the ten keys in
its ``runs`` table and answers 204). It is a constant, not a setting: ``proofpack.cli.
cmd_run`` passes no url and reads no environment variable for one; a customer who must
not reach it runs ``--offline`` or declares ``egress.telemetry: false``. :func:`send` and
:func:`run_telemetry` take a ``url`` parameter, which the loopback tests use
(``tests/test_telemetry.py``); the CLI never fills it.

:func:`send` makes **one HTTP request** with a **5 s timeout** through
:func:`urllib_transport` (the standard library; ``urllib.request`` is imported inside the
function, so an ``--offline`` process never imports a network module). A 3xx answer is
**not followed**: the opener's redirect handler returns ``None``, so a 301/302/303/307/308
is reported as ``http_error`` with that status and no second request is made
(``test_a_redirect_answer_is_not_followed_and_the_location_host_receives_nothing``: five
codes against two loopback listeners, the second listener receives nothing). ``send``
**never raises an** ``Exception`` to the caller (a ``BaseException`` passes through:
``tests/conftest.py`` relies on that to trap a reach for the real transport): the result
is a :class:`SendResult` - ``sent`` with the HTTP status, or not sent with one of
:data:`REASON_CODES`. The caller prints one line (``[W16]``, ``errors.WARN_CODES``) and
nothing else changes: the exit code is the run's, ``run.json`` was written before the
call and is not touched by it (``tests/test_telemetry.py`` hashes it before and after).

:func:`run_telemetry` is what the single call site (``proofpack.cli.cmd_run``, after
``write_run``) calls: it short-circuits **before building anything** when ``--offline`` is
set or ``egress.telemetry`` is false (no document is built, no socket, no name lookup),
otherwise it builds the payload (:func:`~proofpack.egress.build.build_payload`) and sends.

Inside :func:`send` the payload is projected through the whitelist
(:func:`~proofpack.egress.whitelist.project`, ``re.fullmatch`` on every pattern) and
validated against ``$defs/telemetry`` a second time, so a caller that hands it a document
the schema does not admit - including a string with a trailing newline, which
``jsonschema``'s ``$`` accepts and the site's ``RegExp`` refuses
(``test_send_refuses_a_trailing_newline_in_licence_id_and_platform``) - gets
``payload_invalid`` and no bytes leave.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from proofpack.egress import whitelist
from proofpack.egress.build import EgressError, _validate, build_payload, egress_schema

#: The one endpoint (see the module docstring). Also recorded in
#: ``schema/egress_schema.json`` ``x-proofpack.telemetry_url``; the tests hold them equal.
TELEMETRY_URL = "https://proofpack.globalphoenix.co.uk/api/telemetry"
#: One attempt, this long, including the name lookup and the TLS handshake.
TIMEOUT_S = 5.0
#: What the request says it is. No engine version here (the body carries it) and no
#: hostname or user name.
USER_AGENT = "proofpack-telemetry/1"
#: Closed set of reasons a send did not happen or did not succeed.
REASON_CODES = (
    "payload_invalid",  # the document failed the schema inside send(); nothing left
    "timeout",  # no answer within TIMEOUT_S
    "unreachable",  # name lookup or route failed (no network, DNS refused)
    "connection_refused",  # the host answered with a refusal
    "http_error",  # a status outside 2xx; ``status`` carries it
    "transport_error",  # any other exception from the transport
)
#: What one line of the W16 warning reads; the code itself lives in ``errors.WARN_CODES``.
W16 = "W16"

Transport = Callable[[str, bytes, float], int]


@dataclass(frozen=True)
class SendResult:
    sent: bool
    status: int | None = None
    reason_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"sent": self.sent, "status": self.status, "reason_code": self.reason_code}

    def line(self) -> str:
        """The one line the CLI prints for this result."""
        if self.sent:
            return f"telemetry sent (http {self.status}) to {TELEMETRY_URL}"
        detail = self.reason_code or "not_sent"
        if self.status is not None:
            detail = f"{detail}, http {self.status}"
        return f"[{W16}] telemetry not sent ({detail}); run.json and the exit code are unchanged"


def urllib_transport(url: str, body: bytes, timeout: float) -> int:
    """POST ``body`` as ``application/json`` to ``url``; returns the HTTP status. A 3xx
    answer is returned as that status, not followed (:class:`_NoRedirect`). Raises
    whatever ``urllib`` raises (``send`` classifies it). Imported lazily so that a
    process that never sends never imports ``urllib.request``."""
    import urllib.error  # noqa: PLC0415 - lazy by design (module docstring)
    import urllib.request  # noqa: PLC0415

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        """``build_opener`` puts this in place of the default redirect handler; returning
        ``None`` makes ``urllib`` raise ``HTTPError`` with the 3xx status instead of
        issuing a GET to the ``Location`` host."""

        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: PLR0913
            return None

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:  # noqa: S310 - https constant
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def classify(exc: BaseException) -> str:
    """Map a transport exception onto one of :data:`REASON_CODES`."""
    # ``socket`` is not imported here (no network module is imported anywhere under
    # src/proofpack at module level): ``socket.timeout`` is ``TimeoutError`` since Python
    # 3.10 and ``gaierror`` / ``herror`` are told apart by name.
    seen: set[int] = set()
    node: BaseException | None = exc
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        if isinstance(node, TimeoutError):
            return "timeout"
        if isinstance(node, ConnectionRefusedError):
            return "connection_refused"
        if type(node).__name__ in ("gaierror", "herror"):
            return "unreachable"
        if isinstance(node, OSError) and getattr(node, "errno", None) in (101, 113, 51, 65):
            return "unreachable"  # ENETUNREACH / EHOSTUNREACH (linux, macOS)
        reason = getattr(node, "reason", None)
        node = reason if isinstance(reason, BaseException) else node.__cause__
    if "timed out" in str(exc).lower():
        return "timeout"
    return "transport_error"


def send(
    payload: Mapping[str, Any],
    url: str = TELEMETRY_URL,
    transport: Transport | None = None,
    *,
    timeout: float = TIMEOUT_S,
) -> SendResult:
    """One HTTP request; never raises an ``Exception`` (module docstring)."""
    try:
        schema = egress_schema()
        projected = whitelist.project(payload, schema, schema["$defs"]["telemetry"])
        _validate("telemetry", payload, "telemetry")
    except (EgressError, whitelist.WhitelistError):
        return SendResult(False, None, "payload_invalid")
    if projected != dict(payload):  # the projection dropped a key the schema does not name
        return SendResult(False, None, "payload_invalid")
    body = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    fn = transport if transport is not None else urllib_transport
    try:
        status = int(fn(url, body, timeout))
    except Exception as exc:  # noqa: BLE001 - the contract is "never raises an Exception"
        return SendResult(False, None, classify(exc))
    if 200 <= status < 300:
        return SendResult(True, status, None)
    return SendResult(False, status, "http_error")


def telemetry_enabled(declarations: Mapping[str, Any] | None) -> bool:
    """``egress.telemetry`` of the declarations: opt-out (D1 section 6), so absent is on;
    only the boolean ``false`` turns it off."""
    egress = (declarations or {}).get("egress") or {}
    return egress.get("telemetry", True) is not False


def run_telemetry(
    document: Mapping[str, Any],
    *,
    offline: bool,
    licence_status: str | None = None,
    transport: Transport | None = None,
    url: str = TELEMETRY_URL,
) -> SendResult | None:
    """The single call site's helper. ``None`` when nothing was attempted (``--offline``
    or ``egress.telemetry: false`` - decided before any document is built); otherwise
    the :class:`SendResult`. A payload that fails to build is reported as not sent with
    ``payload_invalid`` rather than raised: the run is already written."""
    if offline or not telemetry_enabled(document.get("declarations")):
        return None
    try:
        payload = build_payload(document, licence_status=licence_status)
    except EgressError:
        return SendResult(False, None, "payload_invalid")
    return send(payload, url=url, transport=transport)
