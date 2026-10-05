# Lane E - build day 12 (E12, the R captures) - lens 2, cold regression-and-record, at `6928511` (E12 repair 1; pre `2328e86`; Monday 5 October 2026)

**FAIL. 2 blockers.**

Both blockers are the class lens 1 raised as FA-B3 and RG-B2, and both reproduce under fresh counter-examples. Two renamed test names still say more than their checks inspect, and the commit subject says "checks that hold their names". The code repairs hold. FA-B1, FA-B2, FA-B4, RG-B1, FA-N8 and RG-N6 are closed by execution (figures below). Every count and command in the repair note reproduces, in Git Bash and in PowerShell 5.1. The new regression file fails at `2328e86` exactly as the note says: `18 failed, 2 passed`, and the passes are the two controls.

`capture.R` and the r-captures workflow have still never run, here or on GitHub. Gate 2 of section 10 is not met by measurement. F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]`. I re-measured this in both shells.

Setup. Detached worktrees under `scratchpad/lens-E12-r2-regression/`:
- `new` (`6928511`): the suite in both shells;
- `old` (`2328e86`): the new tests copied in;
- `mut` (`6928511`): mutants, probes and the note's commands, each restored with `git checkout`;
- `old45` (`45e6761`): the N4 figure.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`. Suite runs used `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8` and `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1. I committed, pushed, downloaded and installed nothing, and I did not install R. This note is the only file I wrote outside the scratchpad.

## Blockers

| # | Blocker | Verbatim evidence | One-line repro |
|---|---|---|---|
| B1 | **The renamed workflow test's name says "no git write step", and the README says that is what the test inspects. Three workflows with a git-write step pass it.** The name is `tests/test_day12_r_captures.py::test_the_workflow_declares_read_permissions_tag_pinned_actions_and_no_git_write_step`. `fixtures/r/README.md` says the workflow "has no step whose `run` calls `git push`, `git commit` or `gh`; that is what `...::test_the_workflow_declares_read_permissions_tag_pinned_actions_and_no_git_write_step` inspects". What the test does inspect is `GIT_WRITE = r"\bgit\s+(push\|commit\|tag\|merge\|rebase\|reset)\b\|\bgh\s+\w"` on each step's `run`, and nothing about `uses`. The docstring states this correctly ("no step's ``run`` matches :data:`GIT_WRITE`"). The name and the README do not. The commit subject reads "... checks that hold their names". The repair's own counter-examples are lens 1's W1-W3. W3 is the bare `git commit && git push` form, which the regex was written to catch. | I planted each mutant in a copy of the committed workflow and called the test function with `REPO` pointed at the copy. Each one **PASSED**: M1, the capture step's `run` + `&& git -C . push origin HEAD`. M2, `&& git -c user.name=x commit -am c`. M3, a step `- uses: stefanzweifel/git-auto-commit-action@v5` before the upload. The control, the committed file copied, PASSED. M6 (`/usr/bin/git push`), M7 (job `permissions: read-all`), M8 (top-level `id-token: write` added) and M9 (`image: rocker/r-ver:latest`) each FAILED, as they should. | in `mut`: `PYTHONPATH=mut/src python probe_checks.py mut`, which plants `run: Rscript fixtures/r/capture.R && git -C . push origin HEAD` and calls the test |
| B2 | **The renamed `capture.R` test's name says the script "calls only listed packages and commands". Four scripts that run `curl` or fetch a URL pass it.** The name is `::test_capture_r_writes_fixtures_py_paths_and_calls_only_listed_packages_and_commands`. Its docstring names three ways the patterns miss: "``do.call``, a string built at run time, ``eval(parse())``". None of the counter-examples below is one of those three. | Each line was appended alone to a copy of `capture.R`, with `COMMITTED` pointed at the copy. Each one **PASSED**: C1 `s <- system2` then `s("curl", "https://example.invalid")`, an alias. C2 `source("https://example.invalid/x.R")`. C3 `x <- readLines("https://example.invalid")`. C4 `get("system")("curl https://example.invalid")`, which uses a literal string, not a run-time one. The control PASSED. These FAILED: C5, a second `system2("sha256sum", "x")`; C6 `library("ggplot2", character.only = TRUE)`; C7 `base::system("curl x")`; C8 `utils::install.packages("x")`. | append `s <- system2` / `s("curl", "https://example.invalid")` to a copy of `capture.R`; call the test with `COMMITTED` at the copy |

The repair for both is wording, with no code change. Name each test after what it inspects, for example `..._and_no_run_matching_git_write` and `..._whose_package_and_command_patterns_find_only_the_listed_names`. In the README, replace "that is what ... inspects" with the regex the test applies. Name M1-M3 and C1-C4 among what is not inspected. Mutants M1-M3 and C1-C4 can serve as the counter-examples that the new names must survive. Whichever repair lands, plant them first and run them.

## Non-blocking

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **A surviving mutant on the repaired gate, the rule "an unreadable file does not skip" (repair decision 2).** Delete the two lines `if bad & set(needs): return caps, []` from `_gate`. The test meant to pin the rule, `::test_the_skip_reasons_are_the_typed_strings`, then **skips** at its last call; it does not fail. `pytest.skip.Exception` raised inside a test reads as a skip. `-m "day12 or fixture or ap3"` gives `304 passed, 9 skipped`, exit 0. The equivalent check: with that mutant and a committed unreadable `proc_asah.json` (`{"values": `, plus the rest of the synthetic capture), `-m day12` gives `62 passed, 4 skipped`, exit 0. The skip reason is false: `r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json)`. The same state unmutated gives `3 failed, 63 passed`. The report row still reads `not_matched`, and the workflow's `grep -q "SKIPPED"` would see the skip, but that workflow has never run. The gate is the one the repairer counts as statistical (DEC-12 (i)). Suggested repair: assert the gate's return outside `pytest.skip` (call `_gate` directly), or turn `pytest.skip.Exception` into `pytest.fail`. | in `mut`, delete those two lines in `tests/test_day12_r_captures.py`; `python -m pytest -q -rs tests/test_day12_r_captures.py::test_the_skip_reasons_are_the_typed_strings` gives `1 skipped` |
| N2 | **`PINNED_USES` accepts any `v<N>` ref.** `actions/checkout@v9999`, a ref that no tag may carry or that names a branch, passes the workflow test (M5). The docstring already says "a tag can be moved by its owner, so it is a pin by name only". This sits with FA-N4, Josh's question 3. | M5 in `probe2.py` |
| N3 | **The changed `tests/test_day12_r_captures.py` pins nothing in `src` on its own. It is test code.** Copied into the `2328e86` worktree: `27 passed, 8 skipped` (`SKIPPED [3] ... F13 (absent: ...)`, `SKIPPED [5] ... F13b (absent: ...)`). The pins are in `tests/test_e12_repair1.py`, which gives `18 failed, 2 passed` there. The note does not claim otherwise. | `git show 6928511:tests/test_day12_r_captures.py > old/tests/...`; `PYTHONPATH=old/src python -m pytest -q -rs tests/test_day12_r_captures.py` |
| N4 | **Several regression tests pin text, not behaviour, which fits sentence findings.** `test_rg_b1_*`, the docstring half of `test_fa_b4_*` and the comment half of `test_rg_n6_*` fail at `2328e86` on string assertions. The behaviour halves already held there: the `n_cases` fill and the `ValueError`, and the report reading `"NaN"`/`"NA"`/`"Inf"`. The verbatim first failing lines at `2328e86` are the note's: `assert 'the same es...e and counts' not in ...`, `assert 'can never read as a number' not in ...` and `assert 'cannot pass as a skip' not in ...`. | as N3, with `tests/test_e12_repair1.py` |
| N5 | **Carried items, unchanged and confirmed open:** FA-N1 (the name-list mutants), FA-N2 (the method arguments), FA-N3 (the workflow's own gates; the no-skip grep is still pinned by no test), FA-N4, FA-N5, FA-N6, FA-N7, FA-N9 and RG-N2 to RG-N7; lens 4's N6; and the capture run itself. The note's carried table names each. I found nothing open that it omits, beyond B1, B2 and N1 above. | - |

## What I could not break (re-measured, with figures)

**Suite and lint, `6928511`.** Each figure matches the note exactly.

| Run | Git Bash | PowerShell 5.1 |
|---|---|---|
| full suite | `2055 passed, 9 skipped in 254.56s`, exit 0 | `2055 passed, 9 skipped in 258.03s`, exit 0 |
| skip lines | `SKIPPED [3] tests\test_day12_r_captures.py:128: r_captures_not_captured: F13 (absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv)`, `SKIPPED [5] ...:137: r_captures_not_captured: F13b (absent: fixtures/r/rms_val_prob_f4.json)`, `SKIPPED [1] tests\test_doctor_cli.py:57` | the same three lines |
| `-m day12` | `58 passed, 8 skipped, 1998 deselected` | the same |
| `-m day11` | `144 passed, 1920 deselected` | the same |
| `-m day10` | `262 passed, 1802 deselected` | the same |
| `tests/test_e12_repair1.py` | `20 passed` | with `test_day12_carried.py`: `31 passed` |
| `tests/test_day12_carried.py` | `11 passed` | (above) |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `303 files already formatted` | the same |

The test count is 2064, which is the note's 2043 -> 2064.

**The note's commands** (in `mut`, clean, both shells).
- `doctor --offline`: exit 0, 17 `[ok` lines, `All essential checks passed.`
- `fixtures --offline --out DIR --r-captures`: exit 0, `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5`. The `r-captures: r_captures_not_captured - no R capture is committed (fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json); F13 and F13b stay 'no oracle recorded' until fixtures/r/capture.R's output is committed` line is byte for byte the note's. `unverified` appears 37 times in `fixtures_report.json`. F13 reads `no_oracle_recorded | [unverified until captured] the pROC capture (fixtures/r/proc_asah.json) and its input (fixtures/r/asah_vectors.csv) are not both committed; ...`. F13b reads `no_oracle_recorded | [unverified until captured] the rms::val.prob capture (fixtures/r/rms_val_prob_f4.json) is not committed; ... (f4_expected.json r_rms_val_prob: [pending])`.
- `capture_fixture_oracles.py --check`: exit 0, `captured values: 72 identical, 0 differ within their tolerance, 0 differ outside it`.
- The YAML jobs: `['capture', 'compare']`.
- `r_capture_drift.py --committed fixtures/r --fresh fixtures/r`: exit 0, `r-capture drift: no capture is committed; nothing to compare`.

No command failed in either shell.

**Fails pre-build.** I copied `tests/test_e12_repair1.py` into `old` (`2328e86`), where `import proofpack` resolved to `old`. Result: `18 failed, 2 passed in 3.08s`. The passes are `::test_fa_b3_control_the_committed_workflow_copied_passes` and `::test_rg_b2_control_the_committed_capture_r_copied_passes`. Every failure is an assertion, not an import abort, and each first line is the note's:
- FA-B1: `AssertionError: ('test_f13b_engine_slope_and_joint_intercept_equal_val_prob_slope_and_intercept', 'SKIPPED')`;
- FA-B2 (a)-(d): `'compare them with the engine' is contained here`, `assert 'present_comp...rows_f13_f13b' == 'partial_see_rows_f13_f13b'`, `'no R capture is committed' is contained here`, and `assert False` on `endswith(...)`;
- FA-B3 x4 and RG-B2 x3: `Failed: DID NOT RAISE AssertionError`;
- FA-N8: `assert 'not both committed' not in ...`.

**Lens 1's blockers, re-run on `6928511`.**
- **FA-B1, closed.** The synthetic capture in `mut/fixtures/r/`, `asah_vectors.csv` deleted, `val.prob Slope` +1e-3. `-m day12 -rs` gives `3 failed, 60 passed, 3 skipped`, and the only skip line is `SKIPPED [3] ...:128: r_captures_not_captured: F13 (absent: fixtures/r/asah_vectors.csv)`. `fixtures --offline --r-captures` exits 6 with `not matched: F13b (outside tolerance: val.prob Slope)` and `r-captures: partial_see_rows_f13_f13b - read: fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json; unreadable: none; absent: fixtures/r/asah_vectors.csv; row F13 no_oracle_recorded, row F13b not_matched`.
- **FA-B2, closed.** The line above names each row's status. With the full synthetic capture, unperturbed: `-m day12` gives `66 passed, 1998 deselected` (no skip, which is the state the compare job's grep needs). `fixtures` gives `matched 36, ... no oracle recorded 0` and `r-captures: present_compared_in_rows_f13_f13b - read: fixtures/r/proc_asah.json, fixtures/r/rms_val_prob_f4.json, fixtures/r/asah_vectors.csv; unreadable: none; absent: none; row F13 matched, row F13b matched`.
- **FA-B3 and RG-B2.** Lens 1's own mutants now fail (above). Fresh ones pass: B1 and B2.
- **FA-B4 / RG-N1 (lens 4's N5), closed.** The six steps of `clustered_number`'s docstring match the code line by line: suppressed returned; `n_cases None` raises; coverage flag stripped and tier appended; no interval returned; refusal below 5 with `n_cases=number.n_cases if number.n_cases is not None else n_cases`; otherwise the `ᵈ` flag. The test's figures `(4, 40, 20, 0.5, 'none')` and `n_cases` 3 reproduce (`20 passed`).
- **Lens 4's N4.** The docstring of `tests/test_e11_repair3.py` reads "collects 20 tests ... `19 failed, 1 passed`". Its file run in `old45` (`45e6761`) gives `19 failed, 1 passed in 5.29s`, and the only PASSED is `::test_control_an_unclustered_compare_keeps_the_mcnemar_p_value`.
- **RG-B1, closed.** The "cannot pass as a skip" sentence is gone. The new docstring says the test "inspects those two gates only".
- **RG-N6's sentence.** `capture.R`'s new comment says the pytest `_compare` "refuses any string". I ran `_compare({"a": 1.0}, {"a": "1.0"}, {"a": (1e-6, None)})`, which gave `[('a', 1.0, '1.0', None, False)]`.

**Mutants on the repair's code** (in `mut`, `-m "day12 or fixture or ap3"`, each restored). These are killed:

| Mutant | Result |
|---|---|
| status `all(n_values_compared > 0)` -> `any(...)` | `2 failed` |
| `f13b_oracle`'s installed-package branch removed | `1 failed` |
| `F13B_NEEDS` also needs the vectors | `1 failed` |
| the F13b report-row test gated on `_f13_or_skip` | `1 failed` |

One survives: N1.

**Nothing weakened.** `git diff --name-status 2328e86 6928511` deletes no file and modifies no gate. In the diff, the only added `skip` calls are the two gates that replace `_captures_or_skip`. No `xfail`, `.only` or `todo` was added. No marker was removed. `pyproject.toml` and `.github/` are unchanged by the repair. `day12` is in `pyproject.toml` (line 102), and `ci.yml` reads the marker list from it (lines 43-59). All seven changed or added files are `i/lf w/lf`. `git stash list` is empty.

**The workflow as committed:**
- triggers `workflow_dispatch` and `push` with paths `fixtures/r/**` and the workflow itself;
- top-level `permissions: contents: read`, and no job-level permissions;
- no `secrets.`;
- container `rocker/r-ver:4.5.1`;
- every `uses` by tag (`checkout@v4` x2, `upload-artifact@v4`, `download-artifact@v4`, `setup-uv@v6`);
- the no-skip step is `if grep -q "SKIPPED" day12.txt; then ...; exit 1; fi`.

## What I could not check

- Whether `capture.R` runs, or whether the workflow runs: there is no R here, nothing was downloaded, and the workflow needs a push.
- An installed wheel. FA-N8 is measured only with `source_checkout_root` monkeypatched to `None`; installing a wheel would need a pip install.
- Lane S: the site pins `81f1102`, and I ran nothing in `proofpack-site`.
- The equivalences lens 1 marked [unverified] (`lrm.fit` convergence; R3/R4 on aSAH).

## Sentences I refused to write

- "The workflow test proves no step writes to the repository": B1.
- "`capture.R` calls no other package or command": B2.
- "The unreadable-file rule is pinned by a test": N1.
- "The engine matches pROC and rms" / "gate 2 is met": nothing has been compared with R.
