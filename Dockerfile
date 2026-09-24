# ProofPack engine image (A-P3, build day 9): D1 section 9's reference platform,
# python:3.12-slim on linux/amd64, with the dependencies from the pinned lockfile.
#
# Base image digest: [unverified] - not pinned in this file. No image was pulled on the
# build machine, so no digest was read there. The CI job docker-smoke
# (.github/workflows/ci.yml) prints the digest of the image it pulled; the pin
# "FROM --platform=linux/amd64 python:3.12-slim@sha256:<digest>" is added from that printed
# value (tests/test_dockerfile.py accepts the tag alone only while this comment is here).
#
# Build context (.dockerignore admits nothing else): requirements.lock, written by
#   uv export --locked --no-dev --extra stats --no-emit-project --format requirements-txt
# (every line hash-pinned), and dist/*.whl from `uv build --wheel`. No key material enters
# the image: the licence signing key is an environment variable of the issuer only, and a
# customer's licence file is supplied at run time (PROOFPACK_LICENCE or a mounted home).
FROM --platform=linux/amd64 python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.lock /tmp/proofpack/requirements.lock
COPY dist/ /tmp/proofpack/dist/
RUN python -m pip install --require-hashes --no-deps -r /tmp/proofpack/requirements.lock \
 && python -m pip install --no-deps --no-index /tmp/proofpack/dist/proofpack-*.whl \
 && rm -rf /tmp/proofpack \
 && useradd --create-home --uid 10001 --shell /usr/sbin/nologin proofpack

USER proofpack
WORKDIR /home/proofpack
ENTRYPOINT ["proofpack"]
CMD ["doctor", "--offline"]
