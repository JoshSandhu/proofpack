**Verdict: FAIL. Two blockers. B1: a repeated Table III row in `newcombe1998_paired.json` (same `e f g h`) placed first is still dropped silently when its `method10` sides are named `"lower "` / `"Lower"` (or its values sit under `"method10 "` beside an empty `"method10"`): `F5-newcombe-paired` stays `matched`, `fixtures --offline` exits 0 at `ad028a6`, against the commit's headline "a repeated entry inside a list no longer drops silently". B2: the new reason `oracle_entry_ambiguous: <where> is a JSON NoneType, not an object` (and `... JSON float`, `... JSON str`, `... JSON list` for a list of distinct pairs) states that an entry which repeats nothing is ambiguous, names Python types as JSON types, and is raised as `DuplicateJSONKeyError`, whose docstring says a JSON object named one key twice. Row statuses for B2 are right (`not_matched`, exit 6); the defect is the sentence. Everything else the commit claims reproduces (see the tables).**

# E13 N0 lens 2 (fresh attack, DEC-12 (i)) on engine ad028a6 - Tuesday 6 October 2026

Cold adversarial lens on `ad028a6` (repair of N0 lens B1) on `2e844a0` (that lens's note) on `36bfb2b` (the N0 change). The repair adds `_unique()` (refuses a value name built twice from `newcombe1998_paired.json` `rows` and `newcombe_table2.json` `examples`), `_object_entry()` (each `captured.<key>.values` and `register.<key>` in `oracles_v1.json` must be a JSON object) and `except DuplicateJSONKeyError` -> `not_matched`, `oracle_entry_ambiguous: ...` in `compare_row`.

Method. Detached worktrees under the session scratchpad (`n0lens2/new` at `ad028a6`, `n0lens2/old` at `36bfb2b`), `PYTHONPATH=<tree>\src` as a Windows path, proven with `python -c "import proofpack;print(proofpack.__file__)"` (printed `...\n0lens2\new\src\proofpack\__init__.py` and `...\n0lens2\old\src\proofpack\__init__.py`). Plants were made by two scratch scripts (`plant.py`: run `python -m proofpack.cli fixtures --offline --out <tmp>` unplanted, plant one file, run again, restore with `git checkout -- fixtures/<file>`, print every row whose status or reason changed; `sweep.py`: every `captured` and `register` entry of `oracles_v1.json` turned into a list of pairs in turn). `git status --short` was empty in both trees after every batch.

## Blockers

### B1. A repeated paired row whose side names differ by whitespace or case is dropped silently; F5-newcombe-paired stays matched, exit 0

`_paired_rows` reads `row["method10"][side]` only `if side in row["method10"]`, for `side` in `("lower", "upper")`, and ignores every other key of the row and of `method10`. `_unique()` refuses a *built name* seen twice, not a *row* seen twice, so a second row for the same cells whose sides are not spelt exactly `lower` / `upper` contributes no name and is never compared. F14 does not have this hole (it reads `ex[method]["lower"]` unconditionally: the same plant there gives `oracle_error: KeyError`, exit 6, measured), nor do the `captured` values (an extra `"wilson_lo "` gives `engine value missing: wilson_lo `, exit 6, measured).

Repro (in `n0lens2/new`, at `ad028a6`): insert one line as the first element of `rows` in `fixtures/newcombe1998_paired.json` (the real row `{"e": 36, "f": 12, "g": 2, "h": 0, "method10": {"lower": 0.0569, "upper": 0.3404}}` stays where it is), then `python -m proofpack.cli fixtures --offline --out <dir>`:

| planted first element of `rows` | exit | summary line | F5-newcombe-paired |
|---|---|---|---|
| `{"e": 36, "f": 12, "g": 2, "h": 0, "method10": {"lower ": 0.9, "upper ": 0.9}},` | 0 | `rows 46: matched 35, not matched 0, ...` | `matched`, 35 values compared, max deviation 4.876e-05, reason `None` |
| `{"e": 36, "f": 12, "g": 2, "h": 0, "method10": {"Lower": 0.9, "Upper": 0.9}},` | 0 | same | same |
| `{"e": 36, "f": 12, "g": 2, "h": 0, "method10": {}, "method10 ": {"lower": 0.9, "upper": 0.9}},` | 0 | same | same |

The same three give exit 0 at `36bfb2b` (pre-existing). Graded a blocker because (a) it is the shape B1 named - a second row for one Table III cell set, placed first, with 0.9 / 0.9 in the file's bytes that is never compared while the row reads `matched` - in the one file whose reader the repair touched, and (b) the commit message's first sentence, "a repeated entry inside a list no longer drops silently", is false as measured: the commit's narrower clause ("refuses a name built twice") is true. The brief's attack 1 names keys "differing only by type or whitespace" explicitly. Suggested repair: in `_paired_rows`, refuse a repeated cell set (key the row by `(e, f, g, h)` with `int` and not `bool` required), require `method10` to be an object whose keys are a non-empty subset of `{"lower", "upper"}`, and refuse any other key in the row except the known ones (`e`, `f`, `g`, `h`, `method10`); a plant test for each that fails at `ad028a6`.

### B2. The reason `oracle_entry_ambiguous: ... is a JSON NoneType, not an object` states something false

`_object_entry` raises `DuplicateJSONKeyError(f"{where} is a JSON {type(value).__name__}, not an object")`, and `compare_row` writes it as `oracle_entry_ambiguous: {exc}`. Measured reasons at `ad028a6` (each row `not_matched`, exit 6; at `36bfb2b` the same plants gave `oracle_error: TypeError`):

| plant in `oracles_v1.json` | reason written to `fixtures_report.json` |
|---|---|
| `captured.F1-wilson.values` = `null` | `oracle_entry_ambiguous: captured.F1-wilson.values is a JSON NoneType, not an object` |
| `captured.F1-wilson.values` = `0.5` | `oracle_entry_ambiguous: captured.F1-wilson.values is a JSON float, not an object` |
| `captured.F1-wilson.values` = `"x"` | `oracle_entry_ambiguous: captured.F1-wilson.values is a JSON str, not an object` |
| `captured.F1-wilson.values` = `[["wilson_hi", 0.366...], ["wilson_lo", 0.255...]]` (distinct names) | `oracle_entry_ambiguous: captured.F1-wilson.values is a JSON list, not an object` |
| `register.F2` = `null` | `oracle_entry_ambiguous: register.F2 is a JSON NoneType, not an object` |

False on two counts: none of these entries is ambiguous (a null, a number, a string and a list of distinct pairs each have one reading; they are the wrong type), and JSON has no `NoneType`, `float`, `str` or `list` (its names are null, number, string, array). The exception type carries the same error: `DuplicateJSONKeyError`'s docstring reads "A JSON object in an R capture file, an oracle file ... or the committed F16 parity file names one key twice", and it is now raised for a `null` register entry and for a repeated *list* entry, neither of which is a repeated key in an object. This is report text a customer hands on (`fixtures_report.json` is the installation record). Graded under the brief's "a false sentence in ... reason string". Suggested repair: a separate `OracleEntryShapeError` with reason `oracle_entry_not_an_object: register.F2 is null (a JSON object is required)` using JSON names, and keep `oracle_entry_ambiguous` (or `oracle_entry_repeated`) for `_unique`'s case; widen the `DuplicateJSONKeyError` docstring if `_unique` keeps raising it.

## Attack 1: every place an oracle file's content becomes compared values

`grep -n "dict(\|\.update(\|setdefault\|zip(\|{\*\*\|for .* in doc" src/proofpack/fixtures.py`, then each reader:

| reader | file / entry | shape that could collapse | at `ad028a6` |
|---|---|---|---|
| `_captured` | `oracles_v1.json` `captured.<k>.values` | list of pairs | refused (`_object_entry`), every citing row `not_matched` (sweep below) |
| `_register` / `_register_oracle` | `register.<k>` | list of pairs | refused; already `oracle_error: TypeError` at `36bfb2b` (see N2) |
| `_register` (F3_bootstrap) | `register_decimals.F3_bootstrap` as `[["_default", 9], ["_default", 2]]` | list of pairs | `oracle_error: AttributeError`, F3-bootstrap and F9-cluster-bootstrap `not_matched` |
| whole `captured` / whole `register` as a list of pairs | | | `oracle_error: TypeError` on every citing row (18 / 11 rows) |
| `_paired_rows` | `newcombe1998_paired.json` `rows` | repeat with equal built name | refused (`... appears twice`) |
| | | repeat with `e` as `"36"` (string) | refused: builds the same name |
| | | repeat with `e` as `36.0` or `true` | extra name, `engine value missing: e 36.0 ...` / `e True ...`, `not_matched` |
| | | repeat with sides `"lower "` / `"Lower"` / under `"method10 "` | **dropped, `matched`, exit 0: B1** |
| | | real row's `method10` as a list of pairs | `oracle value missing`, `not_matched` |
| | | real row's `method10` gains `"lower ": 0.9` | ignored, `matched`, exit 0 (N1) |
| `_f14_oracle` | `newcombe_table2.json` `examples` | repeat, equal label | refused |
| | | repeat, label + trailing space / NBSP | extra names, `engine value missing`, `not_matched` |
| | | repeat with sides `"lower "` | `oracle_error: KeyError`, `not_matched` |
| | | `method10` as list of pairs | `oracle_error: TypeError` |
| | | example gains `"method10 ": {...0.9}` | ignored, `matched`, exit 0 (N1) |
| `_f4_oracle`, `_f4_register_oracle` | `f4_expected.json` fixed names | `hand` gains `"oe ": {"value": 0.9}` | ignored, exit 0 (N1); `hand` as list of pairs: `oracle_error: TypeError` |
| `f13_recorded_outcome` | R comparison file | `values` / `proc.values` not an object | `_as_dict` -> `{}` -> "no engine and R numbers", `not_matched` (read, not planted: no R) |
| `f16_behaviour` -> `parity.compare` / `_flatten` | `f16_parity_native.json` | nested list, extra non-number element | ignored, F16 `suite_only`, exit 0 (N3) |
| `compare_row` | all | `_number()` | union of `row.compares` and the oracle's keys, so a missing or extra name is `not_matched`; every row has `compares` set (grep) |

Row-level sweep (attack 3), `sweep.py` at `ad028a6`: each of the 17 `captured` entries and 10 `register` entries rewritten in turn as a list of distinct pairs. Every run exited 6, and the set of `not_matched` rows equalled exactly the set of rows whose `oracle_source.entry` names that entry in the baseline report (`mismatches 0`), e.g. `captured.F6-homogeneity` -> `F6-closed-form`, `F6-p`; `register.F3_bootstrap` -> `F3-bootstrap`, `F9-cluster-bootstrap`; `register.F2` -> `F2-register`. No citing row stayed `matched` or became anything other than `not_matched`.

## Attack 4: the previous lens's N1 (the two `--check` scripts)

Still true at `ad028a6`, which does not touch `scripts/` (`git diff 36bfb2b ad028a6 --stat`: `fixtures.py`, the test file, the previous note). With `"wilson_lo": 0.9,` planted before the real key in `oracles_v1.json` and a repeated `"F1-clopper-pearson.cp_hi"` (0.9 first) in `f16_parity_native.json`: `scripts/capture_fixture_oracles.py --check` printed `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`, exit 0; `scripts/f16_parity_native.py --check` printed `F16 native check: 894 entries, 0 failures`, exit 0. No sentence in the commit, the scripts or the tests claims either script detects a repeat (grep for `twice|repeat|duplicate` in both scripts and `tests/test_f16_parity_native.py`: none). Non-blocking, as before.

## Attack 5: the commit message's figures

Run in `wt-e13n0` at `ad028a6` (the only change in the tree was this untracked note), `PYTHONPATH=C:\Users\joshs\GPS\ProofPack\wt-e13n0\src`, import proven in each shell:

| command | Git Bash | PowerShell 5.1 | commit message |
|---|---|---|---|
| `python -m pytest -q -p no:cacheprovider` | 2327 passed, 4 skipped (297 s) | 2327 passed, 4 skipped (289 s) | 2327 passed, 4 skipped |
| `... -m day13` | 124 passed | 124 passed | 124 |
| `... -m day12` | 199 passed, 3 skipped | 199 passed, 3 skipped | 199/3 |
| `python -m ruff check .` / `ruff format --check .` | All checks passed / 348 files already formatted | same | clean |
| `python -m proofpack.cli fixtures --offline --out <dir>` | exit 0, `matched 35, not matched 0` (in `n0lens2/new`) | exit 0, `matched 35, not matched 0` | exit 0 |
| `tests/test_e13_n0_duplicate_keys.py` against `36bfb2b`'s `src` | 4 failed, 6 passed: the four new tests | - | 4 of 4 fail |

The orchestrator's gate run for `ad028a6` (`ci`, run 37494780226, branch `ci/ad028a6-...`) read `completed` / `success` via `gh run list`; not re-run here, and it runs no plant.

## Non-blocking

- **N1. Fixed-name readers ignore a sibling key that differs only by whitespace.** `newcombe1998_paired.json` real row gaining `"lower ": 0.9`, `newcombe_table2.json` example gaining `"method10 ": {"lower": 0.9, "upper": 0.9}`, `f4_expected.json` `hand` gaining `"oe ": {"value": 0.9}`: each exit 0, no row changed, at both `ad028a6` and `36bfb2b`. No value is replaced (each reader takes the exact name), so this is not a collapse; it is the same "a reviewer sees two `lower`s" ambiguity as B1 without a repeated row. Folding a strict-keys check into B1's repair for `_paired_rows` would close the paired case; F14 and F4 would need the same.
- **N2. The register half of `_object_entry` was not a silent drop before.** At `36bfb2b` a `register.F2` list of pairs (with a repeat, 0.9 first) already gave `F2-register` `not_matched`, `oracle_error: TypeError` (the tolerance comprehension hashes each pair). `test_e13n0_b1_a_register_entry_written_as_a_list_is_not_matched` fails at `36bfb2b` only on its reason assertion (`'register.F2 is a JSON list, not an object' in 'oracle_error: TypeError'`). The commit's parenthetical "(a list of pairs passed to dict() kept the last of two equal names)" is true of `captured` only; it does not claim the register path was silent, so not graded false.
- **N3. F16's `_flatten` ignores structure and non-numbers in a `closed` / `irls` / `bootstrap` list.** `F4.E6.calibration_block.ece_equal_width_10.edges` (tol `closed`) with `{"x": 0.9}` appended, or the list wrapped in one more `[...]`: exit 0, F16 `suite_only`, "894 of 894 agree", at both trees. F16 is never `matched`, and the rule mirrors the site's `compareEntry`; pre-existing.
- **N4. Oracle numbers are coerced from strings.** `_paired_rows` uses `float()` and `compare_row`'s `_number()` accepts a string: `"0.0569"` (paired) and `"0.2552885198782742"` (`F1-wilson.wilson_lo`) written as JSON strings stay `matched`, exit 0, at both trees; `float()` also accepts `"0.25_5"`. The number compared equals the string's; no wrong number results. `_json_number` (the F13 path) already refuses strings; the two readers could use it.
- **N5. `int(doc["decimals"])` in `_f5_newcombe_paired_oracle` truncates** (`1.9` -> 1) and accepts `"1"`: both plants exit 0 with a tolerance loosened from 5e-5 to 0.05. A planted `1` does the same, so this is a gate on the file's honesty, not a collapse.
- **N6. `excluded` is not checked against `rows`.** An `excluded` entry naming `e 36 f 12 g 2 h 0 method10 lower` (which is compared) leaves the row `matched` and puts "e 36 f 12 g 2 h 0 method10 lower not compared: ..." into the row's `oracle_source.detail`, a sentence that is then false. Pre-existing, needs a planted file.

## Could not break

- The three repros of the previous lens's B1 at `ad028a6`: each `not_matched`, exit 6 (`... 'e 36 f 12 g 2 h 0 method10 lower' appears twice`; `... '56/70 - 48/80 method10 lower' appears twice`; `captured.F1-wilson.values is a JSON list, not an object`); all three `matched`, exit 0, at `36bfb2b`.
- A repeated key differing only by type: `e` as `"36"` collides with `36` and is refused; `36.0`, `true`, a trailing-space or NBSP label build a different name and are `not_matched` by the union with `row.compares`.
- Every row citing a rewritten `captured` or `register` entry goes `not_matched`, exit 6 (sweep, 27 of 27).
- The `except DuplicateJSONKeyError` arm: the only raisers inside a row's oracle callable are `_object_entry` and `_unique` (the hook's own raise is caught in `load_oracles`, `load_r_captures` and `f16_behaviour`); it sits after `OracleFileUnreadable` and `RCaptureInputMismatch` (both `ValueError`, disjoint classes) and before the catch-all.
- `tests/test_e13_n0_duplicate_keys.py` copied into `n0lens2/old/tests` and run with `PYTHONPATH=old\src`: `4 failed, 6 passed`; the four failures are exactly the four new B1 tests, three on `'matched' == 'not_matched'` and the register one on its reason assertion (N2).

## Could not check

- The Linux side of my plants (Windows only). The orchestrator's gate on `ad028a6` is not re-run here.
- Whether the site's `compareEntry` flattens the way `_flatten` does (N3): `proofpack-site` is outside this lens.
