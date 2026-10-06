**Verdict: FAIL - 1 blocker** (cold fresh-attack lens, round 2, on the capture commit and its repair: `97a2ee4`, `78bd085`, `eef15b9`, `8eed328`, `2af59dc`, `5154468`; base `9d285d9`; Tuesday 6 October 2026)

All probes ran in detached worktrees under `scratchpad/caplens2b/`:
- `main`, `mainps`, `plant` and `plant2` at `5154468`;
- `base` at `9d285d9`.

`PYTHONPATH=<worktree>/src` was forced in each. Every plant run printed `proofpack.__file__` from its own worktree before pytest ran; `scratchpad/caplens2b/plant.py` asserts this. `PROOFPACK_ASAH_VECTORS` and `GITHUB_WORKFLOW` were unset unless named. Each plant was undone with `git reset --hard` in its worktree. Nothing was committed except this note: a draft at `1c2862c`, then this version.

## Blockers

### B1. The absent-state F13 and F13b reasons lost their word-for-word pin: deleted, not moved

**What was lost.** At `9d285d9` the T12 golden was rendered in the absent state. So `test_t12.py::test_golden_t12_matches_the_committed_render` compared every word of F13's and F13b's `[unverified until captured]` reasons (golden lines 271 and 272). The page-wide forbidden-word scan also covered them. At `97a2ee4` the golden was regenerated in the committed state. In the absent state, all that is left is:
- `test_t12.py::test_unverified_markings_survive_to_the_page_without_an_r_capture`, which checks the prefixes only (`"[unverified until captured] the pROC capture"`, `"[unverified until captured] the rms::val.prob"`);
- `test_fixtures_cmd.py::test_without_an_r_capture_f13_and_f13b_have_no_oracle_recorded`, which checks `startswith(fx.F13_ABSENT)` and `startswith(fx.F13B_ABSENT)`;
- `test_day12_r_captures.py::test_absent_captures_leave_f13_and_f13b_no_oracle_recorded_with_the_unverified_reason`, which checks `startswith(fx.F13_ABSENT)` and `== fx.F13B_ABSENT`.

The last two compare the source constants with themselves, so a change to a constant's words cannot fail them. No test holds the text after the prefix. No test runs the forbidden-word scan over the absent-state page.

**Repro.** Run `python scratchpad/caplens2b/plant.py <worktree> <plant> <scope>`. Each plant is a working-tree edit of `src/proofpack/fixtures.py`:
- **N-F13B-ABSENT**: in `F13B_ABSENT`, `"is not committed; fixtures/r/capture.R and the r-captures workflow (build day 12) "` becomes `"is committed and F13b is verified and matched; fixtures/r/capture.R and the r-captures workflow (build day 12) "`.
- **N-F13-ABSENT**: in `F13_ABSENT`, `"(fixtures/r/f13_engine_comparison.json) are not both committed; the aSAH vectors are "` becomes `"(fixtures/r/f13_engine_comparison.json) are committed and F13 is matched; the aSAH vectors are "`.
- **N-F13B-ABSENT-cert**: in `F13B_ABSENT`, `"is not committed; fixtures/r/capture.R and ..."` becomes `"is not committed; the engine is certified and validated by fixtures/r/capture.R and ..."`. "certified" and "validated" are in `test_t12.FORBIDDEN`.

**Measured.**

| plant | `5154468`, targeted files | `5154468`, full suite | `9d285d9`, targeted files |
|---|---|---|---|
| N-F13B-ABSENT | `193 passed, 3 skipped`, exit 0 (a) | `2199 passed, 4 skipped`, exit 0 | `1 failed, 175 passed, 9 skipped`: `test_golden_t12_matches_the_committed_render` (b) |
| N-F13-ABSENT | `193 passed, 3 skipped`, exit 0 (a) | `2199 passed, 4 skipped`, exit 0 | `1 failed, 175 passed, 9 skipped`: the same test (b) |
| N-F13B-ABSENT-cert | `273 passed, 3 skipped`, exit 0 (c) | `2199 passed, 4 skipped`, exit 0 | `4 failed, 91 passed, 9 skipped` (d) |

