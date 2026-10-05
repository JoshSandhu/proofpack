# fixtures/r/capture.R - the R captures for fixtures F13 and F13b (D1 section 3.2).
#
# Build day 12 (lane E, 5 October 2026). Run from the repository root:
#
#     PROOFPACK_ASAH_VECTORS=/tmp/dec77/asah_vectors.csv Rscript fixtures/r/capture.R
#
# DEC-77 (Josh, 5 October 2026): pROC's aSAH rows are never committed and never leave the
# GitHub runner. The script is written to stop when the environment variable
# PROOFPACK_ASAH_VECTORS is unset, or when the directory of the file it names, normalised,
# is the working directory or lies under it; it does not resolve a symbolic link at the file
# itself (the check and its limits are described above the check below; not run here: no R).
# The r-captures job points it at the runner's temporary space; write_lf() writes the vectors
# to that file only, and the
# cat() lines at the end print file names, the row count and four summary values. The two
# JSON files go into PROOFPACK_R_OUT when that is set (the job sets it to the runner's
# temporary space too), else into fixtures/r/:
#
#   proc_asah.json        F13: pROC on its own aSAH data - for outcome ~ s100b and
#                         outcome ~ ndka the AUROC, var(roc, method = "delong") and the
#                         ci.auc(method = "delong") bounds, and the paired
#                         roc.test(method = "delong", paired = TRUE) of s100b against ndka.
#   rms_val_prob_f4.json  F13b: rms::val.prob(p, y, pl = FALSE) on the committed F4 rows
#                         (fixtures/f4_calibration.csv), every statistic it returns under the
#                         name val.prob gives it, and beside it
#                         glm(y ~ qlogis(p), binomial) and glm(y ~ offset(qlogis(p)), binomial)
#                         at R's default glm.control() and at epsilon 1e-14.
#   $PROOFPACK_ASAH_VECTORS  the input vectors the F13 numbers were computed on, in pROC's
#                         row order: the row name, the outcome label, y (1 = "Poor", the
#                         cases; 0 = "Good", the controls), s100b and ndka. Read by
#                         scripts/r_f13_compare.py in the same job; never committed or
#                         uploaded (DEC-77).
#
# Every number is written with 17 significant digits (sprintf("%.17g")), which reads back
# to the same double. Provenance in each JSON's "meta": R.version.string, sessionInfo() as
# text, the versions of pROC, rms and jsonlite, getOption("repos") (the CRAN snapshot the
# packages came from), the run date in UTC, and the GitHub run id, sha and repository when
# those environment variables are set. The sha256 of the bytes read (F4) and of the vectors
# file written, with the vectors' row count, is in each JSON's "input"; no vector value is.
#
# Direction and levels are written explicitly, never left to pROC's auto-detection:
# levels = c("Good", "Poor") (controls, cases) and direction = "<" (a higher score is
# more likely a case).
#
# Packages: base R (with stats, utils, tools), pROC, rms, jsonlite. Nothing else.

suppressPackageStartupMessages({
  library(pROC)
  library(rms)
  library(jsonlite)
})

options(warn = 1)

OUT_DIR <- Sys.getenv("PROOFPACK_R_OUT", unset = file.path("fixtures", "r"))
F4_PATH <- file.path("fixtures", "f4_calibration.csv")
SCHEMA <- "proofpack-r-capture/1"
if (!file.exists(F4_PATH)) {
  stop("run from the repository root: ", F4_PATH, " not found")
}
dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)

# DEC-77: the vectors file must be named. What the check below inspects: the path's
# directory, normalised by normalizePath(dirname(...)); the script stops when that is the
# working directory (getwd(), the checkout in the job) or lies under it. It does not resolve
# a symbolic link at the file itself, and it does not stop git: lens 4 committed a file
# outside a repository with `git --work-tree=<that directory> add`. The job writes the
# vectors to $RUNNER_TEMP/dec77/; no run line of .github/workflows/r-captures.yml calls
# `git add` or `git commit`. Not run here (no R).
VECTORS_PATH <- Sys.getenv("PROOFPACK_ASAH_VECTORS", unset = "")
if (identical(VECTORS_PATH, "")) {
  stop("PROOFPACK_ASAH_VECTORS is not set: it must name a file outside the checkout (DEC-77)")
}
dir.create(dirname(VECTORS_PATH), showWarnings = FALSE, recursive = TRUE)
vectors_dir <- normalizePath(dirname(VECTORS_PATH), winslash = "/", mustWork = TRUE)
work_dir <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
if (identical(vectors_dir, work_dir) || startsWith(vectors_dir, paste0(work_dir, "/"))) {
  stop("PROOFPACK_ASAH_VECTORS lies inside the checkout; DEC-77 keeps the vectors outside it")
}

