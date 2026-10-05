# Lane E - the capture commit: GitHub run 37332685741's R capture into `fixtures/r/` (Monday 5 October 2026)

**Landed, not pushed.** Commit `97a2ee4` on `main` (parent `9d285d9` = `origin/main`). This note is committed on top of it as its own commit.

- **F13b: matched.** `proofpack fixtures --offline` compares 13 engine values on this machine with the committed `rms::val.prob` / `glm` values of run 37332685741. Each is within the `iterative` tolerance (absolute 1e-6). The largest deviation is `2.1908198588604932e-09` (`glm offset tight (Intercept) se`).
- **F13: suite_only.** The row reads the comparison run 37332685741 recorded at engine `9d285d9`: 16 values, largest deviation `2.7755575615628914e-17`. No F13 engine value is computed here, because the aSAH vectors are not here (DEC-77). The reason now says the engine commit is not this checkout's HEAD (`97a2ee4...`).
- **12 tests changed.** 11 failed with the capture present (lens 5 FA-N5's figure), and a 12th once `f4_expected.json` stopped saying `[pending]`. 7 tests are new. Full suite: `2195 passed, 4 skipped` in both shells.
- **First risk after the push** (it is not measured): whether `git` works in later steps of the r-captures container. See "For the orchestrator", item 1.

## Commits

| sha | what |
|---|---|
| `97a2ee4` | the three JSON files; `fixtures/f4_expected.json` `r_rms_val_prob`; 7 test files, the T12 golden and `tests/conftest.py`; `fixtures/r/README.md`; comments and `F13B_ABSENT` in `src/proofpack/fixtures.py`; the header comments of `.github/workflows/r-captures.yml` |
| (this note) | `handoffs/2026-10-05_E_capture_commit.md` |

Both commit messages end with the Co-Authored-By line. Nothing is pushed.

## The artefact bytes

`gh run view 37332685741` gives: workflow `r-captures`, branch `ci/9d285d9`, head sha `9d285d986fedd6f6e43fb2c6bfd1497307adbfa1`, conclusion `success`.

I downloaded the artefact `r-captures` twice, into `scratchpad/rcap2` and `scratchpad/rcapcommit/dl3`, with `gh run download 37332685741 -n r-captures -D <dir>`. Both downloads, and the orchestrator's copy in `scratchpad/rcap`, hold exactly three files, with the same bytes:

| file | bytes | sha256 |
|---|---|---|
| `proc_asah.json` | 4,471 | `01cf2f7bd8c57e7dfbc568ed6867b864701ceb8cf8827db68d7ee3d1e31d9a96` |
| `rms_val_prob_f4.json` | 5,401 | `44a3866fdccd67eb76532705d9b03eda7c26f2a32ff5d7124a5a6c156c79be27` |
| `f13_engine_comparison.json` | 3,517 | `a36b7f54454c68e5e1478cbe4c19651a43f3f954fc1d7b25150f10a06921307f` |

None of the three files holds a CR. I copied them with `cp`; nothing was re-serialised. `git show HEAD:fixtures/r/<file> | sha256sum` gives the same three hashes. `git ls-files --eol fixtures/r` reads `i/lf w/lf` for each file.

I added no `.gitattributes`:
- No fixture in this repository has one (`newcombe_table2.json` is `w/crlf` today).
- `load_r_captures` and the F4 and F13 sha256 checks hash with CRLF read as LF (`fixtures.lf_sha256`).
- `tests/test_capture_commit.py` reads the blobs git tracks.

No CSV and no `*asah*vectors*` path was added. `git diff --cached --name-only | grep -iE "csv|asah.*vectors"` printed nothing before the commit.

What the capture's `meta` says (both R files carry the same values):
- R 4.5.1 (2025-06-13), x86_64-pc-linux-gnu, Ubuntu 24.04.3 LTS.
- pROC 1.19.0.1, rms 8.1.0, jsonlite 2.0.0.
- Repository `https://p3m.dev/cran/__linux__/noble/2025-10-30`.
- Run date `2026-10-05T15:26:18Z`, run attempt 1.

The run log (`gh run view 37332685741 --log`) prints:
- `CRAN=https://p3m.dev/cran/__linux__/noble/2025-10-30`;
- `r-capture drift: no capture is committed; nothing to compare`;
- `r-f13-compare: row F13 matched, max abs deviation 2.7755575615628914e-17, 16 values`;
- `194 passed, 1998 deselected` for `pytest -m day12`, with no `SKIPPED` line;
- the job's fixtures rows `F13 matched 2.7755575615628914e-17` and `F13b matched 2.1908198588604932e-09`;
- `r-upload-guard: 0 problem(s) in upload`.

## F13 and F13b, outside the job (`97a2ee4`, this machine)

`proofpack fixtures --offline --r-captures` exits 0 in both shells and prints:
- `rows 46: matched 35, not matched 0, no oracle recorded 0, no independent oracle 0, not built 5, compared by the test suite only 6`;
- `r-captures: present_compared_in_rows_f13_f13b - read: fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json, fixtures/r/f13_engine_comparison.json; unreadable: none; absent: none; row F13 suite_only, row F13b matched; the aSAH vectors are read inside the r-captures job only (DEC-77)`.

`unverified` appears 36 times in `fixtures_report.json` (37 before; F13b now carries `"unverified": false`).

**F13b `matched`.** Class `iterative`, tolerance absolute 1e-6, `oracle_source.kind` `captured_library`. Engine value against R value, with the absolute deviation:

| name | engine | R (run 37332685741) | abs deviation |
|---|---|---|---|
| val.prob Slope | 1.1945124796435687 | 1.194512479643566 | 2.6645352591003757e-15 |
| val.prob Intercept | 0.4997716342451853 | 0.49977163424518406 | 1.2212453270876722e-15 |
| val.prob Brier | 0.158755 | 0.158755 | 0.0 |
| val.prob C (ROC) | 0.8541666666666666 | 0.8541666666666667 | 1.1102230246251565e-16 |
| glm joint (Intercept) | 0.4997716342451853 | 0.49977163348157905 | 7.636062338001182e-10 |
| glm joint logit_p | 1.1945124796435687 | 1.1945124778153178 | 1.8282508840172795e-09 |
| glm offset (Intercept) | 0.45623046546120954 | 0.4562304654612094 | 1.6653345369377348e-16 |
| glm joint tight (Intercept) | 0.4997716342451853 | 0.4997716342451852 | 5.551115123125783e-17 |
| glm joint tight logit_p | 1.1945124796435687 | 1.1945124796435687 | 0.0 |
| glm joint tight (Intercept) se | 0.5950556263256326 | 0.5950556259960736 | 3.2955893569663886e-10 |
| glm joint tight logit_p se | 0.561745814672772 | 0.561745813951554 | 7.212179742310809e-10 |
| glm offset tight (Intercept) | 0.45623046546120954 | 0.4562304654612094 | 1.6653345369377348e-16 |
| glm offset tight (Intercept) se | 0.5536866258585561 | 0.5536866236677362 | 2.1908198588604932e-09 |

The figures are the same in both shells. The job printed the same maximum on Linux (`2.1908198588604932e-09`). F13b is within its tolerance, so nothing was stopped and no tolerance was touched.

**F13 `suite_only`.** `n_values_compared` 0, `values` `[]`, `oracle_source` null, `max_abs_deviation` `2.7755575615628914e-17`. The reason, verbatim:

> compared inside the r-captures job, not by this command: GitHub run 37332685741 recorded 16 values of the engine at commit 9d285d986fedd6f6e43fb2c6bfd1497307adbfa1 against pROC (proc_asah.json), max abs deviation 2.7755575615628914e-17, each within 1e-6 as recomputed here from the recorded engine and R numbers; the engine commit is not this checkout's HEAD (97a2ee4a8ecaa12e50beaf4730c6953d17ef4ae1); this command did not run that comparison on this checkout's engine. The aSAH vectors are never committed (DEC-77), so a local re-check needs R: the r-captures job (fixtures/r/README.md)

Before the commit, with HEAD at `9d285d9`, the same clause read "the engine commit is this checkout's HEAD". That sentence's figures come from the recorded file:
- 14 of the 16 recorded deviations are 0.0;
- `s100b var_delong` is 4.336808689942018e-19;
- `roc.test p.value` is 2.7755575615628914e-17.

The capture also carries `roc.test conf.int lo/hi` (-0.048870606422809354 / 0.28769174463419145). The report row does not compare them. In the job, `pytest -m day12` ran the F13 test, which compares them when the capture carries them, and that step reported no skip. That is what ran; no recorded figure for them exists outside the job's log.

## The tests changed, and why

Measured at `9d285d9` in a detached worktree with this commit's three JSON files staged, its `f4_expected.json` and its `src/proofpack/fixtures.py`, and the old test files: `12 failed, 2176 passed, 4 skipped`. Without the `f4_expected.json` change: 11 failed, `11 failed, 2177 passed, 4 skipped` in the main tree. Each of the 12 passes at `97a2ee4`.

| test | failed at 9d285d9 with the capture | change |
|---|---|---|
| `test_ap3_repair2.py::test_every_compared_row_declares_the_names_its_engine_and_oracle_carry` | raised `ComparedInRunner` (uncaught) | catches it for F13 only (`status` `suite_only`, `compares` = `F13_NAMES`); now also requires that F13b's names were compared |
| `test_ap3_repair2.py::test_a_truncated_oracle_file_is_not_matched_and_the_report_is_written` | `assert (6 == 5)` | matched 6: F13b does not read `oracles_v1.json` |
| `test_ap3_repair3.py::test_the_check_classes_are_the_fixtures_rows_classes` | raised `ComparedInRunner` | catches it, asserting the row is F13 |
| `test_calibration.py::test_f4_fixture_rows_and_recorded_values_match_r2_section_9` | `[pending]` assertion (once `f4_expected.json` changed) | status `captured`, run id, and R's Brier, Slope, Intercept and `glm offset (Intercept)` against R2's quoted figures at 5e-5 |
| `test_fixtures_cmd.py::test_the_report_validates_against_its_schema_and_carries_the_measured_counts` | summary 35/0/6 against 34/2/5 | committed counts `SUMMARY_WITH_THE_CAPTURE`; the old counts move to the new absent-state test |
| `test_fixtures_cmd.py::test_a_planted_oracle_off_by_2e_9_on_a_closed_form_cell_is_not_matched_and_exits_6` | `34 == 33` | matched 34 (+F13b) |
| `test_fixtures_cmd.py::test_rows_without_an_oracle_are_never_counted_as_matched` | `2.7755575615628914e-17 is None` | F13 `suite_only` carries a deviation by design (E12 repair 4), required here to be between 0 and 1e-6; every other row without an oracle is still `None`; `values == []` added |
| `test_fixtures_cmd.py::test_the_statuses_of_the_register_rows_are_the_ones_named` | `[] == ['F13', 'F13b']` | committed statuses: none `no_oracle_recorded`, F13b `matched`, F13 in `suite_only`, F13's reason names run 37332685741 and carries no `[unverified` |
| `test_fixtures_cmd.py::test_r_captures_prints_the_typed_not_captured_line` | line absent | runs in the absent state (`no_r_capture`) with its assertions unchanged |
| `test_fixtures_cmd.py::test_without_the_newcombe_file_f14_has_no_oracle_recorded_and_the_exit_is_0` | `33` | matched 34 |
| `test_t12.py::test_golden_t12_matches_the_committed_render` | count cells, F13/F13b rows | golden regenerated (6 lines: three count cells, the F13 and F13b rows, the checklist's "35 matched"). `masked_report` masks F13's HEAD clause, which moves with every commit |
| `test_t12.py::test_unverified_markings_survive_to_the_page` | no F13 `[unverified until captured]` span | split: the absent state keeps all four old assertions; the committed page has no `[unverified until captured]` span, and keeps the Newcombe and CSA spans |

No assertion was deleted. Each absent-state assertion now runs in a new or rewritten test against a state the test builds itself.

The fixture `no_r_capture` (`tests/conftest.py`) does this:
- it copies `README.md` and `capture.R` (not the JSON files) to a temporary directory;
- it monkeypatches `fixtures.r_captures_dir` to that directory;
- it unsets `PROOFPACK_ASAH_VECTORS`;
- it asserts that `load_r_captures().present == ()`.

**New tests (7).**
- `test_fixtures_cmd.py::test_without_an_r_capture_the_counts_are_the_absent_states`
- `::test_without_an_r_capture_f13_and_f13b_have_no_oracle_recorded`
- `::test_r_captures_prints_the_committed_capture_line`
- `test_t12.py::test_unverified_markings_survive_to_the_page_without_an_r_capture`
- `tests/test_capture_commit.py`, three tests, markers `day12` and `fixture`:
  - `fixtures/r/` tracks exactly the three JSON files beside `README.md` and `capture.R`, and no tracked path matches `*asah*vectors*` or `fixtures/r/*.csv`;
  - the three files name run 37332685741 and engine `9d285d9`, and the comparison's `proc_asah_sha256` is the tracked file's;
  - `f4_expected.json` `r_rms_val_prob` equals the capture's provenance and figures, field by field.

  These read the capture with `git show :<path>`, not from the working tree. The r-captures job copies a fresh capture over the working tree without staging it.

**Counter-examples run** (each in the `9d285d9` worktree with this commit's files, then restored):

| mutant | result |
|---|---|
| M1: `val.prob Slope` in `f4_expected.json` moved by one ulp (`1.194512479643566` to `1.1945124796435662`) | `test_f4_expected_r_rms_val_prob_is_copied_from_the_committed_capture` FAILED |
| M2: `fixtures/r/asah_vectors.csv` written and `git add -f` | `test_dec77_...` FAILED (1 failed, 2 passed) |
| M2b: `my_asah_vectors.txt` at the root, `git add -f` | `test_dec77_...` FAILED |
| M3: the staged `rms_val_prob_f4.json` with `run_id` 37332685742 | `test_the_three_committed_files_...` and `test_f4_expected_...` FAILED |
| M4: the golden's HEAD mask replaced by a pattern that matches nothing, with `git_sha` returning the engine sha, `f`x40, or not read | masked render equals the golden in all three cases; unmasked, it differs in all three |

**`ComparedInRunner` (the orchestrator called this FA-N4; the lens-5 note numbers it N5).** It is a test defect, not a code defect:
- `row.oracle` raising `ComparedInRunner` for F13 outside the job is the designed protocol;
- `grep -rn "\.oracle(" src scripts` finds one caller, `compare_row`, which catches it;
- the two tests that called `row.oracle` directly caught only `OracleAbsent`.

So no `src` change was made for it, and so there is no failing-first code test. The two tests above failed on it at `9d285d9` with the capture, and pass now.

**`src` changes (comments and one reason string only):**
- `F13B_ABSENT` drops "(f4_expected.json r_rms_val_prob: [pending])", which is false once `r_rms_val_prob` is `captured`. The string is still used in the absent state, and its tests assert `startswith(fx.F13B_ABSENT)`.
- Three comments now state what the capture showed, and keep `[unverified]` on what it did not:
  - `F13_OPTIONAL_NAMES`: pROC 1.19.0.1 carries conf.int; the version that added it is still not read.
  - `F13B_NAMES`: `val.prob Intercept` is 1.2e-15 from `glm joint tight (Intercept)` and 0.044 from `glm offset (Intercept)`; the rms source is still not read.
  - `f13_engine_values`: the run recorded both scores' DeLong bounds 0.0 from `ci.auc`'s; pROC's source is still not read.

**`[unverified until captured]` marks.**
- The three reason constants (`F13_ABSENT`, `F13B_ABSENT`, `R_CAPTURES_NOT_READ`) keep the mark. They are emitted only in the absent state or from an installed wheel, where they are still true.
- The README's "has not run" sentences now give what run 37332685741 printed.
- `r-captures.yml`'s two `[unverified]` comments:
  - The CRAN snapshot is now read: `2025-10-30`. That the tag always resolves to it is still `[unverified]` (it is pinned by tag).
  - setup-uv and uv ran in the image. Whether `git` works in later container steps is now marked `[unverified]` (item 1 below).
- The README keeps pROC's licence and authors `[unverified]` (not fetched) and adds the version, 1.19.0.1, read from `meta`.

## Suite (at `97a2ee4`, tree clean, both shells import `C:\Users\joshs\GPS\ProofPack\proofpack\src\proofpack\__init__.py`)

Environment: `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8`, `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, `PROOFPACK_ASAH_VECTORS` and `PYTHONPATH` unset. Scripts: `scratchpad/rcapcommit/suite.sh`, `suite.ps1`.

| Command | Git Bash | PowerShell 5.1 |
|---|---|---|
| `python -m pytest -q -p no:cacheprovider -rfs` | `2195 passed, 4 skipped in 412.26s`, exit 0 | `2195 passed, 4 skipped in 319.33s`, exit 0 |
| skip lines | `[3] r_vectors_not_committed_dec77: F13 needs the aSAH vectors ...`; `[1] test_doctor_cli.py:57: write access cannot be revoked for this user` | the same |
| `--collect-only` | `2199 tests collected` | `2199 tests collected` |
| `-m day12 -rs` | `194 passed, 3 skipped, 2002 deselected`, exit 0 | the same, exit 0 |
| `-m day11` | `144 passed, 2055 deselected`, exit 0 | the same |
| `-m day10` | `262 passed, 1937 deselected`, exit 0 | the same |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `319 files already formatted` | `All checks passed!` / `320 files already formatted` (this note, untracked when PowerShell ran, is the 320th: ruff includes `handoffs/*.md`) |
| `python -m proofpack.cli doctor --offline` | exit 0, 17 `[ok` lines, last line `Next step: write criteria.yaml ...` | the same |
| `python -m proofpack.cli fixtures --offline --out DIR --r-captures` | exit 0, the lines and rows above, `unverified` 36 times | the same |
| `python scripts/capture_fixture_oracles.py --check` | exit 0, `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it` | run, but the script's last line is its platform line, and neither the count nor the exit code was captured |
| `python scripts/r_capture_drift.py --committed fixtures/r --fresh fixtures/r` | `0 difference(s) above 1e-12` (the committed capture against itself; this says nothing about R) | not run |

Before this commit (`12405ea` handoff): `2182 passed, 10 skipped`. Now there are 7 more tests and 6 fewer skips: the five `r_captures_not_captured: F13b` skips and the one `F13 recorded` skip now run. The remaining skips are `[3] r_vectors_not_committed_dec77` and `[1] test_doctor_cli.py:57`.

## Sentences refused

- "ProofPack's calibration statistics are verified against R." Only the 13 F13b names were compared, on the 20 F4 rows, at absolute 1e-6, against run 37332685741.
- "F13 is verified against pROC at this commit." The comparison ran at `9d285d9`, inside the job. At `97a2ee4` it has not been run. Since then the `src` diff is three comments and one reason string, but nothing re-ran F13 on that engine. The row says so.
- "The drift check confirms the capture is reproducible." The drift check has never compared a committed capture: in run 37332685741 nothing was committed. Its first real comparison is the run this commit's push triggers.
- "The job's git commands work inside the container." This is not observed (item 1).
- "pROC's conf.int agrees with the engine." No recorded figure exists for it outside the job's log. The F13 test that compares it passed in the job, and that is all I can say.
- "`val.prob`'s Intercept is the joint model's intercept." The capture shows 1.2e-15 agreement on these 20 rows only, and the rms source was not read.

## What lane S must change on `/trust/validation` (for a later pin move; DEC-43 pins `81f1102`)

The site's `src/data/engine-register/fixtures_report.81f1102.json` has F13b `no_oracle_recorded`, with a reason ending `(f4_expected.json r_rms_val_prob: [pending])`. When the pin moves to `97a2ee4` or later, regenerate the register from that commit and change these:

1. **Summary.** `matched 35`, `no_oracle_recorded 0`, `suite_only 6` (rows 46, not built 5, not matched 0).
2. **F13b row.** `matched`, 13 values, `oracle_source.kind` `captured_library`, `library_versions` R / pROC / rms / jsonlite, and `detail` naming run 37332685741 and the p3m snapshot. Max deviation `2.19e-9` on Windows cp314; the job printed the same on Linux. Any "checked against R" wording names those 13 fields, the run id and 1e-6.
3. **F13 row.** `suite_only`, `values` `[]`, `n_values_compared` 0, `oracle_source` null, numeric `max_abs_deviation` `2.7755575615628914e-17`, and `suite_tests` the workflow and `tests/test_day12_r_captures.py`.
   - Its reason names the run and engine `9d285d9`, and ends with a HEAD clause that depends on the checkout that generated the report.
   - The page must not call F13 "matched" or "verified at" the pinned commit. It was compared at `9d285d9` in the job.
4. **The `[unverified until captured]` spans for F13 and F13b go away.** The renderer must not keep a hard-coded copy.
5. **The `--r-captures` line** is `present_compared_in_rows_f13_f13b ...`, verbatim as in "F13 and F13b, outside the job" above.
6. **`F13B_ABSENT`'s text changed** (the parenthetical is gone). It shows only in an absent state.
7. **Carried:** the site's generated data cites a deleted node id (L1-RG-N5).

## For the orchestrator

1. **Push, then watch the r-captures run the push starts.** The commit changes `fixtures/r/**` and the workflow, so the push matches its `on: push` paths. That run is:
   - the first drift check against a committed capture;
   - the first F13 comparison at an engine past `9d285d9`;
   - the first time a day-12 test needs `git` to work in the container.

   `test_f4_expected_r_rms_val_prob_is_pending_until_a_capture_is_committed` reads a failed `git ls-files` as "not tracked" and would then assert `[pending]`. `tests/test_capture_commit.py` asserts git's exit code. If the container's git refuses the checkout (for example "dubious ownership", owner other than root), both fail and the job is red. The fix would be a `git config --global --add safe.directory "$GITHUB_WORKSPACE"` step, a workflow change that needs its own lens.

   Run 37332685741 cannot show whether git works there, because before this commit that test passed either way. **[unverified]**
2. **Lens this commit.** It touches no statistical gate: no tolerance, comparison or status logic changed. It does change the tests of the recorded-comparison row (F13) and the counts. A fresh attack should try:
   - the HEAD mask hiding a real reason change;
   - `no_r_capture` failing to hide a file;
   - the index-reading tests passing on a working-tree-only change.
3. **Not done:** no R run here (none installed), and no push.

## Open questions

1. Should the r-captures workflow add the `safe.directory` step pre-emptively, or wait for item 1's run to show the failure?
2. Should `test_f4_expected_r_rms_val_prob_is_pending_until_a_capture_is_committed` fail rather than read a failed `git ls-files` as "not tracked"?
3. Should a later capture replace this one (new run id) or be refused while the drift check reads 0 differences? Today the tests name run 37332685741, so a replacement changes them.
