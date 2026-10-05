# fixtures/r - the R captures (F13, F13b)

Build day 12 (lane E, 5 October 2026). These files let the engine's DeLong and calibration
figures be checked against R by code, on a free GitHub Actions runner (section 10, gate 2 of
the plan).

## What `capture.R` computes

Run from the repository root with `Rscript fixtures/r/capture.R`. It uses base R (with
`stats`, `utils` and `tools`), `pROC`, `rms` and `jsonlite`, and nothing else.

- **F13, `proc_asah.json`.** pROC's own `aSAH` data. For `outcome ~ s100b` and
  `outcome ~ ndka`, with `levels = c("Good", "Poor")` (controls, cases) and
  `direction = "<"` written out rather than detected: `auc()`, `var(roc, method = "delong")`,
  `ci.auc(method = "delong", conf.level = 0.95)` and the case and control counts. Then
  `roc.test(roc_s100b, roc_ndka, method = "delong", paired = TRUE)`: the statistic, the
  p-value, the two estimates, and `conf.int` when the installed pROC returns one.
- **F13b, `rms_val_prob_f4.json`.** `rms::val.prob(p, y, pl = FALSE)` on the committed F4
  rows (`fixtures/f4_calibration.csv`), every statistic it returns under the name it gives
  it. Beside it, `glm(y ~ qlogis(p), binomial)` (the joint intercept and slope) and
  `glm(y ~ offset(qlogis(p)), binomial)` (calibration-in-the-large), each at R's default
  `glm.control()` and at `epsilon = 1e-14`, with standard errors, deviance, iterations and
  whether the fit converged. The engine's `intercept` is compared with `val.prob`'s
  `Intercept` and the joint `glm`; its `intercept_large` with the offset `glm`.
- **`asah_vectors.csv`.** The input the F13 numbers were computed on, in pROC's row order:
  the row name, the outcome label, `y` (1 = Poor, 0 = Good), `s100b` and `ndka`.

Every number is written with 17 significant digits. Each JSON carries, under `meta`,
`R.version.string`, `sessionInfo()` as text, the pROC, rms and jsonlite versions,
`getOption("repos")` (the CRAN snapshot the packages came from), the run date in UTC and
the GitHub run id and commit when it runs in Actions; under `input`, the sha256 of the F4
bytes read and of the vectors file written.

## Running the job

The workflow is `.github/workflows/r-captures.yml`. It runs on `workflow_dispatch` and on
a push that changes `fixtures/r/**` or the workflow itself:

    gh workflow run r-captures.yml
    gh run list --workflow r-captures.yml --limit 1
    gh run download <run id> --name r-captures --dir fresh

Job `capture` runs in the container `rocker/r-ver:4.5.1`, installs pROC, rms and jsonlite
from the repository the image is set to, runs the script and uploads the three files as
the artefact `r-captures` (kept 30 days). Job `compare` checks them against any capture
already committed (a difference above 1e-12 fails: `scripts/r_capture_drift.py`), then
copies them into `fixtures/r/` on the runner and runs `pytest -m day12` (no comparison may
skip) and `proofpack fixtures --offline` (rows F13 and F13b). The workflow has read-only
permissions, uses no secret and commits nothing.

## Committing a capture (the orchestrator, not the workflow)

1. Download the artefact of a green run (above) and read both JSON files' `meta`.
2. Copy `proc_asah.json` and `rms_val_prob_f4.json` into `fixtures/r/`. Whether
   `asah_vectors.csv` may be committed as well is open (below).
3. Replace `r_rms_val_prob` in `fixtures/f4_expected.json` (now `[pending]`) with the
   capture's figures and its run id; `tests/test_day12_r_captures.py` then requires that.
4. Run `python -m pytest -m day12` and `proofpack fixtures --offline`; F13 and F13b should
   read `matched`. Commit, naming the run id in the message.

## Where the aSAH data comes from

`aSAH` is a data set shipped inside the R package pROC on CRAN, loaded by the script with
`data("aSAH", package = "pROC")`. pROC's licence is recalled as GPL (>= 3) and its authors
as Xavier Robin, Natacha Turck, Alexandre Hainard and others **[unverified: the CRAN page
was not fetched on build day 12; the capture's `meta.packages.pROC` records the version
used]**. The data set's documentation in pROC is recalled as crediting Turck and colleagues
(2010) **[unverified: not read]**.

**Not committed today.** This repository's `pyproject.toml` says `Proprietary`; whether a
copy of pROC's `aSAH` data may sit in it is a question for Josh. Until he answers,
`asah_vectors.csv` exists only in the runner and in the 30-day artefact. The alternative:
commit only the R aggregates and the vectors' sha256 (already inside `proc_asah.json`), and
let the workflow's `compare` job run the engine comparison on the runner, where the vectors
exist. Without the vectors file in the tree, F13 stays `no oracle recorded` locally with
the reason naming the absent file.