# ------------------------------------------------------------------ helpers

# sha256 of a file's bytes. tools::sha256sum exists in recent R; otherwise GNU coreutils'
# sha256sum (present in the rocker/r-ver image). The method used is recorded.
sha256_file <- function(path) {
  if (exists("sha256sum", envir = asNamespace("tools"), inherits = FALSE)) {
    fn <- get("sha256sum", envir = asNamespace("tools"))
    return(list(value = unname(as.character(fn(path))), method = "tools::sha256sum"))
  }
  out <- system2("sha256sum", shQuote(path), stdout = TRUE)
  list(value = strsplit(out[1], "[[:space:]]+")[[1]][1], method = "sha256sum (coreutils)")
}

json_string <- function(s) {
  as.character(jsonlite::toJSON(enc2utf8(as.character(s)), auto_unbox = TRUE))
}

# A double as JSON with 17 significant digits; a value that is not finite is written as
# a JSON string ("NaN", "NA", "Inf", "-Inf"). What reads it: the report row
# (proofpack.fixtures._number) passes a string to float() and refuses a result that is not
# finite ("NaN" -> "oracle value not finite (nan)"; "NA" -> "not a number (str)"); the
# pytest comparison (tests/test_day12_r_captures.py, _compare) refuses any string.
# Measured in E12 repair 1: the test_rg_n6_ tests of tests/test_e12_repair1.py.
json_number <- function(x) {
  x <- as.double(x)
  if (is.nan(x)) return(json_string("NaN"))
  if (is.na(x)) return(json_string("NA"))
  if (is.infinite(x)) return(json_string(if (x > 0) "Inf" else "-Inf"))
  sprintf("%.17g", x)
}

# A small JSON writer: named lists are objects, unnamed lists arrays, length-one atomics
# scalars, NULL null. Anything else is an error rather than a guess.
to_json <- function(x, indent = 0L) {
  pad <- strrep("  ", indent + 1L)
  pad0 <- strrep("  ", indent)
  if (is.null(x)) return("null")
  if (is.list(x)) {
    if (length(x) == 0L) return(if (is.null(names(x))) "[]" else "{}")
    items <- vapply(seq_along(x), function(i) to_json(x[[i]], indent + 1L), character(1))
    if (is.null(names(x))) {
      return(paste0("[\n", paste0(pad, items, collapse = ",\n"), "\n", pad0, "]"))
    }
    if (any(names(x) == "") || anyDuplicated(names(x))) stop("to_json: empty or repeated key")
    keys <- vapply(names(x), json_string, character(1), USE.NAMES = FALSE)
    return(paste0("{\n", paste0(pad, keys, ": ", items, collapse = ",\n"), "\n", pad0, "}"))
  }
  if (length(x) != 1L) stop("to_json: a vector of length ", length(x), "; wrap it in as.list()")
  if (is.logical(x)) return(if (is.na(x)) "null" else if (x) "true" else "false")
  if (is.numeric(x)) return(json_number(x))
  json_string(x)
}

write_lf <- function(lines, path) {
  con <- file(path, open = "wb")
  on.exit(close(con))
  writeLines(enc2utf8(lines), con, sep = "\n", useBytes = TRUE)
}

env_or_null <- function(name) {
  v <- Sys.getenv(name, unset = "")
  if (identical(v, "")) NULL else v
}

meta <- function() {
  list(
    script = "fixtures/r/capture.R",
    r_version_string = R.version.string,
    r_platform = R.version$platform,
    session_info = paste(utils::capture.output(print(utils::sessionInfo())), collapse = "\n"),
    packages = list(
      pROC = as.character(utils::packageVersion("pROC")),
      rms = as.character(utils::packageVersion("rms")),
      jsonlite = as.character(utils::packageVersion("jsonlite"))
    ),
    repos = as.list(getOption("repos")),
    cran_env = env_or_null("CRAN"),
    run_date_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    github = list(
      run_id = env_or_null("GITHUB_RUN_ID"),
      run_attempt = env_or_null("GITHUB_RUN_ATTEMPT"),
      sha = env_or_null("GITHUB_SHA"),
      ref = env_or_null("GITHUB_REF"),
      repository = env_or_null("GITHUB_REPOSITORY"),
      workflow = env_or_null("GITHUB_WORKFLOW")
    )
  )
}