Files in each run:
- (a) `test_t12`, `test_e12_repair3`, `test_fixtures_cmd`, `test_capture_commit`, `test_day12_r_captures`, `test_calibration`, `test_ap3_repair2`.
- (b) The same files without `test_capture_commit`, which does not exist at `9d285d9`.
- (c) `test_t12`, `test_fixtures_cmd`, `test_day12_r_captures`, `test_e12_repair3`, `test_capture_commit`, `test_claims`.
- (d) `test_t12`, `test_fixtures_cmd`, `test_day12_r_captures`, `test_e12_repair3`. The four failures are:
  - the golden;
  - `test_a_not_matched_row_prints_as_not_matched`;
  - `test_no_forbidden_word_outside_customer_text_and_the_verbatim_disclaimer`;
  - `test_the_release_script_renders_t12_from_a_report_with_the_no_licence_mark`.

**Why it matters.** Each planted sentence is false, or a forbidden claim word. It reaches `fixtures_report.json` and the T12 page whenever the capture is absent: a checkout where the JSON files are deleted, or a later capture cycle while the files are out. The lens 1 handoff's own category is "an assertion of 9d285d9 deleted rather than moved". Lens 1's B2 found the row-shape half of this deletion; this is the text half.

**Fix.**
1. Under `no_r_capture`, assert F13's and F13b's reasons as literal strings written out in the test, not read from `fx`. Today's text is the right literal: `97a2ee4` correctly dropped "(f4_expected.json r_rms_val_prob: [pending])" from `F13B_ABSENT`.
2. Run the forbidden-word check over the absent-state render. A second golden rendered under `no_r_capture` would do both.

## Non-blocking

1. **A coordinated edit passes the whole suite.** This is the case the brief asked about, and only a person can catch it. Starting from `5154468`, I changed three files and staged them:
   - `f13_engine_comparison.json`: `s100b var_delong` `engine` +1 ulp (`...383` to `...387`, still 3,517 bytes);
   - its sha256 in `fixtures/r/README.md`;
   - its sha256 in `ARTEFACT` in `tests/test_capture_commit.py`.

   Result: `2199 passed, 4 skipped`. Nothing else in the repository holds that file's bytes:
   - `proc_asah.json` is also pinned by `f13_engine_comparison.json` `proc_asah_sha256`;
   - `rms_val_prob_f4.json` is also pinned by `f4_expected.json` `file_sha256`;
   - the comparison file has only the README, the test and its own `r` and run fields.

   The external pin is the artefact itself. `gh api .../runs/37332685741/artifacts` gives zip digest `sha256:23e6a1ee0529a5d6b76c381bda3505b4df1cf31b0addd9d9c76ca63bcb4f8932` and `expires_at 2026-11-04T15:26:43Z` (`retention-days: 30`). From 4 November nobody can re-download it. The capture handoff's "Sentences refused" already says a coordinated edit passes. Suggestions:
   - record the zip digest and the expiry date in the README;
   - before 4 November, keep a copy of the artefact somewhere other than GitHub.
2. **The committed F13 row's `max_abs_deviation` field is held by no test; only the reason's copy of the number is.** The golden masks every row's deviation to `0.0`, F13's included: its deviation cell went from `—` at `9d285d9` to a masked `0`.
   - Plant **N-F13-dev0-recorded**: `f13_recorded_outcome` returns `0.0 if engine_sha.startswith('9d285d9') else worst` as the row's deviation. The reason still says `2.7755575615628914e-17` while the field says `0.0`. Result over 9 files (`test_t12`, `test_e12_repair3/4/5`, `test_fixtures_cmd`, `test_capture_commit`, `test_day12_r_captures`, `test_calibration`, `test_ap3_repair2`): `250 passed, 3 skipped`. Full suite: `2199 passed, 4 skipped`, exit 0.
   - This is a data-keyed plant. The natural mutant, forcing `0.0` for every `suite_only` row in `compare_row` (**N-F13-dev0**), fails `test_e12_repair4.py::test_fa_b2_the_suite_only_row_reports_the_largest_recorded_deviation`.
   - Suggestion: in `test_capture_repair_b1_the_committed_f13_reason_says_this_command_did_not_run_it`, add `f13["max_abs_deviation"] == 2.7755575615628914e-17`.
