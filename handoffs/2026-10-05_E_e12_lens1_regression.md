# Lane E - build day 12 (E12, the R captures) - lens 1, regression-and-record, at `2328e86` (base `169bb15`; Monday 5 October 2026)

**FAIL. 2 blockers.**

Both blockers are hard-rule sentences in `tests/test_day12_r_captures.py` that say what a check prevents. Neither sentence has a counter-example in the build note. I built one for each, ran it, and the check let it through. The code and the figures are sound. Every count, mutant figure and command output the note quotes reproduces, with one exception (N4, an ambiguous mutant description).

The R script and the workflow have never run, here or on GitHub. Gate 2 of section 10 is not met by measurement; the note says so. Today it rests on the "pending, with the reason on the page" route: F13 and F13b are `no_oracle_recorded`, and both reasons start `[unverified until captured]` (re-measured in both shells, below).

Setup. Detached worktrees under `scratchpad/lens-E12-r1-regression/`:
- `after` (`2328e86`): the suite, the markers and the note's commands;
- `before` (`169bb15`): the new and changed tests copied in, and the base suite;
- `mut` (`2328e86`): my planted mutants and probes, each restored with `git checkout`;
- `old45` (`45e6761`): the N4 figure.

Before any figure, `PYTHONPATH=<wt>/src python -c "import proofpack;print(proofpack.__file__)"` printed that worktree's own `src\proofpack\__init__.py`, in Git Bash and in PowerShell 5.1. Suite runs had `PROOFPACK_REQUIRE_DOCX=1`, `PYTHONIOENCODING=utf-8` and `PROOFPACK_TR39_FULL=C:/Users/joshs/GPS/ProofPack/workflows/data/confusables-18.0.0.txt`. Platform: Windows 11, CPython 3.14.6, numpy 2.5.1, scipy 1.18.1.

I committed, pushed, downloaded and installed nothing, and I did not install R. One slip: `git stash -u` in the `before` worktree wrote an entry to the repository's shared `refs/stash`. I dropped it at once (`stash@{0}`, my three copied test files, `89f45b4`); `git stash list` is empty again. This note is the only file I wrote outside the scratchpad.

## Blockers

| # | Blocker | Verbatim evidence | One-line repro |
|---|---|---|---|
| B1 | **A test docstring says a misspelt skip reason "cannot pass as a skip". A misspelt skip passes.** `tests/test_day12_r_captures.py` lines 11-14: "When they are absent every comparison skips with the reason `proofpack.fixtures.R_CAPTURES_NOT_CAPTURED` exactly, and :func:`test_the_skip_reason_is_the_typed_constant` asserts that string, so a misspelt reason cannot pass as a skip." What that test inspects: the constant equals `"r_captures_not_captured"`, and `_captures_or_skip(tmp_path)` on an empty directory skips with exactly that string. It inspects no other skip. The build note records no counter-example. | I appended `def test_lens_probe_a_comparison_with_its_own_misspelt_skip(): pytest.skip("r_capture_not_captured")` and ran `-m day12`. Result: `38 passed, 8 skipped`, exit 0, `SKIPPED [1] tests\test_day12_r_captures.py:656: r_capture_not_captured`. Only the r-captures workflow's `compare` job would fail it, through its `grep -q "SKIPPED"` on any skip. That job has never run. The main CI job and a local run pass it. | append the probe test above to the file, then `python -m pytest -q -m day12 -rs` |
| B2 | **A test name says `capture.R` "uses four packages only". A `capture.R` using three more passes.** `::test_capture_r_writes_the_paths_fixtures_py_names_and_uses_four_packages_only` inspects only `library(...)` calls (must be exactly `{pROC, rms, jsonlite}`, three) and `pkg::` prefixes (a subset of `{pROC, rms, jsonlite, stats, utils, tools}`). It does not inspect `loadNamespace`, `asNamespace`, `requireNamespace` or `system2`. `capture.R` itself already calls `asNamespace("pROC")`, `asNamespace("tools")` and `system2("sha256sum", ...)`. The name does not say which four packages it means. | I appended three lines to `fixtures/r/capture.R`: `x <- loadNamespace("ggplot2")`, `y <- get("lm", envir = asNamespace("Hmisc"))` and `system2("curl", "https://example.invalid")`. Then `-k four_packages` gave `1 passed, 33 deselected`. | append those three lines, then `python -m pytest -q tests/test_day12_r_captures.py -k four_packages` |