# --------------------------------------------------------------- F13: aSAH

data("aSAH", package = "pROC", envir = environment())
asah <- aSAH
LEVELS <- c("Good", "Poor") # controls, cases
DIRECTION <- "<" # controls < cases: a higher score is more likely "Poor"
stopifnot(
  is.factor(asah$outcome),
  identical(levels(asah$outcome), LEVELS),
  !anyNA(asah$outcome), !anyNA(asah$s100b), !anyNA(asah$ndka)
)

one_roc <- function(predictor) {
  suppressMessages(pROC::roc(
    response = asah$outcome, predictor = predictor,
    levels = LEVELS, direction = DIRECTION
  ))
}
roc_s100b <- one_roc(asah$s100b)
roc_ndka <- one_roc(asah$ndka)
stopifnot(
  identical(roc_s100b$direction, DIRECTION), identical(roc_ndka$direction, DIRECTION),
  identical(as.character(roc_s100b$levels), LEVELS)
)

# pROC's own var() generic (var.roc), read from its namespace so that stats::var is never
# the one called.
proc_var <- get("var", envir = asNamespace("pROC"))

roc_values <- function(r, name) {
  ci <- as.numeric(pROC::ci.auc(r, method = "delong", conf.level = 0.95))
  v <- list(
    as.numeric(pROC::auc(r)),
    as.numeric(proc_var(r, method = "delong")),
    ci[1], ci[2], ci[3],
    length(r$cases), length(r$controls)
  )
  names(v) <- paste(name, c(
    "auc", "var_delong", "ci_delong_lo", "ci_delong_mid", "ci_delong_hi",
    "n_cases", "n_controls"
  ))
  v
}

rt <- pROC::roc.test(roc_s100b, roc_ndka, method = "delong", paired = TRUE)
paired <- list(
  "roc.test statistic" = unname(as.numeric(rt$statistic)),
  "roc.test p.value" = unname(as.numeric(rt$p.value)),
  "roc.test estimate 1" = unname(as.numeric(rt$estimate[1])),
  "roc.test estimate 2" = unname(as.numeric(rt$estimate[2]))
)
if (!is.null(rt$conf.int)) {
  paired[["roc.test conf.int lo"]] <- as.numeric(rt$conf.int[1])
  paired[["roc.test conf.int hi"]] <- as.numeric(rt$conf.int[2])
}

vectors_path <- VECTORS_PATH
write_lf(
  c(
    paste0(
      "# aSAH from the R package pROC (data(aSAH)), written by fixtures/r/capture.R in ",
      "pROC's row order; y = 1 when outcome is Poor (cases), 0 when Good (controls)"
    ),
    "row,outcome,y,s100b,ndka",
    paste(
      rownames(asah), as.character(asah$outcome),
      as.integer(asah$outcome == "Poor"),
      sprintf("%.17g", asah$s100b), sprintf("%.17g", asah$ndka),
      sep = ","
    )
  ),
  vectors_path
)
vectors_sha <- sha256_file(vectors_path)

proc_doc <- list(
  schema = SCHEMA,
  fixture = "F13",
  what = paste(
    "pROC on aSAH: roc(outcome ~ s100b) and roc(outcome ~ ndka) with levels",
    "c('Good', 'Poor') and direction '<'; auc(); var(method = 'delong');",
    "ci.auc(method = 'delong', conf.level = 0.95); roc.test(method = 'delong', paired = TRUE)"
  ),
  input = list(
    dataset = "aSAH (R package pROC)",
    n_rows = nrow(asah),
    levels = as.list(LEVELS),
    controls = "Good",
    cases = "Poor",
    direction = DIRECTION,
    y_mapping = list(Good = 0L, Poor = 1L),
    vectors_file = "$PROOFPACK_ASAH_VECTORS in the r-captures job (DEC-77: never committed or uploaded)",
    vectors_sha256 = vectors_sha$value,
    sha256_method = vectors_sha$method
  ),
  values = c(roc_values(roc_s100b, "s100b"), roc_values(roc_ndka, "ndka"), paired),
  meta = meta()
)
write_lf(to_json(proc_doc), file.path(OUT_DIR, "proc_asah.json"))