3. **Some absent-state summary counts were updated rather than moved.** Three tests now assert only committed-state counts:
   - `test_ap3_repair2.py::test_a_truncated_oracle_file_is_not_matched_and_the_report_is_written`: `matched == 5` became `6`;
   - `test_fixtures_cmd.py::test_a_planted_oracle_off_by_2e_9_...`: `33` became `34`;
   - `test_without_the_newcombe_file_...`: `33` became `34`.

   Their absent-state values (5, 33, 33) are no longer measured anywhere. Each difference is exactly row F13b, whose absent shape B2's test now holds. I grade this non-blocking because the subject of each test (truncated oracle file, planted oracle, missing Newcombe file) is still asserted.
4. **`GITHUB_WORKFLOW=r-captures` exempts only the working-tree half of `test_capture_repair_b3_...`.**
   - In the code, `_in_the_r_captures_job()` is read in one place, `tests/test_capture_commit.py:134`. No `src`, `scripts` or other test file reads `GITHUB_WORKFLOW`.
   - `ci.yml` sets no `GITHUB_WORKFLOW` in any `env:`, so GitHub's own value applies, which is the workflow name `ci`.
   - Measured with the variable set:
     - working-tree-only one-ulp edit of `rms_val_prob_f4.json`: `250 passed, 3 skipped` over the 9 files, the documented trade-off;
     - the same edit staged: `2 failed, 2 passed` (B3 and `test_f4_expected_r_rms_val_prob_is_copied_from_the_committed_capture`);
     - lens 1's staged `s100b` engine plant: `1 failed, 3 passed`.

     So the index half always runs.
   - In the container it has now run: gate run `37347799701` (r-captures at `5154468`, success) printed `199 passed, 2004 deselected` for `pytest -m day12` with no skip. The capture handoff's `[unverified]` "None of this has run in the container" is answered by that run.
5. **A README row given twice passes.** `recorded` is built by a dict comprehension over `README_ROW.findall`, so a duplicated row with a wrong sha placed above the right one passes `recorded == ARTEFACT`. Measured: a staged README with a row of 64 zeros added above the real `f13_engine_comparison.json` row gave `test_capture_commit.py` `4 passed`. This is minor. Asserting `len(README_ROW.findall(readme)) == 3` closes it.

## Could not break

- **Lens 1's three plants at `5154468`** (7 files as in B1 (a)):
  - L1B1, the literal "F13 is verified and matched at this checkout": `3 failed` (the golden and the two B1 tests);
  - L1B2, `max_abs_deviation=0.0` in the `OracleAbsent` branch: `1 failed` (the B2 test);
  - L1B3, staged: `s100b` engine +1 ulp, `ndka` engine +1 ulp and `engine_version` `9.9.9` each gave `1 failed` (the B3 test).
- **Other words of F13's committed reason, each a source edit:**

  | edit | failed |
  |---|---|
  | "not by this command" to "verified by this command" | 5 |
  | "a local re-check needs R" to "is not needed" | 4 |
  | the HEAD-not-read branch | 1 (`test_dec77_outside_the_job_...`) |
  | the HEAD-equals branch given "F13 is verified and matched" | 1 (`test_dec77_outside_the_job_...`) |

  F13b, matched, given the reason "verified against R: validated": `4 failed`, among them the golden and the forbidden-word scan.
- **One ulp and field edits in the other two files:**

  | edit | failed |
  |---|---|
  | `proc_asah.json` `ndka var_delong` +1 ulp, staged | 19 |
  | the same, working tree only | 18 (the loader's `proc_asah_sha256` check fails row F13, and B3's working-tree half) |
  | `proc_asah.json` `n_rows` 114, staged | 19 |
  | `rms_val_prob_f4.json` `glm offset tight (Intercept) se` +1 ulp, staged | 2 |
  | the same, working tree only | 1 (B3) |
  | `val.prob Slope` +1 ulp, working tree only | 1 (B3) |
