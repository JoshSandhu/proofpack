"""Test infrastructure: seeded synthetic cohort factory and a valid declarations factory.

This is *test scaffolding only* - the F18 story-injecting generator is Day 7.
Every value is produced by a seeded numpy Generator; nothing is hand-typed.
"""

from __future__ import annotations

import base64
import copy
import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml


def make_cohort(
    seed: int = 20240101,
    n: int = 400,
    prevalence: float = 0.3,
    separation: float = 1.5,
    sites: int = 3,
    with_row_id: bool = True,
    with_case_id: bool = False,
    with_y_pred: bool = False,
    threshold: float = 0.5,
    positive: str = "1",
    negative: str = "0",
) -> dict[str, list[Any]]:
    """Seeded binary cohort with a probability-like score, sex, age, site columns.

    Scores are sigmoid(normal) shifted by ``separation`` for positives, so the
    declared orientation ``higher_is_positive`` is correct and AUROC is well above 0.5.
    """
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < prevalence).astype(int)
    z = rng.normal(0.0, 1.0, n) + separation * y - separation / 2
    score = 1.0 / (1.0 + np.exp(-z))
    cols: dict[str, list[Any]] = {}
    if with_row_id:
        cols["row_id"] = [f"r{i:06d}" for i in range(n)]
    if with_case_id:
        cols["case_id"] = [f"c{i:06d}" for i in range(n)]
    cols["y_true"] = [positive if v == 1 else negative for v in y.tolist()]
    cols["score"] = [round(float(s), 6) for s in score.tolist()]
    if with_y_pred:
        cols["y_pred"] = [positive if s >= threshold else negative for s in cols["score"]]
    cols["sex"] = rng.choice(["F", "M"], size=n).tolist()
    cols["age"] = rng.integers(18, 95, size=n).tolist()
    cols["site"] = rng.choice([f"S{k}" for k in range(1, sites + 1)], size=n).tolist()
    return cols


def make_criteria(threshold: float = 0.5, **overrides: Any) -> dict[str, Any]:
    """A complete, valid criteria.yaml mapping (authored fields are placeholders for tests)."""
    base: dict[str, Any] = {
        "schema_version": 1,
        "model": {
            "name": "synthetic-classifier",
            "version": "1.3",
            "prior_version": "1.2",
            "udi_di": None,
        },
        "task": "binary",
        "classes": {"positive": "1", "negative": "0"},
        "score": {"type": "probability", "orientation": "higher_is_positive"},
        "operating_points": [
            {
                "id": "op1",
                "threshold": threshold,
                "rule": ">=",
                "provenance": "prespecified_sap",
                "source": "test fixture",
            },
        ],
        "reference_standard": {"type": "reference_standard", "description": "test fixture"},
        "indeterminates": {"policy": "none_present", "values": []},
        "clustering": {"unit": "none", "declared_by": "test fixture"},
        "prevalence": [{"label": "intended-use, test", "value": 0.3, "source": "test fixture"}],
        "subgroups": [
            {"attribute": "sex", "prespecified": True, "source": "test", "reference_level": "M"},
            {
                "attribute": "age",
                "prespecified": True,
                "source": "test",
                "bands": [[0, 40], [40, 65], [65, 80], [80, 200]],
                "reference_level": "40-65",
            },
            {"attribute": "site", "prespecified": False, "reference_level": "largest"},
        ],
        "criteria": [
            {
                "id": "C1",
                "metric": "sensitivity",
                "operating_point": "op1",
                "scope": "overall",
                "statistic": "ci_lower_bound",
                "comparator": ">=",
                "value": 0.8,
                "author": "Test Author",
                "date": "2026-01-01",
                "justification": "test fixture",
            },
        ],
        "ledger": {"warn_after_acceptance_runs": 3},
        "egress": {
            "telemetry": False,
            "suppression": {"min_n": 10, "min_events": 5, "min_nonevents": 5},
        },
        "bootstrap": {"B": 200, "seed": 20240101, "interval": "percentile"},
    }
    out = copy.deepcopy(base)
    for k, v in overrides.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = v
    return out


def write_csv(path: Path, cols: dict[str, list[Any]]) -> Path:
    headers = list(cols)
    n = len(cols[headers[0]]) if headers else 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for i in range(n):
            w.writerow([cols[h][i] for h in headers])
    return path


def write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def confirmed_mapping(csv_path: Path, decided_by: str = "file") -> Path:
    """Build day 7 (DEC-26): ``run`` needs a confirmed ``mapping.json``. This writes the
    computed mapping of ``csv_path`` beside it as ``<input>.mapping.json`` with
    ``decided_by`` set (``file`` = a hand-supplied prior the customer vouches for) - the
    non-interactive way to what ``proofpack map`` writes after the prompts."""
    from proofpack.io.mapping import map_headers
    from proofpack.io.schema import load_table

    raw = load_table(csv_path)
    m = map_headers(raw.headers, raw.columns)
    m.decided_by = decided_by
    target = csv_path.with_name(csv_path.name + ".mapping.json")
    m.write(target)
    return target


