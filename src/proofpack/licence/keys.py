"""The licence-verification public keys the engine ships (D1 section 7).

Two lookups, the same bytes:

* :data:`SHIPPED_PUBLIC_KEY_B64` - the key embedded in this package, read from
  ``proofpack-site/keys/licence_pub.b64`` (key id from ``keys/licence_pub.json``,
  ``status: live``) on 21 September 2026. It is decoded **once, at import**, with the
  canonical-spelling check below, and every comparison downstream is on the 32 decoded
  bytes, never on the base64 string (the day-4 site lesson in
  ``proofpack-site/scripts/lib/key-check.mjs``: base64 is not a canonical encoding, and the
  same 32 bytes have at least four spellings - canonical, base64url, unpadded, and
  non-canonical trailing bits - of which Node's ``atob`` and Python's ``b64decode`` accept
  different subsets).
* :data:`PUBLISHED_PUBLIC_KEY_B64` - the copy published on
  ``https://proofpack.globalphoenix.co.uk/trust`` ("Public key (base64, raw 32 bytes)",
  key id ``pp-2026-09``, status live; read there on 21 September 2026). **The engine never
  fetches it**: it is recorded here so a customer can compare the published key with the
  shipped one by eye, and verify a ``.lic`` independently with the site's ten-line
  ``scripts/verify_licence.py`` (the reference verifier; ``tests/test_licence.py`` runs it
  in a subprocess on the same file and asserts both agree). An import-time assertion keeps
  the two literals equal, so a key rotation has to change both or the package fails to
  import.

No private key exists anywhere in this repository. The signing seed lives only in the
site's Cloudflare secret ``LICENCE_SIGNING_KEY``; tests sign with an ephemeral key pair
they generate and register through :class:`KeyRegistry` (a named parameter of
``verify``), never by rebinding the shipped constant.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field

#: keys/licence_pub.b64 (site repository), status live, 21 September 2026.
SHIPPED_PUBLIC_KEY_B64 = "XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA="
#: keys/licence_pub.json ``key_id``; the site's issuer writes it into every payload.
SHIPPED_KEY_ID = "pp-2026-09"
#: The /trust page's copy of the same key (the customer's independent check).
PUBLISHED_PUBLIC_KEY_B64 = "XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA="

ED25519_PUBLIC_KEY_BYTES = 32


class Base64Error(ValueError):
    """A base64 string that is not the canonical spelling of some bytes."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def decode_canonical_base64(s: str) -> bytes:
    """Decode ``s`` and require that re-encoding the bytes gives ``s`` back.

    Rejects with a typed reason: ``base64_invalid`` (characters outside the standard
    alphabet, so base64url ``-`` / ``_``; or a length that cannot be padded, so an
    unpadded spelling) and ``base64_not_canonical`` (decodes, but re-encodes to a
    different string: non-zero unused trailing bits, as in ``...MAB=`` for ``...MAA=``).
    """
    if not isinstance(s, str) or not s:
        raise Base64Error("base64_invalid")
    try:
        raw = base64.b64decode(s.encode("ascii"), validate=True)
    except (binascii.Error, ValueError, UnicodeEncodeError):
        raise Base64Error("base64_invalid") from None
    if base64.b64encode(raw).decode("ascii") != s:
        raise Base64Error("base64_not_canonical")
    return raw


def _public_key_bytes(b64: str) -> bytes:
    raw = decode_canonical_base64(b64)
    if len(raw) != ED25519_PUBLIC_KEY_BYTES:
        raise ValueError("an Ed25519 public key is 32 raw bytes")
    return raw


#: The shipped key as bytes, decoded once at import; comparisons are on these.
SHIPPED_PUBLIC_KEY: bytes = _public_key_bytes(SHIPPED_PUBLIC_KEY_B64)
PUBLISHED_PUBLIC_KEY: bytes = _public_key_bytes(PUBLISHED_PUBLIC_KEY_B64)
if SHIPPED_PUBLIC_KEY != PUBLISHED_PUBLIC_KEY:  # pragma: no cover - import-time guard
    raise ImportError("the shipped and published licence keys differ; rotate both together")


@dataclass(frozen=True)
class KeyRegistry:
    """``key_id`` -> raw 32-byte public key. The shipped registry holds one entry."""

    keys: dict[str, bytes] = field(default_factory=dict)

    def lookup(self, key_id: str) -> bytes | None:
        return self.keys.get(key_id)

    @classmethod
    def shipped(cls) -> KeyRegistry:
        return cls({SHIPPED_KEY_ID: SHIPPED_PUBLIC_KEY})

    @classmethod
    def of(cls, key_id: str, public_key: bytes) -> KeyRegistry:
        """A registry for one key given as bytes (tests: an ephemeral pair)."""
        if len(public_key) != ED25519_PUBLIC_KEY_BYTES:
            raise ValueError("an Ed25519 public key is 32 raw bytes")
        return cls({key_id: bytes(public_key)})