The repair for both is wording, with the sentence scoped to what the check inspects. For example: "the skip of `_captures_or_skip` is asserted to be the constant (`::test_the_skip_reason_is_the_typed_constant`); the workflow's `compare` job fails on any skip", and a test name such as `..._and_calls_library_on_proc_rms_and_jsonlite_only`. No code change is needed. B2's name could instead be made true by extending the regexes to `loadNamespace|requireNamespace|asNamespace` and `system2`, with the probe above as the test that fails first.

## Non-blocking

| # | Record | Evidence and one-line repro |
|---|---|---|
| N1 | **N5 is not fully closed. The rewritten `clustered_number` docstring is still false in one clause and omits one check.** It now says "What the code inspects, in this order" and lists five steps. Step 4 says the refused Number keeps "the same estimate and counts". When the input's `n_cases` is `None`, the refusal writes the argument into it (`n_cases=number.n_cases if number.n_cases is not None else n_cases`). The list also omits the `ValueError` raised for `n_cases=None`, which runs between steps 1 and 2. The flags clause, which was lens 4's N5, is now right: `flags=[]` at 4 cases leaves with `['not_evaluable_shown_for_transparency']`. | input `Number(est=0.5, ci_lo=0.3, ci_hi=0.7, method="wilson", n=40, k=20, flags=[])`: `n_cases` in `None`; after `clustered_number(num, 4)` `n_cases 4` (n 40, k 20 unchanged); at 7 cases `n_cases None`; `clustered_number(num, None)` raises `ValueError a clustered Number needs the case count of its cell` |
| N2 | **Fails pre-build: neither new file fails at `169bb15` on an assertion.** `tests/test_day12_carried.py` gives `11 passed` at `169bb15`. That is expected: item 0 changed only tests and one docstring, so these tests pin behaviour the base already had. `tests/test_day12_r_captures.py` aborts at collection at `169bb15`: `AttributeError: module 'proofpack.fixtures' has no attribute 'F13B_NAMES'`, an import abort and no assertion. The note does not claim either fails at the base. It names mutants instead, and every mutant it names reproduces (see "What I could not break"). The two changed tests behave as follows at `169bb15`. `test_e10_comparison.py::test_paired_delong_callers_in_src_are_the_ones_its_docstrings_name` fails on an assertion (`assert {'fixtures.py...arison.py': 1} == ...`; `fixtures.py` 2 against 3). The `test_ap3_repair2.py` edits are relaxations and pass at the base (`29 passed`). | copy the two files into a `169bb15` worktree; `PYTHONPATH=<wt>/src python -m pytest -q tests/test_day12_carried.py tests/test_day12_r_captures.py` |
| N3 | **The note's alternative (JSON committed, `asah_vectors.csv` not) skips the four F13b pytest comparisons too, not only F13.** `_captures_or_skip` skips unless all three files are present (`len(caps.present) < 3`). F13b needs no vectors. The note says only "locally F13 then stays `no_oracle_recorded`". | synthetic capture in `mut/fixtures/r/`, vectors moved out: `-m day12` gives `38 passed, 7 skipped` (all seven comparisons, F13b's four included); `proofpack fixtures --offline` gives `matched 35, ... no oracle recorded 1` (the F13b row compares, F13 does not) |
| N4 | **The figure "no CRLF normalisation: 1 failed" depends on which line is mutated.** Mutating only the vectors' sha site (`load_r_captures`: `lf_sha256(raw)` -> `hashlib.sha256(raw)`) gives `1 failed` (`test_structure_crlf_vectors_read_as_the_same_bytes`), as the note says. Mutating `lf_sha256` itself gives `4 failed` on this Windows checkout, because `fixtures/f4_calibration.csv` is `i/lf w/crlf` here. On an LF checkout, as on the Linux runner, F4's CRLF reading has no test of its own. | `git ls-files --eol fixtures/f4_calibration.csv`; the two mutants on `src/proofpack/fixtures.py`, then `tests/test_day12_r_captures.py` |
| N5 | **One lane S change is missing from "Changes another lane must know". F13 also lost its `fixture`-marked test.** The site's `src/data/validation_report.generated.json` (lines 330, and 194 of `fixtures_report.sample.json`) cites "Engine test node id `tests/test_discrimination.py::test_f13_matches_proc_on_the_asah_dataset`; the engine records XFAIL for it at commit 3bee15c3". E12 deleted that test (decision 6). The note's lane S paragraph names the reason texts and `r_captures_status()["status"]`, but not the removed node id. Separately, `-m fixture` collects `72` at `169bb15` and `71` at `2328e86`, and no new test carries `fixture` (pyproject: "fixture: named fixture register entries (F1-F21)"). | `grep -n F13 proofpack-site/src/data/validation_report.generated.json` (read only); `pytest --collect-only -q -m fixture` in each worktree |
| N6 | **The report and the pytest disagree on string-typed values. `capture.R`'s "can never read as a number" holds by another mechanism than the one it names.** The report path (`fixtures._number`, unchanged since A-P3) parses with `float()`. With every F13b value rewritten as a JSON string, the row reads `matched`, 13 compared. The pytest `_compare` refuses non-numeric types (`_num`). `capture.R` line 69 says a non-finite value is "written as a JSON string ... so that it can never read as a number". The report reads `"NaN"` as `float('nan')` and refuses it as `oracle value not finite (nan)`. The outcome holds (never matched); the mechanism is the finite check, not the JSON type. | probe in `mut`: `"val.prob Slope": "NaN"` gives `not_matched oracle value not finite (nan): val.prob Slope`; `true` gives `not a number (bool)`; all values `str(v)` give `matched None 13` |
| N7 | **The brief's file and action names are not the build's, and the note covers only one of the three.** The brief says `fixtures/r_captures.json` (one file) and `r-lib/actions/setup-r`. The build writes `proc_asah.json`, `rms_val_prob_f4.json` and `asah_vectors.csv` (D1's and `fixtures.py`'s names) and uses `rocker/r-ver:4.5.1`. The note explains the rocker choice (decision 1) and the plan's `rms_valprob.json`, but not the brief's `r_captures.json`. There is no `handoffs/2026-10-05_E.md` at `2328e86`; the note is in the scratchpad only. | `cat spec/briefs/day12_E.md`; `git ls-tree 2328e86 handoffs/` |

