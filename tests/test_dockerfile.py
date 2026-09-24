"""A-P3 item 4 (build day 9, lane A): the Dockerfile and .dockerignore, parsed.

No image is built here (no base image is pulled on the build machine). What is asserted,
on the file's text after joining continuation lines and dropping comments:

* one ``FROM``, ``--platform=linux/amd64 python:3.12-slim``, either with an
  ``@sha256:<64 hex>`` digest or, while no digest has been measured, with the
  ``Base image digest: [unverified]`` comment present;
* no ``ADD`` instruction whose source is a URL (``http://``, ``https://``, ``git@``), and no
  ``curl`` or ``wget`` in a ``RUN``;
* the ``COPY`` instructions are exactly ``requirements.lock /tmp/proofpack/requirements.lock``
  and ``dist/ /tmp/proofpack/dist/``, and the one ``RUN`` is :data:`THE_RUN` word for word
  (lens FA2-R7 planted ``COPY --from=ghcr.io/x/y:latest /k /k``; lens FA-R6 an unhashed
  ``pip install`` and ``COPY signing.txt``);
* the last ``USER`` is ``proofpack`` (not ``root`` or ``0``), created by ``useradd --uid
  10001``;
* ``ENTRYPOINT ["proofpack"]``;
* no ``ENV`` or ``ARG`` name containing KEY, SECRET, TOKEN, PASSWORD, PRIVATE, CREDENTIAL or
  SEED,
  no ``BEGIN`` of a PEM block, no ``COPY`` of a ``.lic``, ``.pem`` or ``.key`` file;
* the dependency install is ``pip install --require-hashes --no-deps -r requirements.lock``
  and the wheel install ``--no-deps --no-index``;
* ``.dockerignore`` excludes ``*`` first and re-admits ``requirements.lock`` and
  ``dist/*.whl`` only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.day9, pytest.mark.ap3]
REPO = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO / "Dockerfile"
SECRETISH = re.compile(r"KEY|SECRET|TOKEN|PASSWORD|PRIVATE|CREDENTIAL|SEED", re.I)
THE_COPIES = [
    "requirements.lock /tmp/proofpack/requirements.lock",
    "dist/ /tmp/proofpack/dist/",
]
THE_RUN = (
    "python -m pip install --require-hashes --no-deps -r /tmp/proofpack/requirements.lock"
    " && python -m pip install --no-deps --no-index /tmp/proofpack/dist/proofpack-*.whl"
    " && rm -rf /tmp/proofpack"
    " && useradd --create-home --uid 10001 --shell /usr/sbin/nologin proofpack"
)


def instructions(text: str) -> list[tuple[str, str]]:
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    joined = re.sub(r"\\\n", " ", "\n".join(lines))
    out = []
    for ln in joined.splitlines():
        if ln.strip():
            word, _, rest = ln.strip().partition(" ")
            out.append((word.upper(), rest.strip()))
    return out


@pytest.fixture(scope="module")
def text() -> str:
    # no skip: the mutation sweep copies the Dockerfile (scripts/mutation_sweep.py COPIED),
    # so a missing file fails here (lens FA-R11 / RG-N1)
    assert DOCKERFILE.exists(), f"no Dockerfile at {DOCKERFILE}"
    return DOCKERFILE.read_text(encoding="utf-8")


def test_the_base_image_is_python_3_12_slim_amd64_by_digest_or_marked_unverified(text):
    froms = [rest for word, rest in instructions(text) if word == "FROM"]
    assert len(froms) == 1
    m = re.fullmatch(
        r"--platform=linux/amd64 python:3\.12-slim(@sha256:(?P<digest>[0-9a-f]{64}))?", froms[0]
    )
    assert m is not None, froms[0]
    if m.group("digest") is None:
        assert "Base image digest: [unverified]" in text


def test_no_add_of_an_http_or_git_url_and_no_curl_or_wget_in_run(text):
    for word, rest in instructions(text):
        if word == "ADD":
            assert not re.search(r"(^|\s)(https?://|git@)", rest), rest
        if word == "RUN":
            assert not re.search(r"\b(curl|wget)\b", rest), rest


def test_the_copies_and_the_run_are_the_ones_written(text):
    ins = instructions(text)
    assert [rest for word, rest in ins if word == "COPY"] == THE_COPIES
    runs = [" ".join(rest.split()) for word, rest in ins if word == "RUN"]
    assert runs == [THE_RUN]


def test_the_image_runs_as_a_non_root_user(text):
    ins = instructions(text)
    users = [rest for word, rest in ins if word == "USER"]
    assert users and users[-1] == "proofpack"
    assert users[-1] not in ("root", "0")
    run = " ".join(rest for word, rest in ins if word == "RUN")
    assert re.search(r"useradd [^&]*--uid 10001[^&]* proofpack", run)
    last_user = max(i for i, (w, _) in enumerate(ins) if w == "USER")
    assert all(w != "RUN" for w, _ in ins[last_user:])  # nothing runs as root after it


def test_the_entrypoint_is_proofpack(text):
    eps = [rest for word, rest in instructions(text) if word == "ENTRYPOINT"]
    assert len(eps) == 1 and json.loads(eps[0]) == ["proofpack"]


def test_no_secret_looking_env_or_arg_and_no_key_material(text):
    for word, rest in instructions(text):
        if word in ("ENV", "ARG"):
            names = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=", rest) or [rest.split()[0]]
            for name in names:
                assert not SECRETISH.search(name), name
        if word in ("COPY", "ADD"):
            assert not re.search(r"\.(lic|pem|key)\b", rest), rest
    assert "BEGIN" not in text and "PRIVATE KEY" not in text


def test_dependencies_install_from_the_hash_pinned_lock_and_the_wheel_without_an_index(text):
    run = " ".join(rest for word, rest in instructions(text) if word == "RUN")
    assert "pip install --require-hashes --no-deps -r /tmp/proofpack/requirements.lock" in run
    assert "pip install --no-deps --no-index /tmp/proofpack/dist/proofpack-*.whl" in run


def test_dockerignore_admits_the_lock_and_the_wheel_only():
    lines = [
        ln.strip()
        for ln in (REPO / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    assert lines[0] == "*"
    assert [ln for ln in lines if ln.startswith("!")] == [
        "!requirements.lock",
        "!dist",
        "!dist/*.whl",
    ]
    assert lines.index("dist/*") < lines.index("!dist/*.whl")


@pytest.mark.parametrize(
    ("planted", "failing"),
    [
        ("FROM --platform=linux/amd64 python:3-slim", "base"),
        ("FROM python:3.12-slim", "base"),
        ("ADD https://example.org/x.tar.gz /tmp/", "add"),
        ("USER root", "user"),
        ("ENV PROOFPACK_SIGNING_KEY=x", "env"),
        ("ENV PROOFPACK_SIGNING_SEED=x", "env"),
        ("COPY --from=ghcr.io/x/y:latest /k /k", "copy"),
        ("COPY signing.txt /tmp/", "copy"),
        ("RUN python -m pip install cryptography", "copy"),
    ],
)
def test_each_assertion_fails_on_a_planted_line(text, planted, failing):
    """The checks above, run on a copy of the file with one planted line, fail."""
    mutated = text
    if failing == "base":
        mutated = re.sub(r"^FROM .*$", planted, text, flags=re.M)
    elif failing == "user":
        mutated = text.replace("ENTRYPOINT", planted + "\nENTRYPOINT")
    else:
        mutated = text.replace("USER proofpack", planted + "\nUSER proofpack")
    checks = {
        "base": test_the_base_image_is_python_3_12_slim_amd64_by_digest_or_marked_unverified,
        "add": test_no_add_of_an_http_or_git_url_and_no_curl_or_wget_in_run,
        "copy": test_the_copies_and_the_run_are_the_ones_written,
        "user": test_the_image_runs_as_a_non_root_user,
        "env": test_no_secret_looking_env_or_arg_and_no_key_material,
    }
    with pytest.raises(AssertionError):
        checks[failing](mutated)
