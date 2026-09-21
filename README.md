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
   prints `min <suppressed> max 100`). A date min or max month is printed only when
   >= 10 sampled rows fall in that month (DEC-39: `["2024-03-15"] * 49 +
   ["1999-01-01"]` prints `min <suppressed> max 2024-03`); a slash, dot or dash date
   is read day-first, and month-first only when day-first gives a month above 12 and
   month-first does not (`03/15/2024` is `2024-03`; at b0f60a6 it printed `2024-15`;
   `13/15/2024` keeps `2024-15`). A categorical/string column
   with more than half of its non-missing sample unique lists no values.
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
4. Halts H07 before the table when `--out` names an existing directory (the message
   carries the last path component only: `--out names an existing directory (pack)`)
   or when the directory of `--out` does not exist, then prints the table `original
   header -> role -> confidence -> value summary` (under `--quiet` only when stdin is a
   terminal, because the prompts refer to it), then:
   * stdin is a terminal and `--yes` is absent: prompts once per non-high role. The
     answer is stripped of surrounding spaces and lower-cased; `a` or `accept` accepts
     (the entry gains `confirmed: true`, DEC-28), `e` or `edit` asks for a canonical
     role, `attr_<name>` / `rater_<name>` in lower-case letters, digits and `_`, or
     `ignore` (the entry stays `confirmed: false`), `q`, `quit` or `abort` halts H07;
     the empty answer (Enter alone) and any other word print `answer a, e or q` and
     ask again. An accept or an edit that would give a role a second holder among the
     columns already settled is refused at the prompt. An edit to `ignore` on a column
     whose header, after BOM stripping, trimming, NFC and case-folding, equals a role
     that any other column currently holds is refused with one line naming both
     headers and the role (DEC-31: `score` holding 0/1 beside `prob`, both proposed
     as `score low`, cannot be set to `ignore` while `prob` holds `score`; give
     `score` another role, `attr_score_flag` or `y_pred`, or `prob` another role).
     The accept arm runs the same check for a role an already-ignored column is named
     for; `map_headers` proposes `ignore` on no header that is a role name, so that
     direction is reached by a hand-built mapping in
     `tests/test_mapping_repair3.py::test_accept_or_edit_to_a_role_an_ignored_column_is_named_for_is_refused`
     and not from this command as measured on the 19 canonical names, `attr_x` and
     `rater_x`. At `proofpack run` an ignored column keeps its name unless that name
     is one the schema reads as a role (a canonical name, `attr_<identifier>`, a
     `rater_` name), in which case it is keyed `ignored:<header>` and counted in
     `n_unused_columns`: at b0f60a6 `sex` (1/2/9) answered `e ignore` reached the pack
     as the `sex` attribute and `score` (0/1) ignored beside `prob -> attr_prob_raw`
     was read as the score
     (`tests/test_mapping_repair3_2.py::test_an_ignored_column_named_for_a_role_does_not_reach_validate_under_that_name`).
     When every role is high the prompt is once for the whole mapping: `a` or
     `accept` accepts, `q`, `quit` or `abort` halts, the empty answer and any other
     word print `answer a or q` and ask again. The file is written with `decided_by:
     interactive`. Ctrl-C between the table load and the last prompt (the test raises
     it from `load_table` and at two prompts), or a closed stdin at a prompt, is H07
     (`nothing written`); Ctrl-C during the write is H07 `mapping interrupted while
     writing --out` (the file may be partial); an `OSError` on the write (a read-only
     `--out` was fed) is H07 `--out could not be written`, without the path;
   * stdin is not a terminal and `--yes` is absent: halts H07 (`run interactively or
     pass --yes with a prior mapping.json`) before any prompt;
   * `--yes`: accepted only when a prior `mapping.json` at `--out` has the same
     `header_set_sha256`, its `decided_by` is `interactive` or `file` (a `proposed`
     file written by `proofpack run` is refused), its entries name exactly this
     table's headers and every role in it is a canonical role or an `attr_` /
     `rater_` name (DEC-29), no ignored entry is named for a role another entry holds
     (DEC-31, the same H07 as `proofpack run --mapping`), every mapped role in the
     file is `high` or `confirmed: true`, the file's role for each column equals the
     role computed from this table (a prior `age` on a column now holding `[70-80)`
     bands halts: `maps a column to age but the mapping computed from this table
     gives it age_band`), each `confirmed` entry's stored value summary equal to the
     one computed from this table in `inferred_type` and in the values of a
     two-valued `split` (counts are not compared; at b0f60a6 the `patient` column
     confirmed as `categorical; 20 unique` and re-exported as the ten strings `0.0`
     .. `0.9` passed, and `Gender` confirmed as 0/1 and re-exported as 0/1/2 passed;
     now H07 `the values of a column confirmed at the prompt changed`,
     `tests/test_mapping_repair3_2.py::test_yes_halts_h07_when_a_confirmed_columns_values_changed`),
     and every non-high role computed from this table is `confirmed: true` in the
     file (DEC-28); otherwise H07. An entry edited at the prompt is not `confirmed`
     and its computed role differs, so a mapping with an edit does not pass `--yes`
     (repair-3 note, open question 1). The prior file's roles are used
     (`decided_by: file`). A prior file with a leading UTF-8 BOM (PowerShell 5.1
     `Out-File`) is read; the file is written back without it.

