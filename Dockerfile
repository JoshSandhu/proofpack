# ProofPack engine image (A-P3, build day 9): D1 section 9's reference platform,
# python:3.12-slim on linux/amd64, with the dependencies from the pinned lockfile.
#
# Base image digest: [unverified] - not pinned in this file. No image was pulled on the
# build machine, so no digest was read there. The CI job docker-smoke
# (.github/workflows/ci.yml) greps the base reference from its build log (the grep step
# was written after GitHub Actions run 36005620750, whose build log shows the reference);
# the pin "FROM --platform=linux/amd64 python:3.12-slim@sha256:<digest>" is added from that
# printed value (tests/test_dockerfile.py accepts the tag alone only while this comment is
# here).
#
# This file COPYs two inputs: requirements.lock, written by
#   uv export --locked --no-dev --extra stats --no-emit-project --format requirements-txt
# (every line hash-pinned), and dist/*.whl from `uv build --wheel` (.dockerignore admits
# those two; in run 36005620750, 24 September 2026, docker build ran both COPYs and the
# RUN, whose output includes "Successfully installed proofpack-0.1.0.dev1"). The licence
# signing key is not among the inputs: it is an environment variable of the issuer only.
# The wheel carries the Ed25519 public verify key (licence/keys.py SHIPPED_PUBLIC_KEY). A
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
