# proofpack

ProofPack engine (Global Phoenix Solutions Ltd). Computes performance estimates,
confidence intervals, differences and distribution comparisons from a
customer-supplied test table and renders them into evidence-pack templates.

It is statistical software. It is not a certification, an audit, a regulatory
opinion, a clinical evaluation or a submission, and no regulator has reviewed,
accepted, approved or endorsed it (see `src/proofpack/scope.py`).

## Status

Build day 1 (E1, 2026-09-07): validated ingest and declarations. Statistics,
templates, narrative and licensing land on later build days. See `handoffs/`.

## Develop

```
uv python install 3.12
uv venv --python 3.12
uv sync --all-groups --locked
uv run pytest -q                 # all tests
uv run pytest -q -m day1         # one build day
uv run ruff check . && uv run ruff format --check .
uv run pip-audit
uv build --wheel
uv run proofpack doctor --offline
```

## Layout

```
schema/                 JSON Schemas: input table v1, criteria.yaml, claims (skeleton), egress (skeleton)
design/guidance_map_v1.csv   guidance references by internal id; section numbers are transcribed by hand
src/proofpack/io/       schema (load + type + flow), declare (criteria.yaml), mapping (header-only stub)
src/proofpack/gates.py  HALT gates H01-H12 and the ingest pipeline
src/proofpack/doctor.py proofpack doctor
src/proofpack/cli.py    doctor | map | run | compare
tests/                  conftest.py seeded cohort factory; F12 gate tests; hypothesis schema fuzz
handoffs/               one note per build session
```

## Principles fixed on day 1

* Declarations (positive class, score orientation and type, thresholds,
  prevalence, subgroup attributes, reference-standard type, indeterminates,
  clustering) are read from `criteria.yaml` and never inferred. Missing means HALT.
* Every HALT exits 3 and writes nothing.
* `import proofpack` never requires scipy.
* Error messages and any future egress carry aggregates only: never original
  headers, cell values, free-text declaration fields or raw dates.
