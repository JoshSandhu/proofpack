"""Search egress bytes for a string in the forms it could take (build day 13, E13; F19).

F19 (D1 section 3.2) asks that a site name be "absent from every egress byte". A byte
search for the UTF-8 form alone misses the other spellings a serialiser or a transport
could give the same text, so :func:`find` looks for each needle

* in the raw bytes, as its UTF-8 bytes, its JSON-escaped form (``ensure_ascii``: ``ö``
  becomes ``\\u00f6``), its percent-encoded forms (``quote`` and ``quote_plus``) and its
  base64 forms at the three byte alignments a substring can take inside a longer
  base64 text;
* in four decoded views of the bytes: the UTF-8 text, the text percent-decoded
  (``unquote_plus``), every key and string value of the JSON document (when it parses),
  and every run of base64 characters of length 8 or more, decoded.

The comparison is case-insensitive (``casefold``) for needles of six characters or more.
A shorter needle (``S1``) is compared case-sensitively and not in the base64-decoded view:
64 hexadecimal characters of a SHA-256 are valid base64, and their 48 decoded bytes carry
a given two-byte string with probability about 47 / 65,536 per hash, so that view would
report chance matches.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import urllib.parse
from collections.abc import Iterator, Mapping
from typing import Any

#: Needles shorter than this are compared case-sensitively and not in the base64 view.
LONG_NEEDLE = 6
_B64_RUN = re.compile(rb"[A-Za-z0-9+/_-]{8,}={0,2}")


def encoded_forms(needle: str) -> dict[str, bytes]:
    """The byte strings ``needle`` could appear as inside a payload."""
    raw = needle.encode("utf-8")
    forms = {
        "utf8": raw,
        "json_ascii": json.dumps(needle, ensure_ascii=True)[1:-1].encode("ascii"),
        "json_utf8": json.dumps(needle, ensure_ascii=False)[1:-1].encode("utf-8"),
        "percent": urllib.parse.quote(needle, safe="").encode("ascii"),
        "percent_plus": urllib.parse.quote_plus(needle, safe="").encode("ascii"),
    }
    # base64 of the needle at offset 0, 1 and 2 inside a longer text: drop the output
    # characters that depend on the neighbouring bytes (the first one or two and the last
    # one or two) and keep the stable middle when it is at least four characters long
    for pad in range(3):
        enc = base64.b64encode(b"\0" * pad + raw)
        start = {0: 0, 1: 2, 2: 3}[pad]
        stable = enc[start:]
        # a last group holding one needle byte prints one stable character and three that
        # depend on what follows (or padding); two needle bytes print two and two
        drop = {0: 0, 1: 3, 2: 2}[(pad + len(raw)) % 3]
        stable = stable[: len(stable) - drop]
        if len(stable) >= 4:
            forms[f"base64_offset{pad}"] = stable
            forms[f"base64url_offset{pad}"] = stable.replace(b"+", b"-").replace(b"/", b"_")
    return forms


def _json_strings(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        for k, v in value.items():
            yield str(k)
            yield from _json_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _json_strings(v)
    elif isinstance(value, str):
        yield value


def _b64_decoded(data: bytes) -> str:
    out = []
    for m in _B64_RUN.finditer(data):
        chunk = m.group(0).rstrip(b"=")
        for alphabet in (None, b"-_"):
            try:
                text = chunk + b"=" * (-len(chunk) % 4)
                decoded = (
                    base64.b64decode(text, validate=False)
                    if alphabet is None
                    else base64.urlsafe_b64decode(text)
                )
            except (binascii.Error, ValueError):
                continue
            out.append(decoded.decode("utf-8", errors="ignore"))
    return "\n".join(out)


def decoded_views(data: bytes) -> dict[str, str]:
    """The four text views of ``data`` the module docstring lists."""
    text = data.decode("utf-8", errors="replace")
    views = {"text": text, "percent_decoded": urllib.parse.unquote_plus(text)}
    try:
        views["json_strings"] = "\n".join(_json_strings(json.loads(text)))
    except ValueError:
        views["json_strings"] = ""
    views["base64_decoded"] = _b64_decoded(data)
    return views


def find(payloads: Mapping[str, bytes], needles: Mapping[str, str]) -> list[dict[str, str]]:
    """Every place a needle was found: ``{"payload", "needle", "form"}`` per hit. An empty
    list means none of ``needles`` appears in any of ``payloads`` in any form above."""
    hits: list[dict[str, str]] = []
    for pname, data in payloads.items():
        lowered = data.lower()
        views = decoded_views(data)
        for nname, needle in needles.items():
            if not needle:
                continue
            long = len(needle) >= LONG_NEEDLE
            for form, enc in encoded_forms(needle).items():
                hay, probe = (lowered, enc.lower()) if long else (data, enc)
                if form.startswith("base64"):
                    hay, probe = data, enc  # base64 is case-sensitive
                if probe and probe in hay:
                    hits.append({"payload": pname, "needle": nname, "form": form})
            for vname, view in views.items():
                if vname == "base64_decoded" and not long:
                    continue
                hay_t, probe_t = (view.casefold(), needle.casefold()) if long else (view, needle)
                if probe_t in hay_t:
                    hits.append({"payload": pname, "needle": nname, "form": f"view:{vname}"})
    return hits
