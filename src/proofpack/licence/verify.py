"""``licence.verify`` - Ed25519 verification of a ``proofpack.lic`` file (D1 section 7).

File format (D1 section 7; the site's ``functions/_lib/licence.mjs`` issues it):
``base64(JSON payload) "." base64(Ed25519 signature)``, the signature over the **ASCII
bytes of the first segment** as written, not over re-serialised JSON. Payload:
``{licence_id, licensee, company_no, tier: trial|quarterly|annual, models, features,
issued, expires, grace_days, key_id}``; ``issued`` and ``expires`` are ISO-8601 UTC to the
second with a ``Z`` (``isoUtc`` in the issuer).

:func:`verify` **raises nothing on bad input**. Every outcome is a :class:`LicenceResult`
with a status from :data:`STATUSES` and a reason from :data:`REASON_CODES`:

* ``refused`` - the file cannot be trusted: not exactly two dot-separated segments; a
  segment that is not canonical base64 (base64url, unpadded and trailing-bit spellings are
  refused, not canonicalised - the four spellings are in ``tests/test_licence.py``); a
  payload that is not a JSON object; a required field missing or of the wrong type; a
  ``key_id`` the registry does not hold; ``cryptography``'s ``InvalidSignature``;
  ``expires`` or ``issued`` unparsable; ``cryptography`` not importable.
* ``ok`` - the signature verifies and ``now <= expires + 24 h`` (the clock-skew tolerance,
  D1 section 7, applied on the customer's side only: a licence is never refused for a
  clock up to a day behind the issuer's). A trial's effective expiry is the earlier of the
  payload's ``expires`` and ``issued + 30 days`` (D1 section 7: "30 days or until first full
  pack rendered" - the pack half is the renderer's, E9, and is not enforced here).
  ``watermark`` is ``TRIAL`` for ``tier: trial`` and ``None`` otherwise.
* ``grace`` - past the effective expiry (plus skew) but within ``grace_days`` of it;
  ``watermark`` is ``LICENCE EXPIRED - not for submission`` (D4 section 3 footer; the
  ASCII hyphen, DEC-01's rule for every printed mark).
* ``expired`` - past the grace period; the same watermark. What a run does with each
  status is ``cli.cmd_run``'s (D1 section 7: after grace, ``run`` / ``compare`` emit JSON
  only; ``doctor`` / ``map`` / ``fixtures`` always work).

``days_left`` is the whole days from ``now`` to the effective expiry (negative once
past it). The signature bytes are never in the result and never printed.

``cryptography`` is imported inside :func:`verify` so ``import proofpack`` and every
command that does not verify a licence work without it (``tests/test_licence.py`` hides
the module and imports the package).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from proofpack.licence.keys import Base64Error, KeyRegistry, decode_canonical_base64

STATUSES: tuple[str, ...] = ("ok", "grace", "expired", "refused")
TIERS: tuple[str, ...] = ("trial", "quarterly", "annual")
WATERMARK_TRIAL = "TRIAL"
WATERMARK_EXPIRED = "LICENCE EXPIRED - not for submission"
CLOCK_SKEW = timedelta(hours=24)
TRIAL_DAYS = 30

REASON_CODES: dict[str, str] = {
    "valid": "signature verifies and the licence is within its period",
    "expired_within_grace": "past expiry, within grace_days: packs carry the expired watermark",
    "expired_past_grace": "past expiry and past grace_days",
    "no_file": "no licence file at the path given or installed",
    "not_two_segments": "the file is not exactly base64(payload).base64(signature)",
    "base64_invalid": "a segment is not standard base64 (base64url or unpadded spelling)",
    "base64_not_canonical": "a segment re-encodes to a different string (trailing bits)",
    "payload_not_json_object": "the payload segment does not decode to a JSON object",
    "missing_field": "a required payload field is absent or of the wrong type (detail.field)",
    "unknown_tier": "tier is not trial, quarterly or annual",
    "unknown_key_id": "the payload's key_id is not a key this engine ships",
    "signature_invalid": "the Ed25519 signature does not verify against the key_id's key",
    "expires_unparsable": "expires or issued is not an ISO-8601 UTC timestamp",
    "cryptography_unavailable": "the cryptography package is not installed",
}

REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "licence_id": str,
    "licensee": str,
    "tier": str,
    "issued": str,
    "expires": str,
    "grace_days": int,
    "key_id": str,
}


@dataclass(frozen=True)
class LicenceResult:
    status: str
    reason_code: str
    payload: dict[str, Any] | None = None
    key_id: str | None = None
    days_left: int | None = None
    watermark: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def licence_id(self) -> str | None:
        return None if self.payload is None else self.payload.get("licence_id")

    @property
    def tier(self) -> str | None:
        return None if self.payload is None else self.payload.get("tier")

    @property
    def expires(self) -> str | None:
        return None if self.payload is None else self.payload.get("expires")

    @property
    def usable(self) -> bool:
        """``ok`` or ``grace``: a full run is licensed."""
        return self.status in ("ok", "grace")

    def as_dict(self) -> dict[str, Any]:
        """For ``licence show`` / ``verify`` output: no signature, no key bytes."""
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "licence_id": self.licence_id,
            "licensee": None if self.payload is None else self.payload.get("licensee"),
            "tier": self.tier,
            "expires": self.expires,
            "days_left": self.days_left,
            "watermark": self.watermark,
            "key_id": self.key_id,
            "detail": dict(self.detail),
        }


def _refused(reason: str, **detail: Any) -> LicenceResult:
    return LicenceResult("refused", reason, detail=detail)


def parse_utc(value: Any) -> datetime | None:
    """``YYYY-MM-DDTHH:MM:SSZ`` (the issuer's ``isoUtc``) or any ISO-8601 with an offset."""
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(UTC)


def verify(
    source: str | Path | bytes,
    *,
    now: datetime | None = None,
    registry: KeyRegistry | None = None,
) -> LicenceResult:
    """Verify a licence file (a path) or its bytes. Raises nothing on bad input."""
    registry = registry if registry is not None else KeyRegistry.shipped()
    now = (now if now is not None else datetime.now(UTC)).astimezone(UTC)
    if isinstance(source, bytes | bytearray):
        raw = bytes(source)
    else:
        path = Path(source)
        try:
            raw = path.read_bytes()
        except OSError:
            return _refused("no_file")
    try:
        text = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        return _refused("base64_invalid")
    segments = text.split(".")
    if len(segments) != 2 or not all(segments):
        return _refused("not_two_segments", segments=len(segments))
    segment, sig_b64 = segments
    try:
        payload_bytes = decode_canonical_base64(segment)
        signature = decode_canonical_base64(sig_b64)
    except Base64Error as exc:
        return _refused(exc.reason)
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _refused("payload_not_json_object")
    if not isinstance(payload, dict):
        return _refused("payload_not_json_object")
    for name, typ in REQUIRED_FIELDS.items():
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, typ):
            return _refused("missing_field", field=name)
    if payload["tier"] not in TIERS:
        return _refused("unknown_tier")
    if payload["grace_days"] < 0:
        return _refused("missing_field", field="grace_days")
    key_id = payload["key_id"]
    public_key = registry.lookup(key_id)
    if public_key is None:
        return _refused("unknown_key_id", key_id=key_id[:32])
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        return _refused("cryptography_unavailable")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, segment.encode("ascii"))
    except InvalidSignature:
        return LicenceResult("refused", "signature_invalid", key_id=key_id)
    except ValueError:
        # a signature of the wrong length; cryptography raises ValueError, not InvalidSignature
        return LicenceResult("refused", "signature_invalid", key_id=key_id)
    expires = parse_utc(payload["expires"])
    issued = parse_utc(payload["issued"])
    if expires is None or issued is None:
        return LicenceResult("refused", "expires_unparsable", key_id=key_id)
    effective = expires
    if payload["tier"] == "trial":
        effective = min(expires, issued + timedelta(days=TRIAL_DAYS))
    grace_end = effective + timedelta(days=int(payload["grace_days"]))
    days_left = (effective - now) // timedelta(days=1)
    if now <= effective + CLOCK_SKEW:
        mark = WATERMARK_TRIAL if payload["tier"] == "trial" else None
        return LicenceResult("ok", "valid", payload, key_id, int(days_left), mark)
    if now <= grace_end + CLOCK_SKEW:
        return LicenceResult(
            "grace", "expired_within_grace", payload, key_id, int(days_left), WATERMARK_EXPIRED
        )
    return LicenceResult(
        "expired", "expired_past_grace", payload, key_id, int(days_left), WATERMARK_EXPIRED
    )
