**Verdict: FAIL. One blocker (B1): a repeated entry in the two Newcombe oracle files (and a repeated name in an `oracles_v1.json` `values` written as a list of pairs) is still dropped silently - the bogus copy placed before the real one is never compared, the row reads `matched` and `proofpack fixtures --offline` exits 0 at `36bfb2b`. It predates the commit (same at `8ef3266`), but it is the exact shape N0 named and this brief's blocker list covers it. Everything the commit itself claims reproduces: every JSON-object repeat I planted in the four oracle files and the F16 parity file makes the file unreadable and every row citing it `not_matched`, exit 6; 5 of the 6 new tests fail at `8ef3266`; the suite figures reproduce (see Attack 5).**

# E13 N0 lens (fresh attack, DEC-12 (i)) on engine 36bfb2b - Tuesday 6 October 2026

Cold adversarial lens on `36bfb2b` (one commit on `8ef3266`): `load_oracles` (`oracles_v1.json`, `f4_expected.json`, `newcombe1998_paired.json`, `newcombe_table2.json`) and `f16_behaviour` (the committed `fixtures/f16_parity_native.json`) now parse with `_refuse_duplicate_keys`.

Method. Four detached worktrees under the session scratchpad: `new` and `mut` at `36bfb2b`, `old` and `mutold` at `8ef3266`. `PYTHONPATH` set to each tree's `src` as a Windows path, proven each time with `python -c "import proofpack;print(proofpack.__file__)"` (printed `...\n0lens\new\src\proofpack\__init__.py` and `...\n0lens\old\src\proofpack\__init__.py`). Plants were made by a scratch script (`plant.py`: run `python -m proofpack.cli fixtures --offline --out <tmp>` unplanted, plant, run again, restore with `git checkout`, diff the row statuses). Every planted file was restored; `git status --short` was empty in both mutation trees after each plant.

## Blockers

### B1. A repeated entry in an oracle array (or a `values` list of pairs) is dropped silently; the row reads `matched`, exit 0

The hook only sees JSON objects. Three oracle readers build their own keyed mapping from something that is not a JSON object, and Python's `dict` keeps the last copy without a word:

- `_paired_rows` / `_f5_newcombe_paired_oracle` (`fixtures.py`): `values = dict(_paired_rows(doc))`, the key being `"e {e} f {f} g {g} h {h} method10 {side}"` built from each element of the `rows` array of `newcombe1998_paired.json`.
- `_f14_oracle`: `values[f"{ex['label']} {method} lower"] = ...` over the `examples` array of `newcombe_table2.json`.
- `_captured`: `values = dict(entry["values"])` - `dict` accepts a list of `[name, value]` pairs as readily as an object, so `oracles_v1.json` can carry a repeated name without any JSON object repeating a key.

Repro 1 (in `mut`, at `36bfb2b`): insert `{"e": 36, "f": 12, "g": 2, "h": 0, "method10": {"lower": 0.9, "upper": 0.9}},` as the first element of `rows` in `fixtures/newcombe1998_paired.json` (the real `e 36 f 12 g 2 h 0` row, 0.0569 / 0.3404, stays where it is). `python -m proofpack.cli fixtures --offline --out <dir>`:

```
baseline exit 0; planted (paired_dup_row in fixtures/newcombe1998_paired.json) exit 0
  rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only (...) 7
  unchanged rows: 46
```

`F5-newcombe-paired` stays `matched`; the 0.9 in the file's bytes is never compared. Control (the same bogus row appended after the real one, so it is the copy `dict` keeps): exit 6, `not matched: F5-newcombe-paired (outside tolerance: e 36 f 12 g 2 h 0 method10 lower, e 36 f 12 g 2 h 0 method10 upper)`. So the file was read with the plant both times, and which copy is compared depends only on order.

Repro 2: insert a copy of `examples[0]` (label `56/70 - 48/80`) with all four bounds set to 0.9 as the first element of `examples` in `fixtures/newcombe_table2.json`: exit 0, 46 rows unchanged, `F14-newcombe` `matched`. Control (appended): exit 6, `F14-newcombe` `not_matched`, outside tolerance on all four.

Repro 3: replace `captured["F1-wilson"]["values"]` in `fixtures/oracles_v1.json` with `[["wilson_lo", 0.9], ["wilson_hi", 0.36620957698280004], ["wilson_lo", 0.2552885198782742]]`: exit 0, `F1-wilson` `matched`.

All three give the same result at `8ef3266` (pre-existing; the commit did not create them). They are graded blockers because the brief's first blocker class is "a committed oracle file read so that a value is dropped ... while a row reads matched", and because this is the shape N0 asked to close ("a bad copy placed before the real one was never read", the `DuplicateJSONKeyError` docstring) in the very files the commit names. No sentence in the commit is false on this account: every sentence says "a repeated key in any object". Suggested repair: refuse a repeated built key in `_paired_rows` and `_f14_oracle` (raise, so the row is `oracle_error` / `not_matched`), and require `entry["values"]` (and `register[key]`) to be a JSON object before `dict()` - each with a plant test that fails at `36bfb2b`.

