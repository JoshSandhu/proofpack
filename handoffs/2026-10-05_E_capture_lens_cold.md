**Verdict: FAIL - 3 blockers** (cold fresh-attack lens, DEC-12 (i), on the capture commit `97a2ee4` + note `78bd085`, base `9d285d9`; Monday 5 October 2026)

All probes ran in detached worktrees under `scratchpad/caplens/` with `PYTHONPATH=<worktree>/src` forced and proved (`proofpack.__file__` printed the worktree's path each time), `PROOFPACK_ASAH_VECTORS` unset. Worktrees removed afterwards. Nothing committed except this note. Note: `main` moved to `eef15b9` (the orchestrator's `safe.directory` fix) while this lens ran; that commit is not lensed here.

## Blockers

### B1. The T12 golden mask hides a false "verified and matched" sentence in F13's reason; the full suite stays green

`tests/test_t12.py` `F13_HEAD_CLAUSE = re.compile(r"(recorded engine and R numbers; ).*?(\. The aSAH vectors )")` masks the whole clause after "numbers; ", not only the HEAD sha. That clause also carries "this command did not run that comparison on this checkout's engine", and no other test asserts that sentence. `tests/test_e12_repair3.py` checks `"matched" not in reason` only in the HEAD-equals branch; in the not-HEAD branch (the committed state) it checks only `"... is not this checkout's HEAD (fff...)"`.

Repro (worktree at `78bd085`): in `src/proofpack/fixtures.py`, replace the literal `"run that comparison on this checkout's engine"` with `"run that comparison here; F13 is verified and matched at this checkout"`. Then `python -m proofpack.cli fixtures --offline` prints F13's reason as:

> ... the engine commit is not this checkout's HEAD (78bd08501b5877906e18a93ff8204fb0d5e6fab1); this command did not run that comparison here; F13 is verified and matched at this checkout. The aSAH vectors are never committed ...

`python -m pytest -q -p no:cacheprovider -rfs` measured `2195 passed, 4 skipped in 267.53s`, exit 0.

Fix: mask only the 40-hex sha (for example `HEAD \([0-9a-f]{40}\)`), and assert in the committed-state test and in the not-HEAD branch of `test_dec77_outside_the_job_...` that the reason contains "this command did not run that comparison on this checkout's engine" and contains neither "matched" nor "verified".

### B2. An absent-state assertion was deleted, not moved; the handoff's "No assertion was deleted" is false

At `9d285d9`, `test_fixtures_cmd.py::test_rows_without_an_oracle_are_never_counted_as_matched` applied four checks to F13 and F13b, because both were `no_oracle_recorded`: `matched False`, `oracle_source None`, `n_values_compared 0` and `max_abs_deviation None`. At `78bd085` that test runs only in the committed state, where F13b is `matched` and F13 is exempt. The new absent-state test `test_without_an_r_capture_f13_and_f13b_have_no_oracle_recorded` asserts statuses and reasons only. `test_day12_r_captures.py::test_absent_captures_...` asserts F13's `oracle_source` and `n_values_compared` only. Nothing asserts `max_abs_deviation None` for either row in the absent state, and nothing asserts F13b's row shape at all.

Repro: in `compare_row`'s `except OracleAbsent` branch, after `out.update(status="no_oracle_recorded", reason=str(exc))`, add `if row.id in ("F13", "F13b"): out.update(max_abs_deviation=0.0)`.
- At `78bd085`: full suite `2195 passed, 4 skipped in 365.03s`, exit 0.
- The same plant at `9d285d9`: `FAILED tests/test_fixtures_cmd.py::test_rows_without_an_oracle_are_never_counted_as_matched` (`1 failed, 39 passed, 9 skipped` over `test_fixtures_cmd.py` and `test_day12_r_captures.py`).

Fix: in `test_without_an_r_capture_f13_and_f13b_have_no_oracle_recorded`, assert for both rows `matched is False`, `oracle_source is None`, `n_values_compared == 0`, `values == []` and `max_abs_deviation is None`, or run the generic loop under `no_r_capture`. Then correct the handoff sentence.

