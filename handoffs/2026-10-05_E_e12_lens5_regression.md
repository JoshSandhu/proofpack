# Lane E - build day 12 (E12, the R captures) - lens 5, cold regression-and-record, at `174ed35` (E12 repair 4; pre `614edd2`; Monday 5 October 2026)

**PASS. 0 blockers.**

Every count and command in the repair-4 note reproduces in Git Bash and in PowerShell 5.1. Timings differ; counts, exit codes and printed lines do not.

Lens 4's six blocker ids no longer reproduce:
- FA-B1 = RG-B1: lens 4's one-line CLI repro now exits 6, with `oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (JSONDecodeError)`.
- FA-B2: mutant M18 now fails 1 test.
- FA-B3 = RG-B2 (a): a file named with a vectors data line no longer reaches stdout or stderr. I tried 3 plants of my own beyond the test's three; none did.
- FA-B4: the false sentence is gone; the loader's behaviour is now described as it is.
- RG-B2 (b): the `capture.R` sentence is rewritten. Its `git --work-tree` counter-example reproduces as the note quotes.

Every mutant in the note's mutation table fails the tests it names, with the counts it gives.

Ten of the twenty new tests pass at `614edd2`, as the note states. Their evidence is the mutants, which I re-ran (N1).

`capture.R` and the r-captures workflow have still never run. Gate 2 of section 10 is not met. F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]`. I re-measured this in both shells.

Setup. Detached worktrees under `scratchpad/lens-E12-r5-regression/`:
- `new` (`174ed35`): the Git Bash and PowerShell suites, the CLI commands, the probes, and a job-shape run;
- `mut` and `mut2` (`174ed35`): mutants, each applied alone by a script and restored; `git status --short` was empty after each script;
- `old` (`614edd2`): `tests/test_e12_repair4.py` copied in.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`.

One trap I hit: in Git Bash, a two-entry `PYTHONPATH` written with POSIX paths (`/c/...;/c/...`) silently imported the main tree. I discarded those probe results and re-ran them with `cygpath -w` paths, which printed the worktree's file. The main tree is clean at `174ed35`, so the code was the same, but no figure below rests on those runs.