## What I could not break (re-measured)

**Suite and lint.** The same counts in both shells, matching the note exactly:

| Run | `before` `169bb15` (Git Bash) | `after` `2328e86`, Git Bash | `after`, PowerShell 5.1 |
|---|---|---|---|
| full suite | `1998 passed, 1 skipped, 1 xfailed in 235.89s` | `2035 passed, 8 skipped in 297.65s` (`SKIPPED [7] tests\test_day12_r_captures.py:95: r_captures_not_captured`, `[1] tests\test_doctor_cli.py:57`) | `2035 passed, 8 skipped in 251.87s` |
| `-m day12` | - | `38 passed, 7 skipped, 1998 deselected` | the same |
| `-m day11` | - | `144 passed, 1899 deselected` | the same |
| `-m day10` | - | `262 passed, 1781 deselected` | the same |
| `tests/test_day12_carried.py` | `11 passed` | `11 passed` | `11 passed` |
| `ruff check .` / `ruff format --check .` | - / `296 files already formatted` | `All checks passed!` / `300 files already formatted` | the same |

My times differ from the note's because my two full runs overlapped.

With `docx`, `docxtpl` and `matplotlib` hidden (a `-p` plugin setting `sys.modules[name] = None`, the extra-less state of the main CI job and of the `compare` job), `-m day12` gives `38 passed, 7 skipped`. No day-12 test needs the extra. `import proofpack, proofpack.stats, proofpack.fixtures` with scipy, statsmodels, sklearn, docx, docxtpl, matplotlib and jinja2 hidden imports, with `len(F13_NAMES) 16`, `len(F13B_NAMES) 13`.

