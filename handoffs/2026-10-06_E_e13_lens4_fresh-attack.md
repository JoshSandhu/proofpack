**Verdict: FAIL. Two blockers: a duplicate JSON key re-opens B2 (exit 0 with a recorded pair 0.8 apart never recomputed), and the repair's new count sentence "19 of the 67 values equal two or three entries" is false (two of the 19 equal four).**

# E13 lens 4 - fresh attack - on `b672c32` (E13 repair 3; Tuesday 6 October 2026)

Scope: a cold lens on `git show b672c32` (repair 3, by the orchestrator, on `ec989ed` + the handoff `01b615c`), DEC-12 (i) because B2 changes what the F13 recorded gate reads. Three detached worktrees under `scratchpad/e13r3lens/`: `tip` and `mut` at `b672c32`, `base` at `ec989ed`. Every Python process ran with `PYTHONPATH=<worktree>/src` and printed `...\e13r3lens\<worktree>\src\proofpack\__init__.py` before I used its numbers. Each plant in `mut`/`base` was undone with `git checkout --` (and untracked copies deleted); `git status --short` was empty after each. Nothing pushed; I did not run `ci_gate.sh`.

Environment: Windows 11, CPython 3.14.6, `PYTHONIOENCODING=utf-8 PROOFPACK_REQUIRE_DOCX=1 PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, `PROOFPACK_ASAH_VECTORS` unset.

## Blockers

### L4-B1 - a duplicate key in `f13_engine_comparison.json` is never recomputed and the command exits 0 (B2 re-opened by another shape)

`load_r_captures` parses the comparison file with plain `json.loads`, so for a repeated key the last occurrence wins and the earlier one is discarded before `f13_recorded_outcome` sees it. The repair's new check (`extra = sorted(str(k) for k in values if k not in F13_NAMES)`) only sees the surviving dict.

**Repro (the real CLI, working-tree copy in `mut`):** insert, immediately before the existing `"s100b auc"` entry inside `values`,

```
"s100b auc": {"engine": 0.1, "r": 0.9, "tolerance": 1e-06, "abs_deviation": 0.8, "within": false},
```

then `PYTHONPATH=<mut>/src python -m proofpack.cli fixtures --offline --r-captures --out <dir>; echo $?`. Measured:

- **exit 0**; `rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 4, suite only (checked by this command, the test suite or a CI job) 7`;
- `r-captures: present_compared_in_rows_f13_f13b ... row F13 suite_only, row F13b matched`;
- F13 in `fixtures_report.json`: `suite_only`, `max_abs_deviation` 2.7755575615628914e-17, reason "...GitHub run 37332685741 recorded 16 values of the engine ...";
- `t12.values_cell(row)` **16**, `t12.status_text(row)` "compared inside a CI job; deviations recomputed by this command from the recorded values".

The file's bytes record 17 pairs; one (0.8 apart, `within: false` by the file's own account) is neither recomputed nor reported. The same plant with the bad pair placed **after** the good one gives exit 6 / `not_matched` (the bad one wins), so the outcome depends on key order. Two more shapes behave the same (in-process `main([...])` on a scratch copy, `fx.r_captures_dir` patched as `tests/test_e13_repair3.py` does): a duplicate inner `"engine"` (0.1 first, the real value second) and a duplicate top-level `"values"` (a bad object first) - each **exit 0, F13 `suite_only`, cell 16**.

**What catches it, and what does not.** In the committed copy, the sha256 pin `tests/test_capture_commit.py::test_capture_repair_b3_the_three_files_are_the_artefact_bytes_the_readme_records` fails (measured: 1 failed, 3 passed) - but that pin caught lens 3's extra-name plant too, which lens 3 graded a blocker and repair 3 fixed in the command. In any scratch copy nothing catches it; `proofpack fixtures` itself exits 0. Reachability is the same as lens 3's B2: a hand edit (the writer `scripts/r_f13_compare.py` serialises a dict and cannot emit a duplicate). The committed file has no duplicate key (checked with an `object_pairs_hook`).

This meets the brief's blocker definition literally: a recorded F13 shape that exits 0 while not every recorded pair was recomputed within 1e-6. It also makes the repair's new docstring sentence in `t12.values_cell` ("every one of `fixtures.F13_NAMES`, since any other recorded name, or any of them missing, makes the row `not_matched`") an incomplete account of what can be recorded.

**What would close it:** parse `f13_engine_comparison.json` (and `proc_asah.json`) with an `object_pairs_hook` that refuses a repeated key at any depth (the file becomes `unreadable`, F13 `not_matched`, exit 6), with a regression test for each of the three shapes above that fails at `b672c32`.

### L4-B2 - "19 of the 67 values equal two or three entries" is false: two of the 19 equal four (sentence violation, in code, a test docstring and the commit message)

Verbatim, new at `b672c32`:

- `src/proofpack/parity.py:21-22`: "(19 of the 67 values equal two or three entries)";
- `tests/test_f16_parity_native.py:96` (`_register_class_lookup` docstring): "with ``any`` a value matched by two or three keys - 19 of the 67 - passed";
- commit message: "19 of 67 values match two or three keys".

Measured with the test module's own `_register_class_lookup` logic in `mut` (fresh `parity.compute()` on win-amd64-cp314):

| keys matched | values |
|---|---|
| 2 | 9: F1c `wilson_lo`, `cp_lo`; F1d `wilson_hi`, `cp_hi`; F2 `sensitivity`, `specificity`; F6 `se_site1`, `se_site3`; F6 `chi2` |
| 3 | 8: F4 `brier`, `brier_ref`, `ipa`, `oe`, `intercept_large`, `slope`, `intercept`; F6 `chi2_p` |
| **4** | **2: F4-register `ece_10_equal_width` and `ece_10_equal_mass` (0.1955), each equal to `E6.calibration_block.ece_equal_mass_10.number.est`, `E6.calibration_block.ece_equal_width_10.number.est`, `F4-closed-form.ece_equal_mass_10` and `F4-closed-form.ece_equal_width_10`** |

9 + 8 + 2 = 19; the "19" is right, the "two or three" is not. (Lens 3's note carried the same wording; the repair copied it into the code.) Fix: "two to four entries", or "more than one entry", plus the commit message in the repair-4 note, and a `FALSE_AT_B672C32` entry.

## Attack 1 (B2): every shape I tried

In-process `main(["fixtures", "--offline", "--out", ...])` on a scratch copy of `fixtures/r/` (script `scratchpad/e13r3lens/b2probe.py`):

| plant | exit | F13 | Values cell | grade |
|---|---|---|---|---|
| committed copy unchanged | 0 | suite_only, 2.78e-17, "recorded 16" | 16 | - |
| extra name `S100B auc` (case) | 6 | not_matched, named | 0 | held |
| extra `s100b auc ` (trailing space) | 6 | not_matched | 0 | held |
| extra `s100b аuc` (Cyrillic a) | 6 | not_matched | 0 | held |
| extra `ｓ100b auc` (fullwidth; NFKC-equal to a real name) | 6 | not_matched | 0 | held |
| extra with U+200D, with NBSP, with a tab | 6 | not_matched | 0 | held |
| `roc.test conf.int lo` (an F13_OPTIONAL_NAMES name) | 6 | not_matched | 0 | held (the writer emits only the 16) |
| duplicate `s100b auc`, bad pair first | **0** | **suite_only** | **16** | **L4-B1** |
| duplicate `s100b auc`, bad pair last | 6 | not_matched | 0 | held |
| duplicate inner `engine`, bad first | **0** | **suite_only** | **16** | **L4-B1** |
| duplicate top-level `values`, bad object first | **0** | **suite_only** | **16** | **L4-B1** |
| `values` a list / `values` `{}` / one name's value a list | 6 | not_matched | 0 | held |
| a nested pair `{"second": {engine 0.1, r 0.9}}` inside a name's dict | 0 | suite_only | 16 | non-blocking N2 |
| extra top-level `values_2: {"ndka auc": <bad>}` | 0 | suite_only | 16 | non-blocking N2 |
| top-level `status: not_matched`, `max_abs_deviation: 0.8` | 0 | suite_only, 2.78e-17 | 16 | non-blocking N3 |

## Attack 2 (B3): the Values cell

- **Who reaches `SUITE_ONLY_RECORDED_TEXT`.** It needs `status` `suite_only`, no `evidence.measured_by_this_command`, and a numeric `max_abs_deviation`. In `fixtures.py` a numeric `max_abs_deviation` is set only by the compare loop (which then sets `matched`/`not_matched`) and by `ComparedInRunner`, which only `f13_oracle` raises. The `behaviour()` rows (F12, F16, F17, F19) carry `measured_by_this_command`; no `behaviour()` sets `max_abs_deviation`. F13b goes through the compare loop (`matched`, Values 13). T12 is rendered only by `cli.py:747` from the report built in the same process. So in-code only a fully recomputed F13 reaches the 16, and on that path `recomputed` is always 16 (any `continue` appends a problem). **The page prints what the command did.** Could not break.
- `values_cell` keys on the status text, not the row id: a hand-made row (any id) with `suite_only`, no evidence and a numeric deviation prints 16. Not reachable through `run_fixtures`; non-blocking N4.
- `_deviations_read` (the `--r-captures` line) uses the same predicate (`suite_only` and numeric `max_abs_deviation` -> `len(F13_NAMES)`): consistent with the cell.
- The T12 caption does not define "Values" at all (it defines only the largest deviation, "between engine and oracle values in the row"); the F13 row's Oracle and Tolerance cells print "—" beside Values 16 and a deviation. Pre-existing, non-blocking N5. `fixtures_report.json` keeps `n_values_compared` 0 for the same row (schema `allOf[1]`), so page and report now disagree on that number by design; the docstring says so.
- Mutants (against `test_e13_repair3.py test_t12.py test_e13_report_rows.py test_fixtures_cmd.py test_day12_r_captures.py`): M1 extra-name check off - 2 failed; M2 `values_cell` always `n_values_compared` - 2 failed; M3 any `suite_only` prints 16 - 1 failed; M5 any F13 row prints 16 - 1 failed; M4 reason back to `len(F13_NAMES)` - **101 passed** (an equivalent mutant: see N6).

## Attack 3 (B1): the "all keys" lookup on Linux

- Gate run **37480583988** (`ci/b672c32-1791297472-1665`, head `b672c32`): **completed success, 7 of 7**. `pytest + ruff` job 112327336793 on CPython 3.12.11: "2175 passed, 137 skipped in 230.15s" (2175 + 137 = 2312 = local 2308 + 4); day12 "196 passed, 3 skipped"; day13 "108 passed, 2204 deselected" - so `test_e13r3_b1_...` and its `== 19` held on Linux. The F16 tests carry no skip.
- Why it is not platform-fragile: the lookup compares register values with a fresh compute on the **same** platform; `all` adds no Linux risk because the committed key set is checked equal to the fresh one by `compare`. The 19 equalities are structural or exact rationals (0.0, 1.0, 0.9, the same function reached by two keys); if the two ECE values ever split on another platform each would still match two keys and the count would stay 19.
- **Keys empty -> miss** is handled (`not keys or ...`), but **no test pins it**: mutant `if not all(...)` (guard removed, so a value equal to no fresh entry passes) gives `tests/test_f16_parity_native.py` **19 passed**. Non-blocking N1.
- Old `any` restored in the helper: `test_e13r3_b1_deleting_any_one_key_of_a_multi_key_value_is_a_miss` **1 failed, 18 passed**. The claim "fails with the old any-lookup" holds.

## Attack 4: sentences and figures

- `FALSE_AT_EC989ED`: each of the three strings is present at `ec989ed` (`git show ec989ed:<path> | grep -c` = 1 each) and absent at `b672c32`. Copied into `base`, the two `parity.py` parameters fail; the test-file parameter passes (the copied test file brings its own rename: RG-N6 class, carried).
- `tests/test_e13_repair3.py` copied into `base`: **4 failed, 1 passed** - matches "4 of 5 fail at ec989ed (the fifth pins the count)". Of the four, `test_e13r3_b3_a_not_matched_f13_row_prints_n_values_compared` fails only with `AttributeError: ... no attribute 'values_cell'`; at `ec989ed` a not_matched F13 printed `n_values_compared` too, so it pins no change of behaviour (N7).
- The three changed/new test files together in `base`: 6 failed, 51 passed (the 4 above + 2 `FALSE_AT_EC989ED`).
- The renamed test's docstring keeps repair 1's sentence "must equal (exactly) the value of an entry ... and that entry's key must be in the committed file", now followed by "every key ... not any one of them". Read together it is true; alone it reads as the old `any`. Non-blocking N8.
- Sentences outside L4-B2 that I checked and found true: the `f13_recorded_outcome` docstring addition (extra names refused, not_matched; the reason counts names recomputed); `values_cell`'s docstring (except the gap in L4-B1); the commit's "golden diff is that one cell" (`T12.html` 1 line, the F13 Values cell 0 -> 16); "CLI exit 6".

### Measured figures

| | Git Bash (`tip`) | PowerShell (`mut`, clean) | commit message |
|---|---|---|---|
| full suite | 2308 passed, 4 skipped in 305.32 s, exit 0 | 2308 passed, 4 skipped in 334.62 s, exit 0 (same two skips) | 2308 / 4 |
| skips | `[3] test_day12_r_captures.py:156` r_vectors_not_committed_dec77; `[1] test_doctor_cli.py:57` | | |
| `-m day13` | 108 passed, 2204 deselected | 108 passed, 2204 deselected | 108 |
| `-m day12` | 196 passed, 3 skipped | 196 passed, 3 skipped | 196/3 |
| `-m day11` | 144 passed | 144 passed | 144 |
| `-m day10` | 262 passed, 2050 deselected | 262 passed, 2050 deselected | 262 |
| ruff check / format | "All checks passed!" / "340 files already formatted" | the same | clean |
| doctor / fixtures --offline | | doctor exit 0; fixtures --offline exit 0 | exit 0 / 0 |

Independent of repository code (plain `json`): the 16 committed F13 pairs give max `abs(engine - r)` 2.7755575615628914e-17, 0 R values unequal to `proc_asah.json`, all within 1e-6; `proc_asah.json`'s LF sha256 equals the recorded `proc_asah_sha256`.

## Non-blocking (record and carry)

- **N1.** The `not keys` guard in `_register_class_lookup` is unpinned (mutant survives, 19 passed). Add a test that removes an entry from `fresh` (not `committed`) and expects a miss.
- **N2.** Fields the command does not read are not refused: extra keys inside a pair (a nested pair) and extra top-level keys (`values_2`). The claim is scoped to `values`, so not a blocker; a closed field list would remove the class.
- **N3.** The file's own top-level `status`, `reason` and `max_abs_deviation` are not read: a file saying `not_matched`, 0.8, gives `suite_only` with the reason's "max abs deviation 2.78e-17". The reason says the deviation is "as recomputed here", so not false; but the job's own recorded verdict can be contradicted silently. Suggest requiring `status == "matched"` and the recorded maximum equal to the recomputed one.
- **N4.** `values_cell` decides by status text, not row id (see Attack 2).
- **N5.** T12 caption defines no "Values"; F13's Oracle/Tolerance "—" beside a deviation (pre-existing).
- **N6.** `recomputed` always equals 16 on the `suite_only` path, so the M4 mutant is equivalent and `test_e13r3_b2_the_reason_counts_the_values_it_recomputed` passes at `ec989ed` - as the commit says ("the fifth pins the count").
- **N7.** See Attack 4: one of the "4 of 5" fails at `ec989ed` only because the function does not exist.
- **N8.** See Attack 4: the renamed test's first docstring sentence.

## Could not break

- The repair's extra-name refusal against case, whitespace, Cyrillic, fullwidth/NFKC, zero-width, NBSP and tab variants, the optional conf.int names, non-dict and empty `values`.
- The Values cell: only a fully recomputed F13 reaches 16, in code.
- The `all` lookup on Linux (gate run 37480583988 success; day13 108 passed on 3.12.11).
- The B1 regression test fails with `any` restored.
- The 16 F13 deviations, re-derived without repository code.

## Could not check

- Nothing in the commit message's figures failed to reproduce: every figure matches in both shells (table above).
- I did not run `ci_gate.sh` (the orchestrator's); I read run 37480583988 only.
