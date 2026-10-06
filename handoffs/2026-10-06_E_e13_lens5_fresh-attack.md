**Verdict: PASS. Zero blockers. Repair 4 closes L4-B1 (every repeated-key shape I tried, including keys spelt with `\u` escapes, now makes the file unreadable, F13 or F13b `not_matched`, exit 6) and L4-B2 (the 9 / 8 / 2 split re-derived independently). One false count sentence survives outside the repair's scope, in the E13 handoff (N1 below); the brief's blocker list does not cover handoff prose, so it is recorded, not graded.**

# E13 lens 5 - fresh attack - on `38e7ffc` (E13 repair 4; Tuesday 6 October 2026)

Scope: a cold lens on `git show 38e7ffc` (repair 4, by the orchestrator, on `b672c32` repair 3 + the lens-4 note `8bb63e4`), DEC-12 (i) because L4-B1 changes how the F13 / F13b gates read their input files. Four detached worktrees under `scratchpad/e13r4lens/`: `tip`, `mut` and `ps` at `38e7ffc`, `base` at `8bb63e4`. Every Python process ran with `PYTHONPATH=<worktree>/src` and printed `...\e13r4lens\<worktree>\src\proofpack\__init__.py` before I used its numbers. Each mutant in `mut` was undone with `git checkout --`; `git status --short` was empty after each. The copied test file in `base` was deleted after use. Nothing pushed; I did not run `ci_gate.sh` (I read the gate's run list only).

Environment: Windows 11, CPython 3.14.6, `PYTHONIOENCODING=utf-8 PROOFPACK_REQUIRE_DOCX=1 PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, `PROOFPACK_ASAH_VECTORS` unset.

## Blockers

None.

## Attack 1 (L4-B1): other ways to make the JSON parse drop or merge data

Script `scratchpad/e13r4lens/probe.py`: copy `fixtures/r/` to a temporary directory, plant, patch `fx.r_captures_dir`, then `load_r_captures(d, vectors=None)` and in-process `main(["fixtures", "--offline", "--r-captures", "--out", ...])`. Measured at `38e7ffc`:

| plant | unreadable | exit | F13 | F13b |
|---|---|---|---|---|
| committed copy unchanged | none | 0 | suite_only, 2.78e-17, "recorded 16" | matched, 13 |
| lens 4: plain duplicate `"s100b auc"`, bad pair first | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| lens 4: duplicate inner `"engine"`, bad first | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| lens 4: duplicate top-level `"values"`, bad object first | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| `"s100b\u0020auc"` (escaped space), bad first | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| `"\u0073100b auc"`, bad first | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| every character of the key escaped, bad first | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| two lone-surrogate keys `"\ud800"` | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| top-level `"zz": [{"a": 1, "a": 2}]` (duplicate inside an array of objects) | comparison, DuplicateJSONKeyError | 6 | not_matched | matched |
| UTF-8 BOM before the comparison file | comparison, JSONDecodeError | 6 | not_matched | matched |
| a second document after the first (`{}`, or the whole file twice) | comparison, JSONDecodeError | 6 | not_matched | matched |
| F13 `engine` `NaN` | none | 6 | not_matched, "no engine and R numbers" | matched |
| F13 `tolerance` `Infinity` | none | 6 | not_matched, "tolerance not 1e-06" | matched |
| F13 `engine` `1e400` (parses to inf) | none | 6 | not_matched, "no engine and R numbers" | matched |
| F13 `engine` a 401-digit integer | none | 6 | not_matched, `oracle_error: OverflowError` | matched |
| F13 `engine` a 5000-digit integer (over Python's 4300-digit limit) | comparison, ValueError | 6 | not_matched | matched |
| `proc_asah.json`: duplicate `"s100b auc"` in `values`, bad first | proc, DuplicateJSONKeyError | 6 | not_matched, `oracle_file_unreadable: fixtures/r/proc_asah.json (DuplicateJSONKeyError)` | matched |
| `proc_asah.json`: duplicate top-level `"schema"` | proc, DuplicateJSONKeyError | 6 | not_matched | matched |
| `proc_asah.json`: BOM | proc, JSONDecodeError | 6 | not_matched | matched |
| `proc_asah.json`: `"s100b auc": NaN`, comparison's `proc_asah_sha256` resealed to match | none | 6 | not_matched, "R value not proc_asah.json's: s100b auc" | matched |
| `rms_val_prob_f4.json`: duplicate `"val.prob Slope"`, bad first | valprob, DuplicateJSONKeyError | 6 | suite_only | not_matched, n 0, `oracle_file_unreadable: ... (DuplicateJSONKeyError)` |
| `rms_val_prob_f4.json`: `"val.prob Slope": NaN` | none | 6 | suite_only | not_matched, "oracle value not finite (nan): val.prob Slope" |
| `rms_val_prob_f4.json`: `"val.prob Slope"` a 401-digit integer | none | **5** | - | - (see N2) |
| `rms_val_prob_f4.json`: `"val.prob Slope"` as the string of its own value | none | 0 | suite_only | matched, 13 (see N3) |
| comparison file top-level `"zz"` nested 100000 deep | none (RecursionError escapes) | **5** | not_matched, `oracle_error: RecursionError` | not_matched, same (see N2) |
| comparison file top-level `"status": "not_matched"` | none | 0 | suite_only | matched (lens 4 N3, see Attack 3) |

`json.loads` decodes `\u` escapes before the `object_pairs_hook` sees a key, so an escaped spelling is the same key and is refused. `NaN` / `Infinity` / `-Infinity` literals are accepted by the parser but refused where numbers are compared (`_json_number` in `f13_recorded_outcome`, `_number` in `compare_row`, both `math.isfinite`). An unreadable comparison file or `proc_asah.json` gives F13 `not_matched` and exit 6, never `no_oracle_recorded` (`f13_oracle` checks `unreadable` before absence); an unreadable `rms_val_prob_f4.json` gives F13b the same (`f13b_oracle`). **Could not break.**

**In the r-captures job (vectors read).** Every engine-side reader in the job goes through `load_r_captures`: `scripts/r_f13_compare.py:49`, `tests/test_day12_r_captures.py` (lines 143, 157, 405, 525, 747) and `proofpack fixtures --r-captures`. Measured in the job's shape (`load_r_captures(d, vectors=<a vectors file>)`, `compare_row(r_capture_rows(caps)[0], {})`): a duplicate `"s100b auc"` in `proc_asah.json` gives F13 `not_matched`, `oracle_file_unreadable: fixtures/r/proc_asah.json (DuplicateJSONKeyError)`. The one job-side reader that does not use the hook is `scripts/r_capture_drift.py:82-83` (plain `json.loads` on the committed and fresh captures); see N4.

**Mutants** (each against `test_e13_repair4.py test_e13_repair3.py test_day12_r_captures.py test_e12_repair3.py test_e12_repair4.py test_fixtures_cmd.py`; 130 tests):

| mutant | result |
|---|---|
| M1 hook on the comparison file only | 2 failed (the two `proc_asah` / `rms_val_prob_f4` parameters) |
| M2 `DuplicateJSONKeyError` caught as absent (`no_oracle_recorded`) | 4 failed |
| M3 hook lets a repeated object-valued key through | 2 failed |
| M4 hook refuses only a repeated object-valued key | 2 failed (the top-level `"schema"` parameters) |

All four die.

## Attack 2 (L4-B2): the 9 / 8 / 2 split, re-derived

Script `scratchpad/e13r4lens/split.py`, written without `_numbers` or `_register_class_lookup`: a fresh `parity.compute()` round-tripped through `json.dumps`, my own walk of each entry's `value`, run twice (lists only, as the helper does; and lists and dicts). Both give the same: **67 values; keys per value 1: 48, 2: 9, 3: 8, 4: 2** (48 + 9 + 8 + 2 = 67; 19 with more than one key; 0 with none). The two 4-key values are `F4-register` `ece_10_equal_width` and `ece_10_equal_mass`, as lens 4 said. The new sentences are true:

- `src/proofpack/parity.py:21-23`: "19 of the 67 values equal more than one entry: 9 equal two, 8 three and 2 four";
- `tests/test_f16_parity_native.py:97-98`: "19 of the 67: 9 by two, 8 by three, 2 by four";
- the new `Counter` assertion in `test_e13r3_b1_*` (`[(2, 9), (3, 8), (4, 2)]`).

**One count sentence elsewhere is still false**: `handoffs/2026-10-05_E13.md:123` (the E13 handoff, `01b615c`): "19 of the 67 values equal two or three fresh entries". See N1. `git grep "two or three"` at `38e7ffc` finds it nowhere else in `src/` or `tests/` except the quotation inside `tests/test_e13_repair4.py`.

## Attack 3 (lens 4 N2 / N3): does any shipped sentence claim every field of the comparison file is checked?

No. Read: `f13_recorded_outcome`'s docstring (lists the checks: schema, fixture, the four input fields, `engine_sha`, and per name `engine`, `r`, `tolerance`; says "the file's `abs_deviation` and `within` are not read"); the row reason ("max abs deviation ..., each within 1e-6 as recomputed here from the recorded engine and R numbers"); `t12.SUITE_ONLY_RECORDED_TEXT` ("deviations recomputed by this command from the recorded values"); `t12.values_cell`'s docstring ("any other recorded name, or any of them missing, makes the row `not_matched`" - scoped to `values`, and now true with repeated keys refused); `fixtures/r/README.md:60-64` (says what the job writes, not what the command checks); the new `load_r_captures` and `DuplicateJSONKeyError` docstrings. None says the file's top-level `status`, `reason` or `max_abs_deviation` is read. Measured: top-level `"status": "not_matched"` still gives exit 0, F13 `suite_only` with the recomputed 2.78e-17. Lens 4's N2 / N3 stand as non-blocking (carried as N5).

## Attack 4: the commit message's figures and claims

PENDING (being measured).

## Non-blocking (record and carry)

- **N1. A false count sentence in the E13 handoff.** `handoffs/2026-10-05_E13.md:123`, in "Open blockers (lens 3 fresh attack, at `ec989ed`)": "19 of the 67 values equal two or three fresh entries". Two of the 19 equal four (Attack 2). Lens 4 named the code, test docstring and commit message copies; repair 4 fixed the first two and its own commit message is right, but the handoff Josh reads still carries the old figure. Not in the brief's blocker list (code, docstring, test name, commit message), so not graded a blocker. Fix: say it in the repair-4 / closing handoff ("the E13 handoff's 'two or three' is wrong: 9 equal two, 8 three, 2 four"); do not rewrite the dated note.
- **N2. Two parse shapes escape as an internal error (exit 5), not a row.** A 401-digit integer for an F13b R value: `_number` catches `TypeError` and `ValueError` but not `OverflowError` (`float(10**400)`), and the compare loop in `compare_row` is outside a `try`, so `proofpack fixtures` prints "internal error: OverflowError: int too large to convert to float", exit 5, and writes no report. A comparison file nested 100000 deep: `RecursionError` is neither `ValueError` nor `OSError`, so it escapes `load_r_captures`; the report is written with F13 and F13b both `not_matched` (`oracle_error: RecursionError`) and then the `--r-captures` line raises, exit 5. Both are the same at `8bb63e4` (pre-existing), both fail closed (non-zero, no `matched`). Suggest catching `OverflowError` in `_number` and `RecursionError` in `load_r_captures`.
- **N3. An F13b R value written as a JSON string is accepted.** `_number` uses `float(value)`, so `"1.194512479643566"` compares as the number (F13b matched, exit 0). Pre-existing, value-preserving (nothing dropped), but `f13_recorded_outcome` refuses strings for F13 and `f13b_oracle` does not; `float` also accepts `"1_194.5"` and surrounding whitespace.
- **N4. `scripts/r_capture_drift.py` reads both captures with plain `json.loads`.** Inside the job, a repeated key in the committed or the fresh capture is merged silently by the drift check. Everything after it reads through the hook (the copied fresh files through `r_f13_compare.py`, the day12 tests and `fixtures`), so the job still fails closed; the drift step alone can report "no drift" over a file with a dropped pair. Suggest the same hook there.
- **N5. Lens 4's N2 / N3 carried**: fields the command does not read (nested pairs, extra top-level keys, the file's own `status` / `max_abs_deviation`) are not refused. No shipped sentence claims them (Attack 3).
- **N6. Label drift.** The `DuplicateJSONKeyError` docstring says "lens 4 FA-B1" and the new comment in `test_f16_parity_native.py` "lens 4 FA-B2"; the lens-4 note names them `L4-B1` / `L4-B2` (the commit message and `test_e13_repair4.py` use `L4-`). Cosmetic.
- **N7.** The new `Counter` assertion in `test_e13r3_b1_*` passes at `8bb63e4` too (the split is a property of the fixture data, not of the code); the commit says it "pins that split", not that it fails at `8bb63e4`. True as written. The sentence itself is pinned by `test_e13r4_b2_the_false_count_sentence_is_gone`.

## Could not break

- Repeated keys in any object, at any depth, in each of the three files, including escaped and surrogate spellings; inside arrays of objects.
- NaN / Infinity / 1e400 / 401-digit and 5000-digit integers at the F13 recorded comparison; NaN at F13b; BOM and trailing documents.
- F13 / F13b `not_matched` and exit 6 (never `no_oracle_recorded`) for each unreadable file, outside the job and in the job's shape.
- The 9 / 8 / 2 split, re-derived without the repository's helpers.
- Four mutants of the hook, each killed.

## Could not check

- PENDING.