# ------------------------------------------------------- F13b: F4 and val.prob

f4_raw <- readBin(F4_PATH, what = "raw", n = file.info(F4_PATH)$size)
f4_copy <- tempfile(fileext = ".csv")
writeBin(f4_raw, f4_copy)
f4_sha <- sha256_file(f4_copy) # the sha256 of exactly the bytes parsed below
f4 <- utils::read.csv(
  text = rawToChar(f4_raw), comment.char = "#",
  colClasses = c(score = "numeric", y_true = "integer")
)
stopifnot(identical(names(f4), c("score", "y_true")), nrow(f4) == 20L)
p <- f4$score
y <- f4$y_true
logit_p <- stats::qlogis(p)

vp <- rms::val.prob(p, y, pl = FALSE)
vp_values <- as.list(unname(as.numeric(vp)))
names(vp_values) <- paste("val.prob", names(vp))

fit_values <- function(fit, label) {
  co <- summary(fit)$coefficients
  out <- list()
  for (term in rownames(co)) {
    out[[paste(label, term)]] <- unname(co[term, "Estimate"])
    out[[paste(label, term, "se")]] <- unname(co[term, "Std. Error"])
  }
  out[[paste(label, "deviance")]] <- fit$deviance
  out
}
fit_meta <- function(fit, epsilon) {
  list(iterations = fit$iter, converged = isTRUE(fit$converged), epsilon = epsilon)
}
tight <- stats::glm.control(epsilon = 1e-14, maxit = 100)
g_joint <- stats::glm(y ~ logit_p, family = stats::binomial())
g_joint_tight <- stats::glm(y ~ logit_p, family = stats::binomial(), control = tight)
g_offset <- stats::glm(y ~ offset(logit_p), family = stats::binomial())
g_offset_tight <- stats::glm(y ~ offset(logit_p), family = stats::binomial(), control = tight)

valprob_doc <- list(
  schema = SCHEMA,
  fixture = "F13b",
  what = paste(
    "rms::val.prob(p, y, pl = FALSE) on fixtures/f4_calibration.csv; glm(y ~ qlogis(p),",
    "binomial) (joint: intercept and slope) and glm(y ~ offset(qlogis(p)), binomial)",
    "(offset: calibration-in-the-large) at glm.control() and at epsilon 1e-14"
  ),
  input = list(
    file = "fixtures/f4_calibration.csv",
    bytes = length(f4_raw),
    sha256 = f4_sha$value,
    sha256_method = f4_sha$method,
    n_rows = nrow(f4),
    events = sum(y)
  ),
  values = c(
    vp_values,
    fit_values(g_joint, "glm joint"),
    fit_values(g_joint_tight, "glm joint tight"),
    fit_values(g_offset, "glm offset"),
    fit_values(g_offset_tight, "glm offset tight")
  ),
  fits = list(
    "glm joint" = fit_meta(g_joint, stats::glm.control()$epsilon),
    "glm joint tight" = fit_meta(g_joint_tight, tight$epsilon),
    "glm offset" = fit_meta(g_offset, stats::glm.control()$epsilon),
    "glm offset tight" = fit_meta(g_offset_tight, tight$epsilon)
  ),
  meta = meta()
)
write_lf(to_json(valprob_doc), file.path(OUT_DIR, "rms_val_prob_f4.json"))

cat("wrote", file.path(OUT_DIR, c("proc_asah.json", "rms_val_prob_f4.json")), sep = "\n")
cat("wrote the aSAH vectors (", nrow(asah), " rows) to PROOFPACK_ASAH_VECTORS; not printed (DEC-77)\n",
  sep = ""
)
cat("s100b auc", sprintf("%.17g", proc_doc$values[["s100b auc"]]), "\n")
cat("roc.test statistic", sprintf("%.17g", paired[["roc.test statistic"]]), "\n")
cat("val.prob Slope", sprintf("%.17g", vp_values[["val.prob Slope"]]), "\n")
cat("f4 sha256", f4_sha$value, "\n")