## Attack 1: every JSON file the fixtures command or a matched / verified row reads

`grep -rn "json\.load\|object_pairs_hook\|read_text\|read_bytes\|tomllib" src/proofpack scripts`:

| file | reader | hook | can it leave a row matched? |
|---|---|---|---|
| `oracles_v1.json`, `f4_expected.json`, `newcombe1998_paired.json`, `newcombe_table2.json` | `load_oracles` | yes (new) | objects: no (measured). Arrays / pair lists: yes, B1 |
| `fixtures/r/proc_asah.json`, `rms_val_prob_f4.json`, the comparison file | `load_r_captures` | yes (repair 4) | lens 5 measured |
| `fixtures/f16_parity_native.json` | `f16_behaviour` | yes (new) | no; F16 is never `matched` (suite_only at best) |
| `pyproject.toml` | `tomllib.loads` (version) | n/a: `tomllib` refuses a repeated key itself | no |
| `fixtures_report_schema.json` etc. | `load_json_schema` | no | not a comparison input (validation of the report's shape) |
| `run.json`, `pseudonyms.json`, `ingest_report.json` | `f17.py`, `f19.py` | no | written by the engine in the same process, not committed |
| `fixtures/f4_calibration.csv` | `_f4_rows` (CSV, `DictReader`) | n/a | a repeated header column keeps the last column; input data, not an oracle; outside this brief's JSON scope |
| `fixtures/oracles_v1.json` | `scripts/capture_fixture_oracles.py --check` (CI step, `ci.yml:42`) | **no** | no row; see N1 |
| `fixtures/f16_parity_native.json` | `scripts/f16_parity_native.py --check`, `tests/test_f16_parity_native.py::_committed` | **no** | no row; see N1 |
| `fixtures/r/*.json` | `scripts/r_capture_drift.py` (r-captures job) | no | no row (drift report only) |

Plants at `36bfb2b` (each with the bogus copy before the real one):

| plant | exit | rows changed (all to `not_matched`, `oracle_file_unreadable: <file> (DuplicateJSONKeyError)`) | rows naming the file left unchanged |
|---|---|---|---|
| `"wilson_lo": 0.9,` before the first `wilson_lo` in `oracles_v1.json` | 6 (`8ef3266`: 0, 35 matched) | 29: every F1*, F2, F3 (four), F5-mcnemar, F5-register, F5-delong-pair, F6 (three), F8 (two), F9, F10, F11 | none (the 17 unchanged rows' JSON does not contain `oracles_v1`) |
| `"planted": 1, "planted": 2,` at the top of `f4_expected.json` | 6 | F4-closed-form, F4-irls, F4-register | none |
| same, `newcombe1998_paired.json` | 6 | F5-newcombe-paired | none |
| same, `newcombe_table2.json` | 6 | F14-newcombe | none |
| `"fixtures": {},` before the real `"fixtures"` in `f16_parity_native.json` | 6 (`8ef3266`: 0) | F16 | - |

## Attack 2: unreadable oracle file -> every citing row `not_matched`

Yes for all four files (table above): no row citing an unreadable file became `no_oracle_recorded`, `suite_only` or `not_built`. F14: `_f14_oracle` raises `OracleAbsent` (`no_oracle_recorded`) only when `newcombe_table2.json` is neither loaded nor in `unreadable`; the unreadable path reaches `o[NEWCOMBE_FILE]`, whose `__missing__` raises `OracleFileUnreadable`, and the row is `not_matched` (measured: `F14-newcombe: matched -> not_matched | oracle_file_unreadable: newcombe_table2.json (DuplicateJSONKeyError)`). `in` and `.get` on `Oracles` bypass `__missing__`, so I grepped for both: the F14 guard is the only `in`, and it checks `unreadable` too.

## Attack 3: the parity file

A repeated key gives `not_matched` with the error named (`oracle_file_unreadable: fixtures/f16_parity_native.json (DuplicateJSONKeyError); ...`), exit 6. Also measured with a repeated entry key one level down (`"F1-clopper-pearson.cp_hi": {"value": 0.9, ...}` before the real one): `f16_behaviour()` `not_matched`, same reason. `parity.py` itself never reads the committed file (its only `json.loads` round-trips its own output). Two other paths read it without the hook: N1.

## Attack 4: lens 5 N2 shapes in the newly hooked files

| plant | `36bfb2b` | `8ef3266` |
|---|---|---|
| `oracles_v1.json`: first `0.2552885198782742` replaced by a 401-digit integer | exit 5, `internal error: OverflowError: int too large to convert to float`, no report | same |
| `f16_parity_native.json`: first `"value"` number replaced by a 401-digit integer | exit 5, same message, no report | same |
| `oracles_v1.json`: `"zz": ` + 100000 `[` ... `]` at the top | exit 5, `RecursionError: Stack overflow ... decoding a JSON array`, no report | same |
| same with 100000 nested objects | exit 5, `... decoding a JSON object` | same |
| `f16_parity_native.json`, 100000 nested arrays | exit 5 | same |
| `f16_parity_native.json` wrapped in `[...]` | exit 5, `AttributeError: 'list' object has no attribute 'get'` | same |

All fail closed (non-zero, no report, nothing `matched`) and are identical at `8ef3266`: the hook did not make them reachable in a new place. No sentence claims otherwise (`load_oracles` names `ValueError` only). Non-blocking (N2).

## Attack 5: the commit message's figures

Run in `wt-e13n0` at `36bfb2b` (the only change in the tree was this untracked note), `PYTHONPATH=C:\Users\joshs\GPS\ProofPack\wt-e13n0\src`, import proven in each shell:

| command | Git Bash | PowerShell 5.1 | commit message |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | 2323 passed, 4 skipped (285 s) | 2323 passed, 4 skipped (289 s) | 2323 passed, 4 skipped |
| `... -m day13` | 120 passed | 120 passed | 120 |
| `... -m day12` | 199 passed, 3 skipped | 199 passed, 3 skipped | 199/3 |
| `python -m ruff check .` / `ruff format --check .` | All checks passed / 347 files already formatted | same | clean |
| `tests/test_e13_n0_duplicate_keys.py` against `8ef3266`'s `src` | 5 failed, 1 passed | - | 5 of 6 fail |

(A first run from a scratch worktree gave 5 skipped: the confusables test looks for `workflows/data` beside the repository, absent under the scratchpad. Not a defect.)

## Non-blocking

- **N1. Two `--check` scripts read the committed files without the hook and exit 0 on a planted repeat.** (a) `scripts/capture_fixture_oracles.py --check` (a CI step, `ci.yml:42`) with `"wilson_lo": 0.9,` planted in `oracles_v1.json`: `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`, exit 0. (b) `scripts/f16_parity_native.py --check` with a repeated `F1-clopper-pearson.cp_hi` entry (0.9 first): `F16 native check: 894 entries, 0 failures`, exit 0; `tests/test_f16_parity_native.py::_committed` reads the same way. Neither is a row, and CI still goes red on such a plant through `test_e13n0_the_committed_oracle_and_parity_files_have_no_repeated_key` (the "pytest (all markers)" step). The commit message's "the committed F16 parity file are read with the duplicate-key hook" is true of the fixtures command, which is its context; a reader could take it more widely. Suggest giving both scripts the hook (importing `_refuse_duplicate_keys`).
- **N2. Lens 5 N2 now also reachable through `oracles_v1.json` and the parity file** (table above): exit 5 instead of a row. Pre-existing, fail closed. Suggest catching `OverflowError` in `_number` and `RecursionError` beside `ValueError` in `load_oracles`, `f16_behaviour` and `load_r_captures`, and a non-object top level in `f16_behaviour`.
- **N3. `f16_behaviour`'s docstring says "`no_oracle_recorded` when the file cannot be read here"**, but a file that is present and unreadable (now including a repeated key) gives `not_matched`; only a non-checkout install gives `no_oracle_recorded`. The sentence predates the commit (it was already untrue for a `JSONDecodeError`) and "here" can be read as "in this install". Suggest "when this package is not a source checkout".
- **N4. `load_oracles` catches `ValueError` and `FileNotFoundError` only**: a present oracle path that is a directory or unreadable by permission (`OSError`) escapes as exit 5. Pre-existing.
- **N5. The sixth new test** (`..._have_no_repeated_key`) asserts `f16_behaviour()["status"] != "not_matched"`; it would also pass on `no_oracle_recorded` (a non-checkout run). In the suite it runs from a checkout, so it holds; it is a weak pin rather than a defect.

## Could not break

- A JSON-object repeat at any depth in any of the five files: hook runs on every object; plants at the top level, one level down in `oracles_v1.json` (`captured.F1-wilson.values`) and two levels down in the parity file were all refused.
- The unreadable-file path for every row citing each file (Attack 2), F14 included.
- The five failing-at-`8ef3266` tests fail for the reason they name (copied into `mutold/tests`, run with `PYTHONPATH=mutold\src`: `5 failed, 1 passed`; the passing one is the committed-files check), and each would fail again if its hook were removed (they assert the error type).
- The commit's 8ef3266 claim: `"wilson_lo": 0.9` planted gives exit 0, `matched 35, not matched 0`, all four F1*-wilson rows `matched`, at `8ef3266`.

## Could not check

- The Linux side of my plants: I ran them on Windows only. CI run 37490988930 (`ci/36bfb2b-...`, workflow `ci`) read `completed` / `success` at the end of this lens; that is the orchestrator's gate, not re-run here, and it runs no plant.
- Whether any Newcombe or `oracles_v1.json` array was ever committed with a repeated entry: the committed files have none (`examples` labels unique, `rows` cell sets unique, every `values` an object), so B1 is a latent hole, not a wrong number in the current report.
