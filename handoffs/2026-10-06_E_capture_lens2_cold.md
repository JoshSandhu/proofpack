**Verdict: FAIL - 1 blocker** (cold fresh-attack lens, round 2, on the capture commit and its repair: `97a2ee4`, `78bd085`, `eef15b9`, `8eed328`, `2af59dc`, `5154468`; base `9d285d9`; Tuesday 6 October 2026)

Draft written as soon as the blocker was measured; extended below as the remaining checks finished.

All probes ran in detached worktrees under `scratchpad/caplens2b/` (`main`, `mainps`, `plant` at `5154468`; `base` at `9d285d9`) with `PYTHONPATH=<worktree>/src` forced. Every plant run printed `proofpack.__file__` from its own worktree before pytest ran (`scratchpad/caplens2b/plant.py` asserts it). `PROOFPACK_ASAH_VECTORS` and `GITHUB_WORKFLOW` unset unless named. Each plant was undone with `git reset --hard` in its worktree. Nothing committed except this note.

## Blockers

### B1. The word-for-word pin on F13's and F13b's absent-state reasons was deleted, not moved

At `9d285d9` the T12 golden was rendered in the absent state, so `test_t12.py::test_golden_t12_matches_the_committed_render` compared every word of F13's and F13b's `[unverified until captured]` reasons (golden lines 271 and 272). At `97a2ee4` the golden was regenerated in the committed state. In the absent state, what is left is:

- `test_t12.py::test_unverified_markings_survive_to_the_page_without_an_r_capture`: prefixes only (`"[unverified until captured] the pROC capture"`, `"[unverified until captured] the rms::val.prob"`);
- `test_fixtures_cmd.py::test_without_an_r_capture_f13_and_f13b_have_no_oracle_recorded`: `startswith(fx.F13_ABSENT)` and `startswith(fx.F13B_ABSENT)`;
- `test_day12_r_captures.py::test_absent_captures_...`: `startswith(fx.F13_ABSENT)` and `== fx.F13B_ABSENT`.

The last two compare the source constants with themselves, so they cannot fail on a change to the constant's words. No test holds the text after the prefix.

Repro (`scratchpad/caplens2b/plant.py`, worktree at `5154468`, working-tree edit of `src/proofpack/fixtures.py`):

- **N-F13B-ABSENT**: in `F13B_ABSENT`, `"is not committed; fixtures/r/capture.R and the r-captures workflow (build day 12) "` becomes `"is committed and F13b is verified and matched; fixtures/r/capture.R and the r-captures workflow (build day 12) "`.
- **N-F13-ABSENT**: in `F13_ABSENT`, `"(fixtures/r/f13_engine_comparison.json) are not both committed; the aSAH vectors are "` becomes `"(fixtures/r/f13_engine_comparison.json) are committed and F13 is matched; the aSAH vectors are "`.

| plant | at `5154468`, 7 files* | at `5154468`, full suite | at `9d285d9`, 6 files* |
|---|---|---|---|
| N-F13B-ABSENT | `193 passed, 3 skipped`, exit 0 | (pending) | `1 failed, 175 passed, 9 skipped`: `test_golden_t12_matches_the_committed_render` |
| N-F13-ABSENT | `193 passed, 3 skipped`, exit 0 | (pending) | `1 failed, 175 passed, 9 skipped`: the same test |

\* `test_t12.py`, `test_e12_repair3.py`, `test_fixtures_cmd.py`, `test_capture_commit.py` (not at `9d285d9`), `test_day12_r_captures.py`, `test_calibration.py`, `test_ap3_repair2.py`.

Both planted sentences are false and appear in the report and the T12 page whenever the capture is absent: a checkout where the JSON files were deleted, and any later capture cycle while the files are out. The repair's own handoff names this class: "an assertion of 9d285d9 deleted rather than moved". Lens 1's B2 found the row-shape half of it; this is the text half.

Fix: in `test_without_an_r_capture_f13_and_f13b_have_no_oracle_recorded` (or a new test under `no_r_capture`), assert F13's reason and F13b's reason as literal strings, written out in the test, not read from `fx`. At `9d285d9` the golden held them; `F13B_ABSENT` lost "(f4_expected.json r_rms_val_prob: [pending])" in `97a2ee4`, which is correct now, so the literal is today's text. Alternatively render the absent state into a second golden.