- **Artefact bytes, fourth download.** `gh run download 37332685741 -n r-captures` gave 3,517, 4,471 and 5,401 bytes, and `cmp` found each identical to `git show 5154468:fixtures/r/<f>`. The sha256 prefixes are `01cf2f7b`, `44a3866f` and `a36b7f54`. Run 37332685741: r-captures, `ci/9d285d9`, success.
- **DEC-77.** `test_dec77_fixtures_r_tracks_the_three_json_files_and_no_vectors` passes. The diff `9d285d9..5154468` adds no CSV and no vectors. `proc_asah.json` holds `vectors_sha256` only.
- **Numbers, independent of repo code** (plain Python: Newton to the MLE, Mann-Whitney C, mean squared error), over the 20 F4 rows:
  - every engine F13b value is within 2.3e-16 of mine;
  - every R value is within 2.9e-15 of mine, except the default-convergence `glm joint` coefficients (up to 1.8e-9) and the three standard errors (3.3e-10 to 2.19e-9). Lens 1 explained both (IRLS last-iteration weights).
  - F13: recomputing `abs(engine - r)` over the 16 names of the committed comparison gives `2.7755575615628914e-17`; every `r` equals `proc_asah.json`'s value.
  - The report's F13b maximum is `2.1908198588604932e-09`.
  - The Git Bash and PowerShell reports have identical rows and summaries.
- **No tolerance was loosened** in `git diff 9d285d9 5154468 -- tests/ src/`. The only new numeric checks are `abs=5e-5` against R2's quoted figures, which are new assertions, not changed ones. `F13`'s `0.0 <= dev <= 1e-6` in the committed branch replaces `None` for that one row by design (E12 repair 4).
- **Item 3, every `9d285d9` assertion on F13, F13b or the absent state**, from `git diff -U0 9d285d9 5154468 -- tests/`:
  - **Moved to `no_r_capture`:**
    - the summary dict (`SUMMARY_WITHOUT_THE_CAPTURE`);
    - `"rows 46: matched 34, not matched 0"`;
    - `no_oracle_recorded == ["F13", "F13b"]` and the `suite_only` list;
    - F13's `[unverified until captured]` prefix;
    - the `--r-captures` not-captured line;
    - the `n_values_compared 0` and `max_abs_deviation None` loop (B2's test);
    - both `.unverified` span prefixes.
  - **Changed because the fact changed:** `f4_expected.json` `[pending]` became `captured`. The `[pending]` branch of `test_f4_expected_..._pending_...` remains, for an untracked capture.
  - **Strengthened:** `test_f4_expected_..._pending_...` now fails on a git error instead of reading it as "untracked".
  - **Updated, not moved:** the three counts in non-blocking 3.
  - **Deleted:** the golden's F13 and F13b absent rows and the absent page's forbidden-word coverage (B1).
- **Test suite at `5154468`, both shells identical:**

  | check | result |
  |---|---|
  | full suite `-rfs` | Git Bash `2199 passed, 4 skipped in 281.13s`; PowerShell 5.1 `2199 passed, 4 skipped in 251.01s`; exit 0 |
  | skips | `[3] r_vectors_not_committed_dec77`, `[1] test_doctor_cli.py:57` |
  | `-m day12` | `196 passed, 3 skipped, 2004 deselected` |
  | `-m day11` | `144 passed` |
  | `-m day10` | `262 passed` |
  | `python -m ruff check .` / `format --check .` | `All checks passed!` / `321 files already formatted` |
  | `doctor --offline` | exit 0, 17 `[ok` lines |
  | `fixtures --offline --r-captures` | exit 0, `rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 5, compared by the test suite only 6`; `present_compared_in_rows_f13_f13b`; `unverified` 36 times |

  Both worktrees were clean after the run.
- **Gate runs at `5154468`:** ci `37347799744` and r-captures `37347799701` both concluded success.

## Could not check

- R is not installed, so `val.prob` and `glm` were not run. The 16 pROC values were not re-derived, because the aSAH rows are not here (DEC-77).
- Gate run `ci/fcc2c57` (6 October, 10:29, green) appeared during this lens. It is not part of this lens; I did not look at what `fcc2c57` is.