### B3. `f13_engine_comparison.json` is not pinned: a committed edit, two one-ulp plants included, passes the full suite

The commit's claim is "byte for byte as uploaded". The other two files are pinned:
- `proc_asah.json` through `proc_asah_sha256`;
- `rms_val_prob_f4.json` through `f4_expected.json` `file_sha256`.

The comparison file is pinned only through its `r` values, its run id and engine sha, its `status` field, and the F13 reason's maximum deviation in the golden. Each edit below was written into `fixtures/r/f13_engine_comparison.json` and `git add`-ed (as a commit would be). Each run of `python -m pytest -q -p no:cacheprovider` measured `2195 passed, 4 skipped`, exit 0:

| edit | full suite |
|---|---|
| `s100b var_delong` `engine` 0.0026686824571724383 to 0.0026686824571724387 (+1 ulp) | 2195 passed, 4 skipped |
| `ndka var_delong` `engine` 0.003190810549391302 to 0.0031908105493913025 (+1 ulp) | 2195 passed, 4 skipped |
| `ndka auc` `"within": true` to `false` | 2195 passed, 4 skipped |
| `ndka auc` `"abs_deviation": 0.0` to `0.5` | 2195 passed, 4 skipped |
| top-level `max_abs_deviation` to `0.5` | 2195 passed, 4 skipped |
| `engine_version` to `9.9.9` | 2195 passed, 4 skipped |
| `tolerance_class` to `closed_form` | 2195 passed, 4 skipped |
| `"reason": null` to `"outside tolerance: ndka auc"` | 2195 passed, 4 skipped |

The two engine plants survive because their deviation stays below the recorded maximum (2.78e-17), so no report string changes. No reported number becomes false: F13's row recomputes `abs(engine - r)` and does not read `within`, `abs_deviation` or the top-level maximum. But the committed evidence can silently stop being the artefact.

Fix: `tests/test_capture_commit.py` asserts that the `lf_sha256` of each tracked blob equals the README's table (`01cf2f7b...`, `44a3866f...`, `a36b7f54...`).

## Non-blocking

1. **The failure count with a staged capture is 12, not 11.** This is the procedure the README gives: step 2 says `git add` before any test, with `9d285d9`'s test files and `f4_expected.json` unchanged. I measured `12 failed, 2176 passed, 4 skipped`. The twelfth is `test_day12_r_captures.py::test_f4_expected_r_rms_val_prob_is_pending_until_a_capture_is_committed`, which fails by design once the file is tracked. The README (step 5) says 11, and says the twelfth is `test_calibration`'s once step 3 is done.
2. **Gate run 37341132663 (branch `ci/78bd085`, head `78bd085`) failed: the handoff's untested item 1 happened.** The log reads `fatal: detected dubious ownership in repository at '/__w/proofpack/proofpack'` and `4 failed, 193 passed, 2002 deselected`. The four are the three `test_capture_commit.py` tests and `test_f4_expected_..._pending_...`. `eef15b9`'s message says "three day-12 tests"; the log says four.

   That run's log also gives the first measurements after the capture commit:
   - `r-capture drift: proc_asah.json: identical within 1e-12`, and the same for `rms_val_prob_f4.json`;
   - `r-f13-compare: row F13 matched, max abs deviation 2.7755575615628914e-17, 16 values, engine 78bd085...`.
3. **A fresh checkout here has CRLF copies.** With `core.autocrlf=true`, a fresh worktree gives `i/lf w/crlf` for the three JSON files. The tracked blobs are LF and identical to the artefact. The loaders hash with CRLF read as LF, and the suite passed in such a worktree in both shells. The README's "copied unmodified (LF, as uploaded)" is true of the blob, not of every working copy.
4. **Why F13b's standard errors deviate at about 1e-9.** R's `glm` takes its covariance from the weights of the last IRLS iteration, which are evaluated before the final update. The engine evaluates it at the MLE. My own numpy replication of `glm.fit` (mustart `(y+0.5)/2`, convergence `|dev - devold|/(|dev| + 0.1) < eps`) reproduces all 16 `glm` values in the capture to at most 3.6e-15. Its iteration counts are 5, 6, 4 and 4, as the capture records. Newton iteration to the MLE reproduces the engine's standard errors (for example `0.5950556263256326` exactly). Like is compared with like, and the deviations (3.3e-10 to 2.19e-9) are within 1e-6.
5. F13b's `oracle_source.library_versions` lists pROC, which F13b does not use. This is harmless.

