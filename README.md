# proofpack

ProofPack engine (Global Phoenix Solutions Ltd). Computes performance estimates,
confidence intervals, differences and distribution comparisons from a
customer-supplied test table and renders them into evidence-pack templates.

It is statistical software. It is not a certification, an audit, a regulatory
opinion, a clinical evaluation or a submission, and no regulator has reviewed,
accepted, approved or endorsed it (see `src/proofpack/scope.py`).

## Status

Build day 7 (E7, 2026-09-21): `proofpack run` writes the assembled document
(`run.json`: manifest, declarations echo, flow, Table 1, missingness, overall,
calibration, subgroups, fairness, criteria results, ledger) from a confirmed mapping;
`proofpack licence show | verify | install` verifies an Ed25519 licence against the
shipped public key. Templates, narrative and egress land on later build days. See
`handoffs/`.

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
   ["1999-01-01"]` prints `min <suppressed> max 2024-03`); the day/month order of a
   slash, dot or dash date is decided once per column from the sampled values, never
   per value: if any sampled value has a second field above 12 and none a first field
   above 12, the column is month-first; if any has a first field above 12, day-first;
   both or neither, day-first (`["03/15/2024"] * 9 + ["04/03/2024"]` is nine rows of
   March and one of April and prints `min <suppressed> max <suppressed>`; at 4fbbf35
   the order was decided per value and it printed `min 2024-03` for a nine-row month;
   `["03/15/2024"] * 9 + ["03/04/2024"]` prints `2024-03` for both; `["13/15/2024"] *
   60` keeps `2024-15`). A categorical/string column
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
     answer is stripped of surrounding spaces and lower-cased; `a` or `accept` accepts,
     `e` or `edit` asks for a canonical role, `attr_<name>` / `rater_<name>` in
     lower-case letters, digits and `_`, or `ignore`; an entry accepted or edited at the
     prompt gains `confirmed: true` (DEC-28 for the accept, DEC-42 for the edit: at
     4fbbf35 an edit left it `false` and the two edited files fed were H07 under
     `--yes`); `q`, `quit` or `abort` halts H07; the empty answer (Enter alone) and any
     other word print `answer a, e or q` and ask again. An accept or an edit that would give a role a second
     holder among the columns already settled is refused at the prompt. An edit to
     `ignore` on the column `--criteria`'s `period.column` names is refused with one
     line (`refused: the period declaration names a column mapping.json ignores; map it
     to event_date or declare another column`), and a mapping that ignores that column
     (one proposed `ignore high` is not among the prompted entries, which are the
     non-high roles: `visit` holding one ISO date and 59 blanks) halts S03 with the same
     sentence here and at `proofpack run`, with or without a prior; at 4fbbf35 `run --mapping` on such a file built the pack's period
     axis from the ignored column while counting it in `n_unused_columns`
     (`tests/test_mapping_repair4.py::test_an_ignored_visit_named_by_period_column_is_s03_on_both_routes`).
     A `period.column` naming an original header mapped to a role is read under that
     role at `proofpack run` (at 4fbbf35 `visit -> event_date` with `period.column:
     visit` was S03 `declared period column is not present in the table`). An edit to `ignore` on a column
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
     gives it age_band`) unless the file's `decided_by` is `interactive`, the entry is
     `confirmed`, the mapping computed from this table gives the column `medium` or
     `low` (the per-role prompt iterates the `medium` and `low` entries) and its stored value
     summary equals the fresh one (DEC-42: the role a human chose at the prompt stands
     on the values the human saw; `score -> attr_score_flag` edited beside `prob ->
     score` accepted, on `row_id,label,score,prob`, passes `--yes` - at 4fbbf35 it was
     H07 for ever,
     `tests/test_mapping_repair4.py::test_e_attr_score_flag_beside_prob_score_passes_yes_and_e_attr_patient_code_too`;
     `decided_by`, `confirmed` and the stored summary are read from the file and the
     confidence is computed from the table; who typed the file is not verified - the
     paragraph under the JSON below names the files fed),
     each `confirmed` entry's stored value summary equal to the
     one computed from this table in `inferred_type` and in the values of a
     two-valued `split`, where the file holds a summary for that column (a prior
     that holds no summary for a column is not compared for that column, whoever wrote
     it: `value_summaries: {}` or `null` in a confirmed prior passes on a re-exported
     column; a hand-authored `file` prior that does hold a summary line for a
     confirmed column is compared like an engine-written one,
     `tests/test_mapping_repair5.py::test_a_file_prior_with_a_typed_summary_is_compared`;
     `tests/test_mapping_repair4.py::test_a_confirmed_prior_without_summaries_is_not_compared`;
     counts are not compared; at b0f60a6 the `patient` column
     confirmed as `categorical; 20 unique` and re-exported as the ten strings `0.0`
     .. `0.9` passed, and `Gender` confirmed as 0/1 and re-exported as 0/1/2 passed;
     now H07 `the values of a column confirmed at the prompt changed`,
     `tests/test_mapping_repair3_2.py::test_yes_halts_h07_when_a_confirmed_columns_values_changed`),
     and every non-high role computed from this table is `confirmed: true` in the
     file (DEC-28); otherwise H07. The prior file's roles are used and its `decided_by`
     is written back as read (`interactive` stays `interactive`; until 9cfbdd5 it was
     rewritten `file`). A prior file with a leading UTF-8 BOM (PowerShell 5.1
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

The mapper sets `confirmed: true` only on an entry accepted or edited at the per-role
prompt (the all-high accept leaves every entry `false`; at 4fbbf35 an edit did too);
`--yes` reads the flag, cannot verify who set it, and writes the file back with
whatever `confirmed` values it held (`confirmed: true` planted by hand on a high entry
survives `map --yes`:
`tests/test_mapping_repair3_2.py::test_the_mapper_sets_confirmed_only_on_an_accept_or_an_edit_and_yes_writes_back_what_it_read`).
A prior whose `decided_by` is `file` (or absent) and which carries `confirmed: true` on
an entry whose role differs from the computed one is H07 on the role difference
whether or not it holds a value summary for that column: at 9cfbdd5 the file
`proofpack run` writes without a prompt, copied with `decided_by: file`, `age ->
attr_age_years` and `confirmed: true` typed in, passed `map --yes` and `run --yes` and
the pack listed `attr_age_years` (lens-1 fresh-attack B1 of repair 4), and a hand-built
prior with `site -> ignore`, `confirmed: true` and the one line `"site":
{"inferred_type": "categorical", "split": null}` under `value_summaries` passed too
(lens-1 regression B1); both are exit 3 now, with `value_summaries: {}` as at 4fbbf35
(`tests/test_mapping_repair4_2.py::test_a_confirmed_file_prior_is_h07_on_a_role_difference_with_or_without_a_summary`).
`decided_by: interactive` typed by hand into that copy beside `confirmed: true` on
`age` is H07 too, because the mapping computed from the table gives `age` `high` and
the prompt asks about `medium` and `low` entries only; typed beside `confirmed: true`
on `Gender` (`medium`, 0/1) with the engine's summary intact it passes, and so does the
file the prompt wrote after `a a` with `patient -> sex` and `Gender -> case_id` swapped
by hand (`map --yes` exit 0; `run --yes` then halts H05 on the duplicate `case_id`
rows); that swapped file and the one the prompt writes for `e sex`, `e case_id` differ
in the two `notes` strings (`accepted interactively` / `edited interactively`) and the
timestamp only, and `--yes` reads neither
(`tests/test_mapping_repair4_2.py::test_decided_by_interactive_typed_by_hand_is_read_on_a_non_high_entry_only`).
`Mapping.read` takes `true`, `false` or the key absent (read as `false`) and halts H07
on any other JSON type. `decided_by` is `interactive` after the prompts and stays
`interactive` through `--yes` and `proofpack run --mapping` (until 9cfbdd5 both
rewrote it `file`; `tests/test_mapping_repair4_2.py::test_yes_and_run_mapping_keep_decided_by_interactive`),
`file` when a prior says so or has no `decided_by` key, and
`proposed` on the file `map_headers` computes before any confirm step (until build
day 7 `proofpack run` wrote that file into `--out`; DEC-26 ended it). `proofpack run`
on a `proposed` file, with or without `--yes`, halts H07 `this one was not confirmed`
and copies nothing into the pack
(`tests/test_mapping_repair3_2.py::test_a_proposed_prior_is_not_relabelled_file_by_run_mapping`).
The sha256 of the file's bytes is `Mapping.file_sha256` after `write()` or `read()`,
and the same bytes are `manifest.mapping_sha256` in `run.json` (DEC-27).

## `proofpack run` (build day 7, lane E)

`proofpack run --input test.csv --criteria criteria.yaml [--mapping mapping.json]
[--out ./pack] [--offline]`

* **A confirmed mapping is required (DEC-26).** `--mapping FILE`, or
  `<input>.mapping.json` beside the input (`test.csv` -> `test.csv.mapping.json`);
  neither present, or a file that fails the `--yes` rule above (`decided_by`
  `interactive` or `file`, the header-set hash equal, every role high or confirmed),
  is `HALT H07: run proofpack map first ...` before any statistics. `run` never
  proposes a mapping and never writes one anywhere.
* **What is written:** `<out>/run.json`, the D1 section 4.2 document as canonical JSON
  (sorted keys, one-space indent, UTF-8, no `NaN` or `Infinity` - a non-finite float
  raises and nothing is written), plus the day-1 `ingest_report.json`. Nothing is
  written on a HALT.
* **Criteria** (`src/proofpack/criteria.py`): every `criteria.yaml` criterion and the
  fairness bound is one of `met` / `not_met` / `not_assessable` with a machine
  `reason_code`, comparing the statistic the customer named (`ci_lower_bound` =
  `ci_lo`, `ci_upper_bound` = `ci_hi`, `point_estimate` = `est`, read literally
  whatever the comparator) with the customer's comparator and value. The row is routed
  on the Number's `method` before any statistic is read: `method: none` (a typed
  `not_estimable_reason`) is `not_assessable` / `no_interval` under `ci_lower_bound`,
  `ci_upper_bound` and `point_estimate` alike, with the reason in `detail`
  (`tests/test_criteria.py::test_a_number_with_method_none_is_not_assessable_under_each_of_the_three_statistics`;
  at `ab729d3` `point_estimate` was compared on `est`). `attainable_at_n` /
  `max_lower_bound_at_n` (the Wilson lower bound at `k = n`, `stats.attainability`)
  are filled for `ci_lower_bound` criteria on proportion metrics whose Number's
  `method` is `wilson` and whose `n` is an integer above 0; on any other method (a
  cluster bootstrap, `none`) both are `null` and `detail.attainability_not_computed`
  reads `method_not_wilson`, at `n` 0 and `null` too
  (`tests/test_criteria.py::test_a_method_none_number_at_n_zero_or_n_null_is_annotated_method_not_wilson`;
  at `02d00c5` a `zero_denominator` row at `n` 0 carried no annotation). No default
  bound, statistic or comparator exists; a fairness `bound` needs `statistic` and
  `comparator` beside it (H08 otherwise).
