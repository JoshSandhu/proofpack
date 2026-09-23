"""Egress (build day 8, A-P2; D1 section 6): what may leave the customer's machine.

Four rules, one module each, all applied before anything is serialised:

- :mod:`.suppress` - k-suppression: any cell with ``n < min_n``, ``events < min_events``
  or ``non-events < min_nonevents`` is serialised with ``suppressed: true`` and null
  values. Defaults 10 / 5 / 5 from ``criteria.yaml``'s ``egress.suppression``, which a
  customer may only tighten (a looser value is H08).
- :mod:`.pseudonymise` - ``site``, ``device``, ``protocol`` and every ``attr_*`` level
  become ``Site A``, ``Device A``, ``Level A`` ... in a documented order; the map is
  written to ``<out>/pseudonyms.json`` locally and is never part of a payload.
- :mod:`.whitelist` - a document is projected onto ``schema/egress_schema.json``'s keys:
  a key the schema does not name is dropped, a string the schema does not constrain is
  refused, and every string must match its enum, const or pattern.
- :mod:`.build` - :func:`~proofpack.egress.build.build_payload` (the telemetry document,
  D1 section 6's literal payload) and :func:`~proofpack.egress.build.build_aggregates`
  (the ``proofpack-aggregates/1`` document no code path sends at launch), each validated
  with ``jsonschema`` before it is returned; a failure is a typed error, never a send.

:mod:`.telemetry` sends the one document the runner ever sends, and only when neither
``--offline`` nor ``egress.telemetry: false`` is in force. :func:`run_telemetry` is the
single call site's helper (``proofpack.cli.cmd_run``, after ``run.json`` is written).
"""

from __future__ import annotations

from proofpack.egress.build import (
    EgressError,
    build_aggregates,
    build_payload,
    manifest_sha256,
    row_count_bucket,
)
from proofpack.egress.pseudonymise import PSEUDONYMS_JSON, build_map, pseudonyms_document
from proofpack.egress.suppress import DEFAULT_THRESHOLDS, Thresholds, thresholds_from_declarations
from proofpack.egress.telemetry import (
    TELEMETRY_URL,
    TIMEOUT_S,
    SendResult,
    run_telemetry,
    send,
    telemetry_enabled,
)
from proofpack.egress.whitelist import WhitelistError, project

__all__ = [
    "DEFAULT_THRESHOLDS",
    "PSEUDONYMS_JSON",
    "TELEMETRY_URL",
    "TIMEOUT_S",
    "EgressError",
    "SendResult",
    "Thresholds",
    "WhitelistError",
    "build_aggregates",
    "build_map",
    "build_payload",
    "manifest_sha256",
    "project",
    "pseudonyms_document",
    "row_count_bucket",
    "run_telemetry",
    "send",
    "telemetry_enabled",
    "thresholds_from_declarations",
]