## Could not break

- **Artefact bytes.** A fresh `gh run download 37332685741 -n r-captures` holds exactly three files: 4,471, 5,401 and 3,517 bytes. Their sha256 values are `01cf2f7b...`, `44a3866f...` and `a36b7f54...`. `git show 78bd085:fixtures/r/<f>` is `cmp`-identical to each. `rms_val_prob_f4.json` records input sha `0b353b93...` and 381 bytes, which equal `git show 78bd085:fixtures/f4_calibration.csv`.
- **DEC-77.** No CSV, no vectors and no row data are in the diff or the tree. The capture holds aggregates and the vectors' sha256 only.
- **F13b re-derived without repo code** (numpy only, own IRLS and Newton):

  | figure | mine against R |
  |---|---|
  | Brier | 0.158755, R 0.158755 |
  | C | 0.8541666666666666, R 0.8541666666666667 |
  | val.prob Slope | 2.9e-15 from the exact MLE slope 1.1945124796435689 |
  | val.prob Intercept | 1.4e-15 from the exact MLE intercept 0.49977163424518545 |
  | offset-only intercept | 0.4562304654612095, R 0.4562304654612094 |

  The engine's 13 values in `proofpack fixtures --offline` equal my MLE to 2e-16. The report's 13 rows, deviations and maximum (`2.1908198588604932e-09`) equal the handoff's table.
- **One-ulp plants, each staged.** 86 single-value plants were run against 12 test files:
  - 20 in `proc_asah.json`;
  - 16 `r` and 16 `engine` values in `f13_engine_comparison.json`;
  - 34 in `rms_val_prob_f4.json`.

  84 failed. The 2 that passed are in B3.
- **Deleting `f13_engine_comparison.json`.** The row reads `no_oracle_recorded` with the `[unverified until captured]` reason, and the summary is 35 matched / 1 no oracle / 5 suite only, exit 0. The `--r-captures` line reads `partial_see_rows_f13_f13b`. With the deletion in the working tree only, 5 tests fail. With `git rm`, 2 `test_capture_commit.py` tests fail.
- **The moved absent-state tests.** Each failed when its condition was broken, except B2:
  - `F13_ABSENT` without its prefix: 3 failed;
  - `F13B_ABSENT` without its prefix: 1 failed;
  - absent F13b as `suite_only`: 10 failed;
  - equal sha reported as not HEAD: 1 failed;
  - not-HEAD clause without the sha: 1 failed.
- **No tolerance was changed.** The diff adds 5e-5 checks against R2's quoted figures in `test_calibration.py` and loosens nothing. Locally, F13 cannot read `matched` without the vectors in the current code (`suite_only`, `values` `[]`, `oracle_source` null).
- **Suite at `78bd085`, both shells identical:**

  | check | result |
  |---|---|
  | full suite | `2195 passed, 4 skipped`, exit 0 |
  | `-m day12` | `194 passed, 3 skipped, 2002 deselected` |
  | `-m day11` | `144 passed` |
  | `-m day10` | `262 passed` |
  | `python -m ruff check .` / `format --check` | `All checks passed!` / `320 files already formatted` |
  | `doctor --offline` | exit 0, 17 `[ok` lines |
  | `fixtures --offline --r-captures` | exit 0, `rows 46: matched 35, not matched 0, no oracle recorded 0, ... compared by the test suite only 6` |

  `unverified` appears 36 times in the report. `ruff` is not on PATH in either shell; `python -m ruff` is.

## Could not check

- No R is installed here, so `val.prob`'s definitions were not run. Its Slope and Intercept agree with my MLE to 3e-15, and that is all I can say.
- The 16 pROC values were not re-derived: the aSAH data is not here (DEC-77). They were only re-read and their deviations recomputed.
- `eef15b9` and whether the next r-captures run is green.