#: Node ids collected in this run that carry no ``dayN`` marker. Filled at collection
#: time (before ``-m`` deselection) so the assertion in ``test_invariants.py`` sees the
#: whole suite even when CI runs a single day's marker.
UNMARKED_ITEMS: list[str] = []


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items) -> None:
    UNMARKED_ITEMS.clear()
    for item in items:
        if not any(m.name.startswith("day") and m.name[3:].isdigit() for m in item.iter_markers()):
            UNMARKED_ITEMS.append(item.nodeid)


@pytest.fixture
def cohort() -> dict[str, list[Any]]:
    return make_cohort()


@pytest.fixture
def criteria() -> dict[str, Any]:
    return make_criteria()


@pytest.fixture
def cohort_csv(tmp_path: Path, cohort) -> Path:
    return write_csv(tmp_path / "test.csv", cohort)


@pytest.fixture
def criteria_yaml(tmp_path: Path, criteria) -> Path:
    return write_yaml(tmp_path / "criteria.yaml", criteria)


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    return tmp_path / "pack"


# ------------------------------------------------------------------ licences (build day 7)
#
# Tests never hold the production signing key. An Ed25519 pair is generated here, once per
# session, and verification against it goes through the named ``registry`` parameter of
# ``proofpack.cli.main`` / ``proofpack.licence.verify`` (the shipped constant is never
# rebound). ``test_licence.py`` additionally verifies a file signed here against the SHIPPED
# key and asserts it is refused (wrong key).

TEST_KEY_ID = "test-ephemeral"


def _ephemeral_pair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return private, public


TEST_PRIVATE_KEY, TEST_PUBLIC_KEY = _ephemeral_pair()
TEST_PUBLIC_KEY_B64 = base64.b64encode(TEST_PUBLIC_KEY).decode("ascii")


def ephemeral_registry():
    from proofpack.licence.keys import KeyRegistry

    return KeyRegistry.of(TEST_KEY_ID, TEST_PUBLIC_KEY)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def licence_payload(
    *,
    tier: str = "annual",
    issued: datetime | None = None,
    expires: datetime | None = None,
    grace_days: int = 30,
    key_id: str = TEST_KEY_ID,
    licence_id: str = "lic_test0000000000000000000000000001",
    **extra: Any,
) -> dict[str, Any]:
    issued = issued if issued is not None else datetime(2026, 9, 1, tzinfo=UTC)
    expires = expires if expires is not None else issued + timedelta(days=365)
    payload = {
        "licence_id": licence_id,
        "licensee": "Test Licensee Ltd",
        "company_no": "00000000",
        "tier": tier,
        "models": 1,
        "features": ["T1", "T2", "T7", "T8", "T9", "T12", "compare", "monitor"],
        "issued": iso_utc(issued),
        "expires": iso_utc(expires),
        "grace_days": grace_days,
        "key_id": key_id,
    }
    payload.update(extra)
    return payload


def sign_licence(payload: dict[str, Any], private_key=None) -> str:
    """The site's format: base64(JSON payload) '.' base64(signature over the ASCII bytes
    of the first segment)."""
    private_key = private_key if private_key is not None else TEST_PRIVATE_KEY
    segment = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    sig = private_key.sign(segment.encode("ascii"))
    return segment + "." + base64.b64encode(sig).decode("ascii")


def write_licence(path: Path, payload: dict[str, Any] | None = None, **kw: Any) -> Path:
    payload = payload if payload is not None else licence_payload(**kw)
    path.write_text(sign_licence(payload), encoding="ascii")
    return path


@pytest.fixture(scope="session")
def session_home(tmp_path_factory) -> Path:
    """One per-user directory for the whole session with a valid ephemeral-signed annual
    licence installed, so ``run`` through ``main(..., registry=ephemeral_registry())`` exits
    0 / 2 rather than 4. Tests that need no licence, or their own ledger, point
    ``PROOFPACK_HOME`` elsewhere with ``monkeypatch``."""
    home = tmp_path_factory.mktemp("proofpack-home")
    write_licence(home / "proofpack.lic")
    return home


@pytest.fixture(autouse=True)
def _isolated_home(session_home: Path, monkeypatch):
    """Every test reads the session home, never the machine's real per-user directory
    (its licence and ledger must not be touched or counted by a test run)."""
    monkeypatch.setenv("PROOFPACK_HOME", str(session_home))
    monkeypatch.delenv("PROOFPACK_LICENCE", raising=False)
    yield
