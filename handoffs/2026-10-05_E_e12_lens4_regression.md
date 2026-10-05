# Lane E - build day 12 (E12, the R captures) - lens 4, cold regression-and-record, at `614edd2` (E12 repair 3, DEC-77; pre `e6ad3c8`; Monday 5 October 2026)

**FAIL. 2 blockers.**

Every count and command in the repair-3 note reproduces in Git Bash and in PowerShell 5.1. Exceptions: the note's Bash-form simulation command (N4), and four first-failure lines the note does not list (N5).

Lens 3's two blockers no longer reproduce. L1 fails 4 tests. Lens 3's literal G3 is now equivalent: it fails 2 tests through anchors only. Its moves to the files the recorded-comparison gate needs (G3a, G3b) and the runner-shape skip mutant R1 each fail behaviourally.

But B2's class reproduces for the new committed file. A present but corrupt `fixtures/r/f13_engine_comparison.json` is called absent and "[unverified until captured] ... not both committed" under a one-line mutant of `f13_oracle`. That mutant survives the full suite (B1).

Two shipped sentences about DEC-77 assert what a check prevents. Each is false on an input I built and ran (B2).

`capture.R` and the r-captures workflow have still never run. Gate 2 of section 10 is not met. F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]`. I re-measured this in both shells.

Setup. Detached worktrees under `scratchpad/lens-E12-r4-regression/`:
- `new` (`614edd2`): the Git Bash suite, CLI commands and the job-shape simulation;
- `newps` (`614edd2`): the PowerShell 5.1 suite and commands, plus probes, each restored from a copy and checked with `git status --short`;
- `mut` (`614edd2`): 13 mutants, each applied alone and restored by a script;
- `old` (`e6ad3c8`): `tests/test_e12_repair3.py` copied in.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Suite runs used `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8`, `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`, with `PROOFPACK_ASAH_VECTORS` unset unless stated. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1. I committed, pushed, downloaded and installed nothing, and I did not install R. This note is the only file I wrote outside the scratchpad. The main tree is clean at `614edd2`; `origin/main` is `169bb15`.

## Blockers

| # | Blocker | Verbatim evidence | One-line repro |
|---|---|---|---|
| B1 | **Lens 3 B2's class, reproduced for `f13_engine_comparison.json`. The `f13_oracle` branch that names an unreadable recorded comparison is pinned by no test. Reversed, a present but corrupt record makes row F13 `no_oracle_recorded`. The reason then calls the file absent, and `proofpack fixtures` exits 0.** The orchestrator's item 3 asks that the unreadable-file rule hold for every file each gate needs, `f13_engine_comparison.json` included. The test-gate side is pinned: G3a fails 6 tests. The report-row side is not. `test_outside_the_job_an_unreadable_needed_file_fails_the_recorded_comparison[f13_engine_comparison.json unreadable]` asserts only that the pytest reads `failed`, and any status other than `suite_only` gives that. | Mutant M2, in `src/proofpack/fixtures.py` `f13_oracle` (the `vectors_path is None` branch): `for rel in (R_CAPTURE_FILES[0], R_COMPARISON_FILE):` became `for rel in (R_CAPTURE_FILES[0],):`. Results: `-m "day12 or fixture or ap3"` 0 FAILED (survives), and the full suite `2125 passed, 10 skipped in 238.38s`, the same as unmutated. On the synthetic capture with `f13_engine_comparison.json` written as `{"values": `, unmutated: `not_matched \| oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (JSONDecodeError) \| exit 6`. Under M2: `no_oracle_recorded \| [unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and the engine comparison the r-captures job records beside it (fixtures/r/f13_engine_comparison.json) are not both committed; ... (absent: fixtures/r/f13_engine_comparison.json) \| exit 0`. The status line under M2 contradicts itself: `unreadable: fixtures/r/f13_engine_comparison.json; absent: none; row F13 no_oracle_recorded`. The record replaced by a directory gives the same (`PermissionError` unmutated; `no_oracle_recorded`, exit 0 under M2). The note's mutation table does not list this mutant. | in `f13_oracle`, `(R_CAPTURE_FILES[0], R_COMPARISON_FILE)` -> `(R_CAPTURE_FILES[0],)`; `python -m pytest -q` |
| B2 | **Two shipped DEC-77 sentences assert what a check prevents; each is false on an input I built and ran, and the note records no counter-example for either** (hard rule). (a) `scripts/r_upload_guard.py` docstring: "It prints file names and counts, never a line of the vectors." It prints every name in the directory. A file named with a vectors data line puts that line in the job log. (b) `fixtures/r/capture.R`, the comment above the `PROOFPACK_ASAH_VECTORS` checks: "...must lie outside the working directory (the checkout), so that no git command and no upload of the checkout can reach it." `git --work-tree=<runner temp> add` reaches it. | (a) The guard was run on `upload/` holding the three synthetic JSON files plus a file named `5,Good,0,0.13,6.0` (the synthetic vectors' line 7), with `PROOFPACK_ASAH_VECTORS` naming the synthetic vectors. It printed `r-upload-guard: the files are ['5,Good,0,0.13,6.0', 'f13_engine_comparison.json', 'proc_asah.json', 'rms_val_prob_f4.json'], not exactly [...]`, then exit 1. The exit is right, but the line is in stdout. (b) In a throwaway repository: plain `git add <outside path>` gave `fatal: ... is outside repository`, so the sentence holds in that case. `git --work-tree=<runner_temp> add dec77/asah_vectors.csv && git commit` then `git show HEAD:dec77/asah_vectors.csv` printed `5,Good,0,0.13,6.0`. Neither route is in today's workflow; the sentences are still false as written. | (a) put a file named `5,Good,0,0.13,6.0` in `upload/`; `python scripts/r_upload_guard.py upload`. (b) `git --work-tree=$RUNNER_TEMP add dec77/asah_vectors.csv` |

B1 touches the F13 report row's status rule, so under DEC-12 (i) its repair gets a fresh lens. One test closes it: the synthetic capture with `f13_engine_comparison.json` unreadable and the vectors not read; assert the row is `not_matched` and the reason is `oracle_file_unreadable: fixtures/r/f13_engine_comparison.json (JSONDecodeError)`. M2 must then fail. To close B2, rewrite both sentences to name what is inspected: the guard prints the relative names of the entries and the hit counts; the R check stops on a path inside `getwd()`.

## Non-blocking (record and carry)

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **A second surviving mutant beside O1, also unrecorded: M1.** In the job shape (`vectors_path` set), `raise OracleFileMissing(R_CAPTURE_FILES[0])` became `raise OracleAbsent(F13_ABSENT)`. It survives `day12 or fixture or ap3` (0 FAILED). The note's table says the job shape gives an absent `proc_asah.json` `oracle_file_missing`, and handoff item 6 says it gives "`not_matched`, exit 6". Both are true of the code, but no test asserts the status. Measured on the synthetic capture with `proc_asah.json` deleted: unmutated `not_matched \| oracle_file_missing: fixtures/r/proc_asah.json \| exit 6`; under M1 `no_oracle_recorded \| [unverified until captured] ... \| exit 0`. In the job, the earlier `cp` step, `r_f13_compare.py` (exit 1) and the three F13 pytests (they fail on `caps.proc`) all fail first, so this is a status-label gap, not a pass. | in `f13_oracle`, `raise OracleFileMissing(R_CAPTURE_FILES[0])` -> `raise OracleAbsent(F13_ABSENT)` |
| N2 | **The DEC-77 workflow test passes steps that would print or pack the vectors.** R3-N5 records the limit by name ("through a script"). It does not record two gaps: a direct `run` line with a glob, and that the guard need only come before the upload, not immediately before it. Each line below was planted alone in a copy of `r-captures.yml`, just before the upload step (so after the guard), and `::test_dec77_the_workflow_is_one_job_with_listed_actions_no_uv_cache_and_a_guarded_upload` gave `1 passed` on each: `run: cat "$RUNNER_TEMP"/*/*.csv`; `run: find "$RUNNER_TEMP" -name "*.csv" -exec cat {} +`; `run: cp "$RUNNER_TEMP"/d*/a* upload/`; `run: tar czf upload/x.tgz "$RUNNER_TEMP"`; `run: env`. It failed (`1 failed`) on `uses: stefanzweifel/git-auto-commit-action@v5`, `run: cat $PROOFPACK_ASAH_VECTORS`, an `actions/cache@v4` step on `${{ runner.temp }}` and `>> "$GITHUB_STEP_SUMMARY"`. The README's "(so the committing action above fails it)" holds. The committed workflow has none of the passing lines; whether the job leaks is the fresh-attack lens's grade. | plant `      - run: tar czf upload/x.tgz "$RUNNER_TEMP"` before the upload step; run the test |
| N3 | **A stale sentence.** The docstring of `tests/test_day12_r_captures.py::test_f4_expected_r_rms_val_prob_is_pending_until_a_capture_is_committed` still ends "the workflow's compare job copies in a capture git does not track". Since repair 3 there is no `compare` job (`['capture']`). | `grep -n "compare job" tests/test_day12_r_captures.py` -> line 296 |
| N4 | **The note's job-shape simulation command is Bash-only.** In PowerShell 5.1, `PROOFPACK_ASAH_VECTORS=x GITHUB_RUN_ID=20261005 python scripts/r_f13_compare.py ...` gives `CommandNotFoundException: The term 'PROOFPACK_ASAH_VECTORS=x' is not recognized`. The note says "Git Bash unless marked", so this is a record only. Every other command ran in both shells. | as quoted, in PowerShell |
| N5 | **"Fails pre-build" is by API for 43 of 45.** With `tests/test_e12_repair3.py` copied into `e6ad3c8` the run gave `45 failed in 1.82s`, the note's figure, and no test passes there. The first lines: 26 `AttributeError ... 'R_VECTORS_ENV'`, 7 `... 'DEC77_UPLOADED'`, 3 `TypeError: load_r_captures() got an unexpected keyword argument 'vectors'`, 3 `assert 0 == 1` (mutant anchors), the docstring and README assertions. The note does not list four more: 2 `TypeError: test_the_skip_reasons_are_the_typed_strings() takes 1 positional argument but 2 were given`, 1 `AttributeError ... 'f13_comparison_record'`, and the leak test failing on its `TypeError`. The note measures the old behaviours directly instead. I re-measured two at `e6ad3c8`: a `proc_asah.json` directory raised `PermissionError` (now `(('fixtures/r/proc_asah.json', 'PermissionError'),)`), and the two-row assertion printed `'ndka': array([98765.4321, 12345.6789])`, verbatim as the note quotes. | `cp tests/test_e12_repair3.py <old>/tests/`; `PYTHONPATH=<old>/src python -m pytest -q tests/test_e12_repair3.py` |
| N6 | **Carried and unchanged:** R3-N1 (O1; re-measured, 0 FAILED), R3-N2 (lens 3's literal G3: 2 FAILED, both `test_each_gate_mutant_fails_the_skip_reason_test[G3a ...]` / `[G3b ...]` by anchor), R3-N3, R3-N4, R3-N5 (extended by N2), and lens 3's L3-FA-N1..N5 and L3-RG-N1..N3, N5, N6 as tabled in the handoff. | - |

## What I could not break (re-measured, with figures)

**Suite and lint at `614edd2`.** Each figure equals the note's.

| Run | Git Bash (`new`, `mut`) | PowerShell 5.1 (`newps`) |
|---|---|---|
| full suite `-rs` | `2125 passed, 10 skipped in 252.71s`, exit 0 | `2125 passed, 10 skipped in 232.84s`, exit 0 |
| skip lines | `SKIPPED [3] tests\test_day12_r_captures.py:156: r_vectors_not_committed_dec77: F13 needs the aSAH vectors, which exist only inside the r-captures job (PROOFPACK_ASAH_VECTORS is not set)`; `[5] ...:175: r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)`; `[1] ...:166: r_captures_not_captured: F13 recorded (absent: fixtures/r/proc_asah.json, fixtures/r/f13_engine_comparison.json)`; `[1] tests\test_doctor_cli.py:57: write access cannot be revoked for this user` | the same four |
| `-m day12` | - | `128 passed, 9 skipped, 1998 deselected` |
| `-m day11` / `-m day10` | - | `144 passed, 1991 deselected` / `262 passed, 1873 deselected` |
| `-m "day12 or fixture or ap3"` | `375 passed, 9 skipped, 1751 deselected` | the same |
| the four files (`test_day12_carried.py`, `test_e12_repair1.py`, `test_e12_repair2.py`, `test_e12_repair3.py`) | - | `100 passed` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `312 files already formatted` | the same |
| `--collect-only -q` | - | `2135 tests collected` |

**Nothing weakened.** `git diff --name-status e6ad3c8 614edd2` lists 12 files M and 3 A (`scripts/r_f13_compare.py`, `scripts/r_upload_guard.py`, `tests/test_e12_repair3.py`); none D. Four test functions left the day-12 module and repair 1, each replaced and listed in the handoff:
- `..._loader_reads_the_three_files...` -> `..._four_files...`;
- `..._without_its_vectors_stays_no_oracle_recorded` -> `test_structure_in_the_job_shape_a_missing_vectors_file_is_not_matched`;
- `test_drift_changed_vectors_fail_and_crlf_does_not` -> `test_drift_a_changed_vectors_sha256_fails_and_the_vectors_file_is_not_read`;
- `test_fa_b2_both_json_without_the_vectors_is_partial` -> `..._both_captures_without_the_comparison_file_is_partial`.

The added skips are `_f13_or_skip`'s (`r_vectors_not_committed_dec77`) and `_f13_recorded_or_skip`'s (`r_captures_not_captured: F13 recorded`), the named capture skips. I found no `xfail`, `skip` mark, `.only` or `TODO` added and no marker removed. `day12` is in `pyproject.toml` line 102. `ci.yml` runs every `day\d+` marker that `pyproject.toml` declares, so `day12` runs there. Index line endings: `i/lf` for every changed file.

**The workflow** (`yaml.safe_load`):
- `on`: `workflow_dispatch` and `push` with paths `fixtures/r/**` and `.github/workflows/r-captures.yml`;
- top-level `permissions: {'contents': 'read'}`; jobs `['capture']`, no job-level permissions, container `rocker/r-ver:4.5.1`;
- `uses`: `actions/checkout@v4`, `astral-sh/setup-uv@v6` (`enable-cache: false`) and `actions/upload-artifact@v4` (path `upload/`, retention 30).

The note says the same. `git check-ignore -v` names `.gitignore:17:fixtures/r/*.csv` for `fixtures/r/asah_vectors.csv`.

**The CLI commands, both shells.**
- `doctor --offline`: exit 0, 17 `[ok` lines, last line `Next step: write criteria.yaml (...)`.
- `fixtures --offline --out DIR --r-captures`: exit 0; `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`.
  - The all-absent `r-captures: r_captures_not_captured - no R capture is committed (fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json); F13 and F13b stay 'no oracle recorded' until fixtures/r/capture.R's output is committed` is byte for byte lens 3's quote.
  - `unverified` appears 37 times. The two shells' rows and summary are equal.
  - F13: `no_oracle_recorded | [unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and the engine comparison the r-captures job records beside it (fixtures/r/f13_engine_comparison.json) are not both committed; ... (absent: fixtures/r/proc_asah.json, fixtures/r/f13_engine_comparison.json)`.
  - F13b: `no_oracle_recorded | [unverified until captured] the rms::val.prob capture ... (f4_expected.json r_rms_val_prob: [pending])`.
- `capture_fixture_oracles.py --check`: exit 0, `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`.
- The YAML one-liner: `['capture']`.
- `r_capture_drift.py --committed fixtures/r --fresh fixtures/r`: exit 0, last lines `no capture is committed; nothing to compare`, `0 difference(s) above 1e-12`.

**The job-shape simulation** (Git Bash, `new`). Synthetic capture from `write_synthetic_capture`, the vectors outside the tree, `GITHUB_SHA` = HEAD. Every figure equals the note's:
- `r_f13_compare.py`: exit 0, `row F13 matched, max abs deviation 5.551115123125783e-17, 16 values, engine 614edd28975fdf5b75f020d43648616a5bd8f181`, 16 per-name lines. Of the vectors' 81 lines (header and 80 rows), 0 appear in stdout and 0 in the record.
- With `PROOFPACK_ASAH_VECTORS` set:
  - `-m day12 -rs`: `137 passed, 1998 deselected`, `SKIPPED` 0 times;
  - fixtures: `rows 46: matched 36`, with F13 `matched 5.551115123125783e-17` and F13b `matched 2.1908197478381908e-09`;
  - the guard: `0 problem(s)`, exit 0.
- Unset, with the record present:
  - `-m day12`: `134 passed, 3 skipped`;
  - F13 `suite_only` with the reason `compared inside the r-captures job, not by this command: GitHub run 20261005 recorded 16 values ... the engine commit is this checkout's HEAD. ... a local re-check needs R ...`;
  - `compared by the test suite only 6`.
- A first attempt with a mistyped vectors path gave the loud branch: `r-f13-compare: $PROOFPACK_ASAH_VECTORS (asah_vectors.csv) could not be read (FileNotFoundError)`, exit 1; `-m day12` `3 failed, 133 passed, 1 skipped`; F13 `not_matched`; and the guard exit 1 with the record missing. That runner shape failed rather than skipped.

**Mutants** (`mut`, `-m "day12 or fixture or ap3"`, baseline `375 passed, 9 skipped, 1751 deselected`; FAILED counts):

| Mutant | Result |
|---|---|
| L1 (lens 3 B2) | 4 |
| lens 3's literal G3 | 2 (anchor only, R3-N2) |
| G3a | 6 |
| R1 | 8 |
| M8 (an empty value read as unset in the loader) | 2 |
| M3 (the loader also reads `asah_vectors.csv` beside the JSON files when the variable is unset) | 2 |
| M4 (`_deviations_read`'s `suite_only` branch removed) | 4 |
| M5 (HEAD sentence always "is HEAD") | 1 |
| M6 (outside-tolerance check removed) | 2 |
| M7 (`WithheldVectors.__repr__` = `dict.__repr__`) | 2, both leak tests |
| O1 | 0, survives as recorded |
| M1 | 0 (N1) |
| M2 | 0 (B1) |

Every figure the note gives for L1, G3, G3a, R1, L3 and O1 reproduces.

**Lens 3's blockers.**
- B1: the docstring sentence is gone (`::test_the_day12_docstring_names_what_the_skip_reason_test_feeds`), and G3a / G3b / R1 fail behaviourally.
- B2: L1 fails 4 tests, among them `::test_fa_b2_a_corrupt_vectors_file_is_named_unreadable_and_row_f13_says_so`.
- Lens 3 regression N4: closed, measured old and new as in N5 above.
- Lenses 1-3's other pins: they pass at `614edd2` inside the four-file `100 passed`. I did not re-plant their mutants.

**The statistics, re-derived without repository code** (numpy and `math` only; `src/proofpack/stats` is unchanged by this diff).
- DeLong by direct O(mn) placements on the synthetic 80-row vectors (37 cases), compared with `fx.f13_engine_values(..., with_conf_int=True)` over AUROC, variance, the Wald bounds for both scores, and the paired z and p: worst `5.551115123125783e-17` (`ndka ci_delong_lo`).
- Recalibration on `fixtures/f4_calibration.csv` by my own Newton fit: slope `1.1945124796435689`, joint intercept `0.49977163424518545`, offset intercept `0.4562304654612094`. Against `f13b_engine_values()`, the worst deviation is `2.22e-16`.

**E11 lens-4 N4 / N5 sentences.** `git diff e6ad3c8 614edd2 -- src/proofpack/stats tests/test_e11_repair3.py` is empty. I read `clustered_number`'s six listed steps against its body: they match, in order.

## What I could not check

- The r-captures job on GitHub. It has never run, and nothing here can run it. Unrun on this machine:
  - `apt-get install git` in `rocker/r-ver:4.5.1`;
  - setup-uv and `uv python install` inside that container;
  - `$RUNNER_TEMP` in a container job;
  - whether `git` in the container's checkout refuses with "dubious ownership" (`git_sha()` and `test_f4_expected_...` then take their "not read" branches; I did not see that run);
  - what the job log and the artefact actually hold.
- `capture.R` (R is not installed here, by instruction), so neither `proc_asah.json`'s real shape nor pROC's values.
- Whether pytest's failure output in the job could print real vector values through an assertion form other than the one `::test_dec77_a_failing_assertion_on_the_captures_prints_no_vector_value` feeds. I found one subscripted assertion (`test_day12_r_captures.py:604`), and it reads the synthetic capture only. That attack belongs to the fresh-attack lens.
- The full DEC-77 attack (artefact, cache, log, commit routes in the committed workflow). N2 records what the workflow test lets through; grading the live routes is the fresh-attack lens's job this round.