Suite runs used `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8` and `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, with `PROOFPACK_ASAH_VECTORS` unset unless stated. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1.

I committed, pushed, downloaded and installed nothing, and I did not install R. This note is the only file I wrote outside the scratchpad. `origin/main` is `169bb15`.

## Blockers

None.

## Non-blocking (record and carry)

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **Ten of the twenty new tests pass at `614edd2`, so "fails pre-build" holds for ten only.** The ten are the 4 `test_fa_b1_...`, the 5 `test_rg_n1_...` and `test_fa_b2_...`. The note says so and gives the reason: the code was already right, and the defect was that no test failed when the rule was broken. Their pinning therefore rests on mutants, which I re-ran (see "What I could not break"). I grade this as recorded, not a blocker. | `cp tests/test_e12_repair4.py <old>/tests/`; `PYTHONPATH=<old>/src python -m pytest -q -rA tests/test_e12_repair4.py` -> `10 failed, 10 passed in 1.84s` |
| N2 | **The guard docstring's list of what it prints leaves out the directory argument.** The text reads "What it prints ...: the three names above, those of the three it did not find, the error type of a file it could not read, and counts." `main` also prints the path it was given, on the summary line and on the not-a-directory line. In the workflow that path is the literal `upload`, so no vectors value reaches it. Still, the sentence reads as a complete list and is not one. | the guard on a planted `upload` dir printed `r-upload-guard: 3 problem(s) in C:\Users\...\probe\up_nested2` |
| N3 | **`capture.R`'s comment and the README describe a stop condition that has never run.** The comment says "the script stops when that is the working directory ... or lies under it"; the README says "it stops when ... the path's directory ... is the working directory or lies under it". Both carry their own marker ("Not run here (no R)" / "it has not run"), which is what the build brief asks for R code. I read the R against its semantics: a relative path such as `x.csv` gives `dirname` `.`, which normalises to `getwd()`, and `identical` then stops. That agrees with the sentence, but it is a reading, not a run. | `fixtures/r/capture.R` lines 59-75 |
| N4 | **A test name overstates for two of its four cases.** The name `test_rg_b2_the_sentences_lens_4_falsified_are_gone` covers: <br>- the README sentence, which lens 4 *reasoned* about ("reasoned from `capture.R` ...; not run", its FA-N7); <br>- the "compare job" docstring, which was stale rather than falsified. <br>The constant's comment does say "(or stale)". | `tests/test_e12_repair4.py:303-312` |
| N5 | **The handoff's repair-4 paragraph contradicts itself.** It opens "It closes the six blocker ids with five fixes". Further down it says "none counts as closed until lens round 5 grades the repair". | `handoffs/2026-10-05_E.md`, the "Continuation, repair 4" paragraph and the blockers paragraph |
| N6 | **Lens 4's surviving mutants still survive, as the note says** (carried as L4-FA-N1..N3). Each was run with `-m "day12 or fixture or ap3"`, all three with the same result as unmutated, `395 passed, 9 skipped, 1751 deselected`: <br>- M7: `r_f13_compare.py` always returns 0; <br>- M14: the local branch's `_check_header(caps.proc, "F13")` deleted; <br>- M15: the loader's `proc_sha` taken as a plain sha256. | `scratchpad/lens-E12-r5-regression/mutate2.py` |

## What I could not break (re-measured, with figures)

**Suite and lint at `174ed35`.** Each figure equals the note's.

| Run | Git Bash (`new`, `mut`) | PowerShell 5.1 (`new`) |
|---|---|---|
| full suite `-rs` | `2145 passed, 10 skipped in 270.90s`, exit 0 | `2145 passed, 10 skipped in 287.62s`, exit 0 |
| skip lines | `SKIPPED [3] tests\test_day12_r_captures.py:156: r_vectors_not_committed_dec77: F13 needs the aSAH vectors, which exist only inside the r-captures job (PROOFPACK_ASAH_VECTORS is not set)`; `[5] ...:175: r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)`; `[1] ...:166: r_captures_not_captured: F13 recorded (absent: fixtures/r/proc_asah.json, fixtures/r/f13_engine_comparison.json)`; `[1] tests\test_doctor_cli.py:57: write access cannot be revoked for this user` | the same four |
| `--collect-only -q` | `2155 tests collected` | `2155 tests collected` |
| `-m day12` | `148 passed, 9 skipped, 1998 deselected` | the same |
| `-m day11` / `-m day10` | `144 passed, 2011 deselected` / `262 passed, 1893 deselected` | the same |
| `-m "day12 or fixture or ap3"` | `395 passed, 9 skipped, 1751 deselected` | the same |
| the five files (`test_day12_carried.py`, `test_e12_repair1.py` .. `test_e12_repair4.py`) | `120 passed` | `120 passed` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `315 files already formatted` | the same |

Against `614edd2` (lens 4's figures), `-m day12` and the full suite each grew by exactly 20, the new file's count; `day11` and `day10` are unchanged in passes.

The note's PowerShell environment form works in PowerShell 5.1. With the variable set to `x`, `Remove-Item Env:PROOFPACK_ASAH_VECTORS -ErrorAction SilentlyContinue` left it empty.

**Fails pre-build.** `tests/test_e12_repair4.py` copied into `old` (`614edd2`) gave `10 failed, 10 passed`. The ten failures are the ones the note lists, and each first `E` line is the one the note quotes:
- the three `_outside_the_three` plants: `assert ['5,Good,0,0.13,6.0'] == []`;
- `_names_a_missing_allowed_file`: `assert "missing: ['f13_engine_comparison.json']" in "r-upload-guard: the files are ['proc_asah.json', 'rms_val_prob_f4.json'], not exactly ...`;
- the read-error test: `PermissionError: [Errno 13] denied`;
- FA-B4: `assert 'never from ``fixtures/r/``' not in ...`;
- the four `test_rg_b2_...` cases: each sentence still present.

None aborted at import.

**Nothing weakened.**
- `git diff --name-status 614edd2 174ed35`: 6 files M (`fixtures/r/README.md`, `fixtures/r/capture.R`, `handoffs/2026-10-05_E.md`, `scripts/r_upload_guard.py`, `src/proofpack/fixtures.py`, `tests/test_day12_r_captures.py`) and 3 A (the two lens-4 notes, `tests/test_e12_repair4.py`); none D.
- No `def test_` line was removed. The diff adds no `skip`, `xfail`, `.only` or `TODO`; its only mark lines are `pytestmark = pytest.mark.day12` and four `parametrize`.
- `.github/` and `pyproject.toml` are unchanged. `day12` is `pyproject.toml` line 102. `ci.yml` reads every `day\d+` marker out of `pyproject.toml` (lines 43-60), so `day12` runs there.
- `src/proofpack/stats/`, `tests/test_e11_repair3.py` and `tests/test_day12_carried.py` are unchanged. `test_e11_repair3.py` collects 20 tests, as its docstring says (E11 N4).
- Index line endings: `i/lf` for every changed file.