**The note's commands, both shells (`after`).**
- `doctor --offline`: exit 0, 17 `[ok` lines, `All essential checks passed.`
- `fixtures --offline --out DIR --r-captures`: exit 0. It printed `rows 46: matched 34, not matched 0, no oracle recorded 2, no independent oracle 0, not built 5, compared by the test suite only 5` and the `r-captures: r_captures_not_captured - ...` line, byte for byte as quoted. `unverified` appears 37 times in the report. F13 reads `no_oracle_recorded | [unverified until captured] the pROC capture ... (absent: fixtures/r/proc_asah.json, fixtures/r/asah_vectors.csv)` and F13b `no_oracle_recorded | [unverified until captured] the rms::val.prob capture ... (f4_expected.json r_rms_val_prob: [pending])`.
- `capture_fixture_oracles.py --check`: exit 0 in both shells, `72 identical, 0 differ within their tolerance, 0 differ outside it` (Git Bash).
- `yaml.safe_load`: `['capture', 'compare']`.
- `r_capture_drift.py --committed fixtures/r --fresh fixtures/r`: exit 0 and `no capture is committed; nothing to compare`, in both shells. The note had run it in Git Bash only.

In PowerShell, piping a command into `Select-Object -First` reports `$LASTEXITCODE -1`. That comes from cutting the pipe early. Captured into a variable instead, every exit code was 0.

