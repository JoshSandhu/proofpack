**Verdict: FAIL. One blocker, B1: when `rows` in `newcombe1998_paired.json` is a JSON object or a string rather than an array, the new reason reads `oracle_entry_malformed: newcombe1998_paired.json rows[0] is a JSON string, not an object` - there is no `rows[0]`, and the thing that is malformed (`rows`) is an object or a string, not "a JSON string" at index 0. The status is right (`not_matched`, exit 6); the sentence is false, and edf3ddf introduced it (at ad028a6 the same input gave `oracle_error: TypeError`).**

# E13 N0 lens 3 (fresh attack, DEC-12 (i)) on engine edf3ddf - Tuesday 6 October 2026

Cold adversarial lens on `edf3ddf` (repair of lens 2's B1/B2) on `6aa3619` / `ad028a6` / `2e844a0` / `36bfb2b`. Every figure in the commit message reproduces in both shells; every input within claims (a) and (b) gives its rows `not_matched`, exit 6; the one defect is a false reason string the repair introduced.

## Blockers

### B1. A non-array `rows` is reported as a malformed `rows[0]` of type string

`_paired_rows` labels each element `f"{NEWCOMBE_PAIRED_FILE} rows[{i}]"` from `enumerate(doc["rows"])` without first checking that `rows` is an array. When `rows` is an object, Python iterates its keys; when it is a string, its characters. Either way the first item is a Python `str`, `_object_entry` maps it to "string", and the row's reason states a fact about an element that does not exist.

Repro (detached worktree at `edf3ddf`, `PYTHONPATH=<tree>\src`): rewrite `fixtures/newcombe1998_paired.json` with `rows` replaced by `{"r0": <row 0>, "r1": <row 1>, ...}` (or by `"abc"`), then `python -m proofpack.cli fixtures --offline --out <dir>`:

| `rows` planted as | edf3ddf | ad028a6 |
|---|---|---|
| object `{"r0": {...}, ...}` | exit 6, `F5-newcombe-paired` `not_matched`, `oracle_entry_malformed: newcombe1998_paired.json rows[0] is a JSON string, not an object` | exit 6, `oracle_error: TypeError` |
| string `"abc"` | exit 6, same reason | exit 6, `oracle_error: TypeError` |

Graded a blocker on the same bar lens 2 used for its B2 (a false sentence in a new reason string; `fixtures_report.json` is the installation record) and because the false text is new in the commit under review. No value is dropped. Suggested repair: `if not isinstance(doc["rows"], list): raise OracleEntryMalformed(f"{NEWCOMBE_PAIRED_FILE} rows is a JSON {type}, not an array")` before the loop, plus a test with `rows` as an object that fails at `edf3ddf` on the reason.

## Method

Detached worktrees under the session scratchpad: `n0lens3/new` at `edf3ddf`, `n0lens3/old` at `ad028a6`; `PYTHONPATH=<tree>\src` as a Windows path, proven with `python -c "import proofpack;print(proofpack.__file__)"` (printed `...\n0lens3\new\src\proofpack\__init__.py` and `...\n0lens3\old\src\proofpack\__init__.py`). `plant.py` runs `python -m proofpack.cli fixtures --offline --out <tmp>` unplanted, plants one file (text replacement, so a repeated key survives into the bytes; anchors made CRLF-aware because the Windows checkout has CRLF), runs again, restores with `git checkout -- <file>`, and prints every row whose status, reason, count or deviation changed. `git status --short` was empty after every batch. Unplanted baseline at `edf3ddf`: exit 0, `rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only 7`.

## Attack 1: inputs within claims (a) and (b)

Claim (a), one repeated key per file (the hook is global, so one object per file proves the path; nested objects were also planted):

| plant | exit | rows changed |
|---|---|---|
| `oracles_v1.json` `register.F1` `"cp_hi": 0.9,` before the real one | 6 | all 29 rows citing the file `not_matched`, `oracle_file_unreadable: oracles_v1.json (DuplicateJSONKeyError)` |
| `f4_expected.json` top-level `"fixture"` repeated | 6 | F4-closed-form, F4-irls, F4-register, same reason |
| `newcombe_table2.json` `"label"` repeated inside one example | 6 | F14-newcombe, same reason |
| `newcombe1998_paired.json` `"decimals"` repeated; `"e"` repeated inside `rows[0]` | 6 | F5-newcombe-paired, same reason |
| `f16_parity_native.json` `F1-clopper-pearson.cp_hi` `"value": 0.9` before the real one | 6 | F16 `not_matched`, `oracle_file_unreadable: fixtures/f16_parity_native.json (DuplicateJSONKeyError)` |
| `r/proc_asah.json`, `r/f13_engine_comparison.json` `"schema"` repeated | 6 | F13 `not_matched`, `oracle_file_unreadable: fixtures/r/<file> (DuplicateJSONKeyError)` |
| `r/rms_val_prob_f4.json` `"schema"` repeated | 6 | F13b, same |
| a repeated key whose second spelling uses a JSON unicode escape (the underscore of `wilson_lo` written as the escape for U+005F; a `c` written as the escape for U+0063 in an object inside an array), fed to the hook directly | - | `DuplicateJSONKeyError` both times |

Claim (b), `newcombe1998_paired.json` (row 0 is `e 36 f 12 g 2 h 0`; row 7, `e 1 f 97 g 1 h 1`, carries `upper` only):

| plant (first element of `rows` unless said) | exit | F5-newcombe-paired reason |
|---|---|---|
| copy with `e` `"36"` and 0.9 / 0.9 | 6 | `oracle_entry_repeated: newcombe1998_paired.json rows: 'e 36 f 12 g 2 h 0 method10 lower' appears twice` |
| copy with only `upper` 0.9 | 6 | `oracle_entry_repeated: ... 'e 36 f 12 g 2 h 0 method10 upper' appears twice` |
| copy with `e` `36.0` | 6 | `engine value missing: e 36.0 f 12 g 2 h 0 method10 lower; ...` |
| `e 1 f 97 g 1 h 1` with `lower` 0.9 (the side the real row does not carry) | 6 | `engine value missing: e 1 f 97 g 1 h 1 method10 lower` |
| `e 9 f 9 g 9 h 9` with `lower` `true` | 6 | `engine value missing: e 9 f 9 g 9 h 9 method10 lower` |
| extra field `"x": 1` | 6 | `oracle_entry_malformed: newcombe1998_paired.json rows[0] fields ['e', 'f', 'g', 'h', 'method10', 'x']` |
| no `h` | 6 | `oracle_entry_malformed: ... rows[0] fields ['e', 'f', 'g', 'method10']` |
| `method10` `{}` | 6 | `oracle_entry_malformed: ... rows[0].method10 sides []` |
| `method10` `null` / `[["lower", 0.9]]` | 6 | `... rows[0].method10 is a JSON null, not an object` / `... is a JSON array, not an object` |
| row `[36, 12, 2, 0]` / `true` / `1.5` | 6 | `... rows[0] is a JSON array` / `boolean` / `number`, `not an object` |
| `rows` emptied | 6 | `oracle value missing: ...` for all 35 names |
| `rows` an object / a string | 6 | **`... rows[0] is a JSON string, not an object` (B1)** |

Claim (b), `newcombe_table2.json` and `oracles_v1.json`:

| plant | exit | reason |
|---|---|---|
| second `56/70 - 48/80` example, 0.9 bounds, first | 6 | `oracle_entry_repeated: newcombe_table2.json examples: '56/70 - 48/80 method10 lower' appears twice` |
| example `method10` as an array of pairs | 6 | `oracle_error: TypeError` (not claimed; true) |
| `captured.F1-wilson.values` `null` | 6 | `oracle_entry_malformed: captured.F1-wilson.values is a JSON null, not an object` |
| `captured.F1-wilson.values` pairs with `wilson_lo` 0.9 first | 6 | `... is a JSON array, not an object` |
| `register.F1` `"x"` / `true` | 6 | `oracle_entry_malformed: register.F1 is a JSON string, not an object` / `... JSON boolean, ...` |

No input within (a) or (b) left a planted value uncompared with the row `matched` and exit 0.

## Attack 2: new sentences and reason strings

- `oracle_entry_repeated` is raised only by `_unique` (one name built twice from a list); every measured instance names the list and the repeated name, and is true.
- `oracle_entry_malformed` with `is a JSON <type>, not an object`: `_JSON_TYPE` maps `dict/list/str/int/float/bool/None` to `object/array/string/number/number/boolean/null`; the measured reasons used `null`, `array`, `string`, `boolean`, `number`, never a Python type name, and never "ambiguous". True for every element and entry that exists. False only for B1 (an element that does not exist).
- `rows[i] fields [...]` and `rows[i].method10 sides [...]`: true, though terse (the list is printed as a Python list repr and does not say which field is unknown or missing).
- `DuplicateJSONKeyError`'s docstring ("a JSON object ... names one key twice") is true again: after edf3ddf the only raiser is `_refuse_duplicate_keys` (grep), and the `except DuplicateJSONKeyError` arm in `compare_row` was removed; the three hook call sites (`load_oracles`, `load_r_captures`, `f16_behaviour`) each catch `ValueError` themselves.
- No stale `oracle_entry_ambiguous` remains in `src/`, `tests/` or any non-handoff file (grep).
- ad028a6's headline "a repeated entry inside a list no longer drops silently", within the readers it names (paired `rows`, F14 `examples`, `captured.<k>.values`, `register.<k>`): true at edf3ddf. Every repeated paired row or F14 example either builds a name already built (refused), builds a new name (`engine value missing`, `not_matched`), or raises (`not_matched`); none contributes nothing. Lens 2's three B1 spellings are now `oracle_entry_malformed` (the new tests, measured below).

## Attack 3: the committed oracle files still pass

Unplanted `fixtures --offline` at edf3ddf: exit 0, matched 35, not matched 0 (both shells, below). Every committed paired row has exactly the five fields and a non-empty `method10` within `{lower, upper}` (row `e 1 f 97 g 1 h 1` carries `upper` only and is accepted). No legitimate entry is refused.

## Attack 4: the commit message's figures

Run in `wt-e13n0` at `edf3ddf` (only change: this untracked note), `PYTHONPATH=C:\Users\joshs\GPS\ProofPack\wt-e13n0\src`, import proven in each shell:

| command | Git Bash | PowerShell 5.1 | commit message |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | 2334 passed, 4 skipped (315 s) | 2334 passed, 4 skipped (318 s) | 2334 passed, 4 skipped |
| `... -m day13` | 131 passed | 131 passed | 131 |
| `... -m day12` | 199 passed, 3 skipped | 199 passed, 3 skipped | 199/3 |
| `python -m ruff check .` / `ruff format --check .` | All checks passed / 349 files already formatted | All checks passed / 349 files already formatted | clean |
| `python -m proofpack.cli fixtures --offline --out <dir>` | exit 0, matched 35, not matched 0 | exit 0, matched 35, not matched 0 | exit 0 |
| `tests/test_e13_n0_duplicate_keys.py` against `ad028a6`'s `src` (`n0lens3/old`) | 8 failed, 9 passed: the 7 new r2 tests plus the register test on its new reason text | - | 7 of 7; the register test reads the new reason |

The orchestrator's gate run for `edf3ddf` (`ci`, run 37498562190, branch `ci/edf3ddf-...`) read `in_progress` via `gh run list` when checked; not re-run here.

## Non-blocking

- **N1 (carry). Fixed-name readers outside `_paired_rows` still ignore a sibling key that differs by whitespace.** Measured at edf3ddf, each exit 0, no row changed: a `newcombe_table2.json` example's `method10` gaining `"lower ": 0.9` beside the real `lower`; a top-level `"rows "` in `newcombe1998_paired.json` holding a 0.9 / 0.9 copy of row 0 (the paired reader is strict about each row's fields, not about the document's); `r/rms_val_prob_f4.json` `values` gaining `"<first name> ": 0.9` (`_r_values` picks `F13B_NAMES`). Lens 2 measured F4's `hand`. No sentence in this series claims F14, F13b, F4 or the paired document's top level is closed; the `OracleEntryMalformed` docstring describes when it is raised, not that every reader raises it.
- **N2.** `_paired_rows`'s docstring says a row "with a field other than" the five raises; a row missing a field raises too (measured: `fields ['e', 'f', 'g', 'method10']`). Incomplete, not false.
- **N3 (carry from lens 2, not re-measured; edf3ddf does not touch them).** F16 `_flatten` ignores structure and non-numbers; oracle numbers are coerced from strings (`float()` stays in `_paired_rows`); `int(doc["decimals"])` truncates; `excluded` is not checked against `rows`; `scripts/capture_fixture_oracles.py --check` and `scripts/f16_parity_native.py --check` read without the hook (edf3ddf touches no script).

## Could not break

- Claim (a): a repeated key in any object of each of the seven files (four oracle files, the F16 parity file, three R capture files) makes every citing row `not_matched`, exit 6, `oracle_file_unreadable: <file> (DuplicateJSONKeyError)`; a JSON-escaped second spelling is caught by the hook.
- Claim (b): every repeated paired row or F14 example, every non-object captured or register entry, and every paired row with an unknown, missing or misspelt field or side is `not_matched`, exit 6; the 35 committed values still compare.
- The exception chain in `compare_row`: `OracleEntryRepeated` and `OracleEntryMalformed` are disjoint `ValueError` subclasses placed after `OracleFileUnreadable` / `RCaptureInputMismatch` and before the catch-all; nothing earlier catches `ValueError` broadly.

## Could not check

- Linux behaviour of the plants (Windows only); the CI gate for edf3ddf is the orchestrator's.
- Whether lane S's site copy or any downstream reader shows `oracle_entry_*` reasons to a customer differently (`proofpack-site` outside this lens).