**The workflow** (`yaml.safe_load`, unchanged by this diff):
- `on`: `workflow_dispatch`, and `push` with paths `fixtures/r/**` and `.github/workflows/r-captures.yml`;
- `permissions: {'contents': 'read'}`; jobs `['capture']`; container `rocker/r-ver:4.5.1`; no job-level permissions;
- `uses`: `actions/checkout@v4`, `astral-sh/setup-uv@v6` (`enable-cache: False`) and `actions/upload-artifact@v4` (`path: upload/`, `retention-days: 30`, `if-no-files-found: error`).

The only `git` lines are comments (26-28) and the `apt-get install ... git` step (56-57). No `run` line calls `git add` or `git commit`, as the new `capture.R` comment says. `.gitignore` lines 16-17 are `*asah*vectors*` and `fixtures/r/*.csv`, as the new `fixtures.py` comment says.

**The CLI commands, both shells.**
- `doctor --offline`: exit 0, 17 `[ok` lines, last line `Next step: write criteria.yaml (...)`.
- `fixtures --offline --out DIR --r-captures`: exit 0; `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`.
  - The all-absent `r-captures: r_captures_not_captured - no R capture is committed (...); F13 and F13b stay 'no oracle recorded' until fixtures/r/capture.R's output is committed` is unchanged.
  - `unverified` appears 37 times in `fixtures_report.json`, in each shell. The two shells' `rows` arrays compare equal.
  - F13: `no_oracle_recorded | [unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and the engine comparison the r-captures job records beside it (fixtures/r/f13_engine_comparison.json) are not both committed; ...`.
  - F13b: `no_oracle_recorded | [unverified until captured] the rms::val.prob capture (fixtures/r/rms_val_prob_f4.json) is not committed; ... (f4_expected.json r_rms_val_prob: [pending])`.
- `capture_fixture_oracles.py --check`: exit 0, `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`.
- The YAML one-liner: `['capture']`.
- `r_capture_drift.py --committed fixtures/r --fresh fixtures/r`: exit 0, ending `no capture is committed; nothing to compare`, `0 difference(s) above 1e-12`.

**Mutants** (`mut`, `-m day12`, unmutated `148 passed, 9 skipped, 1998 deselected`). Each is one edit, applied alone and restored:

| Mutant | Failed | Failing tests |
|---|---|---|
| M20 (local loop over `(R_CAPTURE_FILES[0],)`) | 2 | `test_fa_b1_...[f13_engine_comparison.json a directory]`, `[... written as {"values": ]` |
| M20b (over `(R_COMPARISON_FILE,)`) | 4 | `test_e12_repair1.py::test_fa_b2_an_unreadable_capture_is_not_called_not_captured`, `test_e12_repair3.py::test_the_loader_names_a_capture_path_that_is_a_directory_unreadable`, `test_fa_b1_...[proc_asah.json ...]` x2 |
| M18 (`worst = max(worst, dev)` deleted) | 1 | `test_fa_b2_the_suite_only_row_reports_the_largest_recorded_deviation` |
| M18b (`worst = dev`) | 1 | the same |
| mine, M18c (`worst = max(worst, round(dev, 7))`) | 1 | the same |
| M1 (job shape: `raise OracleFileMissing(...)` -> `raise OracleAbsent(F13_ABSENT)`) | 1 | `test_rg_n1_...[proc_asah.json absent]` |
| mine, M26 (job-shape unreadable loop over the vectors only) | 2 | `test_day12_r_captures.py::test_structure_an_unreadable_capture_is_not_matched`, `test_rg_n1_...[proc_asah.json written as ...]` |
| mine, M27 (job-shape unreadable loop over `proc_asah.json` only) | 4 | `test_structure_in_the_job_shape_a_missing_vectors_file_is_not_matched`, `test_e12_repair3.py::test_fa_b2_a_corrupt_vectors_file_...`, `test_rg_n1_...[vectors at a path ...]`, `[vectors with 81,... appended]` |
| G1 (guard labels every entry by its path) | 2 | `..._outside_the_three[a directory named ...]`, the read-error test |
| G2 (count line lists every path) | 4 | the three `_outside_the_three` cases and the read-error test |
| G3 (read error not caught) | 1 | the read-error test |
| G4 (read error ignored) | 1 | the read-error test |
| mine, G5 (`missing` always empty) | 2 | `test_fa_b3_the_upload_guard_names_a_missing_allowed_file`, `test_e12_repair3.py::test_dec77_upload_guard_control_...` |
| mine, G6 (the read-error problem printed with the full path) | 1 | the read-error test |

I also ran the whole suite less `slow` (`-m "not slow"`, `PROOFPACK_TR39_FULL` unset, in `mut`), as the note does. Each figure equals the note's:
- M20: `2 failed, 2138 passed, 11 skipped, 4 deselected in 253.93s`;
- M18: `1 failed, 2139 passed, 11 skipped, 4 deselected in 247.18s`;
- M1: `1 failed, 2139 passed, 11 skipped, 4 deselected in 252.12s`.