**The synthetic capture copied in** (written by the test's own `write_synthetic_capture` into `mut/fixtures/r/`, then deleted):
- `-m day12`: `45 passed`, 0 skipped.
- `fixtures --offline --r-captures`: `matched 36, ... no oracle recorded 0` and `r-captures: present_compared_in_rows_f13_f13b`.
- F13: `matched`, max deviation `5.551115123125783e-17`, 16 values, class `iterative` 1e-6.
- F13b: `matched`, `2.1908197478381908e-09`, 13 values.

Each figure is the note's.

**The workflow** (`.github/workflows/r-captures.yml`):
- `on`: `workflow_dispatch`, plus `push` with paths `fixtures/r/**` and the workflow itself.
- `permissions {contents: read}`; no `secrets.`.
- Jobs: `capture` in container `rocker/r-ver:4.5.1`, uploading `r-captures` (three paths, `retention-days 30`); `compare` with `needs: capture`.
- Every `uses:` is pinned by tag (`checkout@v4`, `upload-artifact@v4`, `download-artifact@v4`, `setup-uv@v6`), as every action in `ci.yml` is.
- `day12` reaches CI through the pyproject marker list, which `ci.yml`'s marker loop reads (`ci.yml` lines 43-74). `ci.yml` itself needed no change.
- New files are `i/lf w/crlf`.

**Nothing weakened.** `git diff --name-status 169bb15 2328e86` deletes no file. The removed tests are the two named in decision 6: `test_f13_matches_proc_on_the_asah_dataset` (xfail) and `test_f13_capture_is_still_outstanding`. Two more changes:
- `test_paired_delong_has_three_callers...` was renamed, and it now asserts `fixtures.py: 3` and the new caller in both docstrings.
- The `test_ap3_repair2.py` regex widening and the `OracleAbsent` branch apply to F13/F13b only (asserted).

No `skip`, `xfail`, `.only` or `todo` was added except `_captures_or_skip`. No marker was removed. Test count: 2000 -> 2043, +45 and -2.

**Mutants, each run on `mut` and restored.** Every figure the note gives reproduces:

| Mutant | Result |
|---|---|
| N5 "refusal keeps `number.flags`" | `1 failed, 10 passed` |
| `AIDSF_STATUS_ANCHOR = "FDA_AIDSF_DATA_MGMT"` | `2 failed, 9 passed` |
| `MODEL_CARD_ANCHOR = "FDA_AIDSF_PERF_VALIDATION"` | `3 failed` |
| L6 (the two checks swapped) | `1 failed, 10 passed` |
| drift `TOL = 1e-11` | `2 failed` |
| logit instead of Wald interval | `5 failed` |
| F4 sha unchecked | `1 failed` |
| vectors sha unchecked | `1 failed` |
| tolerance class `register` | `1 failed` |
| `val.prob Intercept` -> `intercept_large` | `4 failed` |

My own mutants, each killed:

| Mutant | Result |
|---|---|
| the drift check ignores the CSV | `1 failed` |
| the drift check also compares `meta` | `3 failed` |
| an input mismatch reported `matched` | `2 failed` |
| `n_cases` / `n_controls` swapped | `5 failed` |
| `roc.test p.value` halved | `5 failed` |
| `[unverified until captured]` dropped from `F13_ABSENT` | `4 failed` (incl. `test_t12.py::test_unverified_markings_survive_to_the_page`) |
| the same dropped from `F13B_ABSENT` | `2 failed` (`test_t12.py`; no day-12 test reads F13b's marking itself) |

**N4.** The rewritten docstring says the file "collects 20 tests (17 functions, one parametrised four ways)" and gives `19 failed, 1 passed` at `45e6761`, the pass being `test_control_an_unclustered_compare_keeps_the_mcnemar_p_value`. `--collect-only` gives `20 tests collected`, and `grep -c "^def test_"` gives 17, the parametrised one with 4 ids. The `2328e86` file run in an `old45` worktree gives `19 failed, 1 passed in 4.81s`, and the only `PASSED` is that control test.

**Probes of the F13/F13b comparison code** (in `mut`, synthetic capture in a scratch directory):

| Probe | Result |
|---|---|
| a `"NaN"` value | `not_matched oracle value not finite (nan)` |
| `true` | `not_matched ... not a number (bool)` |
| no `fixture` key | `not_matched r_capture_input_mismatch: schema 'proofpack-r-capture/1' fixture None, ...` |

## What I could not check

- **`capture.R` and the workflow have never run.** There is no R here and no download was approved, and the workflow needs a push. Read against my recollection of the pROC, rms and stats documentation, with no package documentation fetched [unverified]:
  - the value names `capture.R` writes match `F13_NAMES` / `F13B_NAMES`: `val.prob`'s `C (ROC)`, `Brier`, `Intercept`, `Slope`, and `glm`'s `(Intercept)` / `logit_p` rows;
  - `ci.auc(method = "delong")` returns three values;
  - `roc.test(..., paired = TRUE)` returns `statistic`, `p.value` and `estimate`.

  Whether `tools::sha256sum` exists in R 4.5.1, whether `actions/checkout@v4` and `upload-artifact@v4` work inside `rocker/r-ver:4.5.1`, whether pROC, rms and jsonlite install there, and which CRAN snapshot the tag pins: all unmeasured.
- Two equivalences, both recorded as [unverified] in the code: `val.prob`'s `Intercept` being the joint-model intercept, and pROC's DeLong interval being the Wald interval clipped to [0, 1]. Only the first green run can show either.
- Whether `/trust/validation` on the live site states F13/F13b as pending. The site pins engine `81f1102`. Its generated data says `status pending` for both, which I read without running anything in `proofpack-site`.
- Lens 4's N6 (the F4 figure's decile bars) is a question for Josh and is carried, as the note says.