`mapping.json` (the one file this command writes original headers to) is written as
below. This is the shape DEC-27 fixes for the E7 manifest hash: a list of entries, each
carrying `original`, `role`, `confidence`, `source`, `notes` and `confirmed`, with the
file-level `header_set_sha256`, `value_summaries`, `decided_by` and `timestamp`.

```json
{
  "header_set_sha256": "<sha256 of the sorted, trimmed header set>",
  "roles": [
    {"original": "SepsisLabel", "role": "y_true", "confidence": "high",
     "source": "synonym", "notes": [], "confirmed": false},
    {"original": "Gender", "role": "sex", "confidence": "medium", "source": "synonym",
     "notes": ["no dictionary declared for 0/1", "accepted interactively"],
     "confirmed": true},
    {"original": "HR", "role": "ignore", "confidence": "high", "source": "ignore",
     "notes": [], "confirmed": false}
  ],
  "value_summaries": {"<original header>": {"inferred_type": "int", "n_sampled": 50,
     "n_missing": 0, "missing_pct": 0.0, "n_unique": 2, "top": [["0", 35], ["1", 15]],
     "n_suppressed_values": 0, "min": "0", "max": "1", "split": [["0", 35], ["1", 15]],
     "free_text": false, "values_shown": true}},
  "decided_by": "interactive | file | proposed",
  "timestamp": "<UTC ISO 8601>"
}
```

The mapper sets `confirmed: true` only when `a` is answered at the per-role prompt (an
edit and the all-high accept leave it `false`); `--yes` reads the flag, cannot verify
who set it, and writes the file back with whatever `confirmed` values it held
(`confirmed: true` planted by hand on a high entry survives `map --yes`:
`tests/test_mapping_repair3_2.py::test_the_mapper_sets_confirmed_only_on_an_accept_and_yes_writes_back_what_it_read`).
`Mapping.read` takes `true`, `false` or the key absent (read as `false`) and halts H07
on any other JSON type. `decided_by` is `interactive` after the prompts, `file` after
`--yes` or `proofpack run --mapping` re-used an `interactive` or `file` prior, and
`proposed` on the file `proofpack run` writes into `--out` when it maps without a
prior (still written at this commit; DEC-26 makes `run` halt H07 `run proofpack map
first` instead, an E7 change). `proofpack run --mapping` on a `proposed` file (no
`--yes`) writes the pack's copy as `proposed` too: at b0f60a6 it relabelled it `file`
and `--yes` then took the copy
(`tests/test_mapping_repair3_2.py::test_a_proposed_prior_is_not_relabelled_file_by_run_mapping`).
The sha256 of the file's bytes is `Mapping.file_sha256` after `write()` or `read()`,
for the E7 manifest. `proofpack run` still maps with the same function and, without a
prior `mapping.json` and without `--yes`, proceeds on the computed mapping (day-1
behaviour; the confirm step is `map`'s); with `--mapping` it applies the DEC-29 and
DEC-31 checks on the prior before `apply_mapping`.