In each case the failing tests were the same ones `-m day12` names. Under G1, the empty-file and `sub/` plants pass and the directory plant fails, as the note explains.

**Lens 4's blockers, by execution.**
- **FA-B1 / RG-B1, lens 4's own CLI repro.** I put the synthetic capture's three JSON files in `new/fixtures/r/` and wrote `f13_engine_comparison.json` as `{"values": `. `fixtures --offline --r-captures` then gave exit 6, `rows 46: matched 35, not matched 1, ...`, F13 `not_matched | oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (JSONDecodeError)`, and the status line `partial_see_rows_f13_f13b - ... unreadable: fixtures/r/f13_engine_comparison.json; absent: none; row F13 not_matched`.
  - With the record intact: exit 0, F13 `suite_only`, `max abs deviation 5.551115123125783e-17`. The reason says "the engine commit is not this checkout's HEAD (174ed35...); this command did not run that comparison on this checkout's engine", and nowhere calls the result a match.
  - The files were removed afterwards and `git status --short` was empty.
- **The same class, widened (my probe, worktree source).** In each of the three committed JSON files I wrote `null`, `[]`, `"x"`, `{}`, the empty string, `0`, a BOM followed by `{}`, and `NaN`. The capture-file cases ran with the vectors read and not read; the comparison-file cases ran with the vectors not read. All 40 cases gave `not_matched`, exit 6: 35 `oracle_file_unreadable`, and 5 `r_capture_input_mismatch` (the `{}` cases).
- **Job shape, a corrupt record (`null` and `{"values": `).** Both were run with the variable set and the three JSON files in `fixtures/r/`. `-m day12` gave `1 failed, 156 passed`, against a baseline of `157 passed, 1998 deselected`, 0 skipped. In this shape row F13 itself stays `matched`, because it reads the vectors and the record is the job's output.
- **FA-B3 / RG-B2 (a), beyond the test's plants.** The guard (`new/scripts`, run as a subprocess) was given six plants of mine. None of the vectors' 81 lines appeared in stdout or stderr, and each exited 1:
  - a data-line name two directories down;
  - a data-line-named file holding that line;
  - `proc_asah.json` holding three rows;
  - `proc_asah.json` as a directory holding a data-line name;
  - the header as a file name;
  - `asah_vectors.csv` copied in.
- **FA-B4.** With the variable unset, the loader read no vectors although `asah_vectors.csv` lay beside the JSON files (`vectors_path None`, `vectors None`). That is the new R3-3 wording.
- **RG-B2 (b).** In a throwaway repository, plain `git add <outside path>` gave `fatal: ... is outside repository at ...`. `git --work-tree=<temp> add dec77/asah_vectors.csv`, a commit and `git show HEAD:dec77/asah_vectors.csv` printed `5,Good,0,0.13,6.0`. The new comment names this route rather than denying it.
- **Lens 4 regression N1 (M1) and N3 (the "compare job" docstring) are closed.** M1 fails 1 test (table above). `grep "compare job"` finds nothing in `tests/test_day12_r_captures.py`.

**The note's other claims.**
- The repair-3 guard tests (`-k test_dec77_upload_guard`): `7 passed`.
- `F13_NAMES` has 16 names and ends with `roc.test estimate 2`, as `test_fa_b2`'s docstring says.
- The new file collects 20 tests (4 + 5 + 1 + 3 + 1 + 1 + 4 + 1), as the handoff's item 0 says.

## What I could not check

- Any run of `capture.R` or of the r-captures job. Nothing here can run them: there is no R and nothing is pushed. So real pROC and rms values, the job log, the artefact and `$RUNNER_TEMP` in the container are unseen.
- Real aSAH figures. Under DEC-77 they exist only on the runner; I used the tests' synthetic rows.
- The guard with symbolic links or an unreadable subdirectory under `rglob`. Windows needs privileges for links, and the runner is Linux, possibly as root. The note's refused sentence names "an exception raised before `check` runs" as unconstructed, and so do I.
- A re-derivation of DeLong and the recalibration fits. `src/proofpack/stats/` and the comparison functions are unchanged by this diff (`fixtures.py`'s diff is a 5-line comment), and lens 4 re-derived both at `614edd2`. That attack belongs to this round's fresh-attack lens.

## Sentences I refused to write

- "The guard can never print a vectors line": I tried six plants of my own plus the test's four; links, and exceptions before `check`, were not tried.
- "Row F13 fails on every unreadable needed file": 40 garbage bodies and 9 named cases; M7, M14 and M15 survive.
- "E12 passed", "Gate 2 is met", "F13 matches pROC", "the aSAH rows cannot leave the runner".