* **Ledger** (`io/ledger.py`): `ledger.json` in the per-user directory
  (`PROOFPACK_HOME`, else `%LOCALAPPDATA%\proofpack` on Windows, `~/.proofpack`
  elsewhere) counts runs with a `criteria` block per test set (SHA-256 of the
  analysed `y_true` and `score` bytes); `W14` when the count exceeds
  `ledger.warn_after_acceptance_runs`; no `ledger` block, no warning.
* **Licence** (`src/proofpack/licence/`): the file at `PROOFPACK_LICENCE`, else the
  per-user `proofpack.lic`, else `./proofpack.lic`, verified against the shipped
  public key (`pp-2026-09`, the key published on `/trust`). `ok` and `grace` are full
  runs (exit 0 / 2; `grace` puts `LICENCE EXPIRED - not for submission` in
  `manifest.watermark`); expired past grace, refused or absent still computes and
  writes `run.json` with that watermark and exits 4 with the one-line fix (D1
  section 7: after grace `run` / `compare` emit JSON only; `doctor` / `map` /
  `fixtures` always work). A trial carries `TRIAL` and expires 30 days after issue.
* `proofpack licence show` (the installed file, no signature printed),
  `proofpack licence verify FILE` (exit 0 for `ok` / `grace`, 4 otherwise) and
  `proofpack licence install FILE` (verifies, then copies to the per-user location;
  a refused file is not installed).
* Exit codes: 0 ok, 2 warnings only, 3 HALT, 4 licence, 5 internal.
