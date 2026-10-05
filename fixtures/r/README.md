# fixtures/r - the R captures (F13, F13b)

Build day 12 (lane E, 5 October 2026). These files let the engine's DeLong and calibration
figures be checked against R by code, on a free GitHub Actions runner (section 10, gate 2 of
the plan).

## DEC-77: the aSAH rows never leave the runner

Josh decided on 5 October 2026 (DEC-77, `spec/DECISIONS_2026-09-13_Josh.md`): pROC's `aSAH`
rows are never committed to this repository and never leave the GitHub runner. The
`r-captures` job writes them to the runner's temporary space only, runs the engine's F13
comparison against pROC in the same job, and uploads only R's aggregate results, the
engine comparison and the sha256 of the vectors it used. The reasons recorded with the
decision: pROC's licence (GPL-3, `[unverified]`) against this repository's "Proprietary"
`pyproject.toml`, and ProofPack's no-row-level-data stance. The cost accepted: re-checking
F13 needs R, that is a run of the job. F13b (`rms::val.prob` on the committed F4 rows) stays
re-runnable locally.

What is committed, once a run is green: `proc_asah.json`, `rms_val_prob_f4.json` and
`f13_engine_comparison.json`, in this directory. What is never committed and never
uploaded: the aSAH vectors (`asah_vectors.csv` in the job's `$RUNNER_TEMP/dec77/`).
`.gitignore` lists `*asah*vectors*` and `fixtures/r/*.csv`.

## What `capture.R` computes

Run from the repository root with
`PROOFPACK_ASAH_VECTORS=<a file outside the checkout> Rscript fixtures/r/capture.R`; it stops
when that variable is unset or names a file inside the working directory. It uses base R
(with `stats`, `utils` and `tools`), `pROC`, `rms` and `jsonlite`, and nothing else. The two
JSON files go to `PROOFPACK_R_OUT` when set, else here.

- **F13, `proc_asah.json`.** pROC's own `aSAH` data. For `outcome ~ s100b` and
  `outcome ~ ndka`, with `levels = c("Good", "Poor")` (controls, cases) and
  `direction = "<"` written out rather than detected: `auc()`, `var(roc, method = "delong")`,
  `ci.auc(method = "delong", conf.level = 0.95)` and the case and control counts. Then
  `roc.test(roc_s100b, roc_ndka, method = "delong", paired = TRUE)`: the statistic, the
  p-value, the two estimates, and `conf.int` when the installed pROC returns one. Its
  `input` records the vectors' sha256 and row count, not the rows.
- **F13b, `rms_val_prob_f4.json`.** `rms::val.prob(p, y, pl = FALSE)` on the committed F4
  rows (`fixtures/f4_calibration.csv`), every statistic it returns under the name it gives
  it. Beside it, `glm(y ~ qlogis(p), binomial)` (the joint intercept and slope) and
  `glm(y ~ offset(qlogis(p)), binomial)` (calibration-in-the-large), each at R's default
  `glm.control()` and at `epsilon = 1e-14`, with standard errors, deviance, iterations and
  whether the fit converged. The engine's `intercept` is compared with `val.prob`'s
  `Intercept` and the joint `glm`; its `intercept_large` with the offset `glm`.
- **The aSAH vectors**, written to the file `PROOFPACK_ASAH_VECTORS` names: the row name,
  the outcome label, `y` (1 = Poor, 0 = Good), `s100b` and `ndka`, in pROC's row order.

Every number is written with 17 significant digits. Each JSON carries, under `meta`,
`R.version.string`, `sessionInfo()` as text, the pROC, rms and jsonlite versions,
`getOption("repos")` (the CRAN snapshot the packages came from), the run date in UTC and
the GitHub run id and commit when it runs in Actions; under `input`, the sha256 of the F4
bytes read and of the vectors file written.

`f13_engine_comparison.json` is written by `scripts/r_f13_compare.py` in the job
(`proofpack.fixtures.f13_comparison_record`): the engine commit (`GITHUB_SHA`), the run id,
the sha256 of `proc_asah.json` and of the vectors with their row count, and per compared
name the engine value, the R value, the absolute deviation, the tolerance (1e-6) and
whether it is within.

## Running the job

The workflow is `.github/workflows/r-captures.yml`. It runs on `workflow_dispatch` and on
a push that changes `fixtures/r/**` or the workflow itself:

    gh workflow run r-captures.yml
    gh run list --workflow r-captures.yml --limit 1
    gh run download <run id> --name r-captures --dir fresh

It is one job, `capture`, in the container `rocker/r-ver:4.5.1`. In order: install git;
check out; point `PROOFPACK_ASAH_VECTORS` and `PROOFPACK_R_OUT` at `$RUNNER_TEMP`; print
the R version and repository; install pROC, rms and jsonlite; run `capture.R`; install the
engine the way `ci.yml` does (setup-uv with its cache off, `uv python install 3.12`,
`uv sync --all-groups --locked`); the drift check against any capture already committed (a
difference above 1e-12 fails: `scripts/r_capture_drift.py`); copy the two fresh JSON files
into `fixtures/r/`; `scripts/r_f13_compare.py` (exit 1 unless row F13 is `matched`);
`pytest -m day12 -rs` (the step exits 1 when that output holds the word `SKIPPED`);
`proofpack fixtures --offline --r-captures` (rows F13 and F13b); copy the three JSON files
into `upload/` and run `scripts/r_upload_guard.py upload`, which exits 1 when a name there
matches `*asah*vectors*` or ends `.csv`, when the names are not exactly the three, or when a
file holds the vectors' header or one of their data lines; upload `upload/` as the
artefact `r-captures` (kept 30 days). With `PROOFPACK_ASAH_VECTORS` set, the F13 gate of
the day-12 tests does not skip: `tests/test_e12_repair3.py` feeds six cases (the vectors
corrupt, missing, set to the empty string or a directory; `proc_asah.json` unreadable or
absent) and reads each of the three F13 comparisons fail.

The workflow file declares `permissions: contents: read` at the top level and no
job-level permissions.
`tests/test_day12_r_captures.py::test_the_workflow_declares_read_permissions_uses_match_pinned_uses_no_run_matches_git_write`
inspects the declared permissions (top level exactly `contents: read`; each job's absent
or all `read` or `none`), the substring `secrets.`, every `uses` against `PINNED_USES` and
every `run` against the regular expression `GIT_WRITE`
(`\bgit\s+(push|commit|tag|merge|rebase|reset)\b|\bgh\s+\w`). Lens 2 of E12 planted
`git -C . push`, `git -c user.name=x commit -am c`, `secrets['GITHUB_TOKEN']` and a step
`uses: stefanzweifel/git-auto-commit-action@v5`, and that test passed on each
(`tests/test_e12_repair2.py::test_fa_b2_lens_2_workflow_mutants_pass_this_check`).
`tests/test_day12_r_captures.py::test_dec77_the_workflow_is_one_job_with_listed_actions_no_uv_cache_and_a_guarded_upload`
inspects the DEC-77 shape: one job; `uses` limited to checkout, setup-uv and
upload-artifact (so the committing action above fails it); the uv cache off; the upload of
`upload/` after the guard; and only the step that sets `PROOFPACK_ASAH_VECTORS` naming the
vectors. The job has not run yet.

## Committing a capture (the orchestrator, not the workflow)

1. Download the artefact of a green run (above) and read the three JSON files' `meta`,
   `github_run_id` and `engine_sha`.
2. Copy `proc_asah.json`, `rms_val_prob_f4.json` and `f13_engine_comparison.json` into
   `fixtures/r/`. The vectors are not in the artefact and are never committed (DEC-77).
3. Replace `r_rms_val_prob` in `fixtures/f4_expected.json` (now `[pending]`) with the
   capture's figures and its run id; `tests/test_day12_r_captures.py` then requires that.
4. Run `python -m pytest -m day12` and `proofpack fixtures --offline`; F13b should read
   `matched` and F13 `suite_only`: outside the job F13 reads the job's recorded
   comparison, and its reason names the run, the engine commit, the maximum deviation, that
   a local re-check needs R, and whether that commit is this checkout's HEAD (it is not,
   once the JSON files are committed on top of the commit the job ran). The three F13
   comparisons that need the vectors skip with `r_vectors_not_committed_dec77`. Then run
   the full suite: with a capture present, lens 1 of E12 measured 8 tests outside `day12`
   that assert the absent state failing (its FA-N5: T12 golden, fixtures counts and
   statuses, the not-captured line); they change in the same commit. Commit, naming the run
   id in the message.

## Where the aSAH data comes from

`aSAH` is a data set shipped inside the R package pROC on CRAN, loaded by the script with
`data("aSAH", package = "pROC")`. pROC's licence is recalled as GPL (>= 3) and its authors
as Xavier Robin, Natacha Turck, Alexandre Hainard and others **[unverified: the CRAN page
was not fetched on build day 12; the capture's `meta.packages.pROC` records the version
used]**. The data set's documentation in pROC is recalled as crediting Turck and colleagues
(2010) **[unverified: not read]**. Under DEC-77 no copy of it is in this repository.
