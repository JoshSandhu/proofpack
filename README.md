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
src/proofpack/io/       schema (load + type + flow), declare (criteria.yaml), mapping (roles, H07, H11),
                        profile (value-level column summaries, suppressed)
src/proofpack/gates.py  HALT gates H01-H12 and the ingest pipeline
src/proofpack/doctor.py proofpack doctor
src/proofpack/cli.py    doctor | map | run | compare
tests/                  conftest.py seeded cohort factory; F12 gate tests; hypothesis schema fuzz;
                        fixtures/mapping/ 35 header-variant CSVs with authored expectations
scripts/                mutation_sweep.py (DEC-12 ii), coverage_bar.py, make_mapping_fixtures.py
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

## `proofpack map` (build day 6, lane A)

`proofpack map --input test.csv [--criteria criteria.yaml] [--out mapping.json] [--yes]`

What it does, in order:

1. Reads the table (`io.schema.load_table`), then profiles every column from its first
   10,000 rows after the header (`io.profile`): inferred type (int / float / date /
   categorical / string), `n_unique`, the top <= 20 values with counts, min/max for
   numeric and date columns (dates coarsened to `YYYY-MM`), missing % after the
   missing-token normalisation, and for <= 2-unique columns the split. A value is
   listed only when its count is >= 10 (the egress cell floor of D1 section 6, reused
   here because D1 section 5 states no floor of its own); below that it prints as
   `<suppressed>`. A numeric min or max is printed only when >= 10 sampled rows hold
   that value; otherwise it prints as `<suppressed>` too (`["100"] * 41 + ["7"] * 9`
   prints `min <suppressed> max 100`). A categorical/string column with more than half
   of its non-missing sample unique lists no values.
2. Assigns a role and a confidence to every header (`io.mapping.map_headers`): exact
   canonical name, the synonym table, an affix-stripped synonym (`pt_age`,
   `label_v2`), a header token (`patient_nbr`), a date-like header, then the value
   heuristics (two-valued label sets, floats within [0, 1], parseable dates, unique
   integers). The confidence table is in the module docstring. Declarations (positive
   class, orientation, threshold, reference-standard type, indeterminates, clustering)
   are not read by the mapper; `io.declare` reads them from `criteria.yaml`.
3. Halts with a typed code and exit 3: H07 when two headers coincide after case-folding,
   trimming and NFC normalisation; E01 (DEC-11) when two headers resolve to `case_id`
   by name (canonical, synonym or affix - `patient_id` + `subject_id`; two headers that
   only carry a token, `patient_nbr` + `mrn_local`, are both `case_id low` for the
   prompt, and `proofpack run` on a mapping that still holds two `case_id` columns halts
   E01 at apply time), when `criteria.yaml`'s `clustering.unit` is a list of two or
   more, or a string that splits into two or more tokens on ` and ` (any case) or any
   character outside `[A-Za-z0-9_]` (`subject_id/hadm_id`, `patient_id, study_id`,
   `a b`; the hyphenated single name `patient-id` also counts two), or when
   `clustering.columns` / `key` / `keys` / `column` / `units` / `fields` lists two or
   more or is a string that splits into two or more the same way (message ends `reduce
   your case key to one column`); H11 when a column is date-like by header (the H11
   header regex) or typed `date` by values - every sampled value one of the six shapes in
   `io.profile.DATE_PATTERNS` (ISO, `15/03/2024`, `2024/03/15`, `15-03-2024`,
   `15.03.2024`, `17 Mar 2024`; two-digit years such as `3/17/24` are not among them) -
   and no `period` declaration covers it.
4. Halts H07 before the table when the directory of `--out` does not exist, then prints
   the table `original header -> role -> confidence -> value summary` (under `--quiet`
   only when stdin is a terminal, because the prompts refer to it), then:
   * stdin is a terminal and `--yes` is absent: prompts once per non-high role
     (accept / edit to a canonical role, `attr_<name>` / `rater_<name>` in lower-case
     letters, digits and `_`, or `ignore` / quit; an accept or an edit that would give a
     role a second holder among the columns already settled is refused at the prompt),
     or once for the whole mapping when every role is high (`a` or `q`; anything else
     re-prompts), and writes `mapping.json` with `decided_by: interactive`. Ctrl-C
     between the table load and the last prompt (the test raises it from `load_table`
     and at two prompts), or a closed stdin at a prompt, is H07 (`nothing written`);
   * stdin is not a terminal and `--yes` is absent: halts H07 (`run interactively or
     pass --yes with a prior mapping.json`) before any prompt;
   * `--yes`: accepted only when a prior `mapping.json` at `--out` has the same
     `header_set_sha256`, its `decided_by` is `interactive` or `file` (a `proposed`
     file written by `proofpack run` is refused), and every mapped role is `high` both
     in that file and in the mapping computed from this table; otherwise H07. The prior
     file's roles are used (`decided_by: file`).

`mapping.json` (the one file this command writes original headers to) is written as:

```json
{
  "header_set_sha256": "<sha256 of the sorted, trimmed header set>",
  "roles": [
    {"original": "SepsisLabel", "role": "y_true", "confidence": "high",
     "source": "synonym", "notes": []},
    {"original": "HR", "role": "ignore", "confidence": "high", "source": "ignore", "notes": []}
  ],
  "value_summaries": {"<original header>": {"inferred_type": "int", "n_sampled": 50,
     "n_missing": 0, "missing_pct": 0.0, "n_unique": 2, "top": [["0", 35], ["1", 15]],
     "n_suppressed_values": 0, "min": "0", "max": "1", "split": [["0", 35], ["1", 15]],
     "free_text": false, "values_shown": true}},
  "decided_by": "interactive | file | proposed",
  "timestamp": "<UTC ISO 8601>"
}
```

D1 section 5.5 lists `roles` and `confidences` as separate keys; the day-1 shape keeps
both inside each `roles` entry and day 6 adds `source` and `notes` to it. The sha256 of
the file's bytes is `Mapping.file_sha256` after `write()` or `read()`, for the E7
manifest. `proofpack run` still maps with the same function and, without a prior
`mapping.json` and without `--yes`, proceeds on the computed mapping (day-1 behaviour;
the confirm step is `map`'s).
