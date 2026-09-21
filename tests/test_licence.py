"""Build day 7 (E7): ``proofpack.licence`` - Ed25519 verification, F20, install and show.

No production private key exists in tests: ``conftest`` generates an ephemeral pair once
per session and every signed file here is verified against it through the ``registry``
parameter (``KeyRegistry.of``). One test verifies an ephemeral-signed file against the
SHIPPED registry and asserts ``refused``; one test hands the same file, and the ephemeral
public key, to the site's reference verifier ``scripts/verify_licence.py`` in a
subprocess and asserts the two verifiers agree on the file (both accept it) and on a
tampered copy (both refuse it).

The four base64 spellings of the key-check lesson (``proofpack-site/scripts/lib/
key-check.mjs``) are fed to the segment decoder: canonical accepted, base64url,
unpadded and trailing-bit spellings refused with their own reason codes.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from conftest import (
    TEST_KEY_ID,
    TEST_PUBLIC_KEY,
    TEST_PUBLIC_KEY_B64,
    ephemeral_registry,
    iso_utc,
    licence_payload,
    sign_licence,
    write_licence,
)
from proofpack import licence as licence_mod
from proofpack.cli import main
from proofpack.errors import EXIT_LICENCE, EXIT_OK
from proofpack.licence import keys as keys_mod
from proofpack.licence.keys import Base64Error, KeyRegistry, decode_canonical_base64
from proofpack.licence.verify import (
    CLOCK_SKEW,
    REASON_CODES,
    STATUSES,
    TRIAL_DAYS,
    WATERMARK_EXPIRED,
    WATERMARK_TRIAL,
    verify,
)

pytestmark = pytest.mark.day7

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
SITE_VERIFIER = Path("C:/Users/joshs/GPS/ProofPack/proofpack-site/scripts/verify_licence.py")


def _verify(text: str, now=NOW, registry=None):
    return verify(text.encode("ascii"), now=now, registry=registry or ephemeral_registry())


# ------------------------------------------------------------------------ the keys


def test_the_shipped_key_is_the_site_s_live_key_by_bytes_and_the_published_copy_is_the_same():
    assert keys_mod.SHIPPED_PUBLIC_KEY_B64 == "XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA="
    assert keys_mod.SHIPPED_KEY_ID == "pp-2026-09"
    assert len(keys_mod.SHIPPED_PUBLIC_KEY) == 32
    assert (
        keys_mod.SHIPPED_PUBLIC_KEY.hex()
        == "5d82e76854675953ac2e86f04a691ba3fab2dfb6a73b36be691a6e9f39ab3000"
    )
    assert keys_mod.PUBLISHED_PUBLIC_KEY == keys_mod.SHIPPED_PUBLIC_KEY
    site = Path("C:/Users/joshs/GPS/ProofPack/proofpack-site/keys")
    if (site / "licence_pub.b64").exists():  # the sibling checkout on the build machine
        lines = [
            ln.strip() for ln in (site / "licence_pub.b64").read_text(encoding="utf-8").splitlines()
        ]
        body = [ln for ln in lines if ln and not ln.startswith("#")]
        assert body == [keys_mod.SHIPPED_PUBLIC_KEY_B64]
        meta = json.loads((site / "licence_pub.json").read_text(encoding="utf-8"))
        assert (meta["key_id"], meta["status"], meta["public_key"]) == (
            keys_mod.SHIPPED_KEY_ID,
            "live",
            keys_mod.SHIPPED_PUBLIC_KEY_B64,
        )
    reg = KeyRegistry.shipped()
    assert reg.lookup("pp-2026-09") == keys_mod.SHIPPED_PUBLIC_KEY
    assert reg.lookup(TEST_KEY_ID) is None


def test_no_private_key_material_is_in_the_package():
    src = Path(__file__).resolve().parent.parent / "src" / "proofpack"
    for py in src.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        assert "PRIVATE KEY" not in text and "Ed25519PrivateKey" not in text, py
        assert "-----BEGIN" not in text and "importSigningKey" not in text, py


@pytest.mark.parametrize(
    "spelling, reason",
    [
        ("XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA=", None),  # canonical
        ("XYLnaFRnWVOsLobwSmkbo_qy37anOza-aRpunzmrMAA=", "base64_invalid"),  # base64url
        ("XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAA", "base64_invalid"),  # unpadded
        ("XYLnaFRnWVOsLobwSmkbo/qy37anOza+aRpunzmrMAB=", "base64_not_canonical"),  # bits
        ("", "base64_invalid"),
        ("not base64!", "base64_invalid"),
    ],
)
def test_the_four_spellings_of_the_key_check_lesson(spelling, reason):
    if reason is None:
        assert decode_canonical_base64(spelling) == keys_mod.SHIPPED_PUBLIC_KEY
        return
    with pytest.raises(Base64Error) as ei:
        decode_canonical_base64(spelling)
    assert ei.value.reason == reason


# ------------------------------------------------------------------------ F20


def _lic(**kw) -> str:
    return sign_licence(licence_payload(**kw))


def _tampered() -> str:
    text = _lic()
    seg, sig = text.split(".")
    payload = json.loads(base64.b64decode(seg))
    payload["tier"] = "annual"
    payload["expires"] = "2099-01-01T00:00:00Z"
    seg2 = base64.b64encode(json.dumps(payload).encode()).decode()
    return seg2 + "." + sig


def _wrong_key() -> str:
    # signed by the ephemeral key but claiming the shipped key id: verified against the
    # SHIPPED registry it is an invalid signature
    return sign_licence(licence_payload(key_id=keys_mod.SHIPPED_KEY_ID))


F20_CASES = [
    ("valid_annual", _lic(), None, "ok", "valid", None),
    ("valid_quarterly", _lic(tier="quarterly"), None, "ok", "valid", None),
    ("trial", _lic(tier="trial", issued=NOW - timedelta(days=3)), None, "ok", "valid", "TRIAL"),
    (
        "expired_within_grace",
        _lic(expires=NOW - timedelta(days=10)),
        None,
        "grace",
        "expired_within_grace",
        WATERMARK_EXPIRED,
    ),
    (
        "expired_past_grace",
        _lic(expires=NOW - timedelta(days=40)),
        None,
        "expired",
        "expired_past_grace",
        WATERMARK_EXPIRED,
    ),
    ("tampered_payload", _tampered(), None, "refused", "signature_invalid", None),
    ("wrong_key", _wrong_key(), KeyRegistry.shipped(), "refused", "signature_invalid", None),
    ("unknown_key_id", _lic(), KeyRegistry.shipped(), "refused", "unknown_key_id", None),
]


@pytest.mark.parametrize("name, text, registry, status, reason, mark", F20_CASES)
def test_f20(name, text, registry, status, reason, mark):
    r = _verify(text, registry=registry)
    assert (r.status, r.reason_code, r.watermark) == (status, reason, mark), name
    assert r.usable is (status in ("ok", "grace"))
    if status == "refused":
        assert r.payload is None and r.licence_id is None
    else:
        assert r.payload["licence_id"].startswith("lic_") and r.key_id == TEST_KEY_ID


def test_the_ephemeral_key_against_the_shipped_registry_is_refused_however_spelled():
    r = verify(_lic().encode(), now=NOW)  # the default registry: shipped
    assert r.status == "refused" and r.reason_code == "unknown_key_id"
    r = verify(_wrong_key().encode(), now=NOW)
    assert r.status == "refused" and r.reason_code == "signature_invalid"
    assert r.key_id == keys_mod.SHIPPED_KEY_ID


# -------------------------------------------------------------- malformed input, no raise


@pytest.mark.parametrize(
    "text, reason",
    [
        ("", "not_two_segments"),
        ("abc", "not_two_segments"),
        ("a.b.c", "not_two_segments"),
        (".", "not_two_segments"),
        ("!!!!.AAAA", "base64_invalid"),
        (base64.b64encode(b"[]").decode() + ".AAAA", "payload_not_json_object"),
        (base64.b64encode(b"{not json").decode() + ".AAAA", "payload_not_json_object"),
        (base64.b64encode(b"\xff\xfe").decode() + ".AAAA", "payload_not_json_object"),
    ],
)
def test_malformed_files_are_refused_with_a_typed_reason_and_nothing_raises(text, reason):
    r = _verify(text)
    assert (r.status, r.reason_code) == ("refused", reason), text


def test_missing_or_mistyped_fields_are_refused_naming_the_field():
    for field in ("licence_id", "licensee", "tier", "issued", "expires", "grace_days", "key_id"):
        payload = licence_payload()
        del payload[field]
        r = _verify(sign_licence(payload))
        assert (r.status, r.reason_code, r.detail) == ("refused", "missing_field", {"field": field})
    payload = licence_payload(grace_days="30")
    r = _verify(sign_licence(payload))
    assert r.reason_code == "missing_field" and r.detail == {"field": "grace_days"}
    payload = licence_payload(grace_days=True)
    assert _verify(sign_licence(payload)).reason_code == "missing_field"
    assert _verify(sign_licence(licence_payload(tier="lifetime"))).reason_code == "unknown_tier"
    for bad in ("2026-13-01T00:00:00Z", "yesterday", "2026-10-01"):
        r = _verify(sign_licence(licence_payload(expires=None, **{})).replace("", ""))
        payload = licence_payload()
        payload["expires"] = bad
        r = _verify(sign_licence(payload))
        assert r.reason_code == "expires_unparsable", bad


def test_random_and_hostile_bytes_never_raise():
    import random

    rng = random.Random(7)
    for _ in range(300):
        blob = bytes(rng.getrandbits(8) for _ in range(rng.randrange(0, 200)))
        r = verify(blob, now=NOW, registry=ephemeral_registry())
        assert r.status == "refused" and r.reason_code in REASON_CODES
    seg, sig = _lic().split(".")
    for text in (seg + "." + sig[:-8], seg + "." + "A" * len(sig), seg[:-4] + "." + sig):
        r = _verify(text)
        assert r.status == "refused", text[:20]
    assert set(STATUSES) == {"ok", "grace", "expired", "refused"}


@pytest.mark.parametrize(
    "field, extra",
    [
        ("grace_days", {"grace_days": 3_000_000}),
        ("grace_days", {"grace_days": 10**9}),
        ("expires", {"expires": "9999-12-31T23:59:59Z"}),
        ("expires", {"expires": "0001-01-01T00:00:00+05:00"}),
        ("issued", {"tier": "trial", "issued": "9999-12-31T00:00:00Z"}),
    ],
)
def test_extreme_dates_and_grace_days_are_refused_expires_unparsable(field, extra):
    """Lens 1 of 21 September, FA-N3: at ab729d3 each of these signed payloads raised
    OverflowError out of verify() ('date value out of range', 'days=1000000000; must have
    magnitude <= 999999999', and the year-0 offset in parse_utc). Each is now refused
    expires_unparsable; the field is named except for the fourth, which parse_utc refuses
    (an offset carrying year 1 below the range) before any field is attributed."""
    payload = licence_payload()
    payload.update(extra)
    r = verify(sign_licence(payload).encode("ascii"), now=NOW, registry=ephemeral_registry())
    assert (r.status, r.reason_code) == ("refused", "expires_unparsable"), extra
    if extra.get("expires") == "0001-01-01T00:00:00+05:00":
        assert r.detail == {}
    else:
        assert r.detail == {"field": field}
    assert r.payload is None and r.watermark is None


def test_no_file_is_refused_no_file(tmp_path: Path):
    r = verify(tmp_path / "absent.lic", now=NOW, registry=ephemeral_registry())
    assert (r.status, r.reason_code) == ("refused", "no_file")


# ------------------------------------------------------------- the clock and the skew


def test_clock_skew_of_24_hours_on_expires():
    expires = NOW - timedelta(hours=23)
    assert _verify(_lic(expires=expires)).status == "ok"
    expires = NOW - timedelta(hours=25)
    r = _verify(_lic(expires=expires))
    assert r.status == "grace" and r.days_left == -2
    # the skew is added at the grace end too
    assert _verify(_lic(expires=NOW - CLOCK_SKEW - timedelta(days=30, hours=-1))).status == "grace"
    assert _verify(_lic(expires=NOW - CLOCK_SKEW - timedelta(days=30, hours=1))).status == (
        "expired"
    )


def test_days_left_counts_whole_days_to_the_effective_expiry():
    assert _verify(_lic(expires=NOW + timedelta(days=10, hours=5))).days_left == 10
    assert _verify(_lic(expires=NOW + timedelta(hours=5))).days_left == 0
    assert _verify(_lic(expires=NOW - timedelta(days=3))).days_left == -3


def test_a_trial_expires_after_thirty_days_from_issue_whatever_the_payload_says():
    issued = NOW - timedelta(days=32)
    # the issuer's expires is a year away, the engine's 30-day rule applies (D1 section 7;
    # the "or until first full pack" half is E9's); 32 days ago puts the effective expiry
    # two days back, past the 24 h skew
    r = _verify(_lic(tier="trial", issued=issued, expires=issued + timedelta(days=365)))
    assert r.status == "grace" and r.watermark == WATERMARK_EXPIRED and r.days_left == -2
    # 31 days ago is one day past, inside the skew: still ok, still TRIAL
    issued = NOW - timedelta(days=31)
    r = _verify(_lic(tier="trial", issued=issued, expires=issued + timedelta(days=365)))
    assert r.status == "ok" and r.watermark == WATERMARK_TRIAL and r.days_left == -1
    r = _verify(_lic(tier="trial", issued=NOW - timedelta(days=29)))
    assert r.status == "ok" and r.watermark == WATERMARK_TRIAL and r.days_left == 1
    # a payload expiry earlier than 30 days wins
    r = _verify(_lic(tier="trial", issued=NOW - timedelta(days=5), expires=NOW - timedelta(days=2)))
    assert r.status == "grace"
    assert TRIAL_DAYS == 30


def test_a_zero_grace_period_expires_at_the_skew_edge():
    r = _verify(_lic(expires=NOW - timedelta(hours=25), grace_days=0))
    assert r.status == "expired"


# ----------------------------------------------------------- agreement with the site


@pytest.mark.skipif(not SITE_VERIFIER.exists(), reason="site checkout not beside the engine")
def test_the_site_reference_verifier_agrees_on_the_same_file(tmp_path: Path):
    key_file = tmp_path / "pub.b64"
    key_file.write_text(TEST_PUBLIC_KEY_B64 + "\n", encoding="ascii")
    good = tmp_path / "good.lic"
    good.write_text(_lic(), encoding="ascii")
    bad = tmp_path / "bad.lic"
    bad.write_text(_tampered(), encoding="ascii")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for path, expect_ok in ((good, True), (bad, False)):
        proc = subprocess.run(
            [sys.executable, str(SITE_VERIFIER), str(path), str(key_file)],
            capture_output=True,
            text=True,
            env=env,
        )
        ours = verify(path, now=NOW, registry=ephemeral_registry())
        assert (proc.returncode == 0) is expect_ok, proc.stderr
        assert (ours.status != "refused") is expect_ok
        if expect_ok:
            assert "signature OK" in proc.stdout
            printed = json.loads(proc.stdout.split("signature OK", 1)[1])
            assert printed == ours.payload
        else:
            assert "InvalidSignature" in proc.stderr and ours.reason_code == "signature_invalid"


# ---------------------------------------------------------------------- the CLI


def test_import_proofpack_with_cryptography_hidden_still_imports():
    code = (
        "import sys; sys.modules['cryptography'] = None; "
        "sys.modules['cryptography.hazmat'] = None; "
        "sys.modules['cryptography.hazmat.primitives'] = None; "
        "import proofpack, proofpack.licence, proofpack.cli, proofpack.run; "
        "from proofpack.licence import verify; "
        "r = verify(b'abc'); print(r.status, r.reason_code); "
        "r = verify(sys.argv[1].encode()); print(r.status, r.reason_code)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, _lic(key_id=keys_mod.SHIPPED_KEY_ID)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == "refused not_two_segments"
    assert lines[1] == "refused cryptography_unavailable"


def test_licence_verify_install_and_show_through_the_cli(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    reg = ephemeral_registry()
    good = write_licence(tmp_path / "good.lic")
    bad = write_licence(tmp_path / "bad.lic", tier="annual")
    bad.write_text(_tampered(), encoding="ascii")
    # show: nothing installed
    assert main(["licence", "show"], registry=reg) == EXIT_LICENCE
    out = capsys.readouterr().out
    assert "licence: none found" in out and "refused (no_file)" in out
    assert "licence install FILE" in out and "/docs/licence" in out
    # verify the good file: exit 0 and the fields, no signature
    assert main(["licence", "verify", str(good)], registry=reg) == EXIT_OK
    out = capsys.readouterr().out
    assert "status: ok (valid)" in out and "tier: annual" in out and "watermark: None" in out
    assert good.read_text().split(".")[1] not in out
    # verify the tampered file: exit 4
    assert main(["licence", "verify", str(bad)], registry=reg) == EXIT_LICENCE
    assert "signature_invalid" in capsys.readouterr().out
    # install the tampered file: refused, nothing copied
    assert main(["licence", "install", str(bad)], registry=reg) == EXIT_LICENCE
    assert not (home / "proofpack.lic").exists()
    assert "not installed" in capsys.readouterr().out
    # install the good file: copied byte for byte to the per-user location
    assert main(["licence", "install", str(good)], registry=reg) == EXIT_OK
    assert (home / "proofpack.lic").read_bytes() == good.read_bytes()
    assert str(home / "proofpack.lic") in capsys.readouterr().out
    # show now reads it
    assert main(["licence", "show"], registry=reg) == EXIT_OK
    out = capsys.readouterr().out
    assert "status: ok (valid)" in out and "expires: 2027-09-01T00:00:00Z" in out
    # json-log carries the same dict, without the signature
    assert main(["--json-log", "licence", "show"], registry=reg) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["licence"]["status"] == "ok" and "signature" not in json.dumps(payload)
    # against the shipped key (no registry) the same installed file is refused
    assert main(["licence", "show"]) == EXIT_LICENCE
    assert "unknown_key_id" in capsys.readouterr().out
    # PROOFPACK_LICENCE points elsewhere and wins
    monkeypatch.setenv("PROOFPACK_LICENCE", str(bad))
    assert licence_mod.installed_path() == bad
    assert main(["licence", "show"], registry=reg) == EXIT_LICENCE


def test_installed_path_order(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    monkeypatch.delenv("PROOFPACK_LICENCE", raising=False)
    monkeypatch.chdir(tmp_path)
    assert licence_mod.installed_path() is None
    cwd_file = write_licence(tmp_path / "proofpack.lic")
    assert licence_mod.installed_path() == cwd_file
    home.mkdir()
    write_licence(home / "proofpack.lic")
    assert licence_mod.installed_path() == home / "proofpack.lic"


def test_show_prints_the_grace_watermark_and_exits_0(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("PROOFPACK_HOME", str(home))
    write_licence(home / "proofpack.lic", expires=datetime.now(UTC) - timedelta(days=5))
    assert main(["licence", "show"], registry=ephemeral_registry()) == EXIT_OK
    out = capsys.readouterr().out
    assert "status: grace (expired_within_grace)" in out and WATERMARK_EXPIRED in out
    assert iso_utc(datetime(2026, 1, 1, tzinfo=UTC)) == "2026-01-01T00:00:00Z"
    assert len(TEST_PUBLIC_KEY) == 32
